import numpy as np
import pytest

import agent.ufh_world_state as world_state_module
from agent.ufh_world_state import (
    RasterDependencyError,
    RasterDomainError,
    RasterRoutingDomain,
    ReservationConflictError,
    SnapshotMismatchError,
    WorldState,
)


def domain(**kwargs):
    return RasterRoutingDomain(
        origin_mm=(100.0, 200.0),
        width_mm=45.0,
        height_mm=35.0,
        cell_size_mm=10.0,
        **kwargs,
    )


def test_mm_cell_conversion_uses_yx_cells_and_clips_partial_cell_centres():
    state = domain()
    assert state.shape == (4, 5)
    assert state.mm_to_cell((100.0, 200.0)) == (0, 0)
    assert state.mm_to_cell((144.999, 234.999)) == (3, 4)
    assert state.cell_to_mm((3, 4)) == (142.5, 232.5)
    assert state.cell_to_mm((3, 4), anchor="lower") == (140.0, 230.0)
    with pytest.raises(RasterDomainError):
        state.mm_to_cell((145.0, 220.0))


def test_static_and_dynamic_layers_are_separate_and_external_copies_are_safe():
    static = np.zeros((4, 5), dtype=bool)
    static[1, 1] = True
    state = domain(static_mask=static)
    route = state.mask_from_cells([(2, 3)])
    reservation = state.reserve(route, owner="circuit-1", role="SUPPLY")

    assert state.static_mask[1, 1]
    assert not state.occupied_mask[1, 1]
    assert state.occupied_mask[2, 3]
    assert state.owner_layer[2, 3] == "circuit-1"
    assert state.role_layer[2, 3] == "SUPPLY"
    assert reservation.material_cell_count == 1

    leaked_copy = state.occupied_mask
    leaked_copy[:] = False
    assert state.occupied_mask[2, 3]


def test_reservation_is_atomic_and_reports_static_and_occupied_conflicts():
    static = np.zeros((4, 5), dtype=bool)
    static[1, 1] = True
    state = domain(static_mask=static)
    state.reserve(state.mask_from_cells([(2, 2)]), owner="a", role="BODY")
    before = state.snapshot()

    proposed = state.mask_from_cells([(1, 1), (2, 2), (3, 3)])
    with pytest.raises(ReservationConflictError) as error:
        state.reserve(proposed, owner="b", role="RETURN")
    assert error.value.static_cell_count == 1
    assert error.value.occupied_cell_count == 1
    assert np.array_equal(state.occupied_mask, before.occupied_mask)
    assert set(state.reservations) == {"reservation-00000001"}


def test_clearance_reserves_cells_by_cell_footprint_distance_conservatively():
    state = RasterRoutingDomain(
        origin_mm=(0.0, 0.0), width_mm=70.0, height_mm=70.0, cell_size_mm=10.0
    )
    record = state.reserve(
        state.mask_from_cells([(3, 3)]),
        owner="loop-1",
        role="BODY",
        clearance_mm=10.0,
    )
    # Immediate neighbours touch the material cell; cells one full cell away
    # have a 10 mm footprint gap and are also included conservatively.
    assert record.reserved_mask[3, 1]
    assert record.reserved_mask[1, 3]
    assert not record.reserved_mask[3, 0]
    assert not state.can_reserve(state.mask_from_cells([(3, 1)]))


def test_clearance_fails_closed_at_world_boundary_unless_clipping_is_explicit():
    state = RasterRoutingDomain(
        origin_mm=(0.0, 0.0), width_mm=50.0, height_mm=50.0, cell_size_mm=10.0
    )
    edge = state.mask_from_cells([(0, 2)])
    with pytest.raises(ReservationConflictError) as error:
        state.reserve(edge, owner="edge", role="BODY", clearance_mm=1.0)
    assert error.value.boundary_overflow

    record = state.reserve(
        edge,
        owner="authorized-edge",
        role="BODY",
        clearance_mm=1.0,
        allow_boundary_clipping=True,
    )
    assert record.reserved_cell_count > 1


def test_release_clears_exact_reservation_and_preserves_other_owners():
    state = domain()
    first = state.reserve(
        state.mask_from_cells([(1, 1)]), owner="circuit-1", role="SUPPLY"
    )
    state.reserve(state.mask_from_cells([(2, 3)]), owner="circuit-2", role="RETURN")
    released = state.release(first.reservation_id)

    assert released.owner == "circuit-1"
    assert not state.occupied_mask[1, 1]
    assert state.owner_layer[1, 1] is None
    assert state.owner_layer[2, 3] == "circuit-2"
    with pytest.raises(RasterDomainError):
        state.release(first.reservation_id)


def test_same_owner_overlap_is_explicit_and_release_rebuilds_shared_cells():
    state = RasterRoutingDomain(
        origin_mm=(0.0, 0.0), width_mm=100.0, height_mm=100.0, cell_size_mm=10.0
    )
    first = state.reserve(
        state.mask_from_cells([(4, 4)]),
        owner="circuit-1",
        role="BODY",
        clearance_mm=10.0,
    )
    with pytest.raises(ReservationConflictError):
        state.reserve(
            state.mask_from_cells([(4, 5)]),
            owner="circuit-1",
            role="SUPPLY",
            clearance_mm=10.0,
        )

    with pytest.raises(ReservationConflictError):
        state.reserve(
            state.mask_from_cells([(4, 5)]),
            owner="circuit-1",
            role="SUPPLY",
            clearance_mm=10.0,
            allow_same_owner_overlap=True,
        )

    second_material = state.mask_from_cells([(4, 5)])
    join = (
        state.dilate_mask(second_material, clearance_mm=10.0)
        & first.reserved_mask
        & ~first.material_mask
    )
    incomplete_join = join.copy()
    incomplete_join[tuple(np.argwhere(incomplete_join)[0])] = False
    with pytest.raises(ReservationConflictError):
        state.reserve(
            second_material,
            owner="circuit-1",
            role="SUPPLY",
            clearance_mm=10.0,
            allow_same_owner_overlap=True,
            same_owner_join_mask=incomplete_join,
        )
    second = state.reserve(
        second_material,
        owner="circuit-1",
        role="SUPPLY",
        clearance_mm=10.0,
        allow_same_owner_overlap=True,
        same_owner_join_mask=join,
    )
    state.release(second.reservation_id)

    assert first.reservation_id in state.reservations
    assert state.occupied_mask[4, 4]
    assert not state.material_mask_for_owner("circuit-1")[4, 5]


def test_snapshot_and_transaction_rollback_restore_all_layers_and_ids():
    state = domain()
    baseline = state.reserve(
        state.mask_from_cells([(1, 1)]), owner="baseline", role="BODY"
    )
    snapshot = state.snapshot()
    state.release(baseline.reservation_id)
    state.reserve(state.mask_from_cells([(2, 2)]), owner="replacement", role="SUPPLY")
    state.rollback(snapshot)

    assert set(state.reservations) == {baseline.reservation_id}
    assert state.owner_layer[1, 1] == "baseline"
    assert not state.occupied_mask[2, 2]

    with pytest.raises(RuntimeError, match="abort"):
        with state.transaction():
            state.reserve(state.mask_from_cells([(3, 3)]), owner="temporary", role="RETURN")
            raise RuntimeError("abort")
    assert set(state.reservations) == {baseline.reservation_id}
    assert not state.occupied_mask[3, 3]


def test_snapshot_from_another_domain_and_missing_numpy_fail_closed(monkeypatch):
    first = domain()
    second = domain()
    with pytest.raises(SnapshotMismatchError):
        second.rollback(first.snapshot())

    monkeypatch.setattr(world_state_module, "np", None)
    with pytest.raises(RasterDependencyError, match="requires NumPy"):
        WorldState(origin_mm=(0, 0), width_mm=100, height_mm=100)

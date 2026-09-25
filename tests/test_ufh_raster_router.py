import numpy as np

from agent.ufh_raster_router import (
    route_and_reserve_raster,
    route_raster_a_star,
)
from agent.ufh_world_state import RasterRoutingDomain


def world(rows=7, columns=9, *, static_cells=()):
    static = np.zeros((rows, columns), dtype=bool)
    for cell in static_cells:
        static[cell] = True
    return RasterRoutingDomain(
        origin_mm=(0.0, 0.0),
        width_mm=columns * 10.0,
        height_mm=rows * 10.0,
        cell_size_mm=10.0,
        static_mask=static,
    )


def assert_four_neighbor_path(path):
    assert path
    assert all(
        abs(first[0] - second[0]) + abs(first[1] - second[1]) == 1
        for first, second in zip(path, path[1:])
    )


def test_directional_a_star_is_four_neighbor_and_charges_turn_penalty():
    state = world(static_cells=((3, 4),))
    result = route_raster_a_star(
        state,
        (3, 1),
        (3, 7),
        turn_penalty=7.5,
        max_expanded_cells=500,
    )

    assert result.status == "ROUTE_FOUND"
    assert result.path[0] == (3, 1)
    assert result.path[-1] == (3, 7)
    assert (3, 4) not in result.path
    assert_four_neighbor_path(result.path)
    assert result.turn_count == 2
    assert result.cost == len(result.path) - 1 + 2 * 7.5
    assert result.physical_validation == "NOT_EVALUATED"
    assert "RASTER_ROUTE_REQUIRES_VECTOR_VALIDATION" in result.diagnostics


def test_turn_penalty_can_prefer_a_longer_route_with_fewer_turns():
    static_cells = (
        (0, 4), (0, 5), (1, 3), (1, 9), (2, 9), (3, 1),
        (3, 2), (3, 5), (4, 2), (4, 3), (5, 2), (5, 9),
    )
    state = world(rows=7, columns=11, static_cells=static_cells)

    shortest = route_raster_a_star(
        state, (3, 0), (3, 10), turn_penalty=0, max_expanded_cells=500
    )
    turn_aware = route_raster_a_star(
        state, (3, 0), (3, 10), turn_penalty=8, max_expanded_cells=500
    )

    assert len(shortest.path) == 13
    assert shortest.turn_count == 3
    assert len(turn_aware.path) == 17
    assert turn_aware.turn_count == 2
    assert turn_aware.cost < (len(shortest.path) - 1) + 3 * 8


def test_equal_cost_search_has_a_stable_tie_break():
    state = world(static_cells=((3, 4),))
    paths = {
        route_raster_a_star(state, (3, 1), (3, 7), turn_penalty=3).path
        for _ in range(10)
    }

    assert len(paths) == 1
    path = next(iter(paths))
    # Direction is part of the state and the full heap key is stable.  The
    # chosen side is pinned so a later refactor cannot introduce hash-order
    # dependent routing.
    assert (4, 4) in path
    assert (2, 4) not in path


def test_static_and_foreign_occupancy_are_blocked_by_default():
    state = world(static_cells=tuple((row, 4) for row in range(7)))
    before = state.snapshot()
    result = route_raster_a_star(state, (3, 1), (3, 7), max_expanded_cells=500)

    assert result.status == "NO_ROUTE"
    assert result.path == ()
    assert "NO_FEASIBLE_4_NEIGHBOR_PATH" in result.diagnostics
    assert np.array_equal(state.occupied_mask, before.occupied_mask)
    assert state.revision == before.revision

    other = world()
    other.reserve(other.mask_from_cells([(3, 4)]), owner="foreign", role="BODY")
    occupied_result = route_raster_a_star(other, (3, 4), (3, 7))
    assert occupied_result.status == "BLOCKED_START"
    assert "START_OCCUPIED" in occupied_result.diagnostics


def test_same_owner_traversal_is_explicit_and_never_allows_foreign_crossing():
    state = world(rows=3, columns=7)
    state.reserve(
        state.mask_from_cells([(1, 0), (1, 1), (1, 2)]),
        owner="loop-a",
        role="SUPPLY",
    )
    # Walls make the centre row the only possible route.
    static = state.empty_mask()
    static[0, :] = True
    static[2, :] = True
    state.set_static_mask(static)

    blocked = route_raster_a_star(state, (1, 0), (1, 6), owner="loop-a")
    allowed = route_raster_a_star(
        state, (1, 0), (1, 6), owner="loop-a", allow_same_owner=True
    )
    assert blocked.status == "BLOCKED_START"
    assert allowed.status == "ROUTE_FOUND"
    assert allowed.path == tuple((1, column) for column in range(7))

    state.reserve(state.mask_from_cells([(1, 4)]), owner="loop-b", role="RETURN")
    foreign = route_raster_a_star(
        state, (1, 0), (1, 6), owner="loop-a", allow_same_owner=True
    )
    assert foreign.status == "NO_ROUTE"


def test_clearance_is_applied_during_search_and_can_close_a_narrow_corridor():
    static_cells = tuple((row, column) for row in (0, 6) for column in range(9))
    state = world(rows=7, columns=9, static_cells=static_cells)
    state.reserve(
        state.mask_from_cells([(3, 4)]), owner="foreign", role="BODY"
    )

    without_clearance = route_raster_a_star(
        state, (3, 1), (3, 7), clearance_mm=0, max_expanded_cells=500
    )
    with_clearance = route_raster_a_star(
        state, (3, 1), (3, 7), clearance_mm=10, max_expanded_cells=500
    )

    assert without_clearance.status == "ROUTE_FOUND"
    assert with_clearance.status == "NO_ROUTE"
    assert "NO_FEASIBLE_4_NEIGHBOR_PATH" in with_clearance.diagnostics


def test_foreign_clearance_buffer_is_obstacle_even_when_material_is_elsewhere():
    state = world(rows=15, columns=15)
    foreign = state.reserve(
        state.mask_from_cells([(7, 7)]),
        owner="foreign",
        role="BODY",
        clearance_mm=10,
    )
    result = route_raster_a_star(
        state, (7, 1), (7, 13), clearance_mm=10, max_expanded_cells=2_000
    )

    assert result.status == "ROUTE_FOUND"
    assert set(result.path).isdisjoint(
        set(map(tuple, np.argwhere(foreign.reserved_mask)))
    )
    assert (3, 7) not in result.path
    assert (11, 7) not in result.path


def test_same_owner_material_is_traversable_and_buffer_is_not_material():
    state = world(rows=7, columns=11)
    existing = state.reserve(
        state.mask_from_cells([(3, column) for column in range(2, 9)]),
        owner="loop-a",
        role="BODY",
        clearance_mm=10,
    )
    result = route_raster_a_star(
        state,
        (3, 2),
        (3, 8),
        owner="loop-a",
        allow_same_owner=True,
        clearance_mm=10,
        max_expanded_cells=500,
    )

    assert not existing.material_mask[2, 5]
    assert existing.reserved_mask[2, 5]
    assert state.owner_layer[2, 5] == "loop-a"
    assert result.status == "ROUTE_FOUND"
    assert result.path == tuple((3, column) for column in range(2, 9))

    protected_buffer_start = route_raster_a_star(
        state,
        (2, 5),
        (3, 8),
        owner="loop-a",
        allow_same_owner=True,
        clearance_mm=10,
        max_expanded_cells=500,
    )
    assert protected_buffer_start.status == "BLOCKED_START"
    assert "START_SAME_OWNER_PROTECTED_BUFFER" in protected_buffer_start.diagnostics
    assert not state.material_mask_for_owner("loop-a")[2, 5]


def test_same_owner_clearance_blocks_a_parallel_line_without_explicit_join_mask():
    state = world(rows=9, columns=15)
    existing = state.reserve(
        state.mask_from_cells([(4, column) for column in range(4, 11)]),
        owner="loop-a",
        role="BODY",
        clearance_mm=10,
    )

    result = route_raster_a_star(
        state,
        (3, 1),
        (3, 13),
        owner="loop-a",
        allow_same_owner=True,
        clearance_mm=10,
        max_expanded_cells=2_000,
    )

    assert existing.reserved_mask[3, 4]
    assert not existing.material_mask[3, 4]
    assert result.status == "BLOCKED_START"
    assert "START_CLEARANCE_BLOCKED" in result.diagnostics


def test_explicit_short_join_can_leave_same_owner_terminal_and_reserve():
    state = world(rows=9, columns=15)
    state.reserve(
        state.mask_from_cells([(4, column) for column in range(2, 6)]),
        owner="loop-a",
        role="BODY",
        clearance_mm=10,
    )
    intended_extension = state.mask_from_cells(
        [(4, column) for column in range(6, 12)]
    )
    own_material = state.material_mask_for_owner("loop-a")
    join = (
        state.dilate_mask(intended_extension, clearance_mm=10)
        & state.protected_mask_for_owner("loop-a")
        & ~own_material
    )

    blocked = route_raster_a_star(
        state,
        (4, 5),
        (4, 11),
        owner="loop-a",
        allow_same_owner=True,
        clearance_mm=10,
        max_expanded_cells=2_000,
    )
    result = route_and_reserve_raster(
        state,
        (4, 5),
        (4, 11),
        owner="loop-a",
        role="SUPPLY",
        allow_same_owner=True,
        same_owner_join_mask=join,
        clearance_mm=10,
        max_expanded_cells=2_000,
    )

    assert blocked.status == "NO_ROUTE"
    assert result.status == "ROUTE_RESERVED"
    assert result.path == tuple((4, column) for column in range(5, 12))
    assert state.material_mask_for_owner("loop-a")[4, 6]


def test_same_owner_extension_with_clearance_reserves_and_releases_safely():
    state = world(rows=9, columns=15)
    first = state.reserve(
        state.mask_from_cells([(4, column) for column in range(2, 6)]),
        owner="loop-a",
        role="BODY",
        clearance_mm=10,
    )

    intended_extension = state.mask_from_cells(
        [(4, column) for column in range(6, 12)]
    )
    join = (
        state.dilate_mask(intended_extension, clearance_mm=10)
        & first.reserved_mask
        & ~first.material_mask
    )
    result = route_and_reserve_raster(
        state,
        (4, 5),
        (4, 11),
        owner="loop-a",
        role="SUPPLY",
        allow_same_owner=True,
        same_owner_join_mask=join,
        clearance_mm=10,
        max_expanded_cells=2_000,
    )

    assert result.status == "ROUTE_RESERVED"
    assert result.reservation_id in state.reservations
    assert state.material_mask_for_owner("loop-a")[4, 11]

    state.release(result.reservation_id)
    assert first.reservation_id in state.reservations
    assert state.material_mask_for_owner("loop-a")[4, 5]
    assert not state.material_mask_for_owner("loop-a")[4, 11]
    assert state.occupied_mask[4, 5]


def test_foreign_clearance_has_priority_over_same_owner_material_exception():
    state = world(rows=7, columns=11)
    state.reserve(
        state.mask_from_cells([(3, 3)]), owner="loop-a", role="BODY"
    )
    state.reserve(
        state.mask_from_cells([(3, 5)]), owner="loop-b", role="BODY"
    )

    result = route_raster_a_star(
        state,
        (3, 3),
        (3, 9),
        owner="loop-a",
        allow_same_owner=True,
        clearance_mm=10,
        max_expanded_cells=500,
    )

    assert result.status == "BLOCKED_START"
    assert "START_OCCUPIED_BY_FOREIGN_OWNER" in result.diagnostics


def test_expansion_budget_fails_closed_without_partial_path_or_mutation():
    state = world(rows=20, columns=20)
    before = state.snapshot()
    result = route_raster_a_star(
        state, (0, 0), (19, 19), max_expanded_cells=5
    )

    assert result.status == "SEARCH_LIMIT_REACHED"
    assert result.expanded_cells == 5
    assert result.path == ()
    assert "MAX_EXPANDED_CELLS_REACHED" in result.diagnostics
    assert state.revision == before.revision
    assert np.array_equal(state.occupied_mask, before.occupied_mask)


def test_reservation_occurs_once_and_only_after_complete_path_is_found(monkeypatch):
    state = world(static_cells=((3, 4),))
    calls = []
    original = state.reserve

    def recording_reserve(mask, **kwargs):
        calls.append(tuple(map(tuple, np.argwhere(mask))))
        return original(mask, **kwargs)

    monkeypatch.setattr(state, "reserve", recording_reserve)
    result = route_and_reserve_raster(
        state,
        (3, 1),
        (3, 7),
        owner="loop-a",
        role="SUPPLY",
        turn_penalty=4,
        max_expanded_cells=500,
    )

    assert result.status == "ROUTE_RESERVED"
    assert len(calls) == 1
    assert set(calls[0]) == set(result.path)
    assert result.reservation_id in state.reservations
    assert all(state.owner_layer[cell] == "loop-a" for cell in result.path)

    failed_state = world(static_cells=tuple((row, 4) for row in range(7)))
    failed_calls = []
    failed_original = failed_state.reserve

    def should_not_be_called(mask, **kwargs):
        failed_calls.append(True)
        return failed_original(mask, **kwargs)

    monkeypatch.setattr(failed_state, "reserve", should_not_be_called)
    failed = route_and_reserve_raster(
        failed_state, (3, 1), (3, 7), owner="loop-a", role="SUPPLY"
    )
    assert failed.status == "NO_ROUTE"
    assert failed_calls == []
    assert not failed_state.occupied_mask.any()


def test_reservation_failure_rolls_back_even_after_a_partial_external_mutation(monkeypatch):
    state = world()
    baseline = state.reserve(
        state.mask_from_cells([(0, 0)]), owner="baseline", role="BODY"
    )
    before = state.snapshot()
    original = state.reserve

    def mutate_then_fail(mask, **kwargs):
        original(mask, **kwargs)
        raise RuntimeError("simulated post-write failure")

    monkeypatch.setattr(state, "reserve", mutate_then_fail)
    result = route_and_reserve_raster(
        state, (3, 1), (3, 7), owner="loop-a", role="RETURN"
    )

    assert result.status == "RESERVATION_FAILED"
    assert result.reservation_id is None
    assert "RESERVATION_ROLLED_BACK" in result.diagnostics
    assert state.revision == before.revision
    assert set(state.reservations) == {baseline.reservation_id}
    assert np.array_equal(state.occupied_mask, before.occupied_mask)
    assert np.array_equal(state.owner_id_layer, before.owner_ids)


def test_same_owner_route_reserves_only_new_cells_without_overwriting_existing_role():
    state = world(rows=3, columns=7)
    existing = state.reserve(
        state.mask_from_cells([(1, 0), (1, 1)]),
        owner="loop-a",
        role="BODY",
    )
    static = state.empty_mask()
    static[0, :] = True
    static[2, :] = True
    state.set_static_mask(static)

    result = route_and_reserve_raster(
        state,
        (1, 0),
        (1, 6),
        owner="loop-a",
        role="SUPPLY",
        allow_same_owner=True,
    )

    assert result.status == "ROUTE_RESERVED"
    assert state.role_layer[1, 0] == "BODY"
    assert state.role_layer[1, 1] == "BODY"
    assert all(state.role_layer[1, column] == "SUPPLY" for column in range(2, 7))
    assert existing.reservation_id in state.reservations
    assert result.reservation_id in state.reservations


def test_all_existing_same_owner_route_rejects_an_unmet_larger_clearance():
    state = world(rows=7, columns=9)
    state.reserve(
        state.mask_from_cells([(3, 2), (3, 3), (3, 4)]),
        owner="loop-a",
        role="BODY",
        clearance_mm=0,
    )
    before = state.snapshot()

    result = route_and_reserve_raster(
        state,
        (3, 2),
        (3, 4),
        owner="loop-a",
        role="BODY",
        allow_same_owner=True,
        clearance_mm=10,
    )

    assert result.status == "RESERVATION_FAILED"
    assert not result.reserved
    assert "INSUFFICIENT_EXISTING_OWNER_CLEARANCE" in result.diagnostics
    assert np.array_equal(state.occupied_mask, before.occupied_mask)
    assert set(state.reservations) == set(before.reservations)

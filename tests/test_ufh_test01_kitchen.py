import json
from hashlib import sha256

import numpy as np
import pytest
from shapely.geometry import LineString

from agent.ufh_test01_kitchen import (
    CANONICAL_KITCHEN_RESERVATION_IDS,
    CANONICAL_KITCHEN_ROUTE_IDS,
    DEFAULT_OPENINGS_SOURCE,
    KITCHEN_ROOM_ID,
    build_first_floor_kitchen_candidate,
)
from agent.ufh_test01_occupancy import DEFAULT_TEST01_SOURCE, import_test01_coverage_bodies


@pytest.fixture(scope="module")
def baseline_and_candidate():
    return import_test01_coverage_bodies(), build_first_floor_kitchen_candidate()


def test_builds_one_valid_bifilar_body_without_claiming_opening_alignment(baseline_and_candidate):
    _baseline, candidate = baseline_and_candidate

    assert candidate.body_accepted
    assert candidate.opening_transit_blocked
    assert candidate.overall_status == "BODY_ACCEPTED_OPENING_TRANSIT_BLOCKED"
    assert candidate.topology.valid
    assert candidate.topology.center_hairpin_present
    assert candidate.topology.interleaved_return_present
    assert candidate.topology.self_intersection_count == 0
    assert candidate.topology.duplicate_centerline_length_mm == 0
    assert LineString(candidate.centerline_mm).is_simple

    supply, returned = candidate.centerline_mm[0], candidate.centerline_mm[-1]
    assert supply[0] == returned[0]
    assert supply[1] - returned[1] == 200.0
    assert candidate.metadata["terminal_source_vector_alignment"] == (
        "NOT_ALIGNED_TO_SOURCE_VECTOR"
    )


def test_r80_length_coverage_and_global_reservation_are_proven(baseline_and_candidate):
    _baseline, candidate = baseline_and_candidate
    domain = candidate.occupancy.worlds["FLOOR_1_PLAN"].domain
    reservation = domain.reservations[candidate.reservation_id]

    assert candidate.bend_validation.valid
    assert candidate.bend_validation.radius_mm == 80.0
    assert candidate.bend_validation.outer_radius_mm == 8.0
    assert candidate.rounded_length_mm <= 90_000.0
    assert candidate.rounded_coverage_ratio >= 0.96
    assert candidate.metadata["vector_clearance_status"] == "PROVEN_R80_AXIS_CLEARANCES"
    assert candidate.metadata["minimum_own_nonadjacent_axis_clearance_mm"] >= 32.0
    assert candidate.metadata["minimum_axis_to_retained_body_mm"] >= 32.0
    assert candidate.metadata["minimum_axis_to_room_boundary_mm"] >= 24.0
    assert len(candidate.metadata["retained_body_axis_clearances_mm"]) == 7
    assert reservation.owner == f"{KITCHEN_ROOM_ID}/candidate-counterflow-body"
    assert reservation.role == "BODY"
    assert reservation.material_cell_count > 0
    assert not np.any(reservation.reserved_mask & domain.static_mask)
    for other_id, other in domain.reservations.items():
        if other_id != candidate.reservation_id:
            assert not np.any(reservation.reserved_mask & other.reserved_mask)


def test_replaces_only_kitchen_bodies_and_preserves_attic(baseline_and_candidate):
    baseline, candidate = baseline_and_candidate
    before_floor = baseline.worlds["FLOOR_1_PLAN"].domain
    after_floor = candidate.occupancy.worlds["FLOOR_1_PLAN"].domain
    before_attic = baseline.worlds["ATTIC_PLAN"].domain
    after_attic = candidate.occupancy.worlds["ATTIC_PLAN"].domain

    old_kitchen_ids = {
        body.reservation_id
        for body in baseline["FLOOR_1_PLAN"].bodies
        if body.room_id == KITCHEN_ROOM_ID
    }
    assert set(candidate.replaced_reservation_ids) == old_kitchen_ids
    assert tuple(candidate.replaced_reservation_ids) == CANONICAL_KITCHEN_RESERVATION_IDS
    assert candidate.metadata["expected_source_route_ids"] == CANONICAL_KITCHEN_ROUTE_IDS
    assert candidate.metadata["canonical_source_body_count_valid"] is True
    assert old_kitchen_ids.isdisjoint(after_floor.reservations)

    preserved_ids = set(before_floor.reservations) - old_kitchen_ids
    assert preserved_ids <= set(after_floor.reservations)
    for reservation_id in preserved_ids:
        before = before_floor.reservations[reservation_id]
        after = after_floor.reservations[reservation_id]
        assert before.owner == after.owner
        assert np.array_equal(before.material_mask, after.material_mask)
        assert np.array_equal(before.reserved_mask, after.reserved_mask)

    assert set(before_attic.reservations) == set(after_attic.reservations)
    assert np.array_equal(before_attic.occupied_mask, after_attic.occupied_mask)
    assert np.array_equal(before_attic.owner_id_layer, after_attic.owner_id_layer)


def test_openings_are_retained_only_as_unverified_candidates(baseline_and_candidate):
    _baseline, candidate = baseline_and_candidate

    assert {opening["source_vector_mm"] for opening in candidate.opening_candidates} == {
        ((12_636.0, 11_345.0), (12_937.0, 11_345.0)),
        ((12_636.0, 13_064.0), (12_937.0, 13_064.0)),
    }
    assert {opening["passage_status"] for opening in candidate.opening_candidates} == {
        "UNVERIFIED_SOURCE_VECTOR_CONFIRMED"
    }
    assert {opening["endpoint_alignment_status"] for opening in candidate.opening_candidates} == {
        "NOT_ALIGNED_TO_SOURCE_VECTOR"
    }
    provenance = candidate.metadata["opening_source_provenance"]
    assert provenance["path"] == str(DEFAULT_OPENINGS_SOURCE.resolve())
    assert provenance["sha256"] == sha256(DEFAULT_OPENINGS_SOURCE.read_bytes()).hexdigest()
    assert candidate.metadata["openings_imported"] is False
    assert candidate.metadata["building_transit_valid"] is False
    assert candidate.metadata["full_circuit_valid"] is False
    assert candidate.metadata["construction_release"] is False
    assert candidate.metadata["coverage_scope"] == "DECLARED_SUBZONE_ONLY"
    assert candidate.metadata["full_room_coverage_valid"] is False
    assert candidate.metadata["uncovered_room_residual_status"] == (
        "UNPLANNED_OUTSIDE_DECLARED_SUBZONE"
    )


def test_impossible_subzone_fails_closed_and_restores_source_bodies():
    blocked = build_first_floor_kitchen_candidate(
        subzone_mm=(13_000.0, 8_750.0, 13_300.0, 9_050.0)
    )

    assert not blocked.body_accepted
    assert blocked.overall_status == "BODY_BLOCKED_OPENING_TRANSIT_BLOCKED"
    assert blocked.reservation_id is None
    assert blocked.metadata["replacement_committed"] is False
    floor = blocked.occupancy.worlds["FLOOR_1_PLAN"].domain
    assert set(blocked.replaced_reservation_ids) <= set(floor.reservations)


def test_noncanonical_kitchen_route_cardinality_rolls_back(tmp_path):
    payload = json.loads(DEFAULT_TEST01_SOURCE.read_text(encoding="utf-8"))
    room = next(item for item in payload["rooms"] if item["id"] == KITCHEN_ROOM_ID)
    room["route_ids"].append("multi_bifilar_spiral-1")
    source = tmp_path / "source.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    blocked = build_first_floor_kitchen_candidate(source)

    assert not blocked.body_accepted
    assert blocked.reason == "CANONICAL_KITCHEN_SOURCE_BODY_SET_MISMATCH"
    assert blocked.metadata["canonical_source_body_count_valid"] is False
    floor = blocked.occupancy.worlds["FLOOR_1_PLAN"].domain
    assert set(CANONICAL_KITCHEN_RESERVATION_IDS) <= set(floor.reservations)

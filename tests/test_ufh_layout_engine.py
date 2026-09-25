from agent.ufh_layout_engine import (
    CONTAINMENT_TOLERANCE_MM,
    build_bifilar_spiral,
    build_meander,
    polyline_length,
    split_polyline_by_length,
    split_required,
    reserve_doorway_lanes,
    validate_containment,
    validate_bifilar_topology,
    validate_circuit_split,
)
import json
from pathlib import Path


RECT = [(0, 0), (7000, 0), (7000, 4000), (0, 4000), (0, 0)]


def test_meander_is_continuous_orthogonal_and_contained():
    route = build_meander((0, 0, 7000, 4000))
    assert route[0] != route[-1]
    assert all(a[0] == b[0] or a[1] == b[1] for a, b in zip(route, route[1:]))
    report = validate_containment(route, RECT)
    assert report.valid
    assert report.total_outside_length_mm == 0


def test_containment_reports_meaningful_excursion_independently():
    report = validate_containment([(100, 100), (7100, 100)], RECT)
    assert report.total_outside_length_mm > CONTAINMENT_TOLERANCE_MM
    assert report.outside_segment_count == 1
    # The metric must measure the real excursion (100 mm past the wall), not the
    # 1 mm clipping tolerance: poly.distance(piece) is a MINIMUM distance and
    # previously made every violation look like exactly 1.0 mm.
    assert report.max_outside_distance_mm >= 99.0
    assert not report.valid


def test_containment_excursion_is_measured_through_a_notch():
    # Notched room: interior is x in [0, 4000] plus x in [6000, 10000].
    # A straight strut at y = 5000 crosses the 2000 mm wide notch; both of its
    # clipped endpoints sit within ~1 mm of a notch wall while the middle of the
    # notch is 1000 mm away from any allowed area.  A vertex-only or a minimum
    # distance metric would report ~1 mm here.
    notched = [
        (0, 0), (10000, 0), (10000, 10000), (6000, 10000),
        (6000, 2000), (4000, 2000), (4000, 10000), (0, 10000), (0, 0),
    ]
    report = validate_containment([(2000, 5000), (8000, 5000)], notched)
    assert report.outside_segment_count == 1
    assert report.total_outside_length_mm > 1900
    assert report.max_outside_distance_mm >= 900.0
    assert not report.valid


def test_containment_accepts_a_route_inside_the_tolerance_band():
    report = validate_containment([(100, 100), (7000, 100)], RECT)
    assert report.valid
    assert report.total_outside_length_mm == 0
    assert report.max_outside_distance_mm == 0


def test_spiral_candidate_has_explicit_centerward_geometry_and_is_not_silent_fallback():
    route = build_bifilar_spiral((0, 0, 7000, 4000))
    assert route
    assert all(a[0] == b[0] or a[1] == b[1] for a, b in zip(route, route[1:]))
    assert validate_containment(route, RECT).valid


def test_length_policy_is_overrideable_preview_only():
    assert split_required(85, 8)
    assert not split_required(80, 8)


def test_polyline_partition_preserves_continuity_and_total_length():
    route = [(100, 100), (1900, 100), (1900, 1900), (100, 1900)]
    parts = split_polyline_by_length(route, 3)
    assert len(parts) == 3
    assert all(len(part) >= 2 for part in parts)
    assert all(parts[index][-1] == parts[index + 1][0] for index in range(2))
    assert sum(polyline_length(part) for part in parts) == polyline_length(route)
    assert all(validate_containment(part, RECT).valid for part in parts)


def test_circuit_split_requires_distinct_authorized_endpoints():
    route = [(100, 100), (1900, 100), (1900, 1900), (100, 1900)]
    parts = split_polyline_by_length(route, 3)
    blocked = validate_circuit_split(parts)
    assert not blocked["valid"]
    assert "SPLIT_ENDPOINT_HAS_NO_AUTHORIZED_COLLECTOR_PATH" in blocked["diagnostics"]
    allowed = validate_circuit_split(parts, authorized_endpoints=[parts[0][0], parts[0][-1], parts[1][-1], parts[2][-1]])
    assert not allowed["valid"]
    assert "SHARED_INTERNAL_SPLIT_ENDPOINT" in allowed["diagnostics"]


def test_bifilar_gate_measures_center_hairpin_and_interleaved_return():
    reference = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "projects/Test_01/exports/floor_heating_svg/HA-FH-VIS-008-CORE-R3/canonical_geometry.json"
        ).read_text()
    )["complete_route"]["ordered_points"]
    report = validate_bifilar_topology(reference, (0, 0, 3200, 3000), RECT[:1] + [(3200, 0), (3200, 3000), (0, 3000), (0, 0)])
    assert report.valid
    assert report.center_hairpin_present
    assert report.interleaved_return_present


def test_bifilar_spiral_materializes_center_turn_and_interleaved_return():
    route = build_bifilar_spiral((0, 0, 7000, 4000))
    report = validate_bifilar_topology(route, (0, 0, 7000, 4000), RECT)
    assert report.valid
    assert report.center_hairpin_present
    assert report.interleaved_return_present


def test_doorway_lane_reservation_is_deterministic_for_five_circuits():
    reservation = reserve_doorway_lanes(
        ((0.0, 0.0), (1000.0, 0.0)),
        5,
        pipe_outer_diameter_mm=16,
        minimum_free_pipe_clearance_mm=16,
        edge_clearance_mm=50,
    )
    assert reservation.valid
    assert reservation.required_lane_count == 10
    assert len(reservation.lanes) == 10
    assert [(lane.circuit_index, lane.flow_role) for lane in reservation.lanes] == [
        (1, "SUPPLY"), (1, "RETURN"), (2, "SUPPLY"), (2, "RETURN"),
        (3, "SUPPLY"), (3, "RETURN"), (4, "SUPPLY"), (4, "RETURN"),
        (5, "SUPPLY"), (5, "RETURN"),
    ]
    centers = [lane.point_mm[0] for lane in reservation.lanes]
    assert all(round(b - a, 6) == 32.0 for a, b in zip(centers, centers[1:]))


def test_doorway_lane_reservation_rejects_a_door_that_cannot_hold_all_pipes():
    reservation = reserve_doorway_lanes(((0.0, 0.0), (200.0, 0.0)), 5)
    assert not reservation.valid
    assert reservation.lanes == ()
    assert reservation.diagnostics == ("DOORWAY_CAPACITY_INSUFFICIENT",)

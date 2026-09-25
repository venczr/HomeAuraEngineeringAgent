from agent.ufh_layout_engine import (
    build_bifilar_spiral,
    build_meander,
    build_polygon_meander,
    validate_bifilar_topology,
)
from agent.ufh_physical_validation import compare_rendered_route, validate_physical_route
from agent.ufh_bend_geometry import build_rounded_centerline, validate_rounded_centerline
from agent.ufh_zone_layout import propose_zoned_meanders


def rect(width, height):
    return [(0, 0), (width, 0), (width, height), (0, height), (0, 0)]


def test_scenario_a_rectangle_true_spiral():
    boundary = rect(3200, 3000)
    route = build_bifilar_spiral((0, 0, 3200, 3000), 200, 200)
    physical = validate_physical_route(route, boundary, spacing_mm=200, minimum_bend_radius_mm=80)
    topology = validate_bifilar_topology(route, (0, 0, 3200, 3000), boundary, spacing_mm=200, minimum_bend_radius_mm=80)
    assert physical.valid and topology.valid
    assert topology.center_hairpin_present and topology.interleaved_return_present


def test_scenario_b_rectangle_continuous_meander():
    boundary = rect(7000, 4000)
    route = build_meander((0, 0, 7000, 4000), 200, 100)
    report = validate_physical_route(route, boundary, spacing_mm=200, minimum_bend_radius_mm=80)
    assert report.valid
    assert report.endpoint_count == 2


def test_scenario_c_l_shape_is_one_ordered_route():
    boundary = [(0, 0), (4000, 0), (4000, 2000), (2000, 2000), (2000, 4000), (0, 4000), (0, 0)]
    route = build_polygon_meander(boundary, 200, 100)
    report = validate_physical_route(route, boundary, spacing_mm=200, minimum_bend_radius_mm=80)
    assert report.valid


def test_scenario_d_internal_obstacle_is_decomposed_without_crossing():
    obstacle = [(2800, 1000), (3200, 1000), (3200, 3000), (2800, 3000), (2800, 1000)]
    left = [(0, 0), (2800, 0), (2800, 4000), (0, 4000), (0, 0)]
    right = [(3200, 0), (6000, 0), (6000, 4000), (3200, 4000), (3200, 0)]
    routes = [build_meander((0, 0, 2800, 4000), 200, 100), build_meander((3200, 0, 6000, 4000), 200, 100)]
    reports = [
        validate_physical_route(route, boundary, obstacles=[obstacle], spacing_mm=200, minimum_bend_radius_mm=80)
        for route, boundary in zip(routes, (left, right))
    ]
    assert all(report.valid for report in reports)


def test_scenario_e_adjacent_rooms_remain_separate_contours():
    first = rect(3000, 3000)
    second = [(3000, 0), (6000, 0), (6000, 3000), (3000, 3000), (3000, 0)]
    first_route = build_meander((0, 0, 3000, 3000), 200, 100)
    second_route = build_meander((3000, 0, 6000, 3000), 200, 100)
    first_report = validate_physical_route(first_route, first, spacing_mm=200, minimum_bend_radius_mm=80)
    second_report = validate_physical_route(second_route, second, spacing_mm=200, minimum_bend_radius_mm=80)
    assert first_report.valid and second_report.valid
    assert first_route[-1] != second_route[0]


def test_scenario_f_two_contours_have_independent_endpoints():
    zones = [
        (rect(3000, 3000), build_meander((0, 0, 3000, 3000), 200, 100)),
        ([(3000, 0), (6000, 0), (6000, 3000), (3000, 3000), (3000, 0)], build_meander((3000, 0, 6000, 3000), 200, 100)),
    ]
    reports = [validate_physical_route(route, boundary, spacing_mm=200, minimum_bend_radius_mm=80) for boundary, route in zones]
    assert all(report.valid and report.endpoint_count == 2 for report in reports)
    assert zones[0][1][0] != zones[1][1][0]


def test_scenario_g_narrow_room_rejects_requested_spiral():
    route = build_bifilar_spiral((0, 0, 1200, 800), 200, 100)
    assert route == []
    report = validate_physical_route(route, rect(1200, 800), spacing_mm=200, minimum_bend_radius_mm=80)
    assert not report.valid


def test_visualization_match_is_exact_centerline_comparison():
    route = build_meander((0, 0, 3000, 3000), 200, 100)
    assert compare_rendered_route(route, route)["VISUALIZATION_VALID"]
    assert not compare_rendered_route(route, route[:-1])["VISUALIZATION_VALID"]


def test_reverse_traversal_is_duplicate_centerline_overlap():
    route = [(0, 0), (1000, 0), (0, 0)]
    report = validate_physical_route(route, rect(2000, 1000), minimum_bend_radius_mm=80)
    assert not report.valid
    assert report.duplicate_centerline_length_mm == 1000
    assert "DUPLICATE_CENTERLINE_OVERLAP" in report.diagnostics


def test_rounded_centerline_models_real_quarter_arcs_and_length():
    route = [(100, 100), (1900, 100), (1900, 1900)]
    report = validate_rounded_centerline(route, rect(2000, 2000), bend_radius_mm=80, pipe_outer_radius_mm=8)
    assert report.valid
    assert report.bend_valid
    assert report.bend_count == 1
    assert report.rounded_length_mm > report.straight_centerline_length_mm - 2 * 80
    assert len(report.rounded_points) > len(route)
    # Two tangent legs of 80 mm are replaced by one exact quarter-circle.
    expected = 3600 - 2 * 80 + 3.141592653589793 * 80 / 2
    assert abs(report.rounded_length_mm - expected) < 1e-6


def test_rounded_centerline_rejects_short_tangent_legs_and_narrow_safe_area():
    short = validate_rounded_centerline([(100, 100), (220, 100), (220, 500)], rect(600, 600), bend_radius_mm=80, pipe_outer_radius_mm=8)
    assert not short.valid
    assert "BEND_TANGENT_CLEARANCE_VIOLATION" in short.diagnostics
    narrow = validate_rounded_centerline([(8, 100), (8, 500), (200, 500)], rect(200, 600), bend_radius_mm=80, pipe_outer_radius_mm=8)
    assert not narrow.valid
    assert "ROUNDED_CENTERLINE_OUTSIDE_PIPE_SAFE_AREA" in narrow.diagnostics


def test_zoning_produces_independent_geometry_candidates_without_claiming_access():
    proposal = propose_zoned_meanders(rect(8000, 4000), target_route_length_mm=50000)
    assert proposal["status"] == "CANDIDATE_UNVERIFIED_ENDPOINT_ACCESS"
    candidate = proposal["recommended"]
    assert candidate["zone_count"] >= 2
    assert candidate["circuit_split_valid"] is False
    assert all(zone["endpoint_access"] == "UNVERIFIED" for zone in candidate["routes"])
    assert all(zone["bend_valid"] for zone in candidate["routes"])

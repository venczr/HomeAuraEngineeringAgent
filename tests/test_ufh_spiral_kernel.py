"""Independent geometric checks for the accessible rectangular spiral."""
import math

import pytest
from shapely.geometry import LineString, Point, box

from agent.ufh_bend_geometry import build_rounded_centerline, validate_rounded_centerline
from agent.ufh_layout_engine import validate_bifilar_topology
from agent.ufh_spiral_kernel import build_accessible_bifilar_spiral


@pytest.mark.parametrize("width,height", [(2000, 4000), (3000, 4000), (3200, 4200), (4100, 7123)])
@pytest.mark.parametrize("mirror", [False, True])
def test_materialized_spiral_is_one_simple_r80_pipe(width, height, mirror):
    room = box(0, 0, width, height)
    points = build_accessible_bifilar_spiral((100, 100, width - 100, height - 100), mirror_x=mirror)
    assert points
    topology = validate_bifilar_topology(points, (0, 0, width, height), list(room.exterior.coords))
    assert topology.valid, topology.diagnostics
    assert topology.connected_component_count == 1
    assert topology.endpoint_count == 2
    assert topology.self_intersection_count == 0
    assert topology.duplicate_centerline_length_mm == 0
    rounded = validate_rounded_centerline(points, list(room.exterior.coords))
    assert rounded.valid, rounded.diagnostics
    assert rounded.minimum_non_adjacent_clearance_mm >= 199.99
    assert LineString(rounded.rounded_points).is_simple
    assert "A 80.000000,80.000000" in rounded.svg_path_data


@pytest.mark.parametrize("mirror", [False, True])
def test_both_terminals_have_unobstructed_outward_rays(mirror):
    points = build_accessible_bifilar_spiral((120, 350, 2920, 4150), mirror_x=mirror)
    first, last = points[0], points[-1]
    assert first[1] == last[1] == 350
    assert abs(first[0] - last[0]) == 200
    assert points[1][0] == first[0] and points[1][1] > first[1]
    assert points[-2][0] == last[0] and points[-2][1] > last[1]
    body = LineString(points)
    for endpoint in (first, last):
        ray = LineString([endpoint, (endpoint[0], endpoint[1] - 1000)])
        assert ray.intersection(body).equals(Point(endpoint))
    extended = [(first[0], first[1] - 1000), *points, (last[0], last[1] - 1000)]
    rounded = build_rounded_centerline(extended)
    assert rounded.valid
    assert LineString(rounded.points).is_simple


def test_central_hairpin_is_materialized_and_return_is_interleaved():
    points = build_accessible_bifilar_spiral((100, 100, 1900, 3900))
    half = len(points) // 2
    before, tip_in, tip_out, after = points[half - 2:half + 2]
    assert math.dist(tip_in, tip_out) == 200
    incoming = (tip_in[0] - before[0], tip_in[1] - before[1])
    outgoing = (after[0] - tip_out[0], after[1] - tip_out[1])
    assert incoming[0] * outgoing[0] + incoming[1] * outgoing[1] < 0
    assert incoming[0] * outgoing[1] - incoming[1] * outgoing[0] == 0
    # Both branches descend through the same sequence of inward turns, with
    # every corresponding supporting line separated by exactly one pitch.
    inward = points[:half]
    outward_reversed = list(reversed(points[half:]))
    for a, b, c, d in zip(inward, inward[1:], outward_reversed, outward_reversed[1:]):
        if a[0] == b[0]:
            assert c[0] == d[0] and abs(a[0] - c[0]) == 200
        else:
            assert c[1] == d[1] and abs(a[1] - c[1]) == 200


def test_supported_core_has_real_physical_coverage():
    room = box(0, 0, 2000, 4000)
    points = build_accessible_bifilar_spiral((100, 100, 1900, 3900))
    rounded = build_rounded_centerline(points)
    line = LineString(rounded.points)
    assert line.buffer(100, quad_segs=16).intersection(room).area / room.area >= 0.97
    distances = [line.distance(Point(x, y)) for x in range(0, 2001, 50) for y in range(0, 4001, 50)]
    assert max(distances) <= 200


@pytest.mark.parametrize("bounds,pitch,radius", [
    ((0, 0, 400, 4000), 200, 80),
    ((0, 0, 2000, 4000), 150, 80),
    ((0, 0, 2000, 4000), 0, 80),
    ((0, 0, 2000, 4000), 200, 0),
    ((0, 0, float("nan"), 4000), 200, 80),
    ((0, 0, 2000, float("inf")), 200, 80),
])
def test_invalid_or_unbuildable_envelope_has_no_silent_fallback(bounds, pitch, radius):
    assert build_accessible_bifilar_spiral(bounds, pitch, minimum_bend_radius_mm=radius) == []


def test_fractional_dimensions_preserve_geometry_without_integer_truncation():
    points = build_accessible_bifilar_spiral((0.25, -350.75, 2921.4, 4812.25))
    assert points[0] == (2921.4, -350.75)
    assert points[-1] == (2721.4, -350.75)
    rounded = build_rounded_centerline(points)
    assert rounded.valid
    assert LineString(rounded.points).is_simple
    assert all(a != b and (a[0] == b[0] or a[1] == b[1]) for a, b in zip(points, points[1:]))

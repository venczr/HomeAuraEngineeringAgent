from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from agent.ufh_polygonal_spiral import (
    build_bifilar_polygonal_spiral,
    build_offset_rings,
    split_concave_into_rectangles,
)


RECT = Polygon([(0, 0), (8000, 0), (8000, 5000), (0, 5000)])
L = Polygon([(0, 0), (10000, 0), (10000, 3000), (4000, 3000), (4000, 10000), (0, 10000)])
NOTCH = Polygon([(0, 0), (10000, 0), (10000, 10000), (7000, 10000), (7000, 3000),
                 (3000, 3000), (3000, 10000), (0, 10000)])
# hourglass: a square pinched to a 400 mm waist; the offset splits into two lobes
HOURGLASS = Polygon([(0, 0), (4000, 0), (4000, 1800), (2200, 1800), (2200, 2200),
                     (4000, 2200), (4000, 4000), (0, 4000), (0, 2200), (1800, 2200),
                     (1800, 1800), (0, 1800)])


def test_offset_rings_rectangle_are_contained_and_ordered() -> None:
    rings, blockers = build_offset_rings(RECT)
    assert not blockers
    assert len(rings) >= 5
    for ring in rings:
        assert RECT.covers(ring.polygon)
    offsets = [r.offset_mm for r in rings]
    assert offsets == sorted(offsets)


def test_offset_rings_l_shape_follow_concave_outline() -> None:
    rings, blockers = build_offset_rings(L)
    assert not blockers
    assert len(rings) >= 5
    for ring in rings:
        assert L.covers(ring.polygon)


def test_offset_rings_split_into_multiple_components() -> None:
    rings, blockers = build_offset_rings(HOURGLASS)
    assert "OFFSET_SPLITS_INTO_MULTIPLE_COMPONENTS" in blockers
    # rings are produced up to the point where the waist pinches off
    assert len(rings) >= 1


def test_bifilar_rectangle_is_a_single_valid_candidate() -> None:
    result = build_bifilar_polygonal_spiral(RECT)
    assert result.status == "GEOMETRY_CANDIDATE"
    assert result.r80_valid is True
    assert result.containment_valid is True
    assert result.topology_valid is True
    assert result.coverage_length_mm > 0
    assert len(result.centerline_mm) >= 4


def test_bifilar_concave_room_is_blocked_not_silently_stitched() -> None:
    for shape in (L, NOTCH):
        result = build_bifilar_polygonal_spiral(shape)
        assert result.status == "BLOCKED"
        assert "CONCAVE_CORNER_OFFSET_FOLD_UNRESOLVED" in result.blocked_reasons
        assert result.centerline_mm == []


def test_bifilar_invalid_room_is_blocked() -> None:
    result = build_bifilar_polygonal_spiral(Polygon())
    assert result.status == "BLOCKED"
    assert "ROOM_POLYGON_INVALID" in result.blocked_reasons


def test_concave_room_splits_into_two_rectangles() -> None:
    zones = split_concave_into_rectangles(L)
    assert zones is not None and len(zones) == 2
    # the two rectangles exactly tile the L-shape
    assert zones[0].area + zones[1].area == pytest.approx(L.area)
    # the shared edge is the concave corner
    assert zones[0].bounds[2] == pytest.approx(4000)
    assert zones[1].bounds[3] == pytest.approx(3000)


def test_each_split_zone_builds_a_valid_bifilar() -> None:
    from agent.ufh_spiral_kernel import build_accessible_bifilar_spiral
    from agent.ufh_bend_geometry import validate_rounded_centerline
    from shapely.geometry import LineString

    zones = split_concave_into_rectangles(L)
    assert zones is not None
    for zone in zones:
        minx, miny, maxx, maxy = zone.bounds
        centerline = build_accessible_bifilar_spiral(
            (minx + 108, miny + 108, maxx - 108, maxy - 108),
            spacing_mm=200, minimum_bend_radius_mm=80,
        )
        assert len(centerline) >= 4
        assert LineString(centerline).is_simple
        report = validate_rounded_centerline(
            centerline, list(zone.exterior.coords), bend_radius_mm=80, pipe_outer_radius_mm=8, samples_per_quarter=4,
        )
        assert report.valid

"""Geometry-only installation checks for hydronic floor-heating routes.

The values are explicit project assumptions, not normative claims.  The
module deliberately does not choose pipe, pump, manifold or hydraulic data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

Point = tuple[int, int]
Polygon = Sequence[Point]


@dataclass(frozen=True)
class InstallationRuleSet:
    wall_clearance_mm: int = 100
    exclusion_clearance_mm: int = 100
    minimum_bend_radius_mm: int = 100
    grid_mm: int = 100


def _expanded_bbox(poly: Polygon, clearance: int) -> tuple[int, int, int, int]:
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs) - clearance, min(ys) - clearance, max(xs) + clearance, max(ys) + clearance


def _segment_hits_bbox(a: Point, b: Point, box: tuple[int, int, int, int]) -> bool:
    left, top, right, bottom = box
    if a[0] == b[0]:
        return left <= a[0] <= right and not (max(min(a[1], b[1]), top) > min(max(a[1], b[1]), bottom))
    if a[1] == b[1]:
        return top <= a[1] <= bottom and not (max(min(a[0], b[0]), left) > min(max(a[0], b[0]), right))
    return True


def validate_installation_geometry(
    points: Sequence[Point],
    room: Polygon,
    exclusions: Sequence[Polygon] = (),
    rules: InstallationRuleSet = InstallationRuleSet(),
    floor_start_index: int = 0,
    floor_end_index: int | None = None,
) -> dict[str, object]:
    """Return deterministic checks for bends, wall clearance and obstacles.

    A rounded physical bend needs enough straight leg on both sides.  For the
    grid-first canonical route this is conservatively represented as each
    adjacent leg being at least the assumed bend radius.  The renderer may
    later round corners, but it must not change the route order or length.
    """
    turns = []
    short_turns = []
    orthogonal = True
    for i, (a, b) in enumerate(zip(points, points[1:])):
        dx, dy = b[0] - a[0], b[1] - a[1]
        if (dx == 0) == (dy == 0):
            orthogonal = False
        if i and i + 1 < len(points) - 1:
            prev, nxt = points[i - 1], points[i + 1]
            leg_a = abs(a[0] - prev[0]) + abs(a[1] - prev[1])
            leg_b = abs(nxt[0] - a[0]) + abs(nxt[1] - a[1])
            if (prev[0] == a[0]) != (a[0] == nxt[0]):
                turns.append({'point': list(a), 'leg_before_mm': leg_a, 'leg_after_mm': leg_b})
                if min(leg_a, leg_b) < rules.minimum_bend_radius_mm:
                    short_turns.append(list(a))
    floor_points = list(points[floor_start_index:floor_end_index]) if floor_end_index is not None else list(points[floor_start_index:])
    room_box = _expanded_bbox(room, -rules.wall_clearance_mm)
    room_clear = all(room_box[0] <= x <= room_box[2] and room_box[1] <= y <= room_box[3] for x, y in floor_points)
    exclusion_boxes = [_expanded_bbox(poly, rules.exclusion_clearance_mm) for poly in exclusions]
    floor_segments = list(zip(floor_points, floor_points[1:]))
    obstacle_clear = not any(_segment_hits_bbox(a, b, box) for box in exclusion_boxes for a, b in floor_segments)
    grid_valid = all(x % rules.grid_mm == 0 and y % rules.grid_mm == 0 for p in points for x, y in [p])
    return {
        'orthogonal': orthogonal,
        'grid_valid': grid_valid,
        'turn_count': len(turns),
        'turns': turns,
        'short_turn_count': len(short_turns),
        'wall_clearance_valid': room_clear,
        'exclusion_clearance_valid': obstacle_clear,
        'result': 'PASS' if orthogonal and grid_valid and not short_turns and room_clear and obstacle_clear else 'REWORK',
        'assumptions': {
            'wall_clearance_mm': rules.wall_clearance_mm,
            'exclusion_clearance_mm': rules.exclusion_clearance_mm,
            'minimum_bend_radius_mm': rules.minimum_bend_radius_mm,
            'grid_mm': rules.grid_mm,
        },
    }

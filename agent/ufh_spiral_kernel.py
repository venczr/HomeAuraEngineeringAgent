"""Rectangular counterflow spirals with two accessible boundary terminals.

The construction offsets one open, inward-winding spine by half a pipe pitch.
Following one offset to its tip, crossing the tip, then following the other
offset backwards gives a single bifilar pipe.  No closed rings are stitched.
"""
from __future__ import annotations

from math import isfinite

Point = tuple[float, float]


def _normal(a: Point, b: Point) -> Point:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = abs(dx) + abs(dy)
    return -dy / length, dx / length


def _offset_spine(spine: list[Point], offset: float) -> list[Point]:
    normals = [_normal(a, b) for a, b in zip(spine, spine[1:])]
    result = [(spine[0][0] + offset * normals[0][0], spine[0][1] + offset * normals[0][1])]
    for index, point in enumerate(spine[1:-1], 1):
        before, after = normals[index - 1], normals[index]
        result.append((point[0] + offset * (before[0] + after[0]), point[1] + offset * (before[1] + after[1])))
    result.append((spine[-1][0] + offset * normals[-1][0], spine[-1][1] + offset * normals[-1][1]))
    return result


def build_accessible_bifilar_spiral(
    bounds: tuple[float, float, float, float],
    spacing_mm: float = 200.0,
    *,
    minimum_bend_radius_mm: float = 80.0,
    mirror_x: bool = False,
) -> list[Point]:
    """Return an orthogonal bifilar centreline with bottom-facing terminals.

    ``bounds`` is the available *centreline* envelope, not the room polygon;
    the caller must first reserve wall/pipe clearances. Both terminals are on
    ``y0``, one pitch apart. Outward rays from them point in ``(0, -1)`` and
    do not meet the body. The first leg points into the rectangle, the last
    leg points out of it. By default terminals lie at ``x1`` and ``x1-pitch``;
    ``mirror_x`` places them at ``x0`` and ``x0+pitch`` instead.

    The final perpendicular segment is an explicit central U-turn between
    the two offset branches, with width exactly one pitch. Every bend must
    still be materialized and independently checked by the caller. Empty
    results mean the envelope cannot contain this construction at the given
    pitch and radius; no alternative morphology is silently substituted.

    This is a candidate constructor, not a coverage certificate: dimensions
    which do not fit the fixed-pitch inner winding can leave a residual core.
    The caller must measure physical coverage against the original polygon
    and reject the candidate when that core exceeds the allowed gap.
    """
    x0, y0, x1, y1 = (float(value) for value in bounds)
    values = (x0, y0, x1, y1, spacing_mm, minimum_bend_radius_mm)
    if not all(isfinite(value) for value in values):
        return []
    if spacing_mm <= 0 or minimum_bend_radius_mm <= 0 or spacing_mm < 2 * minimum_bend_radius_mm:
        return []
    # Build the spine facing east, then rotate its accessible seam south.
    width, height = y1 - y0, x1 - x0
    pitch = float(spacing_mm)
    if min(width, height) < 3 * pitch:
        return []
    left, bottom, right, top = pitch / 2, pitch / 2, width - pitch / 2, height - pitch / 2
    spine: list[Point] = [(width, top)]
    direction = 0
    while True:
        x, y = spine[-1]
        destination = ((left, y), (x, bottom), (right, y), (x, top))[direction]
        length = (x - destination[0], y - destination[1], destination[0] - x, destination[1] - y)[direction]
        # Mitering consumes half a pitch at the final corner. Both resulting
        # legs must retain at least two radii of tangent space.
        if length < pitch / 2 + 2 * minimum_bend_radius_mm:
            break
        if len(spine) > 2 and abs(spine[-1][0] - spine[-2][0]) + abs(spine[-1][1] - spine[-2][1]) < pitch + 2 * minimum_bend_radius_mm:
            break
        spine.append(destination)
        if direction == 0:
            top -= 2 * pitch
        elif direction == 1:
            left += 2 * pitch
        elif direction == 2:
            bottom += 2 * pitch
        else:
            right -= 2 * pitch
        direction = (direction + 1) % 4
    if len(spine) < 5:
        return []
    incoming = _offset_spine(spine, -pitch / 2)
    outgoing = _offset_spine(spine, pitch / 2)
    local = incoming + list(reversed(outgoing))
    result = [(x0 + v, y0 + width - u) for u, v in local]
    if mirror_x:
        result = [(x0 + x1 - x, y) for x, y in result]
    return result


__all__ = ["build_accessible_bifilar_spiral"]

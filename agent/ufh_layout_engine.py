"""Geometry-first UFH layout candidates and independent validation.

This module deliberately contains no thermal or hydraulic claims.  It is used
by the Test_01 preview builder to classify room candidates, validate coverage
containment independently from the canonical engine, and partition long room
loops before building transit metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Iterable, Literal

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union


CONTAINMENT_TOLERANCE_MM = 1.0
MAX_TOTAL_CIRCUIT_LENGTH_M = 90.0
MAX_TOTAL_CIRCUIT_LENGTH_AUTHORITY = "PREVIEW_NON_AUTHORITATIVE_POLICY"


@dataclass(frozen=True)
class ContainmentReport:
    max_outside_distance_mm: float
    total_outside_length_mm: float
    outside_segment_count: int
    valid: bool


@dataclass(frozen=True)
class StrategyCandidate:
    strategy: Literal["BIFILAR_SPIRAL", "MEANDER", "HYBRID_PERIMETER_SPIRAL"]
    feasible: bool
    reason: str
    bend_count: int
    spacing_error_mm: float
    containment: ContainmentReport


def polyline_length(points: Iterable[tuple[float, float]]) -> float:
    pts = list(points)
    return sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def validate_containment(
    points: Iterable[tuple[float, float]],
    allowed_polygon: Iterable[tuple[float, float]],
    tolerance_mm: float = CONTAINMENT_TOLERANCE_MM,
) -> ContainmentReport:
    """Measure line portions outside the allowed polygon without self-certifying.

    The report uses the actual line and polygon objects and exposes outside
    length/count separately, so a caller cannot turn a Boolean into a fake
    coverage claim.
    """
    poly = Polygon(list(allowed_polygon))
    line = LineString(list(points))
    if line.is_empty or not poly.is_valid:
        return ContainmentReport(0.0, 0.0, 0, False)
    outside = line.difference(poly.buffer(tolerance_mm))
    if outside.is_empty:
        return ContainmentReport(0.0, 0.0, 0, True)
    pieces = []
    if outside.geom_type == "LineString":
        pieces = [outside]
    elif outside.geom_type == "MultiLineString":
        pieces = list(outside.geoms)
    length = sum(piece.length for piece in pieces)
    max_distance = max((poly.distance(piece) for piece in pieces), default=0.0)
    return ContainmentReport(
        max_outside_distance_mm=float(max_distance),
        total_outside_length_mm=float(length),
        outside_segment_count=len(pieces),
        valid=length <= tolerance_mm and max_distance <= tolerance_mm,
    )


def _is_orthogonal(points: list[tuple[float, float]]) -> bool:
    return all(a[0] == b[0] or a[1] == b[1] for a, b in zip(points, points[1:]))


def build_bifilar_spiral(
    bounds: tuple[int, int, int, int],
    spacing_mm: int = 200,
    wall_offset_mm: int = 100,
) -> list[tuple[int, int]]:
    """Build a continuous orthogonal inward/outward counter-flow candidate.

    The path is emitted as paired lanes: an inward contour sequence followed
    by a center turnaround and an outward sequence offset by one lane.  The
    center turnaround is explicit; callers must still run containment and bend
    checks for non-rectangular domains.
    """
    x0, y0, x1, y1 = bounds
    if x1 - x0 < 2 * wall_offset_mm + 4 * spacing_mm or y1 - y0 < 2 * wall_offset_mm + 4 * spacing_mm:
        return []
    # Construct a simple inward contour chain. The explicit return half and
    # center turnaround are still a promotion gate; this candidate is never
    # reported as a completed spiral until that topology is materialized.
    l, b = x0 + wall_offset_mm, y0 + wall_offset_mm
    r, t = x1 - wall_offset_mm, y1 - wall_offset_mm
    path: list[tuple[int, int]] = [(l, b)]
    while r - l >= 2 * spacing_mm and t - b >= 2 * spacing_mm:
        path.extend([(r, b), (r, t), (l + spacing_mm, t), (l + spacing_mm, b + spacing_mm)])
        l += spacing_mm; b += spacing_mm; r -= spacing_mm; t -= spacing_mm
        if r - l >= 2 * spacing_mm and t - b >= 2 * spacing_mm:
            path.append((r, b))
    return path


def build_meander(bounds: tuple[int, int, int, int], spacing_mm: int = 200, wall_offset_mm: int = 100) -> list[tuple[int, int]]:
    """Build one continuous orthogonal serpentine loop for a rectangular zone."""
    x0, y0, x1, y1 = bounds
    left, right = x0 + wall_offset_mm, x1 - wall_offset_mm
    bottom, top = y0 + wall_offset_mm, y1 - wall_offset_mm
    if right - left < 2 * wall_offset_mm or top - bottom < spacing_mm:
        return []
    ys = list(range(bottom, top + 1, spacing_mm))
    if ys[-1] != top:
        ys.append(top)
    points = []
    for index, y in enumerate(ys):
        row = [(left, y), (right, y)] if index % 2 == 0 else [(right, y), (left, y)]
        if points:
            points.append((row[0][0], points[-1][1]))
        points.extend(row)
    return points


def classify_strategies(
    points: list[tuple[int, int]],
    room_polygon: Iterable[tuple[int, int]],
    route_length_mm: float,
    spacing_mm: int = 200,
    wall_offset_mm: int = 100,
) -> tuple[StrategyCandidate, ...]:
    poly = Polygon(list(room_polygon))
    bounds = tuple(int(v) for v in poly.bounds)
    spiral = build_bifilar_spiral(bounds, spacing_mm, wall_offset_mm)
    spiral_report = validate_containment(spiral, room_polygon) if spiral else ContainmentReport(0, 0, 0, False)
    rectangular = poly.area / max((bounds[2] - bounds[0]) * (bounds[3] - bounds[1]), 1) > 0.965
    # The current candidate builder emits only the inward contour half. Until
    # a materialized center turnaround and interleaved outward return are
    # present, it is intentionally rejected as a completed bifilar loop.
    spiral_ok = False
    meander_report = validate_containment(points, room_polygon)
    candidates = [
        StrategyCandidate("BIFILAR_SPIRAL", spiral_ok, "regular orthogonal envelope" if spiral_ok else "offset contour or containment gate failed", max(0, len(spiral) - 1), 0.0, spiral_report),
        StrategyCandidate("MEANDER", meander_report.valid, "dense sweep candidate" if meander_report.valid else "containment gate failed", max(0, len(points) - 2), 0.0, meander_report),
    ]
    if rectangular and spiral_ok:
        candidates.append(StrategyCandidate("HYBRID_PERIMETER_SPIRAL", True, "geometry candidate; no thermal cold-zone claim", candidates[0].bend_count + 6, 0.0, spiral_report))
    return tuple(candidates)


def choose_strategy(candidates: Iterable[StrategyCandidate], route_length_mm: float) -> tuple[str, str]:
    feasible = [c for c in candidates if c.feasible]
    if not feasible:
        return "UNRESOLVED", "no candidate passed independent containment"
    # Prefer a true spiral for regular rooms; use meander for narrow/irregular
    # rooms.  Length is a tie-breaker, never a thermal score.
    for name in ("BIFILAR_SPIRAL", "HYBRID_PERIMETER_SPIRAL", "MEANDER"):
        for candidate in feasible:
            if candidate.strategy == name:
                return name, candidate.reason
    return feasible[0].strategy, feasible[0].reason


def split_required(route_length_m: float, transit_allowance_m: float = 8.0) -> bool:
    return route_length_m + transit_allowance_m > MAX_TOTAL_CIRCUIT_LENGTH_M

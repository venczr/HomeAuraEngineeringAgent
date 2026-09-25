"""Polygonal spiral from Shapely offset rings.

Two pieces:

* :func:`build_offset_rings` turns a room polygon into nested inward-offset
  contours (the geometric blanks for a polygonal spiral) and reports, rather
  than silently repairing, the cases where the offset splits into several
  components (``MultiPolygon``) or collapses.
* :func:`build_bifilar_polygonal_spiral` produces ONE continuous bifilar
  centreline.  For an orthogonal rectangular room it reuses the proven
  ``ufh_spiral_kernel.build_accessible_bifilar_spiral`` constructor and
  validates it through ``ufh_bend_geometry``.  For concave / L-shaped / notched
  rooms the ring-to-ring bifilar stitching is still an open question and the
  function returns an explicit ``BLOCKED`` reason instead of emitting several
  unconnected polylines as if they were one pipe.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from shapely.geometry import LineString, Polygon

from agent.ufh_bend_geometry import validate_rounded_centerline
from agent.ufh_spiral_kernel import build_accessible_bifilar_spiral


DEFAULT_WALL_OFFSET_MM = 100.0
DEFAULT_PITCH_MM = 200.0
DEFAULT_MIN_BEND_RADIUS_MM = 80.0
DEFAULT_PIPE_OUTER_RADIUS_MM = 8.0


@dataclass(frozen=True)
class OffsetRingInfo:
    offset_mm: float
    polygon: Polygon
    ring_points: tuple[tuple[float, float], ...]


@dataclass
class PolygonalSpiralResult:
    status: str
    centerline_mm: list[tuple[float, float]]
    rings: list[OffsetRingInfo] = field(default_factory=list)
    coverage_length_mm: float = 0.0
    blocked_reasons: list[str] = field(default_factory=list)
    r80_valid: bool | None = None
    containment_valid: bool | None = None
    topology_valid: bool | None = None
    diagnostics: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "centerline_mm": [[round(x, 2), round(y, 2)] for x, y in self.centerline_mm],
            "coverage_length_mm": round(self.coverage_length_mm, 3),
            "ring_count": len(self.rings),
            "blocked_reasons": list(self.blocked_reasons),
            "r80_valid": self.r80_valid,
            "containment_valid": self.containment_valid,
            "topology_valid": self.topology_valid,
            "diagnostics": list(self.diagnostics),
        }


def _is_orthogonal(points: list[tuple[float, float]], tol_deg: float = 0.5) -> bool:
    n = len(points)
    if n < 4:
        return False
    for i in range(n):
        a, b, c = points[i - 1], points[i], points[(i + 1) % n]
        ab = (b[0] - a[0], b[1] - a[1])
        bc = (c[0] - b[0], c[1] - b[1])
        lab = math.hypot(*ab)
        lbc = math.hypot(*bc)
        if lab < 1e-6 or lbc < 1e-6:
            continue
        dot = (ab[0] * bc[0] + ab[1] * bc[1]) / (lab * lbc)
        if abs(dot) > math.sin(math.radians(tol_deg)):
            return False
    return True


def _is_axis_aligned_rectangle(polygon: Polygon, tol: float = 1.0) -> bool:
    exterior = list(polygon.exterior.coords)[:-1]
    if len(exterior) != 4 or not _is_orthogonal(exterior):
        return False
    minx, miny, maxx, maxy = polygon.bounds
    bbox = Polygon([(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)])
    return abs(polygon.area - bbox.area) < tol and abs(polygon.length - bbox.length) < tol


def _is_convex(polygon: Polygon) -> bool:
    """True when every interior turn is convex (no concave corner)."""
    exterior = [(x, y) for x, y in polygon.exterior.coords[:-1]]
    n = len(exterior)
    sign = None
    for i in range(n):
        a, b, c = exterior[i - 1], exterior[i], exterior[(i + 1) % n]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cross) < 1e-9:
            continue
        s = 1 if cross > 0 else -1
        if sign is None:
            sign = s
        elif s != sign:
            return False
    return True


def _reflex_vertex(polygon: Polygon) -> tuple[float, float] | None:
    """Return the single reflex vertex of an orthogonal concave polygon, if any."""
    exterior = [(x, y) for x, y in polygon.exterior.coords[:-1]]
    n = len(exterior)
    reflex = None
    for i in range(n):
        a, b, c = exterior[i - 1], exterior[i], exterior[(i + 1) % n]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if cross < -1e-9:  # clockwise turn => reflex (interior 270 deg) for CCW input
            if reflex is not None:
                return None  # more than one reflex vertex: not a simple L
            reflex = b
    return reflex


def split_concave_into_rectangles(polygon: Polygon) -> list[Polygon] | None:
    """Split a single-reflex orthogonal concave polygon into two rectangles.

    The reflex vertex is the concave corner; the two rectangles are the
    vertical and horizontal arms of the L-shape.  Returns ``None`` when the
    polygon has no reflex vertex or is not a simple L-shape.
    """
    reflex = _reflex_vertex(polygon)
    if reflex is None:
        return None
    minx, miny, maxx, maxy = polygon.bounds
    rx, ry = reflex
    vertical = Polygon([(minx, miny), (rx, miny), (rx, maxy), (minx, maxy)])
    horizontal = Polygon([(rx, miny), (maxx, miny), (maxx, ry), (rx, ry)])
    return [vertical, horizontal]


def build_offset_rings(
    polygon: Polygon,
    *,
    wall_offset_mm: float = DEFAULT_WALL_OFFSET_MM,
    pitch_mm: float = DEFAULT_PITCH_MM,
    max_rings: int = 200,
) -> tuple[list[OffsetRingInfo], list[str]]:
    """Return the inward offset rings of ``polygon`` and any blockers."""
    blockers: list[str] = []
    rings: list[OffsetRingInfo] = []
    offset = wall_offset_mm
    for _ in range(max_rings):
        ring = polygon.buffer(-offset, join_style=2, quad_segs=1)
        if ring.is_empty:
            break
        if ring.geom_type == "MultiPolygon":
            blockers.append("OFFSET_SPLITS_INTO_MULTIPLE_COMPONENTS")
            break
        if not isinstance(ring, Polygon) or not ring.is_valid:
            blockers.append("OFFSET_RING_INVALID")
            break
        pts = tuple((round(x, 3), round(y, 3)) for x, y in ring.exterior.coords[:-1])
        rings.append(OffsetRingInfo(offset_mm=round(offset, 3), polygon=ring, ring_points=pts))
        offset += pitch_mm
    if not rings:
        blockers.append("NO_OFFSET_RING_FITS_WALL_OFFSET")
    return rings, blockers


def _length(points: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1])
        for i in range(1, len(points))
    )


def build_bifilar_polygonal_spiral(
    polygon: Polygon,
    *,
    wall_offset_mm: float = DEFAULT_WALL_OFFSET_MM,
    pitch_mm: float = DEFAULT_PITCH_MM,
    minimum_bend_radius_mm: float = DEFAULT_MIN_BEND_RADIUS_MM,
    pipe_outer_radius_mm: float = DEFAULT_PIPE_OUTER_RADIUS_MM,
) -> PolygonalSpiralResult:
    blockers: list[str] = []
    if polygon.is_empty or not polygon.is_valid:
        return PolygonalSpiralResult("BLOCKED", [], [], 0.0, ["ROOM_POLYGON_INVALID"])
    exterior = [(x, y) for x, y in polygon.exterior.coords[:-1]]
    if not _is_orthogonal(exterior):
        return PolygonalSpiralResult("BLOCKED", [], [], 0.0, ["NON_ORTHOGONAL_ROOM_NOT_SUPPORTED"])

    rings, ring_blockers = build_offset_rings(polygon, wall_offset_mm=wall_offset_mm, pitch_mm=pitch_mm)
    blockers.extend(ring_blockers)
    if not rings:
        return PolygonalSpiralResult("BLOCKED", [], [], 0.0, blockers)

    if not _is_axis_aligned_rectangle(polygon):
        if not _is_convex(polygon):
            blockers.append("CONCAVE_CORNER_OFFSET_FOLD_UNRESOLVED")
        else:
            blockers.append("BIFILAR_STITCHING_UNRESOLVED_FOR_NON_RECTANGULAR_ROOM")
        return PolygonalSpiralResult("BLOCKED", [], rings, 0.0, blockers)

    minx, miny, maxx, maxy = polygon.bounds
    centerline = [
        (float(x), float(y))
        for x, y in build_accessible_bifilar_spiral(
            (minx + wall_offset_mm, miny + wall_offset_mm, maxx - wall_offset_mm, maxy - wall_offset_mm),
            spacing_mm=pitch_mm,
            minimum_bend_radius_mm=minimum_bend_radius_mm,
        )
    ]
    if len(centerline) < 4:
        return PolygonalSpiralResult("BLOCKED", [], rings, 0.0, ["BIFILAR_SPIRAL_EMPTY"])

    line = LineString(centerline)
    r80 = validate_rounded_centerline(
        centerline, list(polygon.exterior.coords),
        bend_radius_mm=minimum_bend_radius_mm, pipe_outer_radius_mm=pipe_outer_radius_mm,
        samples_per_quarter=4,
    )
    result = PolygonalSpiralResult(
        status="GEOMETRY_CANDIDATE" if r80.valid and line.is_simple else "BLOCKED",
        centerline_mm=centerline,
        rings=rings,
        coverage_length_mm=_length(centerline),
        blocked_reasons=blockers,
        r80_valid=r80.valid,
        containment_valid=r80.geometry_valid,
        topology_valid=r80.topology_valid and line.is_simple,
        diagnostics=list(r80.diagnostics),
    )
    if not line.is_simple:
        result.blocked_reasons.append("CENTERLINE_SELF_INTERSECTS")
    if not r80.valid:
        result.blocked_reasons.append("R80_OR_CONTAINMENT_OR_CLEARANCE_VIOLATION")
    return result


__all__ = [
    "OffsetRingInfo",
    "PolygonalSpiralResult",
    "build_offset_rings",
    "build_bifilar_polygonal_spiral",
    "split_concave_into_rectangles",
]

"""Independent physical route checks.

The route builders return ordered centreline points.  This module treats that
polyline as the source of truth and performs checks without consulting a
strategy label or an SVG.  It deliberately reports hydraulic design as
unevaluated when pipe, flow and manifold inputs are absent.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Iterable

from shapely.geometry import LineString, Polygon


@dataclass(frozen=True)
class PhysicalRouteReport:
    geometry_valid: bool
    topology_valid: bool
    physical_constraints_valid: bool
    hydraulic_valid: str
    visualization_valid: str
    endpoint_count: int
    branch_count: int
    self_intersection_count: int
    route_length_mm: float
    minimum_segment_length_mm: float
    minimum_parallel_clearance_mm: float | None
    diagnostics: tuple[str, ...]
    duplicate_centerline_length_mm: float = 0.0
    bend_valid: bool = False

    @property
    def valid(self) -> bool:
        return (
            self.geometry_valid
            and self.topology_valid
            and self.physical_constraints_valid
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "GEOMETRY_VALID": self.geometry_valid,
            "TOPOLOGY_VALID": self.topology_valid,
            "PHYSICAL_CONSTRAINTS_VALID": self.physical_constraints_valid,
            "HYDRAULIC_VALID": self.hydraulic_valid,
            "VISUALIZATION_VALID": self.visualization_valid,
            "endpoint_count": self.endpoint_count,
            "branch_count": self.branch_count,
            "self_intersection_count": self.self_intersection_count,
            "route_length_mm": round(self.route_length_mm, 3),
            "minimum_segment_length_mm": round(self.minimum_segment_length_mm, 3),
            "minimum_parallel_clearance_mm": (
                None
                if self.minimum_parallel_clearance_mm is None
                else round(self.minimum_parallel_clearance_mm, 3)
            ),
            "duplicate_centerline_length_mm": round(self.duplicate_centerline_length_mm, 3),
            "BEND_VALID": self.bend_valid,
            "valid": self.valid,
            "diagnostics": list(self.diagnostics),
        }


def _length(a: tuple[int, int], b: tuple[int, int]) -> float:
    return hypot(b[0] - a[0], b[1] - a[1])


def _parallel_clearance(
    points: list[tuple[int, int]],
    *,
    minimum_required_mm: int,
) -> float | None:
    segments = list(zip(points, points[1:]))
    clearances: list[float] = []
    for index, (first_start, first_end) in enumerate(segments):
        for other_start, other_end in segments[index + 2 :]:
            first_horizontal = first_start[1] == first_end[1]
            other_horizontal = other_start[1] == other_end[1]
            if first_horizontal != other_horizontal:
                continue
            if first_horizontal:
                overlap = min(max(first_start[0], first_end[0]), max(other_start[0], other_end[0])) - max(
                    min(first_start[0], first_end[0]), min(other_start[0], other_end[0])
                )
                if overlap <= 0:
                    continue
                clearances.append(abs(first_start[1] - other_start[1]))
            else:
                overlap = min(max(first_start[1], first_end[1]), max(other_start[1], other_end[1])) - max(
                    min(first_start[1], first_end[1]), min(other_start[1], other_end[1])
                )
                if overlap <= 0:
                    continue
                clearances.append(abs(first_start[0] - other_start[0]))
    return min(clearances, default=None)


def _duplicate_segment_overlap_length(points: list[tuple[int, int]]) -> float:
    segments = list(zip(points, points[1:]))
    overlap = 0.0
    for index, (a, b) in enumerate(segments):
        if a == b:
            continue
        for c, d in segments[index + 1:]:
            if c == d:
                continue
            if a[1] == b[1] == c[1] == d[1]:
                left = max(min(a[0], b[0]), min(c[0], d[0]))
                right = min(max(a[0], b[0]), max(c[0], d[0]))
            elif a[0] == b[0] == c[0] == d[0]:
                left = max(min(a[1], b[1]), min(c[1], d[1]))
                right = min(max(a[1], b[1]), max(c[1], d[1]))
            else:
                continue
            if right > left:
                overlap += right - left
    return overlap


def validate_physical_route(
    points: Iterable[tuple[int, int]],
    allowed_polygon: Iterable[tuple[int, int]],
    *,
    obstacles: Iterable[Iterable[tuple[int, int]]] = (),
    spacing_mm: int | None = None,
    minimum_bend_radius_mm: int = 80,
    maximum_length_mm: int | None = None,
    expected_start: tuple[int, int] | None = None,
    expected_end: tuple[int, int] | None = None,
) -> PhysicalRouteReport:
    raw = [(int(x), int(y)) for x, y in points]
    polygon = Polygon(list(allowed_polygon))
    diagnostics: list[str] = []
    if len(raw) < 2 or not polygon.is_valid or polygon.is_empty:
        diagnostics.append("INVALID_ROUTE_OR_BOUNDARY")
    segments = list(zip(raw, raw[1:]))
    lengths = [_length(a, b) for a, b in segments if a != b]
    if any(a == b for a, b in segments):
        diagnostics.append("ZERO_LENGTH_SEGMENT")
    if any(a[0] != b[0] and a[1] != b[1] for a, b in segments):
        diagnostics.append("NON_ORTHOGONAL_SEGMENT")

    neighbours: dict[tuple[int, int], set[tuple[int, int]]] = {}
    for first, second in segments:
        if first == second:
            continue
        neighbours.setdefault(first, set()).add(second)
        neighbours.setdefault(second, set()).add(first)
    endpoint_count = sum(len(value) == 1 for value in neighbours.values())
    branch_count = sum(len(value) > 2 for value in neighbours.values())
    if endpoint_count != 2:
        diagnostics.append("ENDPOINT_COUNT_NOT_TWO")
    if branch_count:
        diagnostics.append("BRANCHING_NODE")
    if expected_start is not None and raw and raw[0] != expected_start:
        diagnostics.append("START_ENDPOINT_MISMATCH")
    if expected_end is not None and raw and raw[-1] != expected_end:
        diagnostics.append("END_ENDPOINT_MISMATCH")

    line = LineString(raw) if len(raw) >= 2 else LineString()
    self_intersection_count = 0
    for index, first in enumerate(segments):
        first_line = LineString(first)
        for other in segments[index + 2 :]:
            if first_line.intersects(LineString(other)):
                self_intersection_count += 1
    if self_intersection_count:
        diagnostics.append("SELF_INTERSECTION_OR_OVERLAP")
    duplicate_overlap = _duplicate_segment_overlap_length(raw) if raw else 0.0
    if duplicate_overlap:
        diagnostics.append("DUPLICATE_CENTERLINE_OVERLAP")

    outside_length = 0.0
    if not line.is_empty and polygon.is_valid:
        outside_length = line.difference(polygon.buffer(1.0)).length
    if outside_length > 1.0:
        diagnostics.append("OUTSIDE_HEATABLE_AREA")
    obstacle_hit = False
    for obstacle in obstacles:
        obstacle_polygon = Polygon(list(obstacle))
        if not obstacle_polygon.is_valid:
            diagnostics.append("INVALID_OBSTACLE")
            obstacle_hit = True
        elif line.intersects(obstacle_polygon.buffer(1.0)):
            obstacle_hit = True
    if obstacle_hit:
        diagnostics.append("OBSTACLE_INTERSECTION")

    short_turn = False
    for index in range(1, len(raw) - 1):
        before = _length(raw[index - 1], raw[index])
        after = _length(raw[index], raw[index + 1])
        if raw[index - 1] == raw[index] or raw[index] == raw[index + 1]:
            continue
        if (raw[index - 1][0] == raw[index][0]) == (raw[index][0] == raw[index + 1][0]):
            continue
        if min(before, after) < minimum_bend_radius_mm:
            short_turn = True
    if short_turn:
        diagnostics.append("MINIMUM_BEND_RADIUS_VIOLATION")
    # A bend is represented by its centerline polyline, but the tube must have
    # room for a radius-r fillet at every corner.  Both tangent legs must reach
    # the tangent points; this is a geometric bend gate, separate from route
    # length and from the spacing gate.
    bend_valid = True
    for index in range(1, len(raw) - 1):
        before, corner, after = raw[index - 1], raw[index], raw[index + 1]
        incoming = (corner[0] - before[0], corner[1] - before[1])
        outgoing = (after[0] - corner[0], after[1] - corner[1])
        if incoming[0] == 0 and incoming[1] == 0 or outgoing[0] == 0 and outgoing[1] == 0:
            continue
        if incoming[0] != 0 and outgoing[0] != 0 or incoming[1] != 0 and outgoing[1] != 0:
            continue
        if min(_length(before, corner), _length(corner, after)) < 2 * minimum_bend_radius_mm:
            bend_valid = False
    if not bend_valid:
        diagnostics.append("BEND_TANGENT_CLEARANCE_VIOLATION")

    clearance = _parallel_clearance(raw, minimum_required_mm=spacing_mm or 0) if raw else None
    if spacing_mm is not None and clearance is not None and clearance < spacing_mm:
        # A final strip is often shortened by the exact room boundary.  Keep
        # this visible, but only fail the physical gate when the reduction is
        # large enough to threaten installation clearance.
        tolerance_floor = minimum_bend_radius_mm
        diagnostics.append(
            "FIELD_SPACING_BELOW_REQUEST"
            if clearance < tolerance_floor
            else "BOUNDARY_TERMINAL_SPACING_ADJUSTED"
        )
    route_length = sum(lengths)
    if maximum_length_mm is not None and route_length > maximum_length_mm:
        diagnostics.append("MAXIMUM_CIRCUIT_LENGTH_EXCEEDED")

    geometry_valid = bool(polygon.is_valid and not polygon.is_empty and outside_length <= 1.0 and not obstacle_hit)
    topology_valid = bool(len(raw) >= 2 and endpoint_count == 2 and branch_count == 0 and not self_intersection_count and all(a != b for a, b in segments))
    physical_valid = bool(
        not any(code in diagnostics for code in (
            "NON_ORTHOGONAL_SEGMENT", "MINIMUM_BEND_RADIUS_VIOLATION",
            "FIELD_SPACING_BELOW_REQUEST", "MAXIMUM_CIRCUIT_LENGTH_EXCEEDED",
            "DUPLICATE_CENTERLINE_OVERLAP", "BEND_TANGENT_CLEARANCE_VIOLATION",
        ))
    )
    return PhysicalRouteReport(
        geometry_valid=geometry_valid,
        topology_valid=topology_valid,
        physical_constraints_valid=physical_valid,
        hydraulic_valid="NOT_EVALUATED_MISSING_PIPE_FLOW_AND_MANIFOLD_INPUTS",
        visualization_valid="NOT_EVALUATED_UNTIL_RENDER_MATCH_CHECK",
        endpoint_count=endpoint_count,
        branch_count=branch_count,
        self_intersection_count=self_intersection_count,
        route_length_mm=route_length,
        minimum_segment_length_mm=min(lengths, default=0.0),
        minimum_parallel_clearance_mm=clearance,
        diagnostics=tuple(dict.fromkeys(diagnostics)),
        duplicate_centerline_length_mm=duplicate_overlap,
        bend_valid=bend_valid,
    )


def compare_rendered_route(
    route: Iterable[tuple[int, int]],
    rendered_route: Iterable[tuple[int, int]],
    *,
    tolerance_mm: int = 1,
    allow_collinear_vertices: bool = False,
) -> dict[str, object]:
    source = [(int(x), int(y)) for x, y in route]
    rendered = [(int(x), int(y)) for x, y in rendered_route]
    if allow_collinear_vertices:
        def compress(points):
            result=[]
            for point in points:
                if result and point == result[-1]:
                    continue
                result.append(point)
                while len(result) >= 3:
                    a,b,c=result[-3:]
                    if (b[0]-a[0])*(c[1]-b[1]) == (b[1]-a[1])*(c[0]-b[0]):
                        result.pop(-2)
                    else:
                        break
            return result
        source = compress(source)
        rendered = compress(rendered)
    equal = len(source) == len(rendered) and all(
        _length(a, b) <= tolerance_mm for a, b in zip(source, rendered)
    )
    return {
        "VISUALIZATION_VALID": equal,
        "source_point_count": len(source),
        "rendered_point_count": len(rendered),
        "diagnostics": [] if equal else ["RENDERED_ROUTE_DOES_NOT_MATCH_CALCULATED_CENTERLINE"],
    }


__all__ = ["PhysicalRouteReport", "validate_physical_route", "compare_rendered_route"]

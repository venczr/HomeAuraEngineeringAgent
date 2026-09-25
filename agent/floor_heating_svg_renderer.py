"""Deterministic SVG inspection renderer for accepted floor-heating geometry.

The renderer is deliberately read-only with respect to engineering geometry.
Every pipe path is serialized directly from one accepted CircuitRoute.polyline.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import xml.etree.ElementTree as ET

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from agent.floor_heating_coverage import (
    FloorHeatingCoveragePlan,
    FloorHeatingCoverageRequest,
)
from agent.floor_heating_models import CircuitRoute, FloorHeatingPoint


SVG_NS = "http://www.w3.org/2000/svg"
GENERATION_VERSION = "HA-FH-VIS-001/1.0"
ROUTE_COLOURS = ("#087e8b", "#d1495b", "#6a4c93")
Point = tuple[int, int]
Segment = tuple[Point, Point]

ET.register_namespace("", SVG_NS)


@dataclass(frozen=True)
class FloorHeatingSvgBundle:
    verdict: Literal[
        "TWO_D_SVG_LAYOUT_READY_FOR_VISUAL_REVIEW",
        "REWORK_ROUTING_GEOMETRY",
        "REWORK_COVERAGE_PLAN",
        "REWORK_SVG_RENDERER",
    ]
    svg: str
    html: str
    report: dict[str, Any]
    geometry: dict[str, Any]
    geometry_digest: str


def _tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _points(route: CircuitRoute) -> list[Point]:
    return [(point.x_mm, point.y_mm) for point in route.polyline]


def _segments(points: list[Point]) -> list[Segment]:
    return list(zip(points, points[1:]))


def _path_data(points: list[Point]) -> str:
    first, *rest = points
    return " ".join(
        [f"M {first[0]} {first[1]}"]
        + [f"L {point[0]} {point[1]}" for point in rest]
    )


def _geometry_length(points: list[Point]) -> float:
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in _segments(points))


def _cross(a: Point, b: Point, c: Point) -> int:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: Point, b: Point, point: Point) -> bool:
    return (
        _cross(a, b, point) == 0
        and min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= point[1] <= max(a[1], b[1])
    )


def _intersects(first: Segment, second: Segment) -> bool:
    a, b = first
    c, d = second
    values_1 = (_cross(a, b, c), _cross(a, b, d))
    values_2 = (_cross(c, d, a), _cross(c, d, b))
    if values_1[0] == values_1[1] == values_2[0] == values_2[1] == 0:
        return not (
            max(a[0], b[0]) < min(c[0], d[0])
            or max(c[0], d[0]) < min(a[0], b[0])
            or max(a[1], b[1]) < min(c[1], d[1])
            or max(c[1], d[1]) < min(a[1], b[1])
        )
    return (
        (values_1[0] == 0 or values_1[1] == 0 or (values_1[0] < 0) != (values_1[1] < 0))
        and (values_2[0] == 0 or values_2[1] == 0 or (values_2[0] < 0) != (values_2[1] < 0))
    )


def _self_intersection_count(points: list[Point]) -> int:
    values = _segments(points)
    count = 0
    for index, first in enumerate(values):
        for other_index in range(index + 1, len(values)):
            if other_index == index + 1:
                continue
            if _intersects(first, values[other_index]):
                count += 1
    return count


def _inter_route_crossings(routes: list[CircuitRoute]) -> list[dict[str, Any]]:
    crossings: list[dict[str, Any]] = []
    for route_index, route in enumerate(routes):
        route_segments = _segments(_points(route))
        for other_index in range(route_index + 1, len(routes)):
            other = routes[other_index]
            other_segments = _segments(_points(other))
            for segment_index, segment in enumerate(route_segments):
                for other_segment_index, other_segment in enumerate(other_segments):
                    if _intersects(segment, other_segment):
                        crossings.append({
                            "first_route_id": route.id,
                            "first_segment_index": segment_index,
                            "second_route_id": other.id,
                            "second_segment_index": other_segment_index,
                        })
    return crossings


def _branch_count(points: list[Point]) -> int:
    neighbours: dict[Point, set[Point]] = {}
    for first, second in _segments(points):
        neighbours.setdefault(first, set()).add(second)
        neighbours.setdefault(second, set()).add(first)
    return sum(len(values) > 2 for values in neighbours.values())


def _point_inside(point: Point, polygon: list[Point]) -> bool:
    for first, second in _segments(polygon):
        if _on_segment(first, second, point):
            return True
    inside = False
    x, y = point
    for first, second in _segments(polygon):
        if (first[1] > y) != (second[1] > y):
            cross_x = (second[0] - first[0]) * (y - first[1]) / (second[1] - first[1]) + first[0]
            if x < cross_x:
                inside = not inside
    return inside


def _segment_hits_polygon(segment: Segment, polygon: list[Point]) -> bool:
    if _point_inside(segment[0], polygon) or _point_inside(segment[1], polygon):
        return True
    return any(_intersects(segment, edge) for edge in _segments(polygon))


def _point_segment_distance(point: Point, segment: Segment) -> float:
    px, py = point
    (ax, ay), (bx, by) = segment
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    fraction = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + fraction * dx), py - (ay + fraction * dy))


def _segment_distance(first: Segment, second: Segment) -> float:
    if _intersects(first, second):
        return 0.0
    return min(
        _point_segment_distance(first[0], second),
        _point_segment_distance(first[1], second),
        _point_segment_distance(second[0], first),
        _point_segment_distance(second[1], first),
    )


def _parallel_spacing(first: Segment, second: Segment) -> float | None:
    dx1, dy1 = first[1][0] - first[0][0], first[1][1] - first[0][1]
    dx2, dy2 = second[1][0] - second[0][0], second[1][1] - second[0][1]
    if dx1 * dy2 != dy1 * dx2:
        return None
    return _point_segment_distance(second[0], first)


def _polygon_points(values: list[FloorHeatingPoint]) -> list[Point]:
    return [(point.x_mm, point.y_mm) for point in values]


def _spacing_evidence(
    request: FloorHeatingCoverageRequest,
    routes: list[CircuitRoute],
) -> dict[str, Any]:
    tolerance = 1.0
    observed: dict[int, list[float]] = {100: [], 200: []}
    transitions = 0
    route_segments: list[Segment] = []
    for route in routes:
        route_points = _points(route)
        route_segments.extend(_segments(route_points))
        classifications: dict[int, int] = {}
        for item in route.outer_wall_segments:
            classifications[item.segment_index] = item.nominal_spacing_mm
        for item in route.field_segments:
            classifications[item.segment_index] = item.nominal_spacing_mm
        for index in range(len(route_points) - 2):
            first = classifications.get(index)
            second = classifications.get(index + 1)
            if first is not None and second is not None and first != second:
                transitions += 1
        for sample in route.spacing_segments:
            first = (
                (sample.first_start.x_mm, sample.first_start.y_mm),
                (sample.first_end.x_mm, sample.first_end.y_mm),
            )
            second = (
                (sample.second_start.x_mm, sample.second_start.y_mm),
                (sample.second_end.x_mm, sample.second_end.y_mm),
            )
            value = _parallel_spacing(first, second)
            if value is not None and sample.spacing_mm in observed:
                observed[sample.spacing_mm].append(value)

    boundary = _polygon_points(request.boundary.points)
    boundary_edges = _segments(boundary)
    wall_clearance = min(
        (_segment_distance(pipe, wall) for pipe in route_segments for wall in boundary_edges),
        default=0.0,
    )
    exclusion_edges = [
        edge
        for exclusion in request.exclusion_zones
        for edge in _segments(_polygon_points(exclusion.points))
    ]
    exclusion_clearance = (
        min(_segment_distance(pipe, edge) for pipe in route_segments for edge in exclusion_edges)
        if exclusion_edges
        else None
    )

    def evidence(spacing: int, requested: int | None) -> dict[str, Any]:
        values = observed[spacing]
        passed = bool(values) and requested == spacing and all(
            abs(value - spacing) <= tolerance for value in values
        )
        return {
            "requested_spacing_mm": requested,
            "observed_minimum_mm": min(values) if values else None,
            "observed_maximum_mm": max(values) if values else None,
            "sample_count": len(values),
            "tolerance_mm": tolerance,
            "status": "PASS" if passed else "FAIL",
        }

    perimeter = evidence(100, request.perimeter_spacing_mm)
    field = evidence(200, request.field_spacing_mm)
    transition = {
        "sample_count": transitions,
        "connected": transitions > 0,
        "status": "PASS" if transitions > 0 else "FAIL",
    }
    clearance = {
        "requested_pipe_to_wall_mm": request.wall_offset_mm,
        "observed_minimum_pipe_to_wall_mm": wall_clearance,
        "wall_status": "PASS" if wall_clearance + tolerance >= request.wall_offset_mm else "FAIL",
        "requested_pipe_to_exclusion_mm": None,
        "observed_minimum_pipe_to_exclusion_mm": exclusion_clearance,
        "exclusion_status": "OBSERVED_ONLY_NO_DECLARED_MINIMUM",
    }
    passed = (
        perimeter["status"] == "PASS"
        and field["status"] == "PASS"
        and transition["status"] == "PASS"
        and clearance["wall_status"] == "PASS"
    )
    return {
        "perimeter": perimeter,
        "field": field,
        "transition": transition,
        "clearance": clearance,
        "status": "PASS" if passed else "FAIL",
    }


def _audit(
    request: FloorHeatingCoverageRequest,
    plan: FloorHeatingCoveragePlan,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    boundary = _polygon_points(request.boundary.points)
    exclusions = [_polygon_points(value.points) for value in request.exclusion_zones]
    route_reports: list[dict[str, Any]] = []
    if request.project_id != plan.project_id or request.room_id != plan.room_id:
        failures.append("SOURCE_IDENTITY_MISMATCH")
    if len(request.exterior_wall_segments) != 1:
        failures.append("EXACTLY_ONE_EXTERIOR_WALL_REQUIRED_BY_ACCEPTED_COVERAGE")
    if request.perimeter_band_depth_mm is None:
        failures.append("MISSING_EXPLICIT_PERIMETER_BAND_DEPTH")
    if request.perimeter_spacing_mm is None:
        failures.append("MISSING_EXPLICIT_PERIMETER_SPACING")
    if request.field_spacing_mm is None:
        failures.append("MISSING_EXPLICIT_FIELD_SPACING")
    if request.installation_grid_spacing_mm is None:
        failures.append("MISSING_EXPLICIT_REFERENCE_GRID_SPACING")
    if plan.status == "impossible":
        failures.append("COVERAGE_PLAN_IMPOSSIBLE")
    if len(plan.circuit_routes) != plan.collector_port_count:
        failures.append("COLLECTOR_PORT_COUNT_MISMATCH")

    for route in plan.circuit_routes:
        points = _points(route)
        source_validation = route.validation
        geometry_length = _geometry_length(points)
        endpoint_count = 2 if len(points) >= 2 and points[0] != points[-1] else 0
        branches = _branch_count(points)
        self_intersections = _self_intersection_count(points)
        room_violations = sum(not _point_inside(point, boundary) for point in points)
        exclusion_intersections = sum(
            _segment_hits_polygon(segment, polygon)
            for segment in _segments(points)
            for polygon in exclusions
        )
        start_matches = points[0] == (
            route.collector_supply_point.x_mm,
            route.collector_supply_point.y_mm,
        )
        end_matches = points[-1] == (
            route.collector_return_point.x_mm,
            route.collector_return_point.y_mm,
        )
        delta = abs(geometry_length - route.length_mm)
        local_failures: list[str] = []
        checks = {
            "one_canonical_route": source_validation.polyline_count == 1,
            "endpoint_count": endpoint_count == 2,
            "start_maps_to_supply": start_matches,
            "end_maps_to_return": end_matches,
            "connected": source_validation.connected,
            "branch_free": branches == 0 and not source_validation.branches,
            "self_intersection_free": self_intersections == 0 and not source_validation.self_intersection,
            "inside_room": room_violations == 0 and source_validation.inside_boundary,
            "exclusion_clear": exclusion_intersections == 0 and source_validation.exclusion_clear,
            "spacing_classified": source_validation.step_valid and bool(route.spacing_segments),
            "length_reconciled": delta <= 1.0,
            "length_in_range": 40_000 <= route.length_mm <= 80_000 and source_validation.length_valid,
            "source_validation": source_validation.valid,
        }
        for name, passed in checks.items():
            if not passed:
                code = f"{route.id}:{name.upper()}"
                failures.append(code)
                local_failures.append(code)
        route_reports.append({
            "route_id": route.id,
            "actual_length_mm": route.length_mm,
            "actual_length_m": route.length_mm / 1000.0,
            "minimum_length_mm": 40_000,
            "maximum_length_mm": 80_000,
            "endpoint_count": endpoint_count,
            "branch_count": branches,
            "self_intersection_count": self_intersections,
            "room_boundary_violation_count": room_violations,
            "exclusion_intersection_count": exclusion_intersections,
            "spacing_status": "PASS" if source_validation.step_valid else "FAIL",
            "collector_connectivity": start_matches and end_matches,
            "calculated_length_mm": source_validation.calculated_length_mm,
            "geometry_length_mm": geometry_length,
            "length_delta_mm": delta,
            "source_validation_valid": source_validation.valid,
            "overall_status": "PASS" if not local_failures else "FAIL",
            "failures": local_failures,
        })

    crossings = _inter_route_crossings(plan.circuit_routes)
    if crossings:
        failures.append("INTER_CIRCUIT_CROSSING")
    spacing = _spacing_evidence(request, plan.circuit_routes)
    if spacing["status"] != "PASS":
        failures.append("SPACING_EVIDENCE_FAILED")
    return ({
        "circuits": route_reports,
        "inter_circuit_crossing_count": len(crossings),
        "inter_circuit_crossings": crossings,
        "spacing_validation": spacing,
        "overall_status": "PASS" if not failures else "FAIL",
    }, failures)


def _bounds(request: FloorHeatingCoverageRequest) -> tuple[int, int, int, int]:
    points = _polygon_points(request.boundary.points)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _display_y(max_y: int, engineering_y: int) -> int:
    return max_y - engineering_y


def _add_text(parent: ET.Element, x: int | float, y: int | float, value: str, **attributes: str) -> ET.Element:
    element = ET.SubElement(parent, _tag("text"), {"x": str(x), "y": str(y), **attributes})
    element.text = value
    return element


def _build_svg(
    request: FloorHeatingCoverageRequest,
    plan: FloorHeatingCoveragePlan,
    geometry_digest: str,
    audit: dict[str, Any],
    failures: list[str],
) -> str:
    min_x, min_y, max_x, max_y = _bounds(request)
    width, height = max_x - min_x, max_y - min_y
    accepted = not failures
    root = ET.Element(_tag("svg"), {
        "id": "FLOOR_HEATING_LAYOUT",
        "version": "1.1",
        "viewBox": f"{min_x - 700} -500 {width + 4700} {height + 1000}",
        "width": "1400",
        "height": "800",
        "data-units": "mm",
        "data-drawing-scale": "1-svg-unit-per-mm",
        "data-generation-version": GENERATION_VERSION,
        "data-geometry-digest": geometry_digest,
        "data-status": "READY_FOR_VISUAL_REVIEW" if accepted else "REWORK",
    })
    ET.SubElement(root, _tag("title")).text = "HomeAura deterministic floor-heating layout"
    ET.SubElement(root, _tag("desc")).text = (
        "Read-only SVG serialization of accepted CircuitRoute polylines in millimetres."
    )
    metadata = ET.SubElement(root, _tag("metadata"), {"id": "ENGINEERING_METADATA"})
    metadata.text = _canonical_json({
        "project_id": request.project_id,
        "room_id": request.room_id,
        "route_ids": [route.id for route in plan.circuit_routes],
        "geometry_digest": geometry_digest,
        "coverage_plan_digest": plan.plan_digest,
        "units": "mm",
        "drawing_scale": "1-svg-unit-per-mm",
        "generation_version": GENERATION_VERSION,
    })
    defs = ET.SubElement(root, _tag("defs"))
    hatch = ET.SubElement(defs, _tag("pattern"), {
        "id": "NO_LAY_HATCH", "width": "80", "height": "80",
        "patternUnits": "userSpaceOnUse", "patternTransform": "rotate(45)",
    })
    ET.SubElement(hatch, _tag("line"), {
        "x1": "0", "y1": "0", "x2": "0", "y2": "80",
        "stroke": "#9b2c2c", "stroke-width": "18",
    })

    transform = f"translate(0 {max_y + min_y}) scale(1 -1)"
    context = ET.SubElement(root, _tag("g"), {"id": "ROOM_CONTEXT"})
    geometry_group = ET.SubElement(context, _tag("g"), {"transform": transform})
    boundary_points = _polygon_points(request.boundary.points)
    ET.SubElement(geometry_group, _tag("path"), {
        "id": "ROOM_BOUNDARY", "d": _path_data(boundary_points),
        "fill": "#ffffff", "stroke": "#20262e", "stroke-width": "30",
        "data-width-mm": str(width), "data-height-mm": str(height),
    })
    offset = request.wall_offset_mm
    if width > 2 * offset and height > 2 * offset:
        ET.SubElement(geometry_group, _tag("rect"), {
            "id": "WALL_OFFSET_BOUNDARY", "x": str(min_x + offset),
            "y": str(min_y + offset), "width": str(width - 2 * offset),
            "height": str(height - 2 * offset), "fill": "none",
            "stroke": "#667085", "stroke-width": "12", "stroke-dasharray": "55 35",
            "data-wall-offset-mm": str(offset),
        })
    for index, wall in enumerate(request.exterior_wall_segments, 1):
        ET.SubElement(geometry_group, _tag("line"), {
            "id": f"EXTERIOR_WALL_{index}",
            "x1": str(wall.start.x_mm), "y1": str(wall.start.y_mm),
            "x2": str(wall.end.x_mm), "y2": str(wall.end.y_mm),
            "stroke": "#e36414", "stroke-width": "70",
            "data-wall-reference": wall.reference,
        })
    dimensions = ET.SubElement(context, _tag("g"), {"id": "ROOM_DIMENSIONS"})
    ET.SubElement(dimensions, _tag("line"), {
        "x1": str(min_x), "y1": "-220", "x2": str(max_x), "y2": "-220",
        "stroke": "#344054", "stroke-width": "10",
    })
    _add_text(dimensions, (min_x + max_x) / 2, -270, f"{width} mm", **{
        "text-anchor": "middle", "font-size": "120", "fill": "#344054",
    })
    ET.SubElement(dimensions, _tag("line"), {
        "x1": str(min_x - 240), "y1": "0", "x2": str(min_x - 240), "y2": str(height),
        "stroke": "#344054", "stroke-width": "10",
    })
    _add_text(dimensions, min_x - 300, height / 2, f"{height} mm", **{
        "text-anchor": "middle", "font-size": "120", "fill": "#344054",
        "transform": f"rotate(-90 {min_x - 300} {height / 2})",
    })

    grid = ET.SubElement(root, _tag("g"), {
        "id": "REFERENCE_GRID", "transform": transform,
        "data-grid-spacing-mm": str(request.installation_grid_spacing_mm or 100),
        "data-engineering-role": "installation-reference-only",
    })
    grid_spacing = request.installation_grid_spacing_mm
    if grid_spacing is not None:
        for x in range(min_x, max_x + 1, grid_spacing):
            ET.SubElement(grid, _tag("line"), {
                "x1": str(x), "y1": str(min_y), "x2": str(x), "y2": str(max_y),
                "stroke": "#d0d5dd", "stroke-width": "6", "opacity": "0.45",
            })
        for y in range(min_y, max_y + 1, grid_spacing):
            ET.SubElement(grid, _tag("line"), {
                "x1": str(min_x), "y1": str(y), "x2": str(max_x), "y2": str(y),
                "stroke": "#d0d5dd", "stroke-width": "6", "opacity": "0.45",
            })

    band_depth = request.perimeter_band_depth_mm or 0
    perimeter = ET.SubElement(root, _tag("g"), {
        "id": "PERIMETER_ZONE", "data-depth-mm": str(band_depth),
        "data-spacing-mm": str(request.perimeter_spacing_mm),
    })
    perimeter_geometry = ET.SubElement(perimeter, _tag("g"), {"transform": transform})
    wall = request.exterior_wall_segments[0] if request.exterior_wall_segments else None
    if wall is None or band_depth <= 0:
        band_rect = (min_x, min_y, 0, 0)
        field_rect = (min_x, min_y, width, height)
    elif wall.start.y_mm == wall.end.y_mm == min_y:
        band_rect = (min_x, min_y, width, band_depth)
        field_rect = (min_x, min_y + band_depth, width, height - band_depth)
    elif wall.start.y_mm == wall.end.y_mm == max_y:
        band_rect = (min_x, max_y - band_depth, width, band_depth)
        field_rect = (min_x, min_y, width, height - band_depth)
    elif wall.start.x_mm == wall.end.x_mm == min_x:
        band_rect = (min_x, min_y, band_depth, height)
        field_rect = (min_x + band_depth, min_y, width - band_depth, height)
    else:
        band_rect = (max_x - band_depth, min_y, band_depth, height)
        field_rect = (min_x, min_y, width - band_depth, height)
    ET.SubElement(perimeter_geometry, _tag("rect"), {
        "id": "PERIMETER_BAND_GEOMETRY", "x": str(band_rect[0]), "y": str(band_rect[1]),
        "width": str(band_rect[2]), "height": str(band_rect[3]),
        "fill": "#fef0c7", "fill-opacity": "0.72", "stroke": "#f79009", "stroke-width": "14",
    })
    _add_text(perimeter, (min_x + max_x) / 2, height - 520, "PERIMETER ZONE — 100 mm", **{
        "text-anchor": "middle", "font-size": "105", "font-weight": "700", "fill": "#7a2e0e",
    })

    field = ET.SubElement(root, _tag("g"), {
        "id": "FIELD_ZONE", "data-spacing-mm": str(request.field_spacing_mm),
    })
    field_geometry = ET.SubElement(field, _tag("g"), {"transform": transform})
    ET.SubElement(field_geometry, _tag("rect"), {
        "id": "FIELD_ZONE_GEOMETRY", "x": str(field_rect[0]), "y": str(field_rect[1]),
        "width": str(max(0, field_rect[2])), "height": str(max(0, field_rect[3])),
        "fill": "#e6f4f1", "fill-opacity": "0.28", "stroke": "#67b7a5", "stroke-width": "10",
    })
    _add_text(field, (min_x + max_x) / 2, 350, "FIELD — 200 mm", **{
        "text-anchor": "middle", "font-size": "105", "font-weight": "700", "fill": "#145c4e",
    })

    exclusion_group = ET.SubElement(root, _tag("g"), {"id": "EXCLUSION_ZONES"})
    exclusion_geometry = ET.SubElement(exclusion_group, _tag("g"), {"transform": transform})
    for index, exclusion in enumerate(request.exclusion_zones, 1):
        points = _polygon_points(exclusion.points)
        xs, ys = [point[0] for point in points], [point[1] for point in points]
        ET.SubElement(exclusion_geometry, _tag("path"), {
            "id": f"EXCLUSION_ZONE_{index}", "d": _path_data(points),
            "fill": "url(#NO_LAY_HATCH)", "stroke": "#9b2c2c", "stroke-width": "22",
            "data-width-mm": str(max(xs) - min(xs)), "data-height-mm": str(max(ys) - min(ys)),
        })
        label_y = _display_y(max_y, (min(ys) + max(ys)) // 2)
        _add_text(exclusion_group, (min(xs) + max(xs)) / 2, label_y - 60, "NO-LAY", **{
            "text-anchor": "middle", "font-size": "80", "font-weight": "700", "fill": "#7a271a",
        })
        _add_text(exclusion_group, (min(xs) + max(xs)) / 2, label_y + 60, f"{max(xs)-min(xs)} × {max(ys)-min(ys)} mm", **{
            "text-anchor": "middle", "font-size": "65", "fill": "#7a271a",
        })

    uncovered_area = max(0, plan.heated_area_mm2 - plan.estimated_coverage_mm2)
    uncovered = ET.SubElement(root, _tag("g"), {
        "id": "UNCOVERED_AREA_OVERLAY",
        "data-geometry-available": "false",
        "data-estimated-uncovered-area-mm2": str(uncovered_area),
        "data-full-coverage-claimed": str(plan.full_coverage_claimed).lower(),
    })
    coverage_geometry = ET.SubElement(uncovered, _tag("g"), {"transform": transform})
    for zone_index, zone in enumerate(plan.zones, 1):
        ET.SubElement(coverage_geometry, _tag("path"), {
            "id": f"COVERAGE_DOMAIN_{zone_index}",
            "d": _path_data(_polygon_points(zone.boundary.points)),
            "fill": "none", "stroke": "#1570ef", "stroke-width": "16",
            "stroke-dasharray": "70 45", "opacity": "0.45",
            "data-zone-id": zone.zone_id,
            "data-estimated-coverage-mm2": str(zone.estimated_coverage_mm2),
            "data-exact-served-region": "false",
        })
    _add_text(uncovered, min_x, height + 310, (
        f"COVERAGE {plan.coverage_ratio * 100:.2f}% · FULL_COVERAGE_CLAIMED={str(plan.full_coverage_claimed).lower()} · "
        "uncovered location unavailable from planner"
    ), **{"font-size": "90", "fill": "#7a2e0e"})

    collector = ET.SubElement(root, _tag("g"), {"id": "COLLECTOR"})
    collector_geometry = ET.SubElement(collector, _tag("g"), {"transform": transform})
    supplies = [(route.collector_supply_point.x_mm, route.collector_supply_point.y_mm) for route in plan.circuit_routes]
    returns = [(route.collector_return_point.x_mm, route.collector_return_point.y_mm) for route in plan.circuit_routes]
    if supplies and returns:
        rail_min = min(point[0] for point in supplies + returns) - 180
        rail_max = max(point[0] for point in supplies + returns) + 180
        supply_y = supplies[0][1]
        return_y = returns[0][1]
        ET.SubElement(collector_geometry, _tag("line"), {
            "id": "COLLECTOR_SUPPLY_RAIL", "x1": str(rail_min), "y1": str(supply_y),
            "x2": str(rail_max), "y2": str(supply_y), "stroke": "#b42318", "stroke-width": "45", "opacity": "0.55",
        })
        ET.SubElement(collector_geometry, _tag("line"), {
            "id": "COLLECTOR_RETURN_RAIL", "x1": str(rail_min), "y1": str(return_y),
            "x2": str(rail_max), "y2": str(return_y), "stroke": "#175cd3", "stroke-width": "45", "opacity": "0.55",
        })
        for index, route in enumerate(plan.circuit_routes, 1):
            for role, point, colour in (
                ("SUPPLY", route.collector_supply_point, "#b42318"),
                ("RETURN", route.collector_return_point, "#175cd3"),
            ):
                ET.SubElement(collector_geometry, _tag("circle"), {
                    "id": f"COLLECTOR_{role}_PORT_{index}", "cx": str(point.x_mm), "cy": str(point.y_mm),
                    "r": "55", "fill": "#ffffff", "stroke": colour, "stroke-width": "28",
                    "data-port-number": str(index), "data-route-id": route.id,
                    "data-x-mm": str(point.x_mm), "data-y-mm": str(point.y_mm),
                })
        _add_text(collector, (rail_min + rail_max) / 2, height + 470, "SHARED COLLECTOR · RED SUPPLY / BLUE RETURN", **{
            "text-anchor": "middle", "font-size": "92", "font-weight": "700", "fill": "#101828",
        })

    routes_group = ET.SubElement(root, _tag("g"), {"id": "CIRCUIT_ROUTES", "transform": transform})
    for index, route in enumerate(plan.circuit_routes, 1):
        points = _points(route)
        colour = ROUTE_COLOURS[(index - 1) % len(ROUTE_COLOURS)] if accepted else "#d92d20"
        ET.SubElement(routes_group, _tag("path"), {
            "id": f"CIRCUIT_ROUTE_{index}", "d": _path_data(points),
            "fill": "none", "stroke": colour, "stroke-width": "32",
            "stroke-linejoin": "round", "stroke-linecap": "round",
            "data-route-id": route.id, "data-point-count": str(len(points)),
            "data-length-mm": str(route.length_mm),
            "data-canonical-order-digest": _digest(points),
        })

    arrows = ET.SubElement(root, _tag("g"), {"id": "FLOW_DIRECTION", "transform": transform})
    roles = ("supply-transit", "inward-path", "after-centre-turn", "outward-return", "return-transit")
    for route_index, route in enumerate(plan.circuit_routes, 1):
        points = _points(route)
        segment_count = len(points) - 1
        indices = (0, segment_count // 4, segment_count // 2, (3 * segment_count) // 4, segment_count - 1)
        colour = ROUTE_COLOURS[(route_index - 1) % len(ROUTE_COLOURS)] if accepted else "#d92d20"
        for arrow_index, (role, segment_index) in enumerate(zip(roles, indices), 1):
            first, second = points[segment_index], points[segment_index + 1]
            x, y = (first[0] + second[0]) / 2, (first[1] + second[1]) / 2
            angle = math.degrees(math.atan2(second[1] - first[1], second[0] - first[0]))
            ET.SubElement(arrows, _tag("polygon"), {
                "id": f"FLOW_ARROW_{route_index}_{arrow_index}",
                "points": "-60,-38 70,0 -60,38", "fill": colour, "stroke": "#ffffff", "stroke-width": "10",
                "transform": f"translate({x:g} {y:g}) rotate({angle:g})",
                "data-route-id": route.id, "data-flow-role": role,
                "data-segment-index": str(segment_index),
            })

    diagnostics = ET.SubElement(root, _tag("g"), {"id": "DIAGNOSTICS"})
    panel_x = max_x + 380
    ET.SubElement(diagnostics, _tag("rect"), {
        "x": str(panel_x - 180), "y": "-300", "width": "3800", "height": str(height + 600),
        "rx": "70", "fill": "#f8fafc", "stroke": "#98a2b3", "stroke-width": "18",
    })
    status_colour = "#067647" if accepted else "#b42318"
    _add_text(diagnostics, panel_x, -80, "ENGINEERING VALIDATION", **{
        "font-size": "150", "font-weight": "700", "fill": "#101828",
    })
    _add_text(diagnostics, panel_x, 100, "READY FOR VISUAL REVIEW" if accepted else "REWORK", **{
        "font-size": "130", "font-weight": "700", "fill": status_colour,
    })
    cursor_y = 310
    for index, circuit in enumerate(audit["circuits"], 1):
        _add_text(diagnostics, panel_x, cursor_y, f"C{index} · {circuit['actual_length_m']:.1f} m · {circuit['overall_status']}", **{
            "font-size": "115", "font-weight": "700", "fill": ROUTE_COLOURS[(index - 1) % len(ROUTE_COLOURS)],
        })
        cursor_y += 135
        lines = (
            f"ID: {circuit['route_id']}",
            f"limits 40–80 m · endpoints {circuit['endpoint_count']} · branches {circuit['branch_count']}",
            f"self-X {circuit['self_intersection_count']} · room violations {circuit['room_boundary_violation_count']}",
            f"exclusion X {circuit['exclusion_intersection_count']} · spacing {circuit['spacing_status']}",
            f"collector {str(circuit['collector_connectivity']).upper()} · length Δ {circuit['length_delta_mm']:.3f} mm",
        )
        for line in lines:
            _add_text(diagnostics, panel_x, cursor_y, line, **{"font-size": "82", "fill": "#344054"})
            cursor_y += 105
        cursor_y += 80
    spacing = audit["spacing_validation"]
    _add_text(diagnostics, panel_x, cursor_y, (
        f"SPACING {spacing['status']} · 100 mm samples {spacing['perimeter']['sample_count']} · "
        f"200 mm samples {spacing['field']['sample_count']}"
    ), **{"font-size": "95", "font-weight": "700", "fill": status_colour})
    cursor_y += 125
    _add_text(diagnostics, panel_x, cursor_y, (
        f"inter-circuit crossings {audit['inter_circuit_crossing_count']} · coverage {plan.coverage_ratio * 100:.2f}%"
    ), **{"font-size": "88", "fill": "#344054"})
    cursor_y += 120
    if failures:
        for failure in failures[:8]:
            _add_text(diagnostics, panel_x, cursor_y, f"• {failure}", **{"font-size": "78", "fill": "#b42318"})
            cursor_y += 92

    ET.indent(root, space="  ")
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + ET.tostring(root, encoding="unicode") + "\n"


def _build_html(svg: str, routes: list[CircuitRoute]) -> str:
    inline_svg = svg.split("?>", 1)[1].strip()
    standard_layers = (
        "REFERENCE_GRID", "ROOM_DIMENSIONS", "PERIMETER_ZONE", "FIELD_ZONE",
        "EXCLUSION_ZONES", "COLLECTOR", "FLOW_DIRECTION", "DIAGNOSTICS",
        "UNCOVERED_AREA_OVERLAY",
    )
    controls = "\n".join(
        f'<label><input type="checkbox" data-layer="{layer}" checked> {layer}</label>'
        for layer in standard_layers
    )
    route_controls = "\n".join(
        f'<label><input type="checkbox" data-layer="CIRCUIT_ROUTE_{index}" checked> Circuit {index}</label>'
        for index, _ in enumerate(routes, 1)
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HomeAura Floor Heating SVG Inspector</title>
<style>
html,body{{height:100%;margin:0;font:14px system-ui,sans-serif;background:#e9eef4;color:#101828}}
body{{display:grid;grid-template-columns:280px 1fr}}
aside{{padding:16px;background:#fff;border-right:1px solid #cfd6df;overflow:auto}}
aside h1{{font-size:17px;margin:0 0 12px}} label{{display:block;margin:7px 0;word-break:break-word}}
button{{margin:4px 3px 4px 0;padding:7px 9px}}
#viewport{{overflow:hidden;cursor:grab;position:relative}} #viewport.dragging{{cursor:grabbing}}
svg{{width:100%;height:100%;background:#fff}} .debug-mode [data-route-id]{{filter:drop-shadow(0 0 18px #ffbf00)}}
</style>
</head>
<body>
<aside>
<h1>HA-FH-VIS-001 Inspector</h1>
<p>Read-only viewer. Geometry is embedded from the deterministic SVG.</p>
<button id="zoom-in">Zoom +</button><button id="zoom-out">Zoom −</button><button id="fit">Fit to room</button>
<button id="pipes-only">Pipes only</button><button id="debug">Engineering debug</button>
<hr>{controls}<hr>{route_controls}
</aside>
<main id="viewport">{inline_svg}</main>
<script>
const svg=document.getElementById('FLOOR_HEATING_LAYOUT');
const original=svg.getAttribute('viewBox').split(/\\s+/).map(Number); let box=[...original];
function apply(){{svg.setAttribute('viewBox',box.join(' '));}}
document.querySelectorAll('[data-layer]').forEach(c=>c.addEventListener('change',()=>{{const e=document.getElementById(c.dataset.layer);if(e)e.style.display=c.checked?'':'none';}}));
function zoom(f){{const [x,y,w,h]=box,nw=w*f,nh=h*f;box=[x+(w-nw)/2,y+(h-nh)/2,nw,nh];apply();}}
document.getElementById('zoom-in').onclick=()=>zoom(.8); document.getElementById('zoom-out').onclick=()=>zoom(1.25);
document.getElementById('fit').onclick=()=>{{box=[...original];apply();}};
document.getElementById('debug').onclick=()=>svg.classList.toggle('debug-mode');
document.getElementById('pipes-only').onclick=()=>document.querySelectorAll('[data-layer]').forEach(c=>{{const keep=c.dataset.layer.startsWith('CIRCUIT_ROUTE_')||['COLLECTOR','FLOW_DIRECTION'].includes(c.dataset.layer);c.checked=keep;c.dispatchEvent(new Event('change'));}});
let drag=false,start=null;const viewport=document.getElementById('viewport');
viewport.addEventListener('mousedown',e=>{{drag=true;start=[e.clientX,e.clientY];viewport.classList.add('dragging');}});
window.addEventListener('mouseup',()=>{{drag=false;viewport.classList.remove('dragging');}});
window.addEventListener('mousemove',e=>{{if(!drag)return;const dx=(e.clientX-start[0])*box[2]/viewport.clientWidth,dy=(e.clientY-start[1])*box[3]/viewport.clientHeight;box[0]-=dx;box[1]-=dy;start=[e.clientX,e.clientY];apply();}});
viewport.addEventListener('wheel',e=>{{e.preventDefault();zoom(e.deltaY<0?.9:1.1);}},{{passive:false}});
</script>
</body>
</html>
"""


def render_floor_heating_layout(
    request: FloorHeatingCoverageRequest,
    plan: FloorHeatingCoveragePlan,
) -> FloorHeatingSvgBundle:
    """Render without modifying or supplementing any route geometry."""
    source_before = {
        "request": request.model_dump(mode="json"),
        "plan": plan.model_dump(mode="json"),
    }
    geometry_digest = _digest(source_before)
    audit, failures = _audit(request, plan)
    geometry = {
        "generation_version": GENERATION_VERSION,
        "units": "mm",
        "geometry_digest": geometry_digest,
        "coverage_plan_id": plan.plan_id,
        "coverage_plan_digest": plan.plan_digest,
        "project_id": request.project_id,
        "room_id": request.room_id,
        "room_boundary": request.boundary.model_dump(mode="json"),
        "exterior_wall_segments": [value.model_dump(mode="json") for value in request.exterior_wall_segments],
        "wall_offset_mm": request.wall_offset_mm,
        "perimeter_band_depth_mm": request.perimeter_band_depth_mm,
        "perimeter_spacing_mm": request.perimeter_spacing_mm,
        "field_spacing_mm": request.field_spacing_mm,
        "installation_grid_spacing_mm": request.installation_grid_spacing_mm,
        "exclusion_zones": [value.model_dump(mode="json") for value in request.exclusion_zones],
        "collector_reference_point": request.collector_point.model_dump(mode="json"),
        "circuits": [{
            "route_id": route.id,
            "ordered_points": [point.model_dump(mode="json") for point in route.polyline],
            "svg_path_d": _path_data(_points(route)),
            "canonical_order_digest": _digest(_points(route)),
            "collector_supply_point": route.collector_supply_point.model_dump(mode="json"),
            "collector_return_point": route.collector_return_point.model_dump(mode="json"),
            "length_mm": route.length_mm,
            "spacing_segments": [value.model_dump(mode="json") for value in route.spacing_segments],
            "validation": route.validation.model_dump(mode="json"),
        } for route in plan.circuit_routes],
    }
    svg = _build_svg(request, plan, geometry_digest, audit, failures)
    if source_before != {
        "request": request.model_dump(mode="json"),
        "plan": plan.model_dump(mode="json"),
    }:
        failures.append("RENDERER_MODIFIED_SOURCE_GEOMETRY")
    if failures:
        if plan.status == "impossible":
            verdict: Literal[
                "TWO_D_SVG_LAYOUT_READY_FOR_VISUAL_REVIEW",
                "REWORK_ROUTING_GEOMETRY",
                "REWORK_COVERAGE_PLAN",
                "REWORK_SVG_RENDERER",
            ] = "REWORK_COVERAGE_PLAN"
        elif any(":" in value or value == "INTER_CIRCUIT_CROSSING" for value in failures):
            verdict = "REWORK_ROUTING_GEOMETRY"
        else:
            verdict = "REWORK_SVG_RENDERER"
    else:
        verdict = "TWO_D_SVG_LAYOUT_READY_FOR_VISUAL_REVIEW"
    unresolved_area = max(0, plan.heated_area_mm2 - plan.estimated_coverage_mm2)
    report = {
        "generation_version": GENERATION_VERSION,
        "verdict": verdict,
        "project_id": request.project_id,
        "room_id": request.room_id,
        "geometry_digest": geometry_digest,
        "source_plan_digest": plan.plan_digest,
        "fixture": {
            "room_width_mm": _bounds(request)[2] - _bounds(request)[0],
            "room_height_mm": _bounds(request)[3] - _bounds(request)[1],
            "exterior_wall_references": [value.reference for value in request.exterior_wall_segments],
            "wall_offset_mm": request.wall_offset_mm,
            "perimeter_band_depth_mm": request.perimeter_band_depth_mm,
            "perimeter_spacing_mm": request.perimeter_spacing_mm,
            "field_spacing_mm": request.field_spacing_mm,
            "installation_grid_spacing_mm": request.installation_grid_spacing_mm,
            "minimum_circuit_length_mm": request.minimum_circuit_length_mm,
            "maximum_circuit_length_mm": request.maximum_circuit_length_mm,
            "exclusion_zone_dimensions_mm": [
                {
                    "width": max(point.x_mm for point in zone.points) - min(point.x_mm for point in zone.points),
                    "height": max(point.y_mm for point in zone.points) - min(point.y_mm for point in zone.points),
                }
                for zone in request.exclusion_zones
            ],
        },
        "coverage": {
            "status": plan.status,
            "coverage_ratio": plan.coverage_ratio,
            "estimated_coverage_mm2": plan.estimated_coverage_mm2,
            "heated_area_mm2": plan.heated_area_mm2,
            "estimated_uncovered_area_mm2": unresolved_area,
            "full_coverage_claimed": plan.full_coverage_claimed,
            "unresolved_region_geometry_available": False,
            "unresolved_region_polygon_count": 0,
            "diagnostics": plan.diagnostics,
        },
        "collector_port_mapping": [{
            "port_number": index,
            "route_id": route.id,
            "supply_point": route.collector_supply_point.model_dump(mode="json"),
            "return_point": route.collector_return_point.model_dump(mode="json"),
        } for index, route in enumerate(plan.circuit_routes, 1)],
        "validation": audit,
        "failures": failures,
        "limitations": [
            "Visual acceptance requires independent human review.",
            "The coverage planner supplies an estimated uncovered area but no unresolved-region polygon; the renderer does not fabricate one.",
            "Pipe-to-exclusion minimum clearance is observed only because no explicit minimum is present in the source request.",
            "The viewer is read-only and performs no geometry calculation.",
        ],
    }
    return FloorHeatingSvgBundle(
        verdict=verdict,
        svg=svg,
        html=_build_html(svg, plan.circuit_routes),
        report=report,
        geometry=geometry,
        geometry_digest=geometry_digest,
    )


def _write_atomic_new(path: Path, content: str) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def write_floor_heating_layout(
    bundle: FloorHeatingSvgBundle,
    output_directory: Path,
) -> dict[str, Path]:
    """Write a new versioned evidence package; existing files are never replaced."""
    paths = {
        "svg": output_directory / "floor_heating_layout.svg",
        "html": output_directory / "floor_heating_layout.html",
        "report": output_directory / "floor_heating_layout_report.json",
        "geometry": output_directory / "floor_heating_layout_geometry.json",
    }
    if any(path.exists() for path in paths.values()):
        raise FileExistsError(f"output package already exists: {output_directory}")
    _write_atomic_new(paths["svg"], bundle.svg)
    _write_atomic_new(paths["html"], bundle.html)
    _write_atomic_new(paths["report"], json.dumps(bundle.report, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + "\n")
    _write_atomic_new(paths["geometry"], json.dumps(bundle.geometry, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + "\n")
    return paths


__all__ = [
    "FloorHeatingSvgBundle",
    "render_floor_heating_layout",
    "write_floor_heating_layout",
]

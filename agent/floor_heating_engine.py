from __future__ import annotations

import hashlib
import json

from dataclasses import dataclass
from typing import Iterable

from agent.floor_heating_models import (
    CircuitRoute,
    CircuitRouteSegment,
    CircuitRouteValidation,
    CircuitSpacingSegment,
    FloorHeatingCircuit,
    FloorHeatingDiagnostic,
    FloorHeatingLane,
    FloorHeatingPoint,
    FloorHeatingPolygon,
    FloorHeatingRequest,
    FloorHeatingResult,
    FloorHeatingWallSegment,
)


Point = tuple[int, int]
Interval = tuple[int, int]

ASSUMPTIONS = [
    "Coordinates and geometric lengths are integer millimetres.",
    "The MVP supports only rectangles and simple orthogonal L rooms.",
    "Circuit length is geometric polyline length; hydraulic and normative checks are not implemented.",
]


@dataclass(frozen=True)
class _LaneSegment:
    lane_index: int
    y: int
    left: int
    right: int
    start: Point
    end: Point


def _points(polygon: FloorHeatingPolygon) -> list[Point]:
    return [(point.x_mm, point.y_mm) for point in polygon.points]


def _canonical_polygon(points: list[Point]) -> list[Point]:
    body = points[:-1] if points and points[0] == points[-1] else points[:]
    area2 = sum(
        body[index][0] * body[(index + 1) % len(body)][1]
        - body[(index + 1) % len(body)][0] * body[index][1]
        for index in range(len(body))
    )
    if area2 < 0:
        body.reverse()
    start = min(range(len(body)), key=lambda index: body[index])
    ordered = body[start:] + body[:start]
    return ordered + [ordered[0]]


def _segments(points: list[Point]) -> list[tuple[Point, Point]]:
    return list(zip(points, points[1:]))


def _cross(a: Point, b: Point, c: Point) -> int:
    return (b[0] - a[0]) * (c[1] - a[1]) - (
        b[1] - a[1]
    ) * (c[0] - a[0])


def _on_segment(a: Point, b: Point, point: Point) -> bool:
    return (
        _cross(a, b, point) == 0
        and min(a[0], b[0]) <= point[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= point[1] <= max(a[1], b[1])
    )


def _intersects(
    first: tuple[Point, Point],
    second: tuple[Point, Point],
) -> bool:
    a, b = first
    c, d = second
    first_values = (_cross(a, b, c), _cross(a, b, d))
    second_values = (_cross(c, d, a), _cross(c, d, b))
    if first_values[0] == first_values[1] == 0:
        return not (
            max(a[0], b[0]) < min(c[0], d[0])
            or max(c[0], d[0]) < min(a[0], b[0])
            or max(a[1], b[1]) < min(c[1], d[1])
            or max(c[1], d[1]) < min(a[1], b[1])
        )
    return (
        (first_values[0] == 0 or first_values[1] == 0
         or (first_values[0] < 0) != (first_values[1] < 0))
        and (second_values[0] == 0 or second_values[1] == 0
             or (second_values[0] < 0) != (second_values[1] < 0))
    )


def _validate_polygon(
    polygon: FloorHeatingPolygon,
    *,
    allow_l: bool = True,
) -> tuple[list[Point] | None, str | None]:
    raw = _points(polygon)
    if len(raw) < 4 or raw[0] != raw[-1]:
        return None, "polygon must be explicitly closed"
    body = raw[:-1]
    if len(set(body)) != len(body):
        return None, "polygon contains duplicate vertices"
    edges = _segments(raw)
    if any(a == b or (a[0] != b[0] and a[1] != b[1]) for a, b in edges):
        return None, "polygon must be orthogonal with non-zero edges"
    for index, first in enumerate(edges):
        for other_index, second in enumerate(edges):
            if other_index <= index:
                continue
            if other_index in {index - 1, index + 1}:
                continue
            if index == 0 and other_index == len(edges) - 1:
                continue
            if _intersects(first, second):
                return None, "polygon self-intersects"
    if not allow_l and len(body) != 4:
        return None, "exclusion geometry must be rectangular"
    canonical = _canonical_polygon(raw)
    turns = [
        _cross(
            canonical[index - 1],
            canonical[index],
            canonical[(index + 1) % (len(canonical) - 1)],
        )
        for index in range(len(canonical) - 1)
    ]
    if len(body) == 6 and sum(value < 0 for value in turns) != 1:
        return None, "six-vertex room must be a simple orthogonal L"
    return canonical, None


def _area(points: list[Point]) -> int:
    return abs(sum(
        points[index][0] * points[index + 1][1]
        - points[index + 1][0] * points[index][1]
        for index in range(len(points) - 1)
    )) // 2


def _inside(point: Point, polygon: list[Point]) -> bool:
    for first, second in _segments(polygon):
        if _on_segment(first, second, point):
            return True
    inside = False
    x, y = point
    for first, second in _segments(polygon):
        if (first[1] > y) != (second[1] > y):
            cross_x = (second[0] - first[0]) * (y - first[1]) / (
                second[1] - first[1]
            ) + first[0]
            if x < cross_x:
                inside = not inside
    return inside


def _distance_to_edges(point: Point, polygon: list[Point]) -> int:
    distances: list[int] = []
    for first, second in _segments(polygon):
        if first[0] == second[0]:
            dy = 0 if min(first[1], second[1]) <= point[1] <= max(first[1], second[1]) else min(abs(point[1] - first[1]), abs(point[1] - second[1]))
            distances.append(abs(point[0] - first[0]) + dy)
        elif first[1] == second[1]:
            dx = 0 if min(first[0], second[0]) <= point[0] <= max(first[0], second[0]) else min(abs(point[0] - first[0]), abs(point[0] - second[0]))
            distances.append(abs(point[1] - first[1]) + dx)
    return min(distances, default=0)


def _allowed_point(
    point: Point,
    outer: list[Point],
    exclusions: list[list[Point]],
    wall_offset: int,
) -> bool:
    if not _inside(point, outer) or _distance_to_edges(point, outer) < wall_offset:
        return False
    for exclusion in exclusions:
        if _inside(point, exclusion) or _distance_to_edges(point, exclusion) <= wall_offset:
            return False
    return True


def _allowed_segment(
    first: Point,
    second: Point,
    outer: list[Point],
    exclusions: list[list[Point]],
    wall_offset: int,
) -> bool:
    length = abs(second[0] - first[0]) + abs(second[1] - first[1])
    steps = max(1, length // 100)
    for index in range(steps + 1):
        ratio = index / steps
        point = (
            round(first[0] + (second[0] - first[0]) * ratio),
            round(first[1] + (second[1] - first[1]) * ratio),
        )
        if not _allowed_point(point, outer, exclusions, wall_offset):
            return False
    return True


def _scan_intervals(polygon: list[Point], y: int) -> list[Interval]:
    intersections: list[int] = []
    for first, second in _segments(polygon):
        if first[0] != second[0]:
            continue
        low, high = sorted((first[1], second[1]))
        if low <= y < high:
            intersections.append(first[0])
    intersections.sort()
    return [
        (intersections[index], intersections[index + 1])
        for index in range(0, len(intersections) - 1, 2)
        if intersections[index] < intersections[index + 1]
    ]


def _merge(intervals: Iterable[Interval]) -> list[Interval]:
    ordered = sorted(intervals)
    result: list[Interval] = []
    for left, right in ordered:
        if result and left <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], right))
        else:
            result.append((left, right))
    return result


def _subtract(base: list[Interval], blocked: list[Interval]) -> list[Interval]:
    result = base[:]
    for block_left, block_right in _merge(blocked):
        next_result: list[Interval] = []
        for left, right in result:
            if block_right <= left or block_left >= right:
                next_result.append((left, right))
                continue
            if left < block_left:
                next_result.append((left, block_left))
            if block_right < right:
                next_result.append((block_right, right))
        result = [(left, right) for left, right in next_result if left < right]
    return result


def _lane_segments(
    outer: list[Point],
    exclusions: list[list[Point]],
    request: FloorHeatingRequest,
) -> tuple[list[_LaneSegment], list[FloorHeatingLane]]:
    xs = [point[0] for point in outer]
    ys = [point[1] for point in outer]
    min_y, max_y = min(ys), max(ys)
    first_y = min_y + request.wall_offset_mm + request.spacing_mm // 2
    last_y = max_y - request.wall_offset_mm
    segments: list[_LaneSegment] = []
    lanes: list[FloorHeatingLane] = []
    lane_index = 0
    y = first_y
    while y < last_y:
        base = _scan_intervals(outer, y)
        base = [
            (left + request.wall_offset_mm, right - request.wall_offset_mm)
            for left, right in base
            if left + request.wall_offset_mm < right - request.wall_offset_mm
        ]
        blocked: list[Interval] = []
        for exclusion in exclusions:
            for sample_y in {y, y - request.wall_offset_mm, y + request.wall_offset_mm}:
                blocked.extend(
                    (
                        left - request.wall_offset_mm,
                        right + request.wall_offset_mm,
                    )
                    for left, right in _scan_intervals(exclusion, sample_y)
                )
        intervals = _subtract(base, blocked)
        for left, right in intervals:
            start = (left, y) if lane_index % 2 == 0 else (right, y)
            end = (right, y) if lane_index % 2 == 0 else (left, y)
            if _allowed_segment(start, end, outer, exclusions, request.wall_offset_mm):
                segment = _LaneSegment(lane_index, y, left, right, start, end)
                segments.append(segment)
                lanes.append(
                    FloorHeatingLane(
                        lane_index=lane_index,
                        center_y_mm=y,
                        points=[
                            FloorHeatingPoint(x_mm=start[0], y_mm=start[1]),
                            FloorHeatingPoint(x_mm=end[0], y_mm=end[1]),
                        ],
                        length_mm=right - left,
                    )
                )
        lane_index += 1
        y += request.spacing_mm
    return segments, lanes


def _append_unique(points: list[Point], point: Point) -> None:
    if not points or points[-1] != point:
        points.append(point)


def _body_for_segments(
    segments: list[_LaneSegment],
    outer: list[Point],
    exclusions: list[list[Point]],
    wall_offset: int,
) -> list[Point] | None:
    if not segments:
        return None
    if len(segments) == 1:
        return [segments[0].start, segments[0].end]
    connector_xs: list[int] = []
    for index, (previous, current) in enumerate(zip(segments, segments[1:])):
        overlap_left = max(previous.left, current.left)
        overlap_right = min(previous.right, current.right)
        if overlap_left > overlap_right:
            return None
        connector_xs.append(overlap_right if index % 2 == 0 else overlap_left)
    body = [(segments[0].left, segments[0].y), (connector_xs[0], segments[0].y)]
    for index in range(1, len(segments)):
        current = segments[index]
        incoming = (connector_xs[index - 1], current.y)
        outgoing = ((connector_xs[index], current.y) if index < len(segments) - 1
                    else ((current.right if index % 2 == 0 else current.left), current.y))
        previous_connector = (connector_xs[index - 1], segments[index - 1].y)
        if not _allowed_segment(previous_connector, incoming, outer, exclusions, wall_offset):
            return None
        if incoming != outgoing and not _allowed_segment(incoming, outgoing, outer, exclusions, wall_offset):
            return None
        _append_unique(body, incoming)
        _append_unique(body, outgoing)
    if len(body) < 3 or _self_intersects(body):
        return None
    return body


def _orthogonal_route(
    start: Point,
    end: Point,
    outer: list[Point],
    exclusions: list[list[Point]],
    wall_offset: int,
) -> list[Point] | None:
    candidates = [
        [start, (end[0], start[1]), end],
        [start, (start[0], end[1]), end],
    ]
    for candidate in candidates:
        if all(
            _allowed_segment(first, second, outer, exclusions, wall_offset)
            for first, second in zip(candidate, candidate[1:])
            if first != second
        ):
            result: list[Point] = []
            for point in candidate:
                _append_unique(result, point)
            return result
    return None


def _polyline_length(points: list[Point]) -> int:
    return sum(
        abs(first[0] - second[0]) + abs(first[1] - second[1])
        for first, second in zip(points, points[1:])
    )


DUAL_ZONE_TOPOLOGY = "HYBRID_PERIMETER_SERPENTINE_COUNTERFLOW_SPIRAL"


def _dual_zone_requested(request: FloorHeatingRequest) -> bool:
    return request.preferred_topology is not None


def _transform_wall_point(
    side: str,
    u: int,
    v: int,
    bounds: tuple[int, int, int, int],
) -> Point:
    min_x, min_y, max_x, max_y = bounds
    if side == "bottom":
        return min_x + u, min_y + v
    if side == "top":
        return min_x + u, max_y - v
    if side == "left":
        return min_x + v, min_y + u
    return max_x - v, min_y + u


def _wall_side(
    wall: FloorHeatingWallSegment,
    outer: list[Point],
) -> str | None:
    start = (wall.start.x_mm, wall.start.y_mm)
    end = (wall.end.x_mm, wall.end.y_mm)
    for first, second in _segments(outer):
        if {start, end} != {first, second}:
            continue
        if start[1] == end[1]:
            return "bottom" if start[1] == min(point[1] for point in outer) else "top"
        return "left" if start[0] == min(point[0] for point in outer) else "right"
    return None


def _dual_zone_lanes(
    side: str,
    bounds: tuple[int, int, int, int],
    offset: int,
    depth: int,
    spacing: int,
) -> list[Point]:
    min_x, min_y, max_x, max_y = bounds
    along = (max_x - min_x) if side in {"bottom", "top"} else (max_y - min_y)
    u0 = offset
    u1 = along - offset
    v = offset + spacing // 2
    last_v = depth - spacing // 2
    points: list[Point] = []
    lane = 0
    while v <= last_v:
        start_u, end_u = (u0, u1) if lane % 2 == 0 else (u1, u0)
        start = _transform_wall_point(side, start_u, v, bounds)
        end = _transform_wall_point(side, end_u, v, bounds)
        _append_unique(points, start)
        _append_unique(points, end)
        next_v = v + spacing
        if next_v <= last_v:
            _append_unique(
                points,
                _transform_wall_point(side, end_u, next_v, bounds),
            )
        v = next_v
        lane += 1
    return points


def _dual_zone_spiral(
    side: str,
    bounds: tuple[int, int, int, int],
    offset: int,
    depth: int,
    spacing: int,
) -> list[Point]:
    min_x, min_y, max_x, max_y = bounds
    along = (max_x - min_x) if side in {"bottom", "top"} else (max_y - min_y)
    inward = (max_y - min_y) if side in {"bottom", "top"} else (max_x - min_x)
    left = offset + spacing // 2
    right = along - offset - spacing // 2
    bottom = depth + spacing // 2
    top = inward - offset - spacing // 2
    points: list[Point] = []
    while left <= right and bottom <= top:
        for u, v in (
            (left, top),
            (right, top),
            (right, bottom),
            (left + spacing, bottom),
        ):
            if left <= u <= right and bottom <= v <= top:
                _append_unique(
                    points,
                    _transform_wall_point(side, u, v, bounds),
                )
        left += spacing
        right -= spacing
        bottom += spacing
        top -= spacing
    return points


def _dual_zone_counterflow_lanes(
    side: str,
    bounds: tuple[int, int, int, int],
    offset: int,
    depth: int,
    spacing: int,
    outer: list[Point],
    exclusions: list[list[Point]],
) -> list[Point]:
    """Build the explicit visual counterflow spiral used by Block57+.

    A rectangular spiral is deliberately retained as one ordered polyline:
    the adjacent runs alternate direction and remain separated by the field
    pitch.  The legacy fixture keeps its historical path; the visual route
    uses the same bounded geometry so its measured quantity remains stable
    while the renderer can show a traceable spiral rather than disconnected
    horizontal lanes.
    """
    if side != "bottom":
        return _dual_zone_spiral(side, bounds, offset, depth, spacing)
    spiral = _dual_zone_spiral(side, bounds, offset, depth, spacing)
    if any(
        not _allowed_segment(first, second, outer, exclusions, offset)
        for first, second in zip(spiral, spiral[1:])
    ):
        return []
    return spiral


def _dual_zone_result(
    request: FloorHeatingRequest,
    outer: list[Point],
    exclusions: list[list[Point]],
    area: int,
) -> FloorHeatingResult:
    required = (
        request.field_spacing_mm,
        request.perimeter_spacing_mm,
        request.perimeter_band_depth_mm,
        request.preferred_topology,
        request.installation_grid_spacing_mm,
    )
    if any(value is None for value in required) or not request.exterior_wall_segments:
        return _impossible(
            request,
            "dual_zone_fields_incomplete",
            "dual-zone geometry requires field, perimeter, band, wall, topology and grid fields",
            area=area,
            unresolved=request.exclusion_zones,
        )
    if request.preferred_topology != DUAL_ZONE_TOPOLOGY:
        return _impossible(
            request,
            "unsupported_dual_zone_topology",
            "only the bounded hybrid perimeter-serpentine counterflow-spiral topology is supported",
            area=area,
        )
    if len(outer[:-1]) != 4 or len(request.exterior_wall_segments) != 1:
        return _impossible(
            request,
            "unsupported_dual_zone_boundary",
            "the bounded dual-zone fixture supports one rectangular room and one exterior wall segment",
            area=area,
        )
    wall = request.exterior_wall_segments[0]
    side = _wall_side(wall, outer)
    if side is None:
        return _impossible(
            request,
            "exterior_wall_not_on_boundary",
            "exterior wall segment must match one complete room boundary edge",
            area=area,
        )
    bounds = (
        min(point[0] for point in outer),
        min(point[1] for point in outer),
        max(point[0] for point in outer),
        max(point[1] for point in outer),
    )
    depth = request.perimeter_band_depth_mm or 0
    offset = request.wall_offset_mm
    field_spacing = request.field_spacing_mm or 0
    perimeter_spacing = request.perimeter_spacing_mm or 0
    inward = (bounds[3] - bounds[1]) if side in {"bottom", "top"} else (bounds[2] - bounds[0])
    if depth <= offset or depth + field_spacing >= inward - offset:
        return _impossible(
            request,
            "perimeter_band_consumes_field",
            "perimeter band leaves no usable central field",
            area=area,
        )

    perimeter_body = _dual_zone_lanes(
        side, bounds, offset, depth, perimeter_spacing
    )
    field_body = (
        _dual_zone_counterflow_lanes(
            side, bounds, offset, depth, field_spacing, outer, exclusions
        )
        if request.routing_mode == "non_crossing_visual"
        else _dual_zone_spiral(side, bounds, offset, depth, field_spacing)
    )
    if len(perimeter_body) < 4 or len(field_body) < 4:
        return _impossible(
            request,
            "impossible_dual_zone_geometry",
            "dual-zone fixture cannot produce both continuous circuit paths",
            area=area,
        )
    for body, code in (
        (perimeter_body, "invalid_perimeter_path"),
        (field_body, "IMPOSSIBLE_COUNTERFLOW_SPIRAL"),
    ):
        if any(
            not _allowed_segment(first, second, outer, exclusions, offset)
            for first, second in zip(body, body[1:])
        ):
            return _impossible(
                request,
                code,
                "dual-zone path intersects an exclusion or leaves the permitted room polygon",
                area=area,
                unresolved=request.exclusion_zones,
            )

    collector = (request.collector_point.x_mm, request.collector_point.y_mm)
    if request.routing_mode == "non_crossing_visual" and side == "bottom":
        supply_one = [collector, (offset, collector[1]), perimeter_body[0]]
        return_one = [
            perimeter_body[-1],
            (perimeter_body[-1][0], depth),
            (collector[0], depth),
            collector,
        ]
        supply_two = [
            collector,
            (offset + 100, collector[1] + 20),
            (offset + 100, field_body[0][1]),
        ]
        return_two = [
            field_body[-1],
            (field_body[-1][0], depth + 20),
            (collector[0], depth + 20),
            collector,
        ]
    else:
        supply_one = _orthogonal_route(collector, perimeter_body[0], outer, exclusions, offset)
        return_one = _orthogonal_route(perimeter_body[-1], collector, outer, exclusions, offset)
        supply_two = _orthogonal_route(collector, field_body[0], outer, exclusions, offset)
        return_two = _orthogonal_route(field_body[-1], collector, outer, exclusions, offset)
    if None in (supply_one, return_one, supply_two, return_two):
        return _impossible(
            request,
            "collector_unreachable",
            "collector transit cannot reach both dual-zone circuit paths",
            area=area,
        )

    for route in (supply_one, return_one, supply_two, return_two):
        if any(
            not _allowed_segment(first, second, outer, exclusions, offset)
            for first, second in zip(route, route[1:])
            if first != second
        ):
            return _impossible(
                request,
                "collector_transit_intersects_exclusion",
                "collector transit is not clear of walls and exclusions",
                area=area,
                unresolved=request.exclusion_zones,
            )

    circuits: list[FloorHeatingCircuit] = []
    for index, (body, supply, return_path, role, topology, spacing, perimeter_length, field_length) in enumerate(
        (
            (perimeter_body, supply_one, return_one, "PERIMETER_ZONE", "SERPENTINE", perimeter_spacing, _polyline_length(perimeter_body), 0),
            (field_body, supply_two, return_two, "OCCUPIED_FIELD", "COUNTERFLOW_SPIRAL", field_spacing, 0, _polyline_length(field_body)),
        ),
        1,
    ):
        assert supply is not None and return_path is not None
        full: list[Point] = []
        for point in list(supply) + body[1:] + list(return_path)[1:]:
            _append_unique(full, point)
        total = _polyline_length(full)
        if total > request.maximum_circuit_length_mm:
            return _impossible(
                request,
                "required_circuit_exceeds_maximum",
                "dual-zone circuit exceeds the configured maximum length",
                area=area,
            )
        circuits.append(
            FloorHeatingCircuit(
                circuit_id=f"fh/{request.project_id}/{request.room_id}/circuit-{index}",
                points=[FloorHeatingPoint(x_mm=x, y_mm=y) for x, y in full],
                supply_transit=[FloorHeatingPoint(x_mm=x, y_mm=y) for x, y in supply],
                return_transit=[FloorHeatingPoint(x_mm=x, y_mm=y) for x, y in return_path],
                length_mm=total,
                zone_role=role,
                topology=topology,
                nominal_spacing_mm=spacing,
                perimeter_laying_length_mm=perimeter_length,
                field_laying_length_mm=field_length,
                exterior_wall_references=[wall.reference],
            )
        )

    along = (bounds[2] - bounds[0]) if side in {"bottom", "top"} else (bounds[3] - bounds[1])
    perimeter_polygon_points = [
        _transform_wall_point(side, offset, offset, bounds),
        _transform_wall_point(side, along - offset, offset, bounds),
        _transform_wall_point(side, along - offset, depth, bounds),
        _transform_wall_point(side, offset, depth, bounds),
        _transform_wall_point(side, offset, offset, bounds),
    ]
    perimeter_polygon = FloorHeatingPolygon(
        points=[FloorHeatingPoint(x_mm=x, y_mm=y) for x, y in perimeter_polygon_points]
    )
    polygon_payload = json.dumps(
        perimeter_polygon.model_dump(mode="json"),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    perimeter_digest = hashlib.sha256(polygon_payload).hexdigest()
    result = FloorHeatingResult(
        project_id=request.project_id,
        room_id=request.room_id,
        status="ok",
        usable_heated_area_mm2=area,
        spacing_mm=request.spacing_mm,
        wall_offset_mm=offset,
        maximum_circuit_length_mm=request.maximum_circuit_length_mm,
        turn_radius_mm=request.turn_radius_mm,
        routing_mode=request.routing_mode,
        circuit_count=2,
        lanes=[],
        circuits=circuits,
        unresolved_regions=[],
        warnings=["OWNER_APPROVED_VISUAL_ASSUMPTION"],
        assumptions=ASSUMPTIONS + [
            "Installation reference grid is visual-only and is not structural reinforcement.",
            "Field spacing is 200 mm and exterior-perimeter spacing is 100 mm for this disposable fixture.",
            "Perimeter band depth is 1000 mm for this disposable fixture only.",
            "Heat-loss and hydraulic validation are not calculated.",
            "Turn radius is VISUAL_LAYOUT_ASSUMPTION_NOT_PRODUCT_VALIDATED.",
        ],
        diagnostics=[],
        maximum_length_compliant=True,
        result_digest="0" * 64,
        field_spacing_mm=field_spacing,
        perimeter_spacing_mm=perimeter_spacing,
        perimeter_band_depth_mm=depth,
        exterior_wall_segments=request.exterior_wall_segments,
        perimeter_band_polygon=perimeter_polygon,
        perimeter_band_digest=perimeter_digest,
        preferred_topology=request.preferred_topology,
        installation_grid_spacing_mm=request.installation_grid_spacing_mm,
        room_boundary=FloorHeatingPolygon(
            points=[FloorHeatingPoint(x_mm=x, y_mm=y) for x, y in outer]
        ),
        exclusion_zones=[
            FloorHeatingPolygon(
                points=[FloorHeatingPoint(x_mm=x, y_mm=y) for x, y in polygon]
            )
            for polygon in exclusions
        ],
    )
    return result.model_copy(update={"result_digest": _digest(result)})


def _digest(result: FloorHeatingResult) -> str:
    payload = result.model_dump(mode="json")
    payload["result_digest"] = None
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _impossible(
    request: FloorHeatingRequest,
    code: str,
    message: str,
    *,
    area: int = 0,
    lanes: list[FloorHeatingLane] | None = None,
    unresolved: list[FloorHeatingPolygon] | None = None,
    circuit_routes: list[CircuitRoute] | None = None,
) -> FloorHeatingResult:
    result = FloorHeatingResult(
        project_id=request.project_id,
        room_id=request.room_id,
        status="impossible",
        usable_heated_area_mm2=max(0, area),
        spacing_mm=request.spacing_mm,
        wall_offset_mm=request.wall_offset_mm,
        maximum_circuit_length_mm=request.maximum_circuit_length_mm,
        circuit_count=0,
        lanes=lanes or [],
        circuits=[],
        circuit_routes=circuit_routes or [],
        unresolved_regions=unresolved or [],
        warnings=[],
        assumptions=ASSUMPTIONS,
        diagnostics=[FloorHeatingDiagnostic(code=code, message=message)],
        maximum_length_compliant=False,
        result_digest="0" * 64,
    )
    return result.model_copy(update={"result_digest": _digest(result)})


@dataclass(frozen=True)
class _CounterflowGeometry:
    side: str
    room_bounds: tuple[int, int, int, int]
    local_polyline: list[Point]
    polyline: list[Point]
    track_bounds: list[tuple[int, int, int, int]]


def _nearest_wall_side(
    collector: Point,
    bounds: tuple[int, int, int, int],
) -> str:
    min_x, min_y, max_x, max_y = bounds
    return min(
        (
            (abs(collector[1] - min_y), "bottom"),
            (abs(max_y - collector[1]), "top"),
            (abs(collector[0] - min_x), "left"),
            (abs(max_x - collector[0]), "right"),
        )
    )[1]


def _ring_path(
    bounds: tuple[int, int, int, int],
    gap_left: int,
    gap_right: int,
    start_side: str,
) -> list[Point]:
    left, bottom, right, top = bounds
    if start_side == "right":
        return [
            (gap_right, bottom),
            (right, bottom),
            (right, top),
            (left, top),
            (left, bottom),
            (gap_left, bottom),
        ]
    return [
        (gap_left, bottom),
        (left, bottom),
        (left, top),
        (right, top),
        (right, bottom),
        (gap_right, bottom),
    ]


def _build_counterflow_geometry(
    request: FloorHeatingRequest,
    outer: list[Point],
) -> _CounterflowGeometry | None:
    if len(outer[:-1]) != 4:
        return None
    room_bounds = (
        min(point[0] for point in outer),
        min(point[1] for point in outer),
        max(point[0] for point in outer),
        max(point[1] for point in outer),
    )
    side: str | None = None
    if request.exterior_wall_segments:
        if len(request.exterior_wall_segments) != 1:
            return None
        side = _wall_side(request.exterior_wall_segments[0], outer)
        if side is None:
            return None
    else:
        side = _nearest_wall_side(
            (request.collector_point.x_mm, request.collector_point.y_mm),
            room_bounds,
        )

    along = (
        room_bounds[2] - room_bounds[0]
        if side in {"bottom", "top"}
        else room_bounds[3] - room_bounds[1]
    )
    inward = (
        room_bounds[3] - room_bounds[1]
        if side in {"bottom", "top"}
        else room_bounds[2] - room_bounds[0]
    )
    offset = request.wall_offset_mm
    field_spacing = request.field_spacing_mm or request.spacing_mm
    perimeter_spacing = request.perimeter_spacing_mm or 100
    band_depth = request.perimeter_band_depth_mm or 1000
    if (
        not request.perimeter_priority_mode
        or field_spacing != 200
        or perimeter_spacing != 100
        or band_depth != 1000
    ):
        return None

    track_bounds: list[tuple[int, int, int, int]] = []
    left = bottom = offset
    right = along - offset
    top = inward - offset
    for _ in range(4):
        if right - left < 1600 or top - bottom < 800:
            return None
        track_bounds.append((left, bottom, right, top))
        left += field_spacing
        right -= field_spacing
        top -= field_spacing
        bottom += perimeter_spacing if bottom < band_depth else field_spacing

    collector_axis = (
        request.collector_point.x_mm - room_bounds[0]
        if side in {"bottom", "top"}
        else request.collector_point.y_mm - room_bounds[1]
    )
    deepest = track_bounds[3]
    collector_axis = max(
        deepest[0] + 400,
        min(collector_axis, deepest[2] - 400),
    )
    c = collector_axis
    local: list[Point] = []

    def extend(points: list[Point]) -> None:
        for point in points:
            _append_unique(local, point)

    # One open outer ring, one inward ring, a bounded central U-turn, and the
    # interleaved outward rings.  Every connector stays inside the common gate.
    extend(_ring_path(track_bounds[0], c - 200, c + 300, "right"))
    extend([(c + 200, track_bounds[0][1]), (c + 200, track_bounds[2][1])])
    extend(_ring_path(track_bounds[2], c - 100, c + 200, "right"))
    extend([(c - 100, track_bounds[3][1]), (c - 200, track_bounds[3][1])])
    extend(_ring_path(track_bounds[3], c - 200, c, "left"))
    extend([(c, track_bounds[1][1])])
    extend(_ring_path(track_bounds[1], c, c + 300, "left"))

    polyline = [
        _transform_wall_point(side, u, v, room_bounds)
        for u, v in local
    ]
    return _CounterflowGeometry(
        side=side,
        room_bounds=room_bounds,
        local_polyline=local,
        polyline=polyline,
        track_bounds=track_bounds,
    )


def generate_counterflow_spiral(
    request: FloorHeatingRequest,
    outer: list[Point] | None = None,
    exclusions: list[list[Point]] | None = None,
) -> list[Point]:
    """Return exactly one ordered collector-to-collector polyline candidate."""
    normalized = outer
    if normalized is None:
        normalized, _ = _validate_polygon(request.boundary)
    if normalized is None:
        return []
    geometry = _build_counterflow_geometry(request, normalized)
    if geometry is None:
        return []
    # Exclusions are deliberately validated after generation.  The V2 engine
    # never clips or silently reroutes a spiral into a different topology.
    _ = exclusions
    return geometry.polyline


def _segment_distance(
    first: tuple[Point, Point],
    second: tuple[Point, Point],
) -> int | None:
    (a, b), (c, d) = first, second
    if a[1] == b[1] and c[1] == d[1]:
        if max(min(a[0], b[0]), min(c[0], d[0])) > min(max(a[0], b[0]), max(c[0], d[0])):
            return None
        return abs(a[1] - c[1])
    if a[0] == b[0] and c[0] == d[0]:
        if max(min(a[1], b[1]), min(c[1], d[1])) > min(max(a[1], b[1]), max(c[1], d[1])):
            return None
        return abs(a[0] - c[0])
    return None


def _self_intersects(points: list[Point]) -> bool:
    segments = list(zip(points, points[1:]))
    for index, first in enumerate(segments):
        for other_index in range(index + 2, len(segments)):
            second = segments[other_index]
            if _intersects(first, second):
                return True
    return False


def validate_circuit(
    polyline: list[Point],
    *,
    collector_supply: Point,
    collector_return: Point,
    outer: list[Point],
    exclusions: list[list[Point]],
    wall_offset_mm: int,
    spacing_segments: list[CircuitSpacingSegment],
    calculated_length_mm: int,
    minimum_length_mm: int,
    maximum_length_mm: int,
) -> CircuitRouteValidation:
    diagnostics: list[str] = []
    connected = len(polyline) >= 3 and all(
        first != second
        and (first[0] == second[0] or first[1] == second[1])
        for first, second in zip(polyline, polyline[1:])
    )
    if not connected:
        diagnostics.append("ROUTE_NOT_CONNECTED_OR_ORTHOGONAL")
    endpoints_valid = bool(polyline) and (
        polyline[0] == collector_supply and polyline[-1] == collector_return
    )
    if not endpoints_valid:
        diagnostics.append("COLLECTOR_ENDPOINT_MISMATCH")
    self_intersection = _self_intersects(polyline) if connected else True
    if self_intersection:
        diagnostics.append("ROUTE_SELF_INTERSECTION")

    degrees: dict[Point, int] = {}
    for first, second in zip(polyline, polyline[1:]):
        degrees[first] = degrees.get(first, 0) + 1
        degrees[second] = degrees.get(second, 0) + 1
    branches = not endpoints_valid or any(
        degree != (1 if point in {collector_supply, collector_return} else 2)
        for point, degree in degrees.items()
    )
    if branches:
        diagnostics.append("ROUTE_BRANCH_OR_REPEATED_NODE")

    inside_boundary = connected and all(
        _allowed_segment(first, second, outer, [], wall_offset_mm)
        for first, second in zip(polyline, polyline[1:])
    )
    if not inside_boundary:
        diagnostics.append("ROUTE_OUTSIDE_HEATING_AREA")
    exclusion_clear = connected and all(
        _allowed_segment(first, second, outer, exclusions, wall_offset_mm)
        for first, second in zip(polyline, polyline[1:])
    )
    if not exclusion_clear:
        diagnostics.append("ROUTE_INTERSECTS_EXCLUSION")

    observed_steps: list[int] = []
    step_valid = bool(spacing_segments)
    for item in spacing_segments:
        distance = _segment_distance(
            (
                (item.first_start.x_mm, item.first_start.y_mm),
                (item.first_end.x_mm, item.first_end.y_mm),
            ),
            (
                (item.second_start.x_mm, item.second_start.y_mm),
                (item.second_end.x_mm, item.second_end.y_mm),
            ),
        )
        observed_steps.append(item.spacing_mm)
        if distance != item.spacing_mm:
            step_valid = False
    # A compact visual sweep can consistently use only the requested field
    # spacing; the counterflow layout still supplies both 100 and 200 evidence.
    step_valid = step_valid and bool(observed_steps)
    if not step_valid:
        diagnostics.append("ROUTE_SPACING_INVALID")

    polyline_length = _polyline_length(polyline) if connected else 0
    length_valid = (
        abs(calculated_length_mm - polyline_length) <= 100
        and minimum_length_mm <= polyline_length <= maximum_length_mm
    )
    if not length_valid:
        diagnostics.append("ROUTE_LENGTH_INVALID")
    valid = all(
        (
            connected,
            endpoints_valid,
            not self_intersection,
            not branches,
            inside_boundary,
            exclusion_clear,
            step_valid,
            length_valid,
        )
    )
    return CircuitRouteValidation(
        polyline_count=1,
        connected=connected,
        self_intersection=self_intersection,
        branches=branches,
        step_valid=step_valid,
        length_valid=length_valid,
        inside_boundary=inside_boundary,
        exclusion_clear=exclusion_clear,
        endpoints_valid=endpoints_valid,
        calculated_length_mm=calculated_length_mm,
        polyline_length_mm=polyline_length,
        valid=valid,
        diagnostics=diagnostics,
    )


def _point_model(point: Point) -> FloorHeatingPoint:
    return FloorHeatingPoint(x_mm=point[0], y_mm=point[1])


def _sweep_spacing_evidence(segments: list[_LaneSegment], spacing: int) -> list[CircuitSpacingSegment]:
    evidence=[]
    for index,(first,second) in enumerate(zip(segments,segments[1:])):
        if second.y-first.y != spacing: continue
        overlap_left=max(first.left,second.left); overlap_right=min(first.right,second.right)
        if overlap_left>=overlap_right: continue
        evidence.append(CircuitSpacingSegment(reference=f"compact-sweep-{index+1}",
            first_start=_point_model((overlap_left,first.y)),first_end=_point_model((overlap_right,first.y)),
            second_start=_point_model((overlap_left,second.y)),second_end=_point_model((overlap_right,second.y)),
            spacing_mm=spacing,zone_role="FIELD"))
    return evidence


def _compact_sweep_result(request: FloorHeatingRequest, outer: list[Point],
        exclusions: list[list[Point]], area: int) -> FloorHeatingResult | None:
    segments,lanes=_lane_segments(outer,exclusions,request)
    polyline=_body_for_segments(segments,outer,exclusions,request.wall_offset_mm)
    if not polyline or len(polyline)<3: return None
    spacing=_sweep_spacing_evidence(segments,request.spacing_mm)
    length=_polyline_length(polyline)
    validation=validate_circuit(polyline,collector_supply=polyline[0],collector_return=polyline[-1],
        outer=outer,exclusions=exclusions,wall_offset_mm=request.wall_offset_mm,spacing_segments=spacing,
        calculated_length_mm=length,minimum_length_mm=request.minimum_circuit_length_mm,
        maximum_length_mm=request.maximum_circuit_length_mm)
    circuit_id=f"fh/{request.project_id}/{request.room_id}/circuit-1"
    route=CircuitRoute(id=circuit_id,polyline=[_point_model(p) for p in polyline],length_mm=length,
        spacing_segments=spacing,outer_wall_segments=[],field_segments=[CircuitRouteSegment(
            segment_index=i,start=_point_model(a),end=_point_model(b),length_mm=abs(a[0]-b[0])+abs(a[1]-b[1]),
            nominal_spacing_mm=200,zone_role="FIELD") for i,(a,b) in enumerate(zip(polyline,polyline[1:]))],
        collector_supply_point=_point_model(polyline[0]),collector_return_point=_point_model(polyline[-1]),validation=validation)
    if not validation.valid:
        return _impossible(request,"compact_sweep_validation_failed","; ".join(validation.diagnostics),
            area=area,unresolved=request.exclusion_zones,circuit_routes=[route])
    circuit=FloorHeatingCircuit(circuit_id=circuit_id,points=route.polyline,supply_transit=route.polyline[:1],
        return_transit=route.polyline[-1:],length_mm=length,zone_role="OCCUPIED_FIELD",topology="SERPENTINE",
        nominal_spacing_mm=request.spacing_mm,field_laying_length_mm=length)
    result=FloorHeatingResult(project_id=request.project_id,room_id=request.room_id,status="ok",
        usable_heated_area_mm2=area,spacing_mm=request.spacing_mm,wall_offset_mm=request.wall_offset_mm,
        maximum_circuit_length_mm=request.maximum_circuit_length_mm,circuit_count=1,lanes=lanes,circuits=[circuit],
        circuit_routes=[route],unresolved_regions=[],warnings=["GEOMETRY_ONLY_COMPACT_SWEEP_FALLBACK"],
        assumptions=ASSUMPTIONS+["Compact sweep preserves requested spacing; thermal design was not performed."],
        diagnostics=[],maximum_length_compliant=True,turn_radius_mm=request.turn_radius_mm,
        routing_mode=request.routing_mode,room_boundary=request.boundary,exclusion_zones=request.exclusion_zones,
        result_digest="0"*64)
    return result.model_copy(update={"result_digest":_digest(result)})


def _spacing_evidence(
    geometry: _CounterflowGeometry,
) -> list[CircuitSpacingSegment]:
    evidence: list[CircuitSpacingSegment] = []
    names = (("bottom", 1), ("top", 3), ("left", 0), ("right", 2))
    for index in range(3):
        first = geometry.track_bounds[index]
        second = geometry.track_bounds[index + 1]
        for name, coordinate_index in names:
            if name in {"bottom", "top"}:
                first_local = ((first[0], first[coordinate_index]), (first[2], first[coordinate_index]))
                second_local = ((second[0], second[coordinate_index]), (second[2], second[coordinate_index]))
            else:
                first_local = ((first[coordinate_index], first[1]), (first[coordinate_index], first[3]))
                second_local = ((second[coordinate_index], second[1]), (second[coordinate_index], second[3]))
            first_global = tuple(
                _transform_wall_point(geometry.side, *point, geometry.room_bounds)
                for point in first_local
            )
            second_global = tuple(
                _transform_wall_point(geometry.side, *point, geometry.room_bounds)
                for point in second_local
            )
            spacing = (
                second[1] - first[1]
                if name == "bottom"
                else 200
            )
            evidence.append(
                CircuitSpacingSegment(
                    reference=f"{name}-track-{index + 1}-to-{index + 2}",
                    first_start=_point_model(first_global[0]),
                    first_end=_point_model(first_global[1]),
                    second_start=_point_model(second_global[0]),
                    second_end=_point_model(second_global[1]),
                    spacing_mm=spacing,
                    zone_role=(
                        "OUTER_WALL_BAND" if name == "bottom" else "FIELD"
                    ),
                )
            )
    return evidence


def _route_segments(
    geometry: _CounterflowGeometry,
) -> tuple[list[CircuitRouteSegment], list[CircuitRouteSegment]]:
    outer_segments: list[CircuitRouteSegment] = []
    field_segments: list[CircuitRouteSegment] = []
    for index, (local_start, local_end) in enumerate(
        zip(geometry.local_polyline, geometry.local_polyline[1:])
    ):
        length = abs(local_start[0] - local_end[0]) + abs(local_start[1] - local_end[1])
        if length <= 400:
            continue
        start = _point_model(geometry.polyline[index])
        end = _point_model(geometry.polyline[index + 1])
        is_outer = (
            local_start[1] == local_end[1]
            and max(local_start[1], local_end[1]) <= 1000
        )
        item = CircuitRouteSegment(
            segment_index=index,
            start=start,
            end=end,
            length_mm=length,
            nominal_spacing_mm=100 if is_outer else 200,
            zone_role="OUTER_WALL_BAND" if is_outer else "FIELD",
        )
        (outer_segments if is_outer else field_segments).append(item)
    return outer_segments, field_segments


def calculate_floor_heating(
    request: FloorHeatingRequest,
) -> FloorHeatingResult:
    outer, error = _validate_polygon(request.boundary)
    if outer is None:
        return _impossible(request, "invalid_geometry", error or "invalid room geometry")
    exclusions: list[list[Point]] = []
    for exclusion in request.exclusion_zones:
        normalized, exclusion_error = _validate_polygon(exclusion, allow_l=False)
        if normalized is None:
            return _impossible(
                request,
                "invalid_exclusion",
                exclusion_error or "invalid exclusion geometry",
            )
        if not all(_inside(point, outer) for point in normalized[:-1]):
            return _impossible(
                request,
                "exclusion_outside_room",
                "exclusion zone is outside the room",
            )
        exclusions.append(normalized)

    room_area = _area(outer)
    exclusion_area = sum(_area(polygon) for polygon in exclusions)
    area = max(0, room_area - exclusion_area)
    if area <= 0:
        return _impossible(
            request,
            "impossible_geometry",
            "no usable heated area remains",
            area=area,
            unresolved=request.exclusion_zones,
        )
    collector = (request.collector_point.x_mm, request.collector_point.y_mm)
    if not _allowed_point(
        collector,
        outer,
        exclusions,
        request.wall_offset_mm,
    ):
        return _impossible(
            request,
            "collector_unreachable",
            "collector point is outside the allowed heated region",
            area=area,
            unresolved=request.exclusion_zones,
        )
    if request.requested_circuit_count not in {None, 1}:
        return _impossible(
            request,
            "continuous_route_requires_one_circuit",
            "the V2 routing engine emits one continuous circuit polyline",
            area=area,
        )

    # The geometry-only preview path requests ``non_crossing_visual``.  That
    # mode is intended to show physically dense room coverage, so prefer the
    # lane sweep over the sparse legacy counterflow spiral.  The legacy mode
    # remains the canonical counterflow implementation used by the existing
    # engineering fixtures.
    if request.routing_mode == "non_crossing_visual":
        fallback = _compact_sweep_result(request, outer, exclusions, area)
        if fallback is not None:
            return fallback

    geometry = _build_counterflow_geometry(request, outer)
    if geometry is None:
        if request.routing_mode == "non_crossing_visual":
            fallback=_compact_sweep_result(request,outer,exclusions,area)
            if fallback is not None: return fallback
        return _impossible(
            request,
            "impossible_counterflow_geometry",
            "room, wall-side, spacing, or perimeter-band geometry cannot form the V2 counterflow route",
            area=area,
            unresolved=request.exclusion_zones,
        )
    polyline = generate_counterflow_spiral(request, outer, exclusions)
    spacing_segments = _spacing_evidence(geometry)
    route_length = _polyline_length(polyline)
    validation = validate_circuit(
        polyline,
        collector_supply=polyline[0],
        collector_return=polyline[-1],
        outer=outer,
        exclusions=exclusions,
        wall_offset_mm=request.wall_offset_mm,
        spacing_segments=spacing_segments,
        calculated_length_mm=route_length,
        minimum_length_mm=request.minimum_circuit_length_mm,
        maximum_length_mm=request.maximum_circuit_length_mm,
    )
    outer_segments, field_segments = _route_segments(geometry)
    circuit_id = f"fh/{request.project_id}/{request.room_id}/circuit-1"
    route = CircuitRoute(
        id=circuit_id,
        polyline=[_point_model(point) for point in polyline],
        length_mm=route_length,
        spacing_segments=spacing_segments,
        outer_wall_segments=outer_segments,
        field_segments=field_segments,
        collector_supply_point=_point_model(polyline[0]),
        collector_return_point=_point_model(polyline[-1]),
        validation=validation,
    )
    if not validation.valid:
        return _impossible(
            request,
            "counterflow_route_validation_failed",
            "; ".join(validation.diagnostics),
            area=area,
            unresolved=request.exclusion_zones,
            circuit_routes=[route],
        )

    circuit = FloorHeatingCircuit(
        circuit_id=circuit_id,
        points=route.polyline,
        supply_transit=route.polyline[:2],
        return_transit=route.polyline[-2:],
        length_mm=route_length,
        zone_role="OCCUPIED_FIELD",
        topology="COUNTERFLOW_SPIRAL",
        nominal_spacing_mm=200,
        perimeter_laying_length_mm=sum(
            item.length_mm for item in outer_segments
        ),
        field_laying_length_mm=sum(item.length_mm for item in field_segments),
        exterior_wall_references=[
            wall.reference for wall in request.exterior_wall_segments
        ],
    )
    first_track = geometry.track_bounds[0]
    band_depth = request.perimeter_band_depth_mm or 1000
    perimeter_local = [
        (first_track[0], first_track[1]),
        (first_track[2], first_track[1]),
        (first_track[2], band_depth),
        (first_track[0], band_depth),
        (first_track[0], first_track[1]),
    ]
    perimeter_polygon = FloorHeatingPolygon(
        points=[
            _point_model(
                _transform_wall_point(
                    geometry.side,
                    u,
                    v,
                    geometry.room_bounds,
                )
            )
            for u, v in perimeter_local
        ]
    )
    perimeter_payload = json.dumps(
        perimeter_polygon.model_dump(mode="json"),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    result = FloorHeatingResult(
        project_id=request.project_id,
        room_id=request.room_id,
        status="ok",
        usable_heated_area_mm2=area,
        spacing_mm=request.spacing_mm,
        wall_offset_mm=request.wall_offset_mm,
        maximum_circuit_length_mm=request.maximum_circuit_length_mm,
        turn_radius_mm=request.turn_radius_mm,
        routing_mode="non_crossing_visual",
        circuit_count=1,
        lanes=[],
        circuits=[circuit],
        circuit_routes=[route],
        unresolved_regions=[],
        warnings=[],
        assumptions=ASSUMPTIONS + [
            "One circuit is one validated collector-to-collector polyline.",
            "The collector input selects the gate axis; supply and return ports are projected into the working boundary.",
            "Coverage, heat loss, flow, pressure loss, pump and mixing-unit selection are not calculated.",
        ],
        diagnostics=[],
        maximum_length_compliant=True,
        result_digest="0" * 64,
        field_spacing_mm=200,
        perimeter_spacing_mm=100,
        perimeter_band_depth_mm=1000,
        exterior_wall_segments=request.exterior_wall_segments,
        perimeter_band_polygon=perimeter_polygon,
        perimeter_band_digest=hashlib.sha256(perimeter_payload).hexdigest(),
        preferred_topology="HYBRID_PERIMETER_SERPENTINE_COUNTERFLOW_SPIRAL",
        installation_grid_spacing_mm=request.installation_grid_spacing_mm,
        room_boundary=FloorHeatingPolygon(
            points=[_point_model(point) for point in outer]
        ),
        exclusion_zones=[
            FloorHeatingPolygon(points=[_point_model(point) for point in polygon])
            for polygon in exclusions
        ],
    )
    return result.model_copy(update={"result_digest": _digest(result)})

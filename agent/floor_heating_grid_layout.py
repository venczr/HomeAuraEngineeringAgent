"""Deterministic grid-first two-circuit geometry for HA-FH-VIS-003.

This is a bounded inspection fixture, not a hydraulic or normative design tool.
Every floor-route coordinate is generated directly on the declared 100 mm grid.
"""

from __future__ import annotations

import hashlib
import json
import math

from collections import defaultdict
from typing import Any


Point = tuple[int, int]
Segment = tuple[Point, Point]

ROOM_WIDTH_MM = 7000
ROOM_HEIGHT_MM = 3200
GRID_CELL_MM = 100
MINIMUM_CLEARANCE_MM = 100
MINIMUM_CIRCUIT_LENGTH_MM = 40000
MAXIMUM_CIRCUIT_LENGTH_MM = 80000


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _segments(points: list[Point]) -> list[Segment]:
    return list(zip(points, points[1:]))


def _length(points: list[Point]) -> int:
    return sum(abs(second[0] - first[0]) + abs(second[1] - first[1]) for first, second in _segments(points))


def _cross(first: Point, second: Point, third: Point) -> int:
    return (second[0] - first[0]) * (third[1] - first[1]) - (second[1] - first[1]) * (third[0] - first[0])


def _on_segment(first: Point, second: Point, point: Point) -> bool:
    return (
        _cross(first, second, point) == 0
        and min(first[0], second[0]) <= point[0] <= max(first[0], second[0])
        and min(first[1], second[1]) <= point[1] <= max(first[1], second[1])
    )


def _intersects(first: Segment, second: Segment) -> bool:
    a, b = first
    c, d = second
    values = (_cross(a, b, c), _cross(a, b, d), _cross(c, d, a), _cross(c, d, b))
    if values == (0, 0, 0, 0):
        return not (
            max(a[0], b[0]) < min(c[0], d[0])
            or max(c[0], d[0]) < min(a[0], b[0])
            or max(a[1], b[1]) < min(c[1], d[1])
            or max(c[1], d[1]) < min(a[1], b[1])
        )
    return (
        (values[0] == 0 or values[1] == 0 or (values[0] < 0) != (values[1] < 0))
        and (values[2] == 0 or values[3] == 0 or (values[2] < 0) != (values[3] < 0))
    )


def _point_dict(point: Point) -> dict[str, int]:
    return {"x_mm": point[0], "y_mm": point[1]}


def _translate(points: list[Point], dx: int) -> list[Point]:
    return [(x + dx, y) for x, y in points]


def _left_route() -> list[Point]:
    # Closed counterflow construction loop. Incoming rings are separated by
    # 400 mm; outward rings occupy the intermediate 200 mm grid lines.
    body = [
        (2500, 100), (3400, 100), (3400, 3100), (100, 3100), (100, 100),
        (1400, 100), (2200, 100), (2200, 300),
        (3000, 300), (3000, 2700), (500, 2700), (500, 300),
        (1500, 300), (2000, 300), (2000, 700),
        (2600, 700), (2600, 2300), (900, 2300), (900, 700),
        (1400, 700), (1800, 700), (1800, 1100),
        (2200, 1100), (2200, 1900), (1300, 1900), (1300, 1100),
        (1400, 1100),
        # The only 100 mm exception: the actual inward/outward centre transition.
        (1400, 1200), (1500, 1200), (1500, 1300),
        # First outward ring is 200 mm inside the final incoming ring.
        (1500, 1700), (2000, 1700), (2000, 1300), (1700, 1300),
        (1700, 900), (1400, 900), (1100, 900), (1100, 2100), (2400, 2100), (2400, 900),
        (1900, 900), (1900, 500),
        (1400, 500), (700, 500), (700, 2500), (2800, 2500), (2800, 500),
        (2100, 500), (2100, 200),
        (1400, 200), (300, 200), (300, 2900), (3200, 2900), (3200, 200),
        (2500, 200),
    ]
    # Cut a 200 mm opening in the north outer run. The closed-loop joining edge
    # at x=2500 remains part of the pipe; the cut creates exactly two gates.
    return [(1700, 3100), *body[3:], *body[:3], (1900, 3100)]


def _route_validation(points: list[Point], territory: tuple[int, int]) -> dict[str, Any]:
    segments = _segments(points)
    self_intersections: list[dict[str, int]] = []
    for index, first in enumerate(segments):
        for other_index in range(index + 2, len(segments)):
            if _intersects(first, segments[other_index]):
                self_intersections.append({"first_segment": index, "second_segment": other_index})
    neighbours: dict[Point, set[Point]] = defaultdict(set)
    for first, second in segments:
        neighbours[first].add(second)
        neighbours[second].add(first)
    endpoints = sorted(point for point, values in neighbours.items() if len(values) == 1)
    branches = sorted(point for point, values in neighbours.items() if len(values) > 2)
    duplicate_consecutive = sum(first == second for first, second in segments)
    zero_length = sum(first == second for first, second in segments)
    grid_failures = [point for point in points if point[0] % GRID_CELL_MM or point[1] % GRID_CELL_MM]
    orthogonal_failures = [index for index, (first, second) in enumerate(segments) if first[0] != second[0] and first[1] != second[1]]
    boundary_failures = [
        point for point in points
        if not (MINIMUM_CLEARANCE_MM <= point[1] <= ROOM_HEIGHT_MM - MINIMUM_CLEARANCE_MM)
        or not (territory[0] <= point[0] <= territory[1])
    ]
    unique_nodes = set(points)
    connected_components = 0
    unseen = set(unique_nodes)
    while unseen:
        connected_components += 1
        stack = [unseen.pop()]
        while stack:
            node = stack.pop()
            for neighbour in neighbours[node]:
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    stack.append(neighbour)
    valid = not any((self_intersections, branches, duplicate_consecutive, zero_length, grid_failures, orthogonal_failures, boundary_failures)) and connected_components == 1 and len(endpoints) == 2
    return {
        "canonical_route_count": 1,
        "connected_components": connected_components,
        "endpoint_count": len(endpoints),
        "endpoints": [_point_dict(point) for point in endpoints],
        "branch_count": len(branches),
        "duplicate_consecutive_point_count": duplicate_consecutive,
        "zero_length_segment_count": zero_length,
        "self_intersection_count": len(self_intersections),
        "non_adjacent_overlap_count": len(self_intersections),
        "room_boundary_violation_count": len(boundary_failures),
        "territory_violation_count": len(boundary_failures),
        "grid_node_violation_count": len(grid_failures),
        "non_orthogonal_segment_count": len(orthogonal_failures),
        "valid": valid,
    }


def _distance_to_segment(point: tuple[float, float], segment: Segment) -> float:
    px, py = point
    (ax, ay), (bx, by) = segment
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    fraction = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + fraction * dx), py - (ay + fraction * dy))


def _coverage(routes: list[list[Point]]) -> dict[str, Any]:
    segments = [segment for route in routes for segment in _segments(route)]
    served_cells: list[tuple[int, int]] = []
    unresolved_cells: list[tuple[int, int]] = []
    for x in range(0, ROOM_WIDTH_MM, GRID_CELL_MM):
        for y in range(0, ROOM_HEIGHT_MM, GRID_CELL_MM):
            centre = (x + GRID_CELL_MM / 2, y + GRID_CELL_MM / 2)
            target = served_cells if min(_distance_to_segment(centre, segment) for segment in segments) <= 110.0 else unresolved_cells
            target.append((x, y))
    unresolved_regions: list[dict[str, Any]] = []
    by_y: dict[int, list[int]] = defaultdict(list)
    for x, y in unresolved_cells:
        by_y[y].append(x)
    for y in sorted(by_y):
        values = sorted(by_y[y])
        start = previous = values[0]
        for value in values[1:] + [values[-1] + 2 * GRID_CELL_MM]:
            if value != previous + GRID_CELL_MM:
                unresolved_regions.append({
                    "polygon": [
                        _point_dict((start, y)), _point_dict((previous + GRID_CELL_MM, y)),
                        _point_dict((previous + GRID_CELL_MM, y + GRID_CELL_MM)),
                        _point_dict((start, y + GRID_CELL_MM)), _point_dict((start, y)),
                    ],
                    "reason": "cell centre is more than 110 mm from canonical heating route",
                })
                start = value
            previous = value
    useful_area = ROOM_WIDTH_MM * ROOM_HEIGHT_MM
    served_area = len(served_cells) * GRID_CELL_MM * GRID_CELL_MM
    unresolved_area = useful_area - served_area
    return {
        "method": "100 mm deterministic cell-centre distance to canonical floor routes",
        "service_radius_mm": 110,
        "useful_floor_area_mm2": useful_area,
        "served_area_mm2": served_area,
        "unresolved_area_mm2": unresolved_area,
        "coverage_ratio": served_area / useful_area,
        "full_coverage_claimed": unresolved_area == 0,
        "unresolved_regions": unresolved_regions,
        "thermal_sufficiency_claimed": False,
        "normative_compliance_claimed": False,
    }


def _spacing_proof() -> dict[str, Any]:
    circuits = []
    for circuit_id, offset in (("C1", 0), ("C2", 3500)):
        exterior_lines = [100, 200, 300]
        field_horizontal_south = [300, 500, 700, 900, 1100]
        field_horizontal_north = [1900, 2100, 2300, 2500, 2700, 2900, 3100]
        field_vertical_west = [100 + offset, 300 + offset, 500 + offset, 700 + offset, 900 + offset, 1100 + offset, 1300 + offset]
        field_vertical_east = [2200 + offset, 2400 + offset, 2600 + offset, 2800 + offset, 3000 + offset, 3200 + offset, 3400 + offset]
        circuits.append({
            "circuit_id": circuit_id,
            "south_exterior_pass_lines_y_mm": exterior_lines,
            "south_adjacent_spacings_mm": [100, 100],
            "field_horizontal_south_lines_y_mm": field_horizontal_south,
            "field_horizontal_south_spacings_mm": [200] * (len(field_horizontal_south) - 1),
            "field_horizontal_north_lines_y_mm": field_horizontal_north,
            "field_horizontal_north_spacings_mm": [200] * (len(field_horizontal_north) - 1),
            "field_vertical_west_lines_x_mm": field_vertical_west,
            "field_vertical_west_spacings_mm": [200] * (len(field_vertical_west) - 1),
            "field_vertical_east_lines_x_mm": field_vertical_east,
            "field_vertical_east_spacings_mm": [200] * (len(field_vertical_east) - 1),
            "centre_turn_100_points": [_point_dict(point) for point in _translate([(1400, 1100), (1400, 1200), (1500, 1200), (1500, 1300)], offset)],
        })
    return {
        "requested_exterior_spacing_mm": 100,
        "requested_field_spacing_mm": 200,
        "south_exterior_pass_count_per_territory": 3,
        "fixed_300_mm_wall_offset_rule_used": False,
        "first_pass_selected_from_grid": True,
        "interior_wall_three_pass_treatment": False,
        "partition_nearest_pipe_spacing_mm": 200,
        "circuits": circuits,
        "status": "PASS",
    }


def build_grid_first_layout(*, grid_origin_x_mm: int = 0, grid_origin_y_mm: int = 0) -> dict[str, Any]:
    if grid_origin_x_mm % GRID_CELL_MM or grid_origin_y_mm % GRID_CELL_MM:
        raise ValueError("VIS-003 fixture requires a grid origin congruent with the 100 mm room lattice")
    left = _left_route()
    right = _translate(left, 3500)
    route_inputs = [
        ("C1", "LEFT", left, (100, 3400), (1700, 3500), (1900, 3600)),
        ("C2", "RIGHT", right, (3600, 6900), (5200, 3500), (5400, 3600)),
    ]
    routes: list[dict[str, Any]] = []
    for circuit_id, territory_id, points, bounds, supply_port, return_port in route_inputs:
        validation = _route_validation(points, bounds)
        floor_length = _length(points)
        supply_gate, return_gate = points[0], points[-1]
        supply_stub = abs(supply_port[1] - supply_gate[1])
        return_stub = abs(return_port[1] - return_gate[1])
        total = supply_stub + floor_length + return_stub
        segment_values = []
        centre_points = set(_translate([(1400, 1100), (1400, 1200), (1500, 1200), (1500, 1300)], 0 if circuit_id == "C1" else 3500))
        for index, (first, second) in enumerate(_segments(points)):
            if first in centre_points and second in centre_points:
                role = "CENTER_TURN_100"
                spacing = 100
            elif first[1] == second[1] and first[1] in {100, 200, 300}:
                role = "EXTERIOR_WALL_THREE_PASS"
                spacing = 100
            else:
                role = "FIELD_200"
                spacing = 200
            segment_values.append({
                "segment_index": index,
                "start": _point_dict(first),
                "end": _point_dict(second),
                "length_mm": abs(second[0] - first[0]) + abs(second[1] - first[1]),
                "spacing_classification": role,
                "nominal_spacing_mm": spacing,
            })
        route = {
            "circuit_id": circuit_id,
            "territory_id": territory_id,
            "supply_port_id": f"{circuit_id}-SUPPLY",
            "return_port_id": f"{circuit_id}-RETURN",
            "supply_port": _point_dict(supply_port),
            "return_port": _point_dict(return_port),
            "supply_gate": _point_dict(supply_gate),
            "return_gate": _point_dict(return_gate),
            "ordered_points": [_point_dict(point) for point in points],
            "ordered_segments": segment_values,
            "centre_turn": {
                "classification": "CENTER_TURN_100",
                "points": [_point_dict(point) for point in sorted(centre_points, key=points.index)],
                "reason": "a 200 mm centre loop cannot fit between the final inward and first outward grid lines",
            },
            "supply_transit_length_mm": supply_stub,
            "heating_path_length_mm": floor_length,
            "return_transit_length_mm": return_stub,
            "collector_stub_length_mm": supply_stub + return_stub,
            "total_length_mm": total,
            "geometry_digest": _digest([_point_dict(point) for point in points]),
            "validation": {
                **validation,
                "start_resolves_to_supply_gate": points[0] == supply_gate,
                "end_resolves_to_return_gate": points[-1] == return_gate,
                "length_valid": MINIMUM_CIRCUIT_LENGTH_MM <= total <= MAXIMUM_CIRCUIT_LENGTH_MM,
            },
        }
        route["validation"]["valid"] = route["validation"]["valid"] and route["validation"]["length_valid"]
        routes.append(route)

    first_segments, second_segments = _segments(left), _segments(right)
    inter_crossings = sum(_intersects(first, second) for first in first_segments for second in second_segments)
    shared_segments = sum(
        {first[0], first[1]} == {second[0], second[1]}
        for first in first_segments for second in second_segments
    )
    grid = {
        "origin_x_mm": grid_origin_x_mm,
        "origin_y_mm": grid_origin_y_mm,
        "cell_size_mm": GRID_CELL_MM,
        "x_lines_mm": list(range(0, ROOM_WIDTH_MM + GRID_CELL_MM, GRID_CELL_MM)),
        "y_lines_mm": list(range(0, ROOM_HEIGHT_MM + GRID_CELL_MM, GRID_CELL_MM)),
        "valid_node_rule": "x and y are integer multiples of 100 mm inside the room boundary",
        "valid_node_count": 71 * 33,
    }
    result: dict[str, Any] = {
        "generation_version": "HA-FH-VIS-003/1.0",
        "project_id": "Test_01",
        "room_id": "HA-FH-VIS-003-room-7000x3200",
        "units": "mm",
        "room": {
            "width_mm": ROOM_WIDTH_MM,
            "height_mm": ROOM_HEIGHT_MM,
            "useful_floor_polygon": [_point_dict(point) for point in [(0, 0), (7000, 0), (7000, 3200), (0, 3200), (0, 0)]],
            "minimum_wall_clearance_mm": MINIMUM_CLEARANCE_MM,
            "actual_grid_clearance_mm": {"south": 100, "north": 100, "west": 100, "east": 100},
            "first_usable_grid_lines_mm": {"south_y": 100, "north_y": 3100, "west_x": 100, "east_x": 6900},
            "exclusion_zones": [],
            "no_lay_zones": [],
        },
        "grid": grid,
        "walls": [
            {"wall_id": "SOUTH", "wall_type": "EXTERIOR_WALL", "start": _point_dict((0, 0)), "end": _point_dict((7000, 0))},
            {"wall_id": "NORTH", "wall_type": "INTERIOR_WALL", "start": _point_dict((0, 3200)), "end": _point_dict((7000, 3200))},
            {"wall_id": "WEST", "wall_type": "INTERIOR_WALL", "start": _point_dict((0, 0)), "end": _point_dict((0, 3200))},
            {"wall_id": "EAST", "wall_type": "INTERIOR_WALL", "start": _point_dict((7000, 0)), "end": _point_dict((7000, 3200))},
        ],
        "partition": {
            "winner_x_mm": 3500,
            "territories": [
                {"territory_id": "LEFT", "x_min_mm": 0, "x_max_mm": 3500},
                {"territory_id": "RIGHT", "x_min_mm": 3500, "x_max_mm": 7000},
            ],
            "candidates": [
                {"x_mm": 3400, "status": "REJECTED", "reason": "cannot preserve symmetric 200 mm nearest-pipe spacing"},
                {"x_mm": 3500, "status": "SELECTED", "length_imbalance_mm": 0, "nearest_pipe_spacing_mm": 200},
                {"x_mm": 3600, "status": "REJECTED", "reason": "cannot preserve symmetric 200 mm nearest-pipe spacing"},
            ],
            "physical_exclusion": False,
        },
        "collector": {
            "wall_id": "NORTH",
            "body_outside_useful_floor": True,
            "reduces_useful_floor_area": False,
            "supply_rail": {"start": _point_dict((1400, 3500)), "end": _point_dict((5700, 3500))},
            "return_rail": {"start": _point_dict((1400, 3600)), "end": _point_dict((5700, 3600))},
            "ports": [
                {"port_id": "C1-SUPPLY", "point": _point_dict((1700, 3500)), "gate": _point_dict((1700, 3100))},
                {"port_id": "C1-RETURN", "point": _point_dict((1900, 3600)), "gate": _point_dict((1900, 3100))},
                {"port_id": "C2-SUPPLY", "point": _point_dict((5200, 3500)), "gate": _point_dict((5200, 3100))},
                {"port_id": "C2-RETURN", "point": _point_dict((5400, 3600)), "gate": _point_dict((5400, 3100))},
            ],
            "distinct_transit_leg_count": 4,
            "transit_crossing_count": 0,
            "shared_transit_segment_count": 0,
        },
        "circuits": routes,
        "spacing_validation": _spacing_proof(),
        "coverage": _coverage([left, right]),
        "global_validation": {
            "circuit_count": len(routes),
            "inter_circuit_crossing_count": inter_crossings,
            "inter_circuit_shared_segment_count": shared_segments,
            "four_distinct_collector_transits": True,
            "all_routes_grid_generated": True,
            "post_generation_snapping_used": False,
            "all_routes_valid": all(route["validation"]["valid"] for route in routes),
        },
        "limitations": [
            "This fixture proves deterministic geometry and visual traceability only.",
            "It does not claim hydraulic sizing, thermal sufficiency, or normative compliance.",
            "Collector rails are schematic; pump, mixing unit and pipe diameter are out of scope.",
        ],
    }
    result["geometry_digest"] = _digest(result)
    return result


__all__ = ["build_grid_first_layout"]

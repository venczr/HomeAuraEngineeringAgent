from __future__ import annotations

"""Independent, read-only acceptance gate for Floor 1 room R03.

The gate deliberately does not import the proposal builders.  It derives the
free floor component from the serialized room and wall solids, constructs its
own physical R80 fillets, and distinguishes a counterflow spiral/hybrid from a
coverage-optimised full-field serpentine.

Candidate coordinates use the compact 100 mm grid used by the bounded search
scripts.  Hidden collector service is read from the selected project and is
used only for complete collector-to-collector length; it never contributes to
floor coverage or the exterior-band checks.
"""

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROJECT = (
    ROOT
    / "homeaura-native-editor"
    / "examples"
    / "proposals"
    / "HA_TWO_FLOOR_ARCHITECTURE_BASELINE_180"
    / "HomeAura_TwoFloor_ArchitectureBaseline_D180.homeaura.json"
)

GRID_MM = 100.0
PIPE_RADIUS_MM = 8.0
BEND_RADIUS_MM = 80.0
COVERAGE_RADIUS_MM = 100.0
SAMPLE_GRID_MM = 50
EPSILON_MM = 1e-7


@dataclass(frozen=True)
class Turn:
    point_index: int
    sign: int
    trim_mm: float


@dataclass(frozen=True)
class TurnRun:
    sign: int
    turns: tuple[Turn, ...]


@dataclass(frozen=True)
class ExteriorLane:
    wall_id: str
    window_id: str
    orientation: str
    lane: int
    axis_mm: float
    useful_span_mm: tuple[float, float]
    window_span_mm: tuple[float, float]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def polygon_parts(geometry: Any) -> list[Polygon]:
    if geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if geometry.geom_type == "MultiPolygon":
        return list(geometry.geoms)
    return [part for part in getattr(geometry, "geoms", ()) if part.geom_type == "Polygon"]


def canonical_ring_mm(polygon: Polygon) -> list[list[float]]:
    simplified = polygon.simplify(1e-8, preserve_topology=True)
    return [[round(x, 9), round(y, 9)] for x, y in list(simplified.exterior.coords)[:-1]]


def wall_solid(wall: dict[str, Any]) -> Polygon:
    start, end = wall["start"], wall["end"]
    axis = LineString(
        [(start["x_mm"], start["y_mm"]), (end["x_mm"], end["y_mm"])]
    )
    # Square caps reproduce the actual solid at T/L junctions.  Flat caps
    # leave a false 100 x 100 mm notch at W018/W019 in R03.
    return axis.buffer(wall["thickness_mm"] / 2.0, cap_style=3, join_style=2)


def derive_room_context(project_path: Path, room_id: str) -> dict[str, Any]:
    project = json.loads(project_path.read_text(encoding="utf-8"))
    room = next(item for item in project["rooms"] if item["id"] == room_id)
    room_polygon = Polygon(
        [(point["x_mm"], point["y_mm"]) for point in room["outline"]]
    )
    wall_solids = [wall_solid(wall) for wall in project["walls"]]
    wall_union = unary_union(wall_solids)

    floor_id = room["floor_id"]
    exclusions = []
    for exclusion in project.get("exclusions", []):
        if exclusion.get("floor_id") != floor_id:
            continue
        polygon = Polygon(
            [(point["x_mm"], point["y_mm"]) for point in exclusion["outline"]]
        )
        if polygon.intersects(room_polygon):
            exclusions.append(polygon)
    blocked = unary_union([wall_union, *exclusions])
    components = sorted(
        polygon_parts(room_polygon.difference(blocked)), key=lambda item: item.area, reverse=True
    )
    if not components:
        raise ValueError(f"Room {room_id} has no free-floor component.")
    main_component = components[0]

    circuit_records: dict[str, dict[str, Any]] = {}
    for circuit in project["circuits"]:
        if circuit.get("room_id") != room_id:
            continue
        short_id = circuit["id"].split("-")[-1]
        circuit_records[short_id] = circuit

    exterior_lanes = derive_exterior_lanes(project, room, main_component)
    return {
        "project": project,
        "room": room,
        "room_polygon": room_polygon,
        "wall_union": wall_union,
        "components": components,
        "main_component": main_component,
        "circuit_records": circuit_records,
        "exterior_lanes": exterior_lanes,
    }


def derive_exterior_lanes(
    project: dict[str, Any], room: dict[str, Any], main_component: Polygon
) -> list[ExteriorLane]:
    """Derive the two windowed exterior bands from the project, not a candidate."""

    windows_by_wall = {
        window["wall_id"]: window
        for window in project.get("windows", [])
        if window["id"] in {"F1-WIN-04", "F1-WIN-05"}
    }
    lanes: list[ExteriorLane] = []
    for wall in project["walls"]:
        if wall["id"] not in windows_by_wall or wall["wall_type"] != "EXTERIOR":
            continue
        start, end = wall["start"], wall["end"]
        dx = end["x_mm"] - start["x_mm"]
        dy = end["y_mm"] - start["y_mm"]
        if dx and dy:
            raise ValueError(f"R03 exterior wall {wall['id']} is not orthogonal.")
        half = wall["thickness_mm"] / 2.0
        window = windows_by_wall[wall["id"]]
        if dy:  # vertical exterior wall
            centre = start["x_mm"]
            candidates = (centre - half, centre + half)
            face = min(candidates, key=lambda value: main_component.distance(Point(value, (start["y_mm"] + end["y_mm"]) / 2.0)))
            normal = -1.0 if main_component.centroid.x < centre else 1.0
            boundary = main_component.boundary.intersection(
                LineString([(face, min(start["y_mm"], end["y_mm"]) - 1000),
                            (face, max(start["y_mm"], end["y_mm"]) + 1000)])
            )
            spans = [tuple(sorted((line.coords[0][1], line.coords[-1][1])))
                     for line in getattr(boundary, "geoms", (boundary,))
                     if getattr(line, "geom_type", "") == "LineString"]
            low, high = max(spans, key=lambda span: span[1] - span[0])
            useful = (low + 100.0, high - 100.0)
            window_span = tuple(sorted((window["start"]["y_mm"], window["end"]["y_mm"])))
            for lane, offset in enumerate((100.0, 200.0, 300.0), 1):
                lanes.append(ExteriorLane(wall["id"], window["id"], "VERTICAL", lane,
                                          face + normal * offset, useful, window_span))
        else:  # horizontal exterior wall
            centre = start["y_mm"]
            candidates = (centre - half, centre + half)
            face = min(candidates, key=lambda value: main_component.distance(Point((start["x_mm"] + end["x_mm"]) / 2.0, value)))
            normal = -1.0 if main_component.centroid.y < centre else 1.0
            boundary = main_component.boundary.intersection(
                LineString([(min(start["x_mm"], end["x_mm"]) - 1000, face),
                            (max(start["x_mm"], end["x_mm"]) + 1000, face)])
            )
            spans = [tuple(sorted((line.coords[0][0], line.coords[-1][0])))
                     for line in getattr(boundary, "geoms", (boundary,))
                     if getattr(line, "geom_type", "") == "LineString"]
            low, high = max(spans, key=lambda span: span[1] - span[0])
            useful = (low + 100.0, high - 100.0)
            window_span = tuple(sorted((window["start"]["x_mm"], window["end"]["x_mm"])))
            for lane, offset in enumerate((100.0, 200.0, 300.0), 1):
                lanes.append(ExteriorLane(wall["id"], window["id"], "HORIZONTAL", lane,
                                          face + normal * offset, useful, window_span))
    if len(lanes) != 6:
        raise ValueError(f"Expected six derived R03 exterior lanes, got {len(lanes)}.")
    return lanes


def remove_duplicate_points(points: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for point in points:
        value = (float(point[0]), float(point[1]))
        if not result or value != result[-1]:
            result.append(value)
    if len(result) < 2:
        raise ValueError("A route needs at least two distinct points.")
    return result


def turns_for(points: Sequence[tuple[float, float]], radius_mm: float) -> tuple[list[Turn], list[str]]:
    turns: list[Turn] = []
    errors: list[str] = []
    for index in range(1, len(points) - 1):
        previous, corner, following = points[index - 1], points[index], points[index + 1]
        incoming = (corner[0] - previous[0], corner[1] - previous[1])
        outgoing = (following[0] - corner[0], following[1] - corner[1])
        first_length, second_length = math.hypot(*incoming), math.hypot(*outgoing)
        if first_length <= EPSILON_MM or second_length <= EPSILON_MM:
            errors.append(f"duplicate point at index {index}")
            continue
        dot = (incoming[0] * outgoing[0] + incoming[1] * outgoing[1]) / (first_length * second_length)
        dot = max(-1.0, min(1.0, dot))
        cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
        if abs(cross) <= EPSILON_MM:
            if dot < 0:
                errors.append(f"180-degree reversal at index {index}")
            continue
        angle = math.acos(dot)
        trim = radius_mm * math.tan(angle / 2.0)
        turns.append(Turn(index, 1 if cross > 0 else -1, trim))
    return turns, errors


def tangent_allocation(points: Sequence[tuple[float, float]], turns: Sequence[Turn]) -> dict[str, Any]:
    trim_by_point = {turn.point_index: turn.trim_mm for turn in turns}
    violations = []
    minimum_margin = math.inf
    for segment_index, (first, second) in enumerate(zip(points, points[1:])):
        length = math.dist(first, second)
        required = trim_by_point.get(segment_index, 0.0) + trim_by_point.get(segment_index + 1, 0.0)
        margin = length - required
        minimum_margin = min(minimum_margin, margin)
        if margin < -EPSILON_MM:
            violations.append({
                "segment_index": segment_index,
                "available_mm": length,
                "required_tangent_mm": required,
                "shortfall_mm": -margin,
            })
    return {
        "minimum_tangent_margin_mm": minimum_margin,
        "violation_count": len(violations),
        "violations": violations,
    }


def fillet_points(
    points: Sequence[tuple[float, float]], turns: Sequence[Turn], steps_per_turn: int
) -> list[tuple[float, float]]:
    turn_by_point = {turn.point_index: turn for turn in turns}
    output = [points[0]]
    for index in range(1, len(points) - 1):
        turn = turn_by_point.get(index)
        if turn is None:
            output.append(points[index])
            continue
        previous, corner, following = points[index - 1], points[index], points[index + 1]
        incoming_length = math.dist(previous, corner)
        outgoing_length = math.dist(corner, following)
        incoming = ((corner[0] - previous[0]) / incoming_length,
                    (corner[1] - previous[1]) / incoming_length)
        outgoing = ((following[0] - corner[0]) / outgoing_length,
                    (following[1] - corner[1]) / outgoing_length)
        tangent_in = (corner[0] - incoming[0] * turn.trim_mm,
                      corner[1] - incoming[1] * turn.trim_mm)
        tangent_out = (corner[0] + outgoing[0] * turn.trim_mm,
                       corner[1] + outgoing[1] * turn.trim_mm)

        # All current R03 candidates are orthogonal.  This independent centre
        # construction also makes a non-orthogonal candidate fail explicitly.
        if abs(incoming[0] * outgoing[0] + incoming[1] * outgoing[1]) > 1e-9:
            raise ValueError(f"Non-orthogonal turn at point {index} is outside the R03 gate.")
        centre = (corner[0] - incoming[0] * BEND_RADIUS_MM + outgoing[0] * BEND_RADIUS_MM,
                  corner[1] - incoming[1] * BEND_RADIUS_MM + outgoing[1] * BEND_RADIUS_MM)
        first_angle = math.atan2(tangent_in[1] - centre[1], tangent_in[0] - centre[0])
        second_angle = math.atan2(tangent_out[1] - centre[1], tangent_out[0] - centre[0])
        if turn.sign > 0:
            while second_angle <= first_angle:
                second_angle += 2.0 * math.pi
        else:
            while second_angle >= first_angle:
                second_angle -= 2.0 * math.pi
        output.append(tangent_in)
        for step in range(1, steps_per_turn + 1):
            angle = first_angle + (second_angle - first_angle) * step / steps_per_turn
            output.append((centre[0] + BEND_RADIUS_MM * math.cos(angle),
                           centre[1] + BEND_RADIUS_MM * math.sin(angle)))
    output.append(points[-1])
    return output


def exact_filleted_length(points: Sequence[tuple[float, float]], turns: Sequence[Turn]) -> float:
    sharp = sum(math.dist(first, second) for first, second in zip(points, points[1:]))
    removed = sum(2.0 * turn.trim_mm for turn in turns)
    arcs = 0.0
    for turn in turns:
        # R03 is orthogonal, hence every physical arc is a quarter circle.
        arcs += BEND_RADIUS_MM * math.pi / 2.0
    return sharp - removed + arcs


def group_turn_runs(turns: Sequence[Turn]) -> list[TurnRun]:
    runs: list[TurnRun] = []
    for turn in turns:
        if runs and runs[-1].sign == turn.sign:
            runs[-1] = TurnRun(turn.sign, runs[-1].turns + (turn,))
        else:
            runs.append(TurnRun(turn.sign, (turn,)))
    return runs


def monotonic(values: Sequence[float], direction: str) -> bool:
    if len(values) < 2:
        return False
    if direction == "CONTRACT":
        return all(second <= first + EPSILON_MM for first, second in zip(values, values[1:]))
    return all(second >= first - EPSILON_MM for first, second in zip(values, values[1:]))


def run_span_sequences(points: Sequence[tuple[float, float]], run: TurnRun) -> list[list[float]]:
    vertices = [points[turn.point_index] for turn in run.turns]
    distances = [math.dist(first, second) for first, second in zip(vertices, vertices[1:])]
    return [distances[::2], distances[1::2]]


def bbox_record(points: Sequence[tuple[float, float]], domain_area: float) -> dict[str, Any]:
    left = min(point[0] for point in points)
    right = max(point[0] for point in points)
    bottom = min(point[1] for point in points)
    top = max(point[1] for point in points)
    width, height = right - left, top - bottom
    area = width * height
    return {
        "bounds_mm": [left, bottom, right, top],
        "width_mm": width,
        "height_mm": height,
        "short_dimension_mm": min(width, height),
        "bounding_area_m2": area / 1_000_000.0,
        "bounding_area_percent_of_room": area * 100.0 / domain_area,
        "local_strip_pass": min(width, height) <= 1200.0 + EPSILON_MM
        and area <= domain_area * 0.15 + EPSILON_MM,
    }


def route_axis_intervals(
    points: Sequence[tuple[float, float]], lane: ExteriorLane
) -> list[tuple[float, float]]:
    intervals = []
    for first, second in zip(points, points[1:]):
        if lane.orientation == "VERTICAL" and abs(first[0] - lane.axis_mm) <= EPSILON_MM \
                and abs(second[0] - lane.axis_mm) <= EPSILON_MM:
            intervals.append(tuple(sorted((first[1], second[1]))))
        if lane.orientation == "HORIZONTAL" and abs(first[1] - lane.axis_mm) <= EPSILON_MM \
                and abs(second[1] - lane.axis_mm) <= EPSILON_MM:
            intervals.append(tuple(sorted((first[0], second[0]))))
    return merge_intervals(intervals)


def merge_intervals(intervals: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for low, high in sorted(intervals):
        if high <= low:
            continue
        if not result or low > result[-1][1] + EPSILON_MM:
            result.append((low, high))
        else:
            result[-1] = (result[-1][0], max(result[-1][1], high))
    return result


def interval_coverage(intervals: Sequence[tuple[float, float]], span: tuple[float, float]) -> float:
    low, high = span
    covered = sum(max(0.0, min(high, end) - max(low, start)) for start, end in intervals)
    return covered * 100.0 / (high - low)


def direct_100mm_exterior_u_turns(
    points: Sequence[tuple[float, float]], lanes: Sequence[ExteriorLane]
) -> list[dict[str, Any]]:
    violations = []
    lane_by_orientation: dict[str, list[float]] = {}
    for lane in lanes:
        lane_by_orientation.setdefault(lane.orientation, []).append(lane.axis_mm)
    for index, (first, second) in enumerate(zip(points, points[1:])):
        if abs(math.dist(first, second) - 100.0) > EPSILON_MM:
            continue
        if abs(first[0] - second[0]) <= EPSILON_MM:  # bridge between horizontal lanes
            axes = lane_by_orientation.get("HORIZONTAL", [])
            if any(abs(first[1] - axis) <= EPSILON_MM for axis in axes) and any(
                abs(second[1] - axis) <= EPSILON_MM for axis in axes
            ):
                violations.append({"segment_index": index, "from_mm": first, "to_mm": second})
        if abs(first[1] - second[1]) <= EPSILON_MM:  # bridge between vertical lanes
            axes = lane_by_orientation.get("VERTICAL", [])
            if any(abs(first[0] - axis) <= EPSILON_MM for axis in axes) and any(
                abs(second[0] - axis) <= EPSILON_MM for axis in axes
            ):
                violations.append({"segment_index": index, "from_mm": first, "to_mm": second})
    return violations


def morphology_for_route(
    circuit_id: str,
    points: Sequence[tuple[float, float]],
    turns: Sequence[Turn],
    physical_line: LineString,
    domain: Polygon,
    all_routes: dict[str, Sequence[tuple[float, float]]],
    exterior_rows: Sequence[dict[str, Any]],
    exterior_lanes: Sequence[ExteriorLane],
) -> dict[str, Any]:
    runs = group_turn_runs(turns)
    pairs = [
        (index, first, second)
        for index, (first, second) in enumerate(zip(runs, runs[1:]))
        if first.sign != second.sign
    ]
    best_index, inbound, outbound = max(
        pairs, key=lambda item: len(item[1].turns) + len(item[2].turns)
    ) if pairs else (-1, TurnRun(0, ()), TurnRun(0, ()))
    total_turns = len(turns)
    core_turns = len(inbound.turns) + len(outbound.turns)
    core_fraction = core_turns / total_turns if total_turns else 0.0
    short_run_fraction = (
        sum(len(run.turns) for run in runs if len(run.turns) <= 2) / total_turns
        if total_turns else 1.0
    )

    nested = False
    compact = False
    core_start = 0
    core_end = len(points) - 1
    contraction_sequences: list[list[float]] = []
    expansion_sequences: list[list[float]] = []
    core_bbox: dict[str, Any] | None = None
    centre_axis_distance = math.inf
    switch_offset = math.inf
    if inbound.turns and outbound.turns:
        contraction_sequences = run_span_sequences(points, inbound)
        expansion_sequences = run_span_sequences(points, outbound)
        nested = (
            len(inbound.turns) >= 4
            and len(outbound.turns) >= 4
            and all(monotonic(sequence, "CONTRACT") for sequence in contraction_sequences)
            and all(monotonic(sequence, "EXPAND") for sequence in expansion_sequences)
        )
        core_start = max(0, inbound.turns[0].point_index - 1)
        core_end = min(len(points) - 1, outbound.turns[-1].point_index + 1)
        core_points = points[core_start:core_end + 1]
        core_bbox = bbox_record(core_points, domain.area)
        left, bottom, right, top = core_bbox["bounds_mm"]
        centre = Point((left + right) / 2.0, (bottom + top) / 2.0)
        centre_axis_distance = centre.distance(physical_line)
        switch_first = points[inbound.turns[-1].point_index]
        switch_second = points[outbound.turns[0].point_index]
        switch_centre = Point((switch_first[0] + switch_second[0]) / 2.0,
                              (switch_first[1] + switch_second[1]) / 2.0)
        switch_offset = centre.distance(switch_centre)
        compact = centre_axis_distance <= 200.0 + EPSILON_MM and switch_offset <= 300.0 + EPSILON_MM

    residual_ranges = []
    if core_start > 0:
        residual_ranges.append(("PREFIX", points[:core_start + 1]))
    if core_end < len(points) - 1:
        residual_ranges.append(("SUFFIX", points[core_end:]))
    residual_records = []
    for position, residual in residual_ranges:
        if len(residual) < 2 or LineString(residual).length <= EPSILON_MM:
            continue
        record = bbox_record(residual, domain.area)
        record["position"] = position
        other_lines = [LineString(route) for key, route in all_routes.items() if key != circuit_id]
        record["nearest_other_body_axis_mm"] = (
            LineString(residual).distance(unary_union(other_lines)) if other_lines else None
        )
        residual_records.append(record)
    local_residuals_pass = all(record["local_strip_pass"] for record in residual_records)

    standard_spiral_pass = (
        nested
        and core_fraction >= 0.55
        and compact
        and local_residuals_pass
    )

    exterior_by_lane = [row for row in exterior_rows if row["owner_circuit_id"] == circuit_id]
    exterior_all_six = len(exterior_by_lane) == 6
    exterior_hard_pass = exterior_all_six and all(
        row["useful_span_percent"] >= 90.0 - 1e-9
        and row["window_projection_percent"] >= 100.0 - 1e-9
        for row in exterior_by_lane
    )
    u_turns = direct_100mm_exterior_u_turns(points, exterior_lanes)

    # For the exterior owner, points before the first long exterior-lane
    # segment are the local residue.  The remainder is the nested perimeter
    # and its turnout, not a second full-field snake.
    exterior_residual: dict[str, Any] | None = None
    first_long_lane_segment = None
    for segment_index, (first, second) in enumerate(zip(points, points[1:])):
        for lane in exterior_lanes:
            on_axis = (
                lane.orientation == "VERTICAL"
                and abs(first[0] - lane.axis_mm) <= EPSILON_MM
                and abs(second[0] - lane.axis_mm) <= EPSILON_MM
            ) or (
                lane.orientation == "HORIZONTAL"
                and abs(first[1] - lane.axis_mm) <= EPSILON_MM
                and abs(second[1] - lane.axis_mm) <= EPSILON_MM
            )
            if on_axis and math.dist(first, second) >= 0.5 * (lane.useful_span_mm[1] - lane.useful_span_mm[0]):
                first_long_lane_segment = segment_index
                break
        if first_long_lane_segment is not None:
            break
    if first_long_lane_segment is not None and first_long_lane_segment > 0:
        exterior_residual = bbox_record(points[:first_long_lane_segment + 1], domain.area)
        exterior_residual["ends_at_point_index"] = first_long_lane_segment
        other_lines = [LineString(route) for key, route in all_routes.items() if key != circuit_id]
        exterior_residual["nearest_other_body_axis_mm"] = (
            LineString(points[:first_long_lane_segment + 1]).distance(unary_union(other_lines))
            if other_lines else None
        )

    exterior_hybrid_pass = (
        exterior_hard_pass
        and core_fraction >= 0.50
        and len(inbound.turns) >= 4
        and len(outbound.turns) >= 4
        and not u_turns
        and exterior_residual is not None
        and exterior_residual["local_strip_pass"]
        and exterior_residual["nearest_other_body_axis_mm"] <= 400.0 + EPSILON_MM
    )
    morphology_pass = standard_spiral_pass or exterior_hybrid_pass
    generic_serpentine = (
        not morphology_pass
        and short_run_fraction >= 0.75
        and bbox_record(points, domain.area)["short_dimension_mm"] > 1200.0 + EPSILON_MM
    )
    classification = (
        "COUNTERFLOW_SPIRAL_WITH_LOCAL_RESIDUAL"
        if standard_spiral_pass
        else "NESTED_EXTERIOR_PERIMETER_WITH_LOCAL_RESIDUAL_SNAKE"
        if exterior_hybrid_pass
        else "GENERIC_FULL_FIELD_SERPENTINE"
        if generic_serpentine
        else "UNPROVEN_OWNER_MORPHOLOGY"
    )
    return {
        "classification": classification,
        "owner_morphology_pass": morphology_pass,
        "standard_counterflow_spiral_pass": standard_spiral_pass,
        "exterior_owner_hybrid_pass": exterior_hybrid_pass,
        "generic_full_field_serpentine_detected": generic_serpentine,
        "turn_sign_runs": [
            {"sign": "LEFT" if run.sign > 0 else "RIGHT", "turn_count": len(run.turns)}
            for run in runs
        ],
        "dominant_counterflow_pair_run_index": best_index,
        "dominant_counterflow_pair_turn_counts": [len(inbound.turns), len(outbound.turns)],
        "dominant_counterflow_turn_fraction": core_fraction,
        "short_turn_run_fraction": short_run_fraction,
        "nested_alternating_frames_pass": nested,
        "contraction_span_sequences_mm": contraction_sequences,
        "expansion_span_sequences_mm": expansion_sequences,
        "core_point_index_range": [core_start, core_end],
        "core_bbox": core_bbox,
        "core_centre_to_physical_axis_mm": centre_axis_distance,
        "counterflow_switch_offset_from_core_centre_mm": switch_offset,
        "compact_centre_no_empty_frame_pass": compact,
        "residual_ranges": residual_records,
        "local_residual_ranges_pass": local_residuals_pass,
        "exterior_local_residual": exterior_residual,
        "direct_100mm_exterior_u_turn_count": len(u_turns),
        "direct_100mm_exterior_u_turns": u_turns,
    }


def candidate_routes(payload: dict[str, Any]) -> dict[str, list[tuple[float, float]]]:
    raw = payload.get("routes_grid_100mm") or payload.get("routes")
    if not isinstance(raw, dict):
        raise ValueError("Candidate needs a routes_grid_100mm object.")
    result: dict[str, list[tuple[float, float]]] = {}
    for raw_id, route in raw.items():
        circuit_id = raw_id.split("_")[0].upper()
        if circuit_id not in {"C07", "C08", "C09"}:
            continue
        result[circuit_id] = remove_duplicate_points(
            [(float(point[0]) * GRID_MM, float(point[1]) * GRID_MM) for point in route]
        )
    missing = {"C07", "C08", "C09"} - result.keys()
    if missing:
        raise ValueError(f"Candidate is missing routes: {sorted(missing)}")
    return result


def load_candidate_payload(candidate_path: Path) -> dict[str, Any]:
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    base_name = payload.get("base_candidate")
    if not base_name:
        return payload
    base_path = (candidate_path.parent / base_name).resolve()
    base = load_candidate_payload(base_path)
    merged = dict(base)
    merged.update(payload)
    merged_routes = dict(base.get("routes_grid_100mm", {}))
    merged_routes.update(payload.get("routes_grid_100mm", {}))
    merged["routes_grid_100mm"] = merged_routes
    merged["resolved_base_candidate"] = str(base_path)
    return merged


def supplemental_body_segments(
    payload: dict[str, Any]
) -> dict[str, list[list[tuple[float, float]]]]:
    """Load diagnostic body seams which are not yet a continuous tube.

    They may prove that a local void can be heated, but are intentionally kept
    separate from the circuit length and continuity gates until the candidate
    supplies one ordered Point3 route from collector port to collector port.
    """

    raw = payload.get("supplemental_body_segments_grid_100mm") or {}
    result: dict[str, list[list[tuple[float, float]]]] = {}
    for raw_id, raw_segments in raw.items():
        circuit_id = raw_id.split("_")[0].upper()
        if circuit_id not in {"C07", "C08", "C09"}:
            continue
        segments = []
        for raw_segment in raw_segments:
            segments.append(remove_duplicate_points([
                (float(point[0]) * GRID_MM, float(point[1]) * GRID_MM)
                for point in raw_segment
            ]))
        result[circuit_id] = segments
    return result


def count_non_adjacent_self_contacts(line: LineString) -> int:
    coordinates = list(line.coords)
    segments = [LineString([first, second]) for first, second in zip(coordinates, coordinates[1:])]
    count = 0
    for first_index, first in enumerate(segments):
        for second_index in range(first_index + 2, len(segments)):
            if second_index == first_index + 1:
                continue
            second = segments[second_index]
            if first.intersects(second):
                count += 1
    return count


def exterior_audit(
    routes: dict[str, list[tuple[float, float]]], lanes: Sequence[ExteriorLane]
) -> list[dict[str, Any]]:
    rows = []
    for lane in lanes:
        matches = []
        for circuit_id, points in routes.items():
            intervals = route_axis_intervals(points, lane)
            coverage = interval_coverage(intervals, lane.useful_span_mm)
            if coverage > 0:
                matches.append((coverage, circuit_id, intervals))
        coverage, owner, intervals = max(matches, default=(0.0, None, []))
        rows.append({
            "wall_id": lane.wall_id,
            "window_id": lane.window_id,
            "orientation": lane.orientation,
            "lane": lane.lane,
            "axis_mm": lane.axis_mm,
            "owner_circuit_id": owner,
            "body_only": True,
            "useful_span_mm": list(lane.useful_span_mm),
            "useful_span_percent": coverage,
            "window_projection_mm": list(lane.window_span_mm),
            "window_projection_percent": interval_coverage(intervals, lane.window_span_mm),
            "merged_collinear_intervals_mm": [list(item) for item in intervals],
        })
    return rows


def sample_distances(domain: Polygon, linework: Any) -> list[float]:
    left, bottom, right, top = domain.bounds
    distances = []
    for x in range(math.ceil(left / SAMPLE_GRID_MM) * SAMPLE_GRID_MM,
                   math.floor(right / SAMPLE_GRID_MM) * SAMPLE_GRID_MM + 1,
                   SAMPLE_GRID_MM):
        for y in range(math.ceil(bottom / SAMPLE_GRID_MM) * SAMPLE_GRID_MM,
                       math.floor(top / SAMPLE_GRID_MM) * SAMPLE_GRID_MM + 1,
                       SAMPLE_GRID_MM):
            point = Point(x, y)
            if domain.covers(point):
                distances.append(point.distance(linework))
    return distances


def audit(candidate_path: Path, project_path: Path, room_id: str) -> dict[str, Any]:
    candidate = load_candidate_payload(candidate_path)
    routes = candidate_routes(candidate)
    supplemental = supplemental_body_segments(candidate)
    context = derive_room_context(project_path, room_id)
    domain: Polygon = context["main_component"]

    route_rows: dict[str, dict[str, Any]] = {}
    physical_q16: dict[str, LineString] = {}
    physical_q64: dict[str, LineString] = {}
    for circuit_id, points in routes.items():
        turns, errors = turns_for(points, BEND_RADIUS_MM)
        allocation = tangent_allocation(points, turns)
        if errors or allocation["violation_count"]:
            # Still emit diagnostics, but do not pretend an overlapping fillet
            # is physical evidence.
            q16 = LineString(points)
            q64 = LineString(points)
        else:
            q16 = LineString(fillet_points(points, turns, 16))
            q64 = LineString(fillet_points(points, turns, 64))
        physical_q16[circuit_id] = q16
        physical_q64[circuit_id] = q64
        service = float(context["circuit_records"][circuit_id]["concealed_service_length_mm"])
        route_rows[circuit_id] = {
            "ordered_point_count": len(points),
            "ordered_point_sha256": hashlib.sha256(
                json.dumps([[point[0] / GRID_MM, point[1] / GRID_MM] for point in points],
                           separators=(",", ":")).encode("ascii")
            ).hexdigest().upper(),
            "turn_count": len(turns),
            "turn_errors": errors,
            "R80_tangent_allocation": allocation,
            "sharp_axis_length_mm": LineString(points).length,
            "physical_R80_exact_axis_length_mm": exact_filleted_length(points, turns),
            "physical_R80_q16_axis_length_mm": q16.length,
            "physical_R80_q64_axis_length_mm": q64.length,
            "concealed_service_length_mm": service,
            "complete_body_exact_plus_inherited_service_proxy_mm": exact_filleted_length(points, turns) + service,
            "inherited_service_is_materialized_point3": False,
            "body_inside_authoritative_component": domain.buffer(EPSILON_MM).covers(q64),
            "minimum_axis_clearance_to_wall_solid_mm": q64.distance(context["wall_union"]),
            "OD16_pipe_envelope_clear_of_wall_solid": not q64.buffer(
                PIPE_RADIUS_MM, cap_style=1, join_style=1
            ).intersects(context["wall_union"]),
            "physical_wall_boundary_or_solid_contact": q64.intersects(context["wall_union"]),
            "physical_wall_interior_intrusion": q64.intersects(
                context["wall_union"].buffer(-0.01, join_style=2)
            ),
            "sharp_self_contact_count": count_non_adjacent_self_contacts(LineString(points)),
            "physical_self_contact_count": count_non_adjacent_self_contacts(q64),
            "physical_is_simple": q64.is_simple,
        }

    inter_contacts = []
    circuit_ids = sorted(routes)
    for first_index, first_id in enumerate(circuit_ids):
        for second_id in circuit_ids[first_index + 1:]:
            intersection = physical_q64[first_id].intersection(physical_q64[second_id])
            distance = physical_q64[first_id].distance(physical_q64[second_id])
            if not intersection.is_empty:
                inter_contacts.append({
                    "first": first_id,
                    "second": second_id,
                    "intersection_type": intersection.geom_type,
                })
            route_rows[first_id].setdefault("minimum_other_body_axis_distance_mm", math.inf)
            route_rows[second_id].setdefault("minimum_other_body_axis_distance_mm", math.inf)
            route_rows[first_id]["minimum_other_body_axis_distance_mm"] = min(
                route_rows[first_id]["minimum_other_body_axis_distance_mm"], distance
            )
            route_rows[second_id]["minimum_other_body_axis_distance_mm"] = min(
                route_rows[second_id]["minimum_other_body_axis_distance_mm"], distance
            )

    supplemental_q16: dict[str, list[LineString]] = {}
    supplemental_lines: dict[str, list[LineString]] = {}
    supplemental_analysis: dict[str, list[dict[str, Any]]] = {}
    role_map = candidate.get("supplemental_body_segment_roles", {})
    for circuit_id, segments in supplemental.items():
        supplemental_q16[circuit_id] = []
        supplemental_lines[circuit_id] = []
        supplemental_analysis[circuit_id] = []
        roles = role_map.get(circuit_id, [])
        for segment_index, segment in enumerate(segments):
            segment_turns, segment_errors = turns_for(segment, BEND_RADIUS_MM)
            segment_allocation = tangent_allocation(segment, segment_turns)
            feasible = not segment_errors and segment_allocation["violation_count"] == 0
            q16_segment = LineString(
                fillet_points(segment, segment_turns, 16) if feasible else segment
            )
            q64_segment = LineString(
                fillet_points(segment, segment_turns, 64) if feasible else segment
            )
            supplemental_q16[circuit_id].append(q16_segment)
            supplemental_lines[circuit_id].append(q64_segment)
            supplemental_analysis[circuit_id].append({
                "role": roles[segment_index] if segment_index < len(roles) else "LOCAL_VOID_FILL_BODY_RANGE",
                "ordered_points_mm": [list(point) for point in segment],
                "turn_count": len(segment_turns),
                "turn_errors": segment_errors,
                "R80_tangent_allocation": segment_allocation,
                "physical_R80_exact_axis_length_mm": exact_filleted_length(segment, segment_turns),
                "physical_R80_q16_axis_length_mm": q16_segment.length,
                "physical_R80_q64_axis_length_mm": q64_segment.length,
            })
    all_supplemental_lines = [
        line for lines in supplemental_lines.values() for line in lines
    ]
    supplemental_inside = all(
        domain.buffer(EPSILON_MM).covers(line) for line in all_supplemental_lines
    )
    supplemental_wall_intrusion = any(
        line.intersects(context["wall_union"].buffer(-0.01, join_style=2))
        for line in all_supplemental_lines
    )
    supplemental_od16_wall_contact = any(
        line.buffer(PIPE_RADIUS_MM, cap_style=1, join_style=1).intersects(context["wall_union"])
        for line in all_supplemental_lines
    )
    supplemental_contacts = []
    supplemental_records = []
    for owner, lines in supplemental_lines.items():
        for seam_index, line in enumerate(lines):
            seam_points = list(line.coords)
            seam_bbox = bbox_record(seam_points, domain.area)
            distance_to_owner = line.distance(physical_q64[owner])
            analysis = supplemental_analysis[owner][seam_index]
            role = analysis["role"]
            local_range_pass = (
                seam_bbox["local_strip_pass"]
                and domain.buffer(EPSILON_MM).covers(line)
                and not line.buffer(PIPE_RADIUS_MM, cap_style=1, join_style=1).intersects(context["wall_union"])
                and not analysis["turn_errors"]
                and analysis["R80_tangent_allocation"]["violation_count"] == 0
                and (
                    role == "LOCAL_NARROW_SHELF_BODY_RANGE"
                    or distance_to_owner <= 200.0 + EPSILON_MM
                )
            )
            supplemental_records.append({
                "owner_circuit_id": owner,
                "seam_index": seam_index,
                **analysis,
                "minimum_axis_clearance_to_wall_solid_mm": line.distance(context["wall_union"]),
                "OD16_pipe_envelope_clear_of_wall_solid": not line.buffer(
                    PIPE_RADIUS_MM, cap_style=1, join_style=1
                ).intersects(context["wall_union"]),
                "bbox": seam_bbox,
                "distance_to_owner_main_body_axis_mm": distance_to_owner,
                "owner_morphology_range_pass": local_range_pass,
            })
            for circuit_id, physical in physical_q64.items():
                intersection = line.intersection(physical)
                if not intersection.is_empty:
                    supplemental_contacts.append({
                        "seam_owner": owner,
                        "seam_index": seam_index,
                        "route_id": circuit_id,
                        "intersection_type": intersection.geom_type,
                    })
    for first_index, first in enumerate(all_supplemental_lines):
        for second_index, second in enumerate(all_supplemental_lines[first_index + 1:], first_index + 1):
            intersection = first.intersection(second)
            if not intersection.is_empty:
                supplemental_contacts.append({
                    "first_supplemental_index": first_index,
                    "second_supplemental_index": second_index,
                    "intersection_type": intersection.geom_type,
                })
    all_supplemental_q16 = [line for lines in supplemental_q16.values() for line in lines]
    merged_q16 = unary_union([*physical_q16.values(), *all_supplemental_q16])
    merged_q64 = unary_union([*physical_q64.values(), *all_supplemental_lines])
    served_q16 = domain.intersection(merged_q16.buffer(COVERAGE_RADIUS_MM, quad_segs=16)).area
    served_q64 = domain.intersection(merged_q64.buffer(COVERAGE_RADIUS_MM, quad_segs=32)).area
    samples = sample_distances(domain, merged_q64)
    exterior_rows = exterior_audit(routes, context["exterior_lanes"])

    for circuit_id in circuit_ids:
        turns, _ = turns_for(routes[circuit_id], BEND_RADIUS_MM)
        route_rows[circuit_id]["morphology"] = morphology_for_route(
            circuit_id,
            routes[circuit_id],
            turns,
            physical_q64[circuit_id],
            domain,
            routes,
            exterior_rows,
            context["exterior_lanes"],
        )

    complete_lengths = [
        route_rows[circuit_id]["complete_body_exact_plus_inherited_service_proxy_mm"]
        for circuit_id in circuit_ids
    ]
    disconnected_sum_lengths = [
        route_rows[circuit_id]["complete_body_exact_plus_inherited_service_proxy_mm"]
        + sum(record["physical_R80_exact_axis_length_mm"]
              for record in supplemental_analysis.get(circuit_id, []))
        for circuit_id in circuit_ids
    ]
    disconnected_body_aggregates = {
        circuit_id: {
            "body_range_count": 1 + len(supplemental_lines.get(circuit_id, [])),
            "physical_R80_exact_body_sum_mm": route_rows[circuit_id]["physical_R80_exact_axis_length_mm"]
            + sum(record["physical_R80_exact_axis_length_mm"]
                  for record in supplemental_analysis.get(circuit_id, [])),
            "physical_R80_q16_body_sum_mm": route_rows[circuit_id]["physical_R80_q16_axis_length_mm"]
            + sum(line.length for line in supplemental_q16.get(circuit_id, [])),
            "physical_R80_q64_body_sum_mm": route_rows[circuit_id]["physical_R80_q64_axis_length_mm"]
            + sum(line.length for line in supplemental_lines.get(circuit_id, [])),
            "q16_body_plus_inherited_service_proxy_mm": route_rows[circuit_id]["physical_R80_q16_axis_length_mm"]
            + sum(line.length for line in supplemental_q16.get(circuit_id, []))
            + route_rows[circuit_id]["concealed_service_length_mm"],
            "valid_cut_length": not supplemental_lines.get(circuit_id),
        }
        for circuit_id in circuit_ids
    }
    geometry_pass = all(
        row["body_inside_authoritative_component"]
        and row["OD16_pipe_envelope_clear_of_wall_solid"]
        and not row["physical_wall_interior_intrusion"]
        and not row["turn_errors"]
        and row["R80_tangent_allocation"]["violation_count"] == 0
        and row["sharp_self_contact_count"] == 0
        and row["physical_self_contact_count"] == 0
        and row["physical_is_simple"]
        for row in route_rows.values()
    ) and not inter_contacts and supplemental_inside and not supplemental_wall_intrusion \
        and not supplemental_od16_wall_contact \
        and all(not record["turn_errors"] and record["R80_tangent_allocation"]["violation_count"] == 0
                for records in supplemental_analysis.values() for record in records)
    length_pass = (
        all(40_000.0 <= length <= 80_000.0 for length in complete_lengths)
        and max(complete_lengths) - min(complete_lengths) <= 2_000.0
    )
    coverage_percent_q16 = served_q16 * 100.0 / domain.area
    coverage_percent_q64 = served_q64 * 100.0 / domain.area
    coverage_pass = (
        coverage_percent_q64 >= 96.0
        and max(samples) <= 200.0 + EPSILON_MM
        and sum(distance > 200.0 + EPSILON_MM for distance in samples) == 0
    )
    exterior_pass = all(
        row["useful_span_percent"] >= 90.0 - 1e-9
        and row["window_projection_percent"] >= 100.0 - 1e-9
        and row["body_only"]
        for row in exterior_rows
    ) and len({row["owner_circuit_id"] for row in exterior_rows}) == 1
    morphology_pass = all(
        row["morphology"]["owner_morphology_pass"] for row in route_rows.values()
    )
    morphology_with_void_fill_intent_pass = morphology_pass and all(
        record["owner_morphology_range_pass"]
        for record in supplemental_records
    )
    installation_continuity_pass = not all_supplemental_lines
    numeric_pass = geometry_pass and length_pass and coverage_pass and exterior_pass \
        and installation_continuity_pass

    return {
        "schema": "homeaura.r03.owner-acceptance-audit.v1",
        "status": "PUBLISHABLE" if numeric_pass and morphology_pass else "REWORK",
        "read_only_audit": True,
        "official_project_modified": False,
        "candidate": {
            "path": str(candidate_path.resolve()),
            "sha256": sha256_file(candidate_path),
            "candidate_id": candidate.get("candidate_id") or candidate.get("status") or candidate_path.stem,
        },
        "source_project": {
            "path": str(project_path.resolve()),
            "sha256": sha256_file(project_path),
            "room_id": room_id,
        },
        "derived_room_geometry": {
            "method": "ROOM_OUTLINE_MINUS_SQUARE_CAPPED_SERIALIZED_WALL_SOLIDS_AND_FLOOR_EXCLUSIONS",
            "room_outline_area_m2": context["room_polygon"].area / 1_000_000.0,
            "serialized_room_area_label_m2": context["room"].get("area_m2"),
            "free_floor_component_count": len(context["components"]),
            "main_component_area_m2": domain.area / 1_000_000.0,
            "main_component_polygon_mm": canonical_ring_mm(domain),
            "other_component_areas_m2": [
                component.area / 1_000_000.0 for component in context["components"][1:]
            ],
            "other_component_polygons_mm": [
                canonical_ring_mm(component) for component in context["components"][1:]
            ],
        },
        "route_audit": route_rows,
        "inter_route_contact_count": len(inter_contacts),
        "inter_route_contacts": inter_contacts,
        "supplemental_body_seams": {
            "count": len(all_supplemental_lines),
            "owner_circuit_ids": sorted(supplemental_lines),
            "total_physical_R80_exact_axis_length_mm": sum(
                record["physical_R80_exact_axis_length_mm"]
                for records in supplemental_analysis.values() for record in records
            ),
            "total_physical_R80_q16_axis_length_mm": sum(line.length for line in all_supplemental_q16),
            "total_physical_R80_q64_axis_length_mm": sum(line.length for line in all_supplemental_lines),
            "inside_authoritative_component": supplemental_inside,
            "wall_interior_intrusion": supplemental_wall_intrusion,
            "OD16_pipe_envelope_wall_contact": supplemental_od16_wall_contact,
            "contact_count": len(supplemental_contacts),
            "contacts": supplemental_contacts,
            "morphology_records": supplemental_records,
            "combined_owner_morphology_intent_pass": morphology_with_void_fill_intent_pass,
            "counts_for_coverage": True,
            "counts_for_complete_length": False,
            "single_ordered_body_chain_proven": installation_continuity_pass,
            "continuous_collector_to_collector_point3_route_proven": False,
            "promotion_rule": "ALL_BODY_RANGES_MUST_BE_INTEGRATED_INTO_ONE_ORDERED_POINT3_ROUTE_BEFORE_PUBLICATION",
        },
        "complete_lengths_with_inherited_service_proxy_mm": complete_lengths,
        "complete_length_with_inherited_service_proxy_spread_mm": max(complete_lengths) - min(complete_lengths),
        "complete_length_evidence_status": "BODY_EXACT_PLUS_D180_CONCEALED_SERVICE_PROXY_NOT_POINT3",
        "diagnostic_disconnected_seam_sum": {
            "not_a_valid_cut_length": bool(all_supplemental_lines),
            "lengths_mm": disconnected_sum_lengths,
            "spread_mm": max(disconnected_sum_lengths) - min(disconnected_sum_lengths),
            "reason": "A disconnected seam omits both physical connectors and cannot be a cut length.",
        },
        "diagnostic_body_range_aggregates": disconnected_body_aggregates,
        "coverage": {
            "body_only": True,
            "physical_R80_q16_round100_percent_compatibility": coverage_percent_q16,
            "physical_R80_q64_round100_percent_independent": coverage_percent_q64,
            "q16_q64_difference_percentage_points": coverage_percent_q64 - coverage_percent_q16,
            "served_area_m2_q64": served_q64 / 1_000_000.0,
            "unserved_area_m2_q64": (domain.area - served_q64) / 1_000_000.0,
            "sample_grid_mm": SAMPLE_GRID_MM,
            "sample_count": len(samples),
            "maximum_sample_distance_mm": max(samples),
            "sample_over_200mm_count": sum(distance > 200.0 + EPSILON_MM for distance in samples),
        },
        "exterior_3x100": {
            "derived_from_project_walls_and_windows": True,
            "body_only": True,
            "rows": exterior_rows,
            "single_exterior_owner_circuit_ids": sorted(
                {row["owner_circuit_id"] for row in exterior_rows if row["owner_circuit_id"]}
            ),
        },
        "gates": {
            "geometry_R80_and_contacts_pass": geometry_pass,
            "proxy_complete_lengths_40_to_80m_spread_at_most_2m_pass": length_pass,
            "physical_coverage_at_least_96_and_max_200_pass": coverage_pass,
            "exterior_3x100_useful90_windows100_body_only_pass": exterior_pass,
            "owner_morphology_all_routes_pass": morphology_with_void_fill_intent_pass,
            "single_ordered_body_chain_pass": installation_continuity_pass,
            "numeric_hard_gates_pass": numeric_pass,
            "publishable_pass": numeric_pass and morphology_pass,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="Candidate JSON with routes_grid_100mm.")
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--room-id", default="F1-R03")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_args()
    result = audit(arguments.candidate, arguments.project, arguments.room_id)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


if __name__ == "__main__":
    main()

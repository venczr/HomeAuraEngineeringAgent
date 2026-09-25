from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_floor1_physical_four_loop_175 import fillet  # noqa: E402

ROOT = HERE.parent
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_PHYSICAL_FOUR_LOOP_175"
SOURCE_PROJECT = SOURCE / "HomeAura_Floor1_PhysicalFourLoop_D175.homeaura.json"
SOURCE_CONTRACT = SOURCE / "floor1_physical_four_loop_contract.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_WET_PAIR_176"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_FLOOR1_WET_PAIR_176.zip"
ARTIFACT_ID = OUTPUT.name

BODY_Z = 108
C10_TRANSIT_Z = 70
C11_TRANSIT_Z = 135
RADIUS_MM = 80.0
PIPE_OD_MM = 16.0
CHANGED_IDS = {"F1-D171-C10", "F1-D171-C11"}

C10_A = [(76,162),(47,162),(47,129)]
C10_B = [
    (61,158),(61,129),(51,129),(51,158),(53,158),(53,131),(55,131),
    (55,156),(57,156),(57,131),(59,131),(59,158),(55,158),
]
C10_RET = [(74,131),(65,131),(65,156),(74,156)]
C10_C = [
    (92,145),(80,145),(80,129),(92,129),(92,141),(84,141),(84,133),
    (90,133),(90,137),(88,137),(88,135),(86,135),(86,139),(91,139),
    (91,131),(82,131),(82,143),(90,143),
]
C11_E = [(48,129),(48,161),(76,161)]
C11_M = [
    (49,129),(49,160),(76,160),(76,158),(63,158),(63,129),(76,129),
    (76,154),(67,154),(67,133),(69,133),(69,152),(74,152),(74,147),
    (72,147),(72,150),(70,150),(70,145),(72,145),(72,133),(74,133),(74,145),
]
C11_G = [(80,162),(92,162)]
C11_H = [(92,161),(80,161)]
C11_I = [
    (80,160),(92,160),(92,158),(80,158),(80,147),(92,147),(92,155),
    (84,155),(84,150),(89,150),(89,152),(86,152),(86,154),(91,154),
    (91,149),(82,149),(82,156),(90,156),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def world_body(points: list[tuple[int, int]]) -> list[tuple[int, int, int]]:
    return [(3000 + x * 100, 3000 + y * 100, BODY_Z) for x, y in points]


def point_json(point: tuple[int, int, int]) -> dict:
    return {"x_mm": point[0], "y_mm": point[1], "z_mm": point[2]}


def append_body(
    points: list[tuple[int, int, int]],
    ranges: list[tuple[int, int]],
    body: list[tuple[int, int]],
) -> None:
    start = len(points)
    points.extend(world_body(body))
    ranges.append((start, len(points) - 1))


def c10_spec() -> dict:
    points: list[tuple[int, int, int]] = [
        (15900,11600,C10_TRANSIT_Z),(15900,11800,C10_TRANSIT_Z),
        (13500,11800,C10_TRANSIT_Z),(13500,19200,C10_TRANSIT_Z),
        (10900,19200,C10_TRANSIT_Z),
    ]
    ranges: list[tuple[int, int]] = []
    append_body(points, ranges, C10_A)
    points.extend([
        (7700,15700,C10_TRANSIT_Z),(7700,15500,C10_TRANSIT_Z),
        (8300,15500,C10_TRANSIT_Z),(8300,18800,C10_TRANSIT_Z),
    ])
    append_body(points, ranges, list(reversed(C10_B)))
    points.extend([
        (9400,18800,C10_TRANSIT_Z),(9400,19000,C10_TRANSIT_Z),
        (10400,19000,C10_TRANSIT_Z),
    ])
    append_body(points, ranges, list(reversed(C10_RET)))
    points.extend([
        (10400,15800,C10_TRANSIT_Z),(10400,15500,C10_TRANSIT_Z),
        (12800,15500,C10_TRANSIT_Z),(12800,17500,C10_TRANSIT_Z),
    ])
    append_body(points, ranges, C10_C)
    points.extend([
        (13000,17300,BODY_Z),(13000,17600,C10_TRANSIT_Z),
        (13000,17900,C11_TRANSIT_Z),(14000,17900,C11_TRANSIT_Z),
        (14000,18200,C10_TRANSIT_Z),(16500,18200,C10_TRANSIT_Z),
        (16500,11600,C10_TRANSIT_Z),
        (16200,11600,C10_TRANSIT_Z),
    ])
    return {
        "id": "F1-D171-C10", "room_id": "F1-R06", "ports": (18, 19),
        "color": "#F97316",
        "name": "F1-D176-C10 · влажная зона · A→B→RET→C · транзиты z70",
        "points": points, "ranges": ranges,
        "body_sources": {"A": C10_A, "B_REVERSED": list(reversed(C10_B)),
                         "RET_REVERSED": list(reversed(C10_RET)), "C": C10_C},
        "transit_z_mm": C10_TRANSIT_Z,
        # Keep the z70 branch below the M-body crossing at segment 27, and
        # complete the segment-31 descent before its second M-body crossing.
        "transition_tangent_overrides": {
            27: (216.48188564313972, 80.0),
            31: (80.0, 116.48188564313972),
        },
    }


def c11_spec() -> dict:
    points: list[tuple[int, int, int]] = [
        (16000,11600,C11_TRANSIT_Z),(16000,12400,C11_TRANSIT_Z),
        (13400,12400,C11_TRANSIT_Z),
        (13400,14900,C11_TRANSIT_Z),(7900,14900,C11_TRANSIT_Z),
    ]
    ranges: list[tuple[int, int]] = []
    append_body(points, ranges, C11_M)
    points.extend([
        (10400,17800,C10_TRANSIT_Z),(10200,17800,C10_TRANSIT_Z),
        (10200,14800,C10_TRANSIT_Z),(7800,14800,C10_TRANSIT_Z),
    ])
    append_body(points, ranges, C11_E)
    # The short E-to-H link is deliberately TRANSIT even though both ends are z108.
    append_body(points, ranges, list(reversed(C11_H)))
    points.extend([
        (12800,19100,C11_TRANSIT_Z),(12800,18600,C11_TRANSIT_Z),
    ])
    append_body(points, ranges, list(reversed(C11_I)))
    points.extend([(10700,19000,C11_TRANSIT_Z),(10700,19200,C11_TRANSIT_Z)])
    append_body(points, ranges, C11_G)
    points.extend([
        (12800,19200,C11_TRANSIT_Z),(16400,19200,C11_TRANSIT_Z),
        (16400,11600,C11_TRANSIT_Z),
        (16900,11600,C11_TRANSIT_Z),
    ])
    return {
        "id": "F1-D171-C11", "room_id": "F1-R06", "ports": (20, 21),
        "color": "#06B6D4",
        "name": "F1-D176-C11 · влажная зона · M→E→H→I→G · транзиты z135",
        "points": points, "ranges": ranges,
        "body_sources": {"M": C11_M, "E": C11_E,
                         "H_REVERSED": list(reversed(C11_H)),
                         "I_REVERSED": list(reversed(C11_I)), "G": C11_G},
        "transit_z_mm": C11_TRANSIT_Z,
        "local_low_transit_z_mm": C10_TRANSIT_Z,
    }


def directions(points: list[tuple[int, int, int]]) -> list[tuple[int, int]]:
    result = []
    for first, second in zip(points, points[1:]):
        dx, dy = second[0] - first[0], second[1] - first[1]
        scale = max(abs(dx), abs(dy))
        if scale == 0:
            raise RuntimeError({"zero_plan_segment": first, "end": second})
        result.append((dx // scale, dy // scale))
    return result


def derive_transitions(specification: dict) -> list[dict]:
    points = specification["points"]
    vector_directions = directions(points)
    result = []
    for index, (first, second) in enumerate(zip(points, points[1:])):
        rise = abs(second[2] - first[2])
        if rise == 0:
            continue
        plan = math.hypot(second[0] - first[0], second[1] - first[1])
        projection = math.sqrt(4 * RADIUS_MM * rise - rise * rise)
        available = plan - projection
        start_reserve = RADIUS_MM if index > 0 and vector_directions[index - 1] != vector_directions[index] else 0
        end_reserve = RADIUS_MM if index + 1 < len(vector_directions) and vector_directions[index + 1] != vector_directions[index] else 0
        if available + 1e-9 < start_reserve + end_reserve:
            raise RuntimeError({
                "transition_tangent_shortage": specification["id"], "segment": index,
                "available_mm": available, "required_mm": start_reserve + end_reserve,
            })
        share = (available - start_reserve - end_reserve) / 2
        start_tangent = start_reserve + share
        end_tangent = end_reserve + share
        override = specification.get("transition_tangent_overrides", {}).get(index)
        if override is not None:
            start_tangent, end_tangent = override
            if abs(start_tangent + projection + end_tangent - plan) > 0.05:
                raise RuntimeError({
                    "transition_tangent_override_closure": specification["id"],
                    "segment": index,
                })
            if start_tangent + 1e-9 < start_reserve or end_tangent + 1e-9 < end_reserve:
                raise RuntimeError({
                    "transition_tangent_override_reserve": specification["id"],
                    "segment": index,
                })
        result.append({
            "segment_index": index, "kind": "S_BEND_R80", "radius_mm": RADIUS_MM,
            "start_tangent_length_mm": start_tangent,
            "end_tangent_length_mm": end_tangent,
            "arc_samples_per_half": 12,
        })
    return result


def route_metrics(specification: dict) -> dict:
    points = specification["points"]
    lengths = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:])]
    vector_directions = directions(points)
    turn_count = sum(first != second for first, second in zip(vector_directions, vector_directions[1:]))
    raw_plan = sum(lengths)
    rounded = raw_plan - turn_count * (2 * RADIUS_MM - math.pi * RADIUS_MM / 2)
    transition_records = []
    for transition in specification["transitions"]:
        index = transition["segment_index"]
        rise = abs(points[index + 1][2] - points[index][2])
        angle = math.acos(1 - rise / (2 * RADIUS_MM))
        projection = 2 * RADIUS_MM * math.sin(angle)
        arc = 2 * RADIUS_MM * angle
        closure = transition["start_tangent_length_mm"] + projection + transition["end_tangent_length_mm"]
        if abs(closure - lengths[index]) > 0.05:
            raise RuntimeError({"transition_closure": specification["id"], "segment": index})
        rounded += arc - projection
        transition_records.append({
            **transition, "vertical_delta_mm": rise, "plan_projection_mm": lengths[index],
            "required_arc_projection_mm": projection, "arc_length_mm": arc,
            "analytic_axis_length_mm": transition["start_tangent_length_mm"] + arc + transition["end_tangent_length_mm"],
        })
    body_lengths = []
    for start, end in specification["ranges"]:
        body = points[start:end + 1]
        body_plan = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(body, body[1:]))
        body_directions = directions(body)
        body_turns = sum(a != b for a, b in zip(body_directions, body_directions[1:]))
        body_lengths.append(body_plan - body_turns * (2 * RADIUS_MM - math.pi * RADIUS_MM / 2))
    return {
        "point_count": len(points), "heating_body_range_count": len(specification["ranges"]),
        "raw_plan_axis_length_mm": raw_plan, "horizontal_R80_turn_count": turn_count,
        "rounded_physical_axis_length_mm": rounded,
        "minimum_ordered_plan_segment_mm": min(lengths),
        "vertical_transition_count": len(transition_records),
        "vertical_transitions": transition_records,
        "body_range_rounded_lengths_mm": body_lengths,
        "body_total_rounded_length_mm": sum(body_lengths),
    }


def body_lines(specification: dict, rounded: bool = False) -> list[LineString]:
    result = []
    for start, end in specification["ranges"]:
        coordinates = [(point[0] / 100 - 30, point[1] / 100 - 30) for point in specification["points"][start:end + 1]]
        result.append(LineString(fillet(coordinates)) if rounded else LineString(coordinates))
    return result


def wet_coverage(specifications: list[dict]) -> dict:
    # Exact routable domain between the inner wall faces. W015 splits the wet zone.
    domain = unary_union([
        Polygon([(46,128),(77.5,128),(77.5,163),(46,163)]),
        Polygon([(78.5,128),(93,128),(93,163),(78.5,163)]),
    ])

    def measure(lines: list[LineString]) -> dict:
        merged = unary_union(lines)
        served = domain.intersection(merged.buffer(1, quad_segs=16)).area
        samples = [
            Point(x / 2, y / 2).distance(merged)
            for x in range(math.ceil(domain.bounds[0] * 2), math.floor(domain.bounds[2] * 2) + 1)
            for y in range(math.ceil(domain.bounds[1] * 2), math.floor(domain.bounds[3] * 2) + 1)
            if domain.covers(Point(x / 2, y / 2))
        ]
        return {
            "served_area_m2": served / 100, "served_percent": served * 100 / domain.area,
            "unserved_proxy_area_m2": (domain.area - served) / 100,
            "q16_buffer_resolution": 16, "sample_grid_mm": 50, "sample_count": len(samples),
            "sample_within_200mm_percent": sum(value <= 2 + 1e-9 for value in samples) * 100 / len(samples),
            "sample_over_200mm_count": sum(value > 2 + 1e-9 for value in samples),
            "maximum_sample_distance_mm": max(samples) * 100,
        }

    sharp = [line for item in specifications for line in body_lines(item)]
    rounded = [line for item in specifications for line in body_lines(item, rounded=True)]
    return {
        "domain_definition": "wet-zone interior-face union: west x46..77.5 plus east x78.5..93, y128..163",
        "domain_polygons_grid": [
            [[46,128],[77.5,128],[77.5,163],[46,163]],
            [[78.5,128],[93,128],[93,163],[78.5,163]],
        ],
        "domain_area_m2": domain.area / 100,
        "sharp_axis_round100": measure(sharp),
        "physical_R80_axis_round100": measure(rounded),
        "proxy_is_heat_loss_or_hydraulic_certificate": False,
    }


def exterior_evidence(specifications: list[dict]) -> dict:
    body_segments: list[tuple[tuple[int, int], tuple[int, int], str]] = []
    for specification in specifications:
        for start, end in specification["ranges"]:
            for segment_index in range(start, end):
                first = specification["points"][segment_index]
                second = specification["points"][segment_index + 1]
                body_segments.append((
                    ((first[0] - 3000) // 100, (first[1] - 3000) // 100),
                    ((second[0] - 3000) // 100, (second[1] - 3000) // 100),
                    specification["id"],
                ))

    def merge(intervals: list[tuple[int, int]]) -> list[list[int]]:
        ordered = sorted((min(a, b), max(a, b)) for a, b in intervals if a != b)
        result: list[list[int]] = []
        for start, end in ordered:
            if not result or start > result[-1][1]:
                result.append([start, end])
            else:
                result[-1][1] = max(result[-1][1], end)
        return result

    def horizontal(y: int) -> list[list[int]]:
        return merge([(a[0], b[0]) for a, b, _ in body_segments if a[1] == b[1] == y])

    def vertical(x: int) -> list[list[int]]:
        return merge([(a[1], b[1]) for a, b, _ in body_segments if a[0] == b[0] == x])

    def coverage(intervals: list[list[int]], required: tuple[int, int]) -> float:
        start, end = required
        covered = sum(max(0, min(high, end) - max(low, start)) for low, high in intervals)
        return 100 * covered / (end - start)

    south_lanes = []
    window_required = (52, 67)
    for lane, y in enumerate([162, 161, 160], start=1):
        intervals = horizontal(y)
        west_required = (47 + lane - 1, 76)
        east_required = (80, 92)
        south_lanes.append({
            "lane": lane, "axis_y_grid": y, "derived_body_intervals_grid": intervals,
            "west_required_interval_grid": list(west_required),
            "west_coverage_percent": coverage(intervals, west_required),
            "east_required_interval_grid": list(east_required),
            "east_coverage_percent": coverage(intervals, east_required),
            "window_id": "F1-WIN-03", "window_required_interval_grid": list(window_required),
            "window_coverage_percent": coverage(intervals, window_required),
        })
    west_lanes = []
    for lane, x in enumerate([47, 48, 49], start=1):
        intervals = vertical(x)
        required = (129, 163 - lane)
        west_lanes.append({
            "lane": lane, "axis_x_grid": x, "derived_body_intervals_grid": intervals,
            "required_interval_grid": list(required),
            "coverage_percent": coverage(intervals, required),
        })
    all_pass = all(
        item["west_coverage_percent"] >= 99.999 and
        item["east_coverage_percent"] >= 99.999 and
        item["window_coverage_percent"] >= 99.999
        for item in south_lanes
    ) and all(item["coverage_percent"] >= 99.999 for item in west_lanes)
    return {
        "classification": "EXACT_BODY_AXES_NOT_TRANSIT",
        "south_W011": {
            "true_interior_face_y_grid": 163,
            "axis_y_grid_by_lane": [162,161,160], "spacing_mm": 100,
            "wall_gap_W015_grid": [77.5,78.5], "derived_lanes": south_lanes,
        },
        "west_W012": {
            "true_interior_face_x_grid": 46,
            "axis_x_grid_by_lane": [47,48,49], "spacing_mm": 100,
            "derived_lanes": west_lanes,
        },
        "window_projection": {
            "window_id": "F1-WIN-03", "required_interval_grid": [52,67],
            "covered_by_all_three_south_lanes": all(item["window_coverage_percent"] >= 99.999 for item in south_lanes),
        },
        "three_lanes_are_heating_body_ranges": True, "all_partition_aware_gates_pass": all_pass,
    }


def transit_wall_audit(project: dict, specifications: list[dict]) -> dict:
    records = []
    failures = []
    for specification in specifications:
        body_indices = {
            segment_index
            for start, end in specification["ranges"]
            for segment_index in range(start, end)
        }
        for segment_index, (first, second) in enumerate(zip(specification["points"], specification["points"][1:])):
            segment = LineString([(first[0], first[1]), (second[0], second[1])])
            segment_horizontal = first[1] == second[1]
            segment_vertical = first[0] == second[0]
            for wall in project["walls"]:
                wall_start = wall["start"]
                wall_end = wall["end"]
                wall_line = LineString([
                    (wall_start["x_mm"], wall_start["y_mm"]),
                    (wall_end["x_mm"], wall_end["y_mm"]),
                ])
                solid = wall_line.buffer(wall["thickness_mm"] / 2, cap_style=2, join_style=2)
                if segment.intersection(solid).is_empty:
                    continue
                wall_horizontal = wall_start["y_mm"] == wall_end["y_mm"]
                wall_vertical = wall_start["x_mm"] == wall_end["x_mm"]
                is_body = segment_index in body_indices
                perpendicular = (wall_horizontal and segment_vertical) or (wall_vertical and segment_horizontal)
                record = {
                    "circuit_id": specification["id"], "segment_index": segment_index,
                    "wall_id": wall["id"], "role": "BODY" if is_body else "TRANSIT",
                    "perpendicular": perpendicular,
                    "terminal_segment": segment_index in {0, len(specification["points"]) - 2},
                }
                records.append(record)
                if is_body or not perpendicular:
                    failures.append(record)
    return {
        "method": "axis-aligned wall-solid intersection; every hit must be TRANSIT and perpendicular",
        "intersection_count": len(records), "records": records,
        "body_wall_hit_count": sum(item["role"] == "BODY" for item in records),
        "longitudinal_or_nonperpendicular_transit_count": sum(
            item["role"] == "TRANSIT" and not item["perpendicular"] for item in records
        ),
        "failures": failures, "pass": not failures,
    }


def run_editor(project_path: Path, output_path: Path, command: str, room_id: str | None = None) -> None:
    args = [
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", command, str(project_path), str(output_path),
    ]
    if room_id:
        args.append(room_id)
    completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError({
            "editor_command": args, "exit_code": completed.returncode,
            "stdout": completed.stdout, "stderr": completed.stderr,
        })


def build_project() -> tuple[dict, list[dict], list[str]]:
    project = json.loads(SOURCE_PROJECT.read_text(encoding="utf-8-sig"))
    source = copy.deepcopy(project)
    specifications = [c10_spec(), c11_spec()]
    for specification in specifications:
        specification["transitions"] = derive_transitions(specification)
    by_id = {item["id"]: item for item in specifications}
    for circuit in project["circuits"]:
        specification = by_id.get(circuit["id"])
        if specification is None:
            continue
        circuit.update({
            "name": specification["name"], "color": specification["color"],
            "ordered_points": [point_json(point) for point in specification["points"]],
            "completed": True, "collector_id": "K1",
            "supply_port_index": specification["ports"][0], "return_port_index": specification["ports"][1],
            "service_zone_id": "K1-TRANSIT-RESERVATION-D171",
            "concealed_service_length_mm": 0, "out_of_plane_length_mm": 0,
            "routing_layer": "HEATING_PLANE", "system_role": "FLOOR_HEATING_LOOP",
            "axis_elevation_mm": BODY_Z, "visible_on_plan": True,
            # R06 is the encompassing wet-zone polygon; each range still stays on one side of W015.
            "room_id": specification["room_id"],
            "heating_body_start_index": None, "heating_body_end_index": None,
            "heating_body_ranges": [
                {"start_index": start, "end_index": end} for start, end in specification["ranges"]
            ],
            "vertical_transitions": specification["transitions"],
        })
    project["training_metadata"] = {
        "label": "DRAFT",
        "author_intent": "D176 rebuilds the wet-area pair as nine owner-style body ranges and two continuous Point3 chains",
        "notes": "C10 uses primary transit z70 plus one local z135 overpass; C11 uses primary z135 plus one local z70 connector. Only transits cross walls. Every elevation change is an explicit R80 S-bend. No sleeves are used.",
    }
    current = {item["id"]: item for item in project["circuits"]}
    unchanged = []
    for circuit in source["circuits"]:
        if circuit["id"] in CHANGED_IDS:
            continue
        if current[circuit["id"]] != circuit:
            raise RuntimeError({"unexpected_circuit_change": circuit["id"]})
        unchanged.append(circuit["id"])
    return project, specifications, unchanged


def package_output() -> None:
    payloads = sorted(path for path in OUTPUT.iterdir() if path.is_file() and path.name != "artifact_manifest.json")
    dump(OUTPUT / "artifact_manifest.json", {
        "artifact_id": ARTIFACT_ID, "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in payloads],
    })
    with zipfile.ZipFile(PACKAGE, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in [*payloads, OUTPUT / "artifact_manifest.json"]:
            archive.write(path, path.name)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D176 is append-only")
    project, specifications, unchanged_ids = build_project()
    metrics = {item["id"]: route_metrics(item) for item in specifications}
    lengths = [item["rounded_physical_axis_length_mm"] for item in metrics.values()]
    spread = max(lengths) - min(lengths)
    if any(item["minimum_ordered_plan_segment_mm"] < 200 for item in metrics.values()):
        raise RuntimeError("D176 contains an ordered plan segment below 200 mm")
    if any(not 40_000 <= item["rounded_physical_axis_length_mm"] <= 80_000 for item in metrics.values()):
        raise RuntimeError({"D176_length_gate": lengths})
    if spread > 4_000:
        raise RuntimeError({"D176_spread_gate_mm": spread})

    coverage = wet_coverage(specifications)
    if coverage["physical_R80_axis_round100"]["served_percent"] < 93.89:
        raise RuntimeError({"wet_R80_coverage_regression": coverage})
    if coverage["physical_R80_axis_round100"]["maximum_sample_distance_mm"] > 253:
        raise RuntimeError({"wet_maximum_gap_regression": coverage})
    exterior = exterior_evidence(specifications)
    if not exterior["all_partition_aware_gates_pass"]:
        raise RuntimeError({"D176_exterior_or_window_gate": exterior})
    wall_audit = transit_wall_audit(project, specifications)
    if not wall_audit["pass"]:
        raise RuntimeError({"D176_wall_solid_gate": wall_audit["failures"]})

    (ROOT / "tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="homeaura_d176_preflight_", dir=ROOT / "tmp") as temporary:
        temporary_path = Path(temporary)
        preflight_project = temporary_path / "D176.homeaura.json"
        dump(preflight_project, project)
        run_editor(preflight_project, temporary_path / "diagnostics.json", "--export-diagnostics")
        diagnostics = json.loads((temporary_path / "diagnostics.json").read_text(encoding="utf-8-sig"))

    diagnostic_gate = {}
    for item in diagnostics["circuits"]:
        if item["circuit_id"] not in CHANGED_IDS:
            continue
        diagnostic_gate[item["circuit_id"]] = {
            key: item[key] for key in [
                "topology_pass", "engineering_pass", "rounded_axis_length_mm",
                "vertical_geometry_materialized", "vertical_transition_count",
                "bend_radius_violation_count", "self_intersections",
                "self_surface_clearance_violations", "inter_circuit_intersections",
                "inter_circuit_surface_clearance_violations", "heating_body_wall_intrusions",
                "heating_body_inside_assigned_room", "start_at_collector", "end_at_collector",
                "minimum_inter_circuit_surface_clearance_mm",
            ]
        }
    failures = {
        circuit_id: item for circuit_id, item in diagnostic_gate.items()
        if not item["topology_pass"] or not item["engineering_pass"] or
        not item["vertical_geometry_materialized"] or item["bend_radius_violation_count"] or
        item["self_intersections"] or item["self_surface_clearance_violations"] or
        item["inter_circuit_intersections"] or item["inter_circuit_surface_clearance_violations"] or
        item["heating_body_wall_intrusions"] or not item["heating_body_inside_assigned_room"] or
        not item["start_at_collector"] or not item["end_at_collector"]
    }
    if failures:
        raise RuntimeError({"CSharp_D176_gate": failures})
    for circuit_id, item in diagnostic_gate.items():
        if abs(item["rounded_axis_length_mm"] - metrics[circuit_id]["rounded_physical_axis_length_mm"]) > 0.003:
            raise RuntimeError({"analytic_CSharp_length_disagreement": circuit_id, "CSharp": item["rounded_axis_length_mm"], "analytic": metrics[circuit_id]["rounded_physical_axis_length_mm"]})

    report = {
        "schema": "homeaura.floor1.wet-pair.report.v1", "artifact_id": ARTIFACT_ID,
        "body_order": {"F1-D171-C10": ["A","B_REVERSED","RET_REVERSED","C"],
                       "F1-D171-C11": ["M","E","H_REVERSED","I_REVERSED","G"]},
        "exact_body_sources_grid": {item["id"]: item["body_sources"] for item in specifications},
        "route_metrics": metrics,
        "pair_rounded_length_spread_mm": spread,
        "body_total_rounded_length_spread_mm": abs(metrics["F1-D171-C10"]["body_total_rounded_length_mm"] - metrics["F1-D171-C11"]["body_total_rounded_length_mm"]),
        "wet_coverage": coverage, "exterior_3x100": exterior,
        "wall_solid_transit_audit": wall_audit,
        "wall_solid_claim_boundaries": {
            "piecewise_collinear_crossings": "A few W009 crossings are split across consecutive collinear TRANSIT segments; together they cross the full 200 mm wall solid perpendicularly.",
            "terminal_grid_exception": "C10 final TRANSIT terminates on the W025 collector-wall axis; it is a bounded terminal-grid endpoint, not heating body or fabricated Eurocone micro-stub.",
        },
        "CSharp_diagnostic_gate": diagnostic_gate,
    }
    contract = {
        "schema": "homeaura.floor1.wet_pair.v1", "artifact_id": ARTIFACT_ID,
        "status": "SIX_POINT3_FLOOR_ROUTES_PASS_COLLECTOR_TERMINALS_REWORK",
        "append_only": True,
        "source_D175_project_sha256": sha(SOURCE_PROJECT),
        "source_D175_contract_sha256": sha(SOURCE_CONTRACT),
        "changed_circuit_ids": sorted(CHANGED_IDS), "unchanged_circuit_ids": unchanged_ids,
        "unchanged_non_wet_circuit_records_preserved": True,
        "route_metrics": metrics, "pair_rounded_length_spread_mm": spread,
        "wet_coverage": coverage, "exterior_3x100": exterior,
        "wall_solid_transit_audit": wall_audit,
        "wall_solid_claim_boundaries": {
            "piecewise_collinear_crossings": "W009 may be crossed by consecutive collinear TRANSIT records; no longitudinal wall run is present.",
            "terminal_grid_exception": "The C10 return reaches the W025 centreline only as a bounded collector terminal; Eurocone micro-stub geometry remains unmaterialized.",
        },
        "CSharp_diagnostic_gate": diagnostic_gate,
        "layer_contract": {
            "heating_axis_elevation_mm": BODY_Z,
            "C10_primary_transit_axis_elevation_mm": C10_TRANSIT_Z,
            "C10_local_overpass_axis_elevation_mm": C11_TRANSIT_Z,
            "C11_primary_transit_axis_elevation_mm": C11_TRANSIT_Z,
            "C11_local_low_connector_axis_elevation_mm": C10_TRANSIT_Z,
            "pipe_outer_diameter_mm": PIPE_OD_MM, "minimum_surface_clearance_mm": 5,
            "z70_to_body_surface_clearance_mm": BODY_Z - C10_TRANSIT_Z - PIPE_OD_MM,
            "z135_to_body_surface_clearance_mm": C11_TRANSIT_Z - BODY_Z - PIPE_OD_MM,
            "all_vertical_changes_materialized_as_R80_S_bends": True, "sleeves_used": False,
        },
        "collector_terminal_contract": {
            "collector_id": "K1", "assigned_ports": {"F1-D171-C10":[18,19],"F1-D171-C11":[20,21]},
            "chain_endpoints_are_explicit": True,
            "micro_stubs_from_terminal_grid_to_eurocone_are_not_fabrication_geometry": True,
        },
        "complete_K1_route_count": 0, "collector_continuous_route_count": 0,
        "bounded_terminal_grid_route_count": 6, "materialized_floor_plane_route_count": 6,
        "whole_floor_R80_violation_count_in_unchanged_routes": 12,
        "installation_ready": False,
        "remaining_blockers": [
            "C03 and C05-C09 retain inherited R80 debt",
            "hydraulic sizing and flow settings are not evaluated",
            "collector-to-grid Eurocone micro-stubs are not fabrication polylines",
        ],
        "next_block": "REBUILD_NEXT_WORST_FIRST_FLOOR_ROOM_WITH_OWNER_COUNTERFLOW_GRAMMAR",
    }

    OUTPUT.mkdir(parents=True)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    project_path = OUTPUT / "HomeAura_Floor1_WetPair_D176.homeaura.json"
    dump(project_path, project)
    dump(OUTPUT / "floor1_wet_pair_contract.json", contract)
    dump(OUTPUT / "wet_pair_report.json", report)
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID, "result": contract["status"],
        "complete_K1_route_count": 0, "collector_continuous_route_count": 0,
        "bounded_terminal_grid_route_count": 6, "materialized_floor_plane_route_count": 6,
        "pair_rounded_length_spread_mm": spread,
        "wet_R80_coverage_percent": coverage["physical_R80_axis_round100"]["served_percent"],
        "changed_body_wall_hits": 0, "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D176 · сбалансированная пара влажной зоны\n\n"
        "C10 и C11 заново собраны как две непрерывные Point3-цепи. Девять тел укладки сохраняют три трубы "
        "с шагом 100 мм вдоль южной и западной внешних стен; стены пересекают только участки TRANSIT. "
        "Основной транзит C10 проходит на z70 с локальным обходом z135; основной транзит C11 — на z135 "
        "с локальным соединителем z70. Тела находятся на z108; каждый переход задан S-изгибом R80.\n\n"
        f"Физические длины: C10={metrics['F1-D171-C10']['rounded_physical_axis_length_mm']/1000:.3f} м, "
        f"C11={metrics['F1-D171-C11']['rounded_physical_axis_length_mm']/1000:.3f} м, "
        f"разброс={spread/1000:.3f} м. Покрытие доступной влажной зоны с R80="
        f"{coverage['physical_R80_axis_round100']['served_percent']:.3f}%.\n\n"
        "Полностью коллекторно-непрерывных маршрутов по-прежнему 0: микроподводки Eurocone не материализованы. "
        "Конечная точка C10 доходит только до оси коллекторной стены W025; это граница расчётной трассы, а не тело укладки. "
        "D176 не является монтажным или гидравлическим сертификатом.\n",
        encoding="utf-8",
    )
    run_editor(project_path, OUTPUT / "engineering_diagnostics.json", "--export-diagnostics")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D176_Editor_View.png", "--export-png")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D176_Clean_View.png", "--export-png-clean")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D176_WetPair_Zoom.png", "--export-room-png", "F1-R06")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D176_WetPair_Clean_Zoom.png", "--export-room-png-clean", "F1-R06")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D176_WetPair_3D_Debug.png", "--export-room-png-diagnostics", "F1-R06")
    package_output()
    print(json.dumps({
        "artifact": ARTIFACT_ID, "project": str(project_path), "package": str(PACKAGE),
        "package_sha256": sha(PACKAGE),
        "rounded_lengths_mm": {key: value["rounded_physical_axis_length_mm"] for key, value in metrics.items()},
        "pair_spread_mm": spread,
        "wet_R80_coverage_percent": coverage["physical_R80_axis_round100"]["served_percent"],
        "complete_K1_route_count": 0, "bounded_terminal_grid_route_count": 6,
        "installation_ready": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

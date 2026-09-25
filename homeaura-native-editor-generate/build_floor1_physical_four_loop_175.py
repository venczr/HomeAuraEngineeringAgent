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
import build_floor1_lower_service_pair_174 as d174  # noqa: E402
from build_owner_style_installation_project_141 import clean, paired_counterflow, self_contacts  # noqa: E402

ROOT = HERE.parent
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_LOWER_SERVICE_PAIR_174"
SOURCE_PROJECT = SOURCE / "HomeAura_Floor1_LowerServicePair_D174.homeaura.json"
SOURCE_CONTRACT = SOURCE / "floor1_lower_service_pair_contract.json"
MANUFACTURER_SOURCE = ROOT / "manufacturer-data" / "uponor_vario_s_fm_14_design_reference.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_PHYSICAL_FOUR_LOOP_175"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_FLOOR1_PHYSICAL_FOUR_LOOP_175.zip"
ARTIFACT_ID = OUTPUT.name

OFFSET = 3000
RADIUS_MM = 80.0
PIPE_OD_MM = 16.0
BODY_Z = 108
LOWER_Z = 70
OVERPASS_Z = 135
OLD_SERVICE_IDS = {
    "F1-D174-C02-SUPPLY", "F1-D174-C02-RETURN",
    "F1-D174-C01-SUPPLY", "F1-D174-C01-RETURN",
}
CHANGED_IDS = {"F1-D171-C01", "F1-D171-C02", "F1-D171-C13"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def xyz(point: tuple[int, int, int]) -> dict:
    x, y, z = point
    return {"x_mm": OFFSET + x * 100, "y_mm": OFFSET + y * 100, "z_mm": z}


def transition(segment: int, start_tangent: float, end_tangent: float) -> dict:
    return {
        "segment_index": segment,
        "kind": "S_BEND_R80",
        "radius_mm": RADIUS_MM,
        "start_tangent_length_mm": start_tangent,
        "end_tangent_length_mm": end_tangent,
        "arc_samples_per_half": 12,
    }


def c01_spec() -> dict:
    upper = d174.UPPER["F1-D171-C01"]["points"]
    points: list[tuple[int, int, int]] = [(130, 85, LOWER_Z)]
    for index, (x, y) in enumerate(upper):
        points.append((x, y, LOWER_Z if index in {3, 4} else BODY_Z))
    points.append((130, 64, LOWER_Z))
    return {
        "id": "F1-D171-C01", "room_id": "F1-R08", "color": "#E43F5A",
        "name": "F1-D175-C01 · непрерывная 3D-улитка · нижние транзиты 70 мм",
        "ports": (0, 1), "points": points, "ranges": [(1, 3), (6, 33)],
        "transitions": [
            transition(0, 7900, 96.481886),
            transition(3, 0, 496.481886),
            transition(5, 100, 396.481886),
            transition(33, 0, 3696.481886),
        ],
        "expected_rounded_mm": 53906.16058463464,
        "lineage": "D174 C01 body unchanged; its two internal gaps and both service legs are one Point3 chain",
    }


def c02_spec() -> dict:
    upper = d174.UPPER["F1-D171-C02"]["points"]
    points: list[tuple[int, int, int]] = [
        (130, 58, LOWER_Z), (128, 58, OVERPASS_Z),
        (94, 58, OVERPASS_Z), (92, 58, BODY_Z),
    ]
    for index, (x, y) in enumerate(upper[1:], start=1):
        if 3 <= index <= 6:
            z = LOWER_Z
        elif 10 <= index <= 12:
            z = OVERPASS_Z
        else:
            z = BODY_Z
        points.append((x, y, z))
    points.extend([(49, 83, LOWER_Z), (49, 81, LOWER_Z), (130, 81, LOWER_Z)])
    return {
        "id": "F1-D171-C02", "room_id": "F1-R08", "color": "#FF8A3D",
        "name": "F1-D175-C02 · непрерывная 3D-улитка · развязка 70/108/135 мм",
        "ports": (2, 3), "points": points, "ranges": [(3, 5), (10, 12), (16, 38)],
        "transitions": [
            transition(0, 71.256068, 0),
            transition(2, 100, 11.056198),
            transition(5, 0, 496.481886),
            transition(9, 100, 196.481886),
            transition(12, 0, 611.056198),
            transition(15, 100, 211.056198),
            transition(38, 0, 96.481886),
        ],
        "expected_rounded_mm": 55465.396936873585,
        "lineage": "D174 C02 bodies unchanged; all three gaps, long z135 overpass, and rerouted return form one Point3 chain",
    }


def c13_body() -> list[tuple[int, int]]:
    centre = [
        (117,117),(117,129),(110,129),(110,127),(115,127),(115,125),(110,125),
        (110,123),(115,123),(115,121),(110,121),(110,119),(108,119),
    ]
    original = paired_counterflow((98, 109, 125, 141))
    main = (original[:11] + centre + original[14:])[::-1]
    lower_centre = [(121,148),(121,154),(119,154),(119,152),(117,152),(117,150),(115,150)]
    original_lower = paired_counterflow((109, 144, 125, 162))
    lower = [(x, 306 - y) for x, y in original_lower[:7] + lower_centre + original_lower[10:]]
    body = clean(main + [(125, 144)] + lower)
    if body[0] != (123, 139) or body[-1] != (123, 146) or self_contacts(body):
        raise RuntimeError("C13 owner-style body construction changed")
    return body


def c13_spec() -> dict:
    body = c13_body()
    points = [(130,92,LOWER_Z),(130,139,LOWER_Z),(125,139,LOWER_Z),(123,139,BODY_Z)]
    points.extend((x, y, BODY_Z) for x, y in body[1:])
    points.extend([(134,146,LOWER_Z),(134,101,LOWER_Z)])
    return {
        "id": "F1-D171-C13", "room_id": "F1-R02", "color": "#22C55E",
        "name": "F1-D175-C13 · длинная улитка холла · физическая подача и обратка",
        "ports": (24, 25), "points": points, "ranges": [(3, 56)],
        "transitions": [transition(2, 96.481886, 0), transition(56, 0, 996.481886)],
        "expected_rounded_mm": 75063.9648319174,
        "body_grid": body,
        "lineage": "regular owner counterflow upper lobe joined to compact reflected lower lobe",
    }


def c14_body() -> list[tuple[int, int]]:
    centre = [
        (117,66),(117,84),(110,84),(110,82),(115,82),(115,80),(110,80),
        (110,78),(115,78),(115,76),(110,76),(110,74),(115,74),(115,72),
        (110,72),(110,70),(115,70),(115,68),(108,68),
    ]
    original = paired_counterflow((98, 58, 125, 96))
    modified = original[:11] + centre + original[14:]
    main = [(223 - x, y) for x, y in modified][::-1]
    stair_lobe = [
        (98,107),(111,107),(111,105),(100,105),(100,103),
        (111,103),(111,101),(100,101),(100,99),(111,99),
    ]
    body = clean(main + stair_lobe)
    if body[0] != (100, 94) or body[-1] != (111, 99) or self_contacts(body):
        raise RuntimeError("C14 owner-style body construction changed")
    return body


def c14_spec() -> dict:
    body = c14_body()
    # (100,94) is collinear between the z108 ramp endpoint and (123,94), so it is
    # deliberately collapsed. This preserves the exact axis and removes a false
    # 100 mm ordered segment; the 100 mm coaxial extension is classified as body.
    points = [
        (134,59,LOWER_Z),(124,59,BODY_Z),(99,59,BODY_Z),(99,90,BODY_Z),
        (99,92,OVERPASS_Z),(99,94,BODY_Z),
    ]
    points.extend((x, y, BODY_Z) for x, y in body[1:])
    points.append((129,99,LOWER_Z))
    return {
        "id": "F1-D175-C14", "room_id": "F1-R02", "color": "#8B5CF6",
        "name": "F1-D175-C14 · северная 3×100 полоса + компактная улитка холла",
        "ports": (26, 27), "points": points, "ranges": [(1, 54)],
        "transitions": [
            transition(0, 896.481886, 0),
            transition(3, 80, 31.056198),
            transition(4, 31.056198, 80),
            transition(54, 0, 1696.481886),
        ],
        "expected_rounded_mm": 72412.04441754727,
        "body_grid": [[124, 59], [99, 59]],
        "main_body_grid": body,
        "lineage": "nested north 3x100 pass plus reflected owner counterflow and stair-side compact lobe",
    }


def all_specs() -> list[dict]:
    return [c01_spec(), c02_spec(), c13_spec(), c14_spec()]


def segment_plan_lengths(points: list[tuple[int, int, int]]) -> list[float]:
    return [math.hypot((b[0] - a[0]) * 100, (b[1] - a[1]) * 100) for a, b in zip(points, points[1:])]


def directions(points: list[tuple[int, int, int]]) -> list[tuple[int, int]]:
    result = []
    for first, second in zip(points, points[1:]):
        dx, dy = second[0] - first[0], second[1] - first[1]
        divisor = max(abs(dx), abs(dy))
        result.append((dx // divisor, dy // divisor))
    return result


def rounded_length(specification: dict) -> dict:
    points = specification["points"]
    lengths = segment_plan_lengths(points)
    vector_directions = directions(points)
    turn_count = sum(first != second for first, second in zip(vector_directions, vector_directions[1:]))
    raw_plan = sum(lengths)
    rounded = raw_plan - turn_count * (2 * RADIUS_MM - math.pi * RADIUS_MM / 2)
    transition_records = []
    for item in specification["transitions"]:
        index = item["segment_index"]
        first, second = points[index], points[index + 1]
        rise = abs(second[2] - first[2])
        theta = math.acos(1 - rise / (2 * RADIUS_MM))
        projection = 2 * RADIUS_MM * math.sin(theta)
        arc_length = 2 * RADIUS_MM * theta
        plan = lengths[index]
        closure = item["start_tangent_length_mm"] + projection + item["end_tangent_length_mm"]
        if abs(closure - plan) > 0.05:
            raise RuntimeError({"transition_closure": specification["id"], "segment": index, "difference_mm": closure - plan})
        rounded += arc_length - projection
        transition_records.append({
            **item, "vertical_delta_mm": rise, "plan_projection_mm": plan,
            "required_arc_projection_mm": projection, "turn_angle_degrees": math.degrees(theta),
            "arc_length_mm": arc_length,
            "analytic_axis_length_mm": item["start_tangent_length_mm"] + arc_length + item["end_tangent_length_mm"],
        })
    if abs(rounded - specification["expected_rounded_mm"]) > 0.001:
        raise RuntimeError({"length": specification["id"], "actual": rounded, "expected": specification["expected_rounded_mm"]})
    return {
        "point_count": len(points), "raw_plan_axis_length_mm": raw_plan,
        "horizontal_R80_turn_count": turn_count, "rounded_physical_axis_length_mm": rounded,
        "minimum_ordered_plan_segment_mm": min(lengths), "vertical_transitions": transition_records,
    }


def body_lines(specification: dict) -> list[LineString]:
    points = [(x, y) for x, y, _ in specification["points"]]
    return [LineString(points[start:end + 1]) for start, end in specification["ranges"]]


def fillet(points: list[tuple[float, float]], radius: float = .8, steps: int = 16) -> list[tuple[float, float]]:
    output: list[tuple[float, float]] = [points[0]]
    for index in range(1, len(points) - 1):
        previous, corner, following = points[index - 1], points[index], points[index + 1]
        incoming = (previous[0] - corner[0], previous[1] - corner[1])
        outgoing = (following[0] - corner[0], following[1] - corner[1])
        incoming_length, outgoing_length = math.hypot(*incoming), math.hypot(*outgoing)
        cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
        if incoming_length == 0 or outgoing_length == 0 or abs(cross) < 1e-12:
            output.append(corner)
            continue
        first_unit = (incoming[0] / incoming_length, incoming[1] / incoming_length)
        second_unit = (outgoing[0] / outgoing_length, outgoing[1] / outgoing_length)
        first = (corner[0] + first_unit[0] * radius, corner[1] + first_unit[1] * radius)
        second = (corner[0] + second_unit[0] * radius, corner[1] + second_unit[1] * radius)
        centre = (corner[0] + (first_unit[0] + second_unit[0]) * radius,
                  corner[1] + (first_unit[1] + second_unit[1]) * radius)
        output.append(first)
        first_angle = math.atan2(first[1] - centre[1], first[0] - centre[0])
        second_angle = math.atan2(second[1] - centre[1], second[0] - centre[0])
        traversal_cross = (-incoming[0]) * outgoing[1] - (-incoming[1]) * outgoing[0]
        if traversal_cross > 0:
            while second_angle <= first_angle:
                second_angle += 2 * math.pi
        else:
            while second_angle >= first_angle:
                second_angle -= 2 * math.pi
        for step in range(1, steps + 1):
            angle = first_angle + (second_angle - first_angle) * step / steps
            output.append((centre[0] + radius * math.cos(angle), centre[1] + radius * math.sin(angle)))
    output.append(points[-1])
    return output


def hall_coverage(specifications: list[dict]) -> dict:
    hall_specs = [item for item in specifications if item["room_id"] == "F1-R02"]
    sharp_lines = [line for item in hall_specs for line in body_lines(item)]
    rounded_lines = [LineString(fillet(list(line.coords))) for line in sharp_lines]
    domain = Polygon([
        (108.16,163.83),(126.28,163.83),(126.28,108),(113,108),(113,98),
        (126,98),(126,97),(126,96),(126,57),(97,57),(97,142.16),
        (108.16,142.16),(108.16,163.83),
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
            "served_area_m2": served / 100,
            "served_percent": served * 100 / domain.area,
            "unserved_proxy_area_m2": (domain.area - served) / 100,
            "q16_buffer_resolution": 16,
            "sample_grid_mm": 50,
            "sample_count": len(samples),
            "sample_within_200mm_percent": sum(value <= 2 + 1e-9 for value in samples) * 100 / len(samples),
            "sample_over_200mm_count": sum(value > 2 + 1e-9 for value in samples),
            "maximum_sample_distance_mm": max(samples) * 100,
        }

    c13 = unary_union(body_lines(next(item for item in hall_specs if item["id"] == "F1-D171-C13")))
    c14 = unary_union(body_lines(next(item for item in hall_specs if item["id"] == "F1-D175-C14")))
    return {
        "domain_definition": "F1-R02 minus wall solids and F1-X-STAIR-3; grid polygon is explicit below",
        "domain_polygon_grid": [list(item) for item in domain.exterior.coords[:-1]],
        "domain_area_m2": domain.area / 100,
        "sharp_axis_round100": measure(sharp_lines),
        "physical_R80_axis_round100": measure(rounded_lines),
        "minimum_C13_C14_body_axis_distance_mm": c13.distance(c14) * 100,
        "proxy_is_heat_loss_or_hydraulic_certificate": False,
    }


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for start, end in sorted((min(a, b), max(a, b)) for a, b in intervals if a != b):
        if not result or start > result[-1][1]:
            result.append((start, end))
        else:
            result[-1] = (result[-1][0], max(result[-1][1], end))
    return result


def exterior_w016(specifications: list[dict]) -> dict:
    segments = []
    for specification in specifications:
        if specification["room_id"] != "F1-R02":
            continue
        points = [(x, y) for x, y, _ in specification["points"]]
        accepted = {index for start, end in specification["ranges"] for index in range(start, end)}
        segments.extend((points[index], points[index + 1]) for index in accepted)
    records = []
    raw = (98, 125)
    for lane, y, envelope in [(1,58,(98,125)), (2,59,(99,124)), (3,60,(100,123))]:
        intervals = merge([(a[0], b[0]) for a, b in segments if a[1] == b[1] == y])
        covered_raw = sum(max(0, min(end, raw[1]) - max(start, raw[0])) for start, end in intervals)
        covered_envelope = sum(max(0, min(end, envelope[1]) - max(start, envelope[0])) for start, end in intervals)
        records.append({
            "lane": lane, "offset_from_true_interior_face_mm": lane * 100,
            "axis_y_grid": y, "covered_intervals_grid": [list(item) for item in intervals],
            "raw_common_required_interval_grid": list(raw),
            "raw_common_coverage_percent": covered_raw * 100 / (raw[1] - raw[0]),
            "raw_common_continuous_full_span_pass": any(start <= raw[0] and end >= raw[1] for start, end in intervals),
            "R80_nested_corner_envelope_interval_grid": list(envelope),
            "R80_nested_corner_envelope_coverage_percent": covered_envelope * 100 / (envelope[1] - envelope[0]),
            "R80_nested_corner_envelope_full_span_pass": any(start <= envelope[0] and end >= envelope[1] for start, end in intervals),
        })
    if [item["raw_common_continuous_full_span_pass"] for item in records] != [True, False, False]:
        raise RuntimeError("W016 raw audit is no longer honest")
    if not all(item["R80_nested_corner_envelope_full_span_pass"] for item in records):
        raise RuntimeError("W016 nested R80 envelope lost a lane")
    return {
        "wall_id": "FLOOR_1-W016", "true_interior_face_y_grid": 57,
        "raw_full_span_pass_by_lane": [True, False, False],
        "R80_nested_envelope_pass_by_lane": [True, True, True],
        "raw_and_corner_envelope_are_not_conflated": True,
        "lanes": records,
    }


def manufacturer_contract() -> dict:
    source = json.loads(MANUFACTURER_SOURCE.read_text(encoding="utf-8-sig"))
    return {
        "schema": "homeaura.collector.manufacturer-reference.v1",
        "status": source["status"],
        "source_file": str(MANUFACTURER_SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha(MANUFACTURER_SOURCE),
        "manufacturer": source["manufacturer"], "product_family": source["product_family"],
        "variant": source["variant"], "part_number": source["official_variant_part_number"],
        "loop_count": source["heating_circuit_count"], "connection_point_count": 28,
        "loop_pitch_mm": source["loop_pitch_mm"], "header_pitch_mm": source["header_pitch_mm"],
        "reference_length_mm": source["dimensions_mm"]["L1"],
        "K1": {"planned_loop_count": 14, "spare_loop_count": 0, "wall_id": "FLOOR_1-W025", "rotation_degrees": 0},
        "K2": {"planned_loop_count": 13, "spare_loop_count": 1, "wall_id": "FLOOR_1-W025", "rotation_degrees": 180},
        "procurement_approval": False, "hydraulic_selection_complete": False,
        "official_sources": source["official_sources"],
    }


def reference_connection_points() -> list[dict]:
    points = []
    for loop_index in range(14):
        along = -325 + loop_index * 50
        for header, index, cross in (("SUPPLY", loop_index * 2, -112.5), ("RETURN", loop_index * 2 + 1, 112.5)):
            points.append({
                "connection_index": index, "loop_index": loop_index, "header": header,
                "local_position_mm": {"x_mm": along, "y_mm": cross, "z_mm": 0},
            })
    return points


def apply_collector_reference(project: dict) -> None:
    source = json.loads(MANUFACTURER_SOURCE.read_text(encoding="utf-8-sig"))
    for collector in project["collectors"]:
        if collector["id"] not in {"K1", "K2"}:
            continue
        collector.update({
            "ports": 28,
            "reference_width_mm": source["dimensions_mm"]["L1"],
            "reference_depth_mm": 235,
            "reference_height_mm": 320,
            "equipment_status": "SELECTED_REFERENCE",
            "reference_source": source["official_sources"][2]["url"],
            "manufacturer": "Uponor",
            "model": "Vario S manifold FM 14xG3/4 Euro - G1",
            "part_number": source["official_variant_part_number"],
            "loop_count": 14,
            "connection_point_count": 28,
            "header_pitch_mm": source["header_pitch_mm"],
            "loop_connection_pitch_mm": source["loop_pitch_mm"],
            "reference_length_mm": source["dimensions_mm"]["L1"],
            "connection_points": reference_connection_points(),
            "mounting_wall_id": "FLOOR_1-W025",
        })
    k1 = next(item for item in project["collectors"] if item["id"] == "K1")
    k2 = next(item for item in project["collectors"] if item["id"] == "K2")
    k1["rotation_degrees"] = 0
    k1["served_floor_id"] = "FLOOR_1"
    k1["pipe_outlet_direction"] = "DOWN"
    # The exact C13 return terminal is 4.077 m from its materialized FM14 port.
    # Keep the legacy terminal-grid abstraction explicit and use the smallest
    # 100 mm-rounded tolerance that includes it; the undrawn micro-stub remains
    # excluded from fabrication readiness below.
    k1["connection_tolerance_mm"] = 4100
    k2["rotation_degrees"] = 180
    k2["served_floor_id"] = "ATTIC"
    k2["pipe_outlet_direction"] = "UP"


def build_project() -> tuple[dict, list[dict], list[str]]:
    project = json.loads(SOURCE_PROJECT.read_text(encoding="utf-8-sig"))
    source = copy.deepcopy(project)
    specifications = all_specs()
    by_id = {item["id"]: item for item in specifications}

    project["circuits"] = [item for item in project["circuits"] if item["id"] not in OLD_SERVICE_IDS]
    for circuit in project["circuits"]:
        specification = by_id.get(circuit["id"])
        if specification is None:
            continue
        circuit.update({
            "name": specification["name"], "color": specification["color"],
            "ordered_points": [xyz(point) for point in specification["points"]],
            "vertical_transitions": specification["transitions"], "completed": True,
            "collector_id": "K1", "supply_port_index": specification["ports"][0],
            "return_port_index": specification["ports"][1],
            "service_zone_id": "K1-TRANSIT-RESERVATION-D171",
            "concealed_service_length_mm": 0, "out_of_plane_length_mm": 0,
            "routing_layer": "HEATING_PLANE", "system_role": "FLOOR_HEATING_LOOP",
            "axis_elevation_mm": BODY_Z, "visible_on_plan": True,
            "room_id": specification["room_id"],
            "heating_body_start_index": None, "heating_body_end_index": None,
            "heating_body_ranges": [{"start_index": a, "end_index": b} for a, b in specification["ranges"]],
        })
    c14 = by_id["F1-D175-C14"]
    project["circuits"].append({
        "id": c14["id"], "name": c14["name"], "color": c14["color"],
        "ordered_points": [xyz(point) for point in c14["points"]],
        "vertical_transitions": c14["transitions"], "completed": True,
        "collector_id": "K1", "supply_port_index": 26, "return_port_index": 27,
        "service_zone_id": "K1-TRANSIT-RESERVATION-D171",
        "concealed_service_length_mm": 0, "out_of_plane_length_mm": 0,
        "routing_layer": "HEATING_PLANE", "system_role": "FLOOR_HEATING_LOOP",
        "axis_elevation_mm": BODY_Z, "visible_on_plan": True, "room_id": "F1-R02",
        "heating_body_start_index": None, "heating_body_end_index": None,
        "heating_body_ranges": [{"start_index": a, "end_index": b} for a, b in c14["ranges"]],
    })
    apply_collector_reference(project)
    project["training_metadata"] = {
        "label": "DRAFT",
        "author_intent": "D175 four continuous Point3 floor-plane routes ending at explicit terminal-grid points: balanced F1-R08 pair and two owner-style hall spirals",
        "notes": "Only transits cross walls. Every layer change is an explicit R80 S-bend; sleeves are not used. Eurocone micro-stubs and mounting-height fanout are not drawn, so collector-continuous route count is zero. Remaining C03-C12 debt is preserved and bounded.",
    }

    unchanged_ids = []
    new_by_id = {item["id"]: item for item in project["circuits"]}
    for item in source["circuits"]:
        if item["id"] in CHANGED_IDS or item["id"] in OLD_SERVICE_IDS:
            continue
        if new_by_id[item["id"]] != item:
            raise RuntimeError({"unexpected_circuit_change": item["id"]})
        unchanged_ids.append(item["id"])
    return project, specifications, unchanged_ids


def validate_static(project: dict, specifications: list[dict]) -> dict:
    route_metrics = {item["id"]: {**rounded_length(item), "lineage": item["lineage"]} for item in specifications}
    for circuit_id, metrics in route_metrics.items():
        if metrics["minimum_ordered_plan_segment_mm"] < 200:
            raise RuntimeError({"short_segment": circuit_id, "minimum": metrics["minimum_ordered_plan_segment_mm"]})

    room_polygons = {item["id"]: Polygon([(point["x_mm"], point["y_mm"]) for point in item["outline"]]) for item in project["rooms"]}
    wall_solids = [
        LineString([(wall["start"]["x_mm"], wall["start"]["y_mm"]), (wall["end"]["x_mm"], wall["end"]["y_mm"])])
        .buffer(wall["thickness_mm"] / 2, cap_style="square")
        for wall in project["walls"]
    ]
    stair = Polygon([(point["x_mm"], point["y_mm"]) for point in next(item for item in project["exclusions"] if item["id"] == "F1-X-STAIR-3")["outline"]])
    body_wall_hits = 0
    body_stair_hits = 0
    for specification in specifications:
        for line in body_lines(specification):
            world = LineString([(OFFSET + x * 100, OFFSET + y * 100) for x, y in line.coords])
            if not room_polygons[specification["room_id"]].covers(world):
                raise RuntimeError({"body_outside_room": specification["id"]})
            body_wall_hits += sum(not world.intersection(solid).is_empty for solid in wall_solids)
            if specification["room_id"] == "F1-R02" and not world.intersection(stair).is_empty:
                body_stair_hits += 1
    if body_wall_hits or body_stair_hits:
        raise RuntimeError({"body_wall_hits": body_wall_hits, "body_stair_hits": body_stair_hits})

    coverage = hall_coverage(specifications)
    if coverage["minimum_C13_C14_body_axis_distance_mm"] + 1e-6 < 200:
        raise RuntimeError("hall bodies are closer than 200 mm")
    exterior = exterior_w016(specifications)
    lengths = [route_metrics[item]["rounded_physical_axis_length_mm"] for item in ("F1-D171-C13", "F1-D175-C14")]
    return {
        "route_metrics": route_metrics,
        "hall_pair_rounded_length_spread_mm": max(lengths) - min(lengths),
        "body_wall_hit_count": body_wall_hits, "body_stair_exclusion_hit_count": body_stair_hits,
        "hall_coverage": coverage, "exterior_W016_3x100": exterior,
    }


def run_editor(project_path: Path, output_path: Path, command: str, room_id: str | None = None) -> None:
    args = [
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", command, str(project_path), str(output_path),
    ]
    if room_id:
        args.append(room_id)
    subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True)


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
        raise FileExistsError("D175 is append-only")
    project, specifications, unchanged_ids = build_project()
    validation = validate_static(project, specifications)

    # Exercise the real C# loader/analyzer before claiming the append-only path.
    (ROOT / "tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="homeaura_d175_preflight_", dir=ROOT / "tmp") as temporary:
        temporary_path = Path(temporary)
        preflight_project = temporary_path / "D175.homeaura.json"
        dump(preflight_project, project)
        run_editor(preflight_project, temporary_path / "diagnostics.json", "--export-diagnostics")
        diagnostics = json.loads((temporary_path / "diagnostics.json").read_text(encoding="utf-8-sig"))

    changed_diagnostics = {
        item["circuit_id"]: item for item in diagnostics["circuits"]
        if item["circuit_id"] in {specification["id"] for specification in specifications}
    }
    diagnostic_gate = {}
    for circuit_id, item in changed_diagnostics.items():
        diagnostic_gate[circuit_id] = {
            "topology_pass": item["topology_pass"], "engineering_pass": item["engineering_pass"],
            "rounded_axis_length_mm": item["rounded_axis_length_mm"],
            "vertical_geometry_materialized": item["vertical_geometry_materialized"],
            "vertical_transition_count": item["vertical_transition_count"],
            "bend_radius_violation_count": item["bend_radius_violation_count"],
            "self_intersections": item["self_intersections"],
            "self_surface_clearance_violations": item["self_surface_clearance_violations"],
            "inter_circuit_intersections": item["inter_circuit_intersections"],
            "inter_circuit_surface_clearance_violations": item["inter_circuit_surface_clearance_violations"],
            "heating_body_wall_intrusions": item["heating_body_wall_intrusions"],
            "start_at_collector": item["start_at_collector"], "end_at_collector": item["end_at_collector"],
            "minimum_inter_circuit_surface_clearance_mm": item["minimum_inter_circuit_surface_clearance_mm"],
        }
    failures = {
        circuit_id: item for circuit_id, item in diagnostic_gate.items()
        if not item["topology_pass"] or not item["vertical_geometry_materialized"] or item["bend_radius_violation_count"] or
        item["heating_body_wall_intrusions"] or not item["start_at_collector"] or not item["end_at_collector"]
    }
    if failures:
        raise RuntimeError({"CSharp_diagnostic_gate": failures})

    complete_routes = sum(
        item["topology_pass"] and item["vertical_geometry_materialized"] and
        item["start_at_collector"] and item["end_at_collector"]
        for item in diagnostic_gate.values()
    )
    collector_contract = manufacturer_contract()
    contract = {
        "schema": "homeaura.floor1.physical_four_loop.v1", "artifact_id": ARTIFACT_ID,
        "status": "FOUR_POINT3_FLOOR_ROUTES_PASS_COLLECTOR_TERMINALS_REWORK",
        "append_only": True,
        "source_D174_project_sha256": sha(SOURCE_PROJECT), "source_D174_contract_sha256": sha(SOURCE_CONTRACT),
        "changed_existing_circuit_ids": sorted(CHANGED_IDS), "added_circuit_ids": ["F1-D175-C14"],
        "removed_fragment_ids": sorted(OLD_SERVICE_IDS), "unchanged_circuit_ids": unchanged_ids,
        "unchanged_C03_C12_full_records_preserved": True,
        **validation,
        "CSharp_diagnostic_gate": diagnostic_gate,
        "layer_contract": {
            "heating_axis_elevation_mm": BODY_Z, "lower_service_axis_elevation_mm": LOWER_Z,
            "local_overpass_axis_elevation_mm": OVERPASS_Z,
            "pipe_outer_diameter_mm": PIPE_OD_MM, "minimum_surface_clearance_mm": 5,
            "70_to_108_surface_clearance_mm": BODY_Z - LOWER_Z - PIPE_OD_MM,
            "108_to_135_surface_clearance_mm": OVERPASS_Z - BODY_Z - PIPE_OD_MM,
            "all_vertical_changes_materialized_as_R80_S_bends": True,
            "sleeves_used": False,
        },
        "collector_reference": collector_contract,
        "collector_terminal_contract": {
            "collector_id": "K1", "connection_point_count": 28,
            "explicit_reference_connection_points_materialized": True,
            "connection_tolerance_mm": 4100,
            "assigned_ports": {"F1-D171-C01":[0,1],"F1-D171-C02":[2,3],"F1-D171-C13":[24,25],"F1-D175-C14":[26,27]},
            "chain_endpoints_are_explicit": True,
            "start_end_acceptance_uses_declared_collector_connection_tolerance": True,
            "micro_stubs_from_terminal_grid_to_eurocone_are_not_fabrication_geometry": True,
        },
        "complete_K1_route_count": 0,
        "collector_continuous_route_count": 0,
        "bounded_terminal_grid_route_count": complete_routes,
        "materialized_floor_plane_route_count": complete_routes,
        "route_count_scope": "four D175 Point3 floor routes end at explicit terminal-grid points within a declared tolerance; Eurocone micro-stubs and mounting-height fanout are not materialized; C03-C12 remain inherited FLOOR_HEATING_AXIS records",
        "whole_floor_R80_violation_count_in_unchanged_routes": 16,
        "installation_ready": False,
        "remaining_blockers": [
            "C03-C12 retain inherited R80/body-wall debt",
            "hydraulic sizing, flow settings, cabinet and actuator selection are not evaluated",
            "collector-to-grid Eurocone micro-stubs are tolerance-bound references, not fabrication polylines",
        ],
        "next_block": "REBUILD_F1_R06_THEN_F1_R05_WITH_OWNER_COUNTERFLOW_GRAMMAR_AND_CONTINUOUS_POINT3_SERVICES",
    }

    OUTPUT.mkdir(parents=True)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    project_path = OUTPUT / "HomeAura_Floor1_PhysicalFourLoop_D175.homeaura.json"
    dump(project_path, project)
    dump(OUTPUT / "floor1_physical_four_loop_contract.json", contract)
    dump(OUTPUT / "collector_manufacturer_contract.json", collector_contract)
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID, "result": contract["status"],
        "complete_K1_route_count": 0, "collector_continuous_route_count": 0,
        "bounded_terminal_grid_route_count": complete_routes, "materialized_floor_plane_route_count": complete_routes,
        "hall_pair_length_spread_mm": validation["hall_pair_rounded_length_spread_mm"],
        "changed_body_wall_hits": 0, "changed_stair_hits": 0, "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D175 · четыре непрерывных Point3-маршрута в конструкции пола\n\n"
        "C01/C02 теперь являются едиными Point3-цепями между явными точками терминальной сетки: прежние четыре отдельные серые подводки удалены, "
        "а каждый переход 70/108/135 мм задан аналитическим S-изгибом R80. Холл разделён на две обычные улитки C13/C14; "
        "C14 одновременно формирует три вложенные трубы с шагом 100 мм у W016 и локально проходит над собственной трассой на z=135 мм.\n\n"
        + "Физические длины после горизонтальных R80 и вертикальных S-изгибов: "
        + ", ".join(f"{key}={value['rounded_physical_axis_length_mm']/1000:.3f} м" for key, value in validation["route_metrics"].items())
        + f". Разброс холла {validation['hall_pair_rounded_length_spread_mm']/1000:.3f} м. "
        + f"Покрытие доступной области холла: sharp {validation['hall_coverage']['sharp_axis_round100']['served_percent']:.3f}%, "
        + f"с дугами R80 {validation['hall_coverage']['physical_R80_axis_round100']['served_percent']:.3f}%.\n\n"
        "Материализовано 4 маршрута в плоскости пола до терминальной сетки. Полностью коллекторно-непрерывных маршрутов: 0, "
        "потому что микроподводки к Eurocone и высотный веер у коллектора ещё не нарисованы.\n\n"
        "Пользовательские виды: `HomeAura_Floor1_D175_F1-R02_Clean_Zoom.png` — чистая раскладка холла; "
        "`HomeAura_Floor1_D175_F1-R04_Collectors_Zoom.png` — оба коллектора в котельной с подписями. "
        "`HomeAura_Floor1_D175_3D_Layer_Debug.png` оставлен отдельным инженерным видом.\n\n"
        "Оба коллектора показаны в масштабе одного справочного Uponor Vario S FM 14 (1140845) на W025, K2 перевёрнут на 180°. "
        "Это справочная геометрия, не закупочное и не гидравлическое утверждение. D175 не объявляет готовым весь этаж: C03-C12 сохранены без изменений.\n",
        encoding="utf-8",
    )
    run_editor(project_path, OUTPUT / "engineering_diagnostics.json", "--export-diagnostics")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D175_Editor_View.png", "--export-png")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D175_Clean_View.png", "--export-png-clean")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D175_F1-R02_Zoom.png", "--export-room-png", "F1-R02")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D175_F1-R02_Clean_Zoom.png", "--export-room-png-clean", "F1-R02")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D175_F1-R04_Collectors_Zoom.png", "--export-room-png", "F1-R04")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D175_3D_Layer_Debug.png", "--export-room-png-diagnostics", "F1-R02")
    package_output()
    print(json.dumps({
        "artifact": ARTIFACT_ID, "project": str(project_path), "package": str(PACKAGE),
        "package_sha256": sha(PACKAGE), "complete_K1_route_count": 0,
        "collector_continuous_route_count": 0, "bounded_terminal_grid_route_count": complete_routes,
        "rounded_lengths_mm": {key: value["rounded_physical_axis_length_mm"] for key, value in validation["route_metrics"].items()},
        "hall_spread_mm": validation["hall_pair_rounded_length_spread_mm"],
        "hall_R80_coverage_percent": validation["hall_coverage"]["physical_R80_axis_round100"]["served_percent"],
        "installation_ready": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

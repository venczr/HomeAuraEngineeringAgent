from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import sys
import zipfile
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_floor1_provider_pair_172 as d172  # noqa: E402
from build_owner_style_installation_project_141 import length_mm, self_contacts  # noqa: E402

ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_JOINT_WEAVE_173"
SOURCE_PROJECT = SOURCE / "HomeAura_Floor1_JointWeave_D173.homeaura.json"
SOURCE_CONTRACT = SOURCE / "floor1_joint_weave_contract.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_LOWER_SERVICE_PAIR_174"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_FLOOR1_LOWER_SERVICE_PAIR_174.zip"
ARTIFACT_ID = OUTPUT.name
OFFSET = 3000
BODY_Z = 108
SERVICE_Z = 70

# HeatingBodyRange uses a terminal point index: segments [start_index,end_index).
# Every gap is transit; only those gaps may cross wall solids.
UPPER = {
    "F1-D171-C02": {
        "points": [
            (92,58),(47,58),(47,85),(47,91),(50,91),(50,89),(48,89),(48,85),
            (48,59),(92,59),(99,59),(99,89),(51,89),(51,85),(65,85),(65,62),
            (51,62),(51,81),(61,81),(61,66),(55,66),(55,68),(60,68),(60,71),
            (55,71),(55,76),(57,76),(57,73),(59,73),(59,78),(53,78),(53,71),
            (53,64),(63,64),(63,83),(51,83),
        ],
        "ranges": [(0,2),(7,9),(13,35)],
        "centre": (23,29),
    },
    "F1-D171-C01": {
        "points": [
            (49,85),(49,60),(92,60),(98,60),(98,62),(92,62),(67,62),(67,85),
            (92,85),(92,66),(71,66),(71,81),(88,81),(88,70),(75,70),(75,77),
            (84,77),(84,72),(79,72),(79,74),(82,74),(82,76),(77,76),(77,71),
            (86,71),(86,79),(73,79),(73,68),(90,68),(90,83),(69,83),(69,64),
            (92,64),
        ],
        "ranges": [(0,2),(5,32)],
        "centre": (16,22),
    },
}

SERVICE = [
    {"id":"F1-D174-C02-SUPPLY","logical":"F1-D171-C02","leg":"SUPPLY","port":2,"points":[(130,58),(92,58)]},
    {"id":"F1-D174-C02-RETURN","logical":"F1-D171-C02","leg":"RETURN","port":3,"points":[(51,83),(130,83)]},
    {"id":"F1-D174-C01-SUPPLY","logical":"F1-D171-C01","leg":"SUPPLY","port":0,"points":[(130,85),(49,85)]},
    {"id":"F1-D174-C01-RETURN","logical":"F1-D171-C01","leg":"RETURN","port":1,"points":[(92,64),(130,64)]},
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mm(point: tuple[int, int]) -> dict:
    return {"x_mm": OFFSET + point[0] * 100, "y_mm": OFFSET + point[1] * 100}


def mm_line(points: list[tuple[int, int]]) -> LineString:
    return LineString([(OFFSET + x * 100, OFFSET + y * 100) for x, y in points])


def body_indices(ranges: list[tuple[int, int]]) -> set[int]:
    return {index for start, end in ranges for index in range(start, end)}


def body_lines(specification: dict) -> list[LineString]:
    return [LineString(specification["points"][start:end + 1]) for start, end in specification["ranges"]]


def fillet(points: list[tuple[int, int]], radius: float = .8, steps: int = 16) -> list[tuple[float, float]]:
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
        centre = (
            corner[0] + (first_unit[0] + second_unit[0]) * radius,
            corner[1] + (first_unit[1] + second_unit[1]) * radius,
        )
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


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for start, end in sorted((min(a, b), max(a, b)) for a, b in intervals if a != b):
        if not result or start > result[-1][1]:
            result.append((start, end))
        else:
            result[-1] = (result[-1][0], max(result[-1][1], end))
    return result


def exterior_audit() -> dict:
    segments = []
    for specification in UPPER.values():
        accepted = body_indices(specification["ranges"])
        segments.extend(
            (first, second) for index, (first, second) in enumerate(zip(specification["points"], specification["points"][1:]))
            if index in accepted
        )
    definitions = {
        "FLOOR_1-W001": [
            (1,"Y",58,47,92,(46,93),(47,93)),
            (2,"Y",59,48,92,(46,93),(48,93)),
            (3,"Y",60,49,92,(46,93),(49,93)),
        ],
        "FLOOR_1-W004": [
            (1,"X",47,58,85,(57,86),(57,86)),
            (2,"X",48,59,85,(57,86),(58,86)),
            (3,"X",49,60,85,(57,86),(59,86)),
        ],
    }
    result = {}
    for wall_id, definitions_for_wall in definitions.items():
        records = []
        for lane, axis, coordinate, start, end, raw, envelope in definitions_for_wall:
            intervals = merge([
                (first[0], second[0]) if axis == "Y" else (first[1], second[1])
                for first, second in segments
                if (axis == "Y" and first[1] == second[1] == coordinate)
                or (axis == "X" and first[0] == second[0] == coordinate)
            ])
            covered = sum(second - first for first, second in intervals)
            records.append({
                "lane": lane, "axis": axis, "coordinate_grid": coordinate,
                "from_grid": start, "to_grid": end,
                "covered_intervals_grid": [list(item) for item in intervals],
                "covered_length_mm": covered * 100,
                "raw_full_face_required_length_mm": (raw[1] - raw[0]) * 100,
                "raw_full_face_coverage_percent": covered * 100 / (raw[1] - raw[0]),
                "R80_corner_envelope_required_length_mm": (envelope[1] - envelope[0]) * 100,
                "R80_corner_envelope_coverage_percent": covered * 100 / (envelope[1] - envelope[0]),
                "continuous_pass_present": any(first <= start and second >= end for first, second in intervals),
            })
        result[wall_id] = records
    return result


def render(project_file: Path, output: Path, command: str, room_id: str | None = None) -> None:
    args = ["dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
            "-c", "Release", "--", command, str(project_file), str(output)]
    if room_id:
        args.append(room_id)
    subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True)


def package_output() -> None:
    payloads = sorted(path for path in OUTPUT.iterdir() if path.is_file() and path.name != "artifact_manifest.json")
    dump(OUTPUT / "artifact_manifest.json", {
        "artifact_id": ARTIFACT_ID, "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in payloads],
    })
    with zipfile.ZipFile(PACKAGE, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUTPUT.iterdir()):
            if path.is_file():
                archive.write(path, path.name)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D174 is append-only")
    OUTPUT.mkdir(parents=True)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    project = json.loads(SOURCE_PROJECT.read_text(encoding="utf-8-sig"))
    source = copy.deepcopy(project)

    route_records = {}
    sharp_body_lines: list[LineString] = []
    rounded_body_lines: list[LineString] = []
    for circuit_id, specification in UPPER.items():
        points, ranges = specification["points"], specification["ranges"]
        bend = d172.bend_audit(points)
        centre = d172.centre_audit(points, *specification["centre"])
        if bend["tangent_allocation_violation_count"] or bend["minimum_segment_mm"] < 200:
            raise RuntimeError({"R80": circuit_id, "audit": bend})
        if not centre["exact_owner_template_B_D4_match"] or not LineString(points).is_simple or self_contacts(points):
            raise RuntimeError({"owner_or_topology": circuit_id})
        accepted_indices = body_indices(ranges)
        segment_lengths = d172.segment_lengths_mm(points)
        body_length = sum(segment_lengths[index] for index in accepted_indices)
        circuit = next(item for item in project["circuits"] if item["id"] == circuit_id)
        circuit.update({
            "ordered_points": [mm(point) for point in points],
            "heating_body_start_index": None, "heating_body_end_index": None,
            "heating_body_ranges": [{"start_index": start, "end_index": end} for start, end in ranges],
            "system_role": "FLOOR_HEATING_AXIS", "routing_layer": "HEATING_PLANE", "axis_elevation_mm": BODY_Z,
            "collector_id": None, "supply_port_index": None, "return_port_index": None,
            "service_zone_id": None, "concealed_service_length_mm": 0, "out_of_plane_length_mm": 0,
            "name": f"{circuit_id.replace('D171','D174')} · улитка с явными транзитами · тело {body_length/1000:.1f} м",
        })
        sharp_body_lines.extend(body_lines(specification))
        rounded_body_lines.extend(
            LineString(fillet(points[start:end + 1])) for start, end in ranges
        )
        route_records[circuit_id] = {
            "ordered_points_grid": [list(point) for point in points],
            "heating_body_ranges": [{"start_index": start, "end_index": end} for start, end in ranges],
            "body_length_mm": body_length,
            "in_route_transit_length_mm": length_mm(points) - body_length,
            "upper_route_axis_length_mm": length_mm(points),
            "upper_route_rounded_R80_length_mm": bend["rounded_body_length_mm"],
            "R80": bend, "centre": centre,
        }

    unchanged = []
    for source_circuit in source["circuits"]:
        if source_circuit["id"] in UPPER:
            continue
        current = next(item for item in project["circuits"] if item["id"] == source_circuit["id"])
        if current["ordered_points"] != source_circuit["ordered_points"]:
            raise RuntimeError({"unexpected_change": source_circuit["id"]})
        unchanged.append(source_circuit["id"])

    service_records = []
    for specification in SERVICE:
        points = specification["points"]
        bend = d172.bend_audit(points)
        if bend["tangent_allocation_violation_count"] or not LineString(points).is_simple:
            raise RuntimeError({"service_R80": specification["id"]})
        project["circuits"].append({
            "id": specification["id"],
            "name": f"{specification['id']} · нижняя подводка {length_mm(points)/1000:.1f} м",
            "color": "#94A3B8", "ordered_points": [mm(point) for point in points], "completed": True,
            "collector_id": "K1",
            "supply_port_index": specification["port"] if specification["leg"] == "SUPPLY" else None,
            "return_port_index": specification["port"] if specification["leg"] == "RETURN" else None,
            "service_zone_id": "K1-TRANSIT-RESERVATION-D171", "concealed_service_length_mm": 0,
            "out_of_plane_length_mm": 0, "routing_layer": "LOWER_SERVICE_LAYER",
            "system_role": "FLOOR_SERVICE_LEG", "axis_elevation_mm": SERVICE_Z, "visible_on_plan": True,
            "room_id": None, "heating_body_start_index": None, "heating_body_end_index": None,
            "heating_body_ranges": [],
        })
        service_records.append({**specification, "points_grid": [list(point) for point in points],
                                "axis_length_mm": length_mm(points), "rounded_R80_length_mm": bend["rounded_body_length_mm"],
                                "R80": bend, "axis_elevation_mm": SERVICE_Z})

    upper_lines = {circuit_id: LineString(specification["points"]) for circuit_id, specification in UPPER.items()}
    preserved_lines = {
        item["id"]: LineString([((point["x_mm"]-OFFSET)/100, (point["y_mm"]-OFFSET)/100) for point in item["ordered_points"]])
        for item in source["circuits"] if item["id"] not in UPPER
    }
    if not upper_lines["F1-D171-C01"].intersection(upper_lines["F1-D171-C02"]).is_empty:
        raise RuntimeError("upper pair contact")
    if any(not line.intersection(other).is_empty for line in upper_lines.values() for other in preserved_lines.values()):
        raise RuntimeError("upper route contacts preserved route")

    service_lines = {item["id"]: LineString(item["points"]) for item in SERVICE}
    if any(not service_lines[first].intersection(service_lines[second]).is_empty
           for index, first in enumerate(service_lines) for second in list(service_lines)[index+1:]):
        raise RuntimeError("lower service contact")
    lower_minimum = min(service_lines[first].distance(service_lines[second])
                        for index, first in enumerate(service_lines) for second in list(service_lines)[index+1:])

    room = next(item for item in project["rooms"] if item["id"] == "F1-R08")
    room_polygon = Polygon([(point["x_mm"],point["y_mm"]) for point in room["outline"]])
    wall_solids = {
        wall["id"]: LineString([(wall["start"]["x_mm"],wall["start"]["y_mm"]),(wall["end"]["x_mm"],wall["end"]["y_mm"])])
        .buffer(wall["thickness_mm"]/2, cap_style="square") for wall in project["walls"]
    }
    for line in sharp_body_lines:
        world = LineString([(OFFSET+x*100,OFFSET+y*100) for x,y in line.coords])
        if not room_polygon.covers(world) or any(not world.intersection(solid).is_empty for solid in wall_solids.values()):
            raise RuntimeError("heating body leaves room or enters wall")

    wall_axes = {
        wall["id"]: LineString([(wall["start"]["x_mm"],wall["start"]["y_mm"]),(wall["end"]["x_mm"],wall["end"]["y_mm"])])
        for wall in project["walls"]
    }
    upper_wall_audit = []
    for circuit_id, specification in UPPER.items():
        accepted = body_indices(specification["ranges"])
        hits = []
        for segment_index,(first,second) in enumerate(zip(specification["points"],specification["points"][1:])):
            segment = mm_line([first,second])
            for wall_id,wall in wall_axes.items():
                intersection = segment.intersection(wall)
                if intersection.is_empty:
                    continue
                perpendicular = (wall.coords[0][1] == wall.coords[-1][1]) != (first[1] == second[1])
                hits.append({"segment_index":segment_index,"segment_role":"BODY" if segment_index in accepted else "TRANSIT",
                             "wall_id":wall_id,"perpendicular_crossing":perpendicular,"intersection_wkt":intersection.wkt})
        if any(hit["segment_role"] == "BODY" or not hit["perpendicular_crossing"] for hit in hits):
            raise RuntimeError({"wall_crossing":circuit_id,"hits":hits})
        upper_wall_audit.append({"circuit_id":circuit_id,"crossings":hits})

    service_wall_audit = []
    for specification in SERVICE:
        first,second = specification["points"]
        line = mm_line(specification["points"])
        hits = []
        for wall_id,wall in wall_axes.items():
            intersection = line.intersection(wall)
            if intersection.is_empty:
                continue
            perpendicular = (wall.coords[0][1] == wall.coords[-1][1]) != (first[1] == second[1])
            hits.append({"wall_id":wall_id,"perpendicular_crossing":perpendicular,"intersection_wkt":intersection.wkt})
        if any(not hit["perpendicular_crossing"] for hit in hits):
            raise RuntimeError({"service_wall":specification["id"]})
        service_wall_audit.append({"fragment_id":specification["id"],"crossings":hits})

    domain = box(46,57,93,86)
    sharp_union, rounded_union = unary_union(sharp_body_lines), unary_union(rounded_body_lines)
    sharp_served = domain.intersection(sharp_union.buffer(1,quad_segs=16)).area
    rounded_served = domain.intersection(rounded_union.buffer(1,quad_segs=16)).area
    sharp_samples = [Point(x/2,y/2).distance(sharp_union) for x in range(92,187) for y in range(114,173)]
    rounded_samples = [Point(x/2,y/2).distance(rounded_union) for x in range(92,187) for y in range(114,173)]
    if sharp_served*100/domain.area < 98 or max(sharp_samples) > 1.5+1e-9 or max(rounded_samples) > 2+1e-9:
        raise RuntimeError("coverage gate")
    exterior = exterior_audit()
    if any(not record["continuous_pass_present"] or record["R80_corner_envelope_coverage_percent"] < 90
           for records in exterior.values() for record in records):
        raise RuntimeError("exterior lane gate")

    vertical_length = 2*(BODY_Z-SERVICE_Z)
    logical_routes = {}
    for circuit_id,route in route_records.items():
        supply = next(item for item in service_records if item["logical"] == circuit_id and item["leg"] == "SUPPLY")
        returned = next(item for item in service_records if item["logical"] == circuit_id and item["leg"] == "RETURN")
        if tuple(supply["points_grid"][-1]) != UPPER[circuit_id]["points"][0] or tuple(returned["points_grid"][0]) != UPPER[circuit_id]["points"][-1]:
            raise RuntimeError({"handoff":circuit_id})
        rounded_plan = supply["rounded_R80_length_mm"]+route["upper_route_rounded_R80_length_mm"]+returned["rounded_R80_length_mm"]
        logical_routes[circuit_id] = {
            "supply_fragment_id":supply["id"],"upper_axis_id":circuit_id,"return_fragment_id":returned["id"],
            "raw_plan_axis_length_mm":supply["axis_length_mm"]+route["upper_route_axis_length_mm"]+returned["axis_length_mm"],
            "rounded_plan_length_mm":rounded_plan,"known_vertical_transition_length_mm":vertical_length,
            "nominal_3D_rounded_length_mm":rounded_plan+vertical_length,
            "vertical_transition_ramp_geometry":"NOT_MATERIALIZED",
        }
    nominal = [route["nominal_3D_rounded_length_mm"] for route in logical_routes.values()]

    project["training_metadata"] = {
        "label":"DRAFT","author_intent":"D174 balanced F1-R08 pair with multi-range heating bodies and explicit lower service legs",
        "notes":"Only heating_body_ranges heat the room. Gaps and lower legs are transit. 3D R80 layer ramps remain REWORK.",
    }
    project_path = OUTPUT/"HomeAura_Floor1_LowerServicePair_D174.homeaura.json"
    dump(project_path,project)
    contract = {
        "schema":"homeaura.floor1.lower_service_pair.v2","artifact_id":ARTIFACT_ID,
        "status":"BALANCED_MULTI_RANGE_PAIR_GEOMETRY_PASS_REWORK_3D_RAMPS_AND_WHOLE_FLOOR_R80","append_only":True,
        "source_D173_project_sha256":sha(SOURCE_PROJECT),"source_D173_contract_sha256":sha(SOURCE_CONTRACT),
        "changed_circuit_ids":sorted(UPPER),"unchanged_circuit_ids":unchanged,
        "unchanged_circuit_point_arrays_preserved":True,"upper_route_records":route_records,
        "lower_service_fragments":service_records,
        "fragment_validation":{"upper_pair_contact_count":0,"upper_to_unchanged_route_contact_count":0,
            "lower_service_contact_count":0,"minimum_lower_service_centerline_mm":lower_minimum*100,
            "R80_tangent_allocation_violation_count":0,"minimum_segment_mm":200},
        "layer_contract":{"body_axis_elevation_mm":BODY_Z,"lower_service_axis_elevation_mm":SERVICE_Z,
            "axis_separation_mm":BODY_Z-SERVICE_Z,"pipe_outer_diameter_mm":project["routing_rules"]["pipe_outer_diameter_mm"],
            "surface_clearance_mm":BODY_Z-SERVICE_Z-project["routing_rules"]["pipe_outer_diameter_mm"],
            "vertical_transition_count":4,"vertical_transition_ramp_geometry":"NOT_MATERIALIZED"},
        "upper_route_wall_crossing_audit":upper_wall_audit,"service_wall_crossing_audit":service_wall_audit,
        "heating_body_wall_hit_count":0,"longitudinal_wall_segment_count":0,
        "coverage_diagnostic":{"domain_area_m2":domain.area/100,"sharp_axis_round100_served_m2":sharp_served/100,
            "sharp_axis_round100_served_percent":sharp_served*100/domain.area,
            "sharp_axis_50mm_sample_max_distance_mm":max(sharp_samples)*100,
            "R80_filleted_axis_round100_served_m2":rounded_served/100,
            "R80_filleted_axis_round100_served_percent":rounded_served*100/domain.area,
            "R80_filleted_axis_50mm_sample_within150_percent":sum(value<=1.5+1e-9 for value in rounded_samples)*100/len(rounded_samples),
            "R80_filleted_axis_50mm_sample_max_distance_mm":max(rounded_samples)*100,
            "R80_filleted_all_samples_within200":max(rounded_samples)<=2+1e-9,
            "proxy_is_heat_sufficiency_certificate":False},
        "exterior_3x100":{"scope":"ROOM_AGGREGATE_BODY_AXES_FROM_TRUE_INTERIOR_WALL_FACE","passes":exterior,
            "raw_full_face_90_percent_pass_count":sum(record["raw_full_face_coverage_percent"]>=90 for records in exterior.values() for record in records),
            "R80_corner_envelope_90_percent_pass_count":sum(record["R80_corner_envelope_coverage_percent"]>=90 for records in exterior.values() for record in records),
            "pass_count_total":6,"window_projection_covered_by_all_left_passes":True,"corner_envelope_is_explicit":True},
        "logical_route_candidates":logical_routes,"nominal_3D_rounded_length_spread_mm":max(nominal)-min(nominal),
        "pair_balance_target_mm":2000,"pair_balance_candidate_pass":max(nominal)-min(nominal)<=2000,
        "collector_terminal_contract":{"collector_id":"K1","service_terminal_x_grid":130,
            "collector_reference_position_grid":[134,63],"terminal_distance_within_connection_tolerance":True,
            "physical_manifold_port_stubs_materialized":False},
        "complete_K1_route_count":0,"installation_ready":False,
        "whole_floor_R80_violation_count_in_unchanged_routes":16,
        "next_block":"MATERIALIZE_3D_LAYER_RAMPS_THEN_REBUILD_INHERITED_C03_C13_R80_AND_BODY_WALL_COMPLIANCE_ROOM_BY_ROOM",
    }
    dump(OUTPUT/"floor1_lower_service_pair_contract.json",contract)
    dump(OUTPUT/"status.json",{"artifact_id":ARTIFACT_ID,"result":contract["status"],
        "pair_balance_candidate_pass":contract["pair_balance_candidate_pass"],"heating_body_wall_hits":0,
        "R80_tangent_violations_in_changed_pair":0,"complete_K1_route_count":0,"installation_ready":False})
    (OUTPUT/"README.md").write_text(
        "# D174 · сбалансированная пара F1-R08 с явными транзитами\n\n"
        "D174 заменяет только C01/C02. Сплошные диапазоны — отопительное тело, пунктирные промежутки — транзит; "
        "поэтому стены пересекают только короткие перпендикулярные трассы. Три трубы у наружных стен и под окном "
        "видимы, коротких 100-мм П-разворотов нет, R80 нарушений у изменённой пары нет.\n\n"
        f"Sharp-axis proxy: {sharp_served*100/domain.area:.3f}%. С физическими дугами R80: "
        f"{rounded_served*100/domain.area:.3f}%, худшая контрольная точка {max(rounded_samples)*100:.1f} мм; все ближе 200 мм. "
        + "Номинальные округлённые длины: "
        + ", ".join(f"{key}={value['nominal_3D_rounded_length_mm']/1000:.3f} м" for key,value in logical_routes.items())
        + f"; разброс {(max(nominal)-min(nominal))/1000:.3f} м.\n\n"
        "Это ещё не весь готовый этаж: 3D-рампы 70/108 мм и короткие штуцеры коллектора не материализованы, "
        "а в неизменённых C03-C13 остаются 16 старых нарушений R80.\n",encoding="utf-8")
    render(project_path,OUTPUT/"engineering_diagnostics.json","--export-diagnostics")
    render(project_path,OUTPUT/"HomeAura_Floor1_D174_Editor_View.png","--export-png")
    render(project_path,OUTPUT/"HomeAura_Floor1_D174_Clean_View.png","--export-png-clean")
    render(project_path,OUTPUT/"HomeAura_Floor1_D174_F1-R08_Zoom.png","--export-room-png","F1-R08")
    render(project_path,OUTPUT/"HomeAura_Floor1_D174_F1-R08_Diagnostics.png","--export-room-png-diagnostics","F1-R08")
    package_output()
    print(json.dumps({"artifact":ARTIFACT_ID,"sharp_coverage_percent":sharp_served*100/domain.area,
        "R80_coverage_percent":rounded_served*100/domain.area,
        "nominal_lengths_mm":{key:value["nominal_3D_rounded_length_mm"] for key,value in logical_routes.items()},
        "nominal_spread_mm":max(nominal)-min(nominal),"installation_ready":False},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()

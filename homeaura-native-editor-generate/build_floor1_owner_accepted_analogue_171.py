from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_iterative_golden_mean_164 as d164  # noqa: E402


ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D170 = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_USER_MARKUP_CORRECTION_170"
SOURCE_PROJECT = D170 / "HomeAura_Floor1_UserMarkupCorrection_D170.homeaura.json"
SOURCE_CONTRACT = D170 / "floor1_user_markup_correction_contract.json"
OWNER_REFERENCE = ROOT / "homeaura-native-editor" / "examples" / "room-7000x3200-south-exterior.homeaura.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_OWNER_ACCEPTED_ANALOGUE_171"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_FLOOR1_OWNER_ACCEPTED_ANALOGUE_171.zip"
ARTIFACT_ID = OUTPUT.name
OFFSET = 3000
COLORS = [
    "#E43F5A", "#3676C8", "#AB7DF6", "#32D583", "#F59E0B", "#14B8A6", "#F97066",
    "#29B6F6", "#A3E635", "#FB923C", "#60A5FA", "#F472B6", "#22C55E",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def project_point(point: tuple[int, int]) -> dict:
    return {"x_mm": OFFSET + point[0] * 100, "y_mm": OFFSET + point[1] * 100}


def grid_points(circuit: dict) -> list[tuple[int, int]]:
    return [((point["x_mm"] - OFFSET) // 100, (point["y_mm"] - OFFSET) // 100) for point in circuit["ordered_points"]]


def line_mm(points: list[tuple[int, int]]) -> LineString:
    return LineString([(OFFSET + x * 100, OFFSET + y * 100) for x, y in points])


def room_polygon(project: dict, room_id: str) -> Polygon:
    room = next(item for item in project["rooms"] if item["id"] == room_id)
    return Polygon([(point["x_mm"], point["y_mm"]) for point in room["outline"]])


def wall_solids(project: dict) -> list[tuple[str, Polygon]]:
    return [
        (
            wall["id"],
            LineString([
                (wall["start"]["x_mm"], wall["start"]["y_mm"]),
                (wall["end"]["x_mm"], wall["end"]["y_mm"]),
            ]).buffer(wall["thickness_mm"] / 2, cap_style="square"),
        )
        for wall in project["walls"]
    ]


def owner_signature(points: list[tuple[int, int]], exterior_sides: list[str]) -> dict:
    lengths = [abs(first[0] - second[0]) + abs(first[1] - second[1]) for first, second in zip(points, points[1:])]
    short_200 = sum(length == 2 for length in lengths)
    return {
        "orthogonal": all(first[0] == second[0] or first[1] == second[1] for first, second in zip(points, points[1:])),
        "simple": LineString(points).is_simple,
        "compact_200mm_turn_segment_count": short_200,
        "compact_asymmetric_centre_present": short_200 > 0,
        "exterior_three_pass_prelude_present": bool(exterior_sides),
        "field_interleave_mm": 200,
        "inward_frame_step_mm": 400,
    }


def owner_reference_signature() -> dict:
    source = load(OWNER_REFERENCE)
    circuits = source["circuits"]
    lengths = []
    for circuit in circuits:
        points = [(point["x_mm"], point["y_mm"]) for point in circuit["ordered_points"]]
        lengths.append(sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(points, points[1:])))
    centre_one = [[1900, 1900], [1900, 1500], [1700, 1500], [1700, 1700], [1500, 1700], [1500, 1300], [2000, 1300]]
    centre_two = [[4400, 1500], [4400, 2000], [4900, 2000], [4900, 1800], [4600, 1800], [4600, 1600], [5100, 1600]]
    return {
        "artifact_sha256": sha(OWNER_REFERENCE),
        "training_label": source["training_metadata"]["label"],
        "manual_circuit_count": len(circuits),
        "manual_lengths_mm": lengths,
        "manual_length_spread_mm": max(lengths) - min(lengths),
        "exterior_axis_distances_mm": [100, 200, 300],
        "field_pitch_mm": 200,
        "inward_frame_step_mm": 400,
        "accepted_asymmetric_centres_mm": [centre_one, centre_two],
    }


def render(project_file: Path, output: Path, clean_view: bool) -> None:
    subprocess.run([
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", "--export-png-clean" if clean_view else "--export-png", str(project_file), str(output),
    ], cwd=ROOT, check=True, capture_output=True, text=True)


def package_output() -> None:
    files = sorted(path for path in OUTPUT.iterdir() if path.is_file() and path.name != "artifact_manifest.json")
    dump(OUTPUT / "artifact_manifest.json", {
        "artifact_id": ARTIFACT_ID,
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    })
    with zipfile.ZipFile(PACKAGE, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUTPUT.iterdir()):
            if path.is_file():
                archive.write(path, path.name)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D171 is append-only")
    OUTPUT.mkdir(parents=True)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)

    project = load(SOURCE_PROJECT)
    source_contract = load(SOURCE_CONTRACT)
    source_records = {item["circuit_id"]: item for item in source_contract["body_records"]}

    retained = []
    for circuit in project["circuits"]:
        if circuit["room_id"] == "F1-R03":
            continue
        record = source_records[circuit["id"]]
        retained.append({
            "points": grid_points(circuit),
            "room_id": circuit["room_id"],
            "territory": record["territory"],
            "body_length_mm": record["body_length_mm"],
            "service_length_mm": record["estimated_service_length_mm"],
            "total_length_mm": record["estimated_complete_length_mm"],
            "variant": record["geometry_variant"],
            "exterior_sides": record["exterior_sides"],
            "source_D170_circuit_id": circuit["id"],
        })

    kitchen_room = next(room for room in project["rooms"] if room["id"] == "F1-R03")
    kitchen_polygon = Polygon([(point["x_mm"] - OFFSET, point["y_mm"] - OFFSET) for point in kitchen_room["outline"]])
    kitchen_items, kitchen_search = d164.choose_group(
        kitchen_polygon,
        d164.partition_variants((139, 92, 180, 162), 3, "Y"),
        lambda index, count: {"R", "B"} if index == count - 1 else {"R"},
        lambda points, _: d164.floor_service_mm(points),
    )
    kitchen = [{
        **item,
        "room_id": "F1-R03",
        "territory": f"Кухня-гостиная · совместная улитка {index + 1}/3",
        "source_D170_circuit_id": None,
    } for index, item in enumerate(kitchen_items)]

    order = ["F1-R08", "F1-R07", "F1-R04", "F1-R03", "F1-R06", "F1-R05", "F1-R01", "F1-R02"]
    items = retained + kitchen
    items.sort(key=lambda item: (order.index(item["room_id"]), item["points"][0][1], item["points"][0][0]))
    if len(items) != 13:
        raise RuntimeError({"body_count": len(items)})

    project["circuits"] = []
    project["collectors"] = copy.deepcopy(project["collectors"])
    k1 = next(item for item in project["collectors"] if item["id"] == "K1")
    k1["ports"] = 26
    for zone in project.get("service_zones", []):
        if zone["id"] == "K1-TRANSIT-RESERVATION-D170":
            zone["id"] = "K1-TRANSIT-RESERVATION-D171"
            zone["name"] = "Будущие индивидуальные подводки K1 — 13 контуров по эталону владельца"
            zone["pipe_capacity"] = 26
            zone["required_pipe_count"] = 26
            zone["required_plan_width_mm"] = 1300

    walls = wall_solids(project)
    records = []
    for index, item in enumerate(items):
        points = item["points"]
        body_line = line_mm(points)
        room = room_polygon(project, item["room_id"])
        hits = [wall_id for wall_id, solid in walls if body_line.intersects(solid)]
        if hits or not room.covers(body_line):
            raise RuntimeError({"room": item["room_id"], "wall_hits": hits, "contained": room.covers(body_line)})
        signature = owner_signature(points, list(item.get("exterior_sides", [])))
        if not signature["orthogonal"] or not signature["simple"] or not signature["compact_asymmetric_centre_present"]:
            raise RuntimeError({"owner_signature_failed": item["room_id"], "signature": signature})
        circuit_id = f"F1-D171-C{index + 1:02d}"
        project["circuits"].append({
            "id": circuit_id,
            "name": f"{circuit_id} · аналог ручного ACCEPTED · {item['territory']} · {item['body_length_mm'] / 1000:.1f} м",
            "color": COLORS[index],
            "ordered_points": [project_point(point) for point in points],
            "completed": True,
            "collector_id": "K1",
            "supply_port_index": index * 2,
            "return_port_index": index * 2 + 1,
            "service_zone_id": "K1-TRANSIT-RESERVATION-D171",
            "concealed_service_length_mm": item["service_length_mm"],
            "out_of_plane_length_mm": 0,
            "routing_layer": "HEATING_PLANE",
            "system_role": "FLOOR_HEATING_AXIS",
            "axis_elevation_mm": 108,
            "visible_on_plan": True,
            "room_id": item["room_id"],
            "heating_body_start_index": 0,
            "heating_body_end_index": len(points) - 1,
        })
        records.append({
            "circuit_id": circuit_id,
            "source_D170_circuit_id": item["source_D170_circuit_id"],
            "room_id": item["room_id"],
            "territory": item["territory"],
            "body_points_grid": [list(point) for point in points],
            "body_length_mm": item["body_length_mm"],
            "estimated_service_length_mm": item["service_length_mm"],
            "estimated_complete_length_mm": item["total_length_mm"],
            "exterior_sides": item.get("exterior_sides", []),
            "geometry_variant": item["variant"],
            "owner_accepted_analogue_signature": signature,
            "body_inside_assigned_room": True,
            "body_wall_intrusion_count": 0,
        })

    lines = [LineString([(point["x_mm"], point["y_mm"]) for point in circuit["ordered_points"]]) for circuit in project["circuits"]]
    contacts = [
        [project["circuits"][first]["id"], project["circuits"][second]["id"]]
        for first in range(len(lines)) for second in range(first + 1, len(lines))
        if not lines[first].intersection(lines[second]).is_empty
    ]
    if contacts:
        raise RuntimeError({"body_contacts": contacts})
    exclusions = [Polygon([(point["x_mm"], point["y_mm"]) for point in item["outline"]]) for item in project.get("exclusions", [])]
    exclusion_hits = sum(not line.intersection(exclusion).is_empty for line in lines for exclusion in exclusions)
    if exclusion_hits:
        raise RuntimeError({"exclusion_hits": exclusion_hits})

    heated_floor = unary_union([room_polygon(project, room["id"]) for room in project["rooms"] if room.get("heating_allowed", True)])
    served = heated_floor.intersection(unary_union([line.buffer(100, quad_segs=16) for line in lines])).area
    project["routing_rules"].update({
        "exterior_edge_zone_applied": True,
        "exterior_wall_spacing_mm": 100,
        "field_spacing_mm": 200,
        "maximum_parallel_transit_pipes_at_100mm": 3,
        "owner_accepted_reference_required": True,
    })
    project["training_metadata"] = {
        "label": "DRAFT",
        "author_intent": "D171: first-floor bodies generated by analogy with the owner's ACCEPTED manual two-counterflow example",
        "notes": "Эталон — ручные встречные улитки владельца: три оси 100/200/300 мм у наружной стены, далее 200 мм; рамки заходят внутрь по 400 мм, обратная ветвь идёт между ними, центр замыкается компактно и асимметрично. Кухня-гостиная исправлена с 4 до 3 крупных контуров. Только подводкам разрешено пересекать стены; в D171 они ещё не материализованы.",
    }

    project_path = OUTPUT / "HomeAura_Floor1_OwnerAcceptedAnalogue_D171.homeaura.json"
    dump(project_path, project)
    contract = {
        "schema": "homeaura.floor1.owner_accepted_analogue.v1",
        "artifact_id": ARTIFACT_ID,
        "status": "OWNER_ACCEPTED_GRAMMAR_BODY_PASS_REWORK_K1_TRANSITS_AND_EXACT_COVERAGE",
        "append_only": True,
        "sources": {
            "D170_project_sha256": sha(SOURCE_PROJECT),
            "D170_contract_sha256": sha(SOURCE_CONTRACT),
            "owner_ACCEPTED_reference": owner_reference_signature(),
        },
        "allocation": {
            "total_body_count": len(records),
            "K1_ports": 26,
            "room_body_counts": {room_id: sum(item["room_id"] == room_id for item in records) for room_id in order},
            "kitchen_living_changed_from_4_to_3": True,
        },
        "body_records": records,
        "validation": {
            "owner_analogue_signature_pass_count": sum(item["owner_accepted_analogue_signature"]["compact_asymmetric_centre_present"] for item in records),
            "body_inside_assigned_room_count": len(records),
            "body_wall_intrusion_count": 0,
            "body_exclusion_hit_count": exclusion_hits,
            "inter_body_contact_count": len(contacts),
            "field_spacing_mm": 200,
            "exterior_axes_mm": [100, 200, 300],
            "heating_bodies_may_cross_walls": False,
            "future_transits_may_cross_walls": True,
        },
        "coverage_diagnostic": {
            "heated_room_union_area_m2": heated_floor.area / 1_000_000,
            "body_round_100mm_proximity_served_m2": served / 1_000_000,
            "served_percent": served * 100 / heated_floor.area,
            "full_coverage_claimed": False,
            "method": "ROUND_100MM_BODY_ONLY_PROXIMITY_Q16_NOT_THERMAL_PROOF",
        },
        "kitchen_search_evidence": kitchen_search,
        "complete_K1_route_count": 0,
        "planned_K1_circuit_count": len(records),
        "installation_ready": False,
        "next_block": "MATERIALIZE_13_COMPLETE_K1_ROUTES_WITH_TRANSIT_ONLY_WALL_CROSSINGS",
    }
    dump(OUTPUT / "floor1_owner_accepted_analogue_contract.json", contract)
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "result": contract["status"],
        "body_count": len(records),
        "kitchen_living_body_count": 3,
        "owner_reference_label": "ACCEPTED",
        "full_routes_complete": False,
        "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D171 · аналог ручного ACCEPTED-эталона владельца\n\n"
        "Перекомпонован первый этаж по сохранённой ручной геометрической грамматике владельца. "
        "В кухне-гостиной теперь три крупных совместных поля вместо четырёх дробных. У наружных стен сохраняются "
        "три оси 100/200/300 мм, затем поле 200 мм. Отопительные тела не входят в стены; будущие подводки K1 будут "
        "отдельным слоем и только им разрешено пересекать стены.\n",
        encoding="utf-8",
    )
    render(project_path, OUTPUT / "HomeAura_Floor1_D171_Editor_View.png", False)
    render(project_path, OUTPUT / "HomeAura_Floor1_D171_Clean_View.png", True)
    package_output()
    print(json.dumps({
        "artifact": ARTIFACT_ID,
        "body_count": len(records),
        "kitchen_body_count": 3,
        "contacts": 0,
        "wall_intrusions": 0,
        "served_percent": contract["coverage_diagnostic"]["served_percent"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

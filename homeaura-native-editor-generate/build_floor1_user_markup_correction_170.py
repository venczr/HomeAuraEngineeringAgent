from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_iterative_golden_mean_164 as d164  # noqa: E402


ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D169 = PROPOSALS / "HA_TWO_FLOOR_LAYER_CLEARANCE_EVIDENCE_169"
D039 = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039" / "canonical_geometry.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_USER_MARKUP_CORRECTION_170"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_FLOOR1_USER_MARKUP_CORRECTION_170.zip"
OWNER_MARKUP = Path(r"C:\Users\zahar\.codex\codex-remote-attachments\019fc491-99e9-76d1-9c22-d4af32edee0b\06BFD5AB-4266-4DA8-8C71-F8338C7571C5\1-Фото-1.jpg")
ARTIFACT_ID = OUTPUT.name
OFFSET = 3000
COLORS = [
    "#E43F5A", "#3676C8", "#AB7DF6", "#32D583", "#F59E0B", "#14B8A6", "#F97066",
    "#29B6F6", "#A3E635", "#FB923C", "#60A5FA", "#F472B6", "#22C55E", "#06B6D4",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


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


def project_point(point: tuple[int, int]) -> dict:
    return {"x_mm": OFFSET + point[0] * 100, "y_mm": OFFSET + point[1] * 100}


def room_polygon(project: dict, room_id: str) -> Polygon:
    room = next(item for item in project["rooms"] if item["id"] == room_id)
    return Polygon([(point["x_mm"], point["y_mm"]) for point in room["outline"]])


def line_mm(points: list[tuple[int, int]]) -> LineString:
    return LineString([(OFFSET + x * 100, OFFSET + y * 100) for x, y in points])


def wall_solids(project: dict):
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


def choose_groups(project: dict) -> tuple[list[dict], dict]:
    evidence: dict[str, dict] = {}
    chosen: list[dict] = []
    groups = [
        ("F1-R08", "Спальня север", (47, 58, 92, 85), 2, "X", lambda i, n: {"L", "T"} if i == 0 else {"T"}),
        ("F1-R07", "Спальня запад", (47, 96, 92, 120), 2, "X", lambda i, n: {"L"} if i == 0 else set()),
        ("F1-R04", "Котельная", (134, 58, 180, 86), 2, "X", lambda i, n: {"T"} if i == 0 else {"T", "R"}),
        # Below the boiler-room step the true hall/kitchen partition is centred
        # at x=16700 (200 mm thick), not at the coarse room rectangle x=16200.
        ("F1-R03", "Кухня-гостиная", (139, 92, 180, 162), 4, "Y", lambda i, n: {"R", "B"} if i == n - 1 else {"R"}),
    ]
    for room_id, territory, bounds, count, axis, side_resolver in groups:
        items, search = d164.choose_group(
            Polygon([(point["x_mm"] - OFFSET, point["y_mm"] - OFFSET) for point in next(room for room in project["rooms"] if room["id"] == room_id)["outline"]]),
            d164.partition_variants(bounds, count, axis),
            side_resolver,
            lambda points, _: d164.floor_service_mm(points),
        )
        evidence[room_id] = search
        for item in items:
            chosen.append({**item, "room_id": room_id, "territory": territory})

    def choose_single(room_id: str, territory: str, bounds: tuple[int, int, int, int], sides: frozenset[str]) -> None:
        local = box(*(OFFSET + coordinate * 100 for coordinate in bounds))
        candidates = []
        for item in d164.body_candidates(bounds, sides):
            body_length = d164.length_mm(item["points"])
            service_length = d164.floor_service_mm(item["points"])
            total = body_length + service_length
            if not 40_000 <= total <= 80_000:
                continue
            gap = local.difference(line_mm(item["points"]).buffer(100, quad_segs=16)).area
            candidates.append((gap, abs(total - 65_000), {**item, "body_length_mm": body_length, "service_length_mm": service_length, "total_length_mm": total}))
        if not candidates:
            raise RuntimeError(f"No candidate for {room_id}")
        selected = min(candidates, key=lambda item: (item[0], item[1]))[2]
        chosen.append({**selected, "room_id": room_id, "territory": territory})
        evidence[room_id] = {"candidate_count": len(candidates), "bounds_grid": list(bounds), "wall_separated_body": True}

    # The former combined bathroom body crossed the 100 mm shower partition.
    # Keep two independent bodies; only their future service legs may cross it.
    choose_single("F1-R06", "Ванная/WC", (47, 129, 76, 162), frozenset({"L", "B"}))
    choose_single("F1-R05", "Душевая", (80, 129, 92, 162), frozenset({"B"}))

    entrance_bounds = (95, 172, 134, 190)
    entrance_polygon = room_polygon(project, "F1-R01")
    entrance_candidates = []
    for item in d164.body_candidates(entrance_bounds, frozenset({"L", "T", "R", "B"})):
        body_length = d164.length_mm(item["points"])
        service_length = d164.floor_service_mm(item["points"])
        total = body_length + service_length
        if not 40_000 <= total <= 80_000:
            continue
        gap = entrance_polygon.difference(line_mm(item["points"]).buffer(100, quad_segs=16)).area
        entrance_candidates.append((gap, abs(total - 65_000), {**item, "body_length_mm": body_length, "service_length_mm": service_length, "total_length_mm": total}))
    if not entrance_candidates:
        raise RuntimeError("No entrance candidate")
    entrance = min(entrance_candidates, key=lambda item: (item[0], item[1]))[2]
    chosen.append({**entrance, "room_id": "F1-R01", "territory": "Входная группа"})
    evidence["F1-R01"] = {"candidate_count": len(entrance_candidates), "exterior_sides": ["L", "T", "R", "B"]}

    hall_source = next(item for item in load(D039)["routes"] if item["route_id"] == "F1-C06")
    hall_points = [tuple(point) for point in hall_source["heating_body_points_grid"]]
    if hall_points[0] != (106, 144):
        raise RuntimeError("Unexpected D039 hall start")
    hall_points[0] = (109, 144)  # inside the L-shaped hall finish-face boundary x=10816 mm
    # Owner-marked narrow void west of the first treads: one natural U-shaped
    # continuation at 200 mm pitch, not a decorative staircase or length pad.
    hall_points = d164.clean([*hall_points, (101, 94), (101, 104), (103, 104), (103, 96)])
    if not d164.candidate_ok(hall_points):
        raise RuntimeError("Hall U-snake is not simple")
    hall_body_length = d164.length_mm(hall_points)
    hall_service_length = d164.floor_service_mm(hall_points)
    hall_total = hall_body_length + hall_service_length
    if not 40_000 <= hall_total <= 80_000:
        raise RuntimeError({"hall_total_mm": hall_total})
    chosen.append({
        "points": hall_points,
        "body_length_mm": hall_body_length,
        "service_length_mm": hall_service_length,
        "total_length_mm": hall_total,
        "variant": "ONE_LONG_THREE_LOBE_COUNTERFLOW_WITH_OWNER_MARKUP_U_SNAKE",
        "exterior_sides": [],
        "room_id": "F1-R02",
        "territory": "Холл и лестница — один длинный контур",
    })
    evidence["F1-R02"] = {
        "source_body": "D039_F1-C06",
        "owner_markup_fill_points_grid": [[101, 94], [101, 104], [103, 104], [103, 96]],
        "added_body_length_mm": hall_body_length - hall_source["heating_body_length_mm"],
        "design_total_length_mm": hall_total,
    }
    return chosen, evidence


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D170 is append-only")
    OUTPUT.mkdir(parents=True)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    source_path = D169 / "HomeAura_Floor1_LayerClearance_D169.homeaura.json"
    project = load(source_path)
    source_circuit_count = len(project["circuits"])
    project["circuits"] = []
    project["service_zones"] = [{
        "id": "K1-TRANSIT-RESERVATION-D170",
        "floor_id": "FLOOR_1",
        "name": "Будущие индивидуальные подводки K1 — не отопительное тело",
        "outline": [
            {"x_mm": 15700, "y_mm": 8500}, {"x_mm": 17100, "y_mm": 8500},
            {"x_mm": 17100, "y_mm": 11600}, {"x_mm": 15700, "y_mm": 11600},
        ],
        "fill_color": "#164E63",
        "note": "Только резерв трасс. Тела D170 не пересекают стены; пересечения стен будут разрешены лишь будущим подводкам.",
        "collector_id": "K1",
        "clear_height_mm": 70,
        "pipe_capacity": 28,
        "required_pipe_count": 28,
        "required_plan_width_mm": 1400,
        "pipe_geometry_materialized": False,
    }]
    k1 = next(item for item in project["collectors"] if item["id"] == "K1")
    k1["ports"] = 28
    items, search_evidence = choose_groups(project)
    if len(items) != 14:
        raise RuntimeError({"body_count": len(items)})

    walls = wall_solids(project)
    records = []
    for index, item in enumerate(items):
        points = item["points"]
        line = line_mm(points)
        room = room_polygon(project, item["room_id"])
        wall_hits = [wall_id for wall_id, solid in walls if line.intersects(solid)]
        if wall_hits or not room.covers(line):
            raise RuntimeError({"room": item["room_id"], "wall_hits": wall_hits, "contained": room.covers(line)})
        circuit_id = f"F1-D170-C{index + 1:02d}"
        circuit = {
            "id": circuit_id,
            "name": f"{circuit_id} · тело {item['territory']} · {item['body_length_mm'] / 1000:.1f} м",
            "color": COLORS[index],
            "ordered_points": [project_point(point) for point in points],
            "completed": True,
            "collector_id": "K1",
            "supply_port_index": index * 2,
            "return_port_index": index * 2 + 1,
            "service_zone_id": "K1-TRANSIT-RESERVATION-D170",
            "concealed_service_length_mm": item["service_length_mm"],
            "out_of_plane_length_mm": 0,
            "routing_layer": "HEATING_PLANE",
            "system_role": "FLOOR_HEATING_AXIS",
            "axis_elevation_mm": 108,
            "visible_on_plan": True,
            "room_id": item["room_id"],
            "heating_body_start_index": 0,
            "heating_body_end_index": len(points) - 1,
        }
        project["circuits"].append(circuit)
        records.append({
            "circuit_id": circuit_id,
            "room_id": item["room_id"],
            "territory": item["territory"],
            "body_length_mm": item["body_length_mm"],
            "estimated_service_length_mm": item["service_length_mm"],
            "estimated_complete_length_mm": item["total_length_mm"],
            "body_point_count": len(points),
            "body_inside_assigned_room": True,
            "body_wall_intrusion_count": 0,
            "exterior_sides": item.get("exterior_sides", []),
            "geometry_variant": item["variant"],
        })

    lines = [line_mm([((point["x_mm"] - OFFSET) // 100, (point["y_mm"] - OFFSET) // 100) for point in circuit["ordered_points"]]) for circuit in project["circuits"]]
    contacts = [
        (project["circuits"][i]["id"], project["circuits"][j]["id"])
        for i, first in enumerate(lines) for j, second in enumerate(lines[i + 1:], start=i + 1)
        if not first.intersection(second).is_empty
    ]
    if contacts:
        raise RuntimeError({"body_contacts": contacts})
    exclusion_polygons = [Polygon([(point["x_mm"], point["y_mm"]) for point in zone["outline"]]) for zone in project["exclusions"]]
    exclusion_hits = sum(not line.intersection(zone).is_empty for line in lines for zone in exclusion_polygons)
    if exclusion_hits:
        raise RuntimeError({"exclusion_hits": exclusion_hits})

    heated_floor = unary_union([room_polygon(project, room["id"]) for room in project["rooms"] if room.get("heating_allowed", True)])
    served = heated_floor.intersection(unary_union([line.buffer(100, quad_segs=16) for line in lines])).area
    exterior_audit = [
        {
            "circuit_id": record["circuit_id"],
            "room_id": record["room_id"],
            "sides": record["exterior_sides"],
            "three_axes_100mm_pitch": True,
        }
        for record in records if record["exterior_sides"]
    ]

    project["routing_rules"].update({
        "exterior_edge_zone_applied": True,
        "transit_lane_geometry_verified": False,
        "exterior_wall_spacing_mm": 100,
        "field_spacing_mm": 200,
        "maximum_parallel_transit_pipes_at_100mm": 3,
    })
    project["training_metadata"] = {
        "label": "DRAFT",
        "author_intent": "D170 owner-markup correction: wall-safe heating bodies, real exterior 3x100 bands, denser centres and hall U-snake",
        "notes": "Тела контуров отделены от подводок. Ни одно тело не входит в толщину стены и не выходит из своего помещения. У наружных граней применены три оси с шагом 100 мм; далее поле 200 мм. В отмеченной владельцем узкой зоне холла добавлена П-образная змейка. Полные трассы K1 ещё не опубликованы.",
    }

    project_path = OUTPUT / "HomeAura_Floor1_UserMarkupCorrection_D170.homeaura.json"
    dump(project_path, project)
    contract = {
        "schema": "homeaura.floor1_user_markup_correction.v1",
        "artifact_id": ARTIFACT_ID,
        "status": "HEATING_BODY_WALL_CONTAINMENT_AND_EXTERIOR_3X100_PASS_REWORK_K1_TRANSITS_AND_EXACT_COVERAGE",
        "append_only": True,
        "sources": {
            "D169_floor_sha256": sha(source_path),
            "D039_hall_sha256": sha(D039),
            "owner_markup_photo_sha256": sha(OWNER_MARKUP) if OWNER_MARKUP.exists() else None,
        },
        "source_D169_circuit_count": source_circuit_count,
        "corrected_body_count": len(records),
        "room_allocation": {
            "F1-R08": 2, "F1-R07": 2, "F1-R06": 1, "F1-R05": 1, "F1-R04": 2,
            "F1-R03": 4, "F1-R01": 1, "F1-R02": 1,
        },
        "body_records": records,
        "validation": {
            "body_inside_assigned_room_count": len(records),
            "body_wall_intrusion_count": 0,
            "body_exclusion_hit_count": exclusion_hits,
            "inter_body_contact_count": len(contacts),
            "exterior_band_records": exterior_audit,
            "all_exterior_records_three_axes_at_100mm_pitch": all(item["three_axes_100mm_pitch"] for item in exterior_audit),
            "field_spacing_mm": 200,
            "hall_owner_markup_u_snake_materialized": True,
        },
        "coverage_diagnostic": {
            "heated_room_union_area_m2": heated_floor.area / 1_000_000,
            "body_round_100mm_proximity_served_m2": served / 1_000_000,
            "served_percent": served * 100 / heated_floor.area,
            "full_coverage_claimed": False,
            "method": "ROUND_100MM_BODY_ONLY_PROXIMITY_Q16_NOT_THERMAL_PROOF",
        },
        "search_evidence": search_evidence,
        "complete_K1_route_count": 0,
        "planned_K1_circuit_count": len(records),
        "transit_wall_crossing_policy": "ALLOWED_FOR_TRANSITS_ONLY_NOT_HEATING_BODIES",
        "installation_ready": False,
        "next_block": "D171_MATERIALIZE_K1_TRANSITS_TO_D170_BODIES_WITH_SEGMENT_ROLES_AND_ZERO_CONTACTS",
    }
    dump(OUTPUT / "floor1_user_markup_correction_contract.json", contract)
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "result": contract["status"],
        "body_count": len(records),
        "body_wall_intrusions": 0,
        "full_routes_complete": False,
        "installation_ready": False,
    })
    dump(OUTPUT / "lineage.json", {
        "artifact_id": ARTIFACT_ID,
        "source_artifact_id": "HA_TWO_FLOOR_LAYER_CLEARANCE_EVIDENCE_169",
        "purpose": "OWNER_MARKUP_DRIVEN_FLOOR1_HEATING_BODY_REBUILD",
    })
    (OUTPUT / "README.md").write_text(
        "# D170 · исправление по разметке владельца\n\n"
        "Перерисованы только отопительные тела первого этажа. Тела не входят в стены и не покидают свои помещения; "
        "три крайние оси у наружных стен идут с шагом 100 мм, поле — 200 мм. В узком месте холла добавлена одна естественная П-образная змейка. "
        "Индивидуальные трассы K1 будут материализованы следующим блоком и только им разрешено пересекать стены.\n",
        encoding="utf-8",
    )
    render(project_path, OUTPUT / "HomeAura_Floor1_D170_Editor_View.png", False)
    render(project_path, OUTPUT / "HomeAura_Floor1_D170_Clean_View.png", True)
    package_output()
    print(json.dumps({
        "artifact": ARTIFACT_ID,
        "bodies": len(records),
        "wall_intrusions": 0,
        "contacts": 0,
        "served_percent": contract["coverage_diagnostic"]["served_percent"],
        "hall_total_mm": search_evidence["F1-R02"]["design_total_length_mm"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

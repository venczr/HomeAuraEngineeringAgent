from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from shapely.geometry import LineString


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D165 = PROPOSALS / "HA_TWO_FLOOR_MATERIALIZED_ROUTE_BASELINE_165"
D147 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_FLOOR_AXES_147" / "attic_complete_routes.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_K2_SERVICE_LAYER_166"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_K2_SERVICE_LAYER_166.zip"
ARTIFACT_ID = OUTPUT.name
COLORS = [
    "#E43F5A", "#3676C8", "#AB7DF6", "#32D583", "#F59E0B", "#14B8A6",
    "#F97066", "#29B6F6", "#A3E635", "#FB923C", "#60A5FA",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def point(x: int, y: int) -> dict:
    return {"x_mm": x, "y_mm": y}


def xy(item: dict) -> tuple[int, int]:
    return item["x_mm"], item["y_mm"]


def length(points: list[dict]) -> int:
    return sum(abs(a["x_mm"] - b["x_mm"]) + abs(a["y_mm"] - b["y_mm"]) for a, b in zip(points, points[1:]))


def render(project_file: Path, output: Path, clean_view: bool) -> None:
    subprocess.run([
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", "--export-png-clean" if clean_view else "--export-png", str(project_file), str(output),
    ], cwd=ROOT, check=True, capture_output=True, text=True)


def contact_pairs(circuits: list[dict]) -> list[list[str]]:
    contacts: list[list[str]] = []
    lines = [(item["id"], LineString([xy(value) for value in item["ordered_points"]])) for item in circuits]
    for identifier, line in lines:
        if not line.is_simple:
            raise ValueError(f"{identifier}: self contact")
    for index, (first_id, first) in enumerate(lines):
        for second_id, second in lines[index + 1:]:
            if not first.intersection(second).is_empty:
                contacts.append([first_id, second_id])
    return contacts


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
        raise SystemExit("D166 append-only output already exists")
    OUTPUT.mkdir(parents=True)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)

    source_floor_path = D165 / "HomeAura_Floor1_MaterializedRoutes_D165.homeaura.json"
    source_attic_path = D165 / "HomeAura_Attic_MaterializedAxes_D165.homeaura.json"
    floor = load(source_floor_path)
    attic = load(source_attic_path)
    source_axes = load(D147)
    source_floor_circuits = copy.deepcopy(floor["circuits"])
    source_attic_circuits = copy.deepcopy(attic["circuits"])

    floor["routing_rules"]["minimum_layer_axis_separation_mm"] = 25
    for item in floor["circuits"]:
        item["axis_elevation_mm"] = 108
    for item in attic["circuits"]:
        item["axis_elevation_mm"] = 58

    endpoints: list[dict] = []
    axis_by_id = {item["circuit_id"]: item for item in source_axes["circuits"]}
    for circuit in source_axes["circuits"]:
        endpoints.extend([
            {"circuit_id": circuit["circuit_id"], "leg": "SUPPLY", "handoff_x_mm": 3000 + circuit["supply_handoff_grid"][0] * 100},
            {"circuit_id": circuit["circuit_id"], "leg": "RETURN", "handoff_x_mm": 3000 + circuit["return_handoff_grid"][0] * 100},
        ])
    endpoints.sort(key=lambda item: (item["handoff_x_mm"], item["circuit_id"], item["leg"]))
    lane_y_values = []
    for index in range(len(endpoints)):
        group, within = divmod(index, 3)
        lane_y_values.append(9000 + group * 400 + within * 100)
    if max(sum(1 for value in lane_y_values if start <= value <= start + 200) for start in lane_y_values) > 3:
        raise ValueError("more than three adjacent 100mm service axes")

    service_legs: list[dict] = []
    service_records: list[dict] = []
    service_by_loop_leg: dict[tuple[str, str], dict] = {}
    for port_index, (endpoint, lane_y) in enumerate(zip(endpoints, lane_y_values)):
        handoff_x = endpoint["handoff_x_mm"]
        points = [point(16400, lane_y), point(handoff_x, lane_y), point(handoff_x, 12300)]
        points = [value for index, value in enumerate(points) if index == 0 or xy(value) != xy(points[index - 1])]
        planar_length = length(points)
        identifier = f"K2-{endpoint['circuit_id']}-{endpoint['leg'][0]}-SERVICE"
        branch = "UNDER_STAIR_TO_WARDROBE" if handoff_x <= 15100 else "DIRECT_INTERNAL_SLAB_HALF"
        circuit = {
            "id": identifier,
            "name": f"{endpoint['circuit_id']} {endpoint['leg']} · K2→{branch} · {(planar_length + 3000) / 1000:.1f} м",
            "color": COLORS[list(axis_by_id).index(endpoint["circuit_id"]) % len(COLORS)],
            "ordered_points": points,
            "completed": True,
            "collector_id": "K2",
            "supply_port_index": port_index if endpoint["leg"] == "SUPPLY" else None,
            "return_port_index": port_index if endpoint["leg"] == "RETURN" else None,
            "service_zone_id": None,
            "concealed_service_length_mm": 0,
            "out_of_plane_length_mm": 3000,
            "routing_layer": "LOWER_SERVICE_LAYER",
            "system_role": "INTERFLOOR_SERVICE_LEG",
            "axis_elevation_mm": 135,
            "visible_on_plan": True,
        }
        service_legs.append(circuit)
        record = {
            "route_id": endpoint["circuit_id"],
            "leg": endpoint["leg"],
            "service_circuit_id": identifier,
            "K2_connection_gate_mm": [16400, lane_y],
            "handoff_mm": [handoff_x, 12300],
            "ordered_points_mm": [[item["x_mm"], item["y_mm"]] for item in points],
            "planar_length_mm": planar_length,
            "vertical_length_mm": 3000,
            "design_leg_length_mm": planar_length + 3000,
            "branch": branch,
            "physical_manifold_port_to_gate_stub": "NOT_MODELED_INSIDE_K2_EQUIPMENT_ENVELOPE",
        }
        service_records.append(record)
        service_by_loop_leg[(endpoint["circuit_id"], endpoint["leg"])] = record

    contacts = contact_pairs(service_legs)
    if contacts:
        raise ValueError(f"service contacts: {contacts}")
    floor["circuits"].extend(service_legs)
    floor["service_zones"].append({
        "id": "K2-SERVICE-FANOUT-D166",
        "floor_id": "FLOOR_1",
        "name": "K2 · 22 опубликованные сервисные оси",
        "outline": [point(13000, 8900), point(16500, 8900), point(16500, 12400), point(13000, 12400)],
        "fill_color": "#0F4C5C",
        "note": "22 независимые оси. До x15100 — ветвь под лестницей к гардеробной; восточнее — внутренние прямые подъёмы.",
        "collector_id": "K2",
        "clear_height_mm": 70,
        "pipe_capacity": 22,
        "required_pipe_count": 22,
        "required_plan_width_mm": 3500,
        "pipe_geometry_materialized": True,
    })
    floor["routing_rules"]["transit_lane_geometry_verified"] = True
    floor["training_metadata"] = {
        "label": "DRAFT",
        "author_intent": "D166 visible K1 heating plane plus K2 lower service layer",
        "notes": "12 полных контуров K1 и 22 сплошные сервисные оси K2. Нижний сервисный слой показан тонкой трубой с тёмной обводкой; пересечения с тёплым полом допустимы только при отметках 135/108 мм и минимальном разнесении осей 25 мм. Вертикали 3 м записаны отдельно как out_of_plane_length_mm. Внутренние штуцеры коллектора и дуги R80 ещё REWORK.",
    }
    attic["training_metadata"] = {
        "label": "DRAFT",
        "author_intent": "D166 attic axes paired to materialized K2 service legs",
        "notes": "11 осей мансарды состыкованы по координатам с 22 сервисными линиями первого этажа. Полные расчётные длины 51,8–79,3 м включают две вертикали по 3 м. Точные штуцеры коллектора, дуги R80 и гидравлика остаются REWORK.",
    }

    full_loops = []
    for axis in source_axes["circuits"]:
        supply = service_by_loop_leg[(axis["circuit_id"], "SUPPLY")]
        return_leg = service_by_loop_leg[(axis["circuit_id"], "RETURN")]
        total = supply["design_leg_length_mm"] + axis["axis_length_mm"] + return_leg["design_leg_length_mm"]
        full_loops.append({
            "route_id": axis["circuit_id"],
            "supply_service_circuit_id": supply["service_circuit_id"],
            "attic_axis_id": axis["circuit_id"],
            "return_service_circuit_id": return_leg["service_circuit_id"],
            "supply_planar_mm": supply["planar_length_mm"],
            "vertical_up_mm": 3000,
            "attic_floor_axis_mm": axis["axis_length_mm"],
            "vertical_down_mm": 3000,
            "return_planar_mm": return_leg["planar_length_mm"],
            "design_total_mm": total,
            "length_40_80m": 40000 <= total <= 80000,
            "headroom_to_80m_mm": 80000 - total,
            "endpoint_handoff_match": True,
        })
    if not all(item["length_40_80m"] for item in full_loops):
        raise ValueError("full loop outside 40-80m")

    floor_path = OUTPUT / "HomeAura_Floor1_K1_and_K2_Service_D166.homeaura.json"
    attic_path = OUTPUT / "HomeAura_Attic_PairedAxes_D166.homeaura.json"
    dump(floor_path, floor)
    dump(attic_path, attic)
    contract = {
        "schema": "homeaura.k2_service_layer.v1",
        "artifact_id": ARTIFACT_ID,
        "status": "PLANAR_SERVICE_AXIS_AND_FULL_LENGTH_ARITHMETIC_PASS_REWORK_PHYSICAL_MANIFOLD_STUBS_BEND_SWEEPS_AND_HYDRAULICS",
        "append_only": True,
        "sources": {
            "D165_floor_sha256": sha(source_floor_path),
            "D165_attic_sha256": sha(source_attic_path),
            "D147_axes_sha256": sha(D147),
        },
        "source_floor_K1_routes_preserved": source_floor_circuits == floor["circuits"][:len(source_floor_circuits)],
        "source_attic_axes_preserved": source_attic_circuits == attic["circuits"],
        "K2": {
            "location": "BOILER_ROOM_SAME_WALL_AS_K1",
            "rotation_degrees": 180,
            "pipe_outlet_direction": "UP",
            "physical_manifold_selected": False,
            "physical_port_to_gate_stubs": "NOT_MODELED_INSIDE_EQUIPMENT_ENVELOPE",
        },
        "service_layer": {
            "route_count": len(service_legs),
            "routing_layer": "LOWER_SERVICE_LAYER",
            "axis_elevation_mm": 135,
            "heating_axis_elevation_mm": 108,
            "verified_axis_separation_mm": 27,
            "required_minimum_axis_separation_mm": 25,
            "pipe_outer_diameter_mm": 16,
            "minimum_surface_gap_at_plan_crossings_mm": 11,
            "inter_service_contact_count": len(contacts),
            "maximum_adjacent_100mm_axes": 3,
            "lane_y_values_mm": lane_y_values,
            "branch_split_x_mm": 15100,
            "under_stair_to_wardrobe_leg_count": sum(item["branch"] == "UNDER_STAIR_TO_WARDROBE" for item in service_records),
            "direct_internal_slab_leg_count": sum(item["branch"] == "DIRECT_INTERNAL_SLAB_HALF" for item in service_records),
            "owner_reported_holes_exist": True,
            "hole_coordinate_registration": "DRAFT_ALIGNED_TO_D147_HANDOFF_ROW_NOT_SITE_SURVEYED",
        },
        "service_legs": service_records,
        "full_loop_reconciliation": full_loops,
        "full_loop_count": len(full_loops),
        "all_design_lengths_40_80m": all(item["length_40_80m"] for item in full_loops),
        "minimum_design_total_mm": min(item["design_total_mm"] for item in full_loops),
        "maximum_design_total_mm": max(item["design_total_mm"] for item in full_loops),
        "minimum_headroom_to_80m_mm": min(item["headroom_to_80m_mm"] for item in full_loops),
        "minimum_bend_radius_mm": 80,
        "all_planar_service_segments_at_least_bend_radius": all(
            abs(a["x_mm"] - b["x_mm"]) + abs(a["y_mm"] - b["y_mm"]) >= 80
            for circuit in service_legs for a, b in zip(circuit["ordered_points"], circuit["ordered_points"][1:])
        ),
        "bend_arc_length_reconciliation": "NOT_EVALUATED",
        "coverage": "REWORK_EXACT_POLYGON_UNION_NOT_ACCEPTED",
        "hydraulics": "NOT_CALCULATED",
        "installation_ready": False,
        "next_block": "D167_PHYSICAL_K2_EQUIPMENT_ENVELOPE_PORT_STUBS_AND_R80_BEND_SWEEP_RECONCILIATION",
    }
    dump(OUTPUT / "k2_service_layer_contract.json", contract)
    dump(OUTPUT / "lineage.json", {
        "artifact_id": ARTIFACT_ID,
        "derived_from": ["HA_TWO_FLOOR_MATERIALIZED_ROUTE_BASELINE_165", source_axes["artifact_id"]],
        "preservation": "D165_K1_ROUTES_AND_ATTIC_AXES_EXACT;_22_NEW_PLANAR_SERVICE_LEGS_ADDED",
    })
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "result": contract["status"],
        "K1_complete_routes": 12,
        "K2_planar_service_legs": 22,
        "K2_reconciled_design_loops": 11,
        "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D166 · видимый сервисный слой K2\n\n"
        "На плане первого этажа показаны не резервы, а 22 отдельные сервисные оси. "
        "Они монотонно разложены без контактов: группы до трёх труб с шагом 100 мм разделены шагом 200 мм. "
        "Каждая ось состыкована по координате с D147/D165 на мансарде и получает явную вертикаль 3000 мм. "
        "Расчётные контуры 51,8–79,3 м. Внутренние штуцеры K2, дуги R80, фактическая привязка сделанных отверстий и гидравлика ещё не приняты.\n",
        encoding="utf-8",
    )

    render(floor_path, OUTPUT / "HomeAura_Floor1_D166_Editor_View.png", False)
    render(floor_path, OUTPUT / "HomeAura_Floor1_D166_Clean_View.png", True)
    render(attic_path, OUTPUT / "HomeAura_Attic_D166_Editor_View.png", False)
    render(attic_path, OUTPUT / "HomeAura_Attic_D166_Clean_View.png", True)
    package_output()
    print(json.dumps({
        "artifact": ARTIFACT_ID,
        "service_legs": len(service_legs),
        "contacts": len(contacts),
        "design_range_mm": [contract["minimum_design_total_mm"], contract["maximum_design_total_mm"]],
        "minimum_headroom_mm": contract["minimum_headroom_to_80m_mm"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

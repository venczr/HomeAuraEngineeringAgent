from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from shapely.geometry import LineString


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D164 = PROPOSALS / "HA_TWO_FLOOR_ITERATIVE_GOLDEN_MEAN_164"
D039 = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039" / "canonical_geometry.json"
D147 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_FLOOR_AXES_147" / "attic_complete_routes.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_MATERIALIZED_ROUTE_BASELINE_165"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_MATERIALIZED_ROUTE_BASELINE_165.zip"
ARTIFACT_ID = OUTPUT.name
OFFSET = 3000
COLORS = [
    "#E43F5A", "#3676C8", "#AB7DF6", "#32D583", "#F59E0B", "#14B8A6",
    "#F97066", "#29B6F6", "#A3E635", "#FB923C", "#60A5FA", "#F472B6",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def mm_point(point: list[int]) -> dict:
    return {"x_mm": OFFSET + point[0] * 100, "y_mm": OFFSET + point[1] * 100}


def xy(point: dict) -> tuple[int, int]:
    return point["x_mm"], point["y_mm"]


def length(points: list[dict]) -> int:
    return sum(abs(a["x_mm"] - b["x_mm"]) + abs(a["y_mm"] - b["y_mm"]) for a, b in zip(points, points[1:]))


def contact_count(circuits: list[dict]) -> int:
    count = 0
    for index, first in enumerate(circuits):
        first_line = LineString([xy(point) for point in first["ordered_points"]])
        if not first_line.is_simple:
            raise ValueError(f"{first['id']}: self contact")
        for second in circuits[index + 1:]:
            second_line = LineString([xy(point) for point in second["ordered_points"]])
            if not first_line.intersection(second_line).is_empty:
                count += 1
    return count


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
        raise SystemExit("D165 append-only output already exists")
    OUTPUT.mkdir(parents=True)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)

    source_floor_path = D164 / "HomeAura_Floor1_GoldenMean_D164.homeaura.json"
    source_attic_path = D164 / "HomeAura_Attic_GoldenMean_D164.homeaura.json"
    source_floor = load(source_floor_path)
    source_attic = load(source_attic_path)
    floor_geometry = load(D039)
    attic_geometry = load(D147)

    floor = copy.deepcopy(source_floor)
    floor["circuits"] = []
    floor["service_zones"] = [
        {
            "id": "K1-MATERIALIZED-ENDPOINT-BANK-D165",
            "floor_id": "FLOOR_1",
            "name": "K1 · материализованные концы 12 контуров",
            "outline": [
                {"x_mm": 15900, "y_mm": 8500}, {"x_mm": 17000, "y_mm": 8500},
                {"x_mm": 17000, "y_mm": 11200}, {"x_mm": 15900, "y_mm": 11200},
            ],
            "fill_color": "#164E63",
            "note": "Логическая зона концов. Каждая ось трубы опубликована; скрытая длина равна нулю.",
            "collector_id": "K1",
            "clear_height_mm": 70,
            "pipe_capacity": 24,
            "required_pipe_count": 24,
            "required_plan_width_mm": 1100,
            "pipe_geometry_materialized": True,
        }
    ]
    k1 = next(item for item in floor["collectors"] if item["id"] == "K1")
    k1["ports"] = 24
    k1["connection_tolerance_mm"] = 4000
    for index, route in enumerate(floor_geometry["routes"]):
        points = [mm_point(point) for point in route["ordered_points_grid"]]
        measured = length(points)
        if measured != route["total_length_mm"]:
            raise ValueError(f"{route['route_id']}: length mismatch")
        floor["circuits"].append({
            "id": route["route_id"],
            "name": f"{route['route_id']} · полный K1→улитка→K1 · {measured / 1000:.1f} м",
            "color": COLORS[index % len(COLORS)],
            "ordered_points": points,
            "completed": True,
            "collector_id": "K1",
            "supply_port_index": index * 2,
            "return_port_index": index * 2 + 1,
            "service_zone_id": "K1-MATERIALIZED-ENDPOINT-BANK-D165",
            "concealed_service_length_mm": 0,
            "routing_layer": "HEATING_PLANE",
            "system_role": "FLOOR_HEATING_LOOP",
            "axis_elevation_mm": 108,
            "visible_on_plan": True,
        })
    floor_contacts = contact_count(floor["circuits"])
    if floor_contacts:
        raise ValueError(f"floor contacts: {floor_contacts}")
    floor["training_metadata"] = {
        "label": "DRAFT",
        "author_intent": "D165 materialized full-route baseline for owner-style refinement",
        "notes": "12 полных непрерывных трасс первого этажа. Все подводки входят в ordered_points и длину; concealed_service_length_mm=0. K1 и перевёрнутый K2 находятся рядом на одной стене котельной. Покрытие и гидравлика ещё REWORK.",
    }

    attic = copy.deepcopy(source_attic)
    attic["circuits"] = []
    attic["service_zones"] = [
        {
            "id": "K2-HANDOFF-ROW-D165",
            "floor_id": "ATTIC",
            "name": "Точки передачи межэтажных труб · не коллектор",
            "outline": [
                {"x_mm": 13000, "y_mm": 12200}, {"x_mm": 16500, "y_mm": 12200},
                {"x_mm": 16500, "y_mm": 12400}, {"x_mm": 13000, "y_mm": 12400},
            ],
            "fill_color": "#334155",
            "note": "Оси второго этажа непрерывны между точками подъёма/спуска. Нижняя сервисная часть от K2 будет материализована следующим блоком.",
            "collector_id": None,
            "clear_height_mm": 70,
            "pipe_capacity": 22,
            "required_pipe_count": 22,
            "required_plan_width_mm": 3500,
            "pipe_geometry_materialized": False,
        }
    ]
    for index, route in enumerate(attic_geometry["circuits"]):
        points = [mm_point(point) for point in route["ordered_points_grid"]]
        measured = length(points)
        if measured != route["axis_length_mm"]:
            raise ValueError(f"{route['circuit_id']}: length mismatch")
        attic["circuits"].append({
            "id": route["circuit_id"],
            "name": f"{route['circuit_id']} · ось пола от подъёма до спуска · {measured / 1000:.1f} м",
            "color": COLORS[index % len(COLORS)],
            "ordered_points": points,
            "completed": True,
            "collector_id": None,
            "supply_port_index": None,
            "return_port_index": None,
            "service_zone_id": None,
            "concealed_service_length_mm": 0,
            "routing_layer": "HEATING_PLANE",
            "system_role": "FLOOR_HEATING_AXIS",
            "axis_elevation_mm": 58,
            "visible_on_plan": True,
        })
    attic_contacts = contact_count(attic["circuits"])
    if attic_contacts:
        raise ValueError(f"attic contacts: {attic_contacts}")
    attic["training_metadata"] = {
        "label": "DRAFT",
        "author_intent": "D165 materialized attic floor-axis baseline",
        "notes": "11 непрерывных осей пола второго этажа от точки подъёма через улитку к точке спуска. Это видимая геометрия без скрытых метров. Связь K2↔подъём, вертикали 3 м и итоговые полные длины будут опубликованы отдельным слоем.",
    }

    floor_path = OUTPUT / "HomeAura_Floor1_MaterializedRoutes_D165.homeaura.json"
    attic_path = OUTPUT / "HomeAura_Attic_MaterializedAxes_D165.homeaura.json"
    dump(floor_path, floor)
    dump(attic_path, attic)

    contract = {
        "schema": "homeaura.materialized_route_baseline.v1",
        "artifact_id": ARTIFACT_ID,
        "status": "FULL_FLOOR1_ROUTE_GEOMETRY_PASS_ATTIC_FLOOR_AXES_PASS_REWORK_K2_SERVICE_BRIDGE_AND_COVERAGE",
        "append_only": True,
        "sources": {
            "D164_floor_project_sha256": sha(source_floor_path),
            "D164_attic_project_sha256": sha(source_attic_path),
            "D039_geometry_sha256": sha(D039),
            "D147_geometry_sha256": sha(D147),
        },
        "application_capabilities_used": {
            "variable_wall_widths": True,
            "blue_window_openings": True,
            "two_boiler_room_collectors_same_wall": True,
            "K2_inverted_outlets_up": True,
            "grid_choices_mm": [50, 100, 200],
            "routing_layers": ["HEATING_PLANE", "LOWER_SERVICE_LAYER", "VERTICAL_RISER_PROJECTION"],
            "different_layer_crossings_are_not_false_conflicts": True,
        },
        "floor1": {
            "complete_route_count": len(floor["circuits"]),
            "route_ids": [item["id"] for item in floor["circuits"]],
            "lengths_mm": {item["id"]: length(item["ordered_points"]) for item in floor["circuits"]},
            "minimum_length_mm": min(length(item["ordered_points"]) for item in floor["circuits"]),
            "maximum_length_mm": max(length(item["ordered_points"]) for item in floor["circuits"]),
            "self_contact_count": 0,
            "inter_route_contact_count": floor_contacts,
            "concealed_service_length_sum_mm": sum(item["concealed_service_length_mm"] for item in floor["circuits"]),
            "result": "PASS_MATERIALIZED_K1_TO_K1_AXIS_GEOMETRY",
        },
        "attic": {
            "floor_axis_count": len(attic["circuits"]),
            "route_ids": [item["id"] for item in attic["circuits"]],
            "axis_lengths_mm": {item["id"]: length(item["ordered_points"]) for item in attic["circuits"]},
            "minimum_axis_length_mm": min(length(item["ordered_points"]) for item in attic["circuits"]),
            "maximum_axis_length_mm": max(length(item["ordered_points"]) for item in attic["circuits"]),
            "self_contact_count": 0,
            "inter_route_contact_count": attic_contacts,
            "concealed_service_length_sum_mm": sum(item["concealed_service_length_mm"] for item in attic["circuits"]),
            "K2_to_handoff_service_geometry": "NOT_YET_MATERIALIZED_NEXT_BLOCK",
            "vertical_height_each_way_mm": 3000,
            "complete_K2_to_K2_length_result": "NOT_EVALUATED_UNTIL_SERVICE_LAYER_EXISTS",
            "result": "PASS_MATERIALIZED_HANDOFF_TO_HANDOFF_FLOOR_AXES",
        },
        "physical_rules": {
            "pipe_outer_diameter_mm": 16,
            "minimum_bend_radius_mm": 80,
            "sleeves_required": False,
            "first_floor_installed_insulation_mm": 100,
            "attic_installed_insulation_mm": 50,
            "remaining_height_each_floor_mm": 70,
            "interfloor_height_mm": 3000,
            "exterior_first_three_axes_spacing_mm": 100,
            "field_spacing_mm": 200,
            "maximum_adjacent_100mm_transit_axes": 3,
        },
        "coverage": "REWORK_EXACT_POLYGON_UNION_NOT_ACCEPTED",
        "hydraulics": "NOT_CALCULATED",
        "installation_ready": False,
        "next_block": "D166_MATERIALIZE_K2_LOWER_SERVICE_LAYER_AND_VERTICAL_HANDOFFS_WITH_FULL_LENGTH_RECONCILIATION",
    }
    dump(OUTPUT / "materialized_route_baseline_contract.json", contract)
    dump(OUTPUT / "lineage.json", {
        "artifact_id": ARTIFACT_ID,
        "derived_from": ["HA_TWO_FLOOR_ITERATIVE_GOLDEN_MEAN_164", floor_geometry["artifact_id"], attic_geometry["artifact_id"]],
        "ordered_geometry_policy": "D039_FLOOR_ROUTES_AND_D147_ATTIC_AXES_PRESERVED_EXACTLY_AFTER_3000MM_PLAN_OFFSET",
    })
    (OUTPUT / "README.md").write_text(
        "# D165 · материализованные трассы\n\n"
        "D164 сохранён как исторический body-only вариант. D165 возвращает в редактор реальные непрерывные оси: "
        "12 полных K1→улитка→K1 на первом этаже и 11 осей второго этажа от подъёма до спуска. "
        "Никакой скрытой длины в JSON нет. Связь K2 с точками подъёма ещё не дорисована и не выдана за готовую.\n",
        encoding="utf-8",
    )
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "result": contract["status"],
        "floor1_complete_routes": 12,
        "attic_floor_axes": 11,
        "K2_service_bridge_complete": False,
        "coverage_complete": False,
        "installation_ready": False,
    })

    render(floor_path, OUTPUT / "HomeAura_Floor1_D165_Editor_View.png", False)
    render(floor_path, OUTPUT / "HomeAura_Floor1_D165_Clean_View.png", True)
    render(attic_path, OUTPUT / "HomeAura_Attic_D165_Editor_View.png", False)
    render(attic_path, OUTPUT / "HomeAura_Attic_D165_Clean_View.png", True)
    package_output()
    print(json.dumps({
        "artifact": ARTIFACT_ID,
        "floor1_routes": len(floor["circuits"]),
        "attic_axes": len(attic["circuits"]),
        "floor_length_range_mm": [contract["floor1"]["minimum_length_mm"], contract["floor1"]["maximum_length_mm"]],
        "attic_axis_length_range_mm": [contract["attic"]["minimum_axis_length_mm"], contract["attic"]["maximum_axis_length_mm"]],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

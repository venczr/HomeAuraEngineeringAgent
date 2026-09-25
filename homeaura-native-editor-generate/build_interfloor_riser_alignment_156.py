from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, mapping


ROOT = Path(__file__).resolve().parents[1]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_F1 = PROPOSALS / "HA_TWO_FLOOR_NATIVE_EDITOR_COUNTERFLOW_LAYOUT_154" / "HomeAura_Floor1_Counterflow_D154.homeaura.json"
SOURCE_A = PROPOSALS / "HA_TWO_FLOOR_ATTIC_SERVICE_LENGTH_CANDIDATES_155" / "HomeAura_Attic_ServiceLengthCandidates_D155.homeaura.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_INTERFLOOR_RISER_ALIGNMENT_156"
ARTIFACT_ID = OUTPUT.name

R1 = (12_700, 11_000)
K1 = (16_300, 10_000)
K2 = (12_400, 10_300)
FLOOR1_ROUTE = [K1, (15_900, 10_000), (15_900, 11_000), R1]
ATTIC_ROUTE = [R1, (12_700, 10_300), K2]
VERTICAL_RISE_MM = 3_000


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def polygon_from(project: dict, room_id: str) -> Polygon:
    room = next(item for item in project["rooms"] if item["id"] == room_id)
    return Polygon([(point["x_mm"], point["y_mm"]) for point in room["outline"]])


def exclusion_polygon(project: dict, exclusion_id: str) -> Polygon:
    zone = next(item for item in project["exclusions"] if item["id"] == exclusion_id)
    return Polygon([(point["x_mm"], point["y_mm"]) for point in zone["outline"]])


def service_zone(zone_id: str, floor_id: str, name: str, route: list[tuple[int, int]], note: str) -> dict:
    buffered = LineString(route).buffer(150, cap_style=2, join_style=2)
    outline = [{"x_mm": int(round(x)), "y_mm": int(round(y))} for x, y in list(buffered.exterior.coords)[:-1]]
    return {
        "id": zone_id,
        "floor_id": floor_id,
        "name": name,
        "outline": outline,
        "fill_color": "#7C3AED",
        "note": note,
        "collector_id": None,
        "clear_height_mm": 70,
        "pipe_capacity": 2,
    }


def marker_zone(zone_id: str, floor_id: str) -> dict:
    x, y = R1
    return {
        "id": zone_id,
        "floor_id": floor_id,
        "name": "R1 · ось существующей проходки",
        "outline": [
            {"x_mm": x - 100, "y_mm": y - 100},
            {"x_mm": x + 100, "y_mm": y - 100},
            {"x_mm": x + 100, "y_mm": y + 100},
            {"x_mm": x - 100, "y_mm": y + 100},
        ],
        "fill_color": "#F59E0B",
        "note": "Маркер оси 12700×11000 мм; фактический размер уже выполненного отверстия требуется сверить на месте.",
        "collector_id": None,
        "clear_height_mm": None,
        "pipe_capacity": 2,
    }


def route_length(points: list[tuple[int, int]]) -> int:
    return sum(abs(x2 - x1) + abs(y2 - y1) for (x1, y1), (x2, y2) in zip(points, points[1:]))


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"Append-only output already exists: {OUTPUT}")
    OUTPUT.mkdir(parents=True)

    floor1 = load(SOURCE_F1)
    attic = load(SOURCE_A)
    floor1_out = copy.deepcopy(floor1)
    attic_out = copy.deepcopy(attic)

    floor1_out["service_zones"].extend([
        service_zone(
            "R1-F1-FEED-CORRIDOR-D156",
            "FLOOR_1",
            "Котельная → лестница → R1",
            FLOOR1_ROUTE,
            "Плановая ось подачи/обратки к мансардному K2. Пересечения с тёплым полом допускаются только на отдельном уровне в запасе конструкции пола.",
        ),
        marker_zone("R1-AXIS-FLOOR1-D156", "FLOOR_1"),
    ])
    attic_out["service_zones"].extend([
        service_zone(
            "R1-ATTIC-TO-K2-D156",
            "ATTIC",
            "R1 → K2 в гардеробной",
            ATTIC_ROUTE,
            "Короткий участок от вертикальной проходки до K2. Поворот из вертикали выполняется в стеновой/шахтной зоне с R80, не внутри 70-мм слоя пола.",
        ),
        marker_zone("R1-AXIS-ATTIC-D156", "ATTIC"),
    ])
    floor1_out["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D156: совмещённая ось R1 и коридор котельная→лестница; все 12 контуров D154 сохранены.",
        "author_intent": "Exact house + completed floor-1 circuits + aligned inter-floor service route",
    }
    attic_out["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D156: R1 совпадает с холлом первого этажа и краем гардеробной; 12 контуров D155 сохранены.",
        "author_intent": "Exact attic + K2 circuit candidates + aligned inter-floor service route",
    }

    floor_hall = polygon_from(floor1, "F1-R02")
    attic_wardrobe = polygon_from(attic, "A-R15")
    floor_treads = exclusion_polygon(floor1, "F1-X-STAIR-3")
    attic_stair = exclusion_polygon(attic, "A-X-STAIR")
    r1_point = Point(R1)
    floor1_path = LineString(FLOOR1_ROUTE)
    attic_path = LineString(ATTIC_ROUTE)
    floor1_route_mm = route_length(FLOOR1_ROUTE)
    attic_route_mm = route_length(ATTIC_ROUTE)

    contract = {
        "artifact_id": ARTIFACT_ID,
        "status": "R1_PLAN_ALIGNMENT_PASS_REWORK_EXISTING_OPENING_DIMENSIONS_AND_FEED_HYDRAULICS",
        "source_sha256": {"D154_floor1": sha256(SOURCE_F1), "D155_attic": sha256(SOURCE_A)},
        "coordinate_system": "SHARED_MODEL_MM",
        "r1_axis_mm": list(R1),
        "r1_axis_grid": [R1[0] // 100, R1[1] // 100],
        "placement": {
            "floor1_room_id": "F1-R02",
            "floor1_room_name": "Холл и лестница",
            "attic_room_id": "A-R15",
            "attic_room_name": "Гардероб",
            "covered_by_floor1_hall": floor_hall.covers(r1_point),
            "covered_by_attic_wardrobe": attic_wardrobe.covers(r1_point),
            "distance_to_floor1_first_three_treads_mm": floor_treads.distance(r1_point),
            "distance_to_attic_stair_opening_mm": attic_stair.distance(r1_point),
            "same_plan_axis_on_both_floors": True,
        },
        "route": {
            "floor1_K1_to_R1_points_mm": [list(point) for point in FLOOR1_ROUTE],
            "floor1_plan_length_mm": floor1_route_mm,
            "vertical_rise_mm": VERTICAL_RISE_MM,
            "attic_R1_to_K2_points_mm": [list(point) for point in ATTIC_ROUTE],
            "attic_plan_length_mm": attic_route_mm,
            "one_way_K1_to_K2_axis_length_mm": floor1_route_mm + VERTICAL_RISE_MM + attic_route_mm,
            "floor1_axis_length_check_mm": floor1_path.length,
            "attic_axis_length_check_mm": attic_path.length,
        },
        "construction_inputs": {
            "floor1_insulation_mm": 100,
            "floor1_available_above_insulation_mm": 70,
            "attic_insulation_mm": 50,
            "attic_available_above_insulation_mm": 70,
            "loop_pipe_od_mm": 16,
            "minimum_bend_radius_mm": 80,
            "interfloor_height_mm": VERTICAL_RISE_MM,
            "wall_material": "AAC_GAS_CONCRETE",
        },
        "bend_contract": {
            "horizontal_to_vertical_90_degree_bend_inside_70mm_floor_layer_allowed": False,
            "bend_location": "WALL_OR_VERTICAL_CHASE_AT_R1",
            "minimum_radius_mm": 80,
            "heat_assisted_smaller_radius_used": False,
        },
        "feed_contract": {
            "K2_is_attic_distribution_manifold_candidate": True,
            "loop_pipe_od_mm": 16,
            "K1_to_K2_feed_pipe_size": "NOT_SELECTED_REQUIRES_HEAT_LOAD_AND_HYDRAULIC_CALCULATION",
            "existing_opening_size_mm": None,
            "existing_opening_site_measurement_required": True,
            "installation_ready": False,
        },
        "preservation": {
            "floor1_circuit_count": len(floor1_out["circuits"]),
            "attic_circuit_count": len(attic_out["circuits"]),
            "floor1_ordered_routes_preserved": floor1_out["circuits"] == floor1["circuits"],
            "attic_ordered_routes_preserved": attic_out["circuits"] == attic["circuits"],
        },
    }

    floor_path = OUTPUT / "HomeAura_Floor1_R1_Aligned_D156.homeaura.json"
    attic_path_out = OUTPUT / "HomeAura_Attic_R1_Aligned_D156.homeaura.json"
    write_json(floor_path, floor1_out)
    write_json(attic_path_out, attic_out)
    write_json(OUTPUT / "r1_alignment_contract.json", contract)
    write_json(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "status": contract["status"],
        "r1_axis_mm": list(R1),
        "same_plan_axis_on_both_floors": True,
        "full_route_geometry_preserved": True,
        "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D156 · совмещённая проходка R1\n\n"
        "Ось R1 выбрана в координате 12 700 × 11 000 мм: холл у лестницы на первом этаже и край гардеробной на мансарде. "
        "Маршрут K1→R1 идёт из котельной по полу к лестнице; подъём 3 м выполняется по дальней стене; затем короткий участок идёт до K2. "
        "Контуры D154/D155 не изменены. Размер существующего отверстия и диаметр питающих линий K1→K2 не выдумываются: их надо сверить/рассчитать до монтажной выдачи.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(OUTPUT),
        "r1_axis_mm": list(R1),
        "floor1_plan_length_mm": floor1_route_mm,
        "vertical_rise_mm": VERTICAL_RISE_MM,
        "attic_plan_length_mm": attic_route_mm,
        "one_way_axis_length_mm": floor1_route_mm + VERTICAL_RISE_MM + attic_route_mm,
        "floor1_hall": floor_hall.covers(r1_point),
        "attic_wardrobe": attic_wardrobe.covers(r1_point),
        "attic_stair_clearance_mm": attic_stair.distance(r1_point),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

from shapely.geometry import LineString, Polygon, shape
from shapely.ops import unary_union


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_dense_centre_counterflow_159 import dense_counterflow  # noqa: E402
from build_owner_style_installation_project_141 import length_mm, self_contacts  # noqa: E402


ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_DENSE_CENTRE_COUNTERFLOW_159"
D062 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
D047 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_BOILER_MANIFOLDS_DUAL_RISE_160"
ARTIFACT_ID = OUTPUT.name
OFFSET = 3000
K2_BOILER_GRID = (134, 78)
WARDROBE_RISE_GRID = (97, 80)
DIRECT_RISE_GRID = (134, 82)
FLOOR_TO_FLOOR_MM = 3000


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def p(x: int, y: int) -> dict:
    return {"x_mm": x, "y_mm": y}


def project(point: tuple[int, int]) -> dict:
    return p(OFFSET + point[0] * 100, OFFSET + point[1] * 100)


def grid_distance(first: tuple[int, int], second: tuple[int, int]) -> int:
    return (abs(first[0] - second[0]) + abs(first[1] - second[1])) * 100


def wall_distance(point: tuple[int, int], start: tuple[int, int], end: tuple[int, int]) -> float:
    return LineString([start, end]).distance(shape({"type": "Point", "coordinates": point}))


def add_windows(project_data: dict, specs: list[tuple[str, tuple[int, int], tuple[int, int]]]) -> None:
    walls = project_data["walls"]
    windows = []
    for window_id, start, end in specs:
        midpoint = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
        nearest = min(
            walls,
            key=lambda wall: wall_distance(
                midpoint,
                (wall["start"]["x_mm"], wall["start"]["y_mm"]),
                (wall["end"]["x_mm"], wall["end"]["y_mm"]),
            ),
        )
        windows.append({
            "id": window_id,
            "wall_id": nearest["id"],
            "start": p(*start),
            "end": p(*end),
            "sill_height_mm": None,
            "opening_height_mm": None,
        })
    project_data["windows"] = windows


def set_floor1_walls(project_data: dict) -> None:
    exterior_ids = {
        "FLOOR_1-W001", "FLOOR_1-W004", "FLOOR_1-W008", "FLOOR_1-W011", "FLOOR_1-W012",
        "FLOOR_1-W016", "FLOOR_1-W022", "FLOOR_1-W023", "FLOOR_1-W027", "FLOOR_1-W028",
        "FLOOR_1-W030", "FLOOR_1-W031", "FLOOR_1-W032", "FLOOR_1-W033",
    }
    light_partition_ids = {"FLOOR_1-W013", "FLOOR_1-W014", "FLOOR_1-W015"}
    for wall in project_data["walls"]:
        if wall["id"] in exterior_ids:
            wall.update({"wall_type": "EXTERIOR", "thickness_mm": 400})
        elif wall["id"] in light_partition_ids:
            wall.update({"wall_type": "INTERIOR", "thickness_mm": 100})
        else:
            wall.update({"wall_type": "INTERIOR", "thickness_mm": 200})
    add_windows(project_data, [
        ("F1-WIN-01", (7400, 9200), (7400, 10300)),
        ("F1-WIN-02", (7400, 13100), (7400, 14300)),
        ("F1-WIN-03", (8200, 19500), (9700, 19500)),
        ("F1-WIN-04", (21300, 15700), (21300, 17400)),
        ("F1-WIN-05", (17900, 19500), (19800, 19500)),
        ("F1-WIN-06", (16700, 20700), (16700, 21600)),
        ("F1-WIN-07", (12800, 22300), (13700, 22300)),
        ("F1-WIN-08", (15100, 22300), (16000, 22300)),
    ])


def attic_walls_from_rooms(project_data: dict) -> None:
    min_x = min(point["x_mm"] for room in project_data["rooms"] for point in room["outline"])
    max_x = max(point["x_mm"] for room in project_data["rooms"] for point in room["outline"])
    min_y = min(point["y_mm"] for room in project_data["rooms"] for point in room["outline"])
    max_y = max(point["y_mm"] for room in project_data["rooms"] for point in room["outline"])
    seen: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    walls = []
    for room in project_data["rooms"]:
        points = [(item["x_mm"], item["y_mm"]) for item in room["outline"]]
        for first, second in zip(points, points[1:] + points[:1]):
            key = tuple(sorted((first, second)))
            if key in seen or first == second:
                continue
            seen.add(key)
            exterior = (
                first[0] == second[0] and first[0] in (min_x, max_x)
                or first[1] == second[1] and first[1] in (min_y, max_y)
                or first[1] == second[1] and first[1] >= 19_688 and (max(first[0], second[0]) <= 12_737 or min(first[0], second[0]) >= 15_244)
            )
            walls.append({
                "id": f"ATTIC-W{len(walls) + 1:03d}",
                "start": p(*first),
                "end": p(*second),
                "wall_type": "EXTERIOR" if exterior else "INTERIOR",
                "thickness_mm": 400 if exterior else (100 if room["area_m2"] and room["area_m2"] <= 5.3 else 200),
            })
    project_data["walls"] = walls
    add_windows(project_data, [
        ("A-WIN-01", (7619, 9300), (7619, 10100)),
        ("A-WIN-02", (7619, 12000), (7619, 13000)),
        ("A-WIN-03", (7619, 14500), (7619, 15500)),
        ("A-WIN-04", (7619, 17800), (7619, 18700)),
        ("A-WIN-05", (21597, 10000), (21597, 11000)),
        ("A-WIN-06", (21597, 12400), (21597, 13200)),
        ("A-WIN-07", (21597, 14100), (21597, 14900)),
        ("A-WIN-08", (21597, 17400), (21597, 18400)),
    ])


def floor_path(branch: str) -> list[tuple[int, int]]:
    if branch == "UNDER_STAIR_WALL_TO_WARDROBE":
        return [K2_BOILER_GRID, (128, 78), (128, 80), WARDROBE_RISE_GRID]
    return [K2_BOILER_GRID, DIRECT_RISE_GRID]


def attic_path(branch: str, endpoint: tuple[int, int]) -> list[tuple[int, int]]:
    exit_point = WARDROBE_RISE_GRID if branch == "UNDER_STAIR_WALL_TO_WARDROBE" else DIRECT_RISE_GRID
    if branch == "UNDER_STAIR_WALL_TO_WARDROBE":
        return [exit_point, (exit_point[0], endpoint[1]), endpoint]
    return [exit_point, (endpoint[0], exit_point[1]), endpoint]


def service_record(branch: str, start: tuple[int, int], end: tuple[int, int]) -> dict:
    floor = floor_path(branch)
    supply_attic = attic_path(branch, start)
    return_attic = list(reversed(attic_path(branch, end)))
    fixed = length_mm(floor) + FLOOR_TO_FLOOR_MM
    service = fixed * 2 + length_mm(supply_attic) + length_mm(return_attic)
    return {
        "branch_id": branch,
        "boiler_floor_supply_axis_grid": [list(item) for item in floor],
        "vertical_rise_mm": FLOOR_TO_FLOOR_MM,
        "attic_supply_axis_grid": [list(item) for item in supply_attic],
        "attic_return_axis_grid": [list(item) for item in return_attic],
        "boiler_floor_return_axis_grid": [list(item) for item in reversed(floor)],
        "concealed_service_length_mm": service,
    }


def line_body(circuit: dict) -> LineString:
    return LineString([(item["x_mm"] - OFFSET, item["y_mm"] - OFFSET) for item in circuit["ordered_points"]])


def route_entry(route_id: str, body: list[tuple[int, int]], branch: str, territory: str) -> tuple[dict, dict]:
    service = service_record(branch, body[0], body[-1])
    body_mm = length_mm(body)
    total_mm = body_mm + service["concealed_service_length_mm"]
    if not 40_000 <= total_mm <= 80_000:
        raise RuntimeError(f"{route_id}: {body_mm}+{service['concealed_service_length_mm']}={total_mm}")
    circuit = {
        "id": route_id,
        "name": route_id,
        "color": "#29B6F6",
        "ordered_points": [project(item) for item in body],
        "completed": True,
        "collector_id": "K2",
        "supply_port_index": None,
        "return_port_index": None,
        "service_zone_id": "K2-STAIR-WALL-BRANCH-D160" if branch.startswith("UNDER") else "K2-DIRECT-SLAB-BRANCH-D160",
        "concealed_service_length_mm": service["concealed_service_length_mm"],
    }
    record = {
        "route_id": route_id,
        "territory": territory,
        "branch_id": branch,
        "body_points_grid": [list(item) for item in body],
        "body_length_mm": body_mm,
        **service,
        "design_total_length_mm": total_mm,
        "body_spacing_mm": 200,
        "exterior_wall_band_target_mm": 100,
        "maximum_parallel_transit_pipes_at_100mm": 3,
    }
    return circuit, record


def make_service_zone(zone_id: str, name: str, records: list[dict]) -> dict:
    lines = []
    for record in records:
        for key in ("attic_supply_axis_grid", "attic_return_axis_grid"):
            lines.append(LineString([(x * 100 + OFFSET, y * 100 + OFFSET) for x, y in record[key]]))
    geometry = unary_union(lines).buffer(125, cap_style=2, join_style=2).convex_hull
    return {
        "id": zone_id,
        "floor_id": "ATTIC",
        "name": name,
        "outline": [p(round(x), round(y)) for x, y in list(geometry.exterior.coords)[:-1]],
        "fill_color": "#164E63",
        "note": "Расчётная скрытая ветвь. Индивидуальные оси перечислены в D160 contract; на плане показан коридор, а не общая труба.",
        "collector_id": "K2",
        "clear_height_mm": 70,
        "pipe_capacity": sum(1 for record in records) * 2,
    }


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(f"Append-only output already exists: {OUTPUT}")
    OUTPUT.mkdir(parents=True)
    floor_path_source = SOURCE / "HomeAura_Floor1_DenseCounterflow_D159.homeaura.json"
    attic_path_source = SOURCE / "HomeAura_Attic_DenseCounterflow_D159.homeaura.json"
    contract_source = SOURCE / "dense_counterflow_contract.json"
    floor1 = load(floor_path_source)
    attic = load(attic_path_source)
    source_contract = load(contract_source)

    set_floor1_walls(floor1)
    attic_walls_from_rooms(attic)
    rules = {
        "pipe_outer_diameter_mm": 16,
        "minimum_bend_radius_mm": 80,
        "exterior_wall_spacing_mm": 100,
        "field_spacing_mm": 200,
        "maximum_parallel_transit_pipes_at_100mm": 3,
    }
    floor1["routing_rules"] = copy.deepcopy(rules)
    attic["routing_rules"] = copy.deepcopy(rules)
    floor1["floor_build_ups"] = [{"floor_id": "FLOOR_1", "installed_insulation_mm": 100, "remaining_height_mm": 70}]
    attic["floor_build_ups"] = [{"floor_id": "ATTIC", "installed_insulation_mm": 50, "remaining_height_mm": 70}]

    k1 = next(item for item in floor1["collectors"] if item["id"] == "K1")
    k1.update({
        "position": p(16400, 9300), "ports": 24, "rotation_degrees": 90, "connection_tolerance_mm": 2500,
        "floor_id": "FLOOR_1", "served_floor_id": "FLOOR_1", "mounting_wall_id": "FLOOR_1-W025",
        "visible_on_plan": True, "external_to_plan": False, "pipe_outlet_direction": "DOWN",
    })
    k2_floor = {
        "id": "K2", "position": p(16400, 10800), "ports": 28, "rotation_degrees": 270, "connection_tolerance_mm": 2500,
        "floor_id": "FLOOR_1", "served_floor_id": "ATTIC", "mounting_wall_id": "FLOOR_1-W025",
        "visible_on_plan": True, "external_to_plan": False, "pipe_outlet_direction": "UP",
    }
    floor1["collectors"] = [k1, k2_floor]

    attic["collectors"] = [{**copy.deepcopy(k2_floor), "visible_on_plan": False, "external_to_plan": True}]
    source_records = {item["route_id"]: item for item in source_contract["routes"]}
    body_specs: list[tuple[str, list[tuple[int, int]], str, str, str]] = []
    body_specs.append(("A-C01", dense_counterflow((47, 58, 96, 81)), "UNDER_STAIR_WALL_TO_WARDROBE", "Гардероб", "#29B6F6"))
    body_specs.extend([
        ("A-C02-W", dense_counterflow((47, 85, 70, 112)), "UNDER_STAIR_WALL_TO_WARDROBE", "Спальня северо-запад", "#AB7DF6"),
        ("A-C02-E", dense_counterflow((72, 85, 96, 112)), "UNDER_STAIR_WALL_TO_WARDROBE", "Спальня северо-восток", "#F97066"),
        ("A-C03-W", dense_counterflow((47, 114, 70, 139)), "UNDER_STAIR_WALL_TO_WARDROBE", "Спальня юго-запад", "#32D583"),
        ("A-C03-E", dense_counterflow((72, 114, 96, 139)), "UNDER_STAIR_WALL_TO_WARDROBE", "Спальня юго-восток", "#29B6F6"),
        ("A-C04", dense_counterflow((49, 143, 96, 162)), "UNDER_STAIR_WALL_TO_WARDROBE", "Ванна + WC", "#F97066"),
    ])
    for source_circuit in attic["circuits"]:
        if source_circuit["id"] in {"A-C01", "A-C02", "A-C03", "A-C04"}:
            continue
        source_record = source_records[source_circuit["id"]]
        body = [tuple(item) for item in source_record["body_points_grid"]]
        body_specs.append((source_circuit["id"], body, "DIRECT_BOILER_SLAB_TO_RIGHT_HALF", source_record["territory"], source_circuit["color"]))

    circuits, records = [], []
    for index, (route_id, body, branch, territory, colour) in enumerate(body_specs):
        circuit, record = route_entry(route_id, body, branch, territory)
        circuit["color"] = colour
        circuit["supply_port_index"] = index * 2
        circuit["return_port_index"] = index * 2 + 1
        circuits.append(circuit)
        records.append(record)
    if len(circuits) != 14:
        raise RuntimeError(f"Expected 14 attic circuits, got {len(circuits)}")
    attic["circuits"] = circuits

    stair_records = [item for item in records if item["branch_id"].startswith("UNDER")]
    direct_records = [item for item in records if item["branch_id"].startswith("DIRECT")]
    attic["service_zones"] = [
        make_service_zone("K2-STAIR-WALL-BRANCH-D160", "K2 → под лестницей → подъём по стене → гардероб", stair_records),
        make_service_zone("K2-DIRECT-SLAB-BRANCH-D160", "K2 → проходка перекрытия → правая половина мансарды", direct_records),
    ]
    floor1["service_zones"] = [
        {
            "id": "K2-STAIR-WALL-FLOOR-D160", "floor_id": "FLOOR_1", "name": "K2 → под лестницей → дальняя стена",
            "outline": [p(12600, 10600), p(16600, 10600), p(16600, 11000), p(12600, 11000)],
            "fill_color": "#164E63", "note": "Трубы идут в 70-мм запасе пола вдоль стены под лестницей; вертикальный R80 выполняется у стены, не внутри тонкого слоя пола.",
            "collector_id": "K2", "clear_height_mm": 70, "pipe_capacity": len(stair_records) * 2,
        },
        {
            "id": "K2-DIRECT-SLAB-D160", "floor_id": "FLOOR_1", "name": "K2 → отдельная проходка перекрытия",
            "outline": [p(16200, 11000), p(16600, 11000), p(16600, 11400), p(16200, 11400)],
            "fill_color": "#0E7490", "note": "Отдельная внутренняя проходка из котельной для правой половины мансарды. Отверстие выполнено; ось привязана к внутренней стене.",
            "collector_id": "K2", "clear_height_mm": 70, "pipe_capacity": len(direct_records) * 2,
        },
    ]

    body_lines = [line_body(item) for item in circuits]
    for index, line in enumerate(body_lines):
        if not line.is_simple or self_contacts([(round(x / 100), round(y / 100)) for x, y in line.coords]):
            raise RuntimeError(f"Self contact: {circuits[index]['id']}")
        for other_index in range(index):
            if not line.intersection(body_lines[other_index]).is_empty:
                raise RuntimeError(f"Body contact: {circuits[index]['id']} / {circuits[other_index]['id']}")

    domains = load(D062)
    hall = load(D047)
    known_floor = unary_union(
        [shape(item["floor_geojson"]) for item in domains["adjacent_floor_domains"]]
        + [shape(hall["hall_source_contract"]["routing_draft_allowed_floor_geojson"])]
    )
    body_union = unary_union([line.buffer(100, quad_segs=16) for line in body_lines])
    served = known_floor.intersection(body_union).area
    coverage = {
        "method": "ROUND_100MM_BODY_CENTERLINE_PROXIMITY_Q16_ON_VECTOR_DRAFT_DOMAINS",
        "known_floor_area_m2": known_floor.area / 1_000_000,
        "served_proximity_m2": served / 1_000_000,
        "unresolved_proximity_m2": (known_floor.area - served) / 1_000_000,
        "served_proximity_percent": served * 100 / known_floor.area,
        "full_coverage_claimed": False,
        "service_transits_counted_as_heating": False,
    }
    total_lengths = [item["design_total_length_mm"] for item in records]
    contract = {
        "artifact_id": ARTIFACT_ID,
        "status": "DUAL_BOILER_MANIFOLD_AND_TWO_RISE_LAYOUT_PASS_REWORK_FINAL_HYDRAULIC_BALANCING",
        "source_D159_floor1_sha256": sha(floor_path_source),
        "source_D159_attic_sha256": sha(attic_path_source),
        "source_D159_contract_sha256": sha(contract_source),
        "manufacturer_reference": {
            "manifold_visual_model": "TWO_PARALLEL_HEADERS_SUPPLY_WITH_FLOWMETERS_RETURN_WITH_VALVES",
            "interior_wall_location_preferred": True,
            "inverted_mounting_allowed_with_condensation_risk_to_actuators": True,
            "K2_model_semantics": "OUTLETS_UP_SERVICE_COMPONENTS_REMAIN_ACCESSIBLE",
        },
        "boiler_room_manifolds": {
            "same_internal_wall": True,
            "mounting_wall_id": "FLOOR_1-W025",
            "K1": k1,
            "K2": k2_floor,
            "K2_is_upside_down_on_plan": True,
        },
        "routing_rules": rules,
        "floor_build_ups": {"FLOOR_1": {"installed_insulation_mm": 100, "remaining_height_mm": 70}, "ATTIC": {"installed_insulation_mm": 50, "remaining_height_mm": 70}},
        "rise_strategy": {
            "under_stair_wall_to_wardrobe_route_count": len(stair_records),
            "direct_boiler_slab_to_right_half_route_count": len(direct_records),
            "floor_to_floor_height_mm": FLOOR_TO_FLOOR_MM,
            "minimum_bend_radius_mm": 80,
            "vertical_turn_inside_70mm_floor_layer": False,
            "turn_location": "AT_WALL_OR_OPENING_WITH_FULL_R80_ENVELOPE",
        },
        "routes": records,
        "route_count": len(records),
        "all_design_lengths_40_80m": all(40_000 <= value <= 80_000 for value in total_lengths),
        "minimum_design_length_mm": min(total_lengths),
        "maximum_design_length_mm": max(total_lengths),
        "body_contact_count": 0,
        "window_count": len(floor1["windows"]) + len(attic["windows"]),
        "wall_thicknesses_mm": sorted(set(item["thickness_mm"] for item in floor1["walls"] + attic["walls"])),
        "coverage": coverage,
        "hydraulics_calculated": False,
        "installation_ready": False,
        "next_safe_block": "HYDRAULIC_BALANCE_14_LOOP_K2_AND_RESIDUAL_COVERAGE_REVIEW",
    }
    floor1["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D160: K1 и перевёрнутый K2 размещены рядом на одной внутренней стене котельной. Стены имеют толщину, окна показаны голубым. Две ветви мансарды: под лестницей к гардеробу и отдельная проходка из котельной.",
        "author_intent": "Two real-looking manifold assemblies on one boiler-room wall and two internal attic feed strategies",
    }
    attic["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D160: физический K2 находится в котельной и поэтому не рисуется в гардеробной. 14 контуров распределены по двум внутренним подъёмам; большая спальня разделена на четыре короткие улитки без пустого продольного поля.",
        "author_intent": "Dense counterflow fields supplied from boiler-room K2 by wardrobe-wall and direct-slab branches",
    }

    floor_file = OUTPUT / "HomeAura_Floor1_BoilerManifolds_D160.homeaura.json"
    attic_file = OUTPUT / "HomeAura_Attic_DualRise_D160.homeaura.json"
    dump(floor_file, floor1)
    dump(attic_file, attic)
    dump(OUTPUT / "two_manifold_dual_rise_contract.json", contract)
    dump(OUTPUT / "lineage.json", {
        "source_D159_floor1_sha256": sha(floor_path_source),
        "source_D159_attic_sha256": sha(attic_path_source),
        "floor1_route_points_preserved": True,
        "attic_preserved_route_ids": [item["id"] for item in circuits if item["id"] not in {"A-C01", "A-C02-W", "A-C02-E", "A-C03-W", "A-C03-E", "A-C04"}],
        "repartitioned_territories": ["Гардероб", "Спальня 28.7 м²", "Ванна + WC"],
        "K2_removed_from_attic_wardrobe": True,
    })
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "status": contract["status"],
        "floor1_route_count": len(floor1["circuits"]),
        "attic_route_count": len(attic["circuits"]),
        "all_lengths_40_80m": contract["all_design_lengths_40_80m"],
        "body_contact_count": 0,
        "coverage_percent": coverage["served_proximity_percent"],
        "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D160 · два коллектора в котельной и две ветви мансарды\n\n"
        "K1 и K2 стоят рядом на одной внутренней стене котельной. K2 развёрнут патрубками вверх; расходомеры и клапаны остаются в обслуживаемой ориентации. "
        "Левая группа мансарды идёт по полу первого этажа под лестницей, поднимается по дальней стене и выходит в гардеробную. Центральная и правая группы получают отдельную внутреннюю проходку непосредственно из котельной.\n\n"
        "Большая спальня мансарды разделена на четыре короткие регулярные улитки: это сохраняет длины 40-80 м с учётом 3-м подъёма и уменьшает пустоты. "
        "Стены теперь имеют отдельную толщину 100/200/400 мм, окна являются отдельными голубыми объектами редактора.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(OUTPUT),
        "routes": len(records),
        "min_length_m": min(total_lengths) / 1000,
        "max_length_m": max(total_lengths) / 1000,
        "stair_branch_routes": len(stair_records),
        "direct_branch_routes": len(direct_records),
        "coverage": coverage,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

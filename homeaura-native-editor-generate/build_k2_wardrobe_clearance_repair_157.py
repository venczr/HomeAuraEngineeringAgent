from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, shape
from shapely.ops import unary_union


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_owner_style_installation_project_141 import paired_counterflow, length_mm, self_contacts  # noqa: E402


ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D156 = PROPOSALS / "HA_TWO_FLOOR_INTERFLOOR_RISER_ALIGNMENT_156"
D155 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_SERVICE_LENGTH_CANDIDATES_155"
D062 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
D047 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_K2_WARDROBE_CLEARANCE_REPAIR_157"
ARTIFACT_ID = OUTPUT.name
OFFSET = 3000
K2 = (12_400, 10_300)
K2_CABINET = Polygon([(12_100, 9_600), (12_700, 9_600), (12_700, 10_600), (12_100, 10_600)])
NEW_C01_BOX = (47, 58, 90, 81)
COLLECTOR_GRID = (94, 73)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def project_point(point: tuple[int, int]) -> dict:
    return {"x_mm": OFFSET + point[0] * 100, "y_mm": OFFSET + point[1] * 100}


def service_path(endpoint: tuple[int, int]) -> list[tuple[int, int]]:
    x, y = endpoint
    if x <= 98:
        return [COLLECTOR_GRID, (98, 73), (98, y), (x, y)]
    trunk_x = 130 if x <= 130 else 132
    return [COLLECTOR_GRID, (98, 73), (98, 93), (trunk_x, 93), (trunk_x, y), (x, y)]


def grid_length(points: list[tuple[int, int]]) -> int:
    return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(points, points[1:])) * 100


def body_line(project_circuit: dict) -> LineString:
    return LineString([(point["x_mm"], point["y_mm"]) for point in project_circuit["ordered_points"]])


def coverage(project: dict) -> dict:
    domains = load(D062)
    hall = load(D047)
    floor = unary_union(
        [shape(item["floor_geojson"]) for item in domains["adjacent_floor_domains"]]
        + [shape(hall["hall_source_contract"]["routing_draft_allowed_floor_geojson"])]
    )
    served = unary_union([
        LineString([
            (point["x_mm"] - OFFSET, point["y_mm"] - OFFSET)
            for point in circuit["ordered_points"]
        ]).buffer(100, quad_segs=16)
        for circuit in project["circuits"]
    ])
    served_area = floor.intersection(served).area
    return {
        "known_floor_area_m2": floor.area / 1_000_000,
        "served_proximity_m2": served_area / 1_000_000,
        "unresolved_proximity_m2": (floor.area - served_area) / 1_000_000,
        "served_proximity_percent": served_area * 100 / floor.area,
        "full_coverage_claimed": False,
        "method": "ROUND_100MM_CENTERLINE_PROXIMITY_Q16_ON_VECTOR_DRAFT_DOMAINS",
    }


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"Append-only output already exists: {OUTPUT}")
    OUTPUT.mkdir(parents=True)

    floor1_source = D156 / "HomeAura_Floor1_R1_Aligned_D156.homeaura.json"
    attic_source = D156 / "HomeAura_Attic_R1_Aligned_D156.homeaura.json"
    floor1 = load(floor1_source)
    attic = load(attic_source)
    old_attic = copy.deepcopy(attic)
    service_contract = load(D155 / "service_length_contract.json")

    body = paired_counterflow(NEW_C01_BOX)
    if self_contacts(body):
        raise RuntimeError("New wardrobe body is not simple")
    supply = service_path(body[0])
    return_leg = service_path(body[-1])
    concealed = grid_length(supply) + grid_length(return_leg)
    body_mm = length_mm(body)
    total_mm = body_mm + concealed
    if not 40_000 <= total_mm <= 80_000:
        raise RuntimeError(f"A-C01 out of range: {total_mm}")

    circuit = next(item for item in attic["circuits"] if item["id"] == "A-C01")
    old_body = copy.deepcopy(circuit["ordered_points"])
    circuit["ordered_points"] = [project_point(point) for point in body]
    circuit["concealed_service_length_mm"] = concealed

    route_record = next(item for item in service_contract["routes"] if item["route_id"] == "A-C01")
    route_record["body_points_grid"] = [list(point) for point in body]
    route_record["body_length_mm"] = body_mm
    route_record["concealed_supply_skeleton_grid"] = [list(point) for point in supply]
    route_record["concealed_return_skeleton_grid"] = [list(point) for point in return_leg]
    route_record["concealed_service_length_mm"] = concealed
    route_record["design_total_length_mm"] = total_mm
    route_record["territory"] = "Гардероб с резервом под K2"

    all_service_lines: list[LineString] = []
    for route in service_contract["routes"]:
        for key in ("concealed_supply_skeleton_grid", "concealed_return_skeleton_grid"):
            all_service_lines.append(LineString([(x * 100, y * 100) for x, y in route[key]]))
    service_geometry = unary_union(all_service_lines).buffer(100, cap_style=2, join_style=2)
    if service_geometry.geom_type != "Polygon":
        service_geometry = service_geometry.convex_hull
    skeleton_zone = next(item for item in attic["service_zones"] if item["id"] == "K2-SERVICE-SKELETON-D155")
    skeleton_zone["outline"] = [
        {"x_mm": int(round(x + OFFSET)), "y_mm": int(round(y + OFFSET))}
        for x, y in list(service_geometry.exterior.coords)[:-1]
    ]
    skeleton_zone["note"] = (
        "D157: двухуровневый расчётный скелет, индивидуальный веер ещё не материализован. "
        "Гардеробный контур отведён от K2; вертикальный R80 выполняется в стеновой зоне R1."
    )
    attic["service_zones"].append({
        "id": "K2-CABINET-CLEARANCE-D157",
        "floor_id": "ATTIC",
        "name": "K2 · монтажная зона без тёплого пола",
        "outline": [{"x_mm": int(x), "y_mm": int(y)} for x, y in list(K2_CABINET.exterior.coords)[:-1]],
        "fill_color": "#7F1D1D",
        "note": "Кандидат 600×1000 мм у дальней стены гардеробной; точная модель шкафа/коллектора ещё не выбрана.",
        "collector_id": "K2",
        "clear_height_mm": None,
        "pipe_capacity": 24,
    })
    attic["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D157: исправлено пересечение K2 с A-C01; монтажная зона K2 свободна, остальные 11 контуров и R1 сохранены.",
        "author_intent": "Exact attic counterflow layout with K2 cabinet clearance and aligned R1",
    }

    new_line = body_line(circuit)
    k2_distance = new_line.distance(Point(K2))
    cabinet_distance = new_line.distance(K2_CABINET)
    cabinet_intersection = new_line.intersection(K2_CABINET)
    contact_pairs: list[list[str]] = []
    for index, first in enumerate(attic["circuits"]):
        first_line = body_line(first)
        for second in attic["circuits"][index + 1 :]:
            if not first_line.intersection(body_line(second)).is_empty:
                contact_pairs.append([first["id"], second["id"]])
    if contact_pairs or not cabinet_intersection.is_empty:
        raise RuntimeError({"body_contacts": contact_pairs, "cabinet_intersection": cabinet_intersection.wkt})

    service_contract.update({
        "artifact_id": ARTIFACT_ID,
        "status": "K2_WARDROBE_CLEARANCE_PASS_REWORK_INDIVIDUAL_SERVICE_AXES_AND_PHYSICAL_MANIFOLD",
        "source_D156_attic_sha256": sha256(attic_source),
        "source_D155_contract_sha256": sha256(D155 / "service_length_contract.json"),
        "K2_cabinet_candidate_bbox_mm": [12_100, 9_600, 12_700, 10_600],
        "K2_point_mm": list(K2),
        "A_C01_body_distance_to_K2_mm": k2_distance,
        "A_C01_body_distance_to_cabinet_mm": cabinet_distance,
        "A_C01_cabinet_intersection_count": 0,
        "body_contact_pairs": contact_pairs,
        "coverage": coverage(attic),
        "individual_service_pipe_axes_materialized": False,
        "physical_manifold_selected": False,
        "installation_ready": False,
        "next_safe_block": "MATERIALIZE_K2_PORT_BANK_AND_TWO_LAYER_SERVICE_AXES_WITHOUT_ENTERING_CABINET_CLEARANCE",
    })
    service_contract["routes"] = sorted(service_contract["routes"], key=lambda item: next(
        index for index, circuit_item in enumerate(attic["circuits"]) if circuit_item["id"] == item["route_id"]
    ))

    floor_path = OUTPUT / "HomeAura_Floor1_R1_K2_Clearance_D157.homeaura.json"
    attic_path = OUTPUT / "HomeAura_Attic_K2_Clearance_D157.homeaura.json"
    write_json(floor_path, floor1)
    write_json(attic_path, attic)
    write_json(OUTPUT / "k2_clearance_and_service_contract.json", service_contract)
    write_json(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "status": service_contract["status"],
        "A_C01_total_length_mm": total_mm,
        "A_C01_body_distance_to_K2_mm": k2_distance,
        "A_C01_body_distance_to_cabinet_mm": cabinet_distance,
        "body_contact_count": 0,
        "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D157 · освобождение монтажной зоны K2\n\n"
        "Исправлена физическая ошибка D155/D156: K2 больше не лежит на трубе A-C01. "
        "Гардеробная улитка уменьшена только с восточной стороны, её расчётная длина стала 52,2 м с подводками. "
        "У K2 оставлен кандидат монтажной зоны 600×1000 мм; 11 остальных мансардных контуров, первый этаж и ось R1 сохранены.\n",
        encoding="utf-8",
    )
    write_json(OUTPUT / "lineage.json", {
        "source_floor1_sha256": sha256(floor1_source),
        "source_attic_sha256": sha256(attic_source),
        "floor1_project_preserved": True,
        "changed_route_ids": ["A-C01"],
        "unchanged_attic_route_ids": [item["id"] for item in attic["circuits"] if item["id"] != "A-C01"],
        "old_A_C01_points": old_body,
        "new_A_C01_points": circuit["ordered_points"],
    })
    print(json.dumps({
        "output": str(OUTPUT),
        "A_C01_body_mm": body_mm,
        "A_C01_concealed_mm": concealed,
        "A_C01_total_mm": total_mm,
        "distance_to_K2_mm": k2_distance,
        "distance_to_cabinet_mm": cabinet_distance,
        "body_contact_count": len(contact_pairs),
        "coverage": service_contract["coverage"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

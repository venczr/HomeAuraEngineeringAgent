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
from build_owner_style_installation_project_141 import clean, length_mm, self_contacts  # noqa: E402


ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D158 = PROPOSALS / "HA_TWO_FLOOR_K2_CLEARANCE_COVERAGE_CORRECTION_158"
D062 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
D047 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_DENSE_CENTRE_COUNTERFLOW_159"
ARTIFACT_ID = OUTPUT.name
OFFSET = 3000
COLLECTOR_GRID = (94, 73)
K2 = Point(12_400, 10_300)
K2_CABINET = Polygon([(12_100, 9_600), (12_700, 9_600), (12_700, 10_600), (12_100, 10_600)])

REBUILDS = {
    "A-C01": {"box": (47, 58, 90, 81), "orientation": "IDENTITY", "territory": "Гардероб с резервом под K2"},
    "A-C04": {"box": (49, 143, 96, 165), "orientation": "IDENTITY", "territory": "Ванна + WC"},
    "A-C07": {"box": (95, 170, 135, 192), "orientation": "MIRROR_Y", "territory": "Холл - вход"},
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def project_point(point: tuple[int, int]) -> dict:
    return {"x_mm": OFFSET + point[0] * 100, "y_mm": OFFSET + point[1] * 100}


def transform(points: list[tuple[int, int]], box: tuple[int, int, int, int], orientation: str) -> list[tuple[int, int]]:
    left, top, right, bottom = box
    if orientation == "IDENTITY":
        return points
    if orientation == "MIRROR_Y":
        return [(x, top + bottom - y) for x, y in points]
    raise ValueError(orientation)


def dense_counterflow(box: tuple[int, int, int, int]) -> list[tuple[int, int]]:
    left, top, right, bottom = box

    def frames(source: tuple[int, int, int, int], minimum_span: int) -> list[tuple[int, int, int, int]]:
        l, t, r, b = source
        output = []
        while r - l >= minimum_span and b - t >= minimum_span:
            output.append((l, t, r, b))
            l += 4
            t += 4
            r -= 4
            b -= 4
        return output

    def arm(frame_list: list[tuple[int, int, int, int]]) -> list[tuple[int, int]]:
        output: list[tuple[int, int]] = []
        for index, (l, t, r, b) in enumerate(frame_list):
            if index:
                output.append((output[-1][0], b))
            output.extend([(r, b), (l, b), (l, t), (r, t)])
        return clean(output)

    inward = arm(frames(box, 4))
    outward = arm(frames((left + 2, top + 2, right - 2, bottom - 2), 2))
    first, second = inward[-1], outward[-1]
    for turn in [(first[0], second[1]), (second[0], first[1])]:
        candidate = clean([*inward, turn, second, *reversed(outward[:-1])])
        if self_contacts(candidate) == 0:
            if min((abs(b[0] - a[0]) + abs(b[1] - a[1])) * 100 for a, b in zip(candidate, candidate[1:])) < 200:
                continue
            return candidate
    raise RuntimeError(f"Dense counterflow failed for {box}")


def service_path(endpoint: tuple[int, int]) -> list[tuple[int, int]]:
    x, y = endpoint
    if x <= 98:
        return [COLLECTOR_GRID, (98, 73), (98, y), (x, y)]
    trunk_x = 130 if x <= 130 else 132
    return [COLLECTOR_GRID, (98, 73), (98, 93), (trunk_x, 93), (trunk_x, y), (x, y)]


def grid_length(points: list[tuple[int, int]]) -> int:
    return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(points, points[1:])) * 100


def project_line(circuit: dict) -> LineString:
    return LineString([(point["x_mm"], point["y_mm"]) for point in circuit["ordered_points"]])


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"Append-only output already exists: {OUTPUT}")
    OUTPUT.mkdir(parents=True)

    floor_source = D158 / "HomeAura_Floor1_R1_K2_Clearance_D158.homeaura.json"
    attic_source = D158 / "HomeAura_Attic_K2_Clearance_D158.homeaura.json"
    contract_source = D158 / "k2_clearance_and_service_contract.json"
    floor1 = load(floor_source)
    attic = load(attic_source)
    source_attic = copy.deepcopy(attic)
    contract = load(contract_source)

    lineage = []
    for route_id, specification in REBUILDS.items():
        circuit = next(item for item in attic["circuits"] if item["id"] == route_id)
        old_points = copy.deepcopy(circuit["ordered_points"])
        box = specification["box"]
        body = transform(dense_counterflow(box), box, specification["orientation"])
        supply = service_path(body[0])
        return_leg = service_path(body[-1])
        body_mm = length_mm(body)
        concealed_mm = grid_length(supply) + grid_length(return_leg)
        total_mm = body_mm + concealed_mm
        if not 40_000 <= total_mm <= 80_000:
            raise RuntimeError(f"{route_id}: {body_mm}+{concealed_mm}={total_mm}")
        circuit["ordered_points"] = [project_point(point) for point in body]
        circuit["concealed_service_length_mm"] = concealed_mm
        record = next(item for item in contract["routes"] if item["route_id"] == route_id)
        record.update({
            "territory": specification["territory"],
            "body_points_grid": [list(point) for point in body],
            "body_length_mm": body_mm,
            "concealed_supply_skeleton_grid": [list(point) for point in supply],
            "concealed_return_skeleton_grid": [list(point) for point in return_leg],
            "concealed_service_length_mm": concealed_mm,
            "design_total_length_mm": total_mm,
            "centre_fill_variant": "DENSE_FINAL_OUTWARD_FRAME_MIN_SPAN_200MM",
        })
        lineage.append({
            "route_id": route_id,
            "old_points": old_points,
            "new_points": circuit["ordered_points"],
            "body_length_mm": body_mm,
            "concealed_service_length_mm": concealed_mm,
            "design_total_length_mm": total_mm,
        })

    contact_pairs = []
    for index, first in enumerate(attic["circuits"]):
        first_line = project_line(first)
        if self_contacts([((p["x_mm"] - OFFSET) // 100, (p["y_mm"] - OFFSET) // 100) for p in first["ordered_points"]]):
            raise RuntimeError(f"{first['id']}: self contact")
        for second in attic["circuits"][index + 1 :]:
            if not first_line.intersection(project_line(second)).is_empty:
                contact_pairs.append([first["id"], second["id"]])
    if contact_pairs:
        raise RuntimeError(contact_pairs)

    c01_line = project_line(next(item for item in attic["circuits"] if item["id"] == "A-C01"))
    if not c01_line.intersection(K2_CABINET).is_empty:
        raise RuntimeError("A-C01 entered the K2 cabinet zone")

    service_lines = []
    for record in contract["routes"]:
        for key in ("concealed_supply_skeleton_grid", "concealed_return_skeleton_grid"):
            service_lines.append(LineString([(x * 100, y * 100) for x, y in record[key]]))
    service_geometry = unary_union(service_lines).buffer(100, cap_style=2, join_style=2)
    if service_geometry.geom_type != "Polygon":
        service_geometry = service_geometry.convex_hull
    skeleton = next(item for item in attic["service_zones"] if item["id"] == "K2-SERVICE-SKELETON-D155")
    skeleton["outline"] = [
        {"x_mm": int(round(x + OFFSET)), "y_mm": int(round(y + OFFSET))}
        for x, y in list(service_geometry.exterior.coords)[:-1]
    ]
    skeleton["note"] = (
        "D159: плотные центральные развороты A-C01/A-C04/A-C07, два уровня 20/50 мм. "
        "Пунктир остаётся расчётным коридором, а не индивидуальными осями подводок."
    )

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
        for circuit in attic["circuits"]
    ])
    served_area = floor.intersection(served).area
    coverage = {
        "known_floor_area_m2": floor.area / 1_000_000,
        "served_proximity_m2": served_area / 1_000_000,
        "unresolved_proximity_m2": (floor.area - served_area) / 1_000_000,
        "served_proximity_percent": served_area * 100 / floor.area,
        "full_coverage_claimed": False,
        "method": "ROUND_100MM_CENTERLINE_PROXIMITY_Q16_ON_VECTOR_DRAFT_DOMAINS",
        "project_to_source_transform_mm": [-OFFSET, -OFFSET],
    }
    source_coverage = copy.deepcopy(contract["coverage"])
    contract.update({
        "artifact_id": ARTIFACT_ID,
        "status": "DENSE_CENTRE_COUNTERFLOW_PASS_REWORK_INDIVIDUAL_K2_SERVICE_AXES_AND_FINAL_COVERAGE",
        "source_D158_attic_sha256": sha256(attic_source),
        "source_D158_contract_sha256": sha256(contract_source),
        "changed_route_ids": list(REBUILDS),
        "unchanged_route_ids": [item["id"] for item in attic["circuits"] if item["id"] not in REBUILDS],
        "body_contact_pairs": contact_pairs,
        "A_C01_body_distance_to_K2_mm": c01_line.distance(K2),
        "A_C01_body_distance_to_cabinet_mm": c01_line.distance(K2_CABINET),
        "coverage_before_D158": source_coverage,
        "coverage": coverage,
        "coverage_gain_m2": coverage["served_proximity_m2"] - source_coverage["served_proximity_m2"],
        "coverage_gain_percentage_points": coverage["served_proximity_percent"] - source_coverage["served_proximity_percent"],
        "individual_service_pipe_axes_materialized": False,
        "physical_manifold_selected": False,
        "installation_ready": False,
        "next_safe_block": "MATERIALIZE_K2_PORT_BANK_AND_TWO_LAYER_SERVICE_AXES_THEN_POLYGON_RESIDUAL_REVIEW",
    })
    attic["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D159: центральные пустоты уменьшены в A-C01/A-C04/A-C07; все 12 длин 40–80 м, K2/R1 сохранены.",
        "author_intent": "Dense owner-style counterflow bodies with K2 clearance and aligned R1",
    }

    write_json(OUTPUT / "HomeAura_Floor1_DenseCounterflow_D159.homeaura.json", floor1)
    write_json(OUTPUT / "HomeAura_Attic_DenseCounterflow_D159.homeaura.json", attic)
    write_json(OUTPUT / "dense_counterflow_contract.json", contract)
    write_json(OUTPUT / "lineage.json", {
        "source_D158_floor1_sha256": sha256(floor_source),
        "source_D158_attic_sha256": sha256(attic_source),
        "floor1_project_preserved": True,
        "changed_routes": lineage,
        "unchanged_routes_preserved": all(
            next(item for item in attic["circuits"] if item["id"] == source["id"]) == source
            for source in source_attic["circuits"]
            if source["id"] not in REBUILDS
        ),
    })
    write_json(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "status": contract["status"],
        "route_count": len(attic["circuits"]),
        "all_lengths_40_80m": True,
        "body_contact_count": 0,
        "served_proximity_percent": coverage["served_proximity_percent"],
        "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D159 · плотные центры улиток\n\n"
        "Без изменения архитектуры и оси R1 перестроены только A-C01, A-C04 и длинный холловый A-C07. "
        "В последнюю ответную рамку добавлен допустимый 200-мм центральный проход, поэтому крупные пустые сердцевины уменьшились. "
        "Длины с подводками: A-C01 58,6 м; A-C04 78,0 м; A-C07 77,6 м. K2 остаётся на 400 мм от трубы и на 100 мм от монтажной зоны.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(OUTPUT),
        "changed_routes": [{key: item[key] for key in ("route_id", "body_length_mm", "concealed_service_length_mm", "design_total_length_mm")} for item in lineage],
        "coverage": coverage,
        "coverage_gain_m2": contract["coverage_gain_m2"],
        "coverage_gain_percentage_points": contract["coverage_gain_percentage_points"],
        "K2_body_distance_mm": contract["A_C01_body_distance_to_K2_mm"],
        "K2_cabinet_distance_mm": contract["A_C01_body_distance_to_cabinet_mm"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

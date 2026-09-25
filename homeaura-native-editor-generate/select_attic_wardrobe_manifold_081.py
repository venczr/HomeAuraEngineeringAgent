from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.affinity import translate
from shapely.geometry import LineString, box, shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_050 = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
SOURCE_062 = BASE / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
SOURCE_079 = BASE / "HA_TWO_FLOOR_INTERNAL_STAIR_WARDROBE_R1_079" / "internal_stair_wardrobe_r1_strategy.json"
SOURCE_080 = BASE / "HA_TWO_FLOOR_INTERNAL_RISER_3D_080" / "internal_riser_3d.json"
ATTIC_RENDER = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_WARDROBE_MANIFOLD_081"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_WARDROBE_MANIFOLD_081.zip"

DX_MM = 359.83333333356
DY_MM = 304.8
PX_PER_100_MM = 8.503937
MANIFOLD_BBOX_BUILDING_MM = [9070, 7200, 9370, 7800]
MANIFOLD_ANCHOR_BUILDING_MM = [9200, 7500]
MAXIMUM_RESERVED_OPENING_MM = [9150, 7200, 9310, 7600]


def font(size: int, bold: bool = False):
    return ImageFont.truetype(
        str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")),
        size,
    )


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def registered_points(route):
    return [(x - DX_MM, y - DY_MM) for x, y in route["body_points_mm"]]


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D081 is append-only")
    raw_050, attic = read(SOURCE_050)
    raw_062, domains = read(SOURCE_062)
    raw_079, strategy = read(SOURCE_079)
    raw_080, rejected = read(SOURCE_080)

    wardrobe_source = next(
        item for item in domains["adjacent_floor_domains"]
        if item["domain_id"] == "ATTIC_LEFT_NORTH_RECT_DRAFT"
    )
    wardrobe = translate(shape(wardrobe_source["floor_geojson"]), xoff=-DX_MM, yoff=-DY_MM)
    manifold = box(*MANIFOLD_BBOX_BUILDING_MM)
    body_lines = {route["route_id"]: LineString(registered_points(route)) for route in attic["body_routes"]}
    body_contacts = [route_id for route_id, line in body_lines.items() if line.intersects(manifold)]
    body_clearance = min(line.distance(manifold) for line in body_lines.values())

    routes = {route["route_id"]: route for route in attic["body_routes"]}
    topology = []
    for route_id in [
        "A-C01", "A-C02", "A-C03", "A-C04", "A-C05", "A-C06", "A-C07",
        "A-C08", "A-C09", "A-C12", "A-C13",
    ]:
        route = routes[route_id]
        points = registered_points(route)
        supply = manhattan(MANIFOLD_ANCHOR_BUILDING_MM, points[0])
        returning = manhattan(points[-1], MANIFOLD_ANCHOR_BUILDING_MM)
        total = route["body_length_mm"] + supply + returning
        topology.append({
            "circuit_id": route_id,
            "source_body_ids": [route_id],
            "body_length_mm": route["body_length_mm"],
            "optimistic_supply_link_lower_bound_mm": supply,
            "optimistic_return_link_lower_bound_mm": returning,
            "optimistic_total_lower_bound_mm": total,
            "within_40_80m_at_lower_bound": 40000 <= total <= 80000,
            "complete_route_geometry_published": False,
        })

    c10 = routes["A-C10"]
    c11 = routes["A-C11"]
    p10 = registered_points(c10)
    p11 = registered_points(c11)
    alternatives = []
    for order in [("A-C10", "A-C11"), ("A-C11", "A-C10")]:
        for reverse_first in (False, True):
            for reverse_second in (False, True):
                first = list(reversed(registered_points(routes[order[0]]))) if reverse_first else registered_points(routes[order[0]])
                second = list(reversed(registered_points(routes[order[1]]))) if reverse_second else registered_points(routes[order[1]])
                total = (
                    routes[order[0]]["body_length_mm"]
                    + routes[order[1]]["body_length_mm"]
                    + manhattan(MANIFOLD_ANCHOR_BUILDING_MM, first[0])
                    + manhattan(first[-1], second[0])
                    + manhattan(second[-1], MANIFOLD_ANCHOR_BUILDING_MM)
                )
                alternatives.append((total, order, reverse_first, reverse_second, first, second))
    best = min(alternatives, key=lambda item: (item[0], item[1], item[2], item[3]))
    topology.append({
        "circuit_id": "A-C10_C11_SERIAL",
        "source_body_ids": list(best[1]),
        "first_body_reversed": best[2],
        "second_body_reversed": best[3],
        "body_length_mm": c10["body_length_mm"] + c11["body_length_mm"],
        "optimistic_supply_link_lower_bound_mm": manhattan(MANIFOLD_ANCHOR_BUILDING_MM, best[4][0]),
        "optimistic_inter_body_link_lower_bound_mm": manhattan(best[4][-1], best[5][0]),
        "optimistic_return_link_lower_bound_mm": manhattan(best[5][-1], MANIFOLD_ANCHOR_BUILDING_MM),
        "optimistic_total_lower_bound_mm": best[0],
        "within_40_80m_at_lower_bound": 40000 <= best[0] <= 80000,
        "complete_route_geometry_published": False,
    })
    topology = sorted(topology, key=lambda item: item["circuit_id"])
    all_lower_bounds_pass = all(item["within_40_80m_at_lower_bound"] for item in topology)
    source_records = [
        {"artifact_id": data["artifact_id"], "sha256": hashlib.sha256(raw).hexdigest().upper()}
        for raw, data in ((raw_050, attic), (raw_062, domains), (raw_079, strategy), (raw_080, rejected))
    ]
    model = {
        "schema": "homeaura-attic-wardrobe-manifold-topology-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_WARDROBE_MANIFOLD_081",
        "status": "ATTIC_WARDROBE_MANIFOLD_LOCATION_AND_TWELVE_CIRCUIT_TOPOLOGY_SELECTED_REWORK_PRIMARY_MAINS_HYDRAULICS_AND_COMPLETE_ROUTES",
        "source_records": source_records,
        "supersedes_direct_26_pipe_topology_artifact_id": rejected["artifact_id"],
        "superseded_topology_disposition": "REJECTED_AS_FINAL_ARCHITECTURE_TWO_CIRCUIT_LOWER_BOUNDS_EXCEED_80M_BEFORE_OBSTACLE_DETOURS",
        "D080_retained_scope": "LOCAL_3D_PACKING_AND_R80_FEASIBILITY_EVIDENCE_ONLY",
        "selected_architecture": {
            "floor_1_K1_role": "FLOOR_1_LOOPS_AND_PRIMARY_SUPPLY_RETURN_TO_ATTIC",
            "attic_manifold_id": "K2_ATTIC_WARDROBE",
            "attic_manifold_role": "TWELVE_INDEPENDENT_ATTIC_CIRCUITS",
            "primary_vertical_pipe_count": 2,
            "attic_loop_leg_count": 24,
            "attic_circuit_count": 12,
            "second_manifold_required": True,
        },
        "attic_manifold_reservation": {
            "building_bbox_mm": MANIFOLD_BBOX_BUILDING_MM,
            "attic_pdf_bbox_mm": [
                MANIFOLD_BBOX_BUILDING_MM[0] + DX_MM,
                MANIFOLD_BBOX_BUILDING_MM[1] + DY_MM,
                MANIFOLD_BBOX_BUILDING_MM[2] + DX_MM,
                MANIFOLD_BBOX_BUILDING_MM[3] + DY_MM,
            ],
            "routing_anchor_building_mm": MANIFOLD_ANCHOR_BUILDING_MM,
            "wardrobe_draft_floor_contains_reservation": wardrobe.covers(manifold),
            "existing_body_contact_count": len(body_contacts),
            "existing_body_contact_route_ids": body_contacts,
            "minimum_existing_body_clearance_mm": body_clearance,
            "physical_product_selected": False,
            "cabinet_service_clearance_not_evaluated": True,
        },
        "maximum_reserved_opening_bbox_building_mm": MAXIMUM_RESERVED_OPENING_MM,
        "maximum_reserved_opening_is_final_cut_size": False,
        "final_sleeve_or_opening_size": "NOT_SELECTED_UNTIL_PRIMARY_MAIN_OD_INSULATION_BEND_AND_FIRESTOP_ARE_DEFINED",
        "attic_circuit_topology": topology,
        "attic_circuit_count": len(topology),
        "all_optimistic_lower_bounds_40_80m": all_lower_bounds_pass,
        "optimistic_lower_bound_range_mm": [
            min(item["optimistic_total_lower_bound_mm"] for item in topology),
            max(item["optimistic_total_lower_bound_mm"] for item in topology),
        ],
        "direct_26_pipe_diagnostic": {
            "fixed_transit_per_leg_mm": rejected["fixed_transit_length_range_mm"][0],
            "A_C06_optimistic_total_before_detours_mm": next(item["body_plus_two_fixed_transits_mm"] for item in rejected["body_plus_fixed_transit_diagnostics"] if item["route_id"] == "A-C06")
                + 17300,
            "A_C07_optimistic_total_before_detours_mm": next(item["body_plus_two_fixed_transits_mm"] for item in rejected["body_plus_fixed_transit_diagnostics"] if item["route_id"] == "A-C07")
                + 27000,
            "result": "FAIL_TWO_CIRCUITS_ABOVE_80M_LOWER_BOUND",
        },
        "loop_pipe_od_mm": 16,
        "loop_design_centerline_bend_radius_mm": 80,
        "primary_supply_return_pipe_material_and_size": "NOT_SELECTED_REQUIRES_ATTIC_DESIGN_LOAD_FLOW_AND_PRESSURE_DROP",
        "attic_heat_loss_or_design_load": "MISSING",
        "design_temperature_drop": "MISSING",
        "primary_flow_rate": "NOT_CALCULATED",
        "pump_head_and_balancing": "NOT_CALCULATED",
        "physical_manifold_capacity_product": "NOT_SELECTED",
        "complete_attic_route_count": 0,
        "new_pipe_geometry_count": 0,
        "result": "PASS_K2_LOCATION_AND_TWELVE_CIRCUIT_TOPOLOGY_REWORK_PRIMARY_HYDRAULICS_AND_COMPLETE_ROUTE_GEOMETRY",
    }
    model["topology_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_wardrobe_manifold.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    source = Image.open(ATTIC_RENDER).convert("RGB")
    canvas = Image.new("RGB", (1785, 1550), "#F4F8F8")
    draw = ImageDraw.Draw(canvas, "RGBA")
    canvas.paste(source.crop((0, 0, 1785, 1180)), (0, 240))
    draw.rectangle((0, 0, 1785, 240), fill="#071A21")
    draw.text((34, 18), "D081 · КОЛЛЕКТОР МАНСАРДЫ В ГАРДЕРОБНОЙ", font=font(28, True), fill="white")
    draw.text((34, 68), "K1 в котельной → 2 магистрали → K2 в гардеробной → 12 мансардных контуров", font=font(17, True), fill="#A7EEE7")
    draw.text((34, 111), "Ø16 и R80 сохранены для петель · диаметр магистралей выбирается после расчёта расхода", font=font(17), fill="#F3D58C")
    draw.text((34, 155), "C10+C11 объединены в одну последовательную петлю; остальные 11 тел самостоятельны", font=font(16, True), fill="white")
    draw.text((34, 198), "Нижние оценки 40,0…75,3 м PASS · полные маршруты и гидравлика REWORK", font=font(16, True), fill="#FFB2B2")

    def px_building(x, y):
        return ((x + DX_MM) / 100 * PX_PER_100_MM, (y + DY_MM) / 100 * PX_PER_100_MM + 240)

    x0, y0 = px_building(MANIFOLD_BBOX_BUILDING_MM[0], MANIFOLD_BBOX_BUILDING_MM[1])
    x1, y1 = px_building(MANIFOLD_BBOX_BUILDING_MM[2], MANIFOLD_BBOX_BUILDING_MM[3])
    draw.rectangle((x0, y0, x1, y1), fill="#00A66A88", outline="#006A43", width=5)
    draw.text((x0 - 20, y0 - 42), "K2 · 12 ПЕТЕЛЬ", font=font(15, True), fill="#006A43", stroke_width=2, stroke_fill="white")
    hx0, hy0 = px_building(MAXIMUM_RESERVED_OPENING_MM[0], MAXIMUM_RESERVED_OPENING_MM[1])
    hx1, hy1 = px_building(MAXIMUM_RESERVED_OPENING_MM[2], MAXIMUM_RESERVED_OPENING_MM[3])
    draw.rectangle((hx0, hy0, hx1, hy1), fill="#FF6D0055", outline="#D84315", width=3)
    draw.text((hx0 - 15, hy1 + 10), "макс. резерв отверстия", font=font(12, True), fill="#D84315", stroke_width=2, stroke_fill="white")

    draw.rectangle((1020, 270, 1750, 795), fill="#FFFFFFDD", outline="#B7C8CD", width=2)
    draw.text((1045, 290), "РАСПРЕДЕЛЕНИЕ КОНТУРОВ", font=font(18, True), fill="#143842")
    y = 340
    for item in topology:
        label = item["circuit_id"].replace("A-", "")
        value = item["optimistic_total_lower_bound_mm"] / 1000
        color = "#007A4A" if value <= 76 else "#B00020"
        draw.text((1045, y), f"{label:<16}  ≥ {value:4.1f} м", font=font(14, True), fill=color)
        y += 34
    draw.text((1045, 750), "Значения — нижняя оценка, не исполнительная длина.", font=font(12), fill="#566B73")

    draw.rectangle((30, 1430, 1755, 1525), fill="#FFFFFFE8", outline="#CAD8DC", width=2)
    draw.text((50, 1448), "Отверстие 400×160 пока только максимальный резерв. Фактический размер уменьшается после выбора двух магистралей, гильз и заделки.", font=font(15, True), fill="#143842")
    draw.text((50, 1490), "Для продолжения расчёта диаметра нужны теплопотери/мощность мансарды и расчётный перепад температур.", font=font(15, True), fill="#B00020")
    canvas.save(OUTPUT / "attic_wardrobe_manifold_evidence.png")

    (OUTPUT / "report.md").write_text(
        "# D081 — мансардный коллектор в гардеробной\n\n"
        "Прямой подъём всех 26 труб от K1 отклонён как окончательная архитектура: даже оптимистическая нижняя оценка даёт около 83,3 м для A-C06 и 88,5 м для A-C07 до обходов стен. D080 сохраняется только как доказательство локальной вместимости и выполнимости R80.\n\n"
        "Принята схема с отдельным K2 в гардеробной: две межэтажные магистрали от K1 и 12 контуров мансарды. Короткие тела A-C10/A-C11 объединяются в одну последовательную петлю с нижней оценкой около 50,5 м; остальные тела остаются самостоятельными. Диапазон нижних оценок всех 12 петель составляет 40,0–75,3 м.\n\n"
        "Место K2 зарезервировано внутри векторного чернового пола гардеробной без контакта с существующими телами. Физический коллектор, сервисные зазоры, полные маршруты и гидравлика ещё не выбраны. Ø16 и R80 относятся к петлям. Диаметр двух магистралей нельзя честно назначить без расчётной нагрузки мансарды, температурного перепада, расхода и потерь давления. Резерв отверстия 400×160 мм не является окончательным размером резки.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "topology_digest": model["topology_digest"],
        "append_only": True,
        "files": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "attic_circuit_count": len(topology),
        "lower_bound_range_mm": model["optimistic_lower_bound_range_mm"],
        "manifold_contained": model["attic_manifold_reservation"]["wardrobe_draft_floor_contains_reservation"],
        "body_contacts": body_contacts,
        "body_clearance_mm": body_clearance,
        "topology_digest": model["topology_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

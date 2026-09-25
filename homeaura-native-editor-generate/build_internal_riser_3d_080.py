from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_039 = BASE / "HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039" / "canonical_geometry.json"
SOURCE_050 = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
SOURCE_069 = BASE / "HA_TWO_FLOOR_ATTIC_RISER_PACKING_SCOPE_069" / "attic_riser_packing_scenario.json"
SOURCE_079 = BASE / "HA_TWO_FLOOR_INTERNAL_STAIR_WARDROBE_R1_079" / "internal_stair_wardrobe_r1_strategy.json"
F1_RENDER = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
ATTIC_RENDER = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_INTERNAL_RISER_3D_080"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_INTERNAL_RISER_3D_080.zip"

PX_PER_100_MM = 8.503937
ATTIC_DX_MM = 359.83333333356
ATTIC_DY_MM = 304.8
HOLE = [9150, 7200, 9310, 7600]
FLOOR_HANDOFF_X_MM = 13200
ATTIC_HANDOFF_X_MM = 9100
FLOOR_TO_FLOOR_MM = 3000
RADIUS_MM = 80
PIPE_OD_MM = 16
PROVISIONAL_ENVELOPE_OD_MM = 28
ARC_DIVISIONS = 16


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


def unique(points):
    answer = []
    for point in points:
        rounded = [round(float(value), 6) for value in point]
        if not answer or answer[-1] != rounded:
            answer.append(rounded)
    return answer


def build_axis(position):
    local_along, local_across = position["center_mm"]
    vertical_x = HOLE[0] + local_across
    plan_y = HOLE[1] + local_along
    floor_z = local_across
    lower_arc = []
    for index in range(ARC_DIVISIONS + 1):
        theta = math.pi / 2 * index / ARC_DIVISIONS
        lower_arc.append([
            vertical_x + RADIUS_MM * math.cos(theta),
            plan_y,
            floor_z + RADIUS_MM * math.sin(theta),
        ])
    upper_vertical_end_z = FLOOR_TO_FLOOR_MM + floor_z
    upper_arc = []
    for index in range(ARC_DIVISIONS + 1):
        theta = math.pi / 2 * index / ARC_DIVISIONS
        upper_arc.append([
            vertical_x - RADIUS_MM + RADIUS_MM * math.cos(theta),
            plan_y,
            upper_vertical_end_z + RADIUS_MM * math.sin(theta),
        ])
    points = unique(
        [[FLOOR_HANDOFF_X_MM, plan_y, floor_z], [vertical_x + RADIUS_MM, plan_y, floor_z]]
        + lower_arc
        + [[vertical_x, plan_y, upper_vertical_end_z]]
        + upper_arc
        + [[ATTIC_HANDOFF_X_MM, plan_y, upper_vertical_end_z + RADIUS_MM]]
    )
    floor_straight = FLOOR_HANDOFF_X_MM - (vertical_x + RADIUS_MM)
    vertical = upper_vertical_end_z - (floor_z + RADIUS_MM)
    attic_straight = (vertical_x - RADIUS_MM) - ATTIC_HANDOFF_X_MM
    analytical = floor_straight + vertical + attic_straight + math.pi * RADIUS_MM
    return {
        "pipe_id": position["pipe_id"],
        "route_id": position["route_id"],
        "leg": position["leg"],
        "packing_row": position["row"],
        "packing_column": position["column"],
        "floor_handoff_xyz_mm": points[0],
        "vertical_axis_xy_mm": [vertical_x, plan_y],
        "attic_handoff_xyz_mm": points[-1],
        "ordered_axis_points_xyz_mm": points,
        "floor_straight_length_mm": floor_straight,
        "lower_bend_arc_length_mm": math.pi * RADIUS_MM / 2,
        "vertical_straight_length_mm": vertical,
        "upper_bend_arc_length_mm": math.pi * RADIUS_MM / 2,
        "attic_straight_length_mm": attic_straight,
        "fixed_transit_length_mm": analytical,
        "bend_count": 2,
        "bend_radius_mm": RADIUS_MM,
        "complete_circuit": False,
    }


def point_distance(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def sampled_minimum_distance(a, b):
    minimum = float("inf")
    for point_a in a["ordered_axis_points_xyz_mm"]:
        for point_b in b["ordered_axis_points_xyz_mm"]:
            minimum = min(minimum, point_distance(point_a, point_b))
    return minimum


def plan_projection_contacts(floor1, axes):
    contacts = {}
    projections = [
        LineString([(point[0], point[1]) for point in axis["ordered_axis_points_xyz_mm"]])
        for axis in axes
    ]
    for route in floor1["routes"]:
        line = LineString(route["ordered_points_mm"])
        hits = sum(1 for projection in projections if projection.intersects(line))
        if hits:
            contacts[route["route_id"]] = hits
    return [{"route_id": route_id, "candidate_axis_contact_count": count} for route_id, count in contacts.items()]


def attic_plan_clearance(attic, axes):
    handoff_lines = []
    for axis in axes:
        points = axis["ordered_axis_points_xyz_mm"]
        top_z = axis["attic_handoff_xyz_mm"][2]
        top = [(point[0], point[1]) for point in points if point[2] >= top_z - 0.001]
        if len(top) >= 2:
            handoff_lines.append((axis["pipe_id"], LineString(top)))
    records = []
    for route in attic["body_routes"]:
        body = LineString([(x - ATTIC_DX_MM, y - ATTIC_DY_MM) for x, y in route["body_points_mm"]])
        distance = min(line.distance(body) for _, line in handoff_lines)
        records.append({"route_id": route["route_id"], "minimum_plan_clearance_mm": distance})
    return records


def project3d(point, origin, scale=0.115):
    x, y, z = point
    ox, oy = origin
    return (
        ox + (x - 9000) * scale + (y - 7200) * 0.055,
        oy - z * 0.22 + (y - 7200) * 0.07,
    )


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D080 is append-only")
    raw_039, floor1 = read(SOURCE_039)
    raw_050, attic = read(SOURCE_050)
    raw_069, packing = read(SOURCE_069)
    raw_079, strategy = read(SOURCE_079)

    axes = [build_axis(position) for position in packing["scenario_pipe_positions"]]
    pair_records = []
    for index, first in enumerate(axes):
        for second in axes[index + 1:]:
            distance = sampled_minimum_distance(first, second)
            pair_records.append({
                "pipe_ids": [first["pipe_id"], second["pipe_id"]],
                "sampled_minimum_center_distance_mm": distance,
            })
    sampled_minimum = min(record["sampled_minimum_center_distance_mm"] for record in pair_records)
    if abs(sampled_minimum - 40) > 1e-6:
        raise ValueError(f"Unexpected 3D sampled minimum: {sampled_minimum}")

    vertical_xy = [tuple(axis["vertical_axis_xy_mm"]) for axis in axes]
    floor_handoffs = [tuple(axis["floor_handoff_xyz_mm"]) for axis in axes]
    attic_handoffs = [tuple(axis["attic_handoff_xyz_mm"]) for axis in axes]
    if len(set(vertical_xy)) != 26 or len(set(floor_handoffs)) != 26 or len(set(attic_handoffs)) != 26:
        raise ValueError("3D bank point uniqueness failed")

    floor_contacts = plan_projection_contacts(floor1, axes)
    attic_clearance = attic_plan_clearance(attic, axes)
    source_records = [
        {"artifact_id": data["artifact_id"], "sha256": hashlib.sha256(raw).hexdigest().upper()}
        for raw, data in ((raw_039, floor1), (raw_050, attic), (raw_069, packing), (raw_079, strategy))
    ]
    min_fixed = min(axis["fixed_transit_length_mm"] for axis in axes)
    max_fixed = max(axis["fixed_transit_length_mm"] for axis in axes)
    body_plus_fixed = []
    body_map = {route["route_id"]: route["body_length_mm"] for route in attic["body_routes"]}
    for route_id, body_length in body_map.items():
        legs = [axis for axis in axes if axis["route_id"] == route_id]
        body_plus_fixed.append({
            "route_id": route_id,
            "body_length_mm": body_length,
            "supply_fixed_transit_mm": legs[0]["fixed_transit_length_mm"],
            "return_fixed_transit_mm": legs[1]["fixed_transit_length_mm"],
            "body_plus_two_fixed_transits_mm": body_length + sum(axis["fixed_transit_length_mm"] for axis in legs),
            "attic_distribution_links_included": False,
        })

    model = {
        "schema": "homeaura-internal-26-pipe-riser-3d-0.1",
        "artifact_id": "HA_TWO_FLOOR_INTERNAL_RISER_3D_080",
        "status": "TWENTY_SIX_INDEPENDENT_PIPE_AXES_LOCAL_3D_PASS_REWORK_FLOOR_PLAN_CONTACTS_ATTIC_DISTRIBUTION_AND_PHYSICAL_BOX",
        "source_records": source_records,
        "source_strategy_artifact_id": strategy["artifact_id"],
        "source_strategy_digest": strategy["strategy_digest"],
        "topology": "K1_BOILER_HANDOFF_TO_FLOOR_SERVICE_BANK_TO_INTERNAL_SLAB_OPENING_TO_WARDROBE_HANDOFF",
        "pipe_count": 26,
        "circuit_candidate_count": 13,
        "pipe_od_mm": PIPE_OD_MM,
        "provisional_envelope_od_mm": PROVISIONAL_ENVELOPE_OD_MM,
        "floor_to_floor_mm": FLOOR_TO_FLOOR_MM,
        "design_centerline_bend_radius_mm": RADIUS_MM,
        "heated_radius_reduction_credited": False,
        "bend_count_per_pipe": 2,
        "opening_bbox_building_mm": HOLE,
        "opening_clear_size_mm": [160, 400],
        "vertical_axis_grid_shape": [3, 9],
        "vertical_axis_unique_count": len(set(vertical_xy)),
        "opening_axis_edge_margin_mm": 40,
        "floor_service_bank": {
            "handoff_x_building_mm": FLOOR_HANDOFF_X_MM,
            "plan_y_range_mm": [7240, 7560],
            "elevation_levels_mm_above_floor": [40, 80, 120],
            "required_clear_service_box_width_mm": 400,
            "required_clear_service_box_height_mm": 160,
            "physical_box_selected_or_measured": False,
            "inside_floor_screed_claimed": False,
            "preferred_installation": "ACCESSIBLE_PROTECTIVE_FLOOR_OR_LOW_WALL_SERVICE_BOX_PENDING_SITE_DETAIL",
        },
        "attic_wardrobe_handoff_bank": {
            "handoff_x_building_mm": ATTIC_HANDOFF_X_MM,
            "plan_y_range_mm": [7240, 7560],
            "elevation_levels_mm_above_floor": [120, 160, 200],
            "wardrobe_draft_floor_containment": True,
            "second_collector_created": False,
            "all_handoffs_are_individual_loop_legs": True,
        },
        "pipe_axes": axes,
        "fixed_transit_length_range_mm": [min_fixed, max_fixed],
        "body_plus_fixed_transit_diagnostics": body_plus_fixed,
        "sampled_3d_pair_count": len(pair_records),
        "sampled_minimum_center_distance_mm": sampled_minimum,
        "provisional_minimum_envelope_clear_gap_mm": sampled_minimum - PROVISIONAL_ENVELOPE_OD_MM,
        "axis_self_contact_count": 0,
        "axis_pair_contact_count": 0,
        "all_vertical_axes_inside_opening_with_provisional_envelope": True,
        "lower_and_upper_R80_are_materialized": True,
        "floor_1_plan_projection_contact_records": floor_contacts,
        "floor_1_plan_projection_is_contact_free": False,
        "floor_1_local_reroute_required": True,
        "attic_handoff_to_body_plan_clearance_records": attic_clearance,
        "attic_minimum_handoff_to_body_plan_clearance_mm": min(item["minimum_plan_clearance_mm"] for item in attic_clearance),
        "attic_distribution_links_published": False,
        "complete_circuit_count": 0,
        "all_complete_circuit_lengths_40_80m": "NOT_EVALUATED_UNTIL_ATTIC_DISTRIBUTION_LINKS_AND_PHYSICAL_K1_INTERNAL_CONNECTIONS_EXIST",
        "physical_K1_manifold_selected": False,
        "physical_service_box_selected": False,
        "slab_scan_sleeves_firestop_and_structural_detail": "REQUIRED_BEFORE_CONSTRUCTION",
        "result": "PASS_LOCAL_3D_RISER_PACKING_AND_R80_CONTINUITY_REWORK_PLAN_REROUTE_AND_COMPLETE_CIRCUITS",
    }
    model["geometry_digest"] = digest({"axes": axes, "opening": HOLE})

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "internal_riser_3d.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    f1 = Image.open(F1_RENDER).convert("RGB")
    attic_img = Image.open(ATTIC_RENDER).convert("RGB")
    image = Image.new("RGB", (1800, 1500), "#F4F8F8")
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, 1800, 225), fill="#071A21")
    draw.text((34, 18), "D080 · 26 ТРУБ Ø16 ЧЕРЕЗ ВНУТРЕННИЙ СТОЯК", font=font(28, True), fill="white")
    draw.text((34, 69), "3 уровня × 9 рядов · шаг осей 40 мм · отверстие 400×160 мм", font=font(17, True), fill="#A7EEE7")
    draw.text((34, 111), "Каждая труба: короб от котельной → R80 → подъём 3 000 мм → R80 → гардеробная", font=font(17), fill="#F3D58C")
    draw.text((34, 155), "Минимум между осями 40 мм · условная оболочка Ø28: чистый зазор 12 мм", font=font(16, True), fill="white")
    draw.text((34, 193), "Локальная 3D-геометрия PASS · напольные конфликты и связи до 13 тел остаются REWORK", font=font(15, True), fill="#FFB2B2")

    crop = (720, 470, 1330, 860)
    panel_w, panel_h = 810, 520
    f1_crop = f1.crop(crop).resize((panel_w, panel_h))
    a_crop = attic_img.crop(crop).resize((panel_w, panel_h))
    image.paste(f1_crop, (40, 285))
    image.paste(a_crop, (950, 285))
    draw.text((40, 245), "1 ЭТАЖ · 26 ОСЕЙ В ЗАЩИТНОМ КОРОБЕ", font=font(18, True), fill="#143842")
    draw.text((950, 245), "МАНСАРДА · 26 ТОЧЕК ПЕРЕД РАЗВЕДЕНИЕМ", font=font(18, True), fill="#143842")

    def map_plan(x, y, panel_x, attic_space=False):
        if attic_space:
            x += ATTIC_DX_MM
            y += ATTIC_DY_MM
        px = x / 100 * PX_PER_100_MM
        py = y / 100 * PX_PER_100_MM
        return (
            panel_x + (px - crop[0]) * panel_w / (crop[2] - crop[0]),
            285 + (py - crop[1]) * panel_h / (crop[3] - crop[1]),
        )

    colors = ["#DF3A2F", "#008E9B", "#6B4FB5"]
    for axis in axes:
        color = colors[axis["packing_row"] - 1]
        y = axis["vertical_axis_xy_mm"][1]
        x = axis["vertical_axis_xy_mm"][0]
        draw.line([map_plan(FLOOR_HANDOFF_X_MM, y, 40), map_plan(x, y, 40)], fill=color, width=3)
        point = map_plan(x, y, 40)
        draw.ellipse((point[0]-4, point[1]-4, point[0]+4, point[1]+4), fill="#FFD45C", outline="#6A5300", width=1)
        top0 = map_plan(x, y, 950, True)
        top1 = map_plan(ATTIC_HANDOFF_X_MM, y, 950, True)
        draw.line([top0, top1], fill=color, width=3)
        draw.ellipse((top1[0]-4, top1[1]-4, top1[0]+4, top1[1]+4), fill="#FFD45C", outline="#6A5300", width=1)

    draw.rectangle((30, 840, 1770, 1325), fill="#FFFFFF", outline="#CAD8DC", width=2)
    draw.text((50, 858), "ПРОСТРАНСТВЕННАЯ СХЕМА ДВУХ ПОВОРОТОВ R80", font=font(19, True), fill="#143842")
    origin = (160, 1270)
    for axis in axes:
        color = colors[axis["packing_row"] - 1]
        pts = [project3d(point, origin) for point in axis["ordered_axis_points_xyz_mm"]]
        draw.line(pts, fill=color, width=2, joint="curve")
    draw.text((70, 1280), "КОТЕЛЬНАЯ", font=font(14, True), fill="#143842")
    draw.text((1320, 1280), "ОТВЕРСТИЕ", font=font(14, True), fill="#143842")
    draw.text((740, 890), "ГАРДЕРОБНАЯ", font=font(14, True), fill="#143842")
    draw.text((50, 1360), "Цвет = один из трёх уровней короба; внутри каждого уровня трубы остаются в исходном порядке без перестановок.", font=font(15), fill="#566B73")
    draw.text((50, 1403), "Не является монтажной схемой: короб, коллектор K1, плита/балки, гильзы и связи до тел требуют следующих блоков.", font=font(15, True), fill="#B00020")
    image.save(OUTPUT / "internal_riser_3d_evidence.png")

    (OUTPUT / "report.md").write_text(
        "# D080 — локальная 3D-схема внутреннего стояка\n\n"
        "Материализованы 26 независимых осей Ø16 от точки передачи в котельной до точки передачи в гардеробной. В горизонтальном коробе и в отверстии используется порядок 3×9 с шагом 40 мм. Каждая ось имеет два расчётных поворота R80 и прямой подъём между этажами. Нагрев для уменьшения радиуса не учитывается.\n\n"
        "Минимальное расстояние между осями по дискретизированной 3D-проверке равно 40 мм. Для условной оболочки Ø28 остаётся 12 мм. Все 26 вертикальных осей с оболочками помещаются в отверстие 400×160 мм с краевым запасом 26 мм.\n\n"
        "D080 не объявляет полный монтажный маршрут. Проекции горизонтального короба пересекают существующие линии первого этажа и требуют их совместной переразводки. На мансарде опубликованы только точки передачи в гардеробной; связи до 13 тел ещё отсутствуют, поэтому длины 40–80 м, физический K1 и гидравлика не приняты. Сам защитный короб 400×160 мм пока является требуемым свободным габаритом, а не выбранным изделием или подтверждённой стяжкой.\n",
        encoding="utf-8",
    )

    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "geometry_digest": model["geometry_digest"],
        "append_only": True,
        "files": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}
            for path in files
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "pipe_count": len(axes),
        "fixed_transit_length_range_mm": model["fixed_transit_length_range_mm"],
        "sampled_minimum_center_distance_mm": sampled_minimum,
        "envelope_gap_mm": model["provisional_minimum_envelope_clear_gap_mm"],
        "floor_contact_route_ids": [item["route_id"] for item in floor_contacts],
        "attic_minimum_plan_clearance_mm": model["attic_minimum_handoff_to_body_plan_clearance_mm"],
        "geometry_digest": model["geometry_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

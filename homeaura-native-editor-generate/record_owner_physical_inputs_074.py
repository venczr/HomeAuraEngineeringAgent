from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_058 = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058" / "attic_plan_space_diagnostic.json"
SOURCE_069 = BASE / "HA_TWO_FLOOR_ATTIC_RISER_PACKING_SCOPE_069" / "attic_riser_packing_scenario.json"
SOURCE_072 = BASE / "HA_TWO_FLOOR_ATTIC_PHYSICAL_INPUT_GATE_072" / "attic_physical_input_gate.json"
OUTPUT = BASE / "HA_TWO_FLOOR_OWNER_PHYSICAL_INPUTS_074"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_OWNER_PHYSICAL_INPUTS_074.zip"

FLOOR_TO_FLOOR_HEIGHT_MM = 3000
PIPE_OD_MM = 16
DESIGN_CENTERLINE_BEND_RADIUS_MM = 80
WALL_MATERIAL = "AUTOCLAVED_AERATED_CONCRETE_GASOBETON"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D074 is append-only")
    raw_058 = SOURCE_058.read_bytes()
    raw_069 = SOURCE_069.read_bytes()
    raw_072 = SOURCE_072.read_bytes()
    source_058 = json.loads(raw_058.decode("utf-8"))
    source_069 = json.loads(raw_069.decode("utf-8"))

    vertical_leg_mm = FLOOR_TO_FLOOR_HEIGHT_MM
    vertical_pair_mm = 2 * vertical_leg_mm
    fragment_bounds = []
    for fragment in source_058["diagnostic_planar_fragments"]:
        planar = fragment["planar_fragment_length_mm"]
        lower_bound = planar + vertical_pair_mm
        fragment_bounds.append({
            "route_id": fragment["route_id"],
            "planar_diagnostic_fragment_length_mm": planar,
            "owner_supplied_vertical_supply_length_mm": vertical_leg_mm,
            "owner_supplied_vertical_return_length_mm": vertical_leg_mm,
            "known_length_lower_bound_mm": lower_bound,
            "remaining_headroom_to_80000_mm": 80000 - lower_bound,
            "known_lower_bound_at_least_40000": lower_bound >= 40000,
            "known_lower_bound_at_most_80000": lower_bound <= 80000,
            "complete_circuit_length_status": "NOT_COMPLETE_K1_PLANAR_APPROACH_AND_PHYSICAL_TRANSITIONS_MISSING",
        })

    model = {
        "schema": "homeaura-owner-physical-inputs-0.1",
        "artifact_id": "HA_TWO_FLOOR_OWNER_PHYSICAL_INPUTS_074",
        "status": "OWNER_HEIGHT_WALL_PIPE_AND_BEND_INPUTS_ACCEPTED_LENGTH_LOWER_BOUNDS_UPDATED_REWORK_R1_LOCATION_AND_COMPLETE_ROUTES",
        "source_D058_artifact_id": source_058["artifact_id"],
        "source_D058_sha256": hashlib.sha256(raw_058).hexdigest().upper(),
        "source_D069_artifact_id": source_069["artifact_id"],
        "source_D069_sha256": hashlib.sha256(raw_069).hexdigest().upper(),
        "source_D072_artifact_id": "HA_TWO_FLOOR_ATTIC_PHYSICAL_INPUT_GATE_072",
        "source_D072_sha256": hashlib.sha256(raw_072).hexdigest().upper(),
        "owner_inputs_received_date": "2026-08-13",
        "owner_inputs": {
            "floor_to_floor_height_raw": "3",
            "floor_to_floor_height_interpretation": "3_METRES",
            "floor_to_floor_height_mm": FLOOR_TO_FLOOR_HEIGHT_MM,
            "wall_material": WALL_MATERIAL,
            "pipe_outer_diameter_mm": PIPE_OD_MM,
            "design_minimum_bend_radius_mm": DESIGN_CENTERLINE_BEND_RADIUS_MM,
            "bend_radius_reference": "PIPE_CENTERLINE",
            "heated_bending_radius_reduction_allowed_by_owner": True,
            "heated_bending_radius_reduction_credited_in_design": False,
            "design_uses_conservative_radius_mm": DESIGN_CENTERLINE_BEND_RADIUS_MM,
        },
        "r1_definition": {
            "R1": "VERTICAL_SUPPLY_RETURN_RISER_BETWEEN_FLOOR_1_K1_AND_ATTIC",
            "penetration_meaning": "PHYSICAL_HOLE_OR_SLEEVE_THROUGH_FLOOR_SLAB_OR_ADJACENT_BUILDING_ELEMENT_FOR_THE_RISER_PIPES",
            "penetration_is_separate_equipment": False,
        },
        "vertical_length_contract": {
            "vertical_length_per_leg_mm": vertical_leg_mm,
            "vertical_supply_and_return_per_circuit_mm": vertical_pair_mm,
            "assumed_candidate_circuit_count": source_069["assumed_body_candidate_count"],
            "assumed_distinct_vertical_pipe_count": source_069["assumed_distinct_vertical_pipe_count"],
            "aggregate_vertical_pipe_length_for_26_candidate_legs_mm": source_069["assumed_distinct_vertical_pipe_count"] * vertical_leg_mm,
            "vertical_length_is_now_evaluated": True,
        },
        "bend_contract": {
            "pipe_od_mm": PIPE_OD_MM,
            "minimum_centerline_radius_mm": DESIGN_CENTERLINE_BEND_RADIUS_MM,
            "minimum_radius_to_od_ratio": DESIGN_CENTERLINE_BEND_RADIUS_MM / PIPE_OD_MM,
            "sharp_manhattan_corners_are_not_physical_bend_evidence": True,
            "exact_arc_length_reconciliation": "NOT_EVALUATED_UNTIL_PHYSICAL_TRANSITIONS_ARE_ROUTED",
        },
        "seven_diagnostic_fragment_length_lower_bounds": fragment_bounds,
        "known_lower_bound_40_80_count": sum(item["known_lower_bound_at_least_40000"] and item["known_lower_bound_at_most_80000"] for item in fragment_bounds),
        "known_lower_bound_below_40000_route_ids": [item["route_id"] for item in fragment_bounds if not item["known_lower_bound_at_least_40000"]],
        "known_lower_bound_above_80000_route_ids": [item["route_id"] for item in fragment_bounds if not item["known_lower_bound_at_most_80000"]],
        "still_required_for_complete_routes": [
            "physical R1 penetration plan coordinates and clear dimensions",
            "K1 to R1 floor-1 planar approach geometry",
            "attic R1 exit and approach geometry",
            "bend/arc and fitting length reconciliation",
            "wall/slab penetration permission and firestop detail",
            "global zero-contact routing validation",
        ],
        "physical_R1_penetration_location": "NOT_SELECTED",
        "physical_R1_penetration_clear_bbox_mm": None,
        "new_pipe_geometry_count": 0,
        "new_gate_count": 0,
        "complete_attic_circuit_count": 0,
        "geometry_modified": False,
        "result": "PASS_OWNER_INPUT_REGISTRATION_AND_VERTICAL_LENGTH_BOUNDS_REWORK_PHYSICAL_R1_AND_COMPLETE_ROUTING",
    }
    model["input_contract_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "owner_physical_inputs.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    image = Image.new("RGB", (1800, 1320), "#F7FAFA")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 205), fill="#071A21")
    canvas.text((36, 20), "D074 · ДАННЫЕ ВЛАДЕЛЬЦА ПРИНЯТЫ", font=font(30, True), fill="white")
    canvas.text((36, 74), "Высота 3 000 мм · газобетон · труба Ø16 мм · проектный радиус по оси 80 мм", font=font(19, True), fill="#A7EEE7")
    canvas.text((36, 122), "Уменьшение радиуса при прогреве в расчёт НЕ ЗАСЧИТАНО", font=font(16, True), fill="#F3D58C")
    canvas.text((36, 164), "R1 = вертикальные подача+обратка; проходка = отверстие/гильза через перекрытие или соседний элемент", font=font(15), fill="#E8F0F2")

    canvas.rounded_rectangle((50, 245, 1750, 440), radius=22, fill="#EAF3F4", outline="#A7BBC1", width=2)
    canvas.text((80, 272), "Что изменилось в длинах", font=font(22, True), fill="#143842")
    canvas.text((80, 320), "Каждый контур: +3 000 мм подача вверх +3 000 мм обратка вниз = +6 000 мм", font=font(18, True), fill="#143842")
    canvas.text((80, 365), "Для 13 кандидатов: 26 вертикальных ног ×3 000 мм = 78 000 мм вертикальной трубы", font=font(17), fill="#334D55")
    canvas.text((80, 405), "Это длина прямых вертикальных частей; дуги и подводы будут добавлены после выбора места R1", font=font(14), fill="#8A1A1A")

    headers = ["Контур", "План, м", "+ вертикаль, м", "Нижняя граница, м", "До 80 м, м", "Статус"]
    col_x = [70, 310, 535, 800, 1100, 1340]
    y = 500
    for x, header in zip(col_x, headers):
        canvas.text((x, y), header, font=font(15, True), fill="#143842")
    y += 42
    for index, item in enumerate(fragment_bounds):
        if index % 2 == 0:
            canvas.rectangle((55, y - 8, 1745, y + 38), fill="#EDF4F5")
        values = [
            item["route_id"],
            f"{item['planar_diagnostic_fragment_length_mm']/1000:.1f}",
            "6.0",
            f"{item['known_length_lower_bound_mm']/1000:.1f}",
            f"{item['remaining_headroom_to_80000_mm']/1000:.1f}",
            "40–80 lower bound" if item["known_lower_bound_at_least_40000"] else "пока <40",
        ]
        for x, value in zip(col_x, values):
            canvas.text((x, y), value, font=font(14, x == col_x[0]), fill="#23424C" if "<40" not in value else "#B00020")
        y += 55
    canvas.text((55, 1000), "Важно: это нижние границы, не полные контуры. A-C10/A-C11 доберут длину только естественными подводами, без искусственной змейки.", font=font(16, True), fill="#B00020")
    canvas.text((55, 1060), "Осталось определить на плане место отверстия/гильзы R1 и его чистый размер; после этого можно строить физические подводы.", font=font(17, True), fill="#7B4C00")
    canvas.text((55, 1120), "Новых труб и ворот в D074: 0 · геометрия D058 не менялась · гидравлика ещё не рассчитана", font=font(15), fill="#566B73")
    image.save(OUTPUT / "owner_physical_inputs_and_length_bounds.png")

    (OUTPUT / "report.md").write_text(
        "# D074 — принятые физические данные владельца\n\n"
        "Зафиксированы: высота между этажами 3 000 мм, стены из газобетона, труба Ø16 мм и проектный минимальный радиус изгиба по оси 80 мм. "
        "Уменьшение радиуса при прогреве не используется как расчётный запас.\n\n"
        "R1 — это вертикальная пара подача/обратка между K1 первого этажа и мансардой. Проходка R1 означает физическое отверстие или гильзу через перекрытие либо соседний строительный элемент, а не отдельное оборудование. "
        "Вертикальная часть теперь равна 3 000 мм на каждую ногу, то есть 6 000 мм на мансардный контур.\n\n"
        "Длины семи диагностических планарных фрагментов пересчитаны как нижние границы с вертикалью. Полными контурами они не стали: ещё отсутствуют выбранное место проходки, подвод K1→R1, выход R1 на мансарде и физические дуги радиусом 80 мм.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "input_contract_digest": model["input_contract_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "height_mm": 3000, "vertical_pair_mm": 6000, "lower_bounds_mm": {item['route_id']: item['known_length_lower_bound_mm'] for item in fragment_bounds}, "digest": model["input_contract_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

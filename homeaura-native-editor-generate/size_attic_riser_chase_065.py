from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_RISER_PACKING_065"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_RISER_PACKING_065.zip"

PIPE_OD_MM = 16
PROVISIONAL_INSULATED_ENVELOPE_OD_MM = 28
CENTER_PITCH_MM = 40
CHASE_CLEAR_WIDTH_MM = 400
CHASE_CLEAR_DEPTH_MM = 160
ROW_COUNTS = [9, 9, 8]
X_START_MM = 40
Y_ROWS_MM = [40, 80, 120]


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D065 is append-only")
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    pipe_ids = [f'{route["route_id"]}-{leg}' for route in source["body_routes"] for leg in ("S", "R")]
    positions = []
    cursor = 0
    for row_index, (count, y) in enumerate(zip(ROW_COUNTS, Y_ROWS_MM), start=1):
        for column in range(count):
            pipe_id = pipe_ids[cursor]
            positions.append({
                "pipe_id": pipe_id,
                "route_id": pipe_id.rsplit("-", 1)[0],
                "leg": "SUPPLY" if pipe_id.endswith("-S") else "RETURN",
                "row": row_index,
                "column": column + 1,
                "center_mm": [X_START_MM + column * CENTER_PITCH_MM, y],
                "pipe_od_mm": PIPE_OD_MM,
                "provisional_insulated_envelope_od_mm": PROVISIONAL_INSULATED_ENVELOPE_OD_MM,
            })
            cursor += 1
    if len(positions) != 26 or len({tuple(item["center_mm"]) for item in positions}) != 26:
        raise RuntimeError("riser position count")
    minimum_center_distance = min(math.dist(a["center_mm"], b["center_mm"]) for index, a in enumerate(positions) for b in positions[index + 1:])
    minimum_pipe_clear_gap = minimum_center_distance - PIPE_OD_MM
    minimum_insulated_clear_gap = minimum_center_distance - PROVISIONAL_INSULATED_ENVELOPE_OD_MM
    minimum_wall_clearance = min(
        min(x - PROVISIONAL_INSULATED_ENVELOPE_OD_MM / 2, CHASE_CLEAR_WIDTH_MM - x - PROVISIONAL_INSULATED_ENVELOPE_OD_MM / 2, y - PROVISIONAL_INSULATED_ENVELOPE_OD_MM / 2, CHASE_CLEAR_DEPTH_MM - y - PROVISIONAL_INSULATED_ENVELOPE_OD_MM / 2)
        for x, y in (item["center_mm"] for item in positions)
    )
    model = {
        "schema": "homeaura-attic-riser-packing-assumption-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_RISER_PACKING_065",
        "status": "TWENTY_SIX_VERTICAL_PIPE_CROSS_SECTION_FITS_ASSUMED_CHASE_REWORK_PRODUCT_BENDS_LOCATION_AND_INTERFACE",
        "source_D050_artifact_id": source["artifact_id"],
        "source_D050_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "attic_circuit_count": 13,
        "distinct_vertical_pipe_count": 26,
        "shared_pipe_trunk": False,
        "assumptions_are_product_selection": False,
        "pipe_od_mm_assumption": PIPE_OD_MM,
        "provisional_insulated_envelope_od_mm": PROVISIONAL_INSULATED_ENVELOPE_OD_MM,
        "center_pitch_mm": CENTER_PITCH_MM,
        "chase_clear_internal_bbox_mm": [0, 0, CHASE_CLEAR_WIDTH_MM, CHASE_CLEAR_DEPTH_MM],
        "row_counts": ROW_COUNTS,
        "pipe_positions": positions,
        "minimum_center_distance_mm": minimum_center_distance,
        "minimum_bare_pipe_clear_gap_mm": minimum_pipe_clear_gap,
        "minimum_provisional_insulated_envelope_clear_gap_mm": minimum_insulated_clear_gap,
        "minimum_provisional_insulated_envelope_to_chase_wall_mm": minimum_wall_clearance,
        "cross_section_overlap_count": 0,
        "cross_section_containment_pass": minimum_wall_clearance >= 0,
        "chase_outer_construction_thickness": "NOT_EVALUATED",
        "bend_radius_and_fanout": "NOT_EVALUATED",
        "vertical_riser_length_mm": None,
        "firestopping": "NOT_EVALUATED",
        "condensation_and_insulation_product": "NOT_SELECTED",
        "hydraulics": "NOT_CALCULATED",
        "commercial_manifold_banks": "NOT_SELECTED",
        "r1_plan_location": "NOT_SELECTED",
        "floor_penetration_location": "NOT_SELECTED",
        "physical_r1_interface_status": "NOT_EVALUATED",
        "approved_installation_detail": False,
        "result": "PASS_ASSUMPTION_BASED_CROSS_SECTION_CAPACITY_REWORK_PHYSICAL_DESIGN_AND_PRODUCT_SELECTION",
    }
    model["packing_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_riser_packing.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    scale = 3
    ox, oy = 130, 260
    image = Image.new("RGB", (1600, 1050), "#F7FAFA")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 205), fill="#071A21")
    canvas.text((32, 18), "D065 · 26 ОТДЕЛЬНЫХ ТРУБ · ПРОВЕРКА СЕЧЕНИЯ СТОЯКА", font=font(25, True), fill="white")
    canvas.text((32, 62), "Допущение: труба Ø16 мм · временный изолированный envelope Ø28 мм · шаг осей 40 мм", font=font(16), fill="#A7EEE7")
    canvas.text((32, 100), "Чистый внутренний габарит 400×160 мм · ряды 9+9+8 · наложений 0", font=font(16, True), fill="#F3D58C")
    canvas.text((32, 138), "Это не выбранная шахта и не монтажный узел: место, изгибы, огнезаделка и изделия REWORK", font=font(15, True), fill="#FFB2B2")
    canvas.text((32, 173), "Один логический R1 может включать несколько физических гребёнок/кассет; коммерческая комплектация не выбрана", font=font(13), fill="#E8F0F2")
    canvas.rectangle((ox, oy, ox + CHASE_CLEAR_WIDTH_MM * scale, oy + CHASE_CLEAR_DEPTH_MM * scale), fill="#E8F0F2", outline="#23424C", width=5)
    colours = {"SUPPLY": "#D64B4B", "RETURN": "#3978C6"}
    envelope_radius = PROVISIONAL_INSULATED_ENVELOPE_OD_MM * scale / 2
    pipe_radius = PIPE_OD_MM * scale / 2
    for item in positions:
        x = ox + item["center_mm"][0] * scale
        y = oy + item["center_mm"][1] * scale
        canvas.ellipse((x - envelope_radius, y - envelope_radius, x + envelope_radius, y + envelope_radius), fill="#FFF2B8", outline="#8D5900", width=2)
        canvas.ellipse((x - pipe_radius, y - pipe_radius, x + pipe_radius, y + pipe_radius), fill=colours[item["leg"]], outline="white", width=2)
        canvas.text((x - 14, y - 8), item["pipe_id"].replace("A-C", "").replace("-", ""), font=font(7, True), fill="white")
    legend_y = 815
    canvas.text((130, legend_y), f'Минимум по осям: {minimum_center_distance:.0f} мм', font=font(15, True), fill="#23424C")
    canvas.text((130, legend_y + 35), f'Зазор между Ø16: {minimum_pipe_clear_gap:.0f} мм · между envelope Ø28: {minimum_insulated_clear_gap:.0f} мм', font=font(15), fill="#23424C")
    canvas.text((130, legend_y + 70), f'Минимум от envelope до внутренней грани шахты: {minimum_wall_clearance:.0f} мм', font=font(15), fill="#23424C")
    canvas.text((130, legend_y + 115), "Красный = подача · синий = обратка · жёлтый = временный envelope, не выбранная изоляция", font=font(14), fill="#566B73")
    image.save(OUTPUT / "attic_riser_packing_cross_section.png")
    (OUTPUT / "report.md").write_text(
        "# D065 — проверка вместимости стояка\n\n"
        "В чистом сечении 400×160 мм размещены 26 отдельных вертикальных труб в трёх рядах 9+9+8. Приняты только расчётные допущения: Ø16 мм, временный envelope Ø28 мм и шаг осей 40 мм. Наложений нет.\n\n"
        "Эта проверка отвечает только на вопрос вместимости поперечного сечения. Она не выбирает изделие, место шахты, радиусы поворотов, огнезаделку или способ выхода в плоскость пола.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "packing_digest": model["packing_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "pipes": 26, "chase_mm": [400,160], "minimum_envelope_gap_mm": minimum_insulated_clear_gap, "minimum_wall_mm": minimum_wall_clearance, "digest": model["packing_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

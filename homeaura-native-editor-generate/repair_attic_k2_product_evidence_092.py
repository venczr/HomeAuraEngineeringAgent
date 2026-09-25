from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_K2_PRODUCT_SELECTION_091"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_K2_PRODUCT_EVIDENCE_092"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_K2_PRODUCT_EVIDENCE_092.zip"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D092 is append-only")
    source_path = SOURCE / "attic_k2_product_selection.json"
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    model = deepcopy(source)
    manifold = model["selected_design_basis_manifold"]
    cabinet = model["selected_design_basis_cabinet"]
    fit = model["fit_validation"]
    service = fit["service_zone_bbox_building_mm"]
    cabinet_bbox = fit["cabinet_bbox_plan_building_mm"]
    internal_mounting_margin = cabinet["internal_mounting_length_l1_mm"] - manifold["product_measurement_LENGTH_L_mm"]
    outer_length_difference = cabinet["cabinet_length_mm"] - manifold["product_measurement_LENGTH_L_mm"]
    if internal_mounting_margin != 275 or outer_length_difference != 336:
        raise RuntimeError({"internal": internal_mounting_margin, "outer": outer_length_difference})

    model.update(
        schema="homeaura-attic-k2-product-evidence-repair-0.1",
        artifact_id="HA_TWO_FLOOR_ATTIC_K2_PRODUCT_EVIDENCE_092",
        status="K2_MANIFOLD_AND_ON_WALL_CABINET_DESIGN_BASIS_FIT_PASS_REWORK_PROCUREMENT_FIXINGS_PORTS_AND_HYDRAULICS",
        derived_from_artifact_id=source["artifact_id"],
        derived_from_sha256=hashlib.sha256(source_bytes).hexdigest().upper(),
        D091_margin_field_disposition={
            "field": "fit_validation.manifold_length_margin_inside_cabinet_l1_mm",
            "stored_D091_value_mm": fit["manifold_length_margin_inside_cabinet_l1_mm"],
            "stored_value_semantics": "CABINET_OUTER_LENGTH_1050_MINUS_MANIFOLD_LENGTH_714",
            "correct_internal_mounting_margin_mm": internal_mounting_margin,
            "D091_field_rejected": True,
        },
        official_cabinet_compatibility_evidence={
            "official_technical_information_url": "https://brandportal.uponor.com/m/10296a3f66e9083a/original/TI-Vario-cabinets-EN-1095069.pdf",
            "accessed_date": "2026-08-13",
            "manifold_family": "UPONOR_VARIO_S",
            "connection_orientation": "HORIZONTAL_WITHOUT_HEAT_METER_CONNECTION_SET",
            "circuit_count": 12,
            "minimum_official_cabinet_internal_width_class_mm": 850,
            "selected_cabinet_internal_mounting_length_l1_mm": cabinet["internal_mounting_length_l1_mm"],
            "selected_cabinet_compatibility_pass": cabinet["internal_mounting_length_l1_mm"] >= 850,
        },
    )
    fit.update(
        manifold_length_margin_inside_cabinet_l1_mm=internal_mounting_margin,
        cabinet_outer_length_minus_manifold_length_mm=outer_length_difference,
        selected_cabinet_compatibility_by_official_table=True,
        selected_cabinet_internal_mounting_length_l1_mm=cabinet["internal_mounting_length_l1_mm"],
        minimum_official_cabinet_internal_width_class_for_12_horizontal_loops_mm=850,
        result="PASS_PLAN_AND_OFFICIAL_COMPATIBILITY_TABLE_FIT_REWORK_MOUNTING_HEIGHT_FIXINGS_AND_PORT_ORIGIN",
    )
    model["result"] = "PASS_CORRECTED_K2_AND_ON_WALL_CABINET_FIT_REWORK_PORT_GEOMETRY_PROCUREMENT_FIXINGS_AND_HYDRAULICS"
    model.pop("product_selection_digest", None)
    model["evidence_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_k2_product_selection_corrected.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    canvas = Image.new("RGB", (1700, 1120), "#F4F8F8")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, canvas.width, 205), fill="#071A21")
    draw.text((34, 18), "D092 · ИСПРАВЛЕННОЕ ДОКАЗАТЕЛЬСТВО ВЫБОРА K2", font=font(23, True), fill="white")
    draw.text((34, 63), "Uponor Vario S FM 12 · 1140843 + накладной шкаф OW 1050×730×135 · 1136219", font=font(17, True), fill="#A7EEE7")
    draw.text((34, 105), "12 контуров · G3/4 Eurocone · G1 · шаг 50 мм · рейки 215 мм", font=font(17), fill="#F3D58C")
    draw.text((34, 145), "Официальная таблица: горизонтально 10–12 контуров → шкаф l1=850 мм; выбран l1=989 мм", font=font(16, True), fill="white")
    draw.text((34, 179), "ПОРТЫ/КРЕПЁЖ/ПОКУПКА/ГИДРАВЛИКА ЕЩЁ НЕ УТВЕРЖДЕНЫ", font=font(14, True), fill="#FFB2B2")

    draw.rounded_rectangle((90, 270, 1610, 900), radius=18, fill="#FFFFFF", outline="#9BB3BA", width=3)
    scale = 0.62
    sx0, sy0 = 280, 390
    sw, sh = (service[3] - service[1]) * scale, (service[2] - service[0]) * scale
    draw.rectangle((sx0, sy0, sx0 + sw, sy0 + sh), fill="#D9F4E8", outline="#006A43", width=4)
    cab_y = sy0 + (cabinet_bbox[1] - service[1]) * scale
    cab_x = sx0 + (cabinet_bbox[0] - service[0]) * scale
    cab_w = cabinet["cabinet_length_mm"] * scale
    cab_d = cabinet["cabinet_depth_mm"] * scale
    draw.rectangle((cab_y, cab_x, cab_y + cab_w, cab_x + cab_d), fill="#DCE6FA", outline="#244C90", width=4)
    draw.text((sx0, sy0 - 45), "ПЛАН: ЗОНА 1300×300", font=font(15, True), fill="#006A43")
    draw.text((cab_y + 20, cab_x + 20), "OW 1050×135", font=font(13, True), fill="#244C90")

    draw.text((220, 745), "ГЕОМЕТРИЯ ДЛИН", font=font(16, True), fill="#143842")
    draw.text((220, 785), f"Сервисная зона 1300 мм − шкаф 1050 мм = 250 мм → по 125 мм с торцов", font=font(15), fill="#143842")
    draw.text((220, 825), f"Полезная длина шкафа l1=989 мм − коллектор L=714 мм = {internal_mounting_margin} мм", font=font(15, True), fill="#006A43")
    draw.text((220, 865), f"Внешняя длина шкафа 1050 мм − коллектор 714 мм = {outer_length_difference} мм (не монтажный запас l1)", font=font(14), fill="#566B73")
    draw.text((110, 970), "Проектная база подтверждена. До покупки проверить поставку, комплектность и монтажный чертёж.", font=font(15, True), fill="#B00020")
    canvas.save(OUTPUT / "attic_k2_product_evidence.png")

    validation = {
        "artifact_id": model["artifact_id"],
        "source_artifact_id": source["artifact_id"],
        "source_sha256": model["derived_from_sha256"],
        "selected_manifold_part_number": manifold["part_number"],
        "selected_cabinet_part_number": cabinet["part_number"],
        "official_minimum_cabinet_width_class_for_12_horizontal_loops_mm": 850,
        "selected_cabinet_internal_mounting_length_l1_mm": cabinet["internal_mounting_length_l1_mm"],
        "official_compatibility_pass": True,
        "correct_internal_mounting_margin_mm": internal_mounting_margin,
        "outer_length_difference_mm": outer_length_difference,
        "D091_false_margin_field_rejected": True,
        "physical_port_coordinates_bound": False,
        "purchase_authorized": False,
        "result": model["result"],
    }
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "report.md").write_text(
        "# D092 — исправленное доказательство выбора K2\n\n"
        "Выбор D091 сохранён: коллектор Uponor Vario S FM 12, артикул 1140843, и накладной шкаф Uponor OW 1050×730×135, артикул 1136219. Официальная таблица шкафов указывает для Vario S при горизонтальном подключении без теплосчётчика: 10–12 контуров помещаются в класс внутренней длины 850 мм. Выбранный шкаф имеет l1=989 мм и проходит с запасом.\n\n"
        "Исправлена семантика длины: полезный монтажный запас равен 989−714=275 мм. Значение 336 мм — только разница внешней длины шкафа 1050 мм и длины коллектора 714 мм; его нельзя было подписывать как запас l1. Геометрия размещения и выбор изделий не менялись.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"], "evidence_digest": model["evidence_digest"], "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT), "package": str(PACKAGE), "internal_margin_mm": internal_mounting_margin,
        "outer_difference_mm": outer_length_difference, "compatibility": True, "digest": model["evidence_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

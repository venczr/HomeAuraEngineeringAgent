from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_082 = BASE / "HA_TWO_FLOOR_ATTIC_MANIFOLD_SERVICE_ZONE_082" / "attic_manifold_service_zone.json"
SOURCE_085 = BASE / "HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085" / "attic_body_geometry.json"
SOURCE_088 = BASE / "HA_TWO_FLOOR_ATTIC_K2_PORT_LATTICE_088" / "attic_k2_port_lattice.json"
SOURCE_089 = BASE / "HA_TWO_FLOOR_ATTIC_K2_STATION_ASSIGNMENT_089" / "attic_k2_station_assignment.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_K2_PRODUCT_SELECTION_091"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_K2_PRODUCT_SELECTION_091.zip"

SERVICE_BBOX = [9070, 6500, 9370, 7800]
CABINET_LENGTH_MM = 1050
CABINET_HEIGHT_MM = 730
CABINET_DEPTH_MM = 135
CABINET_BACK_PLANE_X_MM = 9370
CABINET_BBOX_PLAN_MM = [
    CABINET_BACK_PLANE_X_MM - CABINET_DEPTH_MM,
    (SERVICE_BBOX[1] + SERVICE_BBOX[3] - CABINET_LENGTH_MM) / 2,
    CABINET_BACK_PLANE_X_MM,
    (SERVICE_BBOX[1] + SERVICE_BBOX[3] + CABINET_LENGTH_MM) / 2,
]
MANIFOLD_LENGTH_MM = 714
MANIFOLD_ITEM_DEPTH_MM = 235
MANIFOLD_ITEM_HEIGHT_MM = 40
LOOP_PITCH_MM = 50
HEADER_PITCH_MM = 215


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def covers(outer, inner):
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D091 is append-only")
    raw_082, service = read(SOURCE_082)
    raw_085, body = read(SOURCE_085)
    raw_088, lattice = read(SOURCE_088)
    raw_089, assignment = read(SOURCE_089)
    product_length_margin = CABINET_LENGTH_MM - MANIFOLD_LENGTH_MM
    cabinet_length_margin = SERVICE_BBOX[3] - SERVICE_BBOX[1] - CABINET_LENGTH_MM
    cabinet_depth_margin = SERVICE_BBOX[2] - SERVICE_BBOX[0] - CABINET_DEPTH_MM
    c01_max_x = body["manifold_outlet_corridor_validation"]["c01_centerline_bounds_building_mm"][2]
    c01_axis_to_cabinet = CABINET_BBOX_PLAN_MM[0] - c01_max_x
    if not covers(SERVICE_BBOX, CABINET_BBOX_PLAN_MM) or product_length_margin < 0 or c01_axis_to_cabinet < 2 * 80:
        raise RuntimeError({"cabinet_fit": covers(SERVICE_BBOX, CABINET_BBOX_PLAN_MM), "product_margin": product_length_margin, "c01": c01_axis_to_cabinet})

    model = {
        "schema": "homeaura-attic-k2-design-basis-product-selection-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_K2_PRODUCT_SELECTION_091",
        "status": "K2_DESIGN_BASIS_MANIFOLD_AND_ON_WALL_CABINET_SELECTED_FIT_PASS_REWORK_PORT_DRAWING_PROCUREMENT_AND_HYDRAULICS",
        "source_records": [
            {"artifact_id": data["artifact_id"], "sha256": hashlib.sha256(raw).hexdigest().upper()}
            for raw, data in ((raw_082, service), (raw_085, body), (raw_088, lattice), (raw_089, assignment))
        ],
        "selected_design_basis_manifold": {
            "manufacturer": "UPONOR_GF_BUILDING_FLOW_SOLUTIONS",
            "product": "UPONOR_VARIO_S_MANIFOLD_FM_12XG3_4_EURO_G1",
            "part_number": "1140843",
            "official_product_url": "https://www.uponor.com/en-en/s/uponor-vario-s-manifold-fm-12xg3-4-euro-g1-1140843",
            "official_product_data_pdf": "https://prod.uponor.com/en-en/product/getproductdatapdf?code=1140843",
            "accessed_date": "2026-08-13",
            "circuit_count": 12,
            "material": "STAINLESS_STEEL",
            "flowmeters": True,
            "flowmeter_range_l_min": [0, 5],
            "loop_connection": "G3_4_EUROCONE",
            "primary_connection": "G1",
            "loop_pitch_mm": LOOP_PITCH_MM,
            "header_pitch_mm": HEADER_PITCH_MM,
            "maximum_pressure_bar_at_60C": 6,
            "item_unit_length_mm": 710,
            "product_measurement_LENGTH_L_mm": MANIFOLD_LENGTH_MM,
            "item_unit_width_mm": MANIFOLD_ITEM_DEPTH_MM,
            "item_unit_height_mm": MANIFOLD_ITEM_HEIGHT_MM,
            "design_basis_selected": True,
            "procurement_availability_and_local_article_confirmation": "REQUIRED",
        },
        "selected_design_basis_cabinet": {
            "manufacturer": "UPONOR_GF_BUILDING_FLOW_SOLUTIONS",
            "product": "UPONOR_VARIO_CABINET_OW_1050X730X135",
            "part_number": "1136219",
            "official_product_url": "https://www.uponor.com/en-gb/s/uponor-vario-cabinet-ow-1050x730x135-1136219",
            "accessed_date": "2026-08-13",
            "mounting_type": "ON_WALL",
            "cabinet_length_mm": CABINET_LENGTH_MM,
            "cabinet_height_mm": CABINET_HEIGHT_MM,
            "cabinet_depth_mm": CABINET_DEPTH_MM,
            "internal_mounting_length_l1_mm": 989,
            "material": "GALVANIZED_STEEL_WHITE_POWDER_COATED",
            "wall_recess_required": False,
            "reason_for_on_wall_selection": "AVOID_FULL_CABINET_RECESS_IN_220MM_AAC_PARTITION",
            "design_basis_selected": True,
            "procurement_availability_and_local_article_confirmation": "REQUIRED",
        },
        "superseded_parametric_geometry": {
            "source_artifact_id": lattice["artifact_id"],
            "D088_header_pitch_mm": lattice["manufacturer_class_evidence"]["header_pitch_mm"],
            "selected_product_header_pitch_mm": HEADER_PITCH_MM,
            "D088_station_y_order_retained_as_assignment_candidate": True,
            "D088_3d_header_z_coordinates_rejected_for_selected_product": True,
            "reason": "SELECTED_ARTICLE_1140843_OFFICIAL_SPECIFICATION_IS_215MM_HEADER_PITCH_NOT_225MM",
        },
        "fit_validation": {
            "service_zone_bbox_building_mm": SERVICE_BBOX,
            "cabinet_bbox_plan_building_mm": CABINET_BBOX_PLAN_MM,
            "service_zone_contains_cabinet_plan_bbox": covers(SERVICE_BBOX, CABINET_BBOX_PLAN_MM),
            "cabinet_length_margin_inside_service_zone_mm": cabinet_length_margin,
            "cabinet_depth_margin_inside_service_zone_mm": cabinet_depth_margin,
            "manifold_length_margin_inside_cabinet_l1_mm": product_length_margin,
            "C01_axis_to_cabinet_front_clearance_mm": c01_axis_to_cabinet,
            "C01_clearance_exceeds_twice_R80": c01_axis_to_cabinet >= 160,
            "wall_mounting_plane_building_x_mm": CABINET_BACK_PLANE_X_MM,
            "wall_finish_build_up_and_mounting_spacer": "NOT_SURVEYED",
            "result": "PASS_PLAN_FIT_REWORK_MOUNTING_HEIGHT_FIXINGS_AND_PRODUCT_DRAWING_PORT_ORIGIN",
        },
        "aac_mounting_detail": {
            "wall_material": "AUTOCLAVED_AERATED_CONCRETE",
            "full_cabinet_recess": False,
            "fixing_type_and_load_spreader": "NOT_DESIGNED_REQUIRES_MANUFACTURER_LOAD_AND_AAC_ANCHOR_DESIGN",
            "wall_chase_for_24_LOOP_PIPES": "NOT_APPROVED_USE_SURFACE_CABINET_AND_FLOOR_ENTRY_ZONE",
        },
        "assignment_candidate_disposition": {
            "source_artifact_id": assignment["artifact_id"],
            "station_order_retained": True,
            "physical_port_coordinates_bound": False,
            "physical_assignment_authority": False,
            "reason": "SELECTED_PRODUCT_DRAWING_ORIGIN_AND_CABINET_MOUNTING_HEIGHT_NOT_YET_BOUND",
        },
        "physical_manifold_selected_as_design_basis": True,
        "physical_cabinet_selected_as_design_basis": True,
        "purchase_authorized": False,
        "physical_port_coordinate_count": 0,
        "fanout_pipe_geometry_count": 0,
        "hydraulic_acceptance": "NOT_EVALUATED_DESIGN_HEAT_LOSS_PRIMARY_PIPE_AND_PUMP_MISSING",
        "result": "PASS_DESIGN_BASIS_K2_AND_ON_WALL_CABINET_FIT_REWORK_PORT_GEOMETRY_PROCUREMENT_FIXINGS_AND_HYDRAULICS",
    }
    model["product_selection_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_k2_product_selection.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    canvas = Image.new("RGB", (1700, 1120), "#F4F8F8")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, canvas.width, 205), fill="#071A21")
    draw.text((34, 18), "D091 · K2 И НАКЛАДНОЙ ШКАФ ВЫБРАНЫ КАК БАЗА ПРОЕКТА", font=font(23, True), fill="white")
    draw.text((34, 63), "Uponor Vario S FM 12 · 1140843 + шкаф OW 1050×730×135 · 1136219", font=font(17, True), fill="#A7EEE7")
    draw.text((34, 105), "12 контуров · G3/4 Eurocone · G1 · шаг 50 мм · рейки 215 мм", font=font(17), fill="#F3D58C")
    draw.text((34, 145), "Накладной шкаф: газобетонную перегородку не вырезаем под весь корпус", font=font(16, True), fill="white")
    draw.text((34, 179), "ПОРТЫ/КРЕПЁЖ/ПОКУПКА/ГИДРАВЛИКА ЕЩЁ НЕ УТВЕРЖДЕНЫ", font=font(14, True), fill="#FFB2B2")

    draw.rounded_rectangle((90, 270, 1610, 900), radius=18, fill="#FFFFFF", outline="#9BB3BA", width=3)
    scale = 0.62
    sx0, sy0 = 280, 390
    sw, sh = (SERVICE_BBOX[3] - SERVICE_BBOX[1]) * scale, (SERVICE_BBOX[2] - SERVICE_BBOX[0]) * scale
    draw.rectangle((sx0, sy0, sx0 + sw, sy0 + sh), fill="#D9F4E8", outline="#006A43", width=4)
    cab_y = sy0 + (CABINET_BBOX_PLAN_MM[1] - SERVICE_BBOX[1]) * scale
    cab_x = sx0 + (CABINET_BBOX_PLAN_MM[0] - SERVICE_BBOX[0]) * scale
    cab_w = CABINET_LENGTH_MM * scale
    cab_d = CABINET_DEPTH_MM * scale
    draw.rectangle((cab_y, cab_x, cab_y + cab_w, cab_x + cab_d), fill="#DCE6FA", outline="#244C90", width=4)
    draw.text((sx0, sy0 - 45), "ПЛАН: ЗОНА 1300×300", font=font(15, True), fill="#006A43")
    draw.text((cab_y + 20, cab_x + 20), "OW 1050×135", font=font(13, True), fill="#244C90")

    draw.text((220, 760), f"Поля шкафа: по длине {cabinet_length_margin / 2:.0f}+{cabinet_length_margin / 2:.0f} мм · по глубине {cabinet_depth_margin:.0f} мм", font=font(15, True), fill="#143842")
    draw.text((220, 802), f"Коллектор 714 мм внутри l1=989 мм: запас {product_length_margin:.0f} мм", font=font(15, True), fill="#143842")
    draw.text((220, 844), f"От оси C01 до передней грани шкафа: {c01_axis_to_cabinet:.1f} мм > 2×R80", font=font(15, True), fill="#006A43")
    draw.text((110, 970), "Выбор — проектная база. Перед покупкой проверить локальную доступность артикула и комплектность.", font=font(15, True), fill="#B00020")
    canvas.save(OUTPUT / "attic_k2_product_selection_evidence.png")

    (OUTPUT / "report.md").write_text(
        "# D091 — проектный выбор K2 и шкафа\n\n"
        "В качестве базы проекта выбран Uponor Vario S manifold FM на 12 контуров, артикул 1140843: нержавеющая сталь, расходомеры, подключения петель G3/4 Eurocone, первичное G1, шаг петель 50 мм и расстояние между рейками 215 мм. Длина по официальному листу 714 мм.\n\n"
        "Для газобетонной перегородки выбран накладной шкаф Uponor Vario OW 1050×730×135, артикул 1136219, чтобы не вырезать нишу под весь короб. Шкаф входит в сервисную зону 300×1300 мм: остаётся по 125 мм по длине и 165 мм по глубине. Внутренняя монтажная длина 989 мм даёт 275 мм запаса относительно коллектора 714 мм.\n\n"
        "D088 остаётся историческим параметрическим доказательством вместимости, но его высотная решётка 225 мм отвергнута для выбранного артикула: официальный размер 1140843 равен 215 мм. Перед выпуском подводок нужны привязка официального чертежа портов, высота шкафа, расчёт крепления к газобетону, подтверждение поставки и гидравлика.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"], "product_selection_digest": model["product_selection_digest"], "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT), "package": str(PACKAGE), "manifold": "1140843", "cabinet": "1136219",
        "cabinet_fit": covers(SERVICE_BBOX, CABINET_BBOX_PLAN_MM), "c01_clearance": c01_axis_to_cabinet,
        "digest": model["product_selection_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

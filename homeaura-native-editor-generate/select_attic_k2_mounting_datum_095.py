from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_092 = BASE / "HA_TWO_FLOOR_ATTIC_K2_PRODUCT_EVIDENCE_092" / "attic_k2_product_selection_corrected.json"
SOURCE_093 = BASE / "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORTS_093" / "attic_k2_selected_ports.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_K2_MOUNTING_DATUM_095"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_K2_MOUNTING_DATUM_095.zip"

CABINET_HEIGHT_MM = 730.0
CABINET_TOP_AFF_MM = 1000.0
CABINET_BOTTOM_AFF_MM = CABINET_TOP_AFF_MM - CABINET_HEIGHT_MM
HEIGHT_ADJUSTMENT_MM = 10.0
PIPE_OD_MM = 16.0
RADIUS_MM = 80.0
CABINET_DEPTH_MM = 135.0
RETURN_AXIS_TO_FRONT_MM = 85.0
SUPPLY_AXIS_TO_FRONT_MM = 105.0


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D095 is append-only")
    raw_092, selection = read(SOURCE_092)
    raw_093, ports = read(SOURCE_093)
    outer_radius = RADIUS_MM + PIPE_OD_MM / 2
    model = {
        "schema": "homeaura-attic-k2-mounting-datum-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_K2_MOUNTING_DATUM_095",
        "status": "K2_CABINET_PROJECT_MOUNTING_DATUM_SELECTED_PASS_REWORK_SITE_FFL_CONFIRMATION_PORT_Z_AND_3D_FANOUT",
        "source_records": [
            {"artifact_id": selection["artifact_id"], "sha256": hashlib.sha256(raw_092).hexdigest().upper()},
            {"artifact_id": ports["artifact_id"], "sha256": hashlib.sha256(raw_093).hexdigest().upper()},
        ],
        "selected_cabinet_part_number": "1136219",
        "selected_manifold_part_number": "1140843",
        "official_installation_manual": {
            "url": "https://brandportal.uponor.com/asset/2d4fd542-cefc-4f60-9278-1cb5a364a9af/IM-Vario-cabinet-OW-INT-1094994-v4.pdf",
            "document_number": "1094994",
            "revision": "v4_12_2025_INT",
            "accessed_date": "2026-08-13",
            "figure_nominal_top_height_from_floor_mm": CABINET_TOP_AFF_MM,
            "cabinet_height_mm": CABINET_HEIGHT_MM,
            "height_adjustment_plus_minus_mm": HEIGHT_ADJUSTMENT_MM,
            "wall_fastener_hole_diameter_mm": 10,
            "manual_mandates_final_project_height": False,
        },
        "project_mounting_datum": {
            "reference": "ATTIC_FINISHED_FLOOR_LEVEL_PROVISIONAL_DATUM",
            "cabinet_top_aff_mm": CABINET_TOP_AFF_MM,
            "cabinet_bottom_aff_mm": CABINET_BOTTOM_AFF_MM,
            "permitted_installation_adjustment_mm": [-HEIGHT_ADJUSTMENT_MM, HEIGHT_ADJUSTMENT_MM],
            "selected_by": "PROJECT_DESIGN_FROM_MANUFACTURER_TEMPLATE_FIGURE",
            "site_finished_floor_level_verified": False,
            "site_marking_required_before_drilling": True,
        },
        "cabinet_envelope_building_xyz_mm": {
            "x": [9235.0, 9370.0],
            "y": [6625.0, 7675.0],
            "z": [CABINET_BOTTOM_AFF_MM, CABINET_TOP_AFF_MM],
        },
        "bend_envelope_screen": {
            "loop_pipe_outer_diameter_mm": PIPE_OD_MM,
            "design_centerline_radius_mm": RADIUS_MM,
            "outer_pipe_envelope_radius_mm": outer_radius,
            "supply_axis_to_cabinet_front_mm": SUPPLY_AXIS_TO_FRONT_MM,
            "return_axis_to_cabinet_front_mm": RETURN_AXIS_TO_FRONT_MM,
            "supply_frontward_turn_envelope_margin_mm": SUPPLY_AXIS_TO_FRONT_MM - outer_radius,
            "return_frontward_turn_envelope_margin_mm": RETURN_AXIS_TO_FRONT_MM - outer_radius,
            "all_frontward_turns_fit_inside_closed_cabinet_depth": RETURN_AXIS_TO_FRONT_MM >= outer_radius,
            "required_fanout_direction": "DOWNWARD_THROUGH_CABINET_BOTTOM_THEN_LONGITUDINAL_OR_ROOMWARD_ONLY_AFTER_CLEARING_CABINET",
            "cabinet_bottom_aff_minus_two_R80_mm": CABINET_BOTTOM_AFF_MM - 2 * RADIUS_MM,
            "vertical_envelope_screen_pass": CABINET_BOTTOM_AFF_MM >= 2 * RADIUS_MM,
            "scope": "ENVELOPE_SCREEN_NOT_FINAL_BEND_CENTERLINES",
        },
        "absolute_manifold_header_z_mm": None,
        "absolute_loop_port_z_mm": None,
        "reason_port_z_unresolved": "CABINET_INTERNAL_RAIL_AND_MANIFOLD_FIXING_POSITION_MUST_BE_SET_FROM_INSTALLATION_TEMPLATE_OR_BIM_DURING_DETAILING",
        "published_3d_fanout_pipe_count": 0,
        "complete_route_count": 0,
        "wall_drilling_authorized": False,
        "procurement_authorized": False,
        "result": "PASS_PROJECT_CABINET_ENVELOPE_DATUM_REWORK_SITE_FFL_INTERNAL_RAIL_Z_AND_FULL_R80_FANOUT",
    }
    model["mounting_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_k2_mounting_datum.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    canvas = Image.new("RGB", (1700, 1150), "#F4F8F8")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, 1700, 205), fill="#071A21")
    draw.text((34, 18), "D095 · МОНТАЖНАЯ ОТМЕТКА K2 В ГАРДЕРОБНОЙ", font=font(23, True), fill="white")
    draw.text((34, 63), "Шкаф 1136219 · верх 1000 мм · низ 270 мм от чистого пола · регулировка ±10 мм", font=font(16, True), fill="#A7EEE7")
    draw.text((34, 105), "Проектная отметка по заводскому шаблону; чистый пол проверить на объекте", font=font(17), fill="#F3D58C")
    draw.text((34, 145), "R80 + радиус трубы = 88 мм: поворот обратки к фасаду внутри шкафа НЕ помещается", font=font(16, True), fill="white")
    draw.text((34, 179), "ВЫХОДЫ ВЕСТИ ВНИЗ ЧЕРЕЗ НИЗ ШКАФА; точные Z портов и 24 линии ещё не опубликованы", font=font(14, True), fill="#FFB2B2")

    floor_y = 1000
    wall_x = 1240
    front_x = 900
    top_y = 310
    bottom_y = 820
    draw.line((180, floor_y, 1530, floor_y), fill="#566B73", width=5)
    draw.text((185, floor_y+18), "ЧИСТЫЙ ПОЛ - ПРОВЕРИТЬ НА ОБЪЕКТЕ", font=font(14, True), fill="#566B73")
    draw.rectangle((front_x, top_y, wall_x, bottom_y), fill="#FFFFFF", outline="#006A43", width=5)
    draw.line((wall_x, 260, wall_x, floor_y), fill="#6C7A80", width=8)
    draw.text((995, top_y-45), "ШКАФ K2", font=font(18, True), fill="#006A43")
    draw.text((945, 520), "1050 × 730 × 135", font=font(17, True), fill="#143842")
    draw.text((945, 560), "настенный", font=font(15), fill="#566B73")
    draw.line((830, top_y, 830, floor_y), fill="#247BA0", width=3)
    draw.line((815, top_y, 845, top_y), fill="#247BA0", width=3)
    draw.line((815, floor_y, 845, floor_y), fill="#247BA0", width=3)
    draw.text((675, 620), "1000 мм", font=font(17, True), fill="#247BA0")
    draw.line((865, bottom_y, 865, floor_y), fill="#B87900", width=3)
    draw.line((850, bottom_y, 880, bottom_y), fill="#B87900", width=3)
    draw.line((850, floor_y, 880, floor_y), fill="#B87900", width=3)
    draw.text((715, 900), "270 мм", font=font(17, True), fill="#B87900")
    draw.line((1100, bottom_y-90, 1100, 945), fill="#006A43", width=10)
    draw.polygon([(1080,945),(1120,945),(1100,980)], fill="#006A43")
    draw.text((920, 870), "24 отвода вниз", font=font(16, True), fill="#006A43")
    draw.rounded_rectangle((120, 300, 600, 790), radius=18, fill="#FFFFFF", outline="#9BB3BA", width=3)
    draw.text((155, 345), "ПРОВЕРКА R80", font=font(18, True), fill="#143842")
    rows = [
        "Радиус оси: 80 мм",
        "Наружный радиус: 88 мм",
        "Подача до фасада: 105 мм  PASS",
        "Обратка до фасада: 85 мм  FAIL -3",
        "Низ шкафа: 270 мм",
        "2×R80: 160 мм  PASS +110",
    ]
    for index, value in enumerate(rows):
        colour = "#B00020" if "FAIL" in value else "#143842"
        draw.text((155, 405+index*56), value, font=font(15, index in (2,3,5)), fill=colour)
    draw.text((125, 1070), "Принято: шкаф на общей внутренней стене лестницы и гардеробной; наружная стена не используется.", font=font(15, True), fill="#006A43")
    canvas.save(OUTPUT / "attic_k2_mounting_datum_evidence.png")
    (OUTPUT / "report.md").write_text(
        "# D095 — монтажная отметка K2\n\n"
        "Для настенного шкафа Uponor 1136219 принята проектная отметка верхней кромки 1000 мм от чистого пола, как показано на заводском монтажном шаблоне. При высоте 730 мм нижняя кромка находится на 270 мм; заводская регулировка составляет ±10 мм. Перед сверлением отметку нужно перенести от фактического чистого пола.\n\n"
        "Проверка R80 показывает важное ограничение: центр обратного отвода находится в 85 мм от фасада, а внешнему контуру трубы Ø16 при радиусе оси 80 мм требуется 88 мм. Поэтому поворачивать обратки к фасаду внутри закрытой глубины шкафа нельзя. Все 24 петлевых отвода следует вывести вниз через низ шкафа и разводить после выхода. Точные высоты портов и пространственные оси пока не опубликованы.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"], "mounting_digest": model["mounting_digest"], "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "top_aff_mm": CABINET_TOP_AFF_MM, "bottom_aff_mm": CABINET_BOTTOM_AFF_MM, "return_front_margin_mm": RETURN_AXIS_TO_FRONT_MM - outer_radius, "digest": model["mounting_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

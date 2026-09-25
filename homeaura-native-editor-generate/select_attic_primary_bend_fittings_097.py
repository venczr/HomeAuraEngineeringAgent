from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_PRIMARY_PIPE_SELECTION_096" / "attic_primary_pipe_selection.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_PRIMARY_BEND_FITTINGS_097"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_PRIMARY_BEND_FITTINGS_097.zip"


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D097 is append-only")
    source_raw = SOURCE.read_bytes()
    source = json.loads(source_raw.decode("utf-8"))
    model = {
        "schema": "homeaura-attic-primary-bend-fitting-selection-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_PRIMARY_BEND_FITTINGS_097",
        "status": "PRIMARY_32MM_PRESS_ELBOW_DESIGN_BASIS_PASS_REWORK_EXACT_PRIMARY_ROUTE_AND_INSTALLER_CONNECTION_DETAIL",
        "source_artifact_id": source["artifact_id"],
        "source_sha256": hashlib.sha256(source_raw).hexdigest().upper(),
        "architecture": "K1_BOILER_ROOM_TO_K2_ATTIC_WARDROBE_TWO_PRIMARY_MAINS",
        "selected_primary_pipe_part_number": source["selected_design_basis_primary_pipe"]["part_number"],
        "selected_direction_change_fitting": {
            "manufacturer": "Uponor",
            "family": "S-Press PLUS elbow",
            "part_number": "1070526",
            "nominal_size": "32-32",
            "official_item_length_mm": [70.8, 70.8],
            "official_leg_length_l_mm": [51.0, 51.0],
            "official_z_mm": [23.0, 23.0],
            "official_product_url": "https://www.uponor.com/en-en/s/uponor-s-press-plus-elbow-32-32-1070526",
            "accessed_date": "2026-08-13",
            "selection_status": "DESIGN_BASIS_NOT_PURCHASE_AUTHORITY",
        },
        "design_quantity_screen": {
            "lower_floor_to_vertical_turns": 2,
            "upper_vertical_to_K2_service_turns": 2,
            "total_32x32_elbows": 4,
            "quantity_is_route_architecture_allowance_not_bill_of_materials": True,
        },
        "bend_policy": {
            "loop_pipe_od_mm": 16,
            "owner_loop_centerline_radius_mm": 80,
            "owner_R80_scope": "LOOP_PIPE_16MM_ONLY",
            "primary_pipe_od_mm": 32,
            "primary_direction_changes_use_selected_press_elbow": True,
            "primary_hot_air_or_open_flame_bending_prohibited": True,
            "primary_field_bend_radius_credited": False,
            "manufacturer_manual_reference": "IM_UNI_PIPE_AND_S_PRESS_SYSTEM_14_110",
        },
        "connection_scope": {
            "K2_adapter_candidate_part_number": "1070509",
            "K2_adapter_quantity_screen": 2,
            "K1_connection_fitting_selected": False,
            "thread_seal_and_union_detail_installer_confirmation_required": True,
            "fitting_equivalent_hydraulic_length_included": False,
        },
        "complete_primary_route_geometry_count": 0,
        "approved_installed_fitting_count": 0,
        "procurement_authorized": False,
        "result": "PASS_PRIMARY_BEND_METHOD_AND_FITTING_DESIGN_BASIS_REWORK_ROUTE_COORDINATES_K1_CONNECTION_AND_PRESS_TOOL_PLAN",
    }
    model["fitting_selection_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_primary_bend_fittings.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    canvas = Image.new("RGB", (1650, 1100), "#F4F8F8")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, 1650, 210), fill="#071A21")
    draw.text((35, 22), "D097 · ПОВОРОТЫ ДВУХ МАГИСТРАЛЕЙ Ø32", font=font(25, True), fill="white")
    draw.text((35, 70), "Uponor S-Press PLUS 32-32 · арт. 1070526 · плечи 51×51 мм", font=font(18, True), fill="#A7EEE7")
    draw.text((35, 116), "4 угольника: 2 внизу + 2 вверху · расчётная комплектация, не ведомость закупки", font=font(16), fill="#F3D58C")
    draw.text((35, 160), "R80 применяется к петлям Ø16; магистраль Ø32 не греем и не гнём по R80", font=font(16, True), fill="#FFB2B2")

    for x, title, subtitle, colour in (
        (95, "ПОДАЧА Ø32", "K1 → пол → стояк → K2", "#D84315"),
        (875, "ОБРАТКА Ø32", "K2 → стояк → пол → K1", "#1565C0"),
    ):
        draw.rounded_rectangle((x, 290, x + 680, 825), radius=24, fill="white", outline="#9BB3BA", width=3)
        draw.text((x + 35, 325), title, font=font(21, True), fill=colour)
        draw.text((x + 35, 370), subtitle, font=font(15), fill="#566B73")
        draw.line((x + 105, 720, x + 345, 720), fill=colour, width=22)
        draw.arc((x + 310, 480, x + 550, 720), 0, 90, fill=colour, width=22)
        draw.line((x + 550, 600, x + 550, 420), fill=colour, width=22)
        draw.ellipse((x + 316, 681, x + 365, 730), fill="#FFB300", outline="#7A5300", width=3)
        draw.text((x + 90, 755), "пресс-угольник 32-32", font=font(15, True), fill="#143842")
        draw.text((x + 90, 790), "не полевой малый изгиб", font=font(14), fill="#566B73")
    draw.text((90, 910), "Не включено: точные оси магистралей, местные сопротивления, К1-переходы, изоляция и пресс-инструмент.", font=font(16), fill="#143842")
    draw.text((90, 965), "СТАТУС: МЕТОД ПОВОРОТА И ФИТИНГ ВЫБРАНЫ · МОНТАЖНАЯ ТРАССА ЕЩЁ НЕ ОПУБЛИКОВАНА", font=font(16, True), fill="#B00020")
    canvas.save(OUTPUT / "attic_primary_bend_fittings_evidence.png")

    (OUTPUT / "report.md").write_text(
        "# D097 — повороты двух магистралей Ø32\n\n"
        "Для переходов горизонталь–стояк у подачи и обратки выбран проектный фитинг Uponor S-Press PLUS 32-32, арт. 1070526. Официальные размеры: плечи l1=l2=51 мм, z1=z2=23 мм. Расчётно предусмотрены четыре угольника — по два на каждую магистраль.\n\n"
        "Радиус R80 относится только к петлевой трубе Ø16. Магистраль 32×3 мм не греется и не сгибается по этому радиусу. Точная трасса, эквивалентные гидравлические длины, соединение у K1 и ведомость закупки пока не утверждены.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "fitting_selection_digest": model["fitting_selection_digest"],
        "append_only": True,
        "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "digest": model["fitting_selection_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

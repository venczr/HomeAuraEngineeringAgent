from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_STACK_OPTIONS_116"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_STACK_OPTIONS_116.zip"
SOURCES = [
    BASE / "HA_TWO_FLOOR_FLOOR_LAYER_STACK_103" / "floor_layer_stack.json",
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_RESEARCH_113" / "floor_primary_research.json",
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_CHANNEL_REVISION_114" / "floor_primary_channel_revision.json",
]


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def main() -> None:
    if PACKAGE.exists() or (OUTPUT.exists() and (OUTPUT / "artifact_manifest.json").exists()):
        raise FileExistsError("D116 is append-only")
    if OUTPUT.exists():
        partial_files = sorted(p.name for p in OUTPUT.iterdir() if p.is_file())
        if partial_files != ["floor_stack_options.json"]:
            raise FileExistsError("D116 contains an unrecognized partial build")
    source_records = []
    models = {}
    for path in SOURCES:
        model = json.loads(path.read_text(encoding="utf8"))
        models[model["artifact_id"]] = model
        source_records.append({"artifact_id": model["artifact_id"], "file": path.name, "sha256": sha(path)})

    model = {
        "schema": "homeaura-floor-stack-options-reconciliation-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_STACK_OPTIONS_116",
        "status": "TWO_70MM_FLOOR_STACK_OPTIONS_PASS_REWORK_EXACT_SCREED_FINISH_LOAD_AND_WET_ROOM_SCHEDULE",
        "source_records": source_records,
        "supersession": {
            "D103_geometry_70mm_available_and_16mm_pipe_preserved": True,
            "D103_combined_WET_FLOW_OR_CALCIUM_SULPHATE_35MM_wording": "SUPERSEDED__35MM_IS_CALCIUM_SULPHATE_BRANCH_ONLY",
            "D109_and_D112_single_51_PLUS_19_stack": "HISTORICAL_DESIGN_BRANCH_NOT_UNIVERSAL_DEFAULT",
        },
        "owner_height_contract": {
            "available_above_installed_insulation_mm": 70,
            "loop_pipe_outer_diameter_mm": 16,
            "loop_pipe_top_above_insulation_mm": 16,
        },
        "official_source": {
            "document": "UPONOR_UNDERFLOOR_HEATING_COOLING_PLANNING_INFORMATION_1186660_V1",
            "url": "https://brandportal.uponor.com/m/7187327a41365ace/original/TI-planning-principles-UFHC-EN-1186660-v1.pdf",
            "pages": [16, 17, 18],
            "design_surface_load_limit_kN_m2": 2,
            "individual_load_limit_kN": 1,
            "construction_specific_manufacturer_confirmation_required": True,
        },
        "floor_stack_options": [
            {
                "option_id": "A_CAF_CALCIUM_SULPHATE_FLOW_SCREEED",
                "screed_family": "ANHYDRITE_CALCIUM_SULPHATE_FLOW_SCREEED",
                "cover_above_pipe_mm": 35,
                "screed_total_from_insulation_top_mm": 51,
                "finish_adhesive_underlay_allowance_mm": 19,
                "height_reconciliation_mm": 70,
                "fits": True,
                "wet_room_use": "NOT_ACCEPTED_WITHOUT_EXACT_PRODUCT_WATERPROOFING_AND_ROOM_DETAIL",
                "manufacturer_written_confirmation_required": True,
                "selected": False,
            },
            {
                "option_id": "B_CT_OR_CEMENT_BASED_FLOW_SCREEED",
                "screed_family": "CEMENT_OR_CEMENT_BASED_FLOW_SCREEED",
                "cover_above_pipe_mm": 45,
                "screed_total_from_insulation_top_mm": 61,
                "finish_adhesive_underlay_allowance_mm": 9,
                "height_reconciliation_mm": 70,
                "fits": True,
                "finish_risk": "NINE_MM_MAY_NOT_FIT_TILE_PLUS_ADHESIVE_OR_OTHER_SELECTED_FINISH",
                "manufacturer_written_confirmation_required": True,
                "selected": False,
            },
        ],
        "common_requirements": {
            "screed_is_load_absorbing_and_load_distributing_layer": True,
            "heating_pipe_pressurised_during_screed_installation": True,
            "joint_plan_required": True,
            "functional_heating_protocol_required": True,
            "ready_for_covering_moisture_protocol_required": True,
            "separating_cover_layer_continuity_required": True,
            "floor_finish_thermal_resistance_limit_m2K_W": 0.15,
            "exact_finish_schedule_selected": False,
            "exact_screed_product_selected": False,
            "design_load_confirmed": False,
        },
        "channel_interface": {
            "engineered_bridge_must_finish_flush_with_existing_insulation_top": True,
            "bridge_must_not_reduce_selected_screed_or_finish_height": True,
            "bridge_must_support_selected_screed_system_over_200mm_service_channel": True,
            "bridge_design_must_address_deflection_crack_control_corrosion_moisture_acoustics_and_thermal_bridge": True,
            "generic_timber_bearer_detail_from_board_overlay_may_be_copied_under_wet_screed": False,
            "bridge_selected": False,
        },
        "selected_option_id": None,
        "construction_authorized": False,
        "result": "PASS_TWO_TRUTHFUL_HEIGHT_BRANCHES_REWORK_PRODUCT_FINISH_AND_LOAD_SELECTION",
    }
    model["options_digest"] = digest(model)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "floor_stack_options.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf8")

    im = Image.new("RGB", (1700, 1100), "#F4F8F8")
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, 0, 1700, 185), fill="#071A21")
    d.text((38, 20), "D116 · ДВА ЧЕСТНЫХ ПИРОГА В 70 ММ", font=font(28, True), fill="white")
    d.text((38, 72), "35 мм - только ветвь кальций-сульфатной стяжки; цементная ветвь - 45 мм", font=font(19, True), fill="#A7EEE7")
    d.text((38, 120), "Ни одна ветвь не выбрана до точной смеси, нагрузки, помещения и чистового покрытия", font=font(17, True), fill="#FFB2B2")

    branches = [
        (75, "A · CAF / АНГИДРИТ", 35, 51, 19, "#5FA9DD", "19 мм на финиш", "Для мокрых зон - отдельное подтверждение"),
        (875, "B · ЦЕМЕНТНАЯ", 45, 61, 9, "#CF8A52", "9 мм на финиш", "Риск: плитка + клей могут не поместиться"),
    ]
    for x, title, cover, screed, finish, color, finish_text, warning in branches:
        d.rounded_rectangle((x, 235, x + 720, 995), radius=24, fill="white", outline="#A7B9BF", width=3)
        d.text((x + 35, 270), title, font=font(24, True), fill="#143842")
        bottom, top = 900, 390
        scale = (bottom - top) / 70
        pipe_top_y = bottom - int(16 * scale)
        screed_top_y = bottom - int(screed * scale)
        # 100 mm insulation is context only, not part of the 70 mm stack.
        d.rectangle((x + 90, pipe_top_y, x + 360, bottom), fill="#D34A42", outline="#7C0000", width=2)
        d.rectangle((x + 90, screed_top_y, x + 360, pipe_top_y), fill=color, outline="#38566B", width=2)
        d.rectangle((x + 90, top, x + 360, screed_top_y), fill="#E8DFD2", outline="#8B7355", width=2)
        d.line((x + 70, bottom, x + 390, bottom), fill="#567A28", width=4)
        d.text((x + 400, 855), "Ø16", font=font(18, True), fill="#B00020")
        d.text((x + 400, 785), f"покрытие: {cover} мм", font=font(18, True), fill="#143842")
        d.text((x + 400, 715), f"всего стяжки: {screed} мм", font=font(18, True), fill="#143842")
        d.text((x + 400, 645), finish_text, font=font(18, True), fill="#006A43" if finish >= 19 else "#B00020")
        d.text((x + 90, 345), "верх существующего утеплителя", font=font(14, True), fill="#567A28")
        d.rounded_rectangle((x + 55, 925, x + 665, 975), radius=10, fill="#FFF0F0")
        d.text((x + 75, 940), warning, font=font(14, True), fill="#B00020")
    im.save(OUTPUT / "floor_stack_options_evidence.png")

    (OUTPUT / "selection_checklist.md").write_text(
        "# D116 — что нужно выбрать\n\n"
        "В доступные 70 мм помещаются две разные ветви. Кальций-сульфатная текучая стяжка: 16 + 35 = 51 мм, остаётся 19 мм. Цементная или цементная текучая: 16 + 45 = 61 мм, остаётся только 9 мм.\n\n"
        "До выбора нужны: точная смесь и технический лист; расчётная нагрузка; список мокрых помещений; покрытие каждого помещения с клеем/подложкой; схема швов; режим функционального прогрева и допустимая остаточная влажность.\n\n"
        "Несущий мост над скрытыми магистралями обязан заканчиваться в уровне верха существующего утеплителя. Он не может забирать высоту у выбранной стяжки или финиша.\n",
        encoding="utf8",
    )
    files = [p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps({"artifact_id": model["artifact_id"], "options_digest": model["options_digest"], "append_only": True,
                    "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]}, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "digest": model["options_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

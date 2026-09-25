from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_LOAD_BRIDGE_GATE_117"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_LOAD_BRIDGE_GATE_117.zip"
SOURCES = [
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_CHANNEL_REVISION_114" / "floor_primary_channel_revision.json",
    BASE / "HA_TWO_FLOOR_FLOOR_STACK_OPTIONS_116" / "floor_stack_options.json",
    BASE / "HA_TWO_FLOOR_PRIMARY_CHANNEL_NO_FASTENER_107" / "primary_channel_no_fastener.json",
]


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D117 is append-only")
    source_records = []
    for path in SOURCES:
        source = json.loads(path.read_text(encoding="utf8"))
        source_records.append({
            "artifact_id": source["artifact_id"],
            "file": path.name,
            "sha256": sha(path),
        })

    actual_od = 62
    actual_radius = actual_od / 2
    nominal_axis_z = 35
    insulation_top_z = 100
    actual_pipe_top_z = nominal_axis_z + actual_radius
    actual_pipe_bottom_z = nominal_axis_z - actual_radius
    nominal_thermal_headroom = insulation_top_z - actual_pipe_top_z
    maximum_axis_for_30mm_infill = insulation_top_z - 30 - actual_radius
    maximum_support_build_under_pipe_for_30mm_infill = maximum_axis_for_30mm_infill - actual_radius

    model = {
        "schema": "homeaura-floor-primary-load-bridge-stage-gate-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_LOAD_BRIDGE_GATE_117",
        "status": "DIMENSIONAL_LOAD_BRIDGE_GATE_PASS_REWORK_PRODUCT_STRUCTURE_AND_THERMAL_DETAIL",
        "source_records": source_records,
        "supersession": {
            "D114_load_bridge_concept_preserved": True,
            "D114_nominal_30mm_thermal_infill_plus_unspecified_bridge": "SUPERSEDED__THEY_SHARE_THE_SAME_30_TO_34MM_VERTICAL_BUDGET",
            "D107_200mm_no_fastener_corridor": "MINIMUM_PIPE_CHANNEL_ONLY__FINAL_PROTECTED_FOOTPRINT_MUST_INCLUDE_EXTERNAL_BEARINGS",
        },
        "fixed_geometry": {
            "installed_floor1_insulation_depth_mm": 100,
            "primary_clear_pipe_channel_width_mm": 200,
            "primary_channel_axis_length_mm": 4570,
            "two_independent_primary_pipes": True,
            "factory_insulated_pipe_actual_comparison_od_mm": actual_od,
            "factory_insulated_pipe_actual_radius_mm": actual_radius,
            "provisional_coordination_envelope_od_mm": 70,
            "nominal_pipe_axis_z_from_slab_mm": nominal_axis_z,
            "actual_pipe_bottom_z_mm": actual_pipe_bottom_z,
            "actual_pipe_top_z_mm": actual_pipe_top_z,
            "insulation_top_z_from_slab_mm": insulation_top_z,
        },
        "vertical_budget": {
            "actual_clearance_under_pipe_at_nominal_axis_mm": actual_pipe_bottom_z,
            "actual_headroom_pipe_top_to_insulation_top_mm": nominal_thermal_headroom,
            "provisional_envelope_headroom_to_insulation_top_mm": 30,
            "thermal_infill_target_mm": 30,
            "maximum_axis_z_retaining_30mm_actual_infill_mm": maximum_axis_for_30mm_infill,
            "maximum_support_build_under_actual_pipe_retaining_30mm_infill_mm": maximum_support_build_under_pipe_for_30mm_infill,
            "maximum_bridge_thickness_if_axis35_and_30mm_actual_infill_are_both_preserved_mm": nominal_thermal_headroom - 30,
            "maximum_bridge_thickness_if_70mm_envelope_and_30mm_infill_are_both_preserved_mm": 0,
            "thirty_mm_infill_and_nonzero_bridge_both_fit_above_70mm_envelope": False,
            "bridge_thickness_selected_mm": None,
            "support_height_selected_mm": None,
            "thermal_infill_after_bridge_selected_mm": None,
            "result": "PASS_DIMENSIONAL_CONFLICT_IDENTIFIED_REWORK_SUPPORT_BRIDGE_AND_THERMAL_RECALCULATION",
        },
        "load_path_contract": {
            "concept": "CONTINUOUS_SERVICE_DUCT_CLOSURE_SPANNING_200MM_CLEAR_CHANNEL_WITH_LONGITUDINAL_BEARINGS_OUTSIDE_PIPE_CHANNEL",
            "bridge_top_target": "FLUSH_WITH_EXISTING_INSULATION_TOP_Z100_UNLESS_THE_SELECTED_FLOOR_SYSTEM_IS_RECALCULATED",
            "clear_span_mm": 200,
            "overall_bridge_width_mm": None,
            "bearing_width_each_side_mm": None,
            "bearings_must_be_outside_clear_pipe_channel": True,
            "bearings_may_contact_or_load_factory_insulated_pipe": False,
            "screed_or_finish_may_span_unsupported_200mm_channel": False,
            "thermal_infill_is_load_bearing": False,
            "pipe_support_base": "STRUCTURAL_CONCRETE_SLAB",
            "pipe_support_may_attach_to_insulation": False,
            "bridge_support_may_attach_only_to_insulation": False,
            "direction_change_and_riser_box_detail_included": False,
        },
        "candidate_system_families": [
            {
                "rank": 1,
                "system": "PROPRIETARY_LOAD_RATED_SERVICE_DUCT_OR_COVER_COMPATIBLE_WITH_SELECTED_HEATED_WET_SCREED",
                "status": "PREFERRED_NOT_SELECTED",
            },
            {
                "rank": 2,
                "system": "ENGINEER_DESIGNED_CONTINUOUS_CORROSION_PROTECTED_METAL_DECK_AND_SIDE_RAILS_FIXED_TO_SLAB_OUTSIDE_CHANNEL",
                "status": "CALCULATION_REQUIRED_NOT_SELECTED",
            },
            {
                "rank": 3,
                "system": "WHOLE_FLOOR_DRY_SCREEED_SYSTEM_WITH_MANUFACTURER_SERVICE_DUCT_DETAIL",
                "status": "SYSTEM_CHANGE_ONLY_NOT_LOCAL_PATCH",
            },
        ],
        "rejected_unengineered_details": [
            "LOOSE_30MM_INSULATION_AS_LOAD_BRIDGE",
            "UNSUPPORTED_WET_SCREEED_OVER_200MM_VOID",
            "GENERIC_TIMBER_BEARERS_COPIED_FROM_BOARD_OVERLAY_DETAIL_INTO_WET_SCREEED",
            "FOAM_FILL_AS_STRUCTURAL_SUPPORT",
            "BEARER_OR_CLIP_CRUSHING_THE_FACTORY_PIPE_INSULATION",
            "BRIDGE_PLACED_ABOVE_Z100_WITHOUT_RECONCILING_THE_70MM_UPPER_FLOOR_STACK",
        ],
        "screening_load_basis_not_design_acceptance": {
            "distributed_surface_load_kN_m2": 2,
            "individual_load_kN": 1,
            "source": "UPONOR_PLANNING_INFORMATION_1186660_V1_PAGES_16_TO_18",
            "actual_project_load_confirmed": False,
        },
        "required_engineering_checks": [
            "SELECT_EXACT_SCREEED_BRANCH_A_OR_B_AND_EXACT_PRODUCT",
            "SELECT_FINISH_BUILDUP_PER_ROOM_INCLUDING_ADHESIVE_OR_UNDERLAY",
            "CONFIRM_ACTUAL_DISTRIBUTED_AND_POINT_LOADS",
            "SELECT_PIPE_SUPPORT_WITH_MEASURED_BUILD_HEIGHT_AND_INSULATION_COMPATIBILITY",
            "CALCULATE_DECK_STRESS_LOCAL_POINT_LOAD_DEFLECTION_AND_EDGE_BEARING",
            "CHECK_DIFFERENTIAL_STIFFNESS_AND_SCREEED_CRACK_CONTROL",
            "CHECK_CORROSION_MOISTURE_ACOUSTICS_FIRE_AND_THERMAL_BRIDGE",
            "DETAIL_DIRECTION_CHANGE_ACCESS_BOX_AND_NO_HIDDEN_FITTINGS",
            "EXPAND_NO_FASTENER_ZONE_TO_FINAL_BRIDGE_AND_BEARING_FOOTPRINT",
            "ISSUE_MANUFACTURER_OR_ENGINEER_SIGNED_DETAIL",
        ],
        "site_release_inputs": {
            "existing_insulation_product_and_compressive_grade": None,
            "slab_flatness_and_local_level_survey": None,
            "factory_insulated_pipe_exact_product_and_jacket": None,
            "pipe_support_product_and_build_height": None,
            "bridge_or_duct_product_and_section": None,
            "screed_product_and_branch": None,
            "finish_schedule": None,
            "wet_room_schedule": None,
            "actual_load_schedule": None,
        },
        "approved_pipe_geometry_count": 0,
        "approved_load_bridge_detail_count": 0,
        "construction_authorized": False,
        "result": "PASS_VERTICAL_AND_LOAD_PATH_CONSTRAINTS_REWORK_SELECTED_ENGINEERED_DETAIL",
    }
    model["load_bridge_gate_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "load_bridge_stage_gate.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf8"
    )

    im = Image.new("RGB", (1800, 1200), "#F3F7F7")
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, 0, 1800, 190), fill="#071B23")
    d.text((42, 20), "D117 · НЕСУЩЕЕ ЗАКРЫТИЕ КАНАЛА 200 ММ", font=font(29, True), fill="white")
    d.text((42, 74), "Геометрический конфликт найден: теплоизоляция и мост делят одни 30–34 мм", font=font(20, True), fill="#A8EEE7")
    d.text((42, 127), "Это задание на подбор и расчёт, а не разрешение на монтаж", font=font(18, True), fill="#FFB4B4")

    # Schematic section, not a selected material detail.
    x0, x1 = 160, 1020
    slab_y, insulation_top_y = 940, 420
    d.rectangle((x0, slab_y, x1, slab_y + 85), fill="#AEB7BD", outline="#55636A", width=3)
    d.text((x0 + 18, slab_y + 25), "Ж/Б ПЛИТА · основание опор", font=font(18, True), fill="#1E3038")
    d.rectangle((x0, insulation_top_y, 360, slab_y), fill="#D8E8A8", outline="#6A8230", width=3)
    d.rectangle((820, insulation_top_y, x1, slab_y), fill="#D8E8A8", outline="#6A8230", width=3)
    d.text((x0 + 15, 455), "100 мм", font=font(18, True), fill="#4D661A")

    channel_left, channel_right = 360, 820
    rail_w = 42
    d.rectangle((channel_left - rail_w, insulation_top_y + 30, channel_left, slab_y), fill="#7B858B", outline="#26353D", width=3)
    d.rectangle((channel_right, insulation_top_y + 30, channel_right + rail_w, slab_y), fill="#7B858B", outline="#26353D", width=3)
    d.text((280, 865), "опоры СНАРУЖИ", font=font(14, True), fill="#26353D")
    d.text((805, 865), "канала", font=font(14, True), fill="#26353D")

    # Pipes and provisional 70-mm envelopes.
    centers = [485, 690]
    axis_y = 758
    for idx, cx in enumerate(centers, start=1):
        d.ellipse((cx - 75, axis_y - 75, cx + 75, axis_y + 75), outline="#ED9A32", width=4)
        d.ellipse((cx - 66, axis_y - 66, cx + 66, axis_y + 66), fill="#E8B64E", outline="#A66B00", width=3)
        d.ellipse((cx - 34, axis_y - 34, cx + 34, axis_y + 34), fill="#267EB5", outline="#054B78", width=3)
        d.text((cx - 20, axis_y - 16), f"P{idx}", font=font(15, True), fill="white")
    d.line((channel_left, axis_y, channel_right, axis_y), fill="#C10D27", width=2)
    d.text((372, 792), "Ø62 факт / Ø70 конверт", font=font(16, True), fill="#8B4800")

    # The bridge is deliberately dashed: no product or thickness selected.
    d.line((channel_left - 70, insulation_top_y, channel_right + 70, insulation_top_y), fill="#005F66", width=8)
    for x in range(channel_left - 70, channel_right + 70, 28):
        d.line((x, insulation_top_y - 7, x + 15, insulation_top_y - 7), fill="#00A7A0", width=3)
    d.text((370, 350), "НЕСУЩАЯ КРЫШКА: толщина и опирание НЕ ВЫБРАНЫ", font=font(19, True), fill="#006068")

    # Dimensions and conflict callout.
    d.line((channel_left, 1015, channel_right, 1015), fill="#B00020", width=3)
    d.line((channel_left, 1002, channel_left, 1028), fill="#B00020", width=3)
    d.line((channel_right, 1002, channel_right, 1028), fill="#B00020", width=3)
    d.text((535, 1032), "200 мм чистый канал", font=font(17, True), fill="#B00020")
    d.rounded_rectangle((1080, 245, 1745, 1050), radius=22, fill="white", outline="#9EB0B7", width=3)
    lines = [
        ("ВЕРТИКАЛЬНЫЙ БЮДЖЕТ", True, "#153A43"),
        ("верх утеплителя: z=100 мм", False, "#153A43"),
        ("ось трубы: z=35 мм", False, "#153A43"),
        ("верх фактической Ø62: z=66 мм", False, "#153A43"),
        ("свободно до z=100: 34 мм", True, "#006A43"),
        ("30 мм заполнения + мост => мост ≤4 мм", True, "#B00020"),
        ("для Ø70: 30 мм + мост => мост 0 мм", True, "#B00020"),
        ("", False, "#153A43"),
        ("ОБЯЗАТЕЛЬНО", True, "#153A43"),
        ("· опоры к плите, не к утеплителю", False, "#153A43"),
        ("· опоры вне 200-мм канала", False, "#153A43"),
        ("· расширить запрет крепежа", False, "#153A43"),
        ("· расчёт прогиба и точечной нагрузки", False, "#153A43"),
        ("· проверить трещины, влагу, коррозию", False, "#153A43"),
        ("", False, "#153A43"),
        ("СТРОИТЕЛЬСТВО: НЕ РАЗРЕШЕНО", True, "#B00020"),
    ]
    y = 285
    for text, bold, color in lines:
        if text:
            d.text((1120, y), text, font=font(18 if bold else 16, bold), fill=color)
        y += 43

    im.save(OUTPUT / "load_bridge_stage_gate_evidence.png")
    (OUTPUT / "engineering_brief.md").write_text(
        "# D117 — задание на несущую крышку канала\n\n"
        "Два изолированных трубопровода проходят в чистом канале шириной 200 мм и должны опираться на бетонную плиту. "
        "Над каналом требуется непрерывная несущая крышка с продольными опорами за пределами чистого канала. "
        "Общая ширина крышки будет больше 200 мм; её нельзя назначить до выбора профиля и требуемой ширины опирания.\n\n"
        "При оси 35 мм верх фактической изоляции Ø62 находится на z=66 мм. До верха существующего утеплителя остаётся 34 мм. "
        "Следовательно, при сохранении 30 мм теплоизоляционного заполнения на физическую толщину крышки остаётся максимум 4 мм. "
        "Для расчётного конверта Ø70 остаётся ровно 30 мм и ненулевая крышка уже не помещается. "
        "Это размерное ограничение, а не выбранная 4-мм металлическая деталь.\n\n"
        "До выпуска рабочей детали требуются точные продукты трубы, опор, крышки и стяжки; отделка; нагрузки; расчёт прогиба, "
        "точечной нагрузки, трещиностойкости, коррозии, влаги, акустики, пожара и теплового моста.\n",
        encoding="utf8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    manifest = {
        "artifact_id": model["artifact_id"],
        "load_bridge_gate_digest": model["load_bridge_gate_digest"],
        "append_only": True,
        "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
    }
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8"
    )
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "digest": model["load_bridge_gate_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

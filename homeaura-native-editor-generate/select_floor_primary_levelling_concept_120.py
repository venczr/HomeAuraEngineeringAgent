from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_LEVELLING_CONCEPT_120"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_LEVELLING_CONCEPT_120.zip"
SOURCES = [
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_LOAD_BRIDGE_GATE_117" / "load_bridge_stage_gate.json",
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
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D120 is append-only")
    source_records = []
    for path in SOURCES:
        model = json.loads(path.read_text(encoding="utf8"))
        source_records.append({"artifact_id": model["artifact_id"], "sha256": sha(path)})

    model = {
        "schema": "homeaura-floor-primary-levelling-concept-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_LEVELLING_CONCEPT_120",
        "status": "MANUFACTURER_ALIGNED_LEVELLING_CONCEPT_PASS_REWORK_EXACT_PRODUCTS_SUPPORT_AND_SCREEED",
        "source_records": source_records,
        "official_source": {
            "document": "UPONOR_MLC_TAP_WATER_AND_HEATING_TECHNICAL_INFORMATION_1119966",
            "url": "https://brandportal.uponor.com/m/6867cd7773f41313/original/TI-MLC-tap-water-and-heating-EN-1119966.pdf",
            "pages": [101, 102],
            "accessed_date": "2026-08-13",
            "requirements_used": [
                "PIPES_ON_LOAD_BEARING_SUBSTRATE_MUST_BE_FIXED",
                "LEVEL_SURFACE_FOR_INSULATION_OR_AT_LEAST_IMPACT_SOUND_LAYER_MUST_BE_RESTORED_BY_COMPENSATION",
                "LEVELLING_LAYER_MUST_BE_BOUND_OR_BULK_USEFULNESS_PROVEN",
                "PRESSURE_RESISTANT_INSULATING_MATERIAL_MAY_BE_USED_AS_LEVELLING",
                "RAW_FLOOR_PIPE_ROUTE_SHOULD_BE_STRAIGHT_AXIS_PARALLEL_AND_CROSSING_FREE",
                "PIPE_ROUTE_WIDTH_INCLUDING_INSULATION_MAX_300MM",
                "SUPPORT_WIDTH_NEXT_TO_ROUTE_MIN_200MM",
                "RAW_FLOOR_FIXING_DISTANCE_RECOMMENDED_800MM",
                "FASTENER_WITHIN_300MM_BEFORE_AND_AFTER_EACH_BEND",
                "THERMAL_MOVEMENT_MUST_NOT_BE_IMPEDED",
            ],
        },
        "supersession": {
            "D114_D115_D117_D119_mandatory_load_bridge_wording": "SUPERSEDED__ENGINEERED_BRIDGE_IS_FALLBACK_NOT_MANDATORY_WHEN_COMPLIANT_LEVELLING_LAYER_RESTORES_LOAD_BEARING_SURFACE",
            "D117_vertical_budget_arithmetic_preserved": True,
            "D114_two_independent_pipe_axis_and_200mm_channel_preserved": True,
        },
        "selected_concept_family": "SLAB_FIXED_PREINSULATED_PIPES_PLUS_COMPLIANT_LEVELLING_LAYER_TO_FLUSH_INSULATION_SURFACE",
        "fixed_geometry": {
            "raw_concrete_slab_z_mm": 0,
            "existing_insulation_top_z_mm": 100,
            "route_width_mm": 200,
            "manufacturer_max_route_width_mm": 300,
            "route_width_within_manufacturer_limit": True,
            "required_support_strip_next_to_route_each_applicable_side_mm": 200,
            "support_strip_continuity_on_plan_verified": False,
            "two_factory_insulated_primary_pipes": True,
            "actual_comparison_od_mm": 62,
            "pipe_axis_pitch_mm": 100,
            "clear_gap_between_actual_insulated_pipes_mm": 38,
            "actual_side_margin_each_side_mm": 19,
        },
        "vertical_variants": [
            {
                "variant_id": "DIRECT_LAY_ON_SLAB_IDEAL_GEOMETRY_NOT_PRODUCT_SELECTION",
                "support_build_height_below_pipe_mm": 0,
                "pipe_axis_z_mm": 31,
                "pipe_top_z_mm": 62,
                "available_levelling_depth_above_pipe_to_z100_mm": 38,
                "accepted_for_construction": False,
            },
            {
                "variant_id": "D114_COORDINATION_AXIS",
                "support_build_height_below_pipe_mm": 4,
                "pipe_axis_z_mm": 35,
                "pipe_top_z_mm": 66,
                "available_levelling_depth_above_pipe_to_z100_mm": 34,
                "accepted_for_construction": False,
            },
        ],
        "preferred_detail_requirements": {
            "pipe_fixing_base": "RAW_STRUCTURAL_CONCRETE_SLAB",
            "pipe_fixing_product": None,
            "recommended_max_fixing_spacing_straight_mm": 800,
            "maximum_fastener_distance_before_and_after_each_bend_mm": 300,
            "pipe_thermal_movement_must_remain_free": True,
            "factory_insulation_may_be_crushed_or_point_loaded": False,
            "levelling_material_family": "BOUND_FILL_OR_PROVEN_PRESSURE_RESISTANT_INSULATION",
            "levelling_material_product": None,
            "levelling_top_surface_z_mm": 100,
            "flat_continuous_support_surface_required": True,
            "screed_or_floor_load_may_bear_directly_on_pipe": False,
            "loose_unproven_bulk_fill_allowed": False,
            "direct_contact_compatibility_with_factory_pipe_jacket_confirmed": False,
            "existing_insulation_compressive_grade_confirmed": False,
            "selected_screed_compatibility_confirmed": False,
        },
        "fallback_detail": {
            "concept": "ENGINEERED_LOAD_RATED_SERVICE_DUCT_OR_COVER",
            "when_required": "USE_IF_COMPLIANT_LEVEL_SURFACE_CANNOT_BE_CREATED_OR_PRODUCT_MANUFACTURER_REQUIRES_A_DUCT",
            "selected": False,
            "structural_calculation_complete": False,
        },
        "fastener_schedule_screen": {
            "straight_axis_length_mm": 4570,
            "recommended_max_spacing_mm": 800,
            "minimum_interval_count_if_only_length_division": 6,
            "minimum_point_count_if_endpoints_are_both_fixed": 7,
            "additional_bend_proximity_fasteners_required": True,
            "exact_count_and_positions": None,
            "reason_not_final": "ROUTE_HAS_DIRECTION_CHANGE_AND_ACCESS_BOX__FASTENER_PRODUCT_AND_FIXED_SLIDING_POINT_SCHEME_NOT_SELECTED",
        },
        "remaining_release_inputs": [
            "IDENTIFY_EXISTING_100MM_INSULATION_PRODUCT_AND_COMPRESSIVE_GRADE",
            "SELECT_PIPE_FIXING_FOR_FACTORY_INSULATED_OD62_AND_VERIFY_THERMAL_MOVEMENT",
            "SELECT_BOUND_FILL_OR_PRESSURE_RESISTANT_INSULATION_WITH_COMPRESSIVE_AND_THERMAL_DATA",
            "VERIFY_CHEMICAL_AND_TEMPERATURE_COMPATIBILITY_WITH_PIPE_JACKET",
            "VERIFY_200MM_SUPPORT_STRIP_CONTINUITY_ALONG_ROUTE",
            "SELECT_D116_SCREEED_BRANCH_AND_FINISH_SCHEDULE",
            "CALCULATE_LOCAL_THERMAL_BRIDGE_AND_FLOOR_SURFACE_TEMPERATURE",
            "ISSUE_INSTALLATION_AND_PHOTOGRAPHIC_CLOSEOUT_PLAN",
        ],
        "approved_pipe_geometry_count": 0,
        "approved_levelling_product_count": 0,
        "approved_load_bridge_detail_count": 0,
        "construction_authorized": False,
        "result": "PASS_PREFERRED_LEVELLING_CONCEPT_REWORK_EXACT_MATERIALS_AND_RELEASE",
    }
    model["levelling_concept_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "floor_primary_levelling_concept.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf8")

    im = Image.new("RGB", (1800, 1200), "#F4F8F8")
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, 0, 1800, 190), fill="#071B23")
    d.text((42, 18), "D120 · ОСНОВНОЙ УЗЕЛ: ВЫРАВНИВАЮЩИЙ СЛОЙ", font=font(29, True), fill="white")
    d.text((42, 72), "Uponor: трубу закрепить к плите и восстановить ровную опорную поверхность", font=font(20, True), fill="#A8EEE7")
    d.text((42, 126), "Рассчитанная крышка остаётся запасным вариантом, а не обязательным первым решением", font=font(18, True), fill="#F3D58C")

    slab_y, top_y = 965, 390
    left, right = 130, 1120
    channel_l, channel_r = 385, 885
    d.rectangle((left, slab_y, right, slab_y + 90), fill="#AEB7BD", outline="#55636A", width=3)
    d.rectangle((left, top_y, channel_l, slab_y), fill="#D8E8A8", outline="#6A8230", width=3)
    d.rectangle((channel_r, top_y, right, slab_y), fill="#D8E8A8", outline="#6A8230", width=3)
    d.rectangle((channel_l, top_y, channel_r, slab_y), fill="#C8E1D5", outline="#328265", width=3)
    d.text((515, 425), "СВЯЗАННОЕ ЗАПОЛНЕНИЕ / ЖЁСТКИЙ УТЕПЛИТЕЛЬ", font=font(17, True), fill="#1F694F")
    d.text((537, 465), "точный продукт и прочность НЕ ВЫБРАНЫ", font=font(15, True), fill="#8A2230")
    for cx, label in ((510, "P1"), (760, "P2")):
        d.ellipse((cx - 78, 785 - 78, cx + 78, 785 + 78), fill="#E8B64E", outline="#A66B00", width=4)
        d.ellipse((cx - 40, 785 - 40, cx + 40, 785 + 40), fill="#267EB5", outline="#054B78", width=3)
        d.text((cx - 22, 765), label, font=font(17, True), fill="white")
    d.line((channel_l, slab_y - 18, channel_r, slab_y - 18), fill="#B00020", width=3)
    d.text((550, slab_y - 11), "200 мм ≤ 300 мм", font=font(17, True), fill="#B00020")
    d.text((155, 1000), "Ж/Б ПЛИТА · крепление труб к плите", font=font(18, True), fill="#243A43")
    d.text((158, 430), "существующий утеплитель", font=font(16, True), fill="#587022")
    d.text((900, 430), "опорная полоса", font=font(16, True), fill="#587022")
    d.text((900, 465), "проверить ≥200 мм", font=font(15, True), fill="#8A2230")
    d.line((left, top_y, right, top_y), fill="#006E72", width=5)
    d.text((444, 330), "РОВНАЯ НЕПРЕРЫВНАЯ ПОВЕРХНОСТЬ z=100", font=font(20, True), fill="#006E72")

    d.rounded_rectangle((1190, 245, 1745, 1065), radius=22, fill="white", outline="#A0B3BA", width=3)
    notes = [
        ("ПРАВИЛА УЗЛА", True, "#153A43"),
        ("· трасса с изоляцией: 200 мм", False, "#153A43"),
        ("· предел Uponor: ≤300 мм", False, "#006A43"),
        ("· опорная полоса рядом: ≥200 мм", False, "#153A43"),
        ("· фиксация на прямой: ≤800 мм", False, "#153A43"),
        ("· до/после поворота: ≤300 мм", False, "#153A43"),
        ("· тепловое движение не зажимать", False, "#153A43"),
        ("", False, "#153A43"),
        ("МАТЕРИАЛ", True, "#153A43"),
        ("связанное заполнение либо", False, "#153A43"),
        ("доказанный жёсткий утеплитель", False, "#153A43"),
        ("точный продукт НЕ ВЫБРАН", True, "#B00020"),
        ("", False, "#153A43"),
        ("НАГРУЗКА НА ТРУБУ: ЗАПРЕЩЕНА", True, "#B00020"),
        ("СТРОИТЕЛЬСТВО: НЕ РАЗРЕШЕНО", True, "#B00020"),
    ]
    y = 290
    for text, bold, color in notes:
        if text:
            d.text((1230, y), text, font=font(17 if not bold else 18, bold), fill=color)
        y += 47
    im.save(OUTPUT / "floor_primary_levelling_concept_evidence.png")

    (OUTPUT / "method_note.md").write_text(
        "# D120 — основной метод восстановления пола\n\n"
        "Предпочтительный узел теперь следует прямому указанию Uponor для труб на черновой бетонной плите: "
        "закрепить трубы, затем восстановить ровную опорную поверхность связанным выравнивающим материалом либо "
        "доказанным жёстким утеплителем. Нагрузка стяжки не должна передаваться на трубу или сминать заводскую изоляцию.\n\n"
        "Трасса 200 мм находится внутри указанного Uponor предела 300 мм. Рядом с трассой требуется непрерывная опорная "
        "полоса не менее 200 мм. На прямой рекомендуется крепление не реже 800 мм, до и после каждого поворота - не далее 300 мм.\n\n"
        "Точный крепёж, заполняющий материал, существующий утеплитель и стяжка пока не идентифицированы. Поэтому узел остаётся "
        "координационным. Если ровную несущую поверхность этим способом подтвердить нельзя, применяется рассчитанный короб/крышка D117.\n",
        encoding="utf8",
    )
    files = [p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    manifest = {
        "artifact_id": model["artifact_id"],
        "levelling_concept_digest": model["levelling_concept_digest"],
        "append_only": True,
        "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
    }
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "digest": model["levelling_concept_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

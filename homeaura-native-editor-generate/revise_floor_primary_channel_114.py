from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_CHANNEL_REVISION_114"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_CHANNEL_REVISION_114.zip"
SOURCES = [
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_INTEGRATION_109" / "floor_primary_integration.json",
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_RESEARCH_113" / "floor_primary_research.json",
    BASE / "HA_TWO_FLOOR_ATTIC_PRIMARY_BEND_FITTINGS_097" / "attic_primary_bend_fittings.json",
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_INSTALLATION_SHEET_112" / "installation_sheet.json",
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
        raise FileExistsError("D114 is append-only")
    records = []
    source = {}
    for path in SOURCES:
        model = json.loads(path.read_text(encoding="utf8"))
        source[model["artifact_id"]] = model
        records.append({"artifact_id": model["artifact_id"], "file": path.name, "sha256": sha(path)})

    d109 = source["HA_TWO_FLOOR_FLOOR_PRIMARY_INTEGRATION_109"]
    d113 = source["HA_TWO_FLOOR_FLOOR_PRIMARY_RESEARCH_113"]
    d097 = source["HA_TWO_FLOOR_ATTIC_PRIMARY_BEND_FITTINGS_097"]
    channel = d109["selected_floor_1_primary_route_method"]

    model = {
        "schema": "homeaura-floor-primary-channel-revision-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_CHANNEL_REVISION_114",
        "status": "REVISED_COORDINATION_DETAIL_PASS_REWORK_ENGINEERED_LOAD_BRIDGE_SUPPORTS_SLAB_RELEASE_AND_PENETRATION_SEAL",
        "source_records": records,
        "supersession": {
            "D109_route_axis_and_noncontact_geometry_preserved": True,
            "D109_thirty_mm_insulation_as_possible_load_closure_rejected": True,
            "D112_coordination_pdf_disposition": "HISTORICAL_COORDINATION_ONLY__DO_NOT_USE_PAGE_2_AS_CONSTRUCTION_LOAD_DETAIL",
        },
        "owner_inputs_preserved": d109["owner_inputs_locked"],
        "horizontal_floor_channel": {
            "route_axis_building_mm": channel["plan_axis_building_mm"],
            "axis_length_mm": channel["axis_length_mm"],
            "channel_width_mm": 200,
            "installed_insulation_depth_mm": 100,
            "service_zone_from_slab_mm": [0, 70],
            "coordination_primary_axis_z_mm": 35,
            "actual_comparison_insulated_pipe_od_mm": 62,
            "actual_pipe_surface_z_range_at_coordination_axis_mm": [4, 66],
            "actual_thermal_infill_nominal_above_pipe_mm": 34,
            "provisional_envelope_od_mm": 70,
            "provisional_envelope_top_z_mm": 70,
            "thermal_infill_design_basis_mm": 30,
            "thermal_infill_is_load_bearing_member": False,
            "structural_clear_span_to_bridge_mm": 200,
            "pipe_axis_pitch_mm": 100,
            "actual_pipe_side_margin_mm": 19,
            "actual_clear_gap_between_pipe_insulation_mm": 38,
            "provisional_envelope_side_margin_mm": 15,
            "provisional_envelope_gap_mm": 30,
            "plan_crossing_route_count": channel["plan_crossing_route_count"],
            "geometric_3d_contact_count": channel["geometric_3d_contact_count"],
            "hidden_fitting_count": 0,
        },
        "required_load_path": {
            "selected_concept": "ENGINEERED_SERVICE_DUCT_OR_LOAD_BRIDGE_OVER_200MM_CHANNEL",
            "bridge_bears_on": "STRUCTURAL_SUPPORTS_OR_VERIFIED_BEARERS_OUTSIDE_PIPE_ENVELOPES",
            "screed_and_finish_load_may_bear_on_pipe_or_thermal_infill": False,
            "bridge_material": None,
            "bridge_thickness_mm": None,
            "support_spacing_mm": None,
            "design_live_load_kpa": None,
            "screed_reinforcement_detail": None,
            "structural_calculation_complete": False,
            "construction_release": False,
        },
        "primary_support_contract": {
            "support_base": "STRUCTURAL_SLAB",
            "support_may_attach_to_insulation": False,
            "support_type": None,
            "support_height_allowance_mm": None,
            "factory_insulation_crushing_check_complete": False,
            "thermal_movement_scheme": "DEFINED_FIXED_POINT_PLUS_PRODUCT_COMPATIBLE_SLIDING_SUPPORTS_REQUIRED",
            "exact_fixed_point_location": None,
            "generic_horizontal_spacing_from_manufacturer_adopted": False,
            "physical_fit_with_selected_support_system_proven": False,
        },
        "vertical_riser_on_far_internal_AAC_wall": {
            "selected_method": "ACCESSIBLE_SURFACE_SERVICE_BOX_OR_SERVICE_ZONE__NO_DEEP_AAC_CHASE",
            "external_wall_used": False,
            "same_plan_coordinates_both_floors": True,
            "insulated_primary_pair_continuous_between_accessible_boxes": True,
            "AAC_anchor_product_selected": False,
            "AAC_wall_load_bearing_status_confirmed": False,
            "deep_chasing_AAC_authorized": False,
            "inspection_access_at_direction_changes_required": True,
        },
        "slab_penetration": {
            "coordination_bbox_building_mm": [9190, 7300, 9310, 7500],
            "coordination_bbox_size_mm": [120, 200],
            "primary_axes_building_mm": [[9250, 7350], [9250, 7450]],
            "provisional_envelope_fits_coordination_bbox": True,
            "coordination_bbox_is_final_core_or_sleeve_size": False,
            "individual_smooth_sleeves_or_tested_common_system_required": True,
            "pipe_bending_over_concrete_or_wall_edge_allowed": False,
            "edge_protection_required": True,
            "slab_scan_complete": False,
            "responsible_structural_release_complete": False,
            "required_fire_resistance_rating": None,
            "penetration_seal_product_selected": False,
            "smoke_air_acoustic_closeout_detail_selected": False,
            "approved_opening_count": 0,
        },
        "bend_and_joint_policy": {
            "loop_pipe_16x2_supported_bend_radius_design_basis_mm": 80,
            "loop_pipe_16x2_free_hand_radius_mm": 128,
            "primary_pipe_32x3_radius_without_tool_mm": 160,
            "primary_pipe_32x3_radius_with_Uponor_tool_mm": 80,
            "primary_hot_bending_allowed": False,
            "primary_repeated_bending_same_point_allowed": False,
            "selected_primary_direction_change": d097["selected_direction_change_fitting"],
            "press_elbows_allowed_only_in_accessible_boxes": True,
            "hidden_joint_count": 0,
        },
        "operating_scope": {
            "heating_only": True,
            "cooling_authorized": False,
            "cooling_requires_vapour_tight_insulation_and_condensation_analysis": True,
            "pressure_test_before_closeout_required": True,
            "photo_and_dimension_record_before_closeout_required": True,
        },
        "site_release_sequence": [
            "SELECT_UFH_AND_SCREED_SYSTEM_FOR_ACTUAL_LOAD_AND_FINISH",
            "DESIGN_LOAD_BEARING_DUCT_OR_BRIDGE_OVER_200MM_CHANNEL",
            "SELECT_SLAB_FIXED_PIPE_SUPPORTS_AND_VERIFY_SEVENTY_MM_ZONE_FIT",
            "SCAN_SLAB_AND_RELEASE_COORDINATION_OPENING",
            "SELECT_SLEEVES_EDGE_PROTECTION_AND_APPLICATION_SPECIFIC_PENETRATION_CLOSEOUT",
            "CONFIRM_AAC_WALL_STATUS_AND_SELECT_SURFACE_BOX_ANCHORS",
            "INSTALL_CONTINUOUS_INSULATED_PRIMARIES_WITH_ACCESSIBLE_ELBOWS_ONLY",
            "PRESSURE_TEST_PHOTOGRAPH_AND_DIMENSION_RECORD",
            "INSTALL_ENGINEERED_BRIDGE_THEN_MARK_NO_FASTENER_ZONE",
        ],
        "research_corrections_all_carried": len(d113["engineering_corrections"]),
        "approved_pipe_geometry_count": 0,
        "complete_primary_route_count": 0,
        "construction_issue_count": 0,
        "procurement_authorized": False,
        "construction_authorized": False,
        "result": "PASS_REVISED_COORDINATION_CONTRACT_REWORK_PRODUCT_AND_SITE_RELEASE",
    }
    model["revision_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "floor_primary_channel_revision.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf8")

    im = Image.new("RGB", (1800, 1250), "#F4F8F8")
    draw = ImageDraw.Draw(im, "RGBA")
    draw.rectangle((0, 0, 1800, 190), fill="#071A21")
    draw.text((38, 22), "D114 · ИСПРАВЛЕННЫЙ УЗЕЛ КАНАЛА", font=font(28, True), fill="white")
    draw.text((38, 72), "30 мм сверху — только тепловое заполнение, не несущая перемычка", font=font(20, True), fill="#FFB2B2")
    draw.text((38, 122), "Стяжку и нагрузку несёт рассчитанный мост/короб; трубы закрепляются к плите", font=font(18, True), fill="#A7EEE7")

    x0, x1 = 120, 1110
    slab_top, ins_top = 1020, 610
    draw.rectangle((x0, slab_top, x1, 1110), fill="#808B90", outline="#263238", width=3)
    draw.text((140, 1044), "Ж/Б ПЛИТА — ОСНОВАНИЕ ОПОР", font=font(17, True), fill="white")
    draw.rectangle((x0, ins_top, x1, slab_top), fill="#DCEFA3", outline="#718542", width=3)
    draw.text((140, 935), "100 мм существующей теплоизоляции", font=font(16, True), fill="#38531C")

    cx0, cx1 = 440, 790
    bridge_y0, bridge_y1 = 565, 635
    draw.rectangle((cx0, 735, cx1, slab_top), fill="#FFF9D9", outline="#C36E00", width=4)
    draw.rectangle((cx0, ins_top, cx1, 735), fill="#B9DB75", outline="#58752B", width=2)
    draw.text((492, 648), "≈30–34 мм тепловое заполнение", font=font(13, True), fill="#38531C")

    draw.rectangle((cx0 - 55, bridge_y0, cx1 + 55, bridge_y1), fill="#556973", outline="#17262C", width=4)
    draw.text((455, 575), "РАССЧИТАННЫЙ НЕСУЩИЙ МОСТ / КОРОБ", font=font(14, True), fill="white")
    draw.rectangle((cx0 - 70, 635, cx0 - 20, slab_top), fill="#8B6747", outline="#4D3420", width=3)
    draw.rectangle((cx1 + 20, 635, cx1 + 70, slab_top), fill="#8B6747", outline="#4D3420", width=3)
    draw.text((330, 700), "опора", font=font(12, True), fill="#4D3420")
    draw.text((830, 700), "опора", font=font(12, True), fill="#4D3420")

    for px, color, label in ((535, "#C83434", "П"), (695, "#2477B3", "О")):
        draw.ellipse((px - 55, 805, px + 55, 915), fill="#87959A", outline="#263238", width=3)
        draw.ellipse((px - 28, 832, px + 28, 888), fill=color, outline="white", width=3)
        draw.text((px - 8, 844), label, font=font(15, True), fill="white")
        draw.line((px, 915, px, 986), fill="#293E47", width=8)
        draw.rectangle((px - 30, 980, px + 30, 1018), fill="#46616D", outline="#263238", width=2)
    draw.text((450, 925), "Опоры/седла к плите; смятие изоляции не допускается", font=font(13, True), fill="#7A4100")
    draw.line((cx0, 535, cx1, 535), fill="#C00020", width=5)
    draw.text((405, 495), "200 мм: запрет крепежа тёплого пола сохраняется", font=font(15, True), fill="#C00020")

    draw.rounded_rectangle((1170, 245, 1745, 1120), radius=22, fill="white", outline="#A7B9BF", width=3)
    draw.text((1210, 280), "ПРИНЯТО", font=font(21, True), fill="#006A43")
    accepted = [
        "маршрут внутри дома",
        "2 × 32×3, заводская изоляция",
        "скрытых соединений: 0",
        "отводы только с доступом",
        "перегиб через кромку: запрещён",
        "R80 петли — с поддержкой",
        "режим: только отопление",
    ]
    y = 335
    for item in accepted:
        draw.ellipse((1210, y + 7, 1225, y + 22), fill="#00A37A")
        draw.text((1245, y), item, font=font(15, True), fill="#143842")
        y += 53
    draw.text((1210, 735), "НЕ ВЫПУЩЕНО", font=font(21, True), fill="#B00020")
    blocked = [
        "материал/толщина моста",
        "опоры труб и их высота",
        "расчёт нагрузки стяжки",
        "сканирование плиты",
        "гильзы и заделка проходки",
        "анкеры сервисного короба в ГБ",
    ]
    y = 790
    for item in blocked:
        draw.rectangle((1210, y + 6, 1225, y + 21), fill="#B00020")
        draw.text((1245, y), item, font=font(15, True), fill="#4A3035")
        y += 48
    im.save(OUTPUT / "floor_primary_channel_revision_evidence.png")

    (OUTPUT / "installation_addendum.md").write_text(
        "# D114 — обязательное дополнение к D112\n\n"
        "Лист D112 остаётся координационным и не является монтажным выпуском. Текст о восстановлении 30 мм утеплителя следует читать только как тепловое заполнение. Оно не передаёт расчётную нагрузку стяжки и чистого пола. Над полосой 200 мм должен быть отдельный рассчитанный несущий мост или сервисный короб с опиранием вне конвертов труб.\n\n"
        "Две магистрали закрепляются совместимыми седлами/опорами к железобетонной плите, а не к утеплителю. До выбора опор нельзя считать доказанной физическую посадку в нижние 70 мм. Заводская изоляция не должна сминаться.\n\n"
        "На дальней внутренней стене принят доступный сервисный короб; глубокое штробление газобетона не разрешено. В перекрытии трубы проходят в гладких гильзах/испытанной системе, не касаются острых кромок и не изгибаются через край. Размер 120×200 остаётся координационным до сканирования и решения конструктора.\n\n"
        "Для 32×3: R160 без инструмента, R80 фирменным инструментом; горячая и повторная гибка запрещены. Базовый способ поворота остаётся прежним — пресс-отводы только в доступных коробах.\n",
        encoding="utf8",
    )
    (OUTPUT / "report.md").write_text(
        "# D114 — исправленный договор узла\n\n"
        "Геометрия D109 сохранена как координационная: полоса 200 мм, две изолированные магистрали, девять пересечений в плане и ноль контактов в 3D. Исправлена конструктивная трактовка закрытия канала. Тридцать миллиметров теплоизоляции над трубами не считаются несущим элементом.\n\n"
        "Вертикальный участок выполняется по дальней внутренней газобетонной стене в доступном коробе, без глубокой штробы. Отверстие совпадает по плану на обоих этажах, но пока не имеет строительного выпуска, гильз и выбранной заделки.\n\n"
        "Монтаж остаётся заблокирован до выбора несущего моста, опор труб, полного пола/стяжки, сканирования плиты и узла проходки.\n",
        encoding="utf8",
    )
    files = [p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps(
            {
                "artifact_id": model["artifact_id"],
                "revision_digest": model["revision_digest"],
                "append_only": True,
                "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf8",
    )
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "digest": model["revision_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

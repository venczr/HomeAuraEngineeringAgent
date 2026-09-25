from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_INTEGRATION_109"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_INTEGRATION_109.zip"
SOURCES = [
    ("D098", BASE / "HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098" / "two_primary_internal_penetration.json"),
    ("D100", BASE / "HA_TWO_FLOOR_OWNER_FLOOR_BUILDUP_100" / "owner_floor_build_up.json"),
    ("D101", BASE / "HA_TWO_FLOOR_PRIMARY_WALL_SERVICE_BOX_101" / "primary_wall_service_box.json"),
    ("D103", BASE / "HA_TWO_FLOOR_FLOOR_LAYER_STACK_103" / "floor_layer_stack.json"),
    ("D104", BASE / "HA_TWO_FLOOR_PRIMARY_INSULATION_CHANNEL_104" / "primary_insulation_channel.json"),
    ("D106", BASE / "HA_TWO_FLOOR_PRIMARY_CHANNEL_3D_EVIDENCE_106" / "primary_channel_3d_corrected.json"),
    ("D107", BASE / "HA_TWO_FLOOR_PRIMARY_CHANNEL_NO_FASTENER_107" / "primary_channel_no_fastener.json"),
    ("D108", BASE / "HA_TWO_FLOOR_PRIMARY_CHANNEL_THERMAL_108" / "primary_channel_thermal.json"),
]


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(payload).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D109 is append-only")
    records = []
    models = {}
    for tag, path in SOURCES:
        raw = path.read_bytes()
        model = json.loads(raw.decode("utf8"))
        models[tag] = model
        records.append({"tag": tag, "artifact_id": model["artifact_id"], "file": path.name, "sha256": hashlib.sha256(raw).hexdigest().upper()})

    d103 = models["D103"]
    d104 = models["D104"]
    d106 = models["D106"]
    d107 = models["D107"]
    d108 = models["D108"]
    model = {
        "schema": "homeaura-floor-primary-integration-stage-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_INTEGRATION_109",
        "status": "FLOOR_BUILDUP_AND_HIDDEN_PRIMARY_DESIGN_BASELINE_PASS_REWORK_SITE_RELEASE_PRODUCTS_AND_LOAD_BRIDGE",
        "source_records": records,
        "owner_inputs_locked": {
            "floor_1_installed_insulation_mm": 100,
            "floor_1_remaining_to_finished_floor_mm": 70,
            "attic_installed_insulation_mm": 50,
            "attic_remaining_to_finished_floor_mm": 70,
            "floor_to_floor_height_owner_value_mm": 3000,
            "wall_material": "AAC_GAS_CONCRETE",
            "loop_pipe_od_mm": 16,
            "loop_design_centerline_bend_radius_mm": 80,
        },
        "selected_floor_layer_design_basis_both_floors": {
            "installed_insulation_top_z_mm": 0,
            "loop_pipe_z_range_mm": [0, 16],
            "design_screed_cover_above_pipe_mm": 35,
            "total_screed_from_insulation_top_mm": 51,
            "finish_adhesive_underlay_allowance_mm": 19,
            "available_above_insulation_mm": 70,
            "height_reconciliation_mm": 70,
            "fits": True,
            "basis_status": "DESIGN_BASIS_NOT_PRODUCT_OR_MIX_ACCEPTANCE",
            "source_D103_reconciles": d103["selected_layer_design_basis"]["height_reconciliation_mm"] == 70,
        },
        "selected_floor_1_primary_route_method": {
            "method": "OPEN_EXISTING_INSULATION_STRIP_TO_STRUCTURAL_SLAB__PLACE_CONTINUOUS_INSULATED_PRIMARIES_IN_LOWER_ZONE__RESTORE_30MM_INSULATION_ABOVE",
            "plan_axis_building_mm": d104["route_axis_building_mm"],
            "axis_length_mm": 4570,
            "strip_width_mm": 200,
            "lower_service_zone_z_from_structural_slab_mm": [0, 70],
            "actual_comparison_insulated_pipe_od_mm": 62,
            "provisional_design_envelope_od_mm": 70,
            "primary_axis_z_mm": 35,
            "restored_insulation_above_service_zone_mm": 30,
            "warm_floor_loop_bottom_z_from_structural_slab_mm": 100,
            "warm_floor_loop_top_z_from_structural_slab_mm": 116,
            "minimum_primary_envelope_to_loop_surface_clearance_mm": 30,
            "plan_crossing_route_count": 9,
            "geometric_3d_contact_count": 0,
            "hidden_press_fitting_count": 0,
            "continuous_factory_insulated_pipe_required": True,
            "D104_depth_cut_wording_disposition": "SUPERSEDED__DO_NOT_CUT_ONLY_70MM_DOWN_FROM_INSULATION_TOP__OPEN_STRIP_TO_SLAB_AND_RESTORE_30MM_ABOVE",
        },
        "floor_1_no_fastener_control": {
            "marked_zone_width_mm": d107["no_fastener_zone_total_width_mm"],
            "marked_zone_area_m2": d107["no_fastener_zone_area_m2"],
            "affected_floor_loop_route_count": d107["affected_route_count"],
            "affected_route_ids": [item["route_id"] for item in d107["affected_routes"]],
            "exact_loop_pipe_length_inside_marked_zone_mm": d107["total_loop_pipe_length_inside_marked_zone_mm"],
            "tacker_clip_staple_screw_anchor_allowed": False,
            "non_penetrating_support_or_load_spreading_bridge_required": True,
            "loop_route_geometry_modified": False,
        },
        "thermal_screen": {
            "route_axis_length_m": d108["primary_route_axis_length_m"],
            "temperature_scenario_range_c": [[35, 30], [45, 38]],
            "pair_heat_loss_range_w": d108["screening_result"]["pair_heat_loss_range_w"],
            "inside_heated_building_envelope": True,
            "additional_30mm_insulation_above_credited": False,
            "local_finished_floor_surface_temperature_calculated": False,
            "linear_thermal_bridge_calculated": False,
        },
        "internal_vertical_transition": {
            "external_wall_used": False,
            "same_plan_coordinates_both_floors": True,
            "opening_bbox_building_mm": [9190, 7300, 9310, 7500],
            "clear_opening_size_mm": [120, 200],
            "primary_axes_building_mm": [[9250, 7350], [9250, 7450]],
            "route_description": "K1_BOILER_ROOM_FLOOR_TO_STAIRS__UP_FAR_INTERNAL_WALL__ATTIC_WARDROBE_K2",
            "slab_scan_and_responsible_designer_release_required": True,
            "approved_slab_opening_count": 0,
        },
        "attic_K2_mounting_datum": {
            "finished_floor_z_above_structural_slab_mm": 120,
            "cabinet_bottom_z_above_structural_slab_mm": 390,
            "cabinet_top_z_above_structural_slab_mm": 1120,
        },
        "fallback_if_floor_channel_rejected": {
            "artifact_id": models["D101"]["artifact_id"],
            "method": "ACCESSIBLE_INTERNAL_WALL_SERVICE_BOX",
            "hidden_wall_chase": False,
            "selected_as_primary": False,
        },
        "installation_sequence": [
            "SCAN_AND_RELEASE_D098_SLAB_OPENING_BEFORE_DRILLING",
            "MARK_200MM_CHANNEL_AND_OPEN_EXISTING_INSULATION_TO_STRUCTURAL_SLAB",
            "INSTALL_TWO_CONTINUOUS_FACTORY_INSULATED_32X3_PRIMARIES_WITH_NO_HIDDEN_FITTINGS",
            "PRESSURE_TEST_PRIMARY_PAIR_AND_PHOTOGRAPH_WITH_DIMENSIONS",
            "RESTORE_30MM_COMPRESSIVE_INSULATION_OR_ENGINEERED_LOAD_BRIDGE_ABOVE_CHANNEL",
            "MARK_NO_FASTENER_ZONE_ON_TOP_SURFACE",
            "INSTALL_16MM_LOOPS_WITHOUT_STAPLES_OR_ANCHORS_IN_MARKED_ZONE",
            "PRESSURE_TEST_ALL_LOOPS_BEFORE_51MM_DESIGN_BASIS_SCREED",
            "VERIFY_19MM_FINISH_BUILDUP_BEFORE_FINISHED_FLOOR",
        ],
        "release_items": [
            "SELECT_SCREED_SYSTEM_AND_CONFIRM_35MM_COVER_FOR_ACTUAL_LOAD_AND_MANUFACTURER",
            "SELECT_19MM_OR_LESS_FINISH_ADHESIVE_UNDERLAY_STACK",
            "SELECT_COMPRESSIVE_30MM_CHANNEL_COVER_OR_LOAD_SPREADING_BRIDGE_AND_FIXING_METHOD",
            "SELECT_EXACT_PRIMARY_INSULATION_AND_CHANNEL_CLOSEOUT_DETAIL",
            "SCAN_REBAR_BEAMS_SERVICES_AND_APPROVE_120X200_SLAB_OPENING",
            "CONFIRM_3000MM_HEIGHT_DATUM_FFL_TO_FFL_OR_OTHER",
        ],
        "approved_pipe_geometry_count": 0,
        "complete_primary_route_count": 0,
        "construction_issue_count": 0,
        "procurement_authorized": False,
        "construction_authorized": False,
        "result": "PASS_INTEGRATED_PARAMETRIC_FLOOR_AND_PRIMARY_DETAIL_REWORK_RELEASE_ITEMS",
    }
    model["integration_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "floor_primary_integration.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf8")

    im = Image.new("RGB", (1800, 1220), "#F4F8F8")
    draw = ImageDraw.Draw(im, "RGBA")
    draw.rectangle((0, 0, 1800, 185), fill="#071A21")
    draw.text((38, 22), "D109 · ПОЛ + СКРЫТЫЕ МАГИСТРАЛИ", font=font(27, True), fill="white")
    draw.text((38, 73), "Основной вариант: две Ø32×3 в заводской изоляции внутри существующих 100 мм утеплителя", font=font(18, True), fill="#A7EEE7")
    draw.text((38, 119), "Полосу открыть до плиты, затем восстановить 30 мм утеплителя сверху · крепёж в полосе запрещён", font=font(17), fill="#F3D58C")

    x0, x1 = 105, 1050
    slab_y, ins_top_y, ffl_y = 1000, 620, 355
    draw.rectangle((x0, slab_y, x1, 1080), fill="#8A9498", outline="#263238", width=2)
    draw.text((115, 1023), "Ж/Б ПЛИТА", font=font(16, True), fill="white")
    draw.rectangle((x0, ins_top_y, x1, slab_y), fill="#DDEFA7", outline="#718542", width=2)
    draw.text((115, 925), "100 мм существующего утеплителя", font=font(16, True), fill="#38531C")
    channel_x0, channel_x1 = 480, 825
    service_top = 735
    draw.rectangle((channel_x0, service_top, channel_x1, slab_y), fill="#EFF8C9", outline="#D07800", width=4)
    draw.rectangle((channel_x0, ins_top_y, channel_x1, service_top), fill="#B9DB75", outline="#4D6D22", width=2)
    draw.text((515, 646), "30 мм восстановить", font=font(14, True), fill="#38531C")
    for cx, color in ((575, "#C83434"), (730, "#2477B3")):
        draw.ellipse((cx - 58, 822, cx + 58, 938), fill="#87959A", outline="#263238", width=3)
        draw.ellipse((cx - 30, 850, cx + 30, 910), fill=color, outline="white", width=3)
    draw.text((506, 952), "2 × Ø32, изоляция Ø62; расчётный конверт Ø70", font=font(13, True), fill="#7A4100")
    draw.line((channel_x0, 602, channel_x1, 602), fill="#C00020", width=5)
    draw.text((465, 560), "ПОЛОСА 200 мм: БЕЗ СКОБ / САМОРЕЗОВ / АНКЕРОВ", font=font(14, True), fill="#C00020")
    draw.rectangle((x0, ins_top_y - 68, x1, ins_top_y), fill="#D8C9B1", outline="#8B7355", width=2)
    draw.text((115, 572), "Труба Ø16 + стяжка: 51 мм", font=font(15, True), fill="#5A4632")
    for cx in (350, 650, 900):
        draw.ellipse((cx - 13, ins_top_y - 20, cx + 13, ins_top_y + 6), fill="#D33838", outline="#7C0000")
    draw.rectangle((x0, ffl_y, x1, ins_top_y - 68), fill="#EEE5DA", outline="#A08C74", width=2)
    draw.text((115, 445), "До 19 мм: финиш + клей / подложка", font=font(15, True), fill="#5A4632")
    draw.line((x0, ffl_y, x1, ffl_y), fill="#071A21", width=5)
    draw.text((110, 315), "ЧИСТЫЙ ПОЛ  +170 мм от плиты", font=font(17, True), fill="#071A21")
    draw.line((865, 735, 865, 620), fill="#007A63", width=3)
    draw.text((885, 665), "30 мм геометрического зазора", font=font(14, True), fill="#007A63")

    draw.rounded_rectangle((1120, 250, 1740, 1090), radius=20, fill="white", outline="#A7B9BF", width=3)
    draw.text((1160, 285), "ЗАКРЕПЛЕНО", font=font(21, True), fill="#006A43")
    locked = [
        "1 этаж: 100 + 70 = 170 мм",
        "Мансарда: 50 + 70 = 120 мм",
        "Контур Ø16, R по оси 80 мм",
        "Стяжка: 16 + 35 = 51 мм",
        "Финишный запас: до 19 мм",
        "Канал: 200 мм × нижние 70 мм",
        "Над каналом: 30 мм утеплителя",
        "Пересечений в плане: 9",
        "Контактов труб в 3D: 0",
        "Длина канала: 4,57 м",
        "Потери пары: 34,9–60,0 Вт",
        "Скрытых фитингов: 0",
    ]
    y = 345
    for text in locked:
        draw.ellipse((1160, y + 5, 1174, y + 19), fill="#00A37A")
        draw.text((1190, y), text, font=font(15, True), fill="#143842")
        y += 50
    draw.text((1160, 965), "НЕ РАЗРЕШЕНО К МОНТАЖУ ДО:", font=font(16, True), fill="#B00020")
    draw.text((1160, 1005), "сканирования плиты, выбора стяжки,", font=font(14), fill="#566B73")
    draw.text((1160, 1040), "утеплителя/мостика и проверки высот.", font=font(14), fill="#566B73")
    im.save(OUTPUT / "floor_primary_integration_evidence.png")

    (OUTPUT / "installation_release_checklist.md").write_text(
        "# D109 — чек-лист выпуска узла\n\n"
        "Основной вариант — две непрерывные заводски изолированные магистрали 32×3 в нижней зоне существующих 100 мм утеплителя первого этажа. Полосу шириной 200 мм открыть до плиты; после опрессовки восстановить 30 мм теплоизоляции или применить рассчитанный распределяющий мостик. В полосе запрещены скобы, саморезы и анкеры тёплого пола.\n\n"
        "## До монтажа\n\n"
        "- выбрать стяжку и письменно подтвердить 35 мм покрытия над трубой для фактической нагрузки;\n"
        "- уложить финишный пирог, клей и подложку в оставшиеся 19 мм;\n"
        "- выбрать материал 30-мм закрытия канала и проверить его прочность;\n"
        "- выбрать точную изоляцию магистралей и способ заполнения/фиксации в канале;\n"
        "- просканировать плиту в зоне отверстия 120×200 мм и получить выпуск ответственного конструктора;\n"
        "- уточнить, 3000 мм — это чистый пол–чистый пол или другая отметка.\n\n"
        "## Контроль монтажа\n\n"
        "Никаких скрытых пресс-фитингов. Опрессовать магистрали до закрытия, сфотографировать с рулеткой, нанести края 200-мм запретной полосы на верх утеплителя, затем уложить контуры Ø16 без проникающего крепежа в этой полосе.\n",
        encoding="utf8",
    )
    (OUTPUT / "report.md").write_text(
        "# D109 — интеграция конструкции пола и первичных магистралей\n\n"
        "Выбран скрытый внутренний вариант: от K1 по полу котельной к лестнице, затем вверх по дальней внутренней стене в гардеробную мансарды к K2. Наружная стена не используется. На первом этаже полоса существующего утеплителя открывается до плиты; две непрерывные изолированные магистрали размещаются в нижних 70 мм, сверху восстанавливается 30 мм утеплителя.\n\n"
        "Пирог тёплого пола обоих этажей принят как проектная основа: Ø16 + 35 мм покрытия стяжки = 51 мм, ещё 19 мм остаётся на чистовое покрытие, клей и подложку. Это пока не выбор конкретной смеси.\n\n"
        "Плановые пересечения с девятью контурами не являются контактом: между наружным конвертом магистралей и трубой Ø16 остаётся 30 мм. В полосе шириной 200 мм запрещён проникающий крепёж. Тепловая отдача пары на участке 4,57 м ориентировочно 34,9–60,0 Вт; расчёт температуры поверхности пола и линейного мостика ещё не выполнен.\n",
        encoding="utf8",
    )

    files = [p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps({"artifact_id": model["artifact_id"], "integration_digest": model["integration_digest"], "append_only": True, "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]}, ensure_ascii=False, indent=2), encoding="utf8"
    )
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "digest": model["integration_digest"], "package": str(PACKAGE)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

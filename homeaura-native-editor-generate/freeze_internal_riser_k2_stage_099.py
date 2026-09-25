from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCES = [
    ("HA_TWO_FLOOR_ATTIC_K2_PRODUCT_EVIDENCE_092", "attic_k2_product_selection_corrected.json"),
    ("HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORTS_093", "attic_k2_selected_ports.json"),
    ("HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORT_BUDGETS_094", "attic_k2_selected_port_budgets.json"),
    ("HA_TWO_FLOOR_ATTIC_K2_MOUNTING_DATUM_095", "attic_k2_mounting_datum.json"),
    ("HA_TWO_FLOOR_ATTIC_PRIMARY_PIPE_SELECTION_096", "attic_primary_pipe_selection.json"),
    ("HA_TWO_FLOOR_ATTIC_PRIMARY_BEND_FITTINGS_097", "attic_primary_bend_fittings.json"),
    ("HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098", "two_primary_internal_penetration.json"),
]
OUTPUT = BASE / "HA_TWO_FLOOR_INTERNAL_RISER_K2_STAGE_GATE_099"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_INTERNAL_RISER_K2_STAGE_GATE_099.zip"


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D099 is append-only")
    records=[]; models={}
    for artifact, filename in SOURCES:
        path=BASE/artifact/filename; raw=path.read_bytes(); data=json.loads(raw.decode("utf-8"))
        records.append({"artifact_id":artifact,"file":filename,"sha256":hashlib.sha256(raw).hexdigest().upper()})
        models[artifact]=data
    ports=models[SOURCES[1][0]]; budgets=models[SOURCES[2][0]]; mounting=models[SOURCES[3][0]]
    primary=models[SOURCES[4][0]]; bends=models[SOURCES[5][0]]; penetration=models[SOURCES[6][0]]
    optimistic=[row["optimistic_total_lower_bound_mm"] for row in budgets["circuit_budgets"]]
    base=primary["base_screening_result"]
    model={
        "schema":"homeaura-internal-riser-k2-stage-gate-0.2",
        "artifact_id":"HA_TWO_FLOOR_INTERNAL_RISER_K2_STAGE_GATE_099",
        "status":"INTERNAL_TWO_MAIN_K2_DESIGN_STAGE_COMPLETE_SITE_AND_HEAT_LOSS_INPUT_REQUIRED_BEFORE_CONSTRUCTION_ROUTING",
        "source_records":records,
        "owner_inputs_locked":{
            "floor_to_floor_height_mm":3000,
            "wall_material":"AAC_GAS_CONCRETE",
            "loop_pipe_outer_diameter_mm":16,
            "loop_design_centerline_bend_radius_mm":80,
            "heated_radius_reduction_credited":False,
            "internal_route":"K1_BOILER_ROOM_ALONG_FLOOR_TO_FAR_STAIR_WALL_VERTICAL_TO_ATTIC_WARDROBE_K2",
            "external_wall_transition_used":False,
        },
        "accepted_design_baseline":{
            "architecture":"K1_TO_K2_TWO_PRIMARY_MAINS_AND_TWELVE_LOCAL_ATTIC_CIRCUITS",
            "attic_circuit_count":12,
            "attic_loop_port_count":ports["port_count"],
            "selected_K2_manifold":"UPONOR_VARIO_S_FM_12X_PART_1140843",
            "selected_K2_cabinet":"UPONOR_VARIO_OW_1050X730X135_PART_1136219",
            "K2_cabinet_plan_bbox_building_mm":ports["mounting_transform"]["cabinet_plan_bbox_building_mm"],
            "K2_project_cabinet_top_aff_mm":mounting["project_mounting_datum"]["cabinet_top_aff_mm"],
            "K2_project_cabinet_bottom_aff_mm":mounting["project_mounting_datum"]["cabinet_bottom_aff_mm"],
            "all_loop_ports_exit_down_before_turning_outside_cabinet":mounting["bend_envelope_screen"]["required_fanout_direction"].startswith("DOWNWARD"),
            "optimistic_complete_length_lower_bound_range_mm":[min(optimistic),max(optimistic)],
            "all_optimistic_lower_bounds_40_80m":budgets["all_optimistic_totals_within_40_80m"],
            "primary_pipe":"UPONOR_UNI_PIPE_PLUS_32X3_PART_1059583",
            "primary_clear_id_mm":primary["selected_design_basis_primary_pipe"]["calculated_clear_inside_diameter_mm"],
            "primary_base_flow_m3_h":base["flow_m3_h"],
            "primary_base_velocity_m_s":base["velocity_m_s"],
            "primary_turn_fitting":"UPONOR_S_PRESS_PLUS_ELBOW_32_32_PART_1070526",
            "primary_turn_fitting_quantity_screen":bends["design_quantity_screen"]["total_32x32_elbows"],
            "penetration_building_bbox_mm":penetration["selected_building_plan_opening_candidate"]["building_bbox_mm"],
            "penetration_clear_size_mm":penetration["selected_building_plan_opening_candidate"]["clear_size_mm"],
            "vertical_primary_axes":penetration["vertical_primary_axes"],
            "same_penetration_coordinates_both_floors":penetration["selected_building_plan_opening_candidate"]["same_physical_plan_coordinates_on_both_floors"],
        },
        "superseded_or_narrowed_evidence":{
            "D079_26_pipe_opening_reservation":"SUPERSEDED_BY_D098_TWO_PRIMARY_120X200_RESERVATION",
            "D093_centerline_only_R80_cabinet_screen":"SUPERSEDED_BY_D095_OUTER_PIPE_ENVELOPE_REQUIRING_DOWNWARD_EXIT",
            "D088_parametric_K2_ports":"SUPERSEDED_BY_D093_SELECTED_PRODUCT_PLAN_PORTS",
            "D089_station_assignment":"SUPERSEDED_BY_D094_SELECTED_PRODUCT_REOPTIMIZATION",
        },
        "site_release_sheet":{
            "mark_building_bbox_mm":[9190,7300,9310,7500],
            "mark_primary_axis_points_mm":[[9250,7350],[9250,7450]],
            "measure_and_record_attic_finished_floor_datum":True,
            "verify_cabinet_top_aff_target_mm":1000,
            "verify_cabinet_service_access_and_door_swing":True,
            "scan_slab_for_rebar_beams_utilities_over_full_candidate_bbox":True,
            "responsible_structural_release_before_drilling":True,
            "record_actual_slab_thickness_and_floor_build_up":True,
            "record_photos_and_measurements_from_both_floors":True,
        },
        "external_or_owner_input_gate":{
            "human_action_required":True,
            "items":[
                "SITE_MARK_AND_SCAN_D098_120X200_CANDIDATE_BEFORE_ANY_DRILLING",
                "CONFIRM_ATTIC_FINISHED_FLOOR_DATUM_AND_K2_CABINET_ACCESS",
                "PROVIDE_BUILDING_ENVELOPE_DATA_OR_ROOM_BY_ROOM_DESIGN_HEAT_LOSS",
                "CONFIRM_LOCAL_PRODUCT_AVAILABILITY_AND_INSTALLER_PRESS_THREAD_FIRESTOP_SYSTEM",
            ],
            "reason":"STRUCTURE_AND_DESIGN_HEAT_LOSS_CANNOT_BE_INFERRED_FROM_FLATTENED_PLANS",
        },
        "not_yet_engineering_accepted":[
            "SLAB_CUT_OR_CORE_DRILLING",
            "SLEEVE_FIRESTOP_ACOUSTIC_AND_WATER_SEAL_DETAIL",
            "FINAL_PRIMARY_INSULATION_PRODUCT",
            "FINAL_K1_CONNECTION_DETAIL",
            "ROOM_BY_ROOM_HEAT_LOSS_AND_FINAL_PRIMARY_DIAMETER",
            "PUMP_HEAD_BALANCING_AND_COMMISSIONING_SETPOINTS",
            "ALL_TWELVE_COMPLETE_ATTIC_ROUTE_POLYLINES_AND_40_80M_VALIDATION",
            "WHOLE_FLOOR_THERMAL_COVERAGE",
        ],
        "complete_attic_route_count":0,
        "approved_slab_opening_count":0,
        "construction_issue_count":0,
        "result":"COMPLETE_CURRENT_DESIGN_BASIS_AND_SITE_MARKING_PACKAGE_NEEDS_SITE_SCAN_AND_HEAT_LOSS_FOR_NEXT_PRODUCTION_STAGE",
    }
    model["stage_gate_digest"]=digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT/"internal_riser_k2_stage_gate.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")

    canvas=Image.new("RGB",(1800,1420),"#F4F8F8"); draw=ImageDraw.Draw(canvas,"RGBA")
    draw.rectangle((0,0,1800,220),fill="#071A21")
    draw.text((34,18),"D099 · ВНУТРЕННИЙ СТОЯК И K2 — РУБЕЖ ПРОЕКТА",font=font(25,True),fill="white")
    draw.text((34,66),"K1 → две магистрали Ø32 → внутренняя проходка → K2 в гардеробной → 12 контуров Ø16",font=font(17,True),fill="#A7EEE7")
    draw.text((34,110),"Высота 3 000 мм · стены газобетон · петли R80 · наружная стена не используется",font=font(16),fill="#F3D58C")
    draw.text((34,154),"Проектная основа завершена; сверление и рабочая разводка требуют натурных данных",font=font(17,True),fill="#FFB2B2")
    cols=[(55,280,570,"ПРИНЯТО","#008F5A"),(615,280,1130,"ПРОВЕРИТЬ НА МЕСТЕ","#D97706"),(1175,280,1745,"ПОСЛЕ НАТУРНЫХ ДАННЫХ","#B00020")]
    for x0,y0,x1,title,colour in cols:
        draw.rounded_rectangle((x0,y0,x1,1190),radius=22,fill="white",outline=colour,width=3)
        draw.rectangle((x0,y0,x1,y0+75),fill=colour)
        draw.text((x0+25,y0+21),title,font=font(18,True),fill="white")
    accepted=["Внутренняя трасса через лестницу","К2: Uponor 1140843, 12 выходов","Шкаф: Uponor 1136219, накладной","Две магистрали 32×3","Повороты: 4 пресс-угольника 32-32","Проходка-кандидат 120×200 мм","Одинаковые координаты этажей","12 нижних оценок длин: 40–80 м"]
    onsite=["Разметить bbox 9190…9310 / 7300…7500","Оси: (9250;7350) и (9250;7450)","Просканировать арматуру/балки/сети","Замерить толщину плиты и пирог пола","Проверить отметку верха шкафа 1000 мм","Проверить дверцы и сервисный доступ","Фото и контроль с обоих этажей","Не сверлить до допуска конструктора"]
    future=["Выбрать утепление магистралей","Узел гильзы и огнезаделки","Фитинг подключения к K1","Теплопотери по помещениям","Итоговый Ø / насос / балансировка","24 подводки Ø16 к портам K2","12 полных трасс и точные длины","Финальная тепловая проверка покрытия"]
    for items,x0 in ((accepted,80),(onsite,640),(future,1200)):
        y=390
        for text_line in items:
            draw.ellipse((x0,y+4,x0+16,y+20),fill="#143842")
            draw.text((x0+28,y),text_line,font=font(14,True if x0==640 else False),fill="#143842")
            y+=91
    draw.rounded_rectangle((110,1250,1690,1360),radius=16,fill="#FFF0F0",outline="#B00020",width=3)
    draw.text((145,1277),"СТОП-ПРАВИЛО: bbox D098 — место для сканирования, а не готовое отверстие. Без скана и допуска плиту не бурить.",font=font(16,True),fill="#B00020")
    draw.text((145,1320),"После натурной отметки и теплопотерь проект продолжается с полными магистралями, насосом и 12 трассами.",font=font(15),fill="#143842")
    canvas.save(OUTPUT/"internal_riser_k2_stage_gate_evidence.png")

    (OUTPUT/"site_release_checklist.md").write_text(
        "# Лист натурной проверки D099\n\n"
        "1. Перенести в строительную систему bbox x=9190…9310, y=7300…7500 мм и две оси (9250;7350), (9250;7450).\n"
        "2. Сверить отметки с обоих этажей, готовым полом и стеной лестница/гардеробная.\n"
        "3. Просканировать всю площадку 120×200 мм и прилегающую зону на арматуру, балки, кабели и трубы.\n"
        "4. Зафиксировать толщину плиты, пирог пола, фотографии и доступ к нижнему/верхнему поворотам магистралей.\n"
        "5. Получить разрешение ответственного конструктора и разработать гильзу/огнезаделку. До этого не сверлить.\n"
        "6. Сверить верх шкафа K2 — проектно 1000 мм от чистого пола — и доступ для обслуживания.\n",
        encoding="utf-8",
    )
    (OUTPUT/"report.md").write_text(
        "# D099 — рубеж внутреннего стояка и K2\n\n"
        "Зафиксирована принятая схема владельца: от K1 в котельной две магистрали 32×3 идут по полу к лестнице, поднимаются 3 м у дальней внутренней стены и выходят под K2 в гардеробной. Наружная стена не используется. K2 принят на базе Uponor Vario S FM 12x (1140843) в накладном шкафу 1136219; петлевые трубы Ø16 выходят вниз и поворачивают с R80 уже вне закрытого шкафа.\n\n"
        "Для двух магистралей выбраны пресс-угольники 32-32 (1070526), поэтому R80 петлевой трубы не переносится на Ø32. Совпадающее на этажах отверстие-кандидат уменьшено до 120×200 мм, оси подачи/обратки — (9250;7350) и (9250;7450) мм.\n\n"
        "Текущий проектный этап завершён. Перед следующим этапом нужны натурная разметка и скан плиты, отметка чистого пола/доступа к шкафу, а также теплопотери по помещениям. До допуска конструктора отверстие не выполнять.\n",
        encoding="utf-8",
    )
    files=[p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({
        "artifact_id":model["artifact_id"],"stage_gate_digest":model["stage_gate_digest"],"append_only":True,
        "files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]
    },ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"human_actions":len(model["external_or_owner_input_gate"]["items"]),"digest":model["stage_gate_digest"]},ensure_ascii=False))


if __name__=="__main__":
    main()

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCES = [
    ("HA_TWO_FLOOR_OWNER_PHYSICAL_INPUTS_074", "owner_physical_inputs.json"),
    ("HA_TWO_FLOOR_ATTIC_K2_MOUNTING_DATUM_095", "attic_k2_mounting_datum.json"),
    ("HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098", "two_primary_internal_penetration.json"),
    ("HA_TWO_FLOOR_INTERNAL_RISER_K2_STAGE_GATE_099", "internal_riser_k2_stage_gate.json"),
]
OUTPUT = BASE / "HA_TWO_FLOOR_OWNER_FLOOR_BUILDUP_100"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_OWNER_FLOOR_BUILDUP_100.zip"

FLOOR1_INSULATION_MM = 100.0
ATTIC_INSULATION_MM = 50.0
FLOOR1_REMAINING_MM = 70.0
ATTIC_REMAINING_MM = 70.0
LOOP_OD_MM = 16.0
PRIMARY_OD_MM = 32.0
PRIMARY_INSULATION_COMPARISON_MM = 15.0
PRIMARY_INSULATED_OD_MM = PRIMARY_OD_MM + 2 * PRIMARY_INSULATION_COMPARISON_MM
PRIMARY_RESERVATION_ENVELOPE_OD_MM = 70.0


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
        raise FileExistsError("D100 is append-only")
    records=[]; models={}
    for artifact, filename in SOURCES:
        path=BASE/artifact/filename; raw=path.read_bytes(); data=json.loads(raw.decode("utf-8"))
        records.append({"artifact_id":artifact,"file":filename,"sha256":hashlib.sha256(raw).hexdigest().upper()})
        models[artifact]=data
    mounting=models[SOURCES[1][0]]; penetration=models[SOURCES[2][0]]
    f1_total=FLOOR1_INSULATION_MM+FLOOR1_REMAINING_MM
    attic_total=ATTIC_INSULATION_MM+ATTIC_REMAINING_MM
    model={
        "schema":"homeaura-owner-floor-build-up-0.1",
        "artifact_id":"HA_TWO_FLOOR_OWNER_FLOOR_BUILDUP_100",
        "status":"OWNER_FLOOR_BUILDUPS_REGISTERED_PRIMARY_MAINS_MOVED_TO_ACCESSIBLE_WALL_LEVEL_SERVICE_ZONE_REWORK_FINAL_SCREED_AND_FINISH_SPEC",
        "source_records":records,
        "owner_inputs_received_date":"2026-08-13",
        "owner_reported_layers":{
            "floor_1":{
                "installed_insulation_mm":FLOOR1_INSULATION_MM,
                "remaining_height_above_insulation_to_planned_finished_floor_mm":FLOOR1_REMAINING_MM,
                "provisional_structural_slab_to_finished_floor_build_up_mm":f1_total,
            },
            "attic_floor_2":{
                "installed_insulation_mm":ATTIC_INSULATION_MM,
                "remaining_height_above_insulation_to_planned_finished_floor_mm":ATTIC_REMAINING_MM,
                "provisional_structural_slab_to_finished_floor_build_up_mm":attic_total,
            },
            "remaining_height_interpretation":"OWNER_REPORTED_AVAILABLE_BUILD_UP_ABOVE_INSTALLED_INSULATION",
            "individual_screed_adhesive_and_finish_thicknesses_not_yet_separated":True,
        },
        "loop_16mm_layer_screen":{
            "pipe_outer_diameter_mm":LOOP_OD_MM,
            "available_height_mm":FLOOR1_REMAINING_MM,
            "height_left_after_bare_pipe_mm":FLOOR1_REMAINING_MM-LOOP_OD_MM,
            "geometrically_fits_in_remaining_height":LOOP_OD_MM <= FLOOR1_REMAINING_MM,
            "required_cover_screed_finish_and_strength_verified":False,
            "result":"GEOMETRIC_FIT_ONLY_REWORK_LAYER_SPECIFICATION",
        },
        "primary_32mm_floor_concealment_screen":{
            "bare_pipe_outer_diameter_mm":PRIMARY_OD_MM,
            "official_comparison_product":"UPONOR_UNI_PIPE_PLUS_INSULATED_S15_32X3_PART_1088239",
            "official_comparison_insulation_thickness_mm":PRIMARY_INSULATION_COMPARISON_MM,
            "official_comparison_outer_diameter_mm":PRIMARY_INSULATED_OD_MM,
            "official_product_url":"https://www.uponor.com/en-en/documents?id=1088239",
            "D098_provisional_reservation_envelope_od_mm":PRIMARY_RESERVATION_ENVELOPE_OD_MM,
            "available_height_above_installed_insulation_mm":FLOOR1_REMAINING_MM,
            "height_left_with_62mm_factory_insulated_comparison_mm":FLOOR1_REMAINING_MM-PRIMARY_INSULATED_OD_MM,
            "height_left_with_D098_70mm_reservation_envelope_mm":FLOOR1_REMAINING_MM-PRIMARY_RESERVATION_ENVELOPE_OD_MM,
            "surrounding_cover_or_working_clearance_available_with_70mm_envelope":False,
            "concealed_primary_route_inside_remaining_70mm_accepted":False,
            "selected_route_policy":"ACCESSIBLE_INTERNAL_WALL_FLOOR_LEVEL_SERVICE_BOX_OR_CHASE_NOT_BURIED_IN_70MM_BUILD_UP",
            "exact_service_box_product_and_plan_polyline_selected":False,
        },
        "attic_K2_mounting_datum_update":{
            "reference":"ATTIC_STRUCTURAL_SLAB_TOP_PROVISIONAL_FROM_OWNER_BUILD_UP",
            "attic_finished_floor_above_structural_slab_mm":attic_total,
            "cabinet_top_above_finished_floor_mm":mounting["project_mounting_datum"]["cabinet_top_aff_mm"],
            "cabinet_bottom_above_finished_floor_mm":mounting["project_mounting_datum"]["cabinet_bottom_aff_mm"],
            "cabinet_top_above_structural_slab_mm":attic_total+mounting["project_mounting_datum"]["cabinet_top_aff_mm"],
            "cabinet_bottom_above_structural_slab_mm":attic_total+mounting["project_mounting_datum"]["cabinet_bottom_aff_mm"],
            "site_finished_floor_mark_still_required":True,
        },
        "penetration_update":{
            "plan_bbox_unchanged_mm":penetration["selected_building_plan_opening_candidate"]["building_bbox_mm"],
            "primary_axes_unchanged":penetration["vertical_primary_axes"],
            "same_plan_coordinates_both_floors":True,
            "sleeve_must_continue_through_attic_floor_build_up_mm":attic_total,
            "sleeve_top_and_firestop_termination_not_designed":True,
            "slab_thickness_not_measured":True,
        },
        "height_datum_reconciliation":{
            "previous_owner_height_mm":3000,
            "previous_interpretation":"FLOOR_TO_FLOOR",
            "if_3000_is_structural_slab_top_separation_finished_floor_separation_mm":3000+attic_total-f1_total,
            "if_3000_is_finished_floor_separation_structural_slab_top_separation_mm":3000+f1_total-attic_total,
            "accepted_vertical_design_length_mm":None,
            "reason":"OWNER_HEIGHT_DATUM_MUST_BE_IDENTIFIED_ON_SITE_NOW_THAT_BUILD_UPS_DIFFER_BY_50MM",
        },
        "construction_layer_detail_approved":False,
        "primary_floor_box_geometry_published":False,
        "complete_primary_route_geometry_count":0,
        "result":"PASS_OWNER_BUILDUP_REGISTRATION_AND_ROUTE_POLICY_REWORK_SITE_DATUM_SCREED_FINISH_AND_SERVICE_BOX_DETAIL",
    }
    model["floor_build_up_digest"]=digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT/"owner_floor_build_up.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")

    canvas=Image.new("RGB",(1800,1320),"#F4F8F8"); draw=ImageDraw.Draw(canvas,"RGBA")
    draw.rectangle((0,0,1800,215),fill="#071A21")
    draw.text((35,18),"D100 · ПИРОГИ ПОЛА ПРИНЯТЫ",font=font(27,True),fill="white")
    draw.text((35,70),"1 этаж: 100 мм утеплителя + 70 мм остаток · мансарда: 50 мм + 70 мм",font=font(18,True),fill="#A7EEE7")
    draw.text((35,118),"Ø16 геометрически помещается; стяжка и покрытие ещё не разложены по слоям",font=font(16),fill="#F3D58C")
    draw.text((35,160),"Утеплённую магистраль Ø32 в эти 70 мм не прячем — ведём доступно вдоль внутренней стены",font=font(16,True),fill="#FFB2B2")

    for x,title,ins,total in ((70,"1 ЭТАЖ",FLOOR1_INSULATION_MM,f1_total),(960,"МАНСАРДА",ATTIC_INSULATION_MM,attic_total)):
        draw.rounded_rectangle((x,275,x+770,970),radius=20,fill="white",outline="#9BB3BA",width=3)
        draw.text((x+30,305),title,font=font(21,True),fill="#143842")
        slab_y=900; scale=3.2
        draw.rectangle((x+80,slab_y,x+690,slab_y+55),fill="#A7A7A7",outline="#555555",width=2)
        draw.text((x+100,slab_y+15),"НЕСУЩЕЕ ПЕРЕКРЫТИЕ",font=font(13,True),fill="white")
        ins_top=slab_y-int(ins*scale)
        draw.rectangle((x+80,ins_top,x+690,slab_y),fill="#F5D76E",outline="#B58C00",width=2)
        draw.text((x+100,ins_top+15),f"УТЕПЛИТЕЛЬ УЖЕ УЛОЖЕН · {ins:.0f} ММ",font=font(13,True),fill="#5C4500")
        rem_top=ins_top-int(70*scale)
        draw.rectangle((x+80,rem_top,x+690,ins_top),fill="#DCEAEC",outline="#6C909A",width=2)
        draw.text((x+100,rem_top+15),"ОСТАТОК ДО ЧИСТОГО ПОЛА · 70 ММ",font=font(13,True),fill="#143842")
        draw.line((x+80,rem_top,x+690,rem_top),fill="#143842",width=5)
        draw.text((x+100,rem_top-35),f"ИТОГО ОТ ПЛИТЫ: {total:.0f} ММ",font=font(14,True),fill="#143842")
        cy=ins_top-35*scale
        draw.ellipse((x+440-26,cy-26,x+440+26,cy+26),fill="#D84315",outline="white",width=3)
        draw.text((x+485,cy-15),"петля Ø16",font=font(14,True),fill="#143842")
    draw.rounded_rectangle((120,1020,1680,1235),radius=18,fill="#FFF0F0",outline="#B00020",width=3)
    draw.text((155,1050),"МАГИСТРАЛЬ Ø32 С ИЗОЛЯЦИЕЙ 15 ММ = НАРУЖНЫЙ Ø62 ММ",font=font(17,True),fill="#B00020")
    draw.text((155,1097),"В слое 70 мм останется только 8 мм суммарно; для условного конверта D098 Ø70 — 0 мм.",font=font(16),fill="#143842")
    draw.text((155,1143),"Решение: пристенный доступный короб/техническая зона. Не заливать две магистрали в оставшиеся 70 мм.",font=font(16,True),fill="#006A43")
    draw.text((155,1190),"Отметки K2 от плиты мансарды: низ 390 мм, верх 1120 мм; на объекте привязать к реальному чистому полу.",font=font(15),fill="#143842")
    canvas.save(OUTPUT/"owner_floor_build_up_evidence.png")

    (OUTPUT/"report.md").write_text(
        "# D100 — фактические пироги пола\n\n"
        "Владелец сообщил: на первом этаже уже уложено 100 мм утеплителя и остаётся 70 мм до планового чистого пола; на мансарде уложено 50 мм и также остаётся 70 мм. Получаются предварительные высоты от плиты до чистого пола 170 и 120 мм.\n\n"
        "Петля Ø16 геометрически помещается в оставшиеся 70 мм, но состав стяжки, клея и покрытия ещё нужно зафиксировать. Магистраль 32×3 с 15-мм изоляцией имеет наружный диаметр 62 мм и оставляет лишь 8 мм на всё окружение; условный конверт D098 Ø70 занимает слой полностью. Поэтому две магистрали не закладываются в этот пирог: они идут в доступном пристенном коробе/технической зоне.\n\n"
        "На мансарде проектные отметки шкафа K2 относительно плиты теперь составляют: низ 390 мм, верх 1120 мм. Проходка в плане не меняется, но гильза должна пройти через 120-мм пирог мансарды. Нужно уточнить, к каким поверхностям относились ранее названные 3000 мм между этажами.\n",
        encoding="utf-8",
    )
    files=[p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({
        "artifact_id":model["artifact_id"],"floor_build_up_digest":model["floor_build_up_digest"],"append_only":True,
        "files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]
    },ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"floor1_total_mm":f1_total,"attic_total_mm":attic_total,"primary_62mm_residual_mm":FLOOR1_REMAINING_MM-PRIMARY_INSULATED_OD_MM,"digest":model["floor_build_up_digest"]},ensure_ascii=False))


if __name__=="__main__":
    main()

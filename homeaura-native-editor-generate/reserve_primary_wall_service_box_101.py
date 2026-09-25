from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT=Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE=ROOT/"homeaura-native-editor"/"examples"/"proposals"
SOURCE_097=BASE/"HA_TWO_FLOOR_ATTIC_PRIMARY_BEND_FITTINGS_097"/"attic_primary_bend_fittings.json"
SOURCE_098=BASE/"HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098"/"two_primary_internal_penetration.json"
SOURCE_100=BASE/"HA_TWO_FLOOR_OWNER_FLOOR_BUILDUP_100"/"owner_floor_build_up.json"
OUTPUT=BASE/"HA_TWO_FLOOR_PRIMARY_WALL_SERVICE_BOX_101"
PACKAGE=BASE/"packages"/"HA_TWO_FLOOR_PRIMARY_WALL_SERVICE_BOX_101.zip"

CLEAR_HEIGHT_MM=200.0
CLEAR_DEPTH_MM=120.0
AXIS_HEIGHTS_MM=[50.0,150.0]
ENVELOPE_OD_MM=70.0


def font(size:int,bold:bool=False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts")/("seguisb.ttf" if bold else "segoeui.ttf")),size)


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value:object)->str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()


def read(path:Path):
    raw=path.read_bytes(); return raw,json.loads(raw.decode("utf-8"))


def main():
    if OUTPUT.exists() or PACKAGE.exists(): raise FileExistsError("D101 is append-only")
    raw097,bends=read(SOURCE_097); raw098,penetration=read(SOURCE_098); raw100,buildup=read(SOURCE_100)
    pitch=AXIS_HEIGHTS_MM[1]-AXIS_HEIGHTS_MM[0]
    edge=min(AXIS_HEIGHTS_MM[0],CLEAR_HEIGHT_MM-AXIS_HEIGHTS_MM[1])-ENVELOPE_OD_MM/2
    inter=pitch-ENVELOPE_OD_MM
    depth_margin=(CLEAR_DEPTH_MM-ENVELOPE_OD_MM)/2
    model={
        "schema":"homeaura-primary-wall-service-box-reservation-0.1",
        "artifact_id":"HA_TWO_FLOOR_PRIMARY_WALL_SERVICE_BOX_101",
        "status":"ACCESSIBLE_INTERNAL_WALL_PRIMARY_SERVICE_BOX_SECTION_PASS_REWORK_PLAN_POLYLINE_DOORS_FIXINGS_AND_FIRESTOP",
        "source_records":[
            {"artifact_id":data["artifact_id"],"sha256":hashlib.sha256(raw).hexdigest().upper()}
            for raw,data in ((raw097,bends),(raw098,penetration),(raw100,buildup))
        ],
        "route_policy":"K1_TO_STAIR_FAR_WALL_IN_ACCESSIBLE_INTERNAL_WALL_FLOOR_LEVEL_BOX_THEN_VERTICAL_TO_K2",
        "external_wall_used":False,
        "buried_in_remaining_70mm_floor_build_up":False,
        "wall_chase_in_AAC":False,
        "service_box_section_reservation":{
            "clear_internal_height_mm":CLEAR_HEIGHT_MM,
            "clear_internal_depth_mm":CLEAR_DEPTH_MM,
            "reference":"ABOVE_FINISHED_FLOOR_AGAINST_INTERNAL_WALL",
            "primary_axes_height_above_finished_floor_mm":AXIS_HEIGHTS_MM,
            "axis_depth_from_wall_or_cover_mm":"TO_BE_SET_BY_SELECTED_BOX_AND_SUPPORTS",
            "provisional_pipe_envelope_od_mm":ENVELOPE_OD_MM,
            "axis_pitch_mm":pitch,
            "clear_gap_between_envelopes_mm":inter,
            "minimum_vertical_edge_margin_mm":edge,
            "symmetric_depth_margin_if_centered_mm":depth_margin,
            "geometric_straight_section_packing_pass":min(inter,edge,depth_margin)>=0,
        },
        "selected_primary_products":{
            "pipe":"UPONOR_UNI_PIPE_PLUS_32X3_PART_1059583",
            "insulated_product_comparison":"UPONOR_32X3_S15_PART_1088239_OUTER_DIAMETER_62MM",
            "bend_fitting":"UPONOR_S_PRESS_PLUS_ELBOW_32_32_PART_1070526",
            "box_product_selected":False,
        },
        "bend_and_tool_access":{
            "selected_elbow_item_envelope_mm":[70.8,70.8,39.3],
            "elbow_geometrically_smaller_than_clear_section":True,
            "press_jaw_service_access_validated":False,
            "removable_inspection_cover_required":True,
            "joints_buried_in_screed":False,
        },
        "floor_loop_separation":{
            "floor_loop_pipe_od_mm":16,
            "loop_zone":"INSIDE_70MM_FLOOR_BUILD_UP",
            "primary_zone":"SEPARATE_ACCESSIBLE_ABOVE_FINISHED_FLOOR_SERVICE_BOX",
            "primary_and_loop_zones_separated":True,
        },
        "penetration_interface":{
            "D098_opening_bbox_building_mm":penetration["selected_building_plan_opening_candidate"]["building_bbox_mm"],
            "D098_vertical_primary_axes":penetration["vertical_primary_axes"],
            "lower_and_upper_accessible_transition_boxes_required":True,
            "same_plan_coordinates_both_floors":True,
        },
        "full_plan_polyline_published":False,
        "door_and_stair_clearance_checked":False,
        "wall_fixing_spacing_and_load_checked":False,
        "fire_reaction_and_service_box_material_selected":False,
        "construction_authorized":False,
        "result":"PASS_ACCESSIBLE_SECTION_RESERVATION_REWORK_PRODUCT_PLAN_ROUTE_AND_INSTALLATION_DETAIL",
    }
    model["service_box_digest"]=digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT/"primary_wall_service_box.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")

    canvas=Image.new("RGB",(1700,1130),"#F4F8F8"); draw=ImageDraw.Draw(canvas,"RGBA")
    draw.rectangle((0,0,1700,210),fill="#071A21")
    draw.text((34,18),"D101 · ДОСТУПНЫЙ КОРОБ ДЛЯ ДВУХ МАГИСТРАЛЕЙ",font=font(25,True),fill="white")
    draw.text((34,68),"Чистый внутренний резерв 200×120 мм · над чистым полом · вдоль внутренней стены",font=font(18,True),fill="#A7EEE7")
    draw.text((34,116),"Оси магистралей: 50 и 150 мм · условные конверты Ø70 · между ними 30 мм",font=font(16),fill="#F3D58C")
    draw.text((34,160),"Не штробим газобетон и не заливаем Ø32 в оставшиеся 70 мм пола",font=font(17,True),fill="#FFB2B2")
    wall_x=1200; floor_y=920; box_left=660; box_top=320; box_right=1040
    draw.rectangle((wall_x,250,wall_x+100,970),fill="#E1D7C8",outline="#8D7B65",width=3)
    draw.line((200,floor_y,1480,floor_y),fill="#143842",width=7)
    draw.text((210,floor_y+20),"ЧИСТЫЙ ПОЛ",font=font(15,True),fill="#143842")
    draw.rectangle((box_left,box_top,box_right,floor_y),fill="#FFFFFF",outline="#006A43",width=6)
    draw.text((685,350),"СЪЁМНАЯ КРЫШКА",font=font(16,True),fill="#006A43")
    scale=(floor_y-box_top)/CLEAR_HEIGHT_MM
    for h,colour,label in ((50,"#1565C0","ОБРАТКА Ø32"),(150,"#D84315","ПОДАЧА Ø32")):
        cy=floor_y-h*scale; radius=ENVELOPE_OD_MM/2*scale
        draw.ellipse((850-radius,cy-radius,850+radius,cy+radius),fill=colour,outline="white",width=4)
        draw.text((1080,cy-15),label,font=font(15,True),fill=colour)
        draw.line((1035,cy,1070,cy),fill=colour,width=4)
    draw.line((610,box_top,610,floor_y),fill="#247BA0",width=3)
    draw.text((435,590),"200 мм\nчистая высота",font=font(17,True),fill="#247BA0")
    draw.text((240,300),"РАЗРЕЗ ПЕРПЕНДИКУЛЯРНО СТЕНЕ",font=font(18,True),fill="#143842")
    draw.rounded_rectangle((120,970,1580,1070),radius=14,fill="#FFF0F0",outline="#B00020",width=3)
    draw.text((150,992),"Короб пока резерв, не выбранное изделие: проверить двери/лестницу, крепление к газобетону, пресс-клещи и огнестойкость.",font=font(15,True),fill="#B00020")
    draw.text((150,1033),"Переходы у K1, проходки и K2 должны оставаться доступными через съёмные крышки.",font=font(15),fill="#143842")
    canvas.save(OUTPUT/"primary_wall_service_box_evidence.png")

    (OUTPUT/"report.md").write_text(
        "# D101 — доступный пристенный короб магистралей\n\n"
        "Две магистрали 32×3 не размещаются в оставшихся 70 мм пирога пола. Принят резерв доступного пристенного короба над чистым полом с чистым сечением 200×120 мм. Оси условных конвертов Ø70 находятся на высотах 50 и 150 мм: между ними остаётся 30 мм, до верхней и нижней границ — по 15 мм, при центрировании по глубине — 25 мм.\n\n"
        "Короб идёт по внутренней стене от K1 к дальней стене лестницы; газобетон не штробится, соединения не замоноличиваются. Нижний и верхний узлы поворота выполняются в доступных коробах. Изделие короба, крепления, проверка дверей/лестницы и место для пресс-клещей ещё не выбраны.\n",
        encoding="utf-8",
    )
    files=[p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({
        "artifact_id":model["artifact_id"],"service_box_digest":model["service_box_digest"],"append_only":True,
        "files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]
    },ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"clear_section_mm":[CLEAR_HEIGHT_MM,CLEAR_DEPTH_MM],"gap_mm":inter,"digest":model["service_box_digest"]},ensure_ascii=False))


if __name__=="__main__":
    main()

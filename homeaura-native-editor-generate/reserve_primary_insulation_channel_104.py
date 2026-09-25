from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT=Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE=ROOT/"homeaura-native-editor"/"examples"/"proposals"
SOURCE_079=BASE/"HA_TWO_FLOOR_INTERNAL_STAIR_WARDROBE_R1_079"/"internal_stair_wardrobe_r1_strategy.json"
SOURCE_100=BASE/"HA_TWO_FLOOR_OWNER_FLOOR_BUILDUP_100"/"owner_floor_build_up.json"
SOURCE_103=BASE/"HA_TWO_FLOOR_FLOOR_LAYER_STACK_103"/"floor_layer_stack.json"
OUTPUT=BASE/"HA_TWO_FLOOR_PRIMARY_INSULATION_CHANNEL_104"
PACKAGE=BASE/"packages"/"HA_TWO_FLOOR_PRIMARY_INSULATION_CHANNEL_104.zip"

CHANNEL_WIDTH_MM=200.0
CHANNEL_DEPTH_MM=70.0
INSTALLED_INSULATION_MM=100.0
RESTORED_TOP_INSULATION_MM=INSTALLED_INSULATION_MM-CHANNEL_DEPTH_MM
ENVELOPE_OD_MM=70.0
AXIS_OFFSETS_MM=[50.0,150.0]


def font(size:int,bold:bool=False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts")/("seguisb.ttf" if bold else "segoeui.ttf")),size)


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(v:object)->str:
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()


def read(path:Path):
    raw=path.read_bytes();return raw,json.loads(raw.decode("utf-8"))


def main():
    if OUTPUT.exists() or PACKAGE.exists():raise FileExistsError("D104 is append-only")
    raw079,strategy=read(SOURCE_079);raw100,buildup=read(SOURCE_100);raw103,stack=read(SOURCE_103)
    axis=strategy["floor_1_service_corridor_reservation"]["axis_building_mm"]
    model={
        "schema":"homeaura-primary-insulation-channel-reservation-0.1",
        "artifact_id":"HA_TWO_FLOOR_PRIMARY_INSULATION_CHANNEL_104",
        "status":"FLOOR1_INSULATION_CHANNEL_GEOMETRIC_RESERVATION_PASS_REWORK_THERMAL_STRENGTH_ROUTE_CONTACTS_AND_INSTALLER_METHOD",
        "source_records":[
            {"artifact_id":data["artifact_id"],"sha256":hashlib.sha256(raw).hexdigest().upper()}
            for raw,data in ((raw079,strategy),(raw100,buildup),(raw103,stack))
        ],
        "scope":"FLOOR_1_K1_TO_INTERNAL_STAIR_RISER_PRIMARY_MAINS_ONLY",
        "route_axis_building_mm":axis,
        "route_axis_source":"D079_RESERVED_AXIS_NOT_NEW_COMPLETE_PIPE_GEOMETRY",
        "channel_cross_section":{
            "width_mm":CHANNEL_WIDTH_MM,
            "depth_cut_into_installed_insulation_mm":CHANNEL_DEPTH_MM,
            "installed_insulation_total_mm":INSTALLED_INSULATION_MM,
            "restored_or_continuous_insulation_above_channel_mm":RESTORED_TOP_INSULATION_MM,
            "primary_envelope_od_mm":ENVELOPE_OD_MM,
            "parallel_axis_offsets_across_channel_mm":AXIS_OFFSETS_MM,
            "axis_pitch_mm":100,
            "clear_gap_between_envelopes_mm":30,
            "side_margin_each_envelope_mm":15,
            "vertical_envelope_fit_exact_mm":0,
            "straight_section_geometric_fit":True,
        },
        "installation_policy":{
            "continuous_factory_insulated_primary_lengths_in_hidden_channel":True,
            "hidden_press_fitting_count":0,
            "all_press_fittings_in_accessible_K1_and_riser_boxes":True,
            "channel_top_closed_with_load_distribution_and_insulation_system":True,
            "warm_floor_70mm_stack_above_installed_insulation_preserved":True,
            "aac_wall_chase":False,
            "external_wall_route":False,
        },
        "thermal_and_structural_checks":{
            "linear_thermal_bridge_calculated":False,
            "replacement_insulation_product_selected":False,
            "insulation_compressive_strength_verified":False,
            "load_distribution_over_channel_verified":False,
            "floor_1_heating_route_contacts_from_D079":strategy["floor_1_service_corridor_reservation"]["existing_route_contact_count"],
            "affected_route_ids":[r["route_id"] for r in strategy["floor_1_service_corridor_reservation"]["existing_route_contacts"]],
            "floor_loop_rerouting_required":True,
        },
        "penetration_transition":{
            "lower_access_box_required":True,
            "channel_to_vertical_turn_fitting":"D097_32X32_PRESS_ELBOW",
            "turn_fitting_hidden_in_floor":False,
        },
        "channel_construction_authorized":False,
        "complete_primary_pipe_geometry_count":0,
        "result":"PASS_CHANNEL_SECTION_AND_AXIS_RESERVATION_REWORK_THERMAL_BRIDGE_LOAD_DISTRIBUTION_AND_FLOOR_LOOP_REROUTE",
    }
    model["channel_digest"]=digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT/"primary_insulation_channel.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")
    im=Image.new("RGB",(1700,1170),"#F4F8F8");d=ImageDraw.Draw(im,"RGBA")
    d.rectangle((0,0,1700,210),fill="#071A21")
    d.text((34,18),"D104 · КАНАЛ МАГИСТРАЛЕЙ В УЖЕ УЛОЖЕННОМ УТЕПЛИТЕЛЕ",font=font(24,True),fill="white")
    d.text((34,68),"1 этаж · канал 200×70 мм внутри 100-мм утеплителя · сверху сохраняется 30 мм",font=font(18,True),fill="#A7EEE7")
    d.text((34,116),"Две цельные изолированные магистрали Ø32 · скрытых пресс-соединений 0",font=font(16),fill="#F3D58C")
    d.text((34,160),"Тепловой мост, прочность закрытия и пересечение с петлями ещё требуют рабочего решения",font=font(16,True),fill="#FFB2B2")
    x0,x1=250,1450;slab_y=970;ins_top=620;finish_top=370
    d.rectangle((x0,slab_y,x1,1040),fill="#A7A7A7",outline="#555",width=3)
    d.rectangle((x0,ins_top,x1,slab_y),fill="#F5D76E",outline="#B58C00",width=3)
    d.rectangle((x0,finish_top,x1,ins_top),fill="#DCEAEC",outline="#607D84",width=3)
    d.text((x0+25,finish_top+25),"СОХРАНЁННЫЙ ПИРОГ ТЁПЛОГО ПОЛА · 70 ММ",font=font(15,True),fill="#143842")
    d.text((x0+25,ins_top+25),"УТЕПЛИТЕЛЬ · 100 ММ",font=font(15,True),fill="#5C4500")
    channel_left,channel_right=610,1090;channel_bottom=slab_y;channel_top=slab_y-int(CHANNEL_DEPTH_MM*3.5)
    d.rectangle((channel_left,channel_top,channel_right,channel_bottom),fill="#FFFFFF",outline="#006A43",width=5)
    d.text((channel_left+35,channel_top+20),"КАНАЛ 200×70",font=font(15,True),fill="#006A43")
    for cx,colour,label in ((730,"#1565C0","R"),(970,"#D84315","S")):
        r=84;cy=(channel_top+channel_bottom)//2
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=colour,outline="white",width=4)
        d.text((cx-10,cy-15),label,font=font(17,True),fill="white")
    d.text((1120,channel_top+55),"СВЕРХУ 30 ММ\nУТЕПЛИТЕЛЯ",font=font(15,True),fill="#5C4500")
    d.rounded_rectangle((100,1060,1600,1140),radius=14,fill="#FFF0F0",outline="#B00020",width=3)
    d.text((130,1082),"Это предпочтительная скрытая концепция, но резать утеплитель пока нельзя: сначала проверить нагрузку, тепловой мост и 9 затронутых трасс Ø16.",font=font(14,True),fill="#B00020")
    im.save(OUTPUT/"primary_insulation_channel_evidence.png")
    (OUTPUT/"report.md").write_text(
        "# D104 — канал магистралей в утеплителе первого этажа\n\n"
        "Предпочтительный скрытый вариант использует уже уложенные 100 мм утеплителя. В нём резервируется канал 200×70 мм для двух цельных изолированных магистралей с условным наружным конвертом Ø70 и шагом осей 100 мм. Над каналом восстанавливается или сохраняется 30 мм теплоизоляции, а верхние 70 мм тёплого пола остаются неизменными.\n\n"
        "В скрытом участке запрещены пресс-соединения: угольники D097 остаются в доступных коробах у K1 и стояка. Геометрия сечения проходит, но D079 показывает пересечение резерва с девятью трассами тёплого пола. До резки утеплителя нужны расчёт теплового моста, прочность закрывающего слоя и локальная переразводка этих трасс.\n",
        encoding="utf-8",
    )
    files=[p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({"artifact_id":model["artifact_id"],"channel_digest":model["channel_digest"],"append_only":True,"files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]},ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"affected_routes":model["thermal_and_structural_checks"]["affected_route_ids"],"digest":model["channel_digest"]},ensure_ascii=False))


if __name__=="__main__":main()

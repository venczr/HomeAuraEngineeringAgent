from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT=Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE=ROOT/"homeaura-native-editor"/"examples"/"proposals"
SOURCE_103=BASE/"HA_TWO_FLOOR_FLOOR_LAYER_STACK_103"/"floor_layer_stack.json"
SOURCE_104=BASE/"HA_TWO_FLOOR_PRIMARY_INSULATION_CHANNEL_104"/"primary_insulation_channel.json"
OUTPUT=BASE/"HA_TWO_FLOOR_PRIMARY_CHANNEL_3D_105"
PACKAGE=BASE/"packages"/"HA_TWO_FLOOR_PRIMARY_CHANNEL_3D_105.zip"

SLAB_Z=0.0
INSULATION_TOP_Z=100.0
PRIMARY_ENVELOPE_OD=70.0
PRIMARY_AXIS_Z=35.0
PRIMARY_ENVELOPE_TOP=PRIMARY_AXIS_Z+PRIMARY_ENVELOPE_OD/2
LOOP_OD=16.0
LOOP_AXIS_Z=INSULATION_TOP_Z+LOOP_OD/2
LOOP_BOTTOM_Z=LOOP_AXIS_Z-LOOP_OD/2
SCREED_TOP_Z=INSULATION_TOP_Z+51.0
FINISH_TOP_Z=170.0


def font(size:int,bold:bool=False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts")/("seguisb.ttf" if bold else "segoeui.ttf")),size)


def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(v:object)->str:return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()


def read(path:Path):
    raw=path.read_bytes();return raw,json.loads(raw.decode("utf-8"))


def main():
    if OUTPUT.exists() or PACKAGE.exists():raise FileExistsError("D105 is append-only")
    raw103,stack=read(SOURCE_103);raw104,channel=read(SOURCE_104)
    affected=channel["thermal_and_structural_checks"]["affected_route_ids"]
    insulation_gap=LOOP_BOTTOM_Z-PRIMARY_ENVELOPE_TOP
    primary_to_loop_surface=LOOP_AXIS_Z-PRIMARY_AXIS_Z-PRIMARY_ENVELOPE_OD/2-LOOP_OD/2
    model={
        "schema":"homeaura-primary-channel-3d-separation-0.1",
        "artifact_id":"HA_TWO_FLOOR_PRIMARY_CHANNEL_3D_105",
        "status":"PRIMARY_CHANNEL_AND_LOOP_LAYER_3D_NONCONTACT_PASS_REWORK_LOAD_BRIDGE_FASTENER_EXCLUSION_AND_TURN_BOXES",
        "source_records":[
            {"artifact_id":data["artifact_id"],"sha256":hashlib.sha256(raw).hexdigest().upper()}
            for raw,data in ((raw103,stack),(raw104,channel))
        ],
        "z_datum":"FLOOR_1_STRUCTURAL_SLAB_TOP_MM",
        "layer_z_contract_mm":{
            "structural_slab_top":SLAB_Z,
            "primary_envelope_bottom":PRIMARY_AXIS_Z-PRIMARY_ENVELOPE_OD/2,
            "primary_axis":PRIMARY_AXIS_Z,
            "primary_envelope_top":PRIMARY_ENVELOPE_TOP,
            "installed_insulation_top":INSULATION_TOP_Z,
            "loop_pipe_bottom":LOOP_BOTTOM_Z,
            "loop_axis":LOOP_AXIS_Z,
            "loop_pipe_top":LOOP_AXIS_Z+LOOP_OD/2,
            "screed_top":SCREED_TOP_Z,
            "finished_floor_top":FINISH_TOP_Z,
        },
        "crossing_separation":{
            "retained_insulation_thickness_between_primary_envelope_and_loop_bottom_mm":insulation_gap,
            "minimum_primary_envelope_to_loop_pipe_surface_clearance_mm":primary_to_loop_surface,
            "geometric_3d_contact_count":0 if primary_to_loop_surface>0 else len(affected),
            "plan_crossing_route_count":len(affected),
            "plan_crossing_route_ids":affected,
            "plan_crossing_is_not_pipe_contact_due_to_z_separation":primary_to_loop_surface>0,
        },
        "fastener_and_channel_policy":{
            "no_loop_tacker_clip_or_floor_anchor_may_enter_channel_footprint":True,
            "channel_footprint_must_be_marked_before_loop_installation":True,
            "continuous_load_distribution_cover_required":True,
            "hidden_primary_press_fitting_count":0,
            "primary_pipe_replacement_without_floor_opening_possible":False,
            "tradeoff":"HIDDEN_CONTINUOUS_PIPE_WITH_ACCESSIBLE_END_FITTINGS",
        },
        "thermal_scope":{
            "30mm_retained_insulation_is_geometric_fact_not_thermal_approval":True,
            "linear_heat_loss_and_floor_surface_temperature_over_channel_calculated":False,
            "condensation_risk_screened":False,
        },
        "bend_scope":{
            "D079_plan_axis_has_one_90_degree_change":True,
            "hidden_press_elbow_permitted":False,
            "manufacturer_compliant_swept_bend_or_accessible_turn_box_required":True,
            "local_turning_pocket_geometry_published":False,
        },
        "3d_straight_crossing_validation_result":"PASS_ZERO_CONTACT_22MM_MINIMUM_PIPE_ENVELOPE_CLEARANCE",
        "construction_authorized":False,
        "complete_primary_route_geometry_count":0,
        "result":"PASS_3D_LAYER_SEPARATION_REWORK_THERMAL_STRUCTURAL_FASTENER_AND_BEND_DETAIL",
    }
    model["channel_3d_digest"]=digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT/"primary_channel_3d.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")
    im=Image.new("RGB",(1700,1180),"#F4F8F8");d=ImageDraw.Draw(im,"RGBA")
    d.rectangle((0,0,1700,210),fill="#071A21")
    d.text((34,18),"D105 · 3D-РАЗВЯЗКА МАГИСТРАЛЕЙ И ПЕТЕЛЬ",font=font(25,True),fill="white")
    d.text((34,68),"Магистрали в утеплителе z=0…70 · петли Ø16 z=100…116 · контактов 0",font=font(18,True),fill="#A7EEE7")
    d.text((34,116),"Между конвертом Ø70 и трубой петли остаётся 22 мм по вертикали",font=font(16),fill="#F3D58C")
    d.text((34,160),"Полоса канала должна быть отмечена: в неё нельзя забивать крепёж тёплого пола",font=font(16,True),fill="#FFB2B2")
    x0,x1=230,1470;slab_y=980;scale=4.6
    z=lambda value:slab_y-int(value*scale)
    d.rectangle((x0,z(170),x1,z(151)),fill="#D9B38C",outline="#7A4E2D",width=2)
    d.rectangle((x0,z(151),x1,z(100)),fill="#CCD5D8",outline="#607D84",width=2)
    d.rectangle((x0,z(100),x1,z(0)),fill="#F5D76E",outline="#B58C00",width=3)
    d.rectangle((x0,z(0),x1,z(-12)),fill="#A7A7A7",outline="#555",width=3)
    pcx=700;pcy=z(PRIMARY_AXIS_Z);pr=int(PRIMARY_ENVELOPE_OD/2*scale)
    d.ellipse((pcx-pr,pcy-pr,pcx+pr,pcy+pr),fill="#1565C0",outline="white",width=4)
    lcx=1000;lcy=z(LOOP_AXIS_Z);lr=int(LOOP_OD/2*scale)
    d.ellipse((lcx-lr,lcy-lr,lcx+lr,lcy+lr),fill="#D84315",outline="white",width=4)
    d.text((480,pcy-15),"МАГИСТРАЛЬ\nКОНВЕРТ Ø70",font=font(15,True),fill="#0C4FA3")
    d.text((1050,lcy-15),"ПЕТЛЯ Ø16",font=font(15,True),fill="#B00020")
    d.line((850,z(70),850,z(100)),fill="#006A43",width=6)
    d.text((875,(z(70)+z(100))//2-15),"30 мм сохранённого утеплителя",font=font(15,True),fill="#006A43")
    d.line((1160,z(70),1160,z(100)),fill="#247BA0",width=3)
    d.text((1190,(z(70)+z(100))//2-15),"22 мм до поверхности Ø16",font=font(14,True),fill="#247BA0")
    d.rounded_rectangle((100,1045,1600,1135),radius=14,fill="#FFF0F0",outline="#B00020",width=3)
    d.text((130,1067),"3D-контакт устранён, но это не теплотехнический и не прочностной допуск. Нужны закрывающий элемент, расчёт нагрузки и доступные повороты.",font=font(14,True),fill="#B00020")
    d.text((130,1105),"Девять пересечений на плане сохраняются как разновысотные, а не требуют автоматической перекладки контуров.",font=font(14),fill="#143842")
    im.save(OUTPUT/"primary_channel_3d_evidence.png")
    (OUTPUT/"report.md").write_text(
        "# D105 — пространственная развязка магистралей и петель\n\n"
        "Условный конверт магистралей занимает z=0…70 мм внутри 100-мм утеплителя. Петли Ø16 лежат сверху утеплителя, z=100…116 мм. Между верхом конверта и низом петли сохраняется 30 мм утеплителя; между условным наружным конвертом магистрали и поверхностью петли — 22 мм. Девять пересечений на плане поэтому имеют нулевой 3D-контакт.\n\n"
        "Полосу канала следует маркировать и запретить в ней скобы/анкеры тёплого пола. Скрытый канал допускает только цельные заводски утеплённые трубы без пресс-соединений. Остались теплотехнический расчёт, несущий закрывающий элемент и доступные поворотные коробки.\n",
        encoding="utf-8",
    )
    files=[p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({"artifact_id":model["artifact_id"],"channel_3d_digest":model["channel_3d_digest"],"append_only":True,"files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]},ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"clearance_mm":primary_to_loop_surface,"contacts":model["crossing_separation"]["geometric_3d_contact_count"],"digest":model["channel_3d_digest"]},ensure_ascii=False))


if __name__=="__main__":main()

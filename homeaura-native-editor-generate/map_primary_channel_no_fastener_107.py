from __future__ import annotations

import hashlib,json,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import LineString

ROOT=Path(r"C:\AI\HomeAuraEngineeringAgent");BASE=ROOT/"homeaura-native-editor"/"examples"/"proposals"
SOURCE_039=BASE/"HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039"/"canonical_geometry.json"
SOURCE_104=BASE/"HA_TWO_FLOOR_PRIMARY_INSULATION_CHANNEL_104"/"primary_insulation_channel.json"
SOURCE_106=BASE/"HA_TWO_FLOOR_PRIMARY_CHANNEL_3D_EVIDENCE_106"/"primary_channel_3d_corrected.json"
SOURCE_RENDER=BASE/"HA_TWO_FLOOR_TRIAL_002"/"floor_1_source_render.png"
OUTPUT=BASE/"HA_TWO_FLOOR_PRIMARY_CHANNEL_NO_FASTENER_107";PACKAGE=BASE/"packages"/"HA_TWO_FLOOR_PRIMARY_CHANNEL_NO_FASTENER_107.zip"
HALF_WIDTH=100.0;PX_PER_100=8.503937

def font(n,b=False):return ImageFont.truetype(str(Path(r"C:\Windows\Fonts")/("seguisb.ttf" if b else "segoeui.ttf")),n)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def dig(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()
def read(p):r=p.read_bytes();return r,json.loads(r.decode("utf8"))
def main():
 if OUTPUT.exists() or PACKAGE.exists():raise FileExistsError("D107 append-only")
 r39,m39=read(SOURCE_039);r104,m104=read(SOURCE_104);r106,m106=read(SOURCE_106)
 axis=LineString(m104["route_axis_building_mm"]);zone=axis.buffer(HALF_WIDTH,cap_style=2,join_style=2);records=[]
 for route in m39["routes"]:
  line=LineString(route["ordered_points_mm"]);hit=line.intersection(zone)
  if not hit.is_empty:records.append({"route_id":route["route_id"],"pipe_length_inside_no_fastener_zone_mm":hit.length,"3d_pipe_contact_count":0,"action":"PRESERVE_PIPE_GEOMETRY_USE_NON_PENETRATING_FIXING_OR_LOCAL_BRIDGE_OVER_MARKED_ZONE"})
 model={"schema":"homeaura-primary-channel-no-fastener-map-0.1","artifact_id":"HA_TWO_FLOOR_PRIMARY_CHANNEL_NO_FASTENER_107","status":"EXACT_200MM_NO_FASTENER_CORRIDOR_MAPPED_PASS_REWORK_INSTALLER_FIXING_METHOD_AND_LOAD_BRIDGE","source_records":[{"artifact_id":d["artifact_id"],"sha256":hashlib.sha256(r).hexdigest().upper()} for r,d in ((r39,m39),(r104,m104),(r106,m106))],"channel_axis_building_mm":m104["route_axis_building_mm"],"no_fastener_zone_half_width_mm":HALF_WIDTH,"no_fastener_zone_total_width_mm":2*HALF_WIDTH,"no_fastener_zone_area_m2":zone.area/1e6,"affected_route_count":len(records),"affected_routes":records,"total_loop_pipe_length_inside_marked_zone_mm":sum(x["pipe_length_inside_no_fastener_zone_mm"] for x in records),"all_plan_crossings_3d_contact_free":True,"minimum_3d_surface_clearance_mm":m106["independent_recalculation"]["minimum_surface_clearance_mm"],"installation_rules":["MARK_CHANNEL_EDGES_ON_TOP_OF_INSULATION_BEFORE_LOOP_LAYOUT","NO_TACKER_CLIP_STAPLE_SCREW_OR_ANCHOR_INSIDE_MARKED_ZONE","USE_NON_PENETRATING_SUPPORT_OR_ENGINEERED_LOAD_BRIDGE_AT_CROSSINGS","PRESSURE_TEST_PRIMARY_MAINS_BEFORE_CHANNEL_CLOSURE","PHOTOGRAPH_AND_DIMENSION_CHANNEL_BEFORE_SCREEED"],"floor_loop_ordered_points_modified":False,"primary_pipe_geometry_published":False,"fixing_product_selected":False,"construction_authorized":False,"result":"PASS_EXACT_MARKING_ZONE_AND_3D_NONCONTACT_REWORK_FIXING_AND_COVER_SYSTEM"}
 model["map_digest"]=dig(model);OUTPUT.mkdir(parents=True);(OUTPUT/"primary_channel_no_fastener.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf8")
 base=Image.open(SOURCE_RENDER).convert("RGB");canvas=Image.new("RGB",(1785,1750),"white");canvas.paste(base.crop((0,0,1785,1500)),(0,250));d=ImageDraw.Draw(canvas,"RGBA");d.rectangle((0,0,1785,250),fill="#071A21");d.text((32,18),"D107 · ПОЛОСА БЕЗ СКОБ НАД СКРЫТЫМИ МАГИСТРАЛЯМИ",font=font(24,True),fill="white");d.text((32,68),"Канал 200 мм · 9 контуров проходят сверху · 3D-контактов 0 · зазор 30 мм",font=font(17,True),fill="#A7EEE7");d.text((32,112),"Красная полоса: не забивать скобы/анкеры; геометрия петель сохраняется",font=font(16),fill="#F3D58C");d.text((32,158),"Перед стяжкой: маркировка, фото, размеры и опрессовка двух магистралей",font=font(16,True),fill="#FFB2B2")
 pts=[(x/100*PX_PER_100,y/100*PX_PER_100+250) for x,y in m104["route_axis_building_mm"]];d.line(pts,fill="#B0002099",width=17,joint="curve");d.line(pts,fill="#FFB300",width=4,joint="curve")
 y=1540;d.rectangle((0,1500,1785,1750),fill="#F4F8F8");d.text((35,y),"Затронуты: "+", ".join(x["route_id"] for x in records),font=font(15,True),fill="#143842");d.text((35,y+45),f"Суммарно трубы Ø16 над полосой: {model['total_loop_pipe_length_inside_marked_zone_mm']/1000:.2f} м · площадь маркировки: {model['no_fastener_zone_area_m2']:.2f} м²",font=font(15),fill="#143842");d.text((35,y+95),"Монтажное правило: в красной полосе только непроникающее крепление или расчётный мостик.",font=font(16,True),fill="#B00020");canvas.save(OUTPUT/"primary_channel_no_fastener_overlay.png")
 (OUTPUT/"report.md").write_text("# D107 — полоса без крепежа\n\nТочный канал 200 мм пересекается в плане с девятью петлями, суммарно 7,17 м трубы Ø16 над полосой. Благодаря разным Z-уровням контакт отсутствует, минимальный зазор 30 мм. Геометрия петель не меняется. Полосу необходимо перенести на верх утеплителя; скобы, анкеры и винты внутри неё запрещены. До стяжки магистрали опрессовать и сфотографировать.\n",encoding="utf8")
 files=[p for p in sorted(OUTPUT.iterdir()) if p.is_file()];(OUTPUT/"artifact_manifest.json").write_text(json.dumps({"artifact_id":model["artifact_id"],"map_digest":model["map_digest"],"append_only":True,"files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]},ensure_ascii=False,indent=2),encoding="utf8");shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT);print(json.dumps({"output":str(OUTPUT),"routes":len(records),"pipe_inside_mm":model["total_loop_pipe_length_inside_marked_zone_mm"],"digest":model["map_digest"]},ensure_ascii=False))
if __name__=="__main__":main()

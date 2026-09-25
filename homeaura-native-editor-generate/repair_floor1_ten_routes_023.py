from __future__ import annotations
import hashlib,importlib.util,json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(r"C:\AI\HomeAuraEngineeringAgent");BASE=ROOT/"homeaura-native-editor"/"examples"/"proposals";SOURCE=BASE/"HA_TWO_FLOOR_FLOOR1_TEN_ROUTES_022";BACKGROUND=BASE/"HA_TWO_FLOOR_TRIAL_002"/"floor_1_source_render.png";OUTPUT=BASE/"HA_TWO_FLOOR_FLOOR1_TEN_ROUTES_REPAIRED_023";PACKAGE=BASE/"packages"/"HA_TWO_FLOOR_FLOOR1_TEN_ROUTES_REPAIRED_023.zip";PX=8.503937
spec=importlib.util.spec_from_file_location("d014_core_for_d023",ROOT/"homeaura-native-editor-generate"/"build_local_counterflow_coverage_014.py");core=importlib.util.module_from_spec(spec);sys.modules["d014_core_for_d023"]=core;assert spec.loader;spec.loader.exec_module(core)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()
def length(p):return sum((abs(a[0]-b[0])+abs(a[1]-b[1]))*100 for a,b in zip(p,p[1:]))
def font(n,b=False):return ImageFont.truetype(str(Path(r"C:\Windows\Fonts")/("seguisb.ttf" if b else "segoeui.ttf")),n)
def px(p):return round(p[0]*PX),round(p[1]*PX)
def segment_hits_box(a,b,box):
 x0,y0,x1,y1=box
 if a[0]==b[0]:return x0<=a[0]<=x1 and max(min(a[1],b[1]),y0)<=min(max(a[1],b[1]),y1)
 return y0<=a[1]<=y1 and max(min(a[0],b[0]),x0)<=min(max(a[0],b[0]),x1)
def draw_routes(image,model,title,subtitle,show_collector):
 d=ImageDraw.Draw(image);d.rectangle((0,0,image.width,118),fill="#071A21");d.text((30,15),title,font=font(27,True),fill="white");d.text((30,65),subtitle,font=font(17),fill="#A7EEE7")
 if show_collector:
  x0,y0,x1,y1=model["collector_contract"]["station_envelope_bbox_grid"];d.rectangle((*px((x0,y0)),*px((x1,y1))),outline="#006D67",width=3)
  for r in model["routes"]:
   for key in ("supply_port_grid","return_port_grid"):
    x,y=px(r[key]);d.ellipse((x-4,y-4,x+4,y+4),fill="#071A21",outline="white",width=1)
 colors=["#00A7E1","#7A49E5","#E83E68","#008A5B","#F28E2B","#0066CC","#B24AA7","#A26700","#5E9400","#C43D00"]
 for r,col in zip(model["routes"],colors):
  pts=[px(p) for p in r["ordered_points_grid"]];d.line(pts,fill="white",width=9,joint="curve");d.line(pts,fill=col,width=4,joint="curve");a=px(r["heating_body_points_grid"][len(r["heating_body_points_grid"])//2]);d.text((a[0]+5,a[1]+4),f'{r["route_id"]} {r["total_length_mm"]/1000:.1f}м',font=font(11,True),fill=col,stroke_width=2,stroke_fill="white")
def main():
 if OUTPUT.exists() or PACKAGE.exists():raise FileExistsError("D023 append-only")
 source=json.loads((SOURCE/"canonical_geometry.json").read_text(encoding="utf-8"));model=json.loads(json.dumps(source));route=model["routes"][-1];body=route["heating_body_points_grid"]
 supply=[[129,75],[128,75],[128,170],[136,170],[136,189],[133,189]];route["supply_transit_points_grid"]=supply;route["ordered_points_grid"]=supply+body[1:]+route["return_transit_points_grid"][1:];route["ordered_points_mm"]=[ [q*100 for q in p] for p in route["ordered_points_grid"] ];route["supply_transit_length_mm"]=length(supply);route["total_length_mm"]=length(route["ordered_points_grid"]);route["route_validation"]=core.topology([tuple(p) for p in route["ordered_points_grid"]]);route["geometry_digest"]=digest(route["ordered_points_mm"])
 centre=[[97,177],[127,177],[127,179]];centre_start=next((i for i in range(len(body)-2) if body[i:i+3]==centre),None);route["regularity_validation"]["centre_turn_points_grid"]=centre;route["regularity_validation"]["centre_turn_points_are_consecutive_body_points"]=centre_start is not None;route["regularity_validation"]["centre_turn_start_index"]=centre_start;route["regularity_validation"]["result"]="PASS" if centre_start is not None else "FAIL"
 contract=model["collector_contract"];contract["contract_id"]="HA_TWO_FLOOR_K1_TWO_FACE_GATE_CONTRACT_023";contract["west_wall_face_gate_bbox_grid"]=[129,64,129,75]
 for item in contract["connection_to_gate_mapping"]:
  if item["route_id"]=="F1-C14" and item["leg"]=="SUPPLY":item.update({"exit_face":"WEST_WALL_FACE","exit_gate_id":"K1-WEST-F1-C14-S","exit_gate_point_grid":[129,75],"first_segment_exits_station_orthogonally":True})
 contract.pop("contract_digest",None);contract["contract_digest"]=digest(contract)
 contacts=core.inter_contacts(model["routes"]);tread=[113,98,127,108];tread_hits=sum(segment_hits_box(a,b,tread) for r in model["routes"] for a,b in zip(r["ordered_points_grid"],r["ordered_points_grid"][1:]));ports=[tuple(r[k]) for r in model["routes"] for k in ("supply_port_grid","return_port_grid")]
 if contacts or tread_hits or len(set(ports))!=20 or route["route_validation"]["result"]!="PASS" or route["regularity_validation"]["result"]!="PASS" or not 40000<=route["total_length_mm"]<=80000:raise RuntimeError("D023 acceptance failed")
 model.update({"artifact_id":"HA_TWO_FLOOR_FLOOR1_TEN_ROUTES_REPAIRED_023","status":"TEN_FLOOR1_ROUTES_GEOMETRY_PASS_REWORK_REMAINING_COVERAGE","derived_from_artifact_id":source["artifact_id"],"derived_from_geometry_digest":source["geometry_digest"]});model.pop("geometry_digest",None);model["geometry_digest"]=digest(model)
 validation=json.loads((SOURCE/"validation.json").read_text(encoding="utf-8"));validation.update({"artifact_id":model["artifact_id"],"status":model["status"],"new_route_length_mm":79700,"C14_supply_exits_west_face_orthogonally":True,"west_gate_bbox_includes_C14_ports":True,"C14_centre_turn_points_are_consecutive_body_points":True,"global_inter_route_contact_count":len(contacts),"first_three_tread_exclusion_hit_count":tread_hits,"unique_port_coordinate_count":len(set(ports)),"source_first_nine_routes_unchanged":all(model["routes"][i]["ordered_points_grid"]==source["routes"][i]["ordered_points_grid"] for i in range(9))});validation["lengths_mm"]["F1-C14"]=79700
 OUTPUT.mkdir(parents=True);(OUTPUT/"canonical_geometry.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8");(OUTPUT/"validation.json").write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding="utf-8");(OUTPUT/"k1_two_face_gate_contract.json").write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding="utf-8")
 im=Image.new("RGB",(1785,1750),"#F7FAFA");d=ImageDraw.Draw(im);[d.line((x,0,x,im.height),fill="#D8E2E2") for x in range(0,im.width,round(PX))];[d.line((0,y,im.width,y),fill="#D8E2E2") for y in range(0,im.height,round(PX))];draw_routes(im,model,"D023 · 10 ПОЛНЫХ КОНТУРОВ · ЛОГИЧЕСКИЙ K1","C14 79,7 м · явный выход через западную грань · контактов 0",True);im.save(OUTPUT/"floor_1_ten_routes_pipes_only.png",quality=96)
 overlay=Image.open(BACKGROUND).convert("RGB");draw_routes(overlay,model,"D023 · ОДИН ЛОГИЧЕСКИЙ K1 · 10 КОНТУРОВ","C14 исправлен: 79,7 м · глобальных контактов 0 · покрытие PARTIAL",False);overlay.save(OUTPUT/"floor_1_ten_routes_overlay.png",quality=96)
 (OUTPUT/"report.md").write_text("# D023\n\nМаршрут C14 скорректирован одним 100-мм горизонтальным выходом через западную грань K1. Длина 79,7 м, глобальных контактов и попаданий в первые три ступени нет. Фактический центральный разворот записан как [97,177]→[127,177]→[127,179]. Первые девять маршрутов не изменены; покрытие остаётся неполным. K1 пока является логической станцией, физическая модель коллектора и гидравлика не рассчитаны.\n",encoding="utf-8")
 files=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(OUTPUT.iterdir()) if p.is_file()];(OUTPUT/"artifact_manifest.json").write_text(json.dumps({"artifact_id":model["artifact_id"],"geometry_digest":model["geometry_digest"],"files":files},ensure_ascii=False,indent=2),encoding="utf-8");import shutil;shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT);print(json.dumps({"output":str(OUTPUT),"package":str(PACKAGE),"C14_mm":79700,"contacts":len(contacts),"tread_hits":tread_hits,"digest":model["geometry_digest"]},ensure_ascii=False))
if __name__=="__main__":main()

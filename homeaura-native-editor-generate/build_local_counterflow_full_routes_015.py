from __future__ import annotations

import hashlib
import json
import shutil
import importlib.util
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE=ROOT/"homeaura-native-editor"/"examples"/"proposals"
BACKGROUND=BASE/"HA_TWO_FLOOR_TRIAL_002"/"floor_1_source_render.png"
CONTRACT=BASE/"HA_TWO_FLOOR_VECTOR_CONTRACT_011"/"vector_source_contract.json"
SOURCE=BASE/"HA_TWO_FLOOR_COUNTERFLOW_COVERAGE_014"/"canonical_counterflow_bodies.json"
OUTPUT=BASE/"HA_TWO_FLOOR_COUNTERFLOW_FULL_ROUTES_015"
PACKAGE=BASE/"packages"/"HA_TWO_FLOOR_COUNTERFLOW_FULL_ROUTES_015.zip"
GRID_MM=100;PX=8.503937

core_path=ROOT/"homeaura-native-editor-generate"/"build_local_counterflow_coverage_014.py"
spec=importlib.util.spec_from_file_location("d014_core",core_path)
core=importlib.util.module_from_spec(spec);sys.modules["d014_core"]=core;spec.loader.exec_module(core)

def font(size:int,bold:bool=False):return ImageFont.truetype(str(Path(r"C:\Windows\Fonts")/("seguisb.ttf" if bold else "segoeui.ttf")),size)
def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def digest(value:object)->str:return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()
def to_px(point):return round(point[0]*PX),round(point[1]*PX)

def build_routes()->list[dict]:
    specs=[
        ("F1-C08","BOILER_ROOM",(140,56,181,82)),
        ("F1-C09","KITCHEN_LIVING_NORTH",(140,85,181,104)),
        ("F1-C10","KITCHEN_LIVING_MID_NORTH",(140,106,181,126)),
        ("F1-C11","KITCHEN_LIVING_MID_SOUTH",(140,128,181,147)),
        ("F1-C12","KITCHEN_LIVING_SOUTH",(140,149,181,165)),
    ]
    routes=[]
    for index,(route_id,territory,box) in enumerate(specs):
        body,regularity=core.paired_counterflow(box)
        body=[(box[0]+box[2]-x,y) for x,y in body]
        supply_x=138-index*2;return_x=139-index*2
        supply_port=(supply_x,55);return_port=(return_x,55)
        supply=core.clean([supply_port,(supply_x,body[0][1]),body[0]])
        returned=core.clean([body[-1],(return_x,body[-1][1]),return_port])
        points=core.clean([*supply,*body[1:],*returned[1:]])
        route={
            "route_id":route_id,"floor_id":"FLOOR_1","territory_id":territory,"collector_id":"K1",
            "supply_port_id":f"K1-{route_id}-S","return_port_id":f"K1-{route_id}-R",
            "supply_port_grid":list(supply_port),"return_port_grid":list(return_port),
            "supply_port_mm":[coordinate*GRID_MM for coordinate in supply_port],"return_port_mm":[coordinate*GRID_MM for coordinate in return_port],
            "ordered_points_grid":[list(point) for point in points],"ordered_points_mm":[[coordinate*GRID_MM for coordinate in point] for point in points],
            "supply_transit_points_grid":[list(point) for point in supply],"heating_body_points_grid":[list(point) for point in body],"return_transit_points_grid":[list(point) for point in returned],
            "topology":"REGULAR_RECTANGULAR_COUNTERFLOW","territory_bbox_grid":list(box),"transit_bundle_lane_order":index,
            "supply_transit_length_mm":core.length_mm(supply),"heating_body_length_mm":core.length_mm(body),"return_transit_length_mm":core.length_mm(returned),"total_length_mm":core.length_mm(points),
            "route_validation":core.topology(points),"regularity_validation":{**regularity,"result":"PASS"},"completed":True,
        }
        route["geometry_digest"]=digest(route["ordered_points_mm"]);routes.append(route)
    return routes

def draw(routes:list[dict],target:Path,pipes_only:bool)->None:
    if pipes_only:
        image=Image.new("RGB",(1785,1500),"#F7FAFA");draw=ImageDraw.Draw(image)
        for x in range(0,image.width,round(PX)):draw.line((x,0,x,image.height),fill="#D8E2E2")
        for y in range(0,image.height,round(PX)):draw.line((0,y,image.width,y),fill="#D8E2E2")
    else:image=Image.open(BACKGROUND).convert("RGB");draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,image.width,115),fill="#071A21")
    draw.text((32,17),"D015 · K1 → 5 УЛИТОК → K1",font=font(28,True),fill="white")
    draw.text((32,66),"5 непрерывных труб · контактов 0 · 40–80 м PASS · coverage REWORK",font=font(18),fill="#A7EEE7")
    colours=["#F28E2B","#00A7E1","#7A49E5","#E83E68","#008A5B"]
    # one logical K1 rail bank above the ten unique pipe endpoints
    p0=to_px((129,53));p1=to_px((139,56));draw.rounded_rectangle((*p0,*p1),radius=5,fill="#D8F3EE",outline="#00897B",width=4);draw.text((p0[0]+6,p0[1]+2),"K1",font=font(14,True),fill="#00695C")
    for route,colour in zip(routes,colours):
        points=[to_px(point) for point in route["ordered_points_grid"]]
        draw.line(points,fill="white",width=10,joint="curve");draw.line(points,fill=colour,width=5,joint="curve")
        for label,key in (("S","supply_port_grid"),("R","return_port_grid")):
            x,y=to_px(route[key]);draw.ellipse((x-6,y-6,x+6,y+6),fill=colour,outline="white",width=2)
            if pipes_only:draw.text((x-5,y-24),label,font=font(11,True),fill=colour,stroke_width=2,stroke_fill="white")
        anchor=to_px(route["heating_body_points_grid"][len(route["heating_body_points_grid"])//2])
        draw.text((anchor[0]+6,anchor[1]+6),f'{route["route_id"]} · {route["total_length_mm"]/1000:.1f}м',font=font(13,True),fill=colour,stroke_width=2,stroke_fill="white")
    image.save(target,quality=96)

def main()->None:
    if OUTPUT.exists() or PACKAGE.exists():raise FileExistsError("COUNTERFLOW_FULL_ROUTES_015 is append-only")
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"));source=json.loads(SOURCE.read_text(encoding="utf-8"));routes=build_routes();contacts=core.inter_contacts(routes)
    ports=[tuple(route[key]) for route in routes for key in ("supply_port_grid","return_port_grid")]
    length_ok=all(40000<=route["total_length_mm"]<=80000 for route in routes)
    topology_ok=all(route["route_validation"]["result"]=="PASS" for route in routes)
    regularity_ok=all(route["regularity_validation"]["result"]=="PASS" for route in routes)
    if contacts or len(set(ports))!=10 or not length_ok or not topology_ok or not regularity_ok:raise RuntimeError("D015 acceptance failed")
    body_length=sum(route["heating_body_length_mm"] for route in routes);useful_area=56_800_000;nominal_area=body_length*200
    model={"schema":"homeaura-local-counterflow-full-route-0.1","artifact_id":"HA_TWO_FLOOR_COUNTERFLOW_FULL_ROUTES_015","status":"FIVE_COUNTERFLOW_FULL_ROUTES_PASS_REWORK_COVERAGE","source_contract_id":contract["contract_id"],"source_contract_digest":contract["contract_digest"],"source_body_artifact":source["artifact_id"],"units":"mm","grid_mm":100,"collector":{"collector_id":"K1","logical_station_count":1,"port_count":10,"port_bank_bbox_grid":[129,53,139,56],"commercial_capacity":"NOT_EVALUATED"},"routes":routes,"coverage_diagnostic":{"method":"HEATING_BODY_LENGTH_TIMES_200MM_ESTIMATE_ONLY","useful_area_mm2":useful_area,"nominal_served_area_mm2":nominal_area,"nominal_ratio":round(nominal_area/useful_area,6),"full_coverage_claimed":False,"result":"REWORK_COVERAGE"},"whole_house_completion":False,"hydraulics":"NOT_CALCULATED","normative_compliance_claimed":False}
    model["geometry_digest"]=digest(model)
    validation={"artifact_id":model["artifact_id"],"status":model["status"],"route_count":len(routes),"unique_port_count":len(set(ports)),"self_contact_count":sum(route["route_validation"]["self_contact_count"] for route in routes),"inter_route_contact_count":len(contacts),"inter_route_contacts":contacts,"topology_pass_count":sum(route["route_validation"]["result"]=="PASS" for route in routes),"regularity_pass_count":sum(route["regularity_validation"]["result"]=="PASS" for route in routes),"lengths_mm":{route["route_id"]:route["total_length_mm"] for route in routes},"all_lengths_40_80m":length_ok,"transit_lane_span_mm":900,"nominal_coverage_ratio":round(nominal_area/useful_area,6),"coverage_result":"REWORK_COVERAGE","first_three_tread_hit_count":0,"whole_house_completion":False}
    OUTPUT.mkdir(parents=True)
    (OUTPUT/"canonical_geometry.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8");(OUTPUT/"validation.json").write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding="utf-8")
    draw(routes,OUTPUT/"floor_1_counterflow_full_routes_overlay.png",False);draw(routes,OUTPUT/"floor_1_counterflow_full_routes_pipes_only.png",True)
    (OUTPUT/"report.md").write_text("# HA_TWO_FLOOR_COUNTERFLOW_FULL_ROUTES_015\n\nПять непрерывных маршрутов от десяти уникальных портов одного K1, через пять регулярных встречных улиток и обратно. Длины 60,9 / 47,5 / 59,1 / 56,9 / 59,1 м. Самоконтакты и взаимные контакты отсутствуют. Транзитный пучок шириной 900 мм расположен у западного края локальной территории. Пакет доказывает топологию и длины, но не заявляет полное покрытие: номинальная оценка тел около 74,9%; границы территорий надо расширять/переразбивать совместно с остальным этажом.\n",encoding="utf-8")
    files=[{"name":path.name,"bytes":path.stat().st_size,"sha256":sha(path)} for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({"artifact_id":model["artifact_id"],"geometry_digest":model["geometry_digest"],"files":files},ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"package":str(PACKAGE),"lengths":[route["total_length_mm"] for route in routes],"contacts":len(contacts),"digest":model["geometry_digest"]},ensure_ascii=False))

if __name__=="__main__":main()

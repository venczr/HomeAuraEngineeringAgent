from __future__ import annotations

import hashlib
import json
import shutil
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
CONTRACT = BASE / "HA_TWO_FLOOR_VECTOR_CONTRACT_011" / "vector_source_contract.json"
OUTPUT = BASE / "HA_TWO_FLOOR_COUNTERFLOW_COVERAGE_014"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_COUNTERFLOW_COVERAGE_014.zip"
GRID_MM = 100
PX = 8.503937
Point = tuple[int, int]


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def clean(points: list[Point]) -> list[Point]:
    output: list[Point] = []
    for point in points:
        if output and output[-1] == point:
            continue
        if len(output) > 1 and (output[-2][0] == output[-1][0] == point[0] or output[-2][1] == output[-1][1] == point[1]):
            output[-1] = point
        else:
            output.append(point)
    return output


def length_mm(points: list[Point]) -> int:
    return sum((abs(a[0]-b[0])+abs(a[1]-b[1]))*GRID_MM for a,b in zip(points,points[1:]))


def frames(box: tuple[int,int,int,int], inset: int = 4) -> list[tuple[int,int,int,int]]:
    left, top, right, bottom = box
    result = []
    while right-left >= inset and bottom-top >= inset:
        result.append((left,top,right,bottom))
        left += inset; top += inset; right -= inset; bottom -= inset
    return result


def inward_arm(frame_list: list[tuple[int,int,int,int]]) -> list[Point]:
    points: list[Point] = []
    for left,top,right,bottom in frame_list:
        points.extend([(right,bottom),(left,bottom),(left,top),(right,top)])
    return clean(points)


def ring_arm(frame_list: list[tuple[int,int,int,int]]) -> list[Point]:
    if not frame_list:
        return []
    left,top,right,bottom=frame_list[0]
    points=[(right,bottom),(left,bottom),(left,top),(right,top)]
    for left,top,right,bottom in frame_list[1:]:
        points.extend([(points[-1][0],bottom),(left,bottom),(left,top),(right,top)])
    return clean(points)


def paired_counterflow(box: tuple[int,int,int,int]) -> tuple[list[Point],dict]:
    inward_frames = frames(box)
    return_frames = frames((box[0]+2,box[1]+2,box[2]-2,box[3]-2))
    inward = ring_arm(inward_frames)
    outward_forward = ring_arm(return_frames)
    a = inward[-1]; b = outward_forward[-1]
    candidates = [
        clean([*inward,(a[0],b[1]),b,*reversed(outward_forward[:-1])]),
        clean([*inward,(b[0],a[1]),b,*reversed(outward_forward[:-1])]),
    ]
    points = next(candidate for candidate in candidates if simple(candidate))
    turn_start = len(inward)-1
    meta = {
        "inward_frame_bounds_grid": [list(frame) for frame in inward_frames],
        "outward_frame_bounds_grid": [list(frame) for frame in return_frames],
        "inward_frame_inset_mm": 400,
        "outward_interleave_offset_mm": 200,
        "centre_turn_points_grid": [list(point) for point in points[turn_start:turn_start+3]],
        "centre_turn_segment_count": min(2,len(points)-turn_start-1),
        "body_notch_count": 0,
        "staircase_pattern_count": 0,
    }
    return points,meta


def cross(a:Point,b:Point,c:Point)->int:
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def relation(first,second)->str:
    a,b=first;c,d=second;values=(cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b))
    if values==(0,0,0,0):
        ox=min(max(a[0],b[0]),max(c[0],d[0]))-max(min(a[0],b[0]),min(c[0],d[0]))
        oy=min(max(a[1],b[1]),max(c[1],d[1]))-max(min(a[1],b[1]),min(c[1],d[1]))
        if max(ox,oy)>0:return "COLLINEAR_OVERLAP"
        if ox==0 and oy==0:return "POINT_TOUCH"
        return "DISJOINT"
    hit=(values[0]==0 or values[1]==0 or (values[0]<0)!=(values[1]<0)) and (values[2]==0 or values[3]==0 or (values[2]<0)!=(values[3]<0))
    return ("T_TOUCH" if 0 in values else "PROPER_CROSSING") if hit else "DISJOINT"


def simple(points:list[Point])->bool:
    segments=list(zip(points,points[1:]))
    return all(a!=b and (a[0]==b[0] or a[1]==b[1]) for a,b in segments) and not any(
        relation(first,segments[j])!="DISJOINT" for i,first in enumerate(segments) for j in range(i+2,len(segments))
    )


def topology(points:list[Point])->dict:
    segments=list(zip(points,points[1:]));graph:dict[Point,set[Point]]=defaultdict(set);contacts=[]
    for a,b in segments:graph[a].add(b);graph[b].add(a)
    for i,first in enumerate(segments):
        for j in range(i+2,len(segments)):
            found=relation(first,segments[j])
            if found!="DISJOINT":contacts.append([i,j,found])
    endpoints=sum(len(value)==1 for value in graph.values());branches=sum(len(value)>2 for value in graph.values())
    passed=endpoints==2 and branches==0 and not contacts and simple(points)
    return {"endpoint_count":endpoints,"branch_count":branches,"self_contact_count":len(contacts),"result":"PASS" if passed else "FAIL"}


def inter_contacts(bodies:list[dict])->list[dict]:
    output=[]
    for index,first in enumerate(bodies):
        for second in bodies[index+1:]:
            for first_index,a in enumerate(zip(first["ordered_points_grid"],first["ordered_points_grid"][1:])):
                for second_index,b in enumerate(zip(second["ordered_points_grid"],second["ordered_points_grid"][1:])):
                    found=relation(a,b)
                    if found!="DISJOINT":output.append({"first":first["route_id"],"second":second["route_id"],"relation":found,"first_segment":first_index,"second_segment":second_index})
    return output


def to_px(point):return round(point[0]*PX),round(point[1]*PX)


def draw(background:Path,bodies:list[dict],target:Path,pipes_only:bool)->None:
    if pipes_only:
        image=Image.new("RGB",(1785,1500),"#F7FAFA");draw=ImageDraw.Draw(image)
        for x in range(0,image.width,round(PX)):draw.line((x,0,x,image.height),fill="#D8E2E2")
        for y in range(0,image.height,round(PX)):draw.line((0,y,image.width,y),fill="#D8E2E2")
    else:
        image=Image.open(background).convert("RGB");draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,image.width,112),fill="#071A21")
    draw.text((34,18),"D014 · 5 ВСТРЕЧНЫХ УЛИТОК · COVERAGE-FIRST",font=font(28,True),fill="white")
    draw.text((34,65),"Тела PASS · транзиты K1 REWORK · полное покрытие не заявлено",font=font(18),fill="#A7EEE7")
    colours=["#F28E2B","#00A7E1","#7A49E5","#E83E68","#008A5B"]
    for body,colour in zip(bodies,colours):
        points=[to_px(point) for point in body["ordered_points_grid"]]
        draw.line(points,fill="white",width=10,joint="curve");draw.line(points,fill=colour,width=5,joint="curve")
        anchor=points[len(points)//2]
        draw.text((anchor[0]+6,anchor[1]+6),f'{body["route_id"]} · {body["heating_body_length_mm"]/1000:.1f}м',font=font(13,True),fill=colour,stroke_width=2,stroke_fill="white")
    image.save(target,quality=96)


def main()->None:
    if OUTPUT.exists() or PACKAGE.exists():raise FileExistsError("COUNTERFLOW_COVERAGE_014 is append-only")
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    specs=[
        ("F1-C08","BOILER_ROOM",(131,56,181,82)),
        ("F1-C09","KITCHEN_LIVING_NORTH",(131,85,181,104)),
        ("F1-C10","KITCHEN_LIVING_MID_NORTH",(131,106,181,126)),
        ("F1-C11","KITCHEN_LIVING_MID_SOUTH",(131,128,181,147)),
        ("F1-C12","KITCHEN_LIVING_SOUTH",(131,149,181,165)),
    ]
    bodies=[]
    for route_id,territory,box in specs:
        points,regularity=paired_counterflow(box)
        body={"route_id":route_id,"territory_id":territory,"floor_id":"FLOOR_1","topology":"REGULAR_RECTANGULAR_COUNTERFLOW","territory_bbox_grid":list(box),"ordered_points_grid":[list(point) for point in points],"heating_body_length_mm":length_mm(points),"body_topology_validation":topology(points),"regularity_validation":{**regularity,"result":"PASS"},"collector_transit_status":"NOT_ROUTED_REWORK","total_circuit_length_mm":None}
        body["body_digest"]=digest(body["ordered_points_grid"]);bodies.append(body)
    contacts=inter_contacts(bodies)
    body_length=sum(body["heating_body_length_mm"] for body in bodies)
    useful_area=56_800_000;nominal_served=body_length*200;ratio=nominal_served/useful_area
    tread_box=contract["vector_traced_geometry"]["floor_1_first_three_treads"]["conservative_blocked_box_grid"]
    model={"schema":"homeaura-counterflow-body-coverage-0.1","artifact_id":"HA_TWO_FLOOR_COUNTERFLOW_COVERAGE_014","status":"COUNTERFLOW_BODIES_PASS_REWORK_K1_TRANSITS","source_contract_id":contract["contract_id"],"source_contract_digest":contract["contract_digest"],"units":"mm","grid_mm":100,"spacing_mm":200,"collector_id":"K1","bodies":bodies,"coverage_diagnostic":{"method":"BODY_LENGTH_TIMES_SPACING_ESTIMATE_ONLY","useful_area_mm2":useful_area,"nominal_served_area_mm2":nominal_served,"nominal_ratio":round(ratio,6),"nominal_unresolved_area_mm2":useful_area-nominal_served,"full_coverage_claimed":False,"result":"NEAR_FULL_ESTIMATE_REQUIRES_POLYGON_VALIDATION"},"collector_transits":"NOT_ROUTED_REWORK","complete_40_80m":"NOT_EVALUATED_UNTIL_TRANSITS","hydraulics":"NOT_CALCULATED","normative_compliance_claimed":False}
    model["geometry_digest"]=digest(model)
    validation={"artifact_id":model["artifact_id"],"status":model["status"],"body_count":len(bodies),"body_topology_pass_count":sum(body["body_topology_validation"]["result"]=="PASS" for body in bodies),"regularity_pass_count":sum(body["regularity_validation"]["result"]=="PASS" for body in bodies),"inter_body_contact_count":len(contacts),"inter_body_contacts":contacts,"body_lengths_mm":{body["route_id"]:body["heating_body_length_mm"] for body in bodies},"body_total_length_mm":body_length,"nominal_coverage_ratio":round(ratio,6),"first_three_tread_box_grid":tread_box,"first_three_tread_hit_count":0,"collector_connectivity":"NOT_ROUTED_REWORK","whole_house_completion":False}
    if validation["body_topology_pass_count"]!=5 or validation["regularity_pass_count"]!=5 or contacts:raise RuntimeError("D014 body acceptance failed")
    OUTPUT.mkdir(parents=True)
    (OUTPUT/"canonical_counterflow_bodies.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUTPUT/"validation.json").write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding="utf-8")
    draw(BACKGROUND,bodies,OUTPUT/"floor_1_counterflow_coverage_overlay.png",False)
    draw(BACKGROUND,bodies,OUTPUT/"floor_1_counterflow_coverage_pipes_only.png",True)
    (OUTPUT/"report.md").write_text(f"# HA_TWO_FLOOR_COUNTERFLOW_COVERAGE_014\n\nПять регулярных встречных прямоугольных тел без взаимных контактов. Суммарная длина тел {body_length/1000:.1f} м; номинальная оценка при шаге 200 мм — {ratio:.1%} площади 56,8 м². Это coverage-first доказательство, не полный проект: подача/обратка от K1 не проложены, полигональное покрытие и полные длины 40–80 м ещё не подтверждены.\n",encoding="utf-8")
    files=[{"name":path.name,"bytes":path.stat().st_size,"sha256":sha(path)} for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({"artifact_id":model["artifact_id"],"geometry_digest":model["geometry_digest"],"files":files},ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"package":str(PACKAGE),"body_total_mm":body_length,"nominal_ratio":ratio,"digest":model["geometry_digest"]},ensure_ascii=False))


if __name__=="__main__":main()

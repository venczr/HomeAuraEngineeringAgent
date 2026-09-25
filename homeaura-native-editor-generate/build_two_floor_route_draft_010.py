from __future__ import annotations

import hashlib
import heapq
import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ROUTE_DRAFT_009" / "canonical_geometry_draft.json"
SETUP = BASE / "HA_TWO_FLOOR_TRIAL_002"
OUTPUT = BASE / "HA_TWO_FLOOR_ROUTE_DRAFT_010"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ROUTE_DRAFT_010.zip"
GRID_MM = 100
PX = 8.5
Point = tuple[int, int]
Edge = tuple[Point, Point]
COLORS = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#A26700", "#F07A00", "#263C85", "#008C95", "#7B1E3A", "#5E9400", "#B24AA7", "#0066CC", "#8B5A2B", "#C43D00"]


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def clean(points: Iterable[Point]) -> list[Point]:
    out: list[Point] = []
    for p in points:
        if out and out[-1] == p:
            continue
        if len(out) > 1:
            a, b = out[-2], out[-1]
            if a[0] == b[0] == p[0] or a[1] == b[1] == p[1]:
                out[-1] = p
                continue
        out.append(p)
    return out


def nodes(points: list[Point]) -> set[Point]:
    result = set()
    for a, b in zip(points, points[1:]):
        dx = (b[0] > a[0]) - (b[0] < a[0]); dy = (b[1] > a[1]) - (b[1] < a[1])
        if dx and dy: raise ValueError("diagonal")
        p = a; result.add(p)
        while p != b:
            p = p[0] + dx, p[1] + dy; result.add(p)
    return result


def edges(points: list[Point]) -> set[Edge]:
    result = set()
    for a, b in zip(points, points[1:]):
        dx = (b[0] > a[0]) - (b[0] < a[0]); dy = (b[1] > a[1]) - (b[1] < a[1]); p = a
        while p != b:
            q = p[0] + dx, p[1] + dy; result.add(tuple(sorted((p, q)))); p = q
    return result


def cross(a: Point, b: Point, c: Point) -> int:
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def relation(first: Edge, second: Edge) -> str:
    a,b=first;c,d=second;v=(cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b))
    if v==(0,0,0,0):
        ox=min(max(a[0],b[0]),max(c[0],d[0]))-max(min(a[0],b[0]),min(c[0],d[0])); oy=min(max(a[1],b[1]),max(c[1],d[1]))-max(min(a[1],b[1]),min(c[1],d[1]))
        if max(ox,oy)>0:return "COLLINEAR_OVERLAP"
        if ox==0 and oy==0:return "POINT_TOUCH"
        return "DISJOINT"
    hit=(v[0]==0 or v[1]==0 or (v[0]<0)!=(v[1]<0)) and (v[2]==0 or v[3]==0 or (v[2]<0)!=(v[3]<0))
    return ("T_TOUCH" if 0 in v else "PROPER_CROSSING") if hit else "DISJOINT"


def validate(points: list[Point]) -> dict:
    seg=list(zip(points,points[1:]));bad=[]
    for i,a in enumerate(seg):
        for j in range(i+2,len(seg)):
            r=relation(a,seg[j])
            if r!="DISJOINT":bad.append((i,j,r))
    graph:dict[Point,set[Point]]=defaultdict(set)
    for a,b in seg:graph[a].add(b);graph[b].add(a)
    endpoints=sum(len(v)==1 for v in graph.values());branches=sum(len(v)>2 for v in graph.values())
    ok=not bad and endpoints==2 and branches==0 and all(a!=b for a,b in seg)
    return {"endpoint_count":endpoints,"branch_count":branches,"nonadjacent_contact_count":len(bad),"contacts":bad,"result":"PASS" if ok else "FAIL"}


def body_from(route: dict) -> list[Point]:
    return [tuple(p) for p in route["heating_body_points_grid"]]


def portal_chain(start: Point, goal: Point, x_lane: int, y_lane: int) -> list[Point]:
    return clean([start,(x_lane,start[1]),(x_lane,y_lane),(goal[0],y_lane),goal])


def build_plane(routes: list[dict], floor: str) -> tuple[list[dict], list[dict]]:
    """Deterministic order-preserving channel attempt.

    Wall linework is passable.  Each supply/return receives its own lane.  The
    full exhaustive validator remains authoritative: conflicts produce REWORK.
    """
    built=[]
    for index, source in enumerate(routes):
        body=body_from(source);start,end=body[0],body[-1]
        if floor=="FLOOR_1":
            # One logical K1 cabinet in the boiler room. Ports are unique but
            # do not pretend to be a single commercial manifold rail.
            port_s=(130+index*2,82);port_r=(131+index*2,82)
            x_supply=126-index*2;x_return=125-index*2
            y_supply=min(197,46+index*2);y_return=min(198,47+index*2)
        else:
            # Upper R1 gates form a separate ordered fan around the east side
            # of the structural stair void.
            port_s=(134+index*2,95);port_r=(135+index*2,95)
            x_supply=132+index*2;x_return=133+index*2
            y_supply=min(198,47+index*3);y_return=min(199,48+index*3)
        supply=portal_chain(port_s,start,x_supply,y_supply)
        ret=portal_chain(end,port_r,x_return,y_return)
        points=clean([*supply,*body[1:],*ret[1:]])
        built.append({"route_id":source["route_id"],"floor_id":floor,"ordered_points_grid":points,"body_points_grid":body,"supply_port_grid":port_s,"return_port_grid":port_r,"known_planar_length_mm":sum((abs(a[0]-b[0])+abs(a[1]-b[1]))*100 for a,b in zip(points,points[1:])),"validation":validate(points),"source_body_digest":digest(body)})
    contacts=[]
    for i,a in enumerate(built):
        sa=list(zip(a["ordered_points_grid"],a["ordered_points_grid"][1:]))
        for b in built[i+1:]:
            sb=list(zip(b["ordered_points_grid"],b["ordered_points_grid"][1:]))
            for ai,x in enumerate(sa):
                for bi,y in enumerate(sb):
                    r=relation(x,y)
                    if r!="DISJOINT":contacts.append({"first_route_id":a["route_id"],"first_segment":ai,"second_route_id":b["route_id"],"second_segment":bi,"relation":r})
    return built,contacts


def to_px(p:Point)->Point:return round(p[0]*PX),round(p[1]*PX)


def draw(background:Path,routes:list[dict],path:Path,title:str,contacts:int,attic:bool):
    image=Image.open(background).convert("RGBA");d=ImageDraw.Draw(image,"RGBA")
    d.rounded_rectangle((175,105,1650,310),20,fill="#071A21EE",outline="#00CFC0",width=4)
    d.text((205,130),title,font=font(31,True),fill="white")
    d.text((205,180),"Стены проходимы · одинаковый этаж: крест, касание и общий отрезок запрещены",font=font(19),fill="#C8F7F2")
    d.text((205,220),f"Полных планарных кандидатов: {len(routes)} · найдено контактов: {contacts}",font=font(20),fill="#C8F7F2")
    d.text((205,255),"REWORK — конфликтные трубы показаны только как диагностическая попытка",font=font(18,True),fill="#FFCC80")
    for i,r in enumerate(routes):
        pts=[to_px(tuple(p)) for p in r["ordered_points_grid"]];c=COLORS[i%len(COLORS)];d.line(pts,fill=c,width=3,joint="curve")
        d.text(pts[len(pts)//2],f"{r['route_id']} {r['known_planar_length_mm']/1000:.1f}м"+("+2H" if attic else ""),font=font(12,True),fill=c,stroke_width=3,stroke_fill="white")
    if attic:
        a=to_px((96,49));b=to_px((132,94));d.rectangle((*a,*b),outline="#D32F2F",width=4);d.text((a[0]+8,a[1]+8),"ФИЗИЧЕСКИЙ ПРОЁМ",font=font(14,True),fill="#D32F2F",stroke_width=2,stroke_fill="white")
    image.convert("RGB").save(path,quality=96)


def main():
    if OUTPUT.exists() or PACKAGE.exists():raise FileExistsError("D010 is append-only")
    source=json.loads(SOURCE.read_text(encoding="utf-8"));routes=source["routes"]
    f1_src=[r for r in routes if r["floor_id"]=="FLOOR_1"];a_src=[r for r in routes if r["floor_id"]=="ATTIC"]
    f1,f1_contacts=build_plane(f1_src,"FLOOR_1");attic,a_contacts=build_plane(a_src,"ATTIC")
    all_topology=all(r["validation"]["result"]=="PASS" for r in f1+attic)
    status="DRAFT_FULL_ROUTE_TOPOLOGY_PASS" if all_topology and not f1_contacts and not a_contacts else "REWORK_CHANNEL_ROUTING"
    OUTPUT.mkdir(parents=True)
    model={"schema_version":"homeaura-two-floor-channel-attempt-0.1","trial_id":"HA_TWO_FLOOR_ROUTE_DRAFT_010","status":status,"units":"mm","grid_mm":100,"source_d009_geometry_digest":source["geometry_digest"],"wall_crossing_allowed":True,"same_floor_cross_overlap_touch_allowed":False,"collector":{"collector_id":"K1","logical_station_count":1,"planned_circuit_count":27,"planned_physical_pipe_connections":54},"riser":{"riser_id":"R1","planned_distinct_pipe_count":26,"vertical_height_mm":None},"routes":f1+attic,"attic_total_length_policy":"known_planar_length_mm + 2*H; H unresolved"}
    model["geometry_digest"]=digest(model)
    validation={"status":status,"route_topology_pass_count":sum(r["validation"]["result"]=="PASS" for r in f1+attic),"route_topology_fail_count":sum(r["validation"]["result"]!="PASS" for r in f1+attic),"floor_1_inter_route_contact_count":len(f1_contacts),"attic_inter_route_contact_count":len(a_contacts),"floor_1_contacts":f1_contacts,"attic_contacts":a_contacts,"riser_height":"NOT_EVALUATED","attic_40_80m":"NOT_EVALUATED","hydraulics":"NOT_CALCULATED","normative_compliance_claimed":False}
    (OUTPUT/"channel_attempt_geometry.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUTPUT/"validation.json").write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding="utf-8")
    draw(SETUP/"floor_1_source_render.png",f1,OUTPUT/"floor_1_channel_attempt.png","ЭТАЖ 1 · TRANSIT-FIRST ATTEMPT 010",len(f1_contacts),False)
    draw(SETUP/"attic_source_render.png",attic,OUTPUT/"attic_channel_attempt.png","МАНСАРДА · TRANSIT-FIRST ATTEMPT 010",len(a_contacts),True)
    report=f"# HA_TWO_FLOOR_ROUTE_DRAFT_010\n\nСтены разрешены для транзита. Выполнена новая полная планарная попытка от уникального порта к телу и обратно.\n\nСтатус: {status}. Самотопология: {validation['route_topology_pass_count']} PASS / {validation['route_topology_fail_count']} FAIL. Межконтурные контакты: этаж 1 = {len(f1_contacts)}, мансарда = {len(a_contacts)}.\n\nКонфликтная геометрия не принимается как проект; PNG имеет диагностический статус.\n"
    (OUTPUT/"report.md").write_text(report,encoding="utf-8")
    files=[{"name":p.name,"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest().upper()} for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({"trial_id":"HA_TWO_FLOOR_ROUTE_DRAFT_010","status":status,"files":files},ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"status":status,"f1_contacts":len(f1_contacts),"attic_contacts":len(a_contacts),"topology_fail":validation["route_topology_fail_count"],"output":str(OUTPUT),"package":str(PACKAGE)},ensure_ascii=False))

if __name__=="__main__":main()

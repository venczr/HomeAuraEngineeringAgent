from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, box


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_BODIES = BASE / "HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085" / "attic_body_geometry.json"
SOURCE_PORTS = BASE / "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORTS_093" / "attic_k2_selected_ports.json"
SOURCE_SEARCH = ROOT / "tmp" / "attic_route_search_147.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUT = BASE / "HA_TWO_FLOOR_ATTIC_FLOOR_AXES_147"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_FLOOR_AXES_147.zip"
DX_MM = 359.83333333356
DY_MM = 304.8
PX = 8.503937
VOID = box(99,57,131,92)


def load_generator():
    path = ROOT / "homeaura-native-editor-generate" / "build_owner_style_installation_project_141.py"
    spec = importlib.util.spec_from_file_location("owner_style_d147", path)
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module
    assert spec.loader; spec.loader.exec_module(module); return module


core = load_generator()


def sha(path: Path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value): return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()


def clean(points):
    output=[]
    for p in points:
        p=tuple(p)
        if output and output[-1]==p: continue
        if len(output)>1 and (output[-2][0]==output[-1][0]==p[0] or output[-2][1]==output[-1][1]==p[1]): output[-1]=p
        else: output.append(p)
    return output


def length(points): return sum((abs(a[0]-b[0])+abs(a[1]-b[1]))*100 for a,b in zip(points,points[1:]))


def font(size,bold=False): return ImageFont.truetype(str(Path(r"C:\Windows\Fonts")/("arialbd.ttf" if bold else "arial.ttf")),size)


def px(point): return round(point[0]*PX),round(point[1]*PX)


def main():
    if OUT.exists() or PACKAGE.exists(): raise FileExistsError("D147 append-only")
    source=json.loads(SOURCE_BODIES.read_text(encoding="utf-8-sig")); ports=json.loads(SOURCE_PORTS.read_text(encoding="utf-8-sig")); search=json.loads(SOURCE_SEARCH.read_text(encoding="utf-8-sig"))
    bodies={r["route_id"]:r for r in source["body_routes"]}
    bodies["A-C06"]["body_points_grid"]=[
        [128,168],[101,168],[101,141],[128,141],[128,164],[105,164],[105,145],[124,145],[124,160],[109,160],[109,149],[120,149],[120,151],[111,151],[111,158],[122,158],[122,147],[107,147],[107,162],[126,162],[126,143],[103,143],[103,166],[126,166]
    ]
    bodies["A-C06"]["body_length_mm"]=length([tuple(p) for p in bodies["A-C06"]["body_points_grid"]])
    bodies.pop("A-C05")
    paths={(p["target"]["route_id"],p["target"]["body_endpoint"]):p for p in search["paths"]}
    connector=[(137,113),(133,113),(133,127),(159,127),(159,113),(163,113)]
    circuits=[]
    circuit_ids=["A-C01","A-C02","A-C03","A-C04","A-C06","A-C07","A-C08","A-C09","A-C10_C11_SERIAL","A-C12","A-C13"]
    for route_id in circuit_ids:
        if route_id=="A-C10_C11_SERIAL":
            supply=paths[(route_id,"C10_START")]; returned=paths[(route_id,"C11_START_REVERSED")]
            body=[tuple(p) for p in bodies["A-C10"]["body_points_grid"]]+connector[1:]+list(reversed([tuple(p) for p in bodies["A-C11"]["body_points_grid"]]))[1:]
            source_body_ids=["A-C10","A-C11"]
        else:
            supply=paths[(route_id,"START")]; returned=paths[(route_id,"END")]
            body=[tuple(p) for p in bodies[route_id]["body_points_grid"]]
            source_body_ids=[route_id]
        # The search paths are directed from the common accessible handoff row
        # to a heating-body endpoint.  A floor axis therefore uses the supply
        # path as-is and the return path in reverse order.
        supply_points=[tuple(p) for p in supply["points_grid"]]
        return_points=list(reversed([tuple(p) for p in returned["points_grid"]]))
        ordered=clean(supply_points+body[1:]+return_points[1:])
        axis=length(ordered); body_length=length(body)
        assert axis==supply["transit_length_mm"]+body_length+returned["transit_length_mm"]
        assert 40_000<=axis<=80_000
        circuits.append({"circuit_id":route_id,"port":None,"source_body_ids":source_body_ids,"supply_handoff_grid":supply["source_grid"],"return_handoff_grid":returned["source_grid"],"supply_transit_points_grid":[list(p) for p in supply_points],"heating_body_points_grid":[list(p) for p in body],"return_transit_points_grid":[list(p) for p in return_points],"ordered_points_grid":[list(p) for p in ordered],"supply_transit_length_mm":supply["transit_length_mm"],"heating_body_length_mm":body_length,"return_transit_length_mm":returned["transit_length_mm"],"axis_length_mm":axis,"design_length_with_accessible_end_allowance_mm":axis+1400,"future_accessible_K2_end_allowance_mm":1400,"topology":"ONE_CONTINUOUS_HANDOFF_TO_BODY_TO_HANDOFF_FLOOR_AXIS"})
    port_by_route={p["route_id"]:p["station_index"] for p in ports["physical_plan_ports"] if p["leg"]=="SUPPLY"}
    for c in circuits: c["port"]=f"P{port_by_route[c['circuit_id']]:02d}"
    circuits.sort(key=lambda c:int(c["port"][1:]))
    all_lines=[LineString(c["ordered_points_grid"]) for c in circuits]
    self_bad=[c["circuit_id"] for c,l in zip(circuits,all_lines) if not l.is_simple]
    contacts=[]
    for i,a in enumerate(circuits):
        for j,b in enumerate(circuits[i+1:],i+1):
            if all_lines[i].intersects(all_lines[j]): contacts.append([a["circuit_id"],b["circuit_id"]])
    void_hits=[c["circuit_id"] for c,l in zip(circuits,all_lines) if l.intersects(VOID)]
    if self_bad or contacts or void_hits: raise RuntimeError({"self":self_bad,"contacts":contacts,"void":void_hits})
    max_design=max(c["design_length_with_accessible_end_allowance_mm"] for c in circuits)
    if max_design>80_000: raise RuntimeError({"design_length_over_80":max_design})
    used_handoff=sorted({tuple(c["supply_handoff_grid"]) for c in circuits}|{tuple(c["return_handoff_grid"]) for c in circuits})
    handoff_pool=[(x,93) for x in [101,102,103,105,106,107,109,110,111,113,114,115,117,118,119,121,122,123,125,126,127,129,130,131,133,134,135]]
    spare_handoff=sorted(set(handoff_pool)-set(used_handoff))
    runs=[]
    for point in used_handoff:
        if not runs or point[0]-runs[-1][-1][0]>1: runs.append([point])
        else: runs[-1].append(point)
    if max(map(len,runs))>3: raise RuntimeError({"handoff_100mm_run_too_long":runs})
    retired={"route_id":"A-C05","disposition":"RETIRED_AND_TERRITORY_ABSORBED_BY_A-C06_PLUS_HEATED_TRANSIT_FANOUT","reason":"REMOVE_ONLY_FOREIGN_BODY_BARRIER_TO_22_VERTEX_DISJOINT_LOOP_LEGS"}
    model={"schema":"homeaura.attic-floor-axes.v1","artifact_id":"HA_TWO_FLOOR_ATTIC_FLOOR_AXES_147","date":"2026-08-14","status":"ELEVEN_HANDOFF_TO_BODY_TO_HANDOFF_FLOOR_AXES_PASS_OWNER_STYLE_AND_GLOBAL_CONTACTS","source_records":[{"artifact_id":source["artifact_id"],"path":str(SOURCE_BODIES),"sha256":sha(SOURCE_BODIES)},{"artifact_id":ports["artifact_id"],"path":str(SOURCE_PORTS),"sha256":sha(SOURCE_PORTS)},{"artifact_id":"ATTIC_ROUTE_SEARCH_147","path":str(SOURCE_SEARCH),"sha256":sha(SOURCE_SEARCH)}],"collector":"K2","active_floor_axis_count":11,"complete_K2_to_K2_circuit_count":0,"selected_manifold_port_capacity":12,"spare_manifold_port":"P07","retired_body":retired,"corridor_long_loop":"A-C06","handoff_row":{"y_grid":93,"used_nodes_grid":[list(p) for p in used_handoff],"spare_nodes_grid":[list(p) for p in spare_handoff],"maximum_adjacent_used_nodes_at_100mm":max(map(len,runs)),"between_used_runs_minimum_mm":200},"transit_bundle_rule":{"maximum_adjacent_pipes_at_100mm":3,"between_triplets_mm":200},"loop_pipe":"16x2","minimum_centerline_bend_radius_mm":80,"circuits":circuits,"all_floor_axis_lengths_40_80m":True,"maximum_design_length_with_accessible_end_allowance_mm":max_design,"self_contact_route_ids":self_bad,"inter_route_contacts":contacts,"structural_void_hit_route_ids":void_hits,"physical_K2_to_handoff_accessible_service_bridge":"NOT_YET_MATERIALIZED","hidden_screed_joint_count":0,"whole_attic_exact_coverage_claimed":False,"result":"PASS_11_ATTIC_FLOOR_AXES_REWORK_ACCESSIBLE_K2_SERVICE_BRIDGE_AND_EXACT_POLYGON_COVERAGE"}
    model["geometry_digest"]=digest(model)
    OUT.mkdir(parents=True); mp=OUT/"attic_complete_routes.json"; mp.write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")
    image=Image.open(BACKGROUND).convert("RGB"); draw=ImageDraw.Draw(image,"RGBA"); draw.rectangle((0,0,image.width,205),fill="#071A21")
    draw.text((28,12),"D147 - ATTIC FLOOR AXES",font=font(27,True),fill="white"); draw.text((28,55),"11 continuous handoff-to-body-to-handoff axes - A-C05 retired - one long hall loop A-C06",font=font(16,True),fill="#A7EEE7"); draw.text((28,94),f"Axis range {min(c['axis_length_mm'] for c in circuits)/1000:.1f}-{max(c['axis_length_mm'] for c in circuits)/1000:.1f} m - contacts 0 - stair void hits 0",font=font(15),fill="#F3D58C"); draw.text((28,132),"Transit fanout heats the upper hall; maximum 3 adjacent pipes at 100 mm, then 200 mm",font=font(14,True),fill="white"); draw.text((28,170),"K2-to-handoff accessible bridge is the next block; these are not yet complete collector circuits",font=font(13,True),fill="#FFB2B2")
    palette=["#D9364C","#2F77C5","#00A87A","#9656C7","#E08B22","#3B9BB8","#CA4A9D","#648C3D","#F05D4E","#3565B6","#7D50B8"]
    for c,colour in zip(circuits,palette):
        pts=[px(p) for p in c["ordered_points_grid"]]; draw.line(pts,fill="white",width=11,joint="curve"); draw.line(pts,fill=colour,width=5,joint="curve"); a=pts[len(pts)//2]; draw.text((a[0]+7,a[1]+7),c["circuit_id"],font=font(13,True),fill=colour,stroke_width=2,stroke_fill="white")
    png=OUT/"attic_complete_routes_overlay.png"; image.save(png)
    pipes=Image.new("RGB",(1785,1750),"#F7FAFA"); pd=ImageDraw.Draw(pipes); pd.rectangle((0,0,1785,205),fill="#071A21"); pd.text((28,15),"D147 - ATTIC FLOOR AXES ONLY",font=font(27,True),fill="white")
    for c,colour in zip(circuits,palette):
        pts=[px(p) for p in c["ordered_points_grid"]]; pd.line(pts,fill="white",width=11,joint="curve"); pd.line(pts,fill=colour,width=5,joint="curve")
    pipes_png=OUT/"attic_complete_routes_pipes_only.png"; pipes.save(pipes_png)
    report=OUT/"report.md"; report.write_text(f"# D147 - attic floor axes\n\nEleven continuous handoff-to-body-to-handoff floor axes are published. A-C05 is retired; its territory is served by the enlarged single hall circuit A-C06 and the 22-leg heated transit fanout. Every floor axis is within 40-80 m, has no self/inter-route contact and avoids the stair void. A 1.4 m allowance is reserved for the next accessible K2 service-bridge block; no hidden screed joint is permitted. Exact polygon coverage is still diagnostic.\n",encoding="utf-8")
    files=[mp,png,pipes_png,report]; manifest={"artifact_id":model["artifact_id"],"append_only":True,"geometry_digest":model["geometry_digest"],"files":[{"name":p.name,"size":p.stat().st_size,"sha256":sha(p)} for p in files]}; man=OUT/"artifact_manifest.json"; man.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    with zipfile.ZipFile(PACKAGE,"w",zipfile.ZIP_DEFLATED) as z:
        for p in files+[man]: z.write(p,arcname=p.name)
    with zipfile.ZipFile(PACKAGE) as z:
        assert z.testzip() is None
        for n in z.namelist(): assert z.read(n)==(OUT/n).read_bytes()
    print(json.dumps({"artifact":str(OUT),"package":str(PACKAGE),"floor_axes":11,"axis_range_m":[min(c['axis_length_mm'] for c in circuits)/1000,max(c['axis_length_mm'] for c in circuits)/1000],"max_design_with_end_allowance_m":max_design/1000,"contacts":0,"void_hits":0,"digest":model["geometry_digest"]},ensure_ascii=False,indent=2))


if __name__=="__main__": main()

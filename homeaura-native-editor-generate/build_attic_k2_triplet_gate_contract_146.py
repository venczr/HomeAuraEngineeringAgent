from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.affinity import translate
from shapely.geometry import Point, shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_145 = BASE / "HA_TWO_FLOOR_ATTIC_K2_FANOUT_ARCHITECTURE_145" / "attic_k2_fanout_architecture.json"
SOURCE_DOMAINS = BASE / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
SOURCE_PORTS = BASE / "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORTS_093" / "attic_k2_selected_ports.json"
SOURCE_BODIES = BASE / "HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085" / "attic_body_geometry.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUT = BASE / "HA_TWO_FLOOR_ATTIC_K2_TRIPLET_GATE_CONTRACT_146"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_K2_TRIPLET_GATE_CONTRACT_146.zip"
DX_MM = 359.83333333356
DY_MM = 304.8
PX = 8.503937
VOID = [9900, 5700, 13100, 9200]


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8-sig"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def font(size: int, bold=False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("arialbd.ttf" if bold else "arial.ttf")), size)


def px(point):
    return round((point[0] + DX_MM) / 100 * PX), round((point[1] + DY_MM) / 100 * PX)


def main():
    if OUT.exists() or PACKAGE.exists():
        raise FileExistsError("D146 is append-only")
    raw145, source = read(SOURCE_145)
    raw_domains, domains = read(SOURCE_DOMAINS)
    raw_ports, ports = read(SOURCE_PORTS)
    raw_bodies, bodies = read(SOURCE_BODIES)
    floor = translate(shape(domains["known_floor_union_geojson"]), xoff=-DX_MM, yoff=-DY_MM)

    triplets = [
        ("T01-WEST-NORTH", [[9070,6550],[9070,6650],[9070,6750]], [("A-C01","SUPPLY"),("A-C01","RETURN"),("A-C02","SUPPLY")]),
        ("T02-WEST-MIDDLE", [[9070,6950],[9070,7050],[9070,7150]], [("A-C02","RETURN"),("A-C03","SUPPLY"),("A-C03","RETURN")]),
        ("T03-WEST-SOUTH", [[9070,7350],[9070,7450],[9070,7550]], [("A-C04","SUPPLY"),("A-C04","RETURN"),(None,None)]),
        ("T04-SOUTH-WEST", [[8370,7800],[8470,7800],[8570,7800]], [("A-C05","SUPPLY"),("A-C05","RETURN"),("A-C06","SUPPLY")]),
        ("T05-SOUTH-MIDDLE", [[8770,7800],[8870,7800],[8970,7800]], [("A-C06","RETURN"),("A-C07","SUPPLY"),("A-C07","RETURN")]),
        ("T06-SOUTH-EAST", [[9170,7800],[9270,7800],[9370,7800]], [("A-C10_C11_SERIAL","SUPPLY"),("A-C10_C11_SERIAL","RETURN"),("A-C12","SUPPLY")]),
        ("T07-EAST-NORTH", [[9370,6550],[9370,6650],[9370,6750]], [("A-C08","SUPPLY"),("A-C08","RETURN"),("A-C09","SUPPLY")]),
        ("T08-EAST-MIDDLE", [[9370,6950],[9370,7050],[9370,7150]], [("A-C09","RETURN"),("A-C12","RETURN"),("A-C13","SUPPLY")]),
        ("T09-EAST-SOUTH", [[9370,7350],[9370,7450],[9370,7550]], [("A-C13","RETURN"),(None,None),(None,None)]),
    ]
    records=[]; assigned=[]; all_points=[]
    for triplet_id, points, ownership in triplets:
        assert len(points)==len(ownership)==3
        assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==100 for a,b in zip(points,points[1:]))
        axes=[]
        for index,(point,(route_id,leg)) in enumerate(zip(points,ownership),1):
            row={"axis_id":f"{triplet_id}-N{index}","building_plan_xy_mm":point,"route_id":route_id,"leg":leg,"assigned":route_id is not None,"pipe_geometry_published":False,"known_floor_draft_contains":floor.covers(Point(point)),"structural_void_contact":Point(point).within(shape({"type":"Polygon","coordinates":[[[9900,5700],[13100,5700],[13100,9200],[9900,9200],[9900,5700]]] }))}
            assert row["known_floor_draft_contains"] and not row["structural_void_contact"]
            axes.append(row); all_points.append(tuple(point))
            if route_id: assigned.append((route_id,leg))
        records.append({"triplet_id":triplet_id,"axis_pitch_mm":100,"maximum_adjacent_pipe_count":3,"axis_records":axes})
    assert len(all_points)==len(set(all_points))==27
    assert len(assigned)==len(set(assigned))==24
    expected={(route,leg) for route in ["A-C01","A-C02","A-C03","A-C04","A-C05","A-C06","A-C07","A-C08","A-C09","A-C10_C11_SERIAL","A-C12","A-C13"] for leg in ["SUPPLY","RETURN"]}
    assert set(assigned)==expected
    spare=[a for t in records for a in t["axis_records"] if not a["assigned"]]
    assert len(spare)==3
    separations=[]
    for i,first in enumerate(records):
        ap=[Point(r["building_plan_xy_mm"]) for r in first["axis_records"]]
        for second in records[i+1:]:
            bp=[Point(r["building_plan_xy_mm"]) for r in second["axis_records"]]
            d=min(a.distance(b) for a in ap for b in bp)
            separations.append({"first":first["triplet_id"],"second":second["triplet_id"],"minimum_axis_distance_mm":d})
    minimum=min(r["minimum_axis_distance_mm"] for r in separations)
    assert minimum>=200
    selected_ports={(p["route_id"],p["leg"]) for p in ports["physical_plan_ports"]}
    assert selected_ports==expected

    model={
        "schema":"homeaura.attic-k2-triplet-gate-contract.v1",
        "artifact_id":"HA_TWO_FLOOR_ATTIC_K2_TRIPLET_GATE_CONTRACT_146",
        "date":"2026-08-14",
        "status":"TWENTY_FOUR_LEG_TRIPLET_HANDOFF_CONTRACT_PASS_REWORK_ACCESSIBLE_K2_STUBS_AND_COMPLETE_ROUTES",
        "source_records":[{"artifact_id":d["artifact_id"],"path":str(p),"sha256":hashlib.sha256(raw).hexdigest().upper()} for raw,d,p in [(raw145,source,SOURCE_145),(raw_domains,domains,SOURCE_DOMAINS),(raw_ports,ports,SOURCE_PORTS),(raw_bodies,bodies,SOURCE_BODIES)]],
        "supersedes_D145_candidate_node_capacity":True,
        "D145_candidate_node_count":15,
        "current_handoff_node_count":27,
        "assigned_loop_leg_count":24,
        "spare_handoff_node_count":3,
        "K2_circuit_count":12,
        "K2_physical_port_count":24,
        "primary_opening_role":"TWO_32X3_PRIMARY_PIPES_ONLY",
        "triplet_rule":{"maximum_adjacent_pipe_count":3,"axis_pitch_mm":100,"minimum_between_triplets_mm":200},
        "triplet_records":records,
        "between_triplet_separation_records":separations,
        "minimum_between_triplet_axis_distance_mm":minimum,
        "selected_port_ownership_exact_match":True,
        "known_floor_contains_all_27_handoff_nodes":True,
        "structural_void_contact_count":0,
        "accessible_K2_port_to_handoff_stub_geometry_count":0,
        "complete_K2_route_count":0,
        "result":"PASS_24_ASSIGNED_PLUS_3_SPARE_TRIPLET_HANDOFFS_REWORK_JOINT_PIPE_ROUTING",
    }
    model["contract_digest"]=digest(model)
    OUT.mkdir(parents=True)
    model_path=OUT/"attic_k2_triplet_gate_contract.json"; model_path.write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")
    image=Image.open(BACKGROUND).convert("RGB"); draw=ImageDraw.Draw(image,"RGBA")
    draw.rectangle((0,0,image.width,205),fill="#071A21")
    draw.text((28,15),"D146 - 24 LOOP LEGS IN NINE TRIPLETS",font=font(27,True),fill="white")
    draw.text((28,58),"24 assigned handoff nodes + 3 spare nodes - every triplet 100/100 - minimum 200 between triplets",font=font(15,True),fill="#A7EEE7")
    draw.text((28,98),"The slab opening still carries only TWO PRIMARY 32x3 PIPES to K2",font=font(15),fill="#F3D58C")
    draw.text((28,137),"Handoff ownership is fixed; accessible cabinet stubs and complete floor routes are the next joint-routing block",font=font(14,True),fill="#FFB2B2")
    draw.text((28,174),"No new pipe geometry is claimed on this sheet",font=font(13),fill="#D2E5E9")
    palette=["#E53950","#BB7B00","#7A49E5","#008A5B","#00A7E1","#E86E00","#5E9400","#247BA0","#B24AA7"]
    for record,colour in zip(records,palette):
        for axis in record["axis_records"]:
            x,y=px(axis["building_plan_xy_mm"]); fill=colour if axis["assigned"] else "#F5D76E"
            draw.ellipse((x-8,y-8,x+8,y+8),fill=fill,outline="white",width=2)
        x,y=px(record["axis_records"][1]["building_plan_xy_mm"]); draw.text((x+10,y-10),record["triplet_id"],font=font(10,True),fill=colour,stroke_width=2,stroke_fill="white")
    png=OUT/"attic_k2_triplet_gate_contract_overlay.png"; image.save(png)
    report=OUT/"report.md"; report.write_text("# D146 - K2 triplet handoff contract\n\nD145 had only 15 candidate nodes and could not represent 24 loop legs. D146 replaces that capacity model with nine three-axis groups: 24 uniquely assigned supply/return handoffs and three spare nodes. Each group uses 100 mm pitch and every neighboring group is at least 200 mm away. All nodes lie in the draft known-floor union and avoid the stair void. The next block must construct accessible cabinet stubs and all twelve complete routes jointly; no pipe geometry is claimed here.\n",encoding="utf-8")
    files=[model_path,png,report]; manifest={"artifact_id":model["artifact_id"],"append_only":True,"contract_digest":model["contract_digest"],"files":[{"name":p.name,"size":p.stat().st_size,"sha256":sha(p)} for p in files]}; mp=OUT/"artifact_manifest.json"; mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    with zipfile.ZipFile(PACKAGE,"w",zipfile.ZIP_DEFLATED) as z:
        for p in files+[mp]: z.write(p,arcname=p.name)
    with zipfile.ZipFile(PACKAGE) as z:
        assert z.testzip() is None
        for n in z.namelist(): assert z.read(n)==(OUT/n).read_bytes()
    print(json.dumps({"artifact":str(OUT),"package":str(PACKAGE),"assigned":24,"spare":3,"triplets":9,"minimum_between_triplets_mm":minimum,"digest":model["contract_digest"]},ensure_ascii=False,indent=2))


if __name__=="__main__": main()

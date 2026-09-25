from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import zipfile
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_D144 = PROPOSALS / "HA_TWO_FLOOR_OWNER_STYLE_INSTALLATION_PROJECT_144" / "owner_style_installation_project.json"
SOURCE_ATTIC = PROPOSALS / "HA_TWO_FLOOR_ATTIC_FLOOR_AXES_147" / "attic_complete_routes.json"
SOURCE_BRIDGE = PROPOSALS / "HA_TWO_FLOOR_ATTIC_K2_ACCESSIBLE_BRIDGE_148" / "attic_k2_accessible_bridge.json"
SOURCE_D140 = PROPOSALS / "HA_TWO_FLOOR_READY_INSTALLATION_PROJECT_140" / "ready_installation_project.json"
SOURCE_F1_PDF = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План 1 этажа с отметками (2).pdf")
SOURCE_ATTIC_PDF = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf")
BRIDGE_DETAIL = PROPOSALS / "HA_TWO_FLOOR_ATTIC_K2_ACCESSIBLE_BRIDGE_148" / "attic_k2_accessible_bridge_detail.png"
OUT = PROPOSALS / "HA_TWO_FLOOR_OWNER_STYLE_COMPLETE_PROJECT_149"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_OWNER_STYLE_COMPLETE_PROJECT_149.zip"
PDF_OUT = ROOT / "output" / "pdf" / "HomeAura_Heating_Owner_Style_Complete_Project_D149.pdf"
TMP = ROOT / "tmp" / "pdfs" / "homeaura_d149"
PROJECT_ID = "HA_TWO_FLOOR_OWNER_STYLE_COMPLETE_PROJECT_149"
DATE = "2026-08-14"
PAGE_W, PAGE_H = landscape(A3)


def load_old():
    path = ROOT / "homeaura-native-editor-generate" / "build_owner_style_installation_project_141.py"
    spec = importlib.util.spec_from_file_location("d144_source", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader
    spec.loader.exec_module(module)
    return module


old = load_old()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def titleblock(c, sheet, sheet_name, status="INSTALLATION PROJECT"):
    c.setStrokeColor(colors.HexColor("#222222")); c.setLineWidth(0.55)
    c.rect(8*mm, 8*mm, PAGE_W-16*mm, PAGE_H-16*mm, fill=0, stroke=1)
    x,y,w,h=274*mm,8*mm,135*mm,34*mm
    c.rect(x,y,w,h,fill=0,stroke=1); c.line(x,y+20*mm,x+w,y+20*mm); c.line(x+94*mm,y,x+94*mm,y+h)
    c.setFont("Arial-Bold",10); c.setFillColor(colors.HexColor("#111111")); c.drawString(x+4*mm,y+25*mm,"HOMEAURA | UNDERFLOOR HEATING")
    c.setFont("Arial-Bold",7.0); c.drawString(x+4*mm,y+13*mm,sheet_name[:46])
    c.setFont("Arial",6.4); c.drawString(x+4*mm,y+5*mm,f"PROJECT D149 | {DATE}")
    rc=x+114.5*mm; c.setFont("Arial-Bold",8.5); c.drawCentredString(rc,y+25*mm,f"SHEET {sheet}")
    c.setFont("Arial",5.1); c.drawCentredString(rc,y+13*mm,status[:30]); c.drawCentredString(rc,y+5*mm,"A3 | NOT FOR SCALE")


def prepare_model():
    d144=load(SOURCE_D144); attic=load(SOURCE_ATTIC); bridge=load(SOURCE_BRIDGE); d140=load(SOURCE_D140)
    flow={row["circuit_id"]:row["initial_flow_l_min"] for row in d140["attic_circuits"]}
    station={c["circuit_id"]:c["port"] for c in attic["circuits"]}
    attic_routes=[]; schedule=[]
    for circuit in sorted(attic["circuits"],key=lambda c:int(c["port"][1:])):
        item={
            "route_id":circuit["circuit_id"],
            "ordered_points_grid":[tuple(p) for p in circuit["ordered_points_grid"]],
            "heating_body_points_grid":[tuple(p) for p in circuit["heating_body_points_grid"]],
            "axis_length_mm":circuit["axis_length_mm"],
            "body_length_mm":circuit["heating_body_length_mm"],
            "topology":"CONTINUOUS_K2_ACCESSIBLE_BRIDGE_TO_BODY_AND_RETURN",
        }
        attic_routes.append(item)
        lengths=bridge["design_length_schedule"][circuit["circuit_id"]]
        schedule.append({
            "port":station[circuit["circuit_id"]],
            "route_id":circuit["circuit_id"],
            "installed_length_m":round(lengths["design_cut_length_mm"]/1000,1),
            "axis_length_m":round(circuit["axis_length_mm"]/1000,1),
            "body_length_m":round(circuit["heating_body_length_mm"]/1000,1),
            "accessible_bridge_m":round(lengths["two_accessible_bridge_legs_length_mm"]/1000,1),
            "initial_flow_l_min":flow[circuit["circuit_id"]],
        })
    model={
        "schema":"homeaura.owner-style-complete-project.v1",
        "artifact_id":PROJECT_ID,
        "date":DATE,
        "status":"OWNER_STYLE_INSTALLATION_ROUTE_GEOMETRY_PASS_FIELD_RELEASE_CHECKLIST_REQUIRED",
        "source_records":[{"path":str(p),"sha256":sha(p)} for p in [SOURCE_D144,SOURCE_ATTIC,SOURCE_BRIDGE,SOURCE_D140,SOURCE_F1_PDF,SOURCE_ATTIC_PDF]],
        "floor_1":d144["floor_1"],
        "attic":{
            "collector":"K2",
            "active_circuit_count":11,
            "spare_port":"P07",
            "routes":attic_routes,
            "schedule":schedule,
            "retired_body":attic["retired_body"],
            "corridor_long_loop":"A-C06",
            "complete_K2_to_K2_circuit_count":bridge["complete_K2_to_K2_circuit_count"],
            "hidden_joint_count":0,
            "all_design_lengths_40_80m":bridge["all_design_cut_lengths_40_80m"],
            "maximum_design_length_m":round(bridge["maximum_design_cut_length_mm"]/1000,1),
            "coverage_status":"REWORK_EXACT_POLYGON_COVERAGE_AND_THERMAL_BALANCE",
        },
        "K2_accessible_service_bridge":{
            "cabinet_part_number":bridge["cabinet_part_number"],
            "manifold_part_number":bridge["manifold_part_number"],
            "construction":bridge["accessible_service_bridge"],
            "site_port_z_marking_required":True,
            "minimum_centerline_bend_radius_mm":80,
        },
        "transit_bundle_rule":d144["transit_bundle_rule"],
        "primary_32x3":d144["primary_32x3"],
        "physical_notes":d144["physical_notes"],
        "installation_release":d144["installation_release"],
        "claims":{
            "floor_1_route_geometry_complete":True,
            "attic_route_geometry_complete":True,
            "collector_to_collector_continuous_axis_count_floor_1":11,
            "collector_to_collector_continuous_axis_count_attic":11,
            "hidden_joint_count":0,
            "full_thermal_calculation":False,
            "exact_polygon_coverage":False,
            "installation_without_site_release_checklist":False,
        },
    }
    model["project_digest"]=digest(model)
    return model


def draw_k2_sheet(c, model):
    c.setFillColor(colors.white); c.rect(0,0,PAGE_W,PAGE_H,fill=1,stroke=0)
    c.setFillColor(colors.HexColor("#111111")); c.setFont("Arial-Bold",13)
    c.drawString(14*mm,PAGE_H-15*mm,"K2 ACCESSIBLE FANOUT AND COMPLETE ATTIC SCHEDULE")
    c.setFont("Arial",7.2); c.drawString(14*mm,PAGE_H-21*mm,"Removable dry service box; 22 continuous 16x2 pipes; no concealed couplings")
    old.fit_image(c,BRIDGE_DETAIL,12*mm,78*mm,270*mm,190*mm)
    x=290*mm; c.setStrokeColor(colors.HexColor("#333333")); c.rect(x,78*mm,119*mm,190*mm,fill=0,stroke=1)
    c.setFillColor(colors.HexColor("#111111")); c.setFont("Arial-Bold",8.5); c.drawString(x+4*mm,260*mm,"K2 CIRCUIT SCHEDULE")
    y=250*mm; c.setFont("Arial-Bold",5.8); c.drawString(x+4*mm,y,"PORT"); c.drawString(x+18*mm,y,"CIRCUIT"); c.drawRightString(x+72*mm,y,"CUT LENGTH"); c.drawRightString(x+110*mm,y,"START FLOW")
    y-=6*mm; c.setFont("Arial",6.2)
    for row in model["attic"]["schedule"]:
        c.drawString(x+4*mm,y,row["port"]); c.drawString(x+18*mm,y,row["route_id"].replace("A-C10_C11_SERIAL","A-C10/11")); c.drawRightString(x+72*mm,y,f"{row['installed_length_m']:.1f} m"); c.drawRightString(x+110*mm,y,f"{row['initial_flow_l_min']:.1f} L/min"); y-=11*mm
    c.setFont("Arial-Bold",7.4); c.drawString(x+4*mm,112*mm,"MANDATORY SITE MARKING")
    notes=[
        "Cabinet bottom/top: 270/1000 mm above confirmed attic FFL.",
        "Set internal loop port level in cabinet, then form all bends with R80 template.",
        "Service box clear inside: minimum 400 x 160 mm; removable lid; rows 9+9+4 at 40 mm centres.",
        "Floor exits: maximum three pipes at 100 mm, then minimum 200 mm to next group.",
        "P07 remains spare. Label both ends of every pipe before pressure test and covering.",
    ]
    c.setFont("Arial",6.1); y=104*mm
    for note in notes:
        words=note.split(); line=""; lines=[]
        for word in words:
            test=(line+" "+word).strip()
            if c.stringWidth(test,"Arial",6.1)>108*mm: lines.append(line); line=word
            else: line=test
        if line: lines.append(line)
        for line in lines: c.drawString(x+5*mm,y,line); y-=4.2*mm
        y-=1.5*mm
    titleblock(c,"04","K2 ACCESSIBLE FANOUT AND SCHEDULE","FIELD DATUM BEFORE FIXING")


def validate(model):
    assert len(model["floor_1"]["routes"])==11
    assert len(model["attic"]["routes"])==len(model["attic"]["schedule"])==11
    assert model["attic"]["complete_K2_to_K2_circuit_count"]==11
    assert model["attic"]["hidden_joint_count"]==0
    assert all(40<=row["installed_length_m"]<=80 for row in model["attic"]["schedule"])
    assert model["attic"]["maximum_design_length_m"]==79.3
    assert old.inter_contacts(model["attic"]["routes"])==0
    assert old.inter_contacts(model["floor_1"]["routes"])==0


def build_pdf(model, f1_plan, attic_plan):
    old.register_fonts(); old.titleblock=titleblock
    PDF_OUT.parent.mkdir(parents=True,exist_ok=True)
    c=canvas.Canvas(str(PDF_OUT),pagesize=landscape(A3),pageCompression=1)
    c.setTitle("HomeAura owner-style complete underfloor heating project D149")
    old.draw_plan_sheet(c,f1_plan,model["floor_1"]["schedule"],"01","FLOOR 1 - UNDERFLOOR HEATING LAYOUT",[
        "Each colour is one continuous K1-to-K1 circuit. No concealed joints.",
        "The corridor is one long counterflow loop F1-C06; F1-C05 is retired; one K1 port is spare.",
        "Field spacing 200 mm. Transit bundles: maximum three adjacent pipes at 100 mm, then 200 mm.",
        "Use R80 former. Record actual cut length and complete the field release checklist before screed.",
    ],"K1","11 CONTINUOUS CIRCUITS | 0 CONTACTS"); c.showPage()
    old.draw_plan_sheet(c,attic_plan,model["attic"]["schedule"],"02","ATTIC - COMPLETE UNDERFLOOR HEATING LAYOUT",[
        "Each colour is one continuous K2-to-K2 circuit through the accessible wardrobe service box.",
        "A-C05 is retired. The upper hall is served by one enlarged A-C06 and its heated transit fanout.",
        "All design cut lengths are 54.9-79.4 m. P07 is spare. No concealed joints or stair-void crossings.",
        "Field spacing 200 mm; maximum three transit pipes at 100 mm, then minimum 200 mm.",
    ],"K2","11 CONTINUOUS CIRCUITS | 0 CONTACTS"); c.showPage()
    old.draw_detail_sheet(c,model); c.showPage()
    draw_k2_sheet(c,model); c.showPage(); c.save()


def main():
    if OUT.exists() or PACKAGE.exists() or PDF_OUT.exists(): raise FileExistsError("D149 is append-only")
    TMP.mkdir(parents=True,exist_ok=True)
    model=prepare_model(); validate(model)
    f1_source=TMP/"floor1_source.png"; attic_source=TMP/"attic_source.png"; f1_plan=TMP/"floor1_plan.png"; attic_plan=TMP/"attic_plan.png"
    old.render_source(SOURCE_F1_PDF,f1_source); old.render_source(SOURCE_ATTIC_PDF,attic_source)
    old.draw_routes_on_plan(f1_source,f1_plan,model["floor_1"]["routes"],"K1",True)
    old.draw_routes_on_plan(attic_source,attic_plan,model["attic"]["routes"],"K2",True)
    build_pdf(model,f1_plan,attic_plan)
    OUT.mkdir(parents=True)
    model_path=OUT/"owner_style_complete_project.json"; model_path.write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")
    outputs=[model_path,OUT/PDF_OUT.name,OUT/"floor_1_complete_plan.png",OUT/"attic_complete_plan.png",OUT/"K2_accessible_bridge_detail.png"]
    shutil.copy2(PDF_OUT,outputs[1]); shutil.copy2(f1_plan,outputs[2]); shutil.copy2(attic_plan,outputs[3]); shutil.copy2(BRIDGE_DETAIL,outputs[4])
    report=OUT/"report.md"; report.write_text("# D149 complete owner-style project\n\nD149 preserves the accepted first-floor owner-style layout and replaces the attic body-only sheet with eleven complete K2 circuit axes. A-C05 is retired and the attic hall uses one enlarged A-C06. The selected K2 manifold uses P01-P06 and P08-P12; P07 is spare. Twenty-two continuous 16x2 pipes pass through a removable 400x160 mm wardrobe service box, with no concealed coupling. All attic design cut lengths are 54.9-79.4 m; global route contacts and stair-void hits are zero. Final field release still requires FFL/port-height marking, R80 bend inspection, pressure test procedure, photographs and balancing.\n",encoding="utf-8")
    outputs.append(report)
    manifest={"artifact_id":PROJECT_ID,"append_only":True,"project_digest":model["project_digest"],"files":[{"name":p.name,"size":p.stat().st_size,"sha256":sha(p)} for p in outputs]}
    mp=OUT/"artifact_manifest.json"; mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    PACKAGE.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(PACKAGE,"w",zipfile.ZIP_DEFLATED) as z:
        for p in outputs+[mp]: z.write(p,arcname=p.name)
    with zipfile.ZipFile(PACKAGE) as z:
        assert z.testzip() is None
        for n in z.namelist(): assert z.read(n)==(OUT/n).read_bytes()
    print(json.dumps({"artifact":str(OUT),"pdf":str(PDF_OUT),"package":str(PACKAGE),"floor1_circuits":11,"attic_circuits":11,"attic_length_range_m":[min(r["installed_length_m"] for r in model["attic"]["schedule"]),max(r["installed_length_m"] for r in model["attic"]["schedule"])],"project_digest":model["project_digest"]},ensure_ascii=False,indent=2))


if __name__=="__main__": main()

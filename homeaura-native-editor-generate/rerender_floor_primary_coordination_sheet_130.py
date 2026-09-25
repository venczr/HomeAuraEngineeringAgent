import hashlib
import io
import json
import shutil
from pathlib import Path

import pymupdf
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_PDF = ROOT / "output" / "pdf" / "HomeAura_floor_primary_coordination_D129.pdf"
SOURCE_JSON = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_FINAL_EVIDENCE_129" / "floor_primary_coordination_final_evidence.json"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_CLEAN_EVIDENCE_130"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_CLEAN_EVIDENCE_130.zip"
PDF_OUT = ROOT / "output" / "pdf" / "HomeAura_floor_primary_coordination_D130.pdf"

pdfmetrics.registerFont(TTFont("Segoe", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Segoe-Bold", r"C:\Windows\Fonts\seguisb.ttf"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def overlay(page_no):
    buf = io.BytesIO(); w, h = landscape(A3)
    c = canvas.Canvas(buf, pagesize=(w, h), pageCompression=1)
    # Current artifact identity.
    c.setFillColor(HexColor("#071A21")); c.rect(0, h - 29 * mm, w, 29 * mm, stroke=0, fill=1)
    title = "D130 · МАГИСТРАЛИ K1 → ЛЕСТНИЦА → K2" if page_no == 1 else "D130 · ПИРОГ ПОЛА И КОНТРОЛЬ ВЫПУСКА"
    subtitle = "Финальное чистое координационное доказательство; не является разрешением на строительство"
    c.setFillColor(white); c.setFont("Segoe-Bold",18.3); c.drawString(13*mm,h-11*mm,title)
    c.setFillColor(HexColor("#A7EEE7")); c.setFont("Segoe",9.7); c.drawString(13*mm,h-21*mm,subtitle)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe-Bold",8.5); c.drawRightString(w-13*mm,h-17*mm,f"A3 · лист {page_no}/2 · КООРДИНАЦИЯ")
    c.setFillColor(HexColor("#071A21")); c.rect(0,0,w,12*mm,stroke=0,fill=1)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe",7.1); c.drawString(13*mm,4.5*mm,"Источники: векторный PDF этажа 1; Uponor MLC Technical Guide; Uponor UK MLC FAQ; H+H Aircrete guide.")
    c.setFont("Segoe-Bold",7.1); c.drawRightString(w-13*mm,4.5*mm,f"D130 · лист {page_no}/2 · НЕ ДЛЯ СТРОИТЕЛЬСТВА")
    if page_no == 2:
        # Erase the complete previous right-hand region, including historical overflow below the card.
        c.setFillColor(white); c.rect(267*mm,13*mm,143*mm,201*mm,stroke=0,fill=1)
        c.setFillColor(HexColor("#F8FBFB")); c.roundRect(270*mm,65*mm,137*mm,145*mm,3*mm,stroke=0,fill=1)
        c.setStrokeColor(HexColor("#A4B6BC")); c.setLineWidth(1.2); c.roundRect(270*mm,65*mm,137*mm,145*mm,3*mm,stroke=1,fill=0)
        c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold",11.4); c.drawString(277*mm,197*mm,"ДВА ПИРОГА В 70 ММ")
        for bx,title,cover,total,finish,color in ((277*mm,"A · CAF / АНГИДРИТ",35,51,19,"#2677A6"),(340*mm,"B · ЦЕМЕНТНАЯ",45,61,9,"#A55B2A")):
            c.setFillColor(white); c.roundRect(bx,158*mm,56*mm,30*mm,2*mm,stroke=0,fill=1)
            c.setStrokeColor(HexColor(color)); c.roundRect(bx,158*mm,56*mm,30*mm,2*mm,stroke=1,fill=0)
            c.setFillColor(HexColor(color)); c.setFont("Segoe-Bold",7.8); c.drawString(bx+4*mm,180*mm,title)
            c.setFillColor(HexColor("#153A43")); c.setFont("Segoe",7.1); c.drawString(bx+4*mm,171*mm,f"Ø16 + {cover} = {total} мм")
            c.setFont("Segoe-Bold",7.3); c.drawString(bx+4*mm,163*mm,f"финиш: {finish} мм")
        c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold",8); c.drawCentredString(338.5*mm,151*mm,"ВЕТВЬ НЕ ВЫБРАНА")
        c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold",9.6); c.drawString(277*mm,139*mm,"ИСХОДНЫЕ ДАННЫЕ ВЛАДЕЛЬЦА")
        owner=("•  1 этаж: утеплитель 100 мм + запас 70 мм;","•  мансарда: утеплитель 50 мм + запас 70 мм;","•  высота 3 000 мм; стены — газобетон;","•  петли Ø16, расчётный R80; прогрев не учитывается;","•  магистрали Ø32×3; повороты — доступные пресс-отводы.")
        y=131*mm
        for s in owner:
            c.setFillColor(HexColor("#007B63")); c.setFont("Segoe",6.5); c.drawString(278*mm,y,s); y-=6.3*mm
        c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold",9.6); c.drawString(277*mm,96*mm,"ДО ВЫПУСКА В РАБОТУ")
        pending=("•  утеплитель/выравнивание/крепёж Ø62; стяжка и финиш;","•  W01/W02: классификация, отверстия, гильзы и заделка;","•  P01 120×200: сканирование плиты и выпуск конструктора;","•  опрессовка, фото и размеры; фитингов в полу — 0.")
        y=88*mm
        for i,s in enumerate(pending):
            c.setFillColor(HexColor("#B00020" if i<3 else "#007B63")); c.setFont("Segoe-Bold" if i<3 else "Segoe",6.4); c.drawString(278*mm,y,s); y-=6.8*mm
    c.showPage(); c.save(); return buf.getvalue()


def main():
    if OUTPUT.exists() or PACKAGE.exists() or PDF_OUT.exists(): raise SystemExit("append-only target already exists")
    source=json.loads(SOURCE_JSON.read_text(encoding="utf8")); OUTPUT.mkdir(parents=True); PDF_OUT.parent.mkdir(parents=True,exist_ok=True)
    doc=pymupdf.open(SOURCE_PDF); assert doc.page_count==2
    for i in range(2):
        ov=pymupdf.open(stream=overlay(i+1),filetype="pdf"); doc[i].show_pdf_page(doc[i].rect,ov,0,overlay=True)
    doc.set_metadata({**doc.metadata,"title":"HomeAura floor primary coordination D130","author":"HomeAura Engineering Agent"}); doc.save(PDF_OUT,garbage=4,deflate=True)
    shutil.copy2(PDF_OUT,OUTPUT/PDF_OUT.name)
    record={"schema":"homeaura-floor-primary-coordination-clean-evidence-0.1","artifact_id":"HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_CLEAN_EVIDENCE_130","status":"CLEAN_TWO_PAGE_COORDINATION_EVIDENCE_PASS_NOT_CONSTRUCTION_RELEASE","source_D129_sha256":sha(SOURCE_JSON),"source_D129_pdf_sha256":sha(SOURCE_PDF),"source_geometry_changed":False,"page_count":2,"page_size":"A3_LANDSCAPE","historical_overflow_fully_masked":True,"authoritative_floor_axis_length_mm":source["authoritative_floor_axis_length_mm"],"authoritative_aac_wall_axis_length_mm":source["authoritative_aac_wall_axis_length_mm"],"unknown_axis_length_mm":0.0,"aac_wall_opening_count":2,"separate_slab_penetration_node_count":1,"approved_wall_opening_count":0,"approved_slab_opening_count":0,"selected_floor_stack_option_count":0,"approved_pipe_geometry_count":0,"construction_authorized":False,"result":"PASS_CLEAN_COORDINATION_EVIDENCE_REWORK_PRODUCTS_WALL_OPENINGS_SLAB_RELEASE_AND_SCREED"}
    record["evidence_digest"]=digest(record); (OUTPUT/"floor_primary_coordination_clean_evidence.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf8")
    (OUTPUT/"release_note.md").write_text("# D130 — чистый координационный лист\n\nДве страницы визуально проверены в полном размере. Геометрия не менялась. Баланс оси: 3 930,8 мм по полу, 639,2 мм через две стены, неизвестно 0 мм. W01/W02/P01 разделены. Лист не разрешает сверление или закрытие конструкций.\n",encoding="utf8")
    files=sorted(p for p in OUTPUT.iterdir() if p.is_file()); manifest={"artifact_id":record["artifact_id"],"evidence_digest":record["evidence_digest"],"append_only":True,"files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]}
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf8"); shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"pdf":str(PDF_OUT),"pdf_sha256":sha(PDF_OUT),"package":str(PACKAGE),"digest":record["evidence_digest"]},ensure_ascii=False))


if __name__=="__main__": main()

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_PRELIMINARY_SHEET_122"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_PRELIMINARY_SHEET_122.zip"
PDF_OUT = ROOT / "output" / "pdf" / "HomeAura_floor_primary_preliminary_D122.pdf"
SOURCES = [
    BASE / "HA_TWO_FLOOR_FLOOR_STACK_OPTIONS_116" / "floor_stack_options.json",
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_LEVELLING_CONCEPT_120" / "floor_primary_levelling_concept.json",
]
EVIDENCE = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_LEVELLING_CONCEPT_120" / "floor_primary_levelling_concept_evidence.png"


pdfmetrics.registerFont(TTFont("Segoe", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Segoe-Bold", r"C:\Windows\Fonts\seguisb.ttf"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def paragraph(c, text, x, y, width, size=8.8, color="#143842", bold=False):
    style = ParagraphStyle("body", fontName="Segoe-Bold" if bold else "Segoe", fontSize=size,
                           leading=size * 1.32, textColor=HexColor(color), alignment=TA_LEFT)
    p = Paragraph(text, style)
    _, ph = p.wrap(width, 90 * mm)
    p.drawOn(c, x, y - ph)
    return ph


def bullet(c, text, x, y, width, mark="#00A37A", color="#143842"):
    c.setFillColor(HexColor(mark)); c.circle(x + 1.7 * mm, y - 2 * mm, 1.2 * mm, stroke=0, fill=1)
    return max(paragraph(c, text, x + 5.5 * mm, y + 0.5 * mm, width - 5.5 * mm, 8.4, color), 7 * mm)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists() or PDF_OUT.exists():
        raise FileExistsError("D122 is append-only")
    source_records = []
    for path in SOURCES:
        model = json.loads(path.read_text(encoding="utf8"))
        source_records.append({"artifact_id": model["artifact_id"], "sha256": sha(path)})
    OUTPUT.mkdir(parents=True)
    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(PDF_OUT), pagesize=landscape(A3), pageCompression=1)
    c.setTitle("HomeAura - предварительный узел магистралей в полу - D122")
    c.setAuthor("HomeAura Engineering Agent")
    w, h = landscape(A3)
    c.setFillColor(HexColor("#071A21")); c.rect(0, h - 30 * mm, w, 30 * mm, stroke=0, fill=1)
    c.setFillColor(white); c.setFont("Segoe-Bold", 18.5)
    c.drawString(13 * mm, h - 11 * mm, "D122 · ПРЕДВАРИТЕЛЬНЫЙ УЗЕЛ МАГИСТРАЛЕЙ В ПОЛУ")
    c.setFillColor(HexColor("#A7EEE7")); c.setFont("Segoe", 10)
    c.drawString(13 * mm, h - 21 * mm, "Основной путь: закрепление к плите + восстановление ровной опорной поверхности; несущая крышка только резерв")
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe-Bold", 8.8)
    c.drawRightString(w - 13 * mm, h - 17 * mm, "A3 · лист 1/1 · КООРДИНАЦИЯ")

    c.setFillColor(HexColor("#FFF0F0")); c.roundRect(13 * mm, h - 49 * mm, w - 26 * mm, 12 * mm, 2.5 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 9.7)
    c.drawCentredString(w / 2, h - 44.5 * mm, "НЕ ЗАЛИВАТЬ И НЕ ЗАКРЫВАТЬ ДО ВЫБОРА МАТЕРИАЛОВ, КРЕПЕЖА, СТЯЖКИ И ПРОВЕРКИ ОПОРНЫХ ПОЛОС")

    c.drawImage(str(EVIDENCE), 10 * mm, 45 * mm, width=262 * mm, height=175 * mm, preserveAspectRatio=True, mask="auto")

    x, bw = 280 * mm, 127 * mm
    c.setFillColor(HexColor("#F8FBFB")); c.roundRect(x, 15 * mm, bw, 205 * mm, 3 * mm, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#A4B6BC")); c.roundRect(x, 15 * mm, bw, 205 * mm, 3 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 12.5)
    c.drawString(x + 7 * mm, 191 * mm, "ПРЕДВАРИТЕЛЬНО ПРИНЯТО")
    yy = 181 * mm
    preferred = [
        "Две непрерывные предизолированные магистрали Uponor 32x3, заводская изоляция 15 мм, наружный Ø62 мм.",
        "Чистая ширина трассы 200 мм; это меньше предела Uponor 300 мм.",
        "Трубы закрепляются к черновой железобетонной плите; тепловое перемещение не зажимается.",
        "До z=100 восстанавливается ровная поверхность связанным заполнением либо доказанным жёстким утеплителем.",
        "Стяжка и финиш не опираются непосредственно на трубу и не сминают заводскую изоляцию.",
    ]
    for item in preferred:
        yy -= bullet(c, item, x + 7 * mm, yy, bw - 14 * mm) + 2 * mm

    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 11.5)
    c.drawString(x + 7 * mm, 118 * mm, "ПИРОГ НАД УТЕПЛИТЕЛЕМ: 70 ММ")
    c.setFillColor(white); c.roundRect(x + 7 * mm, 84 * mm, 54 * mm, 27 * mm, 2 * mm, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#2677A6")); c.roundRect(x + 7 * mm, 84 * mm, 54 * mm, 27 * mm, 2 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor("#2677A6")); c.setFont("Segoe-Bold", 9); c.drawString(x + 11 * mm, 103 * mm, "A · CAF / АНГИДРИТ")
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe", 8.2); c.drawString(x + 11 * mm, 95 * mm, "16 + 35 = 51 мм")
    c.setFont("Segoe-Bold", 8.5); c.drawString(x + 11 * mm, 88 * mm, "финиш: 19 мм")
    c.setFillColor(white); c.roundRect(x + 66 * mm, 84 * mm, 54 * mm, 27 * mm, 2 * mm, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#A55B2A")); c.roundRect(x + 66 * mm, 84 * mm, 54 * mm, 27 * mm, 2 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor("#A55B2A")); c.setFont("Segoe-Bold", 9); c.drawString(x + 70 * mm, 103 * mm, "B · ЦЕМЕНТНАЯ")
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe", 8.2); c.drawString(x + 70 * mm, 95 * mm, "16 + 45 = 61 мм")
    c.setFont("Segoe-Bold", 8.5); c.drawString(x + 70 * mm, 88 * mm, "финиш: только 9 мм")
    c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 8.2); c.drawCentredString(x + bw / 2, 78 * mm, "НИ ОДНА ВЕТВЬ ПОКА НЕ ВЫБРАНА")

    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 11.5); c.drawString(x + 7 * mm, 67 * mm, "КОНТРОЛЬ МОНТАЖА")
    checks = [
        "крепление на прямой: не более 800 мм; до/после поворота: не более 300 мм;",
        "опорная полоса рядом с трассой: проверить непрерывные ≥200 мм;",
        "точный заполнитель, утеплитель, крепёж, стяжка и финиш - по техлистам;",
        "скрытых фитингов - 0; испытание, фото и размеры до закрытия;",
        "если ровную несущую поверхность доказать нельзя - рассчитать короб/крышку D117.",
    ]
    yy = 59 * mm
    for item in checks:
        yy -= bullet(c, item, x + 7 * mm, yy, bw - 14 * mm, mark="#B00020" if "нельзя" in item else "#00A37A") + 1.2 * mm

    c.setFillColor(HexColor("#071A21")); c.rect(0, 0, w, 12 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe", 7.2)
    c.drawString(13 * mm, 4.5 * mm, "Источник метода: Uponor MLC tap water and heating 1119966, стр. 101-102. Пирог: Uponor Planning Information 1186660 v1, стр. 16-18.")
    c.setFont("Segoe-Bold", 7.2); c.drawRightString(w - 13 * mm, 4.5 * mm, "D122 · СТРОИТЕЛЬСТВО НЕ РАЗРЕШЕНО")
    c.showPage(); c.save()

    local_pdf = OUTPUT / PDF_OUT.name
    shutil.copy2(PDF_OUT, local_pdf)
    sheet = {
        "schema": "homeaura-floor-primary-preliminary-sheet-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_PRELIMINARY_SHEET_122",
        "status": "ONE_PAGE_PRELIMINARY_LEVELLING_DETAIL_PASS_NOT_CONSTRUCTION_RELEASE",
        "source_records": source_records,
        "supersedes_D119_mandatory_load_bridge_as_primary_method": True,
        "pdf_file": PDF_OUT.name,
        "page_count": 1,
        "page_size": "A3_LANDSCAPE",
        "selected_concept_family": "SLAB_FIXED_PREINSULATED_PIPES_PLUS_COMPLIANT_LEVELLING_LAYER",
        "load_bridge_status": "FALLBACK_NOT_SELECTED",
        "floor_stack_option_count": 2,
        "selected_floor_stack_option_count": 0,
        "approved_pipe_geometry_count": 0,
        "construction_authorized": False,
        "result": "PASS_PRELIMINARY_METHOD_SHEET_REWORK_EXACT_PRODUCTS_SUPPORT_STRIPS_AND_SCREEED",
    }
    sheet["sheet_digest"] = digest(sheet)
    (OUTPUT / "preliminary_sheet.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=2), encoding="utf8")
    files = [p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    manifest = {"artifact_id": sheet["artifact_id"], "sheet_digest": sheet["sheet_digest"], "append_only": True,
                "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]}
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "pdf": str(PDF_OUT), "pdf_sha256": sha(PDF_OUT), "digest": sheet["sheet_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

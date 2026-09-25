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
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_REVISION_SHEET_115"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_REVISION_SHEET_115.zip"
PDF_OUT = ROOT / "output" / "pdf" / "HomeAura_floor_primary_revision_D115.pdf"
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_CHANNEL_REVISION_114" / "floor_primary_channel_revision.json"
EVIDENCE = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_CHANNEL_REVISION_114" / "floor_primary_channel_revision_evidence.png"
SOURCE_PDF = ROOT / "output" / "pdf" / "HomeAura_floor_primary_coordination_D112.pdf"


pdfmetrics.registerFont(TTFont("Segoe", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Segoe-Bold", r"C:\Windows\Fonts\seguisb.ttf"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def paragraph(c, text, x, y, width, size=9.5, color="#143842", bold=False, leading=None):
    style = ParagraphStyle(
        "body",
        fontName="Segoe-Bold" if bold else "Segoe",
        fontSize=size,
        leading=leading or size * 1.35,
        textColor=HexColor(color),
        alignment=TA_LEFT,
    )
    p = Paragraph(text, style)
    _, ph = p.wrap(width, 70 * mm)
    p.drawOn(c, x, y - ph)
    return ph


def bullet(c, text, x, y, width, color="#143842", mark="#00A37A"):
    c.setFillColor(HexColor(mark))
    c.circle(x + 2.2 * mm, y - 2.2 * mm, 1.5 * mm, stroke=0, fill=1)
    ph = paragraph(c, text, x + 7 * mm, y + 1 * mm, width - 7 * mm, size=9.2, color=color)
    return max(ph, 9 * mm)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists() or PDF_OUT.exists():
        raise FileExistsError("D115 is append-only")
    model114 = json.loads(SOURCE.read_text(encoding="utf8"))
    OUTPUT.mkdir(parents=True)
    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(PDF_OUT), pagesize=landscape(A3), pageCompression=1)
    c.setTitle("HomeAura - обязательное дополнение к D112 - D115")
    c.setAuthor("HomeAura Engineering Agent")
    w, h = landscape(A3)
    c.setFillColor(HexColor("#071A21")); c.rect(0, h - 31 * mm, w, 31 * mm, stroke=0, fill=1)
    c.setFillColor(white); c.setFont("Segoe-Bold", 19); c.drawString(14 * mm, h - 12 * mm, "D115 · ОБЯЗАТЕЛЬНОЕ ДОПОЛНЕНИЕ К ЛИСТУ D112")
    c.setFillColor(HexColor("#A7EEE7")); c.setFont("Segoe", 10.5); c.drawString(14 * mm, h - 22 * mm, "Исправление несущего узла канала, фиксации магистралей и проходки перекрытия")
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe-Bold", 9.5); c.drawRightString(w - 14 * mm, h - 18 * mm, "D115 · A3 · лист 1/1")

    c.setFillColor(HexColor("#FFF0F0")); c.roundRect(14 * mm, h - 60 * mm, w - 28 * mm, 18 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 11.5)
    c.drawCentredString(w / 2, h - 51 * mm, "D112, ЛИСТ 2: НЕ ИСПОЛЬЗОВАТЬ КАК НЕСУЩИЙ МОНТАЖНЫЙ УЗЕЛ БЕЗ ЭТОГО ДОПОЛНЕНИЯ")

    c.drawImage(str(EVIDENCE), 12 * mm, 22 * mm, width=245 * mm, height=171 * mm, preserveAspectRatio=True, mask="auto")

    x = 270 * mm
    box_w = 135 * mm
    c.setFillColor(white); c.roundRect(x, 115 * mm, box_w, 95 * mm, 4 * mm, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#A7B9BF")); c.roundRect(x, 115 * mm, box_w, 95 * mm, 4 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor("#006A43")); c.setFont("Segoe-Bold", 13); c.drawString(x + 8 * mm, 198 * mm, "ОБЯЗАТЕЛЬНЫЙ НОВЫЙ УЗЕЛ")
    items = [
        "Над полосой 200 мм ставится <b>рассчитанный несущий мост/короб</b>; 30-34 мм теплоизоляции - только заполнение.",
        "Две магистрали закрепляются <b>к железобетонной плите</b>, не к утеплителю; смятие заводской изоляции запрещено.",
        "Материал, толщина, пролёт и опоры моста назначаются по нагрузке стяжки, покрытия и эксплуатации.",
        "Полоса запрета крепежа тёплого пола 200 мм и ноль скрытых соединений сохраняются.",
    ]
    y = 184 * mm
    for item in items:
        y -= bullet(c, item, x + 7 * mm, y, box_w - 14 * mm) + 4 * mm

    c.setFillColor(white); c.roundRect(x, 22 * mm, box_w, 84 * mm, 4 * mm, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#A7B9BF")); c.roundRect(x, 22 * mm, box_w, 84 * mm, 4 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 13); c.drawString(x + 8 * mm, 94 * mm, "ДО МОНТАЖА ОБЯЗАТЕЛЬНО")
    blocked = [
        "выбрать систему тёплого пола/стяжки и подтвердить покрытие над Ø16;",
        "рассчитать мост и выбрать опоры труб с проверкой посадки в 70 мм;",
        "просканировать плиту и выпустить отверстие 120×200 либо изменить его;",
        "назначить гильзы, защиту кромок и конкретную заделку проходки;",
        "подтвердить газобетонную стену и анкеры доступного сервисного короба.",
    ]
    y = 82 * mm
    for item in blocked:
        y -= bullet(c, item, x + 7 * mm, y, box_w - 14 * mm, color="#4A3035", mark="#B00020") + 2 * mm

    c.setFillColor(HexColor("#071A21")); c.rect(0, 0, w, 12 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe-Bold", 8.8)
    c.drawCentredString(w / 2, 4.4 * mm, "КООРДИНАЦИЯ, НЕ РАЗРЕШЕНИЕ НА СВЕРЛЕНИЕ ИЛИ ЗАЛИВКУ · СКРЫТЫХ ФИТИНГОВ 0")
    c.showPage(); c.save()

    local_pdf = OUTPUT / PDF_OUT.name
    shutil.copy2(PDF_OUT, local_pdf)
    sheet = {
        "schema": "homeaura-floor-primary-revision-sheet-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_REVISION_SHEET_115",
        "status": "ONE_PAGE_MANDATORY_COORDINATION_ADDENDUM_PASS_NOT_CONSTRUCTION_RELEASE",
        "source_artifact_id": model114["artifact_id"],
        "source_sha256": sha(SOURCE),
        "historical_D112_pdf_sha256": sha(SOURCE_PDF),
        "pdf_file": PDF_OUT.name,
        "page_count": 1,
        "page_size": "A3_LANDSCAPE",
        "D112_page_2_load_detail_superseded": True,
        "load_bearing_bridge_required": True,
        "primary_support_base": "STRUCTURAL_SLAB",
        "approved_slab_opening_count": 0,
        "construction_authorized": False,
        "result": "PASS_MANDATORY_ADDENDUM_REWORK_ENGINEERED_SELECTIONS_AND_SITE_RELEASE",
    }
    sheet["sheet_digest"] = digest(sheet)
    (OUTPUT / "revision_sheet.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=2), encoding="utf8")
    files = [p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps(
            {"artifact_id": sheet["artifact_id"], "sheet_digest": sheet["sheet_digest"], "append_only": True,
             "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]},
            ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "pdf": str(PDF_OUT), "pdf_sha256": sha(PDF_OUT), "digest": sheet["sheet_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

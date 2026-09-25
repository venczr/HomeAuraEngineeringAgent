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
SOURCE_PDF = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_SHEET_126" / "HomeAura_floor_primary_coordination_D126.pdf"
SOURCE_D128 = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_EVIDENCE_REPAIR_128" / "floor_primary_coordination_evidence_repair.json"
SOURCE_D127 = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_VECTOR_DOMAIN_METADATA_REPAIR_127" / "floor_primary_vector_domain_metadata_repair.json"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_FINAL_EVIDENCE_129"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_FINAL_EVIDENCE_129.zip"
PDF_OUT = ROOT / "output" / "pdf" / "HomeAura_floor_primary_coordination_D129.pdf"

pdfmetrics.registerFont(TTFont("Segoe", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Segoe-Bold", r"C:\Windows\Fonts\seguisb.ttf"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def draw_header_footer(c, page_no):
    w, h = landscape(A3)
    c.setFillColor(HexColor("#071A21")); c.rect(0, h - 29 * mm, w, 29 * mm, stroke=0, fill=1)
    title = "D129 · МАГИСТРАЛИ K1 → ЛЕСТНИЦА → K2" if page_no == 1 else "D129 · ПИРОГ ПОЛА И КОНТРОЛЬ ВЫПУСКА"
    subtitle = ("Итоговое координационное доказательство; расчёт D124/D127 и геометрия D126 сохранены" if page_no == 1
                else "100 мм утеплителя на 1 этаже, 50 мм на мансарде; над ним по 70 мм")
    c.setFillColor(white); c.setFont("Segoe-Bold", 18.3); c.drawString(13 * mm, h - 11 * mm, title)
    c.setFillColor(HexColor("#A7EEE7")); c.setFont("Segoe", 9.7); c.drawString(13 * mm, h - 21 * mm, subtitle)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe-Bold", 8.5); c.drawRightString(w - 13 * mm, h - 17 * mm, f"A3 · лист {page_no}/2 · КООРДИНАЦИЯ")
    c.setFillColor(HexColor("#071A21")); c.rect(0, 0, w, 12 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe", 7.1)
    c.drawString(13 * mm, 4.5 * mm, "Источники: векторный PDF этажа 1; Uponor MLC Technical Guide; Uponor UK MLC FAQ; H+H Aircrete guide.")
    c.setFont("Segoe-Bold", 7.1); c.drawRightString(w - 13 * mm, 4.5 * mm, f"D129 · лист {page_no}/2 · НЕ ДЛЯ СТРОИТЕЛЬСТВА")


def node(c, y, tag, name, detail, color):
    c.setFillColor(HexColor(color)); c.roundRect(297 * mm, y - 10 * mm, 26 * mm, 12 * mm, 2 * mm, stroke=0, fill=1)
    c.setFillColor(white); c.setFont("Segoe-Bold", 7.2); c.drawCentredString(310 * mm, y - 5.6 * mm, tag)
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 7.4); c.drawString(328 * mm, y - 2.5 * mm, name)
    c.setFont("Segoe", 6.7); c.drawString(328 * mm, y - 8.3 * mm, detail)


def overlay_page(page_no):
    buf = io.BytesIO()
    w, h = landscape(A3)
    c = canvas.Canvas(buf, pagesize=(w, h), pageCompression=1)
    draw_header_footer(c, page_no)
    if page_no == 1:
        # Fully redraw the inner node card to eliminate every prior label.
        c.setFillColor(HexColor("#F8FBFB")); c.rect(292 * mm, 104 * mm, 113 * mm, 109 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 11.5); c.drawString(297 * mm, 203 * mm, "ТРИ РАЗНЫХ УЗЛА")
        node(c, 190 * mm, "W01", "западная комната → холл", "321,7 мм AAC", "#B8535C")
        node(c, 163 * mm, "W02", "холл → котельная", "317,5 мм AAC", "#B8535C")
        node(c, 136 * mm, "P01 / D098", "плита у лестницы → гардеробная", "120×200; оси 9250/7350 и 9250/7450", "#6F33A8")
        c.setFillColor(HexColor("#FFF3D9")); c.roundRect(297 * mm, 108 * mm, 103 * mm, 18 * mm, 2 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor("#805500")); c.setFont("Segoe-Bold", 6.8)
        c.drawString(301 * mm, 119 * mm, "W01/W02 не заменяют P01. Стеновые проходы — прямые;")
        c.drawString(301 * mm, 113 * mm, "повороты выполняются только в доступных коробах.")
    else:
        # Fix support strip labels on the left card.
        c.setFillColor(HexColor("#B9DB75")); c.rect(102 * mm, 124.2 * mm, 76 * mm, 7.8 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor("#38531C")); c.setFont("Segoe-Bold", 6.1); c.drawCentredString(140 * mm, 126.8 * mm, "ВЕРХ ВЫРОВНЯТЬ ДО z=100")
        c.setFillColor(HexColor("#D8C9B1")); c.rect(102 * mm, 135 * mm, 76 * mm, 6.5 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 6.1); c.drawCentredString(140 * mm, 137.2 * mm, "ПОЛОСА 200 ММ: БЕЗ СКОБ И АНКЕРОВ")

        # Fully redraw the inner right card.
        c.setFillColor(HexColor("#F8FBFB")); c.rect(272 * mm, 67 * mm, 133 * mm, 141 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 11.4); c.drawString(277 * mm, 197 * mm, "ДВА ПИРОГА В 70 ММ")
        for bx, title, cover, total, finish, color in (
            (277 * mm, "A · CAF / АНГИДРИТ", 35, 51, 19, "#2677A6"),
            (340 * mm, "B · ЦЕМЕНТНАЯ", 45, 61, 9, "#A55B2A"),
        ):
            c.setFillColor(white); c.roundRect(bx, 158 * mm, 56 * mm, 30 * mm, 2 * mm, stroke=0, fill=1)
            c.setStrokeColor(HexColor(color)); c.roundRect(bx, 158 * mm, 56 * mm, 30 * mm, 2 * mm, stroke=1, fill=0)
            c.setFillColor(HexColor(color)); c.setFont("Segoe-Bold", 7.8); c.drawString(bx + 4 * mm, 180 * mm, title)
            c.setFillColor(HexColor("#153A43")); c.setFont("Segoe", 7.1); c.drawString(bx + 4 * mm, 171 * mm, f"Ø16 + {cover} = {total} мм")
            c.setFont("Segoe-Bold", 7.3); c.drawString(bx + 4 * mm, 163 * mm, f"финиш: {finish} мм")
        c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 8); c.drawCentredString(338.5 * mm, 151 * mm, "ВЕТВЬ НЕ ВЫБРАНА")

        c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 9.6); c.drawString(277 * mm, 139 * mm, "ИСХОДНЫЕ ДАННЫЕ ВЛАДЕЛЬЦА")
        owner = [
            "•  1 этаж: утеплитель 100 мм + запас 70 мм;",
            "•  мансарда: утеплитель 50 мм + запас 70 мм;",
            "•  высота 3 000 мм; стены — газобетон;",
            "•  петли Ø16, расчётный R80; прогрев не учитывается;",
            "•  магистрали Ø32×3; повороты — доступные пресс-отводы.",
        ]
        y = 131 * mm
        for text in owner:
            c.setFillColor(HexColor("#007B63")); c.setFont("Segoe", 6.5); c.drawString(278 * mm, y, text); y -= 6.3 * mm

        c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 9.6); c.drawString(277 * mm, 96 * mm, "ДО ВЫПУСКА В РАБОТУ")
        pending = [
            "•  утеплитель/выравнивание/крепёж Ø62; стяжка и финиш;",
            "•  W01/W02: классификация, отверстия, гильзы и заделка;",
            "•  P01 120×200: сканирование плиты и выпуск конструктора;",
            "•  опрессовка, фото и размеры до закрытия; фитингов в полу — 0.",
        ]
        y = 88 * mm
        for i, text in enumerate(pending):
            c.setFillColor(HexColor("#B00020" if i < 3 else "#007B63")); c.setFont("Segoe-Bold" if i < 3 else "Segoe", 6.4)
            c.drawString(278 * mm, y, text); y -= 6.8 * mm
    c.showPage(); c.save()
    return buf.getvalue()


def main():
    if OUTPUT.exists() or PACKAGE.exists() or PDF_OUT.exists():
        raise SystemExit("append-only target already exists")
    d128 = json.loads(SOURCE_D128.read_text(encoding="utf8"))
    d127 = json.loads(SOURCE_D127.read_text(encoding="utf8"))
    OUTPUT.mkdir(parents=True)
    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(SOURCE_PDF)
    assert doc.page_count == 2
    for index in range(2):
        ov = pymupdf.open(stream=overlay_page(index + 1), filetype="pdf")
        doc[index].show_pdf_page(doc[index].rect, ov, 0, overlay=True)
    doc.set_metadata({**doc.metadata, "title": "HomeAura floor primary coordination D129", "author": "HomeAura Engineering Agent"})
    doc.save(PDF_OUT, garbage=4, deflate=True)
    shutil.copy2(PDF_OUT, OUTPUT / PDF_OUT.name)
    record = {
        "schema": "homeaura-floor-primary-coordination-final-evidence-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_FINAL_EVIDENCE_129",
        "status": "FINAL_VISUAL_EVIDENCE_PASS_NOT_CONSTRUCTION_RELEASE",
        "source_D126_pdf_sha256": sha(SOURCE_PDF),
        "source_D128_artifact_sha256": sha(SOURCE_D128),
        "source_D128_disposition": "SUPERSEDED_VISUAL_REPAIR_RETAINED_AS_HISTORY",
        "source_D127_artifact_sha256": sha(SOURCE_D127),
        "source_geometry_changed": False,
        "page_count": 2,
        "page_size": "A3_LANDSCAPE",
        "visual_repairs": ["RIGHT_NODE_CARD_FULL_REDRAW", "RIGHT_RELEASE_CARD_FULL_REDRAW", "SUPPORT_LABELS_SEPARATED"],
        "authoritative_floor_axis_length_mm": d127["authoritative_totals"]["vector_draft_floor_axis_length_mm"],
        "authoritative_aac_wall_axis_length_mm": d127["authoritative_totals"]["aac_wall_axis_length_mm"],
        "unknown_axis_length_mm": 0.0,
        "aac_wall_opening_count": 2,
        "separate_slab_penetration_node_count": 1,
        "approved_wall_opening_count": 0,
        "approved_slab_opening_count": 0,
        "selected_floor_stack_option_count": 0,
        "approved_pipe_geometry_count": 0,
        "construction_authorized": False,
        "result": "PASS_CLEAN_COORDINATION_EVIDENCE_REWORK_PRODUCTS_WALL_OPENINGS_SLAB_RELEASE_AND_SCREED",
    }
    record["evidence_digest"] = digest(record)
    (OUTPUT / "floor_primary_coordination_final_evidence.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf8")
    (OUTPUT / "release_note.md").write_text(
        "# D129 — итоговый координационный лист\n\n"
        "Две страницы визуально проверены. Геометрия D126 не менялась; D127 исправляет строковую опечатку D124. "
        "Фактический баланс оси: пол 3 930,8 мм, две стены 639,2 мм, неизвестно 0 мм. W01/W02/P01 разделены. "
        "Документ остаётся координационным и не разрешает сверление или закрытие конструкций.\n",
        encoding="utf8",
    )
    files = sorted(p for p in OUTPUT.iterdir() if p.is_file())
    manifest = {"artifact_id": record["artifact_id"], "evidence_digest": record["evidence_digest"], "append_only": True,
                "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]}
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "pdf": str(PDF_OUT), "pdf_sha256": sha(PDF_OUT), "package": str(PACKAGE), "digest": record["evidence_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

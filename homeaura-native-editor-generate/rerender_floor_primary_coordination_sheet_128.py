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
SOURCE_DIR = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_SHEET_126"
SOURCE_PDF = SOURCE_DIR / "HomeAura_floor_primary_coordination_D126.pdf"
REPAIR = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_VECTOR_DOMAIN_METADATA_REPAIR_127" / "floor_primary_vector_domain_metadata_repair.json"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_EVIDENCE_REPAIR_128"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_EVIDENCE_REPAIR_128.zip"
PDF_OUT = ROOT / "output" / "pdf" / "HomeAura_floor_primary_coordination_D128.pdf"

pdfmetrics.registerFont(TTFont("Segoe", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Segoe-Bold", r"C:\Windows\Fonts\seguisb.ttf"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def overlay_page(page_no):
    buf = io.BytesIO()
    w, h = landscape(A3)
    c = canvas.Canvas(buf, pagesize=(w, h), pageCompression=1)

    # Replace the header and footer so the successor PDF is unambiguous.
    c.setFillColor(HexColor("#071A21")); c.rect(0, h - 29 * mm, w, 29 * mm, stroke=0, fill=1)
    title = "D128 · МАГИСТРАЛИ K1 → ЛЕСТНИЦА → K2" if page_no == 1 else "D128 · ПИРОГ ПОЛА И КОНТРОЛЬ ВЫПУСКА"
    subtitle = ("Исправленное визуальное доказательство D126; геометрия и расчёт не изменены" if page_no == 1
                else "100 мм утеплителя на 1 этаже, 50 мм на мансарде; над ним по 70 мм")
    c.setFillColor(white); c.setFont("Segoe-Bold", 18.3); c.drawString(13 * mm, h - 11 * mm, title)
    c.setFillColor(HexColor("#A7EEE7")); c.setFont("Segoe", 9.7); c.drawString(13 * mm, h - 21 * mm, subtitle)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe-Bold", 8.5); c.drawRightString(w - 13 * mm, h - 17 * mm, f"A3 · лист {page_no}/2 · КООРДИНАЦИЯ")
    c.setFillColor(HexColor("#071A21")); c.rect(0, 0, w, 12 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe", 7.1)
    c.drawString(13 * mm, 4.5 * mm, "Источники: векторный PDF этажа 1; Uponor MLC Technical Guide; Uponor UK MLC FAQ; H+H Aircrete guide.")
    c.setFont("Segoe-Bold", 7.1); c.drawRightString(w - 13 * mm, 4.5 * mm, f"D128 · лист {page_no}/2 · НЕ ДЛЯ СТРОИТЕЛЬСТВА")

    if page_no == 1:
        # Redraw the lower part of the node card so P01 and the warning never overlap.
        c.setFillColor(HexColor("#F8FBFB")); c.rect(292 * mm, 104 * mm, 113 * mm, 48 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor("#6F33A8")); c.roundRect(297 * mm, 133 * mm, 26 * mm, 12 * mm, 2 * mm, stroke=0, fill=1)
        c.setFillColor(white); c.setFont("Segoe-Bold", 7.2); c.drawCentredString(310 * mm, 137.3 * mm, "P01 / D098")
        c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 7.6); c.drawString(328 * mm, 140 * mm, "плита у лестницы → гардеробная")
        c.setFont("Segoe", 6.8); c.drawString(328 * mm, 134.2 * mm, "120×200 мм; оси 9250/7350 и 9250/7450")
        c.setFillColor(HexColor("#FFF3D9")); c.roundRect(297 * mm, 108 * mm, 103 * mm, 18 * mm, 2 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor("#805500")); c.setFont("Segoe-Bold", 6.9)
        c.drawString(301 * mm, 119 * mm, "W01/W02 не заменяют P01. Стеновые проходы — прямые;")
        c.drawString(301 * mm, 113 * mm, "повороты выполняются только в доступных коробах.")
    else:
        # Replace the two colliding annotations in the support strip section.
        c.setFillColor(HexColor("#B9DB75")); c.rect(102 * mm, 124.2 * mm, 76 * mm, 7.8 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor("#38531C")); c.setFont("Segoe-Bold", 6.1); c.drawCentredString(140 * mm, 126.8 * mm, "ВЕРХ ВЫРОВНЯТЬ ДО z=100")
        c.setFillColor(HexColor("#D8C9B1")); c.rect(102 * mm, 135 * mm, 76 * mm, 6.5 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 6.1); c.drawCentredString(140 * mm, 137.2 * mm, "ПОЛОСА 200 ММ: БЕЗ СКОБ И АНКЕРОВ")

        # Compact release checklist inside its card; source D126 text had run below the card.
        c.setFillColor(HexColor("#F8FBFB")); c.rect(275 * mm, 66 * mm, 128 * mm, 39 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 9.3); c.drawString(277 * mm, 99 * mm, "ДО ВЫПУСКА В РАБОТУ")
        rows = [
            ("#B00020", "•  марка/прочность утеплителя; выравнивание и крепёж Ø62 к плите;"),
            ("#B00020", "•  стяжка, нагрузка, финиш, мокрые зоны;"),
            ("#B00020", "•  W01/W02: классификация стен, отверстия, гильзы и заделка;"),
            ("#B00020", "•  P01 120×200: сканирование плиты и выпуск конструктора;"),
            ("#007B63", "•  опрессовка, фото и размеры до закрытия; скрытых фитингов — 0."),
        ]
        y = 92 * mm
        for color, text in rows:
            c.setFillColor(HexColor(color)); c.setFont("Segoe-Bold" if color == "#B00020" else "Segoe", 6.5)
            c.drawString(278 * mm, y, text); y -= 6.1 * mm

    c.showPage(); c.save()
    buf.seek(0)
    return buf.getvalue()


def main():
    if OUTPUT.exists() or PACKAGE.exists() or PDF_OUT.exists():
        raise SystemExit("append-only target already exists")
    repair = json.loads(REPAIR.read_text(encoding="utf8"))
    OUTPUT.mkdir(parents=True)
    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)
    source_doc = pymupdf.open(SOURCE_PDF)
    assert source_doc.page_count == 2
    for index in range(2):
        ov = pymupdf.open(stream=overlay_page(index + 1), filetype="pdf")
        page = source_doc[index]
        page.show_pdf_page(page.rect, ov, 0, overlay=True)
    source_doc.set_metadata({**source_doc.metadata, "title": "HomeAura floor primary coordination D128", "author": "HomeAura Engineering Agent"})
    source_doc.save(PDF_OUT, garbage=4, deflate=True)
    shutil.copy2(PDF_OUT, OUTPUT / PDF_OUT.name)

    record = {
        "schema": "homeaura-floor-primary-coordination-evidence-repair-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_EVIDENCE_REPAIR_128",
        "status": "TWO_PAGE_COORDINATION_EVIDENCE_PASS_NOT_CONSTRUCTION_RELEASE",
        "source_D126_pdf_sha256": sha(SOURCE_PDF),
        "source_D127_repair_sha256": sha(REPAIR),
        "source_D127_repair_digest": repair["repair_digest"],
        "source_geometry_changed": False,
        "page_count": 2,
        "page_size": "A3_LANDSCAPE",
        "visual_repairs": [
            "P01_ROW_AND_WARNING_SEPARATED",
            "SUPPORT_STRIP_ANNOTATIONS_SEPARATED",
            "RELEASE_CHECKLIST_CONTAINED_IN_CARD",
            "ARTIFACT_ID_DATA_BOUND_TO_D128_HEADER_AND_FOOTER",
        ],
        "authoritative_floor_axis_length_mm": repair["authoritative_totals"]["vector_draft_floor_axis_length_mm"],
        "authoritative_aac_wall_axis_length_mm": repair["authoritative_totals"]["aac_wall_axis_length_mm"],
        "unknown_axis_length_mm": 0.0,
        "aac_wall_opening_count": 2,
        "separate_slab_penetration_node_count": 1,
        "approved_wall_opening_count": 0,
        "approved_slab_opening_count": 0,
        "selected_floor_stack_option_count": 0,
        "approved_pipe_geometry_count": 0,
        "construction_authorized": False,
        "result": "PASS_COORDINATION_EVIDENCE_REWORK_PRODUCTS_WALL_OPENINGS_SLAB_RELEASE_AND_SCREED",
    }
    record["evidence_digest"] = digest(record)
    (OUTPUT / "floor_primary_coordination_evidence_repair.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf8")
    (OUTPUT / "release_note.md").write_text(
        "# D128 — исправленный координационный лист\n\n"
        "Геометрия D126 сохранена. Устранены только визуальные наложения и исправлены подписи: 3 930,8 мм оси по полу, 639,2 мм через две стены, неизвестная часть 0 мм. "
        "W01, W02 и P01 остаются тремя отдельными узлами. К строительству лист не выпущен.\n",
        encoding="utf8",
    )
    files = sorted(p for p in OUTPUT.iterdir() if p.is_file())
    manifest = {
        "artifact_id": record["artifact_id"],
        "evidence_digest": record["evidence_digest"],
        "append_only": True,
        "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
    }
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "pdf": str(PDF_OUT), "pdf_sha256": sha(PDF_OUT), "package": str(PACKAGE), "digest": record["evidence_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

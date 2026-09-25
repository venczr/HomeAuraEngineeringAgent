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
SOURCE_PDF = ROOT / "output" / "pdf" / "HomeAura_primary_openings_asbuilt_and_pull_gate_D132.pdf"
SOURCE_JSON = BASE / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ASBUILT_PULL_GATE_132" / "primary_openings_asbuilt_pull_gate.json"
OUTPUT = BASE / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ASBUILT_PULL_GATE_EVIDENCE_133"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ASBUILT_PULL_GATE_EVIDENCE_133.zip"
PDF_OUT = ROOT / "output" / "pdf" / "HomeAura_primary_openings_asbuilt_and_pull_gate_D133.pdf"

pdfmetrics.registerFont(TTFont("Segoe", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Segoe-Bold", r"C:\Windows\Fonts\seguisb.ttf"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def check(c, x, y, text, red=False):
    c.setStrokeColor(HexColor("#7A8D93")); c.rect(x, y - 2.5 * mm, 3.6 * mm, 3.6 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor("#B00020" if red else "#163B44")); c.setFont("Segoe-Bold" if red else "Segoe", 6.8); c.drawString(x + 6 * mm, y - 1.1 * mm, text)


def header_footer(c, page):
    w, h = landscape(A3)
    c.setFillColor(HexColor("#071A21")); c.rect(0, h - 29 * mm, w, 29 * mm, stroke=0, fill=1)
    title = "D133 · ИСПОЛНИТЕЛЬНАЯ КАРТОЧКА W01 / W02 / P01" if page == 1 else "D133 · ПОРЯДОК ПРОТЯЖКИ И СТОП-УСЛОВИЯ"
    subtitle = "Исправленное визуальное доказательство D132; требования и статус не изменены"
    c.setFillColor(white); c.setFont("Segoe-Bold", 18); c.drawString(13 * mm, h - 11 * mm, title)
    c.setFillColor(HexColor("#A7EEE7")); c.setFont("Segoe", 9.5); c.drawString(13 * mm, h - 21 * mm, subtitle)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe-Bold", 8.3); c.drawRightString(w - 13 * mm, h - 17 * mm, f"A3 · лист {page}/2 · ПОЛЕВАЯ КАРТОЧКА")
    c.setFillColor(HexColor("#071A21")); c.rect(0, 0, w, 12 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe", 7); c.drawString(13 * mm, 4.5 * mm, "D133 · отверстия выполнены со слов владельца; пустые поля требуют натурного заполнения.")
    c.setFont("Segoe-Bold", 7); c.drawRightString(w - 13 * mm, 4.5 * mm, "НЕ ЗАКРЫВАТЬ ПРОХОДЫ ДО ОПРЕССОВКИ")


def overlay(page):
    buf = io.BytesIO(); w, h = landscape(A3); c = canvas.Canvas(buf, pagesize=(w, h), pageCompression=1)
    header_footer(c, page)
    if page == 1:
        x_positions = [14 * mm, 148 * mm, 282 * mm]
        for i, x in enumerate(x_positions):
            # Clear only the crowded lower half of each card and redraw at a safe pitch.
            c.setFillColor(HexColor("#F8FBFB")); c.rect(x + 3 * mm, 114 * mm, 120 * mm, 50 * mm, stroke=0, fill=1)
            labels = [
                "гильза или гладкая защитная система установлена",
                "острые кромки сняты / защищены",
                "трещины, сколы, видимые повреждения отсутствуют",
                "арматура / балка не повреждены - подтверждено" if i == 2 else "статус стены и выполненного отверстия принят",
                "совпадение верх/низ плиты измерено" if i == 2 else "прямой проход без фитинга внутри стены",
            ]
            yy = 159 * mm
            for text in labels:
                check(c, x + 6 * mm, yy, text); yy -= 7.4 * mm
            c.setFillColor(HexColor("#163B44")); c.setFont("Segoe", 6.5)
            c.drawString(x + 6 * mm, 120 * mm, "Фото до гильзы: _____________  после: _____________")
            c.drawString(x + 6 * mm, 115 * mm, "Проверил: __________  дата: ________  подпись: ________")
    else:
        # Give the last post-pull checkbox a clear bottom margin.
        c.setFillColor(white); c.rect(270 * mm, 67 * mm, 138 * mm, 56 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor("#F8FBFB")); c.roundRect(270 * mm, 70 * mm, 138 * mm, 52 * mm, 3 * mm, stroke=0, fill=1)
        c.setStrokeColor(HexColor("#00A37A")); c.roundRect(270 * mm, 70 * mm, 138 * mm, 52 * mm, 3 * mm, stroke=1, fill=0)
        c.setFillColor(HexColor("#00A37A")); c.setFont("Segoe-Bold", 10.3); c.drawString(276 * mm, 110 * mm, "ПОСЛЕ ПРОТЯЖКИ")
        rows = [
            "SUPPLY/RETURN читаются на K1 и K2; концы закрыты;",
            "оболочка цела на доступных участках и в выходах гильз;",
            "выполнены фото с рулеткой и привязкой каждого прохода;",
            "опрессовка оформлена отдельным протоколом;",
            "заделка и пол не закрыты до принятия результатов.",
        ]
        yy = 102 * mm
        for text in rows:
            check(c, 278 * mm, yy, text); yy -= 7.1 * mm
    c.showPage(); c.save(); return buf.getvalue()


def main():
    if OUTPUT.exists() or PACKAGE.exists() or PDF_OUT.exists():
        raise SystemExit("append-only target already exists")
    source = json.loads(SOURCE_JSON.read_text(encoding="utf8")); OUTPUT.mkdir(parents=True); PDF_OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(SOURCE_PDF); assert doc.page_count == 2
    for i in range(2):
        ov = pymupdf.open(stream=overlay(i + 1), filetype="pdf"); doc[i].show_pdf_page(doc[i].rect, ov, 0, overlay=True)
    doc.set_metadata({**doc.metadata, "title": "HomeAura openings as-built and pull gate D133", "author": "HomeAura Engineering Agent"})
    doc.save(PDF_OUT, garbage=4, deflate=True); shutil.copy2(PDF_OUT, OUTPUT / PDF_OUT.name)
    record = {
        "schema": "homeaura-primary-openings-asbuilt-pull-gate-evidence-0.1",
        "artifact_id": "HA_TWO_FLOOR_PRIMARY_OPENINGS_ASBUILT_PULL_GATE_EVIDENCE_133",
        "status": "CLEAN_FIELD_PACKET_PASS_REWORK_SITE_COMPLETION",
        "source_D132_artifact_sha256": sha(SOURCE_JSON),
        "source_D132_pdf_sha256": sha(SOURCE_PDF),
        "source_geometry_or_requirements_changed": False,
        "visual_repairs": ["OPENING_CARD_LOWER_FIELDS_SEPARATED", "POST_PULL_LAST_CHECKBOX_MARGIN_REPAIRED", "D133_HEADERS_AND_FOOTERS"],
        "page_count": 2,
        "page_size": "A3_LANDSCAPE",
        "opening_count": source["opening_count"],
        "owner_reported_drilled_count": source["owner_reported_drilled_count"],
        "independently_verified_opening_count": source["independently_verified_opening_count"],
        "pull_release_gate_count": source["pull_release_gate_count"],
        "all_pull_release_gates_pass": False,
        "pressure_test_parameters_selected": False,
        "pipe_pull_authorized": False,
        "penetration_closeout_authorized": False,
        "construction_authorized": False,
        "result": "PASS_CLEAN_FIELD_PACKET_REWORK_AS_BUILT_MEASUREMENTS_AND_PULL_RELEASE",
    }
    record["evidence_digest"] = digest(record)
    (OUTPUT / "primary_openings_asbuilt_pull_gate_evidence.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf8")
    (OUTPUT / "field_instruction.md").write_text("# D133 - чистая полевая карточка\n\nD132 сохранён без изменения инженерных требований; устранены два визуальных наложения. Три отверстия остаются выполненными со слов владельца, но натурные поля пусты и допуск к протяжке не выдан.\n", encoding="utf8")
    files = sorted(p for p in OUTPUT.iterdir() if p.is_file())
    manifest = {"artifact_id": record["artifact_id"], "evidence_digest": record["evidence_digest"], "append_only": True,
                "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]}
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "pdf": str(PDF_OUT), "pdf_sha256": sha(PDF_OUT), "package": str(PACKAGE), "digest": record["evidence_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

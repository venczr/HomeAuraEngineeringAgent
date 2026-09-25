from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from reportlab.lib.colors import Color, HexColor, white
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
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_INSTALLATION_SHEET_112"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_INSTALLATION_SHEET_112.zip"
PDF_OUT = ROOT / "output" / "pdf" / "HomeAura_floor_primary_coordination_D112.pdf"
SOURCES = [
    BASE / "HA_TWO_FLOOR_PRIMARY_CHANNEL_NO_FASTENER_107" / "primary_channel_no_fastener.json",
    BASE / "HA_TWO_FLOOR_PRIMARY_CHANNEL_THERMAL_108" / "primary_channel_thermal.json",
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_INTEGRATION_109" / "floor_primary_integration.json",
    BASE / "HA_TWO_FLOOR_VERTICAL_DATUM_EVIDENCE_111" / "vertical_datum_evidence.json",
]
IMAGES = [
    BASE / "HA_TWO_FLOOR_PRIMARY_CHANNEL_NO_FASTENER_107" / "primary_channel_no_fastener_overlay.png",
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_INTEGRATION_109" / "floor_primary_integration_evidence.png",
    BASE / "HA_TWO_FLOOR_VERTICAL_DATUM_EVIDENCE_111" / "vertical_datum_evidence_corrected.png",
]


pdfmetrics.registerFont(TTFont("Segoe", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Segoe-Bold", r"C:\Windows\Fonts\seguisb.ttf"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def header(c: canvas.Canvas, title: str, subtitle: str, page_no: int):
    w, h = landscape(A3)
    c.setFillColor(HexColor("#071A21"))
    c.rect(0, h - 27 * mm, w, 27 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Segoe-Bold", 18)
    c.drawString(14 * mm, h - 12 * mm, title)
    c.setFillColor(HexColor("#A7EEE7"))
    c.setFont("Segoe", 9.5)
    c.drawString(14 * mm, h - 20 * mm, subtitle)
    c.setFillColor(HexColor("#F3D58C"))
    c.setFont("Segoe-Bold", 9)
    c.drawRightString(w - 14 * mm, h - 17 * mm, f"D112 · лист {page_no}/4")
    c.setFillColor(HexColor("#B00020"))
    c.setFont("Segoe-Bold", 8.5)
    c.drawCentredString(w / 2, 7 * mm, "ПРОЕКТНАЯ КООРДИНАЦИЯ · НЕ РАЗРЕШЕНИЕ НА СВЕРЛЕНИЕ ИЛИ ЗАЛИВКУ")


def fit_image(c: canvas.Canvas, path: Path, x, y, max_w, max_h):
    from PIL import Image

    with Image.open(path) as im:
        iw, ih = im.size
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    c.drawImage(str(path), x + (max_w - w) / 2, y + (max_h - h) / 2, width=w, height=h, preserveAspectRatio=True, mask="auto")


def bullet(c, text, x, y, width, color="#143842", bold=False, size=10):
    c.setFillColor(HexColor("#00A37A"))
    c.circle(x + 2.5 * mm, y + 2.2 * mm, 1.6 * mm, stroke=0, fill=1)
    style = ParagraphStyle("bullet", fontName="Segoe-Bold" if bold else "Segoe", fontSize=size, leading=size * 1.35, textColor=HexColor(color), alignment=TA_LEFT)
    p = Paragraph(text, style)
    p.wrapOn(c, width - 9 * mm, 30 * mm)
    p.drawOn(c, x + 8 * mm, y - 1 * mm)


def main():
    if OUTPUT.exists() or PACKAGE.exists() or PDF_OUT.exists():
        raise FileExistsError("D112 is append-only")
    OUTPUT.mkdir(parents=True)
    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)
    source_records = []
    models = []
    for path in SOURCES:
        raw = path.read_bytes()
        model = json.loads(raw.decode("utf8"))
        models.append(model)
        source_records.append({"artifact_id": model["artifact_id"], "file": path.name, "sha256": hashlib.sha256(raw).hexdigest().upper()})

    c = canvas.Canvas(str(PDF_OUT), pagesize=landscape(A3), pageCompression=1)
    c.setTitle("HomeAura - пол и скрытые магистрали D112")
    c.setAuthor("HomeAura Engineering Agent")
    w, h = landscape(A3)

    header(c, "ПЛАН ПОЛОСЫ СКРЫТЫХ МАГИСТРАЛЕЙ", "K1 в котельной → по полу к лестнице → дальняя внутренняя стена → гардеробная мансарды K2", 1)
    fit_image(c, IMAGES[0], 10 * mm, 17 * mm, 218 * mm, 245 * mm)
    c.setFillColor(HexColor("#FFFFFF"));c.roundRect(238 * mm, 28 * mm, 170 * mm, 225 * mm, 5 * mm, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#A7B9BF"));c.roundRect(238 * mm, 28 * mm, 170 * mm, 225 * mm, 5 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor("#006A43"));c.setFont("Segoe-Bold", 14);c.drawString(248 * mm, 238 * mm, "РАЗМЕТКА НА ОБЪЕКТЕ")
    notes=[
        "Красная полоса: ось скрытого канала шириной <b>200 мм</b>.",
        "Длина оси: <b>4,57 м</b>; две непрерывные магистрали 32×3.",
        "Внутри полосы запрещены скобы, дюбели, саморезы и анкеры.",
        "В плане полосу пересекают 9 контуров Ø16; их геометрию не меняем.",
        "Суммарно внутри полосы находится <b>6,57 м</b> трубы Ø16.",
        "Перед стяжкой нанести края полосы на верх утеплителя и сделать фото с рулеткой.",
        "Наружная стена для перехода на мансарду не используется.",
    ]
    y=216*mm
    for item in notes:
        bullet(c,item,248*mm,y,150*mm);y-=27*mm
    c.setFillColor(HexColor("#FFF2F2"));c.rect(248*mm,39*mm,150*mm,28*mm,stroke=0,fill=1);c.setFillColor(HexColor("#B00020"));c.setFont("Segoe-Bold",10);c.drawString(254*mm,56*mm,"НЕ СВЕРЛИТЬ ПЛИТУ БЕЗ СКАНИРОВАНИЯ");c.setFont("Segoe",9);c.drawString(254*mm,47*mm,"Отверстие 120×200 мм пока не выпущено в монтаж.")
    c.showPage()

    header(c, "ПОПЕРЕЧНЫЙ РАЗРЕЗ ПОЛА ПЕРВОГО ЭТАЖА", "100 мм утеплителя уже уложено; над ним остаётся 70 мм до чистого пола", 2)
    fit_image(c, IMAGES[1], 12 * mm, 22 * mm, 396 * mm, 235 * mm)
    c.showPage()

    header(c, "ВЕРТИКАЛЬНЫЕ ОТМЕТКИ K1 → K2", "Рабочее допущение: 3000 мм между чистыми полами; заменить после лазерной съёмки, если смысл другой", 3)
    fit_image(c, IMAGES[2], 12 * mm, 22 * mm, 396 * mm, 235 * mm)
    c.showPage()

    header(c, "ЧЕК-ЛИСТ ПЕРЕД ЗАКРЫТИЕМ КАНАЛА И СТЯЖКОЙ", "Основной скрытый вариант; внутренний настенный короб D101 остаётся резервным решением", 4)
    cols=[
        (18, "ДО НАЧАЛА", [
            "Уточнить лазером: 3000 мм — чистый пол–чистый пол или чистая высота помещения.",
            "Просканировать арматуру, балки и коммуникации в зоне 120×200 мм.",
            "Получить выпуск ответственного конструктора на отверстие в перекрытии.",
            "Выбрать стяжку и подтвердить 35 мм покрытия над Ø16 для фактической нагрузки.",
            "Выбрать чистовой пирог не более 19 мм: покрытие, клей и/или подложка.",
        ]),
        (148, "СКРЫТЫЕ МАГИСТРАЛИ", [
            "Открыть полосу шириной 200 мм до плиты, не вырезать только верхние 70 мм утеплителя.",
            "Уложить две непрерывные заводски изолированные трубы 32×3 без скрытых фитингов.",
            "Фитинги и повороты оставить только в доступных зонах K1 и вертикального подъёма.",
            "Опрессовать первичную пару до закрытия и зафиксировать давление/время.",
            "Восстановить 30 мм жёсткого утеплителя либо применить рассчитанный распределяющий мостик.",
        ]),
        (278, "ТЁПЛЫЙ ПОЛ И ПРИЁМКА", [
            "Отметить запретную полосу на верхней поверхности утеплителя.",
            "Не ставить в полосе скобы, саморезы, анкеры и дюбели.",
            "Пересечения контуров Ø16 выполнять выше с геометрическим зазором 30 мм.",
            "Опрессовать все контуры до стяжки; сфотографировать трассы и размеры.",
            "Не назначать отрезную длину вертикальной магистрали до отметки патрубков K2 и толщины плиты.",
        ]),
    ]
    for x,title,items in cols:
        c.setFillColor(HexColor("#FFFFFF"));c.roundRect(x*mm,35*mm,120*mm,210*mm,5*mm,stroke=0,fill=1);c.setStrokeColor(HexColor("#A7B9BF"));c.roundRect(x*mm,35*mm,120*mm,210*mm,5*mm,stroke=1,fill=0);c.setFillColor(HexColor("#006A43"));c.setFont("Segoe-Bold",13);c.drawString((x+8)*mm,230*mm,title)
        y=207*mm
        for item in items:
            bullet(c,item,(x+7)*mm,y,107*mm,size=9.2);y-=35*mm
    c.showPage()
    c.save()

    local_pdf = OUTPUT / PDF_OUT.name
    shutil.copy2(PDF_OUT, local_pdf)
    model = {
        "schema": "homeaura-installation-coordination-sheet-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_INSTALLATION_SHEET_112",
        "status": "FOUR_PAGE_COORDINATION_SHEET_PASS_NOT_CONSTRUCTION_RELEASE",
        "source_records": source_records,
        "pdf_file": PDF_OUT.name,
        "page_count": 4,
        "page_size": "A3_LANDSCAPE",
        "selected_method": "HIDDEN_PRIMARY_PAIR_IN_EXISTING_FLOOR1_INSULATION",
        "external_wall_used": False,
        "approved_slab_opening_count": 0,
        "construction_issue_count": 0,
        "construction_authorized": False,
        "result": "PASS_COORDINATION_PDF_REWORK_SITE_RELEASE_ITEMS",
    }
    model["sheet_digest"] = digest(model)
    (OUTPUT / "installation_sheet.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf8")
    files = [p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({"artifact_id": model["artifact_id"], "sheet_digest": model["sheet_digest"], "append_only": True, "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]}, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "pdf": str(PDF_OUT), "pdf_sha256": sha(PDF_OUT), "digest": model["sheet_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

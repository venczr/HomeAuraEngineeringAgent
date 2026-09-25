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
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_STACK_BRIDGE_SHEET_119"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_STACK_BRIDGE_SHEET_119.zip"
PDF_OUT = ROOT / "output" / "pdf" / "HomeAura_floor_primary_stack_bridge_D119.pdf"
SOURCES = [
    BASE / "HA_TWO_FLOOR_FLOOR_STACK_OPTIONS_116" / "floor_stack_options.json",
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_LOAD_BRIDGE_GATE_117" / "load_bridge_stage_gate.json",
]


pdfmetrics.registerFont(TTFont("Segoe", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Segoe-Bold", r"C:\Windows\Fonts\seguisb.ttf"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def paragraph(c, text, x, y, width, size=9.2, color="#143842", bold=False, leading=None):
    style = ParagraphStyle(
        "body",
        fontName="Segoe-Bold" if bold else "Segoe",
        fontSize=size,
        leading=leading or size * 1.35,
        textColor=HexColor(color),
        alignment=TA_LEFT,
    )
    p = Paragraph(text, style)
    _, ph = p.wrap(width, 80 * mm)
    p.drawOn(c, x, y - ph)
    return ph


def bullet(c, text, x, y, width, mark="#00A37A", color="#143842"):
    c.setFillColor(HexColor(mark))
    c.circle(x + 1.7 * mm, y - 2 * mm, 1.2 * mm, stroke=0, fill=1)
    ph = paragraph(c, text, x + 5.5 * mm, y + 0.5 * mm, width - 5.5 * mm, size=8.7, color=color)
    return max(ph, 7.5 * mm)


def option_box(c, x, y, w, h, title, cover, total, finish, color, warning):
    c.setFillColor(HexColor("#FFFFFF")); c.roundRect(x, y, w, h, 3 * mm, stroke=0, fill=1)
    c.setStrokeColor(HexColor(color)); c.setLineWidth(1.4); c.roundRect(x, y, w, h, 3 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor(color)); c.setFont("Segoe-Bold", 11); c.drawString(x + 5 * mm, y + h - 9 * mm, title)
    c.setFillColor(HexColor("#143842")); c.setFont("Segoe", 9)
    c.drawString(x + 5 * mm, y + h - 18 * mm, f"Покрытие над трубой: {cover} мм")
    c.drawString(x + 5 * mm, y + h - 26 * mm, f"Стяжка от утеплителя: {total} мм")
    c.setFont("Segoe-Bold", 10); c.drawString(x + 5 * mm, y + h - 36 * mm, f"Остаток на финиш: {finish} мм")
    paragraph(c, warning, x + 5 * mm, y + 17 * mm, w - 10 * mm, size=7.7, color="#8A2230")
    c.setFillColor(HexColor("#FFF0F0")); c.roundRect(x + 5 * mm, y + 4 * mm, w - 10 * mm, 9 * mm, 1.5 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 7.8); c.drawCentredString(x + w / 2, y + 7 * mm, "НЕ ВЫБРАНО")


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists() or PDF_OUT.exists():
        raise FileExistsError("D119 is append-only")
    source_records = []
    source_models = []
    for path in SOURCES:
        source_models.append(json.loads(path.read_text(encoding="utf8")))
        source_records.append({"artifact_id": source_models[-1]["artifact_id"], "sha256": sha(path)})
    OUTPUT.mkdir(parents=True)
    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(PDF_OUT), pagesize=landscape(A3), pageCompression=1)
    c.setTitle("HomeAura - пирог пола и несущая крышка канала - D119")
    c.setAuthor("HomeAura Engineering Agent")
    w, h = landscape(A3)
    c.setFillColor(HexColor("#071A21")); c.rect(0, h - 30 * mm, w, 30 * mm, stroke=0, fill=1)
    c.setFillColor(white); c.setFont("Segoe-Bold", 18.5)
    c.drawString(13 * mm, h - 11 * mm, "D119 · ПИРОГ ПОЛА И НЕСУЩЕЕ ЗАКРЫТИЕ КАНАЛА")
    c.setFillColor(HexColor("#A7EEE7")); c.setFont("Segoe", 10.2)
    c.drawString(13 * mm, h - 21 * mm, "Исправленная координация: 70 мм сверху, две ветви стяжки и общий бюджет 30-34 мм над магистралями")
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe-Bold", 9)
    c.drawRightString(w - 13 * mm, h - 17 * mm, "A3 · лист 1/1 · НЕ МОНТАЖНЫЙ ЧЕРТЕЖ")

    c.setFillColor(HexColor("#FFF0F0")); c.roundRect(13 * mm, h - 52 * mm, w - 26 * mm, 14 * mm, 2.5 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 10.4)
    c.drawCentredString(w / 2, h - 46.5 * mm, "СТРОИТЕЛЬСТВО НЕ РАЗРЕШЕНО: НИ СТЯЖКА, НИ НЕСУЩАЯ КРЫШКА, НИ ОПОРЫ ЕЩЕ НЕ ВЫБРАНЫ")

    col_y, col_h = 34 * mm, 198 * mm
    x1, w1 = 13 * mm, 116 * mm
    x2, w2 = 137 * mm, 145 * mm
    x3, w3 = 290 * mm, 117 * mm
    for x, cw in ((x1, w1), (x2, w2), (x3, w3)):
        c.setFillColor(HexColor("#F8FBFB")); c.roundRect(x, col_y, cw, col_h, 3 * mm, stroke=0, fill=1)
        c.setStrokeColor(HexColor("#A4B6BC")); c.roundRect(x, col_y, cw, col_h, 3 * mm, stroke=1, fill=0)

    # Column 1: floor stacks.
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 13)
    c.drawString(x1 + 7 * mm, col_y + col_h - 13 * mm, "1 · ВЫБРАТЬ ПИРОГ")
    paragraph(c, "Оба этажа: над существующим утеплителем доступно <b>70 мм</b>. Труба теплого пола Ø16 мм.", x1 + 7 * mm, col_y + col_h - 20 * mm, w1 - 14 * mm, size=9)
    option_box(c, x1 + 7 * mm, col_y + 103 * mm, w1 - 14 * mm, 57 * mm, "A · CAF / АНГИДРИТ", 35, 51, 19, "#2677A6", "Только точный продукт; мокрые зоны и гидроизоляция отдельно.")
    option_box(c, x1 + 7 * mm, col_y + 39 * mm, w1 - 14 * mm, 57 * mm, "B · ЦЕМЕНТНАЯ", 45, 61, 9, "#A55B2A", "9 мм могут не вместить плитку с клеем или другое покрытие.")
    c.setFillColor(HexColor("#E9F5EE")); c.roundRect(x1 + 7 * mm, col_y + 8 * mm, w1 - 14 * mm, 24 * mm, 2 * mm, stroke=0, fill=1)
    paragraph(c, "Существующий утеплитель: 1 этаж - 100 мм; мансарда - 50 мм. Скрытый канал магистралей относится только к 1 этажу.", x1 + 11 * mm, col_y + 27 * mm, w1 - 22 * mm, size=8, color="#245A41", bold=True)

    # Column 2: schematic dimensional gate.
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 13)
    c.drawString(x2 + 7 * mm, col_y + col_h - 13 * mm, "2 · КАНАЛ 200 ММ: РАЗМЕРНЫЙ ЗАПРЕТ")
    sx0, sx1 = x2 + 12 * mm, x2 + w2 - 12 * mm
    slab_y = col_y + 29 * mm
    ins_top = col_y + 127 * mm
    channel_l, channel_r = x2 + 41 * mm, x2 + 104 * mm
    c.setFillColor(HexColor("#AEB7BD")); c.rect(sx0, slab_y, sx1 - sx0, 18 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#DCEAAE")); c.rect(sx0, slab_y + 18 * mm, channel_l - sx0, ins_top - slab_y - 18 * mm, stroke=0, fill=1)
    c.rect(channel_r, slab_y + 18 * mm, sx1 - channel_r, ins_top - slab_y - 18 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#7C878D")); c.rect(channel_l - 5 * mm, slab_y + 18 * mm, 5 * mm, ins_top - slab_y - 26 * mm, stroke=0, fill=1)
    c.rect(channel_r, slab_y + 18 * mm, 5 * mm, ins_top - slab_y - 26 * mm, stroke=0, fill=1)
    for cx in (channel_l + 18 * mm, channel_l + 45 * mm):
        c.setFillColor(HexColor("#E8B64E")); c.circle(cx, slab_y + 51 * mm, 10.5 * mm, stroke=1, fill=1)
        c.setFillColor(HexColor("#2B82B7")); c.circle(cx, slab_y + 51 * mm, 5.5 * mm, stroke=1, fill=1)
    c.setStrokeColor(HexColor("#007F83")); c.setLineWidth(2.4)
    c.line(channel_l - 8 * mm, ins_top, channel_r + 8 * mm, ins_top)
    c.setFillColor(HexColor("#006068")); c.setFont("Segoe-Bold", 8.3)
    c.drawCentredString((channel_l + channel_r) / 2, ins_top + 5 * mm, "КРЫШКА: ТОЛЩИНА НЕ ВЫБРАНА")
    c.setFillColor(HexColor("#253B43")); c.setFont("Segoe", 7.5)
    c.drawString(channel_l - 15 * mm, slab_y + 77 * mm, "опоры вне канала")
    c.drawCentredString((sx0 + sx1) / 2, slab_y + 6 * mm, "Ж/Б плита - основание опор")
    c.setStrokeColor(HexColor("#B00020")); c.line(channel_l, slab_y + 14 * mm, channel_r, slab_y + 14 * mm)
    c.line(channel_l, slab_y + 11 * mm, channel_l, slab_y + 17 * mm); c.line(channel_r, slab_y + 11 * mm, channel_r, slab_y + 17 * mm)
    c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 7.7)
    c.drawCentredString((channel_l + channel_r) / 2, slab_y + 8.5 * mm, "200 мм чистый канал")

    facts_y = col_y + 177 * mm
    facts = [
        "ось магистрали z=35 мм; фактическая изоляция Ø62",
        "верх трубы z=66 мм; до z=100 остаётся 34 мм",
        "30 мм заполнения оставляют крышке максимум 4 мм",
        "для конверта Ø70: 30 мм + ненулевая крышка не помещаются",
    ]
    for item in facts:
        facts_y -= bullet(c, item, x2 + 8 * mm, facts_y, w2 - 16 * mm, mark="#B00020" if "не помещаются" in item or "максимум" in item else "#00A37A") + 1.5 * mm

    c.setFillColor(HexColor("#FFF3D9")); c.roundRect(x2 + 7 * mm, col_y + 6 * mm, w2 - 14 * mm, 37 * mm, 2 * mm, stroke=0, fill=1)
    paragraph(c, "Вывод: 30 мм сверху трубы и отдельная несущая крышка используют один и тот же объём. Нельзя одновременно назначить их без толщины крышки, высоты опор и нового теплотехнического/прочностного расчёта.", x2 + 12 * mm, col_y + 37 * mm, w2 - 24 * mm, size=8.5, color="#7A4B00", bold=True)

    # Column 3: release checklist.
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 13)
    c.drawString(x3 + 7 * mm, col_y + col_h - 13 * mm, "3 · ДО МОНТАЖА")
    required = [
        "Выбрать точную стяжку: ветвь A или B, получить техлист производителя.",
        "Назначить чистовое покрытие каждого помещения с клеем/подложкой.",
        "Подтвердить распределённую и точечную нагрузку.",
        "Выбрать опоры труб к плите и измерить их строительную высоту.",
        "Выбрать заводской короб либо рассчитать металлическую крышку с опорами вне канала.",
        "Проверить прогиб, местную нагрузку, трещины стяжки, влагу, коррозию, звук, пожар и тепловой мост.",
        "Расширить запрет крепежа петель с 200 мм до полного следа крышки и опор.",
        "Отдельно выпустить доступный узел поворота/подъёма; скрытых фитингов - 0.",
    ]
    yy = col_y + col_h - 25 * mm
    for item in required:
        yy -= bullet(c, item, x3 + 7 * mm, yy, w3 - 14 * mm) + 2.5 * mm
    c.setFillColor(HexColor("#FFF0F0")); c.roundRect(x3 + 7 * mm, col_y + 15 * mm, w3 - 14 * mm, 27 * mm, 2 * mm, stroke=0, fill=1)
    paragraph(c, "Запрещено: свободная стяжка над пустотой; утеплитель или пена как несущий элемент; опора на заводскую изоляцию трубы; перенос крышки выше z=100 без пересчёта 70-мм пирога.", x3 + 12 * mm, col_y + 37 * mm, w3 - 24 * mm, size=8, color="#9A1830", bold=True)

    c.setFillColor(HexColor("#071A21")); c.rect(0, 0, w, 12 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe", 7.3)
    c.drawString(13 * mm, 4.5 * mm, "Источники: Uponor Planning Information 1186660 v1, стр. 16-18; Kingspan Thermafloor TF70 BBA, раздел 14.10. Применимость к выбранным продуктам подтверждается отдельно.")
    c.setFont("Segoe-Bold", 7.3); c.drawRightString(w - 13 * mm, 4.5 * mm, "D119 · КООРДИНАЦИЯ · НЕ РАЗРЕШЕНИЕ НА ЗАЛИВКУ")
    c.showPage(); c.save()

    local_pdf = OUTPUT / PDF_OUT.name
    shutil.copy2(PDF_OUT, local_pdf)
    sheet = {
        "schema": "homeaura-floor-primary-stack-bridge-sheet-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_STACK_BRIDGE_SHEET_119",
        "status": "ONE_PAGE_STACK_AND_LOAD_BRIDGE_GATE_PASS_NOT_CONSTRUCTION_RELEASE",
        "source_records": source_records,
        "pdf_file": PDF_OUT.name,
        "page_count": 1,
        "page_size": "A3_LANDSCAPE",
        "floor_stack_option_count": 2,
        "selected_floor_stack_option_count": 0,
        "actual_pipe_headroom_to_insulation_top_mm": 34,
        "maximum_bridge_thickness_with_30mm_actual_infill_mm": 4,
        "selected_load_bridge_detail_count": 0,
        "approved_slab_opening_count": 0,
        "construction_authorized": False,
        "result": "PASS_UPDATED_COORDINATION_SHEET_REWORK_PRODUCTS_LOADS_AND_ENGINEERED_BRIDGE",
    }
    sheet["sheet_digest"] = digest(sheet)
    (OUTPUT / "stack_bridge_sheet.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=2), encoding="utf8")
    files = [p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    manifest = {
        "artifact_id": sheet["artifact_id"],
        "sheet_digest": sheet["sheet_digest"],
        "append_only": True,
        "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
    }
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "pdf": str(PDF_OUT), "pdf_sha256": sha(PDF_OUT), "digest": sheet["sheet_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

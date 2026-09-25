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
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_SHEET_126"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_SHEET_126.zip"
PDF_OUT = ROOT / "output" / "pdf" / "HomeAura_floor_primary_coordination_D126.pdf"
SOURCES = [
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_PRELIMINARY_SHEET_122" / "preliminary_sheet.json",
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_VECTOR_DOMAIN_REPAIR_124" / "floor_primary_vector_domain_repair.json",
    BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_AAC_CROSSINGS_125" / "floor_primary_aac_crossings.json",
    BASE / "HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098" / "two_primary_internal_penetration.json",
]


pdfmetrics.registerFont(TTFont("Segoe", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Segoe-Bold", r"C:\Windows\Fonts\seguisb.ttf"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def paragraph(c, text, x, y, width, size=8.7, color="#143842", bold=False, leading=None):
    style = ParagraphStyle(
        "body",
        fontName="Segoe-Bold" if bold else "Segoe",
        fontSize=size,
        leading=leading or size * 1.3,
        textColor=HexColor(color),
        alignment=TA_LEFT,
    )
    p = Paragraph(text, style)
    _, ph = p.wrap(width, 100 * mm)
    p.drawOn(c, x, y - ph)
    return ph


def bullet(c, text, x, y, width, red=False):
    c.setFillColor(HexColor("#B00020" if red else "#00A37A"))
    c.circle(x + 1.5 * mm, y - 2 * mm, 1.15 * mm, stroke=0, fill=1)
    return max(paragraph(c, text, x + 5 * mm, y + 0.4 * mm, width - 5 * mm, 8.2, "#B00020" if red else "#143842", red), 6.7 * mm)


def header(c, title, subtitle, page_no):
    w, h = landscape(A3)
    c.setFillColor(HexColor("#071A21")); c.rect(0, h - 29 * mm, w, 29 * mm, stroke=0, fill=1)
    c.setFillColor(white); c.setFont("Segoe-Bold", 18.3); c.drawString(13 * mm, h - 11 * mm, title)
    c.setFillColor(HexColor("#A7EEE7")); c.setFont("Segoe", 9.7); c.drawString(13 * mm, h - 21 * mm, subtitle)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe-Bold", 8.5); c.drawRightString(w - 13 * mm, h - 17 * mm, f"A3 · лист {page_no}/2 · КООРДИНАЦИЯ")


def footer(c, page_no):
    w, _ = landscape(A3)
    c.setFillColor(HexColor("#071A21")); c.rect(0, 0, w, 12 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe", 7.1)
    c.drawString(13 * mm, 4.5 * mm, "Источники: векторный PDF этажа 1; Uponor MLC Technical Guide; Uponor UK MLC FAQ; H+H Designing and Building with Aircrete.")
    c.setFont("Segoe-Bold", 7.1); c.drawRightString(w - 13 * mm, 4.5 * mm, f"D126 · лист {page_no}/2 · НЕ ДЛЯ СТРОИТЕЛЬСТВА")


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists() or PDF_OUT.exists():
        raise FileExistsError("D126 is append-only")
    models = [json.loads(p.read_text(encoding="utf8")) for p in SOURCES]
    d122, d124, d125, d098 = models
    records = [{"artifact_id": m["artifact_id"], "sha256": sha(p)} for p, m in zip(SOURCES, models)]
    OUTPUT.mkdir(parents=True)
    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(PDF_OUT), pagesize=landscape(A3), pageCompression=1)
    c.setTitle("HomeAura - магистрали K1-K2 в полу и два прохода AAC - D126")
    c.setAuthor("HomeAura Engineering Agent")
    w, h = landscape(A3)

    header(c, "D126 · МАГИСТРАЛИ K1 → ЛЕСТНИЦА → K2", "План первого этажа, два прохода через газобетон и отдельная совпадающая проходка перекрытия", 1)
    c.setFillColor(HexColor("#FFF0F0")); c.roundRect(13 * mm, h - 47 * mm, w - 26 * mm, 11 * mm, 2.5 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 9.5)
    c.drawCentredString(w / 2, h - 43 * mm, "НЕ СВЕРЛИТЬ СТЕНЫ И ПЛИТУ, НЕ ЗАКРЫВАТЬ КАНАЛ ДО ВЫПУСКА УЗЛОВ W01/W02, СКАНИРОВАНИЯ ПЛИТЫ И ВЫБОРА МАТЕРИАЛОВ")

    px0, py0, pw, ph = 18 * mm, 102 * mm, 265 * mm, 115 * mm
    c.setFillColor(HexColor("#F8FBFB")); c.roundRect(px0, py0, pw, ph, 3 * mm, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#A4B6BC")); c.roundRect(px0, py0, pw, ph, 3 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 11.5); c.drawString(px0 + 6 * mm, py0 + ph - 12 * mm, "ПЛАНОВАЯ ОСЬ 4 570 ММ")
    axis_y = py0 + 54 * mm
    lengths = [66.3996, 321.7342, 3009.8992, 317.5, 254.467]
    labels = ["комната", "W01 AAC", "холл", "W02 AAC", "котельная"]
    colors = ["#48A979", "#B8535C", "#48A979", "#B8535C", "#48A979"]
    scale = (pw - 16 * mm) / 3970.0
    cursor = px0 + 8 * mm
    for length, label, color in zip(lengths, labels, colors):
        width = max(1.5 * mm, length * scale)
        c.setFillColor(HexColor(color)); c.rect(cursor, axis_y, width, 22 * mm, stroke=0, fill=1)
        if width > 17 * mm:
            c.setFillColor(white); c.setFont("Segoe-Bold", 7.3); c.drawCentredString(cursor + width / 2, axis_y + 13.5 * mm, label)
            c.setFont("Segoe", 6.7); c.drawCentredString(cursor + width / 2, axis_y + 7 * mm, f"{length:.1f} мм")
        cursor += width
    c.setStrokeColor(HexColor("#C00025")); c.setLineWidth(1.7 * mm); c.line(px0 + 8 * mm, axis_y + 30 * mm, px0 + pw - 8 * mm, axis_y + 30 * mm)
    c.setFillColor(HexColor("#48A979")); c.setLineWidth(6 * mm); c.line(px0 + 11 * mm, axis_y - 4 * mm, px0 + 11 * mm, axis_y - 31 * mm)
    c.setFillColor(HexColor("#17603C")); c.setFont("Segoe-Bold", 8.2); c.drawString(px0 + 20 * mm, axis_y - 13 * mm, "поворот 600 мм вдоль западной стороны стены")
    c.setFont("Segoe", 7.4); c.drawString(px0 + 20 * mm, axis_y - 21 * mm, "опорная полоса 200 мм помещается на западной стороне")
    c.setFont("Segoe-Bold", 8); c.setFillColor(HexColor("#153A43")); c.drawString(px0 + 8 * mm, py0 + 12 * mm, "Пол: 3 930,8 мм · две стены: 639,2 мм · неизвестная ось: 0 мм")

    x = 290 * mm
    c.setFillColor(HexColor("#F8FBFB")); c.roundRect(x, 102 * mm, 117 * mm, 115 * mm, 3 * mm, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#A4B6BC")); c.roundRect(x, 102 * mm, 117 * mm, 115 * mm, 3 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 11.5); c.drawString(x + 7 * mm, 203 * mm, "ТРИ РАЗНЫХ УЗЛА")
    yy = 190 * mm
    nodes = [
        ("W01", "западная комната → холл", "321,7 мм AAC"),
        ("W02", "холл → котельная", "317,5 мм AAC"),
        ("P01 / D098", "плита у лестницы → гардеробная", "120×200 мм, оси 9250/7350 и 9250/7450"),
    ]
    for tag, name, detail in nodes:
        c.setFillColor(HexColor("#B8535C" if tag.startswith("W") else "#6F33A8")); c.roundRect(x + 7 * mm, yy - 12 * mm, 26 * mm, 12 * mm, 2 * mm, stroke=0, fill=1)
        c.setFillColor(white); c.setFont("Segoe-Bold", 8); c.drawCentredString(x + 20 * mm, yy - 7.5 * mm, tag)
        c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 8.2); c.drawString(x + 38 * mm, yy - 4 * mm, name)
        c.setFont("Segoe", 7.5); c.drawString(x + 38 * mm, yy - 11 * mm, detail)
        yy -= 28 * mm
    c.setFillColor(HexColor("#FFF3D9")); c.roundRect(x + 7 * mm, 110 * mm, 103 * mm, 18 * mm, 2 * mm, stroke=0, fill=1)
    paragraph(c, "W01/W02 не заменяют P01. Стеновые проходы остаются прямыми; повороты — только в доступных коробах.", x + 11 * mm, 124 * mm, 95 * mm, 7.7, "#805500", True)

    c.setFillColor(HexColor("#F8FBFB")); c.roundRect(18 * mm, 18 * mm, 389 * mm, 72 * mm, 3 * mm, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#A4B6BC")); c.roundRect(18 * mm, 18 * mm, 389 * mm, 72 * mm, 3 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 10.7); c.drawString(25 * mm, 79 * mm, "ПРАВИЛА ПРОХОДОВ")
    rules = [
        "две непрерывные предизолированные магистрали 32×3, наружный Ø62 мм; скрытых пресс-фитингов — 0;",
        "каждая труба защищена гладкой гильзой либо испытанной общей системой; сырой газобетон и острые кромки трубы не касаются;",
        "трубу не изгибают через край; тепловое перемещение не зажимают; монтажная пена не касается MLC/оболочки напрямую;",
        "для несущей или пока не классифицированной стены размер отверстия и перемычку выпускает ответственный проектировщик;",
        "P01 сверлится только после сканирования плиты и подтверждения совпадения отметок с обеих сторон перекрытия.",
    ]
    yy = 70 * mm
    for item in rules:
        yy -= bullet(c, item, 25 * mm, yy, 372 * mm) + 0.7 * mm
    footer(c, 1); c.showPage()

    header(c, "D126 · ПИРОГ ПОЛА И КОНТРОЛЬ ВЫПУСКА", "Существующий утеплитель: 100 мм на 1 этаже, 50 мм на мансарде; над ним остаётся по 70 мм", 2)
    c.setFillColor(HexColor("#FFF0F0")); c.roundRect(13 * mm, h - 47 * mm, w - 26 * mm, 11 * mm, 2.5 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 9.5)
    c.drawCentredString(w / 2, h - 43 * mm, "ПРЕДВАРИТЕЛЬНЫЙ УЗЕЛ: МАТЕРИАЛ ВЫРАВНИВАНИЯ, КРЕПЁЖ, СТЯЖКА, ФИНИШ И ПРОХОДКИ ЕЩЁ НЕ ВЫБРАНЫ")

    sx0, sy0, sw, sh = 20 * mm, 65 * mm, 240 * mm, 145 * mm
    c.setFillColor(HexColor("#F8FBFB")); c.roundRect(sx0, sy0, sw, sh, 3 * mm, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#A4B6BC")); c.roundRect(sx0, sy0, sw, sh, 3 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 11.7); c.drawString(sx0 + 7 * mm, sy0 + sh - 13 * mm, "ОСНОВНОЙ СПОСОБ В ПОЛУ")
    slab_y, ins_top_y, screed_top_y = sy0 + 18 * mm, sy0 + 67 * mm, sy0 + 93 * mm
    c.setFillColor(HexColor("#8A9498")); c.rect(sx0 + 10 * mm, slab_y, sw - 20 * mm, 12 * mm, stroke=0, fill=1)
    c.setFillColor(white); c.setFont("Segoe-Bold", 7); c.drawString(sx0 + 13 * mm, slab_y + 4 * mm, "Ж/Б ПЛИТА")
    c.setFillColor(HexColor("#DDEFA7")); c.rect(sx0 + 10 * mm, slab_y + 12 * mm, sw - 20 * mm, 37 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#38531C")); c.setFont("Segoe-Bold", 7.4); c.drawString(sx0 + 13 * mm, slab_y + 42 * mm, "100 мм существующего утеплителя")
    cx0, cx1 = sx0 + 82 * mm, sx0 + 158 * mm
    c.setFillColor(HexColor("#F7E9B9")); c.rect(cx0, slab_y + 12 * mm, cx1 - cx0, 37 * mm, stroke=0, fill=1)
    for cx, color in ((sx0 + 105 * mm, "#C83434"), (sx0 + 137 * mm, "#2477B3")):
        c.setFillColor(HexColor("#87959A")); c.circle(cx, slab_y + 28 * mm, 10 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor(color)); c.circle(cx, slab_y + 28 * mm, 5.2 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#B9DB75")); c.rect(cx0, slab_y + 42 * mm, cx1 - cx0, 7 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#38531C")); c.setFont("Segoe-Bold", 6.8); c.drawCentredString((cx0 + cx1) / 2, slab_y + 44.3 * mm, "верх выровнять до z=100")
    c.setFillColor(HexColor("#D8C9B1")); c.rect(sx0 + 10 * mm, ins_top_y, sw - 20 * mm, 26 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#5A4632")); c.setFont("Segoe-Bold", 7.4); c.drawString(sx0 + 13 * mm, ins_top_y + 17 * mm, "контур Ø16 + выбранная стяжка")
    for cx in (sx0 + 55 * mm, sx0 + 120 * mm, sx0 + 185 * mm):
        c.setFillColor(HexColor("#D33838")); c.circle(cx, ins_top_y + 4.5 * mm, 2.3 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#EEE5DA")); c.rect(sx0 + 10 * mm, screed_top_y, sw - 20 * mm, 12 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#5A4632")); c.setFont("Segoe-Bold", 7.3); c.drawString(sx0 + 13 * mm, screed_top_y + 4 * mm, "финиш / клей / подложка")
    c.setStrokeColor(HexColor("#C00025")); c.setLineWidth(1.6 * mm); c.line(cx0, ins_top_y + 2 * mm, cx1, ins_top_y + 2 * mm)
    c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 6.8); c.drawCentredString((cx0 + cx1) / 2, ins_top_y - 5 * mm, "ПОЛОСА 200 ММ: БЕЗ СКОБ / АНКЕРОВ")
    paragraph(c, "Трубы фиксируются к плите. До z=100 восстанавливается замкнутая ровная опорная поверхность связанным выравниванием либо доказанным жёстким утеплителем. Стяжка не опирается на трубы и не сминает заводскую изоляцию.", sx0 + 10 * mm, sy0 + 37 * mm, sw - 20 * mm, 7.6, "#153A43", False)

    x = 270 * mm
    c.setFillColor(HexColor("#F8FBFB")); c.roundRect(x, 65 * mm, 137 * mm, 145 * mm, 3 * mm, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#A4B6BC")); c.roundRect(x, 65 * mm, 137 * mm, 145 * mm, 3 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 11.7); c.drawString(x + 7 * mm, 197 * mm, "ДВА ПИРОГА В 70 ММ")
    for bx, title, cover, total, finish, color in (
        (x + 7 * mm, "A · CAF / АНГИДРИТ", 35, 51, 19, "#2677A6"),
        (x + 70 * mm, "B · ЦЕМЕНТНАЯ", 45, 61, 9, "#A55B2A"),
    ):
        c.setFillColor(white); c.roundRect(bx, 158 * mm, 56 * mm, 30 * mm, 2 * mm, stroke=0, fill=1)
        c.setStrokeColor(HexColor(color)); c.roundRect(bx, 158 * mm, 56 * mm, 30 * mm, 2 * mm, stroke=1, fill=0)
        c.setFillColor(HexColor(color)); c.setFont("Segoe-Bold", 8.1); c.drawString(bx + 4 * mm, 180 * mm, title)
        c.setFillColor(HexColor("#153A43")); c.setFont("Segoe", 7.3); c.drawString(bx + 4 * mm, 171 * mm, f"Ø16 + {cover} = {total} мм")
        c.setFont("Segoe-Bold", 7.5); c.drawString(bx + 4 * mm, 163 * mm, f"финиш: {finish} мм")
    c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 8.2); c.drawCentredString(x + 68.5 * mm, 151 * mm, "ВЕТВЬ НЕ ВЫБРАНА")
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 10.3); c.drawString(x + 7 * mm, 138 * mm, "ИСХОДНЫЕ ДАННЫЕ ВЛАДЕЛЬЦА")
    yy = 129 * mm
    owner = [
        "1 этаж: утеплитель 100 мм + запас 70 мм;",
        "мансарда: утеплитель 50 мм + запас 70 мм;",
        "высота между этажами: 3 000 мм; стены: газобетон;",
        "петли: Ø16, расчётный R80; уменьшение радиуса прогревом не учитывается;",
        "магистрали: Ø32×3; изменения направления — доступные пресс-отводы, не R80 петли.",
    ]
    for item in owner:
        yy -= bullet(c, item, x + 7 * mm, yy, 123 * mm) + 0.6 * mm
    c.setFillColor(HexColor("#153A43")); c.setFont("Segoe-Bold", 10.3); c.drawString(x + 7 * mm, 90 * mm, "ДО ВЫПУСКА В РАБОТУ")
    pending = [
        "марка/прочность существующего утеплителя; материал выравнивания и крепёж Ø62 к плите;",
        "конкретная стяжка, нагрузка, финиш и мокрые зоны;",
        "размеры/гильзы/заделка W01 и W02 после классификации стен;",
        "сканирование плиты и выпуск P01 120×200;",
        "опрессовка, фото и размеры до закрытия; 0 скрытых фитингов.",
    ]
    yy = 82 * mm
    for idx, item in enumerate(pending):
        yy -= bullet(c, item, x + 7 * mm, yy, 123 * mm, red=idx < 4) + 0.6 * mm
    footer(c, 2); c.showPage(); c.save()

    local_pdf = OUTPUT / PDF_OUT.name
    shutil.copy2(PDF_OUT, local_pdf)
    sheet = {
        "schema": "homeaura-floor-primary-coordination-sheet-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_SHEET_126",
        "status": "TWO_PAGE_COORDINATION_SHEET_PASS_NOT_CONSTRUCTION_RELEASE",
        "source_records": records,
        "pdf_file": PDF_OUT.name,
        "page_count": 2,
        "page_size": "A3_LANDSCAPE",
        "route_axis_length_mm": 4570.0,
        "vector_draft_floor_axis_length_mm": d124["audit_totals"]["vector_draft_floor_axis_length_mm"],
        "aac_wall_axis_length_mm": d124["audit_totals"]["aac_wall_axis_length_mm"],
        "aac_wall_crossing_count": len(d125["crossings"]),
        "approved_aac_wall_opening_count": d125["approved_wall_opening_count"],
        "separate_slab_penetration_coordination_size_mm": d098["selected_building_plan_opening_candidate"]["clear_size_mm"],
        "approved_slab_opening_count": 0,
        "floor_stack_option_count": 2,
        "selected_floor_stack_option_count": 0,
        "support_strip_strength_proven": False,
        "approved_pipe_geometry_count": 0,
        "construction_authorized": False,
        "result": "PASS_COORDINATION_CLARITY_REWORK_PRODUCTS_WALL_OPENINGS_SLAB_RELEASE_AND_SCREEED",
    }
    sheet["sheet_digest"] = digest(sheet)
    (OUTPUT / "floor_primary_coordination_sheet.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=2), encoding="utf8")
    (OUTPUT / "release_note.md").write_text(
        "# D126 — координационный лист магистралей\n\n"
        "Лист разделяет три физических узла: два поперечных прохода через газобетонные стены W01/W02 и совпадающее на этажах отверстие P01 в перекрытии у лестницы. "
        "Из плановой оси 4570 мм 3930,8 мм лежат в черновых областях пола, 639,2 мм — в двух стенах. На участках пола геометрически помещается опорная полоса 200 мм.\n\n"
        "К строительству лист не выпущен. Нужны материалы пола, крепёж, размеры гильз и стеновых отверстий, классификация стен, сканирование плиты и конкретная система стяжки/финиша.\n",
        encoding="utf8",
    )
    files = [p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    manifest = {"artifact_id": sheet["artifact_id"], "sheet_digest": sheet["sheet_digest"], "append_only": True,
                "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]}
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "pdf": str(PDF_OUT), "pdf_sha256": sha(PDF_OUT), "package": str(PACKAGE), "digest": sheet["sheet_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

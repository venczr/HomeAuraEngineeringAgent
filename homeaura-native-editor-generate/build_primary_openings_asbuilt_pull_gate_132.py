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
SOURCES = {
    "D131": BASE / "HA_TWO_FLOOR_PRIMARY_OPENINGS_OWNER_REPORT_131" / "primary_openings_owner_report.json",
    "D125": BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_AAC_CROSSINGS_125" / "floor_primary_aac_crossings.json",
    "D098": BASE / "HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098" / "two_primary_internal_penetration.json",
    "D130": BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_CLEAN_EVIDENCE_130" / "floor_primary_coordination_clean_evidence.json",
}
CLOUD_RESULT = Path(r"C:\Users\zahar\AppData\Local\HomeAuraMultiAgent\results\HA-FLOOR-PRIMARY-POSTOPENING-REVIEW-20260813-001.json")
OUTPUT = BASE / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ASBUILT_PULL_GATE_132"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ASBUILT_PULL_GATE_132.zip"
PDF_OUT = ROOT / "output" / "pdf" / "HomeAura_primary_openings_asbuilt_and_pull_gate_D132.pdf"

pdfmetrics.registerFont(TTFont("Segoe", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Segoe-Bold", r"C:\Windows\Fonts\seguisb.ttf"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def para(c, text, x, y, width, size=8, color="#163B44", bold=False, leading=None):
    style = ParagraphStyle("p", fontName="Segoe-Bold" if bold else "Segoe", fontSize=size,
                           leading=leading or size * 1.28, textColor=HexColor(color), alignment=TA_LEFT)
    p = Paragraph(text, style); _, height = p.wrap(width, 100 * mm); p.drawOn(c, x, y - height); return height


def header(c, title, subtitle, page):
    w, h = landscape(A3)
    c.setFillColor(HexColor("#071A21")); c.rect(0, h - 29 * mm, w, 29 * mm, stroke=0, fill=1)
    c.setFillColor(white); c.setFont("Segoe-Bold", 18); c.drawString(13 * mm, h - 11 * mm, title)
    c.setFillColor(HexColor("#A7EEE7")); c.setFont("Segoe", 9.5); c.drawString(13 * mm, h - 21 * mm, subtitle)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe-Bold", 8.3); c.drawRightString(w - 13 * mm, h - 17 * mm, f"A3 · лист {page}/2 · ПОЛЕВАЯ КАРТОЧКА")
    c.setFillColor(HexColor("#071A21")); c.rect(0, 0, w, 12 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#F3D58C")); c.setFont("Segoe", 7); c.drawString(13 * mm, 4.5 * mm, "D132 · отверстия выполнены со слов владельца; пустые поля требуют натурного заполнения.")
    c.setFont("Segoe-Bold", 7); c.drawRightString(w - 13 * mm, 4.5 * mm, "НЕ ЗАКРЫВАТЬ ПРОХОДЫ ДО ОПРЕССОВКИ")


def blank_line(c, x, y, width, label, unit=""):
    c.setFillColor(HexColor("#163B44")); c.setFont("Segoe", 7.3); c.drawString(x, y, label)
    start = x + 38 * mm
    c.setStrokeColor(HexColor("#87999F")); c.setLineWidth(0.5); c.line(start, y - 0.5 * mm, x + width - (12 * mm if unit else 0), y - 0.5 * mm)
    if unit:
        c.setFont("Segoe", 7); c.drawRightString(x + width, y, unit)


def box(c, x, y, w, h, title, color="#2C7FA7"):
    c.setFillColor(HexColor("#F8FBFB")); c.roundRect(x, y, w, h, 3 * mm, stroke=0, fill=1)
    c.setStrokeColor(HexColor(color)); c.setLineWidth(1); c.roundRect(x, y, w, h, 3 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor(color)); c.setFont("Segoe-Bold", 10.3); c.drawString(x + 6 * mm, y + h - 10 * mm, title)


def check(c, x, y, text, red=False):
    c.setStrokeColor(HexColor("#7A8D93")); c.rect(x, y - 2.5 * mm, 3.6 * mm, 3.6 * mm, stroke=1, fill=0)
    c.setFillColor(HexColor("#B00020" if red else "#163B44")); c.setFont("Segoe-Bold" if red else "Segoe", 7.2); c.drawString(x + 6 * mm, y - 1.1 * mm, text)


def draw_pdf():
    w, h = landscape(A3)
    c = canvas.Canvas(str(PDF_OUT), pagesize=(w, h), pageCompression=1)
    c.setTitle("HomeAura - исполнительная карточка отверстий и допуск к протяжке D132")
    c.setAuthor("HomeAura Engineering Agent")

    header(c, "D132 · ИСПОЛНИТЕЛЬНАЯ КАРТОЧКА W01 / W02 / P01", "Сверление завершено со слов владельца; натурная приёмка и протяжка труб ещё не выпущены", 1)
    c.setFillColor(HexColor("#FFF3D9")); c.roundRect(13 * mm, h - 47 * mm, w - 26 * mm, 11 * mm, 2.5 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#805500")); c.setFont("Segoe-Bold", 9.2); c.drawCentredString(w / 2, h - 43 * mm, "СТАТУС: ОТВЕРСТИЯ СДЕЛАНЫ · РАЗМЕРЫ И СОСТОЯНИЕ НЕ ПОДТВЕРЖДЕНЫ · ТРУБЫ ПОКА НЕ ПРОТЯГИВАТЬ")

    x_positions = [14 * mm, 148 * mm, 282 * mm]
    cards = [
        ("W01 · КОМНАТА → ХОЛЛ", "AAC", "321,7 мм - проектная толщина"),
        ("W02 · ХОЛЛ → КОТЕЛЬНАЯ", "AAC", "317,5 мм - проектная толщина"),
        ("P01 · ПЛИТА → ГАРДЕРОБНАЯ", "Ж/Б", "120×200 мм - только координационный ориентир"),
    ]
    card_y, card_w, card_h = 113 * mm, 126 * mm, 116 * mm
    for i, (title, material, note) in enumerate(cards):
        x = x_positions[i]; box(c, x, card_y, card_w, card_h, title, "#B8535C" if i < 2 else "#6F33A8")
        c.setFillColor(HexColor("#60757C")); c.setFont("Segoe-Bold", 7.2); c.drawString(x + 6 * mm, card_y + card_h - 18 * mm, f"Материал: {material} · {note}")
        yy = card_y + card_h - 29 * mm
        blank_line(c, x + 6 * mm, yy, card_w - 12 * mm, "чистый размер 1", "мм"); yy -= 10 * mm
        blank_line(c, x + 6 * mm, yy, card_w - 12 * mm, "чистый размер 2", "мм"); yy -= 10 * mm
        blank_line(c, x + 6 * mm, yy, card_w - 12 * mm, "толщина / глубина", "мм"); yy -= 10 * mm
        blank_line(c, x + 6 * mm, yy, card_w - 12 * mm, "ось / отметка", "мм"); yy -= 10 * mm
        check(c, x + 6 * mm, yy, "гильза или гладкая защитная система установлена"); yy -= 8 * mm
        check(c, x + 6 * mm, yy, "острые кромки сняты / защищены"); yy -= 8 * mm
        check(c, x + 6 * mm, yy, "трещины, сколы, видимые повреждения отсутствуют"); yy -= 8 * mm
        if i == 2:
            check(c, x + 6 * mm, yy, "арматура / балка не повреждены - подтверждено"); yy -= 8 * mm
            check(c, x + 6 * mm, yy, "совпадение верх/низ плиты измерено"); yy -= 8 * mm
        else:
            check(c, x + 6 * mm, yy, "статус стены и выполненного отверстия принят"); yy -= 8 * mm
            check(c, x + 6 * mm, yy, "прямой проход без фитинга внутри стены"); yy -= 8 * mm
        c.setFillColor(HexColor("#163B44")); c.setFont("Segoe", 7); c.drawString(x + 6 * mm, card_y + 12 * mm, "Фото до гильзы: __________________  после: __________________")
        c.drawString(x + 6 * mm, card_y + 5 * mm, "Проверил: __________________  дата: __________  подпись: __________")

    box(c, 14 * mm, 24 * mm, 394 * mm, 77 * mm, "ОБЩИЙ ДОПУСК К ПРОТЯЖКЕ ДВУХ МАГИСТРАЛЕЙ 32×3", "#00A37A")
    requirements = [
        "все три карточки заполнены; фото и размеры приложены; фактическая геометрия промаркирована на месте;",
        "для W01/W02 подтверждён статус стен и принят выполненный проём; для P01 принят фактический результат сверления плиты;",
        "выбраны гильзы/защита кромок и заделка, совместимые с заводской оболочкой; монтажная пена не касается трубы напрямую;",
        "две трубы проходят непрерывно, без скрытых соединений; повороты и пресс-фитинги остаются доступными;",
        "подача и обратка промаркированы с обоих концов; открытые концы закрыты чистыми защитными колпачками.",
    ]
    yy = 88 * mm
    for item in requirements:
        check(c, 21 * mm, yy, item); yy -= 10 * mm
    c.setFillColor(HexColor("#FFF0F0")); c.roundRect(282 * mm, 31 * mm, 118 * mm, 29 * mm, 2 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 8.3); c.drawString(288 * mm, 51 * mm, "РЕШЕНИЕ")
    check(c, 288 * mm, 43 * mm, "ДОПУСК К ПРОТЯЖКЕ", False)
    check(c, 346 * mm, 43 * mm, "СТОП / ДОРАБОТКА", True)
    c.setFont("Segoe", 7); c.setFillColor(HexColor("#163B44")); c.drawString(288 * mm, 35 * mm, "Ответственный: __________________  дата: __________")
    c.showPage()

    header(c, "D132 · ПОРЯДОК ПРОТЯЖКИ И СТОП-УСЛОВИЯ", "Только после заполнения листа 1; две непрерывные предизолированные магистрали 32×3", 2)
    c.setFillColor(HexColor("#FFF0F0")); c.roundRect(13 * mm, h - 47 * mm, w - 26 * mm, 11 * mm, 2.5 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor("#B00020")); c.setFont("Segoe-Bold", 9.2); c.drawCentredString(w / 2, h - 43 * mm, "НЕ ТЯНУТЬ ЧЕРЕЗ ОСТРУЮ КРОМКУ · НЕ ДЕЛАТЬ СКРЫТЫХ СОЕДИНЕНИЙ · НЕ ЗАКРЫВАТЬ ДО ОПРЕССОВКИ")

    box(c, 14 * mm, 70 * mm, 248 * mm, 160 * mm, "ПОСЛЕДОВАТЕЛЬНОСТЬ РАБОТ", "#2C7FA7")
    steps = [
        ("1", "Обмер и фото", "Заполнить W01/W02/P01, осмотреть кромки, сколы и фактическое положение отверстий."),
        ("2", "Защитная система", "Установить гладкие гильзы/вкладыши и защитить обе кромки; сохранить свободное тепловое перемещение."),
        ("3", "Пробная протяжка", "Пропустить мягкий протяжной элемент или контрольный шаблон без трубы; проверить доступ и сопротивление."),
        ("4", "Маркировка", "До протяжки обозначить SUPPLY/RETURN на обоих концах; концы закрыть от пыли и мусора."),
        ("5", "Протяжка", "Направление выбирает монтажник по фактическому доступу. Тянуть плавно; заводскую оболочку не повреждать."),
        ("6", "Доступные повороты", "Изменения направления Ø32 выполнять доступными пресс-отводами проектной основы; внутри стен и плиты фитингов нет."),
        ("7", "Фиксация и опора", "Не крепить к мягкому утеплителю и не пережимать оболочку. Сохранить 200-мм полосу без скоб/анкеров."),
        ("8", "Контроль до закрытия", "Осмотреть оболочку, сфотографировать трассу с размерами, выполнить опрессовку по принятой процедуре."),
    ]
    yy = 214 * mm
    for no, name, text in steps:
        c.setFillColor(HexColor("#2C7FA7")); c.circle(24 * mm, yy - 3 * mm, 4 * mm, stroke=0, fill=1)
        c.setFillColor(white); c.setFont("Segoe-Bold", 8); c.drawCentredString(24 * mm, yy - 5.4 * mm, no)
        c.setFillColor(HexColor("#163B44")); c.setFont("Segoe-Bold", 8); c.drawString(32 * mm, yy, name)
        para(c, text, 32 * mm, yy - 3 * mm, 220 * mm, 7.3)
        yy -= 17.8 * mm

    box(c, 270 * mm, 130 * mm, 138 * mm, 100 * mm, "СТОП-УСЛОВИЯ", "#B00020")
    stops = [
        "проём меньше выбранной гильзы с требуемым зазором;",
        "видна повреждённая арматура, трещина или нестабильный край;",
        "труба касается сырого AAC/бетона или острой кромки;",
        "для прохода требуется перегнуть трубу через край или нагреть её;",
        "появляется залом, царапина оболочки либо ненормальное сопротивление;",
        "предлагается соединение внутри стены, плиты или будущего закрытого пола;",
        "нет возможности оставить поворот/фитинг доступным;",
        "нет принятой процедуры опрессовки и фотофиксации.",
    ]
    yy = 214 * mm
    for text in stops:
        check(c, 278 * mm, yy, text, True); yy -= 10.2 * mm

    box(c, 270 * mm, 70 * mm, 138 * mm, 50 * mm, "ПОСЛЕ ПРОТЯЖКИ", "#00A37A")
    after = [
        "SUPPLY/RETURN читаются на K1 и K2; концы закрыты;",
        "оболочка цела на всех доступных участках и в выходах гильз;",
        "выполнены фото с рулеткой и привязкой каждого прохода;",
        "опрессовка оформлена отдельным протоколом;",
        "заделка и пол не закрыты до принятия результатов.",
    ]
    yy = 105 * mm
    for text in after:
        check(c, 278 * mm, yy, text); yy -= 8.2 * mm
    c.showPage(); c.save()


def main():
    if OUTPUT.exists() or PACKAGE.exists() or PDF_OUT.exists():
        raise SystemExit("append-only target already exists")
    models = {k: json.loads(v.read_text(encoding="utf8")) for k, v in SOURCES.items()}
    cloud = json.loads(CLOUD_RESULT.read_text(encoding="utf8"))
    assert cloud["status"] == "COMPLETED" and cloud["exit_code"] == 0 and not cloud["timed_out"]
    OUTPUT.mkdir(parents=True); PDF_OUT.parent.mkdir(parents=True, exist_ok=True)
    draw_pdf(); shutil.copy2(PDF_OUT, OUTPUT / PDF_OUT.name)
    gates = [
        {"gate_id": "G01_AS_BUILT_OPENING_RECORDS", "required_opening_ids": [o["opening_id"] for o in models["D131"]["openings"]], "pass": False},
        {"gate_id": "G02_STRUCTURAL_AND_WALL_DISPOSITION", "pass": False},
        {"gate_id": "G03_SLEEVE_EDGE_CLOSEOUT_SYSTEM", "pass": False},
        {"gate_id": "G04_CONTINUOUS_PIPE_AND_ACCESSIBLE_FITTINGS", "pass": False},
        {"gate_id": "G05_LABEL_CAP_AND_PULL_METHOD", "pass": False},
    ]
    record = {
        "schema": "homeaura-primary-openings-asbuilt-pull-gate-0.1",
        "artifact_id": "HA_TWO_FLOOR_PRIMARY_OPENINGS_ASBUILT_PULL_GATE_132",
        "status": "FIELD_ASBUILT_AND_PULL_GATE_READY_REWORK_SITE_COMPLETION",
        "source_records": [{"artifact_id": models[k]["artifact_id"], "sha256": sha(path)} for k, path in SOURCES.items()],
        "independent_cloud_review": {"task_id": cloud["task_id"], "agent": cloud["agent"], "status": cloud["status"], "stdout_sha256": cloud["stdout_sha256"], "material_findings_incorporated": ["OWNER_REPORT_NOT_VERIFICATION", "RETROACTIVE_ASBUILT_ACCEPTANCE", "STRUCTURAL_AND_WALL_DISPOSITION", "SLEEVE_AND_EDGE_PROTECTION", "ACCESSIBLE_BENDS_NO_HIDDEN_JOINTS", "LABEL_CAP_PRESSURE_TEST", "STOP_WORK_TRIGGERS"], "obsolete_D123_unknown_floor_scope_incorporated": False},
        "opening_count": 3,
        "owner_reported_drilled_count": 3,
        "independently_verified_opening_count": 0,
        "pull_release_gate_count": len(gates),
        "pull_release_gates": gates,
        "all_pull_release_gates_pass": False,
        "primary_design_basis": {"count": 2, "pipe": "UPONOR_UNI_PIPE_PLUS_32X3_DESIGN_BASIS", "factory_insulated_comparison_od_mm": 62, "continuous_no_hidden_joints": True, "supply_return_axis_pitch_mm": 100},
        "installation_sequence_count": 8,
        "stop_work_trigger_count": 8,
        "pressure_test_parameters_selected": False,
        "pipe_pull_authorized": False,
        "penetration_closeout_authorized": False,
        "construction_authorized": False,
        "pdf_file": PDF_OUT.name,
        "page_count": 2,
        "page_size": "A3_LANDSCAPE",
        "result": "PASS_FIELD_PACKET_READY_REWORK_MEASUREMENTS_DISPOSITIONS_SLEEVES_AND_PULL_RELEASE",
    }
    record["pull_gate_digest"] = digest(record)
    (OUTPUT / "primary_openings_asbuilt_pull_gate.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf8")
    (OUTPUT / "field_instruction.md").write_text(
        "# D132 - исполнительная приёмка и допуск к протяжке\n\n"
        "W01, W02 и P01 отмечены как выполненные со слов владельца. Полевая карточка готова к заполнению, но ни один из пяти шлюзов допуска пока не закрыт. "
        "Трубы можно протягивать только после обмера, принятия состояния стен/плиты, установки защиты кромок и гильз, подтверждения доступных поворотов и маркировки. "
        "После протяжки проходы остаются открытыми до фотофиксации и опрессовки по отдельно принятой процедуре.\n",
        encoding="utf8",
    )
    files = sorted(p for p in OUTPUT.iterdir() if p.is_file())
    manifest = {"artifact_id": record["artifact_id"], "pull_gate_digest": record["pull_gate_digest"], "append_only": True,
                "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]}
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "pdf": str(PDF_OUT), "pdf_sha256": sha(PDF_OUT), "package": str(PACKAGE), "digest": record["pull_gate_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
SCRATCH = ROOT / "tmp" / "pdfs" / "house_trial_001"
OUTPUT = ROOT / "homeaura-native-editor" / "examples" / "proposals" / "HA_TWO_FLOOR_TRIAL_002"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def marker(draw: ImageDraw.ImageDraw, xy: tuple[int, int], label: str) -> None:
    x, y = xy
    draw.ellipse((x - 24, y - 24, x + 24, y + 24), fill="#06242B", outline="#00E5D4", width=6)
    draw.line((x - 33, y, x + 33, y), fill="#00E5D4", width=4)
    draw.line((x, y - 33, x, y + 33), fill="#00E5D4", width=4)
    draw.text((x + 38, y - 25), label, font=font(27, True), fill="#003E49", stroke_width=4, stroke_fill="white")


def territory(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], label: str, color: str) -> None:
    draw.rounded_rectangle(bbox, radius=10, outline=color, width=5)
    x0, y0, _, _ = bbox
    draw.rounded_rectangle((x0 + 7, y0 + 7, x0 + 218, y0 + 45), radius=8, fill="#FFFFFFE8", outline=color, width=2)
    draw.text((x0 + 15, y0 + 9), label, font=font(21, True), fill=color)


def panel(draw: ImageDraw.ImageDraw, lines: list[str]) -> None:
    draw.rounded_rectangle((250, 175, 1635, 390), radius=18, fill="#FFFFFFF2", outline="#007F86", width=4)
    y = 190
    for index, line in enumerate(lines):
        draw.text((275, y), line, font=font(27 if index == 0 else 21, index == 0), fill="#102C33")
        y += 42 if index == 0 else 34


def annotate_floor_1(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    panel(draw, [
        "ЭТАЖ 1 — ИСХОДНЫЕ ПРАВИЛА ПРИНЯТЫ",
        "К1 — один коллектор в котельной; точка выбрана у стены холла.",
        "Труба идёт во всех помещениях и под мебелью/оборудованием.",
        "Под лестницей греем; NO-LAY только под тремя первыми ступенями.",
    ])
    territory(draw, (360, 455, 800, 760), "F1-A · 1–2 контура", "#008FD5")
    territory(draw, (360, 775, 800, 1045), "F1-B · 1–2 контура", "#5B3FD6")
    territory(draw, (360, 1065, 690, 1410), "F1-C · 1–2 контура", "#D23255")
    territory(draw, (610, 455, 1095, 1410), "F1-D · 3–4 контура", "#007B55")
    territory(draw, (1110, 455, 1560, 720), "F1-E · 1–2 контура", "#8A5A00")
    territory(draw, (1110, 740, 1560, 1410), "F1-F · 3–4 контура", "#E17000")
    territory(draw, (755, 1430, 1180, 1660), "F1-G · 1 контур", "#565F68")
    draw.rounded_rectangle((985, 665, 1088, 780), radius=8, fill="#D0000048", outline="#B00000", width=5)
    draw.text((825, 710), "NO-LAY: только\n3 первые ступени", font=font(20, True), fill="#A00000", stroke_width=3, stroke_fill="white")
    marker(draw, (1135, 650), "К1 · основной коллектор")
    image.convert("RGB").save(destination, quality=95)


def annotate_attic(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    panel(draw, [
        "МАНСАРДА — ПИТАНИЕ ОТ К1 ЧЕРЕЗ СТОЯК",
        "Отдельный коллектор К2 не создаётся; у лестницы отмечен стояк R1.",
        "Труба идёт по всей существующей площади и под мебелью/оборудованием.",
        "Серым оставлен только физический лестничный проём без перекрытия.",
    ])
    territory(draw, (390, 485, 830, 705), "M-A · 1–2 контура", "#8A5A00")
    territory(draw, (390, 715, 830, 1200), "M-B · 2–3 контура", "#008FD5")
    territory(draw, (390, 1210, 830, 1435), "M-C · 1–2 контура", "#D23255")
    territory(draw, (835, 585, 1115, 1435), "M-D · 3–4 контура", "#007B55")
    territory(draw, (1120, 485, 1590, 900), "M-E · 2–3 контура", "#5B3FD6")
    territory(draw, (1120, 910, 1590, 1095), "M-F · 1 контур", "#565F68")
    territory(draw, (1120, 1100, 1590, 1435), "M-G · 1–2 контура", "#E17000")
    draw.rounded_rectangle((835, 485, 1115, 790), radius=8, fill="#A0A0A045", outline="#A00000", width=4)
    draw.text((850, 500), "ПРОЁМ ЛЕСТНИЦЫ\nНЕТ ПЕРЕКРЫТИЯ", font=font(21, True), fill="#A00000")
    marker(draw, (1090, 845), "R1 · парный стояк от К1")
    image.convert("RGB").save(destination, quality=95)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=False)
    floor_source = SCRATCH / "floor_1_page_1.png"
    attic_source = SCRATCH / "attic_page_1.png"
    (OUTPUT / "floor_1_source_render.png").write_bytes(floor_source.read_bytes())
    (OUTPUT / "attic_source_render.png").write_bytes(attic_source.read_bytes())
    annotate_floor_1(floor_source, OUTPUT / "floor_1_accepted_rules.png")
    annotate_attic(attic_source, OUTPUT / "attic_accepted_rules.png")

    contract = {
        "trial_id": "HA_TWO_FLOOR_TRIAL_002",
        "status": "OWNER_RULES_ACCEPTED_ROUTING_DRAFT_NEXT",
        "units": "mm",
        "canonical_grid_mm": 100,
        "collector_strategy": {
            "collector_count": 1,
            "collector_id": "K1",
            "floor": "FLOOR_1",
            "room": "boiler_room",
            "selected_location": "hall-side wall in boiler room",
            "selection_basis": "owner allowed any convenient boiler-room position; shortest central distribution candidate was selected",
            "attic_feed": "separate supply and return riser pair R1 beside stair core",
            "riser_vertical_length_mm": None,
            "riser_length_policy": "must be measured or supplied before final circuit lengths are claimed",
        },
        "heating_scope": {
            "all_rooms": True,
            "under_fixed_furniture": True,
            "under_equipment": True,
            "under_ground_floor_stair": True,
            "no_lay": [
                "ground-floor footprint directly beneath the first three stair treads",
                "attic stairwell opening where no floor slab exists",
            ],
            "other_no_lay_zones": [],
        },
        "source_documents": [
            {
                "floor_id": "FLOOR_1",
                "pdf_path": r"C:\Users\zahar\Downloads\Telegram Desktop\План 1 этажа с отметками (2).pdf",
                "pdf_sha256": sha256(Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План 1 этажа с отметками (2).pdf")),
                "declared_scale": "1:100",
                "visible_overall_dimensions_m": [14.80, 11.80],
                "preliminary_circuit_range": [11, 16],
            },
            {
                "floor_id": "ATTIC",
                "pdf_path": r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf",
                "pdf_sha256": sha256(Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf")),
                "declared_scale": "1:100",
                "preliminary_circuit_range": [11, 17],
            },
        ],
        "routing_constraints": {
            "complete_circuit_length_mm": [40000, 80000],
            "one_ordered_route_per_circuit": True,
            "transits_are_included_in_length": True,
            "riser_is_included_in_attic_circuit_length": True,
            "route_style_profile": "HOMEAURA_OWNER_WHOLE_HOUSE_STYLE_V1",
        },
        "remaining_explicit_assumptions": [
            "The attic has no low-headroom no-lay strip unless the owner later marks one.",
            "All exterior walls are candidates for denser perimeter treatment, pending exact thermal-band confirmation.",
            "The exact floor-to-floor riser length is still unknown and will be shown separately in DRAFT length accounting.",
        ],
        "next_stage": "canonical tracing of room polygons and openings, followed by circuit and transit generation",
    }
    (OUTPUT / "accepted_source_contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")

    report = """# HomeAura — пробный двухэтажный дом 002

## Принятые указания владельца

- Один основной коллектор размещается в котельной первого этажа.
- Полы обогреваются во всех помещениях, включая котельную и входную группу.
- Труба проходит под мебелью и стационарным оборудованием.
- Пространство под лестницей первого этажа обогревается.
- Единственное исключение под лестницей первого этажа — пятно под тремя первыми ступенями.
- На мансарде физический лестничный проём остаётся без трубы, так как там нет перекрытия.

## Принятое размещение

`К1` выбран в котельной на стене со стороны центрального холла. Это сокращает общий пучок к левому крылу, кухне-гостиной и лестничному ядру. Мансарда питается отдельной парой вертикальных линий `R1` возле лестницы; второго коллектора в текущем договоре нет.

## Длина стояка

Высота между этажами в исходных PDF не указана. Вертикальная длина `R1` будет выделена отдельно и включена в длины мансардных контуров только после измерения. До этого итоговые длины мансарды останутся предварительными.

## Следующий блок

Трассировка канонических комнат, проёмов и единственных зон без трубы, затем генерация непрерывных контуров и коллекторных пучков для обоих этажей.
"""
    (OUTPUT / "planning_report.md").write_text(report, encoding="utf-8")

    files = []
    for path in sorted(OUTPUT.iterdir()):
        if path.is_file():
            files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps({"trial_id": "HA_TWO_FLOOR_TRIAL_002", "files": files}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()

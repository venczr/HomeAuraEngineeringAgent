from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
SCRATCH = ROOT / "tmp" / "pdfs" / "house_trial_001"
OUTPUT = (
    ROOT
    / "homeaura-native-editor"
    / "examples"
    / "proposals"
    / "HA_TWO_FLOOR_TRIAL_001"
)


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
    draw.text((x + 38, y - 25), label, font=font(28, True), fill="#003E49", stroke_width=4, stroke_fill="white")


def territory(
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    label: str,
    color: str,
) -> None:
    draw.rounded_rectangle(bbox, radius=10, outline=color, width=5)
    x0, y0, _, _ = bbox
    draw.rounded_rectangle((x0 + 7, y0 + 7, x0 + 190, y0 + 45), radius=8, fill="#FFFFFFDD", outline=color, width=2)
    draw.text((x0 + 15, y0 + 9), label, font=font(22, True), fill=color)


def panel(draw: ImageDraw.ImageDraw, lines: list[str]) -> None:
    box = (250, 185, 1635, 385)
    draw.rounded_rectangle(box, radius=18, fill="#FFFFFFEE", outline="#007F86", width=4)
    y = 200
    for index, line in enumerate(lines):
        draw.text((275, y), line, font=font(27 if index == 0 else 22, index == 0), fill="#102C33")
        y += 41 if index == 0 else 32


def annotate_floor_1(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    panel(
        draw,
        [
            "ЭТАЖ 1 — ПОДГОТОВКА К РАСКЛАДКЕ (DRAFT)",
            "К1? — предлагаемый коллектор в котельной у стены холла.",
            "Числа в территориях — предварительное количество контуров, не расчёт.",
            "Нужно подтвердить К1, отапливаемые зоны и места оборудования/мебели.",
        ],
    )
    territory(draw, (360, 455, 800, 760), "T1 · 1–2", "#008FD5")
    territory(draw, (360, 775, 800, 1045), "T2 · 1–2", "#5B3FD6")
    territory(draw, (360, 1065, 690, 1410), "T3 · 1–2", "#D23255")
    territory(draw, (820, 715, 1095, 1410), "T4 · 2–3", "#007B55")
    territory(draw, (1110, 455, 1560, 720), "T5 · 0–1", "#8A5A00")
    territory(draw, (1110, 740, 1560, 1410), "T6 · 3–4", "#E17000")
    territory(draw, (755, 1430, 1180, 1660), "T7 · 0–1", "#565F68")
    draw.rounded_rectangle((825, 455, 1090, 930), radius=8, fill="#A0A0A030", outline="#A00000", width=4)
    draw.text((842, 470), "ЛЕСТНИЦА\nNO-LAY", font=font(24, True), fill="#A00000")
    marker(draw, (1128, 650), "К1? один коллектор этажа")
    image.convert("RGB").save(destination, quality=95)


def annotate_attic(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    panel(
        draw,
        [
            "МАНСАРДА — ПОДГОТОВКА К РАСКЛАДКЕ (DRAFT)",
            "К2? — предлагаемый отдельный коллектор возле лестничного ядра.",
            "Комнаты размечены как территории; WC пока объединены условно.",
            "Нужно подтвердить К2, скосы кровли и зоны без трубы.",
        ],
    )
    territory(draw, (390, 485, 830, 705), "M1 · 1", "#8A5A00")
    territory(draw, (390, 715, 830, 1200), "M2 · 2–3", "#008FD5")
    territory(draw, (390, 1210, 830, 1435), "M3 · 1", "#D23255")
    territory(draw, (835, 585, 1115, 1435), "M4 · 3", "#007B55")
    territory(draw, (1120, 485, 1590, 900), "M5 · 2", "#5B3FD6")
    territory(draw, (1120, 910, 1590, 1095), "M6 · 1", "#565F68")
    territory(draw, (1120, 1100, 1590, 1435), "M7 · 1–2", "#E17000")
    draw.rounded_rectangle((835, 485, 1115, 790), radius=8, fill="#A0A0A030", outline="#A00000", width=4)
    draw.text((850, 500), "ЛЕСТНИЦА\nNO-LAY", font=font(24, True), fill="#A00000")
    marker(draw, (1090, 845), "К2? отдельный коллектор мансарды")
    image.convert("RGB").save(destination, quality=95)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=False)
    floor_source = SCRATCH / "floor_1_page_1.png"
    attic_source = SCRATCH / "attic_page_1.png"
    floor_copy = OUTPUT / "floor_1_source_render.png"
    attic_copy = OUTPUT / "attic_source_render.png"
    floor_copy.write_bytes(floor_source.read_bytes())
    attic_copy.write_bytes(attic_source.read_bytes())
    annotate_floor_1(floor_copy, OUTPUT / "floor_1_setup_review.png")
    annotate_attic(attic_copy, OUTPUT / "attic_setup_review.png")

    contract = {
        "trial_id": "HA_TWO_FLOOR_TRIAL_001",
        "status": "DRAFT_SOURCE_CONFIRMATION_REQUIRED",
        "units": "mm",
        "canonical_grid_mm": 100,
        "sources": [
            {
                "floor_id": "FLOOR_1",
                "pdf_path": r"C:\Users\zahar\Downloads\Telegram Desktop\План 1 этажа с отметками (2).pdf",
                "pdf_sha256": sha256(Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План 1 этажа с отметками (2).pdf")),
                "page_count": 1,
                "declared_scale": "1:100",
                "visible_overall_dimensions_m": [14.80, 11.80],
                "collector_candidate": {
                    "id": "K1_CANDIDATE",
                    "location": "boiler room at hall-side wall",
                    "confirmed": False,
                },
                "visible_spaces_m2": {
                    "entrance": 12.9,
                    "hall_and_stair": 30.7,
                    "kitchen_living": 40.9,
                    "boiler_room": 15.9,
                    "bedroom_1": 17.3,
                    "bedroom_2": 15.6,
                    "bath_and_toilet": 16.9,
                    "small_wc_shower": 4.4,
                },
                "preliminary_circuit_range": [10, 14],
            },
            {
                "floor_id": "ATTIC",
                "pdf_path": r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf",
                "pdf_sha256": sha256(Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf")),
                "page_count": 1,
                "declared_scale": "1:100",
                "collector_candidate": {
                    "id": "K2_CANDIDATE",
                    "location": "central hall beside stair core",
                    "confirmed": False,
                },
                "visible_spaces_m2": {
                    "wardrobe": 13.0,
                    "bedroom": 28.7,
                    "bath_and_wc": 12.9,
                    "central_hall": 39.9,
                    "children_room_1": 26.0,
                    "wc_1": 5.1,
                    "wc_2": 5.3,
                    "children_room_2": 20.6,
                },
                "preliminary_circuit_range": [11, 13],
            },
        ],
        "confirmed_no_lay": ["stair openings on both floors"],
        "unconfirmed_inputs": [
            "exact collector location and orientation on each floor",
            "whether one separate collector per floor is intended",
            "fixed boiler equipment and service clearances",
            "kitchen cabinet and appliance footprint",
            "bath, shower and fixed sanitary fixture footprints",
            "built-in wardrobes or other fixed furniture",
            "whether entrance veranda and boiler-room floors are heated",
            "attic low-headroom zones caused by roof slopes",
            "exterior-wall and perimeter-spacing confirmation",
        ],
        "routing_not_generated_reason": "Collector positions and no-lay polygons materially determine every canonical supply-to-return route. They cannot be invented from the PDF.",
        "next_after_confirmation": "Trace canonical room/opening/no-lay geometry, allocate transit bundles, then generate separate DRAFT CircuitRoute sets for both floors.",
    }
    (OUTPUT / "source_contract_draft.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report = """# HomeAura — пробный двухэтажный дом 001

## Выполнено

- Обе одностраничные PDF-схемы отрисованы в 1785 × 2526 px и визуально проверены.
- На первом этаже распознано основное пятно 14,80 × 11,80 м и восемь подписанных площадей.
- На мансарде распознано восемь подписанных площадей и центральное лестничное ядро.
- Лестничные проёмы отмечены как подтверждённые зоны без трубы.
- Создано предварительное территориальное разбиение и два кандидата положения коллекторов.

## Кандидаты коллекторов

- `К1?`: котельная, стена со стороны центрального холла.
- `К2?`: центральный холл мансарды рядом с лестничным ядром.
- Рабочее предположение: отдельный коллектор на каждом этаже.

## Почему трубы пока не проведены

Полная труба зависит от расположения коллекторов и реальных запретных зон. PDF не показывает оборудование котельной, кухонный гарнитур, ванны/душевые, встроенную мебель и низкие зоны мансарды. Их выдумывание испортило бы маршруты и обучающий пример.

После подтверждения исходных отметок следующий блок сразу создаст отдельные непрерывные контуры для каждого этажа с коллекторными пучками и длинами.
"""
    (OUTPUT / "planning_report.md").write_text(report, encoding="utf-8")

    manifest = {
        "trial_id": "HA_TWO_FLOOR_TRIAL_001",
        "files": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(OUTPUT.iterdir())
            if path.is_file()
        ],
    }
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()

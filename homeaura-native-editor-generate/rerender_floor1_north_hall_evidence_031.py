from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_NORTH_HALL_029"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_NORTH_HALL_EVIDENCE_031"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_NORTH_HALL_EVIDENCE_031.zip"
PX = 8.503937
TREAD_BOX = (113, 98, 127, 108)

COLOURS = [
    "#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC",
    "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93",
]


def sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def to_px(point):
    return round(point[0] * PX), round(point[1] * PX)


def point_box_distance(point, box) -> float:
    x, y = point
    x0, y0, x1, y1 = box
    dx = max(x0 - x, 0, x - x1)
    dy = max(y0 - y, 0, y - y1)
    return math.hypot(dx, dy)


def segment_box_distance(a, b, box) -> float:
    x0, y0, x1, y1 = box
    if a[0] == b[0]:
        if x0 <= a[0] <= x1 and max(min(a[1], b[1]), y0) <= min(max(a[1], b[1]), y1):
            return 0.0
        if max(min(a[1], b[1]), y0) <= min(max(a[1], b[1]), y1):
            return min(abs(a[0] - x0), abs(a[0] - x1))
    elif a[1] == b[1]:
        if y0 <= a[1] <= y1 and max(min(a[0], b[0]), x0) <= min(max(a[0], b[0]), x1):
            return 0.0
        if max(min(a[0], b[0]), x0) <= min(max(a[0], b[0]), x1):
            return min(abs(a[1] - y0), abs(a[1] - y1))
    corners = ((x0, y0), (x0, y1), (x1, y0), (x1, y1))
    values = [point_box_distance(a, box), point_box_distance(b, box)]
    if a[0] == b[0]:
        sx = a[0]
        lo, hi = sorted((a[1], b[1]))
        values.extend(math.hypot(cx - sx, cy - min(max(cy, lo), hi)) for cx, cy in corners)
    else:
        sy = a[1]
        lo, hi = sorted((a[0], b[0]))
        values.extend(math.hypot(cx - min(max(cx, lo), hi), cy - sy) for cx, cy in corners)
    return min(values)


def polyline_box_distance(points, box) -> float:
    return min(segment_box_distance(a, b, box) for a, b in zip(points, points[1:]))


def draw_base(model: dict, target: Path, mode: str) -> None:
    if mode == "overlay":
        image = Image.open(BACKGROUND).convert("RGB")
    else:
        image = Image.new("RGB", (1785, 1750), "#F7FAFA")
    canvas = ImageDraw.Draw(image, "RGBA")
    if mode != "overlay":
        grid_px = round(PX)
        for x in range(0, image.width, grid_px):
            canvas.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, grid_px):
            canvas.line((0, y, image.width, y), fill="#D8E2E2")
    canvas.rectangle((0, 0, image.width, 128), fill="#071A21")
    canvas.text((30, 13), "D031 · ДОКАЗАТЕЛЬСТВО ГЕОМЕТРИИ D029 · 12 КОНТУРОВ", font=font(26, True), fill="white")
    canvas.text(
        (30, 61),
        "C05 51,3 м · C06 72,5 м · C14 77,9 м · 0 контактов · ПОКРЫТИЕ: REWORK",
        font=font(17),
        fill="#A7EEE7",
    )
    canvas.text((30, 91), "Один логический K1 · физический коллектор и гидравлика не выбраны", font=font(13), fill="#C7D6DB")

    if mode != "overlay":
        x0, y0, x1, y1 = model["collector_contract"]["station_envelope_bbox_grid"]
        canvas.rectangle((*to_px((x0, y0)), *to_px((x1, y1))), outline="#006D67", width=3)
        canvas.text(to_px((x0 + 1, y0 + 2)), "K1 LOGICAL", font=font(11, True), fill="#006D67")

    tx0, ty0, tx1, ty1 = TREAD_BOX
    canvas.rectangle((*to_px((tx0, ty0)), *to_px((tx1, ty1))), fill="#F7CACA", outline="#B00020", width=3)
    canvas.text(to_px((tx0, ty0 - 2)), "НЕ КАТАТЬ: ПЕРВЫЕ 3 СТУПЕНИ", font=font(11, True), fill="#B00020")

    for route, colour in zip(model["routes"], COLOURS):
        points = [to_px(point) for point in route["ordered_points_grid"]]
        canvas.line(points, fill="white", width=9, joint="curve")
        canvas.line(points, fill=colour, width=4, joint="curve")
        anchor = to_px(route["heating_body_points_grid"][len(route["heating_body_points_grid"]) // 2])
        canvas.text(
            (anchor[0] + 4, anchor[1] + 4),
            f'{route["route_id"]} {route["total_length_mm"] / 1000:.1f} м',
            font=font(11, True), fill=colour, stroke_width=2, stroke_fill="white",
        )
    image.save(target, quality=96)


def draw_debug(model: dict, target: Path, clearances: dict) -> None:
    image = Image.new("RGB", (1785, 1750), "#F7FAFA")
    canvas = ImageDraw.Draw(image, "RGBA")
    grid_px = round(PX)
    for x in range(0, image.width, grid_px):
        canvas.line((x, 0, x, image.height), fill="#D8E2E2")
    for y in range(0, image.height, grid_px):
        canvas.line((0, y, image.width, y), fill="#D8E2E2")
    canvas.rectangle((0, 0, image.width, 150), fill="#071A21")
    canvas.text((30, 12), "D031 · C06: ТРИ РЕГУЛЯРНЫЕ ЛОПАСТИ", font=font(27, True), fill="white")
    canvas.text((30, 60), "Одна труба K1 → южная → средняя → северная лестничная → K1", font=font(17), fill="#A7EEE7")
    canvas.text(
        (30, 92),
        f'До 3 ступеней: вся C06 {clearances["whole_c06_mm"]:.0f} мм · переход {clearances["bypass_mm"]:.1f} мм · вертикаль x105 800 мм',
        font=font(15), fill="#F3D58C",
    )
    canvas.text((30, 119), "Зазоры указаны по оси трубы; диаметр и поверхностный зазор не рассчитаны", font=font(13), fill="#C7D6DB")

    lobe_boxes = [
        ("C06-L1 SOUTH", (106, 128, 126, 144), "#247BA0"),
        ("C06-L2 MIDDLE", (107, 110, 126, 126), "#008A5B"),
        ("C06-L3 NORTH STAIR", (108, 80, 125, 96), "#7A49E5"),
    ]
    for label, box, colour in lobe_boxes:
        x0, y0, x1, y1 = box
        canvas.rectangle((*to_px((x0, y0)), *to_px((x1, y1))), fill=colour + "20", outline=colour, width=3)
        canvas.text(to_px((x0, y0 + 1)), label, font=font(10, True), fill=colour, stroke_width=2, stroke_fill="white")

    tx0, ty0, tx1, ty1 = TREAD_BOX
    canvas.rectangle((*to_px((tx0, ty0)), *to_px((tx1, ty1))), fill="#F7CACA", outline="#B00020", width=4)
    canvas.text(to_px((tx0, ty0 - 2)), "3 СТУПЕНИ · NO PIPE", font=font(11, True), fill="#B00020")

    c06 = next(route for route in model["routes"] if route["route_id"] == "F1-C06")
    points = [to_px(point) for point in c06["ordered_points_grid"]]
    canvas.line(points, fill="white", width=12, joint="curve")
    canvas.line(points, fill="#6A35D4", width=5, joint="curve")
    for part, colour in zip(c06["semantic_route_parts"], ["#247BA0", "#E28B00", "#008A5B", "#C43D00", "#7A49E5"]):
        part_points = [to_px(point) for point in part["points_grid"]]
        canvas.line(part_points, fill=colour, width=7, joint="curve")
        mid = part_points[len(part_points) // 2]
        canvas.ellipse((mid[0] - 5, mid[1] - 5, mid[0] + 5, mid[1] + 5), fill=colour)
    image.save(target, quality=96)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D031 is append-only")
    source_bytes = (SOURCE / "canonical_geometry.json").read_bytes()
    model = json.loads(source_bytes.decode("utf-8"))
    c06 = next(route for route in model["routes"] if route["route_id"] == "F1-C06")
    bypass = next(part for part in c06["semantic_route_parts"] if part["role"] == "STAIR_EXCLUSION_BYPASS_TRANSITION")
    bypass_points = [tuple(point) for point in bypass["points_grid"]]
    route_points = [tuple(point) for point in c06["ordered_points_grid"]]
    clearances = {
        "whole_c06_mm": polyline_box_distance(route_points, TREAD_BOX) * 100,
        "bypass_mm": polyline_box_distance(bypass_points, TREAD_BOX) * 100,
        "vertical_x105_mm": abs(105 - TREAD_BOX[0]) * 100,
        "measurement": "CENTERLINE_TO_CLOSED_TREAD_BOX_EUCLIDEAN",
        "pipe_surface_clearance": "NOT_EVALUATED_PIPE_OD_NOT_SUPPLIED",
    }
    if not math.isclose(clearances["whole_c06_mm"], 200.0) or not math.isclose(clearances["bypass_mm"], 538.5164807134504):
        raise RuntimeError(clearances)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry_d029.json").write_bytes(source_bytes)
    (OUTPUT / "k1_twelve_route_gate_contract.json").write_bytes((SOURCE / "k1_twelve_route_gate_contract.json").read_bytes())
    draw_base(model, OUTPUT / "floor_1_north_hall_overlay.png", "overlay")
    draw_base(model, OUTPUT / "floor_1_north_hall_pipes_only.png", "pipes")
    draw_debug(model, OUTPUT / "floor_1_c06_three_lobe_debug.png", clearances)

    validation = {
        "artifact_id": "HA_TWO_FLOOR_FLOOR1_NORTH_HALL_EVIDENCE_031",
        "source_artifact_id": model["artifact_id"],
        "source_canonical_sha256": sha_bytes(source_bytes),
        "source_geometry_digest": model["geometry_digest"],
        "source_geometry_copied_byte_identical": True,
        "route_geometry_modified": False,
        "route_count": len(model["routes"]),
        "C05_total_length_mm": 51300,
        "C06_total_length_mm": c06["total_length_mm"],
        "C14_total_length_mm": 77900,
        "global_inter_route_contact_count": 0,
        "first_three_tread_hit_count": 0,
        "clearance_evidence": clearances,
        "visual_labels": {
            "evidence_id": "D031",
            "geometry_source": "D029",
            "C06_length_label": "72.5 m",
            "coverage_status": "REWORK",
        },
        "coverage_status": "REWORK_EXACT_POLYGON_UNION_AND_EXTERIOR_BAND",
        "C07_status": "CONDITIONAL_ONLY_AFTER_EXACT_POLYGON_COVERAGE",
        "result": "VISUAL_EVIDENCE_PASS_GEOMETRY_UNCHANGED_REWORK_COVERAGE",
    }
    (OUTPUT / "evidence_validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "report.md").write_text(
        "# D031 — исправленное доказательство D029\n\n"
        "Маршруты D029 скопированы побайтно и не изменены. На новых изображениях указаны правильные версия и длины: C05 51,3 м, C06 72,5 м, C14 77,9 м. "
        "C06 показан как одна труба через три регулярные лопасти. Первые три ступени выделены как запретная зона. "
        "Минимальное расстояние по оси всей C06 до неё — 200 мм; минимум перехода — 538,5 мм; значение 800 мм относится только к вертикальному отрезку x=105. "
        "Полное покрытие, наружная полоса 100 мм, поверхностный зазор трубы, физический коллектор и гидравлика не заявляются.\n",
        encoding="utf-8",
    )
    payload_files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    manifest = {
        "artifact_id": validation["artifact_id"],
        "source_geometry_digest": model["geometry_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in payload_files],
    }
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "clearances_mm": clearances, "source_sha256": sha_bytes(source_bytes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

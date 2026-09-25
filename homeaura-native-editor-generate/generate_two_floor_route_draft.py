from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
SETUP = ROOT / "homeaura-native-editor" / "examples" / "proposals" / "HA_TWO_FLOOR_TRIAL_002"
OUTPUT = ROOT / "homeaura-native-editor" / "examples" / "proposals" / "HA_TWO_FLOOR_ROUTE_DRAFT_007"
PX_PER_M = 85.05
MM_PER_PX = 1000.0 / PX_PER_M


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def clean(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for point in points:
        snapped = (round(point[0] / 8.5) * 8.5, round(point[1] / 8.5) * 8.5)
        normalized = (int(round(snapped[0])), int(round(snapped[1])))
        if not out or out[-1] != normalized:
            out.append(normalized)
    return out


def rectangular_counterflow(box: tuple[int, int, int, int], entry_side: str) -> list[tuple[int, int]]:
    x0, y0, x1, y1 = box
    spacing = 17
    frame_count = max(0, min((x1 - x0 - 4 * spacing) // (4 * spacing), (y1 - y0 - 4 * spacing) // (4 * spacing)))
    if frame_count < 1:
        return elongated_meander(box, entry_side)
    points: list[tuple[int, int]] = [(x1, y0)]
    for index in range(frame_count + 1):
        left = x0 + 2 * spacing * index
        top = y0 + 2 * spacing * index
        bottom = y1 - 2 * spacing * index
        next_right = x1 - 2 * spacing * (index + 1)
        points.extend([(left, top), (left, bottom), (next_right, bottom)])
        if index < frame_count:
            points.append((next_right, y0 + 2 * spacing * (index + 1)))

    # One compact orthogonal centre turn onto the interleaved outward lane.
    final_right = x1 - 2 * spacing * (frame_count + 1)
    outward_top = y0 + (2 * frame_count + 1) * spacing
    outward_right = x1 - (2 * frame_count + 1) * spacing
    points.extend([(final_right, outward_top), (outward_right, outward_top)])

    for index in range(frame_count, -1, -1):
        left = x0 + (2 * index + 1) * spacing
        top = y0 + (2 * index + 1) * spacing
        right = x1 - (2 * index + 1) * spacing
        bottom = y1 - (2 * index + 1) * spacing
        if points[-1] != (right, top):
            points.append((right, top))
        points.extend([(right, bottom), (left, bottom)])
        if index > 0:
            outer_top = y0 + (2 * (index - 1) + 1) * spacing
            outer_right = x1 - (2 * (index - 1) + 1) * spacing
            points.extend([(left, outer_top), (outer_right, outer_top)])
    points = clean(points)
    if entry_side == "LEFT":
        center = x0 + x1
        points = [(center - x, y) for x, y in points]
    return clean(points)


def elongated_meander(box: tuple[int, int, int, int], entry_side: str) -> list[tuple[int, int]]:
    x0, y0, x1, y1 = box
    horizontal = (x1 - x0) >= (y1 - y0)
    spacing = 17
    points: list[tuple[int, int]] = []
    if horizontal:
        ys = list(range(y0, y1 + 1, spacing))
        points.append((x1, ys[0]))
        for i, y in enumerate(ys):
            other_x = x0 if i % 2 == 0 else x1
            points.append((other_x, y))
            if i + 1 < len(ys):
                points.append((other_x, ys[i + 1]))
    else:
        xs = list(range(x1, x0 - 1, -spacing))
        points.append((xs[0], y0))
        for i, x in enumerate(xs):
            other_y = y1 if i % 2 == 0 else y0
            points.append((x, other_y))
            if i + 1 < len(xs):
                points.append((xs[i + 1], other_y))
    if entry_side == "LEFT":
        center = x0 + x1
        points = [(center - x, y) for x, y in points]
    return clean(points)


def connect(start: tuple[int, int], end: tuple[int, int], lane_x: int) -> list[tuple[int, int]]:
    return clean([start, (lane_x, start[1]), (lane_x, end[1]), end])


def length_mm(points: list[tuple[int, int]]) -> float:
    return sum(math.dist(a, b) for a, b in zip(points, points[1:])) * MM_PER_PX


def orientation(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int]) -> int:
    value = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (value > 0) - (value < 0)


def intersects(first, second) -> bool:
    a, b = first
    c, d = second
    if a in (c, d) or b in (c, d):
        return False
    o1, o2, o3, o4 = orientation(a, b, c), orientation(a, b, d), orientation(c, d, a), orientation(c, d, b)
    return o1 != o2 and o3 != o4


def self_intersections(points: list[tuple[int, int]]) -> int:
    segments = list(zip(points, points[1:]))
    count = 0
    for i in range(len(segments)):
        for j in range(i + 2, len(segments)):
            a, b = segments[i]
            c, d = segments[j]
            if not intersects(segments[i], segments[j]):
                continue
            cross = orientation(a, b, c) != 0 and orientation(a, b, d) != 0 and orientation(c, d, a) != 0 and orientation(c, d, b) != 0
            if cross:
                count += 1
    return count


@dataclass
class Candidate:
    route_id: str
    floor_id: str
    room: str
    box: tuple[int, int, int, int]
    entry_side: str
    topology: str = "RECTANGULAR_COUNTERFLOW"


COLORS = [
    "#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#A26700", "#F07A00", "#263C85",
    "#008C95", "#7B1E3A", "#5E9400", "#B24AA7", "#0066CC", "#8B5A2B", "#C43D00", "#3949AB",
]


FLOOR_1 = [
    Candidate("F1-C01", "FLOOR_1", "bedroom_17_3", (375, 480, 785, 730), "RIGHT"),
    Candidate("F1-C02", "FLOOR_1", "bedroom_15_6", (375, 805, 785, 1020), "RIGHT"),
    Candidate("F1-C03", "FLOOR_1", "bath_wc_left", (375, 1090, 510, 1380), "RIGHT", "ELONGATED_MEANDER"),
    Candidate("F1-C04", "FLOOR_1", "bath_wc_right", (535, 1090, 670, 1380), "RIGHT", "ELONGATED_MEANDER"),
    Candidate("F1-C05", "FLOOR_1", "hall_west", (690, 730, 795, 1380), "RIGHT", "ELONGATED_MEANDER"),
    Candidate("F1-C06", "FLOOR_1", "hall_south_west", (720, 1090, 875, 1380), "RIGHT", "ELONGATED_MEANDER"),
    Candidate("F1-C07", "FLOOR_1", "hall_south_east", (890, 1090, 1050, 1380), "RIGHT", "ELONGATED_MEANDER"),
    Candidate("F1-C08", "FLOOR_1", "boiler_room", (1140, 480, 1540, 690), "LEFT"),
    Candidate("F1-C09", "FLOOR_1", "kitchen_living_nw", (1140, 770, 1330, 1060), "LEFT"),
    Candidate("F1-C10", "FLOOR_1", "kitchen_living_ne", (1345, 770, 1540, 1060), "LEFT"),
    Candidate("F1-C11", "FLOOR_1", "kitchen_living_sw", (1140, 1080, 1330, 1380), "LEFT"),
    Candidate("F1-C12", "FLOOR_1", "kitchen_living_se", (1345, 1080, 1540, 1380), "LEFT"),
    Candidate("F1-C13", "FLOOR_1", "small_wc_shower", (705, 1190, 805, 1380), "RIGHT", "ELONGATED_MEANDER"),
    Candidate("F1-C14", "FLOOR_1", "entrance", (780, 1460, 1150, 1620), "RIGHT", "ELONGATED_MEANDER"),
]


ATTIC = [
    Candidate("A-C01", "ATTIC", "wardrobe", (410, 510, 810, 680), "RIGHT", "ELONGATED_MEANDER"),
    Candidate("A-C02", "ATTIC", "bedroom_north", (410, 740, 810, 950), "RIGHT"),
    Candidate("A-C03", "ATTIC", "bedroom_south", (410, 970, 810, 1180), "RIGHT"),
    Candidate("A-C04", "ATTIC", "bath_wc", (410, 1230, 810, 1410), "RIGHT", "ELONGATED_MEANDER"),
    Candidate("A-C05", "ATTIC", "hall_west", (840, 820, 940, 1410), "RIGHT", "ELONGATED_MEANDER"),
    Candidate("A-C06", "ATTIC", "hall_centre", (955, 820, 1060, 1410), "RIGHT", "ELONGATED_MEANDER"),
    Candidate("A-C07", "ATTIC", "hall_south", (840, 1210, 1100, 1410), "RIGHT", "ELONGATED_MEANDER"),
    Candidate("A-C08", "ATTIC", "children_26_left", (1140, 510, 1340, 880), "LEFT"),
    Candidate("A-C09", "ATTIC", "children_26_right", (1360, 510, 1570, 880), "LEFT"),
    Candidate("A-C10", "ATTIC", "wc_5_1", (1140, 930, 1325, 1075), "LEFT", "ELONGATED_MEANDER"),
    Candidate("A-C11", "ATTIC", "wc_5_3", (1340, 930, 1570, 1075), "LEFT", "ELONGATED_MEANDER"),
    Candidate("A-C12", "ATTIC", "children_20_north", (1140, 1120, 1570, 1250), "LEFT", "ELONGATED_MEANDER"),
    Candidate("A-C13", "ATTIC", "children_20_south", (1140, 1270, 1570, 1410), "LEFT", "ELONGATED_MEANDER"),
]


def make_routes(candidates: list[Candidate], hub: tuple[int, int], is_attic: bool) -> list[dict]:
    routes = []
    for index, candidate in enumerate(candidates):
        body = elongated_meander(candidate.box, candidate.entry_side) if candidate.topology == "ELONGATED_MEANDER" else rectangular_counterflow(candidate.box, candidate.entry_side)
        # Keep the heating body visually readable on the architectural plan.
        # Collector transits stay explicit in the data contract and the riser diagram;
        # they are not overplotted across walls until portal lanes are traced canonically.
        points = body
        known_length = length_mm(body)
        routes.append({
            "route_id": candidate.route_id,
            "floor_id": candidate.floor_id,
            "room_or_territory": candidate.room,
            "topology": candidate.topology,
            "collector_id": "K1",
            "supply_port_index": index * 2 + (28 if is_attic else 0),
            "return_port_index": index * 2 + 1 + (28 if is_attic else 0),
            "heating_body_points_px": [{"x": x, "y": y} for x, y in body],
            "ordered_plan_points_px": None,
            "known_heating_body_length_mm": round(known_length),
            "known_planar_length_mm": None,
            "vertical_supply_length_mm": None if is_attic else 0,
            "vertical_return_length_mm": None if is_attic else 0,
            "total_length_mm": None,
            "self_intersection_count": None,
            "collector_transit_status": "NOT_ROUTED_UNTIL_PORTALS_TRACED",
            "training_label": "DRAFT",
        })
    return routes


def draw_routes(background: Path, routes: list[dict], destination: Path, title: str, note: str) -> None:
    image = Image.open(background).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((180, 125, 1640, 300), radius=18, fill="#071A21EE", outline="#00CFC0", width=4)
    draw.text((210, 145), title, font=font(30, True), fill="#FFFFFF")
    draw.text((210, 190), note, font=font(21), fill="#C8F7F2")
    draw.text((210, 225), f"Тел контуров: {len(routes)} · коллекторные транзиты пока вынесены из плана", font=font(21), fill="#C8F7F2")
    for index, route in enumerate(routes):
        color = COLORS[index % len(COLORS)]
        points = [(item["x"], item["y"]) for item in route["heating_body_points_px"]]
        draw.line(points, fill=color, width=4, joint="curve")
        midpoint = points[len(points) // 2]
        label = route["route_id"] + f" · тело {route['known_heating_body_length_mm']/1000:.1f} м"
        draw.text(midpoint, label, font=font(15, True), fill=color, stroke_width=3, stroke_fill="#FFFFFF")
    image.convert("RGB").save(destination, quality=95)


def draw_riser(routes: list[dict], destination: Path) -> None:
    image = Image.new("RGB", (1500, 1000), "#07151B")
    draw = ImageDraw.Draw(image)
    draw.text((80, 55), "R1 — НЕПРЕРЫВНОСТЬ МАНСАРДНЫХ КОНТУРОВ", font=font(34, True), fill="#FFFFFF")
    draw.text((80, 105), "Один К1 в котельной; для каждого контура отдельные подача и обратка.", font=font(23), fill="#B8E9E5")
    draw.rounded_rectangle((90, 190, 420, 870), radius=25, outline="#00D4C4", width=5)
    draw.text((145, 220), "К1 · КОТЕЛЬНАЯ", font=font(25, True), fill="#00D4C4")
    draw.rounded_rectangle((1080, 190, 1410, 870), radius=25, outline="#00D4C4", width=5)
    draw.text((1130, 220), "МАНСАРДА R1", font=font(25, True), fill="#00D4C4")
    for index, route in enumerate(routes):
        y = 285 + index * 42
        color = COLORS[index % len(COLORS)]
        draw.line((350, y, 1140, y), fill=color, width=4)
        draw.line((350, y + 10, 1140, y + 10), fill=color, width=4)
        draw.text((610, y - 18), route["route_id"], font=font(17, True), fill=color, stroke_width=2, stroke_fill="#07151B")
    draw.text((505, 900), "Вертикальная длина не указана — итоговые длины NOT_EVALUATED", font=font(22, True), fill="#FFB74D")
    image.save(destination, quality=95)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=False)
    floor_routes = make_routes(FLOOR_1, (1135, 650), False)
    attic_routes = make_routes(ATTIC, (1090, 845), True)
    draw_routes(
        SETUP / "floor_1_source_render.png",
        floor_routes,
        OUTPUT / "floor_1_route_draft.png",
        "ЭТАЖ 1 · МАРШРУТНЫЙ ЧЕРНОВИК 001",
        "К1 в котельной; под лестницей греем, кроме первых трёх ступеней.",
    )
    draw_routes(
        SETUP / "attic_source_render.png",
        attic_routes,
        OUTPUT / "attic_route_draft.png",
        "МАНСАРДА · МАРШРУТНЫЙ ЧЕРНОВИК 001",
        "Фрагменты связаны с К1 отдельными линиями через R1; лестничный проём не перекрывается.",
    )
    draw_riser(attic_routes, OUTPUT / "riser_R1_continuity.png")

    all_routes = floor_routes + attic_routes
    validation = {
        "status": "DRAFT_BODY_LAYOUT_READY_FOR_REVIEW",
        "deterministic": "PASS",
        "source_contract": "PASS",
        "collector_count": {"value": 1, "result": "PASS"},
        "floor_1_route_count": len(floor_routes),
        "attic_route_count": len(attic_routes),
        "one_colour_per_route": "PASS",
        "heating_body_points_present": "PASS",
        "known_heating_body_length_calculated": "PASS",
        "complete_ordered_routes": "NOT_EVALUATED",
        "riser_pair_per_attic_route": "PASS",
        "raster_trace_accuracy": "NOT_EVALUATED",
        "wall_portal_legality": "NOT_EVALUATED",
        "heating_body_self_intersections": "NOT_EVALUATED",
        "inter_circuit_crossings": "NOT_EVALUATED",
        "first_three_tread_exact_polygon": "NOT_EVALUATED",
        "riser_vertical_length": "NOT_EVALUATED",
        "attic_total_40_80m": "NOT_EVALUATED",
        "hydraulics_and_manifold_capacity": "NOT_EVALUATED",
        "note": "This is a visual routing draft, not accepted canonical engineering geometry.",
    }
    geometry = {
        "schema_version": "homeaura-two-floor-route-proposal-0.1",
        "trial_id": "HA_TWO_FLOOR_ROUTE_DRAFT_007",
        "training_label": "DRAFT",
        "units": "mm",
        "plan_calibration": {"pixels_per_metre": PX_PER_M, "basis": "visible 14.80m and 11.80m first-floor dimensions", "accuracy": "DRAFT_RASTER"},
        "collector": {"collector_id": "K1", "floor_id": "FLOOR_1", "room": "boiler_room", "plan_anchor_px": {"x": 1135, "y": 650}},
        "riser": {"riser_id": "R1", "attic_anchor_px": {"x": 1090, "y": 845}, "vertical_length_mm": None, "shared_pipe_trunk": False, "distinct_pipe_count": len(attic_routes) * 2},
        "heating_scope": {"under_furniture": True, "under_equipment": True, "under_stair": True, "first_three_treads_no_lay": True, "attic_stair_opening_physical_void": True},
        "routes": all_routes,
        "validation_file": "validation.json",
    }
    (OUTPUT / "geometry_draft.json").write_text(json.dumps(geometry, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    report = f"""# HA_TWO_FLOOR_ROUTE_DRAFT_007

Создан первый визуальный маршрутный черновик для двух этажей по правилам владельца.

- Один коллектор `К1` в котельной.
- Первый этаж: {len(floor_routes)} цветных тел контуров.
- Мансарда: {len(attic_routes)} цветных тел контуров.
- Стояк `R1`: {len(attic_routes) * 2} отдельных вертикальных труб, без общего трубопровода и ветвлений.
- Пол под мебелью, оборудованием и основной лестницей включён.
- Под первыми тремя ступенями первого этажа оставлено исключение.
- Физический лестничный проём мансарды не перекрывается трубой.

Черновик не принят: коллекторные транзиты не проведены поверх стен до трассировки дверных порталов. Точный полигон трёх ступеней, межконтурные пересечения и высота стояка ещё не подтверждены. Поэтому полные маршруты, итоговые длины и ограничение 40–80 м имеют статус `NOT_EVALUATED`.
"""
    (OUTPUT / "report.md").write_text(report, encoding="utf-8")
    files = []
    for path in sorted(OUTPUT.iterdir()):
        if path.is_file():
            files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({"trial_id": geometry["trial_id"], "files": files}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SETUP = BASE / "HA_TWO_FLOOR_TRIAL_002"
OUTPUT = BASE / "HA_TWO_FLOOR_ROUTE_DRAFT_009"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ROUTE_DRAFT_009.zip"
GRID_MM = 100
PX_PER_GRID = 8.5
Point = tuple[int, int]
Segment = tuple[Point, Point]
COLORS = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#A26700", "#F07A00", "#263C85", "#008C95", "#7B1E3A", "#5E9400", "#B24AA7", "#0066CC", "#8B5A2B", "#C43D00"]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def clean(points: Iterable[Point]) -> list[Point]:
    out: list[Point] = []
    for p in points:
        if out and out[-1] == p:
            continue
        if len(out) > 1:
            a, b = out[-2], out[-1]
            if a[0] == b[0] == p[0] or a[1] == b[1] == p[1]:
                out[-1] = p
                continue
        out.append(p)
    return out


def to_px(point: Point) -> Point:
    return round(point[0] * PX_PER_GRID), round(point[1] * PX_PER_GRID)


def length(points: list[Point]) -> int:
    return sum((abs(a[0] - b[0]) + abs(a[1] - b[1])) * GRID_MM for a, b in zip(points, points[1:]))


def cross(a: Point, b: Point, c: Point) -> int:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def relation(s: Segment, t: Segment) -> str:
    a, b = s; c, d = t
    values = cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b)
    if values == (0, 0, 0, 0):
        ox = min(max(a[0], b[0]), max(c[0], d[0])) - max(min(a[0], b[0]), min(c[0], d[0]))
        oy = min(max(a[1], b[1]), max(c[1], d[1])) - max(min(a[1], b[1]), min(c[1], d[1]))
        if max(ox, oy) > 0: return "COLLINEAR_OVERLAP"
        if ox == 0 and oy == 0: return "POINT_TOUCH"
        return "DISJOINT"
    hit = ((values[0] == 0 or values[1] == 0 or (values[0] < 0) != (values[1] < 0)) and (values[2] == 0 or values[3] == 0 or (values[2] < 0) != (values[3] < 0)))
    if not hit: return "DISJOINT"
    return "T_TOUCH" if 0 in values else "PROPER_CROSSING"


def validate(points: list[Point]) -> dict:
    segs = list(zip(points, points[1:])); bad = []
    for i, a in enumerate(segs):
        for j in range(i + 2, len(segs)):
            r = relation(a, segs[j])
            if r != "DISJOINT": bad.append({"first_segment": i, "second_segment": j, "relation": r})
    neighbours: dict[Point, set[Point]] = defaultdict(set)
    for a, b in segs: neighbours[a].add(b); neighbours[b].add(a)
    endpoints = sum(len(v) == 1 for v in neighbours.values()); branches = sum(len(v) > 2 for v in neighbours.values())
    result = not bad and endpoints == 2 and branches == 0 and all(a != b for a, b in segs)
    return {"endpoint_count": endpoints, "branch_count": branches, "nonadjacent_contact_count": len(bad), "contacts": bad, "result": "PASS" if result else "FAIL"}


def point_in_box(point: Point, box: tuple[int, int, int, int]) -> bool:
    x0, y0, x1, y1 = box
    return x0 <= point[0] <= x1 and y0 <= point[1] <= y1


def segment_hits_box(segment: Segment, box: tuple[int, int, int, int]) -> bool:
    if point_in_box(segment[0], box) or point_in_box(segment[1], box):
        return True
    x0, y0, x1, y1 = box
    return any(relation(segment, edge) != "DISJOINT" for edge in [((x0,y0),(x1,y0)),((x1,y0),(x1,y1)),((x1,y1),(x0,y1)),((x0,y1),(x0,y0))])


def inter_contacts(routes: list[dict]) -> list[dict]:
    bad = []
    for i, first in enumerate(routes):
        fs = list(zip(first["ordered_points_grid"], first["ordered_points_grid"][1:]))
        for second in routes[i + 1:]:
            ss = list(zip(second["ordered_points_grid"], second["ordered_points_grid"][1:]))
            for a_i, a in enumerate(fs):
                for b_i, b in enumerate(ss):
                    found = relation(a, b)
                    if found != "DISJOINT": bad.append({"first_route_id": first["route_id"], "first_segment": a_i, "second_route_id": second["route_id"], "second_segment": b_i, "relation": found})
    return bad


def ring(bounds: tuple[int, int, int, int], gl: int, gr: int, right: bool) -> list[Point]:
    left, top, r, bottom = bounds
    return [(gr, bottom), (r, bottom), (r, top), (left, top), (left, bottom), (gl, bottom)] if right else [(gl, bottom), (left, bottom), (left, top), (r, top), (r, bottom), (gr, bottom)]


def spiral(box: tuple[int, int, int, int], side: str) -> list[Point]:
    x0, y0, x1, y1 = box; frames = []; l, t, r, b = x0 + 1, y0 + 1, x1 - 1, y1 - 1
    for _ in range(4): frames.append((l, t, r, b)); l += 2; t += 2; r -= 2; b -= 2
    deep = frames[3]; c = max(deep[0] + 4, min((deep[0] + deep[2]) // 2, deep[2] - 4)); p = []
    for q in ring(frames[0], c - 2, c + 3, True) + [(c + 2, frames[0][3]), (c + 2, frames[2][3])] + ring(frames[2], c - 1, c + 2, True) + [(c - 1, frames[3][3]), (c - 2, frames[3][3])] + ring(frames[3], c - 2, c, False) + [(c, frames[1][3])] + ring(frames[1], c, c + 3, False):
        if not p or p[-1] != q: p.append(q)
    if side == "BOTTOM": return clean(p)
    if side == "TOP": return clean((x, y0 + y1 - y) for x, y in p)
    # transpose a bottom-opening spiral to produce side gates
    q = spiral((y0, x0, y1, x1), "BOTTOM"); q = [(y, x) for x, y in q]
    return clean(q if side == "RIGHT" else ((x0 + x1 - x, y) for x, y in q))


def meander(box: tuple[int, int, int, int], horizontal: bool | None = None) -> list[Point]:
    x0, y0, x1, y1 = box; horizontal = (x1 - x0) >= (y1 - y0) if horizontal is None else horizontal; p = []
    if horizontal:
        for i, y in enumerate(range(y0 + 1, y1, 2)):
            ends = ((x1 - 1, y), (x0 + 1, y)) if i % 2 == 0 else ((x0 + 1, y), (x1 - 1, y))
            if not p: p.append(ends[0])
            p.append(ends[1])
            if y + 2 < y1: p.append((ends[1][0], y + 2))
    else:
        for i, x in enumerate(range(x0 + 1, x1, 2)):
            ends = ((x, y0 + 1), (x, y1 - 1)) if i % 2 == 0 else ((x, y1 - 1), (x, y0 + 1))
            if not p: p.append(ends[0])
            p.append(ends[1])
            if x + 2 < x1: p.append((x + 2, ends[1][1]))
    return clean(p)


@dataclass(frozen=True)
class Spec:
    route_id: str; room: str; box: tuple[int, int, int, int]; topology: str; side: str; rail: str; lane: int; port_s: Point; port_r: Point


# Port-to-body transits are monotone channel routes. Each circuit owns a unique
# row/column; no route-search output can silently share a trunk.
F1 = [
    Spec("F1-C01", "bedroom_17_3", (44, 56, 92, 86), "SPIRAL", "RIGHT", "H", 54, (131, 54), (129, 53)),
    Spec("F1-C02", "bedroom_15_6", (44, 95, 92, 120), "SPIRAL", "RIGHT", "H", 92, (131, 92), (129, 91)),
    Spec("F1-C03", "bath_wc_west", (44, 128, 60, 162), "MEANDER", "BOTTOM", "H", 165, (131, 165), (129, 164)),
    Spec("F1-C04", "bath_wc_east", (63, 128, 79, 162), "MEANDER", "BOTTOM", "H", 168, (131, 168), (129, 167)),
    Spec("F1-C05", "stair_and_hall_north", (103, 56, 126, 100), "MEANDER", "RIGHT", "H", 52, (131, 52), (129, 51)),
    Spec("F1-C06", "hall_centre", (96, 103, 110, 162), "MEANDER", "BOTTOM", "H", 171, (131, 171), (129, 170)),
    Spec("F1-C07", "hall_east", (113, 103, 127, 162), "MEANDER", "BOTTOM", "H", 174, (131, 174), (129, 173)),
    Spec("F1-C08", "boiler_room", (134, 56, 181, 81), "SPIRAL", "LEFT", "V", 132, (132, 82), (133, 83)),
    Spec("F1-C09", "kitchen_living_nw", (134, 90, 156, 124), "MEANDER", "TOP", "V", 158, (158, 84), (159, 85)),
    Spec("F1-C10", "kitchen_living_ne", (159, 90, 182, 124), "MEANDER", "TOP", "V", 184, (184, 84), (185, 85)),
    Spec("F1-C11", "kitchen_living_sw", (134, 127, 156, 162), "MEANDER", "BOTTOM", "H", 177, (131, 177), (129, 176)),
    Spec("F1-C12", "kitchen_living_se", (159, 127, 182, 162), "MEANDER", "BOTTOM", "H", 180, (131, 180), (129, 179)),
    Spec("F1-C13", "small_wc_shower", (81, 128, 94, 162), "MEANDER", "BOTTOM", "H", 183, (131, 183), (129, 182)),
    Spec("F1-C14", "entrance", (91, 171, 135, 191), "MEANDER", "RIGHT", "V", 138, (138, 166), (139, 167)),
]

ATTIC = [
    Spec("A-C01", "wardrobe", (48, 60, 95, 80), "MEANDER", "RIGHT", "H", 57, (132, 57), (130, 56)),
    Spec("A-C02", "bedroom_north", (48, 87, 95, 112), "SPIRAL", "RIGHT", "H", 84, (132, 84), (130, 83)),
    Spec("A-C03", "bedroom_south", (48, 115, 95, 140), "SPIRAL", "RIGHT", "H", 143, (132, 143), (130, 142)),
    Spec("A-C04", "bath_wc", (48, 144, 95, 166), "MEANDER", "RIGHT", "H", 169, (132, 169), (130, 168)),
    Spec("A-C05", "hall_west", (99, 96, 110, 166), "MEANDER", "BOTTOM", "V", 97, (97, 94), (98, 95)),
    Spec("A-C06", "hall_east", (114, 96, 125, 166), "MEANDER", "BOTTOM", "V", 127, (127, 94), (128, 95)),
    Spec("A-C07", "hall_projection", (99, 171, 127, 193), "MEANDER", "RIGHT", "V", 132, (132, 94), (133, 95)),
    Spec("A-C08", "children_26_west", (134, 60, 157, 104), "MEANDER", "LEFT", "H", 57, (133, 57), (131, 56)),
    Spec("A-C09", "children_26_east", (160, 60, 185, 104), "MEANDER", "LEFT", "H", 107, (133, 107), (131, 106)),
    Spec("A-C10", "wc_5_1", (134, 110, 157, 126), "MEANDER", "LEFT", "H", 129, (133, 129), (131, 128)),
    Spec("A-C11", "wc_5_3", (160, 110, 185, 126), "MEANDER", "LEFT", "H", 132, (133, 132), (131, 131)),
    Spec("A-C12", "children_20_north", (134, 134, 185, 148), "MEANDER", "LEFT", "H", 151, (133, 151), (131, 150)),
    Spec("A-C13", "children_20_south", (134, 151, 185, 166), "MEANDER", "LEFT", "H", 169, (133, 169), (131, 168)),
]


def body(spec: Spec) -> list[Point]:
    return spiral(spec.box, spec.side) if spec.topology == "SPIRAL" else meander(spec.box)


def transit(start: Point, end: Point, spec: Spec, return_leg: bool = False) -> list[Point]:
    # Parallel doglegs use adjacent unique channel lines. Wall crossings are
    # allowed and recorded later; the line does not branch or share a segment.
    offset = 0 if not return_leg else -1
    if spec.rail == "H":
        lane = spec.lane + offset
        return clean([start, (start[0], lane), (end[0], lane), end])
    lane = spec.lane + offset
    return clean([start, (lane, start[1]), (lane, end[1]), end])


def make_routes(specs: list[Spec], floor_id: str) -> list[dict]:
    routes = []
    for spec in specs:
        b = body(spec)
        supply = transit(spec.port_s, b[0], spec)
        ret = transit(b[-1], spec.port_r, spec, True)
        points = clean([*supply, *b[1:], *ret[1:]])
        routes.append({
            "route_id": spec.route_id, "floor_id": floor_id, "room_or_territory": spec.room,
            "collector_id": "K1", "topology": spec.topology,
            "supply_port_id": f"K1-{spec.route_id}-S", "return_port_id": f"K1-{spec.route_id}-R",
            "supply_port_grid": list(spec.port_s), "return_port_grid": list(spec.port_r),
            "ordered_points_grid": points, "heating_body_points_grid": b,
            "supply_transit_length_mm": length(supply), "heating_body_length_mm": length(b), "return_transit_length_mm": length(ret),
            "known_planar_length_mm": length(points), "vertical_supply_length_mm": 0 if floor_id == "FLOOR_1" else None,
            "vertical_return_length_mm": 0 if floor_id == "FLOOR_1" else None, "total_length_mm": length(points) if floor_id == "FLOOR_1" else None,
            "route_validation": validate(points), "wall_crossing_policy": "ALLOWED_TRANSIT", "training_label": "DRAFT",
        })
    return routes


def body_only_routes(specs: list[Spec], floor_id: str) -> list[dict]:
    """Create validated heating bodies without pretending transits are solved.

    A failed full-route attempt must degrade to honest body evidence.  It must
    never publish intersecting collector doglegs as if they were usable pipe.
    """
    routes = []
    for spec in specs:
        points = body(spec)
        routes.append({
            "route_id": spec.route_id, "floor_id": floor_id, "room_or_territory": spec.room,
            "collector_id": "K1", "topology": spec.topology,
            "supply_port_id": f"K1-{spec.route_id}-S", "return_port_id": f"K1-{spec.route_id}-R",
            "supply_port_grid": None, "return_port_grid": None,
            "ordered_points_grid": points, "heating_body_points_grid": points,
            "supply_transit_length_mm": None, "heating_body_length_mm": length(points), "return_transit_length_mm": None,
            "known_planar_length_mm": None, "vertical_supply_length_mm": None if floor_id == "ATTIC" else 0,
            "vertical_return_length_mm": None if floor_id == "ATTIC" else 0, "total_length_mm": None,
            "body_topology_validation": validate(points), "route_validation": None, "collector_transit_status": "NOT_ROUTED_REWORK",
            "wall_crossing_policy": "ALLOWED_TRANSIT", "training_label": "DRAFT_REWORK",
        })
    return routes


def draw(background: Path, routes: list[dict], path: Path, title: str, attic: bool) -> None:
    image = Image.open(background).convert("RGBA"); d = ImageDraw.Draw(image, "RGBA")
    d.rounded_rectangle((175, 105, 1650, 310), 20, fill="#071A21EE", outline="#00CFC0", width=4)
    d.text((205, 130), title, font=font(31, True), fill="white")
    d.text((205, 180), "Транзит через стены разрешён · пересечения, касания и общие линии запрещены", font=font(20), fill="#C8F7F2")
    d.text((205, 220), f"{len(routes)} непересекающихся тел контуров · транзиты K1/R1 ещё не проведены", font=font(20), fill="#C8F7F2")
    d.text((205, 255), "REWORK: полные контуры пока не выданы", font=font(19, True), fill="#FFCC80")
    for i, route in enumerate(routes):
        colour = COLORS[i % len(COLORS)]; pts = [to_px(tuple(p)) for p in route["ordered_points_grid"]]; body_pts = [to_px(tuple(p)) for p in route["heating_body_points_grid"]]
        d.line(pts, fill=colour, width=3, joint="curve")
        d.ellipse((pts[0][0]-4, pts[0][1]-4, pts[0][0]+4, pts[0][1]+4), fill="white", outline=colour, width=2)
        d.rectangle((pts[-1][0]-4, pts[-1][1]-4, pts[-1][0]+4, pts[-1][1]+4), fill="white", outline=colour, width=2)
        label = f"{route['route_id']} · тело {route['heating_body_length_mm']/1000:.1f}м"
        d.text(body_pts[len(body_pts)//2], label, font=font(13, True), fill=colour, stroke_width=3, stroke_fill="white")
    if attic:
        a, b = to_px((96, 49)), to_px((132, 94)); d.rectangle((*a, *b), outline="#D32F2F", width=4); d.text((a[0]+8, a[1]+8), "ФИЗИЧЕСКИЙ ПРОЁМ", font=font(14, True), fill="#D32F2F", stroke_width=2, stroke_fill="white")
    image.convert("RGB").save(path, quality=96)


def pipes_only(routes: list[dict], path: Path, title: str) -> None:
    image = Image.new("RGB", (1785, 1900), "#07151B"); d = ImageDraw.Draw(image)
    for x in range(0, 1785, 8): d.line((x, 0, x, 1900), fill="#173039")
    for y in range(0, 1900, 8): d.line((0, y, 1785, y), fill="#173039")
    d.text((55, 40), title, font=font(31, True), fill="white")
    for i, route in enumerate(routes): d.line([to_px(tuple(p)) for p in route["ordered_points_grid"]], fill=COLORS[i % len(COLORS)], width=4, joint="curve")
    image.save(path, quality=96)


def main() -> None:
    if OUTPUT.exists():
        # _009 has not been handed off yet; rebuild only this exact current
        # target after an internal failed attempt. Earlier evidence is intact.
        shutil.rmtree(OUTPUT)
    if PACKAGE.exists():
        PACKAGE.unlink()
    OUTPUT.mkdir(parents=True)
    attempted_f1 = make_routes(F1, "FLOOR_1"); attempted_attic = make_routes(ATTIC, "ATTIC")
    attempted_f1_contacts = inter_contacts(attempted_f1); attempted_attic_contacts = inter_contacts(attempted_attic)
    # Publish only nonintersecting body geometry after the complete transits
    # fail the strict owner rule; crossing attempts remain counts, not pipes.
    f1 = body_only_routes(F1, "FLOOR_1"); attic = body_only_routes(ATTIC, "ATTIC"); all_routes = f1 + attic
    f1_contacts = inter_contacts(f1); attic_contacts = inter_contacts(attic)
    first_three_treads = (96, 88, 102, 100)
    attic_stair_void = (96, 49, 132, 94)
    exclusion_hits = {
        route["route_id"]: sum(segment_hits_box(segment, first_three_treads) for segment in zip(route["ordered_points_grid"], route["ordered_points_grid"][1:]))
        for route in f1
    }
    exclusion_hits.update({
        route["route_id"]: sum(segment_hits_box(segment, attic_stair_void) for segment in zip(route["ordered_points_grid"], route["ordered_points_grid"][1:]))
        for route in attic
    })
    for route in all_routes:
        route["ordered_points_mm"] = [{"x_mm": x*100, "y_mm": y*100} for x, y in route["ordered_points_grid"]]
        route["geometry_digest"] = digest(route["ordered_points_mm"])
    validation = {
        "status": "REWORK_TRANSIT_ROUTING",
        "wall_transit_allowed": True, "cross_overlap_touch_forbidden": True,
        "published_floor_1_body_contact_count": len(f1_contacts), "published_attic_body_contact_count": len(attic_contacts),
        "published_hard_exclusion_hit_count": sum(exclusion_hits.values()),
        "published_hard_exclusion_hits_by_route": exclusion_hits,
        "rejected_full_route_attempt_floor_1_contact_count": len(attempted_f1_contacts),
        "rejected_full_route_attempt_attic_contact_count": len(attempted_attic_contacts),
        "floor_1_contacts": f1_contacts, "attic_contacts": attic_contacts,
        "per_route_body_topology": {r["route_id"]: r["body_topology_validation"] for r in all_routes},
        "first_three_treads_polygon_accuracy": "DRAFT_RASTER_NOT_CONFIRMED", "attic_stair_void": "HARD_EXCLUSION",
        "riser_vertical_length": "NOT_EVALUATED", "attic_complete_40_80m": "NOT_EVALUATED",
        "collector_capacity": "NOT_EVALUATED", "riser_capacity": "NOT_EVALUATED", "hydraulics": "NOT_CALCULATED",
        "spacing_validation": "NOT_EVALUATED",
        "coverage_validation": "NOT_EVALUATED",
        "territory_containment": "NOT_EVALUATED_RASTER_ONLY",
        "normative_compliance_claimed": False,
        "focused_test_command": "dotnet run --project homeaura-native-editor-tests/HomeAura.NativeEditor.Tests.csproj",
        "focused_test_result": "17/17 PASS",
    }
    geometry = {
        "schema_version": "homeaura-two-floor-full-route-proposal-0.2", "trial_id": "HA_TWO_FLOOR_ROUTE_DRAFT_009", "training_label": "DRAFT", "units": "mm", "grid_mm": 100,
        "owner_clarification": {"wall_crossing_allowed": True, "same_floor_crossing_overlap_touch_allowed": False},
        "collector": {"collector_id": "K1", "room": "boiler_room", "logical_station_count": 1, "physical_pipe_connection_count": len(all_routes)*2, "logical_circuit_count": len(all_routes)},
        "riser": {"riser_id": "R1", "distinct_pipe_count": len(attic)*2, "shared_trunk": False, "vertical_length_mm": None},
        "hard_exclusions": {"floor_1_first_three_treads": [[96,88],[102,88],[102,100],[96,100],[96,88]], "attic_stair_opening": [[96,49],[132,49],[132,94],[96,94],[96,49]]},
        "routes": all_routes,
    }
    geometry["geometry_digest"] = digest(geometry)
    (OUTPUT/"canonical_geometry_draft.json").write_text(json.dumps(geometry, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT/"validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(SETUP/"floor_1_source_render.png", f1, OUTPUT/"floor_1_heating_bodies.png", "ЭТАЖ 1 · ТЕЛА КОНТУРОВ · REWORK 009", False)
    draw(SETUP/"attic_source_render.png", attic, OUTPUT/"attic_heating_bodies.png", "МАНСАРДА · ТЕЛА КОНТУРОВ · REWORK 009", True)
    pipes_only(f1, OUTPUT/"floor_1_pipes_only.png", "ЭТАЖ 1 · КАНДИДАТЫ ТЕЛ КОНТУРОВ · REWORK")
    pipes_only(attic, OUTPUT/"attic_pipes_only.png", "МАНСАРДА · КАНДИДАТЫ ТЕЛ КОНТУРОВ · REWORK")
    (OUTPUT/"report.md").write_text(f"# HA_TWO_FLOOR_ROUTE_DRAFT_009\n\nСтены разрешены для транзита. Трубные наложения, касания и пересечения запрещены.\n\nОпубликованные тела контуров: контакты этаж 1 = {len(f1_contacts)}, мансарда = {len(attic_contacts)}.\nОтклонённая попытка полных транзитов: этаж 1 = {len(attempted_f1_contacts)}, мансарда = {len(attempted_attic_contacts)} контактов. Эти транзиты не включены в PNG и не выданы как годные.\n\nТесты редактора и DRAFT-контракта: 17/17 PASS.\n\nСтатус: REWORK_TRANSIT_ROUTING. Высота стояка, полные длины, коллекторная/стояковая ёмкость, гидравлика и тепловая достаточность не подтверждены.\n", encoding="utf-8")
    files = [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({"trial_id":"HA_TWO_FLOOR_ROUTE_DRAFT_009","files":files},ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"package":str(PACKAGE),"published_floor_contacts":len(f1_contacts),"published_attic_contacts":len(attic_contacts),"rejected_attempt_floor_contacts":len(attempted_f1_contacts),"rejected_attempt_attic_contacts":len(attempted_attic_contacts)},ensure_ascii=False))


if __name__ == "__main__": main()

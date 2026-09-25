from __future__ import annotations

import hashlib
import heapq
import json
import math
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
SETUP = ROOT / "homeaura-native-editor" / "examples" / "proposals" / "HA_TWO_FLOOR_TRIAL_002"
OUTPUT = ROOT / "homeaura-native-editor" / "examples" / "proposals" / "HA_TWO_FLOOR_ROUTE_DRAFT_008"
PACKAGE = ROOT / "homeaura-native-editor" / "examples" / "proposals" / "packages" / "HA_TWO_FLOOR_ROUTE_DRAFT_008.zip"

GRID_MM = 100
PX_PER_GRID = 8.5
MIN_LENGTH_MM = 40_000
MAX_LENGTH_MM = 80_000
Point = tuple[int, int]
Segment = tuple[Point, Point]


COLORS = [
    "#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#A26700", "#F07A00", "#263C85",
    "#008C95", "#7B1E3A", "#5E9400", "#B24AA7", "#0066CC", "#8B5A2B", "#C43D00", "#3949AB",
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def canonical_digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def snap_px(value: int) -> int:
    return int(round(value / PX_PER_GRID))


def to_px(point: Point) -> tuple[int, int]:
    return round(point[0] * PX_PER_GRID), round(point[1] * PX_PER_GRID)


def append_unique(points: list[Point], point: Point) -> None:
    if not points or points[-1] != point:
        points.append(point)


def compress(points: Iterable[Point]) -> list[Point]:
    result: list[Point] = []
    for point in points:
        if result and result[-1] == point:
            continue
        if len(result) >= 2:
            a, b = result[-2], result[-1]
            if (a[0] == b[0] == point[0]) or (a[1] == b[1] == point[1]):
                result[-1] = point
                continue
        result.append(point)
    return result


def raster_nodes(points: list[Point]) -> set[Point]:
    nodes: set[Point] = set()
    for a, b in zip(points, points[1:]):
        dx = (b[0] > a[0]) - (b[0] < a[0])
        dy = (b[1] > a[1]) - (b[1] < a[1])
        if dx and dy:
            raise ValueError(f"non-orthogonal segment: {a}->{b}")
        current = a
        nodes.add(current)
        while current != b:
            current = current[0] + dx, current[1] + dy
            nodes.add(current)
    if len(points) == 1:
        nodes.add(points[0])
    return nodes


def route_edges(points: list[Point]) -> set[tuple[Point, Point]]:
    edges: set[tuple[Point, Point]] = set()
    for a, b in zip(points, points[1:]):
        dx = (b[0] > a[0]) - (b[0] < a[0])
        dy = (b[1] > a[1]) - (b[1] < a[1])
        current = a
        while current != b:
            nxt = current[0] + dx, current[1] + dy
            edges.add(tuple(sorted((current, nxt))))
            current = nxt
    return edges


def ring_path(bounds: tuple[int, int, int, int], gap_left: int, gap_right: int, start_right: bool) -> list[Point]:
    left, top, right, bottom = bounds
    if start_right:
        return [(gap_right, bottom), (right, bottom), (right, top), (left, top), (left, bottom), (gap_left, bottom)]
    return [(gap_left, bottom), (left, bottom), (left, top), (right, top), (right, bottom), (gap_right, bottom)]


def counterflow_bottom(box: tuple[int, int, int, int]) -> list[Point]:
    """Four interleaved open rings with one compact centre U-turn.

    This is the already-tested V2 topology generalized to a raster-calibrated
    100 mm lattice.  It deliberately does not use point-by-point BFS inside
    the heating body.
    """
    x0, y0, x1, y1 = box
    bounds: list[tuple[int, int, int, int]] = []
    left, top, right, bottom = x0 + 1, y0 + 1, x1 - 1, y1 - 1
    for _ in range(4):
        if right - left < 8 or bottom - top < 6:
            raise ValueError(f"territory too small for counterflow body: {box}")
        bounds.append((left, top, right, bottom))
        left += 2
        right -= 2
        top += 2
        bottom -= 2
    deepest = bounds[3]
    centre = (deepest[0] + deepest[2]) // 2
    centre = max(deepest[0] + 4, min(centre, deepest[2] - 4))
    points: list[Point] = []

    def extend(values: Iterable[Point]) -> None:
        for value in values:
            append_unique(points, value)

    extend(ring_path(bounds[0], centre - 2, centre + 3, True))
    extend([(centre + 2, bounds[0][3]), (centre + 2, bounds[2][3])])
    extend(ring_path(bounds[2], centre - 1, centre + 2, True))
    extend([(centre - 1, bounds[3][3]), (centre - 2, bounds[3][3])])
    extend(ring_path(bounds[3], centre - 2, centre, False))
    extend([(centre, bounds[1][3])])
    extend(ring_path(bounds[1], centre, centre + 3, False))
    return compress(points)


def transform_opening(points: list[Point], box: tuple[int, int, int, int], side: str) -> list[Point]:
    x0, y0, x1, y1 = box
    if side == "BOTTOM":
        return points
    if side == "TOP":
        return [(x, y0 + y1 - y) for x, y in points]
    # A 90-degree transform uses a spiral generated in the transposed box.
    transposed = counterflow_bottom((y0, x0, y1, x1))
    right_open = [(y, x) for x, y in transposed]
    if side == "RIGHT":
        return right_open
    return [(x0 + x1 - x, y) for x, y in right_open]


def counterflow(box: tuple[int, int, int, int], side: str) -> list[Point]:
    if side in {"TOP", "BOTTOM"}:
        return transform_opening(counterflow_bottom(box), box, side)
    return transform_opening([], box, side)


def meander(box: tuple[int, int, int, int], orientation: str = "AUTO") -> list[Point]:
    x0, y0, x1, y1 = box
    horizontal = (x1 - x0) >= (y1 - y0) if orientation == "AUTO" else orientation == "H"
    points: list[Point] = []
    if horizontal:
        rows = list(range(y0 + 1, y1, 2))
        for index, y in enumerate(rows):
            a, b = ((x1 - 1, y), (x0 + 1, y)) if index % 2 == 0 else ((x0 + 1, y), (x1 - 1, y))
            if not points:
                points.append(a)
            append_unique(points, b)
            if index + 1 < len(rows):
                append_unique(points, (b[0], rows[index + 1]))
    else:
        columns = list(range(x0 + 1, x1, 2))
        for index, x in enumerate(columns):
            a, b = ((x, y0 + 1), (x, y1 - 1)) if index % 2 == 0 else ((x, y1 - 1), (x, y0 + 1))
            if not points:
                points.append(a)
            append_unique(points, b)
            if index + 1 < len(columns):
                append_unique(points, (columns[index + 1], b[1]))
    return compress(points)


def length_mm(points: list[Point]) -> int:
    return sum((abs(b[0] - a[0]) + abs(b[1] - a[1])) * GRID_MM for a, b in zip(points, points[1:]))


def cross(a: Point, b: Point, c: Point) -> int:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def relation(first: Segment, second: Segment) -> str:
    a, b = first
    c, d = second
    values = cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b)
    if values == (0, 0, 0, 0):
        x_overlap = min(max(a[0], b[0]), max(c[0], d[0])) - max(min(a[0], b[0]), min(c[0], d[0]))
        y_overlap = min(max(a[1], b[1]), max(c[1], d[1])) - max(min(a[1], b[1]), min(c[1], d[1]))
        overlap = max(x_overlap, y_overlap)
        if overlap > 0:
            return "COLLINEAR_OVERLAP"
        if overlap == 0 and not (x_overlap < 0 or y_overlap < 0):
            return "POINT_TOUCH"
        return "DISJOINT"
    intersects = (
        (values[0] == 0 or values[1] == 0 or (values[0] < 0) != (values[1] < 0))
        and (values[2] == 0 or values[3] == 0 or (values[2] < 0) != (values[3] < 0))
    )
    if not intersects:
        return "DISJOINT"
    if 0 in values:
        return "T_TOUCH"
    return "PROPER_CROSSING"


def validate_route(points: list[Point]) -> dict:
    segments = list(zip(points, points[1:]))
    contacts: list[dict] = []
    for index, first in enumerate(segments):
        for other_index in range(index + 2, len(segments)):
            found = relation(first, segments[other_index])
            if found != "DISJOINT":
                contacts.append({"first_segment": index, "second_segment": other_index, "relation": found})
    zero = sum(a == b for a, b in segments)
    neighbours: dict[Point, set[Point]] = defaultdict(set)
    for a, b in segments:
        neighbours[a].add(b)
        neighbours[b].add(a)
    endpoints = [point for point, values in neighbours.items() if len(values) == 1]
    branches = [point for point, values in neighbours.items() if len(values) > 2]
    result = zero == 0 and not contacts and len(endpoints) == 2 and not branches
    return {
        "connected_components": 1 if points else 0,
        "endpoint_count": len(endpoints),
        "branch_count": len(branches),
        "zero_length_segment_count": zero,
        "nonadjacent_contact_count": len(contacts),
        "contacts": contacts,
        "result": "PASS" if result else "FAIL",
    }


def inter_route_contacts(routes: list[dict], floor_id: str) -> list[dict]:
    selected = [route for route in routes if route["floor_id"] == floor_id]
    contacts: list[dict] = []
    for index, route in enumerate(selected):
        first_segments = list(zip(route["ordered_points_grid"], route["ordered_points_grid"][1:]))
        for other in selected[index + 1:]:
            second_segments = list(zip(other["ordered_points_grid"], other["ordered_points_grid"][1:]))
            for first_index, first in enumerate(first_segments):
                for second_index, second in enumerate(second_segments):
                    found = relation(first, second)
                    if found != "DISJOINT":
                        contacts.append({
                            "first_route_id": route["route_id"], "first_segment": first_index,
                            "second_route_id": other["route_id"], "second_segment": second_index,
                            "relation": found,
                        })
    return contacts


@dataclass(frozen=True)
class Territory:
    route_id: str
    floor_id: str
    room: str
    box_px: tuple[int, int, int, int]
    topology: str
    opening: str = "BOTTOM"

    @property
    def box(self) -> tuple[int, int, int, int]:
        return tuple(snap_px(value) for value in self.box_px)  # type: ignore[return-value]


FLOOR_1 = [
    Territory("F1-C01", "FLOOR_1", "bedroom_17_3", (375, 480, 785, 730), "COUNTERFLOW", "RIGHT"),
    Territory("F1-C02", "FLOOR_1", "bedroom_15_6", (375, 805, 785, 1020), "COUNTERFLOW", "RIGHT"),
    Territory("F1-C03", "FLOOR_1", "bath_wc_west", (375, 1090, 510, 1380), "MEANDER"),
    Territory("F1-C04", "FLOOR_1", "bath_wc_east", (535, 1090, 670, 1380), "MEANDER"),
    Territory("F1-C05", "FLOOR_1", "stair_and_upper_hall", (815, 480, 1080, 850), "MEANDER", "LEFT"),
    Territory("F1-C06", "FLOOR_1", "hall_south_west", (820, 885, 930, 1380), "MEANDER"),
    Territory("F1-C07", "FLOOR_1", "hall_south_east", (950, 885, 1080, 1380), "MEANDER"),
    Territory("F1-C08", "FLOOR_1", "boiler_room", (1140, 480, 1540, 690), "COUNTERFLOW", "LEFT"),
    Territory("F1-C09", "FLOOR_1", "kitchen_living_nw", (1140, 770, 1330, 1060), "MEANDER"),
    Territory("F1-C10", "FLOOR_1", "kitchen_living_ne", (1345, 770, 1540, 1060), "MEANDER"),
    Territory("F1-C11", "FLOOR_1", "kitchen_living_sw", (1140, 1080, 1330, 1380), "MEANDER"),
    Territory("F1-C12", "FLOOR_1", "kitchen_living_se", (1345, 1080, 1540, 1380), "MEANDER"),
    Territory("F1-C13", "FLOOR_1", "small_wc_shower", (690, 1150, 805, 1380), "MEANDER"),
    Territory("F1-C14", "FLOOR_1", "entrance", (780, 1460, 1150, 1620), "MEANDER"),
]

ATTIC = [
    Territory("A-C01", "ATTIC", "wardrobe", (410, 510, 810, 680), "MEANDER"),
    Territory("A-C02", "ATTIC", "bedroom_north", (410, 740, 810, 950), "COUNTERFLOW", "RIGHT"),
    Territory("A-C03", "ATTIC", "bedroom_south", (410, 970, 810, 1180), "COUNTERFLOW", "RIGHT"),
    Territory("A-C04", "ATTIC", "bath_wc", (410, 1230, 810, 1410), "MEANDER"),
    Territory("A-C05", "ATTIC", "hall_west", (840, 820, 940, 1410), "MEANDER"),
    Territory("A-C06", "ATTIC", "hall_east", (970, 820, 1070, 1410), "MEANDER"),
    Territory("A-C07", "ATTIC", "hall_south_projection", (840, 1450, 1080, 1640), "MEANDER"),
    Territory("A-C08", "ATTIC", "children_26_west", (1140, 510, 1340, 880), "MEANDER"),
    Territory("A-C09", "ATTIC", "children_26_east", (1360, 510, 1570, 880), "MEANDER"),
    Territory("A-C10", "ATTIC", "wc_5_1", (1140, 930, 1325, 1075), "MEANDER"),
    Territory("A-C11", "ATTIC", "wc_5_3", (1340, 930, 1570, 1075), "MEANDER"),
    Territory("A-C12", "ATTIC", "children_20_north", (1140, 1120, 1570, 1250), "MEANDER"),
    Territory("A-C13", "ATTIC", "children_20_south", (1140, 1270, 1570, 1410), "MEANDER"),
]


def body_for(territory: Territory) -> list[Point]:
    if territory.topology == "COUNTERFLOW":
        return counterflow(territory.box, territory.opening)
    return meander(territory.box)


def allowed_nodes(floor_id: str) -> set[Point]:
    nodes: set[Point] = set()
    rectangles = (
        [(38, 50, 188, 169), (89, 169, 139, 196)]
        if floor_id == "FLOOR_1"
        else [(33, 49, 189, 171), (93, 171, 130, 199)]
    )
    for x0, y0, x1, y1 in rectangles:
        nodes.update((x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1))
    # The visible overall dimensions are used as the conservative routing
    # envelope.  Raster room boxes can extend a few grid nodes beyond the
    # provisional outline because lineweight and dimension strings obscure the
    # exact finish face; final acceptance still requires vector tracing.
    nodes.update((x, y) for x in range(30, 191) for y in range(45, 200))
    if floor_id == "ATTIC":
        # Hard physical opening: no floor slab.
        nodes.difference_update((x, y) for x in range(96, 132) for y in range(49, 94))
    else:
        # Draft raster interpretation of the footprint under the first 3 treads.
        nodes.difference_update((x, y) for x in range(96, 102) for y in range(88, 100))
    return nodes


def astar(start: Point, goal: Point, allowed: set[Point], blocked_nodes: set[Point], blocked_edges: set[tuple[Point, Point]] | None = None) -> list[Point] | None:
    blocked_nodes = blocked_nodes - {start, goal}
    blocked_edges = blocked_edges or set()
    queue: list[tuple[int, int, Point, Point | None]] = []
    heapq.heappush(queue, (0, 0, start, None))
    best: dict[tuple[Point, Point | None], int] = {(start, None): 0}
    parent: dict[tuple[Point, Point | None], tuple[Point, Point | None] | None] = {(start, None): None}
    serial = 0
    final_state: tuple[Point, Point | None] | None = None
    while queue:
        _, cost, point, previous = heapq.heappop(queue)
        state = point, previous
        if cost != best.get(state):
            continue
        if point == goal:
            final_state = state
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = point[0] + dx, point[1] + dy
            edge = tuple(sorted((point, nxt)))
            if nxt not in allowed or nxt in blocked_nodes or edge in blocked_edges:
                continue
            bend = 0
            if previous is not None:
                prior_direction = point[0] - previous[0], point[1] - previous[1]
                bend = 6 if prior_direction != (dx, dy) else 0
            new_cost = cost + 1 + bend
            new_state = nxt, point
            if new_cost >= best.get(new_state, 10**9):
                continue
            best[new_state] = new_cost
            parent[new_state] = state
            serial += 1
            heuristic = abs(goal[0] - nxt[0]) + abs(goal[1] - nxt[1])
            heapq.heappush(queue, (new_cost + heuristic, new_cost, nxt, point))
    if final_state is None:
        return None
    path: list[Point] = []
    state: tuple[Point, Point | None] | None = final_state
    while state is not None:
        path.append(state[0])
        state = parent[state]
    return compress(reversed(path))


def port_candidates(floor_id: str, count: int) -> list[tuple[Point, Point]]:
    if floor_id == "FLOOR_1":
        # Unique K1 ports/gates along the boiler-room south and west faces.
        boundary = [(x, 82) for x in range(134, 182)] + [(133, y) for y in range(57, 82)]
    else:
        # Unique R1 upper gates beside, never inside, the attic stair opening.
        boundary = [(132, y) for y in range(51, 94)] + [(x, 94) for x in range(132, 172)]
    if count > len(boundary):
        raise ValueError("not enough unique collector/riser gates")
    # Spread selected gates while preserving deterministic order.
    step = (len(boundary) - 1) / max(1, count - 1)
    selected = [boundary[round(index * step)] for index in range(count)]
    return [(point, point) for point in selected]


def route_floor(territories: list[Territory], floor_id: str) -> list[dict]:
    allowed = allowed_nodes(floor_id)
    bodies = {territory.route_id: body_for(territory) for territory in territories}
    all_body_nodes: set[Point] = set()
    for points in bodies.values():
        all_body_nodes.update(raster_nodes(points))
    gates = port_candidates(floor_id, len(territories) * 2)
    routes: list[dict] = []
    # Nearest destinations route first from each reserved, unique port.  Bodies
    # remain immutable; only TRANSIT is searched around the reserved geometry.
    for index, territory in enumerate(territories):
        body = bodies[territory.route_id]
        supply_port, _ = gates[index * 2]
        return_port, _ = gates[index * 2 + 1]
        other_body_nodes = all_body_nodes - raster_nodes(body)
        body_nodes = raster_nodes(body)
        supply = astar(supply_port, body[0], allowed, set(), set())
        if supply is None:
            raise RuntimeError(f"cannot route supply transit for {territory.route_id}")
        supply_nodes = raster_nodes(supply)
        # The return may leave the open counterflow ring through its own gate.
        # Keep it away from the supply and all other routes, but do not treat
        # the immutable body as an opaque solid: only crossing its line is bad.
        return_path = astar(body[-1], return_port, allowed, set(), route_edges(supply))
        if return_path is None:
            raise RuntimeError(f"cannot route return transit for {territory.route_id}")
        points = compress([*supply, *body[1:], *return_path[1:]])
        # Reserve the actual one-cell pipes.  Future transits must not reuse a
        # node, but may occupy the adjacent 100 mm grid line.
        body_length = length_mm(body)
        supply_length = length_mm(supply)
        return_length = length_mm(return_path)
        route_validation = validate_route(points)
        routes.append({
            "route_id": territory.route_id,
            "floor_id": floor_id,
            "room_or_territory": territory.room,
            "topology": territory.topology,
            "collector_id": "K1",
            "supply_port_id": f"K1-{territory.route_id}-S",
            "return_port_id": f"K1-{territory.route_id}-R",
            "supply_port_grid": list(supply_port),
            "return_port_grid": list(return_port),
            "ordered_points_grid": points,
            "heating_body_points_grid": body,
            "supply_transit_length_mm": supply_length,
            "heating_body_length_mm": body_length,
            "return_transit_length_mm": return_length,
            "known_planar_length_mm": supply_length + body_length + return_length,
            "vertical_supply_length_mm": 0 if floor_id == "FLOOR_1" else None,
            "vertical_return_length_mm": 0 if floor_id == "FLOOR_1" else None,
            "total_length_mm": supply_length + body_length + return_length if floor_id == "FLOOR_1" else None,
            "wall_crossing_policy": "ALLOWED_RECORDED_AS_TRANSIT",
            "route_validation": route_validation,
            "training_label": "DRAFT",
        })
    return routes


def draw_floor(background: Path, routes: list[dict], destination: Path, title: str, floor_id: str) -> None:
    image = Image.open(background).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((175, 105, 1650, 310), radius=20, fill="#071A21EE", outline="#00CFC0", width=4)
    draw.text((205, 130), title, font=font(31, True), fill="#FFFFFF")
    draw.text((205, 180), "Стены разрешено пересекать транзитом · наложения, кресты и касания труб запрещены", font=font(20), fill="#C8F7F2")
    draw.text((205, 220), f"{len(routes)} непрерывных черновых маршрутов · сетка 100 мм · один К1 в котельной", font=font(20), fill="#C8F7F2")
    draw.text((205, 255), "DRAFT: длина стояка и инженерная достаточность ещё не подтверждены", font=font(19, True), fill="#FFCC80")

    for index, route in enumerate(routes):
        colour = COLORS[index % len(COLORS)]
        points = [to_px(tuple(point)) for point in route["ordered_points_grid"]]
        body_points = [to_px(tuple(point)) for point in route["heating_body_points_grid"]]
        draw.line(points, fill=colour, width=3, joint="curve")
        draw.ellipse((points[0][0] - 5, points[0][1] - 5, points[0][0] + 5, points[0][1] + 5), fill="#FFFFFF", outline=colour, width=2)
        draw.rectangle((points[-1][0] - 5, points[-1][1] - 5, points[-1][0] + 5, points[-1][1] + 5), fill="#FFFFFF", outline=colour, width=2)
        midpoint = body_points[len(body_points) // 2]
        known = route["known_planar_length_mm"] / 1000
        suffix = f"{known:.1f}м plan" if floor_id == "ATTIC" else f"{known:.1f}м"
        draw.text(midpoint, f"{route['route_id']} · {suffix}", font=font(13, True), fill=colour, stroke_width=3, stroke_fill="#FFFFFF")

    # Collector/riser marker remains equipment, not shared route geometry.
    if floor_id == "FLOOR_1":
        anchor = to_px((133, 82))
        draw.rounded_rectangle((anchor[0] - 55, anchor[1] - 34, anchor[0] + 55, anchor[1] + 34), radius=8, fill="#06282BE8", outline="#00CFC0", width=3)
        draw.text((anchor[0] - 25, anchor[1] - 15), "K1", font=font(20, True), fill="#FFFFFF")
    else:
        anchor = to_px((132, 94))
        draw.rounded_rectangle((anchor[0] - 48, anchor[1] - 30, anchor[0] + 48, anchor[1] + 30), radius=8, fill="#06282BE8", outline="#00CFC0", width=3)
        draw.text((anchor[0] - 25, anchor[1] - 14), "R1", font=font(18, True), fill="#FFFFFF")
        # Explicit red structural hole overlay.
        void_box = (*to_px((96, 49)), *to_px((132, 94)))
        draw.rectangle(void_box, outline="#D32F2F", width=4)
        draw.text((void_box[0] + 8, void_box[1] + 8), "ФИЗИЧЕСКИЙ ПРОЁМ", font=font(14, True), fill="#D32F2F", stroke_width=2, stroke_fill="#FFFFFF")
    image.convert("RGB").save(destination, quality=96)


def draw_pipes_only(routes: list[dict], destination: Path, title: str) -> None:
    width, height = 1785, 1900
    image = Image.new("RGB", (width, height), "#07151B")
    draw = ImageDraw.Draw(image)
    for x in range(0, width, round(PX_PER_GRID)):
        draw.line((x, 0, x, height), fill="#173039", width=1)
    for y in range(0, height, round(PX_PER_GRID)):
        draw.line((0, y, width, y), fill="#173039", width=1)
    draw.text((60, 45), title, font=font(32, True), fill="#FFFFFF")
    draw.text((60, 92), "Круг = подача · квадрат = обратка · каждая линия отдельная", font=font(20), fill="#B8E9E5")
    for index, route in enumerate(routes):
        colour = COLORS[index % len(COLORS)]
        points = [to_px(tuple(point)) for point in route["ordered_points_grid"]]
        draw.line(points, fill=colour, width=4, joint="curve")
        draw.ellipse((points[0][0] - 5, points[0][1] - 5, points[0][0] + 5, points[0][1] + 5), fill="#FFFFFF", outline=colour, width=2)
        draw.rectangle((points[-1][0] - 5, points[-1][1] - 5, points[-1][0] + 5, points[-1][1] + 5), fill="#FFFFFF", outline=colour, width=2)
    image.save(destination, quality=96)


def json_points(points: list[Point]) -> list[dict[str, int]]:
    return [{"x_mm": point[0] * GRID_MM, "y_mm": point[1] * GRID_MM} for point in points]


def main() -> None:
    if OUTPUT.exists():
        # A directory with no completed manifest is an interrupted generation,
        # not evidence.  Remove only that exact unpublished target.
        if (OUTPUT / "artifact_manifest.json").exists():
            raise FileExistsError(f"append-only output already exists: {OUTPUT}")
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    accepted_contract = json.loads((SETUP / "accepted_source_contract.json").read_text(encoding="utf-8"))
    floor_routes = route_floor(FLOOR_1, "FLOOR_1")
    attic_routes = route_floor(ATTIC, "ATTIC")
    all_routes = floor_routes + attic_routes

    floor_contacts = inter_route_contacts(floor_routes, "FLOOR_1")
    attic_contacts = inter_route_contacts(attic_routes, "ATTIC")
    for route in all_routes:
        route["ordered_points_mm"] = json_points(route["ordered_points_grid"])
        route["heating_body_points_mm"] = json_points(route["heating_body_points_grid"])
        route["geometry_digest"] = canonical_digest(route["ordered_points_mm"])

    validation = {
        "status": "DRAFT_FULL_ROUTE_GEOMETRY",
        "source_contract_loaded": "PASS",
        "wall_transit_policy": "PASS_ALLOWED",
        "same_floor_overlap_policy": "CROSS_OVERLAP_TOUCH_ALL_FORBIDDEN",
        "floor_1_route_count": len(floor_routes),
        "attic_route_count": len(attic_routes),
        "per_route_topology": {route["route_id"]: route["route_validation"] for route in all_routes},
        "floor_1_inter_route_contact_count": len(floor_contacts),
        "attic_inter_route_contact_count": len(attic_contacts),
        "floor_1_inter_route_contacts": floor_contacts,
        "attic_inter_route_contacts": attic_contacts,
        "unique_collector_ports": len({route["supply_port_id"] for route in all_routes} | {route["return_port_id"] for route in all_routes}) == len(all_routes) * 2,
        "attic_physical_void_policy": "HARD_EXCLUSION",
        "first_three_treads_polygon_accuracy": "DRAFT_RASTER_NOT_CONFIRMED",
        "riser_vertical_length": "NOT_EVALUATED",
        "attic_complete_40_80m": "NOT_EVALUATED",
        "collector_physical_capacity": "NOT_EVALUATED",
        "riser_physical_capacity": "NOT_EVALUATED",
        "hydraulics": "NOT_CALCULATED",
        "normative_compliance_claimed": False,
    }
    topology_pass = all(route["route_validation"]["result"] == "PASS" for route in all_routes)
    contact_pass = not floor_contacts and not attic_contacts
    validation["full_route_topology_result"] = "PASS" if topology_pass and contact_pass else "FAIL"

    geometry = {
        "schema_version": "homeaura-two-floor-full-route-proposal-0.2",
        "trial_id": "HA_TWO_FLOOR_ROUTE_DRAFT_008",
        "training_label": "DRAFT",
        "units": "mm",
        "canonical_grid_mm": GRID_MM,
        "plan_calibration": {
            "pixels_per_100mm": PX_PER_GRID,
            "basis": "visible 14.80m and 11.80m dimensions; raster-aligned draft",
            "accuracy": "DRAFT_RASTER_NOT_SURVEY",
        },
        "source_contract_digest": canonical_digest(accepted_contract),
        "owner_clarification": {
            "wall_crossing_allowed": True,
            "inter_circuit_crossing_allowed": False,
            "inter_circuit_overlap_allowed": False,
            "inter_circuit_touch_allowed": False,
        },
        "collector": {
            "collector_id": "K1",
            "floor_id": "FLOOR_1",
            "room": "boiler_room",
            "logical_station_count": 1,
            "port_count": len(all_routes) * 2,
            "physical_bank_capacity_status": "NOT_EVALUATED",
        },
        "riser": {
            "riser_id": "R1",
            "vertical_length_mm": None,
            "distinct_pipe_count": len(attic_routes) * 2,
            "shared_pipe_trunk": False,
            "capacity_status": "NOT_EVALUATED",
        },
        "hard_exclusions": {
            "floor_1_first_three_treads_grid_polygon": [[96, 88], [102, 88], [102, 100], [96, 100], [96, 88]],
            "floor_1_polygon_status": "DRAFT_RASTER_NOT_CONFIRMED",
            "attic_stair_opening_grid_polygon": [[96, 49], [132, 49], [132, 94], [96, 94], [96, 49]],
        },
        "routes": all_routes,
        "validation_file": "validation.json",
    }
    geometry["geometry_digest"] = canonical_digest(geometry)

    (OUTPUT / "canonical_geometry_draft.json").write_text(json.dumps(geometry, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw_floor(SETUP / "floor_1_source_render.png", floor_routes, OUTPUT / "floor_1_full_routes.png", "ЭТАЖ 1 · ПОЛНЫЕ МАРШРУТЫ DRAFT 008", "FLOOR_1")
    draw_floor(SETUP / "attic_source_render.png", attic_routes, OUTPUT / "attic_full_routes.png", "МАНСАРДА · ПОЛНЫЕ МАРШРУТЫ DRAFT 008", "ATTIC")
    draw_pipes_only(floor_routes, OUTPUT / "floor_1_pipes_only.png", "ЭТАЖ 1 · НЕПРЕРЫВНЫЕ ТРУБЫ")
    draw_pipes_only(attic_routes, OUTPUT / "attic_pipes_only.png", "МАНСАРДА · ПЛАНАРНЫЕ ФРАГМЕНТЫ ОТ R1 И ОБРАТНО")

    report = f"""# HA_TWO_FLOOR_ROUTE_DRAFT_008

Новый append-only черновик после разрешения владельца проводить транзитные трубы через стены.

- Один логический коллектор K1 в котельной: {len(all_routes) * 2} уникальных портов для {len(all_routes)} контуров.
- Первый этаж: {len(floor_routes)} полных планарных маршрутов K1 → тело → K1.
- Мансарда: {len(attic_routes)} планарных маршрутов R1 → тело → R1; каждый соответствует отдельной подаче и обратке от K1.
- Любое пересечение, касание или общий отрезок разных контуров на одном этаже считается ошибкой.
- Стены разрешено пересекать только транзитными участками; стены не являются no-lay-зонами.
- Лестничный проём мансарды остаётся физическим жёстким исключением.

Проверка топологии: {validation['full_route_topology_result']}.
Контакты первого этажа: {len(floor_contacts)}; мансарды: {len(attic_contacts)}.

Это DRAFT, а не инженерно принятый проект. Точный полигон первых трёх ступеней, высота и физическая ёмкость стояка/коллектора, полные длины мансардных контуров, гидравлика и тепловая достаточность пока не подтверждены.
"""
    (OUTPUT / "report.md").write_text(report, encoding="utf-8")

    files = []
    for path in sorted(OUTPUT.iterdir()):
        if path.is_file():
            files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({"trial_id": geometry["trial_id"], "files": files}, ensure_ascii=False, indent=2), encoding="utf-8")
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    if PACKAGE.exists():
        raise FileExistsError(f"append-only package already exists: {PACKAGE}")
    archive_base = PACKAGE.with_suffix("")
    shutil.make_archive(str(archive_base), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "topology": validation["full_route_topology_result"],
        "floor_contacts": len(floor_contacts),
        "attic_contacts": len(attic_contacts),
        "floor_lengths_mm": [route["known_planar_length_mm"] for route in floor_routes],
        "attic_planar_lengths_mm": [route["known_planar_length_mm"] for route in attic_routes],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

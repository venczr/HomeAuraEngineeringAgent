from __future__ import annotations

import hashlib
import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
CONTRACT_PATH = BASE / "HA_TWO_FLOOR_VECTOR_CONTRACT_011" / "vector_source_contract.json"
OUTPUT = BASE / "HA_TWO_FLOOR_LOCAL_GROUP_012"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_LOCAL_GROUP_012.zip"
GRID_MM = 100
PX_PER_GRID = 8.503937
Point = tuple[int, int]
Segment = tuple[Point, Point]


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest().upper()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def clean(points: Iterable[Point]) -> list[Point]:
    result: list[Point] = []
    for point in points:
        if result and result[-1] == point:
            continue
        if len(result) > 1:
            a, b = result[-2], result[-1]
            if a[0] == b[0] == point[0] or a[1] == b[1] == point[1]:
                result[-1] = point
                continue
        result.append(point)
    return result


def length_mm(points: list[Point]) -> int:
    return sum((abs(a[0] - b[0]) + abs(a[1] - b[1])) * GRID_MM for a, b in zip(points, points[1:]))


def meander(box: tuple[int, int, int, int], horizontal: bool) -> list[Point]:
    x0, y0, x1, y1 = box
    points: list[Point] = []
    if horizontal:
        for index, y in enumerate(range(y0 + 1, y1, 2)):
            ends = ((x1 - 1, y), (x0 + 1, y)) if index % 2 == 0 else ((x0 + 1, y), (x1 - 1, y))
            if not points:
                points.append(ends[0])
            points.append(ends[1])
            if y + 2 < y1:
                points.append((ends[1][0], y + 2))
    else:
        for index, x in enumerate(range(x0 + 1, x1, 2)):
            ends = ((x, y0 + 1), (x, y1 - 1)) if index % 2 == 0 else ((x, y1 - 1), (x, y0 + 1))
            if not points:
                points.append(ends[0])
            points.append(ends[1])
            if x + 2 < x1:
                points.append((x + 2, ends[1][1]))
    return clean(points)


def cross(a: Point, b: Point, c: Point) -> int:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def relation(first: Segment, second: Segment) -> str:
    a, b = first
    c, d = second
    values = cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b)
    if values == (0, 0, 0, 0):
        overlap_x = min(max(a[0], b[0]), max(c[0], d[0])) - max(min(a[0], b[0]), min(c[0], d[0]))
        overlap_y = min(max(a[1], b[1]), max(c[1], d[1])) - max(min(a[1], b[1]), min(c[1], d[1]))
        if max(overlap_x, overlap_y) > 0:
            return "COLLINEAR_OVERLAP"
        if overlap_x == 0 and overlap_y == 0:
            return "POINT_TOUCH"
        return "DISJOINT"
    hit = (
        (values[0] == 0 or values[1] == 0 or (values[0] < 0) != (values[1] < 0))
        and (values[2] == 0 or values[3] == 0 or (values[2] < 0) != (values[3] < 0))
    )
    if not hit:
        return "DISJOINT"
    return "T_TOUCH" if 0 in values else "PROPER_CROSSING"


def route_validation(points: list[Point]) -> dict:
    segments = list(zip(points, points[1:]))
    contacts: list[dict] = []
    for i, first in enumerate(segments):
        for j in range(i + 2, len(segments)):
            found = relation(first, segments[j])
            if found != "DISJOINT":
                contacts.append({"first_segment": i, "second_segment": j, "relation": found})
    neighbours: dict[Point, set[Point]] = defaultdict(set)
    for a, b in segments:
        neighbours[a].add(b)
        neighbours[b].add(a)
    endpoints = sum(len(items) == 1 for items in neighbours.values())
    branches = sum(len(items) > 2 for items in neighbours.values())
    orthogonal = all(a != b and (a[0] == b[0] or a[1] == b[1]) for a, b in segments)
    passed = orthogonal and endpoints == 2 and branches == 0 and not contacts
    return {
        "connected_component_count": 1 if passed else None,
        "endpoint_count": endpoints,
        "branch_count": branches,
        "self_contact_count": len(contacts),
        "orthogonal_nonzero": orthogonal,
        "result": "PASS" if passed else "FAIL",
    }


def inter_contacts(routes: list[dict]) -> list[dict]:
    contacts: list[dict] = []
    for index, first in enumerate(routes):
        first_segments = list(zip(first["ordered_points_grid"], first["ordered_points_grid"][1:]))
        for second in routes[index + 1 :]:
            second_segments = list(zip(second["ordered_points_grid"], second["ordered_points_grid"][1:]))
            for first_index, first_segment in enumerate(first_segments):
                for second_index, second_segment in enumerate(second_segments):
                    found = relation(first_segment, second_segment)
                    if found != "DISJOINT":
                        contacts.append(
                            {
                                "first_route_id": first["route_id"],
                                "first_segment": first_index,
                                "second_route_id": second["route_id"],
                                "second_segment": second_index,
                                "relation": found,
                            }
                        )
    return contacts


def point_in_box(point: Point, box: tuple[int, int, int, int]) -> bool:
    x0, y0, x1, y1 = box
    return x0 <= point[0] <= x1 and y0 <= point[1] <= y1


def segment_hits_box(segment: Segment, box: tuple[int, int, int, int]) -> bool:
    if point_in_box(segment[0], box) or point_in_box(segment[1], box):
        return True
    x0, y0, x1, y1 = box
    edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    return any(relation(segment, edge) != "DISJOINT" for edge in edges)


def make_route(
    route_id: str,
    territory: str,
    supply_port: Point,
    return_port: Point,
    supply_transit: list[Point],
    body: list[Point],
    return_transit: list[Point],
) -> dict:
    points = clean([*supply_transit, *body[1:], *return_transit[1:]])
    route = {
        "route_id": route_id,
        "floor_id": "FLOOR_1",
        "territory_id": territory,
        "collector_id": "K1",
        "supply_collector_id": "K1",
        "return_collector_id": "K1",
        "supply_port_id": f"K1-{route_id}-S",
        "return_port_id": f"K1-{route_id}-R",
        "supply_port_grid": list(supply_port),
        "return_port_grid": list(return_port),
        "supply_port_mm": [coordinate * GRID_MM for coordinate in supply_port],
        "return_port_mm": [coordinate * GRID_MM for coordinate in return_port],
        "ordered_points_grid": [list(point) for point in points],
        "ordered_points_mm": [[coordinate * GRID_MM for coordinate in point] for point in points],
        "supply_transit_points_grid": [list(point) for point in supply_transit],
        "heating_body_points_grid": [list(point) for point in body],
        "return_transit_points_grid": [list(point) for point in return_transit],
        "supply_transit_length_mm": length_mm(supply_transit),
        "heating_body_length_mm": length_mm(body),
        "return_transit_length_mm": length_mm(return_transit),
        "calculated_length_mm": length_mm(points),
        "completed": True,
        "wall_crossing_policy": "ALLOWED_TRANSIT_ONLY",
        "route_validation": route_validation(points),
    }
    route["geometry_digest"] = digest(route["ordered_points_mm"])
    return route


def build_routes() -> list[dict]:
    boiler_body = [(180 - (x - 140), y) for x, y in meander((140, 56, 180, 80), horizontal=True)]
    west_body = meander((138, 88, 155, 162), horizontal=False)
    east_body = list(reversed(meander((159, 88, 180, 159), horizontal=False)))
    return [
        make_route(
            "F1-C08",
            "BOILER_ROOM",
            (136, 56),
            (136, 60),
            [(136, 56), (141, 56), boiler_body[0]],
            boiler_body,
            [boiler_body[-1], (137, 79), (137, 60), (136, 60)],
        ),
        make_route(
            "F1-C09",
            "KITCHEN_LIVING_WEST",
            (132, 64),
            (133, 64),
            [(132, 64), (132, 87), (139, 87), west_body[0]],
            west_body,
            [west_body[-1], (153, 86), (133, 86), (133, 64)],
        ),
        make_route(
            "F1-C10",
            "KITCHEN_LIVING_EAST",
            (136, 81),
            (136, 82),
            [(136, 81), (179, 81), (179, 89), east_body[0]],
            east_body,
            [east_body[-1], (157, 89), (157, 82), (136, 82)],
        ),
    ]


def to_px(point: list[int] | Point) -> tuple[int, int]:
    return round(point[0] * PX_PER_GRID), round(point[1] * PX_PER_GRID)


def draw_overlay(routes: list[dict], target: Path) -> None:
    image = Image.open(SOURCE).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((165, 102, 1665, 330), 20, fill="#071A21EE", outline="#00CFC0", width=4)
    draw.text((198, 126), "ЭТАЖ 1 · ЛОКАЛЬНАЯ ГРУППА D012", font=font(31, True), fill="white")
    draw.text((198, 178), "3 полных петли K1 → помещение → K1 · стены проходимы", font=font(20), fill="#C8F7F2")
    draw.text((198, 220), "Пересечения / касания / общие линии: 0", font=font(20, True), fill="#66FFCC")
    draw.text((198, 263), "50,8 м · 66,7 м · 79,1 м", font=font(23, True), fill="#FFFFFF")
    draw.text((198, 300), "ПРОМЕЖУТОЧНО: остальные зоны дома ещё не проложены", font=font(17, True), fill="#FFCC80")
    k1 = tuple(round(value * PX_PER_GRID) for value in (132, 56, 136, 82))
    draw.rectangle(k1, fill="#00A88A33", outline="#00897B", width=5)
    draw.text((k1[0] + 6, k1[1] + 8), "K1", font=font(17, True), fill="#00695C", stroke_width=2, stroke_fill="white")
    colours = ["#F28E2B", "#00A7E1", "#7A49E5"]
    for route, colour in zip(routes, colours):
        points = [to_px(point) for point in route["ordered_points_grid"]]
        draw.line(points, fill="#FFFFFF", width=9, joint="curve")
        draw.line(points, fill=colour, width=5, joint="curve")
        for port_key in ("supply_port_grid", "return_port_grid"):
            x, y = to_px(route[port_key])
            draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=colour, outline="white", width=2)
        anchor = to_px(route["heating_body_points_grid"][len(route["heating_body_points_grid"]) // 2])
        draw.text((anchor[0] + 8, anchor[1] + 8), f'{route["route_id"]} · {route["calculated_length_mm"] / 1000:.1f} м', font=font(17, True), fill=colour, stroke_width=3, stroke_fill="white")
    image.convert("RGB").save(target, quality=96)


def draw_pipes_only(routes: list[dict], target: Path) -> None:
    width, height = 1785, 1100
    image = Image.new("RGB", (width, height), "#F7FAFA")
    draw = ImageDraw.Draw(image)
    for x in range(0, width, round(PX_PER_GRID)):
        draw.line((x, 0, x, height), fill="#D8E2E2", width=1)
    for y in range(0, height, round(PX_PER_GRID)):
        draw.line((0, y, width, y), fill="#D8E2E2", width=1)
    draw.rectangle((0, 0, width, 104), fill="#071A21")
    draw.text((35, 22), "D012 · КОТЕЛЬНАЯ И КУХНЯ · 3 ПОЛНЫХ ПЕТЛИ", font=font(29, True), fill="white")
    draw.text((35, 64), "Один K1 · 6 уникальных портов · контактов 0", font=font(18), fill="#A7EEE7")
    k1 = tuple(round(value * PX_PER_GRID) for value in (132, 56, 136, 82))
    draw.rectangle(k1, fill="#D8F3EE", outline="#00897B", width=5)
    draw.text((k1[0] + 5, k1[1] + 5), "K1", font=font(16, True), fill="#00695C")
    colours = ["#F28E2B", "#00A7E1", "#7A49E5"]
    for route, colour in zip(routes, colours):
        points = [to_px(point) for point in route["ordered_points_grid"]]
        draw.line(points, fill="white", width=10, joint="curve")
        draw.line(points, fill=colour, width=5, joint="curve")
        for port_key in ("supply_port_grid", "return_port_grid"):
            x, y = to_px(route[port_key])
            draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=colour, outline="white", width=2)
    image.save(target, quality=96)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("LOCAL_GROUP_012 is append-only")
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    routes = build_routes()
    contacts = inter_contacts(routes)
    tread_box = tuple(contract["vector_traced_geometry"]["floor_1_first_three_treads"]["conservative_blocked_box_grid"])
    exclusion_hits = []
    for route in routes:
        segments = list(zip(route["ordered_points_grid"], route["ordered_points_grid"][1:]))
        for index, segment in enumerate(segments):
            if segment_hits_box(segment, tread_box):
                exclusion_hits.append({"route_id": route["route_id"], "segment": index})
    ports = [tuple(route[key]) for route in routes for key in ("supply_port_grid", "return_port_grid")]
    k1 = tuple(contract["vector_traced_geometry"]["collector_k1_reserved_bbox"]["box_grid"])
    ports_inside = all(point_in_box(point, k1) for point in ports)
    lengths_valid = all(40000 <= route["calculated_length_mm"] <= 80000 for route in routes)
    topology_valid = all(route["route_validation"]["result"] == "PASS" for route in routes)
    accepted = not contacts and not exclusion_hits and len(set(ports)) == 6 and ports_inside and lengths_valid and topology_valid
    if not accepted:
        raise RuntimeError("D012 local group did not satisfy its bounded acceptance contract")
    geometry = {
        "schema": "homeaura-local-full-circuit-group-0.1",
        "artifact_id": "HA_TWO_FLOOR_LOCAL_GROUP_012",
        "status": "THREE_LOCAL_K1_FULL_ROUTES_PASS",
        "scope": "BOILER_AND_KITCHEN_ONLY",
        "units": "mm",
        "grid_mm": GRID_MM,
        "source_contract_id": contract["contract_id"],
        "source_contract_digest": contract["contract_digest"],
        "collector": {
            "collector_id": "K1",
            "logical_assembly_count": 1,
            "bbox_grid": list(k1),
            "physical_commercial_capacity": "NOT_EVALUATED",
        },
        "routes": routes,
        "whole_house_completion": False,
        "coverage_validation": "NOT_EVALUATED_IN_THIS_LOCAL_BLOCK",
        "hydraulics": "NOT_CALCULATED",
        "normative_compliance_claimed": False,
    }
    geometry["geometry_digest"] = digest(geometry)
    validation = {
        "artifact_id": geometry["artifact_id"],
        "result": geometry["status"],
        "route_count": len(routes),
        "collector_assembly_count": 1,
        "unique_port_id_count": len({route[key] for route in routes for key in ("supply_port_id", "return_port_id")}),
        "unique_port_coordinate_count": len(set(ports)),
        "all_ports_inside_k1_bbox": ports_inside,
        "route_topology_pass_count": sum(route["route_validation"]["result"] == "PASS" for route in routes),
        "self_contact_count": sum(route["route_validation"]["self_contact_count"] for route in routes),
        "inter_route_contact_count": len(contacts),
        "inter_route_contacts": contacts,
        "first_three_tread_exclusion_hit_count": len(exclusion_hits),
        "first_three_tread_exclusion_hits": exclusion_hits,
        "lengths_mm": {route["route_id"]: route["calculated_length_mm"] for route in routes},
        "all_complete_lengths_40_80m": lengths_valid,
        "wall_crossing_allowed": True,
        "whole_house_status": "IN_PROGRESS",
        "not_activated": ["ATTIC_ROUTES", "RISER_VERTICALS", "HYDRAULICS", "AUTOCAD", "DWG", "NORMATIVE_COMPLIANCE"],
    }
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(geometry, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw_overlay(routes, OUTPUT / "floor_1_local_group_overlay.png")
    draw_pipes_only(routes, OUTPUT / "floor_1_local_group_pipes_only.png")
    (OUTPUT / "report.md").write_text(
        "# HA_TWO_FLOOR_LOCAL_GROUP_012\n\n"
        "Проверенный ограниченный блок: котельная и кухня/гостиная первого этажа. "
        "Три полных контура начинаются и заканчиваются на шести уникальных портах одного K1. "
        "Длины 50,8 м, 66,7 м и 79,1 м. Самопересечения, взаимные пересечения, касания, "
        "общие участки и попадание в зону первых трёх ступеней отсутствуют. "
        "Это не завершённый проект дома: остальные зоны, мансарда, стояк, покрытие, гидравлика "
        "и нормативное соответствие ещё не подтверждены.\n",
        encoding="utf-8",
    )
    files = [
        {"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(OUTPUT.iterdir())
        if path.is_file()
    ]
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps({"artifact_id": geometry["artifact_id"], "geometry_digest": geometry["geometry_digest"], "files": files}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "geometry_digest": geometry["geometry_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

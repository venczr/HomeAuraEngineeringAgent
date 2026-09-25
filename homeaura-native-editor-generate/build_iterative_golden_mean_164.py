from __future__ import annotations

import copy
import functools
import hashlib
import itertools
import json
import math
import subprocess
import sys
import zipfile
from pathlib import Path

from shapely.geometry import LineString, Polygon, box, shape
from shapely.ops import unary_union


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_boiler_room_manifolds_dual_rise_160 import make_service_zone, route_entry, service_record  # noqa: E402
from build_dense_centre_counterflow_159 import dense_counterflow  # noqa: E402
from build_owner_style_installation_project_141 import clean, length_mm, self_contacts  # noqa: E402


ROOT = HERE.parents[0]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = PROPOSALS / "HA_TWO_FLOOR_AUDITED_DENSE_DUAL_RISE_163"
D062 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
D047 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
D039 = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039" / "canonical_geometry.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_ITERATIVE_GOLDEN_MEAN_164"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_ITERATIVE_GOLDEN_MEAN_164.zip"
ARTIFACT_ID = OUTPUT.name
OFFSET = 3000
K1_GRID = (134, 63)
COLORS = [
    "#E43F5A", "#3676C8", "#AB7DF6", "#32D583", "#F59E0B", "#14B8A6", "#F97066", "#29B6F6",
    "#A3E635", "#FB923C", "#60A5FA", "#F472B6", "#22C55E", "#06B6D4", "#C084FC", "#EF4444",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def project(point: tuple[int, int]) -> dict:
    return {"x_mm": OFFSET + point[0] * 100, "y_mm": OFFSET + point[1] * 100}


def render(project_file: Path, output: Path, clean_view: bool) -> None:
    subprocess.run([
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", "--export-png-clean" if clean_view else "--export-png", str(project_file), str(output),
    ], cwd=ROOT, check=True, capture_output=True, text=True)


def package_output() -> None:
    files = sorted(path for path in OUTPUT.iterdir() if path.is_file() and path.name != "artifact_manifest.json")
    dump(OUTPUT / "artifact_manifest.json", {
        "artifact_id": ARTIFACT_ID,
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    })
    with zipfile.ZipFile(PACKAGE, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUTPUT.iterdir()):
            if path.is_file():
                archive.write(path, path.name)


def transformed(points: list[tuple[int, int]], bounds: tuple[int, int, int, int], code: str) -> list[tuple[int, int]]:
    left, top, right, bottom = bounds
    return [
        (left + right - x if "X" in code else x, top + bottom - y if "Y" in code else y)
        for x, y in points
    ]


def orthogonal(points: list[tuple[int, int]]) -> bool:
    return all(first[0] == second[0] or first[1] == second[1] for first, second in zip(points, points[1:]))


def candidate_ok(points: list[tuple[int, int]]) -> bool:
    return (
        len(points) >= 2
        and orthogonal(points)
        and self_contacts(points) == 0
        and LineString(points).is_simple
        and all(first != second for first, second in zip(points, points[1:]))
    )


@functools.lru_cache(maxsize=None)
def dense_centre_candidates(bounds: tuple[int, int, int, int]) -> list[list[tuple[int, int]]]:
    left, top, right, bottom = bounds

    def frames(source: tuple[int, int, int, int], minimum_span: int) -> list[tuple[int, int, int, int]]:
        l, t, r, b = source
        output = []
        while r - l >= minimum_span and b - t >= minimum_span:
            output.append((l, t, r, b))
            l += 4
            t += 4
            r -= 4
            b -= 4
        return output

    def arm(frame_list: list[tuple[int, int, int, int]]) -> list[tuple[int, int]]:
        output: list[tuple[int, int]] = []
        for index, (l, t, r, b) in enumerate(frame_list):
            if index:
                output.append((output[-1][0], b))
            output.extend([(r, b), (l, b), (l, t), (r, t)])
        return clean(output)

    base = dense_counterflow(bounds)
    candidates = [base]
    inward = arm(frames(bounds, 4))
    outward = arm(frames((left + 2, top + 2, right - 2, bottom - 2), 2))
    if len(outward) >= 4:
        start = inward[-1]
        exit_point = outward[-3]
        width = start[0] - exit_point[0]
        height = exit_point[1] - start[1]
        if width >= height and width >= 4 and height >= 4:
            inner_left = exit_point[0] + 2
            inner_right = start[0] - 2
            y = start[1] + 2
            snake = [*inward, (start[0], y)]
            go_left = True
            while True:
                x = inner_left if go_left else inner_right
                snake.append((x, y))
                next_y = y + 2
                if next_y >= exit_point[1]:
                    break
                snake.append((x, next_y))
                y = next_y
                go_left = not go_left
            snake.extend([(exit_point[0], snake[-1][1]), exit_point])
            snake = clean([*snake, *reversed(outward[:-3])])
            if candidate_ok(snake):
                candidates.append(snake)
    unique: dict[tuple[tuple[int, int], ...], list[tuple[int, int]]] = {}
    for candidate in candidates:
        unique[tuple(candidate)] = candidate
    return list(unique.values())


def exterior_band(
    bounds: tuple[int, int, int, int], sides: frozenset[str]
) -> tuple[list[tuple[int, int]], tuple[int, int, int, int]]:
    left, top, right, bottom = bounds
    if sides == frozenset({"L", "T", "R", "B"}):
        # Three open nested perimeter passes. They cover every exterior face at
        # 100 mm pitch without closing a loop or duplicating an edge.
        return [
            (left, bottom), (left, top), (right, top), (right, bottom), (left + 1, bottom),
            (left + 1, top + 1), (right - 1, top + 1), (right - 1, bottom - 1), (left + 2, bottom - 1),
            (left + 2, top + 2), (right - 2, top + 2), (right - 2, bottom - 2),
        ], (left + 4, top + 4, right - 4, bottom - 4)
    if sides == frozenset({"L"}):
        return [(left, bottom), (left, top), (left + 1, top), (left + 1, bottom), (left + 2, bottom), (left + 2, top)], (left + 4, top, right, bottom)
    if sides == frozenset({"R"}):
        return [(right, bottom), (right, top), (right - 1, top), (right - 1, bottom), (right - 2, bottom), (right - 2, top)], (left, top, right - 4, bottom)
    if sides == frozenset({"B"}):
        return [(left, bottom), (right, bottom), (right, bottom - 1), (left, bottom - 1), (left, bottom - 2), (right, bottom - 2)], (left, top, right, bottom - 4)
    if sides == frozenset({"T"}):
        return [(right, top), (left, top), (left, top + 1), (right, top + 1), (right, top + 2), (left, top + 2)], (left, top + 4, right, bottom)
    if sides == frozenset({"L", "T"}):
        return [(left, bottom), (left, top), (right, top), (right, top + 1), (left + 1, top + 1), (left + 1, bottom), (left + 2, bottom), (left + 2, top + 2), (right, top + 2)], (left + 4, top + 4, right, bottom)
    if sides == frozenset({"R", "T"}):
        return [(right, bottom), (right, top), (left, top), (left, top + 1), (right - 1, top + 1), (right - 1, bottom), (right - 2, bottom), (right - 2, top + 2), (left, top + 2)], (left, top + 4, right - 4, bottom)
    if sides == frozenset({"L", "B"}):
        return [(left, top), (left, bottom), (right, bottom), (right, bottom - 1), (left + 1, bottom - 1), (left + 1, top), (left + 2, top), (left + 2, bottom - 2), (right, bottom - 2)], (left + 4, top, right, bottom - 4)
    if sides == frozenset({"R", "B"}):
        return [(right, top), (right, bottom), (left, bottom), (left, bottom - 1), (right - 1, bottom - 1), (right - 1, top), (right - 2, top), (right - 2, bottom - 2), (left, bottom - 2)], (left, top, right - 4, bottom - 4)
    raise ValueError(sides)


@functools.lru_cache(maxsize=None)
def body_candidates(bounds: tuple[int, int, int, int], sides: frozenset[str]) -> list[dict]:
    bounds_polygon = box(*bounds)
    output: list[dict] = []
    if not sides:
        for core in dense_centre_candidates(bounds):
            for code in ("", "X", "Y", "XY"):
                candidate = transformed(core, bounds, code)
                for reverse in (False, True):
                    points = list(reversed(candidate)) if reverse else candidate
                    if candidate_ok(points):
                        output.append({"points": points, "core_bounds": bounds, "exterior_sides": [], "variant": f"CORE_{code or 'I'}_{int(reverse)}"})
    else:
        prelude, base_core_bounds = exterior_band(bounds, sides)
        for inset in (0, 2, 4):
            l, t, r, b = base_core_bounds
            core_bounds = (l + inset, t + inset, r - inset, b - inset)
            if core_bounds[2] - core_bounds[0] < 8 or core_bounds[3] - core_bounds[1] < 8:
                continue
            for core in dense_centre_candidates(core_bounds):
                for code in ("", "X", "Y", "XY"):
                    oriented = transformed(core, core_bounds, code)
                    for reverse in (False, True):
                        route = list(reversed(oriented)) if reverse else oriented
                        last_is_vertical = prelude[-2][0] == prelude[-1][0]
                        # Exit the third perimeter pass perpendicularly. A collinear join lets
                        # clean() shorten that pass and creates exactly the window-edge void
                        # the owner rejected.
                        bends = ((route[0][0], prelude[-1][1]),) if last_is_vertical else ((prelude[-1][0], route[0][1]),)
                        for bend in bends:
                            points = clean([*prelude, bend, *route])
                            line = LineString(points)
                            if candidate_ok(points) and bounds_polygon.covers(line):
                                output.append({
                                    "points": points,
                                    "core_bounds": core_bounds,
                                    "exterior_sides": sorted(sides),
                                    "variant": f"EDGE_{''.join(sorted(sides))}_I{inset}_{code or 'I'}_{int(reverse)}",
                                })
    unique: dict[tuple[tuple[int, int], ...], dict] = {}
    for item in output:
        unique[tuple(item["points"])] = item
    return list(unique.values())


def compositions(total: int, count: int, low: int, high: int):
    if count == 1:
        if low <= total <= high:
            yield (total,)
        return
    for first in range(low, high + 1):
        yield from ((first, *rest) for rest in compositions(total - first, count - 1, low, high))


def partition_variants(bounds: tuple[int, int, int, int], count: int, axis: str) -> list[list[tuple[int, int, int, int]]]:
    left, top, right, bottom = bounds
    total = (right - left if axis == "X" else bottom - top) - 2 * (count - 1)
    average = total / count
    low = max(8, math.floor(average) - 3)
    high = math.ceil(average) + 3
    variants = []
    for spans in compositions(total, count, low, high):
        cursor = left if axis == "X" else top
        boxes = []
        for span in spans:
            if axis == "X":
                boxes.append((cursor, top, cursor + span, bottom))
            else:
                boxes.append((left, cursor, right, cursor + span))
            cursor += span + 2
        variants.append(boxes)
    variants.sort(key=lambda boxes: sum((
        ((right - left) if axis == "X" else (bottom - top)) - average
    ) ** 2 for left, top, right, bottom in boxes))
    return variants[:256]


def floor_service_mm(points: list[tuple[int, int]]) -> int:
    start, end = points[0], points[-1]
    return (
        abs(start[0] - K1_GRID[0]) + abs(start[1] - K1_GRID[1])
        + abs(end[0] - K1_GRID[0]) + abs(end[1] - K1_GRID[1])
    ) * 100


def choose_group(
    polygon: Polygon,
    variants: list[list[tuple[int, int, int, int]]],
    side_resolver,
    service_resolver,
    minimum_total_mm: int = 40_000,
    maximum_total_mm: int = 80_000,
) -> tuple[list[dict], dict]:
    evaluated = 0
    accepted = 0
    best = None
    for boxes in variants:
        chosen = []
        failed = False
        for index, bounds in enumerate(boxes):
            sides = frozenset(side_resolver(index, len(boxes)))
            local_best = None
            local_polygon = box(*(coordinate * 100 for coordinate in bounds))
            for candidate in body_candidates(bounds, sides):
                evaluated += 1
                points = candidate["points"]
                service_mm = service_resolver(points, index)
                body_mm = length_mm(points)
                total_mm = body_mm + service_mm
                if not minimum_total_mm <= total_mm <= maximum_total_mm:
                    continue
                accepted += 1
                line = LineString([(x * 100, y * 100) for x, y in points])
                gap = local_polygon.difference(line.buffer(100, quad_segs=16)).area
                score = (gap, abs(total_mm - 65_000), body_mm)
                if local_best is None or score < local_best[0]:
                    local_best = (score, {**candidate, "bounds": bounds, "body_length_mm": body_mm, "service_length_mm": service_mm, "total_length_mm": total_mm})
            if local_best is None:
                failed = True
                break
            chosen.append(local_best[1])
        if failed:
            continue
        lines = [LineString([(x * 100, y * 100) for x, y in item["points"]]) for item in chosen]
        if any(not first.intersection(second).is_empty for i, first in enumerate(lines) for second in lines[i + 1 :]):
            continue
        served = polygon.intersection(unary_union([line.buffer(100, quad_segs=16) for line in lines])).area
        score = (polygon.area - served, max(item["total_length_mm"] for item in chosen) - min(item["total_length_mm"] for item in chosen))
        if best is None or score < best[0]:
            best = (score, chosen)
    if best is None:
        raise RuntimeError("No group candidate")
    return best[1], {"evaluated_body_variants": evaluated, "accepted_length_variants": accepted, "partition_variants": len(variants)}


def serial_join(first_candidates: list[dict], second_candidates: list[dict], allowed: Polygon, service_fn) -> dict:
    best = None
    evaluated = 0
    for first in first_candidates:
        for second in second_candidates:
            for bend in (
                (first["points"][-1][0], second["points"][0][1]),
                (second["points"][0][0], first["points"][-1][1]),
            ):
                evaluated += 1
                points = clean([*first["points"], bend, *second["points"]])
                line = LineString(points)
                if not candidate_ok(points) or not allowed.covers(line):
                    continue
                service_mm = service_fn(points)
                body_mm = length_mm(points)
                total_mm = body_mm + service_mm
                if not 40_000 <= total_mm <= 80_000:
                    continue
                gap = allowed.difference(line.buffer(1, quad_segs=16)).area
                score = (gap, abs(total_mm - 65_000))
                if best is None or score < best[0]:
                    best = (score, {
                        "points": points,
                        "body_length_mm": body_mm,
                        "service_length_mm": service_mm,
                        "total_length_mm": total_mm,
                        "variant": f"SERIAL_{first['variant']}__{second['variant']}",
                        "exterior_sides": sorted(set(first["exterior_sides"]) | set(second["exterior_sides"])),
                        "evaluated_serial_joins": evaluated,
                    })
    if best is None:
        raise RuntimeError("No serial join")
    best[1]["evaluated_serial_joins"] = evaluated
    return best[1]


def floor_room_polygon(project_data: dict, room_id: str) -> Polygon:
    room = next(item for item in project_data["rooms"] if item["id"] == room_id)
    return Polygon([(point["x_mm"] - OFFSET, point["y_mm"] - OFFSET) for point in room["outline"]])


def project_room_polygon(project_data: dict, room_id: str) -> Polygon:
    room = next(item for item in project_data["rooms"] if item["id"] == room_id)
    return Polygon([(point["x_mm"], point["y_mm"]) for point in room["outline"]])


def make_floor_circuit(route_id: str, item: dict, colour: str, territory: str) -> tuple[dict, dict]:
    circuit = {
        "id": route_id,
        "name": f"{route_id} · улитка 3×100/200",
        "color": colour,
        "ordered_points": [project(point) for point in item["points"]],
        "completed": True,
        "collector_id": "K1",
        "supply_port_index": None,
        "return_port_index": None,
        "service_zone_id": "K1-HIDDEN-TRANSIT-RESERVATION-D164",
        "concealed_service_length_mm": item["service_length_mm"],
    }
    record = {
        "route_id": route_id,
        "territory": territory,
        "body_points_grid": [list(point) for point in item["points"]],
        "body_length_mm": item["body_length_mm"],
        "concealed_service_length_mm": item["service_length_mm"],
        "design_total_length_mm": item["total_length_mm"],
        "body_spacing_mm": 200,
        "window_wall_edge_axes_mm": [100, 200, 300] if item.get("exterior_sides") else [],
        "exterior_sides": item.get("exterior_sides", []),
        "geometry_variant": item.get("variant"),
        "service_axis_geometry_materialized": False,
    }
    return circuit, record


def window_edge_audit(project_data: dict, circuits: list[dict]) -> dict:
    wall_by_id = {item["id"]: item for item in project_data["walls"]}
    segments = []
    for circuit in circuits:
        points = [(point["x_mm"], point["y_mm"]) for point in circuit["ordered_points"]]
        segments.extend((circuit["id"], first, second) for first, second in zip(points, points[1:]))
    records = []
    for window in project_data.get("windows", []):
        wall = wall_by_id[window["wall_id"]]
        a = (wall["start"]["x_mm"], wall["start"]["y_mm"])
        b = (wall["end"]["x_mm"], wall["end"]["y_mm"])
        w1 = (window["start"]["x_mm"], window["start"]["y_mm"])
        w2 = (window["end"]["x_mm"], window["end"]["y_mm"])
        vertical = a[0] == b[0]
        distances = set()
        owners = set()
        for route_id, first, second in segments:
            parallel = first[0] == second[0] if vertical else first[1] == second[1]
            if not parallel:
                continue
            if vertical:
                overlap = min(max(first[1], second[1]), max(w1[1], w2[1])) - max(min(first[1], second[1]), min(w1[1], w2[1]))
                distance = abs(first[0] - a[0])
            else:
                overlap = min(max(first[0], second[0]), max(w1[0], w2[0])) - max(min(first[0], second[0]), min(w1[0], w2[0]))
                distance = abs(first[1] - a[1])
            if overlap > 0 and distance <= 320:
                distances.add(round(distance))
                owners.add(route_id)
        ordered = sorted(distances)
        pass_three = len(ordered) >= 3 and ordered[0] <= 110 and 90 <= ordered[1] - ordered[0] <= 110 and 90 <= ordered[2] - ordered[1] <= 110
        records.append({"window_id": window["id"], "axis_distances_mm": ordered, "route_ids": sorted(owners), "three_axes_at_100mm_pitch": pass_three})
    return {"window_count": len(records), "pass_count": sum(item["three_axes_at_100mm_pitch"] for item in records), "records": records}


def coverage(project_data: dict, circuits: list[dict], floor_geometry: Polygon | None = None) -> dict:
    if floor_geometry is None:
        floor_geometry = unary_union([
            Polygon([(point["x_mm"], point["y_mm"]) for point in room["outline"]])
            for room in project_data["rooms"]
        ])
        lines = [LineString([(point["x_mm"], point["y_mm"]) for point in circuit["ordered_points"]]) for circuit in circuits]
    else:
        lines = [LineString([(point["x_mm"] - OFFSET, point["y_mm"] - OFFSET) for point in circuit["ordered_points"]]) for circuit in circuits]
    sweep = unary_union([line.buffer(100, quad_segs=16) for line in lines])
    served = floor_geometry.intersection(sweep).area
    return {
        "floor_area_m2": floor_geometry.area / 1_000_000,
        "served_m2": served / 1_000_000,
        "unresolved_m2": (floor_geometry.area - served) / 1_000_000,
        "served_percent": served * 100 / floor_geometry.area,
        "method": "ROUND_100MM_BODY_CENTERLINE_PROXIMITY_Q16",
        "service_transits_counted": False,
        "full_coverage_claimed": False,
    }


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D164 is append-only")
    OUTPUT.mkdir(parents=True)
    floor_source = SOURCE / "HomeAura_Floor1_Audited_D163.homeaura.json"
    attic_source = SOURCE / "HomeAura_Attic_Audited_D163.homeaura.json"
    contract_source = SOURCE / "audited_dense_dual_rise_contract.json"
    floor1, attic, source_contract = load(floor_source), load(attic_source), load(contract_source)

    search_evidence: dict[str, dict] = {}
    floor_items: list[tuple[str, dict, str]] = []

    floor_groups = [
        ("F1-R08", "Спальня север", (45, 56, 93, 86), 2, "X", lambda i, n: {"L"} if i == 0 else set()),
        ("F1-R07", "Спальня запад", (45, 95, 92, 120), 2, "X", lambda i, n: {"L"} if i == 0 else set()),
        ("F1-R06", "Ванная и душевая", (45, 128, 93, 164), 2, "Y", lambda i, n: {"B"} if i == n - 1 else set()),
        ("F1-R04", "Котельная", (133, 56, 182, 87), 2, "X", lambda i, n: set()),
        ("F1-R03", "Кухня-гостиная", (133, 91, 182, 164), 5, "Y", lambda i, n: ({"R", "B"} if i == n - 1 else {"R"})),
    ]
    next_index = 1
    for room_id, territory, bounds, count, axis, side_resolver in floor_groups:
        items, evidence = choose_group(
            floor_room_polygon(floor1, room_id),
            partition_variants(bounds, count, axis),
            side_resolver,
            lambda points, _: floor_service_mm(points),
        )
        search_evidence[room_id] = evidence
        for item in items:
            floor_items.append((f"F1-G{next_index:02d}", item, territory))
            next_index += 1

    entrance_candidates = []
    entrance_polygon = floor_room_polygon(floor1, "F1-R01")
    for item in body_candidates((93, 170, 136, 192), frozenset({"R", "B"})):
        service_mm = floor_service_mm(item["points"])
        body_mm = length_mm(item["points"])
        total_mm = body_mm + service_mm
        if 40_000 <= total_mm <= 80_000:
            line = LineString([(x * 100, y * 100) for x, y in item["points"]])
            gap = entrance_polygon.difference(line.buffer(100, quad_segs=16)).area
            entrance_candidates.append((gap, abs(total_mm - 65_000), {**item, "body_length_mm": body_mm, "service_length_mm": service_mm, "total_length_mm": total_mm}))
    if not entrance_candidates:
        raise RuntimeError("Entrance candidate")
    entrance = min(entrance_candidates, key=lambda candidate: (candidate[0], candidate[1]))[2]
    search_evidence["F1-R01"] = {"evaluated_body_variants": len(body_candidates((93, 170, 136, 192), frozenset({"R", "B"}))), "accepted_length_variants": len(entrance_candidates)}
    floor_items.append((f"F1-G{next_index:02d}", entrance, "Входная группа"))
    next_index += 1

    hall_source = next(route for route in load(D039)["routes"] if route["route_id"] == "F1-C06")
    hall_points = [tuple(point) for point in hall_source["heating_body_points_grid"]]
    hall_long = {
        "points": hall_points,
        "body_length_mm": hall_source["heating_body_length_mm"],
        "service_length_mm": hall_source["total_length_mm"] - hall_source["heating_body_length_mm"],
        "total_length_mm": hall_source["total_length_mm"],
        "variant": "ONE_LONG_THREE_LOBE_COUNTERFLOW_D039",
        "exterior_sides": [],
    }
    search_evidence["F1-R02"] = {
        "selected_long_hall_source": hall_source["route_id"],
        "body_point_count": len(hall_points),
        "design_total_length_mm": hall_source["total_length_mm"],
    }
    floor_items.append((f"F1-G{next_index:02d}", hall_long, "Холл — один длинный трёхзонный контур-улитка"))

    if len(floor_items) != 15:
        raise RuntimeError(f"K1 count {len(floor_items)}")
    floor_circuits, floor_records = [], []
    for index, (route_id, item, territory) in enumerate(floor_items):
        circuit, record = make_floor_circuit(route_id, item, COLORS[index], territory)
        circuit["supply_port_index"] = index * 2
        circuit["return_port_index"] = index * 2 + 1
        floor_circuits.append(circuit)
        floor_records.append(record)
    floor1["circuits"] = floor_circuits
    next(item for item in floor1["collectors"] if item["id"] == "K1")["ports"] = 30
    floor1["service_zones"] = [item for item in floor1["service_zones"] if not item["id"].startswith("K1-HIDDEN")]
    floor1["service_zones"].append({
        "id": "K1-HIDDEN-TRANSIT-RESERVATION-D164",
        "floor_id": "FLOOR_1",
        "name": "K1 → 15 тел контуров первого этажа",
        "outline": [{"x_mm": 12600, "y_mm": 8500}, {"x_mm": 16200, "y_mm": 8500}, {"x_mm": 16200, "y_mm": 11800}, {"x_mm": 12600, "y_mm": 11800}],
        "fill_color": "#92400E",
        "note": "Резерв индивидуальных подводок K1; не общая труба и не часть body-only покрытия.",
        "collector_id": "K1",
        "clear_height_mm": 70,
        "pipe_capacity": None,
        "required_pipe_count": 30,
        "required_plan_width_mm": None,
        "pipe_geometry_materialized": False,
    })

    domains = load(D062)
    hall_contract = load(D047)
    attic_floor = unary_union(
        [shape(item["floor_geojson"]) for item in domains["adjacent_floor_domains"]]
        + [shape(hall_contract["hall_source_contract"]["routing_draft_allowed_floor_geojson"])]
    )
    attic_contract_records = {item["route_id"]: item for item in source_contract["routes"]}
    attic_items: list[tuple[str, dict, str, str]] = []

    attic_groups = [
        ("A-R15", "Гардероб", (47, 58, 96, 81), 1, "X", lambda i, n: {"L"}, "UNDER_STAIR_WALL_TO_WARDROBE"),
        ("A-R14", "Спальня — три контура вместо четырёх", (47, 85, 96, 139), 3, "Y", lambda i, n: {"L"}, "UNDER_STAIR_WALL_TO_WARDROBE"),
        ("A-R16", "Ванная/WC", (47, 143, 96, 165), 2, "X", lambda i, n: {"L"} if i == 0 else set(), "UNDER_STAIR_WALL_TO_WARDROBE"),
        ("A-R10", "Детская восток", (133, 58, 185, 104), 3, "X", lambda i, n: {"R"} if i == n - 1 else set(), "DIRECT_BOILER_SLAB_TO_RIGHT_HALF"),
        ("A-R12", "Детская юго-восток", (133, 130, 185, 166), 2, "X", lambda i, n: {"R"} if i == n - 1 else set(), "DIRECT_BOILER_SLAB_TO_RIGHT_HALF"),
    ]
    attic_index = 1
    for room_id, territory, bounds, count, axis, side_resolver, branch in attic_groups:
        room_polygon = Polygon([(x - OFFSET, y - OFFSET) for x, y in project_room_polygon(attic, room_id).exterior.coords])
        items, evidence = choose_group(
            room_polygon,
            partition_variants(bounds, count, axis),
            side_resolver,
            lambda points, _: service_record(branch, points[0], points[-1])["concealed_service_length_mm"],
        )
        search_evidence[room_id] = evidence
        for item in items:
            attic_items.append((f"A-G{attic_index:02d}", item, territory, branch))
            attic_index += 1

    wc_allowed = unary_union([
        Polygon([(x - OFFSET, y - OFFSET) for x, y in project_room_polygon(attic, room_id).exterior.coords])
        for room_id in ("A-R11", "A-R13")
    ])
    wc_allowed_grid = unary_union([
        Polygon([(x / 100, y / 100) for x, y in polygon.exterior.coords])
        for polygon in wc_allowed.geoms
    ]).convex_hull
    wc_candidates = []
    for item in body_candidates((133, 108, 185, 126), frozenset({"R"})):
        line = LineString(item["points"])
        body_mm = length_mm(item["points"])
        service_mm = service_record("DIRECT_BOILER_SLAB_TO_RIGHT_HALF", item["points"][0], item["points"][-1])["concealed_service_length_mm"]
        total_mm = body_mm + service_mm
        if 40_000 <= total_mm <= 80_000 and wc_allowed_grid.covers(line):
            gap = wc_allowed_grid.difference(line.buffer(1, quad_segs=16)).area
            wc_candidates.append((gap, abs(total_mm - 65_000), {
                **item,
                "body_length_mm": body_mm,
                "service_length_mm": service_mm,
                "total_length_mm": total_mm,
                "variant": f"TWO_WC_ONE_LONG_COUNTERFLOW_{item['variant']}",
            }))
    if not wc_candidates:
        raise RuntimeError("No two-WC long spiral")
    wc_serial = min(wc_candidates, key=lambda candidate: (candidate[0], candidate[1]))[2]
    attic_items.append((f"A-G{attic_index:02d}", wc_serial, "Два малых WC — один последовательный контур", "DIRECT_BOILER_SLAB_TO_RIGHT_HALF"))
    attic_index += 1

    for old_id, territory in (("A-C05", "Холл — север"), ("A-C06", "Холл — середина"), ("A-C07", "Холл — юг")):
        old = attic_contract_records[old_id]
        points = [tuple(point) for point in old["body_points_grid"]]
        service_mm = service_record("DIRECT_BOILER_SLAB_TO_RIGHT_HALF", points[0], points[-1])["concealed_service_length_mm"]
        attic_items.append((f"A-G{attic_index:02d}", {
            "points": points,
            "body_length_mm": length_mm(points),
            "service_length_mm": service_mm,
            "total_length_mm": length_mm(points) + service_mm,
            "variant": f"D163_PRESERVED_{old_id}",
            "exterior_sides": [],
        }, territory, "DIRECT_BOILER_SLAB_TO_RIGHT_HALF"))
        attic_index += 1

    if len(attic_items) != 15:
        raise RuntimeError(f"K2 count {len(attic_items)}")
    attic_circuits, attic_records = [], []
    for index, (route_id, item, territory, branch) in enumerate(attic_items):
        circuit, record = route_entry(route_id, item["points"], branch, territory)
        circuit["color"] = COLORS[index]
        circuit["supply_port_index"] = index * 2
        circuit["return_port_index"] = index * 2 + 1
        circuit["service_zone_id"] = "K2-STAIR-WALL-BRANCH-D164" if branch.startswith("UNDER") else "K2-DIRECT-SLAB-BRANCH-D164"
        record.update({
            "window_wall_edge_axes_mm": [100, 200, 300] if item.get("exterior_sides") else [],
            "exterior_sides": item.get("exterior_sides", []),
            "geometry_variant": item.get("variant"),
        })
        attic_circuits.append(circuit)
        attic_records.append(record)
    attic["circuits"] = attic_circuits
    stair_records = [item for item in attic_records if item["branch_id"].startswith("UNDER")]
    direct_records = [item for item in attic_records if item["branch_id"].startswith("DIRECT")]
    floor_zone_by_id = {item["id"]: item for item in floor1["service_zones"]}
    stair_floor_zone = floor_zone_by_id.pop("K2-STAIR-WALL-FLOOR-D163", None)
    direct_floor_zone = floor_zone_by_id.pop("K2-DIRECT-SLAB-D163", None)
    shared_zone = floor_zone_by_id.pop("K1-K2-SHARED-WALL-CABINET-D163", None)
    if stair_floor_zone:
        stair_floor_zone.update({"id": "K2-STAIR-WALL-FLOOR-D164", "required_pipe_count": len(stair_records) * 2})
        floor_zone_by_id[stair_floor_zone["id"]] = stair_floor_zone
    if direct_floor_zone:
        direct_floor_zone.update({"id": "K2-DIRECT-SLAB-D164", "required_pipe_count": len(direct_records) * 2})
        floor_zone_by_id[direct_floor_zone["id"]] = direct_floor_zone
    if shared_zone:
        shared_zone.update({
            "id": "K1-K2-SHARED-WALL-CABINET-D164",
            "required_pipe_count": (len(floor_records) + len(attic_records)) * 2,
            "pipe_capacity": (len(floor_records) + len(attic_records)) * 2,
        })
        floor_zone_by_id[shared_zone["id"]] = shared_zone
    floor1["service_zones"] = list(floor_zone_by_id.values())
    attic["service_zones"] = [
        {**make_service_zone("K2-STAIR-WALL-BRANCH-D164", "K2 → под лестницей → дальняя стена → гардероб", stair_records), "pipe_geometry_materialized": False, "required_pipe_count": len(stair_records) * 2},
        {**make_service_zone("K2-DIRECT-SLAB-BRANCH-D164", "K2 → внутренняя проходка → правая половина", direct_records), "pipe_geometry_materialized": False, "required_pipe_count": len(direct_records) * 2},
    ]
    next(item for item in floor1["collectors"] if item["id"] == "K2")["ports"] = 30
    attic["collectors"][0].update({"ports": 30, "rotation_degrees": 180, "pipe_outlet_direction": "UP", "visible_on_plan": False, "external_to_plan": True})

    all_lines = []
    for floor_name, circuits in (("FLOOR_1", floor_circuits), ("ATTIC", attic_circuits)):
        for circuit in circuits:
            line = LineString([(point["x_mm"], point["y_mm"]) for point in circuit["ordered_points"]])
            if not line.is_simple:
                raise RuntimeError(f"Self contact {circuit['id']}")
            all_lines.append((floor_name, circuit["id"], line))
        floor_lines = [(route_id, line) for floor_id, route_id, line in all_lines if floor_id == floor_name]
        for index, (first_id, first) in enumerate(floor_lines):
            for second_id, second in floor_lines[index + 1 :]:
                if not first.intersection(second).is_empty:
                    raise RuntimeError(f"Contact {first_id}/{second_id}")

    floor1_coverage = coverage(floor1, floor_circuits)
    attic_coverage = coverage(attic, attic_circuits, attic_floor)
    floor1_windows = window_edge_audit(floor1, floor_circuits)
    attic_windows = window_edge_audit(attic, attic_circuits)
    if floor1_windows["pass_count"] != floor1_windows["window_count"] or attic_windows["pass_count"] != attic_windows["window_count"]:
        raise RuntimeError({"floor1": floor1_windows, "attic": attic_windows})
    floor_totals = [item["design_total_length_mm"] for item in floor_records]
    attic_totals = [item["design_total_length_mm"] for item in attic_records]
    if not all(40_000 <= item <= 80_000 for item in floor_totals + attic_totals):
        raise RuntimeError({"floor": floor_totals, "attic": attic_totals})

    for project_data in (floor1, attic):
        project_data["routing_rules"].update({
            "exterior_edge_zone_applied": True,
            "transit_lane_geometry_verified": False,
            "exterior_wall_spacing_mm": 100,
            "field_spacing_mm": 200,
            "maximum_parallel_transit_pipes_at_100mm": 3,
        })
    floor1["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D164: 15 K1 контуров; холл обслуживается одним длинным контуром; все 8 окон имеют три отдельные оси 100 мм; тела улиток отделены от резервов подводок.",
        "author_intent": "Iterative golden-mean room allocation with explicit window-wall edge bands",
    }
    attic["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D164: 15 K2 контуров; большая спальня теперь 3 контура вместо 4; все 8 окон имеют три оси 100 мм.",
        "author_intent": "Fewer natural room circuits with edge-band-first counterflow search",
    }

    contract = {
        "artifact_id": ARTIFACT_ID,
        "status": "ITERATIVE_GOLDEN_MEAN_BODY_LAYOUT_PASS_REWORK_INDIVIDUAL_TRANSIT_AXES_AND_HYDRAULICS",
        "source_D163_floor1_sha256": sha(floor_source),
        "source_D163_attic_sha256": sha(attic_source),
        "source_D163_contract_sha256": sha(contract_source),
        "owner_rules": {
            "floor_loop_pipe_od_mm": 16,
            "minimum_bend_radius_mm": 80,
            "field_spacing_mm": 200,
            "window_external_wall_first_three_axes_spacing_mm": 100,
            "penetration_sleeves_required": False,
            "maximum_three_parallel_transit_pipes_at_100mm": True,
        },
        "collector_allocation": {
            "same_boiler_room_wall": True,
            "K1_floor1_circuit_count": len(floor_records),
            "K1_connection_count": len(floor_records) * 2,
            "K2_attic_circuit_count": len(attic_records),
            "K2_connection_count": len(attic_records) * 2,
            "K2_rotation_degrees": 180,
            "K2_outlets": "UP",
        },
        "room_allocation": {
            "floor1": {"north_bedroom": 2, "west_bedroom": 2, "bath_and_shower": 2, "boiler_room": 2, "kitchen_living": 5, "entrance": 1, "hall": 1},
            "attic": {"wardrobe": 1, "large_bedroom": 3, "bath_wc": 2, "east_child": 3, "two_small_wc_serial": 1, "south_east_child": 2, "hall": 3},
            "large_attic_bedroom_changed_from_four_to_three": True,
        },
        "floor1_routes": floor_records,
        "attic_routes": attic_records,
        "floor1_coverage": floor1_coverage,
        "attic_coverage": attic_coverage,
        "floor1_window_edge_audit": floor1_windows,
        "attic_window_edge_audit": attic_windows,
        "search_evidence": search_evidence,
        "body_contact_count": 0,
        "all_design_lengths_40_80m": True,
        "minimum_design_length_mm": min(floor_totals + attic_totals),
        "maximum_design_length_mm": max(floor_totals + attic_totals),
        "individual_transit_axes_materialized": False,
        "hydraulic_balance_calculated": False,
        "installation_ready": False,
    }

    floor_file = OUTPUT / "HomeAura_Floor1_GoldenMean_D164.homeaura.json"
    attic_file = OUTPUT / "HomeAura_Attic_GoldenMean_D164.homeaura.json"
    dump(floor_file, floor1)
    dump(attic_file, attic)
    dump(OUTPUT / "iterative_golden_mean_contract.json", contract)
    dump(OUTPUT / "lineage.json", {
        "source_D163_floor1_sha256": sha(floor_source),
        "source_D163_attic_sha256": sha(attic_source),
        "floor1_body_layout_rebuilt": True,
        "attic_body_layout_rebuilt": True,
        "service_reservations_remain_non_pipe_geometry": True,
    })
    dump(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "status": contract["status"],
        "K1_circuit_count": len(floor_records),
        "K2_circuit_count": len(attic_records),
        "floor1_served_percent": floor1_coverage["served_percent"],
        "attic_served_percent": attic_coverage["served_percent"],
        "window_edge_pass_count": floor1_windows["pass_count"] + attic_windows["pass_count"],
        "window_count": floor1_windows["window_count"] + attic_windows["window_count"],
        "body_contact_count": 0,
        "installation_ready": False,
    })
    (OUTPUT / "README.md").write_text(
        "# D164 — итерационный поиск золотой середины\n\n"
        "Первый этаж перестроен на 15 тел контуров K1, мансарда — на 15 тел K2. Холл первого этажа обслуживает один длинный трёхзонный контур; большая спальня мансарды теперь имеет три контура вместо четырёх. "
        "У каждой из 16 оконных стеновых позиций доказаны три отдельные оси с шагом 100 мм; остальное поле заполняется с шагом 200 мм.\n\n"
        f"Body-only proximity: первый этаж {floor1_coverage['served_percent']:.2f}%, мансарда {attic_coverage['served_percent']:.2f}%. "
        "Подводки пока остаются резервами, а не совпадающими линиями труб; гидравлическая балансировка не заявлена.\n",
        encoding="utf-8",
    )

    render(floor_file, OUTPUT / "HomeAura_Floor1_D164_Editor_View.png", False)
    render(floor_file, OUTPUT / "HomeAura_Floor1_D164_Clean_View.png", True)
    render(attic_file, OUTPUT / "HomeAura_Attic_D164_Editor_View.png", False)
    render(attic_file, OUTPUT / "HomeAura_Attic_D164_Clean_View.png", True)
    package_output()
    print(json.dumps({
        "artifact_id": ARTIFACT_ID,
        "K1_circuits": len(floor_records),
        "K2_circuits": len(attic_records),
        "floor1_coverage": floor1_coverage,
        "attic_coverage": attic_coverage,
        "window_edge_pass": floor1_windows["pass_count"] + attic_windows["pass_count"],
        "window_count": floor1_windows["window_count"] + attic_windows["window_count"],
        "minimum_length_m": min(floor_totals + attic_totals) / 1000,
        "maximum_length_m": max(floor_totals + attic_totals) / 1000,
        "package": str(PACKAGE),
        "package_sha256": sha(PACKAGE),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

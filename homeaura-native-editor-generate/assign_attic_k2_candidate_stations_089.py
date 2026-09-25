from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_085 = BASE / "HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085" / "attic_body_geometry.json"
SOURCE_086 = BASE / "HA_TWO_FLOOR_ATTIC_ROUTING_BUDGETS_086" / "attic_routing_budgets.json"
SOURCE_088 = BASE / "HA_TWO_FLOOR_ATTIC_K2_PORT_LATTICE_088" / "attic_k2_port_lattice.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_K2_STATION_ASSIGNMENT_089"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_K2_STATION_ASSIGNMENT_089.zip"

DX_MM = 359.83333333356
DY_MM = 304.8
TARGET_MM = 78_000


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def registered_points(route):
    return [(x - DX_MM, y - DY_MM) for x, y in route["body_points_mm"]]


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D089 is append-only")
    raw_085, body = read(SOURCE_085)
    raw_086, budgets = read(SOURCE_086)
    raw_088, lattice = read(SOURCE_088)
    routes = {route["route_id"]: route for route in body["body_routes"]}
    definitions = []
    for circuit in budgets["circuit_budgets"]:
        ids = circuit["source_body_ids"]
        if len(ids) == 1:
            points = registered_points(routes[ids[0]])
            start, end = points[0], points[-1]
        else:
            first = registered_points(routes[ids[0]])
            second = registered_points(routes[ids[1]])
            if circuit["first_body_reversed"]:
                first.reverse()
            if circuit["second_body_reversed"]:
                second.reverse()
            start, end = first[0], second[-1]
        definitions.append({
            "circuit_id": circuit["circuit_id"],
            "source_body_ids": ids,
            "body_length_mm": circuit["body_length_mm"],
            "start_building_mm": start,
            "end_building_mm": end,
        })

    stations = sorted({tuple(item["plan_xy_mm"]) for item in lattice["candidate_ports"]}, key=lambda point: (point[1], point[0]))
    count = len(definitions)
    infinity = float("inf")
    dp = [infinity] * (1 << count)
    parent = [None] * (1 << count)
    dp[0] = 0.0
    for mask in range(1 << count):
        circuit_index = mask.bit_count()
        if circuit_index >= count or dp[mask] == infinity:
            continue
        circuit = definitions[circuit_index]
        for station_index, station in enumerate(stations):
            if mask & (1 << station_index):
                continue
            cost = manhattan(station, circuit["start_building_mm"]) + manhattan(circuit["end_building_mm"], station)
            new_mask = mask | (1 << station_index)
            candidate = dp[mask] + cost
            if candidate < dp[new_mask] - 1e-9:
                dp[new_mask] = candidate
                parent[new_mask] = (mask, station_index, cost)
    mask = (1 << count) - 1
    assignment_indices = []
    for circuit_index in range(count - 1, -1, -1):
        previous, station_index, cost = parent[mask]
        assignment_indices.append((circuit_index, station_index, cost))
        mask = previous
    assignment_indices.reverse()

    assignments = []
    for circuit_index, station_index, link_length in assignment_indices:
        circuit = definitions[circuit_index]
        station = stations[station_index]
        lower = circuit["body_length_mm"] + link_length
        assignments.append({
            "circuit_id": circuit["circuit_id"],
            "source_body_ids": circuit["source_body_ids"],
            "candidate_station_index": station_index + 1,
            "candidate_station_plan_xy_building_mm": list(station),
            "candidate_supply_port_id": f"K2-P{station_index + 1:02d}-S",
            "candidate_return_port_id": f"K2-P{station_index + 1:02d}-R",
            "body_length_mm": circuit["body_length_mm"],
            "paired_manhattan_link_lower_bound_mm": link_length,
            "optimistic_total_lower_bound_mm": lower,
            "budget_to_78m_target_mm": TARGET_MM - lower,
            "within_40_80m_at_lower_bound": 40_000 <= lower <= 80_000,
            "assignment_status": "OPTIMIZATION_CANDIDATE_NOT_PHYSICAL_PORT_ASSIGNMENT",
            "fanout_geometry_published": False,
        })
    tightest = min(assignments, key=lambda item: item["budget_to_78m_target_mm"])

    model = {
        "schema": "homeaura-attic-k2-station-assignment-candidate-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_K2_STATION_ASSIGNMENT_089",
        "status": "TWELVE_CIRCUIT_TO_TWELVE_STATION_MINIMUM_TOTAL_MANHATTAN_ASSIGNMENT_PASS_REWORK_PRODUCT_AND_FANOUT",
        "source_records": [
            {"artifact_id": data["artifact_id"], "sha256": hashlib.sha256(raw).hexdigest().upper()}
            for raw, data in ((raw_085, body), (raw_086, budgets), (raw_088, lattice))
        ],
        "optimization_method": "DETERMINISTIC_BITMASK_DYNAMIC_PROGRAM_MINIMIZE_SUM_OF_PAIRED_SUPPLY_RETURN_MANHATTAN_LINK_LOWER_BOUNDS",
        "circuit_count": count,
        "candidate_station_count": len(stations),
        "assignment_count": len(assignments),
        "unique_assigned_station_count": len({item["candidate_station_index"] for item in assignments}),
        "total_paired_link_lower_bound_mm": dp[-1],
        "assignments": assignments,
        "all_optimistic_totals_within_40_80m": all(item["within_40_80m_at_lower_bound"] for item in assignments),
        "optimistic_total_range_mm": [
            min(item["optimistic_total_lower_bound_mm"] for item in assignments),
            max(item["optimistic_total_lower_bound_mm"] for item in assignments),
        ],
        "tightest_budget_to_78m_target": {"circuit_id": tightest["circuit_id"], "budget_mm": tightest["budget_to_78m_target_mm"]},
        "physical_K2_product_selected": False,
        "current_assigned_physical_port_count": 0,
        "candidate_assignment_is_installation_authority": False,
        "fanout_pipe_geometry_count": 0,
        "complete_route_count": 0,
        "result": "PASS_OPTIMIZED_STATION_OWNERSHIP_CANDIDATE_REWORK_SELECTED_PRODUCT_AND_FULL_24_LEG_FANOUT",
    }
    model["assignment_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_k2_station_assignment.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    canvas = Image.new("RGB", (1700, 1450), "#F4F8F8")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, canvas.width, 205), fill="#071A21")
    draw.text((34, 18), "D089 · КАНДИДАТ НАЗНАЧЕНИЯ 12 КОНТУРОВ СТАНЦИЯМ K2", font=font(23, True), fill="white")
    draw.text((34, 64), "Глобальный минимум суммарных манхэттенских подходов · каждая станция используется один раз", font=font(16, True), fill="#A7EEE7")
    lower = model["optimistic_total_range_mm"]
    draw.text((34, 105), f"Нижние оценки после назначения: {lower[0] / 1000:.1f}…{lower[1] / 1000:.1f} м", font=font(17), fill="#F3D58C")
    draw.text((34, 145), f'Самый малый запас до цели 78 м: {tightest["budget_to_78m_target_mm"] / 1000:.1f} м ({tightest["circuit_id"]})', font=font(16, True), fill="white")
    draw.text((34, 179), "КАНДИДАТ, НЕ ФИЗИЧЕСКОЕ НАЗНАЧЕНИЕ: изделие K2 и 24 подводки ещё не выбраны", font=font(14, True), fill="#FFB2B2")

    x0, y0 = 70, 250
    widths = [280, 160, 245, 220, 220, 380]
    headers = ["Контур", "Станция", "Подходы, м", "Нижняя оценка, м", "Запас до 78, м", "Статус"]
    x = x0
    for width, header in zip(widths, headers):
        draw.rectangle((x, y0, x + width, y0 + 62), fill="#DCEAEC", outline="#9BB3BA")
        draw.text((x + 12, y0 + 20), header, font=font(13, True), fill="#143842")
        x += width
    for row, item in enumerate(assignments, start=1):
        y = y0 + row * 62
        fill = "#FFFFFF" if row % 2 else "#EDF4F5"
        values = [
            item["circuit_id"], f'{item["candidate_station_index"]:02d}',
            f'{item["paired_manhattan_link_lower_bound_mm"] / 1000:.1f}',
            f'{item["optimistic_total_lower_bound_mm"] / 1000:.1f}',
            f'{item["budget_to_78m_target_mm"] / 1000:.1f}',
            "БЕРЕЧЬ ЗАПАС" if item["budget_to_78m_target_mm"] < 5000 else "КАНДИДАТ PASS",
        ]
        x = x0
        for index, (width, value) in enumerate(zip(widths, values)):
            draw.rectangle((x, y, x + width, y + 62), fill=fill, outline="#B7C8CD")
            colour = "#B00020" if index == 5 and item["budget_to_78m_target_mm"] < 5000 else "#143842"
            draw.text((x + 12, y + 19), value, font=font(13, index in (0, 5)), fill=colour)
            x += width
    bottom = y0 + (len(assignments) + 1) * 62
    draw.text((70, bottom + 50), "Назначение уменьшает только плановую нижнюю оценку. Разводка R80 и обходы увеличат длину.", font=font(15, True), fill="#143842")
    draw.text((70, bottom + 92), "A-C07 остаётся первым приоритетом трассировки; допустимый дополнительный путь — около 3,7 м до цели 78 м.", font=font(15, True), fill="#B00020")
    draw.text((70, bottom + 146), "Следующий шаг возможен только как параметрический 3D-фан-аут либо после выбора конкретного K2.", font=font(15, True), fill="#006A43")
    canvas.save(OUTPUT / "attic_k2_station_assignment_evidence.png")

    (OUTPUT / "report.md").write_text(
        "# D089 — кандидат назначения контуров станциям K2\n\n"
        "Двенадцать контуров назначены двенадцати параметрическим станциям решётки D088 детерминированной глобальной оптимизацией суммы кратчайших плановых подходов. Каждая станция использована ровно один раз. "
        f"Оптимистические нижние оценки лежат в диапазоне {lower[0] / 1000:.1f}–{lower[1] / 1000:.1f} м. Самый жёсткий бюджет остаётся у {tightest['circuit_id']}: {tightest['budget_to_78m_target_mm'] / 1000:.1f} м до практической цели 78 м. "
        "Это не физическое назначение портов: конкретное изделие, положения штуцеров, фан-аут R80, препятствия и полные маршруты не опубликованы.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"], "assignment_digest": model["assignment_digest"], "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT), "package": str(PACKAGE), "assignments": len(assignments),
        "total_link_lower_bound_mm": dp[-1], "range_mm": lower,
        "tightest": model["tightest_budget_to_78m_target"], "digest": model["assignment_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

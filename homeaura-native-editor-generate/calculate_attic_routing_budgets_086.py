from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_081 = BASE / "HA_TWO_FLOOR_ATTIC_WARDROBE_MANIFOLD_081" / "attic_wardrobe_manifold.json"
SOURCE_085 = BASE / "HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085" / "attic_body_geometry.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_ROUTING_BUDGETS_086"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_ROUTING_BUDGETS_086.zip"

DX_MM = 359.83333333356
DY_MM = 304.8
MAX_LENGTH_MM = 80_000
PRACTICAL_TARGET_MM = 78_000


def font(size: int, bold: bool = False):
    return ImageFont.truetype(
        str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size
    )


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def manhattan(a, b) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def registered_points(route: dict):
    return [(x - DX_MM, y - DY_MM) for x, y in route["body_points_mm"]]


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D086 is append-only")
    raw_081, architecture = read(SOURCE_081)
    raw_085, body_model = read(SOURCE_085)
    anchor = architecture["attic_manifold_reservation"]["routing_anchor_building_mm"]
    routes = {route["route_id"]: route for route in body_model["body_routes"]}
    circuits = []

    for route_id in [
        "A-C01", "A-C02", "A-C03", "A-C04", "A-C05", "A-C06", "A-C07",
        "A-C08", "A-C09", "A-C12", "A-C13",
    ]:
        route = routes[route_id]
        points = registered_points(route)
        supply = manhattan(anchor, points[0])
        returning = manhattan(points[-1], anchor)
        lower = route["body_length_mm"] + supply + returning
        circuits.append({
            "circuit_id": route_id,
            "source_body_ids": [route_id],
            "body_length_mm": route["body_length_mm"],
            "optimistic_supply_link_lower_bound_mm": supply,
            "optimistic_return_link_lower_bound_mm": returning,
            "optimistic_total_lower_bound_mm": lower,
            "detour_budget_to_80m_mm": MAX_LENGTH_MM - lower,
            "detour_budget_to_78m_target_mm": PRACTICAL_TARGET_MM - lower,
            "within_40_80m_at_lower_bound": 40_000 <= lower <= 80_000,
            "complete_route_geometry_published": False,
        })

    alternatives = []
    for order in [("A-C10", "A-C11"), ("A-C11", "A-C10")]:
        for reverse_first in (False, True):
            for reverse_second in (False, True):
                first = list(reversed(registered_points(routes[order[0]]))) if reverse_first else registered_points(routes[order[0]])
                second = list(reversed(registered_points(routes[order[1]]))) if reverse_second else registered_points(routes[order[1]])
                supply = manhattan(anchor, first[0])
                link = manhattan(first[-1], second[0])
                returning = manhattan(second[-1], anchor)
                total = routes[order[0]]["body_length_mm"] + routes[order[1]]["body_length_mm"] + supply + link + returning
                alternatives.append((total, order, reverse_first, reverse_second, supply, link, returning))
    total, order, reverse_first, reverse_second, supply, link, returning = min(alternatives, key=lambda item: (item[0], item[1], item[2], item[3]))
    circuits.append({
        "circuit_id": "A-C10_C11_SERIAL",
        "source_body_ids": list(order),
        "first_body_reversed": reverse_first,
        "second_body_reversed": reverse_second,
        "body_length_mm": routes["A-C10"]["body_length_mm"] + routes["A-C11"]["body_length_mm"],
        "optimistic_supply_link_lower_bound_mm": supply,
        "optimistic_inter_body_link_lower_bound_mm": link,
        "optimistic_return_link_lower_bound_mm": returning,
        "optimistic_total_lower_bound_mm": total,
        "detour_budget_to_80m_mm": MAX_LENGTH_MM - total,
        "detour_budget_to_78m_target_mm": PRACTICAL_TARGET_MM - total,
        "within_40_80m_at_lower_bound": 40_000 <= total <= 80_000,
        "complete_route_geometry_published": False,
    })
    circuits.sort(key=lambda item: item["circuit_id"])
    tightest = min(circuits, key=lambda item: item["detour_budget_to_78m_target_mm"])

    model = {
        "schema": "homeaura-attic-routing-budget-screening-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_ROUTING_BUDGETS_086",
        "status": "TWELVE_CIRCUIT_MANHATTAN_ROUTING_BUDGETS_PASS_REWORK_PORTS_OBSTACLE_ROUTES_AND_HYDRAULICS",
        "source_records": [
            {"artifact_id": architecture["artifact_id"], "sha256": hashlib.sha256(raw_081).hexdigest().upper()},
            {"artifact_id": body_model["artifact_id"], "sha256": hashlib.sha256(raw_085).hexdigest().upper()},
        ],
        "architecture": {
            "floor_1_manifold_id": "K1",
            "attic_manifold_id": "K2_ATTIC_WARDROBE",
            "primary_main_count": 2,
            "attic_circuit_count": 12,
            "attic_loop_leg_count": 24,
            "routing_anchor_building_mm": anchor,
        },
        "calculation_method": "MANHATTAN_DISTANCE_FROM_SINGLE_ABSTRACT_K2_ROUTING_ANCHOR_TO_BODY_ENDPOINTS_WITH_ONE_C10_C11_SERIAL_PAIR",
        "method_limitations": [
            "NO_OBSTACLE_DETOURS",
            "NO_SELECTED_PRODUCT_PORT_COORDINATES",
            "NO_PIPE_DIAMETER_OR_BEND_ARC_LENGTH_RECONCILIATION",
            "NO_VERTICAL_LOCAL_K2_STUBS",
            "NO_PRESSURE_DROP_OR_BALANCING",
        ],
        "maximum_circuit_length_mm": MAX_LENGTH_MM,
        "practical_screening_target_mm": PRACTICAL_TARGET_MM,
        "owner_minimum_bend_radius_mm": 80,
        "circuit_budgets": circuits,
        "all_optimistic_lower_bounds_within_40_80m": all(item["within_40_80m_at_lower_bound"] for item in circuits),
        "optimistic_lower_bound_range_mm": [
            min(item["optimistic_total_lower_bound_mm"] for item in circuits),
            max(item["optimistic_total_lower_bound_mm"] for item in circuits),
        ],
        "tightest_detour_budget_to_78m_target": {
            "circuit_id": tightest["circuit_id"],
            "budget_mm": tightest["detour_budget_to_78m_target_mm"],
        },
        "minimum_detour_budget_to_80m_mm": min(item["detour_budget_to_80m_mm"] for item in circuits),
        "minimum_detour_budget_to_78m_target_mm": min(item["detour_budget_to_78m_target_mm"] for item in circuits),
        "complete_route_count": 0,
        "K2_port_geometry_published": False,
        "hydraulic_acceptance": "NOT_EVALUATED_D083_D084_SCREENING_ONLY",
        "result": "PASS_ROUTING_BUDGET_SCREENING_REWORK_EXACT_PORT_FANOUT_COMPLETE_ROUTES_AND_HYDRAULICS",
    }
    model["budget_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_routing_budgets.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    canvas = Image.new("RGB", (1650, 1280), "#F4F8F8")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, canvas.width, 205), fill="#071A21")
    draw.text((32, 18), "D086 · ЗАПАСЫ ДЛИНЫ 12 КОНТУРОВ МАНСАРДЫ", font=font(24, True), fill="white")
    draw.text((32, 63), "K2 в гардеробной · C01 обновлён · C10+C11 объединены последовательно", font=font(17, True), fill="#A7EEE7")
    draw.text((32, 105), f'Нижние оценки: {model["optimistic_lower_bound_range_mm"][0] / 1000:.1f}…{model["optimistic_lower_bound_range_mm"][1] / 1000:.1f} м', font=font(17), fill="#F3D58C")
    draw.text((32, 145), f'Самый малый запас до практической цели 78 м: {model["minimum_detour_budget_to_78m_target_mm"] / 1000:.1f} м ({tightest["circuit_id"]})', font=font(16, True), fill="white")
    draw.text((32, 179), "НИ ОДИН МАРШРУТ ЕЩЁ НЕ ПРИНЯТ: порты, препятствия, R80 и гидравлика не включены", font=font(14, True), fill="#FFB2B2")

    x0, y0 = 55, 250
    widths = [245, 180, 230, 220, 220, 420]
    headers = ["Контур", "Тело, м", "Нижняя оценка, м", "Запас до 80, м", "Запас до 78, м", "Состояние"]
    x = x0
    for width, header in zip(widths, headers):
        draw.rectangle((x, y0, x + width, y0 + 62), fill="#DCEAEC", outline="#9BB3BA")
        draw.text((x + 12, y0 + 20), header, font=font(13, True), fill="#143842")
        x += width
    for row, item in enumerate(circuits, start=1):
        y = y0 + row * 62
        fill = "#FFFFFF" if row % 2 else "#EDF4F5"
        values = [
            item["circuit_id"],
            f'{item["body_length_mm"] / 1000:.1f}',
            f'{item["optimistic_total_lower_bound_mm"] / 1000:.1f}',
            f'{item["detour_budget_to_80m_mm"] / 1000:.1f}',
            f'{item["detour_budget_to_78m_target_mm"] / 1000:.1f}',
            "ОСТОРОЖНО" if item["detour_budget_to_78m_target_mm"] < 6000 else "СКРИНИНГ PASS",
        ]
        x = x0
        for index, (width, value) in enumerate(zip(widths, values)):
            draw.rectangle((x, y, x + width, y + 62), fill=fill, outline="#B7C8CD")
            color = "#B00020" if index == 5 and item["detour_budget_to_78m_target_mm"] < 6000 else "#143842"
            draw.text((x + 12, y + 19), value, font=font(13, index in (0, 5)), fill=color)
            x += width
    draw.text((55, 1030), "Как читать: нижняя оценка — это длина тела плюс кратчайшие осевые связи до одной условной точки K2.", font=font(15, True), fill="#143842")
    draw.text((55, 1066), "Реальная трасса будет длиннее из-за раздельных портов, обходов и монтажных вводов.", font=font(15), fill="#566B73")
    draw.text((55, 1102), "A-C07 требует особенно бережного маршрута; остальные контуры имеют больший резерв.", font=font(15, True), fill="#B00020")
    draw.text((55, 1160), "Следующий допуск: конкретный K2 → реальные порты → совместная трассировка 24 подводок → 40–80 м и гидравлика.", font=font(15, True), fill="#006A43")
    canvas.save(OUTPUT / "attic_routing_budgets_evidence.png")

    (OUTPUT / "report.md").write_text(
        "# D086 — скрининг запаса длины для 12 контуров мансарды\n\n"
        f"После перестройки C01 все двенадцать оптимистических нижних оценок лежат в диапазоне {model['optimistic_lower_bound_range_mm'][0] / 1000:.1f}–{model['optimistic_lower_bound_range_mm'][1] / 1000:.1f} м. "
        f"Наименьший запас до практической цели 78 м остаётся у {tightest['circuit_id']}: {tightest['detour_budget_to_78m_target_mm'] / 1000:.1f} м. "
        "Это не полные маршруты: расчёт использует одну абстрактную точку K2 и манхэттенские расстояния без препятствий, реальных портов, дуг R80, местных вертикальных вводов и гидравлики. "
        "Блок предназначен только для приоритета трассировщика: A-C07 строить первым и не расходовать его запас на необоснованные обходы.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "budget_digest": model["budget_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "range_mm": model["optimistic_lower_bound_range_mm"],
        "tightest": model["tightest_detour_budget_to_78m_target"],
        "digest": model["budget_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

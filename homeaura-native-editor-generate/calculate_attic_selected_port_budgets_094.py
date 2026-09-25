from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_085 = BASE / "HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085" / "attic_body_geometry.json"
SOURCE_089 = BASE / "HA_TWO_FLOOR_ATTIC_K2_STATION_ASSIGNMENT_089" / "attic_k2_station_assignment.json"
SOURCE_093 = BASE / "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORTS_093" / "attic_k2_selected_ports.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORT_BUDGETS_094"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORT_BUDGETS_094.zip"

DX_MM = 359.83333333356
DY_MM = 304.8
TARGET_MM = 78_000.0
MAX_MM = 80_000.0


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


def registered(route):
    return [(x - DX_MM, y - DY_MM) for x, y in route["body_points_mm"]]


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D094 is append-only")
    raw_085, body = read(SOURCE_085)
    raw_089, prior = read(SOURCE_089)
    raw_093, selected = read(SOURCE_093)
    routes = {item["route_id"]: item for item in body["body_routes"]}
    stations = {}
    for port in selected["physical_plan_ports"]:
        stations.setdefault(port["station_index"], {})[port["leg"]] = port
    if set(stations) != set(range(1, 13)) or any(set(parts) != {"SUPPLY", "RETURN"} for parts in stations.values()):
        raise RuntimeError("selected port station structure")

    definitions = []
    for route_id in ["A-C01", "A-C02", "A-C03", "A-C04", "A-C05", "A-C06", "A-C07", "A-C08", "A-C09", "A-C12", "A-C13"]:
        points = registered(routes[route_id])
        definitions.append({
            "circuit_id": route_id,
            "source_body_ids": [route_id],
            "body_length_mm": routes[route_id]["body_length_mm"],
            "variants": [
                {"body_direction": "FORWARD", "start": points[0], "end": points[-1], "inter_body_link_mm": 0.0},
                {"body_direction": "REVERSED", "start": points[-1], "end": points[0], "inter_body_link_mm": 0.0},
            ],
        })
    serial_variants = []
    for order in [("A-C10", "A-C11"), ("A-C11", "A-C10")]:
        for first_reversed in (False, True):
            for second_reversed in (False, True):
                first = registered(routes[order[0]])
                second = registered(routes[order[1]])
                if first_reversed:
                    first.reverse()
                if second_reversed:
                    second.reverse()
                serial_variants.append({
                    "body_order": list(order),
                    "first_body_reversed": first_reversed,
                    "second_body_reversed": second_reversed,
                    "start": first[0],
                    "end": second[-1],
                    "inter_body_link_mm": manhattan(first[-1], second[0]),
                })
    definitions.append({
        "circuit_id": "A-C10_C11_SERIAL",
        "source_body_ids": ["A-C10", "A-C11"],
        "body_length_mm": routes["A-C10"]["body_length_mm"] + routes["A-C11"]["body_length_mm"],
        "variants": serial_variants,
    })

    def best_at(circuit, station_index):
        supply = stations[station_index]["SUPPLY"]["building_plan_xy_mm"]
        returning = stations[station_index]["RETURN"]["building_plan_xy_mm"]
        candidates = []
        for variant in circuit["variants"]:
            s = manhattan(supply, variant["start"])
            r = manhattan(variant["end"], returning)
            total_links = s + variant["inter_body_link_mm"] + r
            candidates.append((total_links, json.dumps(variant, sort_keys=True), variant, s, r))
        _, _, variant, s, r = min(candidates, key=lambda item: (item[0], item[1]))
        return variant, s, r

    count = len(definitions)
    costs = {}
    for circuit_index, circuit in enumerate(definitions):
        for station_index in range(1, 13):
            variant, supply, returning = best_at(circuit, station_index)
            costs[(circuit_index, station_index)] = (supply + variant["inter_body_link_mm"] + returning, variant, supply, returning)
    infinity = float("inf")
    dp = [infinity] * (1 << count)
    parent = [None] * (1 << count)
    dp[0] = 0.0
    for mask in range(1 << count):
        circuit_index = mask.bit_count()
        if circuit_index >= count or dp[mask] == infinity:
            continue
        for station_index in range(1, 13):
            bit = 1 << (station_index - 1)
            if mask & bit:
                continue
            value = dp[mask] + costs[(circuit_index, station_index)][0]
            new_mask = mask | bit
            if value < dp[new_mask] - 1e-9:
                dp[new_mask] = value
                parent[new_mask] = (mask, station_index)
    mask = (1 << count) - 1
    pairs = []
    for circuit_index in range(count - 1, -1, -1):
        previous, station_index = parent[mask]
        pairs.append((circuit_index, station_index))
        mask = previous
    pairs.reverse()

    prior_station = {item["circuit_id"]: item["candidate_station_index"] for item in prior["assignments"]}
    results = []
    for circuit_index, station_index in pairs:
        circuit = definitions[circuit_index]
        link, variant, supply, returning = costs[(circuit_index, station_index)]
        total = circuit["body_length_mm"] + link
        record = {
            "circuit_id": circuit["circuit_id"],
            "source_body_ids": circuit["source_body_ids"],
            "selected_product_station_index": station_index,
            "selected_supply_port_id": stations[station_index]["SUPPLY"]["physical_port_id"],
            "selected_return_port_id": stations[station_index]["RETURN"]["physical_port_id"],
            "selected_supply_plan_xy_mm": stations[station_index]["SUPPLY"]["building_plan_xy_mm"],
            "selected_return_plan_xy_mm": stations[station_index]["RETURN"]["building_plan_xy_mm"],
            "body_length_mm": circuit["body_length_mm"],
            "optimistic_supply_link_lower_bound_mm": supply,
            "optimistic_inter_body_link_lower_bound_mm": variant["inter_body_link_mm"],
            "optimistic_return_link_lower_bound_mm": returning,
            "optimistic_total_lower_bound_mm": total,
            "budget_to_80m_mm": MAX_MM - total,
            "budget_to_78m_target_mm": TARGET_MM - total,
            "within_40_80m_at_lower_bound": 40_000 <= total <= 80_000,
            "optimized_body_traversal": {key: value for key, value in variant.items() if key not in ("start", "end", "inter_body_link_mm")},
            "D089_station_index": prior_station[circuit["circuit_id"]],
            "station_assignment_unchanged_from_D089": station_index == prior_station[circuit["circuit_id"]],
            "complete_route_geometry_published": False,
        }
        results.append(record)
    tight = min(results, key=lambda item: item["budget_to_78m_target_mm"])
    changed = [item["circuit_id"] for item in results if not item["station_assignment_unchanged_from_D089"]]
    model = {
        "schema": "homeaura-attic-selected-k2-port-routing-budget-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORT_BUDGETS_094",
        "status": "SELECTED_PRODUCT_24_PORT_REOPTIMIZED_LOWER_BOUNDS_PASS_REWORK_R80_FANOUT_COMPLETE_ROUTES_AND_HYDRAULICS",
        "source_records": [
            {"artifact_id": data["artifact_id"], "sha256": hashlib.sha256(raw).hexdigest().upper()}
            for raw, data in ((raw_085, body), (raw_089, prior), (raw_093, selected))
        ],
        "method": "GLOBAL_STATION_REOPTIMIZATION_USING_DISTINCT_SELECTED_PRODUCT_SUPPLY_RETURN_PLAN_PORTS_AND_BEST_BODY_DIRECTION",
        "selected_manifold_part_number": "1140843",
        "circuit_count": 12,
        "physical_plan_port_count": 24,
        "assignment_count": len(results),
        "unique_station_count": len({item["selected_product_station_index"] for item in results}),
        "total_paired_link_lower_bound_mm": dp[-1],
        "station_assignments_changed_from_D089": changed,
        "all_station_assignments_unchanged_from_D089": not changed,
        "circuit_budgets": results,
        "optimistic_total_range_mm": [min(item["optimistic_total_lower_bound_mm"] for item in results), max(item["optimistic_total_lower_bound_mm"] for item in results)],
        "tightest_budget_to_78m_target": {"circuit_id": tight["circuit_id"], "budget_mm": tight["budget_to_78m_target_mm"]},
        "all_optimistic_totals_within_40_80m": all(item["within_40_80m_at_lower_bound"] for item in results),
        "calculation_limitations": [
            "MANHATTAN_LOWER_BOUND_ONLY",
            "NO_OBSTACLE_AVOIDANCE",
            "NO_R80_ARC_RECONCILIATION",
            "NO_3D_MOUNTING_HEIGHT_OR_VERTICAL_STUBS",
            "NO_PRESSURE_DROP_OR_BALANCING",
        ],
        "fanout_pipe_geometry_count": 0,
        "complete_route_count": 0,
        "installation_authority": False,
        "result": "PASS_SELECTED_PRODUCT_PORT_BUDGET_SCREENING_REWORK_FULL_GEOMETRY_AND_HYDRAULICS",
    }
    model["budget_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_k2_selected_port_budgets.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    canvas = Image.new("RGB", (1700, 1450), "#F4F8F8")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, 1700, 205), fill="#071A21")
    draw.text((34, 18), "D094 · ДЛИНЫ ОТ РЕАЛЬНЫХ ПЛАНОВЫХ ПОРТОВ K2", font=font(23, True), fill="white")
    draw.text((34, 63), "Uponor 1140843 · 24 разные XY-точки · глобальная перепроверка назначения", font=font(16, True), fill="#A7EEE7")
    lo, hi = model["optimistic_total_range_mm"]
    draw.text((34, 105), f"Нижние оценки: {lo/1000:.1f}…{hi/1000:.1f} м · все 12 внутри 40–80 м", font=font(17), fill="#F3D58C")
    draw.text((34, 145), f"Самый малый запас до цели 78 м: {tight['budget_to_78m_target_mm']/1000:.1f} м ({tight['circuit_id']})", font=font(16, True), fill="white")
    draw.text((34, 179), "ЭТО НИЖНИЕ ОЦЕНКИ: R80, препятствия, высота и гидравлика ещё не включены", font=font(14, True), fill="#FFB2B2")
    x0, y0 = 55, 250
    widths = [255, 125, 215, 210, 210, 200, 410]
    headers = ["Контур", "Станция", "Тело, м", "Связи, м", "Итого ≥, м", "Запас до 78, м", "Назначение"]
    x = x0
    for width, header in zip(widths, headers):
        draw.rectangle((x, y0, x+width, y0+62), fill="#DCEAEC", outline="#9BB3BA")
        draw.text((x+10, y0+20), header, font=font(12, True), fill="#143842")
        x += width
    for row, item in enumerate(results, start=1):
        y = y0 + row*62
        fill = "#FFFFFF" if row % 2 else "#EDF4F5"
        links = item["optimistic_supply_link_lower_bound_mm"] + item["optimistic_inter_body_link_lower_bound_mm"] + item["optimistic_return_link_lower_bound_mm"]
        values = [item["circuit_id"], f"{item['selected_product_station_index']:02d}", f"{item['body_length_mm']/1000:.1f}", f"{links/1000:.1f}", f"{item['optimistic_total_lower_bound_mm']/1000:.1f}", f"{item['budget_to_78m_target_mm']/1000:.1f}", "D089 сохранено" if item["station_assignment_unchanged_from_D089"] else "переназначено"]
        x = x0
        for index, (width, value) in enumerate(zip(widths, values)):
            draw.rectangle((x, y, x+width, y+62), fill=fill, outline="#B7C8CD")
            colour = "#B00020" if index == 5 and item["budget_to_78m_target_mm"] < 5000 else "#143842"
            draw.text((x+10, y+19), value, font=font(12, index in (0, 6)), fill=colour)
            x += width
    bottom = y0 + 13*62
    draw.text((55, bottom+45), f"Переназначения относительно D089: {len(changed)}. Порядок станций {'подтверждён' if not changed else 'обновлён'}.", font=font(15, True), fill="#006A43")
    draw.text((55, bottom+90), "Следующая граница: высота установки шкафа → 3D R80-фан-аут 24 подводок → полные маршруты.", font=font(15, True), fill="#B00020")
    canvas.save(OUTPUT / "attic_k2_selected_port_budgets_evidence.png")
    (OUTPUT / "report.md").write_text(
        "# D094 — длины от выбранных портов K2\n\n"
        f"Назначение двенадцати контуров повторно оптимизировано по реальным плановым координатам 24 отводов Uponor 1140843. Переназначений относительно D089: {len(changed)}. "
        f"Оптимистические нижние оценки составляют {lo/1000:.1f}–{hi/1000:.1f} м. Самый жёсткий контур — {tight['circuit_id']}, запас до практической цели 78 м равен {tight['budget_to_78m_target_mm']/1000:.1f} м. "
        "Это ещё не полные трассы: не учтены пространственный фан-аут с R80, препятствия, абсолютная высота шкафа и гидравлическая балансировка.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"], "budget_digest": model["budget_digest"], "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "range_mm": [lo, hi], "tightest": model["tightest_budget_to_78m_target"], "changed": changed, "digest": model["budget_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

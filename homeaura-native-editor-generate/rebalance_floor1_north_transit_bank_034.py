from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_NORTH_HALL_029"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_NORTH_TRANSIT_BANK_034"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_NORTH_TRANSIT_BANK_034.zip"
PX = 8.503937
MM_PER_PDF_POINT = 35.27777777777778
TREAD_GRID_BOX = (113, 98, 127, 108)
REASSIGNMENT = {
    "F1-C01": {"supply_y": 57, "return_y": 56},
    "F1-C02": {"supply_y": 59, "return_y": 58},
    "F1-C03": {"supply_y": 61, "return_y": 60},
    "F1-C04": {"supply_y": 63, "return_y": 62},
}

spec = importlib.util.spec_from_file_location(
    "d014_core_for_d034",
    ROOT / "homeaura-native-editor-generate" / "build_local_counterflow_coverage_014.py",
)
core = importlib.util.module_from_spec(spec)
sys.modules["d014_core_for_d034"] = core
assert spec.loader is not None
spec.loader.exec_module(core)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def to_px(point):
    return round(point[0] * PX), round(point[1] * PX)


def length(points) -> int:
    return sum((abs(a[0] - b[0]) + abs(a[1] - b[1])) * 100 for a, b in zip(points, points[1:]))


def segment_hits_box(a, b, bounds) -> bool:
    x0, y0, x1, y1 = bounds
    if a[0] == b[0]:
        return x0 <= a[0] <= x1 and max(min(a[1], b[1]), y0) <= min(max(a[1], b[1]), y1)
    return y0 <= a[1] <= y1 and max(min(a[0], b[0]), x0) <= min(max(a[0], b[0]), x1)


def hall_allowed_polygon():
    source = [(272.64, 153.24), (357.96, 153.24), (357.96, 464.40), (306.60, 464.40), (306.60, 402.96), (272.64, 402.96)]
    polygon = Polygon([(x * MM_PER_PDF_POINT, y * MM_PER_PDF_POINT) for x, y in source])
    physical_treads = box(*[value * MM_PER_PDF_POINT for value in (321.36, 278.76, 357.96, 304.80)])
    return polygon.difference(physical_treads)


def coverage(model):
    allowed = hall_allowed_polygon()
    served = allowed.intersection(unary_union([
        LineString(route["ordered_points_mm"]).buffer(100, cap_style=1, join_style=1, quad_segs=16)
        for route in model["routes"]
    ]))
    unresolved = allowed.difference(served)
    return {
        "allowed_area_m2": round(allowed.area / 1_000_000, 6),
        "served_area_m2": round(served.area / 1_000_000, 6),
        "unresolved_area_m2": round(unresolved.area / 1_000_000, 6),
        "served_ratio_percent": round(100 * served.area / allowed.area, 4),
        "distance_model": "TRUE_ROUND_EUCLIDEAN_BUFFER_100MM",
        "full_coverage_claimed": False,
    }


def draw(model, target, pipes_only: bool):
    image = Image.new("RGB", (1785, 1750), "#F7FAFA") if pipes_only else Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    if pipes_only:
        for x in range(0, image.width, round(PX)):
            canvas.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, round(PX)):
            canvas.line((0, y, image.width, y), fill="#D8E2E2")
    canvas.rectangle((0, 0, image.width, 145), fill="#071A21")
    coverage_data = model["hall_coverage_diagnostic"]
    canvas.text((28, 12), "D034 · СЕВЕРНЫЙ ТРАНЗИТНЫЙ ПУЧОК · 12 КОНТУРОВ", font=font(25, True), fill="white")
    canvas.text((28, 55), "C01–C04: 8 отдельных линий y=56…63 · пересечений 0 · тела улиток не изменены", font=font(16), fill="#A7EEE7")
    canvas.text((28, 86), f'Г-образный холл: {coverage_data["served_area_m2"]:.2f}/{coverage_data["allowed_area_m2"]:.2f} м² ({coverage_data["served_ratio_percent"]:.1f}%) · C07 НЕ ДОБАВЛЯТЬ', font=font(15), fill="#F3D58C")
    canvas.text((28, 115), "Статус покрытия REWORK · один логический K1 · физический коллектор/гидравлика не рассчитаны", font=font(13), fill="#E8F0F2")

    x0, y0, x1, y1 = model["collector_contract"]["station_envelope_bbox_grid"]
    if pipes_only:
        canvas.rectangle((*to_px((x0, y0)), *to_px((x1, y1))), outline="#006D67", width=3)
        canvas.text(to_px((x0 + 1, y0 + 2)), "K1 LOGICAL", font=font(11, True), fill="#006D67")
    tx0, ty0, tx1, ty1 = TREAD_GRID_BOX
    canvas.rectangle((*to_px((tx0, ty0)), *to_px((tx1, ty1))), fill="#F7CACA", outline="#B00020", width=3)
    canvas.text(to_px((tx0, ty0 - 2)), "3 СТУПЕНИ", font=font(11, True), fill="#B00020")

    colours = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC", "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93"]
    for route, colour in zip(model["routes"], colours):
        points = [to_px(point) for point in route["ordered_points_grid"]]
        canvas.line(points, fill="white", width=9, joint="curve")
        canvas.line(points, fill=colour, width=4, joint="curve")
        anchor = to_px(route["heating_body_points_grid"][len(route["heating_body_points_grid"]) // 2])
        canvas.text((anchor[0] + 3, anchor[1] + 3), f'{route["route_id"]} {route["total_length_mm"] / 1000:.1f} м', font=font(10, True), fill=colour, stroke_width=2, stroke_fill="white")

    for route_id in REASSIGNMENT:
        route = next(item for item in model["routes"] if item["route_id"] == route_id)
        for point in (route["supply_port_grid"], route["return_port_grid"]):
            x, y = to_px(point)
            canvas.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#FFFFFF", outline="#071A21", width=2)
    image.save(target, quality=96)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D034 is append-only")
    source_bytes = (SOURCE / "canonical_geometry.json").read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    model = json.loads(source_bytes.decode("utf-8"))
    routes = {route["route_id"]: route for route in model["routes"]}
    source_body_digests = {route_id: routes[route_id]["heating_body_digest"] for route_id in REASSIGNMENT}

    for route_id, assignment in REASSIGNMENT.items():
        route = routes[route_id]
        supply = [list(point) for point in route["supply_transit_points_grid"]]
        returned = [list(point) for point in route["return_transit_points_grid"]]
        body = [list(point) for point in route["heating_body_points_grid"]]
        supply[0][1] = assignment["supply_y"]
        supply[1][1] = assignment["supply_y"]
        returned[-1][1] = assignment["return_y"]
        returned[-2][1] = assignment["return_y"]
        points = [*supply, *body[1:], *returned[1:]]
        route.update(
            supply_port_grid=supply[0],
            return_port_grid=returned[-1],
            supply_port_mm=[[value * 100 for value in supply[0]][0], [value * 100 for value in supply[0]][1]],
            return_port_mm=[[value * 100 for value in returned[-1]][0], [value * 100 for value in returned[-1]][1]],
            supply_transit_points_grid=supply,
            return_transit_points_grid=returned,
            ordered_points_grid=points,
            ordered_points_mm=[[value * 100 for value in point] for point in points],
            supply_transit_length_mm=length(supply),
            return_transit_length_mm=length(returned),
            total_length_mm=length(points),
            route_validation=core.topology([tuple(point) for point in points]),
            transit_rebalance={
                "change_kind": "WEST_K1_GATE_PAIR_MOVED_NORTH",
                "purpose": "SERVE_NORTH_HALL_STRIP_WITH_EXISTING_DISTINCT_TRANSITS",
                "supply_gate_grid": supply[0],
                "return_gate_grid": returned[-1],
                "heating_body_unchanged": True,
            },
        )
        route["geometry_digest"] = digest(route["ordered_points_mm"])

    contacts = core.inter_contacts(model["routes"])
    tread_hits = sum(segment_hits_box(a, b, TREAD_GRID_BOX) for route in model["routes"] for a, b in zip(route["ordered_points_grid"], route["ordered_points_grid"][1:]))
    if contacts or tread_hits or any(route["route_validation"]["result"] != "PASS" for route in model["routes"]):
        raise RuntimeError({"contacts": contacts, "tread_hits": tread_hits})
    if any(routes[route_id]["heating_body_digest"] != source_body_digests[route_id] for route_id in REASSIGNMENT):
        raise RuntimeError("heating body digest changed")
    if not all(40000 <= route["total_length_mm"] <= 80000 for route in model["routes"]):
        raise RuntimeError("length range")

    contract = model["collector_contract"]
    for mapping_item in contract["connection_to_gate_mapping"]:
        if mapping_item["route_id"] not in REASSIGNMENT:
            continue
        assignment = REASSIGNMENT[mapping_item["route_id"]]
        y = assignment["supply_y"] if mapping_item["leg"] == "SUPPLY" else assignment["return_y"]
        mapping_item["port_point_grid"] = [129, y]
        mapping_item["exit_gate_point_grid"] = [129, y]
    contract["west_wall_face_gate_bbox_grid"] = [129, 56, 129, 81]
    contract["west_wall_face_gates_grid"] = [[129, y] for y in [56, 57, 58, 59, 60, 61, 62, 63, 72, 73, 74, 77, 80, 81]]
    contract["north_transit_bank_reassignment"] = {
        "routes": REASSIGNMENT,
        "pair_order": ["F1-C01", "F1-C02", "F1-C03", "F1-C04"],
        "distinct_gate_count": 8,
        "lane_spacing_mm": 100,
        "shared_segments": False,
        "lane_swaps": False,
    }
    contract.pop("contract_digest", None)
    contract["contract_digest"] = digest(contract)

    before = coverage(source)
    after = coverage(model)
    model.update(
        artifact_id="HA_TWO_FLOOR_FLOOR1_NORTH_TRANSIT_BANK_034",
        status="TWELVE_ROUTE_GEOMETRY_PASS_NORTH_TRANSIT_REBALANCED_REWORK_EXACT_COVERAGE",
        derived_from_artifact_id=source["artifact_id"],
        derived_from_geometry_digest=source["geometry_digest"],
        hall_coverage_diagnostic={
            **after,
            "source_before_served_area_m2": before["served_area_m2"],
            "source_before_ratio_percent": before["served_ratio_percent"],
            "served_area_gain_m2": round(after["served_area_m2"] - before["served_area_m2"], 6),
            "ratio_gain_percentage_points": round(after["served_ratio_percent"] - before["served_ratio_percent"], 4),
            "threshold_ownership": "NOT_EVALUATED_FLATTENED_PDF_AMBIGUOUS",
            "exterior_wall_100mm_band_evaluated": False,
            "C07_decision": "DO_NOT_ADD",
            "result": "REWORK_REMAINING_FRAGMENTED_HALL_GAPS",
        },
        whole_floor_completion=False,
        whole_house_completion=False,
    )
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)

    validation = {
        "artifact_id": model["artifact_id"],
        "route_count": len(model["routes"]),
        "source_geometry_digest": source["geometry_digest"],
        "changed_route_ids": list(REASSIGNMENT),
        "unchanged_heating_body_ids": list(REASSIGNMENT),
        "unchanged_heating_body_digests": source_body_digests,
        "global_inter_route_contact_count": len(contacts),
        "first_three_tread_hit_count": tread_hits,
        "all_lengths_40_80m": True,
        "lengths_mm": {route["route_id"]: route["total_length_mm"] for route in model["routes"]},
        "new_gate_mapping": REASSIGNMENT,
        "unique_new_gate_count": len({value for assignment in REASSIGNMENT.values() for value in assignment.values()}),
        "hall_coverage_before": before,
        "hall_coverage_after": after,
        "coverage_result": model["hall_coverage_diagnostic"]["result"],
        "result": "GEOMETRY_PASS_REWORK_REMAINING_COVERAGE",
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "k1_twelve_route_gate_contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, OUTPUT / "floor_1_north_transit_overlay.png", False)
    draw(model, OUTPUT / "floor_1_north_transit_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D034 — северный транзитный пучок\n\n"
        f"Восемь отдельных подающих/обратных линий C01–C04 переставлены из y=64…71 на свободные линии y=56…63 без смены порядка и без общей трубы. Их регулярные тела сохранены побайтно. "
        f"Длины C01–C04 теперь {routes['F1-C01']['total_length_mm']/1000:.1f}, {routes['F1-C02']['total_length_mm']/1000:.1f}, {routes['F1-C03']['total_length_mm']/1000:.1f}, {routes['F1-C04']['total_length_mm']/1000:.1f} м. "
        f"Пересечений, касаний и попаданий в первые три ступени нет. По черновому Г-образному полигону круглое 100-мм покрытие выросло с {before['served_ratio_percent']:.1f}% до {after['served_ratio_percent']:.1f}%, остаток {after['unresolved_area_m2']:.2f} м². "
        "C07 не добавляется; покрытие остаётся REWORK до принятия дверных порогов и устранения внутренних разрывов существующими маршрутами.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({"artifact_id": model["artifact_id"], "geometry_digest": model["geometry_digest"], "append_only": True, "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files]}, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "lengths": validation["lengths_mm"], "contacts": len(contacts), "coverage_before": before, "coverage_after": after, "digest": model["geometry_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

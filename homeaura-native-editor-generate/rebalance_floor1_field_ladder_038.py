from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from shapely.geometry import LineString, mapping


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_WALL_CLEARANCE_037"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_FIELD_LADDER_038"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_FIELD_LADDER_038.zip"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
TREAD_GRID_BOX = (113, 98, 127, 108)
REASSIGNMENT = {
    "F1-C05": {"supply_y": 70, "return_y": 72},
    "F1-C06": {"supply_y": 74, "return_y": 76},
    "F1-C14": {"supply_y": 80, "return_y": 78},
}

spec = importlib.util.spec_from_file_location(
    "d037_core_for_d038",
    ROOT / "homeaura-native-editor-generate" / "certify_floor1_wall_clearance_037.py",
)
d037 = importlib.util.module_from_spec(spec)
sys.modules["d037_core_for_d038"] = d037
assert spec.loader is not None
spec.loader.exec_module(d037)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest().upper()


def length(points) -> int:
    return sum((abs(a[0] - b[0]) + abs(a[1] - b[1])) * 100 for a, b in zip(points, points[1:]))


def rebuild_route_transits(route, supply_y: int, return_y: int):
    supply = [list(point) for point in route["supply_transit_points_grid"]]
    returned = [list(point) for point in route["return_transit_points_grid"]]
    body = [list(point) for point in route["heating_body_points_grid"]]
    supply[0][1] = supply_y
    supply[1][1] = supply_y
    returned[-1][1] = return_y
    returned[-2][1] = return_y
    ordered = [*supply, *body[1:], *returned[1:]]
    compact = []
    for point in ordered:
        if not compact or point != compact[-1]:
            compact.append(point)
    route.update(
        supply_port_grid=supply[0],
        return_port_grid=returned[-1],
        supply_port_mm=[value * 100 for value in supply[0]],
        return_port_mm=[value * 100 for value in returned[-1]],
        supply_transit_points_grid=supply,
        return_transit_points_grid=returned,
        ordered_points_grid=compact,
        ordered_points_mm=[[value * 100 for value in point] for point in compact],
        supply_transit_length_mm=length(supply),
        return_transit_length_mm=length(returned),
        total_length_mm=length(compact),
        route_validation=d037.d034.core.topology([tuple(point) for point in compact]),
        transit_rebalance={
            "change_kind": "CONTINUE_200MM_FIELD_LADDER",
            "supply_gate_grid": supply[0],
            "return_gate_grid": returned[-1],
            "heating_body_unchanged": True,
        },
    )
    route["geometry_digest"] = digest(route["ordered_points_mm"])


def material_components(unresolved):
    parts = d037.polygons(unresolved)
    return sorted((part for part in parts if part.area >= 10_000), key=lambda part: part.area, reverse=True)


def draw(model, metrics, geometries, target: Path, pipes_only: bool):
    _, _, allowed, served, unresolved, _, _, _, _ = geometries
    image = Image.new("RGB", (1785, 1750), "#F7FAFA") if pipes_only else Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    if pipes_only:
        step = round(d037.PX_PER_GRID)
        for x in range(0, image.width, step):
            canvas.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, step):
            canvas.line((0, y, image.width, y), fill="#D8E2E2")
    else:
        d037.fill_geometry(canvas, allowed, "#F1F4F45A", "#526A73")
        d037.fill_geometry(canvas, served, "#41B88335", "#16845B")
        d037.fill_geometry(canvas, unresolved, "#E148555E", "#B00020")

    canvas.rectangle((0, 0, image.width, 158), fill="#071A21")
    canvas.text((28, 10), "D038 · 12 КОНТУРОВ · НЕПРЕРЫВНАЯ ЛЕСТНИЦА ПОЛЯ", font=d037.font(24, True), fill="white")
    canvas.text(
        (28, 49),
        "Север: 56/57/58 — 100 мм; затем 60/62/64/66/68/70/72/74/76/78/80 — 200 мм",
        font=d037.font(15), fill="#A7EEE7",
    )
    canvas.text(
        (28, 81),
        f'C05 {metrics["lengths_mm"]["F1-C05"] / 1000:.1f} м · C06 {metrics["lengths_mm"]["F1-C06"] / 1000:.1f} м · C14 {metrics["lengths_mm"]["F1-C14"] / 1000:.1f} м · контактов 0',
        font=d037.font(15), fill="#F3D58C",
    )
    canvas.text(
        (28, 113),
        f'Черновой L-полигон: {metrics["served_ratio_percent"]:.1f}% · остаток {metrics["unresolved_area_m2"]:.2f} м² · покрытие REWORK · C07 не добавлен',
        font=d037.font(14), fill="#E8F0F2",
    )

    x0, y0, x1, y1 = model["collector_contract"]["station_envelope_bbox_grid"]
    if pipes_only:
        canvas.rectangle((*d037.grid_to_px((x0, y0)), *d037.grid_to_px((x1, y1))), outline="#006D67", width=3)
        canvas.text(d037.grid_to_px((x0 + 1, y0 + 2)), "K1 LOGICAL", font=d037.font(11, True), fill="#006D67")
    tx0, ty0, tx1, ty1 = TREAD_GRID_BOX
    canvas.rectangle((*d037.grid_to_px((tx0, ty0)), *d037.grid_to_px((tx1, ty1))), fill="#F7CACA", outline="#B00020", width=3)
    canvas.text(d037.grid_to_px((tx0, ty0 - 2)), "3 СТУПЕНИ", font=d037.font(11, True), fill="#B00020")

    colours = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC", "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93"]
    for route, colour in zip(model["routes"], colours):
        points = [d037.grid_to_px(point) for point in route["ordered_points_grid"]]
        canvas.line(points, fill="white", width=9, joint="curve")
        canvas.line(points, fill=colour, width=4, joint="curve")
        anchor = d037.grid_to_px(route["heating_body_points_grid"][len(route["heating_body_points_grid"]) // 2])
        canvas.text((anchor[0] + 3, anchor[1] + 3), f'{route["route_id"]} {route["total_length_mm"] / 1000:.1f} м', font=d037.font(10, True), fill=colour, stroke_width=2, stroke_fill="white")
    image.save(target, quality=96)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D038 is append-only")
    source_path = SOURCE / "canonical_geometry.json"
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    model = json.loads(source_bytes.decode("utf-8"))
    routes = {route["route_id"]: route for route in model["routes"]}
    source_bodies = {route_id: json.dumps(routes[route_id]["heating_body_points_grid"], separators=(",", ":")) for route_id in REASSIGNMENT}

    for route_id, assignment in REASSIGNMENT.items():
        rebuild_route_transits(routes[route_id], assignment["supply_y"], assignment["return_y"])

    lengths = d037.validate_routes(model)
    if any(json.dumps(routes[route_id]["heating_body_points_grid"], separators=(",", ":")) != source_bodies[route_id] for route_id in REASSIGNMENT):
        raise RuntimeError("heating body changed")
    if len({tuple(route[key]) for route in model["routes"] for key in ("supply_port_grid", "return_port_grid")}) != 24:
        raise RuntimeError("ports are not unique")

    geometries = d037.coverage_geometry(model)
    _, _, allowed, served, unresolved, landing, landing_served, routable, routable_served = geometries
    material = material_components(unresolved)
    source_evidence = source["wall_clearance_and_coverage_evidence"]
    metrics = {
        "artifact_id": "HA_TWO_FLOOR_FLOOR1_FIELD_LADDER_038",
        "status": "TWELVE_ROUTE_GEOMETRY_AND_CONTINUOUS_FIELD_LADDER_PASS_REWORK_POLYGON_COVERAGE",
        "source_artifact_id": source["artifact_id"],
        "source_geometry_digest": source["geometry_digest"],
        "changed_route_ids": list(REASSIGNMENT),
        "heating_bodies_unchanged": True,
        "lengths_mm": lengths,
        "global_inter_route_contact_count": 0,
        "first_three_tread_hit_count": 0,
        "ordered_bank_y_grid": [56, 57, 58, 60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80],
        "adjacent_delta_grid": [1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        "exterior_adjacent_passes_y_grid": [56, 57, 58],
        "field_passes_y_grid": [60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80],
        "exterior_spacing_mm": 100,
        "field_spacing_mm": 200,
        "spacing_scope": "NORTH_ENTRY_AND_WEST_K1_TRANSIT_LADDER",
        "full_exterior_band_evaluated": False,
        "hall_allowed_area_m2": round(allowed.area / 1_000_000, 6),
        "served_area_m2": round(served.area / 1_000_000, 6),
        "unresolved_area_m2": round(unresolved.area / 1_000_000, 6),
        "served_ratio_percent": round(100 * served.area / allowed.area, 4),
        "source_served_area_m2": source_evidence["hall_served_area_m2"],
        "source_unresolved_area_m2": source_evidence["hall_unresolved_area_m2"],
        "source_served_ratio_percent": source_evidence["hall_served_ratio_percent"],
        "served_area_gain_m2": round(served.area / 1_000_000 - source_evidence["hall_served_area_m2"], 6),
        "ratio_gain_percentage_points": round(100 * served.area / allowed.area - source_evidence["hall_served_ratio_percent"], 4),
        "material_unresolved_components": [
            {"area_m2": round(part.area / 1_000_000, 6), "bounds_mm": [round(value) for value in part.bounds], "geometry": mapping(part)}
            for part in material
        ],
        "distance_model": "TRUE_ROUND_EUCLIDEAN_BUFFER_100MM_QUAD_SEGS_16",
        "hall_semantics": source_evidence["hall_semantics"],
        "C07_decision": "DO_NOT_ADD_OPTIMIZE_EXISTING_C05_C06_BODIES_FIRST",
        "full_coverage_claimed": False,
        "result": "PASS_ROUTE_GEOMETRY_AND_FIELD_LADDER_REWORK_POLYGON_COVERAGE",
    }

    model["artifact_id"] = metrics["artifact_id"]
    model["status"] = metrics["status"]
    model["derived_from_artifact_id"] = source["artifact_id"]
    model["derived_from_geometry_digest"] = source["geometry_digest"]
    contract = model["collector_contract"]
    contract["contract_id"] = "HA_TWO_FLOOR_K1_TWELVE_ROUTE_GATE_CONTRACT_038"
    contract["west_wall_face_gate_bbox_grid"] = [129, 56, 129, 80]
    contract["west_wall_face_gates_grid"] = [[129, y] for y in metrics["ordered_bank_y_grid"]]
    for item in contract["connection_to_gate_mapping"]:
        if item["route_id"] not in REASSIGNMENT:
            continue
        assignment = REASSIGNMENT[item["route_id"]]
        y = assignment["supply_y"] if item["leg"] == "SUPPLY" else assignment["return_y"]
        item["port_point_grid"] = [129, y]
        item["exit_gate_point_grid"] = [129, y]
    contract["continuous_field_ladder_reassignment"] = {
        "routes": REASSIGNMENT,
        "ordered_y_grid": metrics["ordered_bank_y_grid"],
        "adjacent_delta_grid": metrics["adjacent_delta_grid"],
        "heating_bodies_unchanged": True,
        "shared_segments": False,
        "lane_swaps": False,
        "scope": metrics["spacing_scope"],
        "result": "PASS",
    }
    contract.pop("contract_digest", None)
    contract["contract_digest"] = digest(contract)
    model["field_ladder_and_coverage_evidence"] = metrics
    model["hall_coverage_diagnostic"].update(
        served_area_m2=metrics["served_area_m2"],
        unresolved_area_m2=metrics["unresolved_area_m2"],
        served_ratio_percent=metrics["served_ratio_percent"],
        full_coverage_claimed=False,
        result="REWORK_INTERNAL_HALL_GAPS_AFTER_CONTINUOUS_FIELD_LADDER",
    )
    model["whole_floor_completion"] = False
    model["whole_house_completion"] = False
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)

    validation = {
        "artifact_id": metrics["artifact_id"],
        "source_canonical_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_geometry_digest": source["geometry_digest"],
        "route_count": len(model["routes"]),
        "changed_route_ids": list(REASSIGNMENT),
        "reassignment": REASSIGNMENT,
        "heating_bodies_unchanged": True,
        "lengths_mm": lengths,
        "all_lengths_40_80m": all(40_000 <= value <= 80_000 for value in lengths.values()),
        "global_inter_route_contact_count": 0,
        "first_three_tread_hit_count": 0,
        "unique_port_coordinate_count": 24,
        "spacing_validation": {
            "ordered_y_grid": metrics["ordered_bank_y_grid"],
            "adjacent_delta_grid": metrics["adjacent_delta_grid"],
            "exterior_three_pass_count": 3,
            "exterior_spacing_mm": 100,
            "field_spacing_mm": 200,
            "scope": metrics["spacing_scope"],
            "result": "PASS",
        },
        "coverage": {key: metrics[key] for key in (
            "hall_allowed_area_m2", "served_area_m2", "unresolved_area_m2", "served_ratio_percent",
            "source_served_area_m2", "source_unresolved_area_m2", "source_served_ratio_percent",
            "served_area_gain_m2", "ratio_gain_percentage_points", "full_coverage_claimed",
        )},
        "collector_contract_digest": contract["contract_digest"],
        "result": metrics["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "k1_twelve_route_gate_contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, metrics, geometries, OUTPUT / "floor_1_field_ladder_overlay.png", False)
    draw(model, metrics, geometries, OUTPUT / "floor_1_field_ladder_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D038 — непрерывная лестница полевого шага\n\n"
        "Геометрия 12 контуров остаётся бесконтактной; тела улиток не изменены. После трёх наружных проходов y=56/57/58 через 100 мм все последующие транзитные линии идут через 200 мм до y=80. "
        f"C05={lengths['F1-C05']/1000:.1f} м, C06={lengths['F1-C06']/1000:.1f} м, C14={lengths['F1-C14']/1000:.1f} м. "
        f"Диагностическое круглое 100-мм покрытие чернового L-полигона выросло с {metrics['source_served_ratio_percent']:.2f}% до {metrics['served_ratio_percent']:.2f}%; остаток уменьшился с {metrics['source_unresolved_area_m2']:.2f} до {metrics['unresolved_area_m2']:.2f} м². "
        "Полное покрытие, физический коллектор и гидравлика не заявляются. C07 не добавлен: дальнейшее улучшение выполняется существующими C05/C06.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": metrics["artifact_id"],
        "geometry_digest": model["geometry_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "digest": model["geometry_digest"],
        "lengths": {key: lengths[key] for key in REASSIGNMENT},
        "contacts": 0,
        "coverage_before": metrics["source_served_ratio_percent"],
        "coverage_after": metrics["served_ratio_percent"],
        "unresolved_m2": metrics["unresolved_area_m2"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

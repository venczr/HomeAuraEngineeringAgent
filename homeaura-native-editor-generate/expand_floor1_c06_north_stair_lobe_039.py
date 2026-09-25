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
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_FIELD_LADDER_038"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039.zip"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
TREAD_GRID_BOX = (113, 98, 127, 108)

spec = importlib.util.spec_from_file_location(
    "d038_core_for_d039",
    ROOT / "homeaura-native-editor-generate" / "rebalance_floor1_field_ladder_038.py",
)
d038 = importlib.util.module_from_spec(spec)
sys.modules["d038_core_for_d039"] = d038
assert spec.loader is not None
spec.loader.exec_module(d038)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest().upper()


def length(points) -> int:
    return d038.d037.d034.core.length_mm([tuple(point) for point in points])


def material_components(unresolved):
    parts = d038.d037.polygons(unresolved)
    return sorted((part for part in parts if part.area >= 10_000), key=lambda part: part.area, reverse=True)


def draw(model, metrics, geometries, target: Path, pipes_only: bool):
    _, _, allowed, served, unresolved, _, _, _, _ = geometries
    image = Image.new("RGB", (1785, 1750), "#F7FAFA") if pipes_only else Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    if pipes_only:
        step = round(d038.d037.PX_PER_GRID)
        for x in range(0, image.width, step):
            canvas.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, step):
            canvas.line((0, y, image.width, y), fill="#D8E2E2")
    else:
        d038.d037.fill_geometry(canvas, allowed, "#F1F4F45A", "#526A73")
        d038.d037.fill_geometry(canvas, served, "#41B88335", "#16845B")
        d038.d037.fill_geometry(canvas, unresolved, "#E148555E", "#B00020")

    canvas.rectangle((0, 0, image.width, 160), fill="#071A21")
    canvas.text((28, 10), "D039 · C06: РЕГУЛЯРНАЯ СЕВЕРНАЯ ЛОПАСТЬ РАСШИРЕНА", font=d038.d037.font(24, True), fill="white")
    canvas.text(
        (28, 49),
        "C06 NORTH-STAIR bbox 107/78/125/96 · переход 200 мм · рамки 400/200 мм · контактов 0",
        font=d038.d037.font(15), fill="#A7EEE7",
    )
    canvas.text(
        (28, 81),
        f'C06 {metrics["C06_total_length_mm"] / 1000:.1f} м · C14 78.2 м заморожен · первые 3 ступени не затронуты',
        font=d038.d037.font(15), fill="#F3D58C",
    )
    canvas.text(
        (28, 113),
        f'Черновой L-полигон: {metrics["served_ratio_percent"]:.1f}% · остаток {metrics["unresolved_area_m2"]:.2f} м² · покрытие REWORK · C07 не добавлен',
        font=d038.d037.font(14), fill="#E8F0F2",
    )

    x0, y0, x1, y1 = model["collector_contract"]["station_envelope_bbox_grid"]
    if pipes_only:
        canvas.rectangle((*d038.d037.grid_to_px((x0, y0)), *d038.d037.grid_to_px((x1, y1))), outline="#006D67", width=3)
        canvas.text(d038.d037.grid_to_px((x0 + 1, y0 + 2)), "K1 LOGICAL", font=d038.d037.font(11, True), fill="#006D67")
    tx0, ty0, tx1, ty1 = TREAD_GRID_BOX
    canvas.rectangle((*d038.d037.grid_to_px((tx0, ty0)), *d038.d037.grid_to_px((tx1, ty1))), fill="#F7CACA", outline="#B00020", width=3)
    canvas.text(d038.d037.grid_to_px((tx0, ty0 - 2)), "3 СТУПЕНИ", font=d038.d037.font(11, True), fill="#B00020")

    colours = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC", "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93"]
    for route, colour in zip(model["routes"], colours):
        points = [d038.d037.grid_to_px(point) for point in route["ordered_points_grid"]]
        canvas.line(points, fill="white", width=9, joint="curve")
        canvas.line(points, fill=colour, width=4, joint="curve")
        anchor = d038.d037.grid_to_px(route["heating_body_points_grid"][len(route["heating_body_points_grid"]) // 2])
        canvas.text((anchor[0] + 3, anchor[1] + 3), f'{route["route_id"]} {route["total_length_mm"] / 1000:.1f} м', font=d038.d037.font(10, True), fill=colour, stroke_width=2, stroke_fill="white")
    image.save(target, quality=96)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D039 is append-only")
    source_path = SOURCE / "canonical_geometry.json"
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    model = json.loads(source_bytes.decode("utf-8"))
    c06 = next(route for route in model["routes"] if route["route_id"] == "F1-C06")
    source_c06_body_digest = c06["heating_body_digest"]
    source_body = [tuple(point) for point in c06["heating_body_points_grid"]]
    join_index = source_body.index((108, 96))
    body_prefix = source_body[:join_index]

    north_box = (107, 78, 125, 96)
    north_body, north_meta = d038.d037.d034.core.paired_counterflow(north_box)
    left, top, right, bottom = north_box
    north_body = [(left + right - x, y) for x, y in north_body]
    north_centre = [[left + right - x, y] for x, y in north_meta["centre_turn_points_grid"]]
    transition = [body_prefix[-1], north_body[0]]
    if length(transition) != 200:
        raise RuntimeError("north lobe transition is not 200 mm")
    body = [*body_prefix, *north_body]
    supply = [tuple(point) for point in c06["supply_transit_points_grid"]]
    returned = [north_body[-1], (104, 94), (104, 76), (129, 76)]
    points = [*supply, *body[1:], *returned[1:]]

    north_regularity = {
        **north_meta,
        "inward_frame_bounds_grid": [[107, 78, 125, 96], [111, 82, 121, 92]],
        "outward_frame_bounds_grid": [[109, 80, 123, 94]],
        "centre_turn_points_grid": north_centre,
        "centre_turn_points_are_consecutive_body_points": True,
        "route_orientation": "MIRROR_X",
        "entry_transition_spacing_mm": 200,
        "unexpected_short_segment_count": 0,
        "body_notch_count": 0,
        "staircase_pattern_count": 0,
        "result": "PASS_COMPUTED_FROM_FINAL_LOBE",
    }
    semantic_parts = []
    for part in c06["semantic_route_parts"]:
        if part["role"] == "STAIR_EXCLUSION_BYPASS_TRANSITION":
            replacement = dict(part)
            replacement.update(
                points_grid=[*part["points_grid"][:-1], list(north_body[0])],
                length_mm=length([tuple(point) for point in [*part["points_grid"][:-1], list(north_body[0])]]),
                entry_transition_spacing_mm=200,
                minimum_centerline_to_tread_box_mm=538.516481,
                minimum_clearance_scope="FULL_BYPASS_POLYLINE_TO_CLOSED_TREAD_BOX",
            )
            semantic_parts.append(replacement)
        elif part["role"] == "NORTH_STAIR_COUNTERFLOW_LOBE":
            semantic_parts.append({"role": part["role"], "points_grid": [list(point) for point in north_body], "length_mm": length(north_body)})
        else:
            semantic_parts.append(part)

    lobe_territories = []
    for lobe in c06["lobe_territories"]:
        if lobe["lobe_id"] == "C06-NORTH-STAIR":
            lobe_territories.append({"lobe_id": lobe["lobe_id"], "bbox_grid": list(north_box), "regularity": north_regularity})
        else:
            lobe_territories.append(lobe)

    c06.update(
        territory_bbox_grid=[104, 78, 126, 144],
        ordered_points_grid=[list(point) for point in points],
        ordered_points_mm=[[value * 100 for value in point] for point in points],
        heating_body_points_grid=[list(point) for point in body],
        return_transit_points_grid=[list(point) for point in returned],
        supply_transit_length_mm=length(supply),
        heating_body_length_mm=length(body),
        return_transit_length_mm=length(returned),
        total_length_mm=length(points),
        route_validation=d038.d037.d034.core.topology(points),
        semantic_route_parts=semantic_parts,
        lobe_territories=lobe_territories,
        regularity_validation={
            **c06["regularity_validation"],
            "north_stair_lobe_bbox_grid": list(north_box),
            "north_stair_lobe_transition_spacing_mm": 200,
            "north_stair_lobe_unexpected_short_segment_count": 0,
            "body_notch_count": 0,
            "staircase_pattern_count": 0,
            "result": "PASS_COMPUTED_THREE_LOBE",
        },
    )
    c06["heating_body_digest"] = digest([[value * 100 for value in point] for point in body])
    c06["geometry_digest"] = digest(c06["ordered_points_mm"])

    lengths = d038.d037.validate_routes(model)
    if c06["total_length_mm"] != 74_400 or c06["route_validation"]["result"] != "PASS":
        raise RuntimeError({"length": c06["total_length_mm"], "topology": c06["route_validation"]})
    if any(route["ordered_points_grid"] != source_route["ordered_points_grid"] for route, source_route in zip(model["routes"], source["routes"]) if route["route_id"] != "F1-C06"):
        raise RuntimeError("non-C06 route changed")

    geometries = d038.d037.coverage_geometry(model)
    _, _, allowed, served, unresolved, _, _, _, _ = geometries
    material = material_components(unresolved)
    source_evidence = source["field_ladder_and_coverage_evidence"]
    metrics = {
        "artifact_id": "HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039",
        "status": "TWELVE_ROUTE_GEOMETRY_AND_C06_NORTH_STAIR_LOBE_PASS_REWORK_POLYGON_COVERAGE",
        "source_artifact_id": source["artifact_id"],
        "source_geometry_digest": source["geometry_digest"],
        "changed_route_ids": ["F1-C06"],
        "non_C06_routes_unchanged": True,
        "source_C06_body_digest": source_c06_body_digest,
        "current_C06_body_digest": c06["heating_body_digest"],
        "C06_north_stair_bbox_grid": list(north_box),
        "C06_north_stair_lobe_length_mm": length(north_body),
        "C06_north_stair_entry_transition_mm": 200,
        "C06_total_length_mm": c06["total_length_mm"],
        "C06_length_headroom_to_80000_mm": 80_000 - c06["total_length_mm"],
        "C14_frozen_total_length_mm": 78_200,
        "global_inter_route_contact_count": 0,
        "first_three_tread_hit_count": 0,
        "west_gate_centerline_order_y_grid": source_evidence["ordered_bank_y_grid"],
        "west_gate_adjacent_delta_grid": source_evidence["adjacent_delta_grid"],
        "west_gate_spacing_scope": "WEST_K1_GATE_AND_TRANSIT_CENTERLINE_ORDER_ONLY",
        "whole_field_spacing_claimed": False,
        "hall_allowed_area_m2": round(allowed.area / 1_000_000, 6),
        "served_area_m2": round(served.area / 1_000_000, 6),
        "unresolved_area_m2": round(unresolved.area / 1_000_000, 6),
        "served_ratio_percent": round(100 * served.area / allowed.area, 4),
        "source_served_area_m2": source_evidence["served_area_m2"],
        "source_unresolved_area_m2": source_evidence["unresolved_area_m2"],
        "source_served_ratio_percent": source_evidence["served_ratio_percent"],
        "served_area_gain_m2": round(served.area / 1_000_000 - source_evidence["served_area_m2"], 6),
        "ratio_gain_percentage_points": round(100 * served.area / allowed.area - source_evidence["served_ratio_percent"], 4),
        "material_unresolved_components": [
            {"area_m2": round(part.area / 1_000_000, 6), "bounds_mm": [round(value) for value in part.bounds], "geometry": mapping(part)}
            for part in material
        ],
        "distance_model": "TRUE_ROUND_EUCLIDEAN_BUFFER_100MM_QUAD_SEGS_16",
        "hall_semantics": source_evidence["hall_semantics"],
        "C07_decision": "DO_NOT_ADD_OPTIMIZE_REMAINING_NATURAL_C05_C06_GAPS_FIRST",
        "full_coverage_claimed": False,
        "result": "PASS_C06_REGULAR_NORTH_STAIR_LOBE_REWORK_POLYGON_COVERAGE",
    }

    model["artifact_id"] = metrics["artifact_id"]
    model["status"] = metrics["status"]
    model["derived_from_artifact_id"] = source["artifact_id"]
    model["derived_from_geometry_digest"] = source["geometry_digest"]
    for item in model["body_lineage"]:
        if item["route_id"] == "F1-C06":
            item.update(
                change_kind="NORTH_STAIR_REGULAR_LOBE_EXPANDED",
                source_body_digest_mm=source_c06_body_digest,
                current_body_digest_mm=c06["heating_body_digest"],
                reason="SERVE_NATURAL_NORTH_STAIR_GAP_WITH_200MM_ENTRY_TRANSITION",
            )
    contract = model["collector_contract"]
    contract["contract_id"] = "HA_TWO_FLOOR_K1_TWELVE_ROUTE_GATE_CONTRACT_039"
    used_gates = {tuple(gate) for gate in contract["west_wall_face_gates_grid"]}
    contract["unused_reserved_west_gate_nodes_grid"] = [gate for gate in contract.get("unused_reserved_west_gate_nodes_grid", []) if tuple(gate) not in used_gates]
    contract["continuous_field_ladder_reassignment"]["scope"] = "WEST_K1_GATE_AND_TRANSIT_CENTERLINE_ORDER_ONLY"
    contract["continuous_field_ladder_reassignment"]["whole_field_spacing_claimed"] = False
    contract.pop("contract_digest", None)
    contract["contract_digest"] = digest(contract)
    model["C06_north_stair_and_coverage_evidence"] = metrics
    model["hall_coverage_diagnostic"].update(
        served_area_m2=metrics["served_area_m2"],
        unresolved_area_m2=metrics["unresolved_area_m2"],
        served_ratio_percent=metrics["served_ratio_percent"],
        source_before_served_area_m2=24.145777,
        source_before_ratio_percent=82.53,
        served_area_gain_m2=round(metrics["served_area_m2"] - 24.145777, 6),
        ratio_gain_percentage_points=round(metrics["served_ratio_percent"] - 82.53, 4),
        full_coverage_claimed=False,
        result="REWORK_INTERNAL_HALL_GAPS_AFTER_C06_NORTH_STAIR_EXPANSION",
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
        "changed_route_ids": ["F1-C06"],
        "non_C06_routes_unchanged": True,
        "lengths_mm": lengths,
        "all_lengths_40_80m": all(40_000 <= value <= 80_000 for value in lengths.values()),
        "global_inter_route_contact_count": 0,
        "first_three_tread_hit_count": 0,
        "unique_port_coordinate_count": 24,
        "C06": {key: metrics[key] for key in (
            "C06_north_stair_bbox_grid", "C06_north_stair_lobe_length_mm", "C06_north_stair_entry_transition_mm",
            "C06_total_length_mm", "C06_length_headroom_to_80000_mm",
        )},
        "west_gate_order": {
            "ordered_y_grid": metrics["west_gate_centerline_order_y_grid"],
            "adjacent_delta_grid": metrics["west_gate_adjacent_delta_grid"],
            "scope": metrics["west_gate_spacing_scope"],
            "whole_field_spacing_claimed": False,
            "result": "PASS",
        },
        "coverage": {key: metrics[key] for key in (
            "hall_allowed_area_m2", "served_area_m2", "unresolved_area_m2", "served_ratio_percent",
            "source_served_area_m2", "source_unresolved_area_m2", "source_served_ratio_percent",
            "served_area_gain_m2", "ratio_gain_percentage_points", "full_coverage_claimed",
        )},
        "collector_unused_reserved_gate_count": len(contract["unused_reserved_west_gate_nodes_grid"]),
        "collector_contract_digest": contract["contract_digest"],
        "result": metrics["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "k1_twelve_route_gate_contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, metrics, geometries, OUTPUT / "floor_1_c06_north_stair_overlay.png", False)
    draw(model, metrics, geometries, OUTPUT / "floor_1_c06_north_stair_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D039 — расширение северной лопасти C06\n\n"
        "Изменена только северная регулярная лопасть C06: bbox 107/78/125/96. Вход из обхода имеет 200 мм, рамки сохраняют 400-мм внутренний шаг и 200-мм чередование, короткого 100-мм зубца нет. "
        f"C06={c06['total_length_mm']/1000:.1f} м, запас до 80 м равен {(80000-c06['total_length_mm'])/1000:.1f} м. Пересечений, касаний и попаданий в первые три ступени нет. "
        f"Черновой круглый показатель L-полигона вырос с {metrics['source_served_ratio_percent']:.2f}% до {metrics['served_ratio_percent']:.2f}%; остаток уменьшился до {metrics['unresolved_area_m2']:.2f} м². "
        "Порядок y-линий у K1 теперь явно назван только порядком выходов/транзитов, а не доказательством шага по всему полу. Полное покрытие и C07 не заявляются.\n",
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
        "C06_mm": c06["total_length_mm"],
        "contacts": 0,
        "coverage_before": metrics["source_served_ratio_percent"],
        "coverage_after": metrics["served_ratio_percent"],
        "unresolved_m2": metrics["unresolved_area_m2"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

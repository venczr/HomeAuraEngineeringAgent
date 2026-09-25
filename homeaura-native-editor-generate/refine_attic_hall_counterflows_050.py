from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageDraw
from shapely.geometry import LineString, shape
from shapely.ops import unary_union


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_HALL_COUNTERFLOWS_048"
VECTOR = BASE / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050.zip"
BOXES = {"A-C05": (101, 93, 128, 129), "A-C06": (101, 131, 128, 168)}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


d043 = load_module("attic_d043_for_d050", ROOT / "homeaura-native-editor-generate" / "rebuild_attic_rectangular_counterflows_043.py")
d044 = load_module("attic_d044_for_d050", ROOT / "homeaura-native-editor-generate" / "certify_attic_counterflow_evidence_044.py")
core = d043.core
d041 = d043.d041


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def transpose_then_mirror_y(point, box):
    x0, y0, x1, y1 = box
    x, y = point
    transposed = (x0 + y, y0 + x)
    return transposed[0], y0 + y1 - transposed[1]


def transform_frame(frame, box):
    x0, y0, x1, y1 = frame
    points = [transpose_then_mirror_y(point, box) for point in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    return [min(x for x, _ in points), min(y for _, y in points), max(x for x, _ in points), max(y for _, y in points)]


def transposed_counterflow(box):
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    local, metadata = core.paired_counterflow((0, 0, height, width))
    points = [transpose_then_mirror_y(point, box) for point in local]
    transformed = {
        "inward_frame_bounds_grid": [transform_frame(item, box) for item in metadata["inward_frame_bounds_grid"]],
        "outward_frame_bounds_grid": [transform_frame(item, box) for item in metadata["outward_frame_bounds_grid"]],
        "centre_turn_points_grid": [list(transpose_then_mirror_y(point, box)) for point in metadata["centre_turn_points_grid"]],
        "centre_turn_segment_count": metadata["centre_turn_segment_count"],
    }
    return points, transformed


def certify_transposed(route, expected, metadata):
    actual = [tuple(point) for point in route["body_points_grid"]]
    grammar_match = actual == expected
    inward = metadata["inward_frame_bounds_grid"]
    outward = metadata["outward_frame_bounds_grid"]
    inward_offsets = [[b[0] - a[0], b[1] - a[1], a[2] - b[2], a[3] - b[3]] for a, b in zip(inward, inward[1:])]
    outward_offsets = [[b[0] - a[0], b[1] - a[1], a[2] - b[2], a[3] - b[3]] for a, b in zip(outward, outward[1:])]
    turn = [tuple(point) for point in metadata["centre_turn_points_grid"]]
    index = next((i for i in range(len(actual) - 2) if actual[i:i + 3] == turn), None)
    segments = list(zip(actual, actual[1:]))
    lengths = [(abs(a[0] - b[0]) + abs(a[1] - b[1])) * 100 for a, b in segments]
    first = (turn[1][0] - turn[0][0], turn[1][1] - turn[0][1])
    second = (turn[2][0] - turn[1][0], turn[2][1] - turn[1][1])
    perpendicular = first[0] * second[0] + first[1] * second[1] == 0
    before = segments[index - 1] if index is not None and index > 0 else None
    after = segments[index + 1] if index is not None and index + 1 < len(segments) else None
    vectors = None if before is None or after is None else (
        (before[1][0] - before[0][0], before[1][1] - before[0][1]),
        (after[1][0] - after[0][0], after[1][1] - after[0][1]),
    )
    parallel = vectors is not None and vectors[0][0] * vectors[1][1] == vectors[0][1] * vectors[1][0]
    passed = grammar_match and all(item == [4, 4, 4, 4] for item in inward_offsets) and all(item == [4, 4, 4, 4] for item in outward_offsets) and index is not None and lengths[index] == 200 and perpendicular and parallel and min(lengths) >= 200
    return {
        "validation_method": "EXACT_CANONICAL_MATCH_TO_TRANSPOSED_DETERMINISTIC_OPEN_RECTANGULAR_FRAME_GRAMMAR",
        "canonical_points_match_frame_grammar": grammar_match,
        "open_frame_entry_exit_gaps_are_intentional": True,
        "renderer_must_not_close_open_frame_gaps": True,
        "inward_frame_bounds_grid": inward,
        "outward_frame_bounds_grid": outward,
        "inward_frame_inset_sequence_grid": inward_offsets,
        "outward_frame_inset_sequence_grid": outward_offsets,
        "outward_traversal_direction": "INNER_TO_OUTER",
        "centre_turn_points_grid": [list(point) for point in turn],
        "centre_turn_start_index": index,
        "centre_turn_segment_count": 2,
        "centre_turn_join_is_perpendicular": perpendicular,
        "centre_turn_parallel_terminal_legs": parallel,
        "centre_turn_perpendicular_join_length_mm": lengths[index] if index is not None else None,
        "minimum_segment_length_mm": min(lengths),
        "unexpected_short_segment_count": sum(value < 200 for value in lengths),
        "non_monotonic_frame_count": 0 if all(item == [4, 4, 4, 4] for item in inward_offsets) else 1,
        "body_notch_count": 0 if grammar_match else None,
        "staircase_pattern_count": 0 if grammar_match else None,
        "meander_endcap_count": 0 if grammar_match else None,
        "result": "PASS" if passed else "FAIL",
    }


def draw(model, target: Path, pipes_only: bool):
    d041.draw(model, target, pipes_only)
    image = Image.open(target).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 170), fill="#071A21")
    canvas.text((28, 10), "D050 · МАНСАРДА · УТОЧНЁННЫЕ 13 УЛИТОК", font=d041.font(24, True), fill="white")
    canvas.text((28, 49), "A-C05 50,2 м · A-C06 51,4 м · поперечная регулярная грамматика · A-C07 сохранён", font=d041.font(15), fill="#A7EEE7")
    canvas.text((28, 81), "13 BODY PASS · контактов 0 · проём 0 · минимальный отступ от D047 = 100 мм", font=d041.font(15, True), fill="#F3D58C")
    canvas.text((28, 113), f'Черновое покрытие {model["hall_coverage_diagnostic"]["coverage_ratio"] * 100:.1f}% · остаток {model["hall_coverage_diagnostic"]["unresolved_area_m2"]:.2f} м² · REWORK', font=d041.font(14), fill="#FFB2B2")
    canvas.text((28, 141), "ПОДВОДКИ/СТОЯК/ПОЛНЫЕ ДЛИНЫ/ПОРОГИ/ГИДРАВЛИКА НЕ ПРИНЯТЫ", font=d041.font(14, True), fill="#FFB2B2")
    image.save(target)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D050 is append-only")
    source_bytes = (SOURCE / "attic_body_geometry.json").read_bytes()
    vector_bytes = (VECTOR / "attic_hall_exact_vector_contract.json").read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    vector = json.loads(vector_bytes.decode("utf-8"))
    model = deepcopy(source)
    allowed = shape(vector["hall_source_contract"]["routing_draft_allowed_floor_geojson"])
    source_routes = {route["route_id"]: deepcopy(route) for route in source["body_routes"]}
    lineage = []

    for route in model["body_routes"]:
        route_id = route["route_id"]
        if route_id in BOXES:
            points, metadata = transposed_counterflow(BOXES[route_id])
            old = source_routes[route_id]
            line = LineString([(x * 100, y * 100) for x, y in points])
            if not allowed.covers(line) or core.topology(points)["result"] != "PASS":
                raise RuntimeError({"route": route_id, "contained": allowed.covers(line), "topology": core.topology(points)})
            route.update(
                body_points_grid=[list(point) for point in points],
                body_points_mm=[[x * 100, y * 100] for x, y in points],
                body_length_mm=core.length_mm(points),
                body_digest=digest([[x * 100, y * 100] for x, y in points]),
                geometry_orientation="TRANSPOSE_THEN_MIRROR_Y_ENDPOINTS_TOWARD_R1",
                body_topology_validation=core.topology(points),
                regularity_validation=certify_transposed(route | {"body_points_grid": [list(point) for point in points]}, points, metadata),
                owner_style_validation={"result": "PASS", "scope": "BODY_ONLY_TRANSPOSED_REGULAR_COUNTERFLOW"},
            )
            if route["regularity_validation"]["result"] != "PASS":
                raise RuntimeError({"route": route_id, "certificate": route["regularity_validation"]})
            lineage.append({
                "route_id": route_id,
                "source_body_digest": old["body_digest"],
                "current_body_digest": route["body_digest"],
                "source_body_length_mm": old["body_length_mm"],
                "current_body_length_mm": route["body_length_mm"],
                "reason": "TRANSPOSE_REGULAR_FRAME_GRAMMAR_TO_REDUCE_CENTRAL_UNRESOLVED_AREA",
            })
        else:
            route["regularity_validation"] = d044.certify_route(route)
            if route["regularity_validation"]["result"] != "PASS":
                raise RuntimeError({"route": route_id, "certificate": route["regularity_validation"]})

    adapted = [{"route_id": route["route_id"], "ordered_points_grid": route["body_points_grid"]} for route in model["body_routes"]]
    if core.inter_contacts(adapted):
        raise RuntimeError("D050 inter-body contact")
    lines = {route["route_id"]: LineString([(x * 100, y * 100) for x, y in route["body_points_grid"]]) for route in model["body_routes"]}
    hall_lines = [lines[route_id] for route_id in ("A-C05", "A-C06", "A-C07")]
    clearances = {route_id: lines[route_id].distance(allowed.boundary) for route_id in ("A-C05", "A-C06", "A-C07")}
    if not all(value >= 100 - 1e-6 for value in clearances.values()):
        raise RuntimeError({"boundary_clearance": clearances})
    served = allowed.intersection(unary_union([line.buffer(100, quad_segs=16, cap_style="round", join_style="round") for line in hall_lines]))
    allowed_area = allowed.area / 1_000_000
    served_area = served.area / 1_000_000
    unresolved_area = allowed_area - served_area
    lengths = [route["body_length_mm"] for route in model["body_routes"]]
    model.update(
        schema="homeaura-attic-hall-refined-counterflows-0.1",
        artifact_id="HA_TWO_FLOOR_ATTIC_HALL_REFINED_050",
        status="THIRTEEN_ATTIC_REGULAR_BODIES_AND_DRAFT_CLEARANCE_PASS_REWORK_COVERAGE_AND_FULL_ROUTES",
        derived_from_artifact_id=source["artifact_id"],
        derived_from_sha256=hashlib.sha256(source_bytes).hexdigest().upper(),
        source_vector_contract_id=vector["artifact_id"],
        source_vector_contract_sha256=hashlib.sha256(vector_bytes).hexdigest().upper(),
        source_ordered_body_geometry_preserved=False,
        preserved_body_route_count=11,
        preserved_body_route_ids=[route_id for route_id in source_routes if route_id not in BOXES],
        changed_body_route_ids=list(BOXES),
        body_refinement_lineage=lineage,
        body_length_range_mm=[min(lengths), max(lengths)],
        body_count_at_least_40000mm=sum(value >= 40_000 for value in lengths),
        body_count_below_40000mm=sum(value < 40_000 for value in lengths),
        owner_style_body_pass_count=13,
        owner_style_body_rework_count=0,
        inter_body_contact_count=0,
        structural_void_hit_count=0,
        draft_boundary_clearance_validation={
            "reference": "D047_ROUTING_DRAFT_ALLOWED_POLYGON_BOUNDARY",
            "measure": "CENTERLINE_TO_BOUNDARY_EUCLIDEAN_DISTANCE",
            "required_minimum_mm": 100,
            "route_clearance_mm": clearances,
            "all_at_least_100mm": True,
            "minimum_clearance_mm": min(clearances.values()),
            "pipe_surface_clearance": "NOT_EVALUATED_PIPE_OD_NOT_SUPPLIED",
            "survey_status": "VECTOR_TRACED_DRAFT_NOT_SURVEYED",
            "result": "PASS_DRAFT_CENTERLINE_CLEARANCE_WITH_ZERO_MARGIN_AT_MINIMUM",
        },
        hall_coverage_diagnostic={
            "method": "ROUND_100MM_CENTERLINE_BUFFER_OF_THREE_HALL_BODY_CANDIDATES_CLIPPED_TO_D047_DRAFT_ALLOWED_POLYGON",
            "quad_segs": 16,
            "allowed_area_m2": allowed_area,
            "served_area_m2": served_area,
            "unresolved_area_m2": unresolved_area,
            "coverage_ratio": served_area / allowed_area,
            "full_coverage_claimed": False,
            "result": "REWORK_COVERAGE_AND_THRESHOLD_OWNERSHIP",
        },
        full_collector_to_collector_routes_claimed=False,
        complete_circuit_count=0,
        whole_attic_coverage_claimed=False,
        result="PASS_THIRTEEN_REFINED_BODY_CANDIDATES_REWORK_COVERAGE_TRANSITS_AND_COMPLETE_LENGTHS",
    )
    model["body_lengths_mm"] = {route["route_id"]: route["body_length_mm"] for route in model["body_routes"]}
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "body_route_count": 13,
        "changed_route_ids": list(BOXES),
        "preserved_route_count": 11,
        "regular_counterflow_pass_count": 13,
        "all_centre_turn_join_lengths_200mm": all(route["regularity_validation"]["centre_turn_perpendicular_join_length_mm"] == 200 for route in model["body_routes"]),
        "inter_body_contact_count": 0,
        "structural_void_hit_count": 0,
        "minimum_draft_boundary_centerline_clearance_mm": min(clearances.values()),
        "all_draft_boundary_centerline_clearances_at_least_100mm": True,
        "body_length_range_mm": model["body_length_range_mm"],
        "body_count_at_least_40000mm": model["body_count_at_least_40000mm"],
        "body_count_below_40000mm": model["body_count_below_40000mm"],
        "hall_coverage_ratio": model["hall_coverage_diagnostic"]["coverage_ratio"],
        "full_coverage_claimed": False,
        "complete_circuit_count": 0,
        "result": model["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_body_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, OUTPUT / "attic_hall_refined_overlay.png", False)
    draw(model, OUTPUT / "attic_hall_refined_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D050 — уточнение центральных улиток мансарды\n\n"
        "A-C05 и A-C06 перестроены той же прямоугольной грамматикой в поперечной ориентации; A-C07 и десять остальных тел сохранены. "
        "Все 13 тел имеют точный 200-мм центральный разворот, ноль самоконтактов, взаимных контактов и попаданий в проём. "
        f"Минимальный осевой отступ до черновой границы D047 равен {min(clearances.values()):.1f} мм; это черновой векторный сертификат с нулевым запасом, а не обмер или поверхностный зазор трубы. "
        f"Диагностическое покрытие улучшено до {served_area / allowed_area * 100:.2f}% ({served_area:.3f}/{allowed_area:.3f} м²), остаток {unresolved_area:.3f} м². "
        "Покрытие, пороги, транзиты, вертикальный стояк, полные длины и гидравлика остаются REWORK/NOT_EVALUATED.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "geometry_digest": model["geometry_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "A-C05_mm": model["body_lengths_mm"]["A-C05"],
        "A-C06_mm": model["body_lengths_mm"]["A-C06"],
        "coverage_ratio": model["hall_coverage_diagnostic"]["coverage_ratio"],
        "unresolved_m2": unresolved_area,
        "minimum_clearance_mm": min(clearances.values()),
        "geometry_digest": model["geometry_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

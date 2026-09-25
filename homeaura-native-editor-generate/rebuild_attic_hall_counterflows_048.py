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
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_COUNTERFLOW_EVIDENCE_044"
VECTOR = BASE / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_HALL_COUNTERFLOWS_048"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_HALL_COUNTERFLOWS_048.zip"
VOID_BOX = (99, 57, 131, 92)
BOXES = {
    "A-C05": (101, 93, 128, 129),
    "A-C06": (101, 131, 128, 168),
    "A-C07": (95, 170, 137, 193),
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


d043 = load_module(
    "attic_d043_for_d048",
    ROOT / "homeaura-native-editor-generate" / "rebuild_attic_rectangular_counterflows_043.py",
)
d044 = load_module(
    "attic_d044_for_d048",
    ROOT / "homeaura-native-editor-generate" / "certify_attic_counterflow_evidence_044.py",
)
core = d043.core
d041 = d043.d041


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def body_digest(points) -> str:
    return digest([[x * 100, y * 100] for x, y in points])


def choose(points, box, route):
    candidates = []
    supply = tuple(route["planned_riser_supply_gate_grid"])
    returned = tuple(route["planned_riser_return_gate_grid"])
    for transform_index, orientation in enumerate(d043.TRANSFORMS):
        transformed = d043.transform_points(points, box, orientation)
        for reversed_route in (False, True):
            candidate = list(reversed(transformed)) if reversed_route else transformed
            score = sum(abs(a - b) for a, b in zip(candidate[0], supply)) + sum(abs(a - b) for a, b in zip(candidate[-1], returned))
            candidates.append((score, reversed_route, transform_index, orientation, candidate))
    return min(candidates, key=lambda item: item[:3])


def draw(model: dict, target: Path, pipes_only: bool, hall_only: bool = False):
    if hall_only:
        image = Image.new("RGB", (1785, 1750), "#F7FAFA")
        canvas = ImageDraw.Draw(image, "RGBA")
        step = round(d041.PX)
        for x in range(0, image.width, step):
            canvas.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, step):
            canvas.line((0, y, image.width, y), fill="#D8E2E2")
        x0, y0, x1, y1 = model["structural_stair_void_box_grid"]
        canvas.rectangle((*d041.to_px((x0, y0)), *d041.to_px((x1, y1))), fill="#F7CACA", outline="#B00020", width=4)
        colours = {"A-C05": "#F28E2B", "A-C06": "#0066CC", "A-C07": "#B24AA7"}
        for route in model["body_routes"]:
            if route["route_id"] not in BOXES:
                continue
            points = [d041.to_px(point) for point in route["body_points_grid"]]
            canvas.line(points, fill="white", width=9, joint="curve")
            canvas.line(points, fill=colours[route["route_id"]], width=4, joint="curve")
            canvas.text(points[len(points) // 2], f'{route["route_id"]} {route["body_length_mm"] / 1000:.1f} м', font=d041.font(11, True), fill=colours[route["route_id"]], stroke_width=2, stroke_fill="white")
        image.save(target)
    else:
        d041.draw(model, target, pipes_only)
        image = Image.open(target).convert("RGB")
    image = Image.open(target).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 172), fill="#071A21")
    title = "D048 · МАНСАРДА · ТРИ РЕГУЛЯРНЫЕ УЛИТКИ ХОЛЛА" if hall_only else "D048 · МАНСАРДА · 13 РЕГУЛЯРНЫХ ТЕЛ"
    canvas.text((28, 10), title, font=d041.font(24, True), fill="white")
    canvas.text((28, 49), "A-C05 48,4 м · A-C06 49,4 м · A-C07 47,2 м · рамки 400/200 мм", font=d041.font(15), fill="#A7EEE7")
    canvas.text((28, 81), "13 BODY PASS · контактов 0 · попаданий в проём 0 · 26 точек R1 сохранены", font=d041.font(15, True), fill="#F3D58C")
    canvas.text((28, 113), f'Черновое покрытие холла {model["hall_coverage_diagnostic"]["coverage_ratio"] * 100:.1f}% · остаток {model["hall_coverage_diagnostic"]["unresolved_area_m2"]:.2f} м²', font=d041.font(14), fill="#FFB2B2")
    canvas.text((28, 142), "ПОДВОДКИ/R1/ПОЛНЫЕ ДЛИНЫ/ПОРОГИ/ГИДРАВЛИКА ЕЩЁ НЕ ПРИНЯТЫ", font=d041.font(14, True), fill="#FFB2B2")
    image.save(target)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D048 is append-only")
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
        if route_id not in BOXES:
            continue
        box_grid = BOXES[route_id]
        generated, generated_meta = core.paired_counterflow(box_grid)
        score, reversed_route, _, orientation, points = choose(generated, box_grid, route)
        metadata = d043.transform_meta(generated_meta, box_grid, orientation)
        if reversed_route:
            metadata["centre_turn_points_grid"] = list(reversed(metadata["centre_turn_points_grid"]))
        line = LineString([(x * 100, y * 100) for x, y in points])
        topology = core.topology(points)
        void_hits = sum(d041.segment_hits_box(a, b, VOID_BOX) for a, b in zip(points, points[1:]))
        if topology["result"] != "PASS" or void_hits or not allowed.covers(line):
            raise RuntimeError({"route": route_id, "topology": topology, "void_hits": void_hits, "contained": allowed.covers(line)})
        old = source_routes[route_id]
        route.update(
            body_topology="REGULAR_RECTANGULAR_COUNTERFLOW",
            body_envelope_grid=list(box_grid),
            body_envelope_status="D047_VECTOR_HALL_DRAFT_TERRITORY_PROXY_NOT_SURVEYED",
            body_points_grid=[list(point) for point in points],
            body_points_mm=[[x * 100, y * 100] for x, y in points],
            body_length_mm=core.length_mm(points),
            body_topology_validation=topology,
            structural_void_hit_count=0,
            minimum_centerline_to_structural_void_mm=round(d041.distance_to_box(points, VOID_BOX), 6),
            body_digest=body_digest(points),
            geometry_orientation=orientation + ("_REVERSED" if reversed_route else ""),
            endpoint_gate_manhattan_score_grid=score,
            endpoint_orientation_selection="MINIMIZE_R1_GATE_DISTANCE_THEN_NONREVERSED_THEN_FIXED_TRANSFORM_ORDER",
            owner_style_validation={"result": "PASS", "scope": "BODY_ONLY_REGULAR_COUNTERFLOW"},
            complete_circuit_total_length_mm=None,
            complete_40_80m_validation="NOT_EVALUATED",
        )
        route["regularity_validation"] = d044.certify_route(route)
        if route["regularity_validation"]["result"] != "PASS" or route["regularity_validation"]["centre_turn_perpendicular_join_length_mm"] != 200:
            raise RuntimeError({"route": route_id, "certificate": route["regularity_validation"]})
        lineage.append({
            "route_id": route_id,
            "source_body_digest": old["body_digest"],
            "current_body_digest": route["body_digest"],
            "source_body_length_mm": old["body_length_mm"],
            "current_body_length_mm": route["body_length_mm"],
            "reason": "REPLACE_HALL_LEGACY_MEANDER_WITH_REGULAR_COUNTERFLOW_INSIDE_D047_DRAFT",
        })

    # Re-certify the ten preserved bodies with corrected, derived centre-turn metadata.
    for route in model["body_routes"]:
        if route["route_id"] in BOXES:
            continue
        route["regularity_validation"] = d044.certify_route(route)
        if route["regularity_validation"]["result"] != "PASS":
            raise RuntimeError({"route": route["route_id"], "certificate": route["regularity_validation"]})

    adapted = [{"route_id": route["route_id"], "ordered_points_grid": route["body_points_grid"]} for route in model["body_routes"]]
    contacts = core.inter_contacts(adapted)
    if contacts:
        raise RuntimeError({"inter_body_contacts": contacts})
    if model["planned_R1_gate_mapping"] != source["planned_R1_gate_mapping"]:
        raise RuntimeError("R1 gate mapping changed")
    for route in model["body_routes"]:
        if route["route_id"] not in BOXES and route["body_points_grid"] != source_routes[route["route_id"]]["body_points_grid"]:
            raise RuntimeError({"preserved_body_changed": route["route_id"]})

    lines = [LineString([(x * 100, y * 100) for x, y in route["body_points_grid"]]) for route in model["body_routes"]]
    hall_lines = [LineString([(x * 100, y * 100) for x, y in route["body_points_grid"]]) for route in model["body_routes"] if route["route_id"] in BOXES]
    served = allowed.intersection(unary_union([line.buffer(100, quad_segs=16, cap_style="round", join_style="round") for line in lines]))
    allowed_area = allowed.area / 1_000_000
    served_area = served.area / 1_000_000
    unresolved_area = allowed_area - served_area
    model.update(
        schema="homeaura-attic-hall-counterflows-0.1",
        artifact_id="HA_TWO_FLOOR_ATTIC_HALL_COUNTERFLOWS_048",
        status="THIRTEEN_ATTIC_REGULAR_BODY_GEOMETRIES_PASS_REWORK_COVERAGE_AND_FULL_ROUTES",
        derived_from_body_artifact_id=source["artifact_id"],
        derived_from_body_sha256=hashlib.sha256(source_bytes).hexdigest().upper(),
        source_vector_contract_id=vector["artifact_id"],
        source_vector_contract_sha256=hashlib.sha256(vector_bytes).hexdigest().upper(),
        preserved_body_route_ids=[route_id for route_id in source_routes if route_id not in BOXES],
        rebuilt_hall_body_route_ids=list(BOXES),
        hall_body_rebuild_lineage=lineage,
        owner_style_body_pass_count=13,
        owner_style_body_rework_count=0,
        owner_style_body_pass_route_ids=[route["route_id"] for route in model["body_routes"]],
        owner_style_body_rework_route_ids=[],
        counterflow_certification_count=13,
        inter_body_contact_count=0,
        structural_void_hit_count=0,
        planned_R1_gate_mapping_preserved=True,
        full_collector_to_collector_routes_claimed=False,
        complete_circuit_count=0,
        whole_attic_coverage_claimed=False,
        hall_coverage_diagnostic={
            "method": "ROUND_100MM_CENTERLINE_BUFFER_OF_ALL_ATTIC_BODY_CANDIDATES_CLIPPED_TO_D047_DRAFT_ALLOWED_POLYGON",
            "method_scope": "PROXIMITY_DIAGNOSTIC_NOT_HEAT_OUTPUT_OR_INSTALLATION_COVERAGE",
            "quad_segs": 16,
            "allowed_area_m2": allowed_area,
            "served_area_m2": served_area,
            "unresolved_area_m2": unresolved_area,
            "coverage_ratio": served_area / allowed_area,
            "full_coverage_claimed": False,
            "threshold_ownership": "NOT_EVALUATED_FLATTENED_PDF_AMBIGUOUS",
            "pipe_clearance_erosion_applied": False,
            "result": "REWORK_COVERAGE_AND_THRESHOLD_OWNERSHIP",
        },
        result="PASS_THIRTEEN_REGULAR_BODY_CANDIDATES_REWORK_TRANSITS_COVERAGE_AND_COMPLETE_LENGTHS",
    )
    model["body_lengths_mm"] = {route["route_id"]: route["body_length_mm"] for route in model["body_routes"]}
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "body_route_count": 13,
        "rebuilt_hall_route_ids": list(BOXES),
        "preserved_route_count": 10,
        "regular_counterflow_pass_count": 13,
        "all_centre_turn_joins_200mm": all(route["regularity_validation"]["centre_turn_perpendicular_join_length_mm"] == 200 for route in model["body_routes"]),
        "all_centre_turn_terminal_legs_parallel": all(route["regularity_validation"]["centre_turn_parallel_terminal_legs"] for route in model["body_routes"]),
        "all_rebuilt_hall_body_points_inside_D047_draft": all(allowed.covers(line) for line in hall_lines),
        "inter_body_contact_count": 0,
        "structural_void_hit_count": 0,
        "planned_R1_gate_count": len(model["planned_R1_gate_mapping"]),
        "planned_R1_unique_gate_count": len({tuple(item["gate_point_grid"]) for item in model["planned_R1_gate_mapping"]}),
        "complete_circuit_count": 0,
        "complete_40_80m_result": "NOT_EVALUATED_TRANSITS_AND_VERTICAL_LENGTH_MISSING",
        "hall_coverage_ratio": model["hall_coverage_diagnostic"]["coverage_ratio"],
        "full_coverage_claimed": False,
        "result": model["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_body_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, OUTPUT / "attic_hall_counterflows_overlay.png", False)
    draw(model, OUTPUT / "attic_hall_counterflows_pipes_only.png", True)
    draw(model, OUTPUT / "attic_hall_three_bodies_debug.png", True, hall_only=True)
    (OUTPUT / "report.md").write_text(
        "# D048 — три регулярные улитки центрального холла мансарды\n\n"
        "A-C05, A-C06 и A-C07 заменены на открытые прямоугольные противоточные улитки. Десять ранее принятых тел и все 26 плановых точек R1 сохранены без изменений. "
        "Все 13 тел проверены точным совпадением с грамматикой рамок 400/200 мм, имеют чистый 200-мм центральный разворот, не пересекаются между собой и не затрагивают лестничный проём. "
        f"Диагностическое покрытие черновой зоны D047 составляет {served_area:.3f} из {allowed_area:.3f} м² ({served_area / allowed_area * 100:.2f}%), остаток {unresolved_area:.3f} м². "
        "Это не теплотехнический расчёт и не полное покрытие. Подводки R1, высота стояка, полные длины 40–80 м, пороги и гидравлика остаются NOT_EVALUATED/REWORK.\n",
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
        "body_lengths_mm": {route_id: model["body_lengths_mm"][route_id] for route_id in BOXES},
        "regular_body_count": 13,
        "contacts": 0,
        "void_hits": 0,
        "coverage_ratio": model["hall_coverage_diagnostic"]["coverage_ratio"],
        "geometry_digest": model["geometry_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

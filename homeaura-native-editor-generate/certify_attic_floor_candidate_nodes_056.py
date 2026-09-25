from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Point, box, shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_R1_SOUTH_CANDIDATES_055"
VECTOR = BASE / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_FLOOR_CANDIDATE_NODES_056"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_FLOOR_CANDIDATE_NODES_056.zip"
VOID_BOX_GRID = (99, 57, 131, 92)
NODES = [(x, 93) for x in range(101, 129)]
PX = 8.503937007874017


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D056 is append-only")
    source_bytes = (SOURCE / "attic_r1_south_candidates.json").read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    vector_bytes = VECTOR.read_bytes()
    vector = json.loads(vector_bytes.decode("utf-8"))
    allowed = shape(vector["hall_source_contract"]["routing_draft_allowed_floor_geojson"])
    void = box(*(value * 100 for value in VOID_BOX_GRID))
    records = []
    for x, y in NODES:
        point = Point(x * 100, y * 100)
        records.append({
            "candidate_node_id": f"ATTIC-FLOOR-CANDIDATE-{x}",
            "point_grid": [x, y],
            "point_mm": [x * 100, y * 100],
            "geometric_relation": "ONE_GRID_ROW_BELOW_CONSERVATIVE_VOID",
            "inside_or_on_vector_draft_floor": allowed.covers(point),
            "centerline_distance_to_vector_draft_floor_boundary_mm": allowed.boundary.distance(point),
            "centerline_distance_to_conservative_void_mm": void.distance(point),
            "conservative_void_contact": point.intersects(void),
            "route_id": None,
            "leg": None,
            "assigned_as_gate": False,
            "published_as_pipe_geometry": False,
        })
    if len({tuple(item["point_grid"]) for item in records}) != 28:
        raise RuntimeError("duplicate node")
    if not all(item["inside_or_on_vector_draft_floor"] and not item["conservative_void_contact"] for item in records):
        raise RuntimeError("candidate containment")
    if not all(math.isclose(item["centerline_distance_to_vector_draft_floor_boundary_mm"], 100.0, abs_tol=1e-6) and math.isclose(item["centerline_distance_to_conservative_void_mm"], 100.0, abs_tol=1e-6) for item in records):
        raise RuntimeError("candidate distance")
    model = {
        "schema": "homeaura-attic-floor-candidate-node-set-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_FLOOR_CANDIDATE_NODES_056",
        "status": "FLOOR_CONFIRMED_CANDIDATE_NODE_SET_PASS_NO_INTERFACE_OWNERSHIP",
        "source_D055_artifact_id": source["artifact_id"],
        "source_D055_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_D055_disposition": "SUPERSEDED_BY_STRICT_NO_INTERFACE_CLASSIFICATION",
        "source_D054_disposition": "REWORK_SOURCE_CONTAINED_CANDIDATE_MAPPING_NOT_PROVEN_INTERFACE",
        "vector_floor_contract_id": vector["artifact_id"],
        "vector_floor_contract_sha256": hashlib.sha256(vector_bytes).hexdigest().upper(),
        "source_pdf_sha256": vector["source_pdf_sha256"],
        "source_pdf_page": vector["source_pdf_page"],
        "source_status": "VECTOR_TRACED_DRAFT_NOT_SURVEYED",
        "pipe_clearance_erosion_applied": False,
        "candidate_node_count": len(records),
        "future_leg_count": 26,
        "future_joint_router_selection_rule": "SELECT_26_OF_28_ONLY_AFTER_PHYSICAL_INTERFACE_AND_FULL_FLOOR_DOMAIN_ARE_CONFIRMED",
        "candidate_nodes": records,
        "adjacent_node_spacing_mm": 100,
        "minimum_centerline_distance_to_draft_floor_boundary_mm": min(item["centerline_distance_to_vector_draft_floor_boundary_mm"] for item in records),
        "minimum_centerline_distance_to_conservative_void_mm": min(item["centerline_distance_to_conservative_void_mm"] for item in records),
        "conservative_void_contact_count": sum(item["conservative_void_contact"] for item in records),
        "assigned_gate_count": 0,
        "route_connection_count": 0,
        "published_pipe_geometry_count": 0,
        "full_route_count": 0,
        "r1_interface_status": "NOT_EVALUATED",
        "riser_chase_status": "NOT_EVALUATED",
        "slab_penetration_status": "NOT_EVALUATED",
        "collector_interface_status": "NOT_EVALUATED",
        "wall_crossing_status": "NOT_EVALUATED",
        "threshold_ownership": "NOT_EVALUATED",
        "physical_3d_packing": "NOT_EVALUATED",
        "hydraulics": "NOT_EVALUATED",
        "complete_40_80m_validation": "NOT_EVALUATED",
        "global_route_contacts": "NOT_EVALUATED_NO_NEW_ROUTES",
        "result": "PASS_VECTOR_DRAFT_CONTAINMENT_REWORK_GATE_ASSIGNMENT_AND_FULL_ROUTING",
    }
    model["contract_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "candidate_node_count": 28,
        "future_leg_count": 26,
        "unique_node_count": 28,
        "all_nodes_on_100mm_grid": True,
        "all_nodes_in_x_order": [item["point_grid"][0] for item in records] == list(range(101, 129)),
        "all_nodes_inside_vector_draft_floor": True,
        "minimum_boundary_distance_mm": model["minimum_centerline_distance_to_draft_floor_boundary_mm"],
        "minimum_void_distance_mm": model["minimum_centerline_distance_to_conservative_void_mm"],
        "void_contact_count": 0,
        "assigned_gate_count": 0,
        "route_connection_count": 0,
        "published_pipe_geometry_count": 0,
        "full_route_count": 0,
        "result": model["result"],
    }
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_floor_candidate_nodes.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    for source_name, target_name in (("attic_r1_south_candidates_overlay.png", "attic_floor_candidate_nodes_overlay.png"), ("attic_r1_south_candidates_pipes_only.png", "attic_floor_candidate_nodes_pipes_only.png")):
        image = Image.open(SOURCE / source_name).convert("RGB")
        canvas = ImageDraw.Draw(image, "RGBA")
        canvas.rectangle((0, 0, image.width, 200), fill="#071A21")
        canvas.text((28, 10), "D056 · МАНСАРДА · 28 УЗЛОВ ПОЛА БЕЗ ИНТЕРФЕЙСА R1", font=font(23, True), fill="white")
        canvas.text((28, 49), "x=101…128, y=93 · 100 мм от draft-границы пола · 100 мм от conservative-проёма", font=font(15), fill="#A7EEE7")
        canvas.text((28, 81), "Кандидаты для будущего выбора 26 из 28 · назначенных ворот/соединений/новых труб: 0", font=font(15, True), fill="#F3D58C")
        canvas.text((28, 113), "ЭТО НЕ ГРАНЬ R1, НЕ ПРОХОД ПЕРЕКРЫТИЯ И НЕ ПОДТВЕРЖДЁННАЯ ТРАНЗИТНАЯ ЛЕНТА", font=font(14, True), fill="#FFB2B2")
        canvas.text((28, 145), "R1/СТОЯК/СТЕНЫ/3D-УПАКОВКА/ГИДРАВЛИКА/ПОЛНЫЕ МАРШРУТЫ: NOT EVALUATED", font=font(14, True), fill="#FFB2B2")
        image.save(OUTPUT / target_name)
    (OUTPUT / "report.md").write_text(
        "# D056 — 28 подтверждённых узлов пола без интерфейса R1\n\n"
        "Подтверждён только геометрический факт: 28 узлов x=101…128, y=93 находятся внутри чернового векторного пола D047, не касаются conservative-проёма и имеют осевое расстояние 100 мм до обеих границ. "
        "Они образуют пул для будущего совместного выбора 26 из 28 после подтверждения физического интерфейса.\n\n"
        "Узлы не являются воротами, проходами перекрытия или трубами. Владелец контура и тип ноги не назначены. D054 сохранён как исторический поиск, но его положительное назначение интерфейса отклонено.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "contract_digest": model["contract_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "candidate_nodes": 28,
        "future_legs": 26,
        "assigned_gates": 0,
        "published_pipe_geometry": 0,
        "boundary_mm": model["minimum_centerline_distance_to_draft_floor_boundary_mm"],
        "void_mm": model["minimum_centerline_distance_to_conservative_void_mm"],
        "contract_digest": model["contract_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Point, shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_R1_SPLIT_INTERFACE_054"
VECTOR = BASE / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
IMAGE_SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_R1_CONTRACT_REPAIRED_052"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_R1_SOUTH_CANDIDATES_055"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_R1_SOUTH_CANDIDATES_055.zip"
PX = 8.503937007874017
CANDIDATES = [(x, 93) for x in range(101, 129)]


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
        raise FileExistsError("D055 is append-only")
    source_bytes = (SOURCE / "attic_r1_split_interface.json").read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    vector_bytes = VECTOR.read_bytes()
    vector = json.loads(vector_bytes.decode("utf-8"))
    allowed = shape(vector["hall_source_contract"]["routing_draft_allowed_floor_geojson"])
    records = []
    for point in CANDIDATES:
        metric = Point(point[0] * 100, point[1] * 100)
        records.append({
            "candidate_id": f"SOUTH-CANDIDATE-{point[0]}",
            "point_grid": list(point),
            "point_mm": [point[0] * 100, point[1] * 100],
            "inside_or_on_routing_draft_floor": allowed.covers(metric),
            "centerline_distance_to_routing_draft_floor_boundary_mm": allowed.boundary.distance(metric),
            "gate_owner_route_id": None,
            "gate_owner_leg": None,
            "pipe_geometry_materialized": False,
        })
    if not all(item["inside_or_on_routing_draft_floor"] for item in records):
        raise RuntimeError("candidate outside D047 floor")
    model = {
        "schema": "homeaura-attic-r1-south-candidate-contract-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_R1_SOUTH_CANDIDATES_055",
        "status": "SOUTH_PLANAR_FLOOR_CANDIDATES_PASS_R1_PHYSICAL_CONNECTION_BLOCKED_SOURCE_CONTRACT",
        "source_D054_artifact_id": source["artifact_id"],
        "source_D054_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_D054_disposition": "HISTORICAL_OVERASSERTIVE_GATE_OWNERSHIP_AND_R1_FACE_NOT_ACCEPTED",
        "vector_floor_contract_id": vector["artifact_id"],
        "vector_floor_contract_sha256": hashlib.sha256(vector_bytes).hexdigest().upper(),
        "source_pdf_sha256": vector["source_pdf_sha256"],
        "source_pdf_page": vector["source_pdf_page"],
        "south_candidate_basis": {
            "artificial_void_clipped_north_edge_y_mm": 9200,
            "first_100mm_grid_row_inside_floor_y_grid": 93,
            "candidate_x_grid_inclusive": [101, 128],
            "candidate_count": len(records),
            "required_future_unbuilt_leg_count": 22,
            "selection_spare_candidate_count": len(records) - 22,
        },
        "east_existing_bounded_interface": {
            "status": "TWO_LOCAL_FRAGMENTS_PASS_NOT_EXTENDABLE_BANK",
            "route_ids": ["A-C09", "A-C08"],
            "gate_points_grid": [[132, 57], [132, 58], [132, 59], [132, 60]],
        },
        "south_landing_candidate_interface": {
            "planar_floor_status": "SOURCE_CONFIRMED_D047_VECTOR_DRAFT_NOT_SURVEYED",
            "r1_physical_connection_status": "UNCONFIRMED_NO_SOURCE_EVIDENCE_OF_RISER_TO_SOUTH_LANDING_FANOUT",
            "gate_ownership_status": "UNASSIGNED_SOLVER_MUST_SELECT_22_OF_28",
            "pipe_geometry_status": "NOT_MATERIALIZED",
            "candidates": records,
        },
        "north_interface_status": "SOURCE_UNCONFIRMED",
        "west_interface_status": "SOURCE_UNCONFIRMED",
        "remaining_east_interface_status": "SOURCE_UNCONFIRMED",
        "logical_riser_assembly_count": 1,
        "physical_riser_chase_selected": False,
        "physical_3d_fanout_capacity": "NOT_EVALUATED",
        "current_hall_body_status": "REOPEN_ONLY_IF_SOUTH_PHYSICAL_CONNECTION_IS_CONFIRMED",
        "current_hall_body_route_ids_at_risk": ["A-C05", "A-C06", "A-C07"],
        "new_gate_ownership_count": 0,
        "new_pipe_geometry_count": 0,
        "complete_circuit_count": 0,
        "full_attic_routes_claimed": False,
        "blocking_external_evidence": "PHYSICAL_R1_TO_SOUTH_LANDING_CONNECTION_OR_EQUIVALENT_STRUCTURAL_PENETRATION_NOT_PRESENT_IN_SUPPLIED_PDF",
        "safe_work_remaining_without_owner_evidence": [
            "TRACE_FULL_ATTIC_FINISH_FLOOR_UNION_AND_WALL_SOLIDS",
            "BUILD_GLOBAL_26_LEG_SOLVER_WITH_CANDIDATE_SELECTION_AND_RESIDUAL_MIN_CUT",
            "PRECOMPUTE_HALL_BODY_REPARTITION_SCENARIOS_WITHOUT_PUBLICATION",
        ],
        "result": "PASS_PLANAR_CANDIDATE_NODE_SET_BLOCKED_PHYSICAL_RISER_CONNECTION",
    }
    model["contract_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "candidate_count": len(records),
        "required_candidate_count": 22,
        "spare_count": 6,
        "all_candidates_inside_vector_draft_floor": True,
        "minimum_candidate_boundary_distance_mm": min(item["centerline_distance_to_routing_draft_floor_boundary_mm"] for item in records),
        "new_gate_ownership_count": 0,
        "new_pipe_geometry_count": 0,
        "physical_r1_connection_status": "UNCONFIRMED",
        "result": model["result"],
    }
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_r1_south_candidates.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    for source_name, target_name in (("attic_r1_contract_repaired_overlay.png", "attic_r1_south_candidates_overlay.png"), ("attic_r1_contract_repaired_pipes_only.png", "attic_r1_south_candidates_pipes_only.png")):
        image = Image.open(IMAGE_SOURCE / source_name).convert("RGB")
        canvas = ImageDraw.Draw(image, "RGBA")
        canvas.rectangle((0, 0, image.width, 192), fill="#071A21")
        canvas.text((28, 10), "D055 · МАНСАРДА · КАНДИДАТЫ ЮЖНОЙ ЛИНИИ R1", font=font(23, True), fill="white")
        canvas.text((28, 49), "28 точек x=101…128, y=93 подтверждены только как ПОЛ МАНСАРДЫ · владельцы не назначены", font=font(15), fill="#A7EEE7")
        canvas.text((28, 81), "Будущий решатель должен выбрать 22 точки · новые трубы/ворота: 0 · тела не изменены", font=font(15, True), fill="#F3D58C")
        canvas.text((28, 113), "ФИЗИЧЕСКАЯ СВЯЗЬ ВЕРТИКАЛЬНОГО R1 С ЮЖНОЙ ЛИНИЕЙ НЕ ПОКАЗАНА В PDF", font=font(14, True), fill="#FFB2B2")
        canvas.text((28, 145), "D054 СОХРАНЁН КАК ЧЕРНОВОЙ ПОИСК, НО ЕГО НАЗНАЧЕНИЕ 22 ВОРОТ НЕ ПРИНЯТО", font=font(14, True), fill="#FFB2B2")
        for point in CANDIDATES:
            px, py = round(point[0] * PX), round(point[1] * PX)
            canvas.ellipse((px - 6, py - 6, px + 6, py + 6), fill="#F5C242", outline="#7A5C00", width=2)
        canvas.text((round(101 * PX), round(93 * PX) - 30), "28 КАНДИДАТОВ · НЕ ВОРОТА", font=font(13, True), fill="#7A5C00", stroke_width=3, stroke_fill="white")
        image.save(OUTPUT / target_name)
    (OUTPUT / "report.md").write_text(
        "# D055 — кандидаты южней линии, без назначения ворот\n\n"
        "D047 подтверждает, что точки сетки x=101…128 на строке y=93 находятся на черновом векторном полу мансарды южнее проёма. Это 28 допустимых планарных кандидатов; будущему решателю достаточно выбрать 22. "
        "Но supplied PDF не доказывает физическую связь вертикального стояка R1 с этой линией. Поэтому ни одна точка не назначена контуру и ни одна труба не опубликована.\n\n"
        "D054 остаётся историческим поисковым вариантом, но его владение 22 воротами и название SOUTH face не приняты. До подтверждения конструктивного выхода R1 положительная разводка блокирована исходным контрактом. "
        "Без этого подтверждения безопасно продолжать трассировку остальных полигонов и подготовку глобального решателя.\n",
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
        "candidates": len(records),
        "required": 22,
        "ownership": 0,
        "new_pipe_geometry": 0,
        "minimum_boundary_mm": validation["minimum_candidate_boundary_distance_mm"],
        "contract_digest": model["contract_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

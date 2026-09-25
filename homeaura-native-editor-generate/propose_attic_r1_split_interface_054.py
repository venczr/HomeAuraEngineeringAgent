from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Point, shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_AUDIT = BASE / "HA_TWO_FLOOR_ATTIC_R1_CORRIDOR_AUDIT_053" / "attic_r1_corridor_audit.json"
SOURCE_BODY = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
SOURCE_VECTOR = BASE / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
SOURCE_R1 = BASE / "HA_TWO_FLOOR_ATTIC_R1_CONTRACT_REPAIRED_052" / "attic_r1_contract.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_R1_SPLIT_INTERFACE_054"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_R1_SPLIT_INTERFACE_054.zip"
PX = 8.503937007874017

EAST_MAPPING = [
    ("A-C09", "SUPPLY", (132, 57)), ("A-C09", "RETURN", (132, 58)),
    ("A-C08", "SUPPLY", (132, 59)), ("A-C08", "RETURN", (132, 60)),
]
SOUTH_ORDER = ["A-C01", "A-C02", "A-C03", "A-C04", "A-C05", "A-C06", "A-C07", "A-C10", "A-C11", "A-C12", "A-C13"]
SOUTH_MAPPING = []
for index, route_id in enumerate(SOUTH_ORDER):
    x = 101 + index * 2
    SOUTH_MAPPING.extend(((route_id, "SUPPLY", (x, 93)), (route_id, "RETURN", (x + 1, 93))))
RIBBON_BOUNDS_GRID = (101, 93, 122, 168)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def mm(point):
    return point[0] * 100, point[1] * 100


def draw(body, vector, model, target: Path, pipes_only: bool):
    source_name = "attic_hall_refined_pipes_only.png" if pipes_only else "attic_hall_refined_overlay.png"
    image = Image.open(SOURCE_BODY.parent / source_name).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 185), fill="#071A21")
    canvas.text((28, 10), "D054 · МАНСАРДА · РАЗДЕЛЁННЫЙ ИНТЕРФЕЙС R1", font=font(23, True), fill="white")
    canvas.text((28, 49), "4 восточные точки: A-C09/A-C08 · 22 южные точки: остальные 11 контуров", font=font(15), fill="#A7EEE7")
    canvas.text((28, 81), "Южный пучок x=101…122, y=93…168 находится внутри векторного холла и не попадает в проём", font=font(15, True), fill="#F3D58C")
    canvas.text((28, 113), "A-C05/A-C06/A-C07 ПОДЛЕЖАТ ПЕРЕРАЗБИВКЕ: их нынешние тела заняли будущий транзитный пучок", font=font(14, True), fill="#FFB2B2")
    canvas.text((28, 145), "ПЛАНАРНЫЙ ИНТЕРФЕЙС DRAFT · ФИЗИЧЕСКАЯ 3D-УПАКОВКА/ПЕРЕКРЫТИЕ/ГИДРАВЛИКА НЕ ПРИНЯТЫ", font=font(14, True), fill="#FFB2B2")

    def p(point):
        return round(point[0] * PX), round(point[1] * PX)

    x0, y0, x1, y1 = RIBBON_BOUNDS_GRID
    canvas.rectangle((*p((x0, y0)), *p((x1, y1))), fill="#00A7A016", outline="#00877F", width=4)
    for x in range(x0, x1 + 1):
        canvas.line((*p((x, y0)), *p((x, y1))), fill="#00A7A055", width=2)
    canvas.text((p((101, 146))[0] + 8, p((101, 146))[1]), "22 ОТДЕЛЬНЫЕ\nТРАНЗИТНЫЕ ЛИНИИ\n100 мм", font=font(14, True), fill="#006B66", stroke_width=3, stroke_fill="white")

    for route_id, leg, gate in EAST_MAPPING:
        gx, gy = p(gate)
        canvas.ellipse((gx - 6, gy - 6, gx + 6, gy + 6), fill="#00A7A0", outline="white", width=2)
    for route_id, leg, gate in SOUTH_MAPPING:
        gx, gy = p(gate)
        colour = "#159A5B" if route_id.startswith("A-C0") and route_id in {"A-C01", "A-C02", "A-C03", "A-C04"} else "#D97706" if route_id in {"A-C05", "A-C06", "A-C07"} else "#8B5CF6"
        canvas.ellipse((gx - 6, gy - 6, gx + 6, gy + 6), fill=colour, outline="white", width=2)
    canvas.text((p((101, 93))[0], p((101, 93))[1] - 28), "ЮЖНЫЙ БАНК: 22 ТОЧКИ", font=font(13, True), fill="#006B66", stroke_width=3, stroke_fill="white")
    canvas.text((p((132, 57))[0] + 12, p((132, 57))[1] - 10), "ВОСТОЧНЫЙ БАНК: 4", font=font(13, True), fill="#006B66", stroke_width=3, stroke_fill="white")
    image.save(target)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D054 is append-only")
    audit_bytes = SOURCE_AUDIT.read_bytes()
    body_bytes = SOURCE_BODY.read_bytes()
    vector_bytes = SOURCE_VECTOR.read_bytes()
    r1_bytes = SOURCE_R1.read_bytes()
    audit = json.loads(audit_bytes.decode("utf-8"))
    body = json.loads(body_bytes.decode("utf-8"))
    vector = json.loads(vector_bytes.decode("utf-8"))
    r1 = json.loads(r1_bytes.decode("utf-8"))
    allowed = shape(vector["hall_source_contract"]["routing_draft_allowed_floor_geojson"])
    body_lines = {route["route_id"]: LineString([mm(point) for point in route["body_points_grid"]]) for route in body["body_routes"]}

    mapping = []
    for face, rows in (("EAST_OF_VOID", EAST_MAPPING), ("SOUTH_OF_VOID", SOUTH_MAPPING)):
        for route_id, leg, gate in rows:
            point = Point(mm(gate))
            mapping.append({
                "route_id": route_id,
                "leg": leg,
                "gate_id": f"R1-{face}-{route_id}-{leg[0]}",
                "face": face,
                "gate_point_grid": list(gate),
                "gate_point_mm": list(mm(gate)),
                "inside_or_on_routing_draft_allowed_floor": allowed.covers(point) if face == "SOUTH_OF_VOID" else None,
                "centerline_distance_to_allowed_boundary_mm": allowed.boundary.distance(point) if face == "SOUTH_OF_VOID" else None,
            })
    all_points = [tuple(item["gate_point_grid"]) for item in mapping]
    if len(mapping) != 26 or len(set(all_points)) != 26:
        raise RuntimeError("split interface points are not 26 distinct nodes")
    south = [item for item in mapping if item["face"] == "SOUTH_OF_VOID"]
    if not all(item["inside_or_on_routing_draft_allowed_floor"] for item in south):
        raise RuntimeError("south bank leaves vector draft floor")
    min_boundary = min(item["centerline_distance_to_allowed_boundary_mm"] for item in south)
    ribbon_lines = [LineString([mm((x, RIBBON_BOUNDS_GRID[1])), mm((x, RIBBON_BOUNDS_GRID[3]))]) for x in range(RIBBON_BOUNDS_GRID[0], RIBBON_BOUNDS_GRID[2] + 1)]
    if not all(allowed.covers(line) for line in ribbon_lines):
        raise RuntimeError("south ribbon leaves vector draft floor")
    conflicts = []
    for route_id in ("A-C05", "A-C06", "A-C07"):
        for lane_index, line in enumerate(ribbon_lines, start=RIBBON_BOUNDS_GRID[0]):
            if line.intersects(body_lines[route_id]):
                conflicts.append({"route_id": route_id, "lane_x_grid": lane_index})
    affected = sorted({item["route_id"] for item in conflicts})
    model = {
        "schema": "homeaura-attic-r1-split-interface-proposal-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_R1_SPLIT_INTERFACE_054",
        "status": "SOURCE_CONTAINED_SPLIT_INTERFACE_PASS_REWORK_HALL_BODIES_3D_PACKING_AND_GLOBAL_TRANSITS",
        "source_corridor_audit_id": audit["artifact_id"],
        "source_corridor_audit_sha256": hashlib.sha256(audit_bytes).hexdigest().upper(),
        "preferred_body_source_id": body["artifact_id"],
        "preferred_body_source_sha256": hashlib.sha256(body_bytes).hexdigest().upper(),
        "vector_floor_contract_id": vector["artifact_id"],
        "vector_floor_contract_sha256": hashlib.sha256(vector_bytes).hexdigest().upper(),
        "historical_r1_contract_id": r1["artifact_id"],
        "historical_r1_contract_sha256": hashlib.sha256(r1_bytes).hexdigest().upper(),
        "historical_vertical_26_gate_bank_status": "SUPERSEDED_REWORK_BY_D053_CUT_CAPACITY_FAILURE",
        "logical_riser_assembly_count": 1,
        "physical_riser_chase_selected": False,
        "physical_3d_fanout_capacity": "NOT_EVALUATED",
        "shared_pipe_trunk": False,
        "distinct_connection_count": 26,
        "east_face_connection_count": 4,
        "south_face_connection_count": 22,
        "current_split_gate_mapping": mapping,
        "south_face_gate_order": SOUTH_ORDER,
        "south_transit_ribbon_bbox_grid": list(RIBBON_BOUNDS_GRID),
        "south_transit_ribbon_lane_x_grid": list(range(101, 123)),
        "south_transit_ribbon_lane_count": len(ribbon_lines),
        "south_transit_ribbon_spacing_mm": 100,
        "south_gate_minimum_centerline_distance_to_draft_floor_boundary_mm": min_boundary,
        "south_ribbon_inside_vector_draft_floor": True,
        "south_ribbon_void_hit_count": 0,
        "current_hall_body_conflict_count": len(conflicts),
        "current_hall_body_conflicts": conflicts,
        "hall_body_route_ids_requiring_repartition": affected,
        "hall_heat_strategy": "DENSE_TRANSITS_COUNT_AS_HEATED_FLOOR_THEN_REBUILD_ONLY_NATURAL_RESIDUAL_COUNTERFLOW_LOBES",
        "current_body_geometry_modified": False,
        "new_pipe_geometry_published": False,
        "full_route_count": 0,
        "complete_40_80m_validation": "NOT_EVALUATED_NO_NEW_FULL_ROUTES",
        "threshold_ownership": "NOT_EVALUATED_FLATTENED_PDF_AMBIGUOUS",
        "structural_penetration_design": "NOT_EVALUATED",
        "hydraulics_calculated": False,
        "next_acceptance_requirements": [
            "REPARTITION_A-C05_A-C06_A-C07_AROUND_RESERVED_22_LANE_RIBBON",
            "SOLVE_ALL_22_SOUTH_LEGS_JOINTLY_WITH_ZERO_CROSS_TOUCH_OVERLAP",
            "PROVE_EACH_LANE_STAYS_INSIDE_ROUTABLE_BUILDING_DOMAIN_OR_CLASSIFIED_WALL_TRANSIT",
            "PROVE_PHYSICAL_3D_RISER_FANOUT_OR_KEEP_NOT_EVALUATED",
            "RECOMPUTE_HALL_SERVED_UNION_INCLUDING_TRANSITS_BEFORE_ADDING_HALL_BODY",
        ],
        "result": "PASS_SOURCE_CONTAINED_PLANAR_INTERFACE_REWORK_BODY_CORRIDOR_AND_PHYSICAL_RISER",
    }
    model["interface_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "distinct_gate_count": len(set(all_points)),
        "east_gate_count": len(EAST_MAPPING),
        "south_gate_count": len(SOUTH_MAPPING),
        "south_gate_containment_pass": True,
        "south_ribbon_containment_pass": True,
        "south_gate_min_boundary_mm": min_boundary,
        "current_hall_body_conflict_count": len(conflicts),
        "affected_hall_body_ids": affected,
        "new_pipe_geometry_count": 0,
        "full_route_count": 0,
        "result": model["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_r1_split_interface.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(body, vector, model, OUTPUT / "attic_r1_split_interface_overlay.png", False)
    draw(body, vector, model, OUTPUT / "attic_r1_split_interface_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D054 — разделённый планарный интерфейс R1\n\n"
        "Вертикальная колонна из 26 точек больше не используется как глобальная разводка. Четыре верхние точки остаются за A-C09/A-C08 на восточной стороне проёма. "
        "Остальные 22 индивидуальные трубы получают отдельные точки вдоль южной стороны проёма и резервируют параллельную ленту x=101…122 через центральный холл. "
        "Вся южная лента находится внутри векторного чернового полигона D047 и не пересекает физический проём.\n\n"
        "Нынешние тела A-C05/A-C06/A-C07 конфликтуют с этой лентой и не могут сохраняться как неизменяемые. Их нужно переразбить после расчёта покрытия от самих транзитов. "
        "Новые трубы здесь ещё не опубликованы. Физическая трёхмерная укладка 26 труб в стояке, проходы перекрытия и гидравлика остаются NOT_EVALUATED.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "interface_digest": model["interface_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "east": len(EAST_MAPPING),
        "south": len(SOUTH_MAPPING),
        "south_min_boundary_mm": min_boundary,
        "hall_body_conflict_count": len(conflicts),
        "affected": affected,
        "interface_digest": model["interface_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

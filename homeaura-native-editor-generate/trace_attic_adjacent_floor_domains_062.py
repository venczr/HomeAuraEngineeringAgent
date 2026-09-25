from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw
from shapely.geometry import LineString, box, mapping, shape
from shapely.ops import unary_union


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
PDF = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf")
BODY = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
CENTRAL = BASE / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
DIAGNOSTIC = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058" / "attic_plan_space_diagnostic.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062.zip"
SCALE = 35.27777777777778
PX = 8.503937


DOMAINS = {
    "ATTIC_LEFT_NORTH_RECT_DRAFT": {"faces_pt": [130.92, 161.76, 276.00, 232.68], "paths": {"top": 144, "right": 141, "bottom": 138, "left": 147}},
    "ATTIC_LEFT_MIDDLE_RECT_DRAFT": {"faces_pt": [130.92, 238.92, 276.00, 396.48], "paths": {"top": 972, "right": 969, "bottom": 966, "left": 975}},
    "ATTIC_LEFT_SOUTH_RECT_DRAFT": {"faces_pt": [130.92, 402.72, 276.00, 473.04], "paths": {"top": 770, "right": 773, "bottom": 776, "left": 779}},
    "ATTIC_RIGHT_NORTH_RECT_DRAFT": {"faces_pt": [374.40, 161.76, 527.16, 297.36], "paths": {"top": 422, "right": 419, "bottom": 416, "left": 425}},
    "ATTIC_RIGHT_MIDDLE_LEFT_RECT_DRAFT": {"faces_pt": [374.40, 303.48, 445.80, 359.64], "paths": {"top": 901, "right": 904, "bottom": 907, "left": 910}},
    "ATTIC_RIGHT_MIDDLE_RIGHT_RECT_DRAFT": {"faces_pt": [452.04, 303.48, 527.16, 359.64], "paths": {"top": 3, "right": 6, "bottom": 9, "left": 12}},
    "ATTIC_RIGHT_SOUTH_RECT_DRAFT": {"faces_pt": [374.40, 365.88, 527.16, 473.04], "paths": {"top": 274, "right": 277, "bottom": 280, "left": 283}},
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def to_px(point):
    return round(point[0] / 100 * PX), round(point[1] / 100 * PX)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D062 is append-only")
    pdf_bytes = PDF.read_bytes()
    document = pymupdf.open(PDF)
    drawings = document[0].get_drawings(extended=False)
    records = []
    polygons = []
    for domain_id, spec in DOMAINS.items():
        path_records = []
        for face, path_id in spec["paths"].items():
            rect = drawings[path_id]["rect"]
            path_records.append({
                "face": face.upper(),
                "pdf_path_id": path_id,
                "raw_rect_pt": [rect.x0, rect.y0, rect.x1, rect.y1],
            })
        mm = [value * SCALE for value in spec["faces_pt"]]
        polygon = box(*mm)
        polygons.append(polygon)
        records.append({
            "domain_id": domain_id,
            "status": "VECTOR_FINISH_FACE_RECTANGLE_DRAFT_NOT_SURVEYED",
            "finish_face_bbox_pt": spec["faces_pt"],
            "finish_face_bbox_mm": mm,
            "source_path_records": path_records,
            "area_m2": polygon.area / 1_000_000,
            "floor_geojson": mapping(polygon),
            "door_thresholds_included": False,
            "wall_solids_included": False,
            "semantic_room_name": "NOT_ASSIGNED_FROM_OUTLINED_TEXT",
        })
    central_bytes = CENTRAL.read_bytes()
    central = json.loads(central_bytes.decode("utf-8"))
    central_polygon = shape(central["hall_source_contract"]["routing_draft_allowed_floor_geojson"])
    union = unary_union(polygons + [central_polygon])
    body_bytes = BODY.read_bytes()
    body = json.loads(body_bytes.decode("utf-8"))
    body_records = []
    for route in body["body_routes"]:
        line = LineString([(x * 100, y * 100) for x, y in route["body_points_grid"]])
        body_records.append({
            "route_id": route["route_id"],
            "body_length_mm": line.length,
            "known_floor_union_covered_length_mm": line.intersection(union).length,
            "fully_covered_by_known_floor_union": union.covers(line),
        })
    diagnostic_bytes = DIAGNOSTIC.read_bytes()
    diagnostic = json.loads(diagnostic_bytes.decode("utf-8"))
    transit_records = []
    for fragment in diagnostic["diagnostic_planar_fragments"]:
        legs = []
        for leg, key in (("SUPPLY", "supply_transit_points_grid"), ("RETURN", "return_transit_points_grid")):
            line = LineString([(x * 100, y * 100) for x, y in fragment[key]])
            known = line.intersection(union).length
            legs.append({
                "leg": leg,
                "length_mm": line.length,
                "known_floor_union_length_mm": known,
                "unknown_wall_threshold_or_untraced_floor_length_mm": line.length - known,
                "fully_covered_by_known_floor_union": union.covers(line),
            })
        transit_records.append({"route_id": fragment["route_id"], "legs": legs})
    total_transit = sum(leg["length_mm"] for item in transit_records for leg in item["legs"])
    known_transit = sum(leg["known_floor_union_length_mm"] for item in transit_records for leg in item["legs"])
    model = {
        "schema": "homeaura-attic-adjacent-floor-domains-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062",
        "status": "SEVEN_ADJACENT_RECTANGULAR_FLOOR_DOMAINS_VECTOR_DRAFT_PASS_REWORK_THRESHOLDS_WALLS_AND_WHOLE_ATTIC_UNION",
        "source_pdf_path": str(PDF),
        "source_pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest().upper(),
        "source_pdf_page": 1,
        "source_page_size_pt": [document[0].rect.width, document[0].rect.height],
        "pdf_pt_to_model_mm": SCALE,
        "extractor": f"PyMuPDF {pymupdf.__version__}",
        "source_status": "VECTOR_TRACED_DRAFT_NOT_SURVEYED",
        "adjacent_floor_domains": records,
        "adjacent_domain_count": len(records),
        "adjacent_rectangles_area_m2": sum(item.area for item in polygons) / 1_000_000,
        "source_D047_artifact_id": central["artifact_id"],
        "source_D047_sha256": hashlib.sha256(central_bytes).hexdigest().upper(),
        "D047_local_central_floor_area_m2": central_polygon.area / 1_000_000,
        "known_floor_union_geojson": mapping(union),
        "known_floor_union_area_m2": union.area / 1_000_000,
        "known_floor_union_is_complete_whole_attic": False,
        "door_threshold_ownership": "NOT_EVALUATED_FLATTENED_PDF_AMBIGUOUS",
        "wall_transit_solids": "NOT_SERIALIZED_YET",
        "pipe_clearance_erosion_applied": False,
        "source_D050_body_artifact_id": body["artifact_id"],
        "source_D050_body_sha256": hashlib.sha256(body_bytes).hexdigest().upper(),
        "body_known_floor_records": body_records,
        "all_thirteen_bodies_covered_by_known_floor_union": all(item["fully_covered_by_known_floor_union"] for item in body_records),
        "source_D058_artifact_id": diagnostic["artifact_id"],
        "source_D058_sha256": hashlib.sha256(diagnostic_bytes).hexdigest().upper(),
        "diagnostic_transit_domain_records": transit_records,
        "diagnostic_transit_total_length_mm": total_transit,
        "diagnostic_transit_known_floor_union_length_mm": known_transit,
        "diagnostic_transit_unknown_wall_threshold_or_untraced_floor_length_mm": total_transit - known_transit,
        "diagnostic_transit_known_floor_ratio": known_transit / total_transit,
        "new_pipe_geometry_count": 0,
        "current_assigned_R1_gate_count": 0,
        "physical_R1_interface_status": "NOT_EVALUATED",
        "result": "PASS_VECTOR_DRAFT_ROOM_DOMAINS_REWORK_WALL_THRESHOLD_POLYGONS_AND_PHYSICAL_R1_INTERFACE",
    }
    model["contract_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_adjacent_floor_domains.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    image = Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    colours = ["#58C4DD", "#8C6FE8", "#EE6A8A", "#58B58A", "#F3A64A", "#557ED1", "#B85EAE"]
    for record, colour in zip(records, colours):
        x0, y0, x1, y1 = record["finish_face_bbox_mm"]
        canvas.rectangle((*to_px((x0, y0)), *to_px((x1, y1))), fill=colour + "35", outline=colour, width=3)
        canvas.text(to_px((x0 + 100, y0 + 100)), record["domain_id"].replace("ATTIC_", "").replace("_RECT_DRAFT", ""), fill=colour)
    central_px = [to_px(point) for point in central_polygon.exterior.coords]
    canvas.polygon(central_px, fill="#65C18C35", outline="#087F5B")
    canvas.rectangle((0, 0, image.width, 190), fill="#071A21")
    canvas.text((28, 10), "D062 · МАНСАРДА · 7 СОСЕДНИХ ПОЛИГОНОВ ПОЛА ИЗ ВЕКТОРНОГО PDF", fill="white")
    canvas.text((28, 46), f'7 прямоугольников {model["adjacent_rectangles_area_m2"]:.2f} м² + локальный D047 {model["D047_local_central_floor_area_m2"]:.2f} м²', fill="#A7EEE7")
    canvas.text((28, 78), f'Подводы D058: известно {known_transit / 1000:.1f} м из {total_transit / 1000:.1f} м · остальное стены/пороги/неизвлечённый пол', fill="#F3D58C")
    canvas.text((28, 110), "Дверные пороги, полосы стен, полный union мансарды и физический R1: REWORK", fill="#FFB2B2")
    canvas.text((28, 142), "Цветные прямоугольники — finish-face candidates, не обмер и не готовая трасса", fill="#FFB2B2")
    image.save(OUTPUT / "attic_adjacent_floor_domains_overlay.png")
    (OUTPUT / "report.md").write_text(
        "# D062 — соседние полигоны пола мансарды\n\n"
        "Из векторных прямоугольников PDF выделены семь finish-face кандидатов соседних помещений. Для каждой грани записан исходный path ID и raw bbox. "
        "Вместе с локальным D047 они образуют расширенный, но всё ещё неполный union известного пола.\n\n"
        "Дверные пороги и полосы стен не присвоены ни одному помещению. По разрешению владельца трубы могут пересекать стены, но эти участки должны быть классифицированы отдельно. "
        "Новых труб и ворот R1 в D062 нет.\n",
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
        "domains": len(records),
        "known_union_area_m2": model["known_floor_union_area_m2"],
        "all_bodies_covered": model["all_thirteen_bodies_covered_by_known_floor_union"],
        "transit_total_mm": total_transit,
        "transit_known_mm": known_transit,
        "transit_unknown_mm": total_transit-known_transit,
        "known_ratio": known_transit/total_transit,
        "contract_digest": model["contract_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

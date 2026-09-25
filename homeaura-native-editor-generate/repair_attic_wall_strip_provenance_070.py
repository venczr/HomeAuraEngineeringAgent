from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, box, mapping
from shapely.ops import unary_union


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058" / "attic_plan_space_diagnostic.json"
SOURCE_066 = BASE / "HA_TWO_FLOOR_ATTIC_WALL_TRANSIT_AUDIT_066" / "attic_wall_transit_audit.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
PDF = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf")
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_WALL_STRIPS_070"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_WALL_STRIPS_070.zip"
SCALE = 35.27777777777778
PX = 8.503937
AUDIT_Y0_MM = 9300
AUDIT_Y1_MM = 15400
SCREENING_LIMIT_MM = 500


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def rect_record(drawings, path_id: int) -> dict:
    rect = drawings[path_id]["rect"]
    return {"pdf_path_id": path_id, "raw_rect_pt": [rect.x0, rect.y0, rect.x1, rect.y1]}


def to_px(point_mm):
    return round(point_mm[0] / 100 * PX), round(point_mm[1] / 100 * PX)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D070 is append-only")
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    source_066_bytes = SOURCE_066.read_bytes()
    pdf_bytes = PDF.read_bytes()
    page = pymupdf.open(stream=pdf_bytes, filetype="pdf")[0]
    drawings = page.get_drawings()

    hall_path_id = 579
    right_path_ids = [425, 910, 283]
    hall_rect = drawings[hall_path_id]["rect"]
    wall_x0 = hall_rect.x0 * SCALE
    strips = []
    strip_shapes = []
    for path_id in right_path_ids:
        right_rect = drawings[path_id]["rect"]
        y0 = max(AUDIT_Y0_MM, hall_rect.y0 * SCALE, right_rect.y0 * SCALE)
        y1 = min(AUDIT_Y1_MM, hall_rect.y1 * SCALE, right_rect.y1 * SCALE)
        wall_x1 = right_rect.x1 * SCALE
        if y1 <= y0:
            continue
        shape = box(wall_x0, y0, wall_x1, y1)
        strip_shapes.append(shape)
        strips.append({
            "strip_id": f"SOURCED_STRIP_PATH_{path_id}",
            "hall_face_path": rect_record(drawings, hall_path_id),
            "right_room_face_path": rect_record(drawings, path_id),
            "selected_hall_face": {"axis": "X", "raw_pdf_pt": hall_rect.x0, "mm": wall_x0},
            "selected_right_face": {"axis": "X", "raw_pdf_pt": right_rect.x1, "mm": wall_x1},
            "source_y_overlap_before_audit_clip_mm": [max(hall_rect.y0, right_rect.y0) * SCALE, min(hall_rect.y1, right_rect.y1) * SCALE],
            "D058_contact_audit_clip_mm": [AUDIT_Y0_MM, AUDIT_Y1_MM],
            "effective_bbox_mm": [wall_x0, y0, wall_x1, y1],
            "effective_geojson": mapping(shape),
        })
    wall_union = unary_union(strip_shapes)

    records = []
    for fragment in source["diagnostic_planar_fragments"]:
        legs = []
        for leg, key in (("SUPPLY", "supply_transit_points_grid"), ("RETURN", "return_transit_points_grid")):
            points = fragment[key]
            parallel = 0.0
            perpendicular = 0.0
            segment_records = []
            for a, b in zip(points, points[1:]):
                segment = LineString([(a[0] * 100, a[1] * 100), (b[0] * 100, b[1] * 100)])
                for strip in strips:
                    intersection = segment.intersection(box(*strip["effective_bbox_mm"]))
                    if intersection.length <= 1e-9:
                        continue
                    orientation = "PARALLEL_TO_SOURCED_WALL_FACE" if a[0] == b[0] else "PERPENDICULAR_TO_SOURCED_WALL_FACE"
                    if orientation.startswith("PARALLEL"):
                        parallel += intersection.length
                    else:
                        perpendicular += intersection.length
                    segment_records.append({
                        "segment_grid": [a, b],
                        "strip_id": strip["strip_id"],
                        "intersection_length_mm": intersection.length,
                        "orientation": orientation,
                    })
            if parallel > SCREENING_LIMIT_MM:
                result = "REWORK_LONGITUDINAL_SOURCED_STRIP_RUN"
            elif perpendicular > 0:
                result = "PERPENDICULAR_CROSSING_CANDIDATE_OPENING_AND_STRUCTURE_NOT_RESOLVED"
            else:
                result = "NO_SOURCED_STRIP_CONTACT_IN_AUDIT_CLIP"
            legs.append({
                "leg": leg,
                "parallel_sourced_strip_length_mm": parallel,
                "perpendicular_sourced_strip_length_mm": perpendicular,
                "segment_records": segment_records,
                "result": result,
            })
        records.append({"route_id": fragment["route_id"], "legs": legs})

    long_runs = [{"route_id": row["route_id"], **leg} for row in records for leg in row["legs"] if leg["parallel_sourced_strip_length_mm"] > SCREENING_LIMIT_MM]
    perpendicular = [{"route_id": row["route_id"], **leg} for row in records for leg in row["legs"] if leg["perpendicular_sourced_strip_length_mm"] > 0 and leg["parallel_sourced_strip_length_mm"] <= SCREENING_LIMIT_MM]
    model = {
        "schema": "homeaura-attic-sourced-wall-strip-audit-0.2",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_WALL_STRIPS_070",
        "status": "D058_GEOMETRY_PRESERVED_THREE_SOURCED_STRIPS_REWORK_LONGITUDINAL_A12_A13_LEGS",
        "source_D058_artifact_id": source["artifact_id"],
        "source_D058_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_D066_artifact_id": "HA_TWO_FLOOR_ATTIC_WALL_TRANSIT_AUDIT_066",
        "source_D066_sha256": hashlib.sha256(source_066_bytes).hexdigest().upper(),
        "source_D066_disposition": "SUPERSEDED_SINGLE_RECTANGLE_AND_AMBIGUOUS_HALL_PATH_PROVENANCE",
        "source_pdf_path": str(PDF),
        "source_pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest().upper(),
        "source_pdf_page": 1,
        "extractor": f"PyMuPDF {pymupdf.__version__}",
        "hall_face_provenance": {"pdf_path_id": hall_path_id, "selected_face": "X_MIN", "record": rect_record(drawings, hall_path_id)},
        "right_face_path_ids": right_path_ids,
        "sourced_strip_count": len(strips),
        "sourced_strips": strips,
        "sourced_strip_union_geojson": mapping(wall_union),
        "y_range_semantics": "SOURCE_FACE_OVERLAP_INTERSECTED_WITH_D058_CONTACT_AUDIT_CLIP",
        "D058_contact_audit_clip_mm": [AUDIT_Y0_MM, AUDIT_Y1_MM],
        "audit_clip_is_source_wall_extent": False,
        "door_and_threshold_openings_subtracted": False,
        "wall_strip_status": "VECTOR_FACE_PAIR_DRAFT_NOT_SURVEYED_GAPS_AND_OPENINGS_UNRESOLVED",
        "owner_wall_crossing_permission": True,
        "owner_permission_does_not_prove_opening_or_longitudinal_route": True,
        "screening_threshold_mm": SCREENING_LIMIT_MM,
        "screening_threshold_source": "PROJECT_DIAGNOSTIC_INFERENCE_NOT_NORMATIVE_OR_OWNER_RULE",
        "route_leg_records": records,
        "longitudinal_rework_leg_count": len(long_runs),
        "longitudinal_rework_legs": long_runs,
        "perpendicular_crossing_candidate_count": len(perpendicular),
        "perpendicular_crossing_candidates": perpendicular,
        "A_C13_return_classification": next(item for item in perpendicular if item["route_id"] == "A-C13" and item["leg"] == "RETURN"),
        "total_longitudinal_sourced_strip_length_mm": sum(item["parallel_sourced_strip_length_mm"] for item in long_runs),
        "geometry_modified": False,
        "new_pipe_geometry_count": 0,
        "approved_pipe_geometry_count": 0,
        "current_assigned_R1_gate_count": 0,
        "physical_R1_interface_status": "NOT_EVALUATED",
        "result": "FAIL_D058_LONGITUDINAL_STRIP_CLASSIFICATION_REWORK_A12_SUPPLY_RETURN_AND_A13_SUPPLY",
    }
    model["audit_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_sourced_wall_strip_audit.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "source_D058_geometry.json").write_bytes(source_bytes)

    image = Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    for strip in strips:
        x0, y0, x1, y1 = strip["effective_bbox_mm"]
        canvas.rectangle((*to_px((x0, y0)), *to_px((x1, y1))), fill="#D5000055", outline="#9B0000", width=4)
    for item in long_runs:
        for record in item["segment_records"]:
            a, b = record["segment_grid"]
            canvas.line((to_px((a[0]*100, a[1]*100)), to_px((b[0]*100, b[1]*100))), fill="#9B0000", width=7)
    canvas.rectangle((0, 0, image.width, 190), fill="#071A21")
    canvas.text((28, 10), "D070 · ТРИ ПРОСЛЕЖЕННЫЕ ПОЛОСЫ ПЕРЕГОРОДКИ", font=font(23, True), fill="white")
    canvas.text((28, 48), "Левая грань: только PDF path 579 · правые грани: paths 425 / 910 / 283", font=font(15), fill="#A7EEE7")
    canvas.text((28, 80), f"Продольных ног REWORK: {len(long_runs)} · в полосах {model['total_longitudinal_sourced_strip_length_mm']/1000:.2f} м", font=font(15, True), fill="#F3D58C")
    canvas.text((28, 112), "A-C12 S/R и A-C13 S — вдоль стены; A-C13 R — только поперечный кандидат", font=font(14, True), fill="#FFB2B2")
    canvas.text((28, 143), "Красные полосы ограничены реальными диапазонами PDF; промежутки и дверные проёмы НЕ РАЗРЕШЕНЫ", font=font(13), fill="#E8F0F2")
    canvas.text((28, 168), "D058 не изменён · новых труб и ворот нет · физический R1 не оценён", font=font(12), fill="#E8F0F2")
    image.save(OUTPUT / "attic_sourced_wall_strips_overlay.png")

    (OUTPUT / "report.md").write_text(
        "# D070 — аудит по прослеженным полосам перегородки\n\n"
        "Вместо одного условного прямоугольника использованы три полосы, каждая построена по одной общей грани path 579 и своей противоположной грани paths 425, 910 или 283. "
        "Диапазон 9300–15400 мм явно является окном аудита диагностических ног D058, а не заявленной высотой стены.\n\n"
        "Длинные продольные части A-C12 supply/return и A-C13 supply остаются REWORK. A-C13 return классифицирована отдельно как короткий поперечный кандидат; наличие реального проёма, порога, гильзы и конструкции ещё не доказано.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "audit_digest": model["audit_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "strips": len(strips), "longitudinal": [(item["route_id"], item["leg"], item["parallel_sourced_strip_length_mm"]) for item in long_runs], "perpendicular": [(item["route_id"], item["leg"]) for item in perpendicular], "digest": model["audit_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

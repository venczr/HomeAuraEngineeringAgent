from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
PDF = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf")
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_WALL_TRANSIT_AUDIT_066" / "attic_wall_transit_audit.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_PARTITION_OPENING_067"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_PARTITION_OPENING_067.zip"
SCALE = 35.27777777777778
PX = 8.503937
PATHS = {"HALL_FACE_ABOVE": 1559, "HALL_FACE_BELOW": 1556, "ROOM_FACE_ABOVE": 1586, "ROOM_FACE_BELOW": 1589}


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def to_px(point_grid):
    return round(point_grid[0] * PX), round(point_grid[1] * PX)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D067 is append-only")
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    pdf_bytes = PDF.read_bytes()
    document = pymupdf.open(PDF)
    drawings = document[0].get_drawings(extended=False)
    raw = {}
    for name, path_id in PATHS.items():
        rect = drawings[path_id]["rect"]
        raw[name] = {"pdf_path_id": path_id, "raw_rect_pt": [rect.x0, rect.y0, rect.x1, rect.y1]}
    hall_above_end = raw["HALL_FACE_ABOVE"]["raw_rect_pt"][3]
    hall_below_start = raw["HALL_FACE_BELOW"]["raw_rect_pt"][1]
    room_above_end = raw["ROOM_FACE_ABOVE"]["raw_rect_pt"][3]
    room_below_start = raw["ROOM_FACE_BELOW"]["raw_rect_pt"][1]
    if max(abs(hall_above_end - room_above_end), abs(hall_below_start - room_below_start)) > 0.001:
        raise RuntimeError("opposing wall face gap does not reconcile")
    opening_y0_pt = max(hall_above_end, room_above_end)
    opening_y1_pt = min(hall_below_start, room_below_start)
    opening = {
        "opening_id": "ATTIC_CENTRAL_RIGHT_LOWER_MATCHED_FACE_GAP_067",
        "status": "MATCHED_OPPOSING_VECTOR_FACE_GAP_PASS_THRESHOLD_OWNERSHIP_NOT_EVALUATED",
        "wall_face_x_pt": [368.16, 374.40],
        "opening_y_pt": [opening_y0_pt, opening_y1_pt],
        "opening_bbox_mm": [368.16 * SCALE, opening_y0_pt * SCALE, 374.40 * SCALE, opening_y1_pt * SCALE],
        "opening_clear_width_along_wall_mm": (opening_y1_pt - opening_y0_pt) * SCALE,
        "wall_thickness_between_selected_faces_mm": (374.40 - 368.16) * SCALE,
        "source_paths": raw,
        "door_leaf_semantics": "NOT_EVALUATED_FLATTENED_PDF",
        "threshold_floor_ownership": "NOT_EVALUATED",
        "pipe_crossing_candidate_status": "GEOMETRIC_OPENING_CANDIDATE_OWNER_WALL_CROSSING_PERMISSION_EXISTS_NOT_YET_ROUTED",
        "longitudinal_pipe_run_allowed": False,
    }
    model = {
        "schema": "homeaura-attic-partition-opening-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_PARTITION_OPENING_067",
        "status": "ONE_MATCHED_PARTITION_FACE_GAP_PASS_REWORK_UPPER_OPENINGS_THRESHOLD_AND_REROUTING",
        "source_pdf_path": str(PDF),
        "source_pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest().upper(),
        "source_pdf_page": 1,
        "extractor": f"PyMuPDF {pymupdf.__version__}",
        "source_D066_artifact_id": source["artifact_id"],
        "source_D066_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_D066_wall_band_id": source["draft_wall_band_id"],
        "confirmed_matched_opening_count": 1,
        "matched_opening": opening,
        "upper_face_gap_status": "NOT_MATCHED_ACROSS_OPPOSING_FACES_INTERNAL_PARTITIONS_CHANGE",
        "new_pipe_geometry_count": 0,
        "current_assigned_R1_gate_count": 0,
        "physical_R1_interface_status": "NOT_EVALUATED",
        "A_C12_A_C13_rerouting_status": "NOT_ROUTED_USE_OPENING_AS_CONSTRAINT_CANDIDATE",
        "result": "PASS_ONE_VECTOR_OPENING_CANDIDATE_REWORK_CORRIDOR_AND_PHYSICAL_INTERFACE",
    }
    model["contract_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_partition_opening.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    image = Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    x0, y0, x1, y1 = opening["opening_bbox_mm"]
    canvas.rectangle((*to_px((x0 / 100, y0 / 100)), *to_px((x1 / 100, y1 / 100))), fill="#00B89466", outline="#006B54", width=5)
    canvas.text(to_px((x0 / 100 - 11, y0 / 100 + 2)), "СОВПАВШИЙ РАЗРЫВ 897 мм", font=font(10, True), fill="#006B54", stroke_width=2, stroke_fill="white")
    canvas.rectangle((0, 0, image.width, 188), fill="#071A21")
    canvas.text((28, 10), "D067 · МАНСАРДА · ПОДТВЕРЖДЁННЫЙ РАЗРЫВ ПЕРЕГОРОДКИ", font=font(23, True), fill="white")
    canvas.text((28, 49), f'Обе противоположные finish-face дают один интервал: {opening["opening_clear_width_along_wall_mm"]:.1f} мм', font=font(15), fill="#A7EEE7")
    canvas.text((28, 81), f'Черновая толщина между выбранными гранями: {opening["wall_thickness_between_selected_faces_mm"]:.1f} мм', font=font(15, True), fill="#F3D58C")
    canvas.text((28, 113), "Это кандидат поперечного прохода, а не разрешение вести трубу вдоль стены", font=font(14, True), fill="#FFB2B2")
    canvas.text((28, 141), "Порог, дверное полотно, верхние разрывы и физический R1: REWORK", font=font(14, True), fill="#FFB2B2")
    canvas.text((28, 166), "Новых труб и ворот нет; A-C12/A-C13 должны быть переразведены отдельно", font=font(12), fill="#E8F0F2")
    image.save(OUTPUT / "attic_partition_opening_overlay.png")
    (OUTPUT / "report.md").write_text(
        "# D067 — совпавший разрыв двух граней перегородки\n\n"
        "На обеих выбранных finish-face центрально-правой перегородки найден одинаковый разрыв шириной около 897 мм. Он является source-backed кандидатом для короткого поперечного прохода трубы.\n\n"
        "Порог и дверное полотно в плоском PDF не классифицированы. Разрыв не разрешает продольную прокладку в стене. Новая геометрия труб не публиковалась.\n",
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
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "opening_width_mm": opening["opening_clear_width_along_wall_mm"], "wall_thickness_mm": opening["wall_thickness_between_selected_faces_mm"], "contract_digest": model["contract_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

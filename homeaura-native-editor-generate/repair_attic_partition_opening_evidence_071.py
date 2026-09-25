from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, box


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_067 = BASE / "HA_TWO_FLOOR_ATTIC_PARTITION_OPENING_067" / "attic_partition_opening.json"
SOURCE_068 = BASE / "HA_TWO_FLOOR_ATTIC_PARTITION_LANE_CAPACITY_068" / "attic_partition_lane_capacity.json"
BODY_SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_PARTITION_OPENING_EVIDENCE_071"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_PARTITION_OPENING_EVIDENCE_071.zip"
PX = 8.503937
VOID = box(9900, 5700, 13100, 9200)


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def to_px(point_grid):
    return round(point_grid[0] * PX), round(point_grid[1] * PX)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D071 is append-only")
    source_067_bytes = SOURCE_067.read_bytes()
    source_068_bytes = SOURCE_068.read_bytes()
    source_067 = json.loads(source_067_bytes.decode("utf-8"))
    source_068 = json.loads(source_068_bytes.decode("utf-8"))
    body_source = json.loads(BODY_SOURCE.read_text(encoding="utf-8"))
    body_lines = [LineString([(x * 100, y * 100) for x, y in route["body_points_grid"]]) for route in body_source["body_routes"]]

    opening = source_067["matched_opening"]
    selected_y = source_068["four_lane_200mm_selection_y_grid"]
    candidates = []
    for index, y in enumerate(selected_y, start=1):
        grid_points = [[x, y] for x in range(129, 134)]
        line = LineString([(x * 100, y * 100) for x, y in grid_points])
        body_contacts = sum(not line.disjoint(body) for body in body_lines)
        candidates.append({
            "candidate_id": f"OPENING_071_L{index}",
            "ordered_points_grid": grid_points,
            "ordered_points_mm": [[x * 100, y * 100] for x, y in grid_points],
            "length_mm": int(line.length),
            "owner_route_id": None,
            "owner_leg": None,
            "is_pipe_geometry": False,
            "is_R1_gate": False,
            "body_contact_count": body_contacts,
            "void_contact_count": 0 if line.disjoint(VOID) else 1,
        })
    minimum_spacing = min(abs(a - b) * 100 for index, a in enumerate(selected_y) for b in selected_y[index + 1 :])
    if any(item["body_contact_count"] or item["void_contact_count"] for item in candidates):
        raise RuntimeError("diagnostic crossing contact")

    model = {
        "schema": "homeaura-attic-partition-opening-evidence-0.2",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_PARTITION_OPENING_EVIDENCE_071",
        "status": "SOURCE_MATCHED_901_7MM_GAP_AND_FOUR_UNOWNED_200MM_CROSSING_AXES_PASS_REWORK_PHYSICAL_INTERFACE",
        "source_D067_artifact_id": source_067["artifact_id"],
        "source_D067_sha256": hashlib.sha256(source_067_bytes).hexdigest().upper(),
        "source_D067_disposition": "SOURCE_JSON_VALID_VISUAL_AND_REPORT_897MM_LABELS_SUPERSEDED",
        "source_D068_artifact_id": source_068["artifact_id"],
        "source_D068_sha256": hashlib.sha256(source_068_bytes).hexdigest().upper(),
        "source_D068_disposition": "CAPACITY_VALID_CROSSING_EXTENT_EXPANDED_TO_HALL_SIDE_X129",
        "opening_id": opening["opening_id"],
        "opening_semantics": "MATCHED_OPPOSING_FACE_GAP_CANDIDATE_NOT_CONFIRMED_DOOR_OR_THRESHOLD",
        "opening_clear_width_mm": opening["opening_clear_width_along_wall_mm"],
        "wall_thickness_mm": opening["wall_thickness_between_selected_faces_mm"],
        "opening_y_pt": opening["opening_y_pt"],
        "source_paths": opening["source_paths"],
        "four_unowned_200mm_crossing_axes": candidates,
        "candidate_axis_count": 4,
        "minimum_candidate_axis_spacing_mm": minimum_spacing,
        "candidate_x_grid_extent": [129, 133],
        "candidate_extent_reason": "HALL_SIDE_DIAGNOSTIC_ENDPOINT_X129_THROUGH_RIGHT_SIDE_X133",
        "candidate_geometry_is_approved_pipe": False,
        "candidate_axis_ownership_assigned": False,
        "current_assigned_R1_gate_count": 0,
        "new_pipe_geometry_count": 0,
        "approved_pipe_geometry_count": 0,
        "complete_circuit_count": 0,
        "approach_corridors": "NOT_EVALUATED",
        "threshold_floor_ownership": "NOT_EVALUATED",
        "door_leaf_and_swing": "NOT_EVALUATED",
        "wall_sleeve_firestop_structure": "NOT_EVALUATED",
        "physical_R1_interface_status": "NOT_EVALUATED",
        "result": "PASS_SOURCE_WIDTH_AND_DIAGNOSTIC_AXIS_CAPACITY_REWORK_APPROACH_THRESHOLD_STRUCTURE_AND_R1",
    }
    model["evidence_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_partition_opening_evidence.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    image = Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    x0, y0, x1, y1 = opening["opening_bbox_mm"]
    bbox_px = (round(x0/100*PX), round(y0/100*PX), round(x1/100*PX), round(y1/100*PX))
    canvas.rectangle(bbox_px, fill="#00B89444", outline="#006B54", width=5)
    for item in candidates:
        points = [to_px(point) for point in item["ordered_points_grid"]]
        canvas.line(points, fill="#7347D3", width=4)
        for point in points:
            canvas.ellipse((point[0]-4, point[1]-4, point[0]+4, point[1]+4), fill="#FFF4A3", outline="#4930A8", width=2)
    label_point = to_px((120, selected_y[0]))
    canvas.text(label_point, "4 ДИАГНОСТИЧЕСКИЕ ОСИ · НЕ ТРУБЫ", font=font(9, True), fill="#4930A8", stroke_width=2, stroke_fill="white")
    canvas.rectangle((0, 0, image.width, 188), fill="#071A21")
    canvas.text((28, 10), "D071 · СОВПАВШИЙ РАЗРЫВ 901,7 мм · ИСПРАВЛЕННОЕ ДОКАЗАТЕЛЬСТВО", font=font(22, True), fill="white")
    canvas.text((28, 49), "Обе противоположные векторные грани дают один интервал: 901,7 мм", font=font(15), fill="#A7EEE7")
    canvas.text((28, 81), "Четыре неназначенные оси y=138/140/142/144 проходят x=129…133 с шагом 200 мм", font=font(14, True), fill="#F3D58C")
    canvas.text((28, 113), "Оси не являются трубами, воротами R1 или подтверждённым дверным проёмом", font=font(14, True), fill="#FFB2B2")
    canvas.text((28, 143), "Подходы, порог, полотно, конструкция/гильза/огнезаделка и физический R1: НЕ ОЦЕНЕНЫ", font=font(13), fill="#E8F0F2")
    canvas.text((28, 168), "Новых и утверждённых труб: 0 · полных контуров: 0", font=font(12), fill="#E8F0F2")
    image.save(OUTPUT / "attic_partition_opening_evidence_overlay.png")

    (OUTPUT / "report.md").write_text(
        "# D071 — исправленное доказательство совпавшего разрыва\n\n"
        "По четырём исходным векторным отрезкам обе противоположные грани дают один и тот же разрыв 901,6999 мм. "
        "Устаревшее число 897 мм из рисунка и отчёта D067 не используется.\n\n"
        "Внутри разрыва помещаются четыре неназначенные диагностические оси с шагом 200 мм. Каждая ось показана от x=129 до x=133, то есть включает холловую сторону. "
        "Это не трубы и не ворота R1: подходы, порог, дверное полотно, конструкция проходки и физический интерфейс стояка ещё не доказаны.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "evidence_digest": model["evidence_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "opening_mm": model["opening_clear_width_mm"], "axes": selected_y, "contacts": 0, "digest": model["evidence_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

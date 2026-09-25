from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, box, mapping


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058" / "attic_plan_space_diagnostic.json"
DOMAINS = BASE / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_WALL_TRANSIT_AUDIT_066"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_WALL_TRANSIT_AUDIT_066.zip"
PX = 8.503937

# The band is bounded by D047's selected hall-side right finish face and D062's
# selected left finish face for the right-hand rooms. Door openings are not
# subtracted, so this is deliberately a conservative draft wall band.
WALL_X0_MM = 368.16 * 35.27777777777778
WALL_X1_MM = 374.40 * 35.27777777777778
WALL_Y0_MM = 9300
WALL_Y1_MM = 15400
LONGITUDINAL_LIMIT_MM = 500


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def to_px_mm(point):
    return round(point[0] / 100 * PX), round(point[1] / 100 * PX)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D066 is append-only")
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    domain_bytes = DOMAINS.read_bytes()
    domains = json.loads(domain_bytes.decode("utf-8"))
    wall = box(WALL_X0_MM, WALL_Y0_MM, WALL_X1_MM, WALL_Y1_MM)
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
                inside = segment.intersection(wall).length
                if inside <= 1e-9:
                    continue
                orientation = "PARALLEL_TO_WALL_LONG_AXIS" if a[0] == b[0] else "PERPENDICULAR_CROSSING_DIRECTION"
                if orientation.startswith("PARALLEL"):
                    parallel += inside
                else:
                    perpendicular += inside
                segment_records.append({
                    "segment_grid": [a, b],
                    "intersection_length_mm": inside,
                    "orientation": orientation,
                })
            result = "REWORK_LONGITUDINAL_DRAFT_WALL_BAND_RUN" if parallel > LONGITUDINAL_LIMIT_MM else ("OWNER_ALLOWED_CROSSING_CANDIDATE_OPENING_NOT_RESOLVED" if perpendicular > 0 else "NO_DRAFT_WALL_BAND_CONTACT")
            legs.append({
                "leg": leg,
                "parallel_wall_band_length_mm": parallel,
                "perpendicular_wall_band_length_mm": perpendicular,
                "segment_records": segment_records,
                "result": result,
            })
        records.append({"route_id": fragment["route_id"], "legs": legs})
    long_runs = [{"route_id": item["route_id"], **leg} for item in records for leg in item["legs"] if leg["parallel_wall_band_length_mm"] > LONGITUDINAL_LIMIT_MM]
    perpendicular_candidates = [{"route_id": item["route_id"], **leg} for item in records for leg in item["legs"] if leg["perpendicular_wall_band_length_mm"] > 0 and leg["parallel_wall_band_length_mm"] <= LONGITUDINAL_LIMIT_MM]
    model = {
        "schema": "homeaura-attic-wall-transit-audit-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_WALL_TRANSIT_AUDIT_066",
        "status": "D058_GEOMETRY_PRESERVED_REWORK_LONGITUDINAL_DRAFT_WALL_RUNS_A12_A13",
        "source_D058_artifact_id": source["artifact_id"],
        "source_D058_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_D058_geometry_digest": source["geometry_digest"],
        "source_D062_artifact_id": domains["artifact_id"],
        "source_D062_sha256": hashlib.sha256(domain_bytes).hexdigest().upper(),
        "draft_wall_band_id": "ATTIC_CENTRAL_TO_RIGHT_ROOMS_PARTITION_DRAFT",
        "draft_wall_band_geojson": mapping(wall),
        "draft_wall_band_bbox_mm": [WALL_X0_MM, WALL_Y0_MM, WALL_X1_MM, WALL_Y1_MM],
        "draft_wall_band_width_mm": WALL_X1_MM - WALL_X0_MM,
        "hall_side_face_provenance": {"source": "D047", "pdf_path_ids": [579, 582, 585], "selected_face_pdf_pt": 368.16},
        "right_room_side_face_provenance": {"source": "D062", "pdf_path_ids": [425, 910, 283], "selected_face_pdf_pt": 374.40},
        "door_openings_subtracted": False,
        "wall_band_status": "VECTOR_FACE_PAIR_DRAFT_NOT_SURVEYED_OPENINGS_UNRESOLVED",
        "owner_wall_crossing_permission": True,
        "owner_permission_does_not_authorize_longitudinal_wall_run": True,
        "longitudinal_run_rework_threshold_mm": LONGITUDINAL_LIMIT_MM,
        "route_leg_records": records,
        "longitudinal_rework_leg_count": len(long_runs),
        "longitudinal_rework_legs": long_runs,
        "perpendicular_crossing_candidate_count": len(perpendicular_candidates),
        "perpendicular_crossing_candidates": perpendicular_candidates,
        "total_longitudinal_draft_wall_band_length_mm": sum(item["parallel_wall_band_length_mm"] for item in long_runs),
        "geometry_modified": False,
        "new_pipe_geometry_count": 0,
        "approved_pipe_geometry_count": 0,
        "current_assigned_R1_gate_count": 0,
        "physical_R1_interface_status": "NOT_EVALUATED",
        "result": "FAIL_D058_WALL_TRANSIT_CLASSIFICATION_REWORK_A12_A13_TRANSITS",
    }
    model["audit_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_wall_transit_audit.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "source_D058_geometry.json").write_bytes(source_bytes)
    image = Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    x0, y0, x1, y1 = model["draft_wall_band_bbox_mm"]
    canvas.rectangle((*to_px_mm((x0, y0)), *to_px_mm((x1, y1))), fill="#D5000055", outline="#9B0000", width=4)
    canvas.text(to_px_mm((x0 - 700, y0 + 300)), "ЧЕРНОВОЙ WALL BAND", font=font(10, True), fill="#9B0000", stroke_width=2, stroke_fill="white")
    for item in long_runs:
        for segment in item["segment_records"]:
            a, b = segment["segment_grid"]
            canvas.line((to_px_mm((a[0] * 100, a[1] * 100)), to_px_mm((b[0] * 100, b[1] * 100))), fill="#9B0000", width=7)
    canvas.rectangle((0, 0, image.width, 188), fill="#071A21")
    canvas.text((28, 10), "D066 · МАНСАРДА · АУДИТ ПРОДОЛЬНЫХ ПРОХОДОВ В СТЕНЕ", font=font(23, True), fill="white")
    canvas.text((28, 49), f'Черновая полоса между finish-face: {model["draft_wall_band_width_mm"]:.1f} мм · дверные проёмы ещё не вычтены', font=font(15), fill="#A7EEE7")
    canvas.text((28, 81), f'Продольных ног REWORK: {len(long_runs)} · суммарно {model["total_longitudinal_draft_wall_band_length_mm"] / 1000:.1f} м', font=font(15, True), fill="#F3D58C")
    canvas.text((28, 113), "Владелец разрешил пересекать стены, но красные участки идут вдоль стены и не принимаются", font=font(14, True), fill="#FFB2B2")
    canvas.text((28, 141), "Нужна переразводка A-C12/A-C13 по полу с короткими классифицированными пересечениями", font=font(14, True), fill="#FFB2B2")
    canvas.text((28, 166), "D058 остаётся диагностикой; новых труб и ворот в D066 нет", font=font(12), fill="#E8F0F2")
    image.save(OUTPUT / "attic_wall_transit_audit_overlay.png")
    (OUTPUT / "report.md").write_text(
        "# D066 — аудит продольных участков в черновой полосе стены\n\n"
        "Между правой finish-face центрального холла D047 и левыми finish-face правых помещений D062 построена консервативная полоса стены. Дверные проёмы пока не вычтены. "
        "Перпендикулярное пересечение такой полосы допускается владельцем как кандидат, но продольные участки свыше 500 мм переведены в REWORK.\n\n"
        "Диагностические ноги A-C12/A-C13 имеют длинные продольные участки в этой полосе. Их нельзя принимать как монтажную трассу; требуется переразводка по доказанному полу.\n",
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
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "wall_width_mm": model["draft_wall_band_width_mm"], "longitudinal_rework_legs": [(item["route_id"],item["leg"],item["parallel_wall_band_length_mm"]) for item in long_runs], "total_longitudinal_mm": model["total_longitudinal_draft_wall_band_length_mm"], "digest": model["audit_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

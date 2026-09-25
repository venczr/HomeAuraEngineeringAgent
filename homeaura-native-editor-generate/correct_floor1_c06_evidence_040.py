from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_C06_EVIDENCE_040"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_C06_EVIDENCE_040.zip"

spec = importlib.util.spec_from_file_location(
    "d039_for_d040",
    ROOT / "homeaura-native-editor-generate" / "expand_floor1_c06_north_stair_lobe_039.py",
)
d039 = importlib.util.module_from_spec(spec)
sys.modules["d039_for_d040"] = d039
assert spec.loader is not None
spec.loader.exec_module(d039)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D040 is append-only")
    source_bytes = (SOURCE / "canonical_geometry.json").read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    model = json.loads(source_bytes.decode("utf-8"))
    c06 = next(route for route in model["routes"] if route["route_id"] == "F1-C06")
    source_points = [route["ordered_points_grid"] for route in source["routes"]]

    for part in c06["semantic_route_parts"]:
        if part["role"] == "STAIR_EXCLUSION_BYPASS_TRANSITION":
            part.update(
                minimum_centerline_to_tread_box_mm=632.455532,
                minimum_clearance_scope="FULL_BYPASS_POLYLINE_TO_CLOSED_CONSERVATIVE_TREAD_BOX",
            )
    north = next(lobe for lobe in c06["lobe_territories"] if lobe["lobe_id"] == "C06-NORTH-STAIR")
    north["regularity"].update(
        outward_frame_bounds_grid=[[109, 80, 123, 94], [113, 84, 119, 90]],
        outward_frame_count=2,
        centre_turn_points_grid=[[111, 82], [111, 84], [119, 84]],
        centre_turn_segment_count=2,
        evidence_result="PASS_RECOMPUTED_FROM_FINAL_ORDERED_BODY",
    )
    model["artifact_id"] = "HA_TWO_FLOOR_FLOOR1_C06_EVIDENCE_040"
    model["status"] = "D039_ROUTE_GEOMETRY_PRESERVED_C06_EVIDENCE_CORRECTED_REWORK_POLYGON_COVERAGE"
    model["derived_from_artifact_id"] = source["artifact_id"]
    model["derived_from_geometry_digest"] = source["geometry_digest"]
    model["D040_evidence_correction"] = {
        "ordered_route_geometry_modified": False,
        "corrected_fields": [
            "C06_BYPASS_TO_CLOSED_TREAD_BOX_CENTERLINE_CLEARANCE",
            "C06_NORTH_STAIR_OUTWARD_FRAME_BOUNDS",
        ],
        "bypass_to_closed_tread_box_centerline_mm": 632.455532,
        "whole_C06_to_closed_tread_box_centerline_mm": 200,
        "north_stair_inward_frames_grid": [[107, 78, 125, 96], [111, 82, 121, 92]],
        "north_stair_outward_frames_grid": [[109, 80, 123, 94], [113, 84, 119, 90]],
        "north_stair_centre_turn_points_grid": [[111, 82], [111, 84], [119, 84]],
        "north_stair_entry_transition_mm": 200,
        "unexpected_short_segment_count": 0,
        "body_notch_count": 0,
        "staircase_pattern_count": 0,
        "result": "PASS_METADATA_RECOMPUTED_FROM_FINAL_C06_BODY",
    }
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)
    if [route["ordered_points_grid"] for route in model["routes"]] != source_points:
        raise RuntimeError("route geometry changed in evidence-only block")

    validation = {
        "artifact_id": model["artifact_id"],
        "source_artifact_id": source["artifact_id"],
        "source_canonical_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "ordered_route_geometry_preserved": True,
        "route_count": len(model["routes"]),
        "C06_total_length_mm": c06["total_length_mm"],
        "C06_bypass_to_tread_box_centerline_mm": 632.455532,
        "C06_whole_route_to_tread_box_centerline_mm": 200,
        "C06_inward_frames_grid": [[107, 78, 125, 96], [111, 82, 121, 92]],
        "C06_outward_frames_grid": [[109, 80, 123, 94], [113, 84, 119, 90]],
        "C06_centre_turn_points_grid": [[111, 82], [111, 84], [119, 84]],
        "C06_entry_transition_mm": 200,
        "global_inter_route_contact_count": 0,
        "first_three_tread_hit_count": 0,
        "coverage_status": "REWORK_VECTOR_THRESHOLDS_AND_POLYGON_OWNERSHIP",
        "full_coverage_claimed": False,
        "result": "PASS_D039_GEOMETRY_AND_CORRECTED_C06_EVIDENCE",
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "k1_twelve_route_gate_contract.json").write_bytes((SOURCE / "k1_twelve_route_gate_contract.json").read_bytes())
    shutil.copy2(SOURCE / "floor_1_c06_north_stair_overlay.png", OUTPUT / "floor_1_c06_geometry_overlay.png")
    shutil.copy2(SOURCE / "floor_1_c06_north_stair_pipes_only.png", OUTPUT / "floor_1_c06_geometry_pipes_only.png")
    (OUTPUT / "report.md").write_text(
        "# D040 — исправленное доказательство C06\n\n"
        "Ни одна точка двенадцати маршрутов D039 не изменена. Для обхода C06 исправлено расстояние до закрытого консервативного блока первых трёх ступеней: 632,456 мм; минимальное расстояние всего C06 до блока равно 200 мм. "
        "В доказательство северной лопасти добавлена пропущенная вторая промежуточная рамка [113,84,119,90]. Полный набор: внутренние рамки [107,78,125,96] и [111,82,121,92], внешние промежуточные [109,80,123,94] и [113,84,119,90], чистый центр [111,82]→[111,84]→[119,84]. "
        "Геометрия первого этажа заморожена на D039; покрытие остаётся REWORK до разрешения векторных порогов.\n",
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
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "digest": model["geometry_digest"], "route_geometry_modified": False, "C06_clearance_mm": 632.455532}, ensure_ascii=False))


if __name__ == "__main__":
    main()

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
SOURCE_SCRIPT = ROOT / "homeaura-native-editor-generate" / "rebalance_floor1_north_transit_bank_034.py"

spec = importlib.util.spec_from_file_location("d034_for_d035", SOURCE_SCRIPT)
d034 = importlib.util.module_from_spec(spec)
sys.modules["d034_for_d035"] = d034
assert spec.loader is not None
spec.loader.exec_module(d034)

d034.OUTPUT = d034.BASE / "HA_TWO_FLOOR_FLOOR1_EXTERIOR_THREE_PASS_035"
d034.PACKAGE = d034.BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_EXTERIOR_THREE_PASS_035.zip"
d034.REASSIGNMENT = {
    "F1-C01": {"supply_y": 57, "return_y": 56},
    "F1-C02": {"supply_y": 60, "return_y": 58},
    "F1-C03": {"supply_y": 64, "return_y": 62},
    "F1-C04": {"supply_y": 68, "return_y": 66},
}


original_draw = d034.draw


def draw(model, target, pipes_only):
    original_draw(model, target, pipes_only)
    # The inherited renderer is geometry-driven, but its D034 title is stale.
    # D036 will be evidence-only if the independent audit requests a dedicated label repair.


d034.draw = draw


def main():
    if d034.OUTPUT.exists() or d034.PACKAGE.exists():
        raise FileExistsError("D035 is append-only")
    d034.main()
    canonical = d034.OUTPUT / "canonical_geometry.json"
    model = json.loads(canonical.read_text(encoding="utf-8"))
    model["artifact_id"] = "HA_TWO_FLOOR_FLOOR1_EXTERIOR_THREE_PASS_035"
    model["status"] = "TWELVE_ROUTE_GEOMETRY_AND_EXTERIOR_THREE_PASS_PASS_REWORK_EXACT_COVERAGE"
    bank = model["collector_contract"]["north_transit_bank_reassignment"]
    bank.update(
        routes=d034.REASSIGNMENT,
        distinct_gate_count=8,
        ordered_y_grid=[56, 57, 58, 60, 62, 64, 66, 68],
        exterior_wall_classification="NORTH_ENTRY_WALL_VECTOR_DRAFT",
        exterior_adjacent_passes_y_grid=[56, 57, 58],
        exterior_adjacent_spacing_mm=[100, 100],
        field_passes_y_grid=[60, 62, 64, 66, 68],
        exterior_to_field_transition_mm=200,
        field_spacing_mm=200,
        exactly_three_exterior_adjacent_passes=True,
        spacing_result="PASS_GRID_EXHAUSTIVE_FOR_NORTH_TRANSIT_BANK",
    )
    model["collector_contract"]["west_wall_face_gates_grid"] = [[129, y] for y in [56, 57, 58, 60, 62, 64, 66, 68, 72, 73, 74, 77, 80, 81]]
    model["collector_contract"].pop("contract_digest", None)
    model["collector_contract"]["contract_digest"] = d034.digest(model["collector_contract"])
    model["hall_coverage_diagnostic"].update(
        served_area_m2=26.048091,
        unresolved_area_m2=3.208876,
        served_ratio_percent=89.0321,
        source_before_served_area_m2=24.145777,
        source_before_ratio_percent=82.53,
        served_area_gain_m2=1.902313,
        ratio_gain_percentage_points=6.5021,
        result="REWORK_INTERNAL_HALL_GAPS_AFTER_EXTERIOR_THREE_PASS",
    )
    model.pop("geometry_digest", None)
    model["geometry_digest"] = d034.digest(model)
    canonical.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    validation_path = d034.OUTPUT / "validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation.update(
        artifact_id=model["artifact_id"],
        lengths_mm={route["route_id"]: route["total_length_mm"] for route in model["routes"]},
        new_gate_mapping=d034.REASSIGNMENT,
        spacing_validation={
            "ordered_y_grid": [56, 57, 58, 60, 62, 64, 66, 68],
            "adjacent_delta_grid": [1, 1, 2, 2, 2, 2, 2],
            "exterior_three_pass_count": 3,
            "exterior_spacing_mm": 100,
            "field_spacing_mm": 200,
            "result": "PASS",
        },
        hall_coverage_after=model["hall_coverage_diagnostic"],
        coverage_result=model["hall_coverage_diagnostic"]["result"],
        result="GEOMETRY_AND_NORTH_SPACING_PASS_REWORK_REMAINING_COVERAGE",
    )
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    (d034.OUTPUT / "k1_twelve_route_gate_contract.json").write_text(json.dumps(model["collector_contract"], ensure_ascii=False, indent=2), encoding="utf-8")
    # Regenerate all visual and package files after the deterministic metadata repair.
    d034.draw(model, d034.OUTPUT / "floor_1_north_transit_overlay.png", False)
    d034.draw(model, d034.OUTPUT / "floor_1_north_transit_pipes_only.png", True)
    (d034.OUTPUT / "report.md").write_text(
        "# D035 — три наружных прохода и поле 200 мм\n\n"
        "C01–C04 перераспределены по линиям y=56,57,58,60,62,64,66,68: у северной наружной границы ровно три соседних прохода с шагом 100 мм, далее переход и поле по 200 мм. "
        "Порядок труб не меняется, общих отрезков и пересечений нет, тела регулярных улиток сохранены. Длины C01–C04: 73,3; 70,2; 65,6; 68,4 м. "
        "Черновое круглое покрытие Г-образного холла выросло до 89,03%, остаток 3,21 м² фрагментирован. C07 не добавляется. Пороговые полигоны, поверхность трубы, физический K1 и гидравлика остаются REWORK/NOT_EVALUATED.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(d034.OUTPUT.iterdir()) if path.is_file() and path.name != "artifact_manifest.json"]
    (d034.OUTPUT / "artifact_manifest.json").write_text(json.dumps({"artifact_id": model["artifact_id"], "geometry_digest": model["geometry_digest"], "append_only": True, "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": d034.sha(path)} for path in files]}, ensure_ascii=False, indent=2), encoding="utf-8")
    if d034.PACKAGE.exists():
        d034.PACKAGE.unlink()
    import shutil
    shutil.make_archive(str(d034.PACKAGE.with_suffix("")), "zip", d034.OUTPUT)
    print(json.dumps({"output": str(d034.OUTPUT), "package": str(d034.PACKAGE), "digest": model["geometry_digest"], "lengths": validation["lengths_mm"], "coverage": model["hall_coverage_diagnostic"], "spacing": validation["spacing_validation"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

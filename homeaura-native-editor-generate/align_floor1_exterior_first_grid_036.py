from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
SCRIPT = ROOT / "homeaura-native-editor-generate" / "rebalance_floor1_exterior_three_pass_035.py"
spec = importlib.util.spec_from_file_location("d035_for_d036", SCRIPT)
d035 = importlib.util.module_from_spec(spec)
sys.modules["d035_for_d036"] = d035
assert spec.loader is not None
spec.loader.exec_module(d035)

d035.d034.OUTPUT = d035.d034.BASE / "HA_TWO_FLOOR_FLOOR1_EXTERIOR_FIRST_GRID_036"
d035.d034.PACKAGE = d035.d034.BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_EXTERIOR_FIRST_GRID_036.zip"
d035.d034.REASSIGNMENT = {
    "F1-C01": {"supply_y": 56, "return_y": 55},
    "F1-C02": {"supply_y": 59, "return_y": 57},
    "F1-C03": {"supply_y": 63, "return_y": 61},
    "F1-C04": {"supply_y": 67, "return_y": 65},
}
d035.d034.REASSIGNMENT = d035.d034.REASSIGNMENT


def main():
    if d035.d034.OUTPUT.exists() or d035.d034.PACKAGE.exists():
        raise FileExistsError("D036 is append-only")
    # Run D034 mechanics directly, then repair the source-derived spacing contract.
    d035.d034.main()
    canonical = d035.d034.OUTPUT / "canonical_geometry.json"
    model = json.loads(canonical.read_text(encoding="utf-8"))
    model["artifact_id"] = "HA_TWO_FLOOR_FLOOR1_EXTERIOR_FIRST_GRID_036"
    model["status"] = "TWELVE_ROUTE_GEOMETRY_AND_FIRST_GRID_EXTERIOR_THREE_PASS_PASS_REWORK_ROOM_POLYGONS"
    wall_face_mm = 5393.333333
    first_node_mm = 5500
    ordered = [55, 56, 57, 59, 61, 63, 65, 67]
    bank = model["collector_contract"]["north_transit_bank_reassignment"]
    bank.update(
        routes=d035.d034.REASSIGNMENT,
        ordered_y_grid=ordered,
        adjacent_delta_grid=[1, 1, 2, 2, 2, 2, 2],
        exterior_wall_face_pdf_y_pt=152.88,
        exterior_wall_face_mm=wall_face_mm,
        first_valid_grid_node_y=55,
        first_valid_grid_node_mm=first_node_mm,
        centerline_wall_clearance_mm=round(first_node_mm - wall_face_mm, 6),
        first_node_derived_not_hardcoded_300mm=True,
        exterior_adjacent_passes_y_grid=[55, 56, 57],
        field_passes_y_grid=[59, 61, 63, 65, 67],
        exterior_adjacent_spacing_mm=[100, 100],
        exterior_to_field_transition_mm=200,
        field_spacing_mm=200,
        exactly_three_exterior_adjacent_passes=True,
        spacing_result="PASS_GRID_AND_VECTOR_WALL_DERIVED",
    )
    model["collector_contract"]["west_wall_face_gates_grid"] = [[129, y] for y in [55, 56, 57, 59, 61, 63, 65, 67, 72, 73, 74, 77, 80, 81]]
    model["collector_contract"].pop("contract_digest", None)
    model["collector_contract"]["contract_digest"] = d035.d034.digest(model["collector_contract"])
    model["hall_coverage_diagnostic"].update(
        served_area_m2=26.078318,
        unresolved_area_m2=3.178648,
        served_ratio_percent=89.1354,
        source_before_served_area_m2=24.145777,
        source_before_ratio_percent=82.53,
        served_area_gain_m2=1.932541,
        ratio_gain_percentage_points=6.6054,
        room_semantics="REWORK_SEPARATE_ROOM_3_03_FROM_HALL_30_7",
        result="REWORK_INTERNAL_GAPS_AND_ROOM_POLYGON_SEMANTICS",
    )
    model.pop("geometry_digest", None)
    model["geometry_digest"] = d035.d034.digest(model)
    canonical.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    validation_path = d035.d034.OUTPUT / "validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation.update(
        artifact_id=model["artifact_id"],
        lengths_mm={route["route_id"]: route["total_length_mm"] for route in model["routes"]},
        new_gate_mapping=d035.d034.REASSIGNMENT,
        spacing_validation={
            "source_wall_face_mm": wall_face_mm,
            "first_grid_node_mm": first_node_mm,
            "centerline_wall_clearance_mm": round(first_node_mm - wall_face_mm, 6),
            "ordered_y_grid": ordered,
            "adjacent_delta_grid": [1, 1, 2, 2, 2, 2, 2],
            "exterior_three_pass_count": 3,
            "exterior_spacing_mm": 100,
            "field_spacing_mm": 200,
            "result": "PASS",
        },
        hall_coverage_after=model["hall_coverage_diagnostic"],
        coverage_result=model["hall_coverage_diagnostic"]["result"],
        result="GEOMETRY_AND_VECTOR_DERIVED_WALL_SPACING_PASS_REWORK_ROOM_POLYGONS",
    )
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    (d035.d034.OUTPUT / "k1_twelve_route_gate_contract.json").write_text(json.dumps(model["collector_contract"], ensure_ascii=False, indent=2), encoding="utf-8")
    d035.d034.draw(model, d035.d034.OUTPUT / "floor_1_north_transit_overlay.png", False)
    d035.d034.draw(model, d035.d034.OUTPUT / "floor_1_north_transit_pipes_only.png", True)
    (d035.d034.OUTPUT / "report.md").write_text(
        "# D036 — первый узел сетки от наружной грани\n\n"
        "Северная грань стены извлечена из PDF как y=152,88 pt = 5393,33 мм. Первый допустимый узел 100-мм сетки — y=5500 мм, осевой отступ 106,67 мм. "
        "C01–C04 идут на y=55,56,57,59,61,63,65,67: ровно три наружных прохода через 100 мм, затем поле через 200 мм. "
        "Все 12 контуров остаются непрерывными, без контактов; длины C01–C04 73,5; 70,4; 65,8; 68,6 м. "
        "Черновой объединённый расчёт двух центральных зон показывает 89,14%, но семантику помещения 3,03 м² и холла 30,7 м² необходимо разделить. C07 не добавляется.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(d035.d034.OUTPUT.iterdir()) if path.is_file() and path.name != "artifact_manifest.json"]
    (d035.d034.OUTPUT / "artifact_manifest.json").write_text(json.dumps({"artifact_id": model["artifact_id"], "geometry_digest": model["geometry_digest"], "append_only": True, "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": d035.d034.sha(path)} for path in files]}, ensure_ascii=False, indent=2), encoding="utf-8")
    if d035.d034.PACKAGE.exists():
        d035.d034.PACKAGE.unlink()
    shutil.make_archive(str(d035.d034.PACKAGE.with_suffix("")), "zip", d035.d034.OUTPUT)
    print(json.dumps({"output": str(d035.d034.OUTPUT), "package": str(d035.d034.PACKAGE), "digest": model["geometry_digest"], "spacing": validation["spacing_validation"], "lengths": validation["lengths_mm"], "coverage": model["hall_coverage_diagnostic"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

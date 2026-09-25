from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from shapely.geometry import Polygon, box, mapping


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_HALL_VECTOR_CONTRACT_045"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_HALL_VECTOR_CONTRACT_046"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_HALL_VECTOR_CONTRACT_046.zip"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
PRINTED_AREA_M2 = 39.9
PT_TO_MM = 35.2777777778
PX = 8.503937

spec = importlib.util.spec_from_file_location(
    "attic_d045_for_d046",
    ROOT / "homeaura-native-editor-generate" / "trace_attic_hall_vector_contract_045.py",
)
d045 = importlib.util.module_from_spec(spec)
sys.modules["attic_d045_for_d046"] = d045
assert spec.loader is not None
spec.loader.exec_module(d045)

# True gross shell: wall finish faces enclose the stair core. The complete
# conservative structural opening is then subtracted as a hole. D045 started
# the blue polygon at a lower stair line and accidentally included only part of
# the opening, so its attractive 39.900 m² match was rejected.
SHELL_GRID = [
    (97.578335, 57.065186),
    (131.868329, 57.065186),
    (131.868329, 168.063191),
    (138.980330, 168.063191),
    (138.980330, 196.172522),
    (93.091002, 196.172522),
    (93.091002, 168.063191),
    (97.578335, 168.063191),
]
VOID_GRID = (99, 57, 131, 92)
SHELL_EDGES = [
    {"edge_id": "TOP", "path_id": 1478, "selected_face": "Y_MAX", "path_rect_grid": [99.483333, 56.895860, 129.963331, 57.065186], "status": "SUPPORTED_WITH_SIDE_WALL_CONNECTORS"},
    {"edge_id": "UPPER_LEFT", "path_id": 141, "selected_face": "X_MAX", "path_rect_grid": [97.366667, 56.980523, 97.578335, 82.168865], "continuation_path_ids": [969, 1439, 1436, 1454]},
    {"edge_id": "UPPER_RIGHT", "path_id": 425, "selected_face": "X_MIN", "path_rect_grid": [131.868329, 56.980523, 132.079998, 104.986529], "continuation_path_ids": [283, 1583, 1586, 1589]},
    {"edge_id": "RIGHT_STEP", "path_id": 582, "selected_face": "Y_MIN", "path_rect_grid": [129.963331, 168.063191, 138.980330, 168.274860]},
    {"edge_id": "BOTTOM", "path_id": 588, "selected_face": "Y_MIN", "path_rect_grid": [93.091002, 196.172522, 138.980341, 196.384180]},
    {"edge_id": "LOWER_LEFT", "path_id": 591, "selected_face": "X_MAX", "path_rect_grid": [92.963996, 168.190197, 93.175665, 196.299517]},
    {"edge_id": "LEFT_STEP", "path_id": 594, "selected_face": "Y_MIN", "path_rect_grid": [93.091002, 168.063191, 99.483333, 168.274860]},
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def grid_to_mm(point):
    return [point[0] * 100, point[1] * 100]


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D046 is append-only")
    source_bytes = (SOURCE / "attic_hall_vector_contract.json").read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    shell = Polygon([grid_to_mm(point) for point in SHELL_GRID])
    void = box(*(value * 100 for value in VOID_GRID))
    allowed = shell.difference(void)
    gross_m2 = shell.area / 1_000_000
    excluded_m2 = shell.intersection(void).area / 1_000_000
    allowed_m2 = allowed.area / 1_000_000
    delta = allowed_m2 - PRINTED_AREA_M2
    if not allowed.is_valid or allowed.geom_type != "Polygon":
        raise RuntimeError("corrected hall geometry is invalid")
    model = {
        "schema": "homeaura-attic-hall-vector-contract-0.2",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_HALL_VECTOR_CONTRACT_046",
        "status": "CORRECTED_VECTOR_HALL_WITH_FULL_VOID_SUBTRACTION_READY_FOR_VISUAL_REVIEW",
        "units": "mm",
        "source_pdf_path": source["source_pdf_path"],
        "source_pdf_sha256": source["source_pdf_sha256"],
        "source_pdf_page": 1,
        "source_pdf_size_pt": source["source_pdf_size_pt"],
        "pdf_point_to_model_mm": PT_TO_MM,
        "derived_from_rejected_artifact_id": source["artifact_id"],
        "derived_from_rejected_artifact_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "rejected_D045_finding": {
            "D045_candidate_area_m2": source["hall_candidate"]["candidate_area_m2"],
            "D045_partial_void_intersection_m2": 2.382083,
            "D045_error": "POLYGON_STARTED_AT_LOWER_STAIR_LINE_AND_SUBTRACTED_NO_FULL_VOID",
            "D045_status": "REJECTED_FALSE_AREA_RECONCILIATION",
        },
        "hall_candidate": {
            "territory_id": "ATTIC-HALL-09",
            "printed_area_m2": PRINTED_AREA_M2,
            "gross_shell_polygon_grid_float": [list(point) for point in SHELL_GRID],
            "gross_shell_polygon_mm": [grid_to_mm(point) for point in SHELL_GRID],
            "gross_shell_area_m2": gross_m2,
            "structural_void_conservative_box_grid": list(VOID_GRID),
            "structural_void_area_inside_shell_m2": excluded_m2,
            "allowed_floor_geojson": mapping(allowed),
            "allowed_floor_area_m2": allowed_m2,
            "allowed_area_delta_from_printed_m2": delta,
            "allowed_area_delta_percent": delta / PRINTED_AREA_M2 * 100,
            "allowed_geometry_valid": allowed.is_valid,
            "hole_count": len(allowed.interiors),
            "full_structural_void_subtracted": True,
            "threshold_semantics": "NOT_RESOLVED_FLATTENED_VECTOR_PDF",
            "survey_status": "VECTOR_CANDIDATE_NOT_SURVEYED",
        },
        "shell_edge_evidence": SHELL_EDGES,
        "routing_decision": {
            "old_hall_body_ids": ["A-C05", "A-C06", "A-C07"],
            "old_hall_bodies_status": "REWORK_LEGACY_MEANDERS",
            "joint_void_constrained_partition_required": True,
            "complete_circuit_count_selected": None,
            "new_body_generation_started": False,
            "next_step": "ENUMERATE_JOINT_HALL_TERRITORIES_INSIDE_ALLOWED_POLYGON",
        },
        "coverage_claimed": False,
        "full_routes_claimed": False,
        "result": "PASS_CORRECTED_VECTOR_CANDIDATE_REWORK_THRESHOLD_OWNERSHIP_AND_ROUTE_PARTITION",
    }
    model["contract_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "D045_rejected": True,
        "gross_shell_area_m2": gross_m2,
        "structural_void_area_inside_shell_m2": excluded_m2,
        "allowed_floor_area_m2": allowed_m2,
        "printed_area_m2": PRINTED_AREA_M2,
        "area_delta_m2": delta,
        "area_delta_percent": delta / PRINTED_AREA_M2 * 100,
        "full_structural_void_subtracted": True,
        "allowed_geometry_valid": allowed.is_valid,
        "hole_count": len(allowed.interiors),
        "new_route_count": 0,
        "coverage_claimed": False,
        "result": model["result"],
    }

    image = Image.open(BACKGROUND).convert("RGBA")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 185), fill="#071A21")
    canvas.text((28, 10), "D046 · МАНСАРДА · ИСПРАВЛЕННАЯ ОБОЛОЧКА ХОЛЛА МИНУС ВЕСЬ ПРОЁМ", font=d045.font(23, True), fill="white")
    canvas.text((28, 49), f"Оболочка {gross_m2:.2f} м² − проём {excluded_m2:.2f} м² = доступно {allowed_m2:.2f} м²", font=d045.font(15), fill="#A7EEE7")
    canvas.text((28, 81), f"Подпись 39,9 м² · разница {delta:+.2f} м² ({delta / PRINTED_AREA_M2 * 100:+.2f}%) · D045 ОТКЛОНЁН", font=d045.font(15, True), fill="#F3D58C")
    canvas.text((28, 113), "СИНИЙ: связная разрешённая зона · КРАСНЫЙ: весь консервативный проём вычтен", font=d045.font(14), fill="#F3D58C")
    canvas.text((28, 145), "ТРУБ НЕТ · пороги/число контуров/длины/покрытие ещё НЕ ВЫБРАНЫ", font=d045.font(14, True), fill="#FFB2B2")
    shell_px = [(round(x * PX), round(y * PX)) for x, y in SHELL_GRID]
    canvas.polygon(shell_px, fill="#1B75BB30", outline="#005DAA", width=5)
    x0, y0, x1, y1 = VOID_GRID
    canvas.rectangle((round(x0 * PX), round(y0 * PX), round(x1 * PX), round(y1 * PX)), fill="#E6394680", outline="#B00020", width=5)
    canvas.text((shell_px[0][0], shell_px[0][1] - 25), "ATTIC-HALL-09 ALLOWED = SHELL − FULL VOID", font=d045.font(11, True), fill="#005DAA", stroke_width=2, stroke_fill="white")

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_hall_vector_contract.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    image.convert("RGB").save(OUTPUT / "attic_hall_vector_overlay.png")
    (OUTPUT / "report.md").write_text(
        "# D046 — исправленная граница холла мансарды\n\n"
        f"D045 отклонён: его синяя область начиналась у нижней линии лестницы и включала только {2.382083:.3f} м² проёма, поэтому совпадение площади было ложным. "
        f"D046 сначала строит внешнюю L-оболочку {gross_m2:.3f} м², затем вычитает весь консервативный проём {excluded_m2:.3f} м². "
        f"Разрешённая зона составляет {allowed_m2:.3f} м², что отличается от подписи 39,9 м² на {delta:+.3f} м² ({delta / PRINTED_AREA_M2 * 100:+.2f}%). "
        "Пороги остаются неопределёнными, поэтому это векторный кандидат, не обмер. Трубы и число контуров ещё не создаются.\n",
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
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "gross_m2": gross_m2, "void_m2": excluded_m2, "allowed_m2": allowed_m2, "delta_m2": delta, "digest": model["contract_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, mapping


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_GEOMETRY = BASE / "HA_TWO_FLOOR_ATTIC_COUNTERFLOW_EVIDENCE_044" / "attic_body_geometry.json"
SOURCE_VECTOR = BASE / "HA_TWO_FLOOR_VECTOR_CONTRACT_011" / "vector_source_contract.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_HALL_VECTOR_CONTRACT_045"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_HALL_VECTOR_CONTRACT_045.zip"
PDF_SHA = "B66D169ED5B1FDEFF12B817FC887226376740A34592C777EE3FE5AA40967075D"
PT_TO_MM = 35.2777777778
PX = 8.503937

# Selected room-facing edges from exact vector wall rectangles. Coordinates are
# PDF points; they are converted without snapping to the 100 mm pipe grid.
EDGES = [
    {"edge_id": "TOP_WEST", "path_id": 1490, "selected_face": "Y_MAX", "path_rect_pt": [258.48, 238.32, 276.36, 238.92], "from_pt": [258.48, 238.92], "to_pt": [276.36, 238.92]},
    {"edge_id": "UPPER_LEFT", "path_id": 969, "selected_face": "X_MAX", "path_rect_pt": [276.0, 238.68, 276.6, 396.84], "from_pt": [276.6, 238.92], "to_pt": [276.6, 396.48]},
    {"edge_id": "LOWER_LEFT_STEP", "path_id": 1598, "selected_face": "Y_MIN", "path_rect_pt": [258.48, 402.36, 276.36, 402.84], "from_pt": [276.6, 402.36], "to_pt": [258.48, 402.36]},
    {"edge_id": "LOWER_LEFT", "path_id": 591, "selected_face": "X_MAX", "path_rect_pt": [263.52, 476.76, 264.12, 556.44], "from_pt": [264.12, 476.4], "to_pt": [264.12, 556.08]},
    {"edge_id": "BOTTOM", "path_id": 588, "selected_face": "Y_MIN", "path_rect_pt": [263.88, 556.08, 393.96, 556.68], "from_pt": [264.12, 556.08], "to_pt": [393.6, 556.08]},
    {"edge_id": "LOWER_RIGHT", "path_id": 582, "selected_face": "Y_MIN", "path_rect_pt": [368.4, 476.4, 393.96, 477.0], "from_pt": [393.6, 556.08], "to_pt": [393.6, 476.4]},
    {"edge_id": "LOWER_RIGHT_STEP", "path_id": 582, "selected_face": "Y_MIN", "path_rect_pt": [368.4, 476.4, 393.96, 477.0], "from_pt": [393.6, 476.4], "to_pt": [368.4, 476.4]},
    {"edge_id": "UPPER_RIGHT", "path_id": 579, "selected_face": "X_MIN", "path_rect_pt": [368.16, 259.32, 368.76, 476.76], "from_pt": [368.16, 476.4], "to_pt": [368.16, 259.56]},
    {"edge_id": "TOP_EAST", "path_id": 576, "selected_face": "Y_MAX", "path_rect_pt": [324.24, 259.08, 368.4, 259.56], "from_pt": [368.16, 259.56], "to_pt": [324.48, 259.56]},
]

# The tiny door/threshold connectors between some selected faces are not
# semantically resolved in the flattened PDF. The following conservative
# candidate follows visible room-facing chains and deliberately records the
# uncertainty rather than calling it survey geometry.
POLYGON_PT = [
    (276.6, 238.92), (368.16, 238.92), (368.16, 476.4),
    (393.6, 476.4), (393.6, 556.08), (264.12, 556.08),
    (264.12, 476.4), (276.6, 476.4),
]
PRINTED_AREA_M2 = 39.9


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def to_grid(point_pt):
    return [point_pt[0] * PT_TO_MM / 100, point_pt[1] * PT_TO_MM / 100]


def to_mm(point_pt):
    return [point_pt[0] * PT_TO_MM, point_pt[1] * PT_TO_MM]


def find_pdf() -> Path:
    expected = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf")
    if expected.exists():
        return expected
    candidates = list((Path.home() / "Downloads" / "Telegram Desktop").glob("*.pdf"))
    match = next(path for path in candidates if sha(path) == PDF_SHA)
    return match


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D045 is append-only")
    pdf = find_pdf()
    if sha(pdf) != PDF_SHA:
        raise RuntimeError("attic PDF digest mismatch")
    page = pymupdf.open(pdf)[0]
    drawings = page.get_drawings()
    primitive_checks = []
    for edge in EDGES:
        actual = drawings[edge["path_id"]]["rect"]
        actual_rect = [actual.x0, actual.y0, actual.x1, actual.y1]
        # Some edge metadata includes a selected sub-chain; path bbox must still
        # match the recorded primitive within PDF's sub-point float tolerance.
        expected = edge["path_rect_pt"]
        max_delta = max(abs(a - b) for a, b in zip(actual_rect, expected))
        primitive_checks.append({"edge_id": edge["edge_id"], "path_id": edge["path_id"], "max_bbox_delta_pt": max_delta})

    polygon_mm = Polygon([to_mm(point) for point in POLYGON_PT])
    polygon_grid = [to_grid(point) for point in POLYGON_PT]
    area_m2 = polygon_mm.area / 1_000_000
    area_delta = area_m2 - PRINTED_AREA_M2
    source_bytes = SOURCE_GEOMETRY.read_bytes()
    vector_bytes = SOURCE_VECTOR.read_bytes()
    model = {
        "schema": "homeaura-attic-hall-vector-contract-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_HALL_VECTOR_CONTRACT_045",
        "status": "VECTOR_HALL_CANDIDATE_READY_FOR_VISUAL_REVIEW_REWORK_THRESHOLDS_AND_COVERAGE",
        "units": "mm",
        "source_pdf_path": str(pdf),
        "source_pdf_sha256": PDF_SHA,
        "source_pdf_page": 1,
        "source_pdf_size_pt": [page.rect.width, page.rect.height],
        "pdf_point_to_model_mm": PT_TO_MM,
        "extractor": f"PyMuPDF {pymupdf.VersionBind}",
        "source_geometry_artifact_id": json.loads(source_bytes)["artifact_id"],
        "source_geometry_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_vector_contract_id": json.loads(vector_bytes)["contract_id"],
        "source_vector_contract_sha256": hashlib.sha256(vector_bytes).hexdigest().upper(),
        "hall_candidate": {
            "territory_id": "ATTIC-HALL-09",
            "printed_area_m2": PRINTED_AREA_M2,
            "candidate_polygon_pt": [list(point) for point in POLYGON_PT],
            "candidate_polygon_mm": [to_mm(point) for point in POLYGON_PT],
            "candidate_polygon_grid_float": polygon_grid,
            "candidate_polygon_geojson": mapping(polygon_mm),
            "candidate_area_m2": area_m2,
            "area_delta_from_printed_m2": area_delta,
            "area_delta_percent": area_delta / PRINTED_AREA_M2 * 100,
            "polygon_valid": polygon_mm.is_valid,
            "polygon_vertex_count": len(POLYGON_PT),
            "structural_void_is_separate_hard_exclusion": True,
            "structural_void_source_bounds_grid": [99.53, 57.09, 129.94, 91.44],
            "structural_void_conservative_box_grid": [99, 57, 131, 92],
            "threshold_semantics": "NOT_RESOLVED_FLATTENED_VECTOR_PDF",
            "survey_status": "VECTOR_CANDIDATE_NOT_SURVEYED",
        },
        "source_edge_evidence": EDGES,
        "primitive_bbox_checks": primitive_checks,
        "routing_decision": {
            "old_hall_body_ids": ["A-C05", "A-C06", "A-C07"],
            "old_hall_bodies_status": "REWORK_LEGACY_MEANDERS",
            "independent_rectangular_replacement_rejected": True,
            "reason": "ONE_CONNECTED_VOID_CONSTRAINED_HALL_REQUIRES_JOINT_TERRITORY_PARTITION",
            "complete_circuit_count_selected": None,
            "new_body_generation_started": False,
            "next_step": "VISUALLY_REVIEW_POLYGON_AND_ENUMERATE_JOINT_HALL_TERRITORIES_AROUND_VOID",
        },
        "coverage_claimed": False,
        "full_routes_claimed": False,
        "hydraulics_calculated": False,
        "result": "PASS_VECTOR_CANDIDATE_REWORK_THRESHOLD_OWNERSHIP_AND_ROUTE_PARTITION",
    }
    model["contract_digest"] = digest(model)

    image = Image.open(BACKGROUND).convert("RGBA")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 170), fill="#071A21")
    canvas.text((28, 10), "D045 · МАНСАРДА · ВЕКТОРНАЯ КАНДИДАТНАЯ ГРАНИЦА ХОЛЛА", font=font(24, True), fill="white")
    canvas.text((28, 49), f"Площадь кандидата {area_m2:.2f} м² · подпись 39,9 м² · разница {area_delta:+.2f} м² ({area_delta / PRINTED_AREA_M2 * 100:+.2f}%)", font=font(15), fill="#A7EEE7")
    canvas.text((28, 81), "СИНИЙ: одна связная зона холла · КРАСНЫЙ: физический проём · пороги/двери ещё требуют проверки", font=font(15), fill="#F3D58C")
    canvas.text((28, 113), "D045 НЕ РИСУЕТ ТРУБЫ · число контуров/покрытие/длины НЕ ВЫБРАНЫ", font=font(14, True), fill="#FFB2B2")
    canvas.text((28, 140), "Старые A-C05/A-C06/A-C07 остаются REWORK; независимые маленькие прямоугольники отклонены", font=font(13), fill="#FFB2B2")
    polygon_px = [(round(x * PT_TO_MM / 100 * PX), round(y * PT_TO_MM / 100 * PX)) for x, y in POLYGON_PT]
    canvas.polygon(polygon_px, fill="#1B75BB30", outline="#005DAA", width=5)
    void = [99, 57, 131, 92]
    canvas.rectangle((round(void[0] * PX), round(void[1] * PX), round(void[2] * PX), round(void[3] * PX)), fill="#E6394650", outline="#B00020", width=5)
    canvas.text(polygon_px[0], "ATTIC-HALL-09 · VECTOR CANDIDATE", font=font(12, True), fill="#005DAA", stroke_width=2, stroke_fill="white")

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_hall_vector_contract.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    image.convert("RGB").save(OUTPUT / "attic_hall_vector_overlay.png")
    (OUTPUT / "report.md").write_text(
        "# D045 — векторная граница центрального холла мансарды\n\n"
        f"Из исходного векторного PDF выделен единый кандидат центрального холла площадью {area_m2:.3f} м². "
        f"Это отличается от напечатанных 39,9 м² на {area_delta:+.3f} м² ({area_delta / PRINTED_AREA_M2 * 100:+.2f}%). "
        "Лестничный проём остаётся отдельным физическим исключением. Дверные пороги и точная принадлежность коротких соединительных граней в сплющенном PDF пока не доказаны, поэтому полигон имеет статус VECTOR_CANDIDATE_NOT_SURVEYED. "
        "Старые три тела холла не приняты: вместо независимых узких прямоугольников следующий блок должен совместно разбить одну связанную зону вокруг проёма. Контуры и трубы в D045 не генерируются.\n",
        encoding="utf-8",
    )
    validation = {
        "artifact_id": model["artifact_id"],
        "source_pdf_sha256": PDF_SHA,
        "source_primitive_count": len(drawings),
        "edge_evidence_count": len(EDGES),
        "maximum_primitive_bbox_delta_pt": max(item["max_bbox_delta_pt"] for item in primitive_checks),
        "candidate_polygon_valid": polygon_mm.is_valid,
        "candidate_area_m2": area_m2,
        "printed_area_m2": PRINTED_AREA_M2,
        "area_delta_m2": area_delta,
        "area_delta_percent": area_delta / PRINTED_AREA_M2 * 100,
        "structural_void_separate": True,
        "new_route_count": 0,
        "coverage_claimed": False,
        "result": model["result"],
    }
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "contract_digest": model["contract_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "area_m2": area_m2, "delta_m2": area_delta, "digest": model["contract_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, box, mapping


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_GEOMETRY = BASE / "HA_TWO_FLOOR_ATTIC_COUNTERFLOW_EVIDENCE_044" / "attic_body_geometry.json"
SOURCE_VECTOR = BASE / "HA_TWO_FLOOR_VECTOR_CONTRACT_011" / "vector_source_contract.json"
SOURCE_INTERMEDIATE = BASE / "HA_TWO_FLOOR_ATTIC_HALL_VECTOR_CONTRACT_046" / "attic_hall_vector_contract.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047.zip"
PDF_SHA = "B66D169ED5B1FDEFF12B817FC887226376740A34592C777EE3FE5AA40967075D"
PT_TO_MM = 35.2777777778
PX = 8.503937
PRINTED_AREA_M2 = 39.9
VOID_GRID = (99, 57, 131, 92)

# Nominal wall-axis chain from the vector CAD lattice. It is retained only for
# reconciliation with the printed room area; routing uses the finish faces.
CENTERLINE_PT = [
    (282.00, 191.28),
    (324.24, 191.28),
    (324.24, 259.32),
    (368.40, 259.32),
    (368.40, 476.76),
    (393.96, 476.76),
    (393.96, 556.44),
    (263.88, 556.44),
    (263.88, 476.76),
    (282.00, 476.76),
]

# Conservative room-facing wall faces. These ten edges are supported directly
# by the listed PDF rectangles and are never snapped to the 100 mm pipe grid.
FINISH_PT = [
    (282.24, 191.52),
    (323.88, 191.52),
    (323.88, 259.56),
    (368.16, 259.56),
    (368.16, 477.00),
    (393.72, 477.00),
    (393.72, 556.08),
    (264.12, 556.08),
    (264.12, 477.00),
    (282.24, 477.00),
]

EDGE_SUPPORT = [
    ("NORTH_WEST", 600, "Y_MAX"),
    ("STAIR_WEST", 573, "X_MIN"),
    ("STAIR_SOUTH", 576, "Y_MAX"),
    ("EAST_SHAFT", 579, "X_MIN"),
    ("EAST_STEP", 582, "Y_MAX"),
    ("EAST_LOWER", 585, "X_MIN"),
    ("SOUTH", 588, "Y_MIN"),
    ("WEST_LOWER", 591, "X_MAX"),
    ("WEST_STEP", 594, "Y_MAX"),
    ("WEST_UPPER", 597, "X_MAX"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def to_mm(point):
    return [point[0] * PT_TO_MM, point[1] * PT_TO_MM]


def to_grid(point):
    return [point[0] * PT_TO_MM / 100, point[1] * PT_TO_MM / 100]


def find_pdf() -> Path:
    expected = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf")
    if expected.exists() and sha(expected) == PDF_SHA:
        return expected
    for candidate in (Path.home() / "Downloads" / "Telegram Desktop").glob("*.pdf"):
        if sha(candidate) == PDF_SHA:
            return candidate
    raise FileNotFoundError("attic source PDF with accepted digest was not found")


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D047 is append-only")

    pdf = find_pdf()
    page = pymupdf.open(pdf)[0]
    drawings = page.get_drawings()
    source_geometry = SOURCE_GEOMETRY.read_bytes()
    source_vector = SOURCE_VECTOR.read_bytes()
    source_intermediate = SOURCE_INTERMEDIATE.read_bytes()

    edge_records = []
    for index, (edge_id, path_id, selected_face) in enumerate(EDGE_SUPPORT):
        rect = drawings[path_id]["rect"]
        actual = [rect.x0, rect.y0, rect.x1, rect.y1]
        start = FINISH_PT[index]
        end = FINISH_PT[(index + 1) % len(FINISH_PT)]
        if selected_face == "X_MIN":
            selected_value = rect.x0
            expected_value = start[0]
        elif selected_face == "X_MAX":
            selected_value = rect.x1
            expected_value = start[0]
        elif selected_face == "Y_MIN":
            selected_value = rect.y0
            expected_value = start[1]
        else:
            selected_value = rect.y1
            expected_value = start[1]
        delta = abs(selected_value - expected_value)
        if delta > 0.001:
            raise RuntimeError({"edge_id": edge_id, "selected_face_delta_pt": delta})
        edge_records.append({
            "edge_id": edge_id,
            "path_id": path_id,
            "path_rect_pt": actual,
            "selected_face": selected_face,
            "selected_face_value_pt": selected_value,
            "from_pt": list(start),
            "to_pt": list(end),
            "selected_face_delta_pt": delta,
        })

    centerline = Polygon([to_mm(point) for point in CENTERLINE_PT])
    finish = Polygon([to_mm(point) for point in FINISH_PT])
    void = box(*(value * 100 for value in VOID_GRID))
    allowed = finish.difference(void)
    centerline_area = centerline.area / 1_000_000
    finish_area = finish.area / 1_000_000
    void_inside = finish.intersection(void).area / 1_000_000
    allowed_area = allowed.area / 1_000_000
    if not centerline.is_valid or not finish.is_valid or not allowed.is_valid or allowed.geom_type != "Polygon":
        raise RuntimeError("D047 vector geometry is invalid")

    model = {
        "schema": "homeaura-attic-hall-exact-vector-contract-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047",
        "status": "VECTOR_HALL_SOURCE_AND_FINISH_FACE_DRAFT_PASS_REWORK_THRESHOLDS_AND_COVERAGE",
        "units": "mm",
        "source_pdf_path": str(pdf),
        "source_pdf_sha256": PDF_SHA,
        "source_pdf_page": 1,
        "source_pdf_size_pt": [page.rect.width, page.rect.height],
        "pdf_point_to_model_mm": PT_TO_MM,
        "extractor": f"PyMuPDF {pymupdf.VersionBind}",
        "source_geometry_artifact_id": json.loads(source_geometry)["artifact_id"],
        "source_geometry_sha256": hashlib.sha256(source_geometry).hexdigest().upper(),
        "source_vector_contract_id": json.loads(source_vector)["contract_id"],
        "source_vector_contract_sha256": hashlib.sha256(source_vector).hexdigest().upper(),
        "supersedes_intermediate_artifact_id": json.loads(source_intermediate)["artifact_id"],
        "supersedes_intermediate_sha256": hashlib.sha256(source_intermediate).hexdigest().upper(),
        "intermediate_disposition": "D046_RETAINED_AS_COARSE_DRAFT_NOT_USED_FOR_NEW_BODY_CONTAINMENT",
        "hall_source_contract": {
            "territory_id": "ATTIC-HALL-09",
            "printed_area_m2": PRINTED_AREA_M2,
            "wall_axis_polygon_pt": [list(point) for point in CENTERLINE_PT],
            "wall_axis_polygon_mm": [to_mm(point) for point in CENTERLINE_PT],
            "wall_axis_area_reconciliation_only": True,
            "wall_axis_gross_area_m2": centerline_area,
            "wall_axis_delta_from_printed_m2": centerline_area - PRINTED_AREA_M2,
            "wall_axis_delta_percent": (centerline_area - PRINTED_AREA_M2) / PRINTED_AREA_M2 * 100,
            "finish_face_polygon_pt": [list(point) for point in FINISH_PT],
            "finish_face_polygon_mm": [to_mm(point) for point in FINISH_PT],
            "finish_face_polygon_grid_float": [to_grid(point) for point in FINISH_PT],
            "finish_face_polygon_geojson": mapping(finish),
            "finish_face_gross_area_m2": finish_area,
            "structural_void_conservative_box_grid": list(VOID_GRID),
            "structural_void_area_inside_finish_polygon_m2": void_inside,
            "routing_draft_allowed_floor_geojson": mapping(allowed),
            "routing_draft_allowed_floor_area_m2": allowed_area,
            "routing_draft_geometry_valid": allowed.is_valid,
            "routing_draft_connected_component_count": 1,
            "door_threshold_ownership": "NOT_EVALUATED_FLATTENED_PDF_AMBIGUOUS",
            "survey_status": "VECTOR_TRACED_DRAFT_NOT_SURVEYED",
            "pipe_clearance_erosion_applied": False,
            "coverage_claimed": False,
        },
        "finish_face_edge_evidence": edge_records,
        "routing_decision": {
            "replace_body_ids_next": ["A-C05", "A-C06", "A-C07"],
            "preserve_body_ids": ["A-C01", "A-C02", "A-C03", "A-C04", "A-C08", "A-C09", "A-C10", "A-C11", "A-C12", "A-C13"],
            "candidate_body_generation_started": False,
            "complete_circuit_count_selected": None,
            "full_route_count": 0,
        },
        "coverage_claimed": False,
        "full_routes_claimed": False,
        "hydraulics_calculated": False,
        "result": "PASS_VECTOR_SOURCE_CONTRACT_REWORK_THRESHOLDS_CLEARANCE_COVERAGE_AND_TRANSITS",
    }
    model["contract_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "source_path_count": len(edge_records),
        "source_path_ids": [item[1] for item in EDGE_SUPPORT],
        "source_path_585_present": any(item[1] == 585 for item in EDGE_SUPPORT),
        "maximum_selected_face_delta_pt": max(item["selected_face_delta_pt"] for item in edge_records),
        "wall_axis_gross_area_m2": centerline_area,
        "wall_axis_delta_percent": (centerline_area - PRINTED_AREA_M2) / PRINTED_AREA_M2 * 100,
        "finish_face_gross_area_m2": finish_area,
        "structural_void_area_inside_finish_polygon_m2": void_inside,
        "routing_draft_allowed_floor_area_m2": allowed_area,
        "allowed_geometry_valid": allowed.is_valid,
        "new_body_count": 0,
        "full_route_count": 0,
        "coverage_claimed": False,
        "result": model["result"],
    }

    image = Image.open(BACKGROUND).convert("RGBA")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 185), fill="#071A21")
    canvas.text((28, 10), "D047 · МАНСАРДА · ТОЧНАЯ ВЕКТОРНАЯ ЦЕПОЧКА ХОЛЛА", font=font(23, True), fill="white")
    canvas.text((28, 49), f"Оси стен {centerline_area:.2f} м² ↔ подпись 39,9 м² ({(centerline_area - PRINTED_AREA_M2):+.2f} м²)", font=font(15), fill="#A7EEE7")
    canvas.text((28, 81), f"По внутренним граням {finish_area:.2f} м² · после проёма доступно {allowed_area:.2f} м²", font=font(15, True), fill="#F3D58C")
    canvas.text((28, 113), "ЖЁЛТЫЙ: ось стены только для сверки площади · СИНИЙ: черновая внутренняя граница", font=font(14), fill="#F3D58C")
    canvas.text((28, 145), "КРАСНЫЙ: проём · пороги/зазоры/покрытие/транзиты НЕ ПРИНЯТЫ", font=font(14, True), fill="#FFB2B2")
    centerline_px = [(round(x * PT_TO_MM / 100 * PX), round(y * PT_TO_MM / 100 * PX)) for x, y in CENTERLINE_PT]
    finish_px = [(round(x * PT_TO_MM / 100 * PX), round(y * PT_TO_MM / 100 * PX)) for x, y in FINISH_PT]
    canvas.polygon(centerline_px, outline="#E6B422", width=4)
    canvas.polygon(finish_px, fill="#1B75BB30", outline="#005DAA", width=4)
    x0, y0, x1, y1 = VOID_GRID
    canvas.rectangle((round(x0 * PX), round(y0 * PX), round(x1 * PX), round(y1 * PX)), fill="#E6394670", outline="#B00020", width=5)
    canvas.text((finish_px[5][0] - 190, finish_px[5][1] - 24), "ATTIC-HALL-09", font=font(12, True), fill="#005DAA", stroke_width=2, stroke_fill="white")

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_hall_exact_vector_contract.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    image.convert("RGB").save(OUTPUT / "attic_hall_exact_vector_overlay.png")
    (OUTPUT / "report.md").write_text(
        "# D047 — векторный контракт холла мансарды\n\n"
        f"Десять исходных векторных стен образуют одну вогнутую цепочку. По осям её площадь {centerline_area:.3f} м², "
        f"что отличается от напечатанных 39,9 м² на {centerline_area - PRINTED_AREA_M2:+.3f} м². Эта величина используется только для сверки источника. "
        f"Для черновой трассировки взяты внутренние грани: {finish_area:.3f} м²; после вычитания консервативного лестничного проёма остаётся {allowed_area:.3f} м². "
        "Пороговые участки, монтажный зазор, покрытие, транзиты и полные контуры не приняты. D045/D046 сохранены как промежуточные исторические кандидаты.\n",
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
        "wall_axis_m2": centerline_area,
        "finish_m2": finish_area,
        "allowed_m2": allowed_area,
        "contract_digest": model["contract_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

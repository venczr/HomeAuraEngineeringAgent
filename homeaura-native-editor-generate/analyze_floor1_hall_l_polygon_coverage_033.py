from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Polygon, box, mapping
from shapely.ops import unary_union


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_NORTH_HALL_029"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_HALL_L_POLYGON_COVERAGE_033"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_HALL_L_POLYGON_COVERAGE_033.zip"
MM_PER_PDF_POINT = 35.27777777777778
PX_PER_MM = 8.503937 / 100

# Six finish-face coordinates directly supported by thin vector wall rectangles.
HALL_L_PDF_POINTS = [
    (272.64, 153.24),
    (357.96, 153.24),
    (357.96, 464.40),
    (306.60, 464.40),
    (306.60, 402.96),
    (272.64, 402.96),
]
HALL_SOURCE_PATH_IDS = [15, 3, 6, 9, 12, 4252, 4207]
TREAD_PDF_BOUNDS = (321.36, 278.76, 357.96, 304.80)
TREAD_SOURCE_PATH_IDS = [4459, 4456, 4453, 4501, 4498]
CONSERVATIVE_CENTERLINE_TREAD_BOX_GRID = (113, 98, 127, 108)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def to_mm(point):
    return point[0] * MM_PER_PDF_POINT, point[1] * MM_PER_PDF_POINT


def to_px(point_mm):
    return round(point_mm[0] * PX_PER_MM), round(point_mm[1] * PX_PER_MM)


def polygon_list(geometry):
    return list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]


def fill_geometry(canvas, geometry, fill, outline):
    for polygon in polygon_list(geometry):
        canvas.polygon([to_px(point) for point in polygon.exterior.coords], fill=fill, outline=outline)
        for interior in polygon.interiors:
            canvas.polygon([to_px(point) for point in interior.coords], fill="#F7CACA", outline="#B00020")


def draw(model, hall_polygon, tread, allowed, served, unresolved, target, metrics):
    image = Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 150), fill="#071A21")
    canvas.text((28, 12), "D033 · Г-ОБРАЗНАЯ ВЕКТОРНАЯ ГРАНИЦА ХОЛЛА · D029 НЕ ИЗМЕНЁН", font=font(24, True), fill="white")
    canvas.text(
        (28, 55),
        f'До ступеней {metrics["hall_gross_area_m2"]:.2f} м² (план: 30,7) · отапливаемо {metrics["allowed_area_m2"]:.2f} м² · обслужено {metrics["served_area_m2"]:.2f} м² ({metrics["served_ratio_percent"]:.1f}%)',
        font=font(15), fill="#A7EEE7",
    )
    canvas.text((28, 87), f'Остаток {metrics["unresolved_area_m2"]:.2f} м² · круглый радиус 100 мм · C07 НЕ ДОБАВЛЯТЬ', font=font(15), fill="#F3D58C")
    canvas.text((28, 117), "REWORK: пороги дверей неоднозначны; физическая зона ступеней и консервативный осевой запрет хранятся раздельно", font=font(13), fill="#E8F0F2")

    fill_geometry(canvas, allowed, "#F1F4F4B5", "#243B45")
    fill_geometry(canvas, served, "#41B88375", "#16845B")
    fill_geometry(canvas, unresolved, "#E148557D", "#B00020")
    canvas.polygon([to_px(point) for point in tread.exterior.coords], fill="#F7CACA", outline="#B00020")
    canvas.text(to_px((TREAD_PDF_BOUNDS[0] * MM_PER_PDF_POINT, (TREAD_PDF_BOUNDS[1] - 6) * MM_PER_PDF_POINT)), "3 СТУПЕНИ", font=font(11, True), fill="#B00020")

    colours = [
        "#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC",
        "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93",
    ]
    for route, colour in zip(model["routes"], colours):
        points = [to_px(point) for point in route["ordered_points_mm"]]
        canvas.line(points, fill="white", width=8, joint="curve")
        canvas.line(points, fill=colour, width=4, joint="curve")

    y = 162
    canvas.rectangle((15, y, 475, y + 184), fill="#FFFFFFE8", outline="#526A73")
    canvas.text((30, y + 10), "КРУПНЫЕ ОСТАТКИ (>0,01 м²):", font=font(13, True), fill="#17313C")
    for index, component in enumerate(metrics["material_unresolved_components"][:5], start=1):
        canvas.text((30, y + 10 + index * 28), f'{index}. {component["area_m2"]:.3f} м² · {component["bounds_mm"]}', font=font(11), fill="#8C1722")
    image.save(target, quality=96)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D033 is append-only")
    source_bytes = (SOURCE / "canonical_geometry.json").read_bytes()
    model = json.loads(source_bytes.decode("utf-8"))
    hall_polygon = Polygon([to_mm(point) for point in HALL_L_PDF_POINTS])
    tread = box(*[value * MM_PER_PDF_POINT for value in TREAD_PDF_BOUNDS])
    allowed = hall_polygon.difference(tread)
    sweeps = [LineString(route["ordered_points_mm"]).buffer(100, cap_style=1, join_style=1, quad_segs=16) for route in model["routes"]]
    served = allowed.intersection(unary_union(sweeps))
    unresolved = allowed.difference(served)
    components = sorted(polygon_list(unresolved), key=lambda item: item.area, reverse=True)
    material = [component for component in components if component.area >= 10_000]
    micro = [component for component in components if component.area < 10_000]

    metrics = {
        "artifact_id": "HA_TWO_FLOOR_FLOOR1_HALL_L_POLYGON_COVERAGE_033",
        "status": "VECTOR_L_POLYGON_DRAFT_REQUIRES_THRESHOLD_REVIEW",
        "source_artifact_id": model["artifact_id"],
        "source_geometry_digest": model["geometry_digest"],
        "route_geometry_modified": False,
        "pdf_to_mm": MM_PER_PDF_POINT,
        "hall_finish_face_polygon_pdf_points": HALL_L_PDF_POINTS,
        "hall_finish_face_polygon_mm": [to_mm(point) for point in HALL_L_PDF_POINTS],
        "hall_source_path_ids": HALL_SOURCE_PATH_IDS,
        "hall_gross_area_m2": round(hall_polygon.area / 1_000_000, 6),
        "printed_hall_area_m2": 30.7,
        "gross_area_delta_from_printed_m2": round(hall_polygon.area / 1_000_000 - 30.7, 6),
        "physical_first_three_treads_pdf_bounds": TREAD_PDF_BOUNDS,
        "physical_first_three_treads_mm_bounds": [value * MM_PER_PDF_POINT for value in TREAD_PDF_BOUNDS],
        "tread_source_path_ids": TREAD_SOURCE_PATH_IDS,
        "physical_tread_area_m2": round(tread.area / 1_000_000, 6),
        "conservative_centerline_tread_box_grid": CONSERVATIVE_CENTERLINE_TREAD_BOX_GRID,
        "allowed_area_m2": round(allowed.area / 1_000_000, 6),
        "served_area_m2": round(served.area / 1_000_000, 6),
        "unresolved_area_m2": round(unresolved.area / 1_000_000, 6),
        "served_ratio_percent": round(100 * served.area / allowed.area, 4),
        "distance_model": "TRUE_ROUND_EUCLIDEAN_BUFFER_100MM",
        "route_parts_included": "ALL_COMPLETE_SUPPLY_BODY_RETURN_CENTERLINES",
        "material_unresolved_component_count": len(material),
        "micro_corner_component_count": len(micro),
        "micro_corner_total_area_m2": round(sum(component.area for component in micro) / 1_000_000, 6),
        "material_unresolved_components": [
            {"area_m2": round(component.area / 1_000_000, 6), "bounds_mm": [round(value) for value in component.bounds], "geometry": mapping(component)}
            for component in material
        ],
        "threshold_ownership": "NOT_EVALUATED_FLATTENED_PDF_AMBIGUOUS",
        "exterior_wall_100mm_band_evaluated": False,
        "pipe_surface_clearance_evaluated": False,
        "C07_decision": "DO_NOT_ADD_RESIDUAL_BODY_EQUIVALENT_APPROX_25M_IS_NOT_A_NATURAL_40M_LOOP",
        "full_coverage_claimed": False,
        "result": "REWORK_EXISTING_ROUTE_REBALANCE_BEFORE_ANY_C07",
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry_d029.json").write_bytes(source_bytes)
    (OUTPUT / "hall_l_polygon_coverage.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, hall_polygon, tread, allowed, served, unresolved, OUTPUT / "floor_1_hall_l_polygon_coverage.png", metrics)
    (OUTPUT / "report.md").write_text(
        "# D033 — Г-образная граница холла\n\n"
        f"Маршруты D029 не изменены. Шесть граней из векторного PDF дают площадь холла {metrics['hall_gross_area_m2']:.2f} м² до исключения ступеней; расхождение с подписью 30,7 м² равно {metrics['gross_area_delta_from_printed_m2']:.2f} м². "
        f"После вычитания физической зоны первых трёх ступеней отапливаемая площадь чернового полигона равна {metrics['allowed_area_m2']:.2f} м². Круглый 100-мм буфер всех полных труб обслуживает {metrics['served_area_m2']:.2f} м² ({metrics['served_ratio_percent']:.1f}%), остаток {metrics['unresolved_area_m2']:.2f} м². "
        "Остаток фрагментирован и соответствует примерно 25 м трубы с шагом 200 мм, поэтому отдельный C07 не создаётся. Сначала следует перераспределить существующие транзиты и C05/C06. Пороги дверей и наружная 100-мм зона ещё не приняты.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({"artifact_id": metrics["artifact_id"], "source_geometry_digest": model["geometry_digest"], "append_only": True, "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files]}, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "gross_m2": metrics["hall_gross_area_m2"], "allowed_m2": metrics["allowed_area_m2"], "served_m2": metrics["served_area_m2"], "unresolved_m2": metrics["unresolved_area_m2"], "ratio": metrics["served_ratio_percent"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

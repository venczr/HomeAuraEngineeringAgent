from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, box, mapping
from shapely.ops import unary_union


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_NORTH_HALL_029"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_HALL_VECTOR_COVERAGE_032"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_HALL_VECTOR_COVERAGE_032.zip"
PX_PER_MM = 8.503937 / 100

HALL_FINISH_FACE_MM = (9618.133333, 5405.966667, 12628.033333, 16383.0)
TREAD_BOX_MM = (11300, 9800, 12700, 10800)
PRINTED_HALL_AREA_MM2 = 30_700_000


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def to_px_mm(point):
    return round(point[0] * PX_PER_MM), round(point[1] * PX_PER_MM)


def polygon_paths(geometry):
    polygons = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
    for polygon in polygons:
        yield [to_px_mm(point) for point in polygon.exterior.coords]
        for interior in polygon.interiors:
            yield [to_px_mm(point) for point in interior.coords]


def draw(model: dict, allowed, served, unresolved, target: Path, metrics: dict) -> None:
    image = Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 146), fill="#071A21")
    canvas.text((28, 12), "D032 · ВЕКТОРНАЯ ДИАГНОСТИКА ХОЛЛА · МАРШРУТЫ D029 НЕ ИЗМЕНЕНЫ", font=font(24, True), fill="white")
    canvas.text(
        (28, 55),
        f'Черновая граница {metrics["draft_allowed_area_m2"]:.2f} м² · обслужено {metrics["served_area_m2"]:.2f} м² ({metrics["served_ratio_percent"]:.1f}%) · остаток {metrics["unresolved_area_m2"]:.2f} м²',
        font=font(16), fill="#A7EEE7",
    )
    canvas.text((28, 88), "ЗЕЛЁНЫЙ: ≤100 мм от оси трубы · КРАСНЫЙ: дальше 100 мм · первые 3 ступени исключены", font=font(14), fill="#E8F0F2")
    canvas.text((28, 116), "СТАТУС REWORK: прямоугольник извлечён из векторных граней; требуется проверка дверных проёмов и точного контура лестницы", font=font(13), fill="#F3D58C")

    for path in polygon_paths(allowed):
        canvas.polygon(path, fill="#F1F4F4A8", outline="#243B45")
    for path in polygon_paths(served):
        canvas.polygon(path, fill="#41B88370", outline="#16845B")
    for path in polygon_paths(unresolved):
        canvas.polygon(path, fill="#E148557D", outline="#B00020")

    tx0, ty0, tx1, ty1 = TREAD_BOX_MM
    canvas.rectangle((*to_px_mm((tx0, ty0)), *to_px_mm((tx1, ty1))), fill="#F7CACA", outline="#B00020", width=3)
    canvas.text(to_px_mm((tx0, ty0 - 220)), "NO PIPE · 3 СТУПЕНИ", font=font(11, True), fill="#B00020")

    colours = [
        "#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC",
        "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93",
    ]
    for route, colour in zip(model["routes"], colours):
        points = [to_px_mm(point) for point in route["ordered_points_mm"]]
        canvas.line(points, fill="white", width=8, joint="curve")
        canvas.line(points, fill=colour, width=4, joint="curve")

    y = 160
    canvas.rectangle((15, y, 465, y + 158), fill="#FFFFFFE8", outline="#526A73")
    canvas.text((30, y + 12), "КРУПНЫЕ ОСТАТКИ (черновые):", font=font(13, True), fill="#17313C")
    for index, component in enumerate(metrics["largest_unresolved_components"][:4], start=1):
        canvas.text(
            (30, y + 12 + index * 27),
            f'{index}. {component["area_m2"]:.2f} м² · {component["bounds_mm"]}',
            font=font(12), fill="#8C1722",
        )
    image.save(target, quality=96)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D032 is append-only")
    source_bytes = (SOURCE / "canonical_geometry.json").read_bytes()
    model = json.loads(source_bytes.decode("utf-8"))
    hall_rect = box(*HALL_FINISH_FACE_MM)
    tread = box(*TREAD_BOX_MM)
    allowed = hall_rect.difference(tread)

    route_sweeps = [
        LineString(route["ordered_points_mm"]).buffer(100, cap_style=2, join_style=2)
        for route in model["routes"]
    ]
    served = allowed.intersection(unary_union(route_sweeps))
    unresolved = allowed.difference(served)
    components = sorted(list(unresolved.geoms) if unresolved.geom_type == "MultiPolygon" else [unresolved], key=lambda item: item.area, reverse=True)

    metrics = {
        "method": "VECTOR_FINISH_FACE_RECTANGLE_MINUS_TREADS__ALL_COMPLETE_ROUTE_CENTERLINES_BUFFER_100MM",
        "status": "DRAFT_VECTOR_POLYGON_DIAGNOSTIC_REQUIRES_DOOR_AND_STAIR_CONTOUR_REVIEW",
        "source_artifact_id": model["artifact_id"],
        "source_geometry_digest": model["geometry_digest"],
        "route_geometry_modified": False,
        "hall_finish_face_source_pdf_points": [272.64, 153.24, 357.96, 464.4],
        "hall_finish_face_mm": list(HALL_FINISH_FACE_MM),
        "first_three_treads_mm": list(TREAD_BOX_MM),
        "draft_allowed_area_m2": round(allowed.area / 1_000_000, 6),
        "printed_hall_area_m2": PRINTED_HALL_AREA_MM2 / 1_000_000,
        "draft_minus_printed_area_m2": round((allowed.area - PRINTED_HALL_AREA_MM2) / 1_000_000, 6),
        "served_area_m2": round(served.area / 1_000_000, 6),
        "unresolved_area_m2": round(unresolved.area / 1_000_000, 6),
        "served_ratio_percent": round(100 * served.area / allowed.area, 4),
        "unresolved_ratio_percent": round(100 * unresolved.area / allowed.area, 4),
        "service_radius_mm": 100,
        "spacing_interpretation": "200MM_FIELD_DIAGNOSTIC_ONLY",
        "transit_segments_included": True,
        "exterior_wall_100mm_band_evaluated": False,
        "pipe_surface_clearance_evaluated": False,
        "C07_decision": "DO_NOT_ADD_FROM_DRAFT_RECTANGLE_ALONE",
        "largest_unresolved_components": [
            {
                "area_m2": round(component.area / 1_000_000, 6),
                "bounds_mm": [round(value) for value in component.bounds],
                "geometry": mapping(component),
            }
            for component in components
        ],
        "full_coverage_claimed": False,
        "result": "REWORK_REVIEW_VECTOR_POLYGON_BEFORE_C07_DECISION",
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry_d029.json").write_bytes(source_bytes)
    (OUTPUT / "hall_vector_coverage.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, allowed, served, unresolved, OUTPUT / "floor_1_hall_vector_coverage.png", metrics)
    (OUTPUT / "report.md").write_text(
        "# D032 — черновая векторная диагностика центрального холла\n\n"
        f"Маршруты D029 не изменены. Граница холла взята напрямую с четырёх векторных граней PDF: x=272,64…357,96 pt, y=153,24…464,40 pt. "
        f"После исключения первых трёх ступеней получается {metrics['draft_allowed_area_m2']:.2f} м², что на {metrics['draft_minus_printed_area_m2']:.2f} м² больше напечатанной площади 30,7 м². "
        f"При диагностическом радиусе 100 мм от всех полных маршрутов обслужено {metrics['served_area_m2']:.2f} м² ({metrics['served_ratio_percent']:.1f}%), остаток {metrics['unresolved_area_m2']:.2f} м². "
        "Это не окончательное покрытие: прямоугольник включает стеновые и дверные особенности, которые нужно вычесть по векторным контурам. Поэтому C07 пока не добавляется.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    manifest = {
        "artifact_id": "HA_TWO_FLOOR_FLOOR1_HALL_VECTOR_COVERAGE_032",
        "source_geometry_digest": model["geometry_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "served_m2": metrics["served_area_m2"], "unresolved_m2": metrics["unresolved_area_m2"], "ratio": metrics["served_ratio_percent"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

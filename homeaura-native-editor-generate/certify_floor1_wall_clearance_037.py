from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Polygon, box, mapping
from shapely.ops import unary_union


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_EXTERIOR_THREE_PASS_035"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_WALL_CLEARANCE_037"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_WALL_CLEARANCE_037.zip"
PDF_PATH = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План 1 этажа с отметками (2).pdf")
PDF_SHA256 = "40F396CBB4F7FB6D1DAFC198CE81492999A34F66C2F96D113CA8D33360586B25"
MM_PER_PDF_POINT = 35.27777777777778
PX_PER_GRID = 8.503937
PX_PER_MM = PX_PER_GRID / 100
TREAD_GRID_BOX = (113, 98, 127, 108)
HALL_L_PDF_POINTS = [
    (272.64, 153.24),
    (357.96, 153.24),
    (357.96, 464.40),
    (306.60, 464.40),
    (306.60, 402.96),
    (272.64, 402.96),
]
PHYSICAL_TREAD_PDF_BOUNDS = (321.36, 278.76, 357.96, 304.80)
NORTH_LANDING_PDF_BOUNDS = (272.64, 153.24, 357.96, 182.40)

spec = importlib.util.spec_from_file_location(
    "d034_core_for_d037",
    ROOT / "homeaura-native-editor-generate" / "rebalance_floor1_north_transit_bank_034.py",
)
d034 = importlib.util.module_from_spec(spec)
sys.modules["d034_core_for_d037"] = d034
assert spec.loader is not None
spec.loader.exec_module(d034)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest().upper()


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def to_mm(point):
    return point[0] * MM_PER_PDF_POINT, point[1] * MM_PER_PDF_POINT


def mm_to_px(point):
    return round(point[0] * PX_PER_MM), round(point[1] * PX_PER_MM)


def grid_to_px(point):
    return round(point[0] * PX_PER_GRID), round(point[1] * PX_PER_GRID)


def polygons(geometry):
    return list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]


def coverage_geometry(model):
    hall = Polygon([to_mm(point) for point in HALL_L_PDF_POINTS])
    treads = box(*[value * MM_PER_PDF_POINT for value in PHYSICAL_TREAD_PDF_BOUNDS])
    allowed = hall.difference(treads)
    sweeps = unary_union([
        LineString(route["ordered_points_mm"]).buffer(100, cap_style=1, join_style=1, quad_segs=16)
        for route in model["routes"]
    ])
    served = allowed.intersection(sweeps)
    unresolved = allowed.difference(served)
    landing = box(*[value * MM_PER_PDF_POINT for value in NORTH_LANDING_PDF_BOUNDS])
    landing_served = landing.intersection(sweeps)
    routable = box(
        landing.bounds[0] + 100,
        landing.bounds[1] + 100,
        landing.bounds[2] - 100,
        landing.bounds[3] - 100,
    )
    routable_served = routable.intersection(sweeps)
    return hall, treads, allowed, served, unresolved, landing, landing_served, routable, routable_served


def segment_hits_box(a, b, bounds) -> bool:
    x0, y0, x1, y1 = bounds
    if a[0] == b[0]:
        return x0 <= a[0] <= x1 and max(min(a[1], b[1]), y0) <= min(max(a[1], b[1]), y1)
    return y0 <= a[1] <= y1 and max(min(a[0], b[0]), x0) <= min(max(a[0], b[0]), x1)


def validate_routes(model):
    tread_hits = 0
    lengths = {}
    for route in model["routes"]:
        points = [tuple(point) for point in route["ordered_points_grid"]]
        topology = d034.core.topology(points)
        if topology["result"] != "PASS":
            raise RuntimeError({"route": route["route_id"], "topology": topology})
        measured = sum((abs(a[0] - b[0]) + abs(a[1] - b[1])) * 100 for a, b in zip(points, points[1:]))
        if measured != route["total_length_mm"] or not 40_000 <= measured <= 80_000:
            raise RuntimeError({"route": route["route_id"], "measured": measured})
        tread_hits += sum(segment_hits_box(a, b, TREAD_GRID_BOX) for a, b in zip(points, points[1:]))
        lengths[route["route_id"]] = measured
    contacts = d034.core.inter_contacts(model["routes"])
    if contacts or tread_hits:
        raise RuntimeError({"contacts": contacts, "tread_hits": tread_hits})
    return lengths


def fill_geometry(canvas, geometry, fill, outline):
    for polygon in polygons(geometry):
        canvas.polygon([mm_to_px(point) for point in polygon.exterior.coords], fill=fill, outline=outline)
        for interior in polygon.interiors:
            canvas.polygon([mm_to_px(point) for point in interior.coords], fill="#F7CACA", outline="#B00020")


def draw(model, metrics, geometries, target: Path, pipes_only: bool):
    hall, treads, allowed, served, unresolved, landing, _, _, _ = geometries
    image = Image.new("RGB", (1785, 1750), "#F7FAFA") if pipes_only else Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    if pipes_only:
        step = round(PX_PER_GRID)
        for x in range(0, image.width, step):
            canvas.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, step):
            canvas.line((0, y, image.width, y), fill="#D8E2E2")
    else:
        fill_geometry(canvas, allowed, "#F1F4F45A", "#526A73")
        fill_geometry(canvas, served, "#41B88335", "#16845B")
        fill_geometry(canvas, unresolved, "#E148555E", "#B00020")
        canvas.rectangle((*mm_to_px((landing.bounds[0], landing.bounds[1])), *mm_to_px((landing.bounds[2], landing.bounds[3]))), outline="#7A49E5", width=3)

    canvas.rectangle((0, 0, image.width, 155), fill="#071A21")
    canvas.text((28, 10), f'{metrics["artifact_short_id"]} · 12 КОНТУРОВ · ГЕОМЕТРИЯ D035 СОХРАНЕНА', font=font(24, True), fill="white")
    canvas.text(
        (28, 50),
        "Север: y=56/57/58 — 100 мм; затем y=60/62/64/66/68 — 200 мм · контактов 0",
        font=font(16), fill="#A7EEE7",
    )
    canvas.text(
        (28, 82),
        f'Грань {metrics["wall_finish_face_mm"]:.2f} мм · min {metrics["required_centerline_clearance_mm"]:.0f} мм · первая ось 5600 мм · факт {metrics["actual_centerline_clearance_mm"]:.2f} мм',
        font=font(15), fill="#F3D58C",
    )
    canvas.text(
        (28, 113),
        f'Черновой L-полигон: {metrics["hall_served_ratio_percent"]:.1f}% · покрытие REWORK · C07 не добавлен',
        font=font(14), fill="#E8F0F2",
    )

    x0, y0, x1, y1 = model["collector_contract"]["station_envelope_bbox_grid"]
    if pipes_only:
        canvas.rectangle((*grid_to_px((x0, y0)), *grid_to_px((x1, y1))), outline="#006D67", width=3)
        canvas.text(grid_to_px((x0 + 1, y0 + 2)), "K1 LOGICAL", font=font(11, True), fill="#006D67")
    tx0, ty0, tx1, ty1 = TREAD_GRID_BOX
    canvas.rectangle((*grid_to_px((tx0, ty0)), *grid_to_px((tx1, ty1))), fill="#F7CACA", outline="#B00020", width=3)
    canvas.text(grid_to_px((tx0, ty0 - 2)), "3 СТУПЕНИ", font=font(11, True), fill="#B00020")

    colours = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC", "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93"]
    for route, colour in zip(model["routes"], colours):
        points = [grid_to_px(point) for point in route["ordered_points_grid"]]
        canvas.line(points, fill="white", width=9, joint="curve")
        canvas.line(points, fill=colour, width=4, joint="curve")
        anchor = grid_to_px(route["heating_body_points_grid"][len(route["heating_body_points_grid"]) // 2])
        canvas.text((anchor[0] + 3, anchor[1] + 3), f'{route["route_id"]} {route["total_length_mm"] / 1000:.1f} м', font=font(10, True), fill=colour, stroke_width=2, stroke_fill="white")
    image.save(target, quality=96)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D037 is append-only")
    if sha(PDF_PATH) != PDF_SHA256:
        raise RuntimeError("source PDF digest changed")

    source_path = SOURCE / "canonical_geometry.json"
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    model = json.loads(source_bytes.decode("utf-8"))
    lengths = validate_routes(model)
    geometries = coverage_geometry(model)
    hall, treads, allowed, served, unresolved, landing, landing_served, routable, routable_served = geometries

    wall_finish_face_pt = 153.24
    wall_finish_face_mm = wall_finish_face_pt * MM_PER_PDF_POINT
    required_clearance = 100
    first_valid_grid_mm = math.ceil((wall_finish_face_mm + required_clearance) / 100) * 100
    actual_clearance = first_valid_grid_mm - wall_finish_face_mm
    if first_valid_grid_mm != 5600 or actual_clearance < required_clearance:
        raise RuntimeError("wall clearance derivation failed")

    metrics = {
        "artifact_id": "HA_TWO_FLOOR_FLOOR1_WALL_CLEARANCE_037",
        "artifact_short_id": "D037",
        "status": "GEOMETRY_AND_NORTH_BANK_SPACING_PASS_REWORK_HALL_COVERAGE",
        "source_artifact_id": source["artifact_id"],
        "source_geometry_digest": source["geometry_digest"],
        "ordered_route_geometry_modified": False,
        "source_pdf_sha256": PDF_SHA256,
        "source_pdf_page_index": 0,
        "source_path_id": 18,
        "source_path_rect_pdf_pt": [272.28, 152.64, 358.20, 153.24],
        "selected_finish_face": "LOWER_INTERIOR_EDGE_Y_MAX",
        "wall_finish_face_pdf_y_pt": wall_finish_face_pt,
        "wall_finish_face_mm": round(wall_finish_face_mm, 6),
        "required_centerline_clearance_mm": required_clearance,
        "first_valid_grid_formula": "ceil((finish_face_mm + required_clearance_mm) / 100) * 100",
        "first_valid_grid_node_mm": first_valid_grid_mm,
        "first_valid_grid_node_y": 56,
        "actual_centerline_clearance_mm": round(actual_clearance, 6),
        "grid_overshoot_beyond_required_mm": round(actual_clearance - required_clearance, 6),
        "rejected_y55_clearance_mm": round(5500 - wall_finish_face_mm, 6),
        "rejected_y55_result": "FAIL_BELOW_100MM",
        "ordered_north_bank_y_grid": [56, 57, 58, 60, 62, 64, 66, 68],
        "adjacent_delta_grid": [1, 1, 2, 2, 2, 2, 2],
        "exterior_adjacent_passes_y_grid": [56, 57, 58],
        "field_passes_y_grid": [60, 62, 64, 66, 68],
        "spacing_scope": "NORTH_ENTRY_TRANSIT_BANK_ONLY",
        "full_exterior_band_evaluated": False,
        "hall_candidate_polygon_pdf_points": HALL_L_PDF_POINTS,
        "hall_candidate_gross_area_m2": round(hall.area / 1_000_000, 6),
        "printed_hall_area_m2": 30.7,
        "hall_allowed_area_m2": round(allowed.area / 1_000_000, 6),
        "hall_served_area_m2": round(served.area / 1_000_000, 6),
        "hall_unresolved_area_m2": round(unresolved.area / 1_000_000, 6),
        "hall_served_ratio_percent": round(100 * served.area / allowed.area, 4),
        "hall_semantics": "ROOM2_HALL_L_POLYGON_VECTOR_DRAFT_THRESHOLD_OWNERSHIP_NOT_RESOLVED",
        "north_entry_landing": {
            "pdf_bounds": NORTH_LANDING_PDF_BOUNDS,
            "area_m2": round(landing.area / 1_000_000, 6),
            "label_interpretation": "3.03_WIDTH_DIMENSION_CANDIDATE",
            "is_separate_room_claimed": False,
            "semantic_ownership": "PROVISIONAL_ROOM2_HALL_ENTRY_LANDING",
            "finish_face_domain_served_area_m2": round(landing_served.area / 1_000_000, 6),
            "finish_face_domain_unresolved_area_m2": round(landing.difference(landing_served).area / 1_000_000, 6),
            "finish_face_domain_served_ratio_percent": round(100 * landing_served.area / landing.area, 4),
            "routable_domain_definition": "100MM_INSET_FROM_FINISH_FACE_RECTANGLE",
            "routable_domain_area_m2": round(routable.area / 1_000_000, 6),
            "routable_domain_served_area_m2": round(routable_served.area / 1_000_000, 6),
            "routable_domain_served_ratio_percent": round(100 * routable_served.area / routable.area, 4),
        },
        "distance_model": "TRUE_ROUND_EUCLIDEAN_BUFFER_100MM_QUAD_SEGS_16",
        "route_parts_included": "ALL_COMPLETE_SUPPLY_BODY_RETURN_CENTERLINES",
        "C07_decision": "DO_NOT_ADD_FRAGMENTED_RESIDUAL_AND_POLYGON_STILL_DRAFT",
        "full_coverage_claimed": False,
        "result": "PASS_ROUTE_GEOMETRY_AND_BANK_SPACING_REWORK_POLYGON_COVERAGE",
    }

    model["artifact_id"] = metrics["artifact_id"]
    model["status"] = metrics["status"]
    model["derived_from_artifact_id"] = source["artifact_id"]
    model["derived_from_geometry_digest"] = source["geometry_digest"]
    contract = model["collector_contract"]
    contract["contract_id"] = "HA_TWO_FLOOR_K1_TWELVE_ROUTE_GATE_CONTRACT_037"
    contract["west_wall_face_gate_bbox_grid"] = [129, 56, 129, 81]
    bank = contract["north_transit_bank_reassignment"]
    bank.pop("lane_spacing_mm", None)
    bank.update(
        ordered_y_grid=metrics["ordered_north_bank_y_grid"],
        adjacent_delta_grid=metrics["adjacent_delta_grid"],
        spacing_scope=metrics["spacing_scope"],
        full_exterior_band_evaluated=False,
        wall_source_path_id=18,
        wall_finish_face_pdf_y_pt=wall_finish_face_pt,
        required_centerline_clearance_mm=required_clearance,
        first_valid_grid_node_y=56,
        actual_centerline_clearance_mm=round(actual_clearance, 6),
        spacing_result="PASS_FOR_NORTH_ENTRY_TRANSIT_BANK_ONLY",
    )
    contract.pop("contract_digest", None)
    contract["contract_digest"] = digest(contract)
    model["wall_clearance_and_coverage_evidence"] = metrics
    model["whole_floor_completion"] = False
    model["whole_house_completion"] = False
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)

    validation = {
        "artifact_id": metrics["artifact_id"],
        "source_canonical_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "route_count": len(model["routes"]),
        "route_geometry_preserved": all(
            route["ordered_points_grid"] == source_route["ordered_points_grid"]
            for route, source_route in zip(model["routes"], source["routes"])
        ),
        "lengths_mm": lengths,
        "all_lengths_40_80m": all(40_000 <= value <= 80_000 for value in lengths.values()),
        "global_inter_route_contact_count": 0,
        "first_three_tread_hit_count": 0,
        "port_coordinate_count": len({tuple(route[key]) for route in model["routes"] for key in ("supply_port_grid", "return_port_grid")}),
        "wall_clearance": {key: metrics[key] for key in (
            "source_pdf_sha256", "source_path_id", "source_path_rect_pdf_pt", "selected_finish_face",
            "wall_finish_face_pdf_y_pt", "wall_finish_face_mm", "required_centerline_clearance_mm",
            "first_valid_grid_node_mm", "actual_centerline_clearance_mm", "rejected_y55_clearance_mm", "rejected_y55_result",
        )},
        "spacing_validation": {
            "ordered_y_grid": metrics["ordered_north_bank_y_grid"],
            "adjacent_delta_grid": metrics["adjacent_delta_grid"],
            "exterior_three_pass_count": 3,
            "exterior_spacing_mm": 100,
            "field_spacing_mm": 200,
            "scope": metrics["spacing_scope"],
            "result": "PASS",
        },
        "hall_coverage": {key: metrics[key] for key in (
            "hall_allowed_area_m2", "hall_served_area_m2", "hall_unresolved_area_m2",
            "hall_served_ratio_percent", "hall_semantics", "full_coverage_claimed",
        )},
        "north_entry_landing": metrics["north_entry_landing"],
        "collector_contract_digest": contract["contract_digest"],
        "result": metrics["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "k1_twelve_route_gate_contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "source_provenance.json").write_text(json.dumps({
        "source_pdf_sha256": PDF_SHA256,
        "page_index": 0,
        "pdf_to_model_mm": MM_PER_PDF_POINT,
        "north_wall": {
            "path_id": 18,
            "raw_rect_pdf_pt": metrics["source_path_rect_pdf_pt"],
            "selected_finish_face": metrics["selected_finish_face"],
            "finish_face_pdf_y_pt": wall_finish_face_pt,
            "finish_face_mm": round(wall_finish_face_mm, 6),
        },
        "hall_candidate_edges": [
            {"edge": "TOP", "path_id": 18, "selected_face_pdf_pt": wall_finish_face_pt},
            {"edge": "RIGHT", "path_id": 3, "selected_face_pdf_pt": 357.96},
            {"edge": "BOTTOM", "path_id": 6, "selected_face_pdf_pt": 464.40},
            {"edge": "LOWER_LEFT", "path_id": 9, "selected_face_pdf_pt": 306.60},
            {"edge": "STEP", "path_id": 12, "selected_face_pdf_pt": 402.96},
            {"edge": "UPPER_LEFT", "path_id": 15, "selected_face_pdf_pt": 272.64},
        ],
        "tread_support": {
            "source_path_ids": [4459, 4456, 4453, 4498, 4501, 4504],
            "physical_bounds_pdf_pt": PHYSICAL_TREAD_PDF_BOUNDS,
            "conservative_centerline_box_grid": TREAD_GRID_BOX,
        },
        "semantic_limit": "FLATTENED_VECTOR_PDF_HAS_NO_LAYERS_OR_MACHINE_READABLE_ROOM LABELS",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, metrics, geometries, OUTPUT / "floor_1_wall_clearance_overlay.png", False)
    draw(model, metrics, geometries, OUTPUT / "floor_1_wall_clearance_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D037 — правильная грань стены и первый допустимый узел\n\n"
        f"Геометрия 12 контуров D035 не изменена. Внутренняя грань северной стены PDF-path 18 равна {wall_finish_face_mm:.2f} мм. "
        f"При минимальном осевом отступе 100 мм первый узел 100-мм сетки — 5600 мм; фактический отступ {actual_clearance:.2f} мм. y=5500 отклонён: отступ лишь {5500-wall_finish_face_mm:.2f} мм. "
        "Пучок y=56,57,58,60,62,64,66,68 даёт ровно три прохода через 100 мм, затем 200 мм. "
        f"Круглый 100-мм диагностический буфер обслуживает {metrics['hall_served_ratio_percent']:.2f}% чернового L-полигона; это не теплотехническая достаточность. C07 не добавлен.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": metrics["artifact_id"],
        "geometry_digest": model["geometry_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "geometry_digest": model["geometry_digest"],
        "first_valid_grid_node_y": 56,
        "actual_clearance_mm": round(actual_clearance, 6),
        "hall_ratio": metrics["hall_served_ratio_percent"],
        "landing_ratio": metrics["north_entry_landing"]["finish_face_domain_served_ratio_percent"],
        "contacts": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

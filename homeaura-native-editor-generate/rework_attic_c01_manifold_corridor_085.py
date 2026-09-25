from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.affinity import translate
from shapely.geometry import LineString, box, shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_050 = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
SOURCE_062 = BASE / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
SOURCE_081 = BASE / "HA_TWO_FLOOR_ATTIC_WARDROBE_MANIFOLD_081" / "attic_wardrobe_manifold.json"
SOURCE_082 = BASE / "HA_TWO_FLOOR_ATTIC_MANIFOLD_SERVICE_ZONE_082" / "attic_manifold_service_zone.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085.zip"

DX_MM = 359.83333333356
DY_MM = 304.8
PX_PER_100_MM = 8.503937
NEW_C01_ENVELOPE_GRID = (49, 61, 92, 81)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


d044 = load_module(
    "attic_d044_for_d085",
    ROOT / "homeaura-native-editor-generate" / "certify_attic_counterflow_evidence_044.py",
)
core = d044.core


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def font(size: int, bold: bool = False):
    return ImageFont.truetype(
        str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size
    )


def manhattan(a, b) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def body_line(route: dict) -> LineString:
    return LineString([(x * 100, y * 100) for x, y in route["body_points_grid"]])


def registered_line(route: dict) -> LineString:
    return translate(body_line(route), xoff=-DX_MM, yoff=-DY_MM)


def draw(model: dict, service_bbox: list[int], corridor_bbox: list[float], target: Path, pipes_only: bool):
    image = Image.new("RGB", (1785, 1750), "#F7FAFA") if pipes_only else Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    if pipes_only:
        step = round(PX_PER_100_MM)
        for x in range(0, image.width, step):
            canvas.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, step):
            canvas.line((0, y, image.width, y), fill="#D8E2E2")

    canvas.rectangle((0, 0, image.width, 205), fill="#071A21")
    corridor = model["manifold_outlet_corridor_validation"]
    coverage = model["wardrobe_body_coverage_diagnostic"]
    canvas.text((28, 13), "D085 · C01 ОСВОБОЖДАЕТ ВЫХОДЫ K2 В ГАРДЕРОБНУЮ", font=font(23, True), fill="white")
    canvas.text((28, 54), f'C01: {model["body_lengths_mm"]["A-C01"] / 1000:.1f} м · регулярная улитка 400/200 мм · остальные 12 тел неизменны', font=font(16, True), fill="#A7EEE7")
    canvas.text((28, 91), f'Свободная полоса между осью C01 и зоной K2: {corridor["minimum_axis_to_service_zone_clearance_mm"]:.1f} мм', font=font(16), fill="#F3D58C")
    canvas.text((28, 128), f'Черновое покрытие гардеробной C01: {coverage["coverage_ratio"] * 100:.1f}% · нижняя оценка петли от K2: {model["c01_optimistic_complete_lower_bound"]["total_mm"] / 1000:.1f} м', font=font(15, True), fill="white")
    canvas.text((28, 165), "ПОРТЫ K2 / ПОДВОДКИ / ГИДРАВЛИКА НЕ НАРИСОВАНЫ · покрытие и изделие остаются REWORK", font=font(14, True), fill="#FFB2B2")

    def px_raw_mm(x: float, y: float):
        return (x / 100 * PX_PER_100_MM, y / 100 * PX_PER_100_MM)

    def raw_bbox_from_building(bounds):
        return [bounds[0] + DX_MM, bounds[1] + DY_MM, bounds[2] + DX_MM, bounds[3] + DY_MM]

    raw_service = raw_bbox_from_building(service_bbox)
    raw_corridor = raw_bbox_from_building(corridor_bbox)
    x0, y0 = px_raw_mm(raw_corridor[0], raw_corridor[1])
    x1, y1 = px_raw_mm(raw_corridor[2], raw_corridor[3])
    canvas.rectangle((x0, y0, x1, y1), fill="#FFD45C55", outline="#9A7300", width=2)
    canvas.text((x0 - 48, y0 - 32), "ВЫХОДНАЯ ПОЛОСА", font=font(10, True), fill="#805E00", stroke_width=2, stroke_fill="white")

    sx0, sy0 = px_raw_mm(raw_service[0], raw_service[1])
    sx1, sy1 = px_raw_mm(raw_service[2], raw_service[3])
    canvas.rectangle((sx0, sy0, sx1, sy1), fill="#00A66A33", outline="#006A43", width=3)
    canvas.text((sx0 + 4, sy0 + 4), "K2 SERVICE", font=font(10, True), fill="#006A43", stroke_width=2, stroke_fill="white")

    colours = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC", "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93", "#8A5A00"]
    for route, colour in zip(model["body_routes"], colours):
        points = [px_raw_mm(x * 100, y * 100) for x, y in route["body_points_grid"]]
        canvas.line(points, fill="white", width=9, joint="curve")
        canvas.line(points, fill=colour, width=4, joint="curve")
        if route["route_id"] == "A-C01":
            canvas.text((points[0][0] - 50, points[0][1] + 12), "A-C01", font=font(12, True), fill=colour, stroke_width=2, stroke_fill="white")
    image.save(target)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D085 is append-only")
    raw_050, source = read(SOURCE_050)
    raw_062, domains = read(SOURCE_062)
    raw_081, topology = read(SOURCE_081)
    raw_082, service_model = read(SOURCE_082)
    model = deepcopy(source)
    source_routes = {route["route_id"]: deepcopy(route) for route in source["body_routes"]}
    c01 = next(route for route in model["body_routes"] if route["route_id"] == "A-C01")
    old_c01 = source_routes["A-C01"]

    points, _ = core.paired_counterflow(NEW_C01_ENVELOPE_GRID)
    c01.update(
        body_points_grid=[list(point) for point in points],
        body_points_mm=[[x * 100, y * 100] for x, y in points],
        body_length_mm=core.length_mm(points),
        body_envelope_grid=list(NEW_C01_ENVELOPE_GRID),
        body_topology_validation=core.topology(points),
        body_digest=digest([[x * 100, y * 100] for x, y in points]),
        geometry_orientation="IDENTITY",
        owner_style_validation={"result": "PASS", "scope": "BODY_ONLY_REGULAR_COUNTERFLOW"},
    )
    c01["regularity_validation"] = d044.certify_route(c01)
    if c01["body_topology_validation"]["result"] != "PASS" or c01["regularity_validation"]["result"] != "PASS":
        raise RuntimeError({"topology": c01["body_topology_validation"], "regularity": c01["regularity_validation"]})

    domain = next(item for item in domains["adjacent_floor_domains"] if item["domain_id"] == "ATTIC_LEFT_NORTH_RECT_DRAFT")
    wardrobe_raw = shape(domain["floor_geojson"])
    wardrobe_building = translate(wardrobe_raw, xoff=-DX_MM, yoff=-DY_MM)
    c01_raw_line = body_line(c01)
    c01_building_line = registered_line(c01)
    service_bbox = service_model["service_zone_bbox_building_mm"]
    service = box(*service_bbox)
    corridor_width = c01_building_line.distance(service)
    corridor_bbox = [c01_building_line.bounds[2], service_bbox[1], service_bbox[0], service_bbox[3]]
    if corridor_width < 229 or not wardrobe_building.covers(c01_building_line) or c01_building_line.intersects(service):
        raise RuntimeError({"corridor_width": corridor_width, "contained": wardrobe_building.covers(c01_building_line)})

    all_lines = {route["route_id"]: body_line(route) for route in model["body_routes"]}
    inter_contacts = []
    route_ids = list(all_lines)
    for index, first in enumerate(route_ids):
        for second in route_ids[index + 1:]:
            if all_lines[first].intersects(all_lines[second]):
                inter_contacts.append([first, second])
    if inter_contacts:
        raise RuntimeError({"inter_body_contacts": inter_contacts})

    source_anchor = topology["attic_manifold_reservation"]["routing_anchor_building_mm"]
    registered_points = [(x - DX_MM, y - DY_MM) for x, y in c01["body_points_mm"]]
    supply_lower = manhattan(source_anchor, registered_points[0])
    return_lower = manhattan(registered_points[-1], source_anchor)
    optimistic_total = c01["body_length_mm"] + supply_lower + return_lower

    old_line = body_line(old_c01)
    old_served = wardrobe_raw.intersection(old_line.buffer(100, quad_segs=16, cap_style="round", join_style="round"))
    new_served = wardrobe_raw.intersection(c01_raw_line.buffer(100, quad_segs=16, cap_style="round", join_style="round"))
    old_ratio = old_served.area / wardrobe_raw.area
    new_ratio = new_served.area / wardrobe_raw.area
    body_lengths = {route["route_id"]: route["body_length_mm"] for route in model["body_routes"]}

    model.update(
        schema="homeaura-attic-c01-manifold-corridor-0.1",
        artifact_id="HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085",
        status="C01_REGULAR_BODY_AND_K2_OUTLET_CORRIDOR_PASS_REWORK_PORT_FANOUT_COVERAGE_AND_COMPLETE_ROUTES",
        source_records=[
            {"artifact_id": data["artifact_id"], "sha256": hashlib.sha256(raw).hexdigest().upper()}
            for raw, data in ((raw_050, source), (raw_062, domains), (raw_081, topology), (raw_082, service_model))
        ],
        immediate_body_parent_artifact_id=source["artifact_id"],
        immediate_body_parent_sha256=hashlib.sha256(raw_050).hexdigest().upper(),
        preserved_body_route_count=12,
        preserved_body_route_ids=[route_id for route_id in source_routes if route_id != "A-C01"],
        changed_body_route_ids=["A-C01"],
        body_lineage=[{
            "route_id": "A-C01",
            "source_envelope_grid": old_c01["body_envelope_grid"],
            "current_envelope_grid": list(NEW_C01_ENVELOPE_GRID),
            "source_body_digest": old_c01["body_digest"],
            "current_body_digest": c01["body_digest"],
            "source_length_mm": old_c01["body_length_mm"],
            "current_length_mm": c01["body_length_mm"],
            "reason": "FREE_K2_WALL_SIDE_OUTLET_CORRIDOR_WHILE_PRESERVING_REGULAR_COUNTERFLOW_AND_40_80M_LOWER_BOUND",
        }],
        body_lengths_mm=body_lengths,
        body_length_range_mm=[min(body_lengths.values()), max(body_lengths.values())],
        body_count_at_least_40000mm=sum(value >= 40_000 for value in body_lengths.values()),
        body_count_below_40000mm=sum(value < 40_000 for value in body_lengths.values()),
        inter_body_contact_count=len(inter_contacts),
        wardrobe_draft_domain_validation={
            "source_domain_id": domain["domain_id"],
            "source_status": domain["status"],
            "c01_centerline_fully_contained": wardrobe_raw.covers(c01_raw_line),
            "minimum_centerline_to_draft_boundary_mm": c01_raw_line.distance(wardrobe_raw.boundary),
            "pipe_surface_clearance": "NOT_EVALUATED_FINAL_PIPE_BUILDUP_AND_SURVEY_MISSING",
            "result": "PASS_VECTOR_DRAFT_CENTERLINE_CONTAINMENT_REWORK_SURVEY_AND_SURFACE_CLEARANCE",
        },
        manifold_outlet_corridor_validation={
            "source_service_zone_artifact_id": service_model["artifact_id"],
            "service_zone_bbox_building_mm": service_bbox,
            "c01_centerline_bounds_building_mm": list(c01_building_line.bounds),
            "corridor_bbox_building_mm": corridor_bbox,
            "minimum_axis_to_service_zone_clearance_mm": corridor_width,
            "owner_minimum_bend_radius_mm": 80,
            "clearance_exceeds_twice_owner_bend_radius": corridor_width >= 160,
            "c01_contact_with_service_zone": c01_building_line.intersects(service),
            "port_positions_or_fanout_geometry_published": False,
            "result": "PASS_FREE_PLAN_STRIP_REWORK_PRODUCT_PORT_FANOUT_AND_PIPE_SURFACE_ENVELOPE",
        },
        c01_optimistic_complete_lower_bound={
            "routing_anchor_building_mm": source_anchor,
            "body_length_mm": c01["body_length_mm"],
            "supply_manhattan_lower_bound_mm": supply_lower,
            "return_manhattan_lower_bound_mm": return_lower,
            "total_mm": optimistic_total,
            "within_40_80m": 40_000 <= optimistic_total <= 80_000,
            "complete_route_geometry_published": False,
            "status": "LOWER_BOUND_ONLY_OBSTACLE_DETOURS_AND_K2_PORT_GEOMETRY_MISSING",
        },
        wardrobe_body_coverage_diagnostic={
            "method": "ROUND_100MM_C01_CENTERLINE_BUFFER_CLIPPED_TO_D062_WARDROBE_DRAFT_DOMAIN",
            "quad_segs": 16,
            "draft_domain_area_m2": wardrobe_raw.area / 1_000_000,
            "source_served_area_m2": old_served.area / 1_000_000,
            "current_served_area_m2": new_served.area / 1_000_000,
            "served_area_gain_m2": (new_served.area - old_served.area) / 1_000_000,
            "source_coverage_ratio": old_ratio,
            "coverage_ratio": new_ratio,
            "full_coverage_claimed": False,
            "result": "IMPROVED_PROXY_REWORK_EXACT_ROOM_COVERAGE_AND_EXTERIOR_BAND",
        },
        physical_K2_product_selected=False,
        K2_port_geometry_published=False,
        complete_attic_route_count=0,
        whole_attic_coverage_claimed=False,
        result="PASS_C01_REGULAR_BODY_AND_K2_OUTLET_CORRIDOR_REWORK_COMPLETE_ROUTES_AND_COVERAGE",
    )
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)

    validation = {
        "artifact_id": model["artifact_id"],
        "changed_route_id": "A-C01",
        "preserved_route_count": 12,
        "c01_body_length_mm": c01["body_length_mm"],
        "c01_topology_result": c01["body_topology_validation"]["result"],
        "c01_regularity_result": c01["regularity_validation"]["result"],
        "c01_minimum_segment_length_mm": c01["regularity_validation"]["minimum_segment_length_mm"],
        "inter_body_contact_count": len(inter_contacts),
        "service_zone_contact_count": int(c01_building_line.intersects(service)),
        "minimum_axis_to_service_zone_clearance_mm": corridor_width,
        "wardrobe_draft_containment": wardrobe_raw.covers(c01_raw_line),
        "minimum_centerline_to_draft_boundary_mm": c01_raw_line.distance(wardrobe_raw.boundary),
        "optimistic_complete_lower_bound_mm": optimistic_total,
        "optimistic_complete_lower_bound_within_40_80m": 40_000 <= optimistic_total <= 80_000,
        "coverage_ratio_before": old_ratio,
        "coverage_ratio_after": new_ratio,
        "complete_route_geometry_published": False,
        "result": model["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_body_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, service_bbox, corridor_bbox, OUTPUT / "attic_c01_manifold_corridor_overlay.png", False)
    draw(model, service_bbox, corridor_bbox, OUTPUT / "attic_c01_manifold_corridor_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D085 — свободная полоса между C01 и коллектором K2\n\n"
        f"Только тело A-C01 перестроено из рамки {old_c01['body_envelope_grid']} в {list(NEW_C01_ENVELOPE_GRID)}. "
        f"Длина тела выросла с {old_c01['body_length_mm'] / 1000:.1f} до {c01['body_length_mm'] / 1000:.1f} м; геометрия остаётся регулярной прямоугольной улиткой 400/200 мм с центральным разворотом 200 мм. "
        f"Между осью C01 и сервисной зоной K2 освобождена непрерывная плановая полоса минимум {corridor_width:.1f} мм — больше двойного принятого владельцем радиуса 80 мм. "
        f"Черновой 100-мм буфер C01 внутри векторной области гардеробной вырос с {old_ratio * 100:.1f}% до {new_ratio * 100:.1f}%. "
        f"Оптимистическая нижняя оценка петли от опорной точки K2 равна {optimistic_total / 1000:.1f} м и лежит в диапазоне 40–80 м. "
        "Порты коллектора, 24 подводки, точное покрытие, выбранное изделие и гидравлическая увязка не опубликованы и остаются REWORK.\n",
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
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "c01_length_mm": c01["body_length_mm"],
        "corridor_clearance_mm": corridor_width,
        "boundary_clearance_mm": c01_raw_line.distance(wardrobe_raw.boundary),
        "optimistic_total_mm": optimistic_total,
        "coverage_ratio": new_ratio,
        "digest": model["geometry_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

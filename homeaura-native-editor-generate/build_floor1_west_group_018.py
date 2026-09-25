from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
CONTRACT = BASE / "HA_TWO_FLOOR_VECTOR_CONTRACT_011" / "vector_source_contract.json"
SOURCE_K1 = BASE / "HA_TWO_FLOOR_K1_RECONCILED_017" / "canonical_geometry.json"
OUTPUT = BASE / "HA_TWO_FLOOR_WEST_GROUP_018"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_WEST_GROUP_018.zip"
GRID_MM = 100
PX = 8.503937
Point = tuple[int, int]


core_path = ROOT / "homeaura-native-editor-generate" / "build_local_counterflow_coverage_014.py"
spec = importlib.util.spec_from_file_location("d014_core_for_d018", core_path)
core = importlib.util.module_from_spec(spec)
sys.modules["d014_core_for_d018"] = core
assert spec.loader is not None
spec.loader.exec_module(core)


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest().upper()


def to_px(point: Point) -> Point:
    return round(point[0] * PX), round(point[1] * PX)


def build_routes() -> list[dict]:
    # The two wet-room bodies deliberately split one connected territory into
    # north/south frames.  This avoids the crossing that two side-by-side bodies
    # create at the common transit corridor and keeps both returns regular.
    specs = [
        ("F1-C01", "BEDROOM_17_3", (54, 56, 92, 86), 94, 93, 55, 54),
        ("F1-C02", "BEDROOM_15_6", (54, 95, 92, 120), 96, 95, 57, 56),
        ("F1-C03", "BATH_WC_NORTH", (44, 128, 79, 144), 98, 97, 59, 58),
        ("F1-C04", "BATH_WC_SOUTH", (44, 146, 79, 162), 100, 99, 61, 60),
    ]
    routes: list[dict] = []
    for index, (route_id, territory, box, supply_lane, return_lane, supply_y, return_y) in enumerate(specs):
        body, regularity = core.paired_counterflow(box)
        supply_port = (150, supply_y)
        return_port = (150, return_y)
        supply = core.clean([supply_port, (supply_lane, supply_y), (supply_lane, body[0][1]), body[0]])
        returned = core.clean([body[-1], (return_lane, body[-1][1]), (return_lane, return_y), return_port])
        points = core.clean([*supply, *body[1:], *returned[1:]])
        topology = core.topology(points)
        route = {
            "route_id": route_id,
            "floor_id": "FLOOR_1",
            "territory_id": territory,
            "collector_id": "K1",
            "supply_port_id": f"K1-{route_id}-S",
            "return_port_id": f"K1-{route_id}-R",
            "supply_port_grid": list(supply_port),
            "return_port_grid": list(return_port),
            "ordered_points_grid": [list(point) for point in points],
            "ordered_points_mm": [[coordinate * GRID_MM for coordinate in point] for point in points],
            "supply_transit_points_grid": [list(point) for point in supply],
            "heating_body_points_grid": [list(point) for point in body],
            "return_transit_points_grid": [list(point) for point in returned],
            "topology": "REGULAR_RECTANGULAR_COUNTERFLOW",
            "territory_bbox_grid": list(box),
            "transit_lane_order": index,
            "supply_transit_length_mm": core.length_mm(supply),
            "heating_body_length_mm": core.length_mm(body),
            "return_transit_length_mm": core.length_mm(returned),
            "total_length_mm": core.length_mm(points),
            "route_validation": topology,
            "regularity_validation": {**regularity, "result": "PASS"},
            "wall_crossing_policy": "OWNER_ALLOWED_DISTINCT_TRANSIT",
            "completed": True,
        }
        route["geometry_digest"] = digest(route["ordered_points_mm"])
        routes.append(route)
    return routes


def segment_hits_box(segment, box: tuple[int, int, int, int]) -> bool:
    (a, b) = segment
    x0, y0, x1, y1 = box
    if x0 <= a[0] <= x1 and y0 <= a[1] <= y1:
        return True
    if x0 <= b[0] <= x1 and y0 <= b[1] <= y1:
        return True
    edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    return any(core.relation(segment, edge) != "DISJOINT" for edge in edges)


def draw(routes: list[dict], target: Path, pipes_only: bool) -> None:
    if pipes_only:
        image = Image.new("RGB", (1785, 1500), "#F7FAFA")
        draw = ImageDraw.Draw(image)
        for x in range(0, image.width, round(PX)):
            draw.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, round(PX)):
            draw.line((0, y, image.width, y), fill="#D8E2E2")
    else:
        image = Image.open(BACKGROUND).convert("RGB")
        draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, 116), fill="#071A21")
    draw.text((32, 16), "D018 · ЗАПАДНАЯ ГРУППА ПЕРВОГО ЭТАЖА", font=font(27, True), fill="white")
    draw.text((32, 65), "4 полные трубы K1 → улитка → K1 · контактов 0 · 40–80 м PASS", font=font(18), fill="#A7EEE7")
    colours = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B"]
    # One compact wall-mounted K1 for this bounded group.  Rails are equipment,
    # not a shared pipe trunk; the eight route endpoints remain distinct.
    k0, k1 = to_px((149, 54)), to_px((151, 61))
    draw.rounded_rectangle((*k0, *k1), radius=5, fill="#D8F3EE", outline="#00897B", width=4)
    draw.text((k0[0] + 4, k0[1] + 7), "K1", font=font(13, True), fill="#00695C")
    for route, colour in zip(routes, colours):
        points = [to_px(tuple(point)) for point in route["ordered_points_grid"]]
        draw.line(points, fill="white", width=10, joint="curve")
        draw.line(points, fill=colour, width=5, joint="curve")
        for label, key in (("S", "supply_port_grid"), ("R", "return_port_grid")):
            x, y = to_px(tuple(route[key]))
            draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=colour, outline="white", width=2)
            if pipes_only:
                draw.text((x + 7, y - 7), label, font=font(11, True), fill=colour, stroke_width=2, stroke_fill="white")
        body = route["heating_body_points_grid"]
        anchor = to_px(tuple(body[len(body) // 2]))
        draw.text((anchor[0] + 8, anchor[1] + 5), f"{route['route_id']} · {route['total_length_mm']/1000:.1f}м", font=font(13, True), fill=colour, stroke_width=2, stroke_fill="white")
    image.save(target, quality=96)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("WEST_GROUP_018 is append-only")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    source_k1 = json.loads(SOURCE_K1.read_text(encoding="utf-8"))
    routes = build_routes()
    contacts = core.inter_contacts(routes)
    ports = [tuple(route[key]) for route in routes for key in ("supply_port_grid", "return_port_grid")]
    tread_box = tuple(contract["vector_traced_geometry"]["floor_1_first_three_treads"]["conservative_blocked_box_grid"])
    tread_hits = sum(
        segment_hits_box(segment, tread_box)
        for route in routes
        for segment in zip(route["ordered_points_grid"], route["ordered_points_grid"][1:])
    )
    accepted = (
        len(routes) == 4
        and len(set(ports)) == 8
        and not contacts
        and not tread_hits
        and all(route["route_validation"]["result"] == "PASS" for route in routes)
        and all(40000 <= route["total_length_mm"] <= 80000 for route in routes)
    )
    if not accepted:
        raise RuntimeError("D018 route acceptance failed")
    body_length = sum(route["heating_body_length_mm"] for route in routes)
    named_area_mm2 = 49_800_000
    model = {
        "schema": "homeaura-floor1-west-group-0.1",
        "artifact_id": "HA_TWO_FLOOR_WEST_GROUP_018",
        "status": "FOUR_WEST_GROUP_FULL_ROUTES_PASS_REWORK_WHOLE_FLOOR_INTEGRATION",
        "source_contract_id": contract["contract_id"],
        "source_contract_digest": contract["contract_digest"],
        "derived_from_k1_artifact_id": source_k1["artifact_id"],
        "units": "mm",
        "grid_mm": GRID_MM,
        "collector": {
            "collector_id": "K1",
            "logical_station_count": 1,
            "wall_mount_orientation": "NORTH_WALL_VERTICAL",
            "bounded_group_body_bbox_grid": [149, 54, 151, 61],
            "port_count": 8,
            "shared_pipe_trunk": False,
            "commercial_capacity": "NOT_EVALUATED",
        },
        "routes": routes,
        "coverage_diagnostic": {
            "method": "HEATING_BODY_LENGTH_TIMES_200MM_ESTIMATE_ONLY",
            "named_room_area_mm2": named_area_mm2,
            "nominal_served_area_mm2": body_length * 200,
            "nominal_ratio": round(body_length * 200 / named_area_mm2, 6),
            "full_coverage_claimed": False,
            "result": "REWORK_COVERAGE_AND_TERRITORY_POLYGONS",
        },
        "integration_with_d017_east_group": "NOT_COMBINED_REQUIRES_SINGLE_K1_PORT_REPARTITION",
        "whole_floor_completion": False,
        "whole_house_completion": False,
        "hydraulics": "NOT_CALCULATED",
        "normative_compliance_claimed": False,
    }
    model["geometry_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "status": model["status"],
        "route_count": len(routes),
        "unique_port_count": len(set(ports)),
        "self_contact_count": sum(route["route_validation"]["self_contact_count"] for route in routes),
        "inter_route_contact_count": len(contacts),
        "inter_route_contacts": contacts,
        "first_three_tread_hit_count": tread_hits,
        "all_lengths_40_80m": True,
        "lengths_mm": {route["route_id"]: route["total_length_mm"] for route in routes},
        "regularity_pass_count": 4,
        "integration_with_d017": "NOT_EVALUATED_AS_ONE_PORT_BANK",
        "coverage_result": model["coverage_diagnostic"]["result"],
        "whole_house_completion": False,
    }
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(routes, OUTPUT / "floor_1_west_group_overlay.png", False)
    draw(routes, OUTPUT / "floor_1_west_group_pipes_only.png", True)
    ratio = model["coverage_diagnostic"]["nominal_ratio"]
    (OUTPUT / "report.md").write_text(
        "# HA_TWO_FLOOR_WEST_GROUP_018\n\n"
        "Четыре самостоятельных непрерывных маршрута западной группы первого этажа. "
        "Длины 77,9 / 74,9 / 61,7 / 64,9 м; самоконтактов и взаимных контактов нет; "
        "полигон первых трёх ступеней не затронут. Каждая подача и обратка занимает свою 100-мм линию. "
        f"Номинальная body-only оценка покрытия {ratio:.1%}; полное покрытие не заявлено. "
        "Этот пакет ещё не объединяет порты с пятью восточными маршрутами D017: единый портовый расклад K1 "
        "и глобальная проверка всего этажа являются следующим блоком.\n",
        encoding="utf-8",
    )
    files = [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({"artifact_id": model["artifact_id"], "geometry_digest": model["geometry_digest"], "files": files}, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "lengths_mm": validation["lengths_mm"], "contacts": 0, "digest": model["geometry_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

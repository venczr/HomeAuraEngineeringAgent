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
EAST_SOURCE = BASE / "HA_TWO_FLOOR_K1_RECONCILED_017" / "canonical_geometry.json"
WEST_SOURCE = BASE / "HA_TWO_FLOOR_WEST_GROUP_018" / "canonical_geometry.json"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_UNIFIED_019"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_UNIFIED_019.zip"
GRID_MM = 100
PX = 8.503937
Point = tuple[int, int]


core_path = ROOT / "homeaura-native-editor-generate" / "build_local_counterflow_coverage_014.py"
spec = importlib.util.spec_from_file_location("d014_core_for_d019", core_path)
core = importlib.util.module_from_spec(spec)
sys.modules["d014_core_for_d019"] = core
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


def west_routes(source: dict) -> list[dict]:
    gate_pairs = {
        "F1-C01": ((129, 65), (129, 64), 94, 93),
        "F1-C02": ((129, 67), (129, 66), 96, 95),
        "F1-C03": ((129, 69), (129, 68), 98, 97),
        "F1-C04": ((129, 71), (129, 70), 100, 99),
    }
    routes: list[dict] = []
    for old in source["routes"]:
        route_id = old["route_id"]
        supply_port, return_port, supply_lane, return_lane = gate_pairs[route_id]
        body = [tuple(point) for point in old["heating_body_points_grid"]]
        supply = core.clean([supply_port, (supply_lane, supply_port[1]), (supply_lane, body[0][1]), body[0]])
        returned = core.clean([body[-1], (return_lane, body[-1][1]), (return_lane, return_port[1]), return_port])
        points = core.clean([*supply, *body[1:], *returned[1:]])
        route = json.loads(json.dumps(old))
        route.update({
            "supply_port_grid": list(supply_port),
            "return_port_grid": list(return_port),
            "supply_port_mm": [coordinate * GRID_MM for coordinate in supply_port],
            "return_port_mm": [coordinate * GRID_MM for coordinate in return_port],
            "ordered_points_grid": [list(point) for point in points],
            "ordered_points_mm": [[coordinate * GRID_MM for coordinate in point] for point in points],
            "supply_transit_points_grid": [list(point) for point in supply],
            "return_transit_points_grid": [list(point) for point in returned],
            "supply_transit_length_mm": core.length_mm(supply),
            "return_transit_length_mm": core.length_mm(returned),
            "total_length_mm": core.length_mm(points),
            "route_validation": core.topology(points),
            "wall_penetration_gate_ids": [f"K1-WEST-{route_id}-S", f"K1-WEST-{route_id}-R"],
            "source_d018_route_digest": old["geometry_digest"],
        })
        route["geometry_digest"] = digest(route["ordered_points_mm"])
        routes.append(route)
    return routes


def east_routes(source: dict) -> list[dict]:
    routes = json.loads(json.dumps(source["routes"]))
    for route in routes:
        route["source_d017_route_digest"] = route["geometry_digest"]
        crossings: list[list[int]] = []
        for key in ("supply_transit_points_grid", "return_transit_points_grid"):
            points = route[key]
            for a, b in zip(points, points[1:]):
                if a[0] == b[0] and min(a[1], b[1]) <= 82 <= max(a[1], b[1]):
                    crossings.append([a[0], 82])
        route["wall_penetration_gates_grid"] = crossings
    return routes


def segment_hits_box(segment, box: tuple[int, int, int, int]) -> bool:
    a, b = segment
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
    draw.rectangle((0, 0, image.width, 118), fill="#071A21")
    draw.text((30, 15), "D019 · ЕДИНЫЙ K1 · 9 КОНТУРОВ ПЕРВОГО ЭТАЖА", font=font(27, True), fill="white")
    draw.text((30, 66), "18 уникальных соединений · контактов 0 · длины 40–80 м PASS · покрытие PARTIAL", font=font(17), fill="#A7EEE7")
    colours = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC", "#B24AA7", "#A26700", "#5E9400"]
    # One logical K1 station envelope, with a west wall face and south floor
    # face.  The envelope is equipment only; no shared line is pipe geometry.
    p0, p1 = to_px((129, 54)), to_px((140, 82))
    draw.rounded_rectangle((*p0, *p1), radius=8, fill="#D8F3EE80", outline="#00897B", width=4)
    draw.text((p0[0] + 8, p0[1] + 8), "K1", font=font(18, True), fill="#00695C")
    for route, colour in zip(routes, colours):
        points = [to_px(tuple(point)) for point in route["ordered_points_grid"]]
        draw.line(points, fill="white", width=9, joint="curve")
        draw.line(points, fill=colour, width=4, joint="curve")
        for label, key in (("S", "supply_port_grid"), ("R", "return_port_grid")):
            x, y = to_px(tuple(route[key]))
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=colour, outline="white", width=2)
            if pipes_only:
                draw.text((x + 6, y - 6), label, font=font(10, True), fill=colour, stroke_width=2, stroke_fill="white")
        body = route["heating_body_points_grid"]
        anchor = to_px(tuple(body[len(body) // 2]))
        draw.text((anchor[0] + 6, anchor[1] + 4), f"{route['route_id']} {route['total_length_mm']/1000:.1f}м", font=font(11, True), fill=colour, stroke_width=2, stroke_fill="white")
    image.save(target, quality=96)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("FLOOR1_UNIFIED_019 is append-only")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    east_source = json.loads(EAST_SOURCE.read_text(encoding="utf-8"))
    west_source = json.loads(WEST_SOURCE.read_text(encoding="utf-8"))
    routes = west_routes(west_source) + east_routes(east_source)
    contacts = core.inter_contacts(routes)
    ports = [tuple(route[key]) for route in routes for key in ("supply_port_grid", "return_port_grid")]
    tread_box = tuple(contract["vector_traced_geometry"]["floor_1_first_three_treads"]["conservative_blocked_box_grid"])
    tread_hits = sum(
        segment_hits_box(segment, tread_box)
        for route in routes
        for segment in zip(route["ordered_points_grid"], route["ordered_points_grid"][1:])
    )
    west_gates = [tuple(route[key]) for route in routes[:4] for key in ("supply_port_grid", "return_port_grid")]
    east_gates = sorted({tuple(point) for route in routes[4:] for point in route["wall_penetration_gates_grid"]})
    accepted = (
        len(routes) == 9
        and len(set(ports)) == 18
        and len(west_gates) == 8
        and len(east_gates) == 9
        and not contacts
        and not tread_hits
        and all(route["route_validation"]["result"] == "PASS" for route in routes)
        and all(40000 <= route["total_length_mm"] <= 80000 for route in routes)
    )
    if not accepted:
        raise RuntimeError("D019 global route acceptance failed")
    collector_contract = {
        "contract_id": "HA_TWO_FLOOR_K1_TWO_FACE_GATE_CONTRACT_019",
        "collector_id": "K1",
        "logical_assembly_count": 1,
        "station_envelope_bbox_grid": [129, 54, 140, 82],
        "wall_mounted_body_bbox_grid": [132, 56, 136, 82],
        "south_port_bank_bbox_grid": [130, 55, 140, 56],
        "west_wall_face_gate_bbox_grid": [129, 64, 129, 71],
        "circuit_count": 9,
        "physical_pipe_connection_count": 18,
        "all_ports_unique": True,
        "shared_pipe_trunk": False,
        "wall_crossing_allowed_by_owner": True,
        "west_wall_face_gates_grid": [list(point) for point in sorted(west_gates)],
        "south_wall_penetration_gates_grid": [list(point) for point in east_gates],
        "gate_to_port_mapping": [
            {"route_id": route["route_id"], "supply_port_id": route["supply_port_id"], "supply_point_grid": route["supply_port_grid"], "return_port_id": route["return_port_id"], "return_point_grid": route["return_port_grid"]}
            for route in routes
        ],
        "commercial_capacity": "NOT_EVALUATED",
        "hydraulics": "NOT_CALCULATED",
    }
    collector_contract["contract_digest"] = digest(collector_contract)
    body_length = sum(route["heating_body_length_mm"] for route in routes)
    model = {
        "schema": "homeaura-floor1-unified-route-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR1_UNIFIED_019",
        "status": "NINE_FLOOR1_FULL_ROUTES_ONE_K1_PASS_REWORK_REMAINING_FLOOR1_COVERAGE",
        "source_vector_contract_id": contract["contract_id"],
        "source_vector_contract_digest": contract["contract_digest"],
        "source_east_artifact_id": east_source["artifact_id"],
        "source_east_geometry_digest": east_source["geometry_digest"],
        "source_west_artifact_id": west_source["artifact_id"],
        "source_west_geometry_digest": west_source["geometry_digest"],
        "units": "mm",
        "grid_mm": GRID_MM,
        "collector_contract": collector_contract,
        "routes": routes,
        "coverage_diagnostic": {
            "method": "HEATING_BODY_LENGTH_TIMES_200MM_ESTIMATE_ONLY",
            "completed_named_territory_area_mm2": 106_600_000,
            "whole_floor_named_area_mm2": 154_600_000,
            "nominal_served_area_mm2": body_length * 200,
            "completed_territory_nominal_ratio": round(body_length * 200 / 106_600_000, 6),
            "whole_floor_nominal_ratio": round(body_length * 200 / 154_600_000, 6),
            "remaining_unrouted_named_area_mm2": 48_000_000,
            "unrouted_territories": ["STAIR_AND_HALL", "ENTRANCE", "SMALL_WC_SHOWER"],
            "full_coverage_claimed": False,
            "result": "REWORK_REMAINING_FLOOR1_TERRITORIES_AND_POLYGON_COVERAGE",
        },
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
        "collector_count": 1,
        "unique_port_count": len(set(ports)),
        "self_contact_count": sum(route["route_validation"]["self_contact_count"] for route in routes),
        "inter_route_contact_count": len(contacts),
        "inter_route_contacts": contacts,
        "first_three_tread_hit_count": tread_hits,
        "west_wall_face_gate_count": len(west_gates),
        "south_wall_penetration_gate_count": len(east_gates),
        "all_lengths_40_80m": True,
        "lengths_mm": {route["route_id"]: route["total_length_mm"] for route in routes},
        "source_body_digest_preservation": {
            route["route_id"]: route.get("source_d018_route_digest", route.get("source_d017_route_digest"))
            for route in routes
        },
        "coverage_result": model["coverage_diagnostic"]["result"],
        "whole_floor_completion": False,
    }
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "k1_two_face_gate_contract.json").write_text(json.dumps(collector_contract, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(routes, OUTPUT / "floor_1_unified_nine_routes_overlay.png", False)
    draw(routes, OUTPUT / "floor_1_unified_nine_routes_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# HA_TWO_FLOOR_FLOOR1_UNIFIED_019\n\n"
        "Девять непрерывных контуров первого этажа сведены к одной логической станции K1 с 18 уникальными "
        "соединениями и двумя группами выходов: западная стена и южная сторона котельной. Общая проверка всех "
        "отрезков даёт ноль пересечений, касаний и наложений. Длины: "
        + " / ".join(f"{route['total_length_mm']/1000:.1f}" for route in routes)
        + " м. Полигон первых трёх ступеней не затронут. Коммерческая вместимость коллектора и гидравлика не "
        "рассчитаны. Полное покрытие этажа не заявлено: ещё не проведены центральный холл/лестничная зона, входная "
        "зона и малый санузел; оценка покрытия остаётся только length×spacing, не polygon-union.\n",
        encoding="utf-8",
    )
    files = [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({"artifact_id": model["artifact_id"], "geometry_digest": model["geometry_digest"], "files": files}, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "route_count": len(routes), "lengths_mm": validation["lengths_mm"], "contacts": 0, "digest": model["geometry_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

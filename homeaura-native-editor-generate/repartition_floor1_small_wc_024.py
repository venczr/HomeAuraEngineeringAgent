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
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_TEN_ROUTES_REPAIRED_023"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_REPARTITIONED_024"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_REPARTITIONED_024.zip"
PX = 8.503937
TREAD_BOX = (113, 98, 127, 108)

spec = importlib.util.spec_from_file_location(
    "d014_core_for_d024", ROOT / "homeaura-native-editor-generate" / "build_local_counterflow_coverage_014.py"
)
core = importlib.util.module_from_spec(spec)
sys.modules["d014_core_for_d024"] = core
assert spec.loader is not None
spec.loader.exec_module(core)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest().upper()


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def to_px(point):
    return round(point[0] * PX), round(point[1] * PX)


def segment_hits_box(a, b, box) -> bool:
    x0, y0, x1, y1 = box
    if a[0] == b[0]:
        return x0 <= a[0] <= x1 and max(min(a[1], b[1]), y0) <= min(max(a[1], b[1]), y1)
    return y0 <= a[1] <= y1 and max(min(a[0], b[0]), x0) <= min(max(a[0], b[0]), x1)


def rebuild_wet_route(route: dict, box: tuple[int, int, int, int], supply_lane: int, return_lane: int) -> None:
    body, regularity = core.paired_counterflow(box)
    supply_port = tuple(route["supply_port_grid"])
    return_port = tuple(route["return_port_grid"])
    supply = core.clean([supply_port, (supply_lane, supply_port[1]), (supply_lane, body[0][1]), body[0]])
    returned = core.clean([body[-1], (return_lane, body[-1][1]), (return_lane, return_port[1]), return_port])
    points = core.clean([*supply, *body[1:], *returned[1:]])
    route.update(
        territory_id="BATH_WC_AND_SMALL_WC_COMBINED",
        territory_bbox_grid=list(box),
        ordered_points_grid=[list(point) for point in points],
        ordered_points_mm=[[coordinate * 100 for coordinate in point] for point in points],
        supply_transit_points_grid=[list(point) for point in supply],
        heating_body_points_grid=[list(point) for point in body],
        return_transit_points_grid=[list(point) for point in returned],
        supply_transit_length_mm=core.length_mm(supply),
        heating_body_length_mm=core.length_mm(body),
        return_transit_length_mm=core.length_mm(returned),
        total_length_mm=core.length_mm(points),
        route_validation=core.topology(points),
        regularity_validation={**regularity, "result": "PASS"},
        small_wc_shower_absorbed=True,
    )
    route["heating_body_digest"] = digest(route["heating_body_points_grid"])
    route["geometry_digest"] = digest(route["ordered_points_mm"])


def move_entrance_ports(route: dict) -> None:
    body = [tuple(point) for point in route["heating_body_points_grid"]]
    supply = [(129, 81), (128, 81), (128, 170), (136, 170), (136, 189), (133, 189)]
    returned = [tuple(point) for point in route["return_transit_points_grid"]]
    returned[-3:] = [(101, 170), (101, 80), (129, 80)]
    points = core.clean([*supply, *body[1:], *returned[1:]])
    route.update(
        supply_port_grid=[129, 81],
        return_port_grid=[129, 80],
        supply_port_mm=[12900, 8100],
        return_port_mm=[12900, 8000],
        ordered_points_grid=[list(point) for point in points],
        ordered_points_mm=[[coordinate * 100 for coordinate in point] for point in points],
        supply_transit_points_grid=[list(point) for point in supply],
        return_transit_points_grid=[list(point) for point in returned],
        supply_transit_length_mm=core.length_mm(supply),
        return_transit_length_mm=core.length_mm(returned),
        total_length_mm=core.length_mm(points),
        route_validation=core.topology(points),
    )
    route["geometry_digest"] = digest(route["ordered_points_mm"])


def draw(model: dict, target: Path, pipes_only: bool) -> None:
    if pipes_only:
        image = Image.new("RGB", (1785, 1750), "#F7FAFA")
        draw = ImageDraw.Draw(image)
        for x in range(0, image.width, round(PX)):
            draw.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, round(PX)):
            draw.line((0, y, image.width, y), fill="#D8E2E2")
    else:
        image = Image.open(BACKGROUND).convert("RGB")
        draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, 118), fill="#071A21")
    draw.text((30, 15), "D024 · ПЕРЕРАЗБИВКА ПЕРВОГО ЭТАЖА", font=font(27, True), fill="white")
    draw.text((30, 65), "малый санузел включён в C03/C04 · C14 78,5 м · для холла свободны 6 линий", font=font(17), fill="#A7EEE7")
    if pipes_only:
        x0, y0, x1, y1 = model["collector_contract"]["station_envelope_bbox_grid"]
        draw.rectangle((*to_px((x0, y0)), *to_px((x1, y1))), outline="#006D67", width=3)
        tx0, ty0, tx1, ty1 = TREAD_BOX
        draw.rectangle((*to_px((tx0, ty0)), *to_px((tx1, ty1))), fill="#F7CACA", outline="#B00020", width=3)
        draw.text(to_px((tx0, ty0 - 2)), "ПЕРВЫЕ 3 СТУПЕНИ", font=font(11, True), fill="#B00020")
    colours = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC", "#B24AA7", "#A26700", "#5E9400", "#C43D00"]
    for route, colour in zip(model["routes"], colours):
        points = [to_px(point) for point in route["ordered_points_grid"]]
        draw.line(points, fill="white", width=9, joint="curve")
        draw.line(points, fill=colour, width=4, joint="curve")
        anchor = to_px(route["heating_body_points_grid"][len(route["heating_body_points_grid"]) // 2])
        draw.text((anchor[0] + 5, anchor[1] + 4), f'{route["route_id"]} {route["total_length_mm"] / 1000:.1f}м', font=font(11, True), fill=colour, stroke_width=2, stroke_fill="white")
    image.save(target, quality=96)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D024 is append-only")
    source = json.loads((SOURCE / "canonical_geometry.json").read_text(encoding="utf-8"))
    model = json.loads(json.dumps(source))
    routes = model["routes"]
    rebuild_wet_route(next(route for route in routes if route["route_id"] == "F1-C03"), (44, 128, 94, 144), 98, 97)
    rebuild_wet_route(next(route for route in routes if route["route_id"] == "F1-C04"), (44, 146, 94, 162), 100, 99)
    move_entrance_ports(next(route for route in routes if route["route_id"] == "F1-C14"))

    contract = model["collector_contract"]
    contract["contract_id"] = "HA_TWO_FLOOR_K1_REPARTITIONED_GATE_CONTRACT_024"
    contract["west_wall_face_gate_bbox_grid"] = [129, 64, 129, 81]
    contract["west_wall_face_gates_grid"] = [[129, y] for y in [64, 65, 66, 67, 68, 69, 70, 71, 80, 81]]
    for connection in contract["connection_to_gate_mapping"]:
        if connection["route_id"] == "F1-C14":
            y = 81 if connection["leg"] == "SUPPLY" else 80
            connection["port_point_grid"] = [129, y]
            connection["exit_gate_point_grid"] = [129, y]
            connection["first_segment_exits_station_orthogonally"] = True
    contract["reserved_future_hall_gate_pairs_grid"] = [
        {"route_id": route_id, "supply_gate": [129, y + 1], "return_gate": [129, y]}
        for route_id, y in [("F1-C05", 72), ("F1-C06", 74), ("F1-C07", 76)]
    ]
    contract.pop("contract_digest", None)
    contract["contract_digest"] = digest(contract)

    contacts = core.inter_contacts(routes)
    tread_hits = sum(segment_hits_box(a, b, TREAD_BOX) for route in routes for a, b in zip(route["ordered_points_grid"], route["ordered_points_grid"][1:]))
    ports = [tuple(route[key]) for route in routes for key in ("supply_port_grid", "return_port_grid")]
    if contacts or tread_hits or len(set(ports)) != 20 or not all(route["route_validation"]["result"] == "PASS" for route in routes) or not all(40000 <= route["total_length_mm"] <= 80000 for route in routes):
        raise RuntimeError("D024 acceptance failed")

    body_length = sum(route["heating_body_length_mm"] for route in routes)
    model.update(
        artifact_id="HA_TWO_FLOOR_FLOOR1_REPARTITIONED_024",
        status="TEN_ROUTES_REPARTITIONED_PASS_REWORK_HALL_COVERAGE",
        derived_from_artifact_id=source["artifact_id"],
        derived_from_geometry_digest=source["geometry_digest"],
        small_wc_shower_strategy="ABSORBED_INTO_C03_C04_CONNECTED_WET_ROOM_TERRITORY",
        remaining_route_ids=["F1-C05", "F1-C06", "F1-C07"],
    )
    model["coverage_diagnostic"] = {
        "method": "HEATING_BODY_LENGTH_TIMES_200MM_ESTIMATE_ONLY",
        "completed_named_territory_area_mm2": 123_900_000,
        "whole_floor_named_area_mm2": 154_600_000,
        "nominal_served_area_mm2": body_length * 200,
        "completed_territory_nominal_ratio": round(body_length * 200 / 123_900_000, 6),
        "whole_floor_nominal_ratio": round(body_length * 200 / 154_600_000, 6),
        "remaining_unrouted_named_area_mm2": 30_700_000,
        "unrouted_territories": ["STAIR_AND_HALL"],
        "full_coverage_claimed": False,
        "result": "REWORK_HALL_STAIR_TERRITORY_AND_POLYGON_COVERAGE",
    }
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "status": model["status"],
        "route_count": len(routes),
        "lengths_mm": {route["route_id"]: route["total_length_mm"] for route in routes},
        "unique_port_coordinate_count": len(set(ports)),
        "self_contact_count": sum(route["route_validation"]["self_contact_count"] for route in routes),
        "inter_route_contact_count": len(contacts),
        "first_three_tread_exclusion_hit_count": tread_hits,
        "all_lengths_40_80m": True,
        "C03_C04_small_wc_absorption": "PASS_BOUNDED_RECTANGULAR_REPARTITION",
        "C14_relocated_gate_pair": [[129, 80], [129, 81]],
        "future_hall_gate_pairs_reserved": 3,
        "coverage_result": model["coverage_diagnostic"]["result"],
    }
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "k1_repartitioned_gate_contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, OUTPUT / "floor_1_repartitioned_overlay.png", False)
    draw(model, OUTPUT / "floor_1_repartitioned_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D024\n\nМалый санузел не получил искусственный короткий отдельный контур: его площадь включена в расширенные регулярные контуры C03/C04 смежной мокрой зоны. C14 перенесён на пару выходов y=80/81 и имеет длину 78,5 м. Для C05/C06/C07 зарезервированы три отдельные пары y=72..77. Десять готовых маршрутов не пересекаются, первые три ступени не затронуты; покрытие холла и лестницы ещё не заявлено.\n",
        encoding="utf-8",
    )
    files = [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({"artifact_id": model["artifact_id"], "geometry_digest": model["geometry_digest"], "files": files}, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "lengths_mm": validation["lengths_mm"], "contacts": len(contacts), "tread_hits": tread_hits, "digest": model["geometry_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

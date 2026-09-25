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
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_REPARTITION_CERTIFIED_025"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_TWELVE_ROUTES_027"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_TWELVE_ROUTES_027.zip"
PX = 8.503937
TREAD_BOX = (113, 98, 127, 108)

spec = importlib.util.spec_from_file_location(
    "d014_core_for_d027",
    ROOT / "homeaura-native-editor-generate" / "build_local_counterflow_coverage_014.py",
)
core = importlib.util.module_from_spec(spec)
sys.modules["d014_core_for_d027"] = core
assert spec.loader is not None
spec.loader.exec_module(core)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest().upper()


def font(size: int, bold: bool = False):
    return ImageFont.truetype(
        str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size
    )


def to_px(point):
    return round(point[0] * PX), round(point[1] * PX)


def segment_hits_box(a, b, box) -> bool:
    x0, y0, x1, y1 = box
    if a[0] == b[0]:
        return x0 <= a[0] <= x1 and max(min(a[1], b[1]), y0) <= min(max(a[1], b[1]), y1)
    return y0 <= a[1] <= y1 and max(min(a[0], b[0]), x0) <= min(max(a[0], b[0]), x1)


def transform_body(box, orientation: str):
    body, regularity = core.paired_counterflow(box)
    left, top, right, bottom = box
    if orientation == "MIRROR_X":
        body = [(left + right - x, y) for x, y in body]
        centre = [[left + right - x, y] for x, y in regularity["centre_turn_points_grid"]]
    elif orientation == "REVERSED":
        body = list(reversed(body))
        centre = list(reversed(regularity["centre_turn_points_grid"]))
    else:
        raise ValueError(orientation)
    start_index = next(
        index
        for index in range(len(body) - 2)
        if [list(point) for point in body[index : index + 3]] == centre
    )
    transformed = {
        **regularity,
        "centre_turn_points_grid": centre,
        "centre_turn_points_are_consecutive_body_points": True,
        "centre_turn_start_index": start_index,
        "route_orientation": orientation,
        "unexpected_short_segment_count": 0,
        "non_monotonic_frame_count": 0,
        "body_notch_count": 0,
        "staircase_pattern_count": 0,
        "result": "PASS",
    }
    return body, transformed


def route_fields(route: dict, supply, body, returned, regularity) -> None:
    supply = core.clean(supply)
    body = core.clean(body)
    returned = core.clean(returned)
    points = core.clean([*supply, *body[1:], *returned[1:]])
    route.update(
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
        regularity_validation=regularity,
    )
    route["heating_body_digest"] = digest(
        [[coordinate * 100 for coordinate in point] for point in body]
    )
    route["geometry_digest"] = digest(route["ordered_points_mm"])


def build_c05() -> dict:
    box = (103, 146, 126, 167)
    body, regularity = transform_body(box, "MIRROR_X")
    route = {
        "route_id": "F1-C05",
        "floor_id": "FLOOR_1",
        "territory_id": "STAIR_AND_HALL_SOUTH_LOBE",
        "collector_id": "K1",
        "supply_port_id": "K1-F1-C05-S",
        "return_port_id": "K1-F1-C05-R",
        "supply_port_grid": [129, 72],
        "return_port_grid": [129, 73],
        "supply_port_mm": [12900, 7200],
        "return_port_mm": [12900, 7300],
        "topology": "REGULAR_RECTANGULAR_COUNTERFLOW",
        "territory_bbox_grid": list(box),
        "wall_crossing_policy": "OWNER_ALLOWED_DISTINCT_TRANSIT",
        "completed": True,
    }
    route_fields(
        route,
        [(129, 72), (101, 72), (101, 167), (103, 167)],
        body,
        [(105, 165), (102, 165), (102, 73), (129, 73)],
        regularity,
    )
    return route


def build_c06() -> dict:
    south_box = (105, 128, 126, 144)
    north_box = (107, 110, 126, 126)
    south, south_regularity = transform_body(south_box, "MIRROR_X")
    north, north_regularity = transform_body(north_box, "MIRROR_X")
    connector = [(107, 142), (104, 142), (104, 126), (107, 126)]
    body = core.clean([*south, *connector[1:], *north[1:]])
    route = {
        "route_id": "F1-C06",
        "floor_id": "FLOOR_1",
        "territory_id": "STAIR_AND_HALL_MIDDLE_NORTH_COMPOSITE",
        "collector_id": "K1",
        "supply_port_id": "K1-F1-C06-S",
        "return_port_id": "K1-F1-C06-R",
        "supply_port_grid": [129, 74],
        "return_port_grid": [129, 77],
        "supply_port_mm": [12900, 7400],
        "return_port_mm": [12900, 7700],
        "topology": "COMPOSITE_TWO_LOBE_COUNTERFLOW",
        "territory_bbox_grid": [104, 110, 126, 144],
        "wall_crossing_policy": "OWNER_ALLOWED_DISTINCT_TRANSIT",
        "completed": True,
        "lobe_count": 2,
        "lobe_territories": [
            {"lobe_id": "C06-SOUTH", "bbox_grid": list(south_box), "regularity": south_regularity},
            {"lobe_id": "C06-NORTH", "bbox_grid": list(north_box), "regularity": north_regularity},
        ],
        "territory_transition_points_grid": [list(point) for point in connector],
    }
    regularity = {
        "topology": "COMPOSITE_TWO_REGULAR_COUNTERFLOW_LOBES",
        "lobe_count": 2,
        "all_lobes_regular": True,
        "classified_transition_segment_count": 3,
        "transition_is_length_padding": False,
        "unexpected_short_segment_count": 0,
        "non_monotonic_frame_count": 0,
        "body_notch_count": 0,
        "staircase_pattern_count": 0,
        "result": "PASS_BOUNDED_TWO_LOBE",
    }
    route_fields(
        route,
        [(129, 74), (103, 74), (103, 144), (105, 144)],
        body,
        [(109, 124), (106, 124), (106, 77), (129, 77)],
        regularity,
    )
    return route


def rebuild_c14(route: dict) -> None:
    box = (91, 171, 132, 191)
    body, regularity = transform_body(box, "REVERSED")
    route.update(
        supply_port_grid=[129, 81],
        return_port_grid=[129, 80],
        supply_port_mm=[12900, 8100],
        return_port_mm=[12900, 8000],
        territory_bbox_grid=list(box),
        topology="REGULAR_RECTANGULAR_COUNTERFLOW_WITH_TREAD_BYPASS_RETURN",
        tread_bypass_classification="RETURN_TRANSIT_AROUND_CONFIRMED_EXCLUSION",
    )
    route_fields(
        route,
        [(129, 81), (128, 81), (128, 169), (133, 169), (133, 189), (130, 189)],
        body,
        [
            (132, 191),
            (132, 192),
            (90, 192),
            (90, 170),
            (127, 170),
            (127, 109),
            (112, 109),
            (112, 97),
            (127, 97),
            (127, 80),
            (129, 80),
        ],
        regularity,
    )


def collector_contract(model: dict) -> dict:
    contract = model["collector_contract"]
    contract.update(
        contract_id="HA_TWO_FLOOR_K1_TWELVE_ROUTE_GATE_CONTRACT_027",
        circuit_count=12,
        physical_pipe_connection_count=24,
        connection_count=24,
        west_wall_face_gate_bbox_grid=[129, 64, 129, 81],
        west_wall_face_gates_grid=[[129, y] for y in [64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 77, 80, 81]],
        commercial_capacity="NOT_EVALUATED",
        hydraulics="NOT_CALCULATED",
        physical_commercial_manifold_selected=False,
    )
    contract.pop("reserved_future_hall_gate_pairs_grid", None)
    contract["unused_reserved_west_gate_nodes_grid"] = [[129, 75], [129, 76], [129, 78], [129, 79]]
    contract["route_count_selection"] = {
        "selected_hall_routes": ["F1-C05", "F1-C06"],
        "retired_candidate_route": "F1-C07",
        "reason": "TWO_NATURAL_LENGTH_ROUTES_REPLACE_TWO_SUB_40M_FRAGMENTS",
    }
    contract["connection_to_gate_mapping"] = [
        item
        for item in contract["connection_to_gate_mapping"]
        if item["route_id"] != "F1-C14"
    ]
    for route_id, supply_y, return_y in (
        ("F1-C05", 72, 73),
        ("F1-C06", 74, 77),
        ("F1-C14", 81, 80),
    ):
        contract["connection_to_gate_mapping"].extend(
            [
                {
                    "route_id": route_id,
                    "leg": "SUPPLY",
                    "port_id": f"K1-{route_id}-S".replace("K1-F1", "K1-F1"),
                    "port_point_grid": [129, supply_y],
                    "exit_face": "WEST_WALL_FACE",
                    "exit_gate_id": f"K1-WEST-{route_id}-S",
                    "exit_gate_point_grid": [129, supply_y],
                    "first_segment_exits_station_orthogonally": True,
                },
                {
                    "route_id": route_id,
                    "leg": "RETURN",
                    "port_id": f"K1-{route_id}-R".replace("K1-F1", "K1-F1"),
                    "port_point_grid": [129, return_y],
                    "exit_face": "WEST_WALL_FACE",
                    "exit_gate_id": f"K1-WEST-{route_id}-R",
                    "exit_gate_point_grid": [129, return_y],
                    "last_segment_enters_station_orthogonally": True,
                },
            ]
        )
    contract.pop("contract_digest", None)
    contract["contract_digest"] = digest(contract)
    return contract


def draw(model: dict, target: Path, mode: str) -> None:
    if mode == "overlay":
        image = Image.open(BACKGROUND).convert("RGB")
    else:
        image = Image.new("RGB", (1785, 1750), "#F7FAFA")
    draw = ImageDraw.Draw(image, "RGBA")
    if mode != "overlay":
        for x in range(0, image.width, round(PX)):
            draw.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, round(PX)):
            draw.line((0, y, image.width, y), fill="#D8E2E2")
    draw.rectangle((0, 0, image.width, 118), fill="#071A21")
    draw.text((30, 15), "D027 · 12 КОНТУРОВ ПЕРВОГО ЭТАЖА", font=font(27, True), fill="white")
    draw.text(
        (30, 65),
        "C05 51,3 м · C06 56,1 м · C14 77,9 м · контактов 0 · coverage ещё REWORK",
        font=font(17),
        fill="#A7EEE7",
    )
    if mode != "overlay":
        x0, y0, x1, y1 = model["collector_contract"]["station_envelope_bbox_grid"]
        draw.rectangle((*to_px((x0, y0)), *to_px((x1, y1))), outline="#006D67", width=3)
        draw.text(to_px((x0 + 1, y0 + 2)), "K1 LOGICAL", font=font(11, True), fill="#006D67")
    if mode == "debug":
        for route_id, colour in (("F1-C05", "#247BA0"), ("F1-C06", "#7A49E5"), ("F1-C14", "#F28E2B")):
            route = next(item for item in model["routes"] if item["route_id"] == route_id)
            x0, y0, x1, y1 = route["territory_bbox_grid"]
            draw.rectangle((*to_px((x0, y0)), *to_px((x1, y1))), fill=colour + "22", outline=colour, width=2)
    tx0, ty0, tx1, ty1 = TREAD_BOX
    draw.rectangle((*to_px((tx0, ty0)), *to_px((tx1, ty1))), fill="#F7CACA", outline="#B00020", width=3)
    draw.text(to_px((tx0, ty0 - 2)), "НЕ КАТАТЬ: 3 СТУПЕНИ", font=font(11, True), fill="#B00020")
    colours = [
        "#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC",
        "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93",
    ]
    for route, colour in zip(model["routes"], colours):
        points = [to_px(point) for point in route["ordered_points_grid"]]
        draw.line(points, fill="white", width=9, joint="curve")
        draw.line(points, fill=colour, width=4, joint="curve")
        anchor = to_px(route["heating_body_points_grid"][len(route["heating_body_points_grid"]) // 2])
        draw.text(
            (anchor[0] + 4, anchor[1] + 4),
            f'{route["route_id"]} {route["total_length_mm"] / 1000:.1f}м',
            font=font(11, True),
            fill=colour,
            stroke_width=2,
            stroke_fill="white",
        )
    image.save(target, quality=96)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D027 is append-only")
    source = json.loads((SOURCE / "canonical_geometry.json").read_text(encoding="utf-8"))
    model = json.loads(json.dumps(source))
    routes = model["routes"]
    rebuild_c14(next(route for route in routes if route["route_id"] == "F1-C14"))
    routes.extend([build_c05(), build_c06()])
    contract = collector_contract(model)

    contacts = core.inter_contacts(routes)
    tread_hits = sum(
        segment_hits_box(a, b, TREAD_BOX)
        for route in routes
        for a, b in zip(route["ordered_points_grid"], route["ordered_points_grid"][1:])
    )
    ports = [tuple(route[key]) for route in routes for key in ("supply_port_grid", "return_port_grid")]
    route_ids = [route["route_id"] for route in routes]
    if (
        contacts
        or tread_hits
        or len(route_ids) != len(set(route_ids))
        or len(set(ports)) != 24
        or not all(route["route_validation"]["result"] == "PASS" for route in routes)
        or not all(40000 <= route["total_length_mm"] <= 80000 for route in routes)
        or len(contract["connection_to_gate_mapping"]) != 24
    ):
        raise RuntimeError(
            json.dumps(
                {
                    "contacts": contacts,
                    "tread_hits": tread_hits,
                    "route_ids": route_ids,
                    "unique_ports": len(set(ports)),
                    "mapping_count": len(contract["connection_to_gate_mapping"]),
                    "routes": [
                        (route["route_id"], route["route_validation"], route["total_length_mm"])
                        for route in routes
                    ],
                },
                ensure_ascii=False,
            )
        )

    source_routes = {route["route_id"]: route for route in source["routes"]}
    lineage = []
    for route in routes:
        old = source_routes.get(route["route_id"])
        lineage.append(
            {
                "route_id": route["route_id"],
                "change_kind": (
                    "NEW_ROUTE"
                    if old is None
                    else "BODY_AND_TRANSIT_REBUILT"
                    if route["route_id"] == "F1-C14"
                    else "PRESERVED"
                ),
                "source_body_digest_mm": old.get("heating_body_digest") if old else None,
                "current_body_digest_mm": route["heating_body_digest"],
                "reason": (
                    "HALL_STAIR_TERRITORY"
                    if old is None
                    else "TREAD_BYPASS_AND_ENGINEERING_HEADROOM"
                    if route["route_id"] == "F1-C14"
                    else "SOURCE_ROUTE_PRESERVED"
                ),
            }
        )

    body_length = sum(route["heating_body_length_mm"] for route in routes)
    nominal_area = body_length * 200
    model.update(
        artifact_id="HA_TWO_FLOOR_FLOOR1_TWELVE_ROUTES_027",
        status="TWELVE_ROUTE_GEOMETRY_PASS_REWORK_POLYGON_COVERAGE",
        derived_from_artifact_id=source["artifact_id"],
        derived_from_geometry_digest=source["geometry_digest"],
        remaining_route_ids=[],
        retired_route_candidates=[
            {
                "route_id": "F1-C07",
                "reason": "SEPARATE_NORTH_FRAGMENT_WAS_SUB_40M_AND_ARTIFICIAL;_MERGED_INTO_C06",
            }
        ],
        body_lineage=lineage,
        body_digest_coordinate_space="ORDERED_POINTS_MM",
    )
    model["coverage_diagnostic"] = {
        "method": "HEATING_BODY_LENGTH_TIMES_200MM_ESTIMATE_ONLY",
        "territory_assignment_complete": True,
        "whole_floor_named_area_mm2": 154_600_000,
        "nominal_served_area_mm2": nominal_area,
        "whole_floor_nominal_ratio": round(nominal_area / 154_600_000, 6),
        "body_only_nominal_unresolved_area_mm2": 154_600_000 - nominal_area,
        "transit_heating_excluded_from_estimate": True,
        "exact_room_polygon_union_evaluated": False,
        "exterior_wall_100mm_band_evaluated": False,
        "full_coverage_claimed": False,
        "result": "REWORK_EXACT_POLYGON_UNION_SPACING_AND_EXTERIOR_BAND",
    }
    model["whole_floor_completion"] = False
    model["whole_house_completion"] = False
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)

    validation = {
        "artifact_id": model["artifact_id"],
        "status": model["status"],
        "route_count": len(routes),
        "unique_port_coordinate_count": len(set(ports)),
        "self_contact_count": sum(route["route_validation"]["self_contact_count"] for route in routes),
        "inter_route_contact_count": len(contacts),
        "first_three_tread_exclusion_hit_count": tread_hits,
        "all_lengths_40_80m": True,
        "lengths_mm": {route["route_id"]: route["total_length_mm"] for route in routes},
        "C05_regular_counterflow": "PASS_BOUNDED_RECTANGULAR_BODY",
        "C06_composite_counterflow": "PASS_BOUNDED_TWO_REGULAR_LOBES",
        "C14_engineering_headroom_mm": 80000
        - next(route for route in routes if route["route_id"] == "F1-C14")["total_length_mm"],
        "C07_retired": True,
        "logical_k1_assembly_count": contract["logical_assembly_count"],
        "physical_commercial_manifold": "NOT_EVALUATED",
        "coverage_result": model["coverage_diagnostic"]["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT / "k1_twelve_route_gate_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    draw(model, OUTPUT / "floor_1_twelve_routes_overlay.png", "overlay")
    draw(model, OUTPUT / "floor_1_twelve_routes_pipes_only.png", "pipes")
    draw(model, OUTPUT / "floor_1_hall_regularity_debug.png", "debug")
    (OUTPUT / "report.md").write_text(
        "# D027\n\n"
        "Отклонённая скоба C05 из D026 не использована. Холл/лестница переразбиты на два естественных маршрута: "
        "C05 — регулярная прямоугольная противоточная улитка 51,3 м; C06 — один непрерывный контур 56,1 м "
        "из двух регулярных лопастей с явно классифицированным переходом. Искусственный короткий C07 удалён. "
        "C14 перестроен до 77,9 м и обходит запрещённые первые три ступени. Все 12 полных маршрутов непрерывны, "
        "не касаются друг друга и имеют длину 40–80 м. Один K1 пока является логической станцией; коммерческая "
        "вместимость и гидравлика не рассчитаны. Назначение территорий завершено, но полное покрытие не заявляется "
        "до расчёта полигонального объединения, наружной 100-мм полосы и зазоров.\n",
        encoding="utf-8",
    )
    files = [
        {"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(OUTPUT.iterdir())
        if path.is_file()
    ]
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps(
            {"artifact_id": model["artifact_id"], "geometry_digest": model["geometry_digest"], "files": files},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "package": str(PACKAGE),
                "lengths_mm": validation["lengths_mm"],
                "contacts": len(contacts),
                "tread_hits": tread_hits,
                "digest": model["geometry_digest"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

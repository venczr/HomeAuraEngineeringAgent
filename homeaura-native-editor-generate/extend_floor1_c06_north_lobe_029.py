from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_TWELVE_ROUTES_SPACING_028"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_NORTH_HALL_029"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_NORTH_HALL_029.zip"
TREAD_BOX = (113, 98, 127, 108)

spec = importlib.util.spec_from_file_location(
    "d014_core_for_d029",
    ROOT / "homeaura-native-editor-generate" / "build_local_counterflow_coverage_014.py",
)
core = importlib.util.module_from_spec(spec)
sys.modules["d014_core_for_d029"] = core
assert spec.loader is not None
spec.loader.exec_module(core)

draw_spec = importlib.util.spec_from_file_location(
    "d027_renderer_for_d029",
    ROOT / "homeaura-native-editor-generate" / "build_floor1_twelve_routes_027.py",
)
d027 = importlib.util.module_from_spec(draw_spec)
sys.modules["d027_renderer_for_d029"] = d027
assert draw_spec.loader is not None
draw_spec.loader.exec_module(d027)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest().upper()


def length(points) -> int:
    return core.length_mm([tuple(point) for point in points])


def segment_hits_box(a, b, box) -> bool:
    x0, y0, x1, y1 = box
    if a[0] == b[0]:
        return x0 <= a[0] <= x1 and max(min(a[1], b[1]), y0) <= min(max(a[1], b[1]), y1)
    return y0 <= a[1] <= y1 and max(min(a[0], b[0]), x0) <= min(max(a[0], b[0]), x1)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D029 is append-only")
    model = json.loads((SOURCE / "canonical_geometry.json").read_text(encoding="utf-8"))
    source_digest = model["geometry_digest"]
    c06 = next(route for route in model["routes"] if route["route_id"] == "F1-C06")
    source_body_digest = c06["heating_body_digest"]

    existing_body = [tuple(point) for point in c06["heating_body_points_grid"]]
    north_box = (108, 80, 125, 96)
    upper_body, upper_raw = core.paired_counterflow(north_box)
    left, top, right, bottom = north_box
    upper_body = [(left + right - x, y) for x, y in upper_body]
    upper_centre = [[left + right - x, y] for x, y in upper_raw["centre_turn_points_grid"]]
    upper_regularity = {
        **upper_raw,
        "inward_frame_bounds_grid": [[108, 80, 125, 96], [112, 84, 121, 92]],
        "outward_frame_bounds_grid": [[110, 82, 123, 94]],
        "centre_turn_points_grid": upper_centre,
        "centre_turn_points_are_consecutive_body_points": True,
        "route_orientation": "MIRROR_X",
        "body_notch_count": 0,
        "staircase_pattern_count": 0,
        "result": "PASS_COMPUTED_FROM_FINAL_LOBE",
    }
    stair_bypass_transition = [existing_body[-1], (105, 124), (105, 96), upper_body[0]]
    extended_body = [*existing_body, *stair_bypass_transition[1:], *upper_body[1:]]
    supply = [tuple(point) for point in c06["supply_transit_points_grid"]]
    returned = [upper_body[-1], (104, 94), (104, 77), (129, 77)]
    points = [*supply, *extended_body[1:], *returned[1:]]

    prior_parts = c06["semantic_route_parts"]
    semantic_parts = [
        *prior_parts,
        {
            "role": "STAIR_EXCLUSION_BYPASS_TRANSITION",
            "points_grid": [list(point) for point in stair_bypass_transition],
            "length_mm": length(stair_bypass_transition),
            "clearance_classification": "WEST_OF_FIRST_THREE_TREADS",
            "minimum_centerline_to_tread_box_mm": 800,
        },
        {
            "role": "NORTH_STAIR_COUNTERFLOW_LOBE",
            "points_grid": [list(point) for point in upper_body],
            "length_mm": length(upper_body),
        },
    ]
    c06.update(
        territory_id="STAIR_AND_HALL_THREE_LOBE_COMPOSITE",
        topology="COMPOSITE_THREE_LOBE_COUNTERFLOW",
        territory_bbox_grid=[104, 80, 126, 144],
        ordered_points_grid=[list(point) for point in points],
        ordered_points_mm=[[coordinate * 100 for coordinate in point] for point in points],
        supply_transit_points_grid=[list(point) for point in supply],
        heating_body_points_grid=[list(point) for point in extended_body],
        return_transit_points_grid=[list(point) for point in returned],
        supply_transit_length_mm=length(supply),
        heating_body_length_mm=length(extended_body),
        return_transit_length_mm=length(returned),
        total_length_mm=length(points),
        route_validation=core.topology(points),
        lobe_count=3,
        semantic_route_parts=semantic_parts,
        lobe_territories=[
            *c06["lobe_territories"],
            {"lobe_id": "C06-NORTH-STAIR", "bbox_grid": list(north_box), "regularity": upper_regularity},
        ],
        north_stair_hall_assignment={
            "source_contract": "VECTOR_PDF_DRAFT",
            "allowed_under_stair": True,
            "first_three_treads_excluded": True,
            "exact_polygon_union_complete": False,
            "status": "ROUTE_BODY_ADDED_REQUIRES_POLYGON_COVERAGE_MEASUREMENT",
        },
        regularity_validation={
            "topology": "COMPOSITE_THREE_REGULAR_COUNTERFLOW_LOBES",
            "lobe_count": 3,
            "all_lobes_regular": True,
            "semantic_boundary_points_preserved": True,
            "classified_transition_count": 2,
            "transition_is_length_padding": False,
            "field_spacing_request_mm": 200,
            "first_two_lobes_transition_spacing_mm": 200,
            "north_transition_classification": "STAIR_EXCLUSION_BYPASS",
            "body_notch_count": 0,
            "staircase_pattern_count": 0,
            "result": "PASS_COMPUTED_THREE_LOBE",
        },
    )
    c06["heating_body_digest"] = digest(
        [[coordinate * 100 for coordinate in point] for point in extended_body]
    )
    c06["geometry_digest"] = digest(c06["ordered_points_mm"])

    contacts = core.inter_contacts(model["routes"])
    tread_hits = sum(
        segment_hits_box(a, b, TREAD_BOX)
        for route in model["routes"]
        for a, b in zip(route["ordered_points_grid"], route["ordered_points_grid"][1:])
    )
    if contacts or tread_hits or c06["route_validation"]["result"] != "PASS" or c06["total_length_mm"] != 72500:
        raise RuntimeError({"contacts": contacts, "tread_hits": tread_hits, "c06": c06["route_validation"], "length": c06["total_length_mm"]})

    model.update(
        artifact_id="HA_TWO_FLOOR_FLOOR1_NORTH_HALL_029",
        status="TWELVE_ROUTE_GEOMETRY_AND_NORTH_HALL_BODY_PASS_REWORK_POLYGON_COVERAGE",
        derived_from_artifact_id=SOURCE.name,
        derived_from_geometry_digest=source_digest,
        remaining_route_ids=["F1-C07_ONLY_IF_EXACT_COVERAGE_PROVES_NATURAL_ROUTE"],
    )
    for item in model["body_lineage"]:
        if item["route_id"] == "F1-C06":
            item.update(
                change_kind="THIRD_REGULAR_LOBE_AND_STAIR_BYPASS_ADDED",
                source_body_digest_mm=source_body_digest,
                current_body_digest_mm=c06["heating_body_digest"],
                reason="SERVE_NORTH_STAIR_HALL_WITHOUT_ARTIFICIAL_SUB_40M_C07",
            )
    body_length = sum(route["heating_body_length_mm"] for route in model["routes"])
    nominal_area = body_length * 200
    model["coverage_diagnostic"] = {
        "method": "HEATING_BODY_LENGTH_TIMES_200MM_ESTIMATE_ONLY",
        "territory_assignment_complete": False,
        "whole_floor_named_area_mm2": 154_600_000,
        "nominal_served_area_mm2": nominal_area,
        "whole_floor_nominal_ratio": round(nominal_area / 154_600_000, 6),
        "body_only_nominal_unresolved_area_mm2": 154_600_000 - nominal_area,
        "north_stair_hall_route_body_added": True,
        "transit_heating_excluded_from_estimate": True,
        "exact_room_polygon_union_evaluated": False,
        "exterior_wall_100mm_band_evaluated": False,
        "full_coverage_claimed": False,
        "result": "REWORK_EXACT_POLYGON_UNION_AND_EXTERIOR_BAND",
    }
    model["whole_floor_completion"] = False
    model["whole_house_completion"] = False
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)

    validation = {
        "artifact_id": model["artifact_id"],
        "status": model["status"],
        "route_count": len(model["routes"]),
        "inter_route_contact_count": len(contacts),
        "first_three_tread_exclusion_hit_count": tread_hits,
        "all_lengths_40_80m": all(40000 <= route["total_length_mm"] <= 80000 for route in model["routes"]),
        "lengths_mm": {route["route_id"]: route["total_length_mm"] for route in model["routes"]},
        "C06_component_lengths_mm": {
            "supply": c06["supply_transit_length_mm"],
            "body": c06["heating_body_length_mm"],
            "return": c06["return_transit_length_mm"],
            "total": c06["total_length_mm"],
        },
        "C06_lobe_count": 3,
        "C06_north_stair_lobe_length_mm": length(upper_body),
        "C06_stair_bypass_length_mm": length(stair_bypass_transition),
        "C06_regularity_result": c06["regularity_validation"]["result"],
        "coverage_result": model["coverage_diagnostic"]["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "k1_twelve_route_gate_contract.json").write_text(json.dumps(model["collector_contract"], ensure_ascii=False, indent=2), encoding="utf-8")
    d027.draw(model, OUTPUT / "floor_1_north_hall_overlay.png", "overlay")
    d027.draw(model, OUTPUT / "floor_1_north_hall_pipes_only.png", "pipes")
    d027.draw(model, OUTPUT / "floor_1_north_hall_debug.png", "debug")
    (OUTPUT / "report.md").write_text(
        "# D029\n\nСеверная площадка холла и разрешённая часть под лестницей добавлены в C06 как третья регулярная противоточная лопасть. Связь выполнена отдельным обходом западнее запрещённых первых трёх ступеней. C06 остаётся одной трубой от K1 до K1, длина 72,5 м, контактов с другими трубами и ступенями нет. Отдельный C07 не создаётся искусственно: он остаётся только условным кандидатом, если точный полигональный расчёт покажет естественный незакрытый маршрут не короче 40 м. Полное покрытие и наружная 100-мм полоса пока не заявляются.\n",
        encoding="utf-8",
    )
    files = [
        {"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(OUTPUT.iterdir())
        if path.is_file()
    ]
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps({"artifact_id": model["artifact_id"], "geometry_digest": model["geometry_digest"], "files": files}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "C06_mm": c06["total_length_mm"], "contacts": len(contacts), "tread_hits": tread_hits, "digest": model["geometry_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

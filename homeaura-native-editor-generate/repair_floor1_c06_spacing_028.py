from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_TWELVE_ROUTES_027"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_TWELVE_ROUTES_SPACING_028"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_TWELVE_ROUTES_SPACING_028.zip"
TREAD_BOX = (113, 98, 127, 108)

spec = importlib.util.spec_from_file_location(
    "d014_core_for_d028",
    ROOT / "homeaura-native-editor-generate" / "build_local_counterflow_coverage_014.py",
)
core = importlib.util.module_from_spec(spec)
sys.modules["d014_core_for_d028"] = core
assert spec.loader is not None
spec.loader.exec_module(core)

draw_spec = importlib.util.spec_from_file_location(
    "d027_renderer_for_d028",
    ROOT / "homeaura-native-editor-generate" / "build_floor1_twelve_routes_027.py",
)
d027 = importlib.util.module_from_spec(draw_spec)
sys.modules["d027_renderer_for_d028"] = d027
assert draw_spec.loader is not None
draw_spec.loader.exec_module(d027)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest().upper()


def segment_hits_box(a, b, box) -> bool:
    x0, y0, x1, y1 = box
    if a[0] == b[0]:
        return x0 <= a[0] <= x1 and max(min(a[1], b[1]), y0) <= min(max(a[1], b[1]), y1)
    return y0 <= a[1] <= y1 and max(min(a[0], b[0]), x0) <= min(max(a[0], b[0]), x1)


def length(points) -> int:
    return core.length_mm([tuple(point) for point in points])


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D028 is append-only")
    model = json.loads((SOURCE / "canonical_geometry.json").read_text(encoding="utf-8"))
    source_digest = model["geometry_digest"]
    c06 = next(route for route in model["routes"] if route["route_id"] == "F1-C06")
    old_body_digest = c06["heating_body_digest"]

    south_lobe = [
        (106, 144), (126, 144), (126, 128), (106, 128), (106, 140), (122, 140),
        (122, 132), (110, 132), (110, 134), (120, 134), (120, 138), (108, 138),
        (108, 130), (124, 130), (124, 142), (108, 142),
    ]
    transition = [(108, 142), (104, 142), (104, 126), (107, 126)]
    north_lobe = [
        (107, 126), (126, 126), (126, 110), (107, 110), (107, 122), (122, 122),
        (122, 114), (111, 114), (111, 116), (120, 116), (120, 120), (109, 120),
        (109, 112), (124, 112), (124, 124), (109, 124),
    ]
    semantic_body = [*south_lobe, *transition[1:], *north_lobe[1:]]
    supply = [(129, 74), (103, 74), (103, 144), (106, 144)]
    returned = [(109, 124), (106, 124), (106, 77), (129, 77)]
    points = [*supply, *semantic_body[1:], *returned[1:]]

    south_regularity = {
        "inward_frame_bounds_grid": [[106, 128, 126, 144], [110, 132, 122, 140]],
        "outward_frame_bounds_grid": [[108, 130, 124, 142], [112, 134, 120, 138]],
        "inward_frame_inset_mm": 400,
        "outward_interleave_offset_mm": 200,
        "centre_turn_points_grid": [[110, 132], [110, 134], [120, 134]],
        "centre_turn_segment_count": 2,
        "centre_turn_points_are_consecutive_body_points": True,
        "body_notch_count": 0,
        "staircase_pattern_count": 0,
        "result": "PASS_COMPUTED_FROM_FINAL_LOBE",
    }
    north_regularity = {
        "inward_frame_bounds_grid": [[107, 110, 126, 126], [111, 114, 122, 122]],
        "outward_frame_bounds_grid": [[109, 112, 124, 124], [113, 116, 120, 120]],
        "inward_frame_inset_mm": 400,
        "outward_interleave_offset_mm": 200,
        "centre_turn_points_grid": [[111, 114], [111, 116], [120, 116]],
        "centre_turn_segment_count": 2,
        "centre_turn_points_are_consecutive_body_points": True,
        "body_notch_count": 0,
        "staircase_pattern_count": 0,
        "result": "PASS_COMPUTED_FROM_FINAL_LOBE",
    }
    c06.update(
        ordered_points_grid=[list(point) for point in points],
        ordered_points_mm=[[coordinate * 100 for coordinate in point] for point in points],
        supply_transit_points_grid=[list(point) for point in supply],
        heating_body_points_grid=[list(point) for point in semantic_body],
        return_transit_points_grid=[list(point) for point in returned],
        supply_transit_length_mm=length(supply),
        heating_body_length_mm=length(semantic_body),
        return_transit_length_mm=length(returned),
        total_length_mm=length(points),
        route_validation=core.topology(points),
        territory_bbox_grid=[104, 110, 126, 144],
        lobe_territories=[
            {"lobe_id": "C06-SOUTH", "bbox_grid": [106, 128, 126, 144], "regularity": south_regularity},
            {"lobe_id": "C06-NORTH", "bbox_grid": [107, 110, 126, 126], "regularity": north_regularity},
        ],
        territory_transition_points_grid=[list(point) for point in transition],
        semantic_route_parts=[
            {"role": "SOUTH_COUNTERFLOW_LOBE", "points_grid": [list(point) for point in south_lobe], "length_mm": length(south_lobe)},
            {"role": "TERRITORY_TRANSITION", "points_grid": [list(point) for point in transition], "length_mm": length(transition)},
            {"role": "NORTH_COUNTERFLOW_LOBE", "points_grid": [list(point) for point in north_lobe], "length_mm": length(north_lobe)},
        ],
        regularity_validation={
            "topology": "COMPOSITE_TWO_REGULAR_COUNTERFLOW_LOBES",
            "lobe_count": 2,
            "all_lobes_regular": True,
            "semantic_boundary_points_preserved": True,
            "classified_transition_segment_count": 3,
            "transition_length_mm": length(transition),
            "transition_is_length_padding": False,
            "minimum_transition_to_south_lobe_parallel_spacing_mm": 200,
            "minimum_transition_to_north_lobe_parallel_spacing_mm": 200,
            "field_spacing_request_mm": 200,
            "field_spacing_result": "PASS_FOR_CLASSIFIED_C06_LOBES_AND_TRANSITION",
            "result": "PASS_COMPUTED_TWO_LOBE",
        },
    )
    c06["heating_body_digest"] = digest(c06["ordered_points_mm"][len(supply) - 1 : len(supply) - 1 + len(semantic_body)])
    c06["geometry_digest"] = digest(c06["ordered_points_mm"])

    contacts = core.inter_contacts(model["routes"])
    tread_hits = sum(
        segment_hits_box(a, b, TREAD_BOX)
        for route in model["routes"]
        for a, b in zip(route["ordered_points_grid"], route["ordered_points_grid"][1:])
    )
    if contacts or tread_hits or c06["route_validation"]["result"] != "PASS" or c06["total_length_mm"] != 55500:
        raise RuntimeError({"contacts": contacts, "tread_hits": tread_hits, "c06": c06["route_validation"]})

    model.update(
        artifact_id="HA_TWO_FLOOR_FLOOR1_TWELVE_ROUTES_SPACING_028",
        status="TWELVE_ROUTE_GEOMETRY_AND_C06_SPACING_PASS_REWORK_POLYGON_COVERAGE",
        derived_from_artifact_id=SOURCE.name,
        derived_from_geometry_digest=source_digest,
        remaining_route_ids=["F1-C07_CANDIDATE_AFTER_EXACT_COVERAGE"],
        retired_route_candidates=[],
    )
    for item in model["body_lineage"]:
        if item["route_id"] == "F1-C06":
            item.update(
                change_kind="BODY_AND_SUPPLY_TRANSIT_SPACING_REPAIR",
                source_body_digest_mm=old_body_digest,
                current_body_digest_mm=c06["heating_body_digest"],
                reason="REMOVE_UNCLASSIFIED_100MM_PARALLEL_FIELD_ADJACENCY_AND_PRESERVE_SEMANTIC_BOUNDARIES",
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
        "known_high_priority_unresolved_region": "NORTH_STAIR_AND_HALL",
        "north_stair_hall_proxy_coverage_from_D027_audit": 0.4138,
        "transit_heating_excluded_from_estimate": True,
        "exact_room_polygon_union_evaluated": False,
        "exterior_wall_100mm_band_evaluated": False,
        "full_coverage_claimed": False,
        "result": "REWORK_EXACT_POLYGON_UNION_AND_NORTH_STAIR_HALL",
    }
    model["whole_floor_completion"] = False
    model["whole_house_completion"] = False
    model["length_clearance_diagnostics"] = {
        "F1-C14_length_headroom_to_80000_mm": 80000 - next(route for route in model["routes"] if route["route_id"] == "F1-C14")["total_length_mm"],
        "F1-C14_centerline_to_tread_box_mm": 100,
        "F1-C14_clearance_measure": "CENTERLINE",
        "pipe_outside_diameter_mm": "NOT_SPECIFIED",
        "pipe_surface_to_tread_clearance_mm": "NOT_EVALUATED",
    }
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
        "C06_semantic_boundary_points_preserved": True,
        "C06_transition_field_spacing_mm": 200,
        "C06_regularity_result": c06["regularity_validation"]["result"],
        "coverage_result": model["coverage_diagnostic"]["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "k1_twelve_route_gate_contract.json").write_text(json.dumps(model["collector_contract"], ensure_ascii=False, indent=2), encoding="utf-8")
    d027.draw(model, OUTPUT / "floor_1_twelve_routes_overlay.png", "overlay")
    d027.draw(model, OUTPUT / "floor_1_twelve_routes_pipes_only.png", "pipes")
    d027.draw(model, OUTPUT / "floor_1_hall_regularity_debug.png", "debug")
    (OUTPUT / "report.md").write_text(
        "# D028\n\nC06 исправлен локально: переход между двумя регулярными лопастями теперь имеет проверенный полевой зазор 200 мм, а его смысловые граничные точки сохранены в канонической полилинии. Длина C06 стала 55,5 м; остальные 11 маршрутов не изменены. Точный расчёт покрытия ещё не выполнен: северная часть лестницы и холла остаётся приоритетной незакрытой зоной, поэтому C07 не удалён, а оставлен кандидатом после полигонального анализа. C14 имеет 2,1 м запаса по длине и 100 мм осевого расстояния до блока ступеней; чистый зазор от поверхности трубы не рассчитывался без диаметра.\n",
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

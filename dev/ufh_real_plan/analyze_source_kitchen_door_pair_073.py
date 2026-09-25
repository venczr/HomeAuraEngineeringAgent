#!/usr/bin/env python3
"""Reproduce the bounded run073 kitchen door-pair geometry audit.

The tested leads are sharp candidates. A contact at the lead's own BODY
terminal is required and is reported separately from intersections with every
non-adjacent BODY segment.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.ufh_bend_geometry import build_rounded_centerline


DOORS_PATH = ROOT / "projects/Test_01/exports/ufh_generator_package/16_DOOR_OPENINGS_FROM_PDF.json"
ROUTES_PATH = ROOT / "projects/Test_01/exports/ufh_generator_package/22_KITCHEN_PROJECT_OPENING_ROUTES.json"
OUTPUT_PATH = HERE / "source_kitchen_door_pair_073_20260925.json"
BEND_RADIUS_MM = 80.0
Point2 = tuple[float, float]


def _as_points(points: Iterable[Iterable[float]]) -> list[Point2]:
    return [(float(point[0]), float(point[1])) for point in points]


def lead(term: Point2, open_y: float) -> list[Point2]:
    """Return the original run073 orthogonal sharp lead candidate."""
    return [term, (term[0], float(open_y)), (12612.0, float(open_y))]


def lead_len(points: list[Point2]) -> float:
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))


def _body_segments(body_points: list[Point2]) -> list[LineString]:
    return [LineString([a, b]) for a, b in zip(body_points, body_points[1:])]


def _is_only_terminal_contact(geometry: Any, terminal: Point2, tolerance_mm: float = 1e-7) -> bool:
    return geometry.geom_type == "Point" and geometry.distance(Point(terminal)) <= tolerance_mm


def _opening_crossing(lead_points: list[Point2], opening_mm: list[list[float]]) -> dict[str, Any]:
    """Check the first room-boundary contact, not later travel along the gap line."""
    crossing = lead_points[1]
    opening_line = LineString(_as_points(opening_mm))
    crossing_point = Point(crossing)
    return {
        "source_boundary_crossing_mm": [crossing[0], crossing[1]],
        "crossing_inside_opening": bool(opening_line.covers(crossing_point)),
        "crossing_to_opening_distance_mm": round(crossing_point.distance(opening_line), 3),
    }


def analyze_lead(
    lead_points: list[Point2],
    body_points: list[Point2],
    *,
    terminal_at_start: bool,
    opening_mm: list[list[float]],
) -> dict[str, Any]:
    """Measure terminal contact, forbidden BODY contact, clearance and R80."""
    lead_line = LineString(lead_points)
    body_line = LineString(body_points)
    segments = _body_segments(body_points)
    terminal_segment_index = 0 if terminal_at_start else len(segments) - 1
    terminal_segment = segments[terminal_segment_index]
    non_adjacent_body = unary_union(
        [segment for index, segment in enumerate(segments) if index != terminal_segment_index]
    )

    adjacent_intersection = lead_line.intersection(terminal_segment)
    non_adjacent_intersection = lead_line.intersection(non_adjacent_body)
    terminal = lead_points[0]
    terminal_contact_only = _is_only_terminal_contact(adjacent_intersection, terminal)
    forbidden_adjacent_contact = not adjacent_intersection.is_empty and not terminal_contact_only
    forbidden_body_intersection = bool(
        forbidden_adjacent_contact or not non_adjacent_intersection.is_empty
    )

    rounded = build_rounded_centerline(lead_points, bend_radius_mm=BEND_RADIUS_MM)
    return {
        "sharp_length_mm": round(lead_line.length, 3),
        "terminal_contact": bool(body_line.covers(Point(terminal))),
        "terminal_contact_only_on_adjacent_body_segment": terminal_contact_only,
        "full_body_intersection_wkt": lead_line.intersection(body_line).wkt,
        "forbidden_non_adjacent_body_intersection": forbidden_body_intersection,
        "forbidden_non_adjacent_intersection_wkt": non_adjacent_intersection.wkt,
        "forbidden_overlap_length_mm": round(non_adjacent_intersection.length, 3),
        "minimum_non_adjacent_body_clearance_mm": round(lead_line.distance(non_adjacent_body), 3),
        "r80_materializable_in_isolation": rounded.valid,
        "r80_diagnostics": list(rounded.diagnostics),
        **_opening_crossing(lead_points, opening_mm),
    }


def build_report() -> dict[str, Any]:
    doors = json.loads(DOORS_PATH.read_text(encoding="utf-8"))
    routes = json.loads(ROUTES_PATH.read_text(encoding="utf-8"))

    source_openings: dict[str, dict[str, Any]] = {}
    for opening in doors["openings"]:
        if "KITCHEN-CORRIDOR" not in opening["opening_id"]:
            continue
        source_openings[opening["opening_id"]] = {
            "opening_mm": opening["opening_mm"],
            "width_mm": opening["width_mm"],
            "vector_evidence": opening["vector_evidence"],
            "passage_status": opening["passage_status"],
            "geometry_status": opening["geometry_status"],
            "transit_preview_allowed": opening["transit_preview_allowed"],
            "manifold_connected": opening["manifold_connected"],
            "construction_passage_authorized": False,
        }

    spiral = next(item for item in routes["spirals"] if "zone-3-2" in item["circuit_id"])
    body_points = _as_points(spiral["ordered_rounded_centerline_mm"])
    supply_terminal, return_terminal = body_points[0], body_points[-1]
    openings_by_role = {
        "supply": source_openings["FLOOR_1_PLAN-KITCHEN-CORRIDOR-UPPER"],
        "return": source_openings["FLOOR_1_PLAN-KITCHEN-CORRIDOR-LOWER"],
    }
    supply_open_y = float(openings_by_role["supply"]["opening_mm"][0][1])
    return_open_y = float(openings_by_role["return"]["opening_mm"][0][1])
    supply_lead = lead(supply_terminal, supply_open_y)
    return_lead = lead(return_terminal, return_open_y)
    supply_audit = analyze_lead(
        supply_lead, body_points, terminal_at_start=True,
        opening_mm=openings_by_role["supply"]["opening_mm"],
    )
    return_audit = analyze_lead(
        return_lead, body_points, terminal_at_start=False,
        opening_mm=openings_by_role["return"]["opening_mm"],
    )

    return {
        "document_id": "source_kitchen_door_pair_073_20260925",
        "kind": "kitchen_door_pair_attempt_independently_corrected",
        "room_id": "FLOOR_1_PLAN:dbda1f3916917c37:ROOM (kitchen)",
        "kitchen_openings": source_openings,
        "kitchen_spiral_zone_3_2": {
            "terminals_mm": [list(supply_terminal), list(return_terminal)],
            "geometry": "MEANDER (serpentine, alternating rows at 200mm), NOT bifilar counterflow spiral",
            "owner_rule_violation": "owner manual forbids big meander in regular rectangle",
            "terminal_open_offset_mm": {
                "supply": round(supply_terminal[1] - supply_open_y, 1),
                "return": round(return_terminal[1] - return_open_y, 1),
            },
        },
        "lead_attempt": {
            "supply_lead_mm": [list(point) for point in supply_lead],
            "return_lead_mm": [list(point) for point in return_lead],
            "supply_lead_len_m": round(lead_len(supply_lead) / 1000, 3),
            "return_lead_len_m": round(lead_len(return_lead) / 1000, 3),
            "supply": supply_audit,
            "return": return_audit,
            "supply_status": "NO_GO_R80_AND_SOURCE_OPENING_CROSSING",
            "return_status": "NO_GO_BODY_OVERLAP_AND_SOURCE_OPENING_CROSSING",
            "note": (
                "Supply has only its required BODY-terminal contact; its 9mm first leg cannot materialize R80. "
                "Return has a 200mm overlap with a non-adjacent BODY segment. Both first boundary contacts are "
                "110mm outside their 301mm source-gap candidates."
            ),
        },
        "verdict": (
            "NO-GO for the two tested sharp leads: supply fails R80 and misses the source-gap candidate; "
            "return overlaps non-adjacent BODY and misses the source-gap candidate. The source gaps remain "
            "unverified for construction passage."
        ),
        "collectorContinuous": 0,
        "completeK1": 0,
        "GEOMETRY_VALID": False,
        "TRANSIT_VALID": False,
        "FULL_CIRCUIT_VALID": False,
        "LENGTH_VALID": False,
    }


def main() -> None:
    report = build_report()
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUTPUT_PATH)
    print("sharp lead lengths m", report["lead_attempt"]["supply_lead_len_m"], report["lead_attempt"]["return_lead_len_m"])
    print(
        "forbidden BODY intersections",
        report["lead_attempt"]["supply"]["forbidden_non_adjacent_body_intersection"],
        report["lead_attempt"]["return"]["forbidden_non_adjacent_body_intersection"],
    )


if __name__ == "__main__":
    main()

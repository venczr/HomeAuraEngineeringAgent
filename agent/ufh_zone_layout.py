"""Geometry-only zoning candidates for long UFH room routes.

Zones are independent coverage candidates.  This module deliberately does
not invent collector paths: endpoint access remains UNVERIFIED until a source
or installer supplies an authorized transit route.
"""
from __future__ import annotations

from math import hypot
from typing import Iterable

from shapely.geometry import LineString, Polygon
from shapely.ops import split, unary_union

from agent.ufh_bend_geometry import validate_rounded_centerline
from agent.ufh_endpoint_access import review_zone_route_endpoints
from agent.ufh_layout_engine import build_meander, build_polygon_meander, polyline_length, validate_containment
from agent.ufh_physical_validation import validate_physical_route


def _bounds(boundary):
    poly = Polygon(list(boundary))
    return poly, tuple(int(round(v)) for v in poly.bounds)


def _split_polygons(poly: Polygon, zone_count: int) -> list[Polygon]:
    """Split the observed room polygon into exact horizontal bands.

    Horizontal bands keep the source polygon (including small steps/notches)
    instead of replacing it with an envelope.  This is the useful direction
    for the Test_01 kitchen and remains a conservative geometry-only split.
    """
    min_x, min_y, max_x, max_y = poly.bounds
    pieces: list[Polygon] = [poly]
    for index in range(1, zone_count):
        y = min_y + (max_y - min_y) * index / zone_count
        cutter = LineString([(min_x - 100, y), (max_x + 100, y)])
        next_pieces: list[Polygon] = []
        for piece in pieces:
            result = split(piece, cutter)
            next_pieces.extend(
                geometry for geometry in result.geoms
                if geometry.geom_type == "Polygon" and geometry.area > 1.0
            )
        pieces = next_pieces
    return sorted(pieces, key=lambda item: (item.bounds[1], item.bounds[0]))


def propose_zoned_meanders(
    boundary: Iterable[tuple[int, int]],
    *,
    target_route_length_mm: int = 50000,
    spacing_mm: int = 200,
    wall_offset_mm: int = 100,
    bend_radius_mm: int = 80,
    pipe_outer_radius_mm: int = 8,
    maximum_zones: int = 4,
) -> dict[str, object]:
    poly, bounds = _bounds(boundary)
    if poly.is_empty or not poly.is_valid:
        return {"status": "INVALID_GEOMETRY", "candidates": [], "diagnostics": ["INVALID_BOUNDARY"]}
    area_ratio = poly.area / max((bounds[2] - bounds[0]) * (bounds[3] - bounds[1]), 1)
    if area_ratio < 0.96:
        return {"status": "UNVERIFIED_COMPLEX_BOUNDARY", "candidates": [], "diagnostics": ["COMPLEX_BOUNDARY_REQUIRES_ZONE_DECOMPOSITION"]}
    candidates = []
    for zone_count in range(2, maximum_zones + 1):
        zone_polygons = _split_polygons(poly, zone_count)
        if len(zone_polygons) != zone_count:
            candidates.append({
                "zone_count": zone_count,
                "status": "REJECTED_GEOMETRY",
                "geometry_valid": False,
                "topology_valid": False,
                "bend_valid": False,
                "circuit_split_valid": False,
                "endpoint_access": "UNVERIFIED",
                "manifold_connected": "UNVERIFIED",
                "endpoint_access_geometry": "INVALID",
                "routes": [],
                "diagnostics": ["ZONE_SPLIT_DID_NOT_PRESERVE_POLYGON"],
            })
            continue
        routes = []
        valid = True
        diagnostics = []
        for index, zone_polygon in enumerate(zone_polygons):
            zone_boundary = [
                (int(round(x)), int(round(y)))
                for x, y in zone_polygon.exterior.coords
            ]
            route = build_polygon_meander(zone_boundary, spacing_mm, wall_offset_mm)
            if not route:
                valid = False
                diagnostics.append(f"ZONE_{index + 1}_ROUTE_EMPTY")
                continue
            route_report = validate_physical_route(route, zone_boundary, spacing_mm=spacing_mm, minimum_bend_radius_mm=bend_radius_mm)
            rounded_report = validate_rounded_centerline(route, zone_boundary, bend_radius_mm=bend_radius_mm, pipe_outer_radius_mm=pipe_outer_radius_mm)
            if not route_report.valid or not rounded_report.valid:
                valid = False
                diagnostics.extend([f"ZONE_{index + 1}_CENTERLINE_INVALID", *route_report.diagnostics, *rounded_report.diagnostics])
            routes.append({
                "zone_id": f"zone-{zone_count}-{index + 1}",
                "boundary_mm": [list(point) for point in zone_boundary],
                "route_mm": [list(point) for point in route],
                "length_mm": round(polyline_length(route), 3),
                "geometry_valid": route_report.geometry_valid,
                "topology_valid": route_report.topology_valid,
                "bend_valid": rounded_report.valid,
                "endpoint_access": "UNVERIFIED",
                "manifold_connected": "UNVERIFIED",
            })
        # Geometric endpoint reach is evaluated independently from opening
        # and manifold authority. A route may reach the boundary of its own
        # zone while the building still has no verified wall crossing.
        for route_row in routes:
            endpoint_review = review_zone_route_endpoints(
                route_row["route_mm"],
                route_row["boundary_mm"],
                other_routes=[other["route_mm"] for other in routes if other is not route_row],
            )
            route_row["endpoint_access_geometry"] = endpoint_review
        endpoint_geometry_valid = bool(routes) and all(
            row["endpoint_access_geometry"]["endpoint_access_state"] == "VALID" for row in routes
        )
        if routes:
            merged = unary_union([Polygon(zone["boundary_mm"]) for zone in routes])
            overlap = sum(Polygon(routes[i]["boundary_mm"]).intersection(Polygon(routes[j]["boundary_mm"])).area for i in range(len(routes)) for j in range(i + 1, len(routes)))
            lengths_valid = all(zone["length_mm"] <= target_route_length_mm for zone in routes)
            if overlap > 1.0:
                valid = False
                diagnostics.append("ZONE_BOUNDARY_OVERLAP")
            if not lengths_valid:
                valid = False
                diagnostics.append("ZONE_LENGTH_TARGET_NOT_MET")
            candidates.append({
                "zone_count": zone_count,
                "status": "CANDIDATE_UNVERIFIED_ENDPOINT_ACCESS" if valid else "REJECTED_GEOMETRY",
                "geometry_valid": valid,
                "topology_valid": valid,
                "bend_valid": valid,
                "circuit_split_valid": False,
                "endpoint_access": "UNVERIFIED",
                "manifold_connected": "UNVERIFIED",
                "endpoint_access_geometry": "VALID" if endpoint_geometry_valid else "INVALID",
                "routes": routes,
                "diagnostics": list(dict.fromkeys(diagnostics)),
            })
    accepted = [candidate for candidate in candidates if candidate["geometry_valid"]]
    status = "CANDIDATE_UNVERIFIED_ENDPOINT_ACCESS" if accepted else "NO_GEOMETRIC_ZONE_CANDIDATE"
    return {"status": status, "area_ratio": round(area_ratio, 6), "candidates": candidates, "recommended": accepted[0] if accepted else None, "diagnostics": [] if accepted else ["NO_ZONE_PASSED_GEOMETRY_GATE"]}


__all__ = ["propose_zoned_meanders"]

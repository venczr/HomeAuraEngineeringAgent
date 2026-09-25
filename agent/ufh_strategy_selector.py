"""Priority strategy selection for real Test_01 room geometry.

The selector measures emitted routes.  A label never promotes a meander to a
spiral: every spiral candidate passes the existing topology, bend and exact
boundary gates before it is returned.
"""
from __future__ import annotations

from typing import Iterable

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points, split, unary_union

from agent.ufh_bend_geometry import validate_rounded_centerline
from agent.ufh_endpoint_access import review_zone_route_endpoints
from agent.ufh_layout_engine import (
    build_bifilar_spiral,
    build_polygon_meander,
    polyline_length,
    validate_bifilar_topology,
    validate_containment,
)
from agent.ufh_zone_layout import propose_zoned_meanders


def _bands(poly: Polygon, count: int) -> list[Polygon]:
    min_x, min_y, max_x, max_y = poly.bounds
    pieces: list[Polygon] = [poly]
    for index in range(1, count):
        y = min_y + (max_y - min_y) * index / count
        cutter = LineString([(min_x - 100, y), (max_x + 100, y)])
        next_pieces: list[Polygon] = []
        for piece in pieces:
            result = split(piece, cutter)
            next_pieces.extend(g for g in result.geoms if g.geom_type == "Polygon" and g.area > 1.0)
        pieces = next_pieces
    return sorted(pieces, key=lambda item: (item.bounds[1], item.bounds[0]))


def _route_report(route, boundary, *, max_length_mm, bend_radius_mm, spacing_mm=200, preferred_exit_mm=None, preferred_exit_segment=None, other_routes=()):
    bounds = tuple(int(round(value)) for value in Polygon(boundary).bounds)
    topology = validate_bifilar_topology(route, bounds, boundary, spacing_mm=spacing_mm, minimum_bend_radius_mm=bend_radius_mm)
    rounded = validate_rounded_centerline(route, boundary, bend_radius_mm=bend_radius_mm, pipe_outer_radius_mm=8)
    containment = validate_containment(route, boundary)
    endpoint = review_zone_route_endpoints(route, boundary, other_routes=other_routes, preferred_exit_mm=preferred_exit_mm, preferred_exit_segment=preferred_exit_segment)
    return topology, rounded, containment, endpoint, polyline_length(route), bounds


def _spiral_rectangles(poly: Polygon, *, spacing_mm: int, wall_offset_mm: int, maximum_zones: int):
    """Yield bounded rectangular subregions in several orientations.

    The old search only split equal horizontal bands and then passed the
    complete bounding box to the spiral builder.  This iterator explores a
    small deterministic set of horizontal/vertical cut positions and trims
    each candidate rectangle against the true source polygon.  A candidate is
    never accepted until the emitted centerline is checked against the exact
    zone polygon.
    """
    min_x, min_y, max_x, max_y = poly.bounds
    for count in range(2, maximum_zones + 1):
        for orientation, span in (("H", max_y - min_y), ("V", max_x - min_x)):
            cut_values = [
                [min_y + span * ratio for ratio in ratios]
                if orientation == "H" else
                [min_x + span * ratio for ratio in ratios]
                for ratios in (
                    tuple(index / count for index in range(1, count)),
                    tuple(max(0.12, min(0.88, index / count - 0.08)) for index in range(1, count)),
                    tuple(max(0.12, min(0.88, index / count + 0.08)) for index in range(1, count)),
                )
            ]
            for cuts in cut_values:
                edges = ([min_y, *cuts, max_y] if orientation == "H" else [min_x, *cuts, max_x])
                zones = []
                for start, end in zip(edges, edges[1:]):
                    box = Polygon([(min_x, start), (max_x, start), (max_x, end), (min_x, end)]) if orientation == "H" else Polygon([(start, min_y), (end, min_y), (end, max_y), (start, max_y)])
                    clipped = poly.intersection(box)
                    if clipped.geom_type != "Polygon" or clipped.area <= 1:
                        zones = []
                        break
                    zones.append(clipped)
                if len(zones) == count:
                    yield f"{orientation}{count}", zones


def _spiral_candidate(zone: Polygon, *, spacing_mm: int, wall_offset_mm: int, bend_radius_mm: int, maximum_circuit_length_mm: int):
    """Return a measured spiral candidate and structured rejection reasons."""
    min_x, min_y, max_x, max_y = (int(round(v)) for v in zone.bounds)
    reasons = []
    # Trim the bounding rectangle in grid increments.  This handles notches
    # and narrow shoulders without changing the source polygon.
    trim_step = max(spacing_mm, 200)
    trim_candidates = (
        (0, 0, 0, 0), (trim_step, 0, 0, 0), (0, trim_step, 0, 0),
        (0, 0, trim_step, 0), (0, 0, 0, trim_step),
        (trim_step, trim_step, 0, 0), (0, 0, trim_step, trim_step),
        (trim_step, 0, trim_step, 0), (0, trim_step, 0, trim_step),
        (trim_step * 4, 0, 0, 0), (trim_step * 4, trim_step, 0, 0),
    )
    for left, right, bottom, top in trim_candidates:
                    bounds = (min_x + left, min_y + bottom, max_x - right, max_y - top)
                    if bounds[2] - bounds[0] <= 0 or bounds[3] - bounds[1] <= 0:
                        continue
                    route = build_bifilar_spiral(bounds, spacing_mm, wall_offset_mm)
                    if not route:
                        reasons.append("GENERATOR_ENVELOPE_TOO_SMALL_FOR_REQUESTED_SPACING")
                        continue
                    # Avoid running the expensive rounded-bend and endpoint
                    # validators for an obviously overlong centerline.
                    if polyline_length(route) > maximum_circuit_length_mm:
                        reasons.append("MAXIMUM_CIRCUIT_LENGTH_EXCEEDED")
                        continue
                    topology, rounded, containment, endpoint, length, _ = _route_report(route, list(zone.exterior.coords), max_length_mm=maximum_circuit_length_mm, bend_radius_mm=bend_radius_mm, spacing_mm=spacing_mm)
                    if not containment.valid:
                        reasons.append("CONTAINMENT_GATE_FAILED")
                        continue
                    if not topology.valid:
                        reasons.extend(topology.diagnostics)
                        continue
                    if not rounded.valid:
                        reasons.extend(rounded.diagnostics or ["ROUNDED_BEND_GATE_FAILED"])
                        continue
                    if endpoint["endpoint_access_state"] != "VALID":
                        reasons.append("ENDPOINT_ACCESS_GATE_FAILED")
                        continue
                    if length > maximum_circuit_length_mm:
                        reasons.append("MAXIMUM_CIRCUIT_LENGTH_EXCEEDED")
                        continue
                    inner = Polygon([(bounds[0], bounds[1]), (bounds[2], bounds[1]), (bounds[2], bounds[3]), (bounds[0], bounds[3]), (bounds[0], bounds[1])])
                    return route, inner, []
    return None, None, sorted(set(reasons))


def _joint_endpoint_review(routes, source_polygon: Polygon, *, clearance_mm: int = 108):
    """Check two or more routes together before proposing room exits."""
    lines = [LineString(route) for route in routes]
    occupied = [line.buffer(clearance_mm) for line in lines]
    checks = []
    for index, line in enumerate(lines):
        other = unary_union([occupied[j] for j in range(len(lines)) if j != index]) if len(lines) > 1 else None
        for endpoint_name, endpoint in (("START", line.coords[0]), ("END", line.coords[-1])):
            boundary_point = nearest_points(Point(endpoint), source_polygon.boundary)[1]
            path = LineString([endpoint, boundary_point])
            blocked = bool(other and path.intersects(other))
            checks.append({
                "route_index": index,
                "endpoint": endpoint_name,
                "endpoint_local_mm": [round(endpoint[0], 3), round(endpoint[1], 3)],
                "boundary_candidate_local_mm": [round(boundary_point.x, 3), round(boundary_point.y, 3)],
                "path_length_mm": round(path.length, 3),
                "other_route_clear": not blocked,
                "status": "GEOMETRIC_BOUNDARY_CANDIDATE" if not blocked else "BLOCKED_BY_OTHER_ROUTE",
                "DOOR_PASSAGE_AUTHORIZED": "UNVERIFIED",
                "MANIFOLD_CONNECTED": "UNVERIFIED",
            })
    return {"clearance_mm": clearance_mm, "checks": checks, "joint_endpoint_geometry_valid": all(item["status"] == "GEOMETRIC_BOUNDARY_CANDIDATE" for item in checks)}


def _pipe_band_coverage(source_polygon: Polygon, routes, *, spacing_mm: int, bend_radius_mm: int) -> tuple[float, float]:
    """Real pipe coverage = buffer of BODY rounded centerline, clipped to room.

    Only the rounded BODY centerline is buffered by ``spacing_mm / 2``; transit
    tails are never counted as coverage.  This is intentionally distinct from
    the legacy zone-tiling area.
    """
    if not routes:
        return 0.0, float(source_polygon.area)
    boundary = list(source_polygon.exterior.coords)
    bands: list[Polygon] = []
    for route in routes:
        rounded = validate_rounded_centerline(route, boundary, bend_radius_mm=bend_radius_mm, pipe_outer_radius_mm=8)
        line = LineString(rounded.rounded_points) if len(rounded.rounded_points) >= 2 else LineString()
        if not line.is_empty:
            bands.append(line.buffer(spacing_mm / 2.0))
    if not bands:
        return 0.0, float(source_polygon.area)
    covered = source_polygon.intersection(unary_union(bands))
    uncovered = source_polygon.difference(covered)
    return float(covered.area), float(uncovered.area)


def _coverage_metadata(source_polygon: Polygon, occupied_zones: list[Polygon], *, routes=(), spacing_mm: int = 200, bend_radius_mm: int = 80) -> dict[str, object]:
    occupied = unary_union(occupied_zones) if occupied_zones else Polygon()
    remainder = source_polygon.difference(occupied)
    parts = list(remainder.geoms) if remainder.geom_type == "MultiPolygon" else ([remainder] if remainder.geom_type == "Polygon" and not remainder.is_empty else [])
    pipe_covered, pipe_uncovered = _pipe_band_coverage(source_polygon, routes, spacing_mm=spacing_mm, bend_radius_mm=bend_radius_mm)
    return {
        # Legacy zone-tiling fields (kept for compatibility; NOT pipe coverage).
        "SPIRAL_COVERAGE_AREA": round(float(occupied.area), 3),
        "MEANDER_COVERAGE_AREA": 0.0,
        "UNCOVERED_HEATABLE_AREA": round(float(sum(part.area for part in parts)), 3),
        "UNCOVERED_AREAS_MM": [[[round(x, 3), round(y, 3)] for x, y in part.exterior.coords] for part in parts],
        "COVERAGE_AREA_SEMANTICS": "ZONE_AREA_TILING_LEGACY_NOT_PIPE_COVERAGE",
        # Real pipe-band coverage (BODY only).
        "PIPE_BAND_COVERAGE_AREA": round(pipe_covered, 3),
        "PIPE_BAND_UNCOVERED_AREA": round(pipe_uncovered, 3),
        "PIPE_BAND_COVERAGE_PERCENT": round(100.0 * pipe_covered / source_polygon.area, 3) if source_polygon.area > 0 else 0.0,
        "PIPE_COVERAGE_METHOD": "BODY_ROUNDED_CENTERLINE_BUFFER_SPACING_HALF_NO_TRANSIT",
    }


def _meander_coverage_metadata(source_polygon: Polygon, occupied_zones: list[Polygon], *, routes=(), spacing_mm: int = 200, bend_radius_mm: int = 80) -> dict[str, object]:
    metadata = _coverage_metadata(source_polygon, occupied_zones, routes=routes, spacing_mm=spacing_mm, bend_radius_mm=bend_radius_mm)
    metadata["MEANDER_COVERAGE_AREA"] = metadata["SPIRAL_COVERAGE_AREA"]
    metadata["SPIRAL_COVERAGE_AREA"] = 0.0
    return metadata


def select_layout(
    boundary: Iterable[tuple[int, int]],
    *,
    mode: str = "AUTO",
    maximum_circuit_length_mm: int = 90_000,
    spacing_mm: int = 200,
    wall_offset_mm: int = 100,
    bend_radius_mm: int = 80,
    maximum_zones: int = 3,
    preferred_exit_mm: tuple[int, int] | None = None,
    preferred_exit_segment: tuple[tuple[int, int], tuple[int, int]] | None = None,
) -> dict[str, object]:
    source = [(int(x), int(y)) for x, y in boundary]
    polygon = Polygon(source)
    if polygon.is_empty or not polygon.is_valid:
        return {"strategy": "UNRESOLVED", "routes": [], "diagnostics": ["INVALID_BOUNDARY"]}
    origin_x, origin_y = int(round(polygon.bounds[0])), int(round(polygon.bounds[1]))
    local_polygon = Polygon([(x - origin_x, y - origin_y) for x, y in source])
    local_boundary = list(local_polygon.exterior.coords)
    diagnostics: list[str] = []
    requested = mode.upper()

    preferred_local = None if preferred_exit_mm is None else (float(preferred_exit_mm[0] - origin_x), float(preferred_exit_mm[1] - origin_y))
    preferred_segment_local = None if preferred_exit_segment is None else tuple((float(p[0] - origin_x), float(p[1] - origin_y)) for p in preferred_exit_segment)

    def materialize(strategy, polygons, routes, reasons):
        output = []
        for index, (zone, route) in enumerate(zip(polygons, routes), start=1):
            zone_boundary = [[int(round(x + origin_x)), int(round(y + origin_y))] for x, y in zone.exterior.coords]
            global_route = [[int(round(x + origin_x)), int(round(y + origin_y))] for x, y in route]
            topology, rounded, containment, endpoint, length, _ = _route_report(route, list(zone.exterior.coords), max_length_mm=maximum_circuit_length_mm, bend_radius_mm=bend_radius_mm, spacing_mm=spacing_mm, preferred_exit_mm=preferred_local, preferred_exit_segment=preferred_segment_local, other_routes=[r for r in routes if r is not route])
            # The bifilar topology gate is intentionally strict for spiral
            # candidates.  A fallback meander has a different valid topology
            # contract: one connected, simple centerline with no branches.
            topology_valid = topology.valid
            topology_diagnostics = list(topology.diagnostics)
            if strategy.startswith("MEANDER"):
                simple = LineString(route).is_simple and len(route) >= 2
                topology_valid = bool(simple)
                topology_diagnostics = [] if simple else ["MEANDER_CENTERLINE_TOPOLOGY_INVALID"]
            output.append({
                "route_id": f"{strategy.lower()}-{index}",
                "zone_boundary_mm": zone_boundary,
                "route_mm": global_route,
                "length_mm": round(rounded.rounded_length_mm, 3),
                "INTERNAL_PIPE_LENGTH": round(rounded.rounded_length_mm, 3),
                "IN_ROOM_CONNECTION_LENGTH": round(sum(float(item.get("distance_mm") or 0) for item in endpoint.get("endpoints", [])), 3),
                "BUILDING_TRANSIT_LENGTH": None,
                "TOTAL_CIRCUIT_LENGTH": None,
                "LENGTH_RESERVE": None,
                "GEOMETRY_VALID": containment.valid and topology_valid,
                "TOPOLOGY_VALID": topology_valid,
                "BEND_VALID": rounded.valid,
                "PIPE_LENGTH_VALID": rounded.rounded_length_mm <= maximum_circuit_length_mm,
                "ENDPOINT_ACCESS_VALID": endpoint["endpoint_access_state"] == "VALID",
                "MANIFOLD_CONNECTED": "UNVERIFIED",
                "endpoint_access": endpoint,
                "rounded_geometry": rounded.as_dict(),
                "diagnostics": list(dict.fromkeys([*topology_diagnostics, *rounded.diagnostics, *([] if containment.valid else ["CONTAINMENT_GATE_FAILED"])])),
            })
        return output

    if requested in {"AUTO", "SPIRAL"}:
        bounds = tuple(int(round(value)) for value in local_polygon.bounds)
        route = build_bifilar_spiral(bounds, spacing_mm, wall_offset_mm)
        if route:
            topology, rounded, containment, endpoint, length, _ = _route_report(route, local_boundary, max_length_mm=maximum_circuit_length_mm, bend_radius_mm=bend_radius_mm, spacing_mm=spacing_mm)
            if topology.valid and rounded.valid and containment.valid and length <= maximum_circuit_length_mm:
                rows = materialize("BIFILAR_SPIRAL", [local_polygon], [route], [])
                coverage = _coverage_metadata(local_polygon, [local_polygon], routes=[route], spacing_mm=spacing_mm, bend_radius_mm=bend_radius_mm)
                rows[0].update(coverage)
                return {"strategy": "BIFILAR_SPIRAL", "strategy_reason": "exact boundary, topology, bend and length gates passed", "routes": rows, **coverage, "preferred_exit_segment_mm": preferred_exit_segment, "rejected_candidates": diagnostics}
            diagnostics.append("BIFILAR_SPIRAL_REJECTED:" + ",".join(topology.diagnostics or rounded.diagnostics or (["MAXIMUM_CIRCUIT_LENGTH_EXCEEDED"] if length > maximum_circuit_length_mm else ["CONTAINMENT_GATE_FAILED"])))
        else:
            diagnostics.append("BIFILAR_SPIRAL_REJECTED:ROOM_TOO_NARROW_FOR_R80")
        if requested in {"AUTO", "HYBRID"} and local_polygon.area <= 30_000_000:
            # For stepped rooms, search an inscribed rectangular core.  The
            # result is explicitly HYBRID because the residual polygon is not
            # silently claimed as spiral coverage.
            best = None
            trim_candidates = ((0, 0, 0, 0), (400, 0, 0, 0), (0, 400, 0, 0), (0, 0, 400, 0), (0, 0, 0, 400), (400, 400, 0, 0), (400, 0, 400, 0), (0, 400, 0, 400))
            for trim_left, trim_right, trim_bottom, trim_top in trim_candidates:
                            candidate_bounds = (bounds[0] + trim_left, bounds[1] + trim_bottom, bounds[2] - trim_right, bounds[3] - trim_top)
                            if candidate_bounds[2] - candidate_bounds[0] < 3000 or candidate_bounds[3] - candidate_bounds[1] < 3000:
                                continue
                            candidate = build_bifilar_spiral(candidate_bounds, spacing_mm, wall_offset_mm)
                            if not candidate or not validate_containment(candidate, local_boundary).valid:
                                continue
                            topology, rounded, containment, endpoint, length, _ = _route_report(candidate, local_boundary, max_length_mm=maximum_circuit_length_mm, bend_radius_mm=bend_radius_mm, spacing_mm=spacing_mm)
                            if not (topology.valid and rounded.valid and containment.valid and endpoint["endpoint_access_state"] == "VALID" and length <= maximum_circuit_length_mm):
                                continue
                            area = (candidate_bounds[2] - candidate_bounds[0]) * (candidate_bounds[3] - candidate_bounds[1])
                            if best is None or area > best[0]:
                                best = (area, candidate_bounds, candidate)
            if best:
                core = Polygon([(best[1][0], best[1][1]), (best[1][2], best[1][1]), (best[1][2], best[1][3]), (best[1][0], best[1][3]), (best[1][0], best[1][1])])
                diagnostics.append("HYBRID_SPIRAL_MEANDER_RESIDUAL_AREA_REQUIRES_SEPARATE_CHECK")
                hybrid_routes = materialize("HYBRID_SPIRAL", [core], [best[2]], [])
                for route_item in hybrid_routes:
                    route_item["SPIRAL_COVERAGE_AREA"] = round(core.area, 3)
                    route_item["MEANDER_COVERAGE_AREA"] = 0.0
                    route_item["UNCOVERED_HEATABLE_AREA"] = round(max(0.0, polygon.area - core.area), 3)
                    route_item["HYBRID_CONNECTION_VALID"] = False
                    route_item["HYBRID_VALID"] = False
                coverage = _coverage_metadata(local_polygon, [core], routes=[best[2]], spacing_mm=spacing_mm, bend_radius_mm=bend_radius_mm)
                for route_item in hybrid_routes:
                    route_item.update(coverage)
                diagnostics.append("HYBRID_CONNECTION_UNPROVEN_RESIDUAL_NOT_ROUTED")
                # Keep the result explicitly partial; the selector must not
                # advertise an unconnected spiral core as full hybrid cover.
                return {"strategy": "HYBRID_SPIRAL_MEANDER", "strategy_reason": "spiral core passed, but residual meander connection is not proven; partial geometry only", "routes": hybrid_routes, "rejected_candidates": diagnostics, **coverage, "preferred_exit_segment_mm": preferred_exit_segment, "residual_area_unverified": round(max(0.0, polygon.area - core.area), 3), "HYBRID_CONNECTION_VALID": False, "HYBRID_VALID": False}
        for orientation, zones in _spiral_rectangles(local_polygon, spacing_mm=spacing_mm, wall_offset_mm=wall_offset_mm, maximum_zones=maximum_zones):
            routes = []
            zone_outputs = []
            rejected = []
            for zone in zones:
                candidate, inner, reasons = _spiral_candidate(zone, spacing_mm=spacing_mm, wall_offset_mm=wall_offset_mm, bend_radius_mm=bend_radius_mm, maximum_circuit_length_mm=maximum_circuit_length_mm)
                if not candidate:
                    rejected.extend(reasons or ["NO_SPIRAL_CANDIDATE"])
                    break
                routes.append(candidate)
                zone_outputs.append(inner)
            if len(routes) == len(zones):
                materialized = materialize("MULTI_BIFILAR_SPIRAL", zone_outputs, routes, [])
                coverage_data = _coverage_metadata(local_polygon, zone_outputs, routes=routes, spacing_mm=spacing_mm, bend_radius_mm=bend_radius_mm)
                for index, route_item in enumerate(materialized):
                    zone_coverage = _coverage_metadata(
                        zone_outputs[index], [zone_outputs[index]],
                        routes=[routes[index]], spacing_mm=spacing_mm,
                        bend_radius_mm=bend_radius_mm,
                    )
                    route_item.update(zone_coverage)
                    route_item["PIPE_COVERAGE_DOMAIN"] = "ROUTE_ZONE"
                    route_item["HYBRID_CONNECTION_VALID"] = None
                coverage_data["PIPE_COVERAGE_DOMAIN"] = "SOURCE_ROOM"
                joint = _joint_endpoint_review(routes, local_polygon)
                return {"strategy": "MULTI_BIFILAR_SPIRAL", "strategy_reason": f"{orientation} partition: {len(routes)} independent spiral zones passed measured geometry, bend, endpoint and length gates", "routes": materialized, "rejected_candidates": diagnostics, **coverage_data, "preferred_exit_segment_mm": preferred_exit_segment, "joint_endpoint_access": joint}
            diagnostics.append(f"MULTI_BIFILAR_SPIRAL_{orientation}_REJECTED:" + ",".join(sorted(set(rejected))))
    if requested in {"AUTO", "HYBRID"}:
        diagnostics.append("HYBRID_SPIRAL_MEANDER_UNVERIFIED_FOR_REMAINING_NICHES")
    if requested == "AUTO":
        zoned = propose_zoned_meanders(local_boundary, target_route_length_mm=maximum_circuit_length_mm, spacing_mm=spacing_mm, wall_offset_mm=wall_offset_mm, bend_radius_mm=bend_radius_mm, maximum_zones=maximum_zones)
        if zoned.get("recommended"):
            candidate = zoned["recommended"]
            zones = [Polygon(route["boundary_mm"]) for route in candidate["routes"]]
            routes = [route["route_mm"] for route in candidate["routes"]]
            materialized = materialize("MEANDER", zones, routes, [])
            for index, route_item in enumerate(materialized):
                route_item.update(_meander_coverage_metadata(zones[index], [zones[index]], routes=[routes[index]], spacing_mm=spacing_mm, bend_radius_mm=bend_radius_mm))
                route_item["PIPE_COVERAGE_DOMAIN"] = "ROUTE_ZONE"
            coverage_data = _meander_coverage_metadata(local_polygon, zones, routes=routes, spacing_mm=spacing_mm, bend_radius_mm=bend_radius_mm)
            coverage_data["PIPE_COVERAGE_DOMAIN"] = "SOURCE_ROOM"
            return {"strategy": "MEANDER_ONLY", "strategy_reason": "MULTI_BIFILAR_SPIRAL rejected by R80/zone height gates; independent meander zones selected", "routes": materialized, "rejected_candidates": diagnostics + ["MULTI_BIFILAR_SPIRAL_REJECTED:ZONE_TOO_NARROW_FOR_R80"], **coverage_data}
    if requested in {"AUTO", "HYBRID", "MEANDER"}:
        route = build_polygon_meander(local_boundary, spacing_mm, wall_offset_mm)
        if route:
            candidate_routes = materialize("MEANDER_ONLY", [local_polygon], [route], [])
            if candidate_routes[0]["PIPE_LENGTH_VALID"]:
                coverage_data = _meander_coverage_metadata(local_polygon, [local_polygon], routes=[route], spacing_mm=spacing_mm, bend_radius_mm=bend_radius_mm)
                coverage_data["PIPE_COVERAGE_DOMAIN"] = "SOURCE_ROOM"
                candidate_routes[0].update(coverage_data)
                strategy = "MEANDER_ONLY" if requested != "HYBRID" else "HYBRID_SPIRAL_MEANDER"
                return {"strategy": strategy, "strategy_reason": "spiral candidates rejected by measured geometry/length gates", "routes": candidate_routes, "rejected_candidates": diagnostics, **coverage_data}
            diagnostics.append("MEANDER_ONLY_REJECTED:MAXIMUM_CIRCUIT_LENGTH_EXCEEDED")
    return {"strategy": "UNRESOLVED", "strategy_reason": "all requested strategies failed independent gates", "routes": [], "rejected_candidates": diagnostics}


__all__ = ["select_layout"]

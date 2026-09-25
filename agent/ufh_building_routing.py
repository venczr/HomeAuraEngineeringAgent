"""Building-level preliminary UFH transit routing.

This module joins already validated room centerlines to an explicitly supplied
door threshold and corridor polygon.  It never infers a wall crossing or
collector connection from proximity alone.  Missing corridor/opening authority
therefore produces an explicit UNVERIFIED result instead of a fabricated line.
"""
from __future__ import annotations

from math import hypot
from typing import Iterable

from shapely.geometry import LineString, Point, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union
from agent.ufh_bend_geometry import build_rounded_centerline


def _direct_or_bend(start: tuple[float, float], end: tuple[float, float], allowed: Polygon, blocked=()) -> list[tuple[float, float]] | None:
    blocked_geometries = [LineString(list(x)).buffer(16) for x in blocked if len(list(x)) >= 2]
    direct = LineString([start, end])
    if allowed.covers(direct) and not any(direct.intersects(geometry) for geometry in blocked_geometries):
        return [start, end]
    candidates = [[start, (end[0], start[1]), end], [start, (start[0], end[1]), end]]
    for path in candidates:
        line = LineString(path)
        if allowed.covers(line) and not any(line.intersects(geometry) for geometry in blocked_geometries):
            return path
    return None


def _geometry(value):
    """Create a shapely geometry without losing transition holes/rings.

    Public callers historically supplied a coordinate ring.  New callers may
    supply a polygon mapping with ``outer_mm`` and ``holes_mm`` or a shapely
    object.  Keeping this adapter here lets old previews continue to work
    while the building model persists useful-area holes (for stair contact
    zones) explicitly.
    """
    if value is None:
        return GeometryCollection()
    if hasattr(value, "geom_type"):
        return value
    if isinstance(value, dict):
        outer = value.get("outer_mm") or value.get("polygon_mm") or value.get("coordinates") or []
        holes = value.get("holes_mm") or value.get("interiors_mm") or []
        return Polygon(outer, holes)
    return Polygon(list(value))


def _orthogonal_search(start, end, allowed, blocked=(), *, clearance_mm: float = 16.0):
    """Bounded visibility search for a collision-free polyline.

    The search uses a finite set of obstacle and boundary coordinates plus
    offset points. It is deliberately fail-closed and never changes the
    supplied polygon. Returned points are centreline coordinates; the
    clearance buffer is checked against every occupied route.
    """
    if allowed.is_empty or not allowed.is_valid:
        return None
    # Most room and corridor legs are a direct segment or a single orthogonal
    # dog-leg.  Check those before constructing the bounded visibility graph;
    # this preserves the exact polygon/occupied-route checks and avoids a
    # costly graph build for the common case.
    blocked_geometries = [LineString(list(x)).buffer(clearance_mm) for x in blocked if len(list(x)) >= 2]
    simple_candidates = [
        [tuple(start), tuple(end)],
        [tuple(start), (float(end[0]), float(start[1])), tuple(end)],
        [tuple(start), (float(start[0]), float(end[1])), tuple(end)],
    ]
    for candidate in simple_candidates:
        line = LineString(candidate)
        if allowed.covers(line) and not any(line.intersects(geometry) for geometry in blocked_geometries):
            return candidate
    # The source contour contains many sub-millimetre raster cleanup points;
    # simplify only the search graph, never the persisted project geometry.
    exterior = getattr(allowed, "exterior", None)
    if exterior is not None and len(exterior.coords) > 80:
        allowed = allowed.simplify(25.0, preserve_topology=True)
    obstacles = [LineString(list(x)).buffer(clearance_mm) for x in blocked if len(list(x)) >= 2]
    minx, miny, maxx, maxy = allowed.bounds
    xs = {float(start[0]), float(end[0]), minx, maxx}
    ys = {float(start[1]), float(end[1]), miny, maxy}
    # Boundary-only coordinates can produce a single artificial corridor
    # lane.  Add a bounded interior lattice so a paired return can take a
    # physically separate row through a wide neck.  This does not alter the
    # persisted polygon or invent a wall opening; it only improves visibility
    # inside the already supplied admissible geometry.
    lattice_step = max(200.0, 8.0 * clearance_mm)
    lattice_x = set(); lattice_y = set(); boundary_offset_x = set(); boundary_offset_y = set()
    x = minx + lattice_step
    while x < maxx - lattice_step:
        xs.add(float(x)); lattice_x.add(float(x)); x += lattice_step
    y = miny + lattice_step
    while y < maxy - lattice_step:
        ys.add(float(y)); lattice_y.add(float(y)); y += lattice_step
    for x, y in (start, end):
        xs.update((x - 2 * clearance_mm, x + 2 * clearance_mm))
        ys.update((y - 2 * clearance_mm, y + 2 * clearance_mm))
    boundaries = [allowed] if allowed.geom_type == "Polygon" else list(getattr(allowed, "geoms", []))
    boundary_nodes = set()
    for shape in boundaries:
        for x, y in shape.exterior.coords:
            boundary_nodes.add((float(x), float(y)))
            boundary_offset_x.update((float(x) - clearance_mm, float(x) + clearance_mm, float(x) - 2 * clearance_mm, float(x) + 2 * clearance_mm))
            boundary_offset_y.update((float(y) - clearance_mm, float(y) + clearance_mm, float(y) - 2 * clearance_mm, float(y) + 2 * clearance_mm))
            xs.update((float(x), float(x) - clearance_mm, float(x) + clearance_mm))
            ys.update((float(y), float(y) - clearance_mm, float(y) + clearance_mm))
    nodes = [(x, y) for x in sorted(xs) for y in sorted(ys)]
    if len(nodes) > 2500:
        # Keep a bounded deterministic grid, but never discard source-boundary
        # coordinates or the endpoints needed to pass a narrow neck.  The old
        # blind stride could remove the only two vertices around a stair notch
        # and falsely report the corridor as disconnected.
        x_values = sorted(xs); y_values = sorted(ys)
        # Use the regular interior lattice as the Cartesian graph.  Source
        # boundary vertices are added separately below; including every
        # boundary offset in the Cartesian product creates tens of thousands
        # of nodes without adding visibility information.
        x_grid = lattice_x | {float(minx), float(maxx), float(start[0]), float(end[0]), float(minx + 2 * clearance_mm), float(maxx - 2 * clearance_mm)}
        y_grid = lattice_y | {float(miny), float(maxy), float(start[1]), float(end[1]), float(miny + 2 * clearance_mm), float(maxy - 2 * clearance_mm)}
        # Keep a compact lattice plus exact source vertices.  Cartesian
        # expansion of every boundary x with every boundary y made the
        # visibility search quadratic on the detailed corridor polygon.
        nodes = [(x, y) for x in sorted(x_grid) for y in sorted(y_grid)]
        nodes.extend(boundary_nodes)
        for x in (float(start[0]), float(end[0])):
            nodes.extend((x, y) for y in y_grid)
        for y in (float(start[1]), float(end[1])):
            nodes.extend((x, y) for x in x_grid)
    nodes = [p for p in nodes if allowed.buffer(-clearance_mm).covers(Point(p)) or p in boundary_nodes or p in (tuple(start), tuple(end))]
    if tuple(start) not in nodes: nodes.append(tuple(start))
    if tuple(end) not in nodes: nodes.append(tuple(end))
    # Visibility graph with horizontal/vertical links.  Indexing nodes by
    # their x/y coordinate avoids the old all-pairs scan (which was quadratic
    # for the detailed corridor boundary) while preserving the same bounded
    # graph and fail-closed segment checks.
    import heapq
    by_x: dict[float, list[tuple[float, float]]] = {}
    by_y: dict[float, list[tuple[float, float]]] = {}
    for node in nodes:
        by_x.setdefault(node[0], []).append(node)
        by_y.setdefault(node[1], []).append(node)
    for values in by_x.values():
        values.sort(key=lambda p: p[1])
    for values in by_y.values():
        values.sort(key=lambda p: p[0])
    target = tuple(end)
    queue = [(0.0, tuple(start))]; dist = {tuple(start): 0.0}; prev = {}
    while queue:
        cost, current = heapq.heappop(queue)
        if current == target: break
        if cost > dist.get(current, float("inf")): continue
        candidates = by_x.get(current[0], ())
        candidates = list(candidates) + list(by_y.get(current[1], ()))
        for candidate in candidates:
            if candidate == current: continue
            segment = LineString([current, candidate])
            if not allowed.covers(segment): continue
            if any(segment.intersects(obstacle) for obstacle in obstacles): continue
            new_cost = cost + segment.length
            if new_cost < dist.get(candidate, float("inf")):
                dist[candidate] = new_cost; prev[candidate] = current
                heapq.heappush(queue, (new_cost, candidate))
    if target not in dist:
        # Deterministic lane fallback for a wide corridor whose only valid
        # connection runs through an interior row rather than a persisted
        # boundary vertex.  Candidate polylines are still fail-closed against
        # the original polygon and occupied buffers.
        lane_x = sorted(lattice_x | {minx + 2 * clearance_mm, maxx - 2 * clearance_mm, float(start[0]), float(end[0])})
        lane_y = sorted(lattice_y | {miny + 2 * clearance_mm, maxy - 2 * clearance_mm, float(start[1]), float(end[1])})
        safe_end_x = [float(end[0]), float(end[0] - 2 * clearance_mm), float(end[0] + 2 * clearance_mm)]
        safe_end_y = [float(end[1]), float(end[1] - 2 * clearance_mm), float(end[1] + 2 * clearance_mm)]
        for lx in lane_x:
            for ly in lane_y:
                for ex in safe_end_x:
                    for ey in safe_end_y:
                        candidates = [
                            [tuple(start), (lx, float(start[1])), (lx, ly), (ex, ly), tuple(end)],
                            [tuple(start), (float(start[0]), ly), (lx, ly), (lx, ey), tuple(end)],
                        ]
                        for candidate in candidates:
                            line = LineString(candidate)
                            if not allowed.covers(line):
                                continue
                            if any(line.intersects(obstacle) for obstacle in obstacles):
                                continue
                            return candidate
        return None
    path = [target]
    while path[-1] != tuple(start): path.append(prev[path[-1]])
    return list(reversed(path))


def build_door_transition(
    opening_id: str,
    room_side_segment_mm,
    corridor_side_segment_mm,
    *,
    wall_thickness_mm: float | None = None,
    source_gap_mm: float | None = None,
    passage_status: str = "UNVERIFIED",
    geometry_status: str = "PRELIMINARY_SOURCE_CANDIDATE",
) -> dict[str, object]:
    """Build an explicit finite passage area between two wall faces.

    The two segments must have matching endpoint order.  The quadrilateral is
    the only geometry allowed to cross the separating wall; the router never
    unions complete room and corridor polygons to manufacture a connection.
    """
    room_side = [tuple(map(float, p)) for p in room_side_segment_mm]
    corridor_side = [tuple(map(float, p)) for p in corridor_side_segment_mm]
    if len(room_side) != 2 or len(corridor_side) != 2:
        return {"opening_id": opening_id, "geometry_status": "INVALID", "passage_status": passage_status, "diagnostics": ["TRANSITION_REQUIRES_TWO_SIDES"]}
    polygon = Polygon([room_side[0], room_side[1], corridor_side[1], corridor_side[0]])
    if not polygon.is_valid or polygon.area <= 0:
        return {"opening_id": opening_id, "geometry_status": "INVALID", "passage_status": passage_status, "diagnostics": ["TRANSITION_POLYGON_INVALID"]}
    gap = float(source_gap_mm if source_gap_mm is not None else LineString([room_side[0], corridor_side[0]]).length)
    return {
        "opening_id": opening_id,
        "room_side_segment_mm": [list(p) for p in room_side],
        "corridor_side_segment_mm": [list(p) for p in corridor_side],
        "transition_polygon_mm": [[float(x), float(y)] for x, y in polygon.exterior.coords],
        "wall_thickness_mm": wall_thickness_mm,
        "source_gap_mm": round(gap, 3),
        "geometry_status": geometry_status,
        "passage_status": passage_status,
        "diagnostics": (["DOOR_PASSAGE_AUTHORIZATION_REQUIRED"] if passage_status != "CONFIRMED" else []),
    }


def _transition_parts(value):
    """Return room-side, corridor-side and finite transition polygon."""
    if isinstance(value, dict) and value.get("transition_polygon_mm"):
        room = [tuple(map(float, p)) for p in value.get("room_side_segment_mm", [])]
        corridor = [tuple(map(float, p)) for p in value.get("corridor_side_segment_mm", [])]
        transition = _geometry({"polygon_mm": value["transition_polygon_mm"]})
        return room, corridor, transition, value
    if isinstance(value, dict):
        seg = value.get("segment_mm") or value.get("opening_mm") or []
    else:
        seg = value
    points = [tuple(map(float, p)) for p in (seg or [])]
    line = LineString(points) if len(points) == 2 else GeometryCollection()
    return points, points, line.buffer(0.1), {"passage_status": "UNVERIFIED"}


def route_endpoint_to_collector(
    endpoint: tuple[float, float],
    opening_segment: tuple[tuple[float, float], tuple[float, float]],
    room_polygon: Iterable[tuple[float, float]],
    corridor_polygon: Iterable[tuple[float, float]],
    collector_point: tuple[float, float],
    collector_polygon: Iterable[tuple[float, float]] | dict[str, object] | None = None,
    *, occupied_routes: Iterable[Iterable[tuple[float, float]]] = (),
    clearance_mm: float = 16.0,
    collector_transition: dict[str, object] | None = None,
) -> dict[str, object]:
    """Route a circuit endpoint through its room opening and corridor to a collector."""
    room = _geometry(room_polygon); corridor = _geometry(corridor_polygon)
    collector_room = _geometry(collector_polygon) if collector_polygon is not None else Point(collector_point).buffer(100)
    room_side, corridor_side, transition, transition_meta = _transition_parts(opening_segment)
    if not room.is_valid or not corridor.is_valid or transition.is_empty or len(room_side) != 2 or len(corridor_side) != 2:
        return {"status": "UNVERIFIED", "path_mm": [], "length_mm": None, "diagnostics": ["INVALID_ROUTING_GEOMETRY"]}
    room_candidates = [p for p in room_side if room.distance(Point(p)) <= clearance_mm * 3 or room.covers(Point(p))]
    corridor_candidates = [p for p in corridor_side if corridor.distance(Point(p)) <= clearance_mm * 3 or corridor.covers(Point(p))]
    preferred_index = transition_meta.get("corridor_endpoint_index")
    if preferred_index in (0, 1) and len(room_side) == 2 and len(corridor_side) == 2:
        room_target = room_side[int(preferred_index)]
        corridor_target = corridor_side[int(preferred_index)]
    else:
        room_target = min(room_candidates or room_side, key=lambda p: Point(endpoint).distance(Point(p)))
        corridor_target = min(corridor_candidates or corridor_side, key=lambda p: Point(collector_point).distance(Point(p)))
    room_path = _orthogonal_search(tuple(map(float, endpoint)), room_target, room, occupied_routes, clearance_mm=clearance_mm)
    if room_path is None:
        return {"status": "UNVERIFIED", "path_mm": [], "length_mm": None, "diagnostics": ["ROOM_EXIT_BLOCKED_OR_NO_BOUNDED_PATH"]}
    bridge_line = LineString([room_target, corridor_target])
    if not transition.buffer(clearance_mm).covers(bridge_line):
        return {"status": "UNVERIFIED", "path_mm": [list(p) for p in room_path], "length_mm": round(LineString(room_path).length, 3), "diagnostics": ["DOOR_TRANSITION_DISCONNECTED", "DOOR_PASSAGE_AUTHORIZATION_REQUIRED"]}
    # If a separate corridor→collector transition is supplied, it is the only
    # allowed crossing into the collector room. Otherwise retain the legacy
    # project-assumption behaviour for callers that already place the point in
    # the supplied corridor space.
    corridor_end = tuple(map(float, collector_point))
    collector_bridge = []
    collector_path = [corridor_end]
    collector_meta = collector_transition
    if collector_transition:
        c_room, c_corridor, c_poly, collector_meta = _transition_parts(collector_transition)
        c_room_candidates = [p for p in c_room if collector_room.covers(Point(p)) or collector_room.distance(Point(p)) <= clearance_mm * 3]
        c_corridor_candidates = [p for p in c_corridor if corridor.covers(Point(p)) or corridor.distance(Point(p)) <= clearance_mm * 3]
        if not c_room_candidates or not c_corridor_candidates:
            return {"status": "UNVERIFIED", "path_mm": [list(p) for p in room_path], "length_mm": round(LineString(room_path).length, 3), "diagnostics": ["COLLECTOR_TRANSITION_DISCONNECTED"]}
        collector_corridor_index = collector_meta.get("collector_corridor_index", collector_meta.get("collector_endpoint_index"))
        collector_room_index = collector_meta.get("collector_room_index", collector_meta.get("collector_endpoint_index"))
        if collector_corridor_index in (0, 1) and collector_room_index in (0, 1) and len(c_corridor) == 2 and len(c_room) == 2:
            corridor_end = c_corridor[int(collector_corridor_index)]
            collector_end = c_room[int(collector_room_index)]
        else:
            corridor_end = min(c_corridor_candidates, key=lambda p: Point(corridor_target).distance(Point(p)))
            collector_end = min(c_room_candidates, key=lambda p: Point(collector_point).distance(Point(p)))
        collector_bridge_line = LineString([corridor_end, collector_end])
        if not c_poly.buffer(clearance_mm).covers(collector_bridge_line):
            return {"status": "UNVERIFIED", "path_mm": [list(p) for p in room_path], "length_mm": round(LineString(room_path).length, 3), "diagnostics": ["COLLECTOR_TRANSITION_DISCONNECTED"]}
        # The final collector connection is a termination lane inside the
        # proposed manifold area.  Supply and return may terminate at the same
        # project point while remaining separate in the room/corridor; do not
        # let the first termination spuriously block the second room search.
        collector_path = _orthogonal_search(collector_end, tuple(map(float, collector_point)), collector_room, (), clearance_mm=clearance_mm)
        if collector_path is None:
            return {"status": "UNVERIFIED", "path_mm": [list(p) for p in room_path], "length_mm": round(LineString(room_path).length, 3), "diagnostics": ["COLLECTOR_ROOM_NO_BOUNDED_PATH"]}
        collector_bridge = [corridor_end, collector_end]
    corridor_path = _orthogonal_search(corridor_target, corridor_end, corridor, occupied_routes, clearance_mm=clearance_mm)
    if corridor_path is None:
        return {"status": "UNVERIFIED", "path_mm": [list(p) for p in room_path], "length_mm": round(LineString(room_path).length, 3), "diagnostics": ["CORRIDOR_OR_COLLECTOR_NO_BOUNDED_PATH", "DOOR_PASSAGE_AUTHORIZATION_REQUIRED"]}
    merged = room_path[:-1] + [list(room_target), list(corridor_target)] + corridor_path[1:]
    if collector_bridge:
        merged += collector_bridge[1:] + collector_path[1:]
    line = LineString(merged)
    diag = ["MANIFOLD_CONNECTION_UNVERIFIED"]
    if transition_meta.get("passage_status") != "CONFIRMED" or (collector_meta and collector_meta.get("passage_status") != "CONFIRMED"):
        diag.append("DOOR_PASSAGE_AUTHORIZATION_REQUIRED")
    rounded = build_rounded_centerline(merged, bend_radius_mm=80.0)
    geometry_checks = {
        "centerline_simple": bool(line.is_simple),
        "pipe_outer_diameter_mm": 16.0,
        "required_free_clearance_mm": float(clearance_mm),
        "bend_radius_mm": 80.0,
        "rounded_centerline_length_mm": round(rounded.length_mm, 3),
        "bend_geometry_status": "VALID" if rounded.valid else "REQUIRES_ROUNDED_BEND_REVIEW",
        "bend_diagnostics": list(rounded.diagnostics),
    }
    if not line.is_simple:
        diag.append("ROUTE_CENTERLINE_SELF_INTERSECTION")
    if not rounded.valid:
        diag.append("BEND_GEOMETRY_REQUIRES_REVIEW")
    return {"status": "GEOMETRIC_PREVIEW_UNVERIFIED_AUTHORITY", "path_mm": [list(p) for p in merged], "length_mm": round(line.length, 3), "room_length_mm": round(LineString(room_path).length, 3), "corridor_length_mm": round(LineString(corridor_path).length, 3), "transition_length_mm": round(bridge_line.length + sum(LineString(x).length for x in ([collector_bridge] if collector_bridge else [])), 3), "geometry_checks": geometry_checks, "diagnostics": diag}


def route_endpoint_to_opening(
    endpoint: tuple[float, float],
    opening_segment: tuple[tuple[float, float], tuple[float, float]],
    room_polygon: Iterable[tuple[float, float]],
    corridor_polygon: Iterable[tuple[float, float]] | None,
    *,
    occupied_routes: Iterable[Iterable[tuple[float, float]]] = (),
    clearance_mm: float = 16.0,
) -> dict[str, object]:
    room = Polygon(list(room_polygon))
    if isinstance(opening_segment, dict):
        opening_segment = opening_segment.get("segment_mm") or opening_segment.get("opening_mm") or []
    opening = LineString(opening_segment)
    if room.is_empty or not room.is_valid or opening.is_empty:
        return {"status": "UNVERIFIED", "diagnostics": ["INVALID_ROOM_OR_OPENING_GEOMETRY"], "path_mm": [], "length_mm": None}
    threshold = opening.interpolate(opening.project(Point(endpoint)))
    room_target = (float(threshold.x), float(threshold.y))
    room_path = _direct_or_bend((float(endpoint[0]), float(endpoint[1])), room_target, room, occupied_routes)
    if room_path is None:
        return {"status": "INVALID", "diagnostics": ["ROOM_EXIT_BLOCKED_BY_OCCUPIED_ROUTE"], "path_mm": [], "length_mm": None}
    if corridor_polygon is None:
        return {"status": "UNVERIFIED", "diagnostics": ["CORRIDOR_POLYGON_REQUIRED", "DOOR_PASSAGE_AUTHORIZATION_REQUIRED"], "path_mm": [list(p) for p in room_path], "length_mm": round(LineString(room_path).length, 3), "corridor_path_mm": []}
    corridor = _geometry(corridor_polygon)
    if not corridor.is_valid or not corridor.covers(opening):
        return {"status": "UNVERIFIED", "diagnostics": ["OPENING_NOT_COVERED_BY_CORRIDOR_MODEL"], "path_mm": [list(p) for p in room_path], "length_mm": round(LineString(room_path).length, 3), "corridor_path_mm": []}
    corridor_target = (float(opening.centroid.x), float(opening.centroid.y))
    corridor_path = _direct_or_bend(room_target, corridor_target, corridor, occupied_routes)
    if corridor_path is None:
        return {"status": "INVALID", "diagnostics": ["CORRIDOR_ROUTE_BLOCKED_OR_TOO_NARROW"], "path_mm": [list(p) for p in room_path], "length_mm": round(LineString(room_path).length, 3), "corridor_path_mm": []}
    merged = room_path[:-1] + corridor_path
    return {"status": "GEOMETRIC_PREVIEW_UNVERIFIED_AUTHORITY", "diagnostics": ["DOOR_PASSAGE_AUTHORIZATION_REQUIRED", "MANIFOLD_CONNECTION_UNVERIFIED"], "path_mm": [list(p) for p in merged], "corridor_path_mm": [list(p) for p in corridor_path], "room_length_mm": round(LineString(room_path).length, 3), "corridor_length_mm": round(LineString(corridor_path).length, 3), "length_mm": round(LineString(merged).length, 3)}


def route_building_system(
    circuits: Iterable[dict[str, object]],
    *,
    openings: dict[str, dict[str, object]] | None = None,
    corridor_polygons: dict[str, Iterable[tuple[float, float]]] | None = None,
    vertical_transit_mm: dict[str, float] | None = None,
    manifold_options: tuple[str, ...] = ("SINGLE_MANIFOLD", "TWO_MANIFOLDS"),
    collector_point: tuple[float, float] | None = None,
    collector_polygon: Iterable[tuple[float, float]] | None = None,
    collector_transition: dict[str, object] | None = None,
    occupied_clearance_mm: float = 16.0,
    pair_search_budget: int | None = None,
) -> dict[str, object]:
    circuits = list(circuits)
    openings = openings or {}
    corridor_polygons = corridor_polygons or {}
    vertical_transit_mm = vertical_transit_mm or {}
    rows: list[dict[str, object]] = []
    occupied_routes_global: list[tuple[str, Iterable[tuple[float, float]]]] = []
    body_axes_global = [(str(item.get("circuit_id", "unknown")), str(item.get("floor", "")), item.get("route_mm") or []) for item in circuits]
    for circuit in circuits:
        cid = str(circuit.get("circuit_id", "unknown"))
        opening = openings.get(cid) or openings.get(str(circuit.get("room_id", "")))
        room = circuit.get("room_boundary_mm") or []
        route = circuit.get("route_mm") or []
        base = float(circuit.get("INTERNAL_PIPE_LENGTH", circuit.get("length_mm", 0)) or 0)
        if not opening or len(route) < 2:
            rows.append({"circuit_id": cid, "status": "UNVERIFIED", "MANIFOLD_CONNECTED": "UNVERIFIED", "TOTAL_CIRCUIT_LENGTH": None, "diagnostics": ["OPENING_SEGMENT_NOT_SELECTED"]})
            continue
        seg = opening
        exits = []
        # Every room BODY is an obstacle from the outset, including circuits
        # whose supply/return has not yet been routed. Exclude only this
        # circuit's own BODY so its leads can meet their terminals.
        floor = str(circuit.get("floor", ""))
        occupied = [path for occupied_floor, path in occupied_routes_global if occupied_floor == floor] + [body for other_id, other_floor, body in body_axes_global if other_id != cid and other_floor == floor and len(body) >= 2]
        corridor = corridor_polygons.get(str(circuit.get("floor", "")))
        # Solve supply first, then solve return against the actual supply
        # centreline.  A partially built or failed pair is never reserved for
        # subsequent circuits.  This prevents one blocked return from
        # poisoning the remaining shared corridor search.
        if collector_point is not None and corridor is not None:
            transition = circuit.get("collector_transition") or collector_transition
            supply_candidates = []
            for endpoint_index in (0, 1):
                candidate_opening = dict(seg) if isinstance(seg, dict) else seg
                if isinstance(candidate_opening, dict):
                    candidate_opening["corridor_endpoint_index"] = endpoint_index
                for collector_index in (0, 1):
                    candidate_transition = dict(transition) if isinstance(transition, dict) else transition
                    if isinstance(candidate_transition, dict):
                        candidate_transition["collector_endpoint_index"] = collector_index
                    supply_candidates.append((candidate_opening, candidate_transition, route_endpoint_to_collector(tuple(route[0]), candidate_opening, room, corridor, collector_point, collector_polygon, occupied_routes=occupied, clearance_mm=occupied_clearance_mm, collector_transition=candidate_transition)))
            pair = None
            pair_attempts = 0
            for candidate_opening, candidate_transition, candidate_supply in supply_candidates:
                if candidate_supply.get("status") != "GEOMETRIC_PREVIEW_UNVERIFIED_AUTHORITY":
                    continue
                return_occupied = occupied + [candidate_supply["path_mm"]]
                for endpoint_index in (0, 1):
                    return_opening = dict(seg) if isinstance(seg, dict) else seg
                    if isinstance(return_opening, dict):
                        return_opening["corridor_endpoint_index"] = endpoint_index
                    for collector_corridor_index in (0, 1):
                        for collector_room_index in (0, 1):
                            return_transition = dict(transition) if isinstance(transition, dict) else transition
                            if isinstance(return_transition, dict):
                                return_transition["collector_corridor_index"] = collector_corridor_index
                                return_transition["collector_room_index"] = collector_room_index
                            candidate_return = route_endpoint_to_collector(tuple(route[-1]), return_opening, room, corridor, collector_point, collector_polygon, occupied_routes=return_occupied, clearance_mm=occupied_clearance_mm, collector_transition=return_transition)
                            pair_attempts += 1
                            if candidate_return.get("status") == "GEOMETRIC_PREVIEW_UNVERIFIED_AUTHORITY":
                                pair = (candidate_supply, candidate_return)
                                break
                            if pair_search_budget is not None and pair_attempts >= pair_search_budget:
                                break
                    if pair:
                        break
                    if pair_search_budget is not None and pair_attempts >= pair_search_budget:
                        break
                if pair:
                    break
                if pair_search_budget is not None and pair_attempts >= pair_search_budget:
                    break
            if pair:
                supply, return_ = pair
            else:
                supply = next((candidate for _, _, candidate in supply_candidates if candidate.get("status") == "GEOMETRIC_PREVIEW_UNVERIFIED_AUTHORITY"), supply_candidates[0][2])
                return_ = route_endpoint_to_collector(tuple(route[-1]), seg, room, corridor, collector_point, collector_polygon, occupied_routes=occupied + ([supply.get("path_mm")] if supply.get("path_mm") else []), clearance_mm=occupied_clearance_mm, collector_transition=transition)
        else:
            supply = route_endpoint_to_opening(tuple(route[0]), seg, room, corridor, occupied_routes=occupied, clearance_mm=occupied_clearance_mm)
            # Legacy endpoint-only callers do not yet have a finite transition
            # model, so preserve their established room-boundary preview
            # semantics.  Building-level collector routing uses the stricter
            # pair occupancy branch above.
            return_ = route_endpoint_to_opening(tuple(route[-1]), seg, room, corridor, occupied_routes=occupied, clearance_mm=occupied_clearance_mm)
        exits = [("SUPPLY", supply), ("RETURN", return_)]
        valid = all(item[1]["status"] == "GEOMETRIC_PREVIEW_UNVERIFIED_AUTHORITY" for item in exits)
        if valid:
            occupied_routes_global.extend((floor, value["path_mm"]) for _, value in exits if value.get("path_mm"))
        supply = float(exits[0][1].get("length_mm") or 0)
        ret = float(exits[1][1].get("length_mm") or 0)
        vertical = float(vertical_transit_mm.get(str(circuit.get("floor", "")), 0))
        supply_total = float(exits[0][1].get("length_mm") or 0)
        return_total = float(exits[1][1].get("length_mm") or 0)
        rows.append({"circuit_id": cid, "status": "GEOMETRIC_PREVIEW_UNVERIFIED_AUTHORITY" if valid else "UNVERIFIED", "MANIFOLD_CONNECTED": "UNVERIFIED", "INTERNAL_PIPE_LENGTH": round(base, 3), "IN_ROOM_SUPPLY_LENGTH": round(float(exits[0][1].get("room_length_mm") or 0), 3), "IN_ROOM_RETURN_LENGTH": round(float(exits[1][1].get("room_length_mm") or 0), 3), "IN_ROOM_CONNECTION_LENGTH": round(float(exits[0][1].get("room_length_mm") or 0) + float(exits[1][1].get("room_length_mm") or 0), 3), "CORRIDOR_SUPPLY_LENGTH": round(float(exits[0][1].get("corridor_length_mm") or 0), 3), "CORRIDOR_RETURN_LENGTH": round(float(exits[1][1].get("corridor_length_mm") or 0), 3), "VERTICAL_SUPPLY_LENGTH": round(vertical, 3), "VERTICAL_RETURN_LENGTH": round(vertical, 3), "TOTAL_CIRCUIT_LENGTH": round(base + supply_total + return_total + 2 * vertical, 3) if valid else None, "exits": {name: value for name, value in exits}, "diagnostics": sorted({d for _, value in exits for d in value.get("diagnostics", [])})})
    joint_occupancy = audit_joint_occupancy(circuits, rows)
    corridor_status = joint_occupancy["status"] if corridor_polygons else "UNVERIFIED_WITHOUT_CORRIDOR_SOURCE_POLYGON"
    return {"status": "GEOMETRIC_PREVIEW_UNVERIFIED_AUTHORITY", "manifold_options": [{"id": option, "MANIFOLD_CONNECTED": "UNVERIFIED"} for option in manifold_options], "circuits": rows, "joint_occupancy": joint_occupancy, "corridor_validation": {"status": corridor_status, "shared_route_collisions_checked": joint_occupancy["xy_check_complete"], "occupied_route_clearance_mm": occupied_clearance_mm}}


def audit_joint_occupancy(circuits, rows, *, minimum_axis_clearance_mm: float = 25.0) -> dict[str, object]:
    """Audit the whole XY layout, including every BODY and both transit legs.

    XY separation is only a screening check. It cannot establish 3D clearance,
    valid wall crossings, collector ports, or a complete physical circuit.
    """
    rows_by_id = {str(row.get("circuit_id")): row for row in rows}
    axes = []
    missing = []
    for circuit in circuits:
        cid = str(circuit.get("circuit_id", "unknown"))
        floor = str(circuit.get("floor", ""))
        body = circuit.get("route_mm") or []
        if len(body) >= 2:
            axes.append((cid, floor, "BODY", LineString(body)))
        else:
            missing.append({"circuit_id": cid, "part": "BODY", "reason": "CENTERLINE_MISSING"})
        exits = rows_by_id.get(cid, {}).get("exits") or {}
        for role in ("SUPPLY", "RETURN"):
            leg = exits.get(role) or {}
            path = leg.get("path_mm") or []
            if leg.get("status") != "GEOMETRIC_PREVIEW_UNVERIFIED_AUTHORITY" or len(path) < 2:
                missing.append({"circuit_id": cid, "part": role, "reason": "TRANSIT_NOT_MATERIALIZED"})
                continue
            rounded = build_rounded_centerline(path, bend_radius_mm=80.0)
            if not rounded.valid or len(rounded.points) < 2:
                missing.append({"circuit_id": cid, "part": role, "reason": "ROUNDED_TRANSIT_INVALID"})
                continue
            axes.append((cid, floor, role, LineString(rounded.points)))
    conflicts = []
    # A sampled R80 quarter-arc with 12 segments can differ from the true arc
    # by <0.172 mm. Reserve 0.35 mm for both sides of a pair.
    sampling_margin_mm = 0.35
    for index, (cid_a, floor_a, part_a, line_a) in enumerate(axes):
        for cid_b, floor_b, part_b, line_b in axes[index + 1:]:
            if cid_a == cid_b or floor_a != floor_b:
                continue  # Own BODY/lead joints require a separate topology audit.
            distance = line_a.distance(line_b)
            if distance < minimum_axis_clearance_mm + sampling_margin_mm:
                conflicts.append({"a": {"circuit_id": cid_a, "part": part_a}, "b": {"circuit_id": cid_b, "part": part_b}, "sampled_axis_distance_mm": round(distance, 3)})
    status = "POTENTIAL_XY_CONFLICTS" if conflicts else ("INCOMPLETE_LAYOUT" if missing else "NO_XY_CONFLICTS_SAMPLED_3D_UNVERIFIED")
    return {"status": status, "xy_check_complete": not missing, "minimum_axis_clearance_mm": minimum_axis_clearance_mm, "axis_count": len(axes), "missing_parts": missing, "potential_conflicts": conflicts, "same_circuit_joint_clearance": "UNVERIFIED", "physical_3d_clearance": "UNVERIFIED"}


__all__ = ["build_door_transition", "route_endpoint_to_opening", "route_endpoint_to_collector", "route_building_system", "audit_joint_occupancy"]

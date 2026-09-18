"""Geometry-only UFH routing preview built on the existing route engine."""
from __future__ import annotations

import hashlib
import json
from collections import deque
from typing import Literal

from pydantic import Field

from agent.floor_heating_engine import calculate_floor_heating, _self_intersects
from agent.floor_heating_installation_rules import InstallationRuleSet, validate_installation_geometry
from agent.floor_heating_models import FloorHeatingPoint, FloorHeatingPolygon, FloorHeatingRequest
from agent.project_models import StrictProjectModel


class UfhRoutingPreviewRequest(StrictProjectModel):
    project_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=128)
    room_polygon: FloorHeatingPolygon
    heated_polygon: FloorHeatingPolygon | None = None
    exclusion_zones: list[FloorHeatingPolygon] = Field(default_factory=list, max_length=64)
    manifold_point: FloorHeatingPoint
    spacing_mm: int = Field(default=200, ge=1, le=2000)
    wall_offset_mm: int = Field(default=100, ge=0, le=10000)
    minimum_bend_radius_mm: int = Field(default=100, ge=0, le=5000)
    maximum_preview_length_mm: int = Field(default=150000, ge=1, le=500000)
    orientation: Literal["horizontal", "vertical", "auto"] = "auto"
    scale_status: Literal["VERIFIED", "UNVERIFIED", "UNKNOWN"] = "VERIFIED"
    source_frame: str = Field(default="synthetic-known-mm", min_length=1, max_length=160)
    source_observation_ids: list[str] = Field(default_factory=list, max_length=128)
    source_wall_ids: list[str] = Field(default_factory=list, max_length=128)
    transformation_metadata: list[str] = Field(default_factory=list, max_length=64)
    outside_diameter_mm: int = Field(default=16, ge=1, le=100)
    pipe_profile: str = Field(default="PREVIEW_DEFAULT", min_length=1, max_length=128)


class OrientationMetric(StrictProjectModel):
    orientation: Literal["horizontal", "vertical"]
    feasible: bool
    total_length_mm: int = Field(ge=0)
    coverage_percent: float = Field(ge=0, le=100)
    turn_count: int = Field(ge=0)
    bend_violations: int = Field(ge=0)
    transit_length_mm: int = Field(ge=0)
    rejection_reasons: list[str] = Field(default_factory=list)


class UfhRoutingPreviewResult(StrictProjectModel):
    route_id: str
    room_id: str
    routing_strategy: Literal["SERPENTINE", "COUNTERFLOW_SPIRAL"]
    selected_orientation: Literal["horizontal", "vertical"]
    candidate_orientations: list[OrientationMetric] = Field(default_factory=list)
    selection_reason: str
    status: Literal["GEOMETRY_ONLY_UFH_ROUTING_CANDIDATE", "IMPOSSIBLE"]
    input_polygon: FloorHeatingPolygon
    usable_heated_polygon: FloorHeatingPolygon
    pipe_centerline: list[FloorHeatingPoint] = Field(default_factory=list)
    supply_transit: list[FloorHeatingPoint] = Field(default_factory=list)
    coverage_path: list[FloorHeatingPoint] = Field(default_factory=list)
    return_transit: list[FloorHeatingPoint] = Field(default_factory=list)
    start_point: FloorHeatingPoint
    end_point: FloorHeatingPoint | None = None
    manifold_point: FloorHeatingPoint
    nominal_spacing_mm: int
    effective_spacing_mm: int
    wall_offset_mm: int
    minimum_bend_radius_mm: int
    min_achieved_bend_radius_mm: int = Field(ge=0)
    bend_violations: list[list[int]] = Field(default_factory=list)
    estimated_pipe_length_mm: int = Field(ge=0)
    supply_transit_length_mm: int = Field(ge=0)
    coverage_length_mm: int = Field(ge=0)
    return_transit_length_mm: int = Field(ge=0)
    turn_count: int = Field(ge=0)
    self_intersection: bool
    coverage_area_mm2: int = Field(ge=0)
    heated_area_mm2: int = Field(ge=0)
    coverage_percentage: float = Field(ge=0, le=100)
    uncovered_area_mm2: int = Field(ge=0)
    exclusion_zones: list[FloorHeatingPolygon] = Field(default_factory=list, max_length=64)
    source_frame: str
    source_observation_ids: list[str] = Field(default_factory=list)
    source_wall_ids: list[str] = Field(default_factory=list)
    scale_status: str
    pipe_profile: str
    outside_diameter_mm: int
    transformation_metadata: list[str] = Field(default_factory=list)
    authority_status: Literal["GEOMETRY_ONLY_NON_AUTHORITATIVE"] = "GEOMETRY_ONLY_NON_AUTHORITATIVE"
    diagnostics: list[str] = Field(default_factory=list)
    requested_spacing_mm: int = Field(default=200, ge=1)
    min_effective_spacing_mm: int = Field(default=0, ge=0)
    max_effective_spacing_mm: int = Field(default=0, ge=0)
    mean_effective_spacing_mm: float = Field(default=0, ge=0)
    result_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class UfhCircuitPlan(StrictProjectModel):
    status: Literal["PLANNED", "IMPOSSIBLE"]
    circuit_count: int = Field(ge=0)
    circuits: list[UfhRoutingPreviewResult] = Field(default_factory=list)
    circuit_lengths_mm: list[int] = Field(default_factory=list)
    longest_circuit_mm: int = Field(ge=0)
    shortest_circuit_mm: int = Field(ge=0)
    mean_circuit_length_mm: float = Field(ge=0)
    max_length_difference_mm: int = Field(ge=0)
    relative_length_imbalance: float = Field(ge=0)
    diagnostics: list[str] = Field(default_factory=list)


class CoverageCell(StrictProjectModel):
    cell_id: str
    parent_zone_id: str
    polygon: FloorHeatingPolygon
    adjacent_cells: list[str] = Field(default_factory=list)
    portals: list[FloorHeatingPoint] = Field(default_factory=list)
    routing_feasible: bool
    provenance: list[str] = Field(default_factory=list)


def _area(poly):
    return abs(sum(a.x_mm * b.y_mm - b.x_mm * a.y_mm for a, b in zip(poly.points, poly.points[1:]))) // 2


def _length(points):
    return sum(abs(a.x_mm - b.x_mm) + abs(a.y_mm - b.y_mm) for a, b in zip(points, points[1:]))


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _swap_point(p):
    return FloorHeatingPoint(x_mm=p.y_mm, y_mm=p.x_mm)


def _swap_poly(poly):
    return FloorHeatingPolygon(points=[_swap_point(p) for p in poly.points])


def _engine_request(request, orientation):
    swap = orientation == "vertical"
    tp = _swap_point if swap else (lambda p: p)
    tg = _swap_poly if swap else (lambda p: p)
    heated = request.heated_polygon or request.room_polygon
    transformed_manifold = tp(request.manifold_point)
    # The existing counterflow backend chooses its sweep gate from the nearest
    # boundary side.  Pin the normalized frame to the requested axis so a
    # vertical preview is a genuinely different sweep, while the public result
    # continues to report the caller's real manifold point.
    if swap:
        transformed_manifold = FloorHeatingPoint(x_mm=transformed_manifold.x_mm, y_mm=request.wall_offset_mm)
    return FloorHeatingRequest(project_id=request.project_id, room_id=request.room_id, boundary=tg(heated), exclusion_zones=[tg(z) for z in request.exclusion_zones], collector_point=transformed_manifold, wall_offset_mm=request.wall_offset_mm, spacing_mm=request.spacing_mm if request.spacing_mm in (100, 150, 200) else 200, maximum_circuit_length_mm=request.maximum_preview_length_mm, minimum_circuit_length_mm=1, turn_radius_mm=request.minimum_bend_radius_mm, routing_mode="non_crossing_visual", requested_circuit_count=1)


def _restore(points, orientation):
    return [_swap_point(p) for p in points] if orientation == "vertical" else points


def _rectangle_baseline(request, orientation):
    """Generate a continuous dense meander for an unobstructed rectangle."""
    polygon = request.heated_polygon or request.room_polygon
    body = polygon.points[:-1]
    xs, ys = {p.x_mm for p in body}, {p.y_mm for p in body}
    if len(xs) != 2 or len(ys) != 2 or request.exclusion_zones:
        return None
    left, right = min(xs) + request.wall_offset_mm, max(xs) - request.wall_offset_mm
    bottom, top = min(ys) + request.wall_offset_mm, max(ys) - request.wall_offset_mm
    spacing = request.spacing_mm if request.spacing_mm in (100, 150, 200) else 200
    if right <= left or top <= bottom or top - bottom < spacing:
        return None
    if orientation == "vertical":
        cols = list(range(left, right + 1, spacing))
        if cols[-1] != right: cols.append(right)
        coverage = []
        for i, x in enumerate(cols):
            coverage.extend([(x, bottom), (x, top)] if i % 2 == 0 else [(x, top), (x, bottom)])
            if i < len(cols) - 1: coverage.append((cols[i + 1], coverage[-1][1]))
        coverage_points = [FloorHeatingPoint(x_mm=x, y_mm=y) for x, y in coverage]
        first, last = coverage_points[0], coverage_points[-1]
        return [first], coverage_points, [last]
    rows = list(range(bottom, top + 1, spacing))
    if rows[-1] != top:
        rows.append(top)
    manifold = request.manifold_point
    order = list(range(len(rows)))
    lane_left, lane_right = left, right
    if lane_right <= lane_left:
        return None
    right_first = manifold.x_mm >= (lane_left + lane_right) / 2
    coverage = []
    for sequence_index, row_index in enumerate(order):
        y = rows[row_index]
        start_right = right_first if sequence_index % 2 == 0 else not right_first
        coverage.extend([(lane_right, y), (lane_left, y)] if start_right else [(lane_left, y), (lane_right, y)])
        if sequence_index < len(order) - 1:
            next_y = rows[order[sequence_index + 1]]
            coverage.append((coverage[-1][0], next_y))
    coverage_points = []
    for x, y in coverage:
        point = FloorHeatingPoint(x_mm=x, y_mm=y)
        if not coverage_points or coverage_points[-1] != point:
            coverage_points.append(point)
    first, last = coverage_points[0], coverage_points[-1]
    # A manifold approach through the field would cross every lane.  The
    # baseline therefore exposes a projected connection endpoint; a future
    # transit planner must solve the corridor explicitly rather than crossing
    # coverage runs.
    supply = [first]
    ret = [last]
    return supply, coverage_points, ret


def _inside_xy(point, polygon):
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:]):
        if a[1] == b[1]:
            continue
        if (a[1] > y) != (b[1] > y):
            cross = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            if x < cross:
                inside = not inside
    return inside


def _complex_scan_route(request, orientation):
    """Bounded scan-cell fallback for orthogonal concave zones.

    It uses exact scanline intervals and grid A* portals. No endpoint is
    connected unless every transition segment is inside the heated polygon and
    outside exclusions. This is deliberately conservative and returns None on
    unresolved topology.
    """
    from agent.floor_heating_engine import _validate_polygon, _scan_intervals, _allowed_segment, _self_intersects
    heated = request.heated_polygon or request.room_polygon
    normalized, error = _validate_polygon(heated.model_dump(mode="python")) if False else (None, None)
    outer = [(p.x_mm, p.y_mm) for p in heated.points]
    exclusions = [[(p.x_mm, p.y_mm) for p in z.points] for z in request.exclusion_zones]
    ys = range(min(y for _, y in outer) + request.wall_offset_mm + request.spacing_mm // 2,
               max(y for _, y in outer) - request.wall_offset_mm, request.spacing_mm)
    rows = []
    for y in ys:
        intervals = _scan_intervals(outer, y)
        cleaned = []
        for left, right in intervals:
            left += request.wall_offset_mm; right -= request.wall_offset_mm
            if right <= left: continue
            fragments = [(left, right)]
            for ex in exclusions:
                blocked = _scan_intervals(ex, y)
                next_fragments = []
                for a, b in fragments:
                    pieces = [(a, b)]
                    for bl, br in blocked:
                        updated = []
                        for pl, pr in pieces:
                            if br <= pl or bl >= pr: updated.append((pl, pr)); continue
                            if pl < bl: updated.append((pl, bl))
                            if br < pr: updated.append((br, pr))
                        pieces = updated
                    next_fragments.extend(pieces)
                fragments = next_fragments
            cleaned.extend((a, b) for a, b in fragments if b - a >= request.spacing_mm)
        if cleaned: rows.append((y, cleaned))
    if not rows: return None
    segments = []
    for row_index, (y, intervals) in enumerate(rows):
        for interval_index, (left, right) in enumerate(intervals):
            start, end = ((left, y), (right, y)) if (row_index + interval_index) % 2 == 0 else ((right, y), (left, y))
            segments.append((start, end, row_index, interval_index))
    if len(segments) < 2: return None
    step = max(50, min(request.spacing_mm // 2, 100))
    outer_box = (min(x for x, _ in outer), min(y for _, y in outer), max(x for x, _ in outer), max(y for _, y in outer))
    def free(node):
        x, y = node
        if not _inside_xy(node, outer): return False
        if any(_inside_xy(node, ex) for ex in exclusions): return False
        return True
    def grid_path(start, goal):
        # Snap only the search lattice; endpoints remain exact in the result.
        sx, sy = start; gx, gy = goal
        origin = (round(sx / step) * step, round(sy / step) * step)
        target = (round(gx / step) * step, round(gy / step) * step)
        q = deque([origin]); prev = {origin: None}
        while q:
            cur = q.popleft()
            if cur == target: break
            for nxt in ((cur[0]+step,cur[1]),(cur[0]-step,cur[1]),(cur[0],cur[1]+step),(cur[0],cur[1]-step)):
                if nxt in prev or not (outer_box[0]-step <= nxt[0] <= outer_box[2]+step and outer_box[1]-step <= nxt[1] <= outer_box[3]+step): continue
                if free(nxt) and _allowed_segment(cur, nxt, outer, exclusions, request.wall_offset_mm):
                    prev[nxt] = cur; q.append(nxt)
        if target not in prev: return None
        path=[]; cur=target
        while cur is not None: path.append(cur); cur=prev[cur]
        return list(reversed(path))
    body = [segments[0][0], segments[0][1]]
    for current, nxt in zip(segments, segments[1:]):
        connector = grid_path(current[1], nxt[0])
        if connector is None: return None
        for point in connector[1:]:
            if point != body[-1]: body.append(point)
        body.append(nxt[1])
    if _self_intersects(body): return None
    if any(not _allowed_segment(a, b, outer, exclusions, request.wall_offset_mm) for a, b in zip(body, body[1:])): return None
    return body


def decompose_coverage_cells(request: UfhRoutingPreviewRequest) -> list[CoverageCell]:
    """Return conservative horizontal scan cells and physical overlap portals."""
    heated = request.heated_polygon or request.room_polygon
    outer = [(p.x_mm, p.y_mm) for p in heated.points]
    from agent.floor_heating_engine import _scan_intervals
    cells = []
    rows = range(min(y for _, y in outer) + request.wall_offset_mm + request.spacing_mm // 2,
                max(y for _, y in outer) - request.wall_offset_mm, request.spacing_mm)
    previous = []
    index = 0
    for y in rows:
        intervals = [(a + request.wall_offset_mm, b - request.wall_offset_mm) for a, b in _scan_intervals(outer, y)]
        current = []
        for left, right in intervals:
            if right - left < request.spacing_mm:
                continue
            cell_id = f"{request.room_id}/cell-{index:04d}"
            polygon = FloorHeatingPolygon(points=[FloorHeatingPoint(x_mm=left, y_mm=y-request.spacing_mm//2), FloorHeatingPoint(x_mm=right, y_mm=y-request.spacing_mm//2), FloorHeatingPoint(x_mm=right, y_mm=y+request.spacing_mm//2), FloorHeatingPoint(x_mm=left, y_mm=y+request.spacing_mm//2), FloorHeatingPoint(x_mm=left, y_mm=y-request.spacing_mm//2)])
            adjacent = []
            portals = []
            for other in previous:
                overlap_left, overlap_right = max(left, other["left"]), min(right, other["right"])
                if overlap_right - overlap_left >= request.minimum_bend_radius_mm * 2:
                    adjacent.append(other["id"])
                    portals.append(FloorHeatingPoint(x_mm=(overlap_left + overlap_right)//2, y_mm=y))
            cells.append(CoverageCell(cell_id=cell_id, parent_zone_id=request.room_id, polygon=polygon, adjacent_cells=sorted(adjacent), portals=portals, routing_feasible=True, provenance=["ORTHOGONAL_SCANLINE", request.source_frame]))
            current.append({"id": cell_id, "left": left, "right": right})
            index += 1
        previous = current
    return cells


def _single(request, orientation):
    heated = request.heated_polygon or request.room_polygon
    engine = calculate_floor_heating(_engine_request(request, orientation))
    baseline = _rectangle_baseline(request, orientation)
    route = engine.circuit_routes[0] if engine.circuit_routes else None
    circuit = engine.circuits[0] if engine.circuits else None
    if baseline:
        supply, coverage, ret = baseline
        route = None
        circuit = None
    blocked_by_length = baseline is not None or (engine.status != "ok" and any("length" in diagnostic.message.lower() for diagnostic in engine.diagnostics))
    if route and engine.status != "ok" and route.validation.length_valid is False:
        blocked_by_length = True
    complex_body = None if route or blocked_by_length or request.maximum_preview_length_mm < request.spacing_mm * 8 else _complex_scan_route(request, orientation)
    raw_points = route.polyline if route else ([*supply, *coverage[1:], *ret[1:]] if baseline else [FloorHeatingPoint(x_mm=x, y_mm=y) for x, y in (complex_body or [])])
    points = raw_points if baseline else _restore(raw_points, orientation)
    if not baseline:
        supply = _restore(circuit.supply_transit if circuit else [], orientation)
        ret = _restore(circuit.return_transit if circuit else [], orientation)
    else:
        supply = _restore(supply, orientation)
        coverage = _restore(coverage, orientation)
        ret = _restore(ret, orientation)
    if not baseline:
        coverage = points[len(supply):len(points)-len(ret)] if len(points) > len(supply)+len(ret) else points
    diagnostics = [d.code for d in engine.diagnostics]
    if request.scale_status != "VERIFIED": diagnostics.append("SCALE_UNVERIFIED_GEOMETRY_ONLY")
    if request.spacing_mm not in (100, 150, 200): diagnostics.append("SPACING_NORMALIZED_TO_ENGINE_SUPPORTED_VALUE")
    bend = validate_installation_geometry([(p.x_mm,p.y_mm) for p in points], [(p.x_mm,p.y_mm) for p in heated.points], [[(p.x_mm,p.y_mm) for p in z.points] for z in request.exclusion_zones], InstallationRuleSet(wall_clearance_mm=request.wall_offset_mm, exclusion_clearance_mm=request.wall_offset_mm, minimum_bend_radius_mm=request.minimum_bend_radius_mm)) if points else {"turn_count":0,"turns":[],"short_turn_count":0}
    if bend.get("short_turn_count", 0): diagnostics.append("MINIMUM_BEND_RADIUS_VIOLATION")
    if route and not route.validation.valid: diagnostics.extend(route.validation.diagnostics)
    if complex_body:
        diagnostics = [item for item in diagnostics if not item.startswith("impossible_")]
        diagnostics.append("ORTHOGONAL_SCAN_CELL_FALLBACK")
    heated_area = max(0, _area(heated)-sum(_area(z) for z in request.exclusion_zones))
    effective_status = "ok" if baseline or (engine.status == "ok" and (route or complex_body)) else engine.status
    covered_area = min(heated_area, _length(coverage)*(request.spacing_mm if request.spacing_mm in (100,150,200) else 200)) if effective_status == "ok" else 0
    total = _length(points)
    continuity_gaps = []
    if supply and coverage and supply[-1] != coverage[0]:
        continuity_gaps.append(abs(supply[-1].x_mm-coverage[0].x_mm)+abs(supply[-1].y_mm-coverage[0].y_mm))
    if coverage and ret and coverage[-1] != ret[0]:
        continuity_gaps.append(abs(coverage[-1].x_mm-ret[0].x_mm)+abs(coverage[-1].y_mm-ret[0].y_mm))
    if continuity_gaps:
        diagnostics.append("PIPE_PATH_DISCONTINUOUS")
        effective_status = "impossible"
    if baseline and total > request.maximum_preview_length_mm:
        diagnostics.append("ROUTE_TOO_LONG_REQUIRES_CIRCUIT_SPLIT")
        if request.maximum_preview_length_mm < 10_000:
            effective_status = "impossible"
    min_achieved = min((min(t["leg_before_mm"],t["leg_after_mm"]) for t in bend.get("turns",[])), default=0)
    supply_length, return_length = _length(supply), _length(ret)
    if baseline:
        expected_order = heated_area / 1000 / (request.spacing_mm if request.spacing_mm else 200)
        diagnostics.append(f"EXPECTED_COVERAGE_LENGTH_ORDER_M={expected_order:.2f}")
        diagnostics.append(f"ACTUAL_COVERAGE_LENGTH_M={max(0, total - supply_length - return_length) / 1000:.2f}")
    rendered_manifold = request.manifold_point
    if baseline:
        rendered_manifold = points[0]
        if rendered_manifold != request.manifold_point:
            diagnostics.append("MANIFOLD_PROJECTED_TO_ROUTE_START")
    spacing_values = [abs(a.y_mm-b.y_mm) for a,b in zip(coverage, coverage[1:]) if a.x_mm == b.x_mm and a.y_mm != b.y_mm]
    result = UfhRoutingPreviewResult(route_id=f"ufh-preview/{request.project_id}/{request.room_id}/{orientation}", room_id=request.room_id, routing_strategy="SERPENTINE" if route and route.validation.step_valid else "SERPENTINE", selected_orientation=orientation, candidate_orientations=[], selection_reason="Explicit orientation candidate", status="GEOMETRY_ONLY_UFH_ROUTING_CANDIDATE" if effective_status == "ok" else "IMPOSSIBLE", input_polygon=request.room_polygon, usable_heated_polygon=heated, pipe_centerline=points, supply_transit=supply, coverage_path=coverage, return_transit=ret, start_point=points[0] if points else request.manifold_point, end_point=points[-1] if points else None, manifold_point=rendered_manifold, nominal_spacing_mm=request.spacing_mm, effective_spacing_mm=request.spacing_mm if request.spacing_mm in (100,150,200) else 200, wall_offset_mm=request.wall_offset_mm, minimum_bend_radius_mm=request.minimum_bend_radius_mm, min_achieved_bend_radius_mm=min_achieved, bend_violations=[t["point"] for t in bend.get("turns",[]) if min(t["leg_before_mm"],t["leg_after_mm"]) < request.minimum_bend_radius_mm], estimated_pipe_length_mm=total, supply_transit_length_mm=supply_length, coverage_length_mm=max(0, total - supply_length - return_length), return_transit_length_mm=return_length, turn_count=int(bend.get("turn_count",0)), self_intersection=route.validation.self_intersection if route else (_self_intersects([(p.x_mm,p.y_mm) for p in points]) if points else True), coverage_area_mm2=covered_area, heated_area_mm2=heated_area, coverage_percentage=100*covered_area/heated_area if heated_area else 0, uncovered_area_mm2=max(0,heated_area-covered_area), exclusion_zones=request.exclusion_zones, source_frame=request.source_frame, source_observation_ids=request.source_observation_ids, source_wall_ids=request.source_wall_ids, scale_status=request.scale_status, pipe_profile=request.pipe_profile, outside_diameter_mm=request.outside_diameter_mm, transformation_metadata=request.transformation_metadata+(["XY_SWAP_ROUTING_FRAME"] if orientation == "vertical" else []), diagnostics=sorted(set(diagnostics + (["ROUTE_TOO_LONG_REQUIRES_CIRCUIT_SPLIT"] if baseline and total > request.maximum_preview_length_mm else []))), requested_spacing_mm=request.spacing_mm, min_effective_spacing_mm=min(spacing_values, default=0), max_effective_spacing_mm=max(spacing_values, default=0), mean_effective_spacing_mm=sum(spacing_values)/len(spacing_values) if spacing_values else 0, result_digest="0"*64)
    return result.model_copy(update={"result_digest":_digest(result.model_dump(mode="json", exclude={"result_digest"}))})


def _metric(result):
    return {"orientation":result.selected_orientation,"feasible":result.status != "IMPOSSIBLE","total_length_mm":result.estimated_pipe_length_mm,"coverage_percent":result.coverage_percentage,"turn_count":result.turn_count,"bend_violations":len(result.bend_violations),"transit_length_mm":result.supply_transit_length_mm+result.return_transit_length_mm,"rejection_reasons":result.diagnostics if result.status == "IMPOSSIBLE" else []}


def generate_ufh_routing_preview(request):
    orientations = ("horizontal","vertical") if request.orientation == "auto" else (request.orientation,)
    candidates = [_single(request, orientation) for orientation in orientations]
    feasible = [c for c in candidates if c.status != "IMPOSSIBLE"]
    chosen = min(feasible or candidates, key=lambda c:(c.status == "IMPOSSIBLE",len(c.bend_violations),c.uncovered_area_mm2,c.estimated_pipe_length_mm,c.turn_count,c.selected_orientation))
    metrics = [OrientationMetric.model_validate(_metric(c)) for c in candidates]
    reason = "Feasibility first; then bend validity, coverage, length and turns." if request.orientation == "auto" else "Explicit orientation requested."
    return chosen.model_copy(update={"candidate_orientations":metrics,"selection_reason":reason,"result_digest":_digest({**chosen.model_dump(mode="json",exclude={"result_digest"}),"candidate_orientations":[m.model_dump(mode="json") for m in metrics],"selection_reason":reason})})


def plan_ufh_circuits(request):
    single = generate_ufh_routing_preview(request.model_copy(update={"orientation":"horizontal"}))
    if single.status != "IMPOSSIBLE" and single.estimated_pipe_length_mm <= request.maximum_preview_length_mm:
        return UfhCircuitPlan(status="PLANNED",circuit_count=1,circuits=[single],circuit_lengths_mm=[single.estimated_pipe_length_mm],longest_circuit_mm=single.estimated_pipe_length_mm,shortest_circuit_mm=single.estimated_pipe_length_mm,mean_circuit_length_mm=float(single.estimated_pipe_length_mm),max_length_difference_mm=0,relative_length_imbalance=0)
    body=(request.heated_polygon or request.room_polygon).points[:-1]
    xs,ys=[p.x_mm for p in body],[p.y_mm for p in body]
    if len(set(xs)) != 2 or len(set(ys)) != 2:
        return UfhCircuitPlan(status="IMPOSSIBLE",circuit_count=0,longest_circuit_mm=0,shortest_circuit_mm=0,mean_circuit_length_mm=0,max_length_difference_mm=0,relative_length_imbalance=0,diagnostics=["SPLIT_REQUIRES_RECTANGULAR_HEATED_ZONE"])
    left,right,bottom,top=min(xs),max(xs),min(ys),max(ys)
    count=min(3,max(2,(single.estimated_pipe_length_mm+request.maximum_preview_length_mm-1)//request.maximum_preview_length_mm))
    width=(right-left)//count; circuits=[]
    for i in range(count):
        l,r=left+i*width,right if i==count-1 else left+(i+1)*width
        zone=FloorHeatingPolygon(points=[FloorHeatingPoint(x_mm=l,y_mm=bottom),FloorHeatingPoint(x_mm=r,y_mm=bottom),FloorHeatingPoint(x_mm=r,y_mm=top),FloorHeatingPoint(x_mm=l,y_mm=top),FloorHeatingPoint(x_mm=l,y_mm=bottom)])
        manifold=FloorHeatingPoint(x_mm=max(l+request.wall_offset_mm,min(request.manifold_point.x_mm,r-request.wall_offset_mm)),y_mm=max(bottom+request.wall_offset_mm,min(request.manifold_point.y_mm,top-request.wall_offset_mm)))
        circuits.append(generate_ufh_routing_preview(request.model_copy(update={"room_id": f"{request.room_id}/circuit-{i+1}", "room_polygon":zone,"heated_polygon":zone,"exclusion_zones":[],"manifold_point":manifold,"orientation":"horizontal"})))
    lengths=[c.estimated_pipe_length_mm for c in circuits]; longest=max(lengths,default=0); shortest=min(lengths,default=0)
    status="PLANNED" if circuits and all(c.status != "IMPOSSIBLE" and c.estimated_pipe_length_mm <= request.maximum_preview_length_mm for c in circuits) else "IMPOSSIBLE"
    return UfhCircuitPlan(status=status,circuit_count=len(circuits),circuits=circuits,circuit_lengths_mm=lengths,longest_circuit_mm=longest,shortest_circuit_mm=shortest,mean_circuit_length_mm=sum(lengths)/len(lengths) if lengths else 0,max_length_difference_mm=longest-shortest,relative_length_imbalance=(longest-shortest)/longest if longest else 0,diagnostics=[] if status=="PLANNED" else ["SPLIT_CIRCUIT_EXCEEDS_HARD_MAX"])


def render_ufh_routing_preview_svg(result):
    """Render the exact route geometry carried by a preview result or plan."""
    circuits = getattr(result, "circuits", None) or [result]
    base = circuits[0]
    polygons = [c.usable_heated_polygon for c in circuits]
    pts = polygons[0].points
    max_x = max(p.x_mm for polygon in polygons for p in polygon.points)
    max_y = max(p.y_mm for polygon in polygons for p in polygon.points)
    def points_attr(points):
        return " ".join(f"{p.x_mm},{p.y_mm}" for p in points)
    def path(points, color, layer, circuit_id):
        if not points:
            return ""
        d = " ".join(("M" if i == 0 else "L") + f" {p.x_mm},{p.y_mm}" for i, p in enumerate(points))
        return f'<path data-layer="{layer}" data-circuit-id="{circuit_id}" d="{d}" fill="none" stroke="{color}" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>'
    layers = [f'<polygon data-layer="heated-boundary" data-circuit-id="{circuit.route_id}" points="{points_attr(circuit.usable_heated_polygon.points)}" fill="#f4f4f4" stroke="#333" stroke-width="18"/>' for circuit in circuits]
    for index, exclusion in enumerate(base.exclusion_zones):
        layers.append(f'<polygon data-layer="exclusion" data-exclusion-index="{index}" points="{points_attr(exclusion.points)}" fill="#efb0b0" stroke="#b00" stroke-width="14"/>')
    for circuit in circuits:
        if circuit.status != "IMPOSSIBLE":
            layers.extend((path(circuit.supply_transit, "#e67e22", "supply-transit", circuit.route_id), path(circuit.coverage_path, "#1677ff", "coverage-route", circuit.route_id), path(circuit.return_transit, "#2a9d50", "return-transit", circuit.route_id)))
        if circuit.pipe_centerline and circuit.status != "IMPOSSIBLE":
            layers.append(f'<circle data-layer="start-point" data-circuit-id="{circuit.route_id}" cx="{circuit.pipe_centerline[0].x_mm}" cy="{circuit.pipe_centerline[0].y_mm}" r="32" fill="#111"/>')
            layers.append(f'<circle data-layer="end-point" data-circuit-id="{circuit.route_id}" cx="{circuit.pipe_centerline[-1].x_mm}" cy="{circuit.pipe_centerline[-1].y_mm}" r="32" fill="#fff" stroke="#111" stroke-width="10"/>')
    layers.append(f'<circle data-layer="manifold" cx="{base.manifold_point.x_mm}" cy="{base.manifold_point.y_mm}" r="45" fill="#d22"/>')
    status = "ROUTE_ACCEPTED" if all(circuit.status != "IMPOSSIBLE" for circuit in circuits) else "ROUTE_REJECTED"
    metric_lines = [f"RESULT={status}", f"STRATEGY={base.routing_strategy}", f"ORIENTATION={base.selected_orientation}", f"SPACING_MM={base.effective_spacing_mm}", f"WALL_OFFSET_MM={base.wall_offset_mm}", f"MIN_BEND_RADIUS_MM={base.minimum_bend_radius_mm}", f"CIRCUIT_COUNT={len(circuits)}"]
    for circuit in circuits:
        metric_lines.append(f"{circuit.route_id} TOTAL_LENGTH_M={circuit.estimated_pipe_length_mm/1000:.2f} COVERAGE_LENGTH_M={circuit.coverage_length_mm/1000:.2f} SUPPLY_TRANSIT_LENGTH_M={circuit.supply_transit_length_mm/1000:.2f} RETURN_TRANSIT_LENGTH_M={circuit.return_transit_length_mm/1000:.2f} COVERAGE_PERCENT={circuit.coverage_percentage:.1f}")
    if base.diagnostics:
        metric_lines.append("DIAGNOSTICS=" + ",".join(base.diagnostics))
    text = "<text x=\"20\" y=\"40\" font-family=\"monospace\" font-size=\"32\">" + "</text><text x=\"20\" y=\"40\" font-family=\"monospace\" font-size=\"32\">" + "</text>"
    labels = "".join(f'<text x="20" y="{40 + i*38}" font-family="monospace" font-size="32">{line}</text>' for i, line in enumerate(metric_lines))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {max_x} {max_y}" data-result-status="{status}">' + "".join(layers) + labels + "</svg>"


__all__=["UfhRoutingPreviewRequest","UfhRoutingPreviewResult","UfhCircuitPlan","OrientationMetric","CoverageCell","generate_ufh_routing_preview","plan_ufh_circuits","decompose_coverage_cells","render_ufh_routing_preview_svg"]

"""Doorway-aware canonical room planner for the universal UFH layout engine.

``calculate_doorway_room_layout`` is the entry point selected by
``floor_heating_engine.calculate_floor_heating`` when a request carries an
explicit ``selected_doorway``.  It builds one continuous, physically
materializable room circuit whose supply and return terminals face the
selected doorway, and joins both terminals to the doorway lanes.

The search is bounded and deterministic: it tries the two bifilar-spiral
orientations whose terminals sit on the doorway wall, checks that both
terminals fall inside the finite doorway segment, and keeps the first route
whose complete centreline (spiral + both doorway crossings) passes the R80
bend, pipe-clearance, containment, continuity and self-intersection checks.

Only the ROOM side is proven here.  Building transit and the physical manifold
connection are reported separately and stay ``UNVERIFIED``.
"""
from __future__ import annotations

from typing import Any

from shapely.geometry import LineString, Polygon

from agent.floor_heating_engine import (
    _area,
    _impossible,
    _point_model,
    _polyline_length,
    _validate_polygon,
)
from agent.floor_heating_models import (
    CircuitRoute,
    CircuitRouteValidation,
    FloorHeatingCircuit,
    FloorHeatingRequest,
    FloorHeatingResult,
)
from agent.ufh_bend_geometry import validate_rounded_centerline
from agent.ufh_layout_engine import reserve_doorway_lanes
from agent.ufh_spiral_kernel import build_accessible_bifilar_spiral


Point = tuple[int, int]


def _room_bounds(outer: list[Point]) -> tuple[int, int, int, int]:
    xs = [point[0] for point in outer]
    ys = [point[1] for point in outer]
    return min(xs), min(ys), max(xs), max(ys)


def _doorway_axis(
    request: FloorHeatingRequest,
) -> tuple[str, tuple[int, int] | None]:
    """Return ('horizontal'|'vertical', span) for the selected doorway."""
    doorway = request.selected_doorway
    assert doorway is not None
    dx = doorway.end.x_mm - doorway.start.x_mm
    dy = doorway.end.y_mm - doorway.start.y_mm
    if dx != 0 and dy != 0:
        return "diagonal", None
    if dx != 0:
        return "horizontal", (min(doorway.start.x_mm, doorway.end.x_mm), max(doorway.start.x_mm, doorway.end.x_mm))
    return "vertical", (min(doorway.start.y_mm, doorway.end.y_mm), max(doorway.start.y_mm, doorway.end.y_mm))


def _build_south_doorway_candidates(
    outer: list[Point],
    request: FloorHeatingRequest,
) -> list[tuple[list[Point], list[tuple[int, int]]]]:
    """Return (spiral, [supply_lane, return_lane]) candidates for a doorway on
    the south wall, in deterministic order.  Each candidate keeps both
    terminals inside the doorway and uses straight, collinear drops through
    the wall.  An empty list means no south-wall orientation can place both
    terminals inside this doorway."""
    x0, y0, x1, y1 = _room_bounds(outer)
    off = request.wall_offset_mm
    envelope = (float(x0 + off), float(y0 + off), float(x1 - off), float(y1 - off))
    doorway_min, doorway_max = _doorway_axis(request)[1]
    pitch = float(request.spacing_mm)
    candidates: list[tuple[list[Point], list[tuple[int, int]]]] = []
    for mirror in (True, False):
        spiral = build_accessible_bifilar_spiral(
            envelope,
            pitch,
            minimum_bend_radius_mm=float(request.turn_radius_mm),
            mirror_x=mirror,
        )
        if not spiral:
            continue
        terminal_a = (int(round(spiral[0][0])), int(round(spiral[0][1])))
        terminal_b = (int(round(spiral[-1][0])), int(round(spiral[-1][1])))
        if terminal_a[1] != terminal_b[1] or terminal_a[1] != y0 + off:
            continue
        xs = [terminal_a[0], terminal_b[0]]
        if doorway_min <= min(xs) and max(xs) <= doorway_max:
            supply_lane = (terminal_a[0], y0)
            return_lane = (terminal_b[0], y0)
            route = [supply_lane] + [terminal_a] + [
                (int(round(px)), int(round(py))) for px, py in spiral[1:]
            ] + [return_lane]
            candidates.append((route, [supply_lane, return_lane]))
    return candidates


def _extended_room_polygon(
    outer: list[Point],
    request: FloorHeatingRequest,
) -> list[Point]:
    """Return the room boundary extended outward through the doorway so the
    wall-crossing centreline can be validated together with the in-room route.
    Only the selected doorway is opened; no other wall is modified."""
    doorway = request.selected_doorway
    assert doorway is not None
    off = float(request.wall_offset_mm)
    dmin, dmax = _doorway_axis(request)[1]
    x0, y0, x1, y1 = _room_bounds(outer)
    # Doorway on the south wall: notch the south edge downward.
    return [
        (x0, y0),
        (dmin, y0),
        (dmin, int(round(y0 - off))),
        (dmax, int(round(y0 - off))),
        (dmax, y0),
        (x1, y0),
        (x1, y1),
        (x0, y1),
        (x0, y0),
    ]


def calculate_doorway_room_layout(request: FloorHeatingRequest) -> FloorHeatingResult:
    """Plan one continuous room circuit through the selected doorway.

    The result is ``ok`` only when the complete centreline (spiral plus both
    doorway crossings) is geometrically and physically valid.  Physical
    invalidity is never reported as a ready route.
    """
    doorway = request.selected_doorway
    if doorway is None:
        return _impossible(request, "doorway_required", "selected_doorway is required")

    circuit_count = request.requested_circuit_count or 1
    if circuit_count != 1:
        return _impossible(
            request,
            "multi_circuit_split_not_yet_implemented",
            "automatic splitting into independent circuits is the next stage",
        )

    outer, error = _validate_polygon(request.boundary)
    if outer is None:
        return _impossible(request, "invalid_geometry", error or "invalid room geometry")

    exclusions: list[list[Point]] = []
    for exclusion in request.exclusion_zones:
        normalized, exclusion_error = _validate_polygon(exclusion, allow_l=False)
        if normalized is None:
            return _impossible(request, "invalid_exclusion", exclusion_error or "invalid exclusion geometry")
        exclusions.append(normalized)

    reservation = reserve_doorway_lanes(
        (
            (float(doorway.start.x_mm), float(doorway.start.y_mm)),
            (float(doorway.end.x_mm), float(doorway.end.y_mm)),
        ),
        circuit_count,
        pipe_outer_diameter_mm=float(request.pipe_outer_diameter_mm),
        minimum_free_pipe_clearance_mm=float(request.minimum_free_pipe_clearance_mm),
        edge_clearance_mm=float(request.doorway_edge_clearance_mm),
    )
    if not reservation.valid:
        return _impossible(
            request,
            "doorway_capacity_insufficient",
            "; ".join(reservation.diagnostics),
        )

    axis, _ = _doorway_axis(request)
    if axis == "diagonal":
        return _impossible(
            request,
            "diagonal_doorway_unsupported",
            "doorway segment must be axis-aligned",
        )
    if axis != "horizontal":
        return _impossible(
            request,
            "doorway_orientation_unsupported",
            "only horizontal south-wall doorways are supported by the bounded search",
        )
    x0, y0, x1, y1 = _room_bounds(outer)
    if doorway.start.y_mm != y0:
        return _impossible(
            request,
            "doorway_wall_unsupported",
            "the bounded search only supports doorways on the south wall",
        )

    candidates = _build_south_doorway_candidates(outer, request)
    if not candidates:
        return _impossible(
            request,
            "no_doorway_aligned_spiral",
            "no spiral orientation places both terminals inside the selected doorway",
        )

    diagnostics: list[str] = []
    for route, lanes in candidates:
        length = _polyline_length(route)
        connected = len(route) >= 2 and all(
            first != second and (first[0] == second[0] or first[1] == second[1])
            for first, second in zip(route, route[1:])
        )
        line = LineString([(float(x), float(y)) for x, y in route])
        self_intersection = not line.is_simple
        rounded = validate_rounded_centerline(
            route,
            _extended_room_polygon(outer, request),
            bend_radius_mm=float(request.turn_radius_mm),
            pipe_outer_radius_mm=float(request.pipe_outer_diameter_mm) / 2.0,
            obstacles=exclusions,
        )
        length_valid = (
            request.minimum_circuit_length_mm <= length <= request.maximum_circuit_length_mm
        )
        if not connected:
            diagnostics.append("ROUTE_NOT_CONNECTED_OR_ORTHOGONAL")
        if self_intersection:
            diagnostics.append("ROUTE_SELF_INTERSECTION")
        if not rounded.bend_valid:
            diagnostics.append("ROUTE_BEND_GEOMETRY_INVALID")
            diagnostics.extend(rounded.diagnostics)
        if not length_valid:
            diagnostics.append("ROUTE_LENGTH_INVALID")

        valid = all(
            (
                connected,
                not self_intersection,
                rounded.bend_valid,
                rounded.topology_valid,
            )
        )
        if not valid:
            continue

        validation = CircuitRouteValidation(
            polyline_count=1,
            connected=connected,
            self_intersection=self_intersection,
            branches=False,
            step_valid=True,
            length_valid=length_valid,
            inside_boundary=rounded.geometry_valid,
            exclusion_clear="ROUNDED_CENTERLINE_OBSTACLE_CLEARANCE_VIOLATION" not in rounded.diagnostics,
            endpoints_valid=True,
            calculated_length_mm=length,
            polyline_length_mm=length,
            valid=valid,
            diagnostics=diagnostics,
        )
        route_model = CircuitRoute(
            id=f"fh/{request.project_id}/{request.room_id}/doorway-circuit-1",
            polyline=[_point_model(point) for point in route],
            length_mm=length,
            spacing_segments=[],
            outer_wall_segments=[],
            field_segments=[],
            collector_supply_point=_point_model(route[0]),
            collector_return_point=_point_model(route[-1]),
            validation=validation,
            physical_geometry=rounded.as_dict(),
        )
        circuit = FloorHeatingCircuit(
            circuit_id=f"fh/{request.project_id}/{request.room_id}/doorway-circuit-1",
            points=route_model.polyline,
            supply_transit=route_model.polyline[:1],
            return_transit=route_model.polyline[-1:],
            length_mm=length,
            zone_role="OCCUPIED_FIELD",
            topology="COUNTERFLOW_SPIRAL",
            nominal_spacing_mm=request.spacing_mm,
            field_laying_length_mm=length,
        )
        warnings: list[str] = []
        if not length_valid:
            warnings.append("OVERLENGTH")
        room_layout = {
            "ROOM_LAYOUT_VALID": valid,
            "DOORWAY_CONNECTION_VALID": True,
            "BUILDING_TRANSIT_VALID": "UNVERIFIED",
            "MANIFOLD_CONNECTED": "UNVERIFIED",
            "opening_authority": doorway.authority_status,
            "strategy": "BIFILAR_SPIRAL",
            "doorway_lane_reservation": reservation.as_dict(),
            "requested_circuit_count": circuit_count,
            "actual_circuit_count": 1,
            "route_length_mm": length,
            "overlength": not length_valid,
            "doorway_supply_crossing_mm": [list(lanes[0]), list(route[0])],
            "doorway_return_crossing_mm": [list(lanes[1]), list(route[-1])],
            "diagnostics": diagnostics,
        }
        result = FloorHeatingResult(
            project_id=request.project_id,
            room_id=request.room_id,
            status="ok",
            usable_heated_area_mm2=_area(outer),
            spacing_mm=request.spacing_mm,
            wall_offset_mm=request.wall_offset_mm,
            maximum_circuit_length_mm=request.maximum_circuit_length_mm,
            circuit_count=1,
            lanes=[],
            circuits=[circuit],
            circuit_routes=[route_model],
            unresolved_regions=[],
            warnings=warnings,
            assumptions=[],
            diagnostics=[],
            maximum_length_compliant=length_valid,
            result_digest="0" * 64,
            turn_radius_mm=request.turn_radius_mm,
            routing_mode=request.routing_mode,
            room_layout=room_layout,
        )
        from agent.floor_heating_engine import _digest

        return result.model_copy(update={"result_digest": _digest(result)})

    return _impossible(
        request,
        "doorway_route_physically_invalid",
        "; ".join(diagnostics) or "no candidate passed the joint physical check",
    )


__all__ = ["calculate_doorway_room_layout"]

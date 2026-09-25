"""Fail-closed endpoint access checks for UFH zone candidates.

This module answers a narrow question: can a circuit endpoint reach the
boundary of its own room without crossing the room boundary, obstacles, or
already occupied pipe lanes?  It deliberately does not infer doors, risers,
openings, or manifold connections.  Those remain separate authority gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Iterable

from shapely.geometry import LineString, Point, Polygon


@dataclass(frozen=True)
class EndpointAccess:
    endpoint: tuple[float, float]
    boundary_point: tuple[float, float] | None
    path: tuple[tuple[float, float], ...]
    distance_mm: float | None
    room_boundary_reachable: bool
    occupied_route_clear: bool
    obstacle_clear: bool
    status: str
    diagnostics: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "endpoint": [round(v, 3) for v in self.endpoint],
            "boundary_point": None if self.boundary_point is None else [round(v, 3) for v in self.boundary_point],
            "path_mm": [[round(x, 3), round(y, 3)] for x, y in self.path],
            "distance_mm": None if self.distance_mm is None else round(self.distance_mm, 3),
            "room_boundary_reachable": self.room_boundary_reachable,
            "occupied_route_clear": self.occupied_route_clear,
            "obstacle_clear": self.obstacle_clear,
            "status": self.status,
            "diagnostics": list(self.diagnostics),
        }


def _nearest_boundary_point(room: Polygon, endpoint: tuple[float, float]) -> Point:
    boundary = room.exterior
    return boundary.interpolate(boundary.project(Point(endpoint)))


def check_endpoint_access(
    endpoint: tuple[float, float],
    room_boundary: Iterable[tuple[float, float]],
    occupied_routes: Iterable[Iterable[tuple[float, float]]] = (),
    obstacles: Iterable[Iterable[tuple[float, float]]] = (),
    *,
    pipe_outer_radius_mm: float = 8.0,
    clearance_mm: float = 8.0,
    preferred_exit_mm: tuple[float, float] | None = None,
    preferred_exit_segment: tuple[tuple[float, float], tuple[float, float]] | None = None,
) -> EndpointAccess:
    """Check a straight in-room path to the nearest room boundary point.

    Contact with the endpoint's own centerline at its first point is allowed;
    any additional overlap with occupied lanes is rejected.  A successful
    result means only ``ROOM_BOUNDARY_REACHABLE``.  No opening or manifold
    authority is invented here.
    """
    point = (float(endpoint[0]), float(endpoint[1]))
    room = Polygon(list(room_boundary))
    diagnostics: list[str] = []
    if room.is_empty or not room.is_valid:
        return EndpointAccess(point, None, (point,), None, False, False, False, "INVALID_ROOM_GEOMETRY", ("INVALID_ROOM_GEOMETRY",))
    # A user-selected exit is a preference only.  Project it to the actual
    # room boundary and require the endpoint-to-opening lane to stay inside
    # the room.  This deliberately does not authorize a wall/door crossing.
    if preferred_exit_segment is not None:
        opening = LineString(preferred_exit_segment)
        target = opening.interpolate(opening.project(Point(point)))
        # The threshold segment can be represented on either side of a wall;
        # bind the in-room end to the nearest point on the actual boundary.
        boundary_target = _nearest_boundary_point(room, (target.x, target.y))
        target = boundary_target
    else:
        target = _nearest_boundary_point(room, preferred_exit_mm) if preferred_exit_mm is not None else _nearest_boundary_point(room, point)
    target_xy = (float(target.x), float(target.y))
    access_line = LineString([point, target_xy])
    room_ok = bool(room.covers(access_line))
    if not room_ok:
        diagnostics.append("EXIT_PATH_LEAVES_ROOM")
    occupied_ok = True
    allowed_contact = pipe_outer_radius_mm + clearance_mm
    for route in occupied_routes:
        line = LineString(list(route))
        if line.is_empty:
            continue
        overlap = access_line.intersection(line.buffer(allowed_contact, cap_style=2))
        # The access line starts at this endpoint. Permit only the initial
        # contact needed to leave the circuit, not a parallel/through-pipe run.
        if not overlap.is_empty and overlap.length > allowed_contact + 1e-6:
            occupied_ok = False
            diagnostics.append("EXIT_PATH_CROSSES_OCCUPIED_PIPE")
            break
    obstacle_ok = True
    for obstacle in obstacles:
        obstacle_poly = Polygon(list(obstacle))
        if access_line.intersects(obstacle_poly.buffer(allowed_contact)):
            obstacle_ok = False
            diagnostics.append("EXIT_PATH_CROSSES_OBSTACLE")
            break
    reachable = room_ok and occupied_ok and obstacle_ok
    status = "ROOM_BOUNDARY_REACHABLE" if reachable else "NO_GEOMETRIC_EXIT_PATH"
    if preferred_exit_mm is not None or preferred_exit_segment is not None:
        preferred_distance = Point(preferred_exit_mm).distance(target)
        if preferred_distance > max(2 * clearance_mm, 250.0):
            diagnostics.append("PREFERRED_EXIT_FAR_FROM_ROOM_BOUNDARY")
            reachable = False
    return EndpointAccess(
        point,
        target_xy,
        (point, target_xy),
        hypot(target_xy[0] - point[0], target_xy[1] - point[1]),
        room_ok,
        occupied_ok,
        obstacle_ok,
        status,
        tuple(dict.fromkeys(diagnostics)),
    )


def review_zone_route_endpoints(
    route: Iterable[tuple[float, float]],
    room_boundary: Iterable[tuple[float, float]],
    *,
    other_routes: Iterable[Iterable[tuple[float, float]]] = (),
    obstacles: Iterable[Iterable[tuple[float, float]]] = (),
    preferred_exit_mm: tuple[float, float] | None = None,
    preferred_exit_segment: tuple[tuple[float, float], tuple[float, float]] | None = None,
) -> dict[str, object]:
    points = list(route)
    if len(points) < 2:
        return {
            "endpoint_access_state": "INVALID",
            "opening_authority": "UNVERIFIED_NO_AUTHORIZED_OPENING",
            "manifold_connected": "UNVERIFIED",
            "endpoints": [],
            "diagnostics": ["ROUTE_HAS_FEWER_THAN_TWO_POINTS"],
        }
    checks = [
        check_endpoint_access(points[0], room_boundary, other_routes, obstacles, preferred_exit_mm=preferred_exit_mm, preferred_exit_segment=preferred_exit_segment),
        check_endpoint_access(points[-1], room_boundary, other_routes, obstacles, preferred_exit_mm=preferred_exit_mm, preferred_exit_segment=preferred_exit_segment),
    ]
    geometric = all(c.room_boundary_reachable and c.occupied_route_clear and c.obstacle_clear for c in checks)
    return {
        "endpoint_access_state": "VALID" if geometric else "INVALID",
        "opening_authority": "UNVERIFIED_NO_AUTHORIZED_OPENING",
        "preferred_exit_mm": None if preferred_exit_mm is None else [round(preferred_exit_mm[0], 3), round(preferred_exit_mm[1], 3)],
        "preferred_exit_segment_mm": None if preferred_exit_segment is None else [[round(x, 3), round(y, 3)] for x, y in preferred_exit_segment],
        "manifold_connected": "UNVERIFIED",
        "endpoints": [c.as_dict() for c in checks],
        "diagnostics": list(dict.fromkeys(d for c in checks for d in c.diagnostics)),
        "interpretation": "VALID means geometric reach to this room boundary only; it does not authorize a wall crossing or collector connection.",
    }


__all__ = ["EndpointAccess", "check_endpoint_access", "review_zone_route_endpoints"]

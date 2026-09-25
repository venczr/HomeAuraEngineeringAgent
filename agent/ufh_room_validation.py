"""Independent physical checks for room-local, finite-doorway UFH circuits.

Inputs are geometry and dimensions, never producer validity flags.  A passing
report concerns the materialized room paths only: neither an estimated transit
length nor a doorway terminal establishes a connection to a manifold.  Coverage,
thermal performance and bifilar morphology are separate validation contracts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from math import atan2, cos, hypot, isfinite, pi, sin, sqrt
from typing import Iterable

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

from agent.ufh_bend_geometry import build_rounded_centerline

PointMM = tuple[float, float]
_EPS = 1e-6
_SAMPLES_PER_QUARTER = 32


@dataclass(frozen=True)
class RoomCircuitPhysicalReport:
    circuit_index: int
    valid: bool
    geometry_valid: bool
    topology_valid: bool
    bend_valid: bool
    terminals_valid: bool
    self_clearance_valid: bool
    inter_circuit_clearance_valid: bool
    length_valid: bool
    room_length_mm: float
    estimated_external_transit_length_mm: float | None
    estimated_total_length_mm: float | None
    rounded_points: tuple[PointMM, ...]
    svg_path_data: str
    duplicate_centerline_length_mm: float
    diagnostics: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["rounded_points_mm"] = result.pop("rounded_points")
        result["length_mm"] = self.room_length_mm
        return result


@dataclass(frozen=True)
class RoomCircuitValidationReport:
    valid: bool
    circuits: tuple[RoomCircuitPhysicalReport, ...]
    minimum_inter_circuit_centerline_distance_mm: float | None
    required_centerline_distance_mm: float
    diagnostics: tuple[str, ...]
    transit_authority: str = "NOT_VALIDATED"
    manifold_connected: bool = False

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["circuits"] = [circuit.as_dict() for circuit in self.circuits]
        return result


@dataclass(frozen=True)
class _Primitive:
    line: LineString
    # Every point on the circular arc is within this distance of its chords.
    error_mm: float = 0.0
    center: PointMM | None = None
    radius: float = 0.0
    start_angle: float = 0.0
    sweep_sign: int = 1


def _arc_contains(part: _Primitive, point: PointMM) -> bool:
    assert part.center is not None
    angle = atan2(point[1] - part.center[1], point[0] - part.center[0])
    swept = (part.sweep_sign * (angle - part.start_angle)) % (2 * pi)
    return swept <= pi / 2 + 1e-10 or swept >= 2 * pi - 1e-10


def _point_arc_distance(point: PointMM, arc: _Primitive) -> float:
    assert arc.center is not None
    if _arc_contains(arc, point):
        return abs(hypot(point[0] - arc.center[0], point[1] - arc.center[1]) - arc.radius)
    return min(hypot(point[0] - end[0], point[1] - end[1]) for end in (arc.line.coords[0], arc.line.coords[-1]))


def _straight_arc_distance(straight: _Primitive, arc: _Primitive) -> float:
    assert arc.center is not None
    a, b = straight.line.coords[0], straight.line.coords[-1]
    distance = min(_point_arc_distance(a, arc), _point_arc_distance(b, arc),
                   straight.line.distance(Point(arc.line.coords[0])), straight.line.distance(Point(arc.line.coords[-1])))
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = hypot(dx, dy)
    # Interior extrema occur at radial points normal to the straight line.
    for sign in (-1, 1):
        point = (arc.center[0] - sign * arc.radius * dy / length,
                 arc.center[1] + sign * arc.radius * dx / length)
        if _arc_contains(arc, point):
            distance = min(distance, straight.line.distance(Point(point)))
    # Crossing candidates are roots of the segment/circle quadratic.
    ox, oy = a[0] - arc.center[0], a[1] - arc.center[1]
    qa, qb, qc = length * length, 2 * (ox * dx + oy * dy), ox * ox + oy * oy - arc.radius * arc.radius
    discriminant = qb * qb - 4 * qa * qc
    if discriminant >= -_EPS:
        for sign in (-1, 1):
            parameter = (-qb + sign * sqrt(max(0.0, discriminant))) / (2 * qa)
            if -1e-12 <= parameter <= 1 + 1e-12:
                point = (a[0] + parameter * dx, a[1] + parameter * dy)
                if _arc_contains(arc, point):
                    return 0.0
    return distance


def _exact_distance(first: _Primitive, second: _Primitive) -> float:
    """Exact distance of orthogonal segments/quarter circles, not their chords."""
    if first.center is None and second.center is None:
        return first.line.distance(second.line)
    if first.center is None:
        return _straight_arc_distance(first, second)
    if second.center is None:
        return _straight_arc_distance(second, first)
    distance = min(*(_point_arc_distance(point, second) for point in (first.line.coords[0], first.line.coords[-1])),
                   *(_point_arc_distance(point, first) for point in (second.line.coords[0], second.line.coords[-1])))
    dx, dy = second.center[0] - first.center[0], second.center[1] - first.center[1]
    centers = hypot(dx, dy)
    if centers <= _EPS:
        # Angular overlap includes an endpoint of either closed quarter arc.
        return distance
    ux, uy = dx / centers, dy / centers
    for sign_first in (-1, 1):
        p = (first.center[0] + sign_first * first.radius * ux, first.center[1] + sign_first * first.radius * uy)
        if not _arc_contains(first, p):
            continue
        for sign_second in (-1, 1):
            q = (second.center[0] + sign_second * second.radius * ux, second.center[1] + sign_second * second.radius * uy)
            if _arc_contains(second, q):
                distance = min(distance, hypot(p[0] - q[0], p[1] - q[1]))
    if abs(first.radius - second.radius) - _EPS <= centers <= first.radius + second.radius + _EPS:
        along = (first.radius * first.radius - second.radius * second.radius + centers * centers) / (2 * centers)
        height = sqrt(max(0.0, first.radius * first.radius - along * along))
        for sign in (-1, 1):
            point = (first.center[0] + along * ux - sign * height * uy,
                     first.center[1] + along * uy + sign * height * ux)
            if _arc_contains(first, point) and _arc_contains(second, point):
                return 0.0
    return distance


def _points(values: Iterable[PointMM]) -> list[PointMM]:
    return [(float(x), float(y)) for x, y in values]


def _compress_forward_collinear(points: list[PointMM]) -> list[PointMM]:
    """Remove redundant vertices, preserving backtracking as a real defect."""
    result: list[PointMM] = []
    for point in points:
        result.append(point)
        while len(result) >= 3:
            a, b, c = result[-3:]
            u, v = (b[0] - a[0], b[1] - a[1]), (c[0] - b[0], c[1] - b[1])
            if abs(u[0] * v[1] - u[1] * v[0]) <= _EPS and u[0] * v[0] + u[1] * v[1] > 0:
                result.pop(-2)
            else:
                break
    return result


def _unit(a: PointMM, b: PointMM) -> PointMM:
    length = hypot(b[0] - a[0], b[1] - a[1])
    return ((b[0] - a[0]) / length, (b[1] - a[1]) / length)


def _primitives(points: list[PointMM], radius: float) -> tuple[list[_Primitive], bool]:
    """Split the explicit fillet model into straight legs and quarter arcs.

    The legacy renderer's per-corner 2R check over-rejects terminal legs.
    Here tangent consumption is independently checked for each leg: one R for
    each endpoint that is a corner, zero for a terminal or collinear vertex.
    """
    corners: dict[int, tuple[PointMM, PointMM, _Primitive]] = {}
    sagitta = radius * (1 - cos(pi / (4 * _SAMPLES_PER_QUARTER)))
    for index in range(1, len(points) - 1):
        before, corner, after = points[index - 1:index + 2]
        incoming, outgoing = _unit(before, corner), _unit(corner, after)
        cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
        if abs(cross) < _EPS:
            continue
        entry = (corner[0] - incoming[0] * radius, corner[1] - incoming[1] * radius)
        exit_point = (corner[0] + outgoing[0] * radius, corner[1] + outgoing[1] * radius)
        sign = 1 if cross > 0 else -1
        center = (entry[0] - sign * incoming[1] * radius, entry[1] + sign * incoming[0] * radius)
        angle = atan2(entry[1] - center[1], entry[0] - center[0])
        arc = [entry]
        for sample in range(1, _SAMPLES_PER_QUARTER):
            theta = angle + sign * pi / 2 * sample / _SAMPLES_PER_QUARTER
            arc.append((center[0] + radius * cos(theta), center[1] + radius * sin(theta)))
        arc.append(exit_point)
        corners[index] = (entry, exit_point, _Primitive(LineString(arc), sagitta, center, radius, angle, sign))
    valid = True
    parts: list[_Primitive] = []
    for index, (a, b) in enumerate(zip(points, points[1:])):
        trim = radius * (int(index in corners) + int(index + 1 in corners))
        if hypot(b[0] - a[0], b[1] - a[1]) + _EPS < trim:
            valid = False
        start = corners[index][1] if index in corners else a
        end = corners[index + 1][0] if index + 1 in corners else b
        if hypot(end[0] - start[0], end[1] - start[1]) > _EPS:
            parts.append(_Primitive(LineString([start, end])))
        if index + 1 in corners:
            parts.append(corners[index + 1][2])
    return parts, valid


def _clearance_failure(parts: list[_Primitive], minimum: float, *, self_check: bool) -> bool:
    """Spatial-indexed nonlocal pipe test; adjacent material may join normally.

    Consecutive primitives share a joint.  A straight/arc/straight triple is
    one local elbow, so its two legs are also excluded.  All other pairs are
    tested against their explicit chord error, including short return runs.
    """
    if not parts:
        return False
    tree = STRtree([part.line for part in parts])
    maximum_error = max(part.error_mm for part in parts)
    for index, part in enumerate(parts):
        nearby = tree.query(part.line, predicate="dwithin", distance=minimum + part.error_mm + maximum_error + _EPS)
        for found in nearby:
            other_index = int(found)
            if other_index <= index:
                continue
            if self_check and other_index - index <= 2:
                continue
            other = parts[other_index]
            lower_bound = part.line.distance(other.line) - part.error_mm - other.error_mm
            if lower_bound + _EPS < minimum and _exact_distance(part, other) + _EPS < minimum:
                return True
    return False


def _pair_clearance_failure(first: list[_Primitive], second: list[_Primitive], minimum: float) -> bool:
    if not first or not second:
        return False
    tree = STRtree([part.line for part in second])
    maximum_error = max(part.error_mm for part in second)
    for part in first:
        nearby = tree.query(part.line, predicate="dwithin", distance=minimum + part.error_mm + maximum_error + _EPS)
        for found in nearby:
            other = second[int(found)]
            if (part.line.distance(other.line) - part.error_mm - other.error_mm + _EPS < minimum
                    and _exact_distance(part, other) + _EPS < minimum):
                return True
    return False


def validate_room_circuits(
    routes_mm: Iterable[Iterable[PointMM]],
    room_polygon_mm: Iterable[PointMM],
    doorway_segment_mm: tuple[PointMM, PointMM],
    *,
    bend_radius_mm: float = 80.0,
    pipe_outer_diameter_mm: float = 16.0,
    minimum_free_pipe_clearance_mm: float = 16.0,
    wall_clearance_mm: float = 0.0,
    doorway_edge_clearance_mm: float = 0.0,
    obstacles_mm: Iterable[Iterable[PointMM]] = (),
    obstacle_clearance_mm: float = 0.0,
    minimum_circuit_length_mm: float = 0.0,
    maximum_circuit_length_mm: float = 80_000.0,
    estimated_external_transit_length_mm: float | None = None,
) -> RoomCircuitValidationReport:
    """Validate 1--5 complete room-side paths terminating on one finite door.

    Lengths are exact straight-plus-circular-arc lengths.  Geometric clearance
    uses 32 chords per quarter arc with a conservative sagitta allowance;
    straight doorway lanes at the exact prescribed pitch remain admissible.
    ``wall_clearance_mm`` and ``obstacle_clearance_mm`` are free surface gaps,
    not centerline offsets.  The optional transit estimate applies per circuit
    and only supplies a provisional total-length check.
    """
    required_distance = pipe_outer_diameter_mm + minimum_free_pipe_clearance_mm
    diagnostics: list[str] = []
    parameters = [bend_radius_mm, pipe_outer_diameter_mm, minimum_free_pipe_clearance_mm,
                  wall_clearance_mm, doorway_edge_clearance_mm, obstacle_clearance_mm,
                  minimum_circuit_length_mm, maximum_circuit_length_mm]
    if (not all(isfinite(value) for value in parameters)
            or bend_radius_mm <= 0 or pipe_outer_diameter_mm <= 0
            or min(parameters[2:]) < 0
            or maximum_circuit_length_mm <= 0
            or minimum_circuit_length_mm > maximum_circuit_length_mm
            or estimated_external_transit_length_mm is not None and (
                not isfinite(estimated_external_transit_length_mm) or estimated_external_transit_length_mm < 0)):
        return RoomCircuitValidationReport(False, (), None, required_distance, ("INVALID_VALIDATION_PARAMETER",))
    routes = [_points(route) for route in routes_mm]
    room_points, door_points = _points(room_polygon_mm), _points(doorway_segment_mm)
    obstacle_points = [_points(obstacle) for obstacle in obstacles_mm]
    if not 1 <= len(routes) <= 5:
        diagnostics.append("CIRCUIT_COUNT_OUT_OF_SUPPORTED_RANGE")
    finite = all(isfinite(value) for shape in [room_points, door_points, *obstacle_points, *routes] for point in shape for value in point)
    if not finite or len(room_points) < 3 or len(door_points) != 2 or any(len(points) < 3 for points in obstacle_points):
        return RoomCircuitValidationReport(False, (), None, required_distance, tuple(diagnostics + ["INVALID_INPUT_GEOMETRY"]))
    room, doorway = Polygon(room_points), LineString(door_points)
    obstacles = [Polygon(points) for points in obstacle_points]
    if not room.is_valid or room.area <= 0 or any(not obstacle.is_valid or obstacle.area <= 0 for obstacle in obstacles):
        return RoomCircuitValidationReport(False, (), None, required_distance, tuple(diagnostics + ["INVALID_INPUT_POLYGON"]))
    door_delta = (door_points[1][0] - door_points[0][0], door_points[1][1] - door_points[0][1])
    if (doorway.length <= _EPS or door_delta[0] != 0 and door_delta[1] != 0
            or not room.boundary.buffer(_EPS).covers(doorway)):
        return RoomCircuitValidationReport(False, (), None, required_distance, tuple(diagnostics + ["DOORWAY_NOT_ON_FINITE_ORTHOGONAL_ROOM_EDGE"]))
    # Only this finite portion of the wall is absent.  Jamb endpoints and every
    # other wall remain in the distance test, including other collinear walls.
    solid_boundary = room.boundary.difference(doorway.buffer(_EPS, cap_style=2))
    pipe_radius = pipe_outer_diameter_mm / 2
    reports: list[RoomCircuitPhysicalReport] = []
    route_lines: list[LineString] = []
    route_parts: list[list[_Primitive]] = []
    for circuit_index, raw in enumerate(routes, 1):
        issues: list[str] = []
        usable = len(raw) >= 2 and len(raw) <= 20_000
        if not usable:
            issues.append("EMPTY_OR_OVERSIZED_CENTERLINE")
        zero = any(a == b for a, b in zip(raw, raw[1:]))
        orthogonal = all(a[0] == b[0] or a[1] == b[1] for a, b in zip(raw, raw[1:]))
        if zero:
            issues.append("ZERO_LENGTH_SEGMENT")
        if not orthogonal:
            issues.append("NON_ORTHOGONAL_SEGMENT")
        normalized = _compress_forward_collinear(raw) if usable and not zero else raw if usable else []
        rounded = build_rounded_centerline(normalized, bend_radius_mm=bend_radius_mm, samples_per_quarter=_SAMPLES_PER_QUARTER)
        line = LineString(rounded.points) if len(rounded.points) >= 2 else LineString()
        parts, tangent_valid = _primitives(normalized, bend_radius_mm) if usable and not zero and orthogonal else ([], False)
        bend_valid = usable and orthogonal and not zero and tangent_valid
        if not bend_valid:
            issues.append("BEND_TANGENT_FIT_INVALID")
        duplicate_length = max(0.0, line.length - unary_union(line).length) if not line.is_empty else 0.0
        topology_valid = bool(usable and not zero and orthogonal and line.is_simple and raw[0] != raw[-1] and duplicate_length <= _EPS)
        if not topology_valid:
            issues.append("ROUNDED_TOPOLOGY_INVALID")
        if duplicate_length > _EPS:
            issues.append("DUPLICATE_CENTERLINE_OVERLAP")
        terminal_valid = bool(usable)
        if usable:
            terminal_valid = all(doorway.distance(Point(point)) <= _EPS for point in (raw[0], raw[-1]))
            for point in (raw[0], raw[-1]):
                position = doorway.project(Point(point))
                terminal_valid &= min(position, doorway.length - position) + _EPS >= pipe_radius + doorway_edge_clearance_mm
            for a, b in ((raw[0], raw[1]), (raw[-2], raw[-1])):
                terminal_valid &= abs((b[0] - a[0]) * door_delta[0] + (b[1] - a[1]) * door_delta[1]) <= _EPS
        if not terminal_valid:
            issues.append("TERMINALS_NOT_PERPENDICULAR_ON_FINITE_DOORWAY")
        geometry_valid = bool(parts and not line.is_empty and room.buffer(_EPS).covers(line))
        for part in parts:
            wall_threshold = pipe_radius + wall_clearance_mm + part.error_mm
            # A zero requested free gap still cannot authorize physical contact.
            wall_threshold += _EPS * 2 if wall_clearance_mm == 0 else 0
            if part.line.distance(solid_boundary) + _EPS < wall_threshold:
                geometry_valid = False
                issues.append("PIPE_WALL_CLEARANCE_VIOLATION")
            if part.error_mm and not room.buffer(-part.error_mm).buffer(_EPS).covers(part.line):
                geometry_valid = False
            for obstacle in obstacles:
                threshold = pipe_radius + obstacle_clearance_mm + part.error_mm
                threshold += _EPS * 2 if obstacle_clearance_mm == 0 else 0
                if part.line.distance(obstacle) + _EPS < threshold:
                    geometry_valid = False
                    issues.append("PIPE_OBSTACLE_CLEARANCE_VIOLATION")
        if not geometry_valid:
            issues.append("PHYSICAL_PIPE_OUTSIDE_ALLOWED_ROOM")
        contact_threshold = required_distance + (2 * _EPS if minimum_free_pipe_clearance_mm == 0 else 0)
        self_clearance = not _clearance_failure(parts, contact_threshold, self_check=True)
        if not self_clearance:
            issues.append("NONLOCAL_SELF_PIPE_CLEARANCE_VIOLATION")
        length = rounded.length_mm
        estimated_total = None if estimated_external_transit_length_mm is None else length + estimated_external_transit_length_mm
        checked_length = length if estimated_total is None else estimated_total
        length_valid = bool(length >= 0 and minimum_circuit_length_mm - _EPS <= checked_length <= maximum_circuit_length_mm + _EPS)
        if not length_valid:
            issues.append("ROOM_OR_ESTIMATED_TOTAL_LENGTH_OUT_OF_RANGE")
        reports.append(RoomCircuitPhysicalReport(
            circuit_index, bool(bend_valid and topology_valid and terminal_valid and geometry_valid and self_clearance and length_valid),
            geometry_valid, topology_valid, bend_valid, terminal_valid, self_clearance, True, length_valid,
            length, estimated_external_transit_length_mm, estimated_total, rounded.points,
            rounded.svg_path_data, duplicate_length, tuple(dict.fromkeys(issues)),
        ))
        route_lines.append(line)
        route_parts.append(parts)
    minimum_distance: float | None = None
    for first in range(len(routes)):
        for second in range(first + 1, len(routes)):
            if route_lines[first].is_empty or route_lines[second].is_empty:
                continue
            measured = route_lines[first].distance(route_lines[second])
            minimum_distance = measured if minimum_distance is None else min(minimum_distance, measured)
            contact_threshold = required_distance + (2 * _EPS if minimum_free_pipe_clearance_mm == 0 else 0)
            pair_failure = _pair_clearance_failure(route_parts[first], route_parts[second], contact_threshold)
            if pair_failure or measured <= _EPS:
                diagnostics.append(f"INTER_CIRCUIT_CLEARANCE_VIOLATION:{first + 1}:{second + 1}")
                for index in (first, second):
                    report = reports[index]
                    reports[index] = replace(report, valid=False, inter_circuit_clearance_valid=False,
                                             diagnostics=tuple(dict.fromkeys((*report.diagnostics, "INTER_CIRCUIT_CLEARANCE_VIOLATION"))))
    if any(not report.valid for report in reports):
        diagnostics.append("CIRCUIT_PHYSICAL_VALIDATION_FAILED")
    return RoomCircuitValidationReport(
        bool(not diagnostics and reports and all(report.valid for report in reports)), tuple(reports),
        minimum_distance, required_distance, tuple(diagnostics),
    )


__all__ = ["RoomCircuitPhysicalReport", "RoomCircuitValidationReport", "validate_room_circuits"]

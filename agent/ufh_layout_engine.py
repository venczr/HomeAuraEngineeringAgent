"""Geometry-first UFH layout candidates and independent validation.

This module deliberately contains no thermal or hydraulic claims.  It is used
by the Test_01 preview builder to classify room candidates, validate coverage
containment independently from the canonical engine, and partition long room
loops before building transit metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any, Iterable, Literal

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union


CONTAINMENT_TOLERANCE_MM = 1.0
MAX_TOTAL_CIRCUIT_LENGTH_M = 90.0
MAX_TOTAL_CIRCUIT_LENGTH_AUTHORITY = "PREVIEW_NON_AUTHORITATIVE_POLICY"


@dataclass(frozen=True)
class DoorwayLane:
    """One centreline slot through a finite selected doorway."""

    circuit_index: int
    flow_role: Literal["SUPPLY", "RETURN"]
    point_mm: tuple[float, float]


@dataclass(frozen=True)
class DoorwayLaneReservation:
    """Capacity proof for a room-side doorway, independent of transit routing."""

    requested_circuit_count: int
    required_lane_count: int
    doorway_width_mm: float
    required_width_mm: float
    valid: bool
    lanes: tuple[DoorwayLane, ...]
    diagnostics: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "requested_circuit_count": self.requested_circuit_count,
            "required_lane_count": self.required_lane_count,
            "doorway_width_mm": round(self.doorway_width_mm, 3),
            "required_width_mm": round(self.required_width_mm, 3),
            "valid": self.valid,
            "lanes": [
                {
                    "circuit_index": lane.circuit_index,
                    "flow_role": lane.flow_role,
                    "point_mm": [round(lane.point_mm[0], 3), round(lane.point_mm[1], 3)],
                }
                for lane in self.lanes
            ],
            "diagnostics": list(self.diagnostics),
        }


def reserve_doorway_lanes(
    doorway_segment_mm: tuple[tuple[float, float], tuple[float, float]],
    circuit_count: int,
    *,
    pipe_outer_diameter_mm: float = 16.0,
    minimum_free_pipe_clearance_mm: float = 16.0,
    edge_clearance_mm: float = 50.0,
) -> DoorwayLaneReservation:
    """Reserve distinct supply/return centreline slots before layout generation.

    A room with ``n`` circuits needs ``2n`` ordered lanes.  The calculation is
    intentionally one-dimensional along the supplied finite doorway segment:
    it proves that the room-side interface has capacity but makes no claim
    about a wall penetration, corridor, or manifold connection.
    """
    if circuit_count < 1 or circuit_count > 5:
        return DoorwayLaneReservation(circuit_count, 0, 0.0, 0.0, False, (), ("CIRCUIT_COUNT_OUT_OF_SUPPORTED_RANGE",))
    if min(pipe_outer_diameter_mm, minimum_free_pipe_clearance_mm, edge_clearance_mm) < 0:
        return DoorwayLaneReservation(circuit_count, 0, 0.0, 0.0, False, (), ("NEGATIVE_DOORWAY_LANE_PARAMETER",))
    start, end = doorway_segment_mm
    dx, dy = float(end[0]) - float(start[0]), float(end[1]) - float(start[1])
    width = hypot(dx, dy)
    lane_count = 2 * circuit_count
    pitch = pipe_outer_diameter_mm + minimum_free_pipe_clearance_mm
    required = 2 * edge_clearance_mm + pipe_outer_diameter_mm + max(0, lane_count - 1) * pitch
    if width <= 0:
        return DoorwayLaneReservation(circuit_count, lane_count, width, required, False, (), ("DOORWAY_SEGMENT_ZERO_LENGTH",))
    if width + 1e-9 < required:
        return DoorwayLaneReservation(circuit_count, lane_count, width, required, False, (), ("DOORWAY_CAPACITY_INSUFFICIENT",))
    ux, uy = dx / width, dy / width
    first_center = edge_clearance_mm + pipe_outer_diameter_mm / 2
    lanes: list[DoorwayLane] = []
    for lane_index in range(lane_count):
        distance = first_center + lane_index * pitch
        circuit_index, role_index = divmod(lane_index, 2)
        lanes.append(DoorwayLane(circuit_index + 1, "SUPPLY" if role_index == 0 else "RETURN", (float(start[0]) + ux * distance, float(start[1]) + uy * distance)))
    return DoorwayLaneReservation(circuit_count, lane_count, width, required, True, tuple(lanes))


@dataclass(frozen=True)
class ContainmentReport:
    max_outside_distance_mm: float
    total_outside_length_mm: float
    outside_segment_count: int
    valid: bool


@dataclass(frozen=True)
class StrategyCandidate:
    strategy: Literal["BIFILAR_SPIRAL", "MEANDER", "HYBRID_PERIMETER_SPIRAL"]
    feasible: bool
    reason: str
    bend_count: int
    spacing_error_mm: float
    containment: ContainmentReport


@dataclass(frozen=True)
class BifilarTopologyReport:
    """Evidence produced by the independent bifilar/ulita topology gate."""

    connected_component_count: int
    endpoint_count: int
    branch_count: int
    self_intersection_count: int
    non_orthogonal_segment_count: int
    zero_length_segment_count: int
    minimum_segment_length_mm: float
    center_hairpin_present: bool
    center_hairpin_segment_count: int
    interleaved_return_present: bool
    containment: ContainmentReport
    bend_constraints_valid: bool
    valid: bool
    duplicate_centerline_length_mm: float = 0.0
    diagnostics: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "continuous_component_count": self.connected_component_count,
            "endpoint_count": self.endpoint_count,
            "branch_count": self.branch_count,
            "self_intersection_count": self.self_intersection_count,
            "non_orthogonal_segment_count": self.non_orthogonal_segment_count,
            "zero_length_segment_count": self.zero_length_segment_count,
            "minimum_segment_length_mm": round(self.minimum_segment_length_mm, 3),
            "center_turn_present": self.center_hairpin_present,
            "center_hairpin_segment_count": self.center_hairpin_segment_count,
            "interleaved_return_present": self.interleaved_return_present,
            "containment_valid": self.containment.valid,
            "max_outside_distance_mm": round(self.containment.max_outside_distance_mm, 3),
            "total_outside_length_mm": round(self.containment.total_outside_length_mm, 3),
            "bend_constraints_valid": self.bend_constraints_valid,
            "duplicate_centerline_length_mm": round(self.duplicate_centerline_length_mm, 3),
            "valid": self.valid,
            "diagnostics": list(self.diagnostics),
        }


def polyline_length(points: Iterable[tuple[float, float]]) -> float:
    pts = list(points)
    return sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def validate_containment(
    points: Iterable[tuple[float, float]],
    allowed_polygon: Iterable[tuple[float, float]],
    tolerance_mm: float = CONTAINMENT_TOLERANCE_MM,
) -> ContainmentReport:
    """Measure line portions outside the allowed polygon without self-certifying.

    The report uses the actual line and polygon objects and exposes outside
    length/count separately, so a caller cannot turn a Boolean into a fake
    coverage claim.
    """
    poly = Polygon(list(allowed_polygon))
    line = LineString(list(points))
    if line.is_empty or not poly.is_valid:
        return ContainmentReport(0.0, 0.0, 0, False)
    outside = line.difference(poly.buffer(tolerance_mm))
    if outside.is_empty:
        return ContainmentReport(0.0, 0.0, 0, True)
    pieces = []
    if outside.geom_type == "LineString":
        pieces = [outside]
    elif outside.geom_type == "MultiLineString":
        pieces = list(outside.geoms)
    length = sum(piece.length for piece in pieces)
    max_distance = _max_outside_excursion_mm(pieces, poly)
    return ContainmentReport(
        max_outside_distance_mm=float(max_distance),
        total_outside_length_mm=float(length),
        outside_segment_count=len(pieces),
        valid=length <= tolerance_mm and max_distance <= tolerance_mm,
    )


def _max_outside_excursion_mm(
    pieces: Iterable[LineString],
    poly: Polygon,
    resolution_mm: float = 0.01,
) -> float:
    """Return how far a route actually leaves ``poly``, measured honestly.

    ``poly.distance(piece)`` returns the *minimum* distance between the two
    geometries, so the previous implementation could never report more than the
    clipping tolerance: a 0.26 m sliver and a 0.9 m excursion both looked like
    1.0 mm.  The excursion that matters is the opposite extreme.

    For every outside piece the smallest ``radius`` with
    ``piece ⊆ poly.buffer(radius)`` is bracketed by bisection, which stays
    correct for notched, L-shaped and otherwise non-convex rooms (a convex
    "distance is maximal at a vertex" shortcut is not valid there: a straight
    strut crossing a notch is far from the polygon in its middle while both
    clipped endpoints sit on the notch walls).
    """
    worst = 0.0
    for piece in pieces:
        # Proven upper bound: every point of the piece is within ``piece.length``
        # of one of its own endpoints.
        high = piece.length + max(
            (poly.distance(Point(coord)) for coord in piece.coords),
            default=0.0,
        )
        low = 0.0
        while high - low > resolution_mm:
            middle = (low + high) / 2.0
            if piece.difference(poly.buffer(middle)).is_empty:
                high = middle
            else:
                low = middle
        worst = max(worst, high)
    return worst


def _compress_collinear(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Remove redundant collinear vertices while retaining every turn."""
    result: list[tuple[int, int]] = []
    for point in points:
        if result and point == result[-1]:
            continue
        result.append(point)
        while len(result) >= 3:
            a, b, c = result[-3:]
            if (b[0] - a[0]) * (c[1] - b[1]) == (b[1] - a[1]) * (c[0] - b[0]):
                result.pop(-2)
            else:
                break
    return result


def _graph_topology(points: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    """Return connected components, endpoints, branches and zero-length count."""
    segments = list(zip(points, points[1:]))
    neighbours: dict[tuple[int, int], set[tuple[int, int]]] = {}
    zero_length = 0
    for first, second in segments:
        neighbours.setdefault(first, set())
        neighbours.setdefault(second, set())
        if first == second:
            zero_length += 1
            continue
        neighbours[first].add(second)
        neighbours[second].add(first)
    unseen = set(neighbours)
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            node = stack.pop()
            for neighbour in neighbours[node]:
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    stack.append(neighbour)
    endpoints = sum(len(values) == 1 for values in neighbours.values())
    branches = sum(len(values) > 2 for values in neighbours.values())
    return components, endpoints, branches, zero_length


def _non_adjacent_intersections(points: list[tuple[int, int]]) -> int:
    """Count true non-adjacent crossings/overlaps in the centerline."""
    line = LineString(points)
    if line.is_empty or line.is_simple:
        return 0
    segments = list(zip(points, points[1:]))
    count = 0
    for index, first in enumerate(segments):
        for other_index in range(index + 2, len(segments)):
            # The shared endpoint of adjacent segments is allowed.  A repeated
            # point on non-adjacent segments is a topology defect.
            second = segments[other_index]
            a = LineString([first[0], first[1]])
            b = LineString([second[0], second[1]])
            if a.intersects(b):
                count += 1
    return count


def _duplicate_segment_overlap_length(points: list[tuple[int, int]]) -> float:
    """Measure positive-length reuse of a centerline segment.

    ``LineString.is_simple`` and point-intersection counts do not expose the
    distinction between a crossing and travelling back over an occupied
    segment.  Compare every non-adjacent pair on the same supporting line so
    partial overlaps and reverse-direction A->B->A traversals are measured.
    """
    segments = list(zip(points, points[1:]))
    overlap = 0.0
    for index, (a, b) in enumerate(segments):
        if a == b:
            continue
        for other_a, other_b in segments[index + 1:]:
            if other_a == other_b:
                continue
            if a[1] == b[1] == other_a[1] == other_b[1]:
                left = max(min(a[0], b[0]), min(other_a[0], other_b[0]))
                right = min(max(a[0], b[0]), max(other_a[0], other_b[0]))
            elif a[0] == b[0] == other_a[0] == other_b[0]:
                left = max(min(a[1], b[1]), min(other_a[1], other_b[1]))
                right = min(max(a[1], b[1]), max(other_a[1], other_b[1]))
            else:
                continue
            if right > left:
                overlap += right - left
    return overlap


def _center_hairpin_candidates(
    points: list[tuple[int, int]],
    bounds: tuple[int, int, int, int],
    spacing_mm: int,
) -> list[tuple[int, int, int]]:
    """Find short opposite parallel legs around a central orthogonal turn."""
    compressed = _compress_collinear(points)
    if len(compressed) < 4:
        return []
    x0, y0, x1, y1 = bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # A center turn may be offset from the exact centroid, but it must still
    # live in the central 70% of the envelope on both axes.
    half_width, half_height = (x1 - x0) * 0.35, (y1 - y0) * 0.35
    candidates: list[tuple[int, int, int]] = []
    for index in range(1, len(compressed) - 2):
        a, b, c, d = compressed[index - 1:index + 3]
        ab = (b[0] - a[0], b[1] - a[1])
        bc = (c[0] - b[0], c[1] - b[1])
        cd = (d[0] - c[0], d[1] - c[1])
        if not ((ab[0] == 0) != (ab[1] == 0) and (bc[0] == 0) != (bc[1] == 0) and (cd[0] == 0) != (cd[1] == 0)):
            continue
        parallel_opposite = (ab[0] == 0 and cd[0] == 0 and ab[1] * cd[1] < 0) or (
            ab[1] == 0 and cd[1] == 0 and ab[0] * cd[0] < 0
        )
        if not parallel_opposite:
            continue
        middle_length = abs(bc[0]) + abs(bc[1])
        if not (max(80, spacing_mm // 2) <= middle_length <= spacing_mm * 2):
            continue
        mx, my = (b[0] + c[0]) / 2, (b[1] + c[1]) / 2
        if abs(mx - cx) <= half_width and abs(my - cy) <= half_height:
            candidates.append((index, middle_length, middle_length))
    return candidates


def _has_interleaved_return(
    points: list[tuple[int, int]],
    bounds: tuple[int, int, int, int],
    spacing_mm: int,
    hairpin_candidates: list[tuple[int, int, int]],
) -> bool:
    """Check that lanes after the center turn return between incoming lanes."""
    if not hairpin_candidates:
        return False
    compressed = _compress_collinear(points)
    hairpin_index = hairpin_candidates[0][0]
    before = compressed[:hairpin_index + 1]
    after = compressed[hairpin_index + 2:]
    if len(before) < 2 or len(after) < 2:
        return False
    def axis_runs(path: list[tuple[int, int]]) -> list[tuple[str, int, int]]:
        runs = []
        for a, b in zip(path, path[1:]):
            length = abs(b[0] - a[0]) + abs(b[1] - a[1])
            if length < spacing_mm:
                continue
            if a[1] == b[1]:
                runs.append(("H", a[1], length))
            elif a[0] == b[0]:
                runs.append(("V", a[0], length))
        return runs
    incoming = axis_runs(before)
    outgoing = axis_runs(after)
    # At least one outgoing lane must sit one pitch inside an incoming lane;
    # this is the material evidence that the return is interleaved rather than
    # a second disconnected contour.
    for axis, coord, _ in outgoing:
        same_axis = [value for a, value, _ in incoming if a == axis]
        if any(0 < abs(coord - value) <= spacing_mm * 1.5 for value in same_axis):
            return True
    return False


def validate_bifilar_topology(
    points: Iterable[tuple[int, int]],
    bounds: tuple[int, int, int, int],
    allowed_polygon: Iterable[tuple[int, int]],
    *,
    spacing_mm: int = 200,
    minimum_bend_radius_mm: int = 80,
) -> BifilarTopologyReport:
    """Independently validate a materialized bifilar route.

    The gate intentionally does not infer a spiral from a strategy label or a
    builder name.  Every acceptance field is measured from the emitted
    centerline and the supplied room boundary.
    """
    raw = [(int(x), int(y)) for x, y in points]
    compressed = _compress_collinear(raw)
    components, endpoints, branches, zero_length = _graph_topology(raw)
    non_orthogonal = sum(
        a[0] != b[0] and a[1] != b[1] for a, b in zip(raw, raw[1:])
    )
    intersections = _non_adjacent_intersections(raw) if raw else 0
    duplicate_overlap = _duplicate_segment_overlap_length(raw) if raw else 0.0
    lengths = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(raw, raw[1:]) if a != b]
    minimum_segment = float(min(lengths, default=0))
    hairpins = _center_hairpin_candidates(compressed, bounds, spacing_mm)
    interleaved = _has_interleaved_return(compressed, bounds, spacing_mm, hairpins)
    containment = validate_containment(raw, allowed_polygon) if raw else ContainmentReport(0, 0, 0, False)
    bend_valid = bool(lengths) and minimum_segment >= minimum_bend_radius_mm
    for index in range(1, len(compressed) - 1):
        before, corner, after = compressed[index - 1], compressed[index], compressed[index + 1]
        incoming = (corner[0] - before[0], corner[1] - before[1])
        outgoing = (after[0] - corner[0], after[1] - corner[1])
        if incoming[0] == 0 and incoming[1] == 0 or outgoing[0] == 0 and outgoing[1] == 0:
            continue
        if incoming[0] != 0 and outgoing[0] != 0 or incoming[1] != 0 and outgoing[1] != 0:
            continue
        if min(hypot(*incoming), hypot(*outgoing)) < 2 * minimum_bend_radius_mm:
            bend_valid = False
    diagnostics: list[str] = []
    if components != 1:
        diagnostics.append("CONNECTED_COMPONENT_GATE_FAILED")
    if endpoints != 2:
        diagnostics.append("ENDPOINT_GATE_FAILED")
    if branches:
        diagnostics.append("BRANCH_GATE_FAILED")
    if intersections:
        diagnostics.append("SELF_INTERSECTION_GATE_FAILED")
    if duplicate_overlap:
        diagnostics.append("DUPLICATE_CENTERLINE_OVERLAP_GATE_FAILED")
    if non_orthogonal:
        diagnostics.append("ORTHOGONALITY_GATE_FAILED")
    if zero_length:
        diagnostics.append("ZERO_LENGTH_SEGMENT_GATE_FAILED")
    if not hairpins:
        diagnostics.append("CENTER_HAIRPIN_GATE_FAILED")
    if not interleaved:
        diagnostics.append("INTERLEAVED_RETURN_GATE_FAILED")
    if not containment.valid:
        diagnostics.append("CONTAINMENT_GATE_FAILED")
    if not bend_valid:
        diagnostics.append("BEND_TANGENT_CLEARANCE_GATE_FAILED")
    valid = not diagnostics and non_orthogonal == 0 and zero_length == 0
    return BifilarTopologyReport(
        connected_component_count=components,
        endpoint_count=endpoints,
        branch_count=branches,
        self_intersection_count=intersections,
        non_orthogonal_segment_count=non_orthogonal,
        zero_length_segment_count=zero_length,
        minimum_segment_length_mm=minimum_segment,
        center_hairpin_present=bool(hairpins),
        center_hairpin_segment_count=2 if hairpins else 0,
        interleaved_return_present=interleaved,
        containment=containment,
        bend_constraints_valid=bend_valid,
        valid=valid,
        duplicate_centerline_length_mm=duplicate_overlap,
        diagnostics=tuple(diagnostics),
    )


def _is_orthogonal(points: list[tuple[float, float]]) -> bool:
    return all(a[0] == b[0] or a[1] == b[1] for a, b in zip(points, points[1:]))


def build_bifilar_spiral(
    bounds: tuple[int, int, int, int],
    spacing_mm: int = 200,
    wall_offset_mm: int = 100,
) -> list[tuple[int, int]]:
    """Build one continuous rectangular inward/outward counter-flow route.

    Every even offset is an inward ring and every odd offset is an outward
    ring.  The centre transition is a real U-turn between the final inward
    ring and the innermost outward ring.  The returned points are one ordered
    centreline; no second decorative polyline is introduced.

    The constructor is intentionally limited to a rectangular envelope.  A
    caller with a notch, obstacle, or non-orthogonal boundary must validate
    the candidate against that exact polygon and fall back to a routed
    serpentine or an explicit impossible result.
    """
    x0, y0, x1, y1 = bounds
    if spacing_mm <= 0 or wall_offset_mm < 0:
        return []
    available_width = x1 - x0 - 2 * wall_offset_mm
    available_height = y1 - y0 - 2 * wall_offset_mm
    width_cells = available_width // spacing_mm
    height_cells = available_height // spacing_mm
    if width_cells < 14 or height_cells < 13:
        return []
    # Four grid cells are needed for the centre U-turn and the two interleaved
    # lanes.  Keeping one extra cell at the outer edge leaves the route inside
    # the wall offset even when the source dimensions are not grid aligned.
    ring_count = (min(width_cells, height_cells) - 1) // 4
    if ring_count < 3:
        return []
    right_edge = x0 + wall_offset_mm + width_cells * spacing_mm
    top_edge = y0 + wall_offset_mm + height_cells * spacing_mm
    inward: list[tuple[int, int, int, int]] = []
    for index in range(ring_count):
        offset = 2 * index * spacing_mm
        inward.append((
            x0 + wall_offset_mm + offset,
            y0 + wall_offset_mm + offset,
            right_edge - offset,
            top_edge - offset,
        ))

    route: list[tuple[int, int]] = [
        (inward[0][2], inward[0][3]),
        (inward[0][0], inward[0][3]),
        (inward[0][0], inward[0][1]),
        (inward[0][2], inward[0][1]),
    ]
    for index in range(1, ring_count):
        previous = inward[index - 1]
        current = inward[index]
        route.extend([
            (previous[2], current[3]),
            (current[0], current[3]),
            (current[0], current[1]),
            (current[2], current[1]),
        ])

    last = inward[-1]
    outward_inner_offset = (2 * (ring_count - 1) + 1) * spacing_mm
    outward_inner = (
        x0 + wall_offset_mm + outward_inner_offset,
        y0 + wall_offset_mm + outward_inner_offset,
        right_edge - outward_inner_offset,
        top_edge - outward_inner_offset,
    )
    # Explicit centre hairpin: leave the final inward ring, turn in the
    # central pocket, and land on the innermost outward lane.
    center_x = last[0] + 3 * spacing_mm
    center_y = last[1] + 3 * spacing_mm
    if center_x >= outward_inner[2] or center_y >= outward_inner[3]:
        return []
    route.extend([
        (last[2], center_y),
        (center_x, center_y),
        (center_x, center_y - spacing_mm),
        (outward_inner[2], center_y - spacing_mm),
    ])

    outward: list[tuple[int, int, int, int]] = []
    for index in range(ring_count - 1, -1, -1):
        offset = (2 * index + 1) * spacing_mm
        outward.append((
            x0 + wall_offset_mm + offset,
            y0 + wall_offset_mm + offset,
            right_edge - offset,
            top_edge - offset,
        ))
    for index, (left, bottom, right, top) in enumerate(outward):
        route.extend([(right, bottom), (left, bottom), (left, top)])
        if index < len(outward) - 1:
            route.append((outward[index + 1][2], top))
        else:
            route.append((right, top))
    return route


def build_meander(bounds: tuple[int, int, int, int], spacing_mm: int = 200, wall_offset_mm: int = 100) -> list[tuple[int, int]]:
    """Build one continuous orthogonal serpentine loop for a rectangular zone."""
    x0, y0, x1, y1 = bounds
    left, right = x0 + wall_offset_mm, x1 - wall_offset_mm
    bottom, top = y0 + wall_offset_mm, y1 - wall_offset_mm
    if right - left < 2 * wall_offset_mm or top - bottom < spacing_mm:
        return []
    ys = list(range(bottom, top + 1, spacing_mm))
    if ys[-1] != top and top - ys[-1] >= 80:
        ys.append(top)
    points = []
    for index, y in enumerate(ys):
        row = [(left, y), (right, y)] if index % 2 == 0 else [(right, y), (left, y)]
        if points:
            connector = (row[0][0], points[-1][1])
            if points[-1] != connector:
                points.append(connector)
        for point in row:
            if not points or points[-1] != point:
                points.append(point)
    return points


def build_polygon_meander(
    boundary: Iterable[tuple[int, int]],
    spacing_mm: int = 200,
    wall_offset_mm: int = 100,
) -> list[tuple[int, int]]:
    """Build a conservative scanline meander for a simple observed polygon.

    This is a geometry-only fallback for a room with a diagonal or stepped
    observed edge, such as the area under the first-floor stair.  Each row is
    clipped to the polygon and adjacent rows are connected only when the
    resulting centerline stays inside the same buffered boundary.
    """
    polygon = Polygon(list(boundary))
    if polygon.is_empty or not polygon.is_valid:
        return []
    x0, y0, x1, y1 = polygon.bounds
    rows: list[tuple[tuple[int, int], tuple[int, int]]] = []
    y = int(round(y0 + wall_offset_mm))
    last_y = int(round(y1 - wall_offset_mm))
    while y <= last_y:
        if last_y - y < 80 and rows:
            break
        scan = LineString([(x0 - wall_offset_mm * 2, y), (x1 + wall_offset_mm * 2, y)])
        intersections = polygon.intersection(scan)
        pieces = [intersections] if intersections.geom_type == "LineString" else (
            list(intersections.geoms) if intersections.geom_type == "MultiLineString" else []
        )
        if pieces:
            # A room face should have one interval at each sampled row. If a
            # row crosses multiple intervals, use the longest one and retain
            # the ambiguity in the caller's diagnostics.
            segment = max(pieces, key=lambda item: item.length)
            left, _, right, _ = segment.bounds
            start = (int(round(left + wall_offset_mm)), y)
            end = (int(round(right - wall_offset_mm)), y)
            if end[0] - start[0] >= spacing_mm:
                rows.append((start, end))
        y += spacing_mm
    points: list[tuple[int, int]] = []
    allowed = polygon.buffer(1.0)
    for index, (start, end) in enumerate(rows):
        row = (start, end) if index % 2 == 0 else (end, start)
        if points:
            connector = LineString([points[-1], row[0]])
            if not allowed.covers(connector):
                return []
            points.append(row[0])
        else:
            points.append(row[0])
        points.append(row[1])
    if len(points) < 2:
        return []
    return points


def classify_strategies(
    points: list[tuple[int, int]],
    room_polygon: Iterable[tuple[int, int]],
    route_length_mm: float,
    spacing_mm: int = 200,
    wall_offset_mm: int = 100,
) -> tuple[StrategyCandidate, ...]:
    poly = Polygon(list(room_polygon))
    bounds = tuple(int(v) for v in poly.bounds)
    spiral = build_bifilar_spiral(bounds, spacing_mm, wall_offset_mm)
    spiral_report = validate_containment(spiral, room_polygon) if spiral else ContainmentReport(0, 0, 0, False)
    rectangular = poly.area / max((bounds[2] - bounds[0]) * (bounds[3] - bounds[1]), 1) > 0.965
    topology = validate_bifilar_topology(
        spiral,
        bounds,
        room_polygon,
        spacing_mm=spacing_mm,
        minimum_bend_radius_mm=80,
    ) if spiral else None
    spiral_ok = bool(topology and topology.valid)
    spiral_reason = "materialized center hairpin and interleaved return" if spiral_ok else (
        "topology gate failed: " + ", ".join(topology.diagnostics)
        if topology else "empty spiral candidate"
    )
    meander_report = validate_containment(points, room_polygon)
    candidates = [
        StrategyCandidate("BIFILAR_SPIRAL", spiral_ok, spiral_reason, max(0, len(spiral) - 1), 0.0, spiral_report),
        StrategyCandidate("MEANDER", meander_report.valid, "dense sweep candidate" if meander_report.valid else "containment gate failed", max(0, len(points) - 2), 0.0, meander_report),
    ]
    if rectangular and spiral_ok:
        candidates.append(StrategyCandidate("HYBRID_PERIMETER_SPIRAL", True, "geometry candidate; no thermal cold-zone claim", candidates[0].bend_count + 6, 0.0, spiral_report))
    return tuple(candidates)


def choose_strategy(candidates: Iterable[StrategyCandidate], route_length_mm: float) -> tuple[str, str]:
    feasible = [c for c in candidates if c.feasible]
    if not feasible:
        return "UNRESOLVED", "no candidate passed independent containment"
    # Prefer a true spiral for regular rooms; use meander for narrow/irregular
    # rooms.  Length is a tie-breaker, never a thermal score.
    for name in ("BIFILAR_SPIRAL", "HYBRID_PERIMETER_SPIRAL", "MEANDER"):
        for candidate in feasible:
            if candidate.strategy == name:
                return name, candidate.reason
    return feasible[0].strategy, feasible[0].reason


def split_required(route_length_m: float, transit_allowance_m: float = 8.0) -> bool:
    return route_length_m + transit_allowance_m > MAX_TOTAL_CIRCUIT_LENGTH_M


def split_polyline_by_length(
    points: Iterable[tuple[int, int]],
    circuit_count: int,
) -> list[list[tuple[int, int]]]:
    """Partition an existing route into contiguous centerline circuits.

    The partition is made on the supplied polyline itself, rather than on a
    bounding box.  This preserves the measured non-rectangular room boundary,
    avoids inventing wall geometry, and gives every resulting circuit a real
    endpoint at either an existing vertex or an interpolated point on a real
    segment.
    """
    pts = [(int(x), int(y)) for x, y in points]
    if circuit_count <= 1 or len(pts) < 2:
        return [pts] if pts else []
    segments = [hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    total = sum(segments)
    if total <= 0:
        return [pts]
    target = total / circuit_count
    routes: list[list[tuple[int, int]]] = []
    current: list[tuple[int, int]] = [pts[0]]
    consumed = 0.0
    next_cut = target
    for index, ((ax, ay), (bx, by), seg_len) in enumerate(zip(pts, pts[1:], segments)):
        start = 0.0
        while consumed + seg_len - start >= next_cut - 1e-9 and len(routes) < circuit_count - 1:
            cut = next_cut - consumed
            fraction = 0.0 if seg_len == 0 else cut / seg_len
            point = (int(round(ax + (bx - ax) * fraction)), int(round(ay + (by - ay) * fraction)))
            if current[-1] != point:
                current.append(point)
            routes.append(current)
            current = [point]
            start = cut
            next_cut += target
        if start < seg_len:
            point = (bx, by)
            if current[-1] != point:
                current.append(point)
        consumed += seg_len
    if current[-1] != pts[-1]:
        current.append(pts[-1])
    routes.append(current)
    return [route for route in routes if len(route) >= 2 and polyline_length(route) > 0]


def validate_circuit_split(
    routes: Iterable[Iterable[tuple[int, int]]],
    *,
    authorized_endpoints: Iterable[tuple[int, int]] = (),
) -> dict[str, Any]:
    """Check whether fragments can stand as independent UFH circuits.

    An arclength cut through one pipe creates two fragments sharing the cut
    point.  That point is not a collector connection and cannot be promoted to
    two circuits.  A split is accepted only when every fragment endpoint is
    explicitly authorized and no endpoint is shared by sibling routes.
    """
    normalized = [[(int(x), int(y)) for x, y in route] for route in routes]
    endpoints = [point for route in normalized for point in (route[0], route[-1]) if route]
    authorized = set(authorized_endpoints)
    counts: dict[tuple[int, int], int] = {}
    for point in endpoints:
        counts[point] = counts.get(point, 0) + 1
    shared = sorted(point for point, count in counts.items() if count > 1)
    unauthorized = sorted(point for point in endpoints if point not in authorized)
    valid = bool(normalized) and not shared and not unauthorized
    diagnostics = []
    if shared:
        diagnostics.append("SHARED_INTERNAL_SPLIT_ENDPOINT")
    if unauthorized:
        diagnostics.append("SPLIT_ENDPOINT_HAS_NO_AUTHORIZED_COLLECTOR_PATH")
    return {
        "valid": valid,
        "route_count": len(normalized),
        "endpoint_count": len(endpoints),
        "shared_endpoints": [list(point) for point in shared],
        "unauthorized_endpoints": [list(point) for point in unauthorized],
        "diagnostics": diagnostics,
    }

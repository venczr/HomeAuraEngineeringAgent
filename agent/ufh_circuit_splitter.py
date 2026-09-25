"""Split a concave room into independent UFH circuits that each fit 90 m.

This is a geometry-level splitter: it divides a room's allowed area into
rectangular sub-zones (at the geometry level, not by cutting a finished long
polyline), builds one bifilar spiral per zone, and jointly validates the
result.  Transit to the collector is estimated as a Manhattan distance from
each terminal to a synthetic collector point; it is *not* a physical route, so
the returned totals are ``ESTIMATED`` and never ``FULL_CIRCUIT_VALID``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from shapely.geometry import LineString, Polygon

from agent.ufh_bend_geometry import build_rounded_centerline, validate_rounded_centerline
from agent.ufh_polygonal_spiral import split_concave_into_rectangles
from agent.ufh_spiral_kernel import build_accessible_bifilar_spiral


PITCH_MM = 200.0
WALL_OFFSET_MM = 100.0
PIPE_RADIUS_MM = 8.0
LIMIT_MM = 90_000.0
MIN_CLEARANCE_MM = 32.0  # pipe OD 16 + free clearance 16


@dataclass
class CircuitCandidate:
    circuit_id: str
    zone_polygon: Polygon
    centerline_mm: list[tuple[float, float]]
    coverage_length_mm: float
    terminal_supply_mm: tuple[float, float]
    terminal_return_mm: tuple[float, float]
    estimated_transit_mm: float
    estimated_total_mm: float
    geometry_valid: bool
    length_valid: bool
    supply_route_mm: list[tuple[float, float]] = field(default_factory=list)
    return_route_mm: list[tuple[float, float]] = field(default_factory=list)
    transit_valid: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "circuit_id": self.circuit_id,
            "zone_bounds": [round(v, 2) for v in self.zone_polygon.bounds],
            "coverage_length_mm": round(self.coverage_length_mm, 1),
            "terminal_supply_mm": [round(v, 2) for v in self.terminal_supply_mm],
            "terminal_return_mm": [round(v, 2) for v in self.terminal_return_mm],
            "estimated_transit_mm": round(self.estimated_transit_mm, 1),
            "estimated_total_mm": round(self.estimated_total_mm, 1),
            "geometry_valid": self.geometry_valid,
            "length_valid": self.length_valid,
            "transit_valid": self.transit_valid,
        }


@dataclass
class CircuitSplitResult:
    circuits: list[CircuitCandidate]
    joint_intersections: list[str]
    min_inter_circuit_clearance_mm: float
    joint_layout_valid: bool
    coverage_area_m2: float
    uncovered_area_m2: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "circuits": [c.as_dict() for c in self.circuits],
            "joint_intersections": self.joint_intersections,
            "min_inter_circuit_clearance_mm": round(self.min_inter_circuit_clearance_mm, 2),
            "joint_layout_valid": self.joint_layout_valid,
            "coverage_area_m2": round(self.coverage_area_m2, 3),
            "uncovered_area_m2": round(self.uncovered_area_m2, 3),
        }


def _split_rectangle_into_bands(
    rect: Polygon, n_bands: int, *, axis: str = "y"
) -> list[Polygon]:
    minx, miny, maxx, maxy = rect.bounds
    bands: list[Polygon] = []
    if axis == "y":
        step = (maxy - miny) / n_bands
        for i in range(n_bands):
            y0, y1 = miny + i * step, miny + (i + 1) * step
            bands.append(Polygon([(minx, y0), (maxx, y0), (maxx, y1), (minx, y1)]))
    else:
        step = (maxx - minx) / n_bands
        for i in range(n_bands):
            x0, x1 = minx + i * step, minx + (i + 1) * step
            bands.append(Polygon([(x0, miny), (x1, miny), (x1, maxy), (x0, maxy)]))
    return bands


def _manhattan(a: tuple[float, float], b: tuple[float, float]) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def build_independent_circuits(
    l_shape: Polygon,
    collector_xy: tuple[float, float],
    *,
    pitch_mm: float = PITCH_MM,
    limit_mm: float = LIMIT_MM,
) -> CircuitSplitResult:
    """Build independent bifilar circuits that tile an L-shape within ``limit_mm``."""
    rectangles = split_concave_into_rectangles(l_shape)
    if rectangles is None or len(rectangles) != 2:
        raise ValueError("expected a single-reflex (L-shaped) room")
    vertical, horizontal = rectangles
    # choose band counts so each band's coverage + estimated transit fits 90 m
    # Split the vertical arm into vertical strips (along x) so that every
    # circuit's terminals face the bottom wall (y=0) and can be served by a
    # single bottom collector without crossing another zone's coverage.
    vertical_bands = _split_rectangle_into_bands(vertical, 3, axis="x")
    horizontal_bands = _split_rectangle_into_bands(horizontal, 2, axis="x")
    zones = [(f"V{i+1}", z) for i, z in enumerate(vertical_bands)]
    zones += [(f"H{i+1}", z) for i, z in enumerate(horizontal_bands)]

    circuits: list[CircuitCandidate] = []
    for zone_id, zone in zones:
        minx, miny, maxx, maxy = zone.bounds
        centerline = [
            (float(x), float(y))
            for x, y in build_accessible_bifilar_spiral(
                (minx + WALL_OFFSET_MM + PIPE_RADIUS_MM,
                 miny + WALL_OFFSET_MM + PIPE_RADIUS_MM,
                 maxx - WALL_OFFSET_MM - PIPE_RADIUS_MM,
                 maxy - WALL_OFFSET_MM - PIPE_RADIUS_MM),
                spacing_mm=pitch_mm, minimum_bend_radius_mm=80.0,
            )
        ]
        if len(centerline) < 4:
            circuits.append(CircuitCandidate(
                zone_id, zone, [], 0.0, (0.0, 0.0), (0.0, 0.0),
                0.0, 0.0, False, False, [], [], False,
            ))
            continue
        report = validate_rounded_centerline(
            centerline, list(zone.exterior.coords),
            bend_radius_mm=80.0, pipe_outer_radius_mm=PIPE_RADIUS_MM, samples_per_quarter=4,
        )
        coverage = sum(
            math.hypot(centerline[i][0] - centerline[i - 1][0], centerline[i][1] - centerline[i - 1][1])
            for i in range(1, len(centerline))
        )
        supply_terminal = centerline[0]
        return_terminal = centerline[-1]
        transit = _manhattan(supply_terminal, collector_xy) + _manhattan(return_terminal, collector_xy)
        total = coverage + transit
        # supply/return are straight candidate segments to the synthetic collector,
        # kept as geometry-only candidates (not physical transit)
        supply_route = [collector_xy, supply_terminal]
        return_route = [return_terminal, collector_xy]
        circuits.append(CircuitCandidate(
            zone_id, zone, centerline, coverage,
            supply_terminal, return_terminal, transit, total,
            geometry_valid=report.valid and LineString(centerline).is_simple,
            length_valid=total <= limit_mm,
            supply_route_mm=[(float(x), float(y)) for x, y in supply_route],
            return_route_mm=[(float(x), float(y)) for x, y in return_route],
            transit_valid=False,  # straight candidates are not physical transit
        ))

    # joint validation
    intersections: list[str] = []
    min_clearance = float("inf")
    for i in range(len(circuits)):
        for j in range(i + 1, len(circuits)):
            a = LineString(circuits[i].centerline_mm)
            b = LineString(circuits[j].centerline_mm)
            if a.intersects(b):
                intersections.append(f"{circuits[i].circuit_id} x {circuits[j].circuit_id}")
            min_clearance = min(min_clearance, a.distance(b))
    if min_clearance == float("inf"):
        min_clearance = 0.0
    joint_valid = not intersections and min_clearance >= MIN_CLEARANCE_MM

    # coverage: sum of zone areas vs the L-shape area (wall offsets are the only
    # systematic gap; the zones tile the L-shape exactly)
    zone_area = sum(c.zone_polygon.area for c in circuits) / 1e6
    uncovered = max(0.0, l_shape.area / 1e6 - zone_area)
    return CircuitSplitResult(
        circuits=circuits,
        joint_intersections=intersections,
        min_inter_circuit_clearance_mm=min_clearance,
        joint_layout_valid=joint_valid,
        coverage_area_m2=zone_area,
        uncovered_area_m2=uncovered,
    )


def measure_pipe_coverage(
    result: CircuitSplitResult,
    room: Polygon,
    *,
    half_pitch_mm: float = 100.0,
) -> dict[str, Any]:
    """Measure the R80-rounded *spiral* coverage (union of pipe bands) vs room.

    Coverage counts only the heating spirals, rounded at R80 (the exact
    geometry the validation measures); transit to the collector is *not*
    heating and is excluded.  ``half_pitch_mm`` is the half pipe pitch.
    """
    union = None
    for circuit in result.circuits:
        rounded = build_rounded_centerline(
            circuit.centerline_mm, bend_radius_mm=80.0, samples_per_quarter=24,
        )
        band = LineString(rounded.points).buffer(half_pitch_mm)
        union = band if union is None else union.union(band)
    covered = union.intersection(room)
    room_area = room.area
    gap = room.difference(covered)
    return {
        "room_area_m2": round(room_area / 1e6, 3),
        "covered_area_m2": round(covered.area / 1e6, 3),
        "gap_area_m2": round(gap.area / 1e6, 3),
        "coverage_ratio": round(covered.area / room_area, 4),
        "gap_ratio": round(gap.area / room_area, 4),
    }


def build_circuits_with_boundaries(
    l_shape: Polygon,
    collector_xy: tuple[float, float],
    *,
    vertical_bounds: tuple[float, float],
    horizontal_bound: float,
    pitch_mm: float = PITCH_MM,
    limit_mm: float = LIMIT_MM,
) -> CircuitSplitResult:
    """Build the five circuits with explicit zone boundaries.

    ``vertical_bounds`` are the two x-cuts of the vertical arm, and
    ``horizontal_bound`` the single x-cut of the horizontal arm.  This lets a
    deterministic search shift the internal boundaries (to reduce the spiral
    residual cores) without changing the number of circuits.
    """
    rectangles = split_concave_into_rectangles(l_shape)
    if rectangles is None or len(rectangles) != 2:
        raise ValueError("expected a single-reflex (L-shaped) room")
    vertical, horizontal = rectangles
    vx0, _vy0, vx1, _vy1 = vertical.bounds
    hx0, hy0, hx1, hy1 = horizontal.bounds
    b1, b2 = vertical_bounds
    zones = [
        (f"V1", Polygon([(vx0, _vy0), (b1, _vy0), (b1, _vy1), (vx0, _vy1)])),
        (f"V2", Polygon([(b1, _vy0), (b2, _vy0), (b2, _vy1), (b1, _vy1)])),
        (f"V3", Polygon([(b2, _vy0), (vx1, _vy0), (vx1, _vy1), (b2, _vy1)])),
        (f"H1", Polygon([(hx0, hy0), (horizontal_bound, hy0), (horizontal_bound, hy1), (hx0, hy1)])),
        (f"H2", Polygon([(horizontal_bound, hy0), (hx1, hy0), (hx1, hy1), (horizontal_bound, hy1)])),
    ]

    circuits: list[CircuitCandidate] = []
    for zone_id, zone in zones:
        minx, miny, maxx, maxy = zone.bounds
        centerline = [
            (float(x), float(y))
            for x, y in build_accessible_bifilar_spiral(
                (minx + WALL_OFFSET_MM + PIPE_RADIUS_MM,
                 miny + WALL_OFFSET_MM + PIPE_RADIUS_MM,
                 maxx - WALL_OFFSET_MM - PIPE_RADIUS_MM,
                 maxy - WALL_OFFSET_MM - PIPE_RADIUS_MM),
                spacing_mm=pitch_mm, minimum_bend_radius_mm=80.0,
            )
        ]
        if len(centerline) < 4:
            circuits.append(CircuitCandidate(
                zone_id, zone, [], 0.0, (0.0, 0.0), (0.0, 0.0),
                0.0, 0.0, False, False, [], [], False,
            ))
            continue
        report = validate_rounded_centerline(
            centerline, list(zone.exterior.coords),
            bend_radius_mm=80.0, pipe_outer_radius_mm=PIPE_RADIUS_MM, samples_per_quarter=4,
        )
        coverage = sum(
            math.hypot(centerline[i][0] - centerline[i - 1][0], centerline[i][1] - centerline[i - 1][1])
            for i in range(1, len(centerline))
        )
        supply_terminal = centerline[0]
        return_terminal = centerline[-1]
        transit = _manhattan(supply_terminal, collector_xy) + _manhattan(return_terminal, collector_xy)
        total = coverage + transit
        circuits.append(CircuitCandidate(
            zone_id, zone, centerline, coverage,
            supply_terminal, return_terminal, transit, total,
            geometry_valid=report.valid and LineString(centerline).is_simple,
            length_valid=total <= limit_mm,
        ))

    intersections: list[str] = []
    min_clearance = float("inf")
    for i in range(len(circuits)):
        for j in range(i + 1, len(circuits)):
            a = LineString(circuits[i].centerline_mm)
            b = LineString(circuits[j].centerline_mm)
            if a.intersects(b):
                intersections.append(f"{circuits[i].circuit_id} x {circuits[j].circuit_id}")
            min_clearance = min(min_clearance, a.distance(b))
    if min_clearance == float("inf"):
        min_clearance = 0.0
    joint_valid = not intersections and min_clearance >= MIN_CLEARANCE_MM
    return CircuitSplitResult(
        circuits=circuits,
        joint_intersections=intersections,
        min_inter_circuit_clearance_mm=min_clearance,
        joint_layout_valid=joint_valid,
        coverage_area_m2=sum(c.zone_polygon.area for c in circuits) / 1e6,
        uncovered_area_m2=max(0.0, l_shape.area / 1e6 - sum(c.zone_polygon.area for c in circuits) / 1e6),
    )


__all__ = [
    "CircuitCandidate",
    "CircuitSplitResult",
    "build_independent_circuits",
    "build_circuits_with_boundaries",
    "measure_pipe_coverage",
]

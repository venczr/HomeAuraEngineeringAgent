"""Rounded centerline geometry for physical UFH bend checks.

The legacy route remains an orthogonal centerline for compatibility.  This
module derives a second, explicit centerline with quarter-circle fillets at
orthogonal corners and validates that derived geometry against the room's
safe area.  It never promotes a rounded path to a manifold-connected circuit.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, hypot, pi, sin
from typing import Iterable

from shapely.geometry import LineString, Polygon


@dataclass(frozen=True)
class RoundedCenterline:
    points: tuple[tuple[float, float], ...]
    length_mm: float
    bend_count: int
    valid: bool
    diagnostics: tuple[str, ...] = ()
    svg_path_data: str = ""


@dataclass(frozen=True)
class RoundedBendReport:
    valid: bool
    geometry_valid: bool
    topology_valid: bool
    bend_valid: bool
    radius_mm: float
    outer_radius_mm: float
    rounded_length_mm: float
    straight_centerline_length_mm: float
    bend_count: int
    minimum_non_adjacent_clearance_mm: float | None
    rounded_points: tuple[tuple[float, float], ...]
    diagnostics: tuple[str, ...] = ()
    svg_path_data: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "BEND_GEOMETRY_VALID": self.bend_valid,
            "GEOMETRY_VALID": self.geometry_valid,
            "TOPOLOGY_VALID": self.topology_valid,
            "valid": self.valid,
            "radius_mm": self.radius_mm,
            "outer_radius_mm": self.outer_radius_mm,
            "rounded_length_mm": round(self.rounded_length_mm, 3),
            "straight_centerline_length_mm": round(self.straight_centerline_length_mm, 3),
            "bend_count": self.bend_count,
            "minimum_non_adjacent_clearance_mm": None if self.minimum_non_adjacent_clearance_mm is None else round(self.minimum_non_adjacent_clearance_mm, 3),
            "rounded_points": [[round(x, 3), round(y, 3)] for x, y in self.rounded_points],
            "svg_path_data": self.svg_path_data,
            "diagnostics": list(self.diagnostics),
        }


def _unit(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = hypot(dx, dy)
    return (dx / length, dy / length) if length else (0.0, 0.0)


def _is_collinear(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    return (b[0] - a[0]) * (c[1] - b[1]) == (b[1] - a[1]) * (c[0] - b[0])


def build_rounded_centerline(
    points: Iterable[tuple[float, float]],
    *,
    bend_radius_mm: float = 80.0,
    samples_per_quarter: int = 12,
) -> RoundedCenterline:
    raw: list[tuple[float, float]] = []
    for x, y in points:
        p = (float(x), float(y))
        if not raw or p != raw[-1]:
            raw.append(p)
    if len(raw) < 2 or bend_radius_mm <= 0:
        return RoundedCenterline(tuple(raw), 0.0, 0, False, ("EMPTY_OR_INVALID_CENTERLINE",))
    diagnostics: list[str] = []
    corners: dict[int, tuple[tuple[float, float], tuple[float, float], tuple[float, float], float]] = {}
    bend_count = 0
    for index in range(1, len(raw) - 1):
        before, corner, after = raw[index - 1], raw[index], raw[index + 1]
        incoming = _unit(before, corner)
        outgoing = _unit(corner, after)
        if incoming == (0.0, 0.0) or outgoing == (0.0, 0.0) or _is_collinear(before, corner, after):
            continue
        if incoming[0] != 0 and outgoing[0] != 0 or incoming[1] != 0 and outgoing[1] != 0:
            diagnostics.append("NON_ORTHOGONAL_BEND")
            continue
        entry = (corner[0] - incoming[0] * bend_radius_mm, corner[1] - incoming[1] * bend_radius_mm)
        exit = (corner[0] + outgoing[0] * bend_radius_mm, corner[1] + outgoing[1] * bend_radius_mm)
        cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
        if cross > 0:
            center = (entry[0] - incoming[1] * bend_radius_mm, entry[1] + incoming[0] * bend_radius_mm)
            sweep = pi / 2
        else:
            center = (entry[0] + incoming[1] * bend_radius_mm, entry[1] - incoming[0] * bend_radius_mm)
            sweep = -pi / 2
        corners[index] = (entry, exit, center, sweep)
        bend_count += 1
        if min(hypot(corner[0] - before[0], corner[1] - before[1]), hypot(after[0] - corner[0], after[1] - corner[1])) < 2 * bend_radius_mm:
            diagnostics.append("BEND_TANGENT_CLEARANCE_VIOLATION")
    # A straight leg shared by two adjacent turns must contain both tangent
    # trims. This is the physical clearance condition for the actual fillets;
    # checking each raw leg against 2R alone is overly conservative.
    for index, (start, end) in enumerate(zip(raw, raw[1:])):
        trim = (bend_radius_mm if index in corners else 0.0) + (bend_radius_mm if index + 1 in corners else 0.0)
        segment_length = hypot(end[0] - start[0], end[1] - start[1])
        if trim > segment_length + 1e-9:
            diagnostics.append("BEND_TANGENT_CLEARANCE_VIOLATION")
    if diagnostics:
        # Keep the derived path for diagnostics, but mark it invalid.
        pass
    rounded: list[tuple[float, float]] = [raw[0]]
    svg_commands = [f"M {raw[0][0]:.6f},{raw[0][1]:.6f}"]
    for index in range(1, len(raw) - 1):
        if index not in corners:
            rounded.append(raw[index])
            svg_commands.append(f"L {raw[index][0]:.6f},{raw[index][1]:.6f}")
            continue
        entry, exit, center, sweep = corners[index]
        if rounded[-1] != entry:
            rounded.append(entry)
            svg_commands.append(f"L {entry[0]:.6f},{entry[1]:.6f}")
        start_angle = atan2(entry[1] - center[1], entry[0] - center[0])
        for step in range(1, max(2, samples_per_quarter) + 1):
            if step == max(2, samples_per_quarter):
                rounded.append(exit)
            else:
                angle = start_angle + sweep * step / max(2, samples_per_quarter)
                rounded.append((center[0] + bend_radius_mm * cos(angle), center[1] + bend_radius_mm * sin(angle)))
        if rounded[-1] != exit:
            rounded.append(exit)
        svg_commands.append(f"A {bend_radius_mm:.6f},{bend_radius_mm:.6f} 0 0 {1 if sweep > 0 else 0} {exit[0]:.6f},{exit[1]:.6f}")
    rounded.append(raw[-1])
    svg_commands.append(f"L {raw[-1][0]:.6f},{raw[-1][1]:.6f}")
    # The rendered points approximate each quarter-circle with chords, but the
    # engineering length must be the length of the actual tangent/arc model.
    # Each fillet removes two R tangent pieces from the sharp polyline and
    # replaces them with a quarter arc of length pi*R/2.  Deriving the value
    # from the source polyline avoids accumulating a chord-sampling error (and
    # avoids the old bug that subtracted only one sampled chord per arc).
    sharp_length = sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(raw, raw[1:]))
    exact_length = sharp_length - bend_count * 2 * bend_radius_mm + bend_count * (pi / 2 * bend_radius_mm)
    return RoundedCenterline(tuple(rounded), exact_length, bend_count, not diagnostics, tuple(dict.fromkeys(diagnostics)), " ".join(svg_commands))


def validate_rounded_centerline(
    points: Iterable[tuple[float, float]],
    allowed_polygon: Iterable[tuple[float, float]],
    *,
    bend_radius_mm: float = 80.0,
    pipe_outer_radius_mm: float = 8.0,
    obstacles: Iterable[Iterable[tuple[float, float]]] = (),
    samples_per_quarter: int = 12,
) -> RoundedBendReport:
    raw = [(float(x), float(y)) for x, y in points]
    rounded = build_rounded_centerline(raw, bend_radius_mm=bend_radius_mm, samples_per_quarter=samples_per_quarter)
    polygon = Polygon(list(allowed_polygon))
    # Chord samples lie inside the true arc. Include the maximum sagitta in
    # the containment margin so the exact SVG arc is safe as well.
    sample_count = max(2, samples_per_quarter)
    arc_sagitta = bend_radius_mm * (1 - cos(pi / (4 * sample_count)))
    safe = polygon.buffer(-(pipe_outer_radius_mm + arc_sagitta)) if polygon.is_valid else Polygon()
    line = LineString(rounded.points) if len(rounded.points) >= 2 else LineString()
    diagnostics = list(rounded.diagnostics)
    geometry_valid = bool(not line.is_empty and not safe.is_empty and safe.covers(line))
    if not geometry_valid:
        diagnostics.append("ROUNDED_CENTERLINE_OUTSIDE_PIPE_SAFE_AREA")
    for obstacle in obstacles:
        obstacle_poly = Polygon(list(obstacle))
        if line.intersects(obstacle_poly.buffer(pipe_outer_radius_mm + arc_sagitta)):
            diagnostics.append("ROUNDED_CENTERLINE_OBSTACLE_CLEARANCE_VIOLATION")
            geometry_valid = False
    min_clearance: float | None = None
    parts = [LineString([rounded.points[i], rounded.points[i + 1]]) for i in range(len(rounded.points) - 1)]
    clearances: list[float] = []
    separation_window = max(4, 2 * (samples_per_quarter + 1))
    for index, first in enumerate(parts):
        for other in parts[index + separation_window:]:
            distance = first.distance(other)
            clearances.append(distance)
    if clearances:
        min_clearance = min(clearances)
        if min_clearance < 2 * pipe_outer_radius_mm + 2 * arc_sagitta:
            diagnostics.append("ROUNDED_CENTERLINE_PIPE_CLEARANCE_VIOLATION")
    topology_valid = bool(rounded.points and line.is_simple and rounded.points[0] == raw[0] and rounded.points[-1] == raw[-1])
    if not topology_valid:
        diagnostics.append("ROUNDED_CENTERLINE_TOPOLOGY_INVALID")
    bend_valid = rounded.valid and not any(code.startswith("ROUNDED_CENTERLINE_") or code.startswith("BEND_") or code == "NON_ORTHOGONAL_BEND" for code in diagnostics)
    return RoundedBendReport(
        valid=bool(geometry_valid and topology_valid and bend_valid),
        geometry_valid=geometry_valid,
        topology_valid=topology_valid,
        bend_valid=bend_valid,
        radius_mm=float(bend_radius_mm),
        outer_radius_mm=float(pipe_outer_radius_mm),
        rounded_length_mm=rounded.length_mm,
        straight_centerline_length_mm=sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(raw, raw[1:])),
        bend_count=rounded.bend_count,
        minimum_non_adjacent_clearance_mm=min_clearance,
        rounded_points=rounded.points,
        diagnostics=tuple(dict.fromkeys(diagnostics)),
        svg_path_data=rounded.svg_path_data,
    )


__all__ = ["RoundedCenterline", "RoundedBendReport", "build_rounded_centerline", "validate_rounded_centerline"]

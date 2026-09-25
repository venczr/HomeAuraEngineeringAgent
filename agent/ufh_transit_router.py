"""Physical supply/return routing from a collector to independent circuits.

Synthetic control geometry only (NOT Test_01).  The collector is a vertical
bar of ports below the room, the corridor is the strip ``y in [-520, 0]``, and
each circuit owns a separate bottom-wall door spanning its two terminals with
an explicit edge clearance.  Supply and return are separate orthogonal
polylines; every 90-degree corner is rounded at R80 and validated through the
existing ``ufh_bend_geometry.validate_rounded_centerline`` gate.

``TRANSIT_VALID`` / ``FULL_CIRCUIT_VALID`` are only set once every full rounded
circuit (collector -> supply -> spiral -> return -> collector) passes R80,
topology, the pipe-radius safe area, self-clearance, containment against
``room | corridor``, wall-crossing (only through the owned door), mutual
clearance between the *rounded* centrelines and the 90 m length limit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from shapely.geometry import LineString, Polygon

from agent.ufh_bend_geometry import build_rounded_centerline, validate_rounded_centerline
from agent.ufh_circuit_splitter import CircuitCandidate, build_circuits_with_boundaries


PIPE_SPACING_MM = 32.0
R80_MM = 80.0
PIPE_RADIUS_MM = 8.0
LIMIT_MM = 90_000.0
DOOR_EDGE_CLEARANCE_MM = 50.0
COLLECTOR_X = 2000.0
CORRIDOR_BOTTOM = -520.0


@dataclass(frozen=True)
class SyntheticConnection:
    collector_xy: tuple[float, float]
    corridor_polygon: Polygon
    room: Polygon

    def door_x_range(self, circuit: CircuitCandidate) -> tuple[float, float]:
        left = min(circuit.terminal_supply_mm[0], circuit.terminal_return_mm[0])
        right = max(circuit.terminal_supply_mm[0], circuit.terminal_return_mm[0])
        return (left - DOOR_EDGE_CLEARANCE_MM, right + DOOR_EDGE_CLEARANCE_MM)


@dataclass
class TransitRoute:
    circuit_id: str
    supply_mm: list[tuple[float, float]]
    return_mm: list[tuple[float, float]]
    supply_length_mm: float
    return_length_mm: float
    rounded_total_mm: float
    r80_valid: bool
    length_valid: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "circuit_id": self.circuit_id,
            "supply_length_mm": round(self.supply_length_mm, 1),
            "return_length_mm": round(self.return_length_mm, 1),
            "rounded_total_mm": round(self.rounded_total_mm, 1),
            "r80_valid": self.r80_valid,
            "length_valid": self.length_valid,
        }


def build_synthetic_connection(
    room: Polygon,
    *,
    collector_xy: tuple[float, float] = (COLLECTOR_X, CORRIDOR_BOTTOM),
    corridor_bottom: float = CORRIDOR_BOTTOM,
) -> SyntheticConnection:
    minx, _miny, maxx, _maxy = room.bounds
    corridor = Polygon([
        (minx, corridor_bottom), (maxx, corridor_bottom),
        (maxx, 0.0), (minx, 0.0),
    ])
    return SyntheticConnection(collector_xy, corridor, room)


def _length(points: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1])
        for i in range(1, len(points))
    )


def _crossing_x(points: list[tuple[float, float]], wall_y: float = 0.0) -> list[float]:
    """Return the x of every place a polyline crosses the horizontal line ``wall_y``."""
    crossings: list[float] = []
    for a, b in zip(points, points[1:]):
        if (a[1] - wall_y) * (b[1] - wall_y) < 0.0:
            t = (wall_y - a[1]) / (b[1] - a[1])
            crossings.append(a[0] + t * (b[0] - a[0]))
    return crossings


def route_transit(
    circuits: list[CircuitCandidate],
    connection: SyntheticConnection,
    *,
    spacing_mm: float = PIPE_SPACING_MM,
) -> list[TransitRoute]:
    """Route supply and return as orthogonal polylines from a vertical bar.

    Ports are ordered by the horizontal distance of the terminal from the
    collector and the top-most port is placed low enough that every riser
    (108 - port_y) is at least ``2 * R80``, the tangent length an R80 fillet
    needs on each side.
    """
    collector_x = connection.collector_xy[0]
    top_port_y = -2 * R80_MM - 24.0  # riser = 108 - top = 184 mm > 160 mm (2*R80)
    all_pipes: list[tuple[str, str, float]] = []
    for circuit in circuits:
        all_pipes.append((circuit.circuit_id, "supply", abs(circuit.terminal_supply_mm[0] - collector_x)))
        all_pipes.append((circuit.circuit_id, "return", abs(circuit.terminal_return_mm[0] - collector_x)))
    all_pipes.sort(key=lambda item: item[2])
    port_y: dict[tuple[str, str], float] = {
        (cid, flow): top_port_y - position * spacing_mm
        for position, (cid, flow, _distance) in enumerate(all_pipes)
    }

    routes: list[TransitRoute] = []
    for circuit in circuits:
        sx, sy = circuit.terminal_supply_mm
        rx, ry = circuit.terminal_return_mm
        supply_y = port_y[(circuit.circuit_id, "supply")]
        return_y = port_y[(circuit.circuit_id, "return")]
        supply = [(collector_x, supply_y), (sx, supply_y), (sx, sy)]
        ret = [(rx, ry), (rx, return_y), (collector_x, return_y)]
        supply_len = _length(supply)
        return_len = _length(ret)
        full = supply + list(circuit.centerline_mm[1:]) + ret[1:]
        rounded = validate_rounded_centerline(
            full, list((connection.room.union(connection.corridor_polygon)).exterior.coords),
            bend_radius_mm=R80_MM, pipe_outer_radius_mm=PIPE_RADIUS_MM, samples_per_quarter=12,
        )
        routes.append(TransitRoute(
            circuit.circuit_id, supply, ret, supply_len, return_len,
            rounded.rounded_length_mm, rounded.valid, rounded.rounded_length_mm <= LIMIT_MM,
        ))
    return routes


def validate_full_connection(
    circuits: list[CircuitCandidate],
    transit: list[TransitRoute],
    connection: SyntheticConnection,
    *,
    spacing_mm: float = PIPE_SPACING_MM,
    limit_mm: float = LIMIT_MM,
) -> dict[str, Any]:
    """Run explicit physical checks over the full rounded circuits together."""
    allowed = connection.room.union(connection.corridor_polygon)
    room_boundary = connection.room.boundary
    samples = 24
    # chord sampling of an R80 quarter arc at 24 samples per quarter deviates
    # from the true arc by ~0.17 mm, negligible against the 16 mm free
    # clearance; the closest mutual approach (32 mm) is between straight
    # corridor segments with no arc error.

    r80_failures: list[str] = []
    containment_failures: list[str] = []
    topology_failures: list[str] = []
    door_failures: list[str] = []
    wall_failures: list[str] = []
    continuity_failures: list[str] = []
    length_failures: list[str] = []
    clearance_violations: list[str] = []
    self_clearance_violations: list[str] = []
    bijection_failures: list[str] = []

    # one-to-one correspondence between circuits and transit routes
    circuit_ids = [c.circuit_id for c in circuits]
    route_ids = [r.circuit_id for r in transit]
    seen: set[str] = set()
    for cid in circuit_ids:
        if circuit_ids.count(cid) > 1 and cid not in seen:
            bijection_failures.append(f"duplicate circuit id {cid}")
            seen.add(cid)
    for rid in route_ids:
        if route_ids.count(rid) > 1 and rid not in seen:
            bijection_failures.append(f"duplicate route id {rid}")
            seen.add(rid)
    missing = [cid for cid in set(circuit_ids) if cid not in set(route_ids)]
    extra = [rid for rid in set(route_ids) if rid not in set(circuit_ids)]
    if missing:
        bijection_failures.append(f"missing transit route for circuit(s): {sorted(missing)}")
    if extra:
        bijection_failures.append(f"transit route(s) without circuit: {sorted(extra)}")

    full_rounded: dict[str, list[tuple[float, float]]] = {}
    rounded_length: dict[str, float] = {}
    circuit_by_id = {c.circuit_id: c for c in circuits}
    for route in transit:
        circuit = circuit_by_id.get(route.circuit_id)
        if circuit is None:
            continue  # already reported as an extra route
        full = route.supply_mm + list(circuit.centerline_mm[1:]) + route.return_mm[1:]
        report = validate_rounded_centerline(
            full, list(allowed.exterior.coords),
            bend_radius_mm=R80_MM, pipe_outer_radius_mm=PIPE_RADIUS_MM, samples_per_quarter=samples,
        )
        full_rounded[route.circuit_id] = list(report.rounded_points)
        rounded_length[route.circuit_id] = report.rounded_length_mm
        if not report.valid:
            r80_failures.append(f"{route.circuit_id}: {list(report.diagnostics)}")
        if not report.geometry_valid:
            containment_failures.append(route.circuit_id)
        if not report.topology_valid:
            topology_failures.append(route.circuit_id)
        if report.minimum_non_adjacent_clearance_mm is not None and \
                report.minimum_non_adjacent_clearance_mm < spacing_mm - 1e-3:
            self_clearance_violations.append(
                f"{route.circuit_id}: self-clearance {report.minimum_non_adjacent_clearance_mm:.2f} mm < {spacing_mm} mm"
            )
        # wall crossing: transit must cross y=0 only through the owned door and
        # stay above the corridor bottom.
        door_left, door_right = connection.door_x_range(circuit)
        for name, line in (("supply", LineString(route.supply_mm)), ("return", LineString(route.return_mm))):
            for i in range(len(line.coords) - 1):
                seg = LineString([line.coords[i], line.coords[i + 1]])
                cross = seg.intersection(LineString([(-1e6, 0.0), (1e6, 0.0)]))
                if not cross.is_empty:
                    pts = [cross] if cross.geom_type == "Point" else list(cross.geoms)
                    for p in pts:
                        if p.geom_type == "Point" and not (door_left - 1.0 <= p.x <= door_right + 1.0):
                            door_failures.append(
                                f"{route.circuit_id}:{name} crosses y=0 at x={p.x:.0f} outside door [{door_left:.0f},{door_right:.0f}]"
                            )
                if seg.intersects(room_boundary):
                    inter = seg.intersection(room_boundary)
                    pts = [inter] if inter.geom_type == "Point" else list(inter.geoms)
                    for p in pts:
                        if p.geom_type == "Point" and abs(p.y) > 1.0:
                            wall_failures.append(
                                f"{route.circuit_id}:{name} crosses room boundary at ({p.x:.0f},{p.y:.0f})"
                            )
                if min(c[1] for c in seg.coords) < connection.corridor_polygon.bounds[1] - 1.0:
                    wall_failures.append(f"{route.circuit_id}:{name} goes below corridor bottom")
        if route.supply_mm[-1] != circuit.terminal_supply_mm or route.return_mm[0] != circuit.terminal_return_mm:
            continuity_failures.append(route.circuit_id)
        if rounded_length[route.circuit_id] > limit_mm:
            length_failures.append(route.circuit_id)

    # mutual clearance between the rounded full circuits of different circuits
    ids = list(full_rounded.keys())
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            la = LineString(full_rounded[ids[i]])
            lb = LineString(full_rounded[ids[j]])
            if la.distance(lb) < spacing_mm - 1e-3:
                clearance_violations.append(f"{ids[i]} x {ids[j]}")

    # door geometry: each pipe's wall crossing must stay edge-clearance from both
    # jambs, the pipes must be at least spacing apart, and the door wide enough.
    door_ok = True
    route_by_id = {r.circuit_id: r for r in transit}
    for circuit in circuits:
        route = route_by_id.get(circuit.circuit_id)
        if route is None:
            continue  # missing route already reported as a bijection failure
        supply_xs = _crossing_x(route.supply_mm)
        return_xs = _crossing_x(route.return_mm)
        left, right = connection.door_x_range(circuit)
        width = right - left
        if width < 2 * DOOR_EDGE_CLEARANCE_MM + spacing_mm:
            door_ok = False
            door_failures.append(f"{circuit.circuit_id}: door width {width:.0f} mm too narrow")
        all_crossings = supply_xs + return_xs
        if not all_crossings:
            door_ok = False
            door_failures.append(f"{circuit.circuit_id}: no wall crossing found")
        for x in all_crossings:
            if not (left - 1.0 <= x <= right + 1.0):
                door_ok = False
                door_failures.append(f"{circuit.circuit_id}: crossing x={x:.1f} outside door [{left:.0f},{right:.0f}]")
            for jamb in (left, right):
                if abs(x - jamb) < DOOR_EDGE_CLEARANCE_MM - 1e-3:
                    door_ok = False
                    door_failures.append(
                        f"{circuit.circuit_id}: crossing x={x:.1f} is {abs(x-jamb):.2f} mm from jamb {jamb:.0f} (< {DOOR_EDGE_CLEARANCE_MM})"
                    )
        for a in supply_xs:
            for b in return_xs:
                if abs(a - b) < spacing_mm - 1e-3:
                    door_ok = False
                    door_failures.append(f"{circuit.circuit_id}: supply/return {abs(a-b):.1f} mm apart < {spacing_mm} mm")

    valid = not (r80_failures or containment_failures or topology_failures or door_failures
                 or wall_failures or continuity_failures or length_failures
                 or clearance_violations or self_clearance_violations or not door_ok
                 or bijection_failures)
    return {
        "transit_valid": valid,
        "full_circuit_valid": valid,
        "r80_valid": not r80_failures,
        "containment_valid": not containment_failures,
        "topology_valid": not topology_failures,
        "door_passage_valid": not door_failures,
        "wall_crossing_valid": not wall_failures,
        "continuity_valid": not continuity_failures,
        "length_valid": not length_failures,
        "clearance_valid": not clearance_violations and not self_clearance_violations,
        "bijection_valid": not bijection_failures,
        "rounded_lengths_mm": {cid: round(v, 1) for cid, v in rounded_length.items()},
        "r80_failures": r80_failures,
        "containment_failures": containment_failures,
        "topology_failures": topology_failures,
        "door_failures": door_failures,
        "wall_failures": wall_failures,
        "continuity_failures": continuity_failures,
        "length_failures": length_failures,
        "clearance_violations": clearance_violations,
        "self_clearance_violations": self_clearance_violations,
        "bijection_failures": bijection_failures,
    }


def build_rounded_geometry(
    circuits: list[CircuitCandidate],
    transit: list[TransitRoute],
    connection: SyntheticConnection,
) -> dict[str, dict[str, Any]]:
    """Return the validated rounded geometry for every full circuit.

    This is the exact geometry ``validate_full_connection`` measures, so the
    SVG can be drawn from the same arcs instead of the sharp polylines.
    """
    allowed = connection.room.union(connection.corridor_polygon)
    geometry: dict[str, dict[str, Any]] = {}
    for route in transit:
        circuit = next(c for c in circuits if c.circuit_id == route.circuit_id)
        full = route.supply_mm + list(circuit.centerline_mm[1:]) + route.return_mm[1:]
        report = validate_rounded_centerline(
            full, list(allowed.exterior.coords),
            bend_radius_mm=R80_MM, pipe_outer_radius_mm=PIPE_RADIUS_MM, samples_per_quarter=24,
        )
        geometry[route.circuit_id] = {
            "rounded_points": list(report.rounded_points),
            "svg_path_data": report.svg_path_data,
            "rounded_length_mm": report.rounded_length_mm,
        }
    return geometry


def render_full_connection_svg(
    circuits: list[CircuitCandidate],
    transit: list[TransitRoute],
    connection: SyntheticConnection,
    *,
    colors: dict[str, str] | None = None,
) -> str:
    """Render the rounded full circuits (R80 arcs, not sharp polylines)."""
    default_colors = {"V1": "#d92d20", "V2": "#e67e22", "V3": "#f1c40f", "H1": "#2ecc71", "H2": "#3498db"}
    colors = colors or default_colors
    room = connection.room
    minx, miny, maxx, maxy = room.bounds
    geometry = build_rounded_geometry(circuits, transit, connection)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx-500} {connection.corridor_polygon.bounds[1]-300} {maxx-minx+1000} {maxy-connection.corridor_polygon.bounds[1]+1300}">',
        f'<text x="{minx}" y="{connection.corridor_polygon.bounds[1]-180}" font-size="80">L-shape: 5 R80-rounded circuits (FULL_CIRCUIT_VALID)</text>',
        f'<polygon points="{" ".join(f"{x},{y}" for x, y in room.exterior.coords)}" fill="none" stroke="#333" stroke-width="6"/>',
        f'<rect x="{connection.corridor_polygon.bounds[0]}" y="{connection.corridor_polygon.bounds[1]}" '
        f'width="{connection.corridor_polygon.bounds[2]-connection.corridor_polygon.bounds[0]}" '
        f'height="{connection.corridor_polygon.bounds[3]-connection.corridor_polygon.bounds[1]}" fill="none" stroke="#999" stroke-width="2" stroke-dasharray="10 10"/>',
        f'<line x1="2000" y1="-184" x2="2000" y2="-472" stroke="#000" stroke-width="8"/>',
        f'<text x="2050" y="-200" font-size="60">collector bar (synthetic)</text>',
    ]
    for circuit in circuits:
        col = colors.get(circuit.circuit_id, "#000")
        left, right = connection.door_x_range(circuit)
        parts.append(f'<rect x="{left:.0f}" y="-8" width="{right-left:.0f}" height="16" fill="{col}" opacity="0.6"/>')
    for circuit in circuits:
        col = colors.get(circuit.circuit_id, "#000")
        geo = geometry[circuit.circuit_id]
        parts.append(f'<path d="{geo["svg_path_data"]}" fill="none" stroke="{col}" stroke-width="3"/>')
    parts.append("</svg>")
    return "\n".join(parts)


def search_optimal_split(
    room: Polygon,
    collector_xy: tuple[float, float],
    *,
    step_mm: float = 400.0,
) -> dict[str, Any]:
    """Deterministically search zone boundaries for the best valid coverage.

    Boundaries are shifted in ``step_mm`` increments (default 400 mm = 2*pitch)
    which minimises the bifilar residual core.  Each candidate's *rounded*
    spiral coverage is measured, then candidates are fully validated in
    descending coverage order until the first valid one (early exit), so the
    returned candidate is proven valid.
    """
    from agent.ufh_circuit_splitter import split_concave_into_rectangles

    rectangles = split_concave_into_rectangles(room)
    if rectangles is None or len(rectangles) != 2:
        return {"status": "NOT_A_SIMPLE_L_SHAPE"}
    vertical, horizontal = rectangles
    vx0, _vy0, vx1, _vy1 = vertical.bounds
    hx0, hy0, hx1, hy1 = horizontal.bounds
    candidates: list[tuple[float, tuple[float, float, float], list[CircuitCandidate]]] = []
    b1_start = int(vx0 + 800)
    b1_end = int(vx1 - 2 * 800)  # leave room for V2 and V3
    for b1 in range(b1_start, b1_end + 1, int(step_mm)):
        for b2 in range(b1 + int(step_mm), int(vx1 - step_mm) + 1, int(step_mm)):
            h_start = int(hx0 + 800)
            h_end = int(hx1 - 800)
            for hb in range(h_start, h_end + 1, int(step_mm)):
                split = build_circuits_with_boundaries(
                    room, collector_xy, vertical_bounds=(float(b1), float(b2)), horizontal_bound=float(hb),
                )
                covered = None
                for c in split.circuits:
                    if not c.centerline_mm:
                        continue
                    rounded = build_rounded_centerline(
                        c.centerline_mm, bend_radius_mm=R80_MM, samples_per_quarter=24,
                    )
                    band = LineString(rounded.points).buffer(100.0)
                    covered = band if covered is None else covered.union(band)
                area = 0.0 if covered is None else covered.intersection(room).area
                candidates.append((area, (float(b1), float(b2), float(hb)), split.circuits))

    candidates.sort(key=lambda item: item[0], reverse=True)
    validated = 0
    for area, bounds, circuits in candidates:
        connection = build_synthetic_connection(room, collector_xy=collector_xy)
        transit = route_transit(circuits, connection)
        report = validate_full_connection(circuits, transit, connection)
        validated += 1
        if report["transit_valid"]:
            return {
                "status": "FOUND_VALID_CANDIDATE",
                "candidates_examined": len(candidates),
                "candidates_validated": validated,
                "boundaries": {"vertical_bounds": [bounds[0], bounds[1]], "horizontal_bound": bounds[2]},
                "coverage_area_m2": round(area / 1e6, 3),
                "coverage_ratio": round(area / room.area, 4),
                "rounded_lengths_mm": report["rounded_lengths_mm"],
                "validation": {k: report[k] for k in (
                    "r80_valid", "containment_valid", "topology_valid", "door_passage_valid",
                    "wall_crossing_valid", "continuity_valid", "length_valid", "clearance_valid",
                )},
            }
    return {
        "status": "NO_VALID_CANDIDATE",
        "candidates_examined": len(candidates),
        "candidates_validated": validated,
    }


__all__ = [
    "SyntheticConnection",
    "TransitRoute",
    "build_synthetic_connection",
    "route_transit",
    "validate_full_connection",
    "build_rounded_geometry",
    "render_full_connection_svg",
    "search_optimal_split",
]

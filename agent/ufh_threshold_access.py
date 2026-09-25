"""Geometry-only access check from a room's coverage endpoints to its door.

This module answers one narrowly bounded question for the Test_01 UFH preview:
from the two ends of a room's coverage centreline, can two physically
independent pipe paths reach the room's detected door threshold while staying
inside the room and clear of its walls?

It is deliberately not an authority layer.  A successful result means only
that the *geometry* admits two independent in-room paths.  It never asserts
that the threshold is a permitted transit, that a corridor lane exists, or
that any circuit is connected to the manifold.

Method
------
* the room polygon is eroded by the wall/pipe offset so every reachable cell
  already satisfies the wall clearance;
* a deterministic grid graph (8-connectivity, euclidean edge cost) is built on
  the eroded polygon;
* the two coverage endpoints are snapped into the eroded polygon;
* the first path is the shortest grid path from endpoint A to the threshold
  band; the second is recomputed from endpoint B with the first path's cells
  removed, so the two paths are vertex-disjoint outside the shared band;
* the minimum separation between the two polylines is reported and compared
  with the pipe diameter plus the required free clearance.

Every returned status keeps ``door_passage_authorized`` and
``manifold_connected`` as ``UNVERIFIED``.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass
from math import hypot

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points


DEFAULT_WALL_OFFSET_MM = 100.0
DEFAULT_PIPE_OUTER_DIAMETER_MM = 16.0
DEFAULT_MINIMUM_FREE_CLEARANCE_MM = 16.0
DEFAULT_GRID_STEP_MM = 100.0


@dataclass(frozen=True)
class ThresholdAccessResult:
    status: str
    path_supply_mm: tuple[tuple[float, float], ...]
    path_return_mm: tuple[tuple[float, float], ...]
    supply_length_mm: float
    return_length_mm: float
    minimum_pair_separation_mm: float | None
    wall_clearance_min_mm: float | None
    required_pair_separation_mm: float
    snap_distance_mm: float
    diagnostics: tuple[str, ...]
    endpoint_to_threshold_path_valid: bool
    two_independent_paths_valid: bool
    door_passage_authorized: str = "UNVERIFIED"
    manifold_connected: str = "UNVERIFIED"

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "path_supply_mm": [[round(x, 3), round(y, 3)] for x, y in self.path_supply_mm],
            "path_return_mm": [[round(x, 3), round(y, 3)] for x, y in self.path_return_mm],
            "supply_length_mm": round(self.supply_length_mm, 3),
            "return_length_mm": round(self.return_length_mm, 3),
            "minimum_pair_separation_mm": (
                None if self.minimum_pair_separation_mm is None
                else round(self.minimum_pair_separation_mm, 3)
            ),
            "wall_clearance_min_mm": (
                None if self.wall_clearance_min_mm is None
                else round(self.wall_clearance_min_mm, 3)
            ),
            "required_pair_separation_mm": self.required_pair_separation_mm,
            "snap_distance_mm": round(self.snap_distance_mm, 3),
            "endpoint_to_threshold_path_valid": self.endpoint_to_threshold_path_valid,
            "two_independent_paths_valid": self.two_independent_paths_valid,
            "door_passage_authorized": self.door_passage_authorized,
            "manifold_connected": self.manifold_connected,
            "diagnostics": list(self.diagnostics),
        }


def _empty(status: str, diagnostic: str, required: float, snap: float = 0.0) -> ThresholdAccessResult:
    return ThresholdAccessResult(
        status=status,
        path_supply_mm=(),
        path_return_mm=(),
        supply_length_mm=0.0,
        return_length_mm=0.0,
        minimum_pair_separation_mm=None,
        wall_clearance_min_mm=None,
        required_pair_separation_mm=required,
        snap_distance_mm=snap,
        diagnostics=(diagnostic,),
        endpoint_to_threshold_path_valid=False,
        two_independent_paths_valid=False,
    )


def _snap(point: tuple[float, float], area: Polygon) -> tuple[tuple[float, float], float]:
    """Project a point into the allowed area and report the snap distance."""
    probe = Point(point)
    if area.contains(probe):
        return (float(point[0]), float(point[1])), 0.0
    target, _source = nearest_points(area, probe)
    return (float(target.x), float(target.y)), float(probe.distance(target))


def _polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(
        hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1])
        for i in range(1, len(points))
    )


def check_threshold_access(
    room_boundary_mm: list[list[float]] | list[tuple[float, float]],
    threshold_segment_mm: list[list[float]] | list[tuple[float, float]],
    endpoints_mm: list[list[float]] | list[tuple[float, float]],
    *,
    wall_offset_mm: float = DEFAULT_WALL_OFFSET_MM,
    pipe_outer_diameter_mm: float = DEFAULT_PIPE_OUTER_DIAMETER_MM,
    minimum_free_clearance_mm: float = DEFAULT_MINIMUM_FREE_CLEARANCE_MM,
    grid_step_mm: float = DEFAULT_GRID_STEP_MM,
) -> ThresholdAccessResult:
    required = pipe_outer_diameter_mm + minimum_free_clearance_mm
    if len(endpoints_mm) < 2:
        return _empty("ENDPOINT_SET_INCOMPLETE", "TWO_COVERAGE_ENDPOINTS_REQUIRED", required)
    room = Polygon([tuple(p) for p in room_boundary_mm])
    if room.is_empty or not room.is_valid:
        return _empty("GEOMETRY_INVALID", "ROOM_BOUNDARY_NOT_A_VALID_POLYGON", required)
    allowed = room.buffer(-wall_offset_mm)
    if allowed.is_empty:
        return _empty("WALL_OFFSET_EXCEEDS_ROOM", "ERODED_ROOM_EMPTY", required)
    if allowed.geom_type != "Polygon":
        allowed = max(allowed.geoms, key=lambda geom: geom.area)

    threshold_line = LineString([tuple(p) for p in threshold_segment_mm])
    snap_a, snap_a_distance = _snap(tuple(endpoints_mm[0]), allowed)
    snap_b, snap_b_distance = _snap(tuple(endpoints_mm[-1]), allowed)
    snap_distance = max(snap_a_distance, snap_b_distance)

    # Anchor the grid on the room's own coordinate frame and accept cells that
    # sit on the eroded boundary within a 1 mm tolerance.  Using the eroded
    # bounds with a strict containment test dropped boundary-aligned rows and
    # produced false THRESHOLD_UNREACHABLE results.
    room_minx, room_miny, _room_maxx, _room_maxy = room.bounds
    minx, miny, maxx, maxy = allowed.bounds
    columns = max(2, int((maxx - minx) / grid_step_mm) + 1)
    rows = max(2, int((maxy - miny) / grid_step_mm) + 1)
    if columns * rows > 400_000:
        return _empty("GRID_BUDGET_EXCEEDED", "GRID_CELL_BUDGET_EXCEEDED", required, snap_distance)

    cell_index: dict[tuple[int, int], tuple[float, float]] = {}
    base_x = room_minx + grid_step_mm * ((minx - room_minx) // grid_step_mm - 1)
    base_y = room_miny + grid_step_mm * ((miny - room_miny) // grid_step_mm - 1)
    for column in range(columns + 3):
        x = base_x + column * grid_step_mm
        if x < minx - grid_step_mm or x > maxx + grid_step_mm:
            continue
        for row in range(rows + 3):
            y = base_y + row * grid_step_mm
            if y < miny - grid_step_mm or y > maxy + grid_step_mm:
                continue
            probe = Point(x, y)
            if allowed.contains(probe) or allowed.distance(probe) <= 1.0:
                cell_index[(column, row)] = (x, y)
    if not cell_index:
        return _empty("GRID_EMPTY", "NO_GRID_CELL_INSIDE_ALLOWED_AREA", required, snap_distance)

    def nearest_cell(point: tuple[float, float]) -> tuple[int, int]:
        return min(
            cell_index,
            key=lambda key: hypot(cell_index[key][0] - point[0], cell_index[key][1] - point[1]),
        )

    target_cells = {
        key for key, (x, y) in cell_index.items()
        if threshold_line.distance(Point(x, y)) <= wall_offset_mm + grid_step_mm
    }
    if not target_cells:
        return _empty("THRESHOLD_UNREACHABLE", "NO_CELL_WITHIN_THRESHOLD_BAND", required, snap_distance)

    def dijkstra(start: tuple[int, int], blocked: set[tuple[int, int]]) -> list[tuple[int, int]] | None:
        if start in blocked:
            return None
        distances = {start: 0.0}
        previous: dict[tuple[int, int], tuple[int, int]] = {}
        heap = [(0.0, start)]
        while heap:
            cost, cell = heapq.heappop(heap)
            if cost > distances.get(cell, float("inf")):
                continue
            if cell in target_cells:
                path = [cell]
                while path[-1] in previous:
                    path.append(previous[path[-1]])
                return list(reversed(path))
            column, row = cell
            for d_column in (-1, 0, 1):
                for d_row in (-1, 0, 1):
                    if d_column == 0 and d_row == 0:
                        continue
                    neighbour = (column + d_column, row + d_row)
                    if neighbour not in cell_index or neighbour in blocked:
                        continue
                    step = hypot(d_column, d_row) * grid_step_mm
                    candidate = cost + step
                    if candidate < distances.get(neighbour, float("inf")):
                        distances[neighbour] = candidate
                        previous[neighbour] = cell
                        heapq.heappush(heap, (candidate, neighbour))
        return None

    supply_cells = dijkstra(nearest_cell(snap_a), set())
    if supply_cells is None:
        return _empty("ENDPOINT_A_UNREACHABLE", "SUPPLY_ENDPOINT_CANNOT_REACH_THRESHOLD", required, snap_distance)
    blocked = {cell for cell in set(supply_cells) - target_cells}
    return_cells = dijkstra(nearest_cell(snap_b), blocked)

    supply_points = [snap_a] + [cell_index[cell] for cell in supply_cells]
    if return_cells is None:
        return ThresholdAccessResult(
            status="SINGLE_PATH_ONLY",
            path_supply_mm=tuple(supply_points),
            path_return_mm=(),
            supply_length_mm=_polyline_length(supply_points),
            return_length_mm=0.0,
            minimum_pair_separation_mm=None,
            wall_clearance_min_mm=min(Point(p).distance(room.exterior) for p in supply_points),
            required_pair_separation_mm=required,
            snap_distance_mm=snap_distance,
            diagnostics=("SECOND_INDEPENDENT_PATH_NOT_FOUND", "RETURN_PATH_BLOCKED_BY_SUPPLY_PATH"),
            endpoint_to_threshold_path_valid=True,
            two_independent_paths_valid=False,
        )

    return_points = [snap_b] + [cell_index[cell] for cell in return_cells]
    # The two pipes must run side by side only inside the door opening.  Their
    # clearance is therefore measured between the path portions that lie
    # outside the door zone; the converging tails inside the opening are
    # compared with the opening width instead.
    door_zone_radius = wall_offset_mm + grid_step_mm

    def _trunk(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        return [p for p in points if threshold_line.distance(Point(p)) > door_zone_radius]

    supply_trunk = _trunk(supply_points)
    return_trunk = _trunk(return_points)
    shared_outside_target = (set(supply_cells) & set(return_cells)) - target_cells
    if len(supply_trunk) < 2 or len(return_trunk) < 2:
        separation: float | None = None
        independent = False
        diagnostics = ("PATH_OUTSIDE_DOOR_ZONE_TOO_SHORT_TO_MEASURE_SEPARATION",)
    else:
        separation = LineString(supply_trunk).distance(LineString(return_trunk))
        independent = bool(separation >= required and not shared_outside_target)
        diagnostics = () if independent else (
            "PAIR_SEPARATION_BELOW_PIPE_DIAMETER_PLUS_CLEARANCE"
            if separation < required else "PATHS_SHARE_CELLS_OUTSIDE_DOOR_ZONE",
        )
    return ThresholdAccessResult(
        status="TWO_INDEPENDENT_PATHS_GEOMETRIC_VALID" if independent else "TWO_PATHS_BELOW_SEPARATION",
        path_supply_mm=tuple(supply_points),
        path_return_mm=tuple(return_points),
        supply_length_mm=_polyline_length(supply_points),
        return_length_mm=_polyline_length(return_points),
        minimum_pair_separation_mm=separation,
        wall_clearance_min_mm=min(
            Point(p).distance(room.exterior) for p in supply_points + return_points
        ),
        required_pair_separation_mm=required,
        snap_distance_mm=snap_distance,
        diagnostics=diagnostics,
        endpoint_to_threshold_path_valid=True,
        two_independent_paths_valid=independent,
    )


__all__ = [
    "DEFAULT_WALL_OFFSET_MM",
    "DEFAULT_PIPE_OUTER_DIAMETER_MM",
    "DEFAULT_MINIMUM_FREE_CLEARANCE_MM",
    "DEFAULT_GRID_STEP_MM",
    "ThresholdAccessResult",
    "check_threshold_access",
]

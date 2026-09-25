"""Import verified Test_01 coverage BODY routes into the raster WorldState.

The exported ``routes`` use PDF drawing units while ``global_boundary_mm``
uses the floor-wide millimetre frame.  This adapter proves one uniform affine
transform per floor from every paired ``boundary`` / ``global_boundary_mm``
vertex before it imports any route.  No transform is guessed from room bounds.

Only already validated room-coverage geometry is imported.  Openings,
building transit, manifold connections and construction readiness are outside
this bounded adapter and remain explicitly unverified.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import ceil, floor, hypot, isclose, isfinite
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Iterator, Mapping, Sequence

import numpy as np
from shapely.geometry import LineString, Polygon

from agent.ufh_bend_geometry import validate_rounded_centerline
from agent.ufh_test01_world import (
    DEFAULT_CELL_SIZE_MM,
    DEFAULT_TEST01_SOURCE,
    TEST01_FLOORS,
    Test01WorldSourceError,
    Test01Worlds,
    load_test01_worlds,
)
from agent.ufh_world_state import RasterDomainError, ReservationConflictError


_REQUIRED_ROUTE_GATES = (
    "GEOMETRY_VALID",
    "TOPOLOGY_VALID",
    "BEND_VALID",
    "PIPE_LENGTH_VALID",
    "ENDPOINT_ACCESS_VALID",
)
_TRANSFORM_TOLERANCE_MM = 1e-6
_SCALE_TOLERANCE_MM_PER_UNIT = 1e-9
_SERIALIZED_MM_TOLERANCE = 0.001


class Test01OccupancySourceError(ValueError):
    """Raised when the source package cannot be safely matched to the worlds."""

    __test__ = False


@dataclass(frozen=True)
class SourceToGlobalTransform:
    """Proven uniform drawing-unit to global-millimetre transform."""

    floor_id: str
    scale_mm_per_drawing_unit: float
    offset_x_mm: float
    offset_y_mm: float
    evidence_point_count: int
    maximum_residual_mm: float
    status: str = "PROVEN_FROM_ALL_PAIRED_BOUNDARY_VERTICES"

    def apply(self, point: Sequence[float]) -> tuple[float, float]:
        if len(point) != 2:
            raise Test01OccupancySourceError("Route point must contain exactly x and y")
        x, y = float(point[0]), float(point[1])
        if not isfinite(x) or not isfinite(y):
            raise Test01OccupancySourceError("Route coordinates must be finite")
        return (
            x * self.scale_mm_per_drawing_unit + self.offset_x_mm,
            y * self.scale_mm_per_drawing_unit + self.offset_y_mm,
        )


@dataclass(frozen=True)
class CoverageBodyImport:
    """Import result and retained source/vector metadata for one route."""

    floor_id: str
    room_id: str
    route_id: str
    owner: str
    status: str
    reason: str
    reservation_id: str | None
    source_points: tuple[tuple[float, float], ...]
    global_points_mm: tuple[tuple[float, float], ...]
    rounded_global_points_mm: tuple[tuple[float, float], ...]
    material_cell_count: int
    reserved_cell_count: int
    metadata: Mapping[str, Any]

    @property
    def imported(self) -> bool:
        return self.status == "IMPORTED_SOURCE_ALIGNED_BODY"


@dataclass(frozen=True)
class Test01FloorOccupancy:
    floor_id: str
    transform: SourceToGlobalTransform | None
    bodies: tuple[CoverageBodyImport, ...]
    metadata: Mapping[str, Any]

    @property
    def imported_body_count(self) -> int:
        return int(self.metadata["imported_body_count"])

    @property
    def skipped_body_count(self) -> int:
        return int(self.metadata["skipped_body_count"])


@dataclass(frozen=True)
class Test01Occupancy(Mapping[str, Test01FloorOccupancy]):
    """BODY import report for the two independently reserved floor worlds."""

    worlds: Test01Worlds
    floors: Mapping[str, Test01FloorOccupancy]
    metadata: Mapping[str, Any]

    def __getitem__(self, floor_id: str) -> Test01FloorOccupancy:
        return self.floors[floor_id]

    def __iter__(self) -> Iterator[str]:
        return iter(self.floors)

    def __len__(self) -> int:
        return len(self.floors)


def _load_payload(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Test01OccupancySourceError(f"Cannot read Test_01 source package: {path}") from exc
    if not isinstance(payload, dict) or payload.get("project_id") != "Test_01":
        raise Test01OccupancySourceError("Occupancy source project_id must be Test_01")
    if not isinstance(payload.get("rooms"), list):
        raise Test01OccupancySourceError("Occupancy source has no rooms list")
    return payload, sha256(raw).hexdigest()


def _engineering_parameters(payload: Mapping[str, Any]) -> tuple[float, float, float]:
    parameters = payload.get("parameters")
    if not isinstance(parameters, dict):
        raise Test01OccupancySourceError("Occupancy source has no engineering parameters")
    try:
        bend_radius_mm = float(parameters["bend_radius_mm"])
        maximum_length_mm = float(parameters["maximum_circuit_length_mm"])
        pipe_match = re.fullmatch(
            r"\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*mm\s*",
            str(parameters["pipe"]),
            flags=re.IGNORECASE,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise Test01OccupancySourceError("Invalid occupancy engineering parameters") from exc
    if pipe_match is None:
        raise Test01OccupancySourceError("Pipe must explicitly declare outside diameter as DxT mm")
    outside_diameter_mm = float(pipe_match.group(1))
    if not all(
        isfinite(value)
        for value in (bend_radius_mm, maximum_length_mm, outside_diameter_mm)
    ) or bend_radius_mm <= 0 or maximum_length_mm <= 0 or outside_diameter_mm <= 0:
        raise Test01OccupancySourceError("Occupancy engineering parameters must be positive")
    return bend_radius_mm, outside_diameter_mm / 2.0, maximum_length_mm


def _validate_provided_worlds(
    worlds: Test01Worlds,
    *,
    source_path: Path,
    source_digest: str,
    payload: Mapping[str, Any],
    cell_size_mm: float,
) -> None:
    if Path(worlds.metadata.get("source_path", "")).resolve() != source_path:
        raise Test01OccupancySourceError("Provided worlds were built from another source path")
    if worlds.metadata.get("source_sha256") != source_digest:
        raise Test01OccupancySourceError("Provided worlds were built from different source content")
    if worlds.metadata.get("project_id") != "Test_01" or tuple(worlds) != TEST01_FLOORS:
        raise Test01OccupancySourceError("Provided worlds do not contain the canonical Test_01 floors")
    try:
        expected_worlds = load_test01_worlds(source_path, cell_size_mm=cell_size_mm)
    except Test01WorldSourceError as exc:
        raise Test01OccupancySourceError(str(exc)) from exc
    for floor_id in TEST01_FLOORS:
        floor_world = worlds[floor_id]
        domain = floor_world.domain
        expected_floor_world = expected_worlds[floor_id]
        expected_domain = expected_floor_world.domain
        if (
            floor_world.floor_id != floor_id
            or floor_world.metadata.get("floor_id") != floor_id
            or floor_world.metadata.get("source_sha256") != source_digest
            or floor_world.metadata.get("coordinate_frame") != "global_boundary_mm"
            or not isclose(
                float(floor_world.metadata.get("cell_size_mm", float("nan"))),
                float(cell_size_mm),
                rel_tol=0.0,
                abs_tol=_TRANSFORM_TOLERANCE_MM,
            )
            or not isclose(
                domain.cell_size_mm,
                float(cell_size_mm),
                rel_tol=0.0,
                abs_tol=_TRANSFORM_TOLERANCE_MM,
            )
        ):
            raise Test01OccupancySourceError(f"Provided {floor_id} world metadata is incompatible")
        rooms = [room for room in payload["rooms"] if room.get("floor") == floor_id]
        coordinates = [point for room in rooms for point in room.get("global_boundary_mm", [])]
        if not coordinates:
            raise Test01OccupancySourceError(f"{floor_id} has no domain boundary evidence")
        origin_x = floor(min(float(point[0]) for point in coordinates) / cell_size_mm) * cell_size_mm
        origin_y = floor(min(float(point[1]) for point in coordinates) / cell_size_mm) * cell_size_mm
        end_x = ceil(max(float(point[0]) for point in coordinates) / cell_size_mm) * cell_size_mm
        end_y = ceil(max(float(point[1]) for point in coordinates) / cell_size_mm) * cell_size_mm
        expected_width, expected_height = end_x - origin_x, end_y - origin_y
        expected_shape = (
            int(ceil(expected_height / cell_size_mm)),
            int(ceil(expected_width / cell_size_mm)),
        )
        if (
            domain.origin_mm != (origin_x, origin_y)
            or not isclose(domain.width_mm, expected_width, abs_tol=_TRANSFORM_TOLERANCE_MM)
            or not isclose(domain.height_mm, expected_height, abs_tol=_TRANSFORM_TOLERANCE_MM)
            or domain.shape != expected_shape
            or int(domain.static_mask.sum()) != int(floor_world.metadata["blocked_cell_count"])
            or domain.shape[0] * domain.shape[1] != int(floor_world.metadata["cell_count"])
            or not np.array_equal(domain.static_mask, expected_domain.static_mask)
            or floor_world.rooms != expected_floor_world.rooms
        ):
            raise Test01OccupancySourceError(f"Provided {floor_id} raster domain is incompatible")


def _linear_fit(values: np.ndarray, targets: np.ndarray) -> tuple[float, float]:
    if values.size < 2 or float(np.ptp(values)) <= 0.0:
        raise Test01OccupancySourceError("Transform evidence has no usable coordinate span")
    matrix = np.column_stack((values, np.ones(values.size)))
    scale, offset = np.linalg.lstsq(matrix, targets, rcond=None)[0]
    return float(scale), float(offset)


def _prove_transform(
    floor_id: str, rooms: Sequence[Mapping[str, Any]]
) -> SourceToGlobalTransform:
    source_points: list[tuple[float, float]] = []
    global_points: list[tuple[float, float]] = []
    for room in rooms:
        source = room.get("boundary")
        target = room.get("global_boundary_mm")
        if not isinstance(source, list) or not isinstance(target, list) or len(source) != len(target):
            raise Test01OccupancySourceError(
                f"{floor_id} has unpaired boundary/global_boundary_mm evidence"
            )
        if len(source) < 3:
            raise Test01OccupancySourceError(f"{floor_id} has insufficient transform evidence")
        try:
            source_points.extend((float(point[0]), float(point[1])) for point in source)
            global_points.extend((float(point[0]), float(point[1])) for point in target)
        except (TypeError, ValueError, IndexError) as exc:
            raise Test01OccupancySourceError(
                f"{floor_id} contains invalid transform evidence"
            ) from exc

    source_array = np.asarray(source_points, dtype=np.float64)
    global_array = np.asarray(global_points, dtype=np.float64)
    if not np.isfinite(source_array).all() or not np.isfinite(global_array).all():
        raise Test01OccupancySourceError(f"{floor_id} transform evidence must be finite")
    scale_x, offset_x = _linear_fit(source_array[:, 0], global_array[:, 0])
    scale_y, offset_y = _linear_fit(source_array[:, 1], global_array[:, 1])
    if scale_x <= 0.0 or scale_y <= 0.0 or not isclose(
        scale_x, scale_y, rel_tol=0.0, abs_tol=_SCALE_TOLERANCE_MM_PER_UNIT
    ):
        raise Test01OccupancySourceError(
            f"{floor_id} does not prove one positive uniform source-to-global scale"
        )
    scale = (scale_x + scale_y) / 2.0
    projected = source_array * scale + np.asarray((offset_x, offset_y))
    residuals = np.hypot(
        projected[:, 0] - global_array[:, 0],
        projected[:, 1] - global_array[:, 1],
    )
    maximum_residual = float(residuals.max(initial=0.0))
    if maximum_residual > _TRANSFORM_TOLERANCE_MM:
        raise Test01OccupancySourceError(
            f"{floor_id} source-to-global transform residual {maximum_residual:.6f} mm "
            f"exceeds {_TRANSFORM_TOLERANCE_MM:.6f} mm"
        )
    return SourceToGlobalTransform(
        floor_id=floor_id,
        scale_mm_per_drawing_unit=scale,
        offset_x_mm=offset_x,
        offset_y_mm=offset_y,
        evidence_point_count=len(source_points),
        maximum_residual_mm=maximum_residual,
    )


def _closed_cell_range(
    low: float, high: float, origin: float, cell_size: float, count: int
) -> range:
    """Cells touched by a closed world-coordinate interval."""

    local_low = (low - origin) / cell_size
    local_high = (high - origin) / cell_size
    first = int(floor(local_low))
    # A segment on a cell boundary touches the cell on both sides.
    if isclose(local_low, round(local_low), rel_tol=0.0, abs_tol=1e-10):
        first -= 1
    last = int(floor(local_high))
    first = max(0, first)
    last = min(count - 1, last)
    return range(first, last + 1) if first <= last else range(0)


def _segment_intersects_box(
    start: tuple[float, float],
    end: tuple[float, float],
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
) -> bool:
    """Inclusive Liang-Barsky segment/rectangle intersection."""

    x0, y0 = start
    dx, dy = end[0] - x0, end[1] - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - xmin), (dx, xmax - x0), (-dy, y0 - ymin), (dy, ymax - y0)):
        if abs(p) <= 1e-12:
            if q < -1e-9:
                return False
            continue
        ratio = q / p
        if p < 0.0:
            if ratio > t1:
                return False
            t0 = max(t0, ratio)
        else:
            if ratio < t0:
                return False
            t1 = min(t1, ratio)
    return t0 <= t1 + 1e-12


def supercover_polyline_mask(domain: Any, points_mm: Sequence[Sequence[float]]) -> np.ndarray:
    """Rasterize every cell whose closed footprint touches the polyline."""

    if len(points_mm) < 2:
        raise Test01OccupancySourceError("A coverage BODY route needs at least two points")
    points: list[tuple[float, float]] = []
    for point in points_mm:
        if len(point) != 2:
            raise Test01OccupancySourceError("Route point must contain exactly x and y")
        candidate = (float(point[0]), float(point[1]))
        if not all(isfinite(value) for value in candidate):
            raise Test01OccupancySourceError("Route coordinates must be finite")
        points.append(candidate)

    mask = domain.empty_mask()
    origin_x, origin_y = domain.origin_mm
    cell = domain.cell_size_mm
    world_max_x = origin_x + domain.width_mm
    world_max_y = origin_y + domain.height_mm
    for start, end in zip(points, points[1:]):
        if start == end:
            raise Test01OccupancySourceError("Coverage BODY contains a zero-length segment")
        min_x, max_x = sorted((start[0], end[0]))
        min_y, max_y = sorted((start[1], end[1]))
        if min_x < origin_x or min_y < origin_y or max_x > world_max_x or max_y > world_max_y:
            raise Test01OccupancySourceError("Coverage BODY leaves its floor raster domain")
        columns = _closed_cell_range(min_x, max_x, origin_x, cell, domain.shape[1])
        rows = _closed_cell_range(min_y, max_y, origin_y, cell, domain.shape[0])
        for row in rows:
            ymin = origin_y + row * cell
            ymax = min(ymin + cell, world_max_y)
            for column in columns:
                xmin = origin_x + column * cell
                xmax = min(xmin + cell, world_max_x)
                if _segment_intersects_box(start, end, xmin, ymin, xmax, ymax):
                    mask[row, column] = True
    return mask


def _validation_for_route(room: Mapping[str, Any], route_id: str) -> Mapping[str, Any] | None:
    validations = room.get("route_validation")
    if not isinstance(validations, list):
        return None
    matches = [item for item in validations if isinstance(item, dict) and item.get("route_id") == route_id]
    return matches[0] if len(matches) == 1 else None


def _route_is_valid(room: Mapping[str, Any], validation: Mapping[str, Any] | None) -> bool:
    if room.get("geometry_status") != "USABLE" or room.get("status") != "ROUTED_VALID":
        return False
    if validation is None or not all(validation.get(gate) is True for gate in _REQUIRED_ROUTE_GATES):
        return False
    rounded = validation.get("rounded_geometry")
    return isinstance(rounded, dict) and all(
        rounded.get(gate) is True
        for gate in ("valid", "GEOMETRY_VALID", "TOPOLOGY_VALID", "BEND_GEOMETRY_VALID")
    )


def _prove_route_frame(
    room: Mapping[str, Any],
    source_points: tuple[tuple[float, float], ...],
    global_points: tuple[tuple[float, float], ...],
    transform: SourceToGlobalTransform,
    validation: Mapping[str, Any],
    *,
    expected_bend_radius_mm: float,
    expected_pipe_outer_radius_mm: float,
    maximum_circuit_length_mm: float,
) -> tuple[tuple[tuple[float, float], ...], Mapping[str, Any]]:
    """Bind one route to both advertised frames using independent evidence."""

    try:
        source_boundary = Polygon(room["boundary"])
        global_boundary = Polygon(room["global_boundary_mm"])
        source_line = LineString(source_points)
        global_line = LineString(global_points)
        rounded_metadata = validation["rounded_geometry"]
        expected_straight_length = float(rounded_metadata["straight_centerline_length_mm"])
        expected_rounded_length = float(rounded_metadata["rounded_length_mm"])
        radius_mm = float(rounded_metadata["radius_mm"])
        outer_radius_mm = float(rounded_metadata["outer_radius_mm"])
        expected_bend_count = int(rounded_metadata["bend_count"])
        length_mm = float(validation["length_mm"])
        internal_pipe_length = float(validation["INTERNAL_PIPE_LENGTH"])
        serialized_rounded_points = tuple(
            (float(point[0]), float(point[1]))
            for point in rounded_metadata["rounded_points"]
        )
        room_min_x = min(float(point[0]) for point in room["global_boundary_mm"])
        room_min_y = min(float(point[1]) for point in room["global_boundary_mm"])
        local_global_points = tuple(
            (point[0] - room_min_x, point[1] - room_min_y)
            for point in global_points
        )
        local_global_boundary = tuple(
            (float(point[0]) - room_min_x, float(point[1]) - room_min_y)
            for point in room["global_boundary_mm"]
        )
        numeric_evidence = (
            expected_straight_length,
            expected_rounded_length,
            radius_mm,
            outer_radius_mm,
            length_mm,
            internal_pipe_length,
            *(coordinate for point in serialized_rounded_points for coordinate in point),
        )
        if not all(isfinite(value) for value in numeric_evidence):
            raise ValueError("non-finite route evidence")
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise Test01OccupancySourceError("Route has incomplete coordinate-frame evidence") from exc
    transformed_source_length = float(source_line.length * transform.scale_mm_per_drawing_unit)
    straight_length_residual = abs(transformed_source_length - expected_straight_length)
    source_contained = source_boundary.covers(source_line)
    global_contained = global_boundary.covers(global_line)
    recomputed = validate_rounded_centerline(
        local_global_points,
        local_global_boundary,
        bend_radius_mm=expected_bend_radius_mm,
        pipe_outer_radius_mm=expected_pipe_outer_radius_mm,
    )
    rounded_point_residual = (
        max(
            hypot(point[0] - expected[0], point[1] - expected[1])
            for point, expected in zip(
                recomputed.rounded_points, serialized_rounded_points, strict=True
            )
        )
        if len(recomputed.rounded_points) == len(serialized_rounded_points)
        else float("inf")
    )
    rounded_length_fields = (
        expected_rounded_length,
        length_mm,
        internal_pipe_length,
    )
    rounded_length_residual = max(
        abs(value - recomputed.rounded_length_mm) for value in rounded_length_fields
    )
    rounded_global_points = tuple(
        (point[0] + room_min_x, point[1] + room_min_y)
        for point in serialized_rounded_points
    )
    rounded_global_contained = global_boundary.covers(LineString(rounded_global_points))
    if (
        source_line.is_empty
        or not source_line.is_simple
        or not source_contained
        or not global_contained
        or not rounded_global_contained
        or not recomputed.valid
        or abs(radius_mm - expected_bend_radius_mm) > _TRANSFORM_TOLERANCE_MM
        or abs(outer_radius_mm - expected_pipe_outer_radius_mm) > _TRANSFORM_TOLERANCE_MM
        or expected_bend_count != recomputed.bend_count
        or straight_length_residual > _SERIALIZED_MM_TOLERANCE
        or rounded_length_residual > _SERIALIZED_MM_TOLERANCE
        or rounded_point_residual > _SERIALIZED_MM_TOLERANCE
        or recomputed.rounded_length_mm > maximum_circuit_length_mm
    ):
        raise Test01OccupancySourceError(
            "Route frame is unproven: "
            f"source_contained={source_contained}; global_contained={global_contained}; "
            f"rounded_global_contained={rounded_global_contained}; "
            f"recomputed_rounded_valid={recomputed.valid}; "
            f"bend_count={expected_bend_count}/{recomputed.bend_count}; "
            f"radius_mm={radius_mm}/{expected_bend_radius_mm}; "
            f"outer_radius_mm={outer_radius_mm}/{expected_pipe_outer_radius_mm}; "
            f"straight_length_residual_mm={straight_length_residual:.6f}; "
            f"rounded_length_residual_mm={rounded_length_residual:.6f}; "
            f"rounded_point_residual_mm={rounded_point_residual:.6f}"
        )
    return rounded_global_points, MappingProxyType(
        {
            "status": "PROVEN_SOURCE_ROUTE_AND_RECOMPUTED_R80_TO_GLOBAL_MM",
            "source_boundary_contains_route": source_contained,
            "global_boundary_contains_route": global_contained,
            "rounded_global_boundary_contains_route": rounded_global_contained,
            "transformed_source_length_mm": transformed_source_length,
            "expected_straight_centerline_length_mm": expected_straight_length,
            "straight_length_residual_mm": straight_length_residual,
            "recomputed_rounded_length_mm": recomputed.rounded_length_mm,
            "rounded_length_residual_mm": rounded_length_residual,
            "recomputed_bend_count": recomputed.bend_count,
            "recomputed_radius_mm": expected_bend_radius_mm,
            "recomputed_outer_radius_mm": expected_pipe_outer_radius_mm,
            "rounded_point_residual_mm": rounded_point_residual,
            "rounded_frame_mapping": "LOCAL_ROOM_MM_PLUS_GLOBAL_BOUNDARY_MINIMUM",
        }
    )


def _body_result(
    *,
    floor_id: str,
    room: Mapping[str, Any],
    route_id: str,
    owner: str,
    status: str,
    reason: str,
    source_points: tuple[tuple[float, float], ...] = (),
    global_points: tuple[tuple[float, float], ...] = (),
    rounded_global_points: tuple[tuple[float, float], ...] = (),
    reservation: Any | None = None,
    validation: Mapping[str, Any] | None = None,
    frame_evidence: Mapping[str, Any] | None = None,
) -> CoverageBodyImport:
    metadata = MappingProxyType(
        {
            "source_room_status": room.get("status"),
            "source_geometry_status": room.get("geometry_status"),
            "source_route_validation": validation,
            "source_coordinate_frame": "boundary/PDF_DRAWING_UNITS",
            "target_coordinate_frame": "global_boundary_mm",
            "coordinate_frame_evidence": frame_evidence,
            "engineering_role": "COVERAGE_BODY",
            "manifold_connected": "UNVERIFIED",
            "building_transit_valid": False,
            "full_circuit_valid": False,
            "construction_release": False,
        }
    )
    return CoverageBodyImport(
        floor_id=floor_id,
        room_id=str(room.get("id", "")),
        route_id=route_id,
        owner=owner,
        status=status,
        reason=reason,
        reservation_id=reservation.reservation_id if reservation is not None else None,
        source_points=source_points,
        global_points_mm=global_points,
        rounded_global_points_mm=rounded_global_points,
        material_cell_count=reservation.material_cell_count if reservation is not None else 0,
        reserved_cell_count=reservation.reserved_cell_count if reservation is not None else 0,
        metadata=metadata,
    )


def import_test01_coverage_bodies(
    source_path: str | Path = DEFAULT_TEST01_SOURCE,
    *,
    cell_size_mm: float = DEFAULT_CELL_SIZE_MM,
    worlds: Test01Worlds | None = None,
) -> Test01Occupancy:
    """Reserve accepted Test_01 coverage routes as BODY occupancy.

    Reservation is route-atomic.  A malformed route, failed source validation,
    static obstacle contact, or collision with an earlier BODY is retained as a
    skipped diagnostic and writes no cells.  This function never opens a wall
    or creates transit/manifold geometry.
    """

    path = Path(source_path).resolve()
    payload, source_digest = _load_payload(path)
    bend_radius_mm, pipe_outer_radius_mm, maximum_length_mm = _engineering_parameters(
        payload
    )
    if not isinstance(cell_size_mm, (int, float)) or not isfinite(float(cell_size_mm)):
        raise Test01OccupancySourceError("cell_size_mm must be a finite number")
    if float(cell_size_mm) <= 0:
        raise Test01OccupancySourceError("cell_size_mm must be positive")
    if worlds is None:
        try:
            worlds = load_test01_worlds(path, cell_size_mm=cell_size_mm)
        except Test01WorldSourceError as exc:
            raise Test01OccupancySourceError(str(exc)) from exc
    else:
        _validate_provided_worlds(
            worlds,
            source_path=path,
            source_digest=source_digest,
            payload=payload,
            cell_size_mm=cell_size_mm,
        )

    floor_reports: dict[str, Test01FloorOccupancy] = {}
    for floor_id in TEST01_FLOORS:
        floor_rooms = [room for room in payload["rooms"] if room.get("floor") == floor_id]
        try:
            transform = _prove_transform(floor_id, floor_rooms)
            transform_error = None
        except Test01OccupancySourceError as exc:
            transform = None
            transform_error = str(exc)

        bodies: list[CoverageBodyImport] = []
        for room in floor_rooms:
            routes = room.get("routes") if isinstance(room.get("routes"), list) else []
            route_ids = room.get("route_ids") if isinstance(room.get("route_ids"), list) else []
            route_count = max(len(routes), len(route_ids))
            for index in range(route_count):
                route_id = str(route_ids[index]) if index < len(route_ids) else f"missing-route-id-{index + 1}"
                owner = f"{room.get('id', '')}/{route_id}"
                validation = _validation_for_route(room, route_id)
                if transform is None:
                    bodies.append(
                        _body_result(
                            floor_id=floor_id,
                            room=room,
                            route_id=route_id,
                            owner=owner,
                            status="SKIPPED_COORDINATE_TRANSFORM_UNPROVEN",
                            reason=transform_error or "source-to-global transform is unproven",
                            validation=validation,
                        )
                    )
                    continue
                if index >= len(routes) or index >= len(route_ids) or not _route_is_valid(room, validation):
                    bodies.append(
                        _body_result(
                            floor_id=floor_id,
                            room=room,
                            route_id=route_id,
                            owner=owner,
                            status="SKIPPED_SOURCE_ROUTE_NOT_VALID",
                            reason="room/route validation gates are not all accepted",
                            validation=validation,
                        )
                    )
                    continue
                try:
                    source_points = tuple((float(point[0]), float(point[1])) for point in routes[index])
                    global_points = tuple(transform.apply(point) for point in source_points)
                    rounded_global_points, frame_evidence = _prove_route_frame(
                        room,
                        source_points,
                        global_points,
                        transform,
                        validation,
                        expected_bend_radius_mm=bend_radius_mm,
                        expected_pipe_outer_radius_mm=pipe_outer_radius_mm,
                        maximum_circuit_length_mm=maximum_length_mm,
                    )
                    sharp_mask = supercover_polyline_mask(
                        worlds[floor_id].domain, global_points
                    )
                    rounded_mask = supercover_polyline_mask(
                        worlds[floor_id].domain, rounded_global_points
                    )
                    mask = sharp_mask | rounded_mask
                    reservation = worlds[floor_id].domain.reserve(
                        mask,
                        owner=owner,
                        role="BODY",
                        reservation_id=f"test01-body:{owner}",
                    )
                except (TypeError, ValueError, IndexError, RasterDomainError) as exc:
                    bodies.append(
                        _body_result(
                            floor_id=floor_id,
                            room=room,
                            route_id=route_id,
                            owner=owner,
                            status="SKIPPED_INVALID_ROUTE_GEOMETRY",
                            reason=str(exc),
                            validation=validation,
                        )
                    )
                    continue
                except ReservationConflictError as exc:
                    bodies.append(
                        _body_result(
                            floor_id=floor_id,
                            room=room,
                            route_id=route_id,
                            owner=owner,
                            status="SKIPPED_RESERVATION_CONFLICT",
                            reason=(
                                f"static_cells={exc.static_cell_count}; "
                                f"occupied_cells={exc.occupied_cell_count}; "
                                f"boundary_overflow={exc.boundary_overflow}"
                            ),
                            source_points=source_points,
                            global_points=global_points,
                            rounded_global_points=rounded_global_points,
                            validation=validation,
                            frame_evidence=frame_evidence,
                        )
                    )
                    continue
                bodies.append(
                    _body_result(
                        floor_id=floor_id,
                        room=room,
                        route_id=route_id,
                        owner=owner,
                        status="IMPORTED_SOURCE_ALIGNED_BODY",
                        reason="source validation and conservative raster reservation accepted",
                        source_points=source_points,
                        global_points=global_points,
                        rounded_global_points=rounded_global_points,
                        reservation=reservation,
                        validation=validation,
                        frame_evidence=frame_evidence,
                    )
                )

        imported = sum(body.imported for body in bodies)
        skipped = len(bodies) - imported
        metadata = MappingProxyType(
            {
                "status": (
                    "BLOCKED_UNPROVEN_TRANSFORM"
                    if transform is None
                    else "SOURCE_ALIGNED_BODY_OCCUPANCY_IMPORTED"
                    if imported
                    else "NO_SOURCE_BODY_IMPORTED"
                ),
                "floor_id": floor_id,
                "coordinate_transform_proven": transform is not None,
                "route_candidate_count": len(bodies),
                "imported_body_count": imported,
                "skipped_body_count": skipped,
                "collision_count": sum(body.status == "SKIPPED_RESERVATION_CONFLICT" for body in bodies),
                "role": "BODY",
                "openings_imported": False,
                "building_transit_valid": False,
                "full_circuit_valid": False,
                "construction_release": False,
            }
        )
        floor_reports[floor_id] = Test01FloorOccupancy(
            floor_id=floor_id,
            transform=transform,
            bodies=tuple(bodies),
            metadata=metadata,
        )

    total = sum(len(floor.bodies) for floor in floor_reports.values())
    imported = sum(floor.imported_body_count for floor in floor_reports.values())
    bundle_metadata = MappingProxyType(
        {
            "status": "GEOMETRY_ONLY_SOURCE_BODY_OCCUPANCY",
            "project_id": "Test_01",
            "source_path": str(path),
            "floor_count": len(floor_reports),
            "route_candidate_count": total,
            "imported_body_count": imported,
            "skipped_body_count": total - imported,
            "openings_imported": False,
            "building_transit_valid": False,
            "full_circuit_valid": False,
            "construction_release": False,
        }
    )
    return Test01Occupancy(worlds, MappingProxyType(floor_reports), bundle_metadata)


__all__ = [
    "CoverageBodyImport",
    "SourceToGlobalTransform",
    "Test01FloorOccupancy",
    "Test01Occupancy",
    "Test01OccupancySourceError",
    "import_test01_coverage_bodies",
    "supercover_polyline_mask",
]

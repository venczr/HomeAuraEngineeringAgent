"""Fail-closed raster world adapter for the two Test_01 source plans.

The adapter consumes the already exported, source-frame geometry package.  It
does not regenerate room geometry and it deliberately does not infer doors or
passages.  A raster cell is routable only when its complete footprint is
inside a room whose exported geometry status is ``USABLE``.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import ceil, floor, sqrt
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterator, Mapping

import numpy as np
from shapely import box as shapely_box, contains_xy, covers
from shapely.geometry import Polygon

from agent.ufh_world_state import RasterRoutingDomain


DEFAULT_TEST01_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "projects"
    / "Test_01"
    / "exports"
    / "ufh_generator_package"
    / "08_PROJECT_SOURCE_DATA.json"
)
TEST01_FLOORS = ("FLOOR_1_PLAN", "ATTIC_PLAN")
DEFAULT_CELL_SIZE_MM = 10.0


class Test01WorldSourceError(ValueError):
    """Raised when the exported Test_01 source cannot safely define a world."""

    __test__ = False


@dataclass(frozen=True)
class Test01RoomRasterStatus:
    room_id: str
    label: str
    geometry_status: str
    route_status: str
    raster_access: str
    routable_cell_count: int


@dataclass(frozen=True)
class Test01FloorWorld:
    """One source-aligned floor domain and its immutable source metadata."""

    floor_id: str
    domain: RasterRoutingDomain
    rooms: tuple[Test01RoomRasterStatus, ...]
    metadata: Mapping[str, Any]

    @property
    def room_count(self) -> int:
        return len(self.rooms)

    @property
    def routable_cell_count(self) -> int:
        return int(self.metadata["routable_cell_count"])

    @property
    def blocked_cell_count(self) -> int:
        return int(self.metadata["blocked_cell_count"])


@dataclass(frozen=True)
class Test01Worlds(Mapping[str, Test01FloorWorld]):
    """The two independent Test_01 raster domains."""

    floors: Mapping[str, Test01FloorWorld]
    metadata: Mapping[str, Any]

    def __getitem__(self, floor_id: str) -> Test01FloorWorld:
        return self.floors[floor_id]

    def __iter__(self) -> Iterator[str]:
        return iter(self.floors)

    def __len__(self) -> int:
        return len(self.floors)


def _load_source(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise Test01WorldSourceError(f"Cannot read Test_01 source package: {path}") from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Test01WorldSourceError("Test_01 source package is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("rooms"), list):
        raise Test01WorldSourceError("Test_01 source package has no rooms list")
    return payload, sha256(raw).hexdigest()


def _polygon(room: Mapping[str, Any]) -> Polygon:
    boundary = room.get("global_boundary_mm")
    if not isinstance(boundary, list) or len(boundary) < 3:
        raise Test01WorldSourceError(
            f"Room {room.get('id', '<unknown>')} has no usable global boundary"
        )
    try:
        polygon = Polygon([(float(point[0]), float(point[1])) for point in boundary])
    except (TypeError, ValueError, IndexError) as exc:
        raise Test01WorldSourceError(
            f"Room {room.get('id', '<unknown>')} has an invalid global boundary"
        ) from exc
    if not polygon.is_valid or polygon.is_empty or polygon.area <= 0:
        raise Test01WorldSourceError(
            f"Room {room.get('id', '<unknown>')} has invalid polygon topology"
        )
    return polygon


def _domain_bounds(
    polygons: list[Polygon], cell_size_mm: float
) -> tuple[tuple[float, float], float, float]:
    min_x = min(polygon.bounds[0] for polygon in polygons)
    min_y = min(polygon.bounds[1] for polygon in polygons)
    max_x = max(polygon.bounds[2] for polygon in polygons)
    max_y = max(polygon.bounds[3] for polygon in polygons)
    origin_x = floor(min_x / cell_size_mm) * cell_size_mm
    origin_y = floor(min_y / cell_size_mm) * cell_size_mm
    end_x = ceil(max_x / cell_size_mm) * cell_size_mm
    end_y = ceil(max_y / cell_size_mm) * cell_size_mm
    return (origin_x, origin_y), end_x - origin_x, end_y - origin_y


def _complete_cell_mask(
    polygon: Polygon,
    *,
    origin_mm: tuple[float, float],
    shape: tuple[int, int],
    cell_size_mm: float,
) -> np.ndarray:
    """Return cells whose complete square footprint is covered by ``polygon``.

    ``covers`` permits a cell edge to coincide with the source boundary, but
    rejects every cell with any area outside it.  The vectorized Shapely ufuncs
    keep this exact full-cell test fast enough for the two source floors.
    """

    result = np.zeros(shape, dtype=np.bool_)
    if polygon.is_empty:
        return result

    min_x, min_y, max_x, max_y = polygon.bounds
    column_start = max(0, int(floor((min_x - origin_mm[0]) / cell_size_mm)))
    column_end = min(shape[1], int(ceil((max_x - origin_mm[0]) / cell_size_mm)))
    row_start = max(0, int(floor((min_y - origin_mm[1]) / cell_size_mm)))
    row_end = min(shape[0], int(ceil((max_y - origin_mm[1]) / cell_size_mm)))
    if column_start >= column_end or row_start >= row_end:
        return result

    x0 = origin_mm[0] + np.arange(column_start, column_end) * cell_size_mm
    y0 = origin_mm[1] + np.arange(row_start, row_end) * cell_size_mm
    center_x = x0 + cell_size_mm / 2.0
    center_y = y0 + cell_size_mm / 2.0

    # Most cells are well inside the polygon.  A half-diagonal inward buffer
    # proves those cells safe cheaply.  Only the narrow band rejected by that
    # conservative proof needs the more expensive exact box predicate.
    inset = polygon.buffer(
        -(cell_size_mm * sqrt(2.0) / 2.0), join_style="mitre"
    )
    center_inside = contains_xy(
        polygon, center_x[np.newaxis, :], center_y[:, np.newaxis]
    )
    proven_inside = (
        np.zeros(center_inside.shape, dtype=np.bool_)
        if inset.is_empty
        else contains_xy(inset, center_x[np.newaxis, :], center_y[:, np.newaxis])
    )
    local_mask = proven_inside
    candidate_rows, candidate_columns = np.nonzero(center_inside & ~proven_inside)
    if candidate_rows.size:
        candidate_boxes = shapely_box(
            x0[candidate_columns],
            y0[candidate_rows],
            x0[candidate_columns] + cell_size_mm,
            y0[candidate_rows] + cell_size_mm,
        )
        local_mask[candidate_rows, candidate_columns] = covers(
            polygon, candidate_boxes
        )
    result[row_start:row_end, column_start:column_end] = local_mask
    return result


def load_test01_worlds(
    source_path: str | Path = DEFAULT_TEST01_SOURCE,
    *,
    cell_size_mm: float = DEFAULT_CELL_SIZE_MM,
) -> Test01Worlds:
    """Load both Test_01 floors without running any geometry generator.

    Every domain starts fully blocked.  Only exported ``USABLE`` room
    interiors are subtracted from the static mask.  ``GEOMETRY_UNRESOLVED``
    rooms, space between rooms, wall boundaries and all inferred/candidate
    openings therefore stay blocked.
    """

    if not isinstance(cell_size_mm, (int, float)) or not np.isfinite(cell_size_mm):
        raise Test01WorldSourceError("cell_size_mm must be a finite number")
    if cell_size_mm <= 0:
        raise Test01WorldSourceError("cell_size_mm must be positive")

    path = Path(source_path).resolve()
    payload, source_digest = _load_source(path)
    if payload.get("project_id") != "Test_01":
        raise Test01WorldSourceError("Source package project_id must be Test_01")

    source_rooms = payload["rooms"]
    floor_worlds: dict[str, Test01FloorWorld] = {}
    for floor_id in TEST01_FLOORS:
        floor_rooms = [room for room in source_rooms if room.get("floor") == floor_id]
        if len(floor_rooms) != 8:
            raise Test01WorldSourceError(
                f"{floor_id} must contain exactly 8 source rooms; found {len(floor_rooms)}"
            )
        polygons = [_polygon(room) for room in floor_rooms]
        origin, width, height = _domain_bounds(polygons, float(cell_size_mm))
        rows = int(ceil(height / cell_size_mm))
        columns = int(ceil(width / cell_size_mm))
        routable = np.zeros((rows, columns), dtype=np.bool_)
        room_statuses: list[Test01RoomRasterStatus] = []

        for room, polygon in zip(floor_rooms, polygons, strict=True):
            geometry_status = str(room.get("geometry_status", "UNRESOLVED"))
            if geometry_status == "USABLE":
                room_mask = _complete_cell_mask(
                    polygon,
                    origin_mm=origin,
                    shape=(rows, columns),
                    cell_size_mm=float(cell_size_mm),
                )
                # OR each room independently.  We never union polygons before
                # insetting, so touching room boundaries cannot become doors.
                routable |= room_mask
                access = "OPEN_USABLE_INTERIOR_ONLY"
                count = int(room_mask.sum())
            else:
                access = "BLOCKED_GEOMETRY_UNRESOLVED"
                count = 0
            room_statuses.append(
                Test01RoomRasterStatus(
                    room_id=str(room.get("id", "")),
                    label=str(room.get("label", "")),
                    geometry_status=geometry_status,
                    route_status=str(room.get("status", "UNRESOLVED")),
                    raster_access=access,
                    routable_cell_count=count,
                )
            )

        static_mask = ~routable
        domain = RasterRoutingDomain(
            origin_mm=origin,
            width_mm=width,
            height_mm=height,
            cell_size_mm=float(cell_size_mm),
            static_mask=static_mask,
        )
        cell_count = rows * columns
        metadata = MappingProxyType(
            {
                "status": "FAIL_CLOSED_SOURCE_GEOMETRY_RASTERIZED",
                "project_id": "Test_01",
                "floor_id": floor_id,
                "source_path": str(path),
                "source_sha256": source_digest,
                "source_provenance": payload.get("provenance"),
                "coordinate_frame": "global_boundary_mm",
                "cell_size_mm": float(cell_size_mm),
                "cell_count": cell_count,
                "routable_cell_count": int(routable.sum()),
                "blocked_cell_count": int(static_mask.sum()),
                "room_count": len(room_statuses),
                "usable_room_count": sum(
                    room.geometry_status == "USABLE" for room in room_statuses
                ),
                "geometry_unresolved_room_count": sum(
                    room.geometry_status == "GEOMETRY_UNRESOLVED"
                    for room in room_statuses
                ),
                "opening_policy": "ALL_OPENINGS_BLOCKED_UNLESS_SOURCE_AUTHORIZED",
                "authorized_opening_count": 0,
                "candidate_openings_applied": False,
                "exact_vector_validation_required": True,
                "construction_release": False,
            }
        )
        floor_worlds[floor_id] = Test01FloorWorld(
            floor_id=floor_id,
            domain=domain,
            rooms=tuple(room_statuses),
            metadata=metadata,
        )

    bundle_metadata = MappingProxyType(
        {
            "status": "GEOMETRY_ONLY_FAIL_CLOSED_WORLD",
            "project_id": "Test_01",
            "source_path": str(path),
            "source_sha256": source_digest,
            "floor_count": len(floor_worlds),
            "floor_ids": TEST01_FLOORS,
            "generated_geometry": False,
            "construction_release": False,
        }
    )
    return Test01Worlds(MappingProxyType(floor_worlds), bundle_metadata)


__all__ = [
    "DEFAULT_CELL_SIZE_MM",
    "DEFAULT_TEST01_SOURCE",
    "TEST01_FLOORS",
    "Test01FloorWorld",
    "Test01RoomRasterStatus",
    "Test01WorldSourceError",
    "Test01Worlds",
    "load_test01_worlds",
]

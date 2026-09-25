"""Bounded first-floor kitchen BODY candidate.

This module is deliberately narrower than a floor generator.  It replaces the
two source kitchen BODY reservations in a fresh Test_01 occupancy world with
one independently checked rectangular counterflow body.  Door openings are
retained as source-vector *candidates* only; no wall crossing, transit, or
manifold connection is emitted.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from math import isfinite
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from shapely.geometry import LineString, Polygon

from agent.ufh_bend_geometry import validate_rounded_centerline
from agent.ufh_layout_engine import validate_bifilar_topology
from agent.ufh_spiral_kernel import build_accessible_bifilar_spiral
from agent.ufh_test01_occupancy import (
    DEFAULT_TEST01_SOURCE,
    Test01OccupancySourceError,
    import_test01_coverage_bodies,
    supercover_polyline_mask,
)
from agent.ufh_test01_world import DEFAULT_CELL_SIZE_MM
from agent.ufh_world_state import RasterDomainError, ReservationConflictError


KITCHEN_ROOM_ID = "FLOOR_1_PLAN:dbda1f3916917c37:ROOM"
KITCHEN_FLOOR_ID = "FLOOR_1_PLAN"
ATTIC_FLOOR_ID = "ATTIC_PLAN"
PIPE_OUTER_RADIUS_MM = 8.0
BEND_RADIUS_MM = 80.0
SPACING_MM = 200.0
MAXIMUM_CIRCUIT_LENGTH_MM = 90_000.0

# This zone is a conservative rectangle wholly contained in the source room.
# Keeping its north edge below the stair/notch transition avoids inventing a
# route through the irregular part of the source polygon.
DEFAULT_KITCHEN_SUBZONE_MM = (13_000.0, 8_750.0, 18_150.0, 11_600.0)
OPENING_CANDIDATES = (
    {
        "opening_id": "FLOOR_1_PLAN-KITCHEN-CORRIDOR-UPPER",
        "source_vector": ((12_636.0, 11_345.0), (12_937.0, 11_345.0)),
        "y_mm": 11_345.0,
        "status": "UNVERIFIED_SOURCE_VECTOR_CANDIDATE",
    },
    {
        "opening_id": "FLOOR_1_PLAN-KITCHEN-CORRIDOR-LOWER",
        "source_vector": ((12_636.0, 13_064.0), (12_937.0, 13_064.0)),
        "y_mm": 13_064.0,
        "status": "UNVERIFIED_SOURCE_VECTOR_CANDIDATE",
    },
)


@dataclass(frozen=True)
class KitchenBodyCandidate:
    """Evidence for one accepted (or blocked) kitchen BODY candidate."""

    floor_id: str
    room_id: str
    body_status: str
    overall_status: str
    reason: str
    subzone_mm: tuple[float, float, float, float]
    centerline_mm: tuple[tuple[float, float], ...]
    rounded_centerline_mm: tuple[tuple[float, float], ...]
    rounded_length_mm: float
    rounded_coverage_ratio: float
    topology: Any | None
    bend_validation: Any | None
    reservation_id: str | None
    replaced_reservation_ids: tuple[str, ...]
    opening_candidates: tuple[Mapping[str, Any], ...]
    metadata: Mapping[str, Any]
    occupancy: Any | None

    @property
    def body_accepted(self) -> bool:
        return self.body_status == "ACCEPTED_SOURCE_LOCAL_BIFILAR_BODY"

    @property
    def opening_transit_blocked(self) -> bool:
        return self.overall_status == "BODY_ACCEPTED_OPENING_TRANSIT_BLOCKED"


def _source_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Test01OccupancySourceError(f"Cannot read Test_01 source package: {path}") from exc
    if not isinstance(payload, dict) or payload.get("project_id") != "Test_01":
        raise Test01OccupancySourceError("Kitchen candidate requires canonical Test_01 source")
    return payload


def _room(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    for room in payload.get("rooms", ()):
        if isinstance(room, Mapping) and room.get("id") == KITCHEN_ROOM_ID:
            if room.get("floor") != KITCHEN_FLOOR_ID or room.get("geometry_status") != "USABLE":
                raise Test01OccupancySourceError("Canonical kitchen room is not usable")
            return room
    raise Test01OccupancySourceError(f"Canonical kitchen room {KITCHEN_ROOM_ID} is missing")


def _valid_subzone(room_polygon: Polygon, subzone: tuple[float, float, float, float]) -> Polygon:
    x0, y0, x1, y1 = subzone
    if not all(isfinite(v) for v in subzone) or not (x1 > x0 and y1 > y0):
        raise ValueError("Kitchen subzone must be a finite positive rectangle")
    zone = Polygon(((x0, y0), (x1, y0), (x1, y1), (x0, y1)))
    if not room_polygon.covers(zone):
        raise ValueError("Kitchen subzone is not covered by the canonical room polygon")
    return zone


def _build_centerline(subzone: tuple[float, float, float, float]) -> tuple[tuple[float, float], ...]:
    x0, y0, x1, y1 = subzone
    # The kernel's local orientation exposes the two terminals on its west
    # edge after swapping its generated coordinates back to global x/y.
    raw = build_accessible_bifilar_spiral(
        (y0 + 108.0, x0 + 108.0, y1 - 108.0, x1 - 108.0),
        spacing_mm=SPACING_MM,
        minimum_bend_radius_mm=BEND_RADIUS_MM,
    )
    return tuple((float(v), float(u)) for u, v in raw)


def _blocked(
    reason: str,
    *,
    subzone: tuple[float, float, float, float],
    opening_candidates: tuple[Mapping[str, Any], ...],
    replaced: tuple[str, ...] = (),
    metadata: Mapping[str, Any] | None = None,
    occupancy: Any | None = None,
) -> KitchenBodyCandidate:
    base = {
        "construction_release": False,
        "full_circuit_valid": False,
        "building_transit_valid": False,
        "openings_imported": False,
        "opening_transit_status": "BLOCKED_UNVERIFIED_OPENING",
        "full_room_coverage_valid": False,
        "uncovered_room_residual_status": "UNPLANNED_OUTSIDE_DECLARED_SUBZONE",
    }
    if metadata:
        base.update(metadata)
    return KitchenBodyCandidate(
        KITCHEN_FLOOR_ID,
        KITCHEN_ROOM_ID,
        "BLOCKED_NO_ACCEPTED_BODY",
        "BODY_BLOCKED_OPENING_TRANSIT_BLOCKED",
        reason,
        subzone,
        (),
        (),
        0.0,
        0.0,
        None,
        None,
        None,
        replaced,
        opening_candidates,
        MappingProxyType(base),
        occupancy,
    )


def build_first_floor_kitchen_candidate(
    source_path: str | Path = DEFAULT_TEST01_SOURCE,
    *,
    cell_size_mm: float = DEFAULT_CELL_SIZE_MM,
    subzone_mm: tuple[float, float, float, float] = DEFAULT_KITCHEN_SUBZONE_MM,
) -> KitchenBodyCandidate:
    """Build one west-terminal bifilar kitchen BODY in fresh occupancy.

    The returned status can accept the coverage BODY while explicitly keeping
    opening/transit work blocked.  It never claims a full circuit or release.
    """

    path = Path(source_path).resolve()
    payload = _source_payload(path)
    room = _room(payload)
    openings = tuple(MappingProxyType(dict(item)) for item in OPENING_CANDIDATES)
    occupancy = import_test01_coverage_bodies(path, cell_size_mm=cell_size_mm)
    floor = occupancy[KITCHEN_FLOOR_ID]
    domain = occupancy.worlds[KITCHEN_FLOOR_ID].domain
    before_replacement = domain.snapshot()
    replaced = tuple(
        body.reservation_id
        for body in floor.bodies
        if body.room_id == KITCHEN_ROOM_ID and body.reservation_id is not None
    )
    for reservation_id in replaced:
        domain.release(reservation_id)

    def blocked_result(
        reason: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> KitchenBodyCandidate:
        domain.rollback(before_replacement)
        extra = {"replacement_committed": False}
        if metadata:
            extra.update(metadata)
        return _blocked(
            reason,
            subzone=subzone_mm,
            opening_candidates=openings,
            replaced=replaced,
            metadata=extra,
            occupancy=occupancy,
        )

    try:
        room_polygon = Polygon(room["global_boundary_mm"])
        zone = _valid_subzone(room_polygon, subzone_mm)
        centerline = _build_centerline(subzone_mm)
        if len(centerline) < 2:
            return blocked_result("BIFILAR_KERNEL_CANNOT_FIT_SUBZONE")
        topology = validate_bifilar_topology(
            tuple((int(round(x)), int(round(y))) for x, y in centerline),
            tuple(int(round(v)) for v in subzone_mm),
            tuple((int(round(x)), int(round(y))) for x, y in zone.exterior.coords),
            spacing_mm=int(SPACING_MM),
            minimum_bend_radius_mm=int(BEND_RADIUS_MM),
        )
        bend = validate_rounded_centerline(
            centerline,
            tuple(room_polygon.exterior.coords),
            bend_radius_mm=BEND_RADIUS_MM,
            pipe_outer_radius_mm=PIPE_OUTER_RADIUS_MM,
            samples_per_quarter=24,
        )
        rounded = tuple(bend.rounded_points)
        coverage_band = LineString(rounded).buffer(SPACING_MM / 2.0, quad_segs=12)
        coverage_ratio = float(coverage_band.intersection(zone).area / zone.area)
        sharp_mask = supercover_polyline_mask(domain, centerline)
        rounded_mask = supercover_polyline_mask(domain, rounded)
        material_mask = sharp_mask | rounded_mask
        if not topology.valid or not bend.valid or not LineString(centerline).is_simple:
            return blocked_result(
                "BIFILAR_OR_R80_VALIDATION_FAILED",
                metadata={"topology": topology, "bend_validation": bend},
            )
        if bend.rounded_length_mm > MAXIMUM_CIRCUIT_LENGTH_MM:
            return blocked_result(
                "ROUNDED_LENGTH_EXCEEDS_90M",
                metadata={"topology": topology, "bend_validation": bend},
            )
        # Reserve the full conservative pipe footprint as material.  The
        # centreline supercover already includes every closed cell touched by
        # either representation; dilation adds the 8 mm pipe outer radius.
        material_mask = domain.dilate_mask(
            material_mask,
            clearance_mm=PIPE_OUTER_RADIUS_MM,
        )
        reservation = domain.reserve(
            material_mask,
            owner=f"{KITCHEN_ROOM_ID}/candidate-counterflow-body",
            role="BODY",
            clearance_mm=0.0,
            reservation_id="test01-body:FLOOR_1_PLAN:kitchen-candidate-counterflow-body",
        )
    except (KeyError, TypeError, ValueError, RasterDomainError, ReservationConflictError) as exc:
        return blocked_result(
            f"CANDIDATE_BLOCKED_FAIL_CLOSED: {exc}",
        )

    metadata = MappingProxyType(
        {
            "construction_release": False,
            "full_circuit_valid": False,
            "building_transit_valid": False,
            "openings_imported": False,
            "opening_transit_status": "BLOCKED_UNVERIFIED_OPENING",
            "source_project": "Test_01",
            "source_room_label": room.get("label"),
            "material_mask_definition": "sharp_union_actual_R80_supercover_dilated_by_pipe_outer_radius",
            "pipe_outer_radius_in_material_mm": PIPE_OUTER_RADIUS_MM,
            "terminal_access": "WEST_FACING_TWO_TERMINALS",
            "terminal_opening_candidate": "UPPER_SOURCE_DERIVED_ROOM_FACE_INTERVAL_UNVERIFIED",
            "replacement_committed": True,
            "coverage_scope": "DECLARED_SUBZONE_ONLY",
            "full_room_coverage_valid": False,
            "uncovered_room_residual_status": "UNPLANNED_OUTSIDE_DECLARED_SUBZONE",
        }
    )
    return KitchenBodyCandidate(
        KITCHEN_FLOOR_ID,
        KITCHEN_ROOM_ID,
        "ACCEPTED_SOURCE_LOCAL_BIFILAR_BODY",
        "BODY_ACCEPTED_OPENING_TRANSIT_BLOCKED",
        "R80-valid bifilar BODY reserved; source openings remain unverified and transit is blocked",
        subzone_mm,
        centerline,
        rounded,
        float(bend.rounded_length_mm),
        coverage_ratio,
        topology,
        bend,
        reservation.reservation_id,
        replaced,
        openings,
        metadata,
        occupancy,
    )


# Short aliases make the bounded candidate easy to discover without creating a
# second implementation or implying that this is the final floor generator.
build_kitchen_candidate = build_first_floor_kitchen_candidate
generate_kitchen_candidate = build_first_floor_kitchen_candidate


__all__ = [
    "DEFAULT_KITCHEN_SUBZONE_MM",
    "KITCHEN_FLOOR_ID",
    "KITCHEN_ROOM_ID",
    "KitchenBodyCandidate",
    "OPENING_CANDIDATES",
    "build_first_floor_kitchen_candidate",
    "build_kitchen_candidate",
    "generate_kitchen_candidate",
]

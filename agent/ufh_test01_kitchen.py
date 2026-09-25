"""Bounded first-floor kitchen BODY candidate.

This module is deliberately narrower than a floor generator.  It replaces the
two source kitchen BODY reservations in a fresh Test_01 occupancy world with
one independently checked rectangular counterflow body.  Door openings are
retained as source-vector *candidates* only; no wall crossing, transit, or
manifold connection is emitted.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
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
MINIMUM_FREE_PIPE_CLEARANCE_MM = 16.0
MINIMUM_AXIS_TO_AXIS_CLEARANCE_MM = MINIMUM_FREE_PIPE_CLEARANCE_MM + 2.0 * PIPE_OUTER_RADIUS_MM
MINIMUM_AXIS_TO_ROOM_BOUNDARY_MM = MINIMUM_FREE_PIPE_CLEARANCE_MM + PIPE_OUTER_RADIUS_MM
CANONICAL_KITCHEN_ROUTE_IDS = ("multi_bifilar_spiral-1", "multi_bifilar_spiral-2")
CANONICAL_KITCHEN_RESERVATION_IDS = tuple(
    f"test01-body:{KITCHEN_ROOM_ID}/{route_id}" for route_id in CANONICAL_KITCHEN_ROUTE_IDS
)
KITCHEN_OPENING_IDS = (
    "FLOOR_1_PLAN-KITCHEN-CORRIDOR-UPPER",
    "FLOOR_1_PLAN-KITCHEN-CORRIDOR-LOWER",
)
DEFAULT_OPENINGS_SOURCE = DEFAULT_TEST01_SOURCE.parent / "16_DOOR_OPENINGS_FROM_PDF.json"

# This zone is a conservative rectangle wholly contained in the source room.
# Keeping its north edge below the stair/notch transition avoids inventing a
# route through the irregular part of the source polygon.
DEFAULT_KITCHEN_SUBZONE_MM = (13_000.0, 8_750.0, 18_150.0, 11_600.0)
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


def _opening_candidates(
    path: Path = DEFAULT_OPENINGS_SOURCE,
) -> tuple[tuple[Mapping[str, Any], ...], Mapping[str, Any]]:
    """Load raw source vectors without inferring terminal alignment."""

    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        openings = payload["openings"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise Test01OccupancySourceError(f"Cannot read canonical opening evidence: {path}") from exc
    if payload.get("authority") != "SOURCE_VECTOR_GEOMETRY" or not isinstance(openings, list):
        raise Test01OccupancySourceError("Canonical opening evidence has invalid provenance")
    by_id = {item.get("opening_id"): item for item in openings if isinstance(item, dict)}
    candidates: list[Mapping[str, Any]] = []
    for opening_id in KITCHEN_OPENING_IDS:
        item = by_id.get(opening_id)
        if not isinstance(item, dict):
            raise Test01OccupancySourceError("Canonical kitchen opening candidates are incomplete")
        try:
            vector = tuple((float(p[0]), float(p[1])) for p in item["opening_mm"])
            adjacent = tuple(str(value) for value in item["adjacent_room_ids"])
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise Test01OccupancySourceError(f"Malformed opening evidence: {opening_id}") from exc
        if (
            len(vector) != 2
            or item.get("document_id") != KITCHEN_FLOOR_ID
            or KITCHEN_ROOM_ID not in adjacent
            or item.get("geometry_status") != "DOOR_GEOMETRY_SOURCE_GAP_CANDIDATE"
            or item.get("passage_status") != "UNVERIFIED_SOURCE_VECTOR_CONFIRMED"
        ):
            raise Test01OccupancySourceError(f"Unexpected opening evidence: {opening_id}")
        candidates.append(MappingProxyType({
            "opening_id": opening_id,
            "source_vector_mm": vector,
            "orientation": item.get("orientation"),
            "adjacent_room_ids": adjacent,
            "geometry_status": item.get("geometry_status"),
            "passage_status": item.get("passage_status"),
            "endpoint_alignment_status": "NOT_ALIGNED_TO_SOURCE_VECTOR",
            "transit_status": "BLOCKED_UNVERIFIED_OPENING",
        }))
    provenance = MappingProxyType({
        "path": str(path.resolve()),
        "sha256": sha256(raw).hexdigest(),
        "authority": payload["authority"],
        "method": payload.get("method"),
    })
    return tuple(candidates), provenance


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
    openings, opening_provenance = _opening_candidates()
    occupancy = import_test01_coverage_bodies(path, cell_size_mm=cell_size_mm)
    floor = occupancy[KITCHEN_FLOOR_ID]
    domain = occupancy.worlds[KITCHEN_FLOOR_ID].domain
    before_replacement = domain.snapshot()
    kitchen_bodies = tuple(body for body in floor.bodies if body.room_id == KITCHEN_ROOM_ID)
    replaced = tuple(
        body.reservation_id
        for body in kitchen_bodies
        if body.reservation_id is not None
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

    source_route_ids = tuple(str(value) for value in room.get("route_ids", ()))
    reported_route_ids = tuple(body.route_id for body in kitchen_bodies)
    reported_reservation_ids = tuple(body.reservation_id for body in kitchen_bodies)
    domain_kitchen_ids = tuple(
        reservation_id
        for reservation_id, reservation in before_replacement.reservations.items()
        if reservation.role == "BODY" and reservation.owner.startswith(f"{KITCHEN_ROOM_ID}/")
    )
    canonical_source_bodies = (
        source_route_ids == CANONICAL_KITCHEN_ROUTE_IDS
        and reported_route_ids == CANONICAL_KITCHEN_ROUTE_IDS
        and all(body.imported for body in kitchen_bodies)
        and reported_reservation_ids == CANONICAL_KITCHEN_RESERVATION_IDS
        and domain_kitchen_ids == CANONICAL_KITCHEN_RESERVATION_IDS
    )
    if not canonical_source_bodies:
        return blocked_result(
            "CANONICAL_KITCHEN_SOURCE_BODY_SET_MISMATCH",
            metadata={
                "expected_source_route_ids": CANONICAL_KITCHEN_ROUTE_IDS,
                "actual_source_route_ids": source_route_ids,
                "reported_route_ids": reported_route_ids,
                "expected_source_reservation_ids": CANONICAL_KITCHEN_RESERVATION_IDS,
                "actual_source_reservation_ids": reported_reservation_ids,
                "canonical_source_body_count_valid": False,
                "opening_source_provenance": opening_provenance,
            },
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
        rounded_axis = LineString(rounded)
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
        own_clearance = bend.minimum_non_adjacent_clearance_mm
        boundary_clearance = float(rounded_axis.distance(room_polygon.boundary))
        retained_clearances: dict[str, float] = {}
        retained_bodies = {
            body.reservation_id: body
            for body in floor.bodies
            if body.reservation_id is not None and body.reservation_id not in replaced
        }
        retained_reservation_ids = {
            reservation_id
            for reservation_id, reservation in domain.reservations.items()
            if reservation.role == "BODY"
        }
        if set(retained_bodies) != retained_reservation_ids:
            return blocked_result(
                "RETAINED_BODY_R80_EVIDENCE_INCOMPLETE",
                metadata={"vector_clearance_status": "BLOCKED_UNPROVEN"},
            )
        for reservation_id, body in retained_bodies.items():
            if len(body.rounded_global_points_mm) < 2:
                return blocked_result(
                    "RETAINED_BODY_R80_EVIDENCE_INCOMPLETE",
                    metadata={"vector_clearance_status": "BLOCKED_UNPROVEN"},
                )
            retained_clearances[reservation_id] = float(
                rounded_axis.distance(LineString(body.rounded_global_points_mm))
            )
        retained_minimum = min(retained_clearances.values()) if retained_clearances else None
        if (
            own_clearance is None
            or own_clearance < MINIMUM_AXIS_TO_AXIS_CLEARANCE_MM
            or boundary_clearance < MINIMUM_AXIS_TO_ROOM_BOUNDARY_MM
            or (retained_minimum is not None and retained_minimum < MINIMUM_AXIS_TO_AXIS_CLEARANCE_MM)
        ):
            return blocked_result(
                "R80_VECTOR_PHYSICAL_CLEARANCE_FAILED",
                metadata={
                    "vector_clearance_status": "BLOCKED_INSUFFICIENT_CLEARANCE",
                    "minimum_own_nonadjacent_axis_clearance_mm": own_clearance,
                    "minimum_axis_to_retained_body_mm": retained_minimum,
                    "minimum_axis_to_room_boundary_mm": boundary_clearance,
                    "retained_body_axis_clearances_mm": MappingProxyType(retained_clearances),
                },
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
            "terminal_source_vector_alignment": "NOT_ALIGNED_TO_SOURCE_VECTOR",
            "opening_source_provenance": opening_provenance,
            "source_project": "Test_01",
            "source_room_label": room.get("label"),
            "material_mask_definition": "sharp_union_actual_R80_supercover_dilated_by_pipe_outer_radius",
            "pipe_outer_radius_in_material_mm": PIPE_OUTER_RADIUS_MM,
            "terminal_access": "WEST_FACING_TWO_TERMINALS",
            "replacement_committed": True,
            "canonical_source_body_count_valid": True,
            "expected_source_route_ids": CANONICAL_KITCHEN_ROUTE_IDS,
            "expected_source_reservation_ids": CANONICAL_KITCHEN_RESERVATION_IDS,
            "vector_clearance_status": "PROVEN_R80_AXIS_CLEARANCES",
            "required_own_nonadjacent_axis_clearance_mm": MINIMUM_AXIS_TO_AXIS_CLEARANCE_MM,
            "minimum_own_nonadjacent_axis_clearance_mm": own_clearance,
            "required_axis_to_retained_body_mm": MINIMUM_AXIS_TO_AXIS_CLEARANCE_MM,
            "minimum_axis_to_retained_body_mm": retained_minimum,
            "retained_body_axis_clearances_mm": MappingProxyType(retained_clearances),
            "required_axis_to_room_boundary_mm": MINIMUM_AXIS_TO_ROOM_BOUNDARY_MM,
            "minimum_axis_to_room_boundary_mm": boundary_clearance,
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
    "DEFAULT_OPENINGS_SOURCE",
    "CANONICAL_KITCHEN_RESERVATION_IDS",
    "CANONICAL_KITCHEN_ROUTE_IDS",
    "KITCHEN_FLOOR_ID",
    "KITCHEN_ROOM_ID",
    "KitchenBodyCandidate",
    "build_first_floor_kitchen_candidate",
    "build_kitchen_candidate",
    "generate_kitchen_candidate",
]

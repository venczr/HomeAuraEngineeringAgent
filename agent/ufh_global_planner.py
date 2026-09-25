"""Global preliminary layout planner for the whole UFH building.

This module assembles the building-wide preliminary registry: every room's
coverage candidate, the estimated number of independent circuits (including
the future supply/return transit), and the resulting pipe load per doorway,
corridor segment and manifold.  It is a planning layer, not a construction
authority: every number that depends on unverified transit/openings is kept as
an explicit range or lower bound rather than silently promoted to a fact.

Circuit-count policy
--------------------
The preview length limit (90 m) is the budget of *one* physical loop.  A loop
consists of the in-room coverage plus its own supply and return transit (and,
for the mansard, the vertical rise/drop).  Splitting a room into N circuits
therefore does *not* share the transit: every new circuit pays the transit and
vertical overhead again.  The count is derived from the coverage that remains
after reserving the per-circuit overhead::

    N = ceil(coverage / (policy_limit - transit - vertical))

The old ``ceil((coverage + transit + vertical) / policy_limit)`` rule treated
the transit as a one-off cost and understated the number of circuits for rooms
whose transit is a large share of the budget.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from typing import Any


POLICY_LIMIT_M = 90.0
MIN_CIRCUIT_LENGTH_M = 40.0


@dataclass(frozen=True)
class RoomRecord:
    """One room's preliminary registry entry."""

    zone_id: str
    floor: int
    zone_type: str
    label: str
    authority: str
    area_m2: float | None = None
    coverage_length_m: float | None = None
    transit_length_m: float | None = None
    vertical_length_m: float = 0.0
    geometry_status: str = "UNKNOWN"

    def as_dict(self) -> dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "floor": self.floor,
            "zone_type": self.zone_type,
            "label": self.label,
            "authority": self.authority,
            "geometry_status": self.geometry_status,
            "area_m2": self.area_m2,
            "coverage_length_m": self.coverage_length_m,
            "transit_length_m": self.transit_length_m,
            "vertical_length_m": self.vertical_length_m,
        }


@dataclass(frozen=True)
class CircuitCountEstimate:
    room_zone_id: str
    count: int | None
    minimum_count: int
    basis: str
    reason: str
    total_length_m: float | None = None
    per_circuit_overhead_m: float | None = None
    max_circuit_length_m: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "room_zone_id": self.room_zone_id,
            "count": self.count,
            "minimum_count": self.minimum_count,
            "basis": self.basis,
            "reason": self.reason,
            "total_length_m": None if self.total_length_m is None else round(self.total_length_m, 3),
            "per_circuit_overhead_m": None if self.per_circuit_overhead_m is None else round(self.per_circuit_overhead_m, 3),
            "max_circuit_length_m": None if self.max_circuit_length_m is None else round(self.max_circuit_length_m, 3),
        }


def estimate_circuit_count(
    room: RoomRecord,
    *,
    policy_limit_m: float = POLICY_LIMIT_M,
) -> CircuitCountEstimate:
    """Estimate the preliminary independent-circuit count for a room.

    A circuit's total length must include the in-room coverage AND its own
    supply/return transit to the manifold.  When the transit estimate is
    available the count is exact for the policy budget; when it is unknown the
    result is a lower bound built from coverage alone, so the room is never
    silently dropped from the pipe-load calculation.  Rooms with unresolved
    coverage geometry are kept as an explicit blocker rather than zero.
    """
    if room.coverage_length_m is None:
        return CircuitCountEstimate(
            room.zone_id,
            None,
            1,
            "BLOCKED_UNKNOWN_COVERAGE",
            "room coverage geometry is unresolved; a heated room needs at least one circuit",
        )

    coverage = room.coverage_length_m
    vertical = room.vertical_length_m

    if room.transit_length_m is None:
        minimum_count = max(1, int(ceil((coverage + vertical) / policy_limit_m)))
        return CircuitCountEstimate(
            room.zone_id,
            None,
            minimum_count,
            "LOWER_BOUND_UNVERIFIED_TRANSIT",
            "transit length to manifold is not yet authorized",
        )

    overhead = room.transit_length_m + vertical
    budget = policy_limit_m - overhead
    if budget <= 0.0:
        return CircuitCountEstimate(
            room.zone_id,
            None,
            1,
            "BLOCKED_TRANSIT_EXCEEDS_LIMIT",
            "per-circuit supply+return transit and vertical exceed the policy limit before any coverage",
            per_circuit_overhead_m=overhead,
        )

    count = max(1, int(ceil(coverage / budget)))
    return CircuitCountEstimate(
        room.zone_id,
        count,
        count,
        "PRELIMINARY_EXACT",
        (
            "coverage plus per-circuit transit and vertical exceed the policy limit"
            if count > 1
            else "fits within the policy limit"
        ),
        total_length_m=coverage + overhead * count,
        per_circuit_overhead_m=overhead,
        max_circuit_length_m=coverage / count + overhead,
    )


def room_pipe_demand(room: RoomRecord, estimate: CircuitCountEstimate) -> int:
    """Return the number of pipe ends (supply + return) a room needs.

    Every independent circuit requires exactly one supply and one return, i.e.
    two pipe ends.  A room whose circuit count is unknown contributes only its
    proven lower bound so the total never understates the demand.
    """
    count = estimate.count if estimate.count is not None else estimate.minimum_count
    return 2 * count


def total_circuit_count(estimates: list[CircuitCountEstimate]) -> int | None:
    """Return the exact total circuit count, or None if any room is blocked."""
    total = 0
    for estimate in estimates:
        if estimate.count is None:
            return None
        total += estimate.count
    return total


def total_minimum_circuit_count(estimates: list[CircuitCountEstimate]) -> int:
    return sum(estimate.minimum_count for estimate in estimates)


@dataclass
class CorridorPassage:
    """A corridor, doorway or riser segment with its preliminary pipe load."""

    passage_id: str
    carrier_room_ids: list[str] = field(default_factory=list)
    supply_pipe_count: int = 0
    return_pipe_count: int = 0
    required_width_mm: float | None = None
    available_width_mm: float | None = None
    capacity_status: str = "UNKNOWN"

    def as_dict(self) -> dict[str, Any]:
        return {
            "passage_id": self.passage_id,
            "carrier_room_ids": list(self.carrier_room_ids),
            "supply_pipe_count": self.supply_pipe_count,
            "return_pipe_count": self.return_pipe_count,
            "required_width_mm": self.required_width_mm,
            "available_width_mm": self.available_width_mm,
            "capacity_status": self.capacity_status,
        }


def passage_pipe_load(
    passage: CorridorPassage,
    estimates_by_room: dict[str, CircuitCountEstimate],
) -> tuple[int, int, int]:
    """Count supply/return pipes carried by one passage from its carrier rooms.

    Returns ``(supply_pipe_count, return_pipe_count, unresolved_room_count)``.
    A passage carries exactly the circuits of its carrier rooms: the manifold's
    own egress count is *not* automatically the pipe count of every downstream
    segment.
    """
    supply = 0
    return_count = 0
    unresolved = 0
    for room_id in passage.carrier_room_ids:
        estimate = estimates_by_room.get(room_id)
        if estimate is None:
            unresolved += 1
            continue
        count = estimate.count if estimate.count is not None else estimate.minimum_count
        supply += count
        return_count += count
        if estimate.count is None:
            unresolved += 1
    return supply, return_count, unresolved


def required_pipe_width_mm(
    pipe_count: int,
    *,
    pipe_outer_diameter_mm: float = 16.0,
    minimum_free_clearance_mm: float = 16.0,
    edge_clearance_mm: float = 50.0,
    lane_spacing_mm: float | None = None,
) -> float:
    if pipe_count <= 0:
        return 0.0
    pitch = (
        lane_spacing_mm
        if lane_spacing_mm is not None
        else pipe_outer_diameter_mm + minimum_free_clearance_mm
    )
    return 2 * edge_clearance_mm + pipe_outer_diameter_mm + (pipe_count - 1) * pitch


def build_global_preliminary_plan(
    rooms: list[RoomRecord],
    passages: list[CorridorPassage],
    *,
    policy_limit_m: float = POLICY_LIMIT_M,
) -> dict[str, Any]:
    """Assemble the global preliminary plan from room records and passages.

    Returns room estimates, per-passage pipe load, and the manifold demand.
    The manifold demand counts supply and return ends separately and is never
    asserted to be physically connectable; every downstream passage is computed
    independently from its own carrier rooms.
    """
    estimates = [estimate_circuit_count(room, policy_limit_m=policy_limit_m) for room in rooms]
    estimates_by_room = {estimate.room_zone_id: estimate for estimate in estimates}
    total = total_circuit_count(estimates)
    minimum = total_minimum_circuit_count(estimates)
    supply_ends = sum(e.count if e.count is not None else e.minimum_count for e in estimates)
    return_ends = supply_ends

    room_rows: list[dict[str, Any]] = []
    for room, estimate in zip(rooms, estimates):
        row = room.as_dict()
        row.update(estimate.as_dict())
        row["pipe_end_demand"] = room_pipe_demand(room, estimate)
        row["blocked"] = estimate.count is None
        room_rows.append(row)

    passage_rows: list[dict[str, Any]] = []
    for passage in passages:
        supply, return_count, unresolved = passage_pipe_load(passage, estimates_by_room)
        row = passage.as_dict()
        row["supply_pipe_count"] = supply
        row["return_pipe_count"] = return_count
        row["pipe_count"] = supply + return_count
        row["unresolved_room_count"] = unresolved
        passage_rows.append(row)

    return {
        "policy_limit_m": policy_limit_m,
        "room_count": len(rooms),
        "room_estimates": room_rows,
        "total_circuit_count": total,
        "minimum_total_circuit_count": minimum,
        "manifold_demand": {
            "supply_ends": supply_ends,
            "return_ends": return_ends,
            "total_pipe_ends": supply_ends + return_ends,
            "connection_authority": "UNVERIFIED",
            "note": (
                "Manifold pipe ends are not equal to the pipe count of every "
                "corridor segment: each segment carries only its own carrier rooms."
            ),
        },
        "passages": passage_rows,
    }


__all__ = [
    "POLICY_LIMIT_M",
    "RoomRecord",
    "CircuitCountEstimate",
    "CorridorPassage",
    "estimate_circuit_count",
    "room_pipe_demand",
    "passage_pipe_load",
    "total_circuit_count",
    "total_minimum_circuit_count",
    "required_pipe_width_mm",
    "build_global_preliminary_plan",
]

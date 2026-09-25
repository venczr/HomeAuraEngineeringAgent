"""Bounded directional A* routing over :mod:`agent.ufh_world_state`.

The router is deliberately a candidate-search layer.  A returned route is a
sequence of raster cells and is never a claim that a pipe can be installed:
the existing vector, bend, wall-crossing and hydraulic validators still have
to be run by the caller.

The search state is ``(cell, direction)``.  Four-neighbour moves are explored
in a fixed order and a configurable turn penalty is charged whenever the
direction changes.  Static obstacles and reservations owned by another owner
are always impassable.  Same-owner traversal can be enabled for existing
material plus an exact terminal/join mask supplied by the caller.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from heapq import heappop, heappush
from math import isfinite
from typing import Any, Iterable, Sequence

from agent.ufh_world_state import (
    RasterDomainError,
    RasterReservation,
    RasterRoutingDomain,
    ReservationConflictError,
    WorldState,
)


Cell = tuple[int, int]
Direction = tuple[int, int]

# The order is part of the public determinism contract.  It is also used as a
# stable tie-break when two cells have the same A* score.
DIRECTIONS: tuple[Direction, ...] = (
    (-1, 0),  # north
    (0, 1),   # east
    (1, 0),   # south
    (0, -1),  # west
)
_START_DIRECTION = -1


@dataclass(frozen=True)
class RasterRouteResult:
    """Result of a raster search, optionally followed by one reservation."""

    status: str
    start: Cell
    goal: Cell
    path: tuple[Cell, ...] = ()
    directions: tuple[Direction, ...] = ()
    cost: float | None = None
    expanded_cells: int = 0
    max_expanded_cells: int = 0
    turn_count: int = 0
    reservation_id: str | None = None
    diagnostics: tuple[str, ...] = ()
    # This layer never promotes a route to an engineering/physical result.
    physical_validation: str = "NOT_EVALUATED"

    @property
    def cells(self) -> tuple[Cell, ...]:
        """Alias used by callers that call a route's cells rather than path."""

        return self.path

    @property
    def found(self) -> bool:
        return self.status in {"ROUTE_FOUND", "ROUTE_RESERVED", "ALREADY_RESERVED_BY_OWNER"}

    @property
    def reserved(self) -> bool:
        return self.status in {"ROUTE_RESERVED", "ALREADY_RESERVED_BY_OWNER"}

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "start": list(self.start),
            "goal": list(self.goal),
            "path": [list(cell) for cell in self.path],
            "cells": [list(cell) for cell in self.path],
            "directions": [list(direction) for direction in self.directions],
            "cost": None if self.cost is None else round(float(self.cost), 9),
            "expanded_cells": self.expanded_cells,
            "max_expanded_cells": self.max_expanded_cells,
            "turn_count": self.turn_count,
            "reservation_id": self.reservation_id,
            "diagnostics": list(self.diagnostics),
            "physical_validation": self.physical_validation,
        }


def _cell(value: Sequence[int], *, name: str) -> Cell:
    if isinstance(value, (str, bytes)) or len(value) != 2:
        raise RasterDomainError(f"{name} must contain exactly row and column")
    if any(isinstance(item, bool) or int(item) != item for item in value):
        raise RasterDomainError(f"{name} row and column must be integers")
    return int(value[0]), int(value[1])


def _validate_number(value: float, *, name: str, nonnegative: bool = True) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise RasterDomainError(f"{name} must be finite") from exc
    if not isfinite(result) or (nonnegative and result < 0):
        suffix = " non-negative" if nonnegative else ""
        raise RasterDomainError(f"{name} must be finite{suffix}")
    return result


def _result(
    status: str,
    start: Cell,
    goal: Cell,
    *,
    max_expanded_cells: int,
    diagnostics: Iterable[str] = (),
    **values: Any,
) -> RasterRouteResult:
    diagnostic_list = list(dict.fromkeys([*diagnostics, "RASTER_ROUTE_REQUIRES_VECTOR_VALIDATION"]))
    return RasterRouteResult(
        status=status,
        start=start,
        goal=goal,
        max_expanded_cells=max_expanded_cells,
        diagnostics=tuple(diagnostic_list),
        **values,
    )


def _occupancy_policy(
    world: RasterRoutingDomain,
    *,
    owner: str | None,
    allow_same_owner: bool,
    same_owner_join_mask: Any | None,
) -> tuple[Any, Any, Any, Any]:
    """Return occupied and exact same-owner access/protection masks."""

    occupied = world.occupied_mask
    if not allow_same_owner or owner is None:
        return occupied, world.empty_mask(), world.empty_mask(), world.empty_mask()
    same_owner_material = world.material_mask_for_owner(owner)
    same_owner_protected = world.protected_mask_for_owner(owner)
    same_owner_access = world.same_owner_access_mask(
        owner, join_mask=same_owner_join_mask
    )
    return occupied, same_owner_material, same_owner_protected, same_owner_access


def _routing_blocked_mask(
    world: RasterRoutingDomain,
    *,
    owner: str | None,
    allow_same_owner: bool,
    same_owner_join_mask: Any | None,
    clearance_mm: float,
) -> tuple[Any, Any, Any, Any]:
    """Build the conservative obstacle layer seen by candidate material cells."""

    static = world.static_mask
    occupied, same_owner_material, same_owner_protected, same_owner_access = _occupancy_policy(
        world,
        owner=owner,
        allow_same_owner=allow_same_owner,
        same_owner_join_mask=same_owner_join_mask,
    )
    blocked_static = world.dilate_mask(static, clearance_mm=clearance_mm)
    if allow_same_owner and owner is not None:
        foreign_occupied = occupied & ~same_owner_protected
        blocked_foreign = world.dilate_mask(
            foreign_occupied, clearance_mm=clearance_mm
        )
        forbidden_same_owner = same_owner_protected & ~same_owner_access
        blocked_same_owner = world.dilate_mask(
            forbidden_same_owner, clearance_mm=clearance_mm
        )
        # Existing material is not re-reserved, so it remains traversable even
        # when its neighbourhood contains protected-only cells.  New material,
        # including a join cell, is accepted only when its complete clearance
        # footprint intersects authorized same-owner cells exclusively.
        blocked_same_owner[same_owner_access] = False
        blocked_occupied = blocked_foreign | blocked_same_owner
        blocked_static[same_owner_material & ~blocked_foreign] = False
    else:
        blocked_occupied = world.dilate_mask(occupied, clearance_mm=clearance_mm)
    return blocked_static, blocked_occupied, same_owner_material, same_owner_protected


def _is_blocked(
    cell: Cell,
    *,
    static_mask: Any,
    blocked_occupied: Any,
) -> bool:
    return bool(static_mask[cell] or blocked_occupied[cell])


def route_raster_a_star(
    world: RasterRoutingDomain,
    start: Sequence[int],
    goal: Sequence[int],
    *,
    owner: str | None = None,
    allow_same_owner: bool = False,
    same_owner_join_mask: Any | None = None,
    clearance_mm: float = 0.0,
    step_cost: float = 1.0,
    turn_penalty: float = 0.0,
    max_expanded_cells: int = 10_000,
) -> RasterRouteResult:
    """Find a bounded 4-neighbour route in ``world``.

    ``start`` and ``goal`` are raster cells in ``(row, column)`` order.  The
    world is read-only during this function.  Occupied cells are blocked by
    default.  With ``allow_same_owner=True``, existing material may be
    traversed; protected-only cells remain blocked unless included in the
    exact ``same_owner_join_mask``.
    """

    try:
        start_cell = _cell(start, name="start")
        goal_cell = _cell(goal, name="goal")
        world._validate_cell(start_cell)  # type: ignore[attr-defined]
        world._validate_cell(goal_cell)  # type: ignore[attr-defined]
        clearance = _validate_number(clearance_mm, name="clearance_mm")
        step = _validate_number(step_cost, name="step_cost")
        turn = _validate_number(turn_penalty, name="turn_penalty")
        if not isinstance(max_expanded_cells, int) or isinstance(max_expanded_cells, bool) or max_expanded_cells <= 0:
            raise RasterDomainError("max_expanded_cells must be a positive integer")
        if owner is not None and (not isinstance(owner, str) or not owner.strip()):
            raise RasterDomainError("owner must be a non-empty string when supplied")
        if allow_same_owner and owner is None:
            raise RasterDomainError("owner is required when allow_same_owner=True")
        if same_owner_join_mask is not None and not allow_same_owner:
            raise RasterDomainError(
                "same_owner_join_mask requires allow_same_owner=True"
            )
    except (RasterDomainError, TypeError, ValueError) as exc:
        # There is no valid cell pair to put in a typed result when coercion
        # itself failed.  Preserve the exception for programmer errors while
        # still keeping the normal fail-closed result path deterministic.
        raise RasterDomainError(str(exc)) from exc

    original_static = world.static_mask
    original_occupied = world.occupied_mask
    static_mask, blocked_occupied, same_owner_material, same_owner_protected = _routing_blocked_mask(
        world,
        owner=owner,
        allow_same_owner=allow_same_owner,
        same_owner_join_mask=same_owner_join_mask,
        clearance_mm=clearance,
    )
    if original_static[start_cell]:
        return _result("BLOCKED_START", start_cell, goal_cell, max_expanded_cells=max_expanded_cells, diagnostics=("START_STATIC_BLOCKED",))
    if original_static[goal_cell]:
        return _result("BLOCKED_GOAL", start_cell, goal_cell, max_expanded_cells=max_expanded_cells, diagnostics=("GOAL_STATIC_BLOCKED",))
    if blocked_occupied[start_cell]:
        diagnostic = "START_OCCUPIED"
        if allow_same_owner:
            diagnostic = (
                "START_SAME_OWNER_PROTECTED_BUFFER"
                if same_owner_protected[start_cell] and not same_owner_material[start_cell]
                else "START_OCCUPIED_BY_FOREIGN_OWNER"
            )
        if not original_occupied[start_cell]:
            diagnostic = "START_CLEARANCE_BLOCKED"
        return _result("BLOCKED_START", start_cell, goal_cell, max_expanded_cells=max_expanded_cells, diagnostics=(diagnostic,))
    if blocked_occupied[goal_cell]:
        diagnostic = "GOAL_OCCUPIED"
        if allow_same_owner:
            diagnostic = (
                "GOAL_SAME_OWNER_PROTECTED_BUFFER"
                if same_owner_protected[goal_cell] and not same_owner_material[goal_cell]
                else "GOAL_OCCUPIED_BY_FOREIGN_OWNER"
            )
        if not original_occupied[goal_cell]:
            diagnostic = "GOAL_CLEARANCE_BLOCKED"
        return _result("BLOCKED_GOAL", start_cell, goal_cell, max_expanded_cells=max_expanded_cells, diagnostics=(diagnostic,))
    if static_mask[start_cell]:
        return _result("BLOCKED_START", start_cell, goal_cell, max_expanded_cells=max_expanded_cells, diagnostics=("START_STATIC_CLEARANCE_BLOCKED",))
    if static_mask[goal_cell]:
        return _result("BLOCKED_GOAL", start_cell, goal_cell, max_expanded_cells=max_expanded_cells, diagnostics=("GOAL_STATIC_CLEARANCE_BLOCKED",))
    if start_cell == goal_cell:
        return _result("ROUTE_FOUND", start_cell, goal_cell, max_expanded_cells=max_expanded_cells, path=(start_cell,), directions=(), cost=0.0, expanded_cells=0, turn_count=0)

    # State is ((row, column), direction index); the start state has no
    # direction, so its first step never incurs a turn penalty.
    start_state = (start_cell, _START_DIRECTION)
    g_score: dict[tuple[Cell, int], float] = {start_state: 0.0}
    turns: dict[tuple[Cell, int], int] = {start_state: 0}
    parent: dict[tuple[Cell, int], tuple[Cell, int] | None] = {start_state: None}
    heap: list[tuple[float, float, int, int, int, int, int, tuple[Cell, int]]] = []
    serial = 0

    def heuristic(cell: Cell) -> float:
        return step * (abs(cell[0] - goal_cell[0]) + abs(cell[1] - goal_cell[1]))

    heappush(heap, (heuristic(start_cell), 0.0, 0, start_cell[0], start_cell[1], _START_DIRECTION, serial, start_state))
    expanded = 0
    goal_state: tuple[Cell, int] | None = None

    while heap:
        _f, current_g, _turn_count, row, column, direction_index, _serial, state = heappop(heap)
        if current_g != g_score.get(state):
            continue
        expanded += 1
        current_cell, current_direction = state
        if current_cell == goal_cell:
            goal_state = state
            break
        if expanded >= max_expanded_cells:
            return _result(
                "SEARCH_LIMIT_REACHED", start_cell, goal_cell,
                max_expanded_cells=max_expanded_cells,
                expanded_cells=expanded,
                diagnostics=("MAX_EXPANDED_CELLS_REACHED",),
            )
        for next_direction, (delta_row, delta_column) in enumerate(DIRECTIONS):
            next_cell = (current_cell[0] + delta_row, current_cell[1] + delta_column)
            if not (0 <= next_cell[0] < world.shape[0] and 0 <= next_cell[1] < world.shape[1]):
                continue
            if _is_blocked(next_cell, static_mask=static_mask, blocked_occupied=blocked_occupied):
                continue
            changed = current_direction != _START_DIRECTION and current_direction != next_direction
            next_g = current_g + step + (turn if changed else 0.0)
            next_state = (next_cell, next_direction)
            old_g = g_score.get(next_state)
            next_turn_count = turns[state] + (1 if changed else 0)
            # Equal-cost states keep the first path generated by the fixed
            # neighbour order; replacing only on strict improvement is part of
            # the deterministic tie-break contract.
            if old_g is not None and next_g >= old_g:
                continue
            g_score[next_state] = next_g
            turns[next_state] = next_turn_count
            parent[next_state] = state
            serial += 1
            heappush(
                heap,
                (next_g + heuristic(next_cell), next_g, next_turn_count,
                 next_cell[0], next_cell[1], next_direction, serial, next_state),
            )

    if goal_state is None:
        return _result(
            "NO_ROUTE", start_cell, goal_cell,
            max_expanded_cells=max_expanded_cells,
            expanded_cells=expanded,
            diagnostics=("NO_FEASIBLE_4_NEIGHBOR_PATH",),
        )

    states: list[tuple[Cell, int]] = []
    cursor: tuple[Cell, int] | None = goal_state
    while cursor is not None:
        states.append(cursor)
        cursor = parent[cursor]
    states.reverse()
    path = tuple(state[0] for state in states)
    directions = tuple(DIRECTIONS[state[1]] for state in states[1:])
    return _result(
        "ROUTE_FOUND", start_cell, goal_cell,
        max_expanded_cells=max_expanded_cells,
        path=path,
        directions=directions,
        cost=g_score[goal_state],
        expanded_cells=expanded,
        turn_count=turns[goal_state],
    )


def route_and_reserve_raster(
    world: RasterRoutingDomain,
    start: Sequence[int],
    goal: Sequence[int],
    *,
    owner: str,
    role: str,
    reservation_id: str | None = None,
    clearance_mm: float = 0.0,
    allow_same_owner: bool = False,
    same_owner_join_mask: Any | None = None,
    step_cost: float = 1.0,
    turn_penalty: float = 0.0,
    max_expanded_cells: int = 10_000,
    allow_boundary_clipping: bool = False,
) -> RasterRouteResult:
    """Search first, then atomically reserve the complete route.

    A failed search never mutates the world.  A reservation conflict restores
    the exact pre-call snapshot and returns ``RESERVATION_FAILED``.  Existing
    same-owner material and an exact terminal/join mask may be traversed when
    requested; only new material cells are allocated.  If every route cell
    already belongs to that owner, no duplicate reservation is created and the
    result is ``ALREADY_RESERVED_BY_OWNER``.
    """

    result = route_raster_a_star(
        world, start, goal, owner=owner, allow_same_owner=allow_same_owner,
        same_owner_join_mask=same_owner_join_mask,
        clearance_mm=clearance_mm,
        step_cost=step_cost, turn_penalty=turn_penalty,
        max_expanded_cells=max_expanded_cells,
    )
    if not result.found:
        return result
    if not isinstance(owner, str) or not owner.strip() or not isinstance(role, str) or not role.strip():
        raise RasterDomainError("owner and role must be non-empty strings")

    snapshot = world.snapshot()
    try:
        mask = world.mask_from_cells(result.path)
        if allow_same_owner:
            own_material = world.material_mask_for_owner(owner)
            new_material = mask & ~own_material
        else:
            new_material = mask
        if not new_material.any():
            own_protected = world.protected_mask_for_owner(owner)
            own_protected_only = own_protected & ~own_material
            required_protected = world.dilate_mask(
                mask, clearance_mm=clearance_mm
            )
            existing_clearance_is_sufficient = (
                not (required_protected & ~own_protected).any()
                and world.can_reserve(
                    mask,
                    clearance_mm=clearance_mm,
                    allow_boundary_clipping=allow_boundary_clipping,
                    owner=owner,
                    allow_same_owner_overlap=True,
                    same_owner_join_mask=own_protected_only,
                )
            )
            if not existing_clearance_is_sufficient:
                return replace(
                    result,
                    status="RESERVATION_FAILED",
                    reservation_id=None,
                    diagnostics=tuple(
                        dict.fromkeys(
                            [
                                *result.diagnostics,
                                "INSUFFICIENT_EXISTING_OWNER_CLEARANCE",
                            ]
                        )
                    ),
                )
            return replace(result, status="ALREADY_RESERVED_BY_OWNER", diagnostics=tuple(dict.fromkeys([*result.diagnostics, "ROUTE_CELLS_ALREADY_RESERVED_BY_OWNER"])))
        record: RasterReservation = world.reserve(
            new_material,
            owner=owner,
            role=role,
            clearance_mm=clearance_mm,
            reservation_id=reservation_id,
            allow_boundary_clipping=allow_boundary_clipping,
            allow_same_owner_overlap=allow_same_owner,
            same_owner_join_mask=same_owner_join_mask,
        )
        return replace(result, status="ROUTE_RESERVED", reservation_id=record.reservation_id)
    except Exception as exc:
        world.rollback(snapshot)
        diagnostics = list(result.diagnostics)
        diagnostics.append("RESERVATION_ROLLED_BACK")
        if isinstance(exc, ReservationConflictError):
            diagnostics.append("RESERVATION_CONFLICT")
            if exc.static_cell_count:
                diagnostics.append("RESERVATION_STATIC_CONFLICT")
            if exc.occupied_cell_count:
                diagnostics.append("RESERVATION_OCCUPIED_CONFLICT")
            if exc.boundary_overflow:
                diagnostics.append("RESERVATION_BOUNDARY_OVERFLOW")
        else:
            diagnostics.append("RESERVATION_FAILED")
        return replace(result, status="RESERVATION_FAILED", reservation_id=None, diagnostics=tuple(dict.fromkeys(diagnostics)))


# Short aliases keep the module convenient for callers without creating a
# second implementation or changing the physical-validation boundary.
route_raster = route_raster_a_star
route_raster_and_reserve = route_and_reserve_raster
bounded_directional_a_star = route_raster_a_star


__all__ = [
    "Cell",
    "DIRECTIONS",
    "RasterRouteResult",
    "bounded_directional_a_star",
    "route_and_reserve_raster",
    "route_raster",
    "route_raster_a_star",
    "route_raster_and_reserve",
]

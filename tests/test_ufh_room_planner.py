"""Doorway-aware room planner contract and geometry tests.

These tests pin the restored ``calculate_doorway_room_layout`` contract: a
successful room route must carry both terminals through the selected doorway,
remain R80 materializable on the complete centreline, never cross a solid
wall, and keep building-transit and manifold connection states UNVERIFIED.
"""
from __future__ import annotations

import pytest
from shapely.geometry import LineString, Polygon

from agent.floor_heating_engine import calculate_floor_heating
from agent.floor_heating_models import FloorHeatingRequest


def point(x: int, y: int) -> dict[str, int]:
    return {"x_mm": x, "y_mm": y}


def polygon(points: list[tuple[int, int]]) -> dict:
    return {"points": [point(x, y) for x, y in points]}


def make_request(
    doorway_start: tuple[int, int],
    doorway_end: tuple[int, int],
    *,
    width: int = 7000,
    height: int = 3200,
    **overrides,
) -> FloorHeatingRequest:
    payload = {
        "project_id": "hf-doorway",
        "room_id": "room",
        "boundary": polygon([
            (0, 0), (width, 0), (width, height), (0, height), (0, 0),
        ]),
        "exclusion_zones": [],
        "collector_point": point(width // 2, height // 2),
        "wall_offset_mm": 100,
        "spacing_mm": 200,
        "minimum_circuit_length_mm": 1000,
        "maximum_circuit_length_mm": 80_000,
        "requested_circuit_count": 1,
        "field_spacing_mm": 200,
        "perimeter_spacing_mm": 100,
        "perimeter_band_depth_mm": 1000,
        "turn_radius_mm": 80,
        "exterior_wall_segments": [{
            "reference": "exterior-south",
            "start": point(0, 0),
            "end": point(width, 0),
        }],
        "perimeter_priority_mode": True,
        "selected_doorway": {
            "doorway_id": "door-1",
            "start": point(*doorway_start),
            "end": point(*doorway_end),
            "authority_status": "UNVERIFIED",
        },
    }
    payload.update(overrides)
    return FloorHeatingRequest.model_validate(payload)


def test_module_import_contract_restored() -> None:
    from agent.ufh_room_planner import calculate_doorway_room_layout

    assert callable(calculate_doorway_room_layout)
    # The canonical engine must now dispatch to the planner without crashing.
    result = calculate_floor_heating(
        make_request((6500, 0), (7000, 0))
    )
    assert result.status in {"ok", "impossible"}


def test_south_edge_doorway_builds_continuous_r80_route() -> None:
    result = calculate_floor_heating(make_request((6500, 0), (7000, 0)))
    assert result.status == "ok"
    assert result.room_layout is not None
    assert result.room_layout["ROOM_LAYOUT_VALID"] is True
    assert result.room_layout["DOORWAY_CONNECTION_VALID"] is True

    route = result.circuit_routes[0]
    physical = route.physical_geometry or {}
    assert physical["valid"] is True
    assert physical["BEND_GEOMETRY_VALID"] is True
    assert route.validation.valid is True
    assert route.validation.self_intersection is False


def test_both_terminals_cross_the_doorway_and_nowhere_else() -> None:
    result = calculate_floor_heating(make_request((6500, 0), (7000, 0)))
    points = [(item.x_mm, item.y_mm) for item in result.circuit_routes[0].polyline]

    # Supply and return terminals sit on the south wall inside the doorway.
    assert points[0][1] == 0 and 6500 <= points[0][0] <= 7000
    assert points[-1][1] == 0 and 6500 <= points[-1][0] <= 7000

    # The interior of the route never leaves the room (y >= 0, within x bounds).
    room = Polygon([(0, 0), (7000, 0), (7000, 3200), (0, 3200), (0, 0)])
    line = LineString([(float(x), float(y)) for x, y in points])
    assert room.buffer(1.0).covers(line)


def test_insufficient_doorway_width_is_blocked() -> None:
    result = calculate_floor_heating(make_request((3500, 0), (3600, 0)))
    assert result.status == "impossible"
    assert result.diagnostics[0].code == "doorway_capacity_insufficient"


def test_mid_wall_doorway_is_blocked_not_faked() -> None:
    # The bounded search only emits a route when both spiral terminals can sit
    # inside the doorway; a mid-wall opening has no aligned candidate yet.
    result = calculate_floor_heating(make_request((3500, 0), (4300, 0)))
    assert result.status == "impossible"
    assert result.diagnostics[0].code == "no_doorway_aligned_spiral"


def test_multi_circuit_split_is_deferred() -> None:
    result = calculate_floor_heating(
        make_request((6500, 0), (7000, 0), requested_circuit_count=2)
    )
    assert result.status == "impossible"
    assert result.diagnostics[0].code == "multi_circuit_split_not_yet_implemented"


def test_transit_and_manifold_remain_unverified() -> None:
    result = calculate_floor_heating(make_request((6500, 0), (7000, 0)))
    assert result.room_layout["BUILDING_TRANSIT_VALID"] == "UNVERIFIED"
    assert result.room_layout["MANIFOLD_CONNECTED"] == "UNVERIFIED"


def test_overlength_is_flagged_not_hidden() -> None:
    result = calculate_floor_heating(make_request((6500, 0), (7000, 0)))
    assert result.circuit_routes[0].length_mm > 80_000
    assert result.maximum_length_compliant is False
    assert result.room_layout["overlength"] is True
    assert "OVERLENGTH" in result.warnings


def test_no_selected_doorway_uses_legacy_engine() -> None:
    request = make_request((6500, 0), (7000, 0)).model_copy(
        update={"selected_doorway": None}
    )
    result = calculate_floor_heating(request)
    # The legacy counterflow spiral path is used, not the doorway planner.
    assert result.status == "ok"
    assert result.room_layout is None

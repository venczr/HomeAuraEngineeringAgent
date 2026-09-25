"""Real Test_01 smoke test for the raster world and directional A* boundary."""
from __future__ import annotations

import json

import numpy as np
import pytest
from shapely.geometry import Point, Polygon, box

from agent.ufh_raster_router import route_and_reserve_raster
from agent.ufh_test01_world import (
    DEFAULT_TEST01_SOURCE,
    TEST01_FLOORS,
    load_test01_worlds,
)


@pytest.fixture(scope="module")
def real_test01():
    rooms = json.loads(DEFAULT_TEST01_SOURCE.read_text(encoding="utf-8"))["rooms"]
    return load_test01_worlds(), rooms


def _rectangular_usable_room(rooms, floor_id):
    candidates = []
    for room in rooms:
        if room.get("floor") != floor_id or room.get("geometry_status") != "USABLE":
            continue
        polygon = Polygon(room["global_boundary_mm"])
        if polygon.symmetric_difference(box(*polygon.bounds)).area <= 1.0:
            candidates.append((polygon.area, str(room["id"]), room, polygon))
    assert candidates, f"{floor_id} has no rectangular USABLE source room"
    return min(candidates)[2:]


def _crossing_pairs_inside_room(floor_world, polygon):
    """Choose two crossing free-cell pairs well inside one source room."""

    domain = floor_world.domain
    min_x, min_y, max_x, max_y = polygon.bounds
    column_start = max(0, int((min_x - domain.origin_mm[0]) // domain.cell_size_mm) - 1)
    column_end = min(
        domain.shape[1],
        int(np.ceil((max_x - domain.origin_mm[0]) / domain.cell_size_mm)) + 1,
    )
    row_start = max(0, int((min_y - domain.origin_mm[1]) // domain.cell_size_mm) - 1)
    row_end = min(
        domain.shape[0],
        int(np.ceil((max_y - domain.origin_mm[1]) / domain.cell_size_mm)) + 1,
    )
    free = ~domain.static_mask[row_start:row_end, column_start:column_end]
    free_rows, free_columns = np.where(free)
    assert len(free_rows) > 0
    first_row = row_start + int(free_rows.min())
    last_row = row_start + int(free_rows.max())
    first_column = column_start + int(free_columns.min())
    last_column = column_start + int(free_columns.max())
    free_box = free[
        int(free_rows.min()) : int(free_rows.max()) + 1,
        int(free_columns.min()) : int(free_columns.max()) + 1,
    ]
    assert free_box.all(), "selected rectangular room must contain one continuous free raster"

    row_span = last_row - first_row
    column_span = last_column - first_column
    assert row_span >= 40 and column_span >= 40
    middle_row = (first_row + last_row) // 2
    middle_column = (first_column + last_column) // 2
    horizontal = (
        (middle_row, first_column + column_span // 4),
        (middle_row, last_column - column_span // 4),
    )
    vertical = (
        (first_row + row_span // 4, middle_column),
        (last_row - row_span // 4, middle_column),
    )
    for cell in (*horizontal, *vertical):
        assert not domain.static_mask[cell]
        assert polygon.contains(Point(domain.cell_to_mm(cell)))
    return horizontal, vertical


@pytest.mark.parametrize("floor_id", TEST01_FLOORS)
def test_real_floor_world_routes_reserve_and_respect_existing_occupancy(
    real_test01, floor_id
):
    worlds, rooms = real_test01
    floor_world = worlds[floor_id]
    room, polygon = _rectangular_usable_room(rooms, floor_id)
    horizontal, vertical = _crossing_pairs_inside_room(floor_world, polygon)
    domain = floor_world.domain

    first = route_and_reserve_raster(
        domain,
        *horizontal,
        owner=f"smoke:{floor_id}:horizontal",
        role="INTEGRATION_SMOKE",
        turn_penalty=2.0,
        max_expanded_cells=200_000,
    )
    assert first.status == "ROUTE_RESERVED"
    assert first.path
    assert first.reservation_id in domain.reservations
    assert first.physical_validation == "NOT_EVALUATED"

    # This pair would cross the first route in the empty room.  The second
    # search must route around that foreign reservation or fail closed without
    # exposing/reserving a partial path.
    reservation_count = len(domain.reservations)
    second = route_and_reserve_raster(
        domain,
        *vertical,
        owner=f"smoke:{floor_id}:vertical",
        role="INTEGRATION_SMOKE",
        turn_penalty=2.0,
        max_expanded_cells=200_000,
    )
    assert second.status in {"ROUTE_RESERVED", "NO_ROUTE", "SEARCH_LIMIT_REACHED"}
    if second.status == "ROUTE_RESERVED":
        assert second.path
        assert set(first.path).isdisjoint(second.path)
        assert len(domain.reservations) == reservation_count + 1
    else:
        assert second.path == ()
        assert len(domain.reservations) == reservation_count
        assert any(
            code in second.diagnostics
            for code in ("NO_FEASIBLE_4_NEIGHBOR_PATH", "MAX_EXPANDED_CELLS_REACHED")
        )

    assert room["geometry_status"] == "USABLE"
    assert "RASTER_ROUTE_REQUIRES_VECTOR_VALIDATION" in second.diagnostics
    assert second.physical_validation == "NOT_EVALUATED"

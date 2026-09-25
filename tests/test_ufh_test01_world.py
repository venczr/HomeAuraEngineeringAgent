import json
from pathlib import Path

import pytest
from shapely.geometry import Polygon, box

from agent.ufh_test01_world import (
    DEFAULT_TEST01_SOURCE,
    TEST01_FLOORS,
    Test01WorldSourceError,
    _complete_cell_mask,
    load_test01_worlds,
)


@pytest.fixture(scope="module")
def source_rooms():
    return json.loads(DEFAULT_TEST01_SOURCE.read_text(encoding="utf-8"))["rooms"]


@pytest.fixture(scope="module")
def worlds():
    return load_test01_worlds()


def _representative_cell(floor_world, room):
    point = Polygon(room["global_boundary_mm"]).representative_point()
    return floor_world.domain.mm_to_cell((point.x, point.y))


def test_complete_cell_mask_is_exact_for_aligned_rectangle_and_l_shape():
    rectangle = box(0, 0, 50, 30)
    rectangle_mask = _complete_cell_mask(
        rectangle, origin_mm=(0, 0), shape=(5, 6), cell_size_mm=10
    )
    assert rectangle_mask.sum() == 15
    assert rectangle_mask[:3, :5].all()
    assert not rectangle_mask[3:, :].any()
    assert not rectangle_mask[:, 5].any()

    l_shape = Polygon([(0, 0), (50, 0), (50, 20), (20, 20), (20, 50), (0, 50)])
    l_mask = _complete_cell_mask(
        l_shape, origin_mm=(0, 0), shape=(5, 5), cell_size_mm=10
    )
    assert l_mask.sum() == 16
    for row, column in zip(*l_mask.nonzero(), strict=True):
        footprint = box(column * 10, row * 10, (column + 1) * 10, (row + 1) * 10)
        assert l_shape.covers(footprint)


def test_loads_two_independent_source_aligned_10mm_domains(worlds):
    assert tuple(worlds) == TEST01_FLOORS
    assert worlds.metadata["generated_geometry"] is False
    assert worlds["FLOOR_1_PLAN"].domain is not worlds["ATTIC_PLAN"].domain

    for floor in worlds.values():
        assert floor.domain.cell_size_mm == 10.0
        assert floor.room_count == 8
        assert 1_800_000 < floor.metadata["cell_count"] < 2_100_000
        assert floor.metadata["cell_count"] == (
            floor.blocked_cell_count + floor.routable_cell_count
        )
        assert floor.metadata["coordinate_frame"] == "global_boundary_mm"
        assert floor.domain.origin_mm[0] % 10 == 0
        assert floor.domain.origin_mm[1] % 10 == 0


def test_usable_room_interiors_open_but_unresolved_rooms_remain_blocked(
    worlds, source_rooms
):
    for room in source_rooms:
        floor = worlds[room["floor"]]
        row, column = _representative_cell(floor, room)
        if room["geometry_status"] == "USABLE":
            assert not floor.domain.static_mask[row, column], room["id"]
        else:
            assert room["geometry_status"] == "GEOMETRY_UNRESOLVED"
            assert floor.domain.static_mask[row, column], room["id"]
            status = next(item for item in floor.rooms if item.room_id == room["id"])
            assert status.routable_cell_count == 0
            assert status.raster_access == "BLOCKED_GEOMETRY_UNRESOLVED"


def test_outside_space_and_room_boundaries_fail_closed(worlds, source_rooms):
    for floor_id, floor in worlds.items():
        assert floor.domain.static_mask[0, 0]
        room = next(
            room
            for room in source_rooms
            if room["floor"] == floor_id and room["geometry_status"] == "USABLE"
        )
        # A vertex is a source wall boundary and must never become routable by
        # raster rounding.
        vertex = room["global_boundary_mm"][0]
        row, column = floor.domain.mm_to_cell(vertex)
        assert floor.domain.static_mask[row, column]


def test_no_candidate_opening_is_applied_and_provenance_is_preserved(worlds):
    for floor in worlds.values():
        assert floor.metadata["status"] == "FAIL_CLOSED_SOURCE_GEOMETRY_RASTERIZED"
        assert floor.metadata["opening_policy"] == (
            "ALL_OPENINGS_BLOCKED_UNLESS_SOURCE_AUTHORIZED"
        )
        assert floor.metadata["authorized_opening_count"] == 0
        assert floor.metadata["candidate_openings_applied"] is False
        assert floor.metadata["construction_release"] is False
        assert len(floor.metadata["source_sha256"]) == 64
        assert Path(floor.metadata["source_path"]) == DEFAULT_TEST01_SOURCE.resolve()


def test_adapter_rejects_incomplete_floor_instead_of_opening_partial_world(tmp_path):
    payload = json.loads(DEFAULT_TEST01_SOURCE.read_text(encoding="utf-8"))
    payload["rooms"] = payload["rooms"][:-1]
    broken = tmp_path / "source.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(Test01WorldSourceError, match="exactly 8 source rooms"):
        load_test01_worlds(broken)

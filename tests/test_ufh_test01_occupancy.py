import copy
import json
from pathlib import Path

import numpy as np
import pytest

from agent.ufh_test01_occupancy import (
    Test01OccupancySourceError,
    import_test01_coverage_bodies,
    supercover_polyline_mask,
)
from agent.ufh_test01_world import DEFAULT_TEST01_SOURCE, load_test01_worlds
from agent.ufh_world_state import RasterRoutingDomain


def _write_source(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "08_PROJECT_SOURCE_DATA.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_imports_only_valid_source_routes_into_their_independent_floor_worlds():
    result = import_test01_coverage_bodies()

    assert result.metadata["imported_body_count"] == 22
    assert result.metadata["skipped_body_count"] == 0
    assert result["FLOOR_1_PLAN"].imported_body_count == 9
    assert result["ATTIC_PLAN"].imported_body_count == 13
    assert result.worlds["FLOOR_1_PLAN"].domain is not result.worlds["ATTIC_PLAN"].domain

    for floor in result.values():
        domain = result.worlds[floor.floor_id].domain
        assert len(domain.reservations) == floor.imported_body_count
        assert set(domain.role_layer[domain.occupied_mask]) == {"BODY"}
        assert floor.metadata["collision_count"] == 0
        assert floor.metadata["openings_imported"] is False
        assert floor.metadata["building_transit_valid"] is False
        assert floor.metadata["full_circuit_valid"] is False
        assert floor.metadata["construction_release"] is False
        for body in floor.bodies:
            assert body.imported
            assert body.material_cell_count > 0
            assert body.source_points
            assert len(body.source_points) == len(body.global_points_mm)
            assert body.rounded_global_points_mm
            assert body.metadata["engineering_role"] == "COVERAGE_BODY"
            reservation = domain.reservations[body.reservation_id]
            assert reservation.owner == body.owner
            assert reservation.role == "BODY"


def test_transform_is_proven_from_every_paired_floor_boundary_vertex():
    result = import_test01_coverage_bodies()
    first = result["FLOOR_1_PLAN"].transform
    attic = result["ATTIC_PLAN"].transform

    assert first is not None and attic is not None
    assert first.status == "PROVEN_FROM_ALL_PAIRED_BOUNDARY_VERTICES"
    assert first.evidence_point_count == 187
    assert attic.evidence_point_count == 79
    assert first.scale_mm_per_drawing_unit == 35.276963114841124
    assert attic.scale_mm_per_drawing_unit == 35.19226430063542
    assert first.maximum_residual_mm < 1e-6
    assert attic.maximum_residual_mm < 1e-6

    body = result["FLOOR_1_PLAN"].bodies[0]
    expected = first.apply(body.source_points[0])
    assert body.global_points_mm[0] == expected
    assert body.metadata["coordinate_frame_evidence"]["rounded_frame_mapping"] == (
        "LOCAL_ROOM_MM_PLUS_GLOBAL_BOUNDARY_MINIMUM"
    )


def test_reservation_conservatively_unions_sharp_and_actual_rounded_body():
    result = import_test01_coverage_bodies()

    for floor in result.values():
        domain = result.worlds[floor.floor_id].domain
        for body in floor.bodies:
            reservation = domain.reservations[body.reservation_id]
            sharp = supercover_polyline_mask(domain, body.global_points_mm)
            rounded = supercover_polyline_mask(domain, body.rounded_global_points_mm)
            assert np.all(reservation.material_mask[sharp])
            assert np.all(reservation.material_mask[rounded])


def test_unproven_floor_transform_imports_nothing_from_that_floor(tmp_path):
    payload = json.loads(DEFAULT_TEST01_SOURCE.read_text(encoding="utf-8"))
    first_floor_room = next(room for room in payload["rooms"] if room["floor"] == "FLOOR_1_PLAN")
    first_floor_room["global_boundary_mm"][0][0] += 2
    source = _write_source(tmp_path, payload)

    result = import_test01_coverage_bodies(source)

    floor = result["FLOOR_1_PLAN"]
    assert floor.transform is None
    assert floor.imported_body_count == 0
    assert floor.skipped_body_count == 9
    assert not result.worlds["FLOOR_1_PLAN"].domain.occupied_mask.any()
    assert {body.status for body in floor.bodies} == {
        "SKIPPED_COORDINATE_TRANSFORM_UNPROVEN"
    }
    # A transform failure is floor-bounded and cannot corrupt the independent attic.
    assert result["ATTIC_PLAN"].imported_body_count == 13


def test_failed_route_validation_is_retained_as_skipped_without_reservation(tmp_path):
    payload = json.loads(DEFAULT_TEST01_SOURCE.read_text(encoding="utf-8"))
    room = next(
        room
        for room in payload["rooms"]
        if room["floor"] == "FLOOR_1_PLAN" and room["routes"]
    )
    rejected_route_id = room["route_ids"][0]
    room["route_validation"][0]["BEND_VALID"] = False
    source = _write_source(tmp_path, payload)

    result = import_test01_coverage_bodies(source)
    rejected = next(
        body
        for body in result["FLOOR_1_PLAN"].bodies
        if body.room_id == room["id"] and body.route_id == rejected_route_id
    )

    assert rejected.status == "SKIPPED_SOURCE_ROUTE_NOT_VALID"
    assert rejected.reservation_id is None
    assert rejected.metadata["source_route_validation"]["BEND_VALID"] is False
    assert result["FLOOR_1_PLAN"].imported_body_count == 8
    assert len(result.worlds["FLOOR_1_PLAN"].domain.reservations) == 8


@pytest.mark.parametrize(
    "field",
    ["length_mm", "INTERNAL_PIPE_LENGTH", "rounded_length_mm", "radius_mm", "bend_count"],
)
def test_inconsistent_rounded_length_radius_or_bend_count_fails_closed(
    tmp_path, field
):
    payload = json.loads(DEFAULT_TEST01_SOURCE.read_text(encoding="utf-8"))
    room = next(room for room in payload["rooms"] if room["routes"])
    route_id = room["route_ids"][0]
    validation = room["route_validation"][0]
    if field in {"length_mm", "INTERNAL_PIPE_LENGTH"}:
        validation[field] += 2
    else:
        validation["rounded_geometry"][field] += 2
    source = _write_source(tmp_path, payload)

    result = import_test01_coverage_bodies(source)
    body = next(
        item
        for item in result[room["floor"]].bodies
        if item.room_id == room["id"] and item.route_id == route_id
    )
    assert body.status == "SKIPPED_INVALID_ROUTE_GEOMETRY"
    assert body.reservation_id is None


def test_colliding_source_route_fails_closed_and_does_not_replace_first_owner(tmp_path):
    payload = json.loads(DEFAULT_TEST01_SOURCE.read_text(encoding="utf-8"))
    room = next(
        room
        for room in payload["rooms"]
        if room["floor"] == "FLOOR_1_PLAN" and len(room["routes"]) >= 2
    )
    room["routes"][1] = room["routes"][0]
    duplicate_validation = copy.deepcopy(room["route_validation"][0])
    duplicate_validation["route_id"] = room["route_ids"][1]
    room["route_validation"][1] = duplicate_validation
    source = _write_source(tmp_path, payload)

    result = import_test01_coverage_bodies(source)
    room_bodies = [body for body in result["FLOOR_1_PLAN"].bodies if body.room_id == room["id"]]

    assert room_bodies[0].imported
    assert room_bodies[1].status == "SKIPPED_RESERVATION_CONFLICT"
    assert "occupied_cells=" in room_bodies[1].reason
    assert room_bodies[1].reservation_id is None
    assert result["FLOOR_1_PLAN"].metadata["collision_count"] == 1
    domain = result.worlds["FLOOR_1_PLAN"].domain
    first_mask = domain.reservations[room_bodies[0].reservation_id].material_mask
    assert set(domain.owner_layer[first_mask]) == {room_bodies[0].owner}


def test_sharp_route_with_stale_rounded_evidence_is_invalid_before_reservation(
    tmp_path,
):
    payload = json.loads(DEFAULT_TEST01_SOURCE.read_text(encoding="utf-8"))
    room = next(
        room
        for room in payload["rooms"]
        if room["floor"] == "FLOOR_1_PLAN" and len(room["routes"]) >= 2
    )
    room["routes"][1] = room["routes"][0]
    source = _write_source(tmp_path, payload)

    result = import_test01_coverage_bodies(source)
    room_bodies = [
        body for body in result["FLOOR_1_PLAN"].bodies if body.room_id == room["id"]
    ]

    assert room_bodies[0].imported
    assert room_bodies[1].status == "SKIPPED_INVALID_ROUTE_GEOMETRY"
    assert room_bodies[1].reservation_id is None
    assert result["FLOOR_1_PLAN"].metadata["collision_count"] == 0


def test_supercover_includes_both_sides_of_grid_lines_and_corner_contacts():
    domain = RasterRoutingDomain(
        origin_mm=(0.0, 0.0),
        width_mm=40.0,
        height_mm=40.0,
        cell_size_mm=10.0,
    )
    vertical = supercover_polyline_mask(domain, ((20.0, 5.0), (20.0, 35.0)))
    diagonal = supercover_polyline_mask(domain, ((5.0, 5.0), (35.0, 35.0)))

    assert np.all(vertical[:, 1:3])
    # Closed-cell supercover keeps cells meeting only at a crossed grid corner.
    assert diagonal[0, 0]
    assert diagonal[0, 1]
    assert diagonal[1, 0]
    assert diagonal[1, 1]


def test_unresolved_rooms_and_transit_are_never_materialized():
    payload = json.loads(DEFAULT_TEST01_SOURCE.read_text(encoding="utf-8"))
    unresolved_ids = {
        room["id"] for room in payload["rooms"] if room["geometry_status"] != "USABLE"
    }
    result = import_test01_coverage_bodies()

    assert unresolved_ids
    assert not any(
        body.room_id in unresolved_ids for floor in result.values() for body in floor.bodies
    )
    assert result.metadata["openings_imported"] is False
    assert result.metadata["building_transit_valid"] is False
    assert result.metadata["full_circuit_valid"] is False
    assert result.metadata["construction_release"] is False


def test_provided_worlds_require_exact_source_digest_and_cell_size(tmp_path):
    payload = json.loads(DEFAULT_TEST01_SOURCE.read_text(encoding="utf-8"))
    source = _write_source(tmp_path, payload)
    worlds = load_test01_worlds(source)
    payload["parameters"]["maximum_circuit_length_mm"] += 1
    source.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(Test01OccupancySourceError, match="different source content"):
        import_test01_coverage_bodies(source, worlds=worlds)

    canonical_worlds = load_test01_worlds()
    with pytest.raises(Test01OccupancySourceError, match="metadata is incompatible"):
        import_test01_coverage_bodies(
            worlds=canonical_worlds,
            cell_size_mm=20.0,
        )


def test_provided_worlds_require_the_exact_source_derived_static_mask():
    worlds = load_test01_worlds()
    domain = worlds["FLOOR_1_PLAN"].domain
    changed = domain.static_mask
    blocked_cell = tuple(np.argwhere(changed)[0])
    open_cell = tuple(np.argwhere(~changed)[0])
    changed[blocked_cell] = False
    changed[open_cell] = True
    assert int(changed.sum()) == worlds["FLOOR_1_PLAN"].blocked_cell_count
    domain.set_static_mask(changed)

    with pytest.raises(Test01OccupancySourceError, match="raster domain is incompatible"):
        import_test01_coverage_bodies(worlds=worlds)


def test_proven_transform_with_zero_accepted_routes_has_explicit_status(tmp_path):
    payload = json.loads(DEFAULT_TEST01_SOURCE.read_text(encoding="utf-8"))
    for room in payload["rooms"]:
        if room["floor"] == "FLOOR_1_PLAN":
            room["status"] = "UNRESOLVED_STRATEGY"
    source = _write_source(tmp_path, payload)

    result = import_test01_coverage_bodies(source)

    floor = result["FLOOR_1_PLAN"]
    assert floor.transform is not None
    assert floor.imported_body_count == 0
    assert floor.metadata["status"] == "NO_SOURCE_BODY_IMPORTED"

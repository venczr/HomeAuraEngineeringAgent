"""Global preliminary layout planner tests.

The room records reproduce the actual Test_01 circuit schedule plus the full
16-room source registry, so the planner is exercised against project data, not
synthetic rectangles.  The assertions pin the corrected split policy (per
circuit transit overhead), the two-pipe-per-circuit rule, the honest
lower-bound/blocked behaviour, and the per-passage pipe load that must not be
confused with the manifold egress total.
"""
from __future__ import annotations

import pytest

from agent.ufh_global_planner import (
    CorridorPassage,
    RoomRecord,
    build_global_preliminary_plan,
    estimate_circuit_count,
    passage_pipe_load,
    required_pipe_width_mm,
    room_pipe_demand,
    total_circuit_count,
    total_minimum_circuit_count,
)


def _room(
    zone_id: str,
    floor: int,
    label: str,
    coverage: float | None,
    transit: float | None,
    *,
    vertical: float = 0.0,
    authority: str = "SOURCE_ROOM_GEOMETRY",
    geometry_status: str = "USABLE",
) -> RoomRecord:
    return RoomRecord(
        zone_id,
        floor,
        "ROOM",
        label,
        authority,
        coverage_length_m=coverage,
        transit_length_m=transit,
        vertical_length_m=vertical,
        geometry_status=geometry_status,
    )


def _test01_rooms() -> list[RoomRecord]:
    """The full 16-room Test_01 registry from the source data + real schedule."""
    return [
        _room("ATTIC_PLAN:9776f1f2c9664133:ROOM", 2, "10 / 26.0; Детская", 123.241, 16.047, vertical=6.0),
        _room("ATTIC_PLAN:c4f6e730556e69f2:ROOM", 2, "11 / 5.1; WC", 22.291, 19.865, vertical=6.0),
        _room("ATTIC_PLAN:3d760ac099594432:ROOM", 2, "12 / 20.6; Детская", 96.406, 27.544, vertical=6.0),
        _room("ATTIC_PLAN:9386d71e1d28f2ee:ROOM", 2, "13 / 5.3; WC", 23.551, 21.979, vertical=6.0),
        _room("ATTIC_PLAN:ea7ed4904468a1da:ROOM", 2, "14 / 28.7; Спальня", 137.581, 32.843, vertical=6.0),
        _room("ATTIC_PLAN:112c14729a5a9ee7:ROOM", 2, "15 / 13.0; Гардероб", 55.933, 24.397, vertical=6.0),
        _room("ATTIC_PLAN:49c65e3abf362d77:ROOM", 2, "16 / 12.9; Ванна + WC", 55.933, 41.385, vertical=6.0),
        _room(
            "ATTIC_PLAN:fd106b1227a87876:ROOM", 2, "9 / 39.9; Назначение не подписано",
            None, None, vertical=6.0, authority="GEOMETRY_UNRESOLVED", geometry_status="GEOMETRY_UNRESOLVED",
        ),
        _room("FLOOR_1_PLAN:d82596ad96a4009a:ROOM", 1, "1 / 12.9; Вх. гр.", 56.74, 40.268),
        _room(
            "FLOOR_1_PLAN:23e1c19b1e8cd7bd:ROOM", 1, "2 / 30.7; Назначение не подписано",
            70.587, 21.237, authority="UNVERIFIED_UNDER_STAIR_PREVIEW", geometry_status="GEOMETRY_UNRESOLVED",
        ),
        _room("FLOOR_1_PLAN:dbda1f3916917c37:ROOM", 1, "3 / 40.9; Кухня / зал", 194.938, 20.5),
        _room("FLOOR_1_PLAN:2c35c0ccf04544b4:ROOM", 1, "4 / 15.9; Котельная", 72.0, 10.61),
        _room("FLOOR_1_PLAN:e8abc7453895cbf7:ROOM", 1, "5 / 4.4; Подпись частично неразборчива", 18.0, 36.73),
        _room("FLOOR_1_PLAN:4767e90a4e019716:ROOM", 1, "6 / 16.9; Ванна + туалет", 77.056, 42.816),
        _room("FLOOR_1_PLAN:8c25b2af4cb28379:ROOM", 1, "7 / 15.6; Спальня", 70.178, 35.378),
        _room("FLOOR_1_PLAN:c5b40c4d2c432677:ROOM", 1, "8 / 17.3; Спальня", 80.232, 28.434),
    ]


def test_estimate_exact_count_when_transit_known() -> None:
    room = _room("FLOOR_1_PLAN:dbda1f3916917c37:ROOM", 1, "3 / 40.9; Кухня / зал", 194.938, 20.5)
    estimate = estimate_circuit_count(room)
    assert estimate.count == 3
    assert estimate.basis == "PRELIMINARY_EXACT"
    # Total installed pipe = coverage + 3 x per-circuit transit overhead.
    assert estimate.total_length_m == pytest.approx(194.938 + 20.5 * 3)
    assert estimate.per_circuit_overhead_m == pytest.approx(20.5)
    assert estimate.max_circuit_length_m == pytest.approx(194.938 / 3 + 20.5)


def test_estimate_lower_bound_when_transit_unknown() -> None:
    room = _room("R", 1, "room", 120.0, None)
    estimate = estimate_circuit_count(room)
    assert estimate.count is None
    assert estimate.minimum_count == 2
    assert estimate.basis == "LOWER_BOUND_UNVERIFIED_TRANSIT"


def test_estimate_unknown_coverage_is_blocked_not_zero() -> None:
    room = _room("R", 1, "room", None, None, geometry_status="GEOMETRY_UNRESOLVED")
    estimate = estimate_circuit_count(room)
    assert estimate.count is None
    assert estimate.minimum_count == 1
    assert estimate.basis == "BLOCKED_UNKNOWN_COVERAGE"


def test_estimate_blocked_when_transit_exceeds_limit() -> None:
    room = _room("R", 1, "room", 50.0, 95.0)
    estimate = estimate_circuit_count(room)
    assert estimate.count is None
    assert estimate.basis == "BLOCKED_TRANSIT_EXCEEDS_LIMIT"


def test_every_circuit_needs_two_pipe_ends() -> None:
    room = _room("R", 1, "room", 60.0, 10.0)
    estimate = estimate_circuit_count(room)
    assert estimate.count == 1
    assert room_pipe_demand(room, estimate) == 2

    split = _room("S", 1, "split", 194.938, 20.5)
    split_estimate = estimate_circuit_count(split)
    assert split_estimate.count == 3
    assert room_pipe_demand(split, split_estimate) == 6


def test_per_circuit_transit_changes_split_count() -> None:
    # Room 14 has a large transit (32.843) + vertical (6).  The old one-off
    # rule gave 2 circuits; reserving the overhead per circuit needs 3.
    room = _room("ATTIC_PLAN:ea7ed4904468a1da:ROOM", 2, "14 / 28.7; Спальня", 137.581, 32.843, vertical=6.0)
    estimate = estimate_circuit_count(room)
    assert estimate.count == 3
    assert estimate.max_circuit_length_m == pytest.approx(137.581 / 3 + 38.843)


def test_required_pipe_width_matches_doorway_reservation() -> None:
    # Two 16 mm pipes with 16 mm clearance and 50 mm edges need 148 mm.
    assert required_pipe_width_mm(2) == pytest.approx(148.0)
    # A 50 mm lane pitch (manifold port pitch) is honoured when requested.
    assert required_pipe_width_mm(3, lane_spacing_mm=50.0) == pytest.approx(216.0)


def test_global_plan_reproduces_test01_routed_totals() -> None:
    # The 15 routed rooms (room 9 excluded) total 27 circuits / 54 pipe ends.
    routed = [r for r in _test01_rooms() if r.coverage_length_m is not None]
    estimates = [estimate_circuit_count(room) for room in routed]
    assert total_circuit_count(estimates) == 27
    assert total_minimum_circuit_count(estimates) == 27
    kitchen = next(e for e in estimates if e.room_zone_id == "FLOOR_1_PLAN:dbda1f3916917c37:ROOM")
    assert kitchen.count == 3
    boiler = next(e for e in estimates if e.room_zone_id == "FLOOR_1_PLAN:2c35c0ccf04544b4:ROOM")
    assert boiler.count == 1

    plan = build_global_preliminary_plan(
        routed,
        [CorridorPassage("PREVIEW-CORRIDOR-01", carrier_room_ids=[room.zone_id for room in routed])],
    )
    assert plan["total_circuit_count"] == 27
    assert plan["manifold_demand"]["supply_ends"] == 27
    assert plan["manifold_demand"]["return_ends"] == 27
    assert plan["manifold_demand"]["total_pipe_ends"] == 54
    assert plan["manifold_demand"]["connection_authority"] == "UNVERIFIED"


def test_full_registry_includes_blocked_room_nine() -> None:
    rooms = _test01_rooms()
    assert len(rooms) == 16
    estimates = [estimate_circuit_count(room) for room in rooms]
    room9 = next(e for e in estimates if e.room_zone_id == "ATTIC_PLAN:fd106b1227a87876:ROOM")
    assert room9.count is None
    assert room9.minimum_count == 1
    assert room9.basis == "BLOCKED_UNKNOWN_COVERAGE"
    # Total exact count is unavailable while any room is blocked.
    assert total_circuit_count(estimates) is None
    # Lower bound: 27 routed + 1 for the unresolved room.
    assert total_minimum_circuit_count(estimates) == 28


def test_manifold_ends_are_not_per_segment_pipe_count() -> None:
    rooms = _test01_rooms()
    estimates_by_room = {e.room_zone_id: e for e in (estimate_circuit_count(r) for r in rooms)}

    manifold_egress = CorridorPassage("MANIFOLD-EGRESS", carrier_room_ids=[r.zone_id for r in rooms])
    supply, ret, _ = passage_pipe_load(manifold_egress, estimates_by_room)
    assert supply == 28
    assert ret == 28

    # The corridor<->boiler opening carries only the seven non-boiler floor-1
    # rooms (the boiler room's own circuit is local; attic circuits rise at R1).
    boiler_room = "FLOOR_1_PLAN:2c35c0ccf04544b4:ROOM"
    floor1_non_boiler = [r.zone_id for r in rooms if r.floor == 1 and r.zone_id != boiler_room]
    opening = CorridorPassage("OPENING-CORRIDOR-BOILER", carrier_room_ids=floor1_non_boiler)
    opening_supply, opening_ret, unresolved = passage_pipe_load(opening, estimates_by_room)
    assert opening_supply == 14
    assert opening_ret == 14
    assert unresolved == 0
    # The opening does not carry the whole building (54/56 ends).
    assert opening_supply < supply

    # The riser carries the eight mansard rooms: 12 routed circuits + 1 lower
    # bound for the unresolved room 9.
    mansard = [r.zone_id for r in rooms if r.floor == 2]
    riser = CorridorPassage("RISER-R1", carrier_room_ids=mansard)
    riser_supply, riser_ret, riser_unresolved = passage_pipe_load(riser, estimates_by_room)
    assert riser_supply == 13
    assert riser_ret == 13
    assert riser_unresolved == 1


def test_unknown_transit_rooms_are_not_silently_dropped() -> None:
    rooms = [
        _room("A", 1, "a", 60.0, 10.0),
        _room("B", 1, "b", 120.0, None),
    ]
    estimates = [estimate_circuit_count(room) for room in rooms]
    assert total_circuit_count(estimates) is None
    assert total_minimum_circuit_count(estimates) == 3

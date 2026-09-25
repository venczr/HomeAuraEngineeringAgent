from shapely.geometry import LineString, Polygon

from agent.ufh_building_routing import audit_joint_occupancy, build_door_transition, route_building_system, route_endpoint_to_opening, route_endpoint_to_collector


def test_missing_corridor_geometry_fails_closed_without_fabricated_transit():
    result = route_endpoint_to_opening((100, 100), ((0, 100), (0, 300)), [(0, 0), (1000, 0), (1000, 1000), (0, 1000)], None)
    assert result["status"] == "UNVERIFIED"
    assert "CORRIDOR_POLYGON_REQUIRED" in result["diagnostics"]


def test_building_preview_keeps_manifold_unverified_and_reports_full_preview_length():
    result = route_building_system(
        [{"circuit_id": "r1/c1", "room_id": "r1", "floor": "FLOOR_1_PLAN", "room_boundary_mm": [[0, 0], [1000, 0], [1000, 1000], [0, 1000]], "route_mm": [[100, 100], [900, 100]], "INTERNAL_PIPE_LENGTH": 800}],
        openings={"r1/c1": {"segment_mm": [[0, 100], [0, 300]]}},
        corridor_polygons={"FLOOR_1_PLAN": [(-100, -100), (300, -100), (300, 500), (-100, 500)]},
    )
    row = result["circuits"][0]
    assert row["MANIFOLD_CONNECTED"] == "UNVERIFIED"
    assert row["TOTAL_CIRCUIT_LENGTH"] is not None
    assert row["CORRIDOR_SUPPLY_LENGTH"] > 0
    assert row["CORRIDOR_RETURN_LENGTH"] > 0


def test_connected_transition_control_scenario_builds_supply_and_return():
    room = [[0, 0], [1000, 0], [1000, 1000], [0, 1000]]
    # L-shaped shared corridor, with a narrow upper leg to the collector room.
    corridor = [[1000, 0], [1500, 0], [1500, 2000], [1000, 2000]]
    collector_room = [[1500, 1500], [2500, 1500], [2500, 2000], [1500, 2000]]
    room_transition = build_door_transition("ROOM-CORRIDOR", [[1000, 400], [1000, 600]], [[1050, 400], [1050, 600]], passage_status="CONFIRMED", geometry_status="CONTROL_CONFIRMED")
    collector_transition = build_door_transition("CORRIDOR-COLLECTOR", [[1550, 1600], [1550, 1800]], [[1500, 1600], [1500, 1800]], passage_status="CONFIRMED", geometry_status="CONTROL_CONFIRMED")
    result = route_building_system(
        [{"circuit_id": "control/c1", "room_id": "control", "floor": "F1", "room_boundary_mm": room, "route_mm": [[200, 200], [800, 800]], "INTERNAL_PIPE_LENGTH": 1200}],
        openings={"control/c1": room_transition},
        corridor_polygons={"F1": corridor},
        collector_point=(2100, 1750),
        collector_polygon=collector_room,
        collector_transition=collector_transition,
        occupied_clearance_mm=16,
    )
    row = result["circuits"][0]
    assert row["status"] == "GEOMETRIC_PREVIEW_UNVERIFIED_AUTHORITY"
    assert row["TOTAL_CIRCUIT_LENGTH"] is not None
    assert row["CORRIDOR_SUPPLY_LENGTH"] > 0
    assert row["CORRIDOR_RETURN_LENGTH"] > 0
    for role in ("SUPPLY", "RETURN"):
        path = row["exits"][role]["path_mm"]
        assert path[0] in ([200.0, 200.0], [800.0, 800.0])
        assert path[-1] == [2100.0, 1750.0]
        assert LineString(path).is_simple


def test_joint_occupancy_detects_crossing_bodies_even_without_transit():
    circuits = [
        {"circuit_id": "a", "route_mm": [[0, 0], [1000, 0]]},
        {"circuit_id": "b", "route_mm": [[500, -500], [500, 500]]},
    ]
    audit = audit_joint_occupancy(circuits, [{"circuit_id": "a"}, {"circuit_id": "b"}])
    assert audit["status"] == "POTENTIAL_XY_CONFLICTS"
    assert audit["xy_check_complete"] is False
    assert any({item["a"]["part"], item["b"]["part"]} == {"BODY"} for item in audit["potential_conflicts"])
    assert len(audit["missing_parts"]) == 4


def test_building_does_not_claim_joint_check_when_a_transit_is_missing():
    result = route_building_system(
        [{"circuit_id": "a", "route_mm": [[0, 0], [100, 0]]}],
        corridor_polygons={"F1": [[-100, -100], [200, -100], [200, 100], [-100, 100]]},
    )
    assert result["corridor_validation"]["shared_route_collisions_checked"] is False
    assert result["joint_occupancy"]["status"] == "INCOMPLETE_LAYOUT"


def test_joint_xy_occupancy_keeps_different_floors_separate():
    circuits = [
        {"circuit_id": "a", "floor": "F1", "route_mm": [[0, 0], [1000, 0]]},
        {"circuit_id": "b", "floor": "F2", "route_mm": [[500, -500], [500, 500]]},
    ]
    audit = audit_joint_occupancy(circuits, [{"circuit_id": "a"}, {"circuit_id": "b"}])
    assert audit["status"] == "INCOMPLETE_LAYOUT"
    assert audit["potential_conflicts"] == []

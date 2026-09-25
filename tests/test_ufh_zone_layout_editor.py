import json
from pathlib import Path

from agent.ufh_zone_layout import propose_zoned_meanders
from agent.ufh_strategy_selector import select_layout


def _kitchen_boundary():
    project = json.loads(
        (Path(__file__).parents[1] / "homeaura-editor/public/plans/test01-project.json").read_text(encoding="utf-8")
    )
    room = next(room for room in project["rooms"] if room["label"].startswith("3 /"))
    return [tuple(point) for point in room["global_boundary_mm"]]


def test_kitchen_auto_zoning_materializes_three_independent_routes():
    result = propose_zoned_meanders(_kitchen_boundary(), target_route_length_mm=90_000, maximum_zones=3)
    candidate = result["recommended"]
    assert result["status"] == "CANDIDATE_UNVERIFIED_ENDPOINT_ACCESS"
    assert candidate["zone_count"] == 3
    assert len(candidate["routes"]) == 3
    assert all(route["length_mm"] < 90_000 for route in candidate["routes"])
    assert all(route["endpoint_access_geometry"]["endpoint_access_state"] == "VALID" for route in candidate["routes"])
    assert all(route["manifold_connected"] == "UNVERIFIED" for route in candidate["routes"])
    assert len({route["zone_id"] for route in candidate["routes"]}) == 3


def test_kitchen_auto_zoning_reacts_to_length_limit():
    accepted = propose_zoned_meanders(_kitchen_boundary(), target_route_length_mm=70_000, maximum_zones=3)
    rejected = propose_zoned_meanders(_kitchen_boundary(), target_route_length_mm=50_000, maximum_zones=3)
    assert accepted["recommended"]["zone_count"] == 3
    assert rejected["recommended"] is None
    assert rejected["status"] == "NO_GEOMETRIC_ZONE_CANDIDATE"


def test_kitchen_auto_finds_independent_bifilar_spirals_before_meander():
    result = select_layout(_kitchen_boundary(), mode="AUTO", maximum_circuit_length_mm=90_000, spacing_mm=200, wall_offset_mm=100, bend_radius_mm=80, maximum_zones=3)
    assert result["strategy"] == "MULTI_BIFILAR_SPIRAL"
    assert len(result["routes"]) == 2
    assert all(route["TOPOLOGY_VALID"] and route["BEND_VALID"] and route["PIPE_LENGTH_VALID"] for route in result["routes"])
    assert all(route["MANIFOLD_CONNECTED"] == "UNVERIFIED" for route in result["routes"])


def test_selector_uses_requested_spacing_for_spiral_topology():
    project = json.loads((Path(__file__).parents[1] / "homeaura-editor/public/plans/test01-project.json").read_text(encoding="utf-8"))
    room = next(room for room in project["rooms"] if room["label"].startswith("4 /"))
    result = select_layout([tuple(point) for point in room["global_boundary_mm"]], mode="AUTO", maximum_circuit_length_mm=90_000, spacing_mm=150, wall_offset_mm=100, bend_radius_mm=80, maximum_zones=3)
    assert result["routes"] == []
    assert any("BEND_TANGENT_CLEARANCE" in item for item in result["rejected_candidates"])

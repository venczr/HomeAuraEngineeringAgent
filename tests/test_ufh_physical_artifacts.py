import json
import re
from pathlib import Path

from agent.ufh_layout_engine import build_bifilar_spiral, validate_bifilar_topology


ROOT = Path(__file__).resolve().parents[1]


def test_riser_accounting_matches_mansard_circuit_graph():
    building = json.loads((ROOT / "dev/ufh_real_plan/building_ufh_summary.json").read_text())
    mansard = [c for c in building["circuits"] if c["floor"] == 2]
    riser = building["vertical_risers"][0]
    assert riser["number_of_supply_pipes"] == len(mansard)
    assert riser["number_of_return_pipes"] == len(mansard)
    assert riser["total_pipe_count"] == 2 * len(mansard)


def test_independent_circuit_audit_has_no_teleportation():
    audit = json.loads((ROOT / "dev/ufh_real_plan/transit_validation.json").read_text())
    assert audit["circuit_audit"]
    assert all(not row["TELEPORTATION_DETECTED"] for row in audit["circuit_audit"])


def test_schedule_exposes_policy_margin_and_decomposition():
    schedule = json.loads((ROOT / "dev/ufh_real_plan/circuit_schedule.json").read_text())
    for row in schedule:
        assert row["TOTAL_LENGTH"] == round(row["COVERAGE_LENGTH"] + row["TRANSIT_LENGTH"] + row["VERTICAL_LENGTH"], 3)
        assert row["POLICY_MARGIN"] == round(row["POLICY_LIMIT"] - row["TOTAL_LENGTH"], 3)


def test_physical_routes_pass_preview_containment_and_continuity_gates():
    summary = json.loads((ROOT / "dev/ufh_real_plan/two_floor_summary.json").read_text())
    routes = [gate for room in summary["rooms"] for gate in room.get("physical_containment", [])]
    assert routes
    assert all(gate["valid"] and gate["continuous"] for gate in routes)


def test_overlength_proposals_are_explicitly_unresolved_until_authorized_split():
    schedule = json.loads((ROOT / "dev/ufh_real_plan/circuit_schedule.json").read_text())
    over = [row for row in schedule if row["TOTAL_LENGTH"] > row["POLICY_LIMIT"]]
    assert over
    assert all(row["VALIDATION_STATUS"] == "PREVIEW_REQUIRES_INSTALLER_CONFIRMATION" for row in over)
    assert all(row["TRANSIT_RESPLIT_STATUS"] in {"RESPLIT_REQUIRED_BUT_NOT_APPLIED", "RESPLIT_BLOCKED_NO_AUTHORIZED_ENDPOINTS"} for row in over)


def test_unverified_building_transit_is_not_rendered_as_pipe():
    building = json.loads((ROOT / "dev/ufh_real_plan/building_level_ufh.json").read_text())
    svg = (ROOT / "dev/ufh_real_plan/building_level_ufh.svg").read_text()
    assert building["transit_model"]["pathfinding_valid"] is False
    assert building["transit_model"]["display_policy"] == "OMIT_UNVERIFIED_TRANSIT_GEOMETRY"
    assert 'data-layer="supply-transit"' not in svg
    assert 'data-layer="return-transit"' not in svg
    assert 'data-layer="transit-unresolved"' in svg


def test_preview_ports_are_not_reported_as_physical_manifold_connections():
    building = json.loads((ROOT / "dev/ufh_real_plan/building_level_ufh.json").read_text())
    connections = json.loads((ROOT / "dev/ufh_real_plan/manifold_connections.json").read_text())
    assert building["manifold_connection_gate"]["status"] == "UNRESOLVED_BUILDING_TRANSIT_AUTHORITY"
    assert building["manifold_connection_gate"]["validated_connection_count"] == 0
    assert connections["connections"]
    assert all(not circuit["statuses"]["MANIFOLD_CONNECTED"] for circuit in building["circuits"])
    assert all(not row["physical_connection_valid"] for row in connections["connections"])


def test_manifold_authority_intake_is_fail_closed_and_complete():
    building = json.loads((ROOT / "dev/ufh_real_plan/building_level_ufh.json").read_text())
    intake = json.loads((ROOT / "dev/ufh_real_plan/manifold_authority_intake.json").read_text())
    assert intake["project_authority_status"] == "AWAITING_SOURCE_OR_INSTALLER_CONFIRMATION"
    assert len(intake["connections"]) == len(building["circuits"])
    assert all(row["review_status"] == "AWAITING_FIELD_OR_SOURCE_EVIDENCE" for row in intake["connections"])
    assert all(row["supply"]["measured_route_mm"] is None for row in intake["connections"])
    assert all(row["return"]["measured_route_mm"] is None for row in intake["connections"])
    assert intake["riser"]["measured_height_mm"] is None


def test_visualization_validation_is_based_on_recomposed_centerlines():
    report = json.loads((ROOT / "dev/ufh_real_plan/visualization_validation.json").read_text())
    assert report["source_of_truth"] == "physical_coverage_routes_mm"
    assert report["status"] == "VALID"
    assert report["routes"]
    assert all(row["validation"]["VISUALIZATION_VALID"] for row in report["routes"])


def test_each_emitted_circuit_exposes_independent_three_state_validation():
    building = json.loads((ROOT / "dev/ufh_real_plan/building_level_ufh.json").read_text())
    required = {"GEOMETRY_VALID", "TOPOLOGY_VALID", "BEND_VALID", "CIRCUIT_SPLIT_VALID", "PIPE_LENGTH_VALID", "ENDPOINT_ACCESS_VALID", "MANIFOLD_CONNECTED", "HYDRAULIC_VALID", "VISUALIZATION_VALID"}
    allowed = {"VALID", "INVALID", "UNVERIFIED"}
    assert building["circuits"]
    for circuit in building["circuits"]:
        states = circuit["validation_states"]
        assert required <= states.keys()
        assert set(states.values()) <= allowed
        assert states["MANIFOLD_CONNECTED"] == "UNVERIFIED"
        assert states["HYDRAULIC_VALID"] == "UNVERIFIED"


def test_zone_review_keeps_endpoint_access_unverified():
    review = json.loads((ROOT / "dev/ufh_real_plan/zone_decomposition_review.json").read_text())
    assert review["status"] == "CANDIDATES_REQUIRE_UNVERIFIED_ENDPOINT_ACCESS"
    assert len(review["long_route_rooms"]) == 12
    for room in review["long_route_rooms"]:
        for candidate in room["zone_decomposition"].get("candidates", []):
            assert candidate["endpoint_access"] == "UNVERIFIED"
            assert candidate["manifold_connected"] == "UNVERIFIED"


def test_unresolved_semantic_faces_retain_source_candidates_and_blocker():
    payload = json.loads((ROOT / "dev/ufh_real_plan/semantic_face_resolution.json").read_text())
    assert payload["selection_blocker"]
    assert {row["label"].split(" / ", 1)[0] for row in payload["rooms"]} == {"2", "9"}
    assert all(row["candidates"] for row in payload["rooms"])
    assert all(any(candidate["excluded_void_count"] for candidate in row["candidates"]) for row in payload["rooms"])
    by_number = {row["label"].split(" / ", 1)[0]: row for row in payload["rooms"]}
    assert by_number["2"]["wall_evidence"]
    assert by_number["9"]["wall_evidence"] == []
    assert all(row["next_gate"] == "EXACT_STAIR_BOUNDARY_AND_PASSAGE_CONTINUITY" for row in payload["rooms"])
    assert len(payload["stair_line_evidence"]) == 2
    assert all(item["long_line_count"] >= 1 for item in payload["stair_line_evidence"])
    assert all(item["status"] == "SOURCE_VECTOR_EVIDENCE_NOT_EXACT_STAIR_POLYGON" for item in payload["stair_line_evidence"])
    assert all(item["topology_classification"] == "COINCIDENT_OR_DUPLICATE_DIAGONAL_PAIR" for item in payload["stair_line_evidence"])
    assert all(item["centerline_candidate"]["status"] == "CANDIDATE_ONLY_NOT_ROOM_BOUNDARY" for item in payload["stair_line_evidence"])


def test_continuation_queue_keeps_next_safe_block_explicit():
    queue = json.loads((ROOT / "dev/ufh_real_plan/continuation_queue.json").read_text())
    assert queue["queue"]
    assert queue["queue"][0]["status"] == "READY"
    assert queue["queue"][0]["next_action"]
    assert queue["queue"][0]["completion_condition"]


def test_spiral_svg_uses_the_calculated_first_vertex_and_rejects_duplicate_segments():
    payload = json.loads((ROOT / "dev/ufh_spiral_validation/spiral_validation.json").read_text())
    svg = (ROOT / "dev/ufh_spiral_validation/spiral_validation.svg").read_text()
    by_id = {row["fixture_id"]: row for row in payload}
    for fixture_id, bounds, offset in (
        ("A1_RECTANGLE", (0, 0, 7000, 4000), (0, 0)),
        ("A2_LONG_RECTANGLE", (0, 0, 10000, 3000), (7200, 0)),
        ("A3_SQUARE", (0, 0, 6000, 6000), (17400, 0)),
    ):
        route = build_bifilar_spiral(bounds)
        report = validate_bifilar_topology(route, bounds, [(0, 0), (bounds[2], 0), bounds[2:], (0, bounds[3]), (0, 0)])
        assert by_id[fixture_id]["valid"] is True
        assert by_id[fixture_id]["duplicate_centerline_length_mm"] == 0
        assert report.duplicate_centerline_length_mm == 0
        group = re.search(rf'data-fixture="{fixture_id}".*?<path d="([^"]+)"', svg)
        assert group
        first = group.group(1).split()[1].split(",")
        assert tuple(map(int, first)) == (route[0][0] + offset[0], route[0][1] + offset[1])

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_accepted_spiral_reference_has_visible_topology_gate():
    validation = json.loads(
        (ROOT / "projects/Test_01/exports/floor_heating_svg/HA-FH-VIS-008-CORE-R3/validation.json").read_text()
    )
    assert validation["result"] == "PASS"
    assert validation["connected_components"] == 1
    assert validation["endpoint_count"] == 2
    assert validation["branch_count"] == 0
    assert validation["self_intersections"] == 0
    assert validation["centre_hairpin_segment_count"] >= 1


def test_real_floor_preview_only_claims_gate_approved_spirals():
    summary = json.loads(
        (ROOT / "dev/ufh_real_plan/layout_strategy_summary.json").read_text()
    )
    rooms = summary["rooms"]
    for room in rooms:
        assert room["selected_strategy"] in {"MEANDER", "BIFILAR_SPIRAL", "UNRESOLVED"}
        if room["selected_strategy"] == "BIFILAR_SPIRAL":
            assert room["selected_route_topology_gate"]["valid"] is True

    candidates = json.loads(
        (ROOT / "dev/ufh_spiral_validation/spiral_validation.json").read_text()
    )
    assert candidates
    assert all(item["status"] in {"VALID", "REJECTED"} for item in candidates)
    assert any(item["status"] == "VALID" for item in candidates)
    assert any(item["status"] == "REJECTED" for item in candidates)
    for item in candidates:
        if item["status"] != "REJECTED":
            continue
        # The reason is derived from the measured diagnostics of that fixture,
        # never from a constant.
        expected = "|".join(item["diagnostics"]) or "TOPOLOGY_GATE_FAILED_WITHOUT_DIAGNOSTICS"
        assert item["rejection_reason"] == expected
        # A fixture whose own report proves the centre hairpin and the
        # interleaved return present must not be labelled as a missing centre
        # turn: that would read as a morphology failure while the real gate that
        # failed is containment.
        if item["center_turn_present"] and item["interleaved_return_present"]:
            assert (
                "CENTER_TURN_AND_INTERLEAVED_RETURN_NOT_MATERIALIZED"
                not in item["rejection_reason"]
            )

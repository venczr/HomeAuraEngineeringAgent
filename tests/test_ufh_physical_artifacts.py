import json
from pathlib import Path


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

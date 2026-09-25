import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dev/ufh_real_plan/analyze_source_kitchen_door_pair_073.py"
OUTPUT = ROOT / "dev/ufh_real_plan/source_kitchen_door_pair_073_20260925.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("source_kitchen_door_pair_073", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run073_separates_required_terminal_contact_from_forbidden_body_contact():
    report = _load_module().build_report()
    supply = report["lead_attempt"]["supply"]
    returned = report["lead_attempt"]["return"]

    assert supply["terminal_contact"] is True
    assert supply["terminal_contact_only_on_adjacent_body_segment"] is True
    assert supply["forbidden_non_adjacent_body_intersection"] is False
    assert supply["forbidden_overlap_length_mm"] == 0.0
    assert supply["minimum_non_adjacent_body_clearance_mm"] == 200.0

    assert returned["terminal_contact"] is True
    assert returned["terminal_contact_only_on_adjacent_body_segment"] is True
    assert returned["forbidden_non_adjacent_body_intersection"] is True
    assert returned["forbidden_overlap_length_mm"] == 200.0
    assert returned["minimum_non_adjacent_body_clearance_mm"] == 0.0


def test_run073_recomputes_lengths_r80_and_source_gap_crossings():
    report = _load_module().build_report()
    attempt = report["lead_attempt"]

    assert attempt["supply_lead_len_m"] == 0.444
    assert attempt["return_lead_len_m"] == 0.925
    assert attempt["supply"]["r80_materializable_in_isolation"] is False
    assert "BEND_TANGENT_CLEARANCE_VIOLATION" in attempt["supply"]["r80_diagnostics"]
    assert attempt["return"]["r80_materializable_in_isolation"] is True
    assert attempt["return"]["r80_diagnostics"] == []
    for role in ("supply", "return"):
        assert attempt[role]["crossing_inside_opening"] is False
        assert attempt[role]["crossing_to_opening_distance_mm"] == 110.0


def test_checked_run073_json_matches_the_independent_recalculation():
    module = _load_module()
    checked = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert checked == module.build_report()

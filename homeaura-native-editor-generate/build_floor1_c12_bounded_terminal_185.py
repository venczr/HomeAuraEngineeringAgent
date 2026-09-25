from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TMP = ROOT / "tmp"

SOURCE_D184 = ROOT / (
    "homeaura-native-editor/examples/proposals/"
    "HA_TWO_FLOOR_R07_POINT3_ROUTES_184/"
    "HomeAura_TwoFloor_R07Point3Routes_D184.homeaura.json"
)
FROZEN_F = ROOT / "tmp/reports/C12_SouthTerminals_Point3_D184_scratch_F.homeaura.json"
FINAL_DIAGNOSTICS_REFERENCE = ROOT / (
    "tmp/reports/C12_SouthTerminals_Point3_D184_native_diagnostics_F_gate_final.json"
)
FROZEN_AUDIT = ROOT / "tmp/reports/C12_SouthTerminals_Point3_D184_F_frozen_audit.json"
EDITOR = ROOT / "homeaura-native-editor/bin/Release/net9.0-windows/HomeAuraEditor.exe"
EDITOR_DLL = ROOT / "homeaura-native-editor/bin/Release/net9.0-windows/HomeAuraEditor.dll"

OUTPUT = ROOT / "tmp/D185_scaffold"
PACKAGE = ROOT / "tmp/HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185_SCAFFOLD.zip"
VALIDATION_OUTPUT = ROOT / "tmp/D185_scaffold_validation.json"
ARTIFACT_ID = "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185"
PROJECT_NAME = "HomeAura_TwoFloor_C12BoundedTerminal_D185.homeaura.json"
CONTRACT_NAME = "floor1_c12_bounded_terminal_contract.json"
REPORT_NAME = "floor1_c12_bounded_terminal_report.json"
CIRCUIT_ID = "F1-D171-C12"

EXPECTED_HASHES = {
    SOURCE_D184: "1A00E6B7539A0A704F1341BCCEB5982BB79B95F9520C4713D8791B573A511852",
    FROZEN_F: "558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4",
    FINAL_DIAGNOSTICS_REFERENCE: "FBC6BEDDECE6828102D4AAAA951B0FB20CAE7E13AE845391667CCCFC377A43B9",
    FROZEN_AUDIT: "6CD0F02A109605E90AFDE51C31CC8EB3F4D46CB0BECED22ED60A660F3032BD71",
    EDITOR: "763899F8B7C506B7DA9C2458DF56E7AA278152AEBE24BC4C1CBE74256F4E253E",
    EDITOR_DLL: "4C61EF6C88A2311BA37E2FE7D3A0B149A6B2DD407E7C20ED7312704CD2B49E7F",
}

EXPECTED_Q128_PERCENT = 98.74853523263984
EXPECTED_MAX_GAP_MM = 174.55844122715774
EXPECTED_RAW_3D_MM = 73877.03857936525
EXPECTED_ROUNDED_MM = 72846.94976367301
EXPECTED_SUPPLY_TAIL_GAP_MM = 3957.4620971021313
EXPECTED_RETURN_TAIL_GAP_MM = 3960.6194275643297
EXPECTED_TAIL_LOWER_BOUND_MM = 7918.081524666461
EXPECTED_EXACT_TAIL_TOTAL_LOWER_BOUND_MM = 80765.03128833947
EXPECTED_MINIMUM_ROUTE_SHORTENING_MM = 765.03128833947
REQUIRED_ROUTE_SHORTENING_MM_TO_001 = 765.032
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def close(actual: float, expected: float, label: str, tolerance: float = 1e-9) -> None:
    if abs(actual - expected) > tolerance:
        raise RuntimeError({label: {"actual": actual, "expected": expected}})


def circuit_by_id(project: dict, circuit_id: str) -> dict:
    return next(item for item in project["circuits"] if item["id"] == circuit_id)


def diagnostic_by_id(diagnostics: dict, circuit_id: str) -> dict:
    return next(item for item in diagnostics["circuits"] if item["circuit_id"] == circuit_id)


def structured_sleeve_keys(value: object, prefix: str = "") -> list[str]:
    result: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}/{key}"
            if "sleeve" in key.lower() or "гильз" in key.lower():
                result.append(path)
            result.extend(structured_sleeve_keys(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            result.extend(structured_sleeve_keys(item, f"{prefix}/{index}"))
    return result


def validate_append_only(source: dict, candidate: dict) -> tuple[list[str], list[str]]:
    if {key: value for key, value in source.items() if key != "circuits"} != \
            {key: value for key, value in candidate.items() if key != "circuits"}:
        raise RuntimeError("D185 changed non-circuit D184 payload")
    source_by_id = {item["id"]: item for item in source["circuits"]}
    candidate_by_id = {item["id"]: item for item in candidate["circuits"]}
    if set(source_by_id) != set(candidate_by_id):
        raise RuntimeError("D185 changed the circuit identity set")
    changed = sorted(item for item in source_by_id if source_by_id[item] != candidate_by_id[item])
    if changed != [CIRCUIT_ID]:
        raise RuntimeError({"D185_changed_circuit_ids": changed})
    unchanged = sorted(set(source_by_id) - {CIRCUIT_ID})
    if any(source_by_id[item] != candidate_by_id[item] for item in unchanged):
        raise RuntimeError("D185 changed a preserved circuit")
    return changed, unchanged


def validate_frozen_inputs(source: dict, candidate: dict, diagnostics: dict, audit: dict) -> dict:
    changed, unchanged = validate_append_only(source, candidate)
    circuit = circuit_by_id(candidate, CIRCUIT_ID)
    native = diagnostic_by_id(diagnostics, CIRCUIT_ID)
    ranges = circuit.get("heating_body_ranges", [])
    if ranges != [{"start_index": 8, "end_index": 31}]:
        raise RuntimeError({"D185_BODY_range": ranges})
    if circuit.get("system_role") != "FLOOR_HEATING_LOOP" or \
            circuit.get("collector_id") != "K1" or \
            [circuit.get("supply_port_index"), circuit.get("return_port_index")] != [22, 23] or \
            circuit.get("concealed_service_length_mm") != 0 or circuit.get("out_of_plane_length_mm") != 0:
        raise RuntimeError("D185 C12 frozen route semantics changed")
    points = circuit["ordered_points"]
    if len(points) != 38 or points[31] != {"x_mm": 12800, "y_mm": 20300, "z_mm": 108} or \
            points[32] != {"x_mm": 12600, "y_mm": 20300, "z_mm": 70}:
        raise RuntimeError("D185 frozen terminal ramp endpoints changed")
    transitions = {item["segment_index"]: item for item in circuit.get("vertical_transitions", [])}
    ramp = transitions.get(31)
    if set(transitions) != {1, 4, 7, 31, 35} or not ramp or \
            ramp["kind"] != "S_BEND_R80" or ramp["radius_mm"] != 80 or \
            ramp["arc_samples_per_half"] < 12:
        raise RuntimeError("D185 frozen vertical transitions changed")
    if 31 < ranges[0]["end_index"]:
        raise RuntimeError("D185 segment 31 was incorrectly classified as BODY")

    close(native["axis_length_mm"], EXPECTED_RAW_3D_MM, "raw_3d_axis_mm")
    close(native["rounded_axis_length_mm"], EXPECTED_ROUNDED_MM, "rounded_axis_mm")
    required_true = [
        "grid_aligned", "continuous", "orthogonal", "completed", "length_in_range",
        "rounded_length_in_range", "start_at_collector", "end_at_collector",
        "vertical_geometry_materialized", "vertical_transition_radius_feasible",
        "bend_radius_feasible", "topology_pass", "pass", "engineering_pass",
    ]
    required_zero = [
        "self_intersections", "self_surface_clearance_violations", "inter_circuit_intersections",
        "inter_circuit_surface_clearance_violations", "heating_body_wall_intrusions",
        "horizontal_turn_wall_intrusions", "bend_radius_violation_count",
        "unmaterialized_elevation_change_count", "concealed_service_length_mm",
        "out_of_plane_length_mm",
    ]
    if any(not native[key] for key in required_true) or any(native[key] != 0 for key in required_zero):
        raise RuntimeError("D185 native physical route gates changed")
    if native["exterior3x100_pass"] or native["exterior3x100_useful_span_pass"] or \
            native["exterior_open_spiral_terminal_corner_pass"] or diagnostics["design_pass"]:
        raise RuntimeError("D185 base diagnostic truth changed")

    native_sibling = native.get("exterior_open_spiral_materialized_terminal_ramp")
    expected_native_sibling = {
        "room_id": "F1-R01",
        "applicable": True,
        "pass": True,
        "reason": "PASS_MATERIALIZED_TERMINAL_RAMP_COMPLETES_EXTERIOR_LANE",
        "body_range_start_index": 8,
        "body_range_end_index": 31,
        "body_endpoint_side": "END",
        "circuit_segment_index": 31,
        "transition_kind": "S_BEND_R80",
        "transition_materialized_pass": True,
        "wall_id": "FLOOR_1-W030",
        "lane_index": 2,
        "missing_interval": {
            "start": {"x_mm": 12600, "y_mm": 20300},
            "end": {"x_mm": 12800, "y_mm": 20300},
        },
        "ramp_projected_interval": {
            "start": {"x_mm": 12600, "y_mm": 20300},
            "end": {"x_mm": 12800, "y_mm": 20300},
        },
        "missing_length_mm": 200,
        "ramp_projected_length_mm": 200,
        "adjacent_body_endpoint_pass": True,
        "same_heading_continuation_pass": True,
        "exact_gap_match_pass": True,
        "windowless_gap_pass": True,
        "no_terminal_wall_or_other_lane_contribution_pass": True,
        "deficient_wall_shares_open_corner_pass": True,
        "gap_at_shared_open_corner_pass": True,
        "assigned_room_wall_clear_pass": True,
        "full_circuit_physical_gate_pass": True,
        "native_collector_terminal_tolerance_pass": True,
        "global_inter_circuit_contact_pass": True,
        "completion_candidate_count": 1,
        "augmented_coverage_percent": 100,
        "augmented_window_coverage_percent": 100,
        "augmented_strict_lane_pass": True,
        "augmented_all_non_terminal_walls_strict_pass": True,
        "augmented_open_corner_adjacency_pass": True,
        "open_terminal_wall_id": "FLOOR_1-W033",
        "open_terminal_side": "START",
    }
    if native_sibling != expected_native_sibling or \
            not native.get("exterior_open_spiral_materialized_terminal_ramp_applicable") or \
            not native.get("exterior_open_spiral_materialized_terminal_ramp_pass"):
        raise RuntimeError("D185 current-Release native materialized-terminal-ramp gate changed")

    coverage = audit["physical_BODY_coverage"]["results"]["q128"]
    close(coverage["served_percent"], EXPECTED_Q128_PERCENT, "q128_coverage")
    close(coverage["maximum_sample_distance_mm"], EXPECTED_MAX_GAP_MM, "q128_max_gap")
    if coverage["sample_over_200mm_count"] != 0:
        raise RuntimeError("D185 q128 over-200 count changed")
    supporting_sibling = audit["materialized_terminal_ramp_lane_completion"]
    if supporting_sibling["semantic_gate"] != "MATERIALIZED_TERMINAL_RAMP_COMPLETES_EXTERIOR_LANE" or \
            not supporting_sibling["pass"] or supporting_sibling["ramp_segment_index"] != 31 or \
            supporting_sibling["wall_id"] != "FLOOR_1-W030" or supporting_sibling["lane_index"] != 2:
        raise RuntimeError("D185 sibling terminal-ramp gate changed")
    if audit["status"] != "SCRATCH_POINT3_CONDITIONAL_GO_MATERIALIZED_TERMINAL_RAMP" or \
            not audit["hard_physical_and_Point3_gates_pass"]:
        raise RuntimeError("D185 frozen bounded-terminal audit is not GO")

    if diagnostics["axis_only_circuit_count"] != 0 or diagnostics["total_concealed_service_length_mm"] != 0 or \
            diagnostics["installation_completeness_pass"] or diagnostics["design_pass"]:
        raise RuntimeError("D185 project completeness truth changed")
    floor1 = next(item for item in diagnostics["collector_served_floor_details"] if item["collector_id"] == "K1")
    attic = next(item for item in diagnostics["collector_served_floor_details"] if item["collector_id"] == "K2")
    if [floor1["loop_circuit_count"], floor1["axis_circuit_count"]] != [14, 0] or \
            [attic["heating_body_count"], attic["loop_circuit_count"], attic["axis_circuit_count"]] != [0, 0, 0]:
        raise RuntimeError("D185 floor/attic bounded counts changed")
    if structured_sleeve_keys(candidate):
        raise RuntimeError("D185 contains structured sleeve geometry")

    walls = audit["wall_audit"]
    bank = audit["global_bank_audit"]
    tails = audit["ports_and_terminal_grid_gaps"]
    if not walls["pass"] or walls["intersection_count"] != 4 or walls["body_wall_hit_count"] != 0 or \
            not bank["pass"] or bank["maximum_axes_in_inclusive_300mm_window"] != 3 or \
            tails["selected_ports"] != [22, 23] or tails["collector_continuous"] or tails["complete_K1"]:
        raise RuntimeError("D185 wall/bank/tail evidence changed")
    close(tails["tails"][0]["straight_line_gap_mm"], EXPECTED_SUPPLY_TAIL_GAP_MM, "supply_tail_gap")
    close(tails["tails"][1]["straight_line_gap_mm"], EXPECTED_RETURN_TAIL_GAP_MM, "return_tail_gap")
    close(
        EXPECTED_SUPPLY_TAIL_GAP_MM + EXPECTED_RETURN_TAIL_GAP_MM,
        EXPECTED_TAIL_LOWER_BOUND_MM,
        "tail_sum_lower_bound",
    )
    close(
        EXPECTED_ROUNDED_MM + EXPECTED_TAIL_LOWER_BOUND_MM,
        EXPECTED_EXACT_TAIL_TOTAL_LOWER_BOUND_MM,
        "exact_tail_total_lower_bound",
    )
    close(
        EXPECTED_EXACT_TAIL_TOTAL_LOWER_BOUND_MM - 80000.0,
        EXPECTED_MINIMUM_ROUTE_SHORTENING_MM,
        "minimum_route_shortening",
    )
    return {
        "changed": changed,
        "unchanged": unchanged,
        "circuit": circuit,
        "native": native,
        "coverage": coverage,
        "native_sibling": native_sibling,
        "supporting_sibling": supporting_sibling,
        "walls": walls,
        "bank": bank,
        "tails": tails,
        "floor1": floor1,
        "attic": attic,
    }


def floor1_projection(project: dict) -> dict:
    result = copy.deepcopy(project)
    result["levels"] = [item for item in result["levels"] if item["id"] == "FLOOR_1"]
    result["rooms"] = [item for item in result["rooms"] if item["floor_id"] == "FLOOR_1"]
    result["exclusions"] = [item for item in result["exclusions"] if item["floor_id"] == "FLOOR_1"]
    result["service_zones"] = [item for item in result["service_zones"] if item["floor_id"] == "FLOOR_1"]
    result["walls"] = [item for item in result["walls"] if item["id"].startswith("FLOOR_1-")]
    result["collectors"] = [item for item in result["collectors"] if item["floor_id"] == "FLOOR_1"]
    result["circuits"] = [item for item in result["circuits"] if item["id"].startswith("F1-")]
    result["windows"] = [item for item in result["windows"] if item["wall_id"].startswith("FLOOR_1-")]
    result["floor_build_ups"] = [item for item in result["floor_build_ups"] if item["floor_id"] == "FLOOR_1"]
    return result


def run_editor(project_path: Path, output_path: Path, command: str, room_id: str | None = None) -> None:
    args = [str(EDITOR), command, str(project_path), str(output_path)]
    if room_id:
        args.append(room_id)
    completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError({"command": args, "stdout": completed.stdout, "stderr": completed.stderr})


def png_dimensions(path: Path) -> list[int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise RuntimeError({"not_png": str(path)})
    return list(struct.unpack(">II", data[16:24]))


def deterministic_zip(output: Path, package: Path) -> None:
    files = sorted(path for path in output.iterdir() if path.is_file())
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def safe_refresh() -> None:
    expected_output = (ROOT / "tmp/D185_scaffold").resolve()
    if OUTPUT.resolve() != expected_output or OUTPUT.resolve().parent != TMP.resolve():
        raise RuntimeError("Unsafe D185 scaffold refresh target")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    if PACKAGE.exists():
        PACKAGE.unlink()
    if VALIDATION_OUTPUT.exists():
        VALIDATION_OUTPUT.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-scaffold", action="store_true")
    parser.add_argument("--publish", action="store_true", help="Deliberately blocked until root final GO")
    args = parser.parse_args()
    if args.publish:
        raise RuntimeError(
            "D185 official publication/Program registration is hard-blocked pending two independent D185 package GO records and explicit root GO"
        )
    if OUTPUT.exists() or PACKAGE.exists() or VALIDATION_OUTPUT.exists():
        if not args.refresh_scaffold:
            raise FileExistsError("D185 scaffold exists; use --refresh-scaffold for the exact tmp target")
        safe_refresh()

    for path, expected in EXPECTED_HASHES.items():
        actual = sha(path)
        if actual != expected:
            raise RuntimeError({"D185_frozen_input_hash_changed": {"path": str(path), "actual": actual, "expected": expected}})
    if not EDITOR.exists():
        raise FileNotFoundError(EDITOR)

    source = json.loads(SOURCE_D184.read_text(encoding="utf-8-sig"))
    candidate = json.loads(FROZEN_F.read_text(encoding="utf-8-sig"))
    audit = json.loads(FROZEN_AUDIT.read_text(encoding="utf-8-sig"))

    OUTPUT.mkdir(parents=True)
    project_path = OUTPUT / PROJECT_NAME
    project_path.write_bytes(FROZEN_F.read_bytes())
    if sha(project_path) != EXPECTED_HASHES[FROZEN_F]:
        raise RuntimeError("D185 scaffold project is not byte-identical to frozen F")
    diagnostics_path = OUTPUT / "engineering_diagnostics.json"
    run_editor(project_path, diagnostics_path, "--export-diagnostics")
    if sha(diagnostics_path) != EXPECTED_HASHES[FINAL_DIAGNOSTICS_REFERENCE] or \
            diagnostics_path.read_bytes() != FINAL_DIAGNOSTICS_REFERENCE.read_bytes():
        raise RuntimeError("D185 current Release diagnostics are not byte-identical to the final gate export")
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8-sig"))
    evidence = validate_frozen_inputs(source, candidate, diagnostics, audit)

    publication_guard = {
        "active": True,
        "official_publication_allowed": False,
        "Program_registration_allowed": False,
        "official_freeze_allowed": False,
        "native_final_materialized_terminal_ramp_gate": "PASS",
        "independent_GO_required": 2,
        "independent_GO_received": 0,
        "release_condition": "two independent D185 package GO records, followed by explicit root GO",
    }
    contract = {
        "schema": "homeaura.floor1.c12_bounded_terminal.v1",
        "artifact_id": ARTIFACT_ID,
        "status": "PREPUBLICATION_D185_SCAFFOLD_BOUNDED_TERMINAL_F",
        "publication_state": "SCAFFOLD_HARD_GUARD_ACTIVE_NOT_OFFICIAL",
        "append_only": True,
        "publishable": False,
        "publishable_as_installation_project": False,
        "publication_guard": publication_guard,
        "source_provenance": {
            "official_D184": {"path": str(SOURCE_D184.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_HASHES[SOURCE_D184]},
            "frozen_F_candidate": {"path": str(FROZEN_F.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_HASHES[FROZEN_F]},
            "current_Release_editor_exe": {"path": str(EDITOR.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_HASHES[EDITOR]},
            "current_Release_editor_dll": {"path": str(EDITOR_DLL.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_HASHES[EDITOR_DLL]},
            "deterministic_generator": {"path": str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"), "sha256": sha(Path(__file__).resolve())},
            "final_native_gate_reference": {"path": str(FINAL_DIAGNOSTICS_REFERENCE.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_HASHES[FINAL_DIAGNOSTICS_REFERENCE]},
            "scaffold_engineering_diagnostics": {"generated_by": "current Release --export-diagnostics", "sha256": EXPECTED_HASHES[FINAL_DIAGNOSTICS_REFERENCE], "byte_identical_to_final_native_gate_reference": True},
            "frozen_bounded_terminal_audit": {"path": str(FROZEN_AUDIT.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_HASHES[FROZEN_AUDIT]},
        },
        "append_only_diff_boundary": {
            "changed_circuit_ids": evidence["changed"],
            "unchanged_circuit_ids": evidence["unchanged"],
            "unchanged_circuit_count": len(evidence["unchanged"]),
            "all_other_circuits_equal": True,
            "non_circuit_payload_equal": True,
            "project_byte_identical_to_frozen_F": True,
        },
        "C12_route": {
            "collector_id": "K1",
            "ports": [22, 23],
            "system_role": "FLOOR_HEATING_LOOP",
            "point_count": 38,
            "BODY_range_inclusive": [8, 31],
            "BODY_axis_elevation_mm": 108,
            "TRANSIT_axis_elevations_mm": [70, 135],
            "concealed_service_length_mm": 0,
            "out_of_plane_length_mm": 0,
            "raw_3D_axis_length_mm": EXPECTED_RAW_3D_MM,
            "physical_R80_rounded_axis_length_mm": EXPECTED_ROUNDED_MM,
            "physical_length_40_to_80m": True,
            "native_completed": evidence["native"]["completed"],
            "native_completed_claim_scope": "ordered bounded-terminal route completion under K1 connection_tolerance_mm=4100; not exact Eurocone continuity",
        },
        "native_completion_claim_boundary": {
            "native_completed": evidence["native"]["completed"],
            "native_start_at_collector": evidence["native"]["start_at_collector"],
            "native_end_at_collector": evidence["native"]["end_at_collector"],
            "K1_connection_tolerance_mm": 4100,
            "native_collector_terminal_tolerance_pass": evidence["native_sibling"]["native_collector_terminal_tolerance_pass"],
            "meaning": "native ordered/bounded-terminal completion within configured 4100 mm tolerance only",
            "does_not_mean_exact_Eurocone_continuity": True,
            "collectorContinuous": 0,
            "completeK1": 0,
        },
        "BODY_morphology": {
            "classification": "ONE_COHERENT_REFLECTED_TWO_ARM_COUNTERFLOW",
            "intended_open_terminal_wall": "FLOOR_1-W033",
            "physical_R80_q128_served_percent": EXPECTED_Q128_PERCENT,
            "maximum_sample_distance_mm": EXPECTED_MAX_GAP_MM,
            "sample_over_200mm_count": 0,
            "physical_axis_simple": evidence["coverage"]["physical_axis_simple"],
            "pipe16_inside_clear_domain": evidence["coverage"]["pipe16_inside_clear_domain"],
        },
        "base_native_diagnostic_truth": {
            "legacy_raw_exterior3x100_pass": evidence["native"]["exterior3x100_pass"],
            "useful_span_pass": evidence["native"]["exterior3x100_useful_span_pass"],
            "open_spiral_terminal_corner_pass": evidence["native"]["exterior_open_spiral_terminal_corner_pass"],
            "route_topology_pass": evidence["native"]["topology_pass"],
            "route_engineering_pass": evidence["native"]["engineering_pass"],
            "route_pass": evidence["native"]["pass"],
            "materialized_terminal_ramp_applicable": evidence["native"]["exterior_open_spiral_materialized_terminal_ramp_applicable"],
            "materialized_terminal_ramp_pass": evidence["native"]["exterior_open_spiral_materialized_terminal_ramp_pass"],
            "project_design_pass": diagnostics["design_pass"],
        },
        "additive_sibling_materialized_terminal_ramp": {
            **evidence["native_sibling"],
            "source": "CURRENT_RELEASE_NATIVE_DIAGNOSTICS",
            "segment_role": "TRANSIT",
            "BODY_role_extended": False,
            "arbitrary_TRANSIT_counted_as_BODY": False,
            "claim_scope": "only adjacent same-circuit collinear materialized S_BEND_R80 segment 31 completes W030 lane 2",
        },
        "supporting_frozen_bounded_terminal_audit": evidence["supporting_sibling"],
        "native_physical_gates": evidence["native"],
        "wall_crossing_audit": evidence["walls"],
        "global_same_layer_bank_audit": evidence["bank"],
        "bounded_project_counts": {
            "FLOOR_1_loop_route_count": 14,
            "axis_only_circuit_count": diagnostics["axis_only_circuit_count"],
            "total_concealed_service_length_mm": diagnostics["total_concealed_service_length_mm"],
            "total_out_of_plane_length_mm": diagnostics["total_out_of_plane_length_mm"],
            "K2_ATTIC_heating_body_count": evidence["attic"]["heating_body_count"],
            "K2_ATTIC_loop_route_count": evidence["attic"]["loop_circuit_count"],
            "K2_ATTIC_axis_route_count": evidence["attic"]["axis_circuit_count"],
        },
        "collector_terminal_grid": {
            "collectorContinuous": 0,
            "completeK1": 0,
            "physical_Eurocone_tails_materialized": False,
            "tails_deferred": True,
            "ports": [22, 23],
            "supply_terminal_to_Eurocone_straight_gap_mm": EXPECTED_SUPPLY_TAIL_GAP_MM,
            "return_terminal_to_Eurocone_straight_gap_mm": EXPECTED_RETURN_TAIL_GAP_MM,
            "hard_sum_Euclidean_tail_gaps_lower_bound_mm": EXPECTED_TAIL_LOWER_BOUND_MM,
            "rounded_route_plus_exact_tail_lower_bound_mm": EXPECTED_EXACT_TAIL_TOTAL_LOWER_BOUND_MM,
            "rounded_route_plus_exact_tail_lower_bound_m": EXPECTED_EXACT_TAIL_TOTAL_LOWER_BOUND_MM / 1000.0,
            "exceeds_80m_by_mm": EXPECTED_MINIMUM_ROUTE_SHORTENING_MM,
            "minimum_route_shortening_required_mm_to_0_001": REQUIRED_ROUTE_SHORTENING_MM_TO_001,
            "exact_Eurocone_tails_cannot_be_appended_within_80m": True,
            "required_before_exact_tails": "shorten the existing route by at least 765.032 mm, then materialize both tails and repeat the full 3D audit",
            "exact_evidence": evidence["tails"],
        },
        "installation_truth": {
            "structured_sleeve_geometry_count": 0,
            "sleeves_added": False,
            "installation_completeness_pass": diagnostics["installation_completeness_pass"],
            "installation_ready": False,
            "design_pass": diagnostics["design_pass"],
            "K2_ATTIC_materialized_routes": 0,
        },
        "next_gate": "OBTAIN_TWO_INDEPENDENT_D185_PACKAGE_GO_RECORDS_THEN_EXPLICIT_ROOT_GO",
    }
    report = {
        "schema": "homeaura.floor1.c12_bounded_terminal.report.v1",
        "artifact_id": ARTIFACT_ID,
        "publication_state": contract["publication_state"],
        "append_only_diff_boundary": contract["append_only_diff_boundary"],
        "C12_route": contract["C12_route"],
        "native_completion_claim_boundary": contract["native_completion_claim_boundary"],
        "BODY_morphology": contract["BODY_morphology"],
        "base_native_diagnostic_truth": contract["base_native_diagnostic_truth"],
        "additive_sibling_materialized_terminal_ramp": contract["additive_sibling_materialized_terminal_ramp"],
        "supporting_frozen_bounded_terminal_audit": contract["supporting_frozen_bounded_terminal_audit"],
        "wall_crossing_audit": evidence["walls"],
        "global_same_layer_bank_audit": evidence["bank"],
        "collector_terminal_grid": contract["collector_terminal_grid"],
        "bounded_project_counts": contract["bounded_project_counts"],
        "installation_truth": contract["installation_truth"],
        "publication_guard": publication_guard,
    }
    status = {
        "artifact_id": ARTIFACT_ID,
        "result": "SCAFFOLD_VALID_BOUNDARY_PUBLICATION_BLOCKED",
        "publication_state": contract["publication_state"],
        "publishable": False,
        "official_files_modified": False,
        "changed_circuit_ids": [CIRCUIT_ID],
        "bounded_terminal_grid_route_count": 14,
        "axis_only_circuit_count": 0,
        "total_concealed_service_length_mm": 0,
        "physical_R80_q128_coverage_percent": EXPECTED_Q128_PERCENT,
        "maximum_sample_distance_mm": EXPECTED_MAX_GAP_MM,
        "sample_over_200mm_count": 0,
        "physical_R80_rounded_axis_length_mm": EXPECTED_ROUNDED_MM,
        "native_completed": evidence["native"]["completed"],
        "native_completed_claim_scope": contract["native_completion_claim_boundary"]["meaning"],
        "native_completed_does_not_mean_exact_Eurocone_continuity": True,
        "native_final_materialized_terminal_ramp_gate": "PASS",
        "collectorContinuous": 0,
        "completeK1": 0,
        "physical_Eurocone_tails_materialized": False,
        "hard_sum_Euclidean_tail_gaps_lower_bound_mm": EXPECTED_TAIL_LOWER_BOUND_MM,
        "rounded_route_plus_exact_tail_lower_bound_mm": EXPECTED_EXACT_TAIL_TOTAL_LOWER_BOUND_MM,
        "exceeds_80m_by_mm": EXPECTED_MINIMUM_ROUTE_SHORTENING_MM,
        "minimum_route_shortening_required_mm_to_0_001": REQUIRED_ROUTE_SHORTENING_MM_TO_001,
        "exact_Eurocone_tails_cannot_be_appended_within_80m": True,
        "sleeves_added": False,
        "installation_ready": False,
        "K2_ATTIC_materialized_routes": 0,
        "publication_guard": publication_guard,
    }
    dump(OUTPUT / CONTRACT_NAME, contract)
    dump(OUTPUT / REPORT_NAME, report)
    dump(OUTPUT / "status.json", status)

    readme = (
        "# D185 scaffold · C12 bounded-terminal Point3\n\n"
        "Это только предпубликационный append-only scaffold. Относительно официального D184 изменён один C12; "
        "остальные circuits и весь non-circuit payload совпадают побайтно по JSON-значениям. Геометрия проекта "
        "копируется из frozen F без повторного построения.\n\n"
        f"BODY — одна связная двухрукавная counterflow-улитка: q128 {EXPECTED_Q128_PERCENT:.6f}%, "
        f"максимум {EXPECTED_MAX_GAP_MM:.3f} мм, превышений 200 мм нет. Полная физическая R80-длина "
        f"{EXPECTED_ROUNDED_MM/1000:.6f} м. Native topology/engineering/contact/wall/R80 gates маршрута проходят.\n\n"
        "Legacy raw/useful/open exterior diagnostics остаются false и не скрываются. Текущий Release native "
        "sibling gate PASS считает только соседний TRANSIT S_BEND_R80 segment 31: он физически и без разрыва "
        "завершает W030-L2, но не становится BODY и не разрешает произвольный TRANSIT.\n\n"
        "На FLOOR_1: 14 bounded terminal-grid loops, AXIS=0, concealed=0. Collector continuity=0, completeK1=0; "
        "хвосты портов 22/23 до Eurocone отложены. Их жёсткая сумма прямолинейных нижних границ — "
        f"{EXPECTED_TAIL_LOWER_BOUND_MM:.6f} мм; вместе с текущей rounded-трассой минимум получается "
        f"{EXPECTED_EXACT_TAIL_TOTAL_LOWER_BOUND_MM/1000:.9f} м, то есть выше лимита на "
        f"{EXPECTED_MINIMUM_ROUTE_SHORTENING_MM:.6f} мм. Exact Eurocone tails нельзя просто дописать: сначала "
        f"нужно сократить существующий маршрут минимум на {REQUIRED_ROUTE_SHORTENING_MM_TO_001:.3f} мм, затем "
        "материализовать оба хвоста и заново провести полный 3D-аудит.\n\n"
        "Native completed:true означает только завершённость ordered/bounded-terminal route в пределах "
        "K1 connection_tolerance_mm=4100; это не exact Eurocone continuity. Гильзы не добавлены, "
        "installation_ready=false, на ATTIC/K2 нет отопительных тел или маршрутов.\n\n"
        "Оба R01-рендера — комнатные crop с контекстом соседних трасс проекта: C12 является focus circuit, "
        "а не единственным отображённым контуром. Full-floor clean render отдельно ограничен FLOOR_1 без "
        "ATTIC overlay.\n\n"
        "Публикация, Program registration и official freeze заблокированы до двух независимых GO по D185 "
        "package и явного root GO.\n"
    )
    (OUTPUT / "README.md").write_text(readme, encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="D185_floor1_render_", dir=TMP) as temporary:
        render_project = Path(temporary) / "floor1_only.homeaura.json"
        dump(render_project, floor1_projection(candidate))
        run_editor(render_project, OUTPUT / "HomeAura_Floor1_D185_Clean_View.png", "--export-png-clean")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D185_R01_C12_Clean_Zoom.png", "--export-room-png-clean", "F1-R01")
    run_editor(project_path, OUTPUT / "HomeAura_Floor1_D185_R01_C12_3D_Diagnostic.png", "--export-room-png-diagnostics", "F1-R01")
    render_provenance = {
        "full_floor_clean": {
            "file": "HomeAura_Floor1_D185_Clean_View.png",
            "source_scope": "temporary FLOOR_1-only projection",
            "included_level_ids": ["FLOOR_1"],
            "excluded_level_ids": ["ATTIC"],
            "included_circuit_ids": [item["id"] for item in candidate["circuits"] if item["id"].startswith("F1-")],
            "ATTIC_overlay_rendered": False,
        },
        "R01_C12_clean": {
            "file": "HomeAura_Floor1_D185_R01_C12_Clean_Zoom.png",
            "room_id": "F1-R01",
            "source_scope": "ROOM_CROP_WITH_PROJECT_CONTEXT",
            "render_scope": "ROOM_CROP_WITH_PROJECT_CONTEXT",
            "focus_circuit_ids": [CIRCUIT_ID],
            "context_circuits_rendered": True,
            "exclusive_circuit_filter_applied": False,
        },
        "R01_C12_3D_diagnostic": {
            "file": "HomeAura_Floor1_D185_R01_C12_3D_Diagnostic.png",
            "room_id": "F1-R01",
            "source_scope": "ROOM_CROP_WITH_PROJECT_CONTEXT",
            "render_scope": "ROOM_CROP_WITH_PROJECT_CONTEXT",
            "focus_circuit_ids": [CIRCUIT_ID],
            "context_circuits_rendered": True,
            "exclusive_circuit_filter_applied": False,
        },
    }
    for item in render_provenance.values():
        item["pixel_dimensions"] = png_dimensions(OUTPUT / item["file"])
    dump(OUTPUT / "render_provenance.json", render_provenance)

    payloads = sorted(path for path in OUTPUT.iterdir() if path.is_file() and path.name != "artifact_manifest.json")
    manifest = {
        "artifact_id": ARTIFACT_ID,
        "append_only": True,
        "publication_state": contract["publication_state"],
        "project_sha256": EXPECTED_HASHES[FROZEN_F],
        "engineering_diagnostics_sha256": EXPECTED_HASHES[FINAL_DIAGNOSTICS_REFERENCE],
        "current_Release_editor_exe_sha256": EXPECTED_HASHES[EDITOR],
        "current_Release_editor_dll_sha256": EXPECTED_HASHES[EDITOR_DLL],
        "deterministic_generator_sha256": sha(Path(__file__).resolve()),
        "publication_guard_active": True,
        "files": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}
            for path in payloads
        ],
    }
    dump(OUTPUT / "artifact_manifest.json", manifest)
    deterministic_zip(OUTPUT, PACKAGE)
    print(json.dumps({
        "artifact_id": ARTIFACT_ID,
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "project_sha256": sha(project_path),
        "manifest_sha256": sha(OUTPUT / "artifact_manifest.json"),
        "package_sha256": sha(PACKAGE),
        "publication_guard": publication_guard,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

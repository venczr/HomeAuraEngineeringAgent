from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from build_floor1_wet_pair_176 import transit_wall_audit  # noqa: E402
from build_floor1_wet_pair_physical_turn_fix_177 import collector_tail_evidence  # noqa: E402


PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D181_DIRECTORY = PROPOSALS / "HA_TWO_FLOOR_ATTIC_SOURCE_WALL_DOMAINS_181"
D181_PROJECT = D181_DIRECTORY / "HomeAura_TwoFloor_SourceWallDomains_D181.homeaura.json"
D181_CONTRACT = D181_DIRECTORY / "attic_source_wall_domains_contract.json"
D182_DIRECTORY = PROPOSALS / "HA_TWO_FLOOR_R03_OWNER_BODY_FIXTURE_182"
D182_CONTRACT = D182_DIRECTORY / "r03_owner_body_fixture_contract.json"
SCRATCH_DIRECTORY = ROOT / "tmp" / "r03_transit_optimizer"
CANDIDATE = SCRATCH_DIRECTORY / "final_candidate_forward_exact.homeaura.json"
SCRATCH_DIAGNOSTICS = SCRATCH_DIRECTORY / "final_candidate_forward_exact.diagnostics.json"
SCRATCH_ACCEPTANCE = SCRATCH_DIRECTORY / "final_candidate_forward_exact.acceptance.json"

OFFICIAL_OUTPUT = PROPOSALS / "HA_TWO_FLOOR_R03_POINT3_ROUTES_183"
OFFICIAL_PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_R03_POINT3_ROUTES_183.zip"
SCAFFOLD_OUTPUT = ROOT / "tmp" / "D183_scaffold"
SCAFFOLD_PACKAGE = ROOT / "tmp" / "HA_TWO_FLOOR_R03_POINT3_ROUTES_183_SCAFFOLD.zip"
ARTIFACT_ID = "HA_TWO_FLOOR_R03_POINT3_ROUTES_183"
PROJECT_NAME = "HomeAura_TwoFloor_R03Point3Routes_D183.homeaura.json"
CONTRACT_NAME = "floor1_r03_point3_routes_contract.json"
CHANGED_IDS = ("F1-D171-C07", "F1-D171-C08", "F1-D171-C09")

D181_PROJECT_SHA = "253E0DD8DBD59227BBE0147DBFECB201EDAAD56F19E4B3B0511B22254B8C55F2"
D181_CONTRACT_SHA = "3F165409B96208BA5F2E5C190D2B185A1CA867CC874B863595ECB294A5D5FBF5"
D182_CONTRACT_SHA = "BC4F7A3FAB3969E83516F9E82772A3F7727BAF9870F93ECB094D3691361E08D8"
CANDIDATE_SHA = "E5096220BE3D2F7C93BC5F8B399A374C95556A9D4A29797445EDDC27835CDE4B"
SCRATCH_DIAGNOSTICS_SHA = "FAFC12707CCB88CDB515EAE999088677E8E6F479C3DDF9151A6F22DAF5F2982E"
SCRATCH_ACCEPTANCE_SHA = "C2A85B64A7CF4C87CD35D30A3B71DE2996B6896B08AC935EE646E4CF8F8F8CEB"

EXPECTED_RAW_MM = {
    "F1-D171-C07": 72_335.29922991096,
    "F1-D171-C08": 72_057.71822073533,
    "F1-D171-C09": 72_918.12470016345,
}
EXPECTED_ROUNDED_MM = {
    "F1-D171-C07": 71_236.5378265059,
    "F1-D171-C08": 70_615.59387876619,
    "F1-D171-C09": 71_819.36329675838,
}
EXPECTED_RAW_SPREAD_MM = 860.4064794281148
EXPECTED_ROUNDED_SPREAD_MM = 1_203.7694179921964


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sha_payload(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def close(expected: float, actual: float, label: str, tolerance: float = 0.000001) -> None:
    if abs(expected - actual) > tolerance:
        raise RuntimeError({label: {"expected": expected, "actual": actual}})


def run_editor(project_path: Path, output_path: Path, command: str, room_id: str | None = None) -> None:
    args = [
        "dotnet", "run", "--project", str(ROOT / "homeaura-native-editor" / "HomeAura.NativeEditor.csproj"),
        "-c", "Release", "--", command, str(project_path), str(output_path),
    ]
    if room_id:
        args.append(room_id)
    completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError({"command": args, "stdout": completed.stdout, "stderr": completed.stderr})


def point_tuple(point: dict, fallback_z: int) -> tuple[int, int, int]:
    return point["x_mm"], point["y_mm"], point.get("z_mm", fallback_z)


def circuit_specifications(project: dict) -> list[dict]:
    circuits = {item["id"]: item for item in project["circuits"]}
    result = []
    for circuit_id in CHANGED_IDS:
        circuit = circuits[circuit_id]
        result.append({
            "id": circuit_id,
            "points": [point_tuple(item, circuit.get("axis_elevation_mm", 108)) for item in circuit["ordered_points"]],
            "ranges": [(item["start_index"], item["end_index"]) for item in circuit["heating_body_ranges"]],
        })
    return result


def floor1_render_projection(project: dict) -> dict:
    """Render-only view; the official two-level project remains byte-exact E509."""
    result = copy.deepcopy(project)
    result["levels"] = [item for item in result["levels"] if item["id"] == "FLOOR_1"]
    result["rooms"] = [item for item in result["rooms"] if item["floor_id"] == "FLOOR_1"]
    result["exclusions"] = [item for item in result["exclusions"] if item["floor_id"] == "FLOOR_1"]
    return result


def body_identity(specifications: list[dict], d182: dict) -> dict:
    bodies = {}
    for specification in specifications:
        bodies[specification["id"]] = [
            [[specification["points"][index][0] // 100, specification["points"][index][1] // 100]
             for index in range(start, end + 1)]
            for start, end in specification["ranges"]
        ]
    actual = {
        "C07": sha_payload(bodies["F1-D171-C07"][0]),
        "C08_shelf": sha_payload(bodies["F1-D171-C08"][0]),
        "C08_main": sha_payload(bodies["F1-D171-C08"][1]),
        "C08_seam": sha_payload(bodies["F1-D171-C08"][2]),
        "C08_body_ranges": sha_payload(bodies["F1-D171-C08"]),
        "C09": sha_payload(bodies["F1-D171-C09"][0]),
    }
    expected = d182["ordered_point_sha256"]
    matches = {key: value == expected[key] for key, value in actual.items()}
    if not all(matches.values()):
        raise RuntimeError({"D182_BODY_identity": matches})
    return {"expected_D182_sha256": expected, "actual_D183_sha256": actual,
            "per_range_match": matches, "all_match": True}


def validate_diff(source: dict, project: dict) -> list[str]:
    source_by_id = {item["id"]: item for item in source["circuits"]}
    current_by_id = {item["id"]: item for item in project["circuits"]}
    if {key: value for key, value in source.items() if key != "circuits"} != \
            {key: value for key, value in project.items() if key != "circuits"}:
        raise RuntimeError("D183 changed non-circuit D181 payload")
    changed = sorted(item for item in source_by_id if source_by_id[item] != current_by_id[item])
    if changed != sorted(CHANGED_IDS):
        raise RuntimeError({"D183_changed_circuit_ids": changed})
    unchanged = sorted(set(source_by_id) - set(CHANGED_IDS))
    if any(source_by_id[item] != current_by_id[item] for item in unchanged):
        raise RuntimeError("D183 changed a preserved circuit")
    return unchanged


def validate_ports(project: dict) -> dict:
    selected = {}
    uses = []
    for circuit in project["circuits"]:
        if circuit.get("collector_id") != "K1":
            continue
        pair = [circuit.get("supply_port_index"), circuit.get("return_port_index")]
        uses.extend((value, circuit["id"]) for value in pair if value is not None)
        if circuit["id"] in CHANGED_IDS:
            selected[circuit["id"]] = pair
    expected = {
        "F1-D171-C07": [12, 13], "F1-D171-C08": [14, 15], "F1-D171-C09": [16, 17],
    }
    ports = sorted(item[0] for item in uses)
    if selected != expected or ports != list(range(28)) or len({item[0] for item in uses}) != len(uses):
        raise RuntimeError({"D183_K1_ports": {"selected": selected, "all": ports}})
    return {"selected": selected, "all_K1_connection_indices": ports, "unique_count": len(set(ports))}


def validate_diagnostics(diagnostics: dict) -> tuple[dict, dict, float, float]:
    selected = {item["circuit_id"]: item for item in diagnostics["circuits"]
                if item["circuit_id"] in CHANGED_IDS}
    if set(selected) != set(CHANGED_IDS):
        raise RuntimeError("D183 C# diagnostics omitted an R03 route")
    for circuit_id, item in selected.items():
        required_true = [
            "grid_aligned", "continuous", "orthogonal", "completed", "start_at_collector", "end_at_collector",
            "heating_body_inside_assigned_room", "heating_body_placement_pass", "vertical_geometry_materialized",
            "vertical_transition_radius_feasible", "topology_pass", "pass", "engineering_pass",
        ]
        required_zero = [
            "self_intersections", "self_surface_clearance_violations", "inter_circuit_intersections",
            "inter_circuit_surface_clearance_violations", "heating_body_wall_intrusions",
            "horizontal_turn_wall_intrusions", "bend_radius_violation_count",
            "unmaterialized_elevation_change_count", "concealed_service_length_mm", "out_of_plane_length_mm",
        ]
        if any(not item[key] for key in required_true) or any(item[key] != 0 for key in required_zero):
            raise RuntimeError({"D183_CSharp_gate": {"circuit_id": circuit_id, "diagnostics": item}})
        if item["minimum_inter_circuit_surface_clearance_mm"] < 10.949:
            raise RuntimeError({"D183_surface_clearance": item["minimum_inter_circuit_surface_clearance_mm"]})
        close(EXPECTED_RAW_MM[circuit_id], item["axis_length_mm"], f"{circuit_id}_raw")
        close(EXPECTED_ROUNDED_MM[circuit_id], item["rounded_axis_length_mm"], f"{circuit_id}_rounded")
    raw = {key: selected[key]["axis_length_mm"] for key in CHANGED_IDS}
    rounded = {key: selected[key]["rounded_axis_length_mm"] for key in CHANGED_IDS}
    raw_spread = max(raw.values()) - min(raw.values())
    rounded_spread = max(rounded.values()) - min(rounded.values())
    close(EXPECTED_RAW_SPREAD_MM, raw_spread, "raw_spread")
    close(EXPECTED_ROUNDED_SPREAD_MM, rounded_spread, "rounded_spread")
    project_gates = {
        key: diagnostics[key] for key in [
            "total_concealed_service_length_mm", "total_out_of_plane_length_mm", "axis_only_circuit_count",
            "served_floor_references_pass", "materialized_heating_routes_pass",
            "installation_completeness_pass", "design_pass",
        ]
    }
    if project_gates != {
        "total_concealed_service_length_mm": 79_700,
        "total_out_of_plane_length_mm": 0,
        "axis_only_circuit_count": 3,
        "served_floor_references_pass": True,
        "materialized_heating_routes_pass": False,
        "installation_completeness_pass": False,
        "design_pass": False,
    }:
        raise RuntimeError({"D183_project_completeness": project_gates})
    return selected, {"raw_3d_axis_mm": raw, "physical_R80_rounded_axis_mm": rounded}, raw_spread, rounded_spread


def package_output(output: Path, package: Path) -> None:
    payloads = sorted(path for path in output.iterdir() if path.is_file() and path.name != "artifact_manifest.json")
    dump(output / "artifact_manifest.json", {
        "artifact_id": ARTIFACT_ID, "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in payloads],
    })
    package.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in [*payloads, output / "artifact_manifest.json"]:
            archive.write(path, path.name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="Freeze official append-only D183 output")
    parser.add_argument("--independent-audit-approved", action="store_true",
                        help="Required with --publish after the root receives an independent audit GO")
    parser.add_argument("--refresh-scaffold", action="store_true",
                        help="Refresh only the generator-owned prepublication scaffold")
    args = parser.parse_args()
    if args.publish and args.refresh_scaffold:
        raise RuntimeError("Cannot refresh a frozen official D183 output")
    if args.publish and not args.independent_audit_approved:
        raise RuntimeError("Official D183 publication requires the post-audit root GO")
    output = OFFICIAL_OUTPUT if args.publish else SCAFFOLD_OUTPUT
    package = OFFICIAL_PACKAGE if args.publish else SCAFFOLD_PACKAGE
    if (output.exists() or package.exists()) and not args.refresh_scaffold:
        raise FileExistsError(f"D183 target is append-only: {output}")
    if args.refresh_scaffold and not output.exists():
        raise FileNotFoundError("D183 scaffold refresh requested before scaffold creation")

    expected_hashes = {
        D181_PROJECT: D181_PROJECT_SHA, D181_CONTRACT: D181_CONTRACT_SHA,
        D182_CONTRACT: D182_CONTRACT_SHA, CANDIDATE: CANDIDATE_SHA,
        SCRATCH_DIAGNOSTICS: SCRATCH_DIAGNOSTICS_SHA, SCRATCH_ACCEPTANCE: SCRATCH_ACCEPTANCE_SHA,
    }
    for path, expected in expected_hashes.items():
        if sha(path) != expected:
            raise RuntimeError({"D183_source_hash_changed": {"path": str(path), "actual": sha(path), "expected": expected}})

    source = json.loads(D181_PROJECT.read_text(encoding="utf-8-sig"))
    project = json.loads(CANDIDATE.read_text(encoding="utf-8-sig"))
    d182 = json.loads(D182_CONTRACT.read_text(encoding="utf-8-sig"))
    acceptance = json.loads(SCRATCH_ACCEPTANCE.read_text(encoding="utf-8-sig"))
    if not acceptance["all_scratch_acceptance_gates_pass"]:
        raise RuntimeError("Authoritative scratch acceptance no longer passes")
    unchanged = validate_diff(source, project)
    specifications = circuit_specifications(project)
    identity = body_identity(specifications, d182)
    ports = validate_ports(project)
    sharp_walls = transit_wall_audit(project, specifications)
    endpoint_touches = sum(bool(item.get("terminal_segment")) for item in sharp_walls["records"])
    if not sharp_walls["pass"] or sharp_walls["intersection_count"] != 25 or endpoint_touches != 10:
        raise RuntimeError({"D183_wall_audit": sharp_walls, "endpoint_touch_count": endpoint_touches})
    tails = collector_tail_evidence(project, set(CHANGED_IDS))
    if len(tails["records"]) != 6 or tails["collector_continuous_route_count"] != 0 or \
            any(item["fabrication_tail_materialized"] for item in tails["records"]):
        raise RuntimeError({"D183_collector_tails": tails})

    output.mkdir(parents=True, exist_ok=args.refresh_scaffold)
    project_path = output / PROJECT_NAME
    project_path.write_bytes(CANDIDATE.read_bytes())
    diagnostics_path = output / "engineering_diagnostics.json"
    run_editor(project_path, diagnostics_path, "--export-diagnostics")
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8-sig"))
    selected_diagnostics, lengths, raw_spread, rounded_spread = validate_diagnostics(diagnostics)
    if sha(diagnostics_path) != SCRATCH_DIAGNOSTICS_SHA:
        raise RuntimeError({"D183_diagnostics_not_deterministic": sha(diagnostics_path)})

    coverage = d182["physical_body_metrics"]
    if abs(coverage["physical_round100_coverage_percent"] - 96.68922372440188) > 1e-12 or \
            coverage["maximum_sample_distance_mm"] != 200 or coverage["sample_over_200mm_count"] != 0:
        raise RuntimeError({"D183_D182_coverage": coverage})
    exterior = d182["exterior_3x100"]
    if exterior["WIN_04_percent_by_lane"] != [100.0, 100.0, 100.0] or \
            exterior["WIN_05_percent_by_lane"] != [100.0, 100.0, 100.0]:
        raise RuntimeError({"D183_exterior_window_gate": exterior})

    point3_ids = [
        circuit["id"] for circuit in project["circuits"]
        if circuit.get("system_role") == "FLOOR_HEATING_LOOP"
        and circuit.get("concealed_service_length_mm") == 0
        and circuit.get("out_of_plane_length_mm") == 0
        and circuit.get("ordered_points")
        and all("z_mm" in point for point in circuit["ordered_points"])
    ]
    if len(point3_ids) != 11:
        raise RuntimeError({"D183_bounded_terminal_grid_route_count": len(point3_ids)})

    publication_state = "OFFICIAL_APPEND_ONLY_D183" if args.publish else "PREPUBLICATION_SCAFFOLD_AWAITING_ROOT_GO"
    contract = {
        "schema": "homeaura.floor1.r03_point3_routes.v1",
        "artifact_id": ARTIFACT_ID,
        "status": "R03_C07_C09_POINT3_HARD_GATES_PASS_COLLECTOR_TAILS_DEFERRED",
        "publication_state": publication_state,
        "publishable": False,
        "publishable_as_installation_project": False,
        "terminal_grid_route_only": True,
        "physical_eurocone_tails_materialized": False,
        "append_only": True,
        "source_provenance": {
            "official_D181_project": {"path": str(D181_PROJECT.relative_to(ROOT)).replace("\\", "/"), "sha256": D181_PROJECT_SHA},
            "official_D181_contract": {"path": str(D181_CONTRACT.relative_to(ROOT)).replace("\\", "/"), "sha256": D181_CONTRACT_SHA},
            "official_D182_BODY_contract": {"path": str(D182_CONTRACT.relative_to(ROOT)).replace("\\", "/"), "sha256": D182_CONTRACT_SHA},
            "authoritative_forward_candidate": {"path": str(CANDIDATE.relative_to(ROOT)).replace("\\", "/"), "sha256": CANDIDATE_SHA},
            "authoritative_scratch_diagnostics": {"path": str(SCRATCH_DIAGNOSTICS.relative_to(ROOT)).replace("\\", "/"), "sha256": SCRATCH_DIAGNOSTICS_SHA},
            "authoritative_scratch_acceptance": {"path": str(SCRATCH_ACCEPTANCE.relative_to(ROOT)).replace("\\", "/"), "sha256": SCRATCH_ACCEPTANCE_SHA},
        },
        "append_only_diff_boundary": {
            "changed_circuit_ids": list(CHANGED_IDS), "unchanged_circuit_ids": unchanged,
            "unchanged_circuit_count": len(unchanged), "all_other_circuits_equal": True,
            "non_circuit_payload_equal": True,
        },
        "route_semantics": {
            "system_role": "FLOOR_HEATING_LOOP", "geometry": "CONTINUOUS_POINT3_TERMINAL_GRID_ROUTE",
            "concealed_service_length_mm": 0, "out_of_plane_length_mm": 0,
            "physical_Eurocone_tail_status": "DEFERRED_NOT_MATERIALIZED",
            "raw_3d_axis_is_physical_R80_rounded_axis": False,
        },
        "D182_BODY_identity": identity,
        "route_lengths": {
            **lengths,
            "raw_3d_axis_spread_mm": raw_spread,
            "physical_R80_rounded_axis_spread_mm": rounded_spread,
            "maximum_allowed_spread_mm": 2_000,
            "all_raw_and_rounded_lengths_40_to_80m": True,
        },
        "CSharp_route_gates": selected_diagnostics,
        "CSharp_project_completeness": {
            key: diagnostics[key] for key in [
                "total_concealed_service_length_mm", "total_out_of_plane_length_mm", "axis_only_circuit_count",
                "served_floor_references_pass", "materialized_heating_routes_pass",
                "installation_completeness_pass", "design_pass",
            ]
        },
        "custom_D182_BODY_coverage": {
            "method": "TRANSFERRED_ONLY_AFTER_EXACT_D182_PER_RANGE_BODY_SHA_MATCH",
            "physical_R80_axis_round100": {
                "served_area_m2": coverage["served_area_m2"],
                "served_percent": coverage["physical_round100_coverage_percent"],
                "sample_grid_mm": coverage["sample_grid_mm"], "sample_count": coverage["sample_count"],
                "maximum_sample_distance_mm": coverage["maximum_sample_distance_mm"],
                "sample_over_200mm_count": coverage["sample_over_200mm_count"],
            },
            "coverage_pass": True,
        },
        "exterior_3x100_and_windows": exterior,
        "sharp_wall_solid_transit_audit": {
            **sharp_walls, "endpoint_touch_records_included": True,
            "endpoint_touch_record_count": endpoint_touches,
        },
        "physical_R80_turn_wall_audit": {
            "method": "CSharp_ROUNDED_HORIZONTAL_TURN_WALL_AUDIT",
            "intrusion_count": sum(item["horizontal_turn_wall_intrusions"] for item in selected_diagnostics.values()),
            "pass": all(item["horizontal_turn_wall_intrusions"] == 0 for item in selected_diagnostics.values()),
        },
        "K1_port_ownership": ports,
        "collector_tail_evidence": tails,
        "bounded_terminal_grid_route_ids": point3_ids,
        "bounded_terminal_grid_route_count": 11,
        "materialized_floor_plane_route_count": 11,
        "complete_K1_route_count": 0,
        "collector_continuous_route_count": 0,
        "sleeves_added": False,
        "installation_ready": False,
        "remaining_blockers": [
            "terminal-grid-to-Eurocone XYZ fabrication tails are not materialized",
            "three inherited AXIS records and 79.7 m inherited concealed service remain",
            "ATTIC walls/openings/holes and all K2 routes remain unverified/unmaterialized",
            "hydraulic flow settings and pressure-loss calculation remain not evaluated",
        ],
        "next_block": "MATERIALIZE_A_DIFFERENT_BOUNDED_ROUTE_OR_VERIFY_ARCHITECTURE;_DO_NOT_INFER_EUROCONE_TAILS",
    }
    report = {
        "schema": "homeaura.floor1.r03_point3_routes.report.v1", "artifact_id": ARTIFACT_ID,
        "publication_state": publication_state, "route_lengths": contract["route_lengths"],
        "custom_D182_BODY_coverage": contract["custom_D182_BODY_coverage"],
        "exterior_3x100_and_windows": exterior,
        "sharp_wall_solid_transit_audit": contract["sharp_wall_solid_transit_audit"],
        "physical_R80_turn_wall_audit": contract["physical_R80_turn_wall_audit"],
        "collector_tail_evidence": tails, "CSharp_route_gates": selected_diagnostics,
    }
    dump(output / CONTRACT_NAME, contract)
    dump(output / "floor1_r03_point3_routes_report.json", report)
    dump(output / "status.json", {
        "artifact_id": ARTIFACT_ID, "result": contract["status"], "publication_state": publication_state,
        "publishable": False, "physical_eurocone_tails_materialized": False,
        "physical_R80_coverage_percent": coverage["physical_round100_coverage_percent"],
        "maximum_sample_distance_mm": coverage["maximum_sample_distance_mm"],
        "raw_3d_spread_mm": raw_spread, "physical_R80_rounded_spread_mm": rounded_spread,
        "wall_intersection_count_including_endpoint_touches": sharp_walls["intersection_count"],
        "bounded_terminal_grid_route_count": 11, "collector_continuous_route_count": 0,
        "installation_ready": False,
    })
    (output / "README.md").write_text(
        "# D183 · три непрерывных Point3-маршрута кухни-гостиной\n\n"
        "D183 изменяет относительно официального D181 только C07–C09. BODY полностью совпадает с "
        "проверенным D182; добавлены непрерывные многоуровневые TRANSIT-связи, не считающиеся отопительным покрытием. "
        "Все изменения высоты оформлены S-изгибами R80.\n\n"
        f"Физические R80-длины: {EXPECTED_ROUNDED_MM['F1-D171-C07']/1000:.3f} / "
        f"{EXPECTED_ROUNDED_MM['F1-D171-C08']/1000:.3f} / {EXPECTED_ROUNDED_MM['F1-D171-C09']/1000:.3f} м; "
        f"разброс {EXPECTED_ROUNDED_SPREAD_MM/1000:.3f} м. Покрытие BODY: "
        f"{coverage['physical_round100_coverage_percent']:.3f}%, максимум 200 мм, превышений нет. "
        "Все 25 касаний wall-solid, включая терминальные касания, принадлежат TRANSIT и перпендикулярны стенам.\n\n"
        "Физические XYZ-хвосты от терминальной сетки до Eurocone не материализованы. Поэтому коллекторно-непрерывных "
        "маршрутов и complete K1 routes по-прежнему 0; гильзы не добавлены; installation_ready=false.\n",
        encoding="utf-8",
    )
    temporary_root = ROOT / "tmp"
    temporary_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="D183_floor1_render_", dir=temporary_root) as temporary:
        render_project = Path(temporary) / "floor1_projection.homeaura.json"
        dump(render_project, floor1_render_projection(project))
        run_editor(render_project, output / "HomeAura_Floor1_D183_Clean_View.png", "--export-png-clean")
    run_editor(project_path, output / "HomeAura_Floor1_D183_R03_Clean_Zoom.png", "--export-room-png-clean", "F1-R03")
    run_editor(project_path, output / "HomeAura_Floor1_D183_R03_3D_Diagnostic.png", "--export-room-png-diagnostics", "F1-R03")
    package_output(output, package)
    print(json.dumps({
        "artifact": ARTIFACT_ID, "publication_state": publication_state, "output": str(output),
        "package": str(package), "project_sha256": sha(project_path), "package_sha256": sha(package),
        "raw_3d_axis_mm": lengths["raw_3d_axis_mm"],
        "physical_R80_rounded_axis_mm": lengths["physical_R80_rounded_axis_mm"],
        "physical_R80_rounded_spread_mm": rounded_spread,
        "coverage_percent": coverage["physical_round100_coverage_percent"],
        "wall_intersections_including_endpoint_touches": sharp_walls["intersection_count"],
        "bounded_terminal_grid_route_count": 11, "collector_continuous_route_count": 0,
        "installation_ready": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

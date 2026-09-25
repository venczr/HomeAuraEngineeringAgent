from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"

D183_DIRECTORY = PROPOSALS / "HA_TWO_FLOOR_R03_POINT3_ROUTES_183"
D183_PROJECT = D183_DIRECTORY / "HomeAura_TwoFloor_R03Point3Routes_D183.homeaura.json"
STRICT_BODY = ROOT / "tmp" / "reports" / "R07_Strict_Distributed_BODY_candidate.homeaura.json"
BODY_METRICS = ROOT / "tmp" / "reports" / "R07_Strict_Distributed_BODY_metrics.json"
CANDIDATE = ROOT / "tmp" / "r07_service_audit" / "candidate.homeaura.json"
FROZEN_AUDIT = ROOT / "tmp" / "r07_service_audit" / "frozen_audit.json"
CANDIDATE_DIAGNOSTICS = ROOT / "tmp" / "r07_service_audit" / "diagnostics.json"
INDEPENDENT_AUDIT = ROOT / "tmp" / "r07_point3" / "frozen_candidate_acceptance.json"
SECOND_INDEPENDENT_AUDIT = ROOT / "tmp" / "r07_service_audit" / "second_independent_audit.json"

OFFICIAL_OUTPUT = PROPOSALS / "HA_TWO_FLOOR_R07_POINT3_ROUTES_184"
OFFICIAL_PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_R07_POINT3_ROUTES_184.zip"
SCAFFOLD_OUTPUT = ROOT / "tmp" / "D184_scaffold"
SCAFFOLD_PACKAGE = ROOT / "tmp" / "HA_TWO_FLOOR_R07_POINT3_ROUTES_184_SCAFFOLD.zip"
ARTIFACT_ID = "HA_TWO_FLOOR_R07_POINT3_ROUTES_184"
PROJECT_NAME = "HomeAura_TwoFloor_R07Point3Routes_D184.homeaura.json"
CONTRACT_NAME = "floor1_r07_point3_routes_contract.json"
CHANGED_IDS = ("F1-D171-C03", "F1-D171-C04")

EXPECTED_HASHES = {
    D183_PROJECT: "E5096220BE3D2F7C93BC5F8B399A374C95556A9D4A29797445EDDC27835CDE4B",
    STRICT_BODY: "0D320A979A240D470E6C19ABE6D5475E315E74FC362B68EFDF17FD2F3899A676",
    BODY_METRICS: "51F53E5539ABAB810B05603D09C4D69173150E9CD73334FEFDF8B69203B53F32",
    CANDIDATE: "1A00E6B7539A0A704F1341BCCEB5982BB79B95F9520C4713D8791B573A511852",
    FROZEN_AUDIT: "EBD5C4BA52E99AC63489DFA3B171A3E71F1D34C375CF344C5081029E0FBF97AD",
    CANDIDATE_DIAGNOSTICS: "8C99ABC19A9A0021EFA80C50CA4078E0E4D6E316CB9D126874BDCAFED7F18312",
    INDEPENDENT_AUDIT: "FF15844F195E0C67DE743A2F9FF5696AEFE40661E1CDA4C4CBE2C574ABE6758A",
    SECOND_INDEPENDENT_AUDIT: "E6B938B383DD18918696D9AE43078C5667A1A394DB325176897362DC26A36E38",
}
EXPECTED_RAW_MM = {"F1-D171-C03": 49_710.734410204226, "F1-D171-C04": 51_710.734410204226}
EXPECTED_ROUNDED_MM = {"F1-D171-C03": 48_611.97300679916, "F1-D171-C04": 50_543.30041908634}
EXPECTED_RAW_SPREAD_MM = 2_000.0
EXPECTED_ROUNDED_SPREAD_MM = 1_931.3274122871808


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sha_payload(value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest().upper()


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


def floor1_projection(project: dict) -> dict:
    result = copy.deepcopy(project)
    result["levels"] = [item for item in result["levels"] if item["id"] == "FLOOR_1"]
    result["rooms"] = [item for item in result["rooms"] if item["floor_id"] == "FLOOR_1"]
    result["exclusions"] = [item for item in result["exclusions"] if item["floor_id"] == "FLOOR_1"]
    return result


def validate_diff(source: dict, project: dict) -> list[str]:
    source_by_id = {item["id"]: item for item in source["circuits"]}
    current_by_id = {item["id"]: item for item in project["circuits"]}
    if {key: value for key, value in source.items() if key != "circuits"} != \
            {key: value for key, value in project.items() if key != "circuits"}:
        raise RuntimeError("D184 changed non-circuit D183 payload")
    changed = sorted(item for item in source_by_id if source_by_id[item] != current_by_id[item])
    if changed != sorted(CHANGED_IDS):
        raise RuntimeError({"D184_changed_circuit_ids": changed})
    unchanged = sorted(set(source_by_id) - set(CHANGED_IDS))
    if any(source_by_id[item] != current_by_id[item] for item in unchanged):
        raise RuntimeError("D184 changed a preserved circuit")
    return unchanged


def validate_body_identity(project: dict, strict_body: dict) -> dict:
    current = {item["id"]: item for item in project["circuits"]}
    strict = {item["id"]: item for item in strict_body["circuits"]}
    result = {}
    for circuit_id in CHANGED_IDS:
        circuit = current[circuit_id]
        ranges = circuit["heating_body_ranges"]
        if len(ranges) != 1:
            raise RuntimeError({"D184_body_range_count": circuit_id})
        start, end = ranges[0]["start_index"], ranges[0]["end_index"]
        actual = circuit["ordered_points"][start:end + 1]
        expected = strict[circuit_id]["ordered_points"]
        if actual != expected or any(item.get("z_mm") != 108 for item in actual):
            raise RuntimeError({"D184_strict_BODY_identity": circuit_id})
        result[circuit_id] = {
            "range": [start, end], "point_count": len(actual),
            "strict_BODY_xyz_sha256": sha_payload(expected),
            "candidate_BODY_xyz_sha256": sha_payload(actual), "exact": True,
        }
    return result


def validate_ports(project: dict) -> dict:
    uses = []
    selected = {}
    for circuit in project["circuits"]:
        if circuit.get("collector_id") != "K1":
            continue
        pair = [circuit.get("supply_port_index"), circuit.get("return_port_index")]
        uses.extend(value for value in pair if value is not None)
        if circuit["id"] in CHANGED_IDS:
            selected[circuit["id"]] = pair
    expected = {"F1-D171-C03": [4, 5], "F1-D171-C04": [6, 7]}
    if selected != expected or sorted(uses) != list(range(28)) or len(uses) != len(set(uses)):
        raise RuntimeError({"D184_K1_ports": {"selected": selected, "all": sorted(uses)}})
    return {"selected": selected, "all_K1_connection_indices": sorted(uses), "unique_count": len(set(uses))}


def validate_diagnostics(diagnostics: dict) -> tuple[dict, dict, float, float, list[dict]]:
    selected = {item["circuit_id"]: item for item in diagnostics["circuits"] if item["circuit_id"] in CHANGED_IDS}
    if set(selected) != set(CHANGED_IDS):
        raise RuntimeError("D184 diagnostics omitted an R07 route")
    required_true = [
        "grid_aligned", "continuous", "orthogonal", "completed", "start_at_collector", "end_at_collector",
        "heating_body_inside_assigned_room", "heating_body_placement_pass", "vertical_geometry_materialized",
        "vertical_transition_radius_feasible", "bend_radius_feasible", "horizontal_turn_wall_clearance_pass",
        "topology_pass", "pass", "engineering_pass", "exterior3x100_useful_span_applicable",
        "exterior3x100_useful_span_pass",
    ]
    required_zero = [
        "self_intersections", "self_surface_clearance_violations", "inter_circuit_intersections",
        "inter_circuit_surface_clearance_violations", "heating_body_wall_intrusions",
        "horizontal_turn_wall_intrusions", "bend_radius_violation_count", "unmaterialized_elevation_change_count",
        "concealed_service_length_mm", "out_of_plane_length_mm",
    ]
    for circuit_id, item in selected.items():
        if any(not item[key] for key in required_true) or any(item[key] != 0 for key in required_zero):
            raise RuntimeError({"D184_CSharp_gate": {"circuit_id": circuit_id, "diagnostics": item}})
        if item["minimum_inter_circuit_surface_clearance_mm"] < 10.965:
            raise RuntimeError({"D184_surface_clearance": item["minimum_inter_circuit_surface_clearance_mm"]})
        close(EXPECTED_RAW_MM[circuit_id], item["axis_length_mm"], f"{circuit_id}_raw")
        close(EXPECTED_ROUNDED_MM[circuit_id], item["rounded_axis_length_mm"], f"{circuit_id}_rounded")
    raw = {key: selected[key]["axis_length_mm"] for key in CHANGED_IDS}
    rounded = {key: selected[key]["rounded_axis_length_mm"] for key in CHANGED_IDS}
    raw_spread = max(raw.values()) - min(raw.values())
    rounded_spread = max(rounded.values()) - min(rounded.values())
    close(EXPECTED_RAW_SPREAD_MM, raw_spread, "raw_spread")
    close(EXPECTED_ROUNDED_SPREAD_MM, rounded_spread, "rounded_spread")
    completeness = {key: diagnostics[key] for key in [
        "total_concealed_service_length_mm", "total_out_of_plane_length_mm", "axis_only_circuit_count",
        "served_floor_references_pass", "materialized_heating_routes_pass",
        "installation_completeness_pass", "design_pass",
    ]}
    expected_completeness = {
        "total_concealed_service_length_mm": 29_300, "total_out_of_plane_length_mm": 0,
        "axis_only_circuit_count": 1, "served_floor_references_pass": True,
        "materialized_heating_routes_pass": False, "installation_completeness_pass": False,
        "design_pass": False,
    }
    if completeness != expected_completeness:
        raise RuntimeError({"D184_project_completeness": completeness})
    useful = selected["F1-D171-C03"]["exterior_wall_band_useful_span_details"]
    if len(useful) != 3 or [item["window_coverage_percent"] for item in useful] != [100, 100, 100] or \
            not all(item["useful_span_pass"] for item in useful):
        raise RuntimeError({"D184_exterior_useful_span": useful})
    lane3 = useful[2]
    if lane3["useful_span_mode"] != "STAGGERED_ALTERNATING_TURNOUT" or \
            not lane3["staggered_turnout_pass"] or lane3["previous_lane_end_extension_mm"] != 100 or \
            lane3["aggregate_room_minimum_segment_length_mm"] != 200:
        raise RuntimeError({"D184_staggered_turnout": lane3})
    return selected, {"raw_3d_axis_mm": raw, "physical_R80_rounded_axis_mm": rounded}, raw_spread, rounded_spread, useful


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
    parser.add_argument("--publish", action="store_true", help="Freeze official append-only D184 output")
    parser.add_argument("--independent-audit-approved", action="store_true",
                        help="Required with --publish after root receives independent GO")
    parser.add_argument("--refresh-scaffold", action="store_true")
    args = parser.parse_args()
    if args.publish and args.refresh_scaffold:
        raise RuntimeError("Cannot refresh a frozen official D184 output")
    if args.publish and not args.independent_audit_approved:
        raise RuntimeError("Official D184 publication requires explicit post-audit root approval")
    output = OFFICIAL_OUTPUT if args.publish else SCAFFOLD_OUTPUT
    package = OFFICIAL_PACKAGE if args.publish else SCAFFOLD_PACKAGE
    if output.exists() or package.exists():
        if not args.refresh_scaffold or args.publish:
            raise FileExistsError(f"D184 target is append-only: {output}")
        if output.exists():
            shutil.rmtree(output)
        if package.exists():
            package.unlink()

    for path, expected in EXPECTED_HASHES.items():
        actual = sha(path)
        if actual != expected:
            raise RuntimeError({"D184_source_hash_changed": {"path": str(path), "actual": actual, "expected": expected}})
    source = json.loads(D183_PROJECT.read_text(encoding="utf-8-sig"))
    strict_body = json.loads(STRICT_BODY.read_text(encoding="utf-8-sig"))
    project = json.loads(CANDIDATE.read_text(encoding="utf-8-sig"))
    body_metrics = json.loads(BODY_METRICS.read_text(encoding="utf-8-sig"))
    frozen_audit = json.loads(FROZEN_AUDIT.read_text(encoding="utf-8-sig"))
    independent = json.loads(INDEPENDENT_AUDIT.read_text(encoding="utf-8-sig"))
    second_independent = json.loads(SECOND_INDEPENDENT_AUDIT.read_text(encoding="utf-8-sig"))
    if frozen_audit["status"] != "READ_ONLY_PREFLIGHT_PASS" or \
            independent["status"] != "INDEPENDENT_GO" or not independent["all_independent_audit_gates_pass"] or \
            independent["candidate_under_audit"]["sha256"] != EXPECTED_HASHES[CANDIDATE] or \
            second_independent["status"] != "SECOND_INDEPENDENT_GO_BOUNDED_TERMINAL_GRID" or \
            not all(second_independent["gates"].values()):
        raise RuntimeError("D184 frozen independent source approval is absent")
    unchanged = validate_diff(source, project)
    identity = validate_body_identity(project, strict_body)
    ports = validate_ports(project)

    # These two audits are generated independently and frozen by exact SHA; D184 also regenerates native diagnostics.
    walls = independent["wall_crossing_audit"]
    bundle = independent["global_same_layer_bundle_audit"]
    tails = independent["collector_terminal_XYZ_gap_evidence"]
    if not walls["pass"] or walls["intersection_count"] != 12 or walls["body_wall_hit_count"] != 0 or \
            walls["longitudinal_or_nonperpendicular_transit_count"] != 0:
        raise RuntimeError({"D184_wall_audit": walls})
    if not bundle["all_groups_at_most_three_pipes"] or bundle["maximum_pipe_axes_in_any_group_window"] != 3:
        raise RuntimeError({"D184_transit_bundle": bundle})
    if len(tails["records"]) != 4 or tails["collector_continuous_route_count"] != 0 or \
            any(item["fabrication_tail_materialized"] for item in tails["records"]):
        raise RuntimeError({"D184_collector_tails": tails})

    output.mkdir(parents=True)
    project_path = output / PROJECT_NAME
    project_path.write_bytes(CANDIDATE.read_bytes())
    diagnostics_path = output / "engineering_diagnostics.json"
    run_editor(project_path, diagnostics_path, "--export-diagnostics")
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8-sig"))
    selected, lengths, raw_spread, rounded_spread, useful = validate_diagnostics(diagnostics)
    if sha(diagnostics_path) != EXPECTED_HASHES[CANDIDATE_DIAGNOSTICS]:
        raise RuntimeError({"D184_diagnostics_not_deterministic": sha(diagnostics_path)})

    point3_ids = [
        circuit["id"] for circuit in project["circuits"]
        if circuit.get("system_role") == "FLOOR_HEATING_LOOP"
        and circuit.get("concealed_service_length_mm") == 0
        and circuit.get("out_of_plane_length_mm") == 0
        and circuit.get("ordered_points")
        and all("z_mm" in point for point in circuit["ordered_points"])
    ]
    if len(point3_ids) != 13:
        raise RuntimeError({"D184_bounded_terminal_grid_route_count": len(point3_ids)})
    coverage = body_metrics["coverage_physical_R80_axis_round100"]["q16"]
    close(96.26167789144965, coverage["served_percent"], "coverage", 1e-12)
    if coverage["maximum_sample_distance_mm"] != 200 or coverage["sample_over_200mm_count"] != 0:
        raise RuntimeError({"D184_coverage": coverage})

    publication_state = "OFFICIAL_APPEND_ONLY_D184" if args.publish else "PREPUBLICATION_SCAFFOLD_AWAITING_ROOT_GO"
    contract = {
        "schema": "homeaura.floor1.r07_point3_routes.v1", "artifact_id": ARTIFACT_ID,
        "status": "R07_C03_C04_POINT3_HARD_GATES_PASS_COLLECTOR_TAILS_DEFERRED",
        "publication_state": publication_state, "append_only": True,
        "publishable": False, "publishable_as_installation_project": False,
        "terminal_grid_route_only": True, "physical_eurocone_tails_materialized": False,
        "source_provenance": {
            "official_D183_project": {"path": str(D183_PROJECT.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_HASHES[D183_PROJECT]},
            "strict_R07_BODY": {"path": str(STRICT_BODY.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_HASHES[STRICT_BODY]},
            "strict_R07_BODY_metrics": {"path": str(BODY_METRICS.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_HASHES[BODY_METRICS]},
            "frozen_Point3_candidate": {"path": str(CANDIDATE.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_HASHES[CANDIDATE]},
            "frozen_service_audit": {"path": str(FROZEN_AUDIT.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_HASHES[FROZEN_AUDIT]},
            "independent_GO": {"path": str(INDEPENDENT_AUDIT.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_HASHES[INDEPENDENT_AUDIT]},
            "second_independent_GO": {"path": str(SECOND_INDEPENDENT_AUDIT.relative_to(ROOT)).replace("\\", "/"), "sha256": EXPECTED_HASHES[SECOND_INDEPENDENT_AUDIT]},
        },
        "append_only_diff_boundary": {
            "changed_circuit_ids": list(CHANGED_IDS), "unchanged_circuit_ids": unchanged,
            "unchanged_circuit_count": len(unchanged), "all_other_circuits_equal": True,
            "non_circuit_payload_equal": True,
        },
        "route_semantics": {
            "system_role": "FLOOR_HEATING_LOOP", "geometry": "CONTINUOUS_POINT3_TERMINAL_GRID_ROUTE",
            "body_axis_elevation_mm": 108, "transit_axis_elevations_mm": [135],
            "concealed_service_length_mm": 0, "out_of_plane_length_mm": 0,
            "physical_Eurocone_tail_status": "DEFERRED_NOT_MATERIALIZED",
        },
        "strict_R07_BODY_identity": identity,
        "route_lengths": {**lengths, "raw_3d_axis_spread_mm": raw_spread,
                          "physical_R80_rounded_axis_spread_mm": rounded_spread,
                          "maximum_allowed_spread_mm": 2_000,
                          "all_raw_and_rounded_lengths_40_to_80m": True},
        "CSharp_route_gates": selected,
        "CSharp_project_completeness": {key: diagnostics[key] for key in [
            "total_concealed_service_length_mm", "total_out_of_plane_length_mm", "axis_only_circuit_count",
            "served_floor_references_pass", "materialized_heating_routes_pass",
            "installation_completeness_pass", "design_pass",
        ]},
        "custom_R07_BODY_coverage": {
            "method": "TRANSFERRED_ONLY_AFTER_EXACT_STRICT_BODY_POINT_IDENTITY",
            "physical_R80_axis_round100_q16": {
                "served_area_m2": coverage["served_area_m2"], "served_percent": coverage["served_percent"],
                "sample_grid_mm": coverage["sample_grid_mm"], "sample_count": coverage["sample_count"],
                "maximum_sample_distance_mm": coverage["maximum_sample_distance_mm"],
                "sample_over_200mm_count": coverage["sample_over_200mm_count"],
            }, "coverage_pass": True,
        },
        "exterior_3x100_useful_span": {
            "wall_id": "FLOOR_1-W008", "window_id": "F1-WIN-02",
            "lane_coverage_percent": [item["coverage_percent"] for item in useful],
            "window_coverage_percent": [item["window_coverage_percent"] for item in useful],
            "lane_modes": [item["useful_span_mode"] for item in useful],
            "staggered_lane_3": useful[2], "all_useful_span_pass": True,
            "legacy_raw_exterior3x100_pass": False,
        },
        "sharp_wall_solid_transit_audit": walls,
        "global_same_layer_transit_bundle_audit": bundle,
        "collector_tail_evidence": tails,
        "ports": ports,
        "bounded_terminal_grid_route_count": 13, "complete_K1_route_count": 0,
        "collector_continuous_route_count": 0, "remaining_axis_only_circuit_ids": ["F1-D171-C12"],
        "sleeves_added": False, "installation_ready": False,
        "independent_audit": {"status": "GO", "sha256": EXPECTED_HASHES[INDEPENDENT_AUDIT],
                              "second_status": "GO", "second_sha256": EXPECTED_HASHES[SECOND_INDEPENDENT_AUDIT]},
        "known_limitations": [
            "four physical terminal-grid-to-Eurocone XYZ fabrication tails remain unmaterialized",
            "C12 remains an inherited FLOOR_HEATING_AXIS with concealed service proxy",
            "hydraulic flow settings and pressure-loss calculation remain not evaluated",
        ],
        "next_block": "MATERIALIZE_F1_C12_POINT3_WITHOUT_INFERRING_EUROCONE_TAILS",
    }
    report = {
        "schema": "homeaura.floor1.r07_point3_routes.report.v1", "artifact_id": ARTIFACT_ID,
        "publication_state": publication_state, "route_lengths": contract["route_lengths"],
        "custom_R07_BODY_coverage": contract["custom_R07_BODY_coverage"],
        "exterior_3x100_useful_span": contract["exterior_3x100_useful_span"],
        "sharp_wall_solid_transit_audit": walls,
        "global_same_layer_transit_bundle_audit": bundle,
        "collector_tail_evidence": tails, "CSharp_route_gates": selected,
    }
    dump(output / CONTRACT_NAME, contract)
    dump(output / "floor1_r07_point3_routes_report.json", report)
    dump(output / "status.json", {
        "artifact_id": ARTIFACT_ID, "result": contract["status"], "publication_state": publication_state,
        "publishable": False, "physical_eurocone_tails_materialized": False,
        "physical_R80_coverage_percent": coverage["served_percent"],
        "maximum_sample_distance_mm": coverage["maximum_sample_distance_mm"],
        "raw_3d_spread_mm": raw_spread, "physical_R80_rounded_spread_mm": rounded_spread,
        "wall_intersection_count": walls["intersection_count"],
        "maximum_same_layer_pipe_axes_in_300mm_window": bundle["maximum_pipe_axes_in_any_group_window"],
        "bounded_terminal_grid_route_count": 13, "axis_only_circuit_count": 1,
        "collector_continuous_route_count": 0, "installation_ready": False,
    })
    (output / "README.md").write_text(
        "# D184 · два непрерывных Point3-маршрута комнаты R07\n\n"
        "D184 изменяет относительно официального D183 только C03 и C04. Их BODY дословно совпадает со строгой "
        "проверенной R07-парой: три оси по 100 мм у W008/WIN02, далее согласованное поле и компактное заполнение центра. "
        "Через стены проходят только TRANSIT; все изменения высоты оформлены S-изгибами R80.\n\n"
        f"Физические R80-длины: {EXPECTED_ROUNDED_MM['F1-D171-C03']/1000:.3f} / "
        f"{EXPECTED_ROUNDED_MM['F1-D171-C04']/1000:.3f} м; разброс {EXPECTED_ROUNDED_SPREAD_MM/1000:.3f} м. "
        f"Покрытие BODY: {coverage['served_percent']:.3f}%, максимум 200 мм, превышений нет. "
        "Все 12 касаний wall-solid принадлежат TRANSIT и перпендикулярны стенам; в одном 300-мм окне не более трёх осей.\n\n"
        "Физические XYZ-хвосты до Eurocone не материализованы. Поэтому collector_continuous=0, complete_K1=0, "
        "гильзы не добавлены и installation_ready=false. Последним AXIS на первом этаже остаётся C12.\n",
        encoding="utf-8",
    )
    with tempfile.TemporaryDirectory(prefix="D184_floor1_render_", dir=ROOT / "tmp") as temporary:
        render_project = Path(temporary) / "floor1_projection.homeaura.json"
        dump(render_project, floor1_projection(project))
        run_editor(render_project, output / "HomeAura_Floor1_D184_Clean_View.png", "--export-png-clean")
    run_editor(project_path, output / "HomeAura_Floor1_D184_R07_Clean_Zoom.png", "--export-room-png-clean", "F1-R07")
    run_editor(project_path, output / "HomeAura_Floor1_D184_R07_3D_Diagnostic.png", "--export-room-png-diagnostics", "F1-R07")
    package_output(output, package)
    print(json.dumps({
        "artifact": ARTIFACT_ID, "publication_state": publication_state, "output": str(output),
        "package": str(package), "project_sha256": sha(project_path), "package_sha256": sha(package),
        "physical_R80_rounded_axis_mm": lengths["physical_R80_rounded_axis_mm"],
        "physical_R80_rounded_spread_mm": rounded_spread, "coverage_percent": coverage["served_percent"],
        "wall_intersections": walls["intersection_count"],
        "maximum_same_layer_pipe_axes_in_300mm_window": bundle["maximum_pipe_axes_in_any_group_window"],
        "bounded_terminal_grid_route_count": 13, "axis_only_circuit_count": 1,
        "collector_continuous_route_count": 0, "installation_ready": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

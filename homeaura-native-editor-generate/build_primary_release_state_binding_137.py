import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
RUNTIME_RESULTS = Path.home() / "AppData" / "Local" / "HomeAuraMultiAgent" / "results"
SOURCES = {
    "D125": BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_AAC_CROSSINGS_125" / "floor_primary_aac_crossings.json",
    "D132": BASE / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ASBUILT_PULL_GATE_132" / "primary_openings_asbuilt_pull_gate.json",
    "D134": BASE / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ACCEPTANCE_CRITERIA_134" / "primary_openings_acceptance_criteria.json",
    "D135": BASE / "HA_TWO_FLOOR_PRIMARY_BEND_METHOD_EVIDENCE_135" / "primary_bend_method_evidence.json",
    "D136": BASE / "HA_TWO_FLOOR_PRIMARY_ACCEPTANCE_BEND_CLARIFICATION_136" / "primary_acceptance_bend_clarification.json",
}
CLOUD_RESULTS = {
    "claude": RUNTIME_RESULTS / "HA-D136-FINAL-CLAUDE-20260813-001.json",
    "kimi": RUNTIME_RESULTS / "HA-D136-FINAL-KIMI-20260813-001.json",
}
OUTPUT = BASE / "HA_TWO_FLOOR_PRIMARY_RELEASE_STATE_BINDING_137"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_PRIMARY_RELEASE_STATE_BINDING_137.zip"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists() or PACKAGE.with_suffix(PACKAGE.suffix + ".sha256").exists():
        raise SystemExit("append-only target already exists")

    models = {key: json.loads(path.read_text(encoding="utf8")) for key, path in SOURCES.items()}
    reviews = {key: json.loads(path.read_text(encoding="utf8")) for key, path in CLOUD_RESULTS.items()}
    for key, review in reviews.items():
        if review["status"] != "COMPLETED" or review["exit_code"] != 0 or review["timed_out"]:
            raise SystemExit(f"{key} D136 audit is not a completed successful result")

    d125, d132, d134, d135, d136 = (models[key] for key in ("D125", "D132", "D134", "D135", "D136"))
    digest_fields = {
        "D125": "aac_crossing_digest",
        "D132": "pull_gate_digest",
        "D134": "acceptance_criteria_digest",
        "D135": "bend_method_evidence_digest",
        "D136": "clarification_digest",
    }
    source_records = [
        {
            "source_key": key,
            "artifact_id": models[key]["artifact_id"],
            "file_sha256": sha(SOURCES[key]),
            "canonical_model_digest": models[key][digest_fields[key]],
            "canonical_model_digest_field": digest_fields[key],
        }
        for key in SOURCES
    ]

    readiness_inputs = {
        "openings": d136["authoritative_opening_acceptance_records"],
        "p01": {
            **d136["P01_orientation_screening_preserved"],
            "pitch_offset_axis": None,
        },
        "floor_buildups": d136["per_floor_owner_statement_depth_screening"],
        "required_cover_above_envelope_mm": None,
        "required_annulus_per_primary_mm": None,
        "bend": {
            "owner_directed_radius_mm": d135["owner_directed_radius_mm"],
            "bend_method": None,
            "bend_radius_definition": None,
            "official_minimum_bending_radii_mm": d135["official_minimum_bending_radii_mm"],
            "selected_allowed_method_candidate": d135["selected_allowed_method_candidate"],
            "selected_tool_part_number_candidate": d135["selected_tool_part_number_candidate"],
            "selected_segment_part_number_candidate": d135["selected_segment_part_number_candidate"],
            "tool_and_segment_procured_and_field_verified": False,
            "factory_insulation_bend_method": None,
            "factory_insulation_bend_method_verified": False,
            "actual_pipe_product_code": None,
            "actual_pipe_product_code_verified": False,
            "field_acceptance_inputs": d135["field_acceptance_inputs"],
        },
        "direction_change": {
            "D125_policy": d125["primary_direction_change_policy"],
            "reconciled_with_D135_bend_candidate": False,
            "accessible_locations_and_tangent_lengths": None,
        },
        "pull_method_statement": None,
        "label_and_cap_record": None,
        "accessible_bend_record": None,
        "selected_pressure_test_procedure": None,
        "pressure_test_parameters_selected": False,
    }

    gates = [
        {
            "gate_id": "G01_AS_BUILT_OPENING_RECORDS",
            "inputs_required": [
                "readiness_inputs.openings[].as_built_dimensions_verified",
                "readiness_inputs.openings[].face_records[]",
                "readiness_inputs.openings[].photo_evidence_paths[]",
            ],
            "evaluated": False,
            "passes": None,
        },
        {
            "gate_id": "G02_STRUCTURAL_AND_WALL_DISPOSITION",
            "inputs_required": ["readiness_inputs.openings[].structural_or_wall_disposition_verified"],
            "evaluated": False,
            "passes": None,
        },
        {
            "gate_id": "G03_SLEEVE_EDGE_CLOSEOUT_SYSTEM",
            "inputs_required": [
                "readiness_inputs.openings[].per_primary_records[].sleeve_or_tested_common_system_selected",
                "readiness_inputs.openings[].per_primary_records[].edge_protection_verified",
                "readiness_inputs.openings[].per_primary_records[].annulus_clear_mm",
                "readiness_inputs.openings[].per_primary_records[].closeout_system_selected",
                "readiness_inputs.openings[].per_primary_records[].closeout_system_id",
                "readiness_inputs.required_annulus_per_primary_mm",
            ],
            "evaluated": False,
            "passes": None,
        },
        {
            "gate_id": "G04_CONTINUOUS_PIPE_AND_ACCESSIBLE_FITTINGS",
            "inputs_required": [
                "readiness_inputs.p01.pitch_offset_axis",
                "readiness_inputs.floor_buildups[].pipe_containing_layer",
                "readiness_inputs.floor_buildups[].required_cover_above_envelope_mm",
                "readiness_inputs.required_cover_above_envelope_mm",
                "readiness_inputs.bend.bend_method",
                "readiness_inputs.bend.bend_radius_definition",
                "readiness_inputs.bend.actual_pipe_product_code",
                "readiness_inputs.bend.tool_and_segment_procured_and_field_verified",
                "readiness_inputs.bend.factory_insulation_bend_method",
                "readiness_inputs.bend.field_acceptance_inputs[]",
                "readiness_inputs.direction_change.reconciled_with_D135_bend_candidate",
                "readiness_inputs.direction_change.accessible_locations_and_tangent_lengths",
            ],
            "evaluated": False,
            "passes": None,
        },
        {
            "gate_id": "G05_LABEL_CAP_AND_PULL_METHOD",
            "inputs_required": [
                "readiness_inputs.pull_method_statement",
                "readiness_inputs.label_and_cap_record",
                "readiness_inputs.accessible_bend_record",
                "readiness_inputs.selected_pressure_test_procedure",
                "readiness_inputs.pressure_test_parameters_selected",
            ],
            "evaluated": False,
            "passes": None,
        },
    ]
    gate_ids = [gate["gate_id"] for gate in gates]
    assert gate_ids == [gate["gate_id"] for gate in d132["pull_release_gates"]]
    assert all(path.startswith("readiness_inputs.") for gate in gates for path in gate["inputs_required"])

    record = {
        "schema": "homeaura-primary-release-state-binding-0.1",
        "artifact_id": "HA_TWO_FLOOR_PRIMARY_RELEASE_STATE_BINDING_137",
        "status": "SELF_CONTAINED_RELEASE_STATE_BINDING_PASS_PHYSICAL_RELEASE_REMAINS_FALSE",
        "source_records": source_records,
        "digest_contract": {
            "algorithm": "SHA256_OVER_UTF8_JSON_SORT_KEYS_COMPACT_EXCLUDING_DIGEST_FIELD",
            "source_digest_fields": {key: digest_fields[key] for key in digest_fields},
            "D137_digest_field": "release_state_binding_digest",
        },
        "D136_final_read_only_audits": [
            {
                "agent": key,
                "task_id": review["task_id"],
                "task_sha256": review["task_sha256"].upper(),
                "status": review["status"],
                "exit_code": review["exit_code"],
                "timed_out": review["timed_out"],
                "stdout_sha256": review["stdout_sha256"].upper(),
            }
            for key, review in reviews.items()
        ],
        "D136_findings_disposition": {
            "M1_unresolvable_input_paths": "RESOLVED_BY_SELF_CONTAINED_READINESS_INPUTS",
            "M2_superseded_state_machine_gate_ids": "RESOLVED_BY_REPUBLISHED_D137_STATE_MACHINE",
            "D136_geometry_preserved": True,
            "D136_release_decision_preserved": True,
        },
        "readiness_inputs": readiness_inputs,
        "authoritative_pull_release_gates": gates,
        "authoritative_pull_release_gate_count": len(gates),
        "evaluated_gate_count": 0,
        "passed_gate_count": 0,
        "all_pull_release_gates_pass": False,
        "state_machine": {
            "states": ["S_PREPARATION", "S_PULL_RELEASE", "S_PRESSURE_TEST", "S_CLOSEOUT"],
            "current_state": "S_PREPARATION",
            "D134_state_machine_gate_ids_superseded": True,
            "pressure_test_precedes_closeout": True,
            "transitions": [
                {"from": "S_PREPARATION", "to": "S_PULL_RELEASE", "required_gate_ids": gate_ids},
                {"from": "S_PULL_RELEASE", "to": "S_PRESSURE_TEST", "required_record": "PIPE_INSTALLED_AND_VISIBLE"},
                {"from": "S_PRESSURE_TEST", "to": "S_CLOSEOUT", "required_record": "PRESSURE_TEST_ACCEPTED"},
            ],
        },
        "stop_conditions": list(dict.fromkeys(d134["stop_conditions"] + d136["stop_conditions_added"])),
        "source_access_date_semantics": {
            "D136_accessed_date_value": "2026-08-13",
            "status": "RECORDED_AT_D136_GENERATION_NOT_PRESENT_IN_D135",
        },
        "new_route_coordinate_count": 0,
        "approved_bend_geometry_count": 0,
        "approved_pipe_geometry_count": 0,
        "pipe_bending_authorized": False,
        "pipe_pull_authorized": False,
        "penetration_closeout_authorized": False,
        "construction_authorized": False,
        "physical_release_status": "NOT_RELEASED",
        "result": "PASS_SELF_CONTAINED_BINDING_REWORK_FIELD_INPUTS_AND_PHYSICAL_RELEASE",
    }
    record["release_state_binding_digest"] = digest(record)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "primary_release_state_binding.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf8"
    )
    (OUTPUT / "binding_note.md").write_text(
        "# D137 — самодостаточная привязка шлюзов к состоянию протяжки\n\n"
        "Все обязательные входы пяти шлюзов теперь находятся внутри одного объекта `readiness_inputs`; "
        "переход `S_PREPARATION → S_PULL_RELEASE` использует исходные идентификаторы D132. "
        "Неизвестные размеры, защитный слой, заделка, определение R80, фактическая труба, инструмент, "
        "изоляция и метод испытания остаются незаполненными. Поэтому гибка, протяжка, заделка и строительство не разрешены.\n",
        encoding="utf8",
    )
    files = sorted(path for path in OUTPUT.iterdir() if path.is_file())
    manifest = {
        "artifact_id": record["artifact_id"],
        "release_state_binding_digest": record["release_state_binding_digest"],
        "append_only": True,
        "manifest_self_hash_excluded_by_design": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8"
    )
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    PACKAGE.with_suffix(PACKAGE.suffix + ".sha256").write_text(sha(PACKAGE) + "\n", encoding="ascii")
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "digest": record["release_state_binding_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
RUNTIME_RESULTS = Path.home() / "AppData" / "Local" / "HomeAuraMultiAgent" / "results"
SOURCE_134 = BASE / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ACCEPTANCE_CRITERIA_134" / "primary_openings_acceptance_criteria.json"
SOURCE_135 = BASE / "HA_TWO_FLOOR_PRIMARY_BEND_METHOD_EVIDENCE_135" / "primary_bend_method_evidence.json"
SOURCE_132 = BASE / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ASBUILT_PULL_GATE_132" / "primary_openings_asbuilt_pull_gate.json"
SOURCE_125 = BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_AAC_CROSSINGS_125" / "floor_primary_aac_crossings.json"
PACKAGE_134 = BASE / "packages" / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ACCEPTANCE_CRITERIA_134.zip"
PACKAGE_135 = BASE / "packages" / "HA_TWO_FLOOR_PRIMARY_BEND_METHOD_EVIDENCE_135.zip"
CLOUD_RESULTS = {
    "claude": RUNTIME_RESULTS / "HA-D134-D135-FINAL-CLAUDE-20260813-001.json",
    "kimi": RUNTIME_RESULTS / "HA-D134-D135-FINAL-KIMI-20260813-001.json",
}
OUTPUT = BASE / "HA_TWO_FLOOR_PRIMARY_ACCEPTANCE_BEND_CLARIFICATION_136"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_PRIMARY_ACCEPTANCE_BEND_CLARIFICATION_136.zip"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise SystemExit("append-only target already exists")

    d125 = json.loads(SOURCE_125.read_text(encoding="utf8"))
    d132 = json.loads(SOURCE_132.read_text(encoding="utf8"))
    d134 = json.loads(SOURCE_134.read_text(encoding="utf8"))
    d135 = json.loads(SOURCE_135.read_text(encoding="utf8"))
    reviews = {key: json.loads(path.read_text(encoding="utf8")) for key, path in CLOUD_RESULTS.items()}
    for key, review in reviews.items():
        if review["status"] != "COMPLETED" or review["exit_code"] != 0 or review["timed_out"]:
            raise SystemExit(f"{key} final audit is not a completed successful result")

    d134_file_sha = sha(SOURCE_134)
    d135_file_sha = sha(SOURCE_135)
    d134_canonical_digest = d134["acceptance_criteria_digest"]
    d135_canonical_digest = d135["bend_method_evidence_digest"]
    d135_d134_source_sha = next(
        source["sha256"]
        for source in d135["source_records"]
        if source["artifact_id"] == d134["artifact_id"]
    )
    assert d135_d134_source_sha == d134_file_sha
    assert d135_d134_source_sha != d134_canonical_digest

    source_gate_ids = [gate["gate_id"] for gate in d132["pull_release_gates"]]
    d134_gate_ids = [gate["gate_id"] for gate in d134["pull_release_gates"]]
    superseded_gate_map = [
        {
            "D132_gate_id": source_gate_id,
            "D134_gate_id": d134_gate_id,
            "D136_authoritative_gate_id": source_gate_id,
        }
        for source_gate_id, d134_gate_id in zip(source_gate_ids, d134_gate_ids)
    ]
    authoritative_gates = [
        {
            "gate_id": "G01_AS_BUILT_OPENING_RECORDS",
            "inputs_required": [
                "openings[].as_built_*",
                "openings[].face_records[]",
                "openings[].photo_evidence_paths[]",
            ],
            "evaluated": False,
            "passes": None,
        },
        {
            "gate_id": "G02_STRUCTURAL_AND_WALL_DISPOSITION",
            "inputs_required": ["openings[].structural_or_wall_disposition_verified"],
            "evaluated": False,
            "passes": None,
        },
        {
            "gate_id": "G03_SLEEVE_EDGE_CLOSEOUT_SYSTEM",
            "inputs_required": [
                "openings[].per_primary_records[].sleeve_or_tested_common_system_selected",
                "openings[].per_primary_records[].edge_protection_verified",
                "openings[].per_primary_records[].annulus_clear_mm",
                "openings[].per_primary_records[].closeout_system_selected",
                "openings[].per_primary_records[].closeout_system_id",
                "required_annulus_per_primary_mm",
            ],
            "evaluated": False,
            "passes": None,
        },
        {
            "gate_id": "G04_CONTINUOUS_PIPE_AND_ACCESSIBLE_FITTINGS",
            "inputs_required": [
                "p01_orientation_screening.pitch_offset_axis",
                "owner_stated_inputs.floor_buildups[].pipe_containing_layer",
                "owner_stated_inputs.floor_buildups[].required_cover_above_envelope_mm",
                "derived_envelope_screening.required_cover_above_envelope_mm",
                "owner_stated_inputs.bend_method",
                "owner_stated_inputs.bend_radius_definition",
                "D135.field_acceptance_inputs[]",
                "D125.primary_direction_change_policy",
            ],
            "evaluated": False,
            "passes": None,
        },
        {
            "gate_id": "G05_LABEL_CAP_AND_PULL_METHOD",
            "inputs_required": [
                "pull_method_statement",
                "label_and_cap_record",
                "accessible_bend_record",
                "selected_pressure_test_procedure",
            ],
            "evaluated": False,
            "passes": None,
        },
    ]

    authoritative_openings = json.loads(json.dumps(d134["openings"]))
    for opening in authoritative_openings:
        for primary in opening["per_primary_records"]:
            primary["closeout_system_selected"] = False
            primary["closeout_system_id"] = None

    per_floor_depth_screen = []
    envelope = d134["derived_envelope_screening"]["coordination_envelope_od_mm"]
    comparison = d134["derived_envelope_screening"]["comparison_insulated_od_mm"]
    for floor in d134["owner_stated_inputs"]["floor_buildups"]:
        remaining = floor["remaining_available_depth_mm"]
        per_floor_depth_screen.append(
            {
                "floor_buildup_id": floor["buildup_id"],
                "installed_insulation_mm_owner_statement": floor["installed_insulation_mm"],
                "remaining_available_depth_mm_owner_statement": remaining,
                "remaining_minus_coordination_envelope_mm": remaining - envelope,
                "remaining_minus_comparison_insulated_od_mm": remaining - comparison,
                "applicable_opening_face_ids": [],
                "pipe_containing_layer": floor["pipe_containing_layer"],
                "required_cover_above_envelope_mm": floor["required_cover_above_envelope_mm"],
                "as_built_face_adequacy_evaluated": False,
                "adequacy_claimed": False,
            }
        )

    record = {
        "schema": "homeaura-primary-acceptance-bend-clarification-0.1",
        "artifact_id": "HA_TWO_FLOOR_PRIMARY_ACCEPTANCE_BEND_CLARIFICATION_136",
        "status": "EVIDENCE_SCOPE_AND_HASH_SEMANTICS_CLARIFIED_PHYSICAL_RELEASE_REMAINS_FALSE",
        "source_records": [
            {
                "artifact_id": d125["artifact_id"],
                "file_sha256": sha(SOURCE_125),
                "canonical_model_digest": d125["aac_crossing_digest"],
                "canonical_model_digest_field": "aac_crossing_digest",
            },
            {
                "artifact_id": d132["artifact_id"],
                "file_sha256": sha(SOURCE_132),
                "canonical_model_digest": d132["pull_gate_digest"],
                "canonical_model_digest_field": "pull_gate_digest",
            },
            {
                "artifact_id": d134["artifact_id"],
                "file_sha256": d134_file_sha,
                "canonical_model_digest": d134_canonical_digest,
                "canonical_model_digest_field": "acceptance_criteria_digest",
            },
            {
                "artifact_id": d135["artifact_id"],
                "file_sha256": d135_file_sha,
                "canonical_model_digest": d135_canonical_digest,
                "canonical_model_digest_field": "bend_method_evidence_digest",
            },
        ],
        "independent_final_read_only_audits": [
            {
                "agent": key,
                "task_id": review["task_id"],
                "status": review["status"],
                "stdout_sha256": review["stdout_sha256"].upper(),
            }
            for key, review in reviews.items()
        ],
        "hash_semantics_clarification": {
            "D135_source_records_sha256_semantics": "SOURCE_FILE_BYTES_SHA256",
            "D135_recorded_D134_source_file_sha256": d135_d134_source_sha,
            "independently_recomputed_D134_file_sha256": d134_file_sha,
            "D134_acceptance_criteria_digest_semantics": "CANONICAL_JSON_BEFORE_DIGEST_FIELD_INSERTION",
            "D134_acceptance_criteria_digest": d134_canonical_digest,
            "hash_domain_mismatch_exists": False,
            "values_are_expected_to_differ": True,
            "D134_or_D135_mutated": False,
        },
        "digest_contract": {
            "algorithm": "SHA256_OVER_UTF8_JSON_SORT_KEYS_COMPACT_EXCLUDING_DIGEST_FIELD",
            "D132_digest_field": "pull_gate_digest",
            "D134_digest_field": "acceptance_criteria_digest",
            "D135_digest_field": "bend_method_evidence_digest",
            "D136_digest_field": "clarification_digest",
        },
        "sealed_source_package_hashes": [
            {"artifact_id": d134["artifact_id"], "package_sha256": sha(PACKAGE_134)},
            {"artifact_id": d135["artifact_id"], "package_sha256": sha(PACKAGE_135)},
        ],
        "gate_lineage_and_supersession": {
            "D132_is_gate_definition_source": True,
            "D133_contains_gate_count_but_not_gate_definitions": True,
            "D134_reauthored_four_of_five_gate_ids": True,
            "D134_note_statement_that_it_makes_D133_gates_machine_readable_is_superseded": True,
            "superseded_gate_map": superseded_gate_map,
        },
        "authoritative_pull_release_gates": authoritative_gates,
        "authoritative_pull_release_gate_count": len(authoritative_gates),
        "evaluated_gate_count": 0,
        "passed_gate_count": 0,
        "all_pull_release_gates_pass": False,
        "authoritative_opening_acceptance_records": authoritative_openings,
        "stop_conditions_added": [
            "REMAINING_DEPTH_MINUS_ENVELOPE_BELOW_REQUIRED_COVER",
            "BEND_RADIUS_DEFINITION_NULL_OR_NOT_RECONCILED_WITH_SELECTED_TOOL",
            "CLOSEOUT_SYSTEM_NOT_SELECTED",
        ],
        "release_semantics_clarification": {
            "D134_pass_scope": "ACCEPTANCE_CRITERIA_DEFINITION_ONLY",
            "D135_pass_scope": "OFFICIAL_R80_TOOL_METHOD_EVIDENCE_ONLY",
            "D134_all_pull_release_gates_pass": d134["all_pull_release_gates_pass"],
            "D134_current_state": d134["state_machine"]["current_state"],
            "D135_D134_gate_G04_can_pass": d135["D134_gate_G04_can_pass"],
            "pipe_bending_authorized": False,
            "pipe_pull_authorized": False,
            "penetration_closeout_authorized": False,
            "construction_authorized": False,
            "physical_release_status": "NOT_RELEASED",
        },
        "per_floor_owner_statement_depth_screening": per_floor_depth_screen,
        "depth_screening_scope": {
            "same_remaining_available_depth_owner_statement_on_both_floors_mm": 70,
            "floor_total_difference_mm": d134["owner_stated_inputs"]["buildup_total_difference_mm"],
            "zero_mm_coordination_envelope_margin_is_not_cover_or_face_adequacy": True,
            "eight_mm_comparison_margin_is_not_cover_or_face_adequacy": True,
            "face_assignment_pending": True,
            "instrumental_measurement_pending": True,
            "coordination_envelope_is_provisional": True,
        },
        "D130_relation_clarification": {
            "D130_is_append_only_and_not_changed": True,
            "D134_owner_inputs_enter_D130_floor_axis_balance": d134["owner_stated_inputs"]["owner_inputs_enter_D130_floor_axis_balance"],
            "future_reconciliation_must_be_new_append_only_artifact": True,
            "future_reconciliation_requires_as_built_face_datums_and_selected_floor_stack": True,
            "reconciliation_completed": False,
        },
        "P01_orientation_screening_preserved": {
            "planned_clear_size_mm": d134["p01_orientation_screening"]["planned_clear_size_mm"],
            "pair_envelope_mm": d134["derived_envelope_screening"]["pair_outer_to_outer_envelope_mm"],
            "margin_along_120mm_side_mm": d134["p01_orientation_screening"]["pair_envelope_if_offset_along_120mm_margin_mm"],
            "margin_along_200mm_side_mm": d134["p01_orientation_screening"]["pair_envelope_if_offset_along_200mm_margin_mm"],
            "planned_orientation_resolved": False,
            "as_built_orientation_and_clear_size_verified": False,
            "single_primary_envelope_transverse_margin_mm": 50.0,
        },
        "official_source_metadata_normalization": [
            {
                "publisher": source["publisher"],
                "title": source["document"],
                "url": source["url"],
                "pages": source.get("relevant_pages", []),
                "accessed_date": "2026-08-13",
                "document_revision_or_edition": None,
                "downloaded_document_sha256": None,
                "downloaded_document_hash_status": "NOT_ARCHIVED_IN_D135",
            }
            for source in d135["official_sources"]
        ],
        "method_semantics_clarification": {
            "hot_bending_prohibited_unconditionally": True,
            "external_bending_spring_status": "NOT_CAPTURED_FROM_SOURCE",
            "D125_direction_change_policy": d125["primary_direction_change_policy"],
            "D125_direction_change_policy_reconciled_with_D135_bend_candidate": False,
            "actual_bend_locations_and_tangent_lengths_verified": False,
        },
        "remaining_field_inputs": [
            "W01_W02_P01_AS_BUILT_DIMENSIONS_AND_BOTH_FACE_DATUMS",
            "PHOTO_EVIDENCE_AND_EDGE_OR_STRUCTURAL_DISPOSITION",
            "PER_PRIMARY_SLEEVE_OR_TESTED_COMMON_SYSTEM_AND_ANNULUS",
            "ACTUAL_PIPE_PRODUCT_CODE",
            "TOOL_1071925_AND_R80_SEGMENT_1120411_PRESENT",
            "FACTORY_INSULATION_BEND_METHOD",
            "ACCESSIBLE_TANGENT_LENGTHS_AND_POST_BEND_INSPECTION",
            "SELECTED_FLOOR_STACK_COVER_REQUIREMENT",
        ],
        "new_route_coordinate_count": 0,
        "approved_bend_geometry_count": 0,
        "approved_pipe_geometry_count": 0,
        "result": "PASS_METADATA_CLARIFICATION_REWORK_FIELD_EVIDENCE_AND_PHYSICAL_RELEASE",
    }
    record["clarification_digest"] = digest(record)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "primary_acceptance_bend_clarification.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf8"
    )
    (OUTPUT / "clarification_note.md").write_text(
        "# D136 — уточнение статуса D134/D135\n\n"
        "D134 и D135 не изменяются. Значение `sha256` источника в D135 — SHA-256 байтов файла D134; "
        "внутренний `acceptance_criteria_digest` D134 вычислен по канонической модели до добавления самого поля digest. "
        "Это разные области хеширования, поэтому разные значения корректны.\n\n"
        "D134 переопределил четыре идентификатора шлюзов D132; D136 публикует явную таблицу соответствия и "
        "возвращает в обязательные входы выбор системы заделки проходок, требование защитного слоя и точное "
        "определение радиуса R80.\n\n"
        "Слово PASS в D134 относится только к полноте критериев приемки, а в D135 — только к подтверждению "
        "официального инструментального метода R80. Гибка, протяжка и строительство не разрешены. "
        "Нулевой запас 70−70 мм и сравнительный запас 70−62=8 мм относятся только к заявленным владельцем "
        "остаточным 70 мм на каждом этаже и не доказывают защитный слой или пригодность конкретной грани.\n",
        encoding="utf8",
    )
    files = sorted(path for path in OUTPUT.iterdir() if path.is_file())
    manifest = {
        "artifact_id": record["artifact_id"],
        "clarification_digest": record["clarification_digest"],
        "append_only": True,
        "manifest_self_hash_excluded_by_design": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8"
    )
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    PACKAGE.with_suffix(PACKAGE.suffix + ".sha256").write_text(sha(PACKAGE) + "\n", encoding="ascii")
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "digest": record["clarification_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

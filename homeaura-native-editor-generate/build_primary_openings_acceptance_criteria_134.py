import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
RUNTIME_RESULTS = Path.home() / "AppData" / "Local" / "HomeAuraMultiAgent" / "results"
SOURCES = {
    "D125": BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_AAC_CROSSINGS_125" / "floor_primary_aac_crossings.json",
    "D130": BASE / "HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_CLEAN_EVIDENCE_130" / "floor_primary_coordination_clean_evidence.json",
    "D131": BASE / "HA_TWO_FLOOR_PRIMARY_OPENINGS_OWNER_REPORT_131" / "primary_openings_owner_report.json",
    "D133": BASE / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ASBUILT_PULL_GATE_EVIDENCE_133" / "primary_openings_asbuilt_pull_gate_evidence.json",
}
CLOUD_RESULTS = {
    "claude": RUNTIME_RESULTS / "HA-POSTOPENING-D134-CLAUDE-20260813-001.json",
    "kimi": RUNTIME_RESULTS / "HA-POSTOPENING-D134-KIMI-20260813-001.json",
}
OUTPUT = BASE / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ACCEPTANCE_CRITERIA_134"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_PRIMARY_OPENINGS_ACCEPTANCE_CRITERIA_134.zip"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    return hashlib.sha256(raw).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise SystemExit("append-only target already exists")

    models = {key: json.loads(path.read_text(encoding="utf8")) for key, path in SOURCES.items()}
    reviews = {key: json.loads(path.read_text(encoding="utf8")) for key, path in CLOUD_RESULTS.items()}
    for key, review in reviews.items():
        if review["status"] != "COMPLETED" or review["exit_code"] != 0 or review["timed_out"]:
            raise SystemExit(f"{key} review is not a completed successful result")

    d125 = models["D125"]
    d131 = models["D131"]
    primary = d125["primary_pipe"]
    envelope = float(primary["provisional_coordination_envelope_od_mm"])
    comparison = float(primary["comparison_insulated_od_mm"])
    pitch = float(primary["axis_pitch_mm"])
    pair_envelope = pitch + envelope
    pair_comparison = pitch + comparison
    p01 = d125["separate_slab_penetration_node"]
    p01_size = [float(v) for v in p01["coordination_clear_size_mm"]]

    openings = []
    for source_opening in d131["openings"]:
        opening_id = source_opening["opening_id"]
        is_slab = source_opening["opening_type"] == "FLOOR_SLAB_PENETRATION"
        openings.append(
            {
                "opening_id": opening_id,
                "opening_type": source_opening["opening_type"],
                "owner_reported_drilled": True,
                "as_built_dimensions_verified": False,
                "as_built_clear_width_mm": None,
                "as_built_clear_height_or_length_mm": None,
                "as_built_depth_mm": None,
                "as_built_bbox_mm": None,
                "photo_evidence_paths": [],
                "face_records": [
                    {
                        "face_id": "TOP" if is_slab else "FACE_A",
                        "floor_buildup_id": None,
                        "axis_height_or_elevation_aff_mm": None,
                    },
                    {
                        "face_id": "BOTTOM" if is_slab else "FACE_B",
                        "floor_buildup_id": None,
                        "axis_height_or_elevation_aff_mm": None,
                    },
                ],
                "per_primary_records": [
                    {
                        "primary_id": primary_id,
                        "sleeve_or_tested_common_system_selected": False,
                        "sleeve_or_liner_installed": None,
                        "edge_protection_verified": None,
                        "annulus_clear_mm": None,
                        "factory_insulation_intact": None,
                    }
                    for primary_id in ("SUPPLY", "RETURN")
                ],
                "structural_or_wall_disposition_verified": False,
                "independently_verified": False,
            }
        )

    gates = [
        {
            "gate_id": "G01_AS_BUILT_DIMENSIONS_AND_PHOTOS",
            "statement": "W01_W02_P01_MEASURED_ON_BOTH_FACES_WITH_PHOTO_EVIDENCE",
            "inputs_required": ["openings[].as_built_*", "openings[].face_records[]", "openings[].photo_evidence_paths[]"],
            "evaluated": False,
            "passes": None,
        },
        {
            "gate_id": "G02_STRUCTURAL_AND_WALL_DISPOSITION",
            "statement": "AAC_WALLS_AND_SLAB_RESULT_ACCEPTED_WITH_NO_UNRESOLVED_DAMAGE",
            "inputs_required": ["openings[].structural_or_wall_disposition_verified"],
            "evaluated": False,
            "passes": None,
        },
        {
            "gate_id": "G03_PER_PRIMARY_SLEEVE_AND_EDGE_SYSTEM",
            "statement": "BOTH_PRIMARIES_HAVE_VERIFIED_SLEEVE_OR_TESTED_COMMON_SYSTEM_AND_EDGE_PROTECTION",
            "inputs_required": ["openings[].per_primary_records[]", "required_annulus_per_primary_mm"],
            "evaluated": False,
            "passes": None,
        },
        {
            "gate_id": "G04_GEOMETRY_AND_BEND_METHOD",
            "statement": "P01_PAIR_ORIENTATION_FLOOR_DATUM_AND_80MM_RADIUS_METHOD_RECONCILED",
            "inputs_required": ["p01_orientation_screening.pitch_offset_axis", "floor_buildups[].pipe_containing_layer", "owner_stated_inputs.bend_method"],
            "evaluated": False,
            "passes": None,
        },
        {
            "gate_id": "G05_PULL_METHOD_LABELS_AND_ACCESS",
            "statement": "CONTINUOUS_NO_HIDDEN_JOINT_PULL_METHOD_LABELS_CAPS_AND_ACCESSIBLE_BENDS_READY",
            "inputs_required": ["pull_method_statement", "label_and_cap_record", "accessible_bend_record"],
            "evaluated": False,
            "passes": None,
        },
    ]

    record = {
        "schema": "homeaura-primary-openings-acceptance-criteria-0.1",
        "artifact_id": "HA_TWO_FLOOR_PRIMARY_OPENINGS_ACCEPTANCE_CRITERIA_134",
        "status": "ACCEPTANCE_CRITERIA_READY_REWORK_FIELD_MEASUREMENTS_AND_PULL_RELEASE",
        "source_records": [
            {"artifact_id": models[key]["artifact_id"], "sha256": sha(path)}
            for key, path in SOURCES.items()
        ],
        "independent_read_only_reviews": [
            {
                "agent": key,
                "task_id": review["task_id"],
                "status": review["status"],
                "stdout_sha256": review["stdout_sha256"].upper(),
            }
            for key, review in reviews.items()
        ],
        "owner_stated_inputs": {
            "vertical_rise_mm": 3000,
            "vertical_rise_independently_verified": False,
            "vertical_rise_endpoints_and_datums_recorded": False,
            "coordination_minimum_bend_radius_mm": 80,
            "bend_radius_definition": None,
            "bend_radius_owner_directed_conservative_value": True,
            "bend_radius_manufacturer_verified": False,
            "bend_method": None,
            "hot_bending_authorized": False,
            "floor_buildups": [
                {
                    "buildup_id": "F1",
                    "installed_insulation_mm": 100,
                    "remaining_available_depth_mm": 70,
                    "total_from_owner_statement_mm": 170,
                    "pipe_containing_layer": None,
                    "required_cover_above_envelope_mm": None,
                },
                {
                    "buildup_id": "F2",
                    "installed_insulation_mm": 50,
                    "remaining_available_depth_mm": 70,
                    "total_from_owner_statement_mm": 120,
                    "pipe_containing_layer": None,
                    "required_cover_above_envelope_mm": None,
                },
            ],
            "buildup_total_difference_mm": 50,
            "owner_inputs_are_not_instrumental_verification": True,
            "owner_inputs_enter_D130_floor_axis_balance": False,
        },
        "derived_envelope_screening": {
            "primary_count": 2,
            "pipe_nominal_size": "32X3",
            "axis_pitch_mm": pitch,
            "coordination_envelope_od_mm": envelope,
            "comparison_insulated_od_mm": comparison,
            "pair_outer_to_outer_envelope_mm": pair_envelope,
            "pair_outer_to_outer_comparison_mm": pair_comparison,
            "remaining_depth_minus_coordination_envelope_mm": 70.0 - envelope,
            "remaining_depth_minus_comparison_insulated_od_mm": 70.0 - comparison,
            "required_cover_above_envelope_mm": None,
            "required_annulus_per_primary_mm": None,
            "adequacy_claimed": False,
        },
        "p01_orientation_screening": {
            "planned_clear_size_mm": p01_size,
            "pitch_offset_axis": None,
            "pair_envelope_if_offset_along_120mm_margin_mm": p01_size[0] - pair_envelope,
            "pair_envelope_if_offset_along_200mm_margin_mm": p01_size[1] - pair_envelope,
            "orientation_resolved": False,
            "planned_size_is_not_as_built_size": True,
        },
        "openings": openings,
        "pull_release_gates": gates,
        "pull_release_gate_count": len(gates),
        "evaluated_gate_count": 0,
        "passed_gate_count": 0,
        "all_pull_release_gates_pass": False,
        "state_machine": {
            "states": ["S_PREPARATION", "S_PULL_RELEASE", "S_PRESSURE_TEST", "S_CLOSEOUT"],
            "current_state": "S_PREPARATION",
            "pressure_test_precedes_closeout": True,
            "transitions": [
                {"from": "S_PREPARATION", "to": "S_PULL_RELEASE", "required_gate_ids": [g["gate_id"] for g in gates]},
                {"from": "S_PULL_RELEASE", "to": "S_PRESSURE_TEST", "required_record": "PIPE_INSTALLED_AND_VISIBLE"},
                {"from": "S_PRESSURE_TEST", "to": "S_CLOSEOUT", "required_record": "PRESSURE_TEST_ACCEPTED"},
            ],
        },
        "acceptance_checks": [
            "AS_BUILT_OPENING_DIMENSIONS_AND_BOTH_FACE_DATUMS_PRESENT",
            "TWO_PER_PRIMARY_SLEEVE_OR_TESTED_COMMON_SYSTEM_RECORDS_PER_OPENING",
            "P01_PITCH_OFFSET_AXIS_RESOLVED_TO_FIT_ACTUAL_OPENING",
            "F1_F2_50MM_BUILDUP_DIFFERENCE_RECONCILED_AT_RELEVANT_FACES",
            "AVAILABLE_DEPTH_COVER_CHECK_USES_SELECTED_SYSTEM_REQUIREMENT",
            "80MM_BEND_RADIUS_DEFINITION_RECONCILED_WITH_SELECTED_PRODUCT_AND_METHOD",
            "NO_HIDDEN_JOINTS_AND_ACCESSIBLE_DIRECTION_CHANGES",
            "PRESSURE_TEST_ACCEPTED_BEFORE_ANY_CLOSEOUT",
        ],
        "stop_conditions": [
            "ANY_AS_BUILT_VALUE_POPULATED_WITHOUT_MEASUREMENT_OR_PHOTO_EVIDENCE",
            "ANY_GATE_MARKED_PASS_WHILE_REQUIRED_INPUT_IS_NULL",
            "P01_PAIR_OFFSET_USES_120MM_DIRECTION_WITH_170MM_ENVELOPE",
            "VISIBLE_REBAR_OR_STRUCTURAL_DAMAGE_UNRESOLVED",
            "PIPE_TOUCHES_SHARP_EDGE_OR_UNPROTECTED_AAC_OR_CONCRETE",
            "HIDDEN_FITTING_OR_JOINT_PROPOSED",
            "HOT_BENDING_OR_UNVERIFIED_RADIUS_METHOD_PROPOSED",
            "PRESSURE_OR_HOLD_TIME_INVENTED_WITHOUT_SELECTED_PROCEDURE",
            "PENETRATION_OR_FLOOR_CLOSEOUT_BEFORE_ACCEPTED_PRESSURE_TEST",
        ],
        "new_route_coordinate_count": 0,
        "approved_wall_opening_count": 0,
        "approved_slab_opening_count": 0,
        "approved_pipe_geometry_count": 0,
        "selected_product_count": 0,
        "pressure_test_parameters_selected": False,
        "pipe_pull_authorized": False,
        "penetration_closeout_authorized": False,
        "construction_authorized": False,
        "result": "PASS_ACCEPTANCE_CRITERIA_REWORK_FIELD_EVIDENCE_AND_RELEASE",
    }
    record["acceptance_criteria_digest"] = digest(record)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "primary_openings_acceptance_criteria.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf8"
    )
    (OUTPUT / "criteria_note.md").write_text(
        "# D134 — критерии приёмки выполненных отверстий\n\n"
        "D134 не добавляет трассу и не разрешает протяжку. Он делает пять шлюзов D133 машиночитаемыми, "
        "фиксирует сообщённые владельцем исходные данные (подъём 3 м, радиус 80 мм, конструкции полов 100+70 и 50+70 мм) "
        "и оставляет исполнительные размеры, фотографии, изделия и параметры опрессовки пустыми до натурной приёмки.\n\n"
        "Для каждой из двух магистралей предусмотрена отдельная запись гильзы/защиты. P01 проходит предварительный экран "
        "только при ориентации 170-мм габарита пары вдоль 200-мм стороны; фактическая ориентация и размер ещё не подтверждены.\n",
        encoding="utf8",
    )
    files = sorted(path for path in OUTPUT.iterdir() if path.is_file())
    manifest = {
        "artifact_id": record["artifact_id"],
        "acceptance_criteria_digest": record["acceptance_criteria_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8"
    )
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "digest": record["acceptance_criteria_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

import copy
import json
from pathlib import Path

from agent.ufh_project_engineering_profile_authoring import (
    AuthoredValue,
    AuthoringProvenance,
    FIELD_AUTHORING_MAP,
    InputAcquisitionType,
    load_ufh_project_engineering_authoring_template,
    synthetic_complete_authoring_payload,
    test01_authoring_template_payload as make_test01_authoring_template_payload,
)
from agent.ufh_project_engineering_profile import default_ufh_routing_policy


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "Test_01_UFH_engineering_profile_authoring_template.json"


def test_complete_classification_covers_remaining_41_fields():
    assert len(FIELD_AUTHORING_MAP) == 41
    assert all(isinstance(value, InputAcquisitionType)
               for value in FIELD_AUTHORING_MAP.values())
    assert "sizing.room.outdoor_design_temperature_c" in FIELD_AUTHORING_MAP
    assert "engineering.common_circuit.control" in FIELD_AUTHORING_MAP
    assert "sizing.coverage_request.exclusion_zones" in FIELD_AUTHORING_MAP


def test_template_artifact_matches_generated_payload_and_duplicates_no_project_owned_inputs():
    disk = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    generated = make_test01_authoring_template_payload()
    assert disk == generated
    text = json.dumps(disk, ensure_ascii=False)
    for forbidden in (
        "building_id", "level_id", "room boundary", "room area",
        "indoor room temperature", "air changes per hour",
    ):
        assert forbidden in disk["project_context"]["known_from_project"]
    assert "indoor_temperature_c" not in text
    assert "air_changes_per_hour" not in text
    assert "boundary" not in disk


def test_missing_template_remains_incomplete_and_builds_no_profile():
    result = load_ufh_project_engineering_authoring_template(
        make_test01_authoring_template_payload()
    )
    assert result.status == "INCOMPLETE"
    assert result.profile is None
    assert "sizing.room.outdoor_design_temperature_c" in result.missing_authoring_paths
    assert "engineering.common_circuit.inner_diameter_m" in result.missing_authoring_paths


def test_explicit_empty_is_distinct_from_absence():
    complete = synthetic_complete_authoring_payload()
    complete["explicit_confirmations"]["exclusion_zones"] = {"status": "UNSET"}
    unset = load_ufh_project_engineering_authoring_template(complete)
    assert unset.status == "INCOMPLETE"
    assert "sizing.coverage_request.exclusion_zones" in unset.missing_authoring_paths

    complete = synthetic_complete_authoring_payload()
    ready = load_ufh_project_engineering_authoring_template(complete)
    assert ready.status == "READY"
    assert ready.profile is not None


def test_mode_alternatives_require_sigma_or_supply_temperature():
    payload = synthetic_complete_authoring_payload()
    payload["design_conditions"]["theta_supply_c"] = {
        **payload["design_conditions"]["sigma_k"],
        "value": 45.0,
        "unit": "degC",
    }
    conflict = load_ufh_project_engineering_authoring_template(payload)
    assert conflict.status == "INCOMPLETE"
    assert any(d.code == "AUTHORING_MODE_ALTERNATIVE_CONFLICT"
               for d in conflict.diagnostics)

    payload = synthetic_complete_authoring_payload()
    payload["ufh_design_settings"]["mode"]["value"] = "solve_return"
    payload["design_conditions"]["sigma_k"] = {"status": "UNSET"}
    payload["design_conditions"]["theta_supply_c"] = {
        **payload["design_conditions"]["outdoor_design_temperature_c"],
        "value": 45.0,
        "unit": "degC",
    }
    ready = load_ufh_project_engineering_authoring_template(payload)
    assert ready.status == "READY"
    assert ready.profile.engineering_inputs.mode == "solve_return"
    assert ready.profile.engineering_inputs.sigma_k is None
    assert ready.profile.engineering_inputs.theta_supply_c == 45.0


def test_product_fluid_and_control_are_grouped_but_raw_fields_need_sources():
    incomplete = synthetic_complete_authoring_payload()
    incomplete["pipe_product"]["inner_diameter_m"] = {"status": "UNSET"}
    result = load_ufh_project_engineering_authoring_template(incomplete)
    assert result.status == "INCOMPLETE"
    assert "engineering.common_circuit.inner_diameter_m" in result.missing_authoring_paths

    ready = load_ufh_project_engineering_authoring_template(
        synthetic_complete_authoring_payload()
    )
    assert ready.status == "READY"
    assert ready.profile.engineering_inputs.common_circuit.inner_diameter_m == 0.012
    assert ready.profile.engineering_inputs.common_circuit.control.manufacturer == "Synthetic"


def test_project_owned_ach_is_injected_without_template_duplication():
    payload = synthetic_complete_authoring_payload()
    payload["building_physics"].pop("air_changes_per_hour")
    ach = AuthoredValue(
        status="EXPLICIT_VALUE",
        value=1.0714285373687744,
        unit="1/h",
        provenance=AuthoringProvenance(
            source_type="project_data",
            source_reference="projects/Test_01/exports/rooms/rooms.json",
            source_field="$.Rooms[].AirExchangeRate",
            author_or_confirmation="room-source",
            transformation="authoritative room source value",
            units="1/h",
        ),
    )
    ready = load_ufh_project_engineering_authoring_template(
        payload,
        project_owned_values={
            "sizing.room.insulation.air_changes_per_hour": ach,
        },
    )
    assert ready.status == "READY"
    assert ready.profile.building_physics.air_changes_per_hour == 1.0714285373687744
    provenance = ready.profile.provenance["sizing.room.insulation.air_changes_per_hour"]
    assert provenance.source_kind == "canonical_project_domain"
    assert provenance.source_path == "$.Rooms[].AirExchangeRate"


def test_missing_project_owned_ach_remains_unresolved():
    payload = synthetic_complete_authoring_payload()
    payload["building_physics"].pop("air_changes_per_hour")
    result = load_ufh_project_engineering_authoring_template(payload)
    assert result.status == "INCOMPLETE"
    assert "sizing.room.insulation.air_changes_per_hour" in result.missing_authoring_paths
    assert any(d.code == "AUTHORITATIVE_PROJECT_VALUE_REQUIRED" for d in result.diagnostics)


def test_routing_policy_values_and_digest_are_explicit():
    ready = load_ufh_project_engineering_authoring_template(
        synthetic_complete_authoring_payload()
    )
    assert ready.status == "READY"
    policy = default_ufh_routing_policy()
    assert ready.profile.routing_policy == policy
    assert ready.profile.routing_settings.turn_radius_mm == 100
    assert ready.profile.routing_settings.perimeter_priority_mode is True
    turn = ready.profile.provenance["sizing.coverage_request.turn_radius_mm"]
    perimeter = ready.profile.provenance["sizing.coverage_request.perimeter_priority_mode"]
    assert turn.source_kind == "routing_algorithm_policy"
    assert perimeter.source_kind == "routing_algorithm_policy"
    assert turn.source_file == f"{policy.policy_id}:{policy.policy_version}"
    assert perimeter.source_file == f"{policy.policy_id}:{policy.policy_version}"
    changed = ready.profile.model_copy(update={
        "routing_policy": policy.model_copy(update={"turn_radius_mm": 101})
    })
    assert changed.profile_digest != ready.profile.profile_digest


def test_wrong_units_are_rejected():
    payload = synthetic_complete_authoring_payload()
    payload["pipe_product"]["inner_diameter_m"]["unit"] = "mm"
    result = load_ufh_project_engineering_authoring_template(payload)
    assert result.status == "INCOMPLETE"
    assert any(d.code == "AUTHORING_UNIT_INVALID"
               and d.path == "engineering.common_circuit.inner_diameter_m"
               for d in result.diagnostics)


def test_physical_value_without_provenance_is_rejected():
    payload = synthetic_complete_authoring_payload()
    payload["building_physics"]["floor_u_value_w_m2k"].pop("provenance")
    result = load_ufh_project_engineering_authoring_template(payload)
    assert result.status == "INVALID"
    assert any(d.code == "AUTHORING_TEMPLATE_INVALID" for d in result.diagnostics)


def test_same_template_is_deterministic():
    payload = synthetic_complete_authoring_payload()
    first = load_ufh_project_engineering_authoring_template(payload)
    second = load_ufh_project_engineering_authoring_template(copy.deepcopy(payload))
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.profile.profile_digest == second.profile.profile_digest


def test_synthetic_complete_authoring_builds_existing_typed_profile():
    result = load_ufh_project_engineering_authoring_template(
        synthetic_complete_authoring_payload()
    )
    assert result.status == "READY"
    assert result.profile is not None
    sizing = result.profile.sizing_fragment()
    engineering = result.profile.engineering_fragment()
    assert sizing["coverage_request"]["collector_point"] == {"x_mm": 500, "y_mm": 500}
    assert sizing["coverage_request"]["requested_circuit_count"] is None
    assert engineering["common_circuit"]["fluid"]["density_kg_m3"] == 998.0
    assert "theta_indoor_c" not in engineering

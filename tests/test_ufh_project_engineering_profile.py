from __future__ import annotations

import hashlib
import pytest
from pydantic import ValidationError

from agent.ufh_project_adapter import build_ufh_sizing_request_from_project_room
from agent.ufh_project_engineering_profile import (
    FIELD_CLASSIFICATION,
    UFHProjectDesignConditions,
    UFHProjectEngineeringInputs,
    UFHProjectEngineeringProfile,
    UFHProjectRoutingSettings,
    ProfileValueProvenance,
)
from tests.test_ufh_project_adapter import (
    TEST01_ROOMS,
    _complete_test_source,
    _source_test01,
)


def _leaves(value, prefix):
    if isinstance(value, dict) and value:
        return [path for key, child in value.items()
                for path in _leaves(child, f"{prefix}.{key}")]
    if isinstance(value, (list, tuple)) and value:
        return [path for index, child in enumerate(value)
                for path in _leaves(child, f"{prefix}[{index}]")]
    return [prefix]


def _profile(source):
    # Test-only complete source: the profile fields originate in the existing
    # synthetic sizing and engineering fixtures, never in Test_01.
    from tests.test_ufh_project_adapter import _complete_test_source

    full = _complete_test_source()
    request = full.sizing_inputs
    eng = full.engineering_inputs
    settings = request["coverage_request"]
    routing = UFHProjectRoutingSettings(
        collector_point=settings["collector_point"],
        wall_offset_mm=settings["wall_offset_mm"],
        spacing_mm=settings["spacing_mm"],
        requested_circuit_count=settings["requested_circuit_count"],
        routing_mode=settings["routing_mode"],
        turn_radius_mm=settings["turn_radius_mm"],
        field_spacing_mm=settings.get("field_spacing_mm"),
        perimeter_spacing_mm=settings.get("perimeter_spacing_mm"),
        perimeter_band_depth_mm=settings.get("perimeter_band_depth_mm"),
        preferred_topology=settings.get("preferred_topology"),
        installation_grid_spacing_mm=settings.get("installation_grid_spacing_mm"),
        perimeter_priority_mode=settings["perimeter_priority_mode"],
    )
    profile_values = {
        "design_conditions": {
            "outdoor_design_temperature_c": request["room"]["outdoor_design_temperature_c"],
        },
        "building_physics": request["room"]["insulation"],
        "floor_construction": request["floor_construction"],
        "routing_settings": routing.model_dump(mode="json"),
        "engineering_inputs": eng,
    }
    sizing_fragment = {
        "room": {
            "outdoor_design_temperature_c": profile_values["design_conditions"]["outdoor_design_temperature_c"],
            "insulation": profile_values["building_physics"],
        },
        "floor_construction": profile_values["floor_construction"],
        "coverage_request": routing.model_dump(mode="json"),
    }
    profile_engineering = {
        key: value for key, value in eng.items()
        if key not in {"theta_indoor_c", "theta_below_c"}
    }
    if profile_engineering["mode"] == "solve_supply":
        profile_engineering.pop("theta_supply_c", None)
    else:
        profile_engineering.pop("sigma_k", None)
    paths = _leaves(sizing_fragment, "sizing") + _leaves(
        profile_engineering, "engineering"
    )
    digest = hashlib.sha256(b"test-only-profile-v1").hexdigest()
    provenance = {
        path: ProfileValueProvenance(
            source_file="tests/test_ufh_project_engineering_profile.py#fixture",
            source_sha256=digest,
            source_path=f"fixture:{path}",
            source_kind="test_only",
        )
        for path in paths
    }
    return UFHProjectEngineeringProfile(
        design_conditions=UFHProjectDesignConditions.model_validate(profile_values["design_conditions"]),
        building_physics=profile_values["building_physics"],
        floor_construction=profile_values["floor_construction"],
        routing_settings=routing,
        engineering_inputs=UFHProjectEngineeringInputs.model_validate({
            key: value for key, value in eng.items()
            if key not in {"theta_indoor_c", "theta_below_c"}
        }),
        provenance=provenance,
    )


def test_classification_registry_covers_every_test01_gap():
    result = build_ufh_sizing_request_from_project_room(_source_test01())
    assert result.status == "INCOMPLETE"
    assert result.classified_gaps
    assert all(gap.source_class != "UNKNOWN" for gap in result.classified_gaps)
    assert {gap.path for gap in result.classified_gaps} == set(result.missing_inputs)
    assert all(gap.path in FIELD_CLASSIFICATION for gap in result.classified_gaps)


def test_engineering_theta_below_is_linked_alias_not_second_external_input():
    result = build_ufh_sizing_request_from_project_room(_source_test01())
    gap = next(g for g in result.classified_gaps
               if g.path == "engineering.theta_below_c")
    assert gap.source_class == "DESIGN_CONDITION"
    assert gap.required_externally is False
    assert "sizing.room.insulation.floor_boundary_temperature_c" in gap.action


def test_test01_remains_fail_closed_and_has_explicit_system_schema_defaults():
    raw_digest = hashlib.sha256(TEST01_ROOMS.read_bytes()).hexdigest()
    result = build_ufh_sizing_request_from_project_room(_source_test01())
    assert result.source_digest == raw_digest
    assert result.status == "INCOMPLETE"
    assert result.sizing_request is None
    assert "sizing.room.outdoor_design_temperature_c" in result.missing_inputs
    assert "sizing.room.insulation.exterior_wall_u_value_w_m2k" in result.missing_inputs
    defaults = [f for f in result.mapped_fields
                if f.provenance.source_kind == "SYSTEM_STRUCTURAL_DEFAULT"]
    assert {item.target_path for item in defaults if "schema_version" in item.target_path} == {
        "schema_version", "coverage_request.schema_version",
    }
    schema_defaults = [f for f in defaults if "schema_version" in f.target_path]
    assert all("no physical calculation effect" in f.provenance.transformation for f in schema_defaults)
    routing_policy = [f for f in result.mapped_fields
                      if f.provenance.source_file == "HOMEAURA_UFH_ROUTING_POLICY:V1"]
    assert any(f.target_path == "coverage_request.requested_circuit_count"
               and f.value is None for f in routing_policy)
    assert any(f.target_path == "coverage_request.turn_radius_mm"
               and f.value == 100 for f in routing_policy)
    assert any(f.target_path == "coverage_request.perimeter_priority_mode"
               and f.value is True for f in routing_policy)
    policy_defaults = [f for f in result.mapped_fields
                       if f.provenance.source_kind == "SYSTEM_ROUTING_POLICY"]
    legacy = [f for f in policy_defaults
              if f.provenance.source_file == "LEGACY_MVP_ROUTING_POLICY"]
    assert {f.target_path for f in legacy} == {
        "coverage_request.minimum_circuit_length_mm",
        "coverage_request.maximum_circuit_length_mm",
    }
    assert all("40-80 m" in f.provenance.transformation for f in legacy)


def test_profile_excludes_room_geometry_and_requires_leaf_provenance():
    names = set(UFHProjectEngineeringProfile.model_fields)
    assert "boundary" not in names
    assert "room_geometry" not in names
    assert "room" not in names
    source = _complete_test_source()
    profile = _profile(source)
    expected = set(_leaves(profile.sizing_fragment(), "sizing"))
    expected.update(_leaves(profile.engineering_fragment(), "engineering"))
    assert expected <= set(profile.provenance)


def test_adapter_uses_typed_profile_without_changing_pipeline_contract():
    source = _complete_test_source()
    profile = _profile(source)
    adapted = build_ufh_sizing_request_from_project_room(
        source.model_copy(update={"engineering_profile": profile, "engineering_inputs": {}})
    )
    assert adapted.status == "READY"
    assert adapted.sizing_request is not None
    assert adapted.engineering_inputs is not None
    assert any(f.provenance.source_kind == "test_only"
               and f.target_path == "engineering.common_circuit.fluid.density_kg_m3"
               for f in adapted.mapped_fields)


def test_field_ownership_examples_separate_physics_calculation_and_policy():
    assert FIELD_CLASSIFICATION["sizing.room.insulation.exterior_wall_u_value_w_m2k"] == "BUILDING_PHYSICS"
    assert FIELD_CLASSIFICATION["sizing.room.room_area_mm2"] == "CALCULATED"
    assert FIELD_CLASSIFICATION["sizing.coverage_request.minimum_circuit_length_mm"] == "LEGACY_ROUTING_POLICY"
    assert FIELD_CLASSIFICATION["sizing.coverage_request.requested_circuit_count"] == "UFH_DESIGN_SETTING"
    assert FIELD_CLASSIFICATION["sizing.coverage_request.exclusion_zones"] == "OPTIONAL_EXPLICIT_EMPTY"


def test_missing_physical_project_values_still_fail_closed():
    source = _complete_test_source()
    for parent, key, provenance_path in (
        ("room", "outdoor_design_temperature_c", "sizing.room.outdoor_design_temperature_c"),
        ("floor_construction", "declared_output_at_100mm_w_m2", "sizing.floor_construction.declared_output_at_100mm_w_m2"),
    ):
        sizing = {**source.sizing_inputs, parent: dict(source.sizing_inputs[parent])}
        sizing[parent].pop(key)
        prov = dict(source.input_provenance)
        prov.pop(provenance_path)
        result = build_ufh_sizing_request_from_project_room(
            source.model_copy(update={"sizing_inputs": sizing, "input_provenance": prov})
        )
        assert result.status == "INCOMPLETE"
        assert provenance_path in result.missing_inputs
        assert result.sizing_request is None


def test_room_area_is_derived_from_authoritative_boundary_not_required_separately():
    source = _complete_test_source()
    sizing = {**source.sizing_inputs, "room": dict(source.sizing_inputs["room"])}
    sizing["room"].pop("room_area_mm2")
    provenance = dict(source.input_provenance)
    provenance.pop("sizing.room.room_area_mm2")
    result = build_ufh_sizing_request_from_project_room(
        source.model_copy(update={"sizing_inputs": sizing, "input_provenance": provenance})
    )
    assert result.status == "READY"
    assert result.sizing_request.room.room_area_mm2 == 12_000_000
    area = next(field for field in result.mapped_fields
                if field.target_path == "room.room_area_mm2" and field.applied_to_request)
    assert "shoelace area" in area.provenance.transformation


def test_mode_inapplicable_temperature_output_is_not_an_external_input():
    source = _complete_test_source()
    engineering = dict(source.engineering_inputs)
    engineering["mode"] = "solve_return"
    engineering["sigma_k"] = None
    engineering["theta_supply_c"] = 45.0
    engineering.pop("sigma_k")
    provenance = dict(source.input_provenance)
    provenance.pop("engineering.sigma_k")
    result = build_ufh_sizing_request_from_project_room(
        source.model_copy(update={"engineering_inputs": engineering, "input_provenance": provenance})
    )
    assert result.status == "READY"
    assert result.engineering_inputs.mode == "solve_return"
    assert result.engineering_inputs.sigma_k is None


def test_profile_adapter_digest_is_deterministic():
    source = _complete_test_source()
    profile = _profile(source)
    adapted_source = source.model_copy(update={"engineering_profile": profile})
    first = build_ufh_sizing_request_from_project_room(adapted_source)
    second = build_ufh_sizing_request_from_project_room(adapted_source)
    assert first.adapter_digest == second.adapter_digest
    assert first.classified_gaps == second.classified_gaps
    assert profile.profile_digest == _profile(source).profile_digest


def test_profile_rejects_missing_or_unowned_provenance_paths():
    source = _complete_test_source()
    profile = _profile(source)
    payload = profile.model_dump(mode="python")
    payload["provenance"].pop(next(iter(payload["provenance"])))
    with pytest.raises(ValidationError, match="profile leaf provenance missing"):
        UFHProjectEngineeringProfile.model_validate(payload)

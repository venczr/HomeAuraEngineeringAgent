import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent.ufh_pre_generation_questionnaire import Decision, QuestionnaireState
from agent.ufh_project_adapter import build_ufh_sizing_request_from_project_room
from agent.ufh_project_engineering_profile_authoring import (
    AuthoredValue,
    AuthoringProvenance,
    AuthoringStatus,
    synthetic_complete_authoring_payload,
    load_ufh_project_engineering_authoring_template,
)
from agent.ufh_questionnaire_resolver_contract import (
    INHERITED_ASSUMPTION_AUDIT,
    TEST01_QUESTION_RESOLVER_MAP,
    Binding,
    ResolverResult,
    ResolvedValue,
    apply_resolver_result,
    assumption_audit_by_class,
    invalidate_bindings,
    make_resolver_request,
    replace_questionnaire_decisions_and_invalidate,
)
from tests.test_ufh_project_adapter import _complete_test_source


ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIGEST = "1" * 64


def state() -> QuestionnaireState:
    payload = json.loads(
        (ROOT / "docs" / "Test_01_UFH_engineering_profile_authoring_template.json").read_text(encoding="utf-8")
    )
    return QuestionnaireState(authoring=payload)


def decision(question_id: str, value, revision: str = "1") -> Decision:
    return Decision(question_id=question_id, value=value, source_reference="owner:test", revision=revision)


def climate_request(st: QuestionnaireState):
    return make_resolver_request(
        "CLIMATE_RESOLVER",
        "Test_01",
        "101DAA3",
        PROJECT_DIGEST,
        st.decisions,
    )


def authored(value, unit: str, source_type: str = "normative_source") -> AuthoredValue:
    return AuthoredValue(
        status=AuthoringStatus.EXPLICIT_VALUE,
        value=value,
        unit=unit,
        provenance=AuthoringProvenance(
            source_type=source_type,
            source_reference="resolver-source://fixture",
            source_field="table.field",
            author_or_confirmation="fixture",
            transformation="resolver fixture value",
            units=unit,
        ),
    )


def resolved(field: str, value, unit: str, request, *, authority="NORMATIVE_AUTHORITATIVE", source_type="normative_source"):
    return ResolvedValue(
        target_authoring_field=field,
        authored_value=authored(value, unit, source_type),
        authority_class=authority,
        dependency_digest=request.dependency_digest,
    )


def test_resolver_request_is_strict_and_deterministic():
    st = state()
    st.decisions["climate"] = decision("climate", {"settlement": "Tikhvin", "region": "Leningrad"})
    req = climate_request(st)
    assert req.normalized_decisions["climate"]["value"]["settlement"] == "Tikhvin"
    assert req == climate_request(st)
    with pytest.raises(ValidationError):
        req.model_copy(update={"required_output_fields": ["engineering.theta_supply_c"]}, deep=True).__class__.model_validate(
            {**req.model_dump(mode="python"), "required_output_fields": ["engineering.theta_supply_c"]}
        )


def test_resolved_physical_value_requires_provenance_and_bindable_authority():
    st = state()
    st.decisions["climate"] = decision("climate", {"settlement": "Tikhvin", "region": "Leningrad"})
    req = climate_request(st)
    with pytest.raises(ValidationError):
        ResolvedValue(
            target_authoring_field="design_conditions.outdoor_design_temperature_c",
            authored_value=AuthoredValue(status=AuthoringStatus.EXPLICIT_VALUE, value=-29.0, unit="degC"),
            authority_class="NORMATIVE_AUTHORITATIVE",
            dependency_digest=req.dependency_digest,
        )
    with pytest.raises(ValidationError):
        resolved(
            "design_conditions.outdoor_design_temperature_c",
            -29.0,
            "degC",
            req,
            authority="REFERENCE_ONLY",
        )
    with pytest.raises(ValidationError):
        resolved(
            "design_conditions.outdoor_design_temperature_c",
            -29.0,
            "degC",
            req,
            authority="MANUFACTURER_AUTHORITATIVE",
            source_type="normative_source",
        )


def test_handoff_goes_through_authoring_state_and_cannot_bypass_context():
    st = state()
    st.decisions["climate"] = decision("climate", {"settlement": "Tikhvin", "region": "Leningrad"})
    req = climate_request(st)
    result = ResolverResult(
        resolver_request_id=req.resolver_request_id,
        status="RESOLVED",
        dependency_digest=req.dependency_digest,
        values=[resolved("design_conditions.outdoor_design_temperature_c", -29.0, "degC", req)],
    )
    updated, binding = apply_resolver_result(st, req, result)
    assert updated.authoring.design_conditions["outdoor_design_temperature_c"].value == -29.0
    assert isinstance(binding, Binding)

    bad = req.model_copy(update={"room_id": "other"})
    bad = make_resolver_request(
        "CLIMATE_RESOLVER",
        "Test_01",
        "other",
        PROJECT_DIGEST,
        st.decisions,
    )
    bad_result = result.model_copy(update={
        "resolver_request_id": bad.resolver_request_id,
        "dependency_digest": bad.dependency_digest,
        "values": [
            resolved("design_conditions.outdoor_design_temperature_c", -29.0, "degC", bad)
        ],
    })
    with pytest.raises(ValueError, match="PROJECT_CONTEXT_CONFLICT"):
        apply_resolver_result(st, bad, bad_result)


def test_climate_relevant_change_invalidates_but_unrelated_change_does_not():
    st = state()
    st.decisions["climate"] = decision("climate", {"settlement": "Tikhvin", "region": "Leningrad"}, "1")
    st.decisions["fluid"] = decision("fluid", "WATER", "1")
    req = climate_request(st)
    result = ResolverResult(
        resolver_request_id=req.resolver_request_id,
        status="RESOLVED",
        dependency_digest=req.dependency_digest,
        values=[resolved("design_conditions.outdoor_design_temperature_c", -29.0, "degC", req)],
    )
    updated, binding = apply_resolver_result(st, req, result)
    same, history = replace_questionnaire_decisions_and_invalidate(
        updated,
        {"fluid": decision("fluid", "ANTIFREEZE", "2")},
        [binding],
        PROJECT_DIGEST,
    )
    assert history[0].result.status == "RESOLVED"
    assert same.authoring.design_conditions["outdoor_design_temperature_c"].value == -29.0

    stale, history = replace_questionnaire_decisions_and_invalidate(
        updated,
        {"climate": decision("climate", {"settlement": "Saint Petersburg", "region": "Leningrad"}, "2")},
        [binding],
        PROJECT_DIGEST,
    )
    assert history[0].result.status == "STALE_INPUT"
    assert stale.authoring.design_conditions["outdoor_design_temperature_c"].status == "UNSET"


def test_product_and_fluid_dependency_digests_are_targeted():
    st = state()
    st.decisions["system"] = decision("system", "CATALOG", "1")
    pipe_one = make_resolver_request("PIPE_PRODUCT_RESOLVER", "Test_01", "101DAA3", PROJECT_DIGEST, st.decisions)
    st.decisions["system"] = decision("system", "CUSTOM", "2")
    pipe_two = make_resolver_request("PIPE_PRODUCT_RESOLVER", "Test_01", "101DAA3", PROJECT_DIGEST, st.decisions)
    assert pipe_one.dependency_digest != pipe_two.dependency_digest

    st = state()
    st.decisions["fluid"] = decision("fluid", "WATER", "1")
    st.decisions["fluid.temperature"] = decision("fluid.temperature", {"value": 35.0, "unit": "degC"}, "1")
    fluid_one = make_resolver_request("FLUID_PROPERTY_RESOLVER", "Test_01", "101DAA3", PROJECT_DIGEST, st.decisions)
    st.decisions["collector"] = decision("collector", {"x_mm": 1, "y_mm": 2, "unit": "mm", "coordinate_system": "authoritative room boundary integer millimetres"}, "1")
    fluid_two = make_resolver_request("FLUID_PROPERTY_RESOLVER", "Test_01", "101DAA3", PROJECT_DIGEST, st.decisions)
    assert fluid_one.dependency_digest == fluid_two.dependency_digest
    st.decisions["fluid.temperature"] = decision("fluid.temperature", {"value": 45.0, "unit": "degC"}, "2")
    fluid_three = make_resolver_request("FLUID_PROPERTY_RESOLVER", "Test_01", "101DAA3", PROJECT_DIGEST, st.decisions)
    assert fluid_one.dependency_digest != fluid_three.dependency_digest


def test_explicit_empty_semantics_remain_authoring_decision():
    st = state()
    assert st.authoring.explicit_confirmations["exclusion_zones"].status == "UNSET"
    payload = st.authoring.model_dump(mode="python")
    payload["explicit_confirmations"]["exclusion_zones"] = {
        "status": "EXPLICIT_EMPTY",
        "value": [],
        "unit": "none",
        "provenance": {
            "source_type": "project_decision",
            "source_reference": "owner:test",
            "source_field": "exclusions",
            "author_or_confirmation": "1",
            "transformation": "questionnaire:exclusions",
            "units": "none",
        },
    }
    assert QuestionnaireState(authoring=payload).authoring.explicit_confirmations["exclusion_zones"].status == "EXPLICIT_EMPTY"


def test_ach_precedence_conflict_is_not_silent_adapter_overwrite():
    loaded = load_ufh_project_engineering_authoring_template(synthetic_complete_authoring_payload())
    assert loaded.status == "READY"
    conflicting_physics = loaded.profile.building_physics.model_copy(update={
        "air_changes_per_hour": 1.0,
    })
    profile = loaded.profile.model_copy(update={
        "building_physics": conflicting_physics,
        "provenance": {
            key: value for key, value in loaded.profile.provenance.items()
            if key not in {
                "sizing.room.insulation.floor_boundary_temperature_c",
                "sizing.room.indoor_temperature_c",
            }
        }
    })
    source = _complete_test_source().model_copy(update={
        "engineering_profile": profile,
        "sizing_inputs": None,
        "engineering_inputs": None,
        "input_provenance": {},
    })
    result = build_ufh_sizing_request_from_project_room(source)
    assert result.status in {"INVALID", "INCOMPLETE"}
    assert result.sizing_request is None
    assert any(
        d.code == "SOURCE_VALUE_CONFLICT"
        and d.path == "sizing.room.insulation.air_changes_per_hour"
        for d in result.diagnostics
    )


def test_assumption_audit_classification_is_complete_for_discovered_defaults():
    counts = assumption_audit_by_class()
    assert counts.get("SUSPICIOUS_HIDDEN_ASSUMPTION", 0) == 0
    assert counts["PROJECT_DATA_VALUE"] == 1
    assert counts["ROUTING_ALGORITHM_POLICY"] == 2
    assert counts["LEGACY_ROUTING_POLICY"] == 2
    assert counts["STRUCTURAL_SOFTWARE_DEFAULT"] >= 6
    assert {item["path"] for item in INHERITED_ASSUMPTION_AUDIT} >= {
        "sizing.room.insulation.air_changes_per_hour",
        "sizing.coverage_request.turn_radius_mm",
        "sizing.coverage_request.perimeter_priority_mode",
        "sizing.coverage_request.minimum_circuit_length_mm",
        "sizing.coverage_request.maximum_circuit_length_mm",
    }


def test_test01_question_resolver_map_covers_questionnaire_questions():
    from agent.ufh_pre_generation_questionnaire import QUESTIONS

    assert set(TEST01_QUESTION_RESOLVER_MAP) == {q.question_id for q in QUESTIONS}
    assert TEST01_QUESTION_RESOLVER_MAP["exclusions"]["handoff"] == "DIRECT_AUTHORING_UPDATE"
    assert TEST01_QUESTION_RESOLVER_MAP["climate"]["handoff"] == "CLIMATE_RESOLVER"

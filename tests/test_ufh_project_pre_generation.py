from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from agent.test01_geometry_source_authority import assess_test01_geometry_authority
from agent.ufh_pre_generation_questionnaire import Decision
from agent.ufh_project_pre_generation import (
    apply_ufh_questionnaire_answer,
    create_test01_ufh_pre_generation_session,
    profile_readiness,
    rebuild_ufh_pre_generation_session,
    replace_ufh_questionnaire_answer,
)
import agent.ufh_project_pre_generation as orchestration


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "Test_01"
IFC = ROOT.parent / "HomeAuraEngineeringAgent-ifc-research" / "manual-export"


def actual_session():
    if not (IFC / "Test_01_rooms_ifc4.ifc").is_file():
        pytest.skip("Reviewed Test_01 IFC evidence is unavailable")
    return create_test01_ufh_pre_generation_session(
        PROJECT, IFC, normative_profile="RU_CURRENT"
    )


def answer(question_id, value, revision="fixture-v1"):
    return Decision(
        question_id=question_id,
        value=value,
        source_reference="synthetic://ufh-pre-generation-test",
        revision=revision,
    )


def location(settlement, region="Ленинградская область", revision="location-v1"):
    return answer("climate", {"settlement": settlement, "region": region}, revision)


def test_actual_test01_creates_read_only_incomplete_session_with_project_bindings():
    source_hashes = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (PROJECT / "Test_01.dwg", PROJECT / "HomeAura_Test_01.mrd",
                     PROJECT / "exports" / "rooms" / "rooms.json")
    }
    session = actual_session()
    assert session.project_id == "Test_01"
    assert session.room_id == "101DAA3"
    assert session.adapter_result.room_geometry_digest
    assert session.adapter_result.status == "INCOMPLETE"
    assert session.status == "AWAITING_USER_INPUT"
    assert "climate" in {item.question_id for item in session.active_questions}
    assert len(session.active_questions) == 13
    assert session.remaining_required_engineering_fields
    assert len(session.project_context.project_owned_values.values) == 1
    ach = session.project_context.project_owned_values.values[0]
    assert ach.canonical_field_path == "sizing.room.insulation.air_changes_per_hour"
    assert ach.source_field.endswith("AirExchangeRate")
    assert not any("air_changes_per_hour" in path
                    for path in session.remaining_required_engineering_fields)
    assert profile_readiness(session).status == "INCOMPLETE"
    assert create_test01_ufh_pre_generation_session(
        PROJECT, IFC, normative_profile="RU_CURRENT"
    ).session_digest == session.session_digest
    assert source_hashes == {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source_hashes
    }


def test_climate_answer_runs_existing_resolver_and_authoring_handoff_only():
    import agent.ufh_auto_retry as retry
    import agent.floor_heating_sizing as sizing

    def forbidden(*args, **kwargs):
        raise AssertionError("Pre-generation must not execute UFH engineering")

    original_retry = retry.assess_with_automatic_split_retry
    original_sizing = sizing.size_ufh_requirement
    retry.assess_with_automatic_split_retry = forbidden
    sizing.size_ufh_requirement = forbidden
    try:
        initial = actual_session()
        updated = apply_ufh_questionnaire_answer(
            initial, location("Санкт-Петербург")
        )
    finally:
        retry.assess_with_automatic_split_retry = original_retry
        sizing.size_ufh_requirement = original_sizing

    assert len(updated.resolver_executions) == 1
    execution = updated.resolver_executions[0]
    assert execution.resolver_request.resolver_type == "CLIMATE_RESOLVER"
    assert execution.resolver_result.status == "RESOLVED"
    assert execution.resolver_result.values[0].authored_value.value == -23.0
    assert execution.resolver_result.values[0].authority_class == "PROJECT_APPROVED_NORMATIVE_EXTRACT"
    assert updated.questionnaire_state.authoring.design_conditions[
        "outdoor_design_temperature_c"
    ].value == -23.0
    assert "climate" not in {item.question_id for item in updated.active_questions}
    assert updated.status == "AWAITING_USER_INPUT"
    assert profile_readiness(updated).status == "INCOMPLETE"
    assert "climate" not in actual_session().questionnaire_state.decisions


@pytest.mark.parametrize(
    ("settlement", "expected", "diagnostic"),
    [
        ("Тихвин", "RESOLVED", None),
        ("Нет такого города", "NOT_FOUND", "CLIMATE_LOCALITY_NOT_FOUND"),
        ("Ленинградская область", "INSUFFICIENT_INPUT", "LOCALITY_REQUIRED_FOR_REGION"),
    ],
)
def test_climate_lookup_failure_or_success_is_typed_and_non_corrupting(
    settlement, expected, diagnostic
):
    initial = actual_session()
    updated = apply_ufh_questionnaire_answer(initial, location(settlement))
    execution = updated.resolver_executions[-1]
    assert execution.resolver_result.status == expected
    if diagnostic:
        assert diagnostic in execution.resolver_result.diagnostics
        assert "climate" in {item.question_id for item in updated.active_questions}
        assert updated.questionnaire_state.authoring.design_conditions[
            "outdoor_design_temperature_c"
        ].status == "UNSET"
    else:
        assert "climate" not in {item.question_id for item in updated.active_questions}


def test_climate_correction_invalidates_old_binding_and_re_resolves():
    initial = actual_session()
    first = apply_ufh_questionnaire_answer(initial, location("Санкт-Петербург"))
    second = replace_ufh_questionnaire_answer(
        first, location("Тихвин", revision="location-v2")
    )
    assert second.questionnaire_state.authoring.design_conditions[
        "outdoor_design_temperature_c"
    ].value == -30.0
    assert second.resolver_executions[-1].resolver_request.dependency_digest != (
        first.resolver_executions[0].resolver_request.dependency_digest
    )
    assert second.resolver_executions[-1].resolver_result.status == "RESOLVED"
    assert any(binding.result.status == "STALE_INPUT" for binding in second.bindings)


def test_unknown_location_can_be_corrected_without_corrupting_session():
    initial = actual_session()
    failed = apply_ufh_questionnaire_answer(initial, location("Неизвестный город"))
    corrected = apply_ufh_questionnaire_answer(
        failed, location("Санкт-Петербург", revision="location-v2")
    )
    assert failed.resolver_executions[-1].resolver_result.status == "NOT_FOUND"
    assert corrected.resolver_executions[-1].resolver_result.status == "RESOLVED"
    assert corrected.questionnaire_state.authoring.design_conditions[
        "outdoor_design_temperature_c"
    ].value == -23.0
    assert initial.questionnaire_state.decisions == {}


def test_unrelated_answer_does_not_invalidate_climate_and_identical_replay_is_idempotent():
    initial = actual_session()
    first = apply_ufh_questionnaire_answer(initial, location("Санкт-Петербург"))
    replay = apply_ufh_questionnaire_answer(first, location("Санкт-Петербург"))
    assert replay.session_digest == first.session_digest
    floor = apply_ufh_questionnaire_answer(first, answer("finish", "TILE_STONE"))
    assert floor.bindings[0].result.status == "RESOLVED"
    assert floor.bindings[0].request.dependency_digest == first.bindings[0].request.dependency_digest


def test_project_revision_refreshes_bindings_but_preserves_user_answer():
    initial = actual_session()
    first = apply_ufh_questionnaire_answer(initial, location("Санкт-Петербург"))
    decision = assess_test01_geometry_authority(PROJECT, IFC)
    changed_source = decision.ufh_source.model_copy(update={"source_sha256": "2" * 64})
    refreshed = rebuild_ufh_pre_generation_session(first, changed_source)
    assert refreshed.questionnaire_state.decisions["climate"].value["settlement"] == "Санкт-Петербург"
    assert refreshed.project_revision != first.project_revision
    assert refreshed.resolver_executions[-1].resolver_result.status == "RESOLVED"
    assert refreshed.questionnaire_state.authoring.design_conditions[
        "outdoor_design_temperature_c"
    ].status == "EXPLICIT_VALUE"


def test_unsupported_resolver_is_exposed_without_fabricated_values():
    initial = actual_session()
    updated = apply_ufh_questionnaire_answer(
        initial, answer("below", "GROUND")
    )
    result = updated.resolver_executions[-1].resolver_result
    assert result.status == "RESOLVED"
    assert result.values[0].target_authoring_field == "thermal_boundary_conditions.below"
    assert updated.questionnaire_state.authoring.thermal_boundary_conditions[
        "below"
    ].value["boundary_type"] == "GROUND"
    assert updated.questionnaire_state.authoring.design_conditions[
        "floor_boundary_temperature_c"
    ].status == "UNSET"


def test_authoring_conflict_is_reported_and_never_silently_overwritten(monkeypatch):
    session = actual_session()

    def conflict(*args, **kwargs):
        raise ValueError("AUTHORING_SOURCE_CONFLICT")

    monkeypatch.setattr(orchestration, "apply_resolver_result", conflict)
    updated = apply_ufh_questionnaire_answer(
        session, location("Санкт-Петербург")
    )
    assert "AUTHORING_SOURCE_CONFLICT" in updated.diagnostics
    assert updated.questionnaire_state.authoring.design_conditions[
        "outdoor_design_temperature_c"
    ].status == "UNSET"

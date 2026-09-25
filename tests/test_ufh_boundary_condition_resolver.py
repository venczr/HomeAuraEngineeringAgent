from __future__ import annotations

import pytest

from agent.ufh_boundary_condition_resolver import ThermalBoundaryCondition
from agent.ufh_project_pre_generation import (
    apply_ufh_questionnaire_answer,
    replace_ufh_questionnaire_answer,
)
from tests.test_ufh_project_pre_generation import actual_session, answer, location


def side_answer(side, value, revision="boundary-v1"):
    return answer(side, value, revision)


def read_condition(session, side):
    value = session.questionnaire_state.authoring.thermal_boundary_conditions[side].value
    return ThermalBoundaryCondition.model_validate(value)


def test_heated_below_and_above_are_independent_semantic_results_without_temperatures():
    initial = actual_session()
    below = apply_ufh_questionnaire_answer(
        initial, side_answer("below", "HEATED_ROOM")
    )
    below_condition = read_condition(below, "below")
    assert below_condition.boundary_side == "BELOW"
    assert below_condition.boundary_type == "HEATED_INTERIOR_SPACE"
    assert below_condition.adjacent_zone_id is None
    assert "ADJACENT_ZONE_DESIGN_TEMPERATURE_REQUIRED" in below_condition.dependency_requirements
    assert "below" not in {question.question_id for question in below.active_questions}
    assert "above" in {question.question_id for question in below.active_questions}
    assert below.questionnaire_state.authoring.design_conditions[
        "floor_boundary_temperature_c"
    ].status == "UNSET"

    both = apply_ufh_questionnaire_answer(
        below, side_answer("above", "HEATED_ROOM")
    )
    assert read_condition(both, "above").boundary_type == "HEATED_INTERIOR_SPACE"
    assert both.questionnaire_state.authoring.design_conditions[
        "ceiling_boundary_temperature_c"
    ].status == "UNSET"
    assert both.status != "READY_FOR_ENGINEERING"


def test_unheated_basement_requires_temperature_method_without_default():
    initial = actual_session()
    resolved = apply_ufh_questionnaire_answer(
        initial, side_answer("below", "UNHEATED_BASEMENT")
    )
    condition = read_condition(resolved, "below")
    assert condition.boundary_type == "UNHEATED_INTERIOR_SPACE"
    assert condition.requires_explicit_temperature
    assert "UNHEATED_SPACE_REFERENCE_TEMPERATURE_OR_NORMATIVE_METHOD_REQUIRED" in condition.dependency_requirements
    assert resolved.questionnaire_state.authoring.design_conditions[
        "floor_boundary_temperature_c"
    ].status == "UNSET"
    assert "below.details" in {question.question_id for question in resolved.active_questions}

    described = apply_ufh_questionnaire_answer(
        resolved, side_answer("below.details", "project specifies an unheated basement")
    )
    assert read_condition(described, "below").boundary_type == "UNHEATED_INTERIOR_SPACE"
    assert "below.details" not in {question.question_id for question in described.active_questions}
    assert described.questionnaire_state.authoring.design_conditions[
        "floor_boundary_temperature_c"
    ].status == "UNSET"


@pytest.mark.parametrize(
    ("answer_value", "expected_type"),
    [("GROUND", "GROUND"), ("VENTILATED_VOID", "VENTILATED_VOID"),
     ("OTHER", "UNKNOWN_PROJECT_SPECIFIC")],
)
def test_ground_ventilated_void_and_unknown_remain_distinct(answer_value, expected_type):
    session = apply_ufh_questionnaire_answer(
        actual_session(), side_answer("below", answer_value)
    )
    condition = read_condition(session, "below")
    assert condition.boundary_type == expected_type
    assert condition.thermal_reference_kind != "CLIMATE_DESIGN_TEMPERATURE"
    assert condition.requires_construction_assembly
    assert session.questionnaire_state.authoring.design_conditions[
        "floor_boundary_temperature_c"
    ].status == "UNSET"
    if answer_value == "GROUND":
        assert "GROUND_BOUNDARY_MODEL_REQUIRED" in condition.dependency_requirements
    if answer_value == "VENTILATED_VOID":
        assert "VENTILATED_VOID_THERMAL_METHOD_REQUIRED" in condition.dependency_requirements
    if answer_value == "OTHER":
        assert "below.details" in {q.question_id for q in session.active_questions}


def test_outdoor_boundary_tracks_climate_dependency_without_copying_temperature():
    initial = actual_session()
    outdoor = apply_ufh_questionnaire_answer(
        initial, side_answer("below", "OUTDOOR")
    )
    first = read_condition(outdoor, "below")
    assert first.boundary_type == "OUTDOOR_AIR"
    assert first.may_use_climate_design_temperature
    assert first.climate_dependency_digest
    assert "CLIMATE_DESIGN_CONDITION_REQUIRED" in first.dependency_requirements
    assert outdoor.questionnaire_state.authoring.design_conditions[
        "floor_boundary_temperature_c"
    ].status == "UNSET"

    with_climate = apply_ufh_questionnaire_answer(
        outdoor, location("Санкт-Петербург")
    )
    second = read_condition(with_climate, "below")
    assert second.boundary_type == first.boundary_type
    assert second.climate_dependency_digest != first.climate_dependency_digest
    assert "CLIMATE_DESIGN_CONDITION_DEPENDENCY_TRACKED" in second.dependency_requirements
    assert with_climate.questionnaire_state.authoring.design_conditions[
        "outdoor_design_temperature_c"
    ].value == -23.0
    assert with_climate.questionnaire_state.authoring.design_conditions[
        "floor_boundary_temperature_c"
    ].status == "UNSET"


def test_side_specific_invalidation_and_unrelated_stability():
    session = actual_session()
    session = apply_ufh_questionnaire_answer(
        session, side_answer("below", "HEATED_ROOM")
    )
    session = apply_ufh_questionnaire_answer(
        session, side_answer("above", "HEATED_ROOM")
    )
    above_before = next(b for b in session.bindings
                        if b.request.resolver_context.get("boundary_side") == "ABOVE")
    finish = apply_ufh_questionnaire_answer(
        session, answer("finish", "TILE_STONE")
    )
    above_after_finish = next(b for b in finish.bindings
                              if b.request.resolver_context.get("boundary_side") == "ABOVE")
    assert above_after_finish.request.dependency_digest == above_before.request.dependency_digest

    changed = replace_ufh_questionnaire_answer(
        finish, side_answer("below", "GROUND", revision="boundary-v2")
    )
    above_after = next(b for b in changed.bindings
                       if b.request.resolver_context.get("boundary_side") == "ABOVE")
    below_after = next(b for b in changed.bindings
                       if b.request.resolver_context.get("boundary_side") == "BELOW")
    assert above_after.request.dependency_digest == above_before.request.dependency_digest
    assert above_after.result.status == "RESOLVED"
    assert below_after.request.dependency_digest != above_before.request.dependency_digest
    assert read_condition(changed, "below").boundary_type == "GROUND"


def test_climate_change_rebinds_outdoor_side_but_preserves_heated_side():
    session = apply_ufh_questionnaire_answer(
        actual_session(), side_answer("below", "OUTDOOR")
    )
    session = apply_ufh_questionnaire_answer(
        session, side_answer("above", "HEATED_ROOM")
    )
    above_before = next(b for b in session.bindings
                        if b.request.resolver_context.get("boundary_side") == "ABOVE")
    first_outdoor = next(b for b in session.bindings
                         if b.request.resolver_context.get("boundary_side") == "BELOW")
    changed = apply_ufh_questionnaire_answer(
        session, location("Санкт-Петербург")
    )
    changed = replace_ufh_questionnaire_answer(
        changed, location("Тихвин", revision="climate-v2")
    )
    above_after = next(b for b in changed.bindings
                       if b.request.resolver_context.get("boundary_side") == "ABOVE")
    second_outdoor = next(b for b in reversed(changed.bindings)
                          if b.request.resolver_context.get("boundary_side") == "BELOW"
                          and b.result.status == "RESOLVED")
    assert above_after.request.dependency_digest == above_before.request.dependency_digest
    assert second_outdoor.request.dependency_digest != first_outdoor.request.dependency_digest
    assert read_condition(changed, "below").boundary_type == "OUTDOOR_AIR"
    assert changed.questionnaire_state.authoring.design_conditions[
        "floor_boundary_temperature_c"
    ].status == "UNSET"


def test_boundary_resolver_dependency_is_deterministic_and_test01_has_no_answer():
    first = actual_session()
    second = actual_session()
    assert first.session_digest == second.session_digest
    resolved_a = apply_ufh_questionnaire_answer(
        first, side_answer("above", "VENTILATED_VOID")
    )
    resolved_b = apply_ufh_questionnaire_answer(
        second, side_answer("above", "VENTILATED_VOID")
    )
    assert resolved_a.session_digest == resolved_b.session_digest
    assert "above" not in first.questionnaire_state.decisions
    assert read_condition(resolved_a, "above").boundary_type == "VENTILATED_VOID"

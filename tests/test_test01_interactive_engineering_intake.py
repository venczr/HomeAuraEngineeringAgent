from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from agent.test01_interactive_engineering_intake import (
    EngineeringAnswerSubmission,
    apply_engineering_intake_answer,
    answer_store_path,
    answer_and_persist_engineering_intake,
    clear_engineering_intake_answer,
    create_test01_engineering_intake_session,
    detect_source_user_input_conflict,
    load_engineering_intake_artifact,
    persist_engineering_intake_session,
    replace_engineering_intake_answer,
)
from agent.test01_sp60_engineering_binding import build_test01_sp60_engineering_binding


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects/Test_01"
IFC = ROOT.parent / "HomeAuraEngineeringAgent-ifc-research/manual-export"
STAMP = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


def _tree_digest(root: Path) -> str:
    parts = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            parts.append(path.relative_to(root).as_posix() + "\0" + hashlib.sha256(path.read_bytes()).hexdigest())
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


@pytest.fixture(scope="module")
def session():
    if not (IFC / "Test_01_rooms_ifc4.ifc").is_file():
        pytest.skip("reviewed IFC companion unavailable")
    return create_test01_engineering_intake_session(PROJECT, IFC)


def _answer(session, question_id, value):
    return apply_engineering_intake_answer(session, EngineeringAnswerSubmission(
        question_id=question_id, value=value, answered_at=STAMP,
        source_reference="approved project intake record / test fixture",
    ))


def test_initial_session_reuses_real_binding_and_has_at_most_ten_top_level_questions(session):
    assert (session.project_id, session.room_id) == ("Test_01", "101DAA3")
    assert session.source_binding.authority_status == "AUTHORITATIVE"
    assert len(session.current_questions) == 10
    assert session.status == "INCOMPLETE"
    assert session.dashboard["GEOMETRY"].status == "READY"
    assert session.dashboard["CLIMATE"].status == "BLOCKED"
    assert session.dashboard["UFH_HANDOFF"].status == "BLOCKED"
    assert session.pre_generation_session.status != "READY_FOR_ENGINEERING"


def test_missing_authority_inputs_remain_typed_blockers(session):
    assert session.status == "INCOMPLETE"
    assert session.engineering_profile_status == "INCOMPLETE"
    assert session.unresolved_source_groups
    assert set(session.unresolved_source_groups) >= {
        "CLIMATE_LOCALITY",
        "OUTDOOR_DESIGN_TEMPERATURE",
        "THERMAL_BOUNDARY_INVENTORY",
        "BOUNDARY_SEMANTICS",
        "OPENING_INVENTORY",
        "CONSTRUCTION_ASSEMBLIES",
        "U_VALUES",
        "DESIGN_VENTILATION_AIRFLOW",
        "VENTILATION_AIRFLOW_SEMANTICS",
        "INFILTRATION_ELEMENT_INVENTORY",
        "THERMAL_BRIDGES",
    }
    assert session.dashboard["SP60_ROOM_LOAD"].status == "BLOCKED"
    assert session.dashboard["UFH_HANDOFF"].status == "BLOCKED"
    assert all(
        session.dashboard[group].status in {"BLOCKED", "PARTIAL"}
        for group in (
            "CLIMATE", "BOUNDARIES", "OPENINGS", "CONSTRUCTIONS",
            "VENTILATION", "INFILTRATION", "QMTS", "TRANSMISSION",
        )
    )


def test_four_wall_candidates_have_stable_ui_geometry_but_no_thermal_promotion(session):
    question = next(q for q in session.current_questions if q.question_id == "wall.boundaries")
    candidates = question.ui_context["candidates"]
    assert [item["boundary_id"] for item in candidates] == [
        "boundary-A", "boundary-B", "boundary-C", "boundary-D"]
    assert all(len(item["endpoints_mm"]) == 2 and item["length_mm"] > 0 for item in candidates)
    assert all(item["geometry_source_digest"] for item in candidates)
    assert all("candidate only" in item["candidate_source"] for item in candidates)
    assert session.dashboard["BOUNDARIES"].status == "BLOCKED"


def test_climate_answer_uses_existing_sp131_resolver_and_replacement_invalidates_old_result(session):
    resolved = _answer(session, "climate", {"settlement": "Санкт-Петербург", "region": "Ленинградская область"})
    assert "climate" not in {q.question_id for q in resolved.current_questions}
    assert resolved.dashboard["CLIMATE"].status == "READY"
    assert "CLIMATE_LOCALITY" not in resolved.unresolved_source_groups
    assert "OUTDOOR_DESIGN_TEMPERATURE" not in resolved.unresolved_source_groups
    climate = [e for e in resolved.pre_generation_session.resolver_executions
               if e.resolver_request.resolver_type == "CLIMATE_RESOLVER"]
    assert climate[-1].resolver_result.status == "RESOLVED"
    assert Decimal(str(climate[-1].resolver_result.values[0].authored_value.value)) == Decimal("-23")
    replaced = replace_engineering_intake_answer(resolved, EngineeringAnswerSubmission(
        question_id="climate", value={"settlement": "Выборг", "region": "Ленинградская область"},
        answered_at=STAMP, source_reference="approved locality decision revision 2"))
    results = [e.resolver_result for e in replaced.pre_generation_session.resolver_executions
               if e.resolver_request.resolver_type == "CLIMATE_RESOLVER"]
    assert results[-1].status == "RESOLVED"
    assert Decimal(str(results[-1].values[0].authored_value.value)) == Decimal("-26")
    assert all(Decimal(str(value.authored_value.value)) != Decimal("-23") for value in results[-1].values)
    assert any(item.resolver_type == "CLIMATE_RESOLVER"
               and item.reason == "PARENT_ANSWER_CHANGED_OR_CLEARED"
               for item in replaced.stale_resolver_results)
    assert replaced.session_digest != resolved.session_digest
    assert replaced.status == "INCOMPLETE"


def test_unknown_location_stays_actionable_and_does_not_corrupt_session(session):
    result = _answer(session, "climate", {"settlement": "Несуществующий город", "region": "Ленинградская область"})
    assert "climate" in {q.question_id for q in result.current_questions}
    climate = [e for e in result.pre_generation_session.resolver_executions
               if e.resolver_request.resolver_type == "CLIMATE_RESOLVER"][-1]
    assert climate.resolver_result.status == "NOT_FOUND"
    assert result.status == "INCOMPLETE"
    assert result.pre_generation_session.status != "INVALID"


def test_question_dependencies_stale_descendants_and_unrelated_climate_stability(session):
    use = _answer(session, "room.use", "LIVING_ROOM")
    assert "room.qmts_process" in {q.question_id for q in use.current_questions}
    process = _answer(use, "room.qmts_process", "NO")
    replaced = replace_engineering_intake_answer(process, EngineeringAnswerSubmission(
        question_id="room.use", value="BEDROOM", answered_at=STAMP,
        source_reference="approved room-use revision 2"))
    assert any(a.question_id == "room.qmts_process" and a.validation_status == "STALE"
               for a in replaced.stale_answers)
    assert "room.qmts_process" in {q.question_id for q in replaced.current_questions}
    climate_ready = _answer(session, "climate", {"settlement": "Санкт-Петербург", "region": "Ленинградская область"})
    qmts_update = _answer(climate_ready, "room.use", "KITCHEN")
    climate_results = [e.resolver_result for e in qmts_update.pre_generation_session.resolver_executions
                       if e.resolver_request.resolver_type == "CLIMATE_RESOLVER"]
    assert climate_results[-1].status == "RESOLVED"
    assert Decimal(str(climate_results[-1].values[0].authored_value.value)) == Decimal("-23")


def test_clear_locality_removes_derived_temperature_and_reactivates_question(session):
    resolved = _answer(session, "climate", {"settlement": "Санкт-Петербург", "region": "Ленинградская область"})
    cleared = clear_engineering_intake_answer(resolved, "climate")
    assert "climate" in {q.question_id for q in cleared.current_questions}
    assert cleared.dashboard["CLIMATE"].status == "BLOCKED"
    value = cleared.pre_generation_session.questionnaire_state.authoring.design_conditions.get("outdoor_design_temperature_c")
    assert value is None or value.status == "UNSET"
    assert any(item.question_id == "climate" and item.validation_status == "STALE"
               for item in cleared.stale_answers)


def test_openings_none_is_explicit_answer_not_silence(session):
    result = _answer(session, "openings.inventory", "NONE")
    answer = result.answers["openings.inventory"]
    assert answer.authority_class == "PROJECT_APPROVED_USER_INPUT"
    assert answer.source_type == "user_project_decision"
    assert answer.validation_status == "VALID"
    assert result.opening_inventory_status == "COMPLETE_EMPTY"
    assert result.dashboard["OPENINGS"].status == "PARTIAL"
    assert "opening" in result.dashboard["OPENINGS"].reason.casefold()


def test_manual_construction_and_ventilation_are_branching_and_fail_closed(session):
    construction = _answer(session, "construction.mode", "ENTER_LAYERS_MANUALLY")
    assert "construction.details" in {q.question_id for q in construction.current_questions}
    ventilation = _answer(session, "ventilation.mode", "BALANCED_SUPPLY_EXTRACT")
    question = next(q for q in ventilation.current_questions if q.question_id == "ventilation.design_basis")
    observations = question.ui_context["project_observations"]
    assert observations["AirExchangeRate"]["authority"] == "PROJECT_OBSERVATION_ONLY"
    assert question.ui_context["never_auto_promote"] is True
    with pytest.raises(ValueError, match="USER_CANNOT_ASSERT_EXTERNAL_OR_NORMATIVE_AUTHORITY"):
        _answer(ventilation, "ventilation.design_basis", {
            "mode": "PROJECT_DESIGN_AIRFLOW", "source_reference": "invented",
            "source_field": "L", "authority_class": "NORMATIVE_AUTHORITATIVE"})


def test_parent_change_invalidates_resolver_and_does_not_leave_stale_climate_binding(session):
    resolved = _answer(session, "climate", {"settlement": "Санкт-Петербург", "region": "Ленинградская область"})
    changed = replace_engineering_intake_answer(resolved, EngineeringAnswerSubmission(
        question_id="climate", value={"settlement": "Тихвин", "region": "Ленинградская область"},
        answered_at=STAMP, source_reference="approved locality revision"))
    latest = [e for e in changed.pre_generation_session.resolver_executions
              if e.resolver_request.resolver_type == "CLIMATE_RESOLVER"][-1]
    assert Decimal(str(latest.resolver_result.values[0].authored_value.value)) == Decimal("-30")
    authored = changed.pre_generation_session.questionnaire_state.authoring.design_conditions["outdoor_design_temperature_c"]
    assert Decimal(str(authored.value)) == Decimal("-30")


def test_persistence_is_schema_versioned_atomic_and_separate_from_project_sources(session, tmp_path):
    answered = _answer(session, "room.use", "OFFICE")
    root = tmp_path / "project"
    root.mkdir()
    artifact = persist_engineering_intake_session(answered, root, expected_artifact_digest=None)
    path = answer_store_path(root)
    assert path.relative_to(root).as_posix() == "engineering/ufh_engineering_intake_v1.json"
    assert artifact.schema_version == "1.0"
    reread = load_engineering_intake_artifact(root, session.source_binding)
    assert reread is not None and reread.artifact_digest == artifact.artifact_digest
    assert reread.answers["room.use"].authority_class == "PROJECT_APPROVED_USER_INPUT"
    with pytest.raises(ValueError, match="INTAKE_ARTIFACT_REVISION_CONFLICT"):
        persist_engineering_intake_session(answered, root, expected_artifact_digest=None)
    persist_engineering_intake_session(answered, root, expected_artifact_digest=artifact.artifact_digest)


def test_source_user_conflict_preserves_both_claims():
    conflict = detect_source_user_input_conflict(
        project_id="Test_01", room_id="101DAA3", field_path="x",
        project_value=1.0, user_value=2.0, project_source_reference="rooms.json#x",
        user_source_reference="user decision",
    )
    assert conflict is not None
    assert conflict.code == "PROJECT_SOURCE_USER_INPUT_CONFLICT"
    assert conflict.authoritative_project_value == 1.0
    assert conflict.user_value == 2.0
    assert detect_source_user_input_conflict(
        project_id="Test_01", room_id="101DAA3", field_path="x",
        project_value=1, user_value=1, project_source_reference="p", user_source_reference="u") is None


def test_conflicting_user_claim_is_retained_without_overwriting_project_owned_value(session):
    ventilation = _answer(session, "ventilation.mode", "NATURAL")
    conflicted = _answer(ventilation, "ventilation.design_basis", {
        "mode": "DESIGN_ACH", "value": 2.0, "units": "1/h",
        "confirmed_winter_design_rate": True, "source_reference": "user approved design",
        "source_field": "n", "field_path": "sizing.room.insulation.air_changes_per_hour",
    })
    assert conflicted.answers["ventilation.design_basis"].validation_status == "CONFLICT"
    assert conflicted.conflicts[0].code == "PROJECT_SOURCE_USER_INPUT_CONFLICT"
    assert conflicted.conflicts[0].authoritative_project_value != conflicted.conflicts[0].user_value
    assert conflicted.dashboard["VENTILATION"].status == "BLOCKED"


def test_answer_and_persist_commits_only_after_valid_answer(session, tmp_path):
    root = tmp_path / "separate-project-store"
    root.mkdir()
    updated, artifact = answer_and_persist_engineering_intake(
        session, EngineeringAnswerSubmission(question_id="room.use", value="CORRIDOR",
        answered_at=STAMP, source_reference="approved room schedule"), root,
        expected_artifact_digest=None)
    assert updated.answers["room.use"].normalized_value == "CORRIDOR"
    assert artifact.answers["room.use"].validation_status == "VALID"
    assert answer_store_path(root).is_file()
    previous_bytes = answer_store_path(root).read_bytes()
    with pytest.raises(ValueError, match="QUESTION_NOT_ACTIVE"):
        answer_and_persist_engineering_intake(
            updated, EngineeringAnswerSubmission(question_id="not.active", value="x"), root,
            expected_artifact_digest=artifact.artifact_digest)
    assert answer_store_path(root).read_bytes() == previous_bytes


def test_repeatable_answers_have_same_state_digest_and_project_files_remain_unchanged(session):
    before = _tree_digest(PROJECT)
    first = _answer(session, "room.use", "BEDROOM")
    second = _answer(session, "room.use", "BEDROOM")
    assert first.session_digest == second.session_digest
    assert first.dependency_digest == second.dependency_digest
    assert _tree_digest(PROJECT) == before
    assert first.status == "INCOMPLETE"
    assert first.dashboard["SP60_ROOM_LOAD"].status == "BLOCKED"


def test_answer_timestamp_is_audit_metadata_not_an_engineering_dependency(session):
    first = apply_engineering_intake_answer(session, EngineeringAnswerSubmission(
        question_id="room.use", value="BEDROOM", answered_at=datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc),
        source_reference="approved room-use decision"))
    second = apply_engineering_intake_answer(session, EngineeringAnswerSubmission(
        question_id="room.use", value="BEDROOM", answered_at=datetime(2026, 9, 15, 11, 0, tzinfo=timezone.utc),
        source_reference="approved room-use decision"))
    assert first.answers["room.use"].answered_at != second.answers["room.use"].answered_at
    assert first.answers["room.use"].dependency_digest == second.answers["room.use"].dependency_digest
    assert first.session_digest == second.session_digest


def test_intake_never_invokes_sp60_or_ufh_calculation(session, monkeypatch):
    import agent.building_heat_loss as transmission
    import agent.ventilation_infiltration_heat_loss as air
    import agent.sp60_room_design_heating_load as load
    import agent.floor_heating_sizing as sizing
    import agent.ufh_engineering_kernel as kernel

    def forbidden(*args, **kwargs):
        raise AssertionError("intake must not run physical calculation")

    monkeypatch.setattr(transmission, "calculate_room_transmission", forbidden)
    monkeypatch.setattr(air, "calculate_room_ventilation_heat_loss", forbidden)
    monkeypatch.setattr(air, "calculate_room_infiltration_heat_loss", forbidden)
    monkeypatch.setattr(load, "aggregate_sp60_room_design_heating_load", forbidden)
    monkeypatch.setattr(sizing, "size_ufh_requirement", forbidden)
    monkeypatch.setattr(kernel, "evaluate", forbidden)
    result = _answer(session, "climate", {"settlement": "Санкт-Петербург", "region": "Ленинградская область"})
    assert result.status == "INCOMPLETE"

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from agent.test01_sp60_engineering_binding import build_test01_sp60_engineering_binding


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects/Test_01"
IFC = ROOT.parent / "HomeAuraEngineeringAgent-ifc-research/manual-export"


def _tree_digest(root: Path) -> str:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            rows.append(f"{relative}\0{hashlib.sha256(path.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


@pytest.fixture(scope="module")
def binding():
    if not (IFC / "Test_01_rooms_ifc4.ifc").is_file():
        pytest.skip("Reviewed external Test_01 IFC source unavailable")
    return build_test01_sp60_engineering_binding(PROJECT, IFC)


def _by_id(binding):
    return {item.input_id: item for item in binding.input_matrix}


def test_binds_only_target_room_and_existing_authoritative_identity(binding):
    assert (binding.project_id, binding.room_id, binding.room_code) == ("Test_01", "101DAA3", "101")
    assert binding.authority_status == "AUTHORITATIVE"
    identity = _by_id(binding)["IDENTITY"]
    assert identity.status == "RESOLVED"
    assert identity.value["building_id"] == "1kDE4UYl903ebi3UdgvjXG"
    assert identity.value["level_id"] == "0oQei_Jnn60QnqOIJ3NBzE"
    assert binding.adapter_status == "INCOMPLETE"
    assert binding.adapter_missing_input_count == 41


def test_geometry_area_height_volume_and_indoor_temperature_are_provenance_bound(binding):
    matrix = _by_id(binding)
    assert matrix["ROOM_BOUNDARY_GEOMETRY"].status == "RESOLVED"
    assert matrix["ROOM_AREA"].status == "RESOLVED"
    area = matrix["ROOM_AREA"].value
    assert float(area["net_area_m2"]) == pytest.approx(17.231460571289062)
    assert float(area["authoritative_boundary_contour_area_m2"]) == pytest.approx(17.321458459647975)
    assert matrix["ROOM_PERIMETER"].status == "DERIVED"
    assert float(matrix["ROOM_PERIMETER"].value) == pytest.approx(16.76796776)
    assert matrix["ROOM_HEIGHT"].status == "RESOLVED"
    assert matrix["ROOM_HEIGHT"].value == 2800.0
    assert matrix["ROOM_VOLUME"].status == "DERIVED"
    assert float(matrix["ROOM_VOLUME"].value) == pytest.approx(
        float(matrix["ROOM_AREA"].value["net_area_m2"]) * 2.8)
    assert {item.source_field for item in matrix["ROOM_VOLUME"].evidence} == {
        "$.Rooms[].NetAreaM2", "$.Rooms[].RoomHeightMm"}
    assert matrix["INDOOR_DESIGN_TEMPERATURE"].status == "RESOLVED"
    assert matrix["INDOOR_DESIGN_TEMPERATURE"].value == 20.0
    assert matrix["ROOM_USE"].status == "UNRESOLVED"


def test_geometry_candidates_do_not_become_thermal_semantics_or_areas(binding):
    matrix = _by_id(binding)
    candidates = matrix["THERMAL_BOUNDARY_INVENTORY"]
    assert candidates.status == "UNRESOLVED"
    assert candidates.value["candidate_count"] == 4
    assert candidates.value["ifc_relationships_present"] is False
    assert matrix["BOUNDARY_SEMANTICS"].status == "UNRESOLVED"
    assert matrix["BOUNDARY_AREAS"].status == "BLOCKED_BY_PARENT_DEPENDENCY"
    assert "height" in matrix["BOUNDARY_AREAS"].reason


def test_no_opening_absence_or_construction_is_inferred(binding):
    matrix = _by_id(binding)
    assert matrix["OPENING_INVENTORY"].status == "UNRESOLVED"
    assert matrix["OPENING_INVENTORY"].value == {
        "ifc_opening_types_present": False,
        "dwg_window_door_objects_present": False,
    }
    assert matrix["CONSTRUCTION_ASSEMBLIES"].status == "UNRESOLVED"
    assert matrix["U_VALUES"].status == "BLOCKED_BY_PARENT_DEPENDENCY"
    assert matrix["THERMAL_BRIDGES"].status == "BLOCKED_BY_PARENT_DEPENDENCY"


def test_climate_ventilation_infiltration_and_qmts_remain_fail_closed(binding):
    matrix = _by_id(binding)
    assert matrix["CLIMATE_LOCALITY"].status == "UNRESOLVED"
    assert matrix["OUTDOOR_DESIGN_TEMPERATURE"].status == "BLOCKED_BY_PARENT_DEPENDENCY"
    assert matrix["DESIGN_VENTILATION_AIRFLOW"].status == "UNRESOLVED"
    assert matrix["VENTILATION_AIRFLOW_SEMANTICS"].status == "UNRESOLVED"
    assert matrix["PROJECT_ACH"].status == "RESOLVED"
    assert matrix["PROJECT_ACH"].value == pytest.approx(1.0714285373687744)
    assert matrix["PROJECT_ACH"].units == "1/h"
    assert "not promoted" in matrix["PROJECT_ACH"].reason
    assert matrix["BUILDING_HEIGHT"].status == "UNRESOLVED"
    assert matrix["DESIGN_WIND"].status == "BLOCKED_BY_PARENT_DEPENDENCY"
    assert matrix["AERODYNAMIC_MODEL"].status == "UNRESOLVED"
    assert matrix["PRESSURE_MODE"].status == "UNRESOLVED"
    assert matrix["QMTS_APPLICABILITY"].status == "UNRESOLVED"
    assert binding.readiness.resolved_input_count == sum(
        item.status == "RESOLVED" for item in binding.input_matrix)
    assert binding.readiness.derived_input_count == sum(
        item.status == "DERIVED" for item in binding.input_matrix)
    assert binding.readiness.unresolved_input_count == sum(
        item.status == "UNRESOLVED" for item in binding.input_matrix)
    assert binding.readiness.blocked_input_count == sum(
        item.status == "BLOCKED_BY_PARENT_DEPENDENCY" for item in binding.input_matrix)
    assert len(binding.readiness.blocking_dependency_groups) == 6


def test_minimum_question_set_is_collapsed_and_reuses_existing_question_ids(binding):
    from agent.ufh_pre_generation_questionnaire import Question

    questions = binding.minimum_required_input_set.questions
    assert len(questions) == 8
    by_id = {item.question_id: item for item in questions}
    assert by_id["sp60.climate.locality"].reuses_question_id == "climate"
    assert by_id["sp60.boundary.below"].reuses_question_id == "below"
    assert by_id["sp60.boundary.above"].reuses_question_id == "above"
    assert by_id["sp60.openings.inventory"].reuses_question_id is None
    assert by_id["sp60.envelope.construction_sources"].reuses_question_id == "envelope"
    assert all(len(question.prompt) > 25 for question in questions)
    assert "lambda" not in " ".join(question.prompt.casefold() for question in questions)
    assert binding.minimum_required_input_set.deferred_conditional_inputs
    ui_questions = binding.minimum_required_input_set.as_questionnaire_questions()
    assert all(isinstance(question, Question) for question in ui_questions)
    assert len(ui_questions) == len(questions)
    assert {question.question_id for question in ui_questions} >= {
        "climate", "below", "above", "envelope", "sp60.openings.inventory"}
    assert next(question for question in ui_questions
                if question.question_id == "sp60.openings.inventory").answer_type == "choice"
    assert {"PROJECT_INVENTORY", "EXPLICIT_NONE", "UNKNOWN"} <= set(
        next(question for question in ui_questions
             if question.question_id == "sp60.openings.inventory").allowed_options)
    insulation_rule = next(rule for rule in binding.minimum_required_input_set.dependency_rules
                           if "INSULATION_LAYER_PRESENT" in rule.when_answers)
    assert insulation_rule.trigger_kind == "RESOLVER_RESULT"


def test_project_profile_and_questionnaire_answer_inventory_is_not_fabricated(binding):
    inventory = binding.source_inventory
    assert inventory["authoring_template"]["status"] == "TEMPLATE_ONLY"
    assert inventory["authoring_template"]["resolved_authoring_answers_persisted"] is False
    assert inventory["questionnaire_answers"]["status"] == "NO_PROJECT_SIDE_ANSWER_STORE_FOUND"
    audit = inventory["source_completion_audit"]
    assert audit["status"] == "UNCHANGED_INCOMPLETE"
    assert audit["new_bindings"] == 0
    assert audit["inspected_candidates"] == 9
    assert all(source["status"] == "NOT_FOUND"
               for source in inventory["project_engineering_profiles"])


def test_readiness_only_and_repeatable(binding, monkeypatch):
    import agent.building_heat_loss as transmission
    import agent.ventilation_infiltration_heat_loss as air
    import agent.floor_heating_sizing as sizing
    import agent.ufh_engineering_kernel as kernel
    import agent.ufh_auto_retry as retry

    def forbidden(*args, **kwargs):
        raise AssertionError("Readiness binding must not execute SP60 or UFH calculations")

    monkeypatch.setattr(transmission, "calculate_room_transmission", forbidden)
    monkeypatch.setattr(air, "calculate_room_ventilation_heat_loss", forbidden)
    monkeypatch.setattr(air, "calculate_room_infiltration_heat_loss", forbidden)
    monkeypatch.setattr(air, "aggregate_sp60_a1_components", forbidden)
    monkeypatch.setattr(sizing, "size_ufh_requirement", forbidden)
    monkeypatch.setattr(kernel, "evaluate", forbidden)
    monkeypatch.setattr(retry, "assess_with_automatic_split_retry", forbidden)
    repeated = build_test01_sp60_engineering_binding(PROJECT, IFC)
    assert repeated.digest == binding.digest
    assert repeated.source_set_digest == binding.source_set_digest
    assert repeated.readiness.model_dump() == binding.readiness.model_dump()


def test_test01_tree_is_unchanged(binding):
    del binding
    before = _tree_digest(PROJECT)
    result = build_test01_sp60_engineering_binding(PROJECT, IFC)
    after = _tree_digest(PROJECT)
    assert result.authority_status == "AUTHORITATIVE"
    assert before == after

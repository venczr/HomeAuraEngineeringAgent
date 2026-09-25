import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent.ufh_climate_resolver import (
    ClimateNormativeDataset,
    load_climate_dataset,
    make_climate_resolver_request,
    resolve_climate_for_questionnaire,
    resolve_climate_request,
)
from agent.ufh_pre_generation_questionnaire import (
    Decision,
    ProjectContext,
    QuestionnaireState,
    apply_ufh_questionnaire_answers,
    build_ufh_pre_generation_questions,
)
from agent.ufh_project_engineering_profile_authoring import (
    load_ufh_project_engineering_authoring_template,
)
from agent.ufh_questionnaire_resolver_contract import (
    ResolvedValue,
    allowed_authorities,
    apply_resolver_result,
    invalidate_bindings,
    make_resolver_request,
)


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "Test_01_UFH_engineering_profile_authoring_template.json"
PROJECT_DIGEST = "1" * 64


def template_state():
    return QuestionnaireState(authoring=json.loads(TEMPLATE.read_text(encoding="utf-8")))


def answer(state, locality="Санкт-Петербург", region="Ленинградская область", question_id="climate"):
    return apply_ufh_questionnaire_answers(
        ProjectContext(source_reference="synthetic://questionnaire", coordinate_system="room-mm"),
        state,
        [Decision(question_id=question_id,
                  value={"settlement": locality, "region": region},
                  source_reference="synthetic://owner-confirmed-location",
                  revision="fixture-1")],
    )


def request_for(state, profile="RU_CURRENT", dataset=None):
    return make_climate_resolver_request("Test_01", "101DAA3", PROJECT_DIGEST,
                                         state, profile, dataset)


def test_official_metadata_and_two_layer_dataset_are_explicit():
    dataset = load_climate_dataset()
    assert dataset.normative_document_id == "SP 131.13330.2025"
    assert dataset.approval_order == "470/пр"
    assert dataset.approved_date == "2025-08-08"
    assert dataset.effective_from == "2025-09-09"
    assert dataset.replaces == "SP 131.13330.2020"
    assert dataset.official_status_source["authority_class"] == "NORMATIVE_DOCUMENT_IDENTITY_AUTHORITY"
    assert all(source.publisher_is_official is False for source in dataset.extract_sources)
    assert dataset.authority_class == "PROJECT_APPROVED_NORMATIVE_EXTRACT"
    assert len(dataset.dataset_digest) == len(dataset.extraction_digest) == 64


def test_mirror_is_not_misclassified_as_normative_authoritative():
    dataset = load_climate_dataset()
    state = answer(template_state())
    request = request_for(state, dataset=dataset)
    result = resolve_climate_request(request, dataset)
    resolved = result.values[0]
    assert result.status == "RESOLVED"
    assert resolved.authority_class == "PROJECT_APPROVED_NORMATIVE_EXTRACT"
    assert resolved.authored_value.provenance.source_type == "project_approved_normative_extract"
    assert "PROJECT_APPROVED_NORMATIVE_EXTRACT" in allowed_authorities("CLIMATE_RESOLVER")
    assert "PROJECT_APPROVED_NORMATIVE_EXTRACT" not in allowed_authorities("SURFACE_LIMIT_RESOLVER")
    with pytest.raises(ValidationError, match="AUTHORITY_PROVENANCE_MISMATCH"):
        ResolvedValue(
            target_authoring_field=resolved.target_authoring_field,
            authored_value=resolved.authored_value,
            authority_class="NORMATIVE_AUTHORITATIVE",
            dependency_digest=resolved.dependency_digest,
        )


def test_project_approved_extract_requires_official_identity_and_agreement():
    raw = load_climate_dataset().model_dump(mode="json")
    raw["official_status_source"]["authority_class"] = "REFERENCE_ONLY"
    with pytest.raises(ValidationError, match="OFFICIAL_IDENTITY_EVIDENCE_REQUIRED"):
        ClimateNormativeDataset.model_validate(raw)
    raw = load_climate_dataset().model_dump(mode="json")
    raw["verification"]["all_record_cells_agree_across_sources"] = False
    disputed = ClimateNormativeDataset.model_validate(raw)
    state = answer(template_state())
    assert resolve_climate_request(request_for(state, dataset=disputed), disputed).status == "AMBIGUOUS"


def test_table_column_order_and_values_are_verified_not_guessed():
    dataset = load_climate_dataset()
    assert dataset.verification["column_order"] == [
        "coldest_day_probability_0_98",
        "coldest_day_probability_0_92",
        "coldest_five_day_probability_0_98",
        "coldest_five_day_probability_0_92",
    ]
    spb = next(row for row in dataset.records if row.locality == "Санкт-Петербург")
    assert spb.column_values_c == (-30, -27, -27, -23)
    assert spb.value_c == spb.column_values_c[3] == -23
    assert "пятидневки" in spb.column_label and "0,92" in spb.column_label
    raw = dataset.model_dump(mode="json")
    raw["records"][4]["value_c"] = -27  # coldest five-day 0.98; not the target 0.92 column.
    with pytest.raises(ValidationError, match="CLIMATE_VALUE_NOT_TARGET_COLUMN"):
        ClimateNormativeDataset.model_validate(raw)


def test_saint_petersburg_aliases_resolve_to_same_source_record_and_digest():
    dataset = load_climate_dataset()
    outputs = []
    for locality in ("Санкт-Петербург", " СПб ", "Saint Petersburg"):
        state = answer(template_state(), locality=locality)
        request, result = resolve_climate_for_questionnaire(
            "Test_01", "101DAA3", PROJECT_DIGEST, state, "SP131_2025", dataset)
        assert request.resolver_context["resolved_normative_profile"] == "SP131_2025"
        assert result.status == "RESOLVED"
        assert result.values[0].authored_value.value == -23.0
        assert result.values[0].source_revision.endswith(dataset.dataset_digest)
        outputs.append((result.values[0].authored_value.value,
                        result.values[0].authored_value.provenance.source_reference))
    assert outputs[0] == outputs[1] == outputs[2]


def test_region_only_unknown_and_ambiguous_locality_fail_closed():
    dataset = load_climate_dataset()
    region_state = answer(template_state(), locality="Ленинградская область", region="Ленинградская область")
    assert resolve_climate_request(request_for(region_state, dataset=dataset), dataset).status == "INSUFFICIENT_INPUT"

    unknown_state = answer(template_state(), locality="Неизвестный посёлок")
    assert resolve_climate_request(request_for(unknown_state, dataset=dataset), dataset).status == "NOT_FOUND"

    raw = dataset.model_dump(mode="json")
    raw["records"][1]["aliases"].append("Санкт-Петербург")
    ambiguous_dataset = ClimateNormativeDataset.model_validate(raw)
    ambiguous_state = answer(template_state())
    assert resolve_climate_request(request_for(ambiguous_state, dataset=ambiguous_dataset),
                                   ambiguous_dataset).status == "AMBIGUOUS"


def test_leningrad_locality_records_are_distinct_and_cross_checked():
    dataset = load_climate_dataset()
    expected = {
        "Винницы": -31,
        "Выборг": -26,
        "Николаевское": -26,
        "Новая Ладога": -27,
        "Санкт-Петербург": -23,
        "Тихвин": -30,
    }
    assert {row.locality: row.value_c for row in dataset.records} == expected
    assert len({row.record_digest for row in dataset.records}) == len(expected)
    assert dataset.verification["all_record_cells_agree_across_sources"] is True


def test_resolver_binds_only_outdoor_design_condition_via_authoring_contract():
    dataset = load_climate_dataset()
    state = answer(template_state())
    request = request_for(state, dataset=dataset)
    result = resolve_climate_request(request, dataset)
    updated, binding = apply_resolver_result(state, request, result)
    authored = updated.authoring.design_conditions["outdoor_design_temperature_c"]
    assert authored.value == -23.0
    assert authored.provenance.source_type == "project_approved_normative_extract"
    assert authored.provenance.source_sha256 == dataset.dataset_digest
    loaded = load_ufh_project_engineering_authoring_template(updated.authoring.model_dump(mode="json"))
    assert loaded.status == "INCOMPLETE"
    assert loaded.profile is None
    question_result = build_ufh_pre_generation_questions(
        ProjectContext(source_reference="synthetic://questionnaire", coordinate_system="room-mm"), updated)
    assert "climate" not in {question.question_id for question in question_result.questions}
    assert binding.result.values[0].target_authoring_field == "design_conditions.outdoor_design_temperature_c"


def test_test01_without_explicit_location_keeps_climate_question_and_profile_incomplete():
    state = template_state()
    context = ProjectContext(source_reference="Test_01", coordinate_system="authoritative room boundary integer millimetres")
    questions = build_ufh_pre_generation_questions(context, state)
    assert "climate" in {question.question_id for question in questions.questions}
    loaded = load_ufh_project_engineering_authoring_template(state.authoring.model_dump(mode="json"))
    assert loaded.status == "INCOMPLETE"
    assert loaded.profile is None


def test_locality_normative_profile_and_dataset_revision_invalidate_old_binding():
    dataset = load_climate_dataset()
    state = answer(template_state())
    request = request_for(state, dataset=dataset)
    result = resolve_climate_request(request, dataset)
    updated, binding = apply_resolver_result(state, request, result)

    changed_location = copy.deepcopy(updated)
    changed_location.decisions["climate"] = Decision(
        question_id="climate", value={"settlement": "Тихвин", "region": "Ленинградская область"},
        source_reference="synthetic://owner-confirmed-location", revision="fixture-2")
    stale, history = invalidate_bindings(changed_location, [binding], PROJECT_DIGEST)
    assert history[0].result.status == "STALE_INPUT"
    assert stale.authoring.design_conditions["outdoor_design_temperature_c"].status == "UNSET"

    stale_by_dataset, history = invalidate_bindings(
        updated, [binding], PROJECT_DIGEST,
        resolver_contexts={"CLIMATE_RESOLVER": {
            **request.resolver_context,
            "dataset_digest": "f" * 64,
        }})
    assert history[0].result.status == "STALE_INPUT"
    assert stale_by_dataset.authoring.design_conditions["outdoor_design_temperature_c"].status == "UNSET"

    explicit_profile_request = request_for(state, profile="SP131_2025", dataset=dataset)
    assert explicit_profile_request.dependency_digest != request.dependency_digest
    stale_by_profile, history = invalidate_bindings(
        updated, [binding], PROJECT_DIGEST,
        resolver_contexts={"CLIMATE_RESOLVER": explicit_profile_request.resolver_context})
    assert history[0].result.status == "STALE_INPUT"
    assert stale_by_profile.authoring.design_conditions["outdoor_design_temperature_c"].status == "UNSET"


def test_unrelated_answers_do_not_invalidate_climate_and_dataset_revision_changes_digest():
    dataset = load_climate_dataset()
    state = answer(template_state())
    request = request_for(state, dataset=dataset)
    state.decisions["finish"] = Decision(question_id="finish", value="TILE_STONE",
                                          source_reference="synthetic://finish", revision="1")
    same = make_climate_resolver_request("Test_01", "101DAA3", PROJECT_DIGEST,
                                         state, "RU_CURRENT", dataset)
    assert same.dependency_digest == request.dependency_digest

    changed_source = dataset.model_copy(update={"approval_basis": dataset.approval_basis + "; revision-2"})
    changed = make_climate_resolver_request("Test_01", "101DAA3", PROJECT_DIGEST,
                                            state, "RU_CURRENT", changed_source)
    assert changed.dependency_digest != same.dependency_digest
    assert changed_source.dataset_digest != dataset.dataset_digest


def test_rooms_json_outdoor_observation_is_not_a_climate_input():
    state = answer(template_state())
    request = request_for(state)
    decision = request.normalized_decisions["climate"]["value"]
    assert decision["settlement"] == "Санкт-Петербург"
    assert "OutdoorTemperatureC" not in decision
    assert "outdoor_design_temperature_c" not in request.normalized_decisions["climate"]

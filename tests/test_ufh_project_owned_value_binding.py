from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from agent.rooms_api import RoomExportReport
from agent.test01_geometry_source_authority import assess_test01_geometry_authority
from agent.ufh_pre_generation_questionnaire import (
    QuestionnaireState,
    build_ufh_pre_generation_questions,
    load_questionnaire_authoring,
    project_context_from_adapter_result,
)
from agent.ufh_project_adapter import (
    ProjectRoomUfhSource,
    build_ufh_sizing_request_from_project_room,
    collect_project_owned_ufh_values,
)
from agent.ufh_project_engineering_profile_authoring import (
    load_ufh_project_engineering_authoring_template,
    synthetic_complete_authoring_payload,
)


ROOT = Path(__file__).resolve().parents[1]
ROOMS = ROOT / "projects/Test_01/exports/rooms/rooms.json"
TEMPLATE = ROOT / "docs/Test_01_UFH_engineering_profile_authoring_template.json"


def _adapt_test01(*, omit_ach: bool = False, ach_override: float | None = None):
    raw_bytes = ROOMS.read_bytes()
    raw = json.loads(raw_bytes)
    room_data = next(item for item in raw["Rooms"] if item["SourceHandle"] == "101DAA3")
    if omit_ach:
        room_data.pop("AirExchangeRate", None)
        raw_bytes = json.dumps(raw, sort_keys=True, ensure_ascii=False,
                               separators=(",", ":")).encode()
    elif ach_override is not None:
        room_data["AirExchangeRate"] = ach_override
        raw_bytes = json.dumps(raw, sort_keys=True, ensure_ascii=False,
                               separators=(",", ":")).encode()
    report = RoomExportReport.model_validate(raw)
    room = next(item for item in report.Rooms if item.SourceHandle == "101DAA3")
    source = ProjectRoomUfhSource(
        project_id="Test_01", building_id=None, level_id=None,
        room_id=room.SourceHandle, room_export=report, selected_room=room,
        source_file=str(ROOMS), source_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        source_kind="room_extraction",
    )
    return build_ufh_sizing_request_from_project_room(source)


def test_test01_authoritative_ach_flows_adapter_binding_loader_and_profile_provenance():
    adapter = _adapt_test01()
    binding = collect_project_owned_ufh_values(adapter)
    ach = next(item for item in binding.values
               if item.canonical_field_path == "sizing.room.insulation.air_changes_per_hour")
    mapped_ach = next(field for field in adapter.mapped_fields
                      if field.target_path == "room.insulation.air_changes_per_hour")
    assert ach.value == mapped_ach.value
    assert ach.authority_class == "PROJECT_DATA_VALUE"
    assert ach.units == "1/h"
    assert (ach.project_id, ach.room_id) == ("Test_01", "101DAA3")
    assert ach.source_field == "$.Rooms[].AirExchangeRate"
    assert ach.source_digest == adapter.source_digest

    payload = synthetic_complete_authoring_payload()
    payload["building_physics"].pop("air_changes_per_hour")
    loaded = load_ufh_project_engineering_authoring_template(
        payload, project_owned_values=binding,
    )
    assert loaded.status == "READY"
    assert loaded.project_owned_values_digest == binding.binding_digest
    assert loaded.profile.building_physics.air_changes_per_hour == ach.value
    provenance = loaded.profile.provenance[
        "sizing.room.insulation.air_changes_per_hour"
    ]
    assert provenance.source_file == ach.source_reference
    assert provenance.source_path == ach.source_field
    assert provenance.source_sha256 == adapter.source_digest
    assert provenance.source_kind == "room_extraction"


def test_bound_value_is_available_from_authoritative_test01_adapter_source():
    project = ROOT / "projects/Test_01"
    ifc_directory = ROOT.parent / "HomeAuraEngineeringAgent-ifc-research/manual-export"
    if not (ifc_directory / "Test_01_rooms_ifc4.ifc").is_file():
        pytest.skip("Reviewed Test_01 IFC evidence set is unavailable")
    decision = assess_test01_geometry_authority(project, ifc_directory)
    assert decision.status == "AUTHORITATIVE"
    adapter = build_ufh_sizing_request_from_project_room(decision.ufh_source)
    binding = collect_project_owned_ufh_values(adapter)
    assert adapter.status == "INCOMPLETE"
    assert len(adapter.missing_inputs) == 41
    assert "sizing.room.insulation.air_changes_per_hour" not in adapter.missing_inputs
    assert [item.canonical_field_path for item in binding.values] == [
        "sizing.room.insulation.air_changes_per_hour"
    ]


def test_test01_unfilled_template_resolves_only_ach_and_stays_incomplete():
    adapter = _adapt_test01()
    binding = collect_project_owned_ufh_values(adapter)
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    before = load_ufh_project_engineering_authoring_template(payload)
    after = load_ufh_project_engineering_authoring_template(
        payload, project_owned_values=binding,
    )
    ach_path = "sizing.room.insulation.air_changes_per_hour"
    before_paths = set(before.missing_authoring_paths)
    after_paths = set(after.missing_authoring_paths)
    assert before.status == after.status == "INCOMPLETE"
    assert ach_path in before_paths
    assert ach_path not in after_paths
    assert len(before_paths) - len(after_paths) == 1
    assert after.project_owned_values_digest == binding.binding_digest


def test_conflicting_authoring_ach_fails_closed_and_equal_value_uses_project_owner():
    adapter = _adapt_test01()
    binding = collect_project_owned_ufh_values(adapter)
    ach = binding.values[0]

    conflict = synthetic_complete_authoring_payload()
    conflict["building_physics"]["air_changes_per_hour"]["value"] = ach.value + 0.25
    result = load_ufh_project_engineering_authoring_template(
        conflict, project_owned_values=binding,
    )
    assert result.status == "INVALID"
    assert any(d.code == "SOURCE_VALUE_CONFLICT" and d.path == ach.canonical_field_path
               for d in result.diagnostics)

    same = synthetic_complete_authoring_payload()
    authored = same["building_physics"]["air_changes_per_hour"]
    authored["value"] = ach.value
    result = load_ufh_project_engineering_authoring_template(
        same, project_owned_values=binding,
    )
    assert result.status == "READY"
    assert result.profile.provenance[ach.canonical_field_path].source_sha256 == adapter.source_digest


def test_missing_ach_has_no_fallback_and_non_authoritative_fields_are_not_promoted():
    binding = collect_project_owned_ufh_values(_adapt_test01(omit_ach=True))
    assert binding.values == []
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    loaded = load_ufh_project_engineering_authoring_template(payload, project_owned_values=binding)
    assert loaded.status == "INCOMPLETE"
    assert any(d.code == "AUTHORITATIVE_PROJECT_VALUE_REQUIRED"
               and d.path == "sizing.room.insulation.air_changes_per_hour"
               for d in loaded.diagnostics)

    mapped_paths = {item.canonical_field_path for item in collect_project_owned_ufh_values(
        _adapt_test01()
    ).values}
    assert mapped_paths == {"sizing.room.insulation.air_changes_per_hour"}
    assert not any(token in " ".join(mapped_paths).lower()
                   for token in ("outdoor_design_temperature", "theta_supply", "u_value",
                                 "surface_limit", "inner_diameter", "density", "control"))


def test_invalid_adapter_result_cannot_export_project_owned_values():
    adapter = _adapt_test01()
    rejected = adapter.model_copy(update={"status": "INVALID"})
    assert collect_project_owned_ufh_values(rejected).values == []


def test_binding_and_profile_digests_are_deterministic_and_value_sensitive():
    first_adapter = _adapt_test01()
    first = collect_project_owned_ufh_values(first_adapter)
    repeated = collect_project_owned_ufh_values(_adapt_test01())
    changed = collect_project_owned_ufh_values(_adapt_test01(ach_override=0.9))
    assert first == repeated
    assert first.binding_digest == repeated.binding_digest
    assert first.binding_digest != changed.binding_digest

    payload = synthetic_complete_authoring_payload()
    payload["building_physics"].pop("air_changes_per_hour")
    p1 = load_ufh_project_engineering_authoring_template(
        payload, project_owned_values=first,
    ).profile
    p2 = load_ufh_project_engineering_authoring_template(
        payload, project_owned_values=changed,
    ).profile
    assert p1.profile_digest != p2.profile_digest


def test_questionnaire_context_carries_binding_and_suppresses_bound_ach_question(monkeypatch):
    import agent.ufh_pre_generation_questionnaire as questionnaire

    adapter = _adapt_test01()
    binding = collect_project_owned_ufh_values(adapter)
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    context = project_context_from_adapter_result(
        adapter, payload["project_context"]["coordinate_system"],
    )
    assert context.project_owned_values == binding
    state = QuestionnaireState(authoring=payload)
    monkeypatch.setattr(questionnaire, "QUESTIONS", [questionnaire.Question(
        question_id="project.ach", group="project", prompt="ACH?",
        answer_type="quantity", unit="1/h", targets=["building_physics.air_changes_per_hour"],
        why_required="test binding suppression",
    )])
    questions = build_ufh_pre_generation_questions(context, state).questions
    assert questions == []
    loaded = load_questionnaire_authoring(state, context)
    assert loaded.project_owned_values_digest == binding.binding_digest
    assert loaded.status == "INCOMPLETE"


def test_audit_only_room_fields_never_bind_to_project_profile():
    adapter = _adapt_test01()
    fields = {item.target_path: item for item in adapter.mapped_fields}
    assert fields["room_source.OutdoorTemperatureC"].applied_to_request is False
    assert "room_source.SupplyAirTemperatureC" not in fields
    assert fields["room_source.StructuralHeatLossW"].applied_to_request is False
    assert fields["room_source.HeatLossWM2"].applied_to_request is False
    assert [item.canonical_field_path for item in collect_project_owned_ufh_values(adapter).values] == [
        "sizing.room.insulation.air_changes_per_hour"
    ]

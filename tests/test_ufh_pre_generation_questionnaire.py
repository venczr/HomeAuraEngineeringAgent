import hashlib
import json
from pathlib import Path

import pytest

from agent.ufh_pre_generation_questionnaire import (
    Decision, ProjectContext, QuestionnaireState, build_ufh_pre_generation_questions as build,
    apply_ufh_questionnaire_answers as apply, load_questionnaire_authoring,
)

ROOT = Path(__file__).resolve().parents[1]


def setup():
    payload = json.loads((ROOT / "docs/Test_01_UFH_engineering_profile_authoring_template.json").read_text())
    return ProjectContext(source_reference="docs/Test_01_UFH_engineering_profile_authoring_template.json",
                          coordinate_system=payload["project_context"]["coordinate_system"]), QuestionnaireState(authoring=payload)


def answer(key, value):
    return Decision(question_id=key, value=value, source_reference="owner:test-session", revision="1")


def ids(context, state):
    return [q.question_id for q in build(context, state).questions]


def test_real_template_no_mutation_no_project_owned_questions():
    path = ROOT / "docs/Test_01_UFH_engineering_profile_authoring_template.json"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    context, state = setup()
    assert len(ids(context, state)) == 13
    assert "climate" in ids(context, state)
    assert not set(ids(context, state)) & {"room_id", "boundary", "area", "indoor_temperature", "ACH"}
    assert load_questionnaire_authoring(state).status == "INCOMPLETE"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_known_location_and_authoring_fields_suppress_questions():
    context, state = setup()
    context.known_decisions["climate"] = answer("climate", {"settlement": "test", "region": "test"})
    state = apply(context, state, [answer("exclusions", "NO")])
    assert "climate" not in ids(context, state)
    assert "exclusions" not in ids(context, state)


@pytest.mark.parametrize("choice,ground", [("HEATED_ROOM", False), ("GROUND", True)])
def test_adjacent_dependency(choice, ground):
    context, state = setup()
    state = apply(context, state, [answer("below", choice)])
    assert ("below.source" in ids(context, state)) == ground
    assert state.authoring.design_conditions["floor_boundary_temperature_c"].status == "UNSET"
    assert "RESOLUTION_REQUIRED:below" in build(context, state).resolver_requirements


def test_exclusions_missing_unknown_yes_and_no():
    context, state = setup()
    for choice in ("YES", "UNKNOWN"):
        other = apply(context, state, [answer("exclusions", choice)])
        assert other.authoring.explicit_confirmations["exclusion_zones"].status == "UNSET"
    empty = apply(context, state, [answer("exclusions", "NO")])
    assert empty.authoring.explicit_confirmations["exclusion_zones"].status == "EXPLICIT_EMPTY"
    assert state.authoring.explicit_confirmations["exclusion_zones"].status == "UNSET"
    assert empty.authoring.explicit_confirmations["exclusion_zones"].provenance.source_field == "exclusions"


@pytest.mark.parametrize("selection", ["CATALOG", "AUTO"])
def test_system_decision_never_materializes_raw_properties(selection):
    context, state = setup()
    state = apply(context, state, [answer("system", selection)])
    assert state.decisions["system"].value == selection
    assert all(v.status == "UNSET" for v in state.authoring.pipe_product.values())
    assert not any("diameter" in q.prompt for q in build(context, state).questions)
    assert ("system.source" in ids(context, state)) == (selection == "CATALOG")


@pytest.mark.parametrize("mode,shown,hidden", [
    ("KNOWN_SUPPLY_TEMPERATURE", "thermal.supply", "thermal.delta"),
    ("KNOWN_DELTA_T", "thermal.delta", "thermal.supply"),
    ("AUTO_DESIGN", None, "thermal.supply"),
])
def test_thermal_modes(mode, shown, hidden):
    context, state = setup()
    state = apply(context, state, [answer("thermal", mode)])
    if shown:
        assert shown in ids(context, state)
    assert hidden not in ids(context, state)
    if mode == "AUTO_DESIGN":
        assert "thermal.delta" not in ids(context, state)
        assert state.authoring.ufh_design_settings["mode"].status == "UNSET"


def test_determinism_and_json_roundtrip():
    context, state = setup()
    updated = apply(context, state, [answer("layout", "AUTO"), answer("fluid", "WATER")])
    restored = QuestionnaireState.model_validate_json(updated.model_dump_json())
    assert build(context, updated) == build(context, restored)
    assert "fluid.temperature" in ids(context, updated)
    assert all(v.status == "UNSET" for v in updated.authoring.fluid_definition.values())


def test_collector_units_frame_and_provenance():
    context, state = setup()
    point = {"x_mm": 12, "y_mm": 34, "unit": "mm", "coordinate_system": context.coordinate_system}
    updated = apply(context, state, [answer("collector", point)])
    assert updated.authoring.ufh_design_settings["collector_point_x_mm"].value == 12
    for patch in ({"unit": "m"}, {"coordinate_system": "other"}, {"x_mm": True}):
        with pytest.raises(ValueError):
            apply(context, state, [answer("collector", {**point, **patch})])


def test_inactive_invalid_and_atomic_answers():
    context, state = setup()
    with pytest.raises(ValueError):
        apply(context, state, [answer("thermal.supply", {"value": 40, "unit": "degC"})])
    with pytest.raises(ValueError):
        apply(context, state, [answer("exclusions", "NO"), answer("system", "bad")])
    assert not state.decisions


def test_authoring_loader_is_only_conversion_boundary(monkeypatch):
    import agent.ufh_pre_generation_questionnaire as module
    context, state = setup()
    updated = apply(context, state, [answer("thermal", "KNOWN_DELTA_T"),
        answer("thermal.delta", {"value": 5, "unit": "K"})])
    captured = []
    monkeypatch.setattr(module, "load_ufh_project_engineering_authoring_template",
                        lambda p, **kwargs: captured.append((p, kwargs)))
    module.load_questionnaire_authoring(updated)
    assert captured[0][0]["design_conditions"]["sigma_k"]["value"] == 5
    assert captured[0][1]["project_owned_values"] is None
    assert updated.authoring.design_conditions["theta_supply_c"].status == "UNSET"


def test_pages_and_resumed_authoring_mode():
    context, state = setup()
    assert [len(page) for page in build(context, state).pages()] == [8, 5]
    state = apply(context, state, [answer("thermal", "KNOWN_DELTA_T")])
    state.decisions = {}
    assert "thermal.delta" in ids(context, state)
    assert "thermal.supply" not in ids(context, state)
    assert "thermal" not in ids(context, state)


def test_yes_requires_geometry_workflow():
    context, state = setup()
    state = apply(context, state, [answer("exclusions", "YES")])
    assert "GEOMETRY_SELECTION_REQUIRED:exclusions" in build(context, state).resolver_requirements

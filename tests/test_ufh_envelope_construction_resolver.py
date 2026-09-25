from __future__ import annotations

from decimal import Decimal
import hashlib

import pytest

from agent.ufh_envelope_construction_resolver import (
    ConstructionBoundaryKind as BoundaryKind,
    ConstructionSourceMode as SourceMode,
    EnvelopeAssemblyDefinition,
    EnvelopeConstructionSubmission,
    SurfaceResistanceMethod,
    calculate_assembly,
    calculate_bundle,
)
from agent.ufh_pre_generation_questionnaire import Decision
from agent.ufh_project_engineering_profile_authoring import AuthoringProvenance
from agent.ufh_project_engineering_profile_authoring import (
    Test01UfhEngineeringAuthoringTemplate as AuthoringTemplateModel,
    test01_authoring_template_payload as _template_payload_factory,
)
from agent.ufh_project_pre_generation import (
    apply_ufh_questionnaire_answer,
    profile_readiness,
)
from tests.test_ufh_project_pre_generation import PROJECT, actual_session, answer


def provenance(source_type="project_decision", *, units="W/(m*K)",
               reference="synthetic://TEST_ONLY/construction-A", field="materials.lambda"):
    return AuthoringProvenance(
        source_type=source_type,
        source_reference=reference,
        source_field=field,
        author_or_confirmation="TEST_ONLY synthetic resolver fixture",
        transformation="explicit test-only sourced-property fixture; not project data",
        units=units,
    )


def wall_payload(*, missing_lambda=False, thickness="0.12"):
    return {
        "source_mode": SourceMode.LAYERED_CUSTOM_ASSEMBLY.value,
        "source_reference": "project://construction-package/rev-4",
        "source_field": "Envelope.WallType-A",
        "source_revision": "rev-4",
        "assemblies": [{
            "assembly_id": "external-wall-A",
            "boundary_kind": BoundaryKind.EXTERIOR_WALL.value,
            "source_reference": "project://construction-package/rev-4",
            "source_field": "WallType-A.layers",
            "layers": [
                {"material_product_id": "masonry-A", "thickness_m": thickness,
                 "lambda_w_mk": None if missing_lambda else "0.60",
                 "lambda_provenance": None if missing_lambda else provenance().model_dump(mode="python")},
                {"material_product_id": "insulation-X", "thickness_m": "0.08",
                 "lambda_w_mk": None if missing_lambda else "0.04",
                 "lambda_provenance": None if missing_lambda else provenance(reference="catalog://insulation-X", field="datasheet.lambda").model_dump(mode="python")},
            ],
        }],
    }


def submission(payload):
    return EnvelopeConstructionSubmission.model_validate(payload)


def test_layered_assembly_calculates_sourced_layer_resistance_only_without_surface_method():
    result = calculate_bundle(submission(wall_payload()))
    assembly = result.assemblies[0]
    assert assembly.layered_resistance_m2k_w == Decimal("2.20")
    assert assembly.total_resistance_m2k_w is None
    assert assembly.u_value_w_m2k is None
    assert assembly.calculation_status == "NORMATIVE_SOURCE_REQUIRED"
    assert "NORMATIVE_SURFACE_RESISTANCE_SOURCE_REQUIRED" in assembly.unresolved_dependencies


def test_missing_lambda_is_not_filled_from_material_name():
    assembly = calculate_bundle(submission(wall_payload(missing_lambda=True))).assemblies[0]
    assert assembly.layered_resistance_m2k_w is None
    assert assembly.u_value_w_m2k is None
    assert "MATERIAL_THERMAL_PROPERTY_RESOLVER" in assembly.unresolved_dependencies


def test_surface_resistance_requires_explicit_normative_provenance_and_enables_u_calculation():
    definition = EnvelopeAssemblyDefinition.model_validate(wall_payload()["assemblies"][0])
    method = SurfaceResistanceMethod(
        method_id="test-method-only", method_revision="test-v1",
        r_si_m2k_w=Decimal("0.13"), r_se_m2k_w=Decimal("0.04"),
        provenance=provenance("test_only", units="m2*K/W", reference="test://method"),
    )
    result = calculate_assembly(definition, SourceMode.LAYERED_CUSTOM_ASSEMBLY,
                                surface_method=method)
    assert result.total_resistance_m2k_w == Decimal("2.37")
    assert result.u_value_w_m2k == Decimal(1) / Decimal("2.37")
    assert result.calculation_status == "LAYERED_RESISTANCE_RESOLVED"


def test_lambda_without_provenance_and_explicit_u_without_provenance_are_rejected():
    broken = wall_payload()
    broken["assemblies"][0]["layers"][0]["lambda_provenance"] = None
    with pytest.raises(ValueError, match="LAMBDA_VALUE_AND_PROVENANCE_MUST_BE_PAIRED"):
        EnvelopeAssemblyDefinition.model_validate(broken["assemblies"][0])

    with pytest.raises(ValueError):
        EnvelopeAssemblyDefinition.model_validate({
            "assembly_id": "window-1", "boundary_kind": "WINDOW", "layers": [],
            "explicit_u_value": {"value_w_m2k": "1.1"},
            "source_reference": "project://window", "source_field": "window.U",
        })


def test_explicit_u_provenance_is_accepted_and_openings_cannot_use_generic_glass_inference():
    explicit = {
        "source_mode": SourceMode.EXPLICIT_U_VALUE_WITH_PROVENANCE.value,
        "source_reference": "project://window-schedule", "source_field": "Window.U",
        "assemblies": [{
            "assembly_id": "window-1", "boundary_kind": "WINDOW", "layers": [],
            "source_reference": "project://window-schedule", "source_field": "Window.U",
            "explicit_u_value": {
                "value_w_m2k": "1.1",
                "provenance": provenance("building_construction_data", units="W/(m2*K)",
                                         reference="project://window-schedule", field="Window.U").model_dump(mode="python"),
            },
        }],
    }
    resolved = calculate_bundle(submission(explicit)).assemblies[0]
    assert resolved.u_value_w_m2k == Decimal("1.1")
    assert resolved.layered_resistance_m2k_w is None
    assert resolved.calculation_status == "EXPLICIT_U_VALUE_RESOLVED"

    with pytest.raises(ValueError, match="GENERIC_OPENING_INFERENCE_PROHIBITED"):
        EnvelopeAssemblyDefinition.model_validate({
            "assembly_id": "window-2", "boundary_kind": "WINDOW",
            "layers": wall_payload()["assemblies"][0]["layers"],
            "source_reference": "project://window", "source_field": "window.glass",
        })


def test_explicit_and_calculated_u_conflict_fails_closed():
    raw = wall_payload()
    raw["assemblies"][0]["explicit_u_value"] = {
        "value_w_m2k": "0.5",
        "provenance": provenance("building_construction_data", units="W/(m2*K)",
                                 reference="project://declared-U", field="Wall.U").model_dump(mode="python"),
    }
    definition = EnvelopeAssemblyDefinition.model_validate(raw["assemblies"][0])
    method = SurfaceResistanceMethod(
        method_id="test-method-only", method_revision="test-v1",
        r_si_m2k_w=Decimal("0.13"), r_se_m2k_w=Decimal("0.04"),
        provenance=provenance("test_only", units="m2*K/W", reference="test://method"),
    )
    result = calculate_assembly(definition, SourceMode.LAYERED_CUSTOM_ASSEMBLY,
                                surface_method=method)
    assert result.calculation_status == "SOURCE_VALUE_CONFLICT"
    assert result.u_value_w_m2k is None


def test_climate_is_not_a_construction_dependency_and_layer_or_method_changes_digest():
    first = calculate_bundle(submission(wall_payload()))
    changed_layer = calculate_bundle(submission(wall_payload(thickness="0.13")))
    assert first.dependency_digest != changed_layer.dependency_digest

    one = calculate_bundle(submission(wall_payload())).assemblies[0]
    definition = EnvelopeAssemblyDefinition.model_validate(wall_payload()["assemblies"][0])
    method = SurfaceResistanceMethod(
        method_id="test-method-only", method_revision="test-v1",
        r_si_m2k_w=Decimal("0.13"), r_se_m2k_w=Decimal("0.04"),
        provenance=provenance("test_only", units="m2*K/W", reference="test://method"),
    )
    revised = calculate_assembly(definition, SourceMode.LAYERED_CUSTOM_ASSEMBLY,
                                 surface_method=method.model_copy(update={"method_revision": "test-v2"}))
    assert one.dependency_digest != revised.dependency_digest


def test_ground_slab_keeps_ground_heat_transfer_outside_assembly_u_result():
    raw = wall_payload()
    raw["assemblies"][0]["boundary_kind"] = BoundaryKind.FLOOR_SLAB.value
    assembly = calculate_bundle(submission(raw)).assemblies[0]
    assert assembly.calculation_status == "NORMATIVE_SOURCE_REQUIRED"
    assert assembly.u_value_w_m2k is None
    assert not hasattr(assembly, "heat_loss_w")


def test_session_handoff_stores_assembly_but_does_not_complete_u_value_or_run_heat_loss():
    source_files = (
        PROJECT / "Test_01.dwg",
        PROJECT / "HomeAura_Test_01.mrd",
        PROJECT / "exports" / "rooms" / "rooms.json",
    )
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest()
              for path in source_files if path.is_file()}
    session = actual_session()
    assert session.questionnaire_state.authoring.envelope_constructions["selected"].status == "UNSET"
    initial_numeric_u = session.questionnaire_state.authoring.building_physics[
        "exterior_wall_u_value_w_m2k"
    ].status
    selected = apply_ufh_questionnaire_answer(
        session, answer("envelope", "LAYERED_CUSTOM_ASSEMBLY")
    )
    assert any(q.question_id == "envelope.source" for q in selected.active_questions)
    updated = apply_ufh_questionnaire_answer(
        selected, answer("envelope.source", wall_payload())
    )
    authored = updated.questionnaire_state.authoring.envelope_constructions["selected"]
    assert authored.status == "DERIVED"
    result_bundle = authored.value
    assert Decimal(result_bundle["assemblies"][0]["layered_resistance_m2k_w"]) == Decimal("2.20")
    assert result_bundle["assemblies"][0]["u_value_w_m2k"] is None
    assert updated.questionnaire_state.authoring.building_physics[
        "exterior_wall_u_value_w_m2k"
    ].status == initial_numeric_u == "UNSET"
    assert updated.status != "READY_FOR_ENGINEERING"
    assert any("NORMATIVE_SURFACE_RESISTANCE_SOURCE_REQUIRED" in issue
               for issue in updated.diagnostics)
    readiness = profile_readiness(updated)
    assert readiness.status == "INCOMPLETE"
    after = {path: hashlib.sha256(path.read_bytes()).hexdigest()
             for path in source_files if path.is_file()}
    assert before == after


def test_sp50_resolver_handoff_calculates_conditional_homogeneous_u_only_with_exact_rows():
    selected = apply_ufh_questionnaire_answer(
        actual_session(), answer("envelope", "LAYERED_CUSTOM_ASSEMBLY")
    )
    payload = wall_payload()
    payload["assemblies"][0]["surface_applicability"] = {
        "internal_category": "WALL_FLOOR_SMOOTH_CEILING_LOW_RIB",
        "external_category": "EXTERIOR_WALL_ROOF_EXPOSED_FLOOR_NORTHERN_ZONE",
        "northern_climatic_zone_confirmed": True,
        "climatic_zone_source_reference": "project://building/rev-5",
        "climatic_zone_source_field": "climatic_zone",
    }
    updated = apply_ufh_questionnaire_answer(selected, answer("envelope.source", payload))
    assembly = updated.questionnaire_state.authoring.envelope_constructions[
        "selected"
    ].value["assemblies"][0]
    expected_r = Decimal(1) / Decimal("8.7") + Decimal("2.20") + Decimal(1) / Decimal("23")
    assert Decimal(assembly["total_resistance_m2k_w"]) == expected_r
    assert Decimal(assembly["u_value_w_m2k"]) == Decimal(1) / expected_r
    assert assembly["resistance_scope"] == "HOMOGENEOUS_SECTION_CONDITIONAL_RESISTANCE"
    assert assembly["calculation_status"] == "LAYERED_RESISTANCE_RESOLVED"
    assert "THERMAL_BRIDGES_REMAIN_SEPARATE" in assembly["unresolved_dependencies"]


def test_test_only_physical_source_cannot_bind_through_production_session():
    session = actual_session()
    selected = apply_ufh_questionnaire_answer(
        session, answer("envelope", "LAYERED_CUSTOM_ASSEMBLY")
    )
    payload = wall_payload()
    for layer in payload["assemblies"][0]["layers"]:
        layer["lambda_provenance"]["source_type"] = "test_only"
        layer["lambda_provenance"]["source_reference"] = "synthetic://TEST_ONLY/material"
    updated = apply_ufh_questionnaire_answer(
        selected, answer("envelope.source", payload)
    )
    assert updated.resolver_executions[-1].resolver_result.status == "OUT_OF_DOMAIN"
    assert "TEST_ONLY_SOURCE_NOT_BINDABLE" in updated.resolver_executions[-1].resolver_result.diagnostics
    assert updated.questionnaire_state.authoring.envelope_constructions["selected"].status == "UNSET"


def test_source_and_authoring_digests_are_deterministic():
    a = calculate_bundle(submission(wall_payload()))
    b = calculate_bundle(submission(wall_payload()))
    assert a.dependency_digest == b.dependency_digest
    assert a.model_dump(mode="json") == b.model_dump(mode="json")


def test_older_authoring_payload_remains_loadable_with_unset_construction_extension():
    payload = _template_payload_factory()
    payload.pop("envelope_constructions")
    model = AuthoringTemplateModel.model_validate(payload)
    assert model.envelope_constructions["selected"].status == "UNSET"


def test_project_decision_does_not_turn_unknown_or_catalog_selection_into_fake_data():
    with pytest.raises(ValueError, match="INSUFFICIENT_INPUT"):
        calculate_bundle(submission({
            "source_mode": "UNKNOWN", "source_reference": "user://answer",
            "source_field": "envelope.source", "assemblies": [],
        }))
    with pytest.raises(ValueError, match="SOURCE_UNAVAILABLE"):
        calculate_bundle(submission({
            "source_mode": "CATALOG_SYSTEM", "source_reference": "user://answer",
            "source_field": "envelope.source", "assemblies": [],
        }))

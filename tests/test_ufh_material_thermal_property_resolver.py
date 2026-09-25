from decimal import Decimal
import json

import pytest

from agent.ufh_material_thermal_property_resolver import (
    EnvelopeOperatingCondition, MaterialPropertyClaim, MaterialResolutionRequest,
    MaterialThermalPropertyRecord, SP50_MATERIAL_DATASET,
    build_verified_material_dataset, construction_layer_from_resolution,
    resolve_material_thermal_property,
)
from agent.ufh_project_pre_generation import apply_ufh_questionnaire_answer
from tests.test_ufh_envelope_construction_resolver import wall_payload
from tests.test_ufh_project_pre_generation import actual_session, answer


def request(**kwargs):
    if (kwargs.get("operating_condition") in {"A", "B", EnvelopeOperatingCondition.A,
                                                EnvelopeOperatingCondition.B}
            and kwargs.get("operating_condition_source_reference")
            and kwargs.get("operating_condition_source_field")):
        kwargs.setdefault("operating_condition_authority_class", "PROJECT_AUTHORITATIVE")
    return MaterialResolutionRequest(material_product_id="layer-material", **kwargs)


def test_normative_dataset_is_pinned_and_subset_coverage_is_explicit():
    dataset = SP50_MATERIAL_DATASET
    assert dataset.normative_document == "SP 50.13330.2024"
    assert dataset.edition == "2024"
    assert dataset.appendix_id == "M" and dataset.table_id == "M.1"
    assert dataset.full_table_numbered_rows == 246
    assert dataset.bundled_record_count == 13
    assert dataset.authority_class == "PROJECT_APPROVED_NORMATIVE_EXTRACT"
    assert len({record.row_number for record in dataset.records}) == 13
    assert all(record.authority_class == dataset.authority_class for record in dataset.records)


def test_extraction_compiler_rejects_source_disagreement_and_is_deterministic():
    raw = SP50_MATERIAL_DATASET.records[0].model_dump(mode="json")
    first = build_verified_material_dataset([raw], [raw])
    second = build_verified_material_dataset([raw], [raw])
    assert first.dataset_digest == second.dataset_digest
    changed = dict(raw)
    changed["lambda_b_w_mk"] = "0.048"
    with pytest.raises(ValueError, match="SOURCE_AMBIGUOUS"):
        build_verified_material_dataset([raw], [changed])
    with pytest.raises(ValueError, match="DUPLICATE_TABLE_ROW"):
        build_verified_material_dataset([raw, raw], [raw])


def test_density_variants_are_distinct_and_family_only_is_ambiguous():
    ambiguous = resolve_material_thermal_property(request(material_family="EPS_BOARD"))
    assert ambiguous.status == "AMBIGUOUS_MATERIAL"
    assert len(ambiguous.candidate_record_ids) == 5
    by_density = resolve_material_thermal_property(request(
        material_family="EPS_BOARD", density_kg_m3=Decimal("30")))
    # Record identity is resolved; no operating-condition decision was supplied.
    assert by_density.status == "RECORD_RESOLVED"
    assert by_density.record.row_number == 1
    assert by_density.design_lambda_w_mk is None
    boundary = resolve_material_thermal_property(request(
        material_family="EPS_BOARD", density_kg_m3=Decimal("25")))
    assert boundary.status == "AMBIGUOUS_MATERIAL"  # overlapping endpoints are not guessed


def test_registered_exact_material_aliases_expose_choices_without_fuzzy_lambda_binding():
    eps = resolve_material_thermal_property(request(material_family="пенополистирол"))
    assert eps.status == "AMBIGUOUS_MATERIAL"
    assert len(eps.candidate_record_ids) == 5
    xps = resolve_material_thermal_property(request(material_family="экструзионный пенополистирол"))
    assert xps.status == "AMBIGUOUS_MATERIAL"
    assert xps.candidate_record_ids == ["SP50-2024-M1-R7", "SP50-2024-M1-R8"]


def test_property_claim_source_and_authority_must_match():
    with pytest.raises(ValueError, match="MATERIAL_SOURCE_AUTHORITY_MISMATCH"):
        MaterialPropertyClaim(
            source_type="product_document", authority_class="PROJECT_AUTHORITATIVE",
            lambda_value="0.04", units="W/(m*K)", source_reference="catalog://p",
            source_field="lambda")


def test_exact_noninsulation_record_without_A_or_B_resolves_record_not_design_lambda():
    result = resolve_material_thermal_property(request(
        exact_normative_record_id="SP50-2024-M1-R217"))
    assert result.status == "RECORD_RESOLVED"
    assert result.record.row_number == 217
    assert result.lambda_dry_w_mk == result.record.lambda_dry_w_mk
    assert result.design_lambda_w_mk is None
    assert "OPERATING_CONDITION_REQUIRED" in result.diagnostics


@pytest.mark.parametrize("condition,expected_attr", [
    (EnvelopeOperatingCondition.A, "lambda_a_w_mk"),
    (EnvelopeOperatingCondition.B, "lambda_b_w_mk"),
])
def test_condition_selects_only_matching_design_lambda(condition, expected_attr):
    result = resolve_material_thermal_property(request(
        exact_normative_record_id="SP50-2024-M1-R217",
        operating_condition=condition,
        operating_condition_source_reference="project://building/rev-2",
        operating_condition_source_field="humidity-regime"))
    assert result.status == "RESOLVED"
    assert result.design_lambda_w_mk == getattr(result.record, expected_attr)
    assert result.design_lambda_w_mk != result.lambda_dry_w_mk
    layer = construction_layer_from_resolution("concrete-layer", "0.2", result)
    assert layer.lambda_w_mk == result.design_lambda_w_mk
    assert layer.lambda_provenance.source_type == "project_approved_normative_extract"
    assert layer.material_record_id == result.record.record_id


def test_missing_condition_provenance_fails_closed_and_no_dry_fallback():
    result = resolve_material_thermal_property(request(
        exact_normative_record_id="SP50-2024-M1-R217",
        operating_condition="A"))
    assert result.status == "INSUFFICIENT_INPUT"
    assert result.design_lambda_w_mk is None
    assert "OPERATING_CONDITION_PROVENANCE_REQUIRED" in result.diagnostics
    with pytest.raises(ValueError, match="MATERIAL_DESIGN_LAMBDA_UNRESOLVED"):
        construction_layer_from_resolution("concrete-layer", "0.2", result)


def test_condition_reference_without_authority_is_not_sufficient_provenance():
    result = resolve_material_thermal_property(MaterialResolutionRequest(
        material_product_id="layer-material", exact_normative_record_id="SP50-2024-M1-R217",
        operating_condition="A", operating_condition_source_reference="project://building/r2",
        operating_condition_source_field="condition"))
    assert result.status == "INSUFFICIENT_INPUT"
    assert "OPERATING_CONDITION_PROVENANCE_REQUIRED" in result.diagnostics


def test_sp345_route_consumes_AB_and_reaches_specialized_layer_resistance():
    result = resolve_material_thermal_property(request(
        exact_normative_record_id="SP50-2024-M1-R1",
        operating_condition="A",
        operating_condition_source_reference="project://building/rev-2",
        operating_condition_source_field="humidity-regime",
        sp345_construction_scope="OTHER_OR_UNLISTED", sp345_lambda_route="DIRECT_REFERENCE"))
    assert result.record is not None
    assert result.lambda_dry_w_mk is not None
    assert result.lambda_a_w_mk is not None
    assert result.status == "RESOLVED"
    assert result.design_lambda_w_mk == Decimal("0.040")
    layer = construction_layer_from_resolution("eps-layer", "0.1", result)
    assert layer.resistance_method == "SP345_FORMULA_5_1A"
    assert layer.layer_operating_coefficient == Decimal("1")
    from agent.ufh_envelope_construction_resolver import (
        ConstructionBoundaryKind, ConstructionSourceMode, EnvelopeAssemblyDefinition, calculate_assembly,
        SurfaceResistanceMethod,
    )
    from agent.ufh_project_engineering_profile_authoring import AuthoringProvenance
    surface = SurfaceResistanceMethod(method_id="SP50-test-only", method_revision="fixture-v1",
        r_si_m2k_w=Decimal("0.13"), r_se_m2k_w=Decimal("0.04"),
        provenance=AuthoringProvenance(source_type="test_only", source_reference="test://surface",
            source_field="surface coefficients", transformation="test fixture only", units="m2*K/W"))
    assembly = calculate_assembly(EnvelopeAssemblyDefinition(assembly_id="insulation-test",
        boundary_kind=ConstructionBoundaryKind.EXTERIOR_WALL, layers=[layer],
        source_reference="test://assembly", source_field="layers"),
        ConstructionSourceMode.LAYERED_CUSTOM_ASSEMBLY, surface_method=surface)
    assert assembly.layered_resistance_m2k_w == Decimal("2.5")
    assert assembly.total_resistance_m2k_w == Decimal("2.67")
    assert assembly.u_value_w_m2k == Decimal(1) / Decimal("2.67")


def test_exact_material_revision_change_invalidates_result_and_identity_ignores_climate():
    a = resolve_material_thermal_property(request(
        exact_normative_record_id="SP50-2024-M1-R217", operating_condition="A",
        operating_condition_source_reference="project://building/r2",
        operating_condition_source_field="condition"))
    b = resolve_material_thermal_property(request(
        exact_normative_record_id="SP50-2024-M1-R217", operating_condition="A",
        operating_condition_source_reference="project://building/r2",
        operating_condition_source_field="condition", source_revision="source-rev-2"))
    assert a.dependency_digest != b.dependency_digest
    assert a.record.record_id == b.record.record_id
    # Location is intentionally not part of MaterialResolutionRequest.
    assert "climate_locality" not in MaterialResolutionRequest.model_fields


def test_explicit_project_manufacturer_and_normative_claims_conflict_closed():
    claim_project = MaterialPropertyClaim(
        source_type="project_data", authority_class="PROJECT_AUTHORITATIVE",
        lambda_value="0.50", units="W/(m·°C)", source_reference="project://materials",
        source_field="lambda", source_revision="rev-7")
    result = resolve_material_thermal_property(request(property_claims=[claim_project],
        operating_condition="A", operating_condition_source_reference="project://building",
        operating_condition_source_field="condition"))
    assert result.status == "RESOLVED"
    assert result.design_lambda_w_mk == Decimal("0.50")
    assert result.provenance.source_reference == "project://materials"
    assert result.provenance.transformation.find("W/(m·°C)") >= 0
    conflict = MaterialPropertyClaim(
        source_type="product_document", authority_class="MANUFACTURER_AUTHORITATIVE",
        lambda_value="0.60", units="W/(m*K)", source_reference="catalog://product",
        source_field="declared-lambda")
    result = resolve_material_thermal_property(request(property_claims=[claim_project, conflict]))
    assert result.status == "SOURCE_VALUE_CONFLICT"


def test_multiple_material_resolutions_flow_through_session_to_existing_conditional_U():
    session = apply_ufh_questionnaire_answer(
        actual_session(), answer("envelope", "LAYERED_CUSTOM_ASSEMBLY"))
    payload = wall_payload()
    layers = [
        {"material_product_id": "concrete-217", "thickness_m": "0.20",
         "material_query": {"exact_normative_record_id": "SP50-2024-M1-R217",
             "operating_condition": "A", "operating_condition_source_reference": "project://building/rev-2",
             "operating_condition_source_field": "envelope-operating-condition",
             "operating_condition_authority_class": "PROJECT_AUTHORITATIVE"}},
        {"material_product_id": "mortar-218", "thickness_m": "0.02",
         "material_query": {"exact_normative_record_id": "SP50-2024-M1-R218",
             "operating_condition": "A", "operating_condition_source_reference": "project://building/rev-2",
             "operating_condition_source_field": "envelope-operating-condition",
             "operating_condition_authority_class": "PROJECT_AUTHORITATIVE"}},
    ]
    payload["assemblies"][0]["layers"] = layers
    payload["assemblies"][0]["surface_applicability"] = {
        "internal_category": "WALL_FLOOR_SMOOTH_CEILING_LOW_RIB",
        "external_category": "EXTERIOR_WALL_ROOF_EXPOSED_FLOOR_NORTHERN_ZONE",
        "northern_climatic_zone_confirmed": True,
        "climatic_zone_source_reference": "project://building/rev-2",
        "climatic_zone_source_field": "climatic-zone",
    }
    updated = apply_ufh_questionnaire_answer(session, answer("envelope.source", payload))
    execution = updated.resolver_executions[-1].resolver_result
    assert execution.status == "RESOLVED"
    authored = updated.questionnaire_state.authoring.envelope_constructions["selected"]
    assert authored.status == "DERIVED"
    bundle = authored.value
    assembly = bundle["assemblies"][0]
    records = {record.record_id: record for record in SP50_MATERIAL_DATASET.records}
    r_layers = (Decimal("0.20") / records["SP50-2024-M1-R217"].lambda_a_w_mk
                + Decimal("0.02") / records["SP50-2024-M1-R218"].lambda_a_w_mk)
    expected_total = Decimal(1) / Decimal("8.7") + r_layers + Decimal(1) / Decimal("23")
    assert Decimal(assembly["layered_resistance_m2k_w"]) == r_layers
    assert Decimal(assembly["total_resistance_m2k_w"]) == expected_total
    assert Decimal(assembly["u_value_w_m2k"]) == Decimal(1) / expected_total
    assert assembly["resistance_scope"] == "HOMOGENEOUS_SECTION_CONDITIONAL_RESISTANCE"
    assert {layer["material_record_id"] for layer in assembly["layers"]} == {
        "SP50-2024-M1-R217", "SP50-2024-M1-R218"}
    assert all(layer["condition_authority_class"] == "PROJECT_AUTHORITATIVE"
               for layer in assembly["layers"])


def test_layer_change_updates_R_but_keeps_selected_material_property_provenance():
    request_a = request(exact_normative_record_id="SP50-2024-M1-R217",
        operating_condition="A", operating_condition_source_reference="project://b",
        operating_condition_source_field="condition")
    resolved = resolve_material_thermal_property(request_a)
    layer = construction_layer_from_resolution("concrete", "0.20", resolved)
    changed = layer.model_copy(update={"thickness_m": Decimal("0.25")})
    assert layer.material_record_id == changed.material_record_id
    assert layer.lambda_provenance == changed.lambda_provenance
    assert layer.thickness_m != changed.thickness_m


def test_test01_has_no_material_profile_values_written_by_this_resolver():
    # Inspect only the existing production-derived room source. It supplies no
    # construction/material properties and is not used as a material source.
    from pathlib import Path
    room_source = json.loads(Path("projects/Test_01/exports/rooms/rooms.json").read_text(encoding="utf-8"))
    room = room_source["Rooms"][0]
    assert room["SourceHandle"] == "101DAA3"
    assert not any(key.casefold() in {"materials", "layers", "lambda", "uvalue", "u_value", "density"}
                   for key in room)
    assert all("Test_01" not in record.source_references for record in SP50_MATERIAL_DATASET.records)

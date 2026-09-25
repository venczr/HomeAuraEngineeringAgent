from agent.ufh_sp345_insulation_property_resolver import (
    LegacyAppendixTStatus,
    SP345_ETA_DATASET,
    SP345_IDENTITY,
    SP345_LEGACY_REFERENCE_AUDIT,
    SP345_METHOD_DIGEST,
    SP50_2012_2024_INSULATION_COMPARISONS,
    SP345InsulationRequest,
    SP50_2012_APPENDIX_T_DATASET,
    SP50_2012_ORIGINAL_VS_2024_INSULATION_COMPARISONS,
    SP345ConstructionScope,
    SP345GammaSource,
    SP345GammaClaim,
    resolve_sp345_gamma,
    resolve_sp345_insulation_property,
)
from agent.ufh_material_thermal_property_resolver import EnvelopeOperatingCondition
from decimal import Decimal


def test_official_identity_and_amendment_revision_are_pinned():
    assert SP345_IDENTITY.document == "SP 345.1325800.2017"
    assert SP345_IDENTITY.consolidated_revision == "2017+Amendment1+Amendment2"
    assert SP345_IDENTITY.amendment_1_order == "664/pr"
    assert SP345_IDENTITY.amendment_2_order == "1117/pr"
    assert SP345_IDENTITY.amendment_2_effective == "2023-01-24"
    assert SP345_METHOD_DIGEST == SP345_IDENTITY.identity_digest
    assert SP345_IDENTITY.formula_5_1a == "R_s=(delta_s/lambda_s)*gamma_s_operating"
    assert len(SP345_IDENTITY.formula_5_1a_image_sha256) == 64


def test_table_d1_verified_subset_keeps_classes_eta_units_and_provenance():
    assert SP345_ETA_DATASET.table_id == "D.1"
    assert SP345_ETA_DATASET.dataset_id.endswith("TABLE_D1_VERIFIED_SUBSET_V1")
    assert {record.material_class for record in SP345_ETA_DATASET.records} == {
        "MINERAL_WOOL", "CELLULAR_CONCRETE", "XPS", "EPS", "PIR_PUR"
    }
    assert all(record.units == "1/%" and len(record.source_references) >= 2
               for record in SP345_ETA_DATASET.records)
    assert all(record.authority_class == "PROJECT_APPROVED_NORMATIVE_EXTRACT"
               for record in SP345_ETA_DATASET.records)
    # eta [1/%] multiplied by w [%] is dimensionless as written; no /100.
    eps = next(row for row in SP345_ETA_DATASET.records if row.material_class == "EPS")
    assert eps.eta_per_percent * Decimal("10") == Decimal("0.30")


def test_dated_reference_rule_selects_explicitly_retained_2012_reference():
    audit = SP345_LEGACY_REFERENCE_AUDIT
    assert audit.textual_status == "DATED_REFERENCE_EXPLICITLY_RETAINED"
    assert audit.applicability_status == LegacyAppendixTStatus.DATED_REFERENCE_EXPLICITLY_RETAINED
    assert "SP50.2012" in audit.reason
    assert "SP50.2024" in audit.reason
    assert "clause 2" in audit.dated_reference_clause


def test_appendix_t_amendments_1_2_package_is_narrow_pinned_and_distinct_from_2024():
    dataset = SP50_2012_APPENDIX_T_DATASET
    assert dataset.dataset_id == "SP50_2012_APPENDIX_T_AMENDMENTS_1_2"
    assert len(dataset.records) == 8
    assert [row.row_number for row in dataset.records] == list(range(1, 9))
    assert all(row.revision == "2012+Amendment1+Amendment2" and len(row.source_references) >= 2
               for row in dataset.records)
    assert dataset.records[0].density_text == "25–35"
    assert dataset.records[0].lambda_a_w_mk == Decimal("0.040")


def test_legacy_vs_current_sp50_comparison_preserves_amended_revision_semantics():
    assert len(SP50_2012_2024_INSULATION_COMPARISONS) == 3
    for comparison in SP50_2012_2024_INSULATION_COMPARISONS:
        assert comparison.comparison_status == "IDENTICAL_RELEVANT_FIELDS"
        assert comparison.comparison_scope == "AUDIT_ONLY_NOT_A_SUBSTITUTION"
        assert len(comparison.source_references) == 2
        # Amended 2012 rows 1, 7, 8 match selected 2024 rows; this audit
        # does not rebase the SP345 dated dependency.
        assert comparison.legacy_lambda0_w_mk == comparison.current_lambda0_w_mk
    # The prior unamended 2012 comparison is preserved as audit evidence only;
    # it is not used for the consolidated Amendment-1+2 SP345 package.
    assert all(row.comparison_status == "CHANGED"
               for row in SP50_2012_ORIGINAL_VS_2024_INSULATION_COMPARISONS)


def test_existing_ab_is_consumed_and_direct_lambda_is_bound_from_dated_appendix_t():
    result = resolve_sp345_insulation_property(SP345InsulationRequest(
        material_record_id="SP50-2024-M1-R1",
        operating_condition=EnvelopeOperatingCondition.A,
        operating_condition_source_reference="project://operating-condition",
        operating_condition_source_field="envelope.operating_condition",
        operating_condition_authority_class="PROJECT_APPROVED_NORMATIVE_EXTRACT",
        construction_scope=SP345ConstructionScope.OTHER_OR_UNLISTED,
        lambda_route="DIRECT_REFERENCE",
    ))
    assert result.status == "RESOLVED"
    assert result.operating_condition == EnvelopeOperatingCondition.A
    assert result.design_lambda_w_mk == Decimal("0.040")
    assert result.direct_reference_lambda_w_mk == Decimal("0.040")
    assert result.appendix_d_lambda_w_mk == Decimal("0.04028")
    assert result.route_comparison == "BOTH_DIFFERENCE_REPORTED_NO_TOLERANCE"
    assert result.gamma.source == SP345GammaSource.NORMATIVE_FALLBACK_SP345_5_2
    assert result.gamma.value == Decimal("1")


def test_unresolved_existing_ab_precedes_property_resolution():
    result = resolve_sp345_insulation_property(SP345InsulationRequest(
        material_record_id="SP50-2024-M1-R7"))
    assert result.status == "OPERATING_CONDITION_REQUIRED"
    assert result.design_lambda_w_mk is None


def test_revision_and_dependency_changes_change_digest_deterministically():
    request = SP345InsulationRequest(material_record_id="SP50-2024-M1-R7",
        operating_condition=EnvelopeOperatingCondition.B,
        operating_condition_source_reference="project://conditions/r1",
        operating_condition_source_field="condition")
    first = resolve_sp345_insulation_property(request)
    again = resolve_sp345_insulation_property(request)
    changed = resolve_sp345_insulation_property(request.model_copy(update={"source_revision": "r2"}))
    assert first.dependency_digest == again.dependency_digest
    assert first.dependency_digest != changed.dependency_digest


def test_formula_5_1a_layer_multiplier_and_specific_appendix_e_precedence():
    fallback = resolve_sp345_gamma(SP345ConstructionScope.OTHER_OR_UNLISTED)
    assert fallback.claim.value == Decimal("1")
    assert fallback.claim.clause_id == "SP345:2017+AMD1+AMD2:5.2"
    assert resolve_sp345_gamma(SP345ConstructionScope.ROOF).status == "APPENDIX_E_RESULT_REQUIRED"
    appendix_e = SP345GammaClaim(value="0.9", source="APPENDIX_E_METHOD_RESULT",
        scope="ROOF", source_reference="normative://SP345/E.2", source_field="E.2/R ratio",
        authority_class="PROJECT_APPROVED_NORMATIVE_EXTRACT", clause_id="E.2")
    assert resolve_sp345_gamma(SP345ConstructionScope.ROOF, appendix_e=appendix_e).claim.value == Decimal("0.9")


def test_appendix_d_uses_eta_times_percent_without_percent_rescaling_and_route_choice_is_explicit():
    base = SP345InsulationRequest(material_record_id="SP50-2024-M1-R1",
        operating_condition="B", operating_condition_source_reference="project://AB",
        operating_condition_source_field="A/B", operating_condition_authority_class="PROJECT_APPROVED_NORMATIVE_EXTRACT",
        construction_scope="OTHER_OR_UNLISTED")
    undecided = resolve_sp345_insulation_property(base)
    assert undecided.status == "LAMBDA_ROUTE_SELECTION_REQUIRED"
    assert undecided.appendix_d_lambda_w_mk == Decimal("0.0494")
    selected = resolve_sp345_insulation_property(base.model_copy(update={"lambda_route": "APPENDIX_D_CALCULATED"}))
    assert selected.status == "RESOLVED"
    assert selected.design_lambda_w_mk == Decimal("0.0494")


def test_ab_selects_legacy_columns_and_project_or_test_gamma_beats_appendix_e():
    def resolve(condition):
        return resolve_sp345_insulation_property(SP345InsulationRequest(
            material_record_id="SP50-2024-M1-R1", operating_condition=condition,
            operating_condition_source_reference="project://AB", operating_condition_source_field="A/B",
            operating_condition_authority_class="PROJECT_APPROVED_NORMATIVE_EXTRACT",
            construction_scope="ROOF", lambda_route="DIRECT_REFERENCE",
            gamma_appendix_e_claim=SP345GammaClaim(value="0.9", source="APPENDIX_E_METHOD_RESULT",
                scope="ROOF", source_reference="normative://E2", source_field="E.2 result",
                authority_class="PROJECT_APPROVED_NORMATIVE_EXTRACT", clause_id="E.2"),
            gamma_project_or_test_claim=SP345GammaClaim(value="0.95", source="PROJECT_OR_TEST_RESULT",
                scope="ROOF", source_reference="project://tested-assembly", source_field="test.gamma",
                authority_class="PROJECT_AUTHORITATIVE")))
    a, b = resolve("A"), resolve("B")
    assert a.design_lambda_w_mk == Decimal("0.040")
    assert b.design_lambda_w_mk == Decimal("0.049")
    assert a.gamma.value == b.gamma.value == Decimal("0.95")
    assert a.gamma.source == SP345GammaSource.PROJECT_OR_TEST_RESULT
    assert a.dependency_digest != b.dependency_digest

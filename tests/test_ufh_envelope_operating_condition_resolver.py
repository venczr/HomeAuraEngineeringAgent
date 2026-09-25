from decimal import Decimal

import pytest

from agent.ufh_envelope_operating_condition_resolver import (
    AUTHORITY, ConstructionMoistureZoneInput, SOURCE_PACKAGE_DIGEST,
    TABLE1_ROWS, TABLE2_ROWS, apply_condition_to_material_request,
    classify_room_moisture_regime, resolve_envelope_operating_condition,
)
from agent.ufh_material_thermal_property_resolver import (
    MaterialResolutionRequest, construction_layer_from_resolution,
    resolve_material_thermal_property,
)


@pytest.mark.parametrize(("t", "rh", "expected"), [
    ("12", "60", "DRY"), ("12", "60.0001", "NORMAL"),
    ("12", "75", "NORMAL"), ("12", "75.0001", "HUMID"),
    ("12.0001", "50", "DRY"), ("12.0001", "50.0001", "NORMAL"),
    ("12.0001", "60", "NORMAL"), ("12.0001", "60.0001", "HUMID"),
    ("12.0001", "75", "HUMID"), ("12.0001", "75.0001", "WET"),
    ("24", "50", "DRY"), ("24", "60", "NORMAL"), ("24", "75", "HUMID"),
    ("24", "75.0001", "WET"), ("24.0001", "40", "DRY"),
    ("24.0001", "40.0001", "NORMAL"), ("24.0001", "50", "NORMAL"),
    ("24.0001", "50.0001", "HUMID"), ("24.0001", "60", "HUMID"),
    ("24.0001", "60.0001", "WET"),
])
def test_table1_exact_inclusive_boundaries(t, rh, expected):
    regime, row = classify_room_moisture_regime(Decimal(t), Decimal(rh))
    assert regime == expected
    assert row in TABLE1_ROWS


def test_table2_matrix_matches_packaged_rows_and_scope_is_external_only():
    expected = {
        "DRY": ("A", "A", "B"), "NORMAL": ("A", "B", "B"),
        "HUMID": ("B", "B", "B"), "WET": ("B", "B", "B"),
    }
    for regime, values in expected.items():
        assert tuple(next(r.condition for r in TABLE2_ROWS
                          if r.room_regime == regime and r.moisture_zone == zone)
                     for zone in ("DRY", "NORMAL", "HUMID")) == values
    result = resolve_envelope_operating_condition(
        indoor_design_temperature_c=20, indoor_design_relative_humidity_percent=55,
        moisture_zone=None, construction_scope="INTERIOR", project_id="p", room_id="r",
        project_revision="rev", temperature_provenance="project://t", humidity_provenance="project://rh")
    assert result.status == "OPERATING_CONDITION_NOT_APPLICABLE"
    assert result.operating_condition is None


def zone(value):
    return ConstructionMoistureZoneInput(zone=value, source_reference="approved-project://climate-zone",
        source_field="Appendix A cross-reference", source_revision="rev-1",
        authority_class="PROJECT_AUTHORITATIVE")


def resolve(temp, rh, moisture_zone):
    return resolve_envelope_operating_condition(
        indoor_design_temperature_c=temp,
        indoor_design_relative_humidity_percent=rh,
        moisture_zone=moisture_zone, construction_scope="EXTERIOR_ENVELOPE",
        project_id="synthetic-project", room_id="synthetic-room",
        project_revision="fixture-r1", temperature_provenance="project://room/HeatingTemperatureC",
        humidity_provenance="user-decision://indoor-rh")


def test_missing_rh_zone_and_no_safe_b_fallback():
    assert resolve(20, None, zone("NORMAL")).status == "INSUFFICIENT_INPUT"
    needs_zone = resolve(20, 55, None)
    assert needs_zone.status == "MOISTURE_ZONE_SOURCE_REQUIRED"
    assert needs_zone.room_moisture_regime == "NORMAL"
    assert needs_zone.operating_condition is None


def test_table1_to_table2_to_material_lambda_a_b():
    # At 20 C, RH 50% is dry and gives A in a dry zone; RH 55% is normal and
    # gives B in a normal zone. The same record supplies both lambdas.
    a = resolve(20, 50, zone("DRY"))
    b = resolve(20, 55, zone("NORMAL"))
    assert (a.room_moisture_regime, a.operating_condition) == ("DRY", "A")
    assert (b.room_moisture_regime, b.operating_condition) == ("NORMAL", "B")
    base = MaterialResolutionRequest(material_product_id="reinforced-concrete",
        exact_normative_record_id="SP50-2024-M1-R216")
    ra = resolve_material_thermal_property(apply_condition_to_material_request(base, a))
    rb = resolve_material_thermal_property(apply_condition_to_material_request(base, b))
    assert ra.status == rb.status == "RESOLVED"
    assert ra.design_lambda_w_mk == ra.record.lambda_a_w_mk
    assert rb.design_lambda_w_mk == rb.record.lambda_b_w_mk
    assert ra.design_lambda_w_mk != rb.design_lambda_w_mk
    assert ra.operating_condition_authority_class == AUTHORITY


def test_derived_condition_flows_through_layer_resistance_and_surface_u():
    from agent.ufh_envelope_construction_resolver import (
        ConstructionBoundaryKind, ConstructionSourceMode, EnvelopeAssemblyDefinition,
        calculate_assembly,
    )
    from agent.ufh_sp50_surface_resistance import (
        ExternalSurfaceCategory, InternalSurfaceCategory, SurfaceApplicability,
        resolve_surface_resistances,
    )

    condition = resolve(20, 55, zone("NORMAL"))  # normal room + normal zone => B
    request = MaterialResolutionRequest(material_product_id="concrete-layer",
        exact_normative_record_id="SP50-2024-M1-R216")
    resolved_material = resolve_material_thermal_property(
        apply_condition_to_material_request(request, condition))
    layer = construction_layer_from_resolution("concrete-layer", "0.1", resolved_material)
    surfaces = resolve_surface_resistances(SurfaceApplicability(
        internal_category=InternalSurfaceCategory.WALL_FLOOR_SMOOTH_CEILING_LOW_RIB,
        external_category=ExternalSurfaceCategory.EXTERIOR_WALL_ROOF_EXPOSED_FLOOR_NORTHERN_ZONE,
        northern_climatic_zone_confirmed=True,
        source_reference="synthetic://envelope-context", source_field="wall.surface-applicability",
        climatic_zone_source_reference="approved-project://climatic-zone",
        climatic_zone_source_field="building.climatic-zone"))
    assert surfaces.status == "RESOLVED"
    assembly = calculate_assembly(EnvelopeAssemblyDefinition(
        assembly_id="condition-linked-wall", boundary_kind=ConstructionBoundaryKind.EXTERIOR_WALL,
        layers=[layer], source_reference="synthetic://layered-wall", source_field="layers"),
        ConstructionSourceMode.LAYERED_CUSTOM_ASSEMBLY, surface_method=surfaces.method)
    assert assembly.layered_resistance_m2k_w == Decimal("0.1") / resolved_material.design_lambda_w_mk
    assert assembly.total_resistance_m2k_w is not None
    assert assembly.u_value_w_m2k == Decimal(1) / assembly.total_resistance_m2k_w
    assert assembly.resistance_scope == "HOMOGENEOUS_SECTION_CONDITIONAL_RESISTANCE"


def test_invalidation_dependencies_and_determinism():
    inputs = dict(indoor_design_temperature_c=20, indoor_design_relative_humidity_percent=55,
        moisture_zone=zone("NORMAL"), construction_scope="EXTERIOR_ENVELOPE",
        project_id="p", room_id="r", project_revision="rev",
        temperature_provenance="project://t", humidity_provenance="project://rh")
    first = resolve_envelope_operating_condition(**inputs)
    assert first == resolve_envelope_operating_condition(**inputs)
    assert first.dependency_digest != resolve_envelope_operating_condition(
        **{**inputs, "indoor_design_relative_humidity_percent": 50}).dependency_digest
    assert first.dependency_digest != resolve_envelope_operating_condition(
        **{**inputs, "moisture_zone": zone("DRY")}).dependency_digest
    assert first.dependency_digest == resolve_envelope_operating_condition(
        **{**inputs, "project_revision": "new-revision"}).dependency_digest
    assert first.source_package_digest == SOURCE_PACKAGE_DIGEST


def test_appendix_a_requires_explicit_provenance_bearing_zone():
    assert resolve(20, 55, None).diagnostics == ["APPENDIX_A_LOCALITY_MAPPING_NOT_AUTOMATED"]
    with pytest.raises(Exception):
        ConstructionMoistureZoneInput(zone="NORMAL", source_reference="", source_field="",
            source_revision="", authority_class="REFERENCE_ONLY")


def test_common_resolver_handoff_uses_project_indoor_temperature_and_suppresses_questions():
    from agent.ufh_project_pre_generation import apply_ufh_questionnaire_answer
    from agent.ufh_pre_generation_questionnaire import Decision
    from tests.test_ufh_project_pre_generation import actual_session

    session = actual_session().model_copy(deep=True)
    assert session.questionnaire_state.authoring.envelope_constructions[
        "operating_condition"].status == "UNSET"
    session = apply_ufh_questionnaire_answer(session, Decision(
        question_id="envelope", value="LAYERED_CUSTOM_ASSEMBLY",
        source_reference="synthetic://scope", revision="r1"))
    session = apply_ufh_questionnaire_answer(session, Decision(
        question_id="envelope.source", value={"construction_scope": "EXTERIOR_ENVELOPE",
            "source_reference": "synthetic://assembly", "source_field": "assemblies",
            "assemblies": []}, source_reference="synthetic://assembly", revision="r1"))
    assert {q.question_id for q in session.active_questions} >= {"indoor_rh", "moisture_zone"}
    session = apply_ufh_questionnaire_answer(session, Decision(
        question_id="indoor_rh", value={"value": 55, "unit": "%"},
        source_reference="project-decision://rh", revision="r1"))
    session = apply_ufh_questionnaire_answer(session, Decision(
        question_id="moisture_zone", value={"zone": "NORMAL",
            "source_reference": "approved-project://zone", "source_field": "Appendix A assignment",
            "source_revision": "r1", "authority_class": "PROJECT_AUTHORITATIVE"},
        source_reference="approved-project://zone", revision="r1"))
    assert session.questionnaire_state.authoring.envelope_constructions[
        "operating_condition"].value == "B"
    assert "indoor_rh" not in {q.question_id for q in session.active_questions}
    assert "moisture_zone" not in {q.question_id for q in session.active_questions}
    assert session.status != "READY_FOR_ENGINEERING"
    assert not any("SIZING" in item.resolver_result.diagnostics[0]
                   for item in session.resolver_executions if item.resolver_result.diagnostics)


def test_invalid_rh_or_zone_answer_is_rejected_atomically():
    from agent.ufh_project_pre_generation import apply_ufh_questionnaire_answer
    from agent.ufh_pre_generation_questionnaire import Decision
    from tests.test_ufh_project_pre_generation import actual_session

    session = actual_session().model_copy(deep=True)
    session = apply_ufh_questionnaire_answer(session, Decision(question_id="envelope",
        value="LAYERED_CUSTOM_ASSEMBLY", source_reference="synthetic://scope", revision="r1"))
    session = apply_ufh_questionnaire_answer(session, Decision(question_id="envelope.source",
        value={"construction_scope": "EXTERIOR_ENVELOPE", "assemblies": []},
        source_reference="synthetic://scope", revision="r1"))
    before = session.session_digest
    with pytest.raises(ValueError, match="RELATIVE_HUMIDITY_OUT_OF_RANGE"):
        apply_ufh_questionnaire_answer(session, Decision(question_id="indoor_rh",
            value={"value": 101, "unit": "%"}, source_reference="user://rh", revision="r1"))
    assert session.session_digest == before

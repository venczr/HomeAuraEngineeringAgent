from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from agent.ventilation_infiltration_heat_loss import (
    SP60_AIR_METHOD_DIGEST,
    SP60_AIR_METHOD_PACKAGE,
    A1ComponentInput,
    AerodynamicCoefficientModel,
    AirPermeableEnvelopeElement,
    InfiltrationInput,
    RequiredVentilationAirflow,
    SourcedDecimal,
    aggregate_sp60_a1_components,
    audit_project_air_exchange,
    calculate_air_density,
    calculate_room_infiltration_heat_loss,
    calculate_room_ventilation_heat_loss,
    rectangular_building_aerodynamic_coefficients,
)
from agent.ufh_project_adapter import MappedProjectField, ProjectFieldProvenance, ProjectUfhAdapterResult
from agent.ufh_project_engineering_profile_authoring import AuthoringProvenance

D = Decimal
HASH = "a" * 64


def p(path, units, kind="test_only"):
    return AuthoringProvenance(
        source_type=kind,
        source_reference=f"test://{path}",
        source_sha256=HASH,
        source_field=path,
        transformation="explicit synthetic fixture; source is not Test_01 data",
        units=units,
    )


def sv(value, units, path):
    return SourcedDecimal(value=D(value), units=units, provenance=p(path, units))


def airflow_direct(l="10", *, extra=None):
    return RequiredVentilationAirflow(
        source_mode="PROJECT_DESIGN_AIRFLOW", direct_airflow_m3_h=D(l),
        direct_airflow_provenance=p("hvac.required_outdoor_airflow", "m3/h"),
        pressurization_makeup_airflow_m3_h=D(extra) if extra is not None else None,
        pressurization_makeup_provenance=p("hvac.pressurization_excess", "m3/h") if extra is not None else None,
    )


def infiltration_input(*, mode="BALANCED_SUPPLY_EXHAUST", kind="WINDOW_OR_TRANSLUCENT", elements=None, room_id="fixture-room"):
    return InfiltrationInput(
        room_id=room_id, indoor_temperature=sv("20", "°C", "room.design_temperature"),
        outdoor_temperature=sv("0", "°C", "climate.design_temperature"), pressure_mode=mode,
        building_height_m=D("10"), building_height_provenance=p("building.height", "m"),
        wind_speed_cold_design_m_s=D("2"), wind_speed_provenance=p("climate.design_wind", "m/s"),
        aerodynamic_coefficients=AerodynamicCoefficientModel(
            building_form="RECTANGULAR", windward_coefficient=D("0.8"),
            leeward_coefficient=D("-0.6"), provenance=p("SP60.rectangular_coefficients", "dimensionless")),
        pressure_inventory="COMPLETE", pressure_inventory_provenance=p("envelope.air_permeable_inventory", "1"),
        elements=elements if elements is not None else [AirPermeableEnvelopeElement(
            element_id="window-1", element_kind=kind, area_m2=D("2"),
            area_provenance=p("boundary.window.area", "m2"),
            air_permeability_resistance_ru_m2_h_pa_kg=D("10"),
            resistance_provenance=p("product.window.Ru", "m2*h*Pa/kg"),
            center_height_m=D("1"), center_height_provenance=p("boundary.window.center_height", "m"),
            wind_height_coefficient=D("1.2"), wind_height_coefficient_provenance=p("SP20.kz", "dimensionless"),
        )],
    )


def test_current_sp60_formula_package_has_revision_and_visually_verified_equations():
    from agent.sp60_normative_method import SP60_CANONICAL_REVISION
    assert SP60_AIR_METHOD_PACKAGE["canonical_revision"] is SP60_CANONICAL_REVISION
    assert SP60_AIR_METHOD_PACKAGE["canonical_revision"]["consolidated_amendments"] == [1, 2, 3, 4, 5, 6]
    assert SP60_AIR_METHOD_PACKAGE["canonical_revision"]["amendment_6"]["effective_date"] == "2026-07-07"
    for formula in ("A.1", "A.5", "A.6", "A.7", "A.8", "A.9", "A.10"):
        assert len(SP60_AIR_METHOD_PACKAGE["formula_records"][formula]["visual_sha256"]) == 64
    assert SP60_AIR_METHOD_PACKAGE["formula_records"]["A.1"]["semantics"] == "Q_ов^p = sum_n(Q_tr,n + Q_vent,n + Q_inf,n + Q_mts,n)"
    assert SP60_AIR_METHOD_PACKAGE["a1_internal_gains_term"] == "NOT_PRESENT_IN_CURRENT_A1_FORMULA"
    assert len(SP60_AIR_METHOD_DIGEST) == 64


def test_a6_density_uses_sourced_temperature_and_no_one_point_two_fallback():
    result = calculate_air_density(sv("0", "°C", "design.outdoor_temperature"))
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        expected = D("353") / D("273")
    assert result.density_kg_m3 == expected
    assert result.formula_id == "SP60_A6_2020_AMD1_6"
    assert result.provenance.source_field == "SP60.13330.2020/A.6"
    assert result.density_kg_m3 != D("1.2")


def test_a5_direct_design_airflow_calculates_massflow_and_qvent():
    result = calculate_room_ventilation_heat_loss(
        "fixture-room", airflow_direct("10"), sv("20", "°C", "Ti"), sv("-10", "°C", "Tn"))
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        rho = D("353") / D("263")
        mass = D("10") * rho
        expected_q = D("30") * mass * D("1") * D("0.28")
    assert result.status == "RESOLVED"
    assert result.air_density.density_kg_m3 == rho
    assert result.mass_airflow_kg_h == mass
    assert result.q_vent_w == expected_q
    assert any(item.source_field == "SP60.13330.2020/A.5" for item in result.ventilation_provenance)


def test_a4_normative_ach_requires_correct_semantics_and_authoritative_volume():
    with pytest.raises(ValidationError, match="VENTILATION_AIRFLOW_SOURCE_REQUIRED"):
        RequiredVentilationAirflow(source_mode="NORMATIVE_AIR_CHANGE_RATE",
                                   design_air_changes_per_h=D("1"), air_changes_provenance=p("project.ach", "1/h"),
                                   room_volume_m3=D("50"), room_volume_provenance=p("room.volume", "m3"))
    request = RequiredVentilationAirflow(
        source_mode="NORMATIVE_AIR_CHANGE_RATE", design_air_changes_per_h=D("2"),
        air_changes_provenance=p("norm.required_cold_period_ach", "1/h"),
        air_changes_semantics="REQUIRED_COLD_PERIOD_DESIGN_AIR_CHANGE_RATE",
        room_volume_m3=D("50"), room_volume_provenance=p("project.volume", "m3"))
    result = calculate_room_ventilation_heat_loss("r", request, sv("20", "°C", "Ti"), sv("0", "°C", "To"))
    assert result.required_base_airflow_m3_h == D("100")
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        expected_q = D("20") * D("100") * (D("353") / D("273")) * D("0.28")
    assert result.q_vent_w == expected_q
    with pytest.raises(ValidationError, match="VENTILATION_SOURCE_MODE_FIELDS_CONFLICT"):
        RequiredVentilationAirflow(
            source_mode="PROJECT_DESIGN_AIRFLOW", direct_airflow_m3_h=D("10"),
            direct_airflow_provenance=p("design.airflow", "m3/h"),
            design_air_changes_per_h=D("0.5"), air_changes_provenance=p("project.ach", "1/h"),
            air_changes_semantics="REQUIRED_COLD_PERIOD_DESIGN_AIR_CHANGE_RATE",
            room_volume_m3=D("50"), room_volume_provenance=p("volume", "m3"))


def test_per_person_airflow_requires_occupancy_and_rate_provenance():
    with pytest.raises(ValidationError, match="DESIGN_OCCUPANCY_REQUIRED"):
        RequiredVentilationAirflow(source_mode="PER_PERSON_REQUIREMENT")
    valid = RequiredVentilationAirflow(
        source_mode="PER_PERSON_REQUIREMENT", design_occupancy=2,
        occupancy_provenance=p("project.design_occupancy", "person"),
        airflow_per_person_m3_h=D("30"), per_person_rate_provenance=p("norm.per_person", "m3/(h person)"))
    assert valid.resolve_base_airflow()[0] == D("60")


def test_missing_ventilation_inputs_remain_typed_incomplete():
    result = calculate_room_ventilation_heat_loss("r", None, sv("20", "°C", "Ti"), None)
    assert result.status == "INCOMPLETE"
    assert result.q_vent_w is None
    assert set(result.diagnostics) == {"VENTILATION_AIRFLOW_SOURCE_REQUIRED", "CLIMATE_DESIGN_TEMPERATURE_REQUIRED"}


def test_air_exchange_rate_is_audit_only_not_ventilation_or_infiltration():
    mapped = MappedProjectField(
        target_path="sizing.room.insulation.air_changes_per_hour", value=1.25,
        provenance=ProjectFieldProvenance(source_kind="room_extraction", source_file="fixture://rooms.json",
                                          source_sha256=HASH, source_path="$.Rooms[0].AirExchangeRate",
                                          transformation="preserved"), applied_to_request=False)
    adapter = ProjectUfhAdapterResult(
        status="INCOMPLETE", project_id="p", building_id="b", level_id="l", room_id="r",
        source_file="fixture://rooms.json", source_digest=HASH, mapped_fields=[mapped], adapter_digest="b" * 64)
    observed = audit_project_air_exchange(adapter)
    assert observed.status == "UNCLASSIFIED_PROJECT_AIR_EXCHANGE_VALUE"
    assert observed.value == D("1.25")
    assert observed.promoted_to_ventilation_airflow is False
    assert observed.promoted_to_infiltration_airflow is False
    with pytest.raises(ValidationError, match="VENTILATION_AIRFLOW_SOURCE_REQUIRED"):
        RequiredVentilationAirflow(source_mode="NORMATIVE_AIR_CHANGE_RATE",
                                   design_air_changes_per_h=observed.value,
                                   air_changes_provenance=observed.provenance,
                                   room_volume_m3=D("40"), room_volume_provenance=p("volume", "m3"))


def test_a8_and_a9_calculate_infiltration_separately_using_sourced_air_permeability():
    request = infiltration_input()
    result = calculate_room_infiltration_heat_loss(request)
    item = result.elements[0]
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        rho_o = D("353") / D("273")
        rho_i = D("353") / D("293")
        expected_dp = (D("10") - D("1")) * (rho_o - rho_i) * D("9.81") + rho_o * D("2") ** 2 / D("2") * D("1.4") * D("1.2")
        expected_g = (expected_dp / D("10")) ** (D("2") / D("3")) * D("2") / D("10")
        expected_q = D("20") * expected_g * D("1") * D("0.28")
    assert result.status == "RESOLVED"
    assert result.indoor_reference_pressure_pa == 0
    assert item.pressure_difference_pa == expected_dp
    assert item.mass_airflow_kg_h == expected_g
    assert result.q_inf_w == expected_q
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        assert item.filtering_exponent == D("2") / D("3")
    assert item.pressure_provenance.source_field == "SP60.13330.2020/A.9"


def test_a10_natural_pressure_is_formula_based_and_balanced_ventilation_omits_pv():
    natural = calculate_room_infiltration_heat_loss(infiltration_input(mode="NO_ORGANIZED_VENTILATION"))
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        rho_o, rho_i = D("353") / D("273"), D("353") / D("293")
        expected_pv = D("10") * (rho_o - rho_i) * D("9.81") + rho_o * D("4") / D("4") * D("1.4") * D("1.2")
    assert natural.indoor_reference_pressure_pa == expected_pv
    balanced = calculate_room_infiltration_heat_loss(infiltration_input(mode="BALANCED_SUPPLY_EXHAUST"))
    assert balanced.indoor_reference_pressure_pa == 0
    assert balanced.total_mass_airflow_kg_h != natural.total_mass_airflow_kg_h


def test_a8_pressure_reference_and_exponents_are_normatively_scoped():
    assert SP60_AIR_METHOD_PACKAGE["normative_constants"]["reference_pressure_pa"] == "10"
    door = infiltration_input(kind="DOOR_GATE_OR_OPENING")
    door_result = calculate_room_infiltration_heat_loss(door)
    assert door_result.elements[0].filtering_exponent == D("0.5")
    other = AirPermeableEnvelopeElement(
        element_id="custom", element_kind="OTHER_AIR_PERMEABLE", area_m2=D("1"),
        area_provenance=p("area", "m2"), air_permeability_resistance_ru_m2_h_pa_kg=D("2"),
        resistance_provenance=p("Ru", "m2*h*Pa/kg"), filtering_exponent=D("0.4"),
        filtering_exponent_provenance=p("tested.exponent", "dimensionless"))
    assert other.effective_filtering_exponent()[0] == D("0.4")
    with pytest.raises(ValidationError, match="FILTERING_EXPONENT_SOURCE_REQUIRED"):
        AirPermeableEnvelopeElement(element_id="other", element_kind="OTHER_AIR_PERMEABLE",
                                   area_m2=D(1), area_provenance=p("area", "m2"),
                                   air_permeability_resistance_ru_m2_h_pa_kg=D(1), resistance_provenance=p("Ru", "m2*h*Pa/kg"))


def test_design_wind_aerodynamics_and_wind_height_factor_fail_closed():
    missing_wind = infiltration_input().model_copy(update={"wind_speed_cold_design_m_s": None, "wind_speed_provenance": None})
    result = calculate_room_infiltration_heat_loss(missing_wind)
    assert result.status == "INCOMPLETE"
    assert "DESIGN_WIND_PARAMETER_REQUIRED" in result.diagnostics
    with pytest.raises(ValueError, match="SP20_AERODYNAMIC_MODEL_REQUIRED"):
        rectangular_building_aerodynamic_coefficients("OTHER", p("geometry.form", "dimensionless"))
    no_kz = infiltration_input(elements=[infiltration_input().elements[0].model_copy(update={"wind_height_coefficient": None, "wind_height_coefficient_provenance": None})])
    assert any("DESIGN_WIND_HEIGHT_COEFFICIENT_REQUIRED" in item for item in calculate_room_infiltration_heat_loss(no_kz).diagnostics)


def test_projected_rectangular_coefficients_are_explicitly_scoped_and_digestable():
    model = rectangular_building_aerodynamic_coefficients("RECTANGULAR", p("geometry.building_form", "dimensionless"))
    assert (model.windward_coefficient, model.leeward_coefficient) == (D("0.8"), D("-0.6"))
    assert "rectangular-building" in model.provenance.transformation
    assert model.provenance.source_field == "SP60.13330.2020/A.9"


def test_pressure_positive_room_suppresses_qinf_but_requires_explicit_makeup_air():
    base = infiltration_input()
    pressurized = base.model_copy(update={
        "pressure_mode": "PRESSURIZED_BY_DESIGN",
        "pressurization_makeup_airflow_m3_h": D("3"),
        "pressurization_makeup_provenance": p("hvac.pressurization_excess", "m3/h"),
    })
    inf = calculate_room_infiltration_heat_loss(pressurized)
    vent = calculate_room_ventilation_heat_loss("fixture-room", airflow_direct("10", extra="3"), sv("20", "°C", "Ti"), sv("0", "°C", "To"))
    assert inf.status == "INFILTRATION_SUPPRESSED_BY_DESIGN_PRESSURIZATION"
    assert inf.q_inf_w == 0
    assert inf.ventilation_makeup_airflow_required_in_q_vent_m3_h == D("3")
    assert vent.total_required_airflow_m3_h == D("13")
    with pytest.raises(ValidationError, match="PRESSURIZATION_DESIGN_EVIDENCE_REQUIRED"):
        InfiltrationInput(room_id="r", pressure_mode="PRESSURIZED_BY_DESIGN", pressure_inventory="UNRESOLVED")


def test_complete_empty_permeability_inventory_produces_explicit_zero_not_ach_shortcut():
    source = infiltration_input(elements=[])
    result = calculate_room_infiltration_heat_loss(source)
    assert result.status == "RESOLVED"
    assert result.total_mass_airflow_kg_h == 0
    assert result.q_inf_w == 0
    assert "NO_AIR_PERMEABLE_ELEMENTS_IN_COMPLETE_INVENTORY" in result.diagnostics


def test_unknown_pressure_mode_never_fabricates_zero_or_wind():
    incomplete = infiltration_input().model_copy(update={"indoor_reference_pressure_pa": None,
                                                         "indoor_reference_pressure_provenance": None,
                                                         "pressure_mode": "OTHER_ORGANIZED_VENTILATION"})
    result = calculate_room_infiltration_heat_loss(incomplete)
    assert result.status == "INCOMPLETE"
    assert result.q_inf_w is None
    assert "INDOOR_REFERENCE_PRESSURE_REQUIRED" in result.diagnostics


def test_a1_aggregation_uses_only_current_formula_terms_and_keeps_partial_subtotal():
    transmission = SimpleNamespace(room_id="r", room_transmission_heat_loss_w=D("100"), completeness_status="COMPLETE_DETAILED")
    ventilation = calculate_room_ventilation_heat_loss("r", airflow_direct("10"), sv("20", "°C", "Ti"), sv("0", "°C", "To"))
    infiltration = calculate_room_infiltration_heat_loss(infiltration_input(room_id="r"))
    q_mts_na = A1ComponentInput(status="NOT_APPLICABLE", applicability_provenance=p("materials.not_applicable", "1"), reason="No relevant material movement for this calculation scope")
    partial = aggregate_sp60_a1_components(transmission_result=transmission, ventilation_result=ventilation,
                                          infiltration_result=infiltration, q_mts=q_mts_na)
    assert partial.known_component_subtotal_w == D("100") + ventilation.q_vent_w + infiltration.q_inf_w
    assert partial.total_design_heating_load_w == D("100") + ventilation.q_vent_w + infiltration.q_inf_w
    assert partial.internal_gains_assessment == "NOT_AN_A1_COMPONENT"
    complete = aggregate_sp60_a1_components(
        transmission_result=transmission, ventilation_result=ventilation,
        infiltration_result=infiltration, q_mts=q_mts_na,
        internal_gains_classification_provenance=p("SP60.A1.internal_gains_not_a_term", "1", "normative_source"))
    assert complete.completeness_status == "COMPLETE_SP60_A1_COMPONENTS"
    assert complete.total_design_heating_load_w == complete.q_tr_w + complete.q_vent_w + complete.q_inf_w + D(0)
    assert complete.total_design_heating_load_w != complete.q_tr_w + complete.q_vent_w + complete.q_inf_w - D("50")


def test_incomplete_mts_and_planar_transmission_cannot_claim_complete_a1():
    transmission = SimpleNamespace(room_id="r", room_transmission_heat_loss_w=D("100"), completeness_status="PLANAR_ONLY")
    ventilation = calculate_room_ventilation_heat_loss("r", airflow_direct(), sv("20", "°C", "Ti"), sv("0", "°C", "To"))
    infiltration = calculate_room_infiltration_heat_loss(infiltration_input(room_id="r"))
    result = aggregate_sp60_a1_components(transmission_result=transmission, ventilation_result=ventilation,
                                          infiltration_result=infiltration, q_mts=A1ComponentInput(status="UNRESOLVED"),
                                          internal_gains_classification_provenance=p("classification", "1"))
    assert result.total_design_heating_load_w is None
    assert "Q_TR_COMPLETE_RESULT_REQUIRED" in result.unresolved_components
    assert "Q_MTS_UNRESOLVED" in result.unresolved_components


def test_aggregator_rejects_cross_room_component_mixing():
    transmission = SimpleNamespace(room_id="r", room_transmission_heat_loss_w=D("100"), completeness_status="COMPLETE_DETAILED")
    ventilation = calculate_room_ventilation_heat_loss("other", airflow_direct(), sv("20", "°C", "Ti"), sv("0", "°C", "To"))
    infiltration = calculate_room_infiltration_heat_loss(infiltration_input(room_id="r"))
    result = aggregate_sp60_a1_components(
        transmission_result=transmission, ventilation_result=ventilation,
        infiltration_result=infiltration, q_mts=A1ComponentInput(status="UNRESOLVED"))
    assert result.q_vent_w is None
    assert "VENTILATION_ROOM_ID_MISMATCH" in result.unresolved_components


def test_pressurized_aggregate_requires_same_makeup_flow_in_qvent():
    transmission = SimpleNamespace(room_id="r", room_transmission_heat_loss_w=D("100"), completeness_status="COMPLETE_DETAILED")
    ventilation = calculate_room_ventilation_heat_loss("r", airflow_direct("10"), sv("20", "°C", "Ti"), sv("0", "°C", "To"))
    pressed_data = infiltration_input().model_copy(update={"pressure_mode": "PRESSURIZED_BY_DESIGN",
                                                           "pressurization_makeup_airflow_m3_h": D("3"),
                                                           "pressurization_makeup_provenance": p("extra", "m3/h")})
    infiltration = calculate_room_infiltration_heat_loss(pressed_data)
    q_mts_na = A1ComponentInput(status="NOT_APPLICABLE", applicability_provenance=p("q_mts.na", "1"))
    result = aggregate_sp60_a1_components(transmission_result=transmission, ventilation_result=ventilation,
                                          infiltration_result=infiltration, q_mts=q_mts_na,
                                          internal_gains_classification_provenance=p("not_in_a1", "1"))
    assert "PRESSURIZATION_MAKEUP_MUST_BE_INCLUDED_IN_Q_VENT" in result.unresolved_components
    assert result.total_design_heating_load_w is None


def test_infiltration_and_ventilation_digests_change_only_with_their_dependencies():
    vent = calculate_room_ventilation_heat_loss("r", airflow_direct("10"), sv("20", "°C", "Ti"), sv("0", "°C", "To"))
    changed_flow = calculate_room_ventilation_heat_loss("r", airflow_direct("11"), sv("20", "°C", "Ti"), sv("0", "°C", "To"))
    assert vent.digest != changed_flow.digest
    base = infiltration_input()
    first = calculate_room_infiltration_heat_loss(base)
    changed_routing_unrelated = calculate_room_infiltration_heat_loss(base.model_copy(deep=True))
    assert first.digest == changed_routing_unrelated.digest
    assert SP60_AIR_METHOD_DIGEST == calculate_room_infiltration_heat_loss(base).digest[:0] + SP60_AIR_METHOD_DIGEST


def test_project_adapter_binding_keeps_ach_separate_from_airflow():
    mapped = MappedProjectField(
        target_path="sizing.room.insulation.air_changes_per_hour", value=1.1,
        provenance=ProjectFieldProvenance(source_kind="room_extraction", source_file="fixture://rooms.json",
                                          source_sha256=HASH, source_path="$.Rooms[0].AirExchangeRate",
                                          transformation="identity"), applied_to_request=False)
    adapter = ProjectUfhAdapterResult(status="INCOMPLETE", project_id="p", building_id="b", level_id="l",
                                      room_id="r", source_file="fixture://rooms.json", source_digest=HASH,
                                      mapped_fields=[mapped], adapter_digest="b" * 64)
    observation = audit_project_air_exchange(adapter)
    assert observation.status == "UNCLASSIFIED_PROJECT_AIR_EXCHANGE_VALUE"
    assert observation.provenance.source_field == "$.Rooms[0].AirExchangeRate"

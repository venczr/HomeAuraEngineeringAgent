from decimal import Decimal

import pytest

from agent.building_heat_loss import (
    BuildingHeatLossInput,
    SP60_METHOD_DIGEST,
    SP60_METHOD_PACKAGE,
    TransmissionBoundaryInput,
    calculate_room_transmission,
)
from agent.sp60_normative_method import SP60_CANONICAL_REVISION, SP60_CANONICAL_REVISION_DIGEST
from agent.sp60_room_design_heating_load import (
    aggregate_sp60_room_design_heating_load,
    bind_design_heat_load_to_thermal_task,
    build_ufh_design_heat_load_input,
)
from agent.ufh_engineering_models import ThermalTask
from agent.ufh_project_engineering_profile_authoring import AuthoringProvenance
from agent.ventilation_infiltration_heat_loss import (
    A1ComponentInput,
    AerodynamicCoefficientModel,
    InfiltrationInput,
    MaterialEquipmentWarmingHeatLoadResult,
    RequiredVentilationAirflow,
    SourcedDecimal,
    calculate_room_infiltration_heat_loss,
    calculate_room_ventilation_heat_loss,
    SP60_AIR_METHOD_PACKAGE,
)

D = Decimal
HASH = "e" * 64


def prov(path, units):
    return AuthoringProvenance(source_type="test_only", source_reference=f"test://{path}",
                               source_sha256=HASH, source_field=path,
                               transformation="synthetic test fixture only", units=units)


def sourced(v, units, path):
    return SourcedDecimal(value=D(v), units=units, provenance=prov(path, units))


def component_results(*, q_tr="100", mts_status="NOT_APPLICABLE", inside="20", outside="0", airflow="10"):
    ti, to = D(inside), D(outside)
    qtr = D(q_tr)
    if ti == to:
        area, u = abs(qtr), D("1")
    else:
        area, u = D("1"), abs(qtr / (ti - to))
    tx = calculate_room_transmission(BuildingHeatLossInput(
        project_id="synthetic", building_id="b", level_id="l", room_id="r",
        project_revision_digest=HASH, normative_method_digest=SP60_METHOD_DIGEST,
        calculation_mode="DETAILED_TRANSMISSION",
        boundaries=[TransmissionBoundaryInput(
            boundary_id="south-wall", room_id="r", boundary_kind="OUTDOOR_AIR",
            geometry_reference="test://synthetic-room/south-wall", geometry_digest=HASH,
            area_m2=area, area_provenance=prov("geometry.wall.area", "m2"),
            u_value_w_m2k=u, u_value_role="HOMOGENEOUS_COMPONENT",
            u_value_provenance=prov("construction.wall.U", "W/(m2*K)"),
            inside_temperature_c=ti, inside_temperature_provenance=prov("room.Ti", "°C"),
            opposite_temperature_c=to, opposite_temperature_provenance=prov("climate.To", "°C"),
        )],
        boundary_inventory="COMPLETE", boundary_inventory_provenance=prov("boundary.inventory", "1"),
        thermal_bridge_inventory="COMPLETE", thermal_bridge_inventory_provenance=prov("bridge.inventory", "1"),
    ))
    airflow_source = RequiredVentilationAirflow(source_mode="PROJECT_DESIGN_AIRFLOW", direct_airflow_m3_h=D(airflow),
                                                direct_airflow_provenance=prov("hvac.Ln", "m3/h"))
    vent = calculate_room_ventilation_heat_loss("r", airflow_source, sourced(inside, "°C", "Ti"),
                                                sourced(outside, "°C", "To"))
    infiltration = InfiltrationInput(
        room_id="r", indoor_temperature=sourced(inside, "°C", "Ti"),
        outdoor_temperature=sourced(outside, "°C", "To"), pressure_mode="BALANCED_SUPPLY_EXHAUST",
        building_height_m=D("10"), building_height_provenance=prov("building.H", "m"),
        wind_speed_cold_design_m_s=D("2"), wind_speed_provenance=prov("climate.wind", "m/s"),
        aerodynamic_coefficients=AerodynamicCoefficientModel(
            building_form="RECTANGULAR", windward_coefficient=D("0.8"), leeward_coefficient=D("-0.6"),
            provenance=prov("SP60.rectangular", "dimensionless")),
        pressure_inventory="COMPLETE", pressure_inventory_provenance=prov("envelope.inventory", "1"),
        elements=[],
    )
    inf = calculate_room_infiltration_heat_loss(infiltration)
    mts = MaterialEquipmentWarmingHeatLoadResult(
        status=mts_status,
        applicability_provenance=prov("room.process_inventory", "1") if mts_status == "NOT_APPLICABLE" else None,
        calculation_or_applicability_scope="synthetic room design scope; no material/equipment/vehicle inflow" if mts_status == "NOT_APPLICABLE" else None,
        reason="SP60 A.6 applicability not classified" if mts_status == "INPUT_REQUIRED" else None,
    )
    return tx, vent, inf, mts


def test_canonical_sp60_revision_and_date_fields_are_shared():
    assert SP60_METHOD_PACKAGE["canonical_revision"] is SP60_CANONICAL_REVISION
    assert SP60_AIR_METHOD_PACKAGE["canonical_revision"] is SP60_CANONICAL_REVISION
    dates = SP60_CANONICAL_REVISION["amendment_6"]
    assert dates["approval_date"] == "2026-05-26"
    assert dates["rosstandart_registration_date"] == "2026-06-15"
    assert dates["official_publication_date"] == dates["effective_date"] == "2026-07-07"
    assert len(SP60_CANONICAL_REVISION_DIGEST) == 64


def test_current_formula_a1_is_four_additive_components_no_qbyt_term():
    record = SP60_AIR_METHOD_PACKAGE["formula_records"]["A.1"]
    assert record["semantics"] == "Q_ов^p = sum_n(Q_tr,n + Q_vent,n + Q_inf,n + Q_mts,n)"
    assert record["visual_sha256"] == "9e5c640d05e33251943b2e55ed8769a4f10346822e2d71370a20b91f3dc71151"
    assert SP60_AIR_METHOD_PACKAGE["a1_internal_gains_term"] == "NOT_PRESENT_IN_CURRENT_A1_FORMULA"
    assert SP60_AIR_METHOD_PACKAGE["formula_records"]["A.11"]["visual_sha256"] == \
        "d46beb0df4fea994b6e60fc0b0036d876e188ae3a210348af5b29c27cc77c765a"


def test_qmts_not_applicable_requires_evidence_and_complete_load_handoff_is_exact():
    tx, vent, inf, mts = component_results(q_tr="2", inside="90", outside="80", airflow="35")
    result = aggregate_sp60_room_design_heating_load(transmission_result=tx, ventilation_result=vent,
                                                      infiltration_result=inf, q_mts=mts)
    assert result.completeness_status == "COMPLETE_SP60_A1_COMPONENTS"
    assert result.room_design_heating_load_w == result.q_tr_w + vent.q_vent_w + inf.q_inf_w == D("100")
    assert result.room_design_heating_load_w == result.q_tr_w + result.q_vent_w + result.q_inf_w + result.q_mts_w
    handoff = build_ufh_design_heat_load_input(result)
    assert handoff.design_heat_load_w == result.room_design_heating_load_w
    context = ThermalTask(required_heat_w=1., heated_area_m2=10., k_h_w_m2k=5.5,
                          surface_limit_w_m2=100., theta_indoor_c=20., theta_below_c=18.,
                          r_o_m2k_w=0.1, r_u_m2k_w=0.1, mode="solve_return", theta_supply_c=35.)
    task_input = bind_design_heat_load_to_thermal_task(handoff, context)
    assert D(str(task_input.required_heat_w)) == handoff.design_heat_load_w


def test_incomplete_qmts_or_transmission_blocks_load_and_ufh_handoff():
    tx, vent, inf, _ = component_results(mts_status="INPUT_REQUIRED")
    result = aggregate_sp60_room_design_heating_load(transmission_result=tx, ventilation_result=vent,
                                                      infiltration_result=inf,
                                                      q_mts=MaterialEquipmentWarmingHeatLoadResult(
                                                          status="INPUT_REQUIRED", reason="Q_MTS_SCOPE_UNRESOLVED"))
    assert result.room_design_heating_load_w is None
    assert "Q_MTS_SCOPE_UNRESOLVED" in result.unresolved_components
    with pytest.raises(ValueError, match="DESIGN_HEAT_LOAD_INCOMPLETE"):
        build_ufh_design_heat_load_input(result)
    tx.completeness_status = "PLANAR_ONLY"
    _, _, _, mts = component_results()
    result = aggregate_sp60_room_design_heating_load(transmission_result=tx, ventilation_result=vent,
                                                      infiltration_result=inf, q_mts=mts)
    assert result.room_design_heating_load_w is None
    assert "Q_TR_COMPLETE_RESULT_REQUIRED" in result.unresolved_components


def test_qmts_na_without_scope_reason_cannot_close_a1():
    tx, vent, inf, _ = component_results(inside="20", outside="20")
    result = aggregate_sp60_room_design_heating_load(
        transmission_result=tx, ventilation_result=vent, infiltration_result=inf,
        q_mts=A1ComponentInput(status="NOT_APPLICABLE", applicability_provenance=prov("applicability", "1")),
    )
    assert result.room_design_heating_load_w is None
    assert "Q_MTS_NOT_APPLICABLE_SCOPE_REQUIRED" in result.unresolved_components


def test_decimal_not_exactly_representable_in_ufh_float_slot_fails_closed():
    tx, vent, inf, mts = component_results()
    result = aggregate_sp60_room_design_heating_load(transmission_result=tx, ventilation_result=vent,
                                                      infiltration_result=inf, q_mts=mts)
    heat = build_ufh_design_heat_load_input(result)
    context = ThermalTask(required_heat_w=1., heated_area_m2=10., k_h_w_m2k=5.5,
                          surface_limit_w_m2=100., theta_indoor_c=20., theta_below_c=18.,
                          r_o_m2k_w=0.1, r_u_m2k_w=0.1, mode="solve_return", theta_supply_c=35.)
    with pytest.raises(ValueError, match="UFH_HEAT_LOAD_FLOAT_PRECISION_LOSS"):
        bind_design_heat_load_to_thermal_task(heat, context)


def test_signed_transmission_is_not_absed_and_component_changes_change_digest():
    tx, vent, inf, mts = component_results(q_tr="-25", inside="20", outside="30")
    first = aggregate_sp60_room_design_heating_load(transmission_result=tx, ventilation_result=vent,
                                                     infiltration_result=inf, q_mts=mts)
    assert first.q_tr_w == D("-25")
    tx2, vent2, inf2, mts2 = component_results(q_tr="-24", inside="20", outside="30")
    second = aggregate_sp60_room_design_heating_load(transmission_result=tx2, ventilation_result=vent2,
                                                      infiltration_result=inf2, q_mts=mts2)
    assert first.digest != second.digest

"""Mapping tests use real legacy coverage objects, never engineered route lengths."""
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from agent import ufh_candidate_adapter as adapter
from agent import ufh_engineering_kernel as kernel
from agent.floor_heating_sizing import size_ufh_requirement_and_coverage
from agent.ufh_candidate_adapter import (
    CommonCircuitInputs, UFHEngineeringIntegrationInputs, assess_ufh_candidates,
    map_candidates, mm_to_m, mm2_to_m2, pipe_for_route,
)
from agent.ufh_engineering_models import EmbeddedLosses, FixedLoss, Fluid, Status
from tests.test_floor_heating_sizing import sizing_request
from tests.test_ufh_engineering_kernel import valve


def engineering_inputs(*, control=True, sigma=5., surface=100., area_basis="ACKNOWLEDGED_COVERAGE_ESTIMATE"):
    return UFHEngineeringIntegrationInputs(area_basis=area_basis,k_h_w_m2k=5.5,
        surface_limit_w_m2=surface,theta_indoor_c=21.,theta_below_c=10.,r_o_m2k_w=.13,
        r_u_m2k_w=1.,c_w_j_kgk=4190.,mode="solve_supply",sigma_k=sigma,
        common_circuit=CommonCircuitInputs(inner_diameter_m=.012,roughness_m=0.,
            fluid=Fluid(density_kg_m3=990.22,dynamic_viscosity_pa_s=.000594,specific_gravity=1.),
            embedded_losses=EmbeddedLosses(continuous_bends_pa=0.,pipe_fittings_pa=0.,other_fixed_pipe_path_pa=0.),
            fixed_manifold_losses=(),control=valve(.1) if control else None))


def existing_pair(width=4000,height=3000):
    return size_ufh_requirement_and_coverage(sizing_request(width,height))


def test_actual_geometry_length_and_estimated_area_mapping():
    s,p = existing_pair()
    m, = map_candidates(s,p,engineering_inputs())
    assert m.circuit_id == p.circuit_routes[0].id
    assert m.actual_length_m == p.circuit_routes[0].length_mm/1000 == 44.1
    assert m.served_area_m2 == p.zones[0].estimated_coverage_mm2/1000000 == 7.47
    assert m.area_is_estimate
    assert m.allocated_required_heat_w == s.required_heat_w == 421
    assert m.required_heat_flux_w_m2 == pytest.approx(421/7.47)


def test_unequal_coverage_allocation_is_not_equal_heat_split():
    s,p = existing_pair(7100,3200)
    m = map_candidates(s,p,engineering_inputs())
    areas = {z.circuit_id:z.estimated_coverage_mm2 for z in p.zones}
    assert m[0].allocated_required_heat_w != m[1].allocated_required_heat_w
    for c in m:
        assert c.allocated_required_heat_w == pytest.approx(s.required_heat_w*areas[c.circuit_id]/sum(areas.values()))
    assert sum(c.allocated_required_heat_w for c in m) == pytest.approx(s.required_heat_w)
    assert m[0].required_heat_flux_w_m2 == pytest.approx(m[1].required_heat_flux_w_m2)


def test_80000_mm_mapping_reaches_hydraulic_function_as_80m():
    _,p = existing_pair()
    # Isolated boundary-unit fixture: not presented as a route accepted by the router.
    # Whole-plan admission separately rejects inconsistent polyline length evidence.
    route = p.circuit_routes[0].model_copy(update={'length_mm':80000})
    inputs = engineering_inputs().common_circuit
    with patch.object(kernel,'pipe_hydraulics',wraps=kernel.pipe_hydraulics) as call:
        h = kernel.pipe_hydraulics(pipe_for_route(route,inputs),inputs.fluid,kernel.kg_h_to_kg_s(100.))
    assert call.call_args.args[0].length_m == 80.0
    assert h.pressure_pa == pytest.approx(80*96.3949358433,rel=1e-10)
    assert mm_to_m(80000) == 80.0
    assert mm2_to_m2(1000000) == 1.0


@pytest.mark.parametrize('bad',[True,-1,1.5,'80000'])
def test_geometry_units_are_strict_integers(bad):
    with pytest.raises(ValueError): mm_to_m(bad)
    with pytest.raises(ValueError): mm2_to_m2(bad)


@pytest.mark.parametrize('path', [('k_h_w_m2k',),('common_circuit','inner_diameter_m'),
    ('common_circuit','fluid','dynamic_viscosity_pa_s'),('c_w_j_kgk',),('area_basis',)])
def test_missing_mandatory_assumptions_are_rejected(path):
    payload = engineering_inputs().model_dump()
    target = payload
    for key in path[:-1]: target = target[key]
    del target[path[-1]]
    with pytest.raises(ValidationError): UFHEngineeringIntegrationInputs(**payload)


def test_no_silent_cp_override_or_control_double_count():
    with pytest.raises(ValidationError):
        UFHEngineeringIntegrationInputs(**{**engineering_inputs().model_dump(),'c_w_j_kgk':4180.})
    with pytest.raises(ValidationError):
        CommonCircuitInputs(**{**engineering_inputs().common_circuit.model_dump(),
            'fixed_manifold_losses':(FixedLoss(component_id='control',pressure_pa=10.),)})


def test_exact_area_required_fails_closed_before_kernel():
    s,p = existing_pair()
    with patch.object(kernel,'solve_thermal',side_effect=AssertionError('must not calculate')):
        r = assess_ufh_candidates(s,p,engineering_inputs(area_basis='EXACT_SERVED_AREA_REQUIRED'))
    assert r.engineering_status == 'CIRCUIT_HEAT_ALLOCATION_UNAVAILABLE'
    assert not r.circuits


@pytest.mark.parametrize('change',['missing_zone','zero_area','sum_mismatch'])
def test_unavailable_or_inconsistent_area_fails_closed(change):
    s,p = existing_pair()
    p = p.model_copy(deep=True)
    if change=='missing_zone': p.zones=[]
    elif change=='zero_area': p.zones[0].estimated_coverage_mm2=0
    else: p.estimated_coverage_mm2+=100
    r=assess_ufh_candidates(s,p,engineering_inputs())
    assert r.engineering_status=='CIRCUIT_HEAT_ALLOCATION_UNAVAILABLE'


@pytest.mark.parametrize('change',['project','digest','length','duplicate'])
def test_linked_candidate_evidence_cannot_be_substituted(change):
    s,p = existing_pair()
    p=p.model_copy(deep=True)
    if change=='project': p.project_id='other'
    elif change=='digest': p.plan_digest='f'*64
    elif change=='length': p.circuit_routes[0].length_mm=80000
    else: p.circuit_routes.append(p.circuit_routes[0])
    r=assess_ufh_candidates(s,p,engineering_inputs())
    assert r.engineering_status=='REJECTED_CANDIDATE'
    assert not r.circuits


def test_order_stability_and_no_input_mutation():
    s,p=existing_pair(7100,3200)
    before=(s.model_dump_json(),p.model_dump_json())
    first=assess_ufh_candidates(s,p,engineering_inputs())
    assert before==(s.model_dump_json(),p.model_dump_json())
    p2=p.model_copy(deep=True)
    p2.circuit_routes.reverse();p2.zones.reverse();p2.circuit_budget.reverse()
    assert assess_ufh_candidates(s,p2,engineering_inputs()).model_dump_json()==first.model_dump_json()
    assert assess_ufh_candidates(s,p,engineering_inputs(sigma=4.)).assessment_digest!=first.assessment_digest


def test_optional_control_does_not_invent_a_characteristic():
    s,p=existing_pair()
    with patch.object(kernel,'balance_circuits',side_effect=AssertionError('no control supplied')):
        r=assess_ufh_candidates(s,p,engineering_inputs(control=False))
    assert r.engineering_status==Status.ACCEPTED
    assert r.balance is None
    assert 'BALANCEABILITY_NOT_EVALUATED_NO_CHARACTERISTIC' in [d.code for d in r.diagnostics]
    assert r.circuits[0].pressure.en_pressure_ok


def test_legacy_policy_and_invalid_validation_flags_fail_closed():
    s,p=existing_pair()
    changed=s.model_copy(update={'maximum_circuit_length_mm':100000})
    r=assess_ufh_candidates(changed,p,engineering_inputs())
    assert r.diagnostics[0].code=='LEGACY_ROUTING_POLICY_MISMATCH'
    p=p.model_copy(deep=True)
    p.circuit_routes[0].validation.connected=False
    r=assess_ufh_candidates(s,p,engineering_inputs())
    assert not r.routing_accepted_legacy_policy and r.engineering_status=='REJECTED_CANDIDATE'

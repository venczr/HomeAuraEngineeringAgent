"""End-to-end: legacy heat loss/sizing -> actual routes -> existing engineering math."""
from unittest.mock import patch

import pytest

from agent import floor_heating_sizing as sizing_module
from agent import ufh_engineering_kernel as kernel
from agent.ufh_candidate_adapter import (
    assess_ufh_candidates, size_ufh_requirement_with_engineering,
    UFHEngineeringIntegrationInputs,
)
from agent.ufh_engineering_models import BalanceCircuit,Status
from tests.test_floor_heating_sizing import sizing_request
from tests.test_ufh_candidate_adapter import engineering_inputs,existing_pair


def test_one_circuit_full_pipeline_and_single_routing_pass():
    request=sizing_request(4000,3000)
    inputs=engineering_inputs()
    with patch.object(sizing_module,'solve_floor_heating_coverage',wraps=sizing_module.solve_floor_heating_coverage) as router, \
         patch.object(kernel,'solve_thermal',wraps=kernel.solve_thermal) as thermal, \
         patch.object(kernel,'pipe_hydraulics',wraps=kernel.pipe_hydraulics) as hydraulic:
        result=size_ufh_requirement_with_engineering(request,inputs)
    assert router.call_count==1 and thermal.call_count==1 and hydraulic.call_count==1
    r=result.engineering
    assert result.sizing.coverage_status=='accepted'
    assert r.routing_accepted_legacy_policy and r.sizing_coverage_accepted
    assert r.engineering_status==Status.ACCEPTED
    c,=r.circuits
    assert c.candidate.actual_length_m==result.coverage.circuit_routes[0].length_mm/1000
    assert c.thermal.theta_supply_c>c.thermal.theta_return_c>21
    assert c.mass_flow_kg_h>0 and c.hydraulics.reynolds>0 and c.hydraulics.velocity_m_s>0
    assert c.pressure.en_pressure_ok and c.natural_branch_pressure_pa>0


def test_multicircuit_allocation_flow_and_kernel_balance():
    inputs=engineering_inputs()
    with patch.object(kernel,'balance_circuits',wraps=kernel.balance_circuits) as balance:
        out=size_ufh_requirement_with_engineering(sizing_request(7100,3200),inputs)
    r=out.engineering
    assert balance.call_count==1
    assert r.engineering_status==Status.ACCEPTED and len(r.circuits)==2
    assert [c.candidate.circuit_id for c in r.circuits]==sorted(c.candidate.circuit_id for c in r.circuits)
    assert sum(c.candidate.allocated_required_heat_w for c in r.circuits)==pytest.approx(out.sizing.required_heat_w)
    assert r.circuits[0].mass_flow_kg_h!=r.circuits[1].mass_flow_kg_h
    assert r.total_design_mass_flow_kg_h==pytest.approx(sum(c.mass_flow_kg_h for c in r.circuits))
    assert r.highest_natural_branch_pressure_pa==max(c.natural_branch_pressure_pa for c in r.circuits)
    expected=kernel.balance_circuits(tuple(BalanceCircuit(circuit_id=c.candidate.circuit_id,
        mass_flow_kg_s=kernel.kg_h_to_kg_s(c.mass_flow_kg_h),fluid=inputs.common_circuit.fluid,
        natural_pressure_pa=c.natural_branch_pressure_pa,control=inputs.common_circuit.control) for c in r.circuits))
    assert r.balance==expected and r.balance.balanceable


def test_routing_accepted_hydraulic_failure_recommends_split_without_rerouting():
    request=sizing_request(4000,3000)
    baseline=size_ufh_requirement_with_engineering(request,engineering_inputs())
    with patch.object(sizing_module,'solve_floor_heating_coverage',wraps=sizing_module.solve_floor_heating_coverage) as router:
        failed=size_ufh_requirement_with_engineering(request,engineering_inputs(sigma=.5))
    assert router.call_count==1
    assert failed.coverage==baseline.coverage and failed.sizing==baseline.sizing
    r=failed.engineering
    assert r.routing_accepted_legacy_policy and r.sizing_coverage_accepted
    assert r.engineering_status==Status.REJECTED_CIRCUIT_PRESSURE
    assert r.recommendation=='SPLIT_REQUIRED'
    assert r.balance is None  # Default public call behavior remains unchanged.
    assert r.circuits[0].pressure.en_circuit_pressure_pa>35000
    assert 'EN_CIRCUIT_PRESSURE_LIMIT_EXCEEDED' in [d.code for d in r.diagnostics]


def test_thermal_failure_keeps_geometry_and_is_not_split_fixable():
    out=size_ufh_requirement_with_engineering(sizing_request(4000,3000),engineering_inputs(surface=40.))
    r=out.engineering
    assert r.routing_accepted_legacy_policy and out.sizing.coverage_status=='accepted'
    assert r.engineering_status==Status.REJECTED_SURFACE_LIMIT
    assert r.recommendation is None and r.circuits[0].recommendation is None
    assert r.circuits[0].hydraulic_status=='NOT_EVALUATED'
    assert r.total_design_mass_flow_kg_h is None and r.balance is None
    assert 'SURFACE_HEAT_FLUX_LIMIT_EXCEEDED' in [d.code for d in r.diagnostics]


def test_legacy_call_output_unchanged_and_engineering_opt_in():
    request=sizing_request(7100,3200)
    legacy=sizing_module.size_ufh_requirement(request)
    out=size_ufh_requirement_with_engineering(request,engineering_inputs())
    assert legacy.model_dump_json()==out.sizing.model_dump_json()
    assert legacy.minimum_circuit_length_mm==40000 and legacy.maximum_circuit_length_mm==80000
    assert 'engineering' not in legacy.model_dump()
    assert all(40000<=c.length_mm<=80000 for c in out.coverage.circuit_routes)


def test_temperature_assumptions_cannot_disagree_with_heat_loss_room():
    bad=UFHEngineeringIntegrationInputs(**{**engineering_inputs().model_dump(),'theta_indoor_c':20.})
    with pytest.raises(ValueError,match='must match'):
        size_ufh_requirement_with_engineering(sizing_request(4000,3000),bad)


def test_missing_real_candidate_does_not_generate_synthetic_geometry():
    s,p=existing_pair(12000,6000)
    with patch.object(kernel,'solve_thermal',side_effect=AssertionError('no candidate')):
        r=assess_ufh_candidates(s,p,engineering_inputs())
    assert r.engineering_status=='REJECTED_CANDIDATE'
    assert not r.routing_accepted_legacy_policy and not r.circuits


def test_complete_integration_is_deterministic():
    request=sizing_request(7100,3200)
    assert size_ufh_requirement_with_engineering(request,engineering_inputs()).model_dump_json()== \
           size_ufh_requirement_with_engineering(request,engineering_inputs()).model_dump_json()


def test_manufacturer_limit_and_no_claim_that_split_fixes_surface():
    from agent.ufh_candidate_adapter import CommonCircuitInputs
    base=engineering_inputs()
    limited=CommonCircuitInputs(**{**base.common_circuit.model_dump(),'manufacturer_max_circuit_pressure_pa':100.})
    inputs=UFHEngineeringIntegrationInputs(**{**base.model_dump(),'common_circuit':limited})
    r=size_ufh_requirement_with_engineering(sizing_request(4000,3000),inputs).engineering
    assert r.circuits[0].pressure.en_pressure_ok
    assert r.engineering_status==Status.REJECTED_MANUFACTURER_PRESSURE_LIMIT
    assert r.recommendation=='SPLIT_REQUIRED'


def test_kernel_balance_failure_reason_is_preserved():
    from agent.ufh_candidate_adapter import CommonCircuitInputs
    from tests.test_ufh_engineering_kernel import valve
    # A fixed Kv (zero adjustment interval) cannot balance unequal natural branches.
    base=engineering_inputs()
    control=valve(1.5)
    common=CommonCircuitInputs(**{**base.common_circuit.model_dump(),'control':control})
    inputs=UFHEngineeringIntegrationInputs(**{**base.model_dump(),'common_circuit':common})
    r=size_ufh_requirement_with_engineering(sizing_request(7100,3200),inputs).engineering
    assert all(c.engineering_status==Status.ACCEPTED for c in r.circuits)
    assert r.engineering_status==Status.REJECTED_BALANCEABILITY
    assert not r.balance.balanceable
    assert 'CONTROL_VALVE_INSUFFICIENT_THROTTLING_RANGE' in [d.code for d in r.diagnostics]
    assert r.recommendation is None  # No unsupported promise that splitting helps.


def test_sizing_failure_is_not_promoted_to_acceptance():
    request=sizing_request(7000,3200,wall_u=.65,air_changes=.8,output_100=110.,output_200=90.,
        thermal_bridge_percent=10.,design_margin_percent=15.,opening_u=1.8)
    out=size_ufh_requirement_with_engineering(request,engineering_inputs(surface=500.,sigma=20.))
    assert out.sizing.coverage_status=='insufficient'
    assert out.engineering.routing_accepted_legacy_policy
    assert out.engineering.engineering_status!='ACCEPTED'

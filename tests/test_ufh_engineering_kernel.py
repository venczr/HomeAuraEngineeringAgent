"""Offline regression contract for the isolated V1 engineering kernel."""
import math

import pytest
from pydantic import ValidationError

from agent.ufh_engineering_models import (
    BalanceCircuit, CharacteristicScope, CircuitTask, EmbeddedLosses,
    EngineeringRequest, FixedLoss, Fluid, PipeCandidate, Status, ThermalTask,
    ValveCharacteristic, ValveLimitType,
)
from agent.ufh_engineering_kernel import (
    balance_circuits, check_required_kv, churchill_friction, circuit_pressure,
    design_mass_flow, evaluate, kg_h_to_kg_s, kg_s_to_kg_h, kv_pressure_pa,
    lmtd, mass_flow_to_m3h, mbar_to_pa, pa_to_mbar, pipe_hydraulics,
    required_heat_flux, required_kv, solve_thermal,
)


def fluid():
    # SG=1 is intentional: the requested interval anchors use this approximation.
    return Fluid(density_kg_m3=990.22, dynamic_viscosity_pa_s=.000594, specific_gravity=1.0)


def pipe(length=100.):
    return PipeCandidate(length_m=length, inner_diameter_m=.012, roughness_m=0.)


def valve(minimum=.1, kind=ValveLimitType.MECHANICAL_LIMIT):
    return ValveCharacteristic(manufacturer="Synthetic", product_family="Regression only",
        document_reference="UFH_ENGINEERING_KERNEL_V1 synthetic fixture", characteristic_scope=CharacteristicScope.SINGLE_CONTROL_VALVE,
        included_components=("control",), kv_min_m3h=minimum, kv_max_m3h=1.5,
        limit_type=kind, source_confidence="synthetic_exact")


def thermal(**changes):
    data = dict(required_heat_w=500., heated_area_m2=10., k_h_w_m2k=5.5,
                surface_limit_w_m2=100., theta_indoor_c=20., theta_below_c=20.,
                r_o_m2k_w=.13, r_u_m2k_w=1., mode="solve_supply", sigma_k=5.)
    data.update(changes)
    return ThermalTask(**data)


def circuit(flow_kg_h=100., circuit_id="c1", **changes):
    # Hold q/sigma fixed; solve area from Formula 13 to obtain a requested test flow.
    area = kg_h_to_kg_s(flow_kg_h) * 5 * 4190 / (50 * 1.13)
    data = dict(circuit_id=circuit_id, thermal=thermal(required_heat_w=area*50, heated_area_m2=area),
                fluid=fluid(), pipe=pipe(), embedded_losses=EmbeddedLosses(continuous_bends_pa=0.,
                pipe_fittings_pa=0., other_fixed_pipe_path_pa=0.), fixed_manifold_losses=(), control=valve())
    data.update(changes)
    return CircuitTask(**data)


def branches(minimum=.1, kind=ValveLimitType.MECHANICAL_LIMIT):
    return tuple(BalanceCircuit(circuit_id=f"c{i}", mass_flow_kg_s=kg_h_to_kg_s(m),
        fluid=fluid(), natural_pressure_pa=mbar_to_pa(p), control=valve(minimum, kind))
        for i, (m, p) in enumerate(zip((60,80,100,120,150,180), (27.4,52.9,86.8,131.4,211.6,262.3)), 1))


@pytest.mark.parametrize("mass,re,dp", [(60,2977.084607,39.1850766),
    (100,4961.807678,96.3949358), (200,9923.615357,315.4395548)])
def test_churchill_anchors(mass, re, dp):
    r = pipe_hydraulics(pipe(), fluid(), kg_h_to_kg_s(mass))
    assert r.reynolds == pytest.approx(re, rel=2e-9)
    assert r.pressure_per_m_pa == pytest.approx(dp, rel=2e-9)
    assert r.pressure_pa == pytest.approx(dp*100, rel=2e-9)
    assert r.pressure_mbar == pytest.approx(dp, rel=2e-9)


def test_churchill_laminar_and_roughness_without_switch():
    assert churchill_friction(100., 0., .012) == pytest.approx(64/100, rel=1e-10)
    assert churchill_friction(100000., .00001, .012) > churchill_friction(100000., 0., .012)
    assert math.isfinite(churchill_friction(1e-12, 0., .012))


def test_thermal_supply_root_and_equation_closure():
    r = solve_thermal(thermal())
    assert r.status == Status.ACCEPTED
    assert r.theta_supply_c == pytest.approx(31.8189286347, abs=2e-8)
    assert r.theta_return_c == pytest.approx(26.8189286347, abs=2e-8)
    assert lmtd(r.theta_supply_c, r.theta_return_c, 20.) == pytest.approx(50/5.5, abs=2e-9)
    assert r.sigma_k == pytest.approx(5.)


def test_thermal_return_root_and_closure():
    r = solve_thermal(thermal(mode="solve_return", sigma_k=None, theta_supply_c=35.))
    assert r.status == Status.ACCEPTED
    assert 20 < r.theta_return_c < 35
    assert lmtd(35., r.theta_return_c, 20.) == pytest.approx(50/5.5, abs=2e-9)


@pytest.mark.parametrize("supply", [19.,20.,25.,30.])
def test_no_physical_root(supply):
    # Exactly representable 10 K boundary avoids subtractive float ambiguity.
    r = solve_thermal(thermal(required_heat_w=550., mode="solve_return", sigma_k=None, theta_supply_c=supply))
    assert r.status == Status.REJECTED_NO_PHYSICAL_THERMAL_ROOT
    assert r.diagnostics[0].code == "NO_PHYSICAL_THERMAL_ROOT"


def test_numerical_failure_is_not_physical_failure():
    r = solve_thermal(thermal(), max_iterations=1)
    assert r.status == Status.REJECTED_NUMERICAL_SOLVER_FAILURE
    assert r.diagnostics[0].code == "NUMERICAL_SOLVER_FAILURE"


def test_lmtd_equal_and_near_equal_limits():
    assert lmtd(30.,30.,20.) == 10.
    assert lmtd(30.+1e-9,30.,20.) == pytest.approx(10.+.5e-9, abs=1e-12)
    assert lmtd(40.,25.,20.) != pytest.approx(12.5)
    with pytest.raises(ValueError):
        lmtd(30.,20.,20.)


def test_formula13():
    r = design_mass_flow(10.,50.,5.,.13,1.,20.,20.)
    assert kg_s_to_kg_h(r) == pytest.approx(97.0883054893, abs=1e-8)
    assert design_mass_flow(10.,50.,5.,.13,1.,20.,10.) > r
    with pytest.raises(ValueError):
        design_mass_flow(10.,50.,5.,.13,1.,20.,100.)


@pytest.mark.parametrize("minimum,high,ok", [(.1,394.5462639705,True),(.4,50.3466414982,False)])
def test_balance_anchors(minimum, high, ok):
    r = balance_circuits(branches(minimum))
    assert pa_to_mbar(r.low_global_pa) == pytest.approx(276.9858505588, abs=1e-8)
    assert pa_to_mbar(r.high_global_pa) == pytest.approx(high, abs=1e-8)
    assert r.balanceable is ok
    assert r.limiting_low_circuit == "c6"
    assert r.limiting_high_circuit == "c1"
    if not ok:
        assert r.feasible_interval_pa is None
        assert r.status == Status.REJECTED_BALANCEABILITY
        assert r.diagnostics[0].code == "CONTROL_VALVE_INSUFFICIENT_THROTTLING_RANGE"


def test_published_domain_is_not_physical_impossibility():
    r = check_required_kv(.1194, valve(.3287, ValveLimitType.PUBLISHED_CURVE_LIMIT))
    assert r.status == Status.OUTSIDE_PUBLISHED_CHARACTERISTIC
    assert not r.within_characteristic
    assert r.physical_impossibility is None
    assert r.diagnostics[0].code == "REQUIRED_KV_BELOW_PUBLISHED_MINIMUM_CHARACTERISTIC"


@pytest.mark.parametrize("kind,expected", [
    (ValveLimitType.DIGITIZED_GRAPH_LIMIT, Status.OUTSIDE_PUBLISHED_CHARACTERISTIC),
    (ValveLimitType.MANUFACTURER_RECOMMENDED_LIMIT, Status.OUTSIDE_RECOMMENDED_SETTING_RANGE),
    (ValveLimitType.MANUFACTURER_ADJUSTMENT_LIMIT, Status.REJECTED_BALANCEABILITY)])
def test_soft_domains_do_not_assert_mechanical_impossibility(kind, expected):
    r = balance_circuits(branches(.4, kind))
    assert r.status == expected
    assert r.physical_impossibility is None
    assert check_required_kv(.05, valve(.1,kind)).physical_impossibility is None


def test_same_100m_length_different_engineering_outcome():
    low = evaluate(EngineeringRequest(circuits=(circuit(60.),)))
    high = evaluate(EngineeringRequest(circuits=(circuit(250.),)))
    assert low.status == Status.ACCEPTED
    assert low.circuits[0].pressure.en_pressure_ok
    assert high.status == Status.REJECTED_CIRCUIT_PRESSURE
    assert not high.circuits[0].pressure.en_pressure_ok
    assert "SPLIT_REQUIRED" in [d.code for d in high.diagnostics]


def test_surface_failure_cannot_be_overridden_by_hydraulics():
    r = evaluate(EngineeringRequest(circuits=(circuit(thermal=thermal(required_heat_w=1100.)),)))
    assert r.status == Status.REJECTED_SURFACE_LIMIT
    assert r.circuits[0].hydraulics is None
    assert r.balance is None


def test_manufacturer_limit_is_separate():
    r = evaluate(EngineeringRequest(circuits=(circuit(100.,manufacturer_max_circuit_pressure_pa=5000.),)))
    assert r.status == Status.REJECTED_MANUFACTURER_PRESSURE_LIMIT
    assert r.circuits[0].pressure.en_pressure_ok
    assert r.circuits[0].pressure.manufacturer_pressure_ok is False


def test_en_boundary_and_separate_manifold_losses():
    task = circuit(fixed_manifold_losses=(FixedLoss(component_id="header",pressure_pa=40000.),))
    hydro = pipe_hydraulics(task.pipe, task.fluid, kg_h_to_kg_s(100.))
    task = circuit(embedded_losses=EmbeddedLosses(continuous_bends_pa=35000.-hydro.pressure_pa,
        pipe_fittings_pa=0.,other_fixed_pipe_path_pa=0.), fixed_manifold_losses=task.fixed_manifold_losses)
    p = circuit_pressure(task,hydro)
    assert p.en_pressure_ok
    assert p.en_circuit_pressure_pa == 35000.
    assert p.fixed_manifold_pressure_pa == 40000.
    assert p.manufacturer_pressure_ok is None


def test_double_count_rejected():
    with pytest.raises(ValidationError):
        circuit(fixed_manifold_losses=(FixedLoss(component_id="control",pressure_pa=10.),))


def test_complete_branch_and_required_kv_closure():
    request = EngineeringRequest(circuits=(circuit(60.,"a"), circuit(100.,"b")))
    r = evaluate(request)
    assert r.status == Status.ACCEPTED
    for c in r.circuits:
        assert c.complete_branch_pressure_pa == pytest.approx(r.balance.low_global_pa)
        assert c.pressure.en_circuit_pressure_pa + c.manifold_control_pressure_pa == pytest.approx(c.complete_branch_pressure_pa)
        assert .1-1e-12 <= c.required_control_kv_m3h <= 1.5+1e-12
    assert evaluate(request) == r
    assert evaluate(EngineeringRequest(circuits=tuple(reversed(request.circuits)))) == r
    changed = evaluate(EngineeringRequest(circuits=(circuit(61.,"a"), circuit(100.,"b"))))
    assert changed.result_digest != r.result_digest


def test_balance_ties_and_single_interval():
    a,b = branches()[:2]
    b = BalanceCircuit(**{**a.model_dump(), 'circuit_id':'b'})
    r = balance_circuits((b,a))
    assert r.limiting_low_circuit == 'b'  # b precedes c1 lexicographically.
    assert r.limiting_high_circuit == 'b'
    assert balance_circuits((a,)).balanceable
    with pytest.raises(ValueError):
        balance_circuits((a,a))


def test_unit_and_kv_roundtrips():
    assert kg_s_to_kg_h(kg_h_to_kg_s(100.)) == 100.
    assert pa_to_mbar(mbar_to_pa(350.)) == 350.
    q = mass_flow_to_m3h(kg_h_to_kg_s(100.),990.22)
    for sg in (1.,.99022):
        dp = kv_pressure_pa(q,.7,sg)
        assert required_kv(q,dp,sg) == pytest.approx(.7,abs=1e-14)
    assert required_heat_flux(500.,10.) == 50.


@pytest.mark.parametrize("bad", [0.,-1.,float('nan'),float('inf'),True,"100"])
def test_strict_physical_inputs(bad):
    with pytest.raises((ValidationError,ValueError)):
        thermal(required_heat_w=bad)
    with pytest.raises(ValueError):
        required_heat_flux(bad,10.)


def test_required_explicit_properties_and_immutability():
    with pytest.raises(ValidationError):
        Fluid(density_kg_m3=990.22,dynamic_viscosity_pa_s=.000594)
    with pytest.raises(ValidationError):
        PipeCandidate(length_m=100.,inner_diameter_m=.012)
    with pytest.raises(ValidationError):
        thermal(unexpected=1)
    with pytest.raises(ValidationError):
        thermal().sigma_k = 10.
    with pytest.raises(ValidationError):
        thermal(mode="solve_return")
    with pytest.raises(ValidationError):
        EngineeringRequest(circuits=(circuit(),circuit()))


def test_json_roundtrip():
    r = EngineeringRequest(circuits=(circuit(),))
    assert EngineeringRequest.model_validate_json(r.model_dump_json()) == r


def test_unrepresentable_calculation_fails_closed():
    r = evaluate(EngineeringRequest(circuits=(circuit(pipe=PipeCandidate(length_m=1e308,
        inner_diameter_m=1e-308,roughness_m=0.)),)))
    assert r.status == Status.REJECTED_NUMERICAL_CALCULATION
    assert r.circuits[0].hydraulics is None


def test_surface_precedence_even_with_unrepresentable_lmtd_target():
    bad = circuit(circuit_id="z", thermal=thermal(required_heat_w=1100., k_h_w_m2k=1e-308))
    r = evaluate(EngineeringRequest(circuits=(circuit(250.,"a"),bad)))
    assert r.status == Status.REJECTED_SURFACE_LIMIT
    assert r.circuits[1].thermal.lmtd_required_k is None


@pytest.mark.parametrize("index", [0,1,2,4])
def test_formula13_nonpositive_physical_input(index):
    args = [10.,50.,5.,.13,1.,20.,20.]
    args[index] = 0.
    with pytest.raises(ValueError):
        design_mass_flow(*args)


def test_invalid_formula13_output_rejects_before_hydraulics():
    r = evaluate(EngineeringRequest(circuits=(circuit(thermal=thermal(theta_below_c=100.)),)))
    assert r.status == Status.REJECTED_THERMAL_OUTPUT
    assert r.circuits[0].hydraulics is None


def test_fixed_losses_are_added_once_and_en_over_boundary():
    task = circuit(fixed_manifold_losses=(FixedLoss(component_id="header",pressure_pa=1234.),))
    h = pipe_hydraulics(task.pipe,task.fluid,kg_h_to_kg_s(100.))
    e = EmbeddedLosses(continuous_bends_pa=100.,pipe_fittings_pa=200.,other_fixed_pipe_path_pa=35000.01-h.pressure_pa-300.)
    task = circuit(embedded_losses=e, fixed_manifold_losses=task.fixed_manifold_losses,
                   manufacturer_max_circuit_pressure_pa=20000.)
    p = circuit_pressure(task,h)
    assert p.en_circuit_pressure_pa == pytest.approx(35000.01)
    assert not p.en_pressure_ok and p.manufacturer_pressure_ok is False
    assert p.fixed_manifold_pressure_pa == 1234.


def test_characteristic_requires_valid_provenance_and_ordered_interval():
    payload = valve().model_dump()
    for change in ({'kv_min_m3h':2.}, {'document_reference':''}, {'kv_max_m3h':None},
                   {'included_components':('control','control')}):
        with pytest.raises(ValidationError):
            ValveCharacteristic(**{**payload,**change})


def test_published_upper_boundary_and_inclusive_endpoints():
    c = valve(.1,ValveLimitType.PUBLISHED_CURVE_LIMIT)
    assert check_required_kv(.1,c).within_characteristic
    assert check_required_kv(1.5,c).within_characteristic
    r = check_required_kv(1.6,c)
    assert r.status == Status.OUTSIDE_PUBLISHED_CHARACTERISTIC
    assert r.physical_impossibility is None
    assert r.diagnostics[0].code == "REQUIRED_KV_ABOVE_PUBLISHED_MAXIMUM_CHARACTERISTIC"


def test_complete_path_scope_does_not_add_another_return_valve():
    c = ValveCharacteristic(**{**valve().model_dump(),
        'characteristic_scope':CharacteristicScope.SUPPLY_PLUS_RETURN_BRANCH_PATH,
        'included_components':('supply','return')})
    with pytest.raises(ValidationError):
        circuit(control=c,fixed_manifold_losses=(FixedLoss(component_id='return',pressure_pa=50.),))
    a = evaluate(EngineeringRequest(circuits=(circuit(control=c),)))
    b = evaluate(EngineeringRequest(circuits=(circuit(),)))
    assert a.circuits[0].complete_branch_pressure_pa == b.circuits[0].complete_branch_pressure_pa

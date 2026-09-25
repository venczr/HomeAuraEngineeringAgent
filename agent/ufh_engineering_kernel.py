"""Deterministic, offline UFH math. No routing, CAD, service or API integration."""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable

from agent.ufh_engineering_models import (
    BalanceCircuit, BalanceInterval, BalanceResult, CircuitResult, CircuitTask,
    Diagnostic, DomainResult, EngineeringRequest, EngineeringResult, Fluid,
    HydraulicResult, PipeCandidate, PressureResult, Status, ThermalResult,
    ThermalTask, ValveCharacteristic, ValveLimitType,
)

SECONDS_PER_HOUR = 3600.0
PA_PER_BAR = 100000.0
PA_PER_MBAR = 100.0
WATER_CP_J_KG_K = 4190.0  # Formula 13, explicitly prescribed for V1.
EN_CIRCUIT_LIMIT_PA = 35000.0
ROOT_ABS_TOL_K = 1e-10
ROOT_REL_TOL = 1e-10
ROOT_MAX_ITERATIONS = 200


def _finite(value: float, *, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError("Expected a real number, not coercible text or boolean")
    if not math.isfinite(value) or (positive and value <= 0) or (nonnegative and value < 0):
        raise ValueError("Nonfinite or physically invalid numeric value")
    return float(value)


def kg_h_to_kg_s(value: float) -> float:
    return _finite(_finite(value, nonnegative=True) / SECONDS_PER_HOUR, nonnegative=True)


def kg_s_to_kg_h(value: float) -> float:
    return _finite(_finite(value, nonnegative=True) * SECONDS_PER_HOUR, nonnegative=True)


def pa_to_mbar(value: float) -> float:
    return _finite(_finite(value, nonnegative=True) / PA_PER_MBAR, nonnegative=True)


def mbar_to_pa(value: float) -> float:
    return _finite(_finite(value, nonnegative=True) * PA_PER_MBAR, nonnegative=True)


def mass_flow_to_m3h(mass_flow_kg_s: float, density_kg_m3: float) -> float:
    return _finite(kg_s_to_kg_h(_finite(mass_flow_kg_s, positive=True)) /
                   _finite(density_kg_m3, positive=True), positive=True)


def required_heat_flux(required_heat_w: float, heated_area_m2: float) -> float:
    return _finite(_finite(required_heat_w, positive=True) /
                   _finite(heated_area_m2, positive=True), positive=True)


def _log_mean(a: float, b: float) -> float:
    """Positive excess temperatures; equality uses the exact continuous limit."""
    if a == b:
        return a
    delta = a - b
    ratio = delta / b
    denominator = math.log1p(ratio) if math.isfinite(ratio) else math.log(a) - math.log(b)
    return _finite(delta / denominator, positive=True)


def lmtd(theta_supply_c: float, theta_return_c: float, theta_indoor_c: float) -> float:
    supply, ret, indoor = map(_finite, (theta_supply_c, theta_return_c, theta_indoor_c))
    if not supply >= ret > indoor:
        raise ValueError("LMTD requires supply >= return > indoor")
    return _log_mean(_finite(supply - indoor, positive=True),
                     _finite(ret - indoor, positive=True))


class NumericalSolverFailure(ArithmeticError):
    pass


def _bisect(fn: Callable[[float], float], lower: float, upper: float,
            target: float, max_iterations: int) -> tuple[float, int]:
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or max_iterations < 1:
        raise ValueError("max_iterations must be a positive integer")
    if not lower < upper or fn(lower) >= target or fn(upper) <= target:
        raise NumericalSolverFailure("Representable bracket does not enclose the physical root")
    tolerance = ROOT_ABS_TOL_K + ROOT_REL_TOL * target
    for iteration in range(1, max_iterations + 1):
        middle = lower + (upper - lower) / 2
        value = _finite(fn(middle))
        if abs(value - target) <= tolerance:
            return middle, iteration
        if middle == lower or middle == upper:
            break
        if value < target:
            lower = middle
        else:
            upper = middle
    raise NumericalSolverFailure("Bisection did not achieve equation closure")


def _diag(code: str, message: str, circuit_id: str | None = None) -> Diagnostic:
    return Diagnostic(code=code, message=message, circuit_id=circuit_id)


def solve_thermal(task: ThermalTask, *, max_iterations: int = ROOT_MAX_ITERATIONS) -> ThermalResult:
    q = required_heat_flux(task.required_heat_w, task.heated_area_m2)
    if q > task.surface_limit_w_m2:
        # Physical surface failure takes precedence even if q/K_H would overflow.
        return ThermalResult(status=Status.REJECTED_SURFACE_LIMIT, q_required_w_m2=q,
            iterations=0, diagnostics=(_diag("SURFACE_HEAT_FLUX_LIMIT_EXCEEDED", "Declared surface heat flux limit exceeded"),))
    target = _finite(q / task.k_h_w_m2k, positive=True)
    def failure(status: Status, code: str) -> ThermalResult:
        return ThermalResult(status=status, q_required_w_m2=q, lmtd_required_k=target,
                             iterations=0, diagnostics=(_diag(code, code),))
    if task.mode == "solve_return":
        excess = task.theta_supply_c - task.theta_indoor_c
        # Strict: target == supply excess would require sigma=0 and infinite flow.
        if excess <= 0 or target >= excess:
            return failure(Status.REJECTED_NO_PHYSICAL_THERMAL_ROOT, "NO_PHYSICAL_THERMAL_ROOT")
    try:
        if task.mode == "solve_return":
            # Boundary value 0 is an analytic limit, not a permissible operating return.
            fn = lambda z: 0.0 if z == 0 else _log_mean(excess, z)
            z, count = _bisect(fn, 0.0, excess, target, max_iterations)
            supply = task.theta_supply_c
            ret = task.theta_indoor_c + z
        else:
            sigma = task.sigma_k
            # At z=0 LMTD tends to zero; at z=target it strictly exceeds target.
            fn = lambda z: 0.0 if z == 0 else _log_mean(sigma + z, z)
            z, count = _bisect(fn, 0.0, target, target, max_iterations)
            ret = task.theta_indoor_c + z
            supply = ret + sigma
        solved_sigma = _finite(supply - ret, positive=True)
        if abs(lmtd(supply, ret, task.theta_indoor_c) - target) > ROOT_ABS_TOL_K + ROOT_REL_TOL * target:
            raise NumericalSolverFailure("Temperature reconstruction lost equation closure")
        return ThermalResult(status=Status.ACCEPTED, q_required_w_m2=q,
                             lmtd_required_k=target, theta_supply_c=supply,
                             theta_return_c=ret, sigma_k=solved_sigma, iterations=count)
    except (ArithmeticError, ValueError):
        return failure(Status.REJECTED_NUMERICAL_SOLVER_FAILURE, "NUMERICAL_SOLVER_FAILURE")


def design_mass_flow(area_m2: float, q_w_m2: float, sigma_k: float,
                     r_o_m2k_w: float, r_u_m2k_w: float,
                     theta_indoor_c: float, theta_below_c: float) -> float:
    """EN1264 Formula 13; returns kg/s, including the declared downward heat term."""
    area, q, sigma, ru = (_finite(v, positive=True) for v in
                          (area_m2, q_w_m2, sigma_k, r_u_m2k_w))
    ro = _finite(r_o_m2k_w, nonnegative=True)
    delta = _finite(theta_indoor_c) - _finite(theta_below_c)
    return _finite(area * q / (sigma * WATER_CP_J_KG_K) *
                   (1 + ro / ru + delta / (q * ru)), positive=True)


def _log_add(a: float, b: float) -> float:
    if a == -math.inf:
        return b
    if b == -math.inf:
        return a
    top = max(a, b)
    return top + math.log1p(math.exp(min(a, b) - top))


def churchill_friction(reynolds: float, roughness_m: float, diameter_m: float) -> float:
    """Exact all-regime Darcy Churchill, evaluated in log space to avoid power overflow."""
    re = _finite(reynolds, positive=True)
    eps = _finite(roughness_m, nonnegative=True)
    diameter = _finite(diameter_m, positive=True)
    lr = math.log(re)
    lx = _log_add(.9 * (math.log(7) - lr),
                  math.log(.27) + math.log(eps) - math.log(diameter) if eps else -math.inf)
    base = abs(-2.457 * lx)
    la = 16 * math.log(base) if base else -math.inf
    lb = 16 * (math.log(37530) - lr)
    value = math.exp(math.log(8) + _log_add(12 * (math.log(8) - lr),
                                           -1.5 * _log_add(la, lb)) / 12)
    return _finite(value, positive=True)


def pipe_hydraulics(pipe: PipeCandidate, fluid: Fluid, mass_flow_kg_s: float) -> HydraulicResult:
    mass = _finite(mass_flow_kg_s, positive=True)
    diameter = pipe.inner_diameter_m
    section = _finite(math.pi * diameter * diameter / 4, positive=True)
    velocity = _finite(mass / fluid.density_kg_m3 / section, positive=True)
    re = _finite(fluid.density_kg_m3 * velocity * diameter / fluid.dynamic_viscosity_pa_s, positive=True)
    friction = churchill_friction(re, pipe.roughness_m, diameter)
    per_m = _finite(friction / diameter * fluid.density_kg_m3 * velocity**2 / 2, positive=True)
    pressure = _finite(per_m * pipe.length_m, positive=True)
    return HydraulicResult(reynolds=re, darcy_friction_factor=friction, velocity_m_s=velocity,
                           pressure_pa=pressure, pressure_mbar=pa_to_mbar(pressure), pressure_per_m_pa=per_m)


def kv_pressure_pa(volume_m3h: float, kv_m3h: float, specific_gravity: float) -> float:
    q, kv, sg = (_finite(v, positive=True) for v in (volume_m3h, kv_m3h, specific_gravity))
    return _finite(PA_PER_BAR * sg * (q / kv)**2, positive=True)


def required_kv(volume_m3h: float, pressure_pa: float, specific_gravity: float) -> float:
    q, pressure, sg = (_finite(v, positive=True) for v in (volume_m3h, pressure_pa, specific_gravity))
    return _finite(q * math.sqrt(sg / (pressure / PA_PER_BAR)), positive=True)


def _outside_status(kinds: tuple[ValveLimitType, ...]) -> Status:
    if any(k in (ValveLimitType.PUBLISHED_CURVE_LIMIT, ValveLimitType.DIGITIZED_GRAPH_LIMIT) for k in kinds):
        return Status.OUTSIDE_PUBLISHED_CHARACTERISTIC
    if ValveLimitType.MANUFACTURER_RECOMMENDED_LIMIT in kinds:
        return Status.OUTSIDE_RECOMMENDED_SETTING_RANGE
    return Status.REJECTED_BALANCEABILITY


def check_required_kv(kv: float, characteristic: ValveCharacteristic) -> DomainResult:
    _finite(kv, positive=True)
    if characteristic.kv_min_m3h is None:
        raise ValueError("No published Kv interval; setting interpolation is outside V1")
    inside = characteristic.kv_min_m3h <= kv <= characteristic.kv_max_m3h
    if inside:
        return DomainResult(status=Status.ACCEPTED, within_characteristic=True,
                            physical_impossibility=False, diagnostics=())
    status = _outside_status((characteristic.limit_type,))
    below = kv < characteristic.kv_min_m3h
    if status == Status.OUTSIDE_PUBLISHED_CHARACTERISTIC:
        code = ("REQUIRED_KV_BELOW_PUBLISHED_MINIMUM_CHARACTERISTIC" if below else
                "REQUIRED_KV_ABOVE_PUBLISHED_MAXIMUM_CHARACTERISTIC")
    elif status == Status.OUTSIDE_RECOMMENDED_SETTING_RANGE:
        code = "REQUIRED_KV_OUTSIDE_RECOMMENDED_RANGE"
    else:
        code = "REQUIRED_KV_OUTSIDE_CONFIRMED_ADJUSTMENT_RANGE"
    physical = True if characteristic.limit_type == ValveLimitType.MECHANICAL_LIMIT else None
    diagnostics = (_diag(code, code),)
    if physical is None:
        diagnostics += (_diag("PHYSICAL_FEASIBILITY_UNKNOWN", "Characteristic boundary is not a confirmed physical limit"),)
    return DomainResult(status=status, within_characteristic=False,
                        physical_impossibility=physical, diagnostics=diagnostics)


def balance_circuits(circuits: tuple[BalanceCircuit, ...]) -> BalanceResult:
    if not circuits or len({c.circuit_id for c in circuits}) != len(circuits):
        raise ValueError("Nonempty circuits with unique IDs required")
    ordered = sorted(circuits, key=lambda c: c.circuit_id)
    intervals = []
    for c in ordered:
        if c.control.kv_min_m3h is None:
            raise ValueError("Balance calculation requires an explicit Kv interval")
        volume = mass_flow_to_m3h(c.mass_flow_kg_s, c.fluid.density_kg_m3)
        low = kv_pressure_pa(volume, c.control.kv_max_m3h, c.fluid.specific_gravity)
        high = kv_pressure_pa(volume, c.control.kv_min_m3h, c.fluid.specific_gravity)
        intervals.append(BalanceInterval(circuit_id=c.circuit_id, valve_min_pa=low, valve_max_pa=high,
                                         low_pa=c.natural_pressure_pa + low, high_pa=c.natural_pressure_pa + high))
    # Sorting + stable max/min makes ties select the lexicographically first ID.
    lo = max(intervals, key=lambda i: i.low_pa)
    hi = min(intervals, key=lambda i: i.high_pa)
    ok = lo.low_pa <= hi.high_pa
    types = tuple(c.control.limit_type for c in ordered if c.circuit_id in (lo.circuit_id, hi.circuit_id))
    status = Status.ACCEPTED if ok else _outside_status(types)
    diagnostics = ()
    physical = False if ok else (True if all(t == ValveLimitType.MECHANICAL_LIMIT for t in types) else None)
    if not ok:
        code = ("CONTROL_VALVE_INSUFFICIENT_THROTTLING_RANGE" if status == Status.REJECTED_BALANCEABILITY
                else status.value)
        diagnostics = (_diag(code, "No overlap of the declared LOW/HIGH intervals"),)
        if physical is None:
            diagnostics += (_diag("PHYSICAL_FEASIBILITY_UNKNOWN", "No mechanical impossibility inferred from source domain"),)
    return BalanceResult(status=status, balanceable=ok, physical_impossibility=physical,
                         intervals=tuple(intervals), low_global_pa=lo.low_pa, high_global_pa=hi.high_pa,
                         limiting_low_circuit=lo.circuit_id, limiting_high_circuit=hi.circuit_id,
                         feasible_interval_pa=(lo.low_pa, hi.high_pa) if ok else None, diagnostics=diagnostics)


def circuit_pressure(task: CircuitTask, hydraulics: HydraulicResult) -> PressureResult:
    losses = task.embedded_losses
    en = _finite(math.fsum((hydraulics.pressure_pa, losses.continuous_bends_pa,
                           losses.pipe_fittings_pa, losses.other_fixed_pipe_path_pa)), nonnegative=True)
    fixed = _finite(math.fsum(v.pressure_pa for v in task.fixed_manifold_losses), nonnegative=True)
    return PressureResult(en_circuit_pressure_pa=en, fixed_manifold_pressure_pa=fixed,
                          en_pressure_ok=en <= EN_CIRCUIT_LIMIT_PA,
                          manufacturer_pressure_ok=(None if task.manufacturer_max_circuit_pressure_pa is None
                                                    else en <= task.manufacturer_max_circuit_pressure_pa))


def evaluate(request: EngineeringRequest) -> EngineeringResult:
    results = []
    balance_inputs = []
    for task in sorted(request.circuits, key=lambda c: c.circuit_id):
        thermal = None
        try:
            thermal = solve_thermal(task.thermal)
            if thermal.status != Status.ACCEPTED:
                results.append(CircuitResult(circuit_id=task.circuit_id, status=thermal.status,
                                             thermal=thermal, diagnostics=thermal.diagnostics))
                continue  # Physical thermal failure must never enter hydraulic optimization.
            t = task.thermal
            try:
                mass = design_mass_flow(t.heated_area_m2, thermal.q_required_w_m2, thermal.sigma_k,
                                        t.r_o_m2k_w, t.r_u_m2k_w, t.theta_indoor_c, t.theta_below_c)
            except ValueError:
                results.append(CircuitResult(circuit_id=task.circuit_id, status=Status.REJECTED_THERMAL_OUTPUT,
                    thermal=thermal, diagnostics=(_diag("NONPOSITIVE_OR_NONFINITE_DESIGN_FLOW", "Formula 13 did not produce valid heating flow", task.circuit_id),)))
                continue
            hydraulic = pipe_hydraulics(task.pipe, task.fluid, mass)
            pressure = circuit_pressure(task, hydraulic)
            diagnostics = []
            status = Status.ACCEPTED
            if not pressure.en_pressure_ok:
                status = Status.REJECTED_CIRCUIT_PRESSURE
                diagnostics.append(_diag("EN_CIRCUIT_PRESSURE_LIMIT_EXCEEDED", "Embedded pipe circuit exceeds 35000 Pa", task.circuit_id))
                diagnostics.append(_diag("SPLIT_REQUIRED", "Candidate needs redesign; splitting is not calculated or guaranteed to resolve it", task.circuit_id))
            if pressure.manufacturer_pressure_ok is False:
                if status == Status.ACCEPTED:
                    status = Status.REJECTED_MANUFACTURER_PRESSURE_LIMIT
                diagnostics.append(_diag("MANUFACTURER_PRESSURE_LIMIT_EXCEEDED", "Separate manufacturer circuit limit exceeded", task.circuit_id))
            results.append(CircuitResult(circuit_id=task.circuit_id, status=status, thermal=thermal,
                mass_flow_kg_s=mass, mass_flow_kg_h=kg_s_to_kg_h(mass), hydraulics=hydraulic,
                pressure=pressure, diagnostics=tuple(diagnostics)))
            balance_inputs.append(BalanceCircuit(circuit_id=task.circuit_id, mass_flow_kg_s=mass,
                fluid=task.fluid, natural_pressure_pa=pressure.en_circuit_pressure_pa + pressure.fixed_manifold_pressure_pa,
                control=task.control))
        except (ArithmeticError, ValueError) as error:
            results.append(CircuitResult(circuit_id=task.circuit_id, status=Status.REJECTED_NUMERICAL_CALCULATION,
                thermal=thermal, diagnostics=(_diag("NONFINITE_OR_UNREPRESENTABLE_CALCULATION", type(error).__name__, task.circuit_id),)))
    balance = None
    diagnostics = [v for r in results for v in r.diagnostics]
    if all(r.status == Status.ACCEPTED for r in results):
        try:
            balance = balance_circuits(tuple(balance_inputs))
            diagnostics.extend(balance.diagnostics)
            if balance.balanceable:
                tasks = {c.circuit_id: c for c in request.circuits}
                completed = []
                for r in results:
                    task = tasks[r.circuit_id]
                    control_pa = balance.low_global_pa - r.pressure.en_circuit_pressure_pa - r.pressure.fixed_manifold_pressure_pa
                    kv = required_kv(mass_flow_to_m3h(r.mass_flow_kg_s, task.fluid.density_kg_m3), control_pa, task.fluid.specific_gravity)
                    completed.append(r.model_copy(update=dict(
                        manifold_control_pressure_pa=control_pa + r.pressure.fixed_manifold_pressure_pa,
                        complete_branch_pressure_pa=balance.low_global_pa, required_control_kv_m3h=kv)))
                results = completed
        except (ArithmeticError, ValueError):
            diagnostics.append(_diag("BALANCE_NUMERICAL_FAILURE", "Balance or operating-point calculation is unrepresentable"))
    # Thermal rejection has priority across circuits; ID order only resolves ties.
    priority = (Status.REJECTED_SURFACE_LIMIT, Status.REJECTED_THERMAL_OUTPUT,
                Status.REJECTED_NO_PHYSICAL_THERMAL_ROOT, Status.REJECTED_NUMERICAL_SOLVER_FAILURE,
                Status.REJECTED_NUMERICAL_CALCULATION, Status.REJECTED_CIRCUIT_PRESSURE,
                Status.REJECTED_MANUFACTURER_PRESSURE_LIMIT)
    failures = [status for status in priority if any(r.status == status for r in results)]
    status = failures[0] if failures else (balance.status if balance else Status.REJECTED_NUMERICAL_CALCULATION)
    if any(v.code == "BALANCE_NUMERICAL_FAILURE" for v in diagnostics):
        status = Status.REJECTED_NUMERICAL_CALCULATION
    content = dict(schema_version="1.0", status=status, circuits=tuple(results), balance=balance, diagnostics=tuple(diagnostics))
    provisional = EngineeringResult(**content, result_digest="0" * 64)
    payload = {"request": request.model_dump(mode="json"),
               "result": provisional.model_dump(mode="json", exclude={"result_digest"})}
    # Input order is not semantically relevant; all tie-breaking is ID-based.
    payload['request']['circuits'].sort(key=lambda c: c['circuit_id'])
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, allow_nan=False,
                                       sort_keys=True, separators=(",", ":")).encode("utf8")).hexdigest()
    return provisional.model_copy(update={"result_digest": digest})

"""Opt-in mapping of real legacy coverage candidates to the SI engineering kernel."""
from __future__ import annotations

import hashlib
import json
import math
from typing import Literal

from pydantic import Field, model_validator

from agent import ufh_engineering_kernel as kernel
from agent.floor_heating_coverage import FloorHeatingCoveragePlan
from agent.floor_heating_models import CircuitRoute
from agent.floor_heating_sizing import (
    UFHRequirement, UFHSizingRequest, size_ufh_requirement_and_coverage,
)
from agent.ufh_engineering_models import (
    BalanceCircuit, BalanceResult, Diagnostic, EmbeddedLosses, EngineeringModel,
    Finite, FixedLoss, Fluid, HydraulicResult, Name, Nonnegative, PipeCandidate,
    Positive, PressureResult, Status, ThermalResult, ThermalTask, ValveCharacteristic,
)

MM_PER_M = 1000
MM2_PER_M2 = 1000000
LEGACY_POLICY = "LEGACY_MVP_ROUTING_POLICY"


def mm_to_m(value: int) -> float:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Geometry length must be a nonnegative integer in mm")
    return value / MM_PER_M


def mm2_to_m2(value: int) -> float:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Geometry area must be a nonnegative integer in mm2")
    return value / MM2_PER_M2


class CommonCircuitInputs(EngineeringModel):
    """Explicitly apply these product/loss assumptions to EACH circuit in this room."""
    inner_diameter_m: Positive
    roughness_m: Nonnegative
    fluid: Fluid
    embedded_losses: EmbeddedLosses
    fixed_manifold_losses: tuple[FixedLoss, ...]
    manufacturer_max_circuit_pressure_pa: Positive | None = None
    control: ValveCharacteristic | None = None

    @model_validator(mode="after")
    def pressure_scope(self):
        ids = [v.component_id for v in self.fixed_manifold_losses]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate fixed pressure component")
        if self.control is not None:
            if self.control.kv_min_m3h is None:
                raise ValueError("Kernel V1 requires an explicit Kv characteristic interval")
            if set(ids) & set(self.control.included_components):
                raise ValueError("Fixed/control overlap would double count pressure loss")
        return self


class UFHEngineeringIntegrationInputs(EngineeringModel):
    area_basis: Literal["ACKNOWLEDGED_COVERAGE_ESTIMATE", "EXACT_SERVED_AREA_REQUIRED"]
    k_h_w_m2k: Positive
    surface_limit_w_m2: Positive
    theta_indoor_c: Finite
    theta_below_c: Finite
    r_o_m2k_w: Nonnegative
    r_u_m2k_w: Positive
    c_w_j_kgk: Positive
    mode: Literal["solve_supply", "solve_return"]
    sigma_k: Positive | None = None
    theta_supply_c: Finite | None = None
    common_circuit: CommonCircuitInputs

    @model_validator(mode="after")
    def explicit_thermal_inputs(self):
        if self.c_w_j_kgk != kernel.WATER_CP_J_KG_K:
            raise ValueError("Kernel V1 supports only Formula 13 c_W=4190; no alternative is silently ignored")
        if self.mode == "solve_return":
            if self.theta_supply_c is None or self.sigma_k is not None:
                raise ValueError("solve_return requires supply only")
        elif self.sigma_k is None or self.theta_supply_c is not None:
            raise ValueError("solve_supply requires sigma only")
        return self


class MappedCandidate(EngineeringModel):
    circuit_id: Name
    actual_length_m: Positive
    served_area_m2: Positive
    area_is_estimate: Literal[True] = True
    allocated_required_heat_w: Positive
    required_heat_flux_w_m2: Positive
    pipe: PipeCandidate
    thermal: ThermalTask


class CircuitAssessment(EngineeringModel):
    candidate: MappedCandidate
    engineering_status: Status
    recommendation: Literal["SPLIT_REQUIRED"] | None = None
    thermal_status: Status
    hydraulic_status: Status | Literal["NOT_EVALUATED"]
    thermal: ThermalResult | None = None
    mass_flow_kg_h: Positive | None = None
    hydraulics: HydraulicResult | None = None
    pressure: PressureResult | None = None
    natural_branch_pressure_pa: Nonnegative | None = None
    diagnostics: tuple[Diagnostic, ...] = ()


class IntegrationAssessment(EngineeringModel):
    project_id: Name
    room_id: Name
    sizing_requirement_id: Name
    coverage_plan_id: Name
    sizing_digest: str
    coverage_digest: str
    routing_policy: Literal["LEGACY_MVP_ROUTING_POLICY"] = LEGACY_POLICY
    routing_accepted_legacy_policy: bool
    sizing_coverage_accepted: bool
    engineering_status: Status | Literal["REJECTED_CANDIDATE", "CIRCUIT_HEAT_ALLOCATION_UNAVAILABLE", "REJECTED_SIZING_COVERAGE"]
    recommendation: Literal["SPLIT_REQUIRED"] | None = None
    circuits: tuple[CircuitAssessment, ...]
    total_design_mass_flow_kg_h: Nonnegative | None
    highest_natural_branch_pressure_pa: Nonnegative | None
    balance: BalanceResult | None
    diagnostics: tuple[Diagnostic, ...]
    assessment_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class SizingEngineeringResult(EngineeringModel):
    sizing: UFHRequirement
    coverage: FloorHeatingCoveragePlan
    engineering: IntegrationAssessment


class CandidateMappingError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def pipe_for_route(route: CircuitRoute, inputs: CommonCircuitInputs) -> PipeCandidate:
    """No engineered/inferred length: use the supplied routing object's actual length."""
    return PipeCandidate(length_m=mm_to_m(route.length_mm), inner_diameter_m=inputs.inner_diameter_m,
                         roughness_m=inputs.roughness_m)


def _routing_ok(plan: FloorHeatingCoveragePlan) -> bool:
    return bool(plan.circuit_routes) and plan.status != "impossible" and all(
        r.validation.valid and r.validation.length_valid and r.validation.connected
        and r.validation.step_valid and r.validation.inside_boundary
        and r.validation.exclusion_clear and r.validation.endpoints_valid
        and not r.validation.self_intersection and not r.validation.branches
        and 40000 <= r.length_mm <= 80000
        for r in plan.circuit_routes)


def map_candidates(sizing: UFHRequirement, plan: FloorHeatingCoveragePlan,
                   inputs: UFHEngineeringIntegrationInputs) -> tuple[MappedCandidate, ...]:
    """Allocate the entire room load in proportion to existing coverage estimates."""
    if (sizing.minimum_circuit_length_mm,sizing.maximum_circuit_length_mm) != (40000,80000):
        raise CandidateMappingError("LEGACY_ROUTING_POLICY_MISMATCH")
    if (sizing.project_id, sizing.room_id, sizing.coverage_integration.coverage_plan_digest,
        sizing.coverage_integration.coverage_plan_id) != (plan.project_id, plan.room_id, plan.plan_digest, plan.plan_id):
        raise CandidateMappingError("SIZING_COVERAGE_IDENTITY_MISMATCH")
    if not _routing_ok(plan):
        raise CandidateMappingError("ROUTING_CANDIDATE_NOT_ACCEPTED")
    routes = sorted(plan.circuit_routes, key=lambda r: r.id)
    ids = [r.id for r in routes]
    if (len(ids) != len(set(ids)) or sorted(sizing.coverage_integration.validated_route_ids) != ids
        or len(ids) != plan.collector_port_count or len(ids) != plan.required_circuit_count
        or len(ids) != sizing.coverage_integration.valid_route_count):
        raise CandidateMappingError("CIRCUIT_IDENTITY_OR_COUNT_MISMATCH")
    zones = {z.circuit_id: z for z in plan.zones}
    if len(zones) != len(plan.zones) or set(zones) != set(ids):
        raise CandidateMappingError("CIRCUIT_HEAT_ALLOCATION_UNAVAILABLE")
    for route in routes:
        z = zones[route.id]
        # Verify declared length against routing evidence and its actual polyline.
        actual = sum(abs(a.x_mm-b.x_mm)+abs(a.y_mm-b.y_mm) for a,b in zip(route.polyline,route.polyline[1:]))
        if (actual != route.length_mm or route.validation.polyline_length_mm != actual
            or z.generated_route_length_mm != actual or not z.route_valid):
            raise CandidateMappingError("ROUTE_LENGTH_EVIDENCE_MISMATCH")
    if inputs.area_basis != "ACKNOWLEDGED_COVERAGE_ESTIMATE":
        raise CandidateMappingError("CIRCUIT_HEAT_ALLOCATION_UNAVAILABLE")
    areas = [zones[r.id].estimated_coverage_mm2 for r in routes]
    total_area = sum(areas)
    if (any(a <= 0 for a in areas) or total_area != plan.estimated_coverage_mm2
        or total_area > plan.heated_area_mm2 or sizing.required_heat_w <= 0):
        raise CandidateMappingError("CIRCUIT_HEAT_ALLOCATION_UNAVAILABLE")
    mapped = []
    for route, area_mm2 in zip(routes, areas):
        area = mm2_to_m2(area_mm2)
        heat = sizing.required_heat_w * (area_mm2 / total_area)
        thermal = ThermalTask(required_heat_w=heat, heated_area_m2=area,
            **{key: getattr(inputs,key) for key in ('k_h_w_m2k','surface_limit_w_m2','theta_indoor_c',
                'theta_below_c','r_o_m2k_w','r_u_m2k_w','mode','sigma_k','theta_supply_c')})
        pipe = pipe_for_route(route, inputs.common_circuit)
        mapped.append(MappedCandidate(circuit_id=route.id, actual_length_m=pipe.length_m,
            served_area_m2=area, allocated_required_heat_w=heat,
            required_heat_flux_w_m2=kernel.required_heat_flux(heat,area), pipe=pipe, thermal=thermal))
    return tuple(mapped)


def _diag(code: str, message: str, circuit_id: str | None = None) -> Diagnostic:
    return Diagnostic(code=code, message=message, circuit_id=circuit_id)


def _individual(candidate: MappedCandidate, common: CommonCircuitInputs) -> CircuitAssessment:
    thermal = None
    try:
        thermal = kernel.solve_thermal(candidate.thermal)
        if thermal.status != Status.ACCEPTED:
            return CircuitAssessment(candidate=candidate, engineering_status=thermal.status,
                thermal_status=thermal.status, hydraulic_status="NOT_EVALUATED", thermal=thermal,
                diagnostics=thermal.diagnostics)
        t = candidate.thermal
        try:
            mass = kernel.design_mass_flow(t.heated_area_m2,thermal.q_required_w_m2,thermal.sigma_k,
                t.r_o_m2k_w,t.r_u_m2k_w,t.theta_indoor_c,t.theta_below_c)
        except ValueError:
            return CircuitAssessment(candidate=candidate,engineering_status=Status.REJECTED_THERMAL_OUTPUT,
                thermal_status=Status.REJECTED_THERMAL_OUTPUT,hydraulic_status="NOT_EVALUATED",thermal=thermal,
                diagnostics=(_diag("NONPOSITIVE_OR_NONFINITE_DESIGN_FLOW","Formula 13 did not produce valid heating flow",candidate.circuit_id),))
        hydraulic = kernel.pipe_hydraulics(candidate.pipe,common.fluid,mass)
        # The existing pure pressure function reads only these three validated
        # pressure fields; CommonCircuitInputs supplies that structural interface.
        # No fictitious control characteristic is created when control is absent.
        pressure = kernel.circuit_pressure(common,hydraulic)
        status = Status.ACCEPTED
        diagnostics = []
        recommendation = None
        if not pressure.en_pressure_ok:
            status = Status.REJECTED_CIRCUIT_PRESSURE
            recommendation = "SPLIT_REQUIRED"
            diagnostics.append(_diag("EN_CIRCUIT_PRESSURE_LIMIT_EXCEEDED","Embedded pipe circuit exceeds 35000 Pa",candidate.circuit_id))
        if pressure.manufacturer_pressure_ok is False:
            if status == Status.ACCEPTED:
                status = Status.REJECTED_MANUFACTURER_PRESSURE_LIMIT
            recommendation = "SPLIT_REQUIRED"
            diagnostics.append(_diag("MANUFACTURER_PRESSURE_LIMIT_EXCEEDED","Separate manufacturer circuit limit exceeded",candidate.circuit_id))
        if recommendation:
            diagnostics.append(_diag("SPLIT_REQUIRED","Review splitting or redesign; no geometry change or successful remedy is implied",candidate.circuit_id))
        return CircuitAssessment(candidate=candidate,engineering_status=status,recommendation=recommendation,
            thermal_status=thermal.status,hydraulic_status=status,thermal=thermal,
            mass_flow_kg_h=kernel.kg_s_to_kg_h(mass),hydraulics=hydraulic,pressure=pressure,
            natural_branch_pressure_pa=pressure.en_circuit_pressure_pa+pressure.fixed_manifold_pressure_pa,
            diagnostics=tuple(diagnostics))
    except (ArithmeticError,ValueError):
        return CircuitAssessment(candidate=candidate,engineering_status=Status.REJECTED_NUMERICAL_CALCULATION,
            thermal_status=thermal.status if thermal else Status.REJECTED_NUMERICAL_CALCULATION,
            hydraulic_status=Status.REJECTED_NUMERICAL_CALCULATION if thermal and thermal.status == Status.ACCEPTED else "NOT_EVALUATED",
            thermal=thermal,diagnostics=(_diag("NONFINITE_OR_UNREPRESENTABLE_CALCULATION","Kernel calculation failed closed",candidate.circuit_id),))


def assess_ufh_candidates(sizing: UFHRequirement, plan: FloorHeatingCoveragePlan,
                          inputs: UFHEngineeringIntegrationInputs, *,
                          assess_balance_after_pressure_failure: bool = False) -> IntegrationAssessment:
    """Read-only engineering assessment of an existing, linked sizing/coverage pair."""
    diagnostics = []
    results = ()
    balance = None
    recommendation = None
    try:
        candidates = map_candidates(sizing,plan,inputs)
        diagnostics.append(_diag("COVERAGE_ESTIMATE_USED_FOR_HEAT_ALLOCATION",
            "Served areas are existing coverage estimates, not exact union areas"))
        results = tuple(_individual(c,inputs.common_circuit) for c in candidates)
        diagnostics.extend(d for r in results for d in r.diagnostics)
        priority = (Status.REJECTED_SURFACE_LIMIT,Status.REJECTED_THERMAL_OUTPUT,
            Status.REJECTED_NO_PHYSICAL_THERMAL_ROOT,Status.REJECTED_NUMERICAL_SOLVER_FAILURE,
            Status.REJECTED_NUMERICAL_CALCULATION,Status.REJECTED_CIRCUIT_PRESSURE,
            Status.REJECTED_MANUFACTURER_PRESSURE_LIMIT)
        status = next((s for s in priority if any(r.engineering_status==s for r in results)),Status.ACCEPTED)
        if status in (Status.REJECTED_CIRCUIT_PRESSURE,Status.REJECTED_MANUFACTURER_PRESSURE_LIMIT):
            recommendation = "SPLIT_REQUIRED"
        common = inputs.common_circuit
        complete_balance_inputs = bool(results) and all(
            r.mass_flow_kg_h is not None and r.natural_branch_pressure_pa is not None
            for r in results
        )
        pressure_failed = status in (
            Status.REJECTED_CIRCUIT_PRESSURE,
            Status.REJECTED_MANUFACTURER_PRESSURE_LIMIT,
        )
        if (
            common.control is not None
            and complete_balance_inputs
            and (status == Status.ACCEPTED or (
                assess_balance_after_pressure_failure and pressure_failed
            ))
        ):
            balance = kernel.balance_circuits(tuple(BalanceCircuit(circuit_id=r.candidate.circuit_id,
                mass_flow_kg_s=kernel.kg_h_to_kg_s(r.mass_flow_kg_h),fluid=common.fluid,
                natural_pressure_pa=r.natural_branch_pressure_pa,control=common.control) for r in results))
            diagnostics.extend(balance.diagnostics)
            if status == Status.ACCEPTED:
                status = balance.status
            # Even when pressure fails, record balanceability if all required
            # hydraulic values exist. Preserve the pressure root and its
            # SPLIT_REQUIRED recommendation as the primary engineering result.
        elif status == Status.ACCEPTED and common.control is None:
            diagnostics.append(_diag("BALANCEABILITY_NOT_EVALUATED_NO_CHARACTERISTIC",
                "Individual thermal/hydraulic acceptance only; control characteristic not supplied"))
        if not sizing.coverage_integration.accepted:
            diagnostics.append(_diag("EXISTING_SIZING_COVERAGE_NOT_ACCEPTED","Engineering cannot override the existing sizing coverage failure"))
            if status == Status.ACCEPTED:
                status = "REJECTED_SIZING_COVERAGE"
    except CandidateMappingError as error:
        status = "CIRCUIT_HEAT_ALLOCATION_UNAVAILABLE" if error.code == "CIRCUIT_HEAT_ALLOCATION_UNAVAILABLE" else "REJECTED_CANDIDATE"
        diagnostics.append(_diag(error.code,error.code))
    except (ArithmeticError,ValueError):
        status = Status.REJECTED_NUMERICAL_CALCULATION
        diagnostics.append(_diag("INTEGRATION_CALCULATION_FAILED","Mapping or manifold calculation failed closed"))
    complete_flow = bool(results) and all(r.mass_flow_kg_h is not None for r in results)
    complete_pressure = bool(results) and all(r.natural_branch_pressure_pa is not None for r in results)
    try:
        total = math.fsum(r.mass_flow_kg_h for r in results) if complete_flow else None
        if total is not None and not math.isfinite(total):
            raise OverflowError
    except OverflowError:
        total = None
        status = Status.REJECTED_NUMERICAL_CALCULATION
        recommendation = None
        diagnostics.append(_diag("TOTAL_FLOW_UNREPRESENTABLE","Complete design flow cannot be represented as a finite number"))
    maximum = max(r.natural_branch_pressure_pa for r in results) if complete_pressure else None
    output = IntegrationAssessment(project_id=sizing.project_id,room_id=sizing.room_id,
        sizing_requirement_id=sizing.requirement_id,coverage_plan_id=plan.plan_id,
        sizing_digest=sizing.sizing_digest,coverage_digest=plan.plan_digest,
        routing_accepted_legacy_policy=_routing_ok(plan),sizing_coverage_accepted=sizing.coverage_integration.accepted,
        engineering_status=status,recommendation=recommendation,circuits=results,
        total_design_mass_flow_kg_h=total,highest_natural_branch_pressure_pa=maximum,
        balance=balance,diagnostics=tuple(diagnostics),assessment_digest="0"*64)
    plan_payload = plan.model_dump(mode="json")
    for name,key in (("circuit_routes","id"),("zones","zone_id"),("circuit_budget","circuit_id")):
        plan_payload[name].sort(key=lambda v:v[key])
    sizing_payload = sizing.model_dump(mode="json")
    sizing_payload['coverage_integration']['validated_route_ids'].sort()
    payload = dict(sizing=sizing_payload,coverage=plan_payload,inputs=inputs.model_dump(mode="json"),
                   assessment=output.model_dump(mode="json",exclude={'assessment_digest'}))
    digest = hashlib.sha256(json.dumps(payload,ensure_ascii=False,allow_nan=False,sort_keys=True,
                                       separators=(',',':')).encode('utf8')).hexdigest()
    return output.model_copy(update={'assessment_digest':digest})


def size_ufh_requirement_with_engineering(request: UFHSizingRequest,
    inputs: UFHEngineeringIntegrationInputs, *,
    assess_balance_after_pressure_failure: bool = False) -> SizingEngineeringResult:
    """One legacy sizing/routing call, then a separate assessment; never retry/split."""
    if (inputs.theta_indoor_c != request.room.indoor_temperature_c or
        inputs.theta_below_c != request.room.insulation.floor_boundary_temperature_c):
        raise ValueError("Engineering indoor/lower boundary temperatures must match the sizing room")
    sizing,coverage = size_ufh_requirement_and_coverage(request)
    return SizingEngineeringResult(sizing=sizing,coverage=coverage,
        engineering=assess_ufh_candidates(
            sizing, coverage, inputs,
            assess_balance_after_pressure_failure=assess_balance_after_pressure_failure,
        ))

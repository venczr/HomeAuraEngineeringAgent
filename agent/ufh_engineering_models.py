"""Immutable SI inputs/results for UFH_ENGINEERING_KERNEL_V1 (no router contracts)."""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, model_validator

from agent.project_models import StrictProjectModel

Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Finite = Annotated[float, Field(allow_inf_nan=False)]
Name = Annotated[str, Field(min_length=1, max_length=256)]


class EngineeringModel(StrictProjectModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)


class Status(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED_THERMAL_OUTPUT = "REJECTED_THERMAL_OUTPUT"
    REJECTED_SURFACE_LIMIT = "REJECTED_SURFACE_LIMIT"
    REJECTED_NO_PHYSICAL_THERMAL_ROOT = "REJECTED_NO_PHYSICAL_THERMAL_ROOT"
    REJECTED_NUMERICAL_SOLVER_FAILURE = "REJECTED_NUMERICAL_SOLVER_FAILURE"
    REJECTED_CIRCUIT_PRESSURE = "REJECTED_CIRCUIT_PRESSURE"
    REJECTED_MANUFACTURER_PRESSURE_LIMIT = "REJECTED_MANUFACTURER_PRESSURE_LIMIT"
    REJECTED_BALANCEABILITY = "REJECTED_BALANCEABILITY"
    OUTSIDE_PUBLISHED_CHARACTERISTIC = "OUTSIDE_PUBLISHED_CHARACTERISTIC"
    OUTSIDE_RECOMMENDED_SETTING_RANGE = "OUTSIDE_RECOMMENDED_SETTING_RANGE"
    SPLIT_REQUIRED = "SPLIT_REQUIRED"
    REJECTED_NUMERICAL_CALCULATION = "REJECTED_NUMERICAL_CALCULATION"


class ValveLimitType(str, Enum):
    MECHANICAL_LIMIT = "MECHANICAL_LIMIT"
    MANUFACTURER_ADJUSTMENT_LIMIT = "MANUFACTURER_ADJUSTMENT_LIMIT"
    MANUFACTURER_RECOMMENDED_LIMIT = "MANUFACTURER_RECOMMENDED_LIMIT"
    PUBLISHED_CURVE_LIMIT = "PUBLISHED_CURVE_LIMIT"
    DIGITIZED_GRAPH_LIMIT = "DIGITIZED_GRAPH_LIMIT"


class CharacteristicScope(str, Enum):
    SINGLE_CONTROL_VALVE = "SINGLE_CONTROL_VALVE"
    SUPPLY_VALVE_PATH = "SUPPLY_VALVE_PATH"
    SUPPLY_PLUS_RETURN_BRANCH_PATH = "SUPPLY_PLUS_RETURN_BRANCH_PATH"
    COMPLETE_MANIFOLD_PATH = "COMPLETE_MANIFOLD_PATH"


class Diagnostic(EngineeringModel):
    code: Name
    message: Name
    circuit_id: Name | None = None


class ThermalTask(EngineeringModel):
    required_heat_w: Positive
    heated_area_m2: Positive
    k_h_w_m2k: Positive
    surface_limit_w_m2: Positive
    theta_indoor_c: Finite
    theta_below_c: Finite
    r_o_m2k_w: Nonnegative
    r_u_m2k_w: Positive
    mode: Literal["solve_return", "solve_supply"]
    theta_supply_c: Finite | None = None
    sigma_k: Positive | None = None

    @model_validator(mode="after")
    def mode_inputs(self):
        if self.mode == "solve_return":
            if self.theta_supply_c is None or self.sigma_k is not None:
                raise ValueError("solve_return requires supply only; sigma is solved")
        elif self.sigma_k is None or self.theta_supply_c is not None:
            raise ValueError("solve_supply requires sigma only; supply is solved")
        return self


class Fluid(EngineeringModel):
    density_kg_m3: Positive
    dynamic_viscosity_pa_s: Positive
    specific_gravity: Positive


class PipeCandidate(EngineeringModel):
    # Total actual straight-equivalent centreline length, heat + both transits.
    length_m: Positive
    inner_diameter_m: Positive
    roughness_m: Nonnegative


class ValveCharacteristic(EngineeringModel):
    manufacturer: Name
    product_family: Name
    product_version: Name | None = None
    document_reference: Name
    document_revision: Name | None = None
    characteristic_scope: CharacteristicScope
    included_components: tuple[Name, ...] = Field(min_length=1)
    kv_min_m3h: Positive | None = None
    kv_max_m3h: Positive | None = None
    setting_min: Finite | None = None
    setting_max: Finite | None = None
    limit_type: ValveLimitType
    source_confidence: Name

    @model_validator(mode="after")
    def ranges(self):
        for a, b in ((self.kv_min_m3h, self.kv_max_m3h), (self.setting_min, self.setting_max)):
            if (a is None) != (b is None) or (a is not None and a > b):
                raise ValueError("Characteristic endpoints must be paired and ordered")
        if len(set(self.included_components)) != len(self.included_components):
            raise ValueError("Duplicate included component")
        return self


class FixedLoss(EngineeringModel):
    component_id: Name
    pressure_pa: Nonnegative


class EmbeddedLosses(EngineeringModel):
    continuous_bends_pa: Nonnegative
    pipe_fittings_pa: Nonnegative
    other_fixed_pipe_path_pa: Nonnegative


class CircuitTask(EngineeringModel):
    circuit_id: Name
    thermal: ThermalTask
    fluid: Fluid
    pipe: PipeCandidate
    embedded_losses: EmbeddedLosses
    fixed_manifold_losses: tuple[FixedLoss, ...]
    control: ValveCharacteristic
    manufacturer_max_circuit_pressure_pa: Positive | None = None

    @model_validator(mode="after")
    def no_double_count(self):
        ids = [v.component_id for v in self.fixed_manifold_losses]
        if len(ids) != len(set(ids)) or set(ids) & set(self.control.included_components):
            raise ValueError("Fixed/control component overlap or duplicate: double counting")
        if self.control.kv_min_m3h is None:
            raise ValueError("V1 calculation requires an explicit Kv interval; settings alone unsupported")
        return self


class EngineeringRequest(EngineeringModel):
    schema_version: Literal["1.0"] = "1.0"
    circuits: tuple[CircuitTask, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [c.circuit_id for c in self.circuits]
        if len(set(ids)) != len(ids):
            raise ValueError("Circuit IDs must be unique")
        return self


class ThermalResult(EngineeringModel):
    status: Status
    q_required_w_m2: Positive
    lmtd_required_k: Positive | None = None
    theta_supply_c: Finite | None = None
    theta_return_c: Finite | None = None
    sigma_k: Positive | None = None
    iterations: int = Field(ge=0)
    diagnostics: tuple[Diagnostic, ...] = ()


class HydraulicResult(EngineeringModel):
    reynolds: Positive
    darcy_friction_factor: Positive
    velocity_m_s: Positive
    pressure_pa: Positive
    pressure_mbar: Positive
    pressure_per_m_pa: Positive


class PressureResult(EngineeringModel):
    en_circuit_pressure_pa: Nonnegative
    fixed_manifold_pressure_pa: Nonnegative
    en_pressure_ok: bool
    manufacturer_pressure_ok: bool | None


class BalanceCircuit(EngineeringModel):
    circuit_id: Name
    mass_flow_kg_s: Positive
    fluid: Fluid
    natural_pressure_pa: Nonnegative
    control: ValveCharacteristic


class BalanceInterval(EngineeringModel):
    circuit_id: Name
    valve_min_pa: Positive
    valve_max_pa: Positive
    low_pa: Nonnegative
    high_pa: Nonnegative


class DomainResult(EngineeringModel):
    status: Status
    within_characteristic: bool
    physical_impossibility: bool | None
    diagnostics: tuple[Diagnostic, ...]


class BalanceResult(EngineeringModel):
    status: Status
    balanceable: bool
    physical_impossibility: bool | None
    intervals: tuple[BalanceInterval, ...]
    low_global_pa: Nonnegative
    high_global_pa: Nonnegative
    limiting_low_circuit: Name
    limiting_high_circuit: Name
    feasible_interval_pa: tuple[Nonnegative, Nonnegative] | None
    diagnostics: tuple[Diagnostic, ...]


class CircuitResult(EngineeringModel):
    circuit_id: Name
    status: Status
    thermal: ThermalResult | None
    mass_flow_kg_s: Positive | None = None
    mass_flow_kg_h: Positive | None = None
    hydraulics: HydraulicResult | None = None
    pressure: PressureResult | None = None
    # At the lowest common feasible branch pressure, never an inferred pump head.
    manifold_control_pressure_pa: Nonnegative | None = None
    complete_branch_pressure_pa: Nonnegative | None = None
    required_control_kv_m3h: Positive | None = None
    diagnostics: tuple[Diagnostic, ...] = ()


class EngineeringResult(EngineeringModel):
    schema_version: Literal["1.0"] = "1.0"
    status: Status
    circuits: tuple[CircuitResult, ...]
    balance: BalanceResult | None
    diagnostics: tuple[Diagnostic, ...]
    result_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

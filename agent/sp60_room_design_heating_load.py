"""SP60 A.1 room-load assembly and fail-closed UFH heat-load handoff.

This module composes existing Q_tr, Q_vent and Q_inf calculations; it does
not duplicate their equations or execute the UFH sizing/routing pipeline.
"""
from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from agent.project_models import StrictProjectModel
from agent.ufh_engineering_models import ThermalTask
from agent.ventilation_infiltration_heat_loss import (
    A1ComponentInput,
    MaterialEquipmentWarmingHeatLoadResult,
    RoomVentilationHeatLossResult,
    RoomInfiltrationHeatLossResult,
    RoomHeatingLoadComponents,
    aggregate_sp60_a1_components,
)


def _jsonable(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(_jsonable(value), sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


class SP60RoomDesignHeatingLoad(StrictProjectModel):
    project_id: str
    building_id: str
    level_id: str
    room_id: str
    q_tr_w: Decimal | None
    q_vent_w: Decimal | None
    q_inf_w: Decimal | None
    q_mts_w: Decimal | None
    q_mts_assessment: MaterialEquipmentWarmingHeatLoadResult | A1ComponentInput
    room_design_heating_load_w: Decimal | None
    completeness_status: Literal["INCOMPLETE", "COMPLETE_SP60_A1_COMPONENTS"]
    unresolved_components: list[str]
    component_result_digests: dict[str, str]
    sp60_revision_digest: str
    a1_method_digest: str
    diagnostics: list[str] = Field(default_factory=list)
    digest: str

    @field_validator("q_tr_w", "q_vent_w", "q_inf_w", "q_mts_w", "room_design_heating_load_w", mode="before")
    @classmethod
    def decimal_values(cls, value):
        if value is None:
            return None
        result = value if isinstance(value, Decimal) else Decimal(str(value))
        if not result.is_finite():
            raise ValueError("FINITE_DECIMAL_REQUIRED")
        return result

    @model_validator(mode="after")
    def total_matches_gate(self):
        is_complete = self.completeness_status == "COMPLETE_SP60_A1_COMPONENTS"
        if is_complete != (self.room_design_heating_load_w is not None):
            raise ValueError("ROOM_DESIGN_LOAD_COMPLETENESS_MISMATCH")
        return self


def aggregate_sp60_room_design_heating_load(
    *, transmission_result,
    ventilation_result: RoomVentilationHeatLossResult,
    infiltration_result: RoomInfiltrationHeatLossResult,
    q_mts: MaterialEquipmentWarmingHeatLoadResult | A1ComponentInput,
) -> SP60RoomDesignHeatingLoad:
    """Compose the current four A.1 terms from existing component results."""
    components: RoomHeatingLoadComponents = aggregate_sp60_a1_components(
        transmission_result=transmission_result,
        ventilation_result=ventilation_result,
        infiltration_result=infiltration_result,
        q_mts=q_mts,
    )
    body = {
        "project_id": transmission_result.project_id,
        "building_id": transmission_result.building_id,
        "level_id": transmission_result.level_id,
        "room_id": components.room_id,
        "q_tr_w": components.q_tr_w,
        "q_vent_w": components.q_vent_w,
        "q_inf_w": components.q_inf_w,
        "q_mts_w": components.q_mts_w,
        "q_mts_assessment": q_mts,
        "room_design_heating_load_w": components.a1_total_heating_load_w,
        "completeness_status": components.completeness_status,
        "unresolved_components": components.unresolved_components,
        "component_result_digests": components.input_component_digests,
        "sp60_revision_digest": components.canonical_revision_digest,
        "a1_method_digest": components.normative_method_digest,
        "diagnostics": components.unresolved_components,
    }
    return SP60RoomDesignHeatingLoad.model_validate({**body, "digest": _digest(body)})


class UFHDesignHeatLoadInput(StrictProjectModel):
    """Provenance-bearing output for the existing UFH thermal heat-load slot."""

    project_id: str
    building_id: str
    level_id: str
    room_id: str
    design_heat_load_w: Decimal = Field(gt=0)
    source_sp60_result_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sp60_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_input_path: Literal["ThermalTask.required_heat_w"] = "ThermalTask.required_heat_w"
    digest: str

    @field_validator("design_heat_load_w", mode="before")
    @classmethod
    def decimal_heat(cls, value):
        result = value if isinstance(value, Decimal) else Decimal(str(value))
        if not result.is_finite():
            raise ValueError("FINITE_DECIMAL_REQUIRED")
        return result

def build_ufh_design_heat_load_input(result: SP60RoomDesignHeatingLoad) -> UFHDesignHeatLoadInput:
    if result.completeness_status != "COMPLETE_SP60_A1_COMPONENTS" or result.room_design_heating_load_w is None:
        raise ValueError("DESIGN_HEAT_LOAD_INCOMPLETE")
    if result.room_design_heating_load_w <= 0:
        raise ValueError("DESIGN_HEAT_LOAD_NOT_POSITIVE")
    body = {
        "project_id": result.project_id,
        "building_id": result.building_id,
        "level_id": result.level_id,
        "room_id": result.room_id,
        "design_heat_load_w": result.room_design_heating_load_w,
        "source_sp60_result_digest": result.digest,
        "source_sp60_revision_digest": result.sp60_revision_digest,
        "target_input_path": "ThermalTask.required_heat_w",
    }
    return UFHDesignHeatLoadInput.model_validate({**body, "digest": _digest(body)})


def bind_design_heat_load_to_thermal_task(
    heat_load: UFHDesignHeatLoadInput, thermal_context: ThermalTask,
) -> ThermalTask:
    """Replace only the existing required-heat input; never call the kernel."""
    float_value = float(heat_load.design_heat_load_w)
    if not math.isfinite(float_value):
        raise ValueError("UFH_HEAT_LOAD_OUT_OF_FLOAT_DOMAIN")
    if not float_value.is_integer() and Decimal(str(float_value)) != heat_load.design_heat_load_w:
        raise ValueError("UFH_HEAT_LOAD_FLOAT_PRECISION_LOSS")
    task = thermal_context.model_copy(update={"required_heat_w": float_value})
    validated = ThermalTask.model_validate(task.model_dump())
    if Decimal(str(validated.required_heat_w)) != heat_load.design_heat_load_w:
        raise ValueError("UFH_HEAT_LOAD_FLOAT_PRECISION_LOSS")
    return validated

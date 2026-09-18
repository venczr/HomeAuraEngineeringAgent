"""Explicit, deterministic heat-loss and UFH sizing MVP.

This layer consumes declared engineering assumptions and the accepted coverage
planner.  It does not contain normative defaults, hydraulics, product selection,
or CAD behavior.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Literal

from pydantic import Field, model_validator

from agent.floor_heating_coverage import (
    FloorHeatingCoveragePlan,
    FloorHeatingCoverageRequest,
    solve_floor_heating_coverage,
)
from agent.project_models import StrictProjectModel


class HeatLossOpening(StrictProjectModel):
    opening_id: str = Field(min_length=1, max_length=96)
    kind: Literal["window", "door"]
    width_mm: int = Field(gt=0, le=20_000)
    height_mm: int = Field(gt=0, le=20_000)
    u_value_w_m2k: float = Field(gt=0.0, le=20.0)


class HeatLossInsulationAssumptions(StrictProjectModel):
    exterior_wall_u_value_w_m2k: float = Field(gt=0.0, le=20.0)
    floor_u_value_w_m2k: float = Field(ge=0.0, le=20.0)
    ceiling_u_value_w_m2k: float = Field(ge=0.0, le=20.0)
    air_changes_per_hour: float = Field(ge=0.0, le=20.0)
    ventilation_heat_capacity_factor_wh_m3k: float = Field(gt=0.0, le=2.0)
    thermal_bridge_allowance_percent: float = Field(ge=0.0, le=100.0)
    design_margin_percent: float = Field(ge=0.0, le=100.0)
    floor_boundary_temperature_c: float = Field(ge=-100.0, le=100.0)
    ceiling_boundary_temperature_c: float = Field(ge=-100.0, le=100.0)


class FloorConstructionAssumptions(StrictProjectModel):
    declared_output_at_100mm_w_m2: float = Field(gt=0.0, le=500.0)
    declared_output_at_200mm_w_m2: float = Field(gt=0.0, le=500.0)
    output_basis_reference: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_output_order(self) -> FloorConstructionAssumptions:
        if self.declared_output_at_100mm_w_m2 < self.declared_output_at_200mm_w_m2:
            raise ValueError("100 mm declared output must not be below 200 mm output")
        return self


class RoomModel(StrictProjectModel):
    room_area_mm2: int = Field(gt=0)
    room_height_mm: int = Field(gt=0, le=20_000)
    exterior_wall_length_mm: int = Field(gt=0, le=1_000_000)
    openings: list[HeatLossOpening] = Field(default_factory=list, max_length=128)
    insulation: HeatLossInsulationAssumptions
    indoor_temperature_c: float = Field(ge=-50.0, le=100.0)
    outdoor_design_temperature_c: float = Field(ge=-100.0, le=60.0)

    @model_validator(mode="after")
    def validate_explicit_assumptions(self) -> RoomModel:
        if self.indoor_temperature_c <= self.outdoor_design_temperature_c:
            raise ValueError("indoor temperature must exceed outdoor design temperature")
        if self.insulation.floor_boundary_temperature_c > self.indoor_temperature_c:
            raise ValueError("floor boundary temperature must not exceed indoor temperature")
        if self.insulation.ceiling_boundary_temperature_c > self.indoor_temperature_c:
            raise ValueError("ceiling boundary temperature must not exceed indoor temperature")
        opening_ids = [item.opening_id for item in self.openings]
        if len(opening_ids) != len(set(opening_ids)):
            raise ValueError("opening_id values must be unique")
        if sum(item.width_mm * item.height_mm for item in self.openings) > (
            self.exterior_wall_length_mm * self.room_height_mm
        ):
            raise ValueError("opening area exceeds gross exterior wall area")
        return self


class UFHSizingRequest(StrictProjectModel):
    schema_version: Literal["1.0"] = "1.0"
    room: RoomModel
    coverage_request: FloorHeatingCoverageRequest
    floor_construction: FloorConstructionAssumptions

    @model_validator(mode="after")
    def validate_geometry_integration(self) -> UFHSizingRequest:
        if self.room.room_area_mm2 != _boundary_area_mm2(self.coverage_request):
            raise ValueError("declared room area must match the room boundary polygon")
        if (
            self.coverage_request.minimum_circuit_length_mm != 40_000
            or self.coverage_request.maximum_circuit_length_mm != 80_000
        ):
            raise ValueError("sizing MVP preserves the accepted 40000-80000 mm circuit limits")
        wall = self.coverage_request.exterior_wall_segments
        if len(wall) != 1:
            raise ValueError("sizing MVP requires exactly one exterior wall segment")
        segment = wall[0]
        segment_length = abs(segment.start.x_mm - segment.end.x_mm) + abs(
            segment.start.y_mm - segment.end.y_mm
        )
        if segment_length != self.room.exterior_wall_length_mm:
            raise ValueError("exterior wall length must match wall-side geometry")
        return self


class HeatLossBreakdown(StrictProjectModel):
    room_area_mm2: int = Field(ge=0)
    gross_exterior_wall_area_mm2: int = Field(ge=0)
    opening_area_mm2: int = Field(ge=0)
    net_opaque_wall_area_mm2: int = Field(ge=0)
    exterior_wall_loss_w: int = Field(ge=0)
    opening_loss_w: int = Field(ge=0)
    floor_loss_w: int = Field(ge=0)
    ceiling_loss_w: int = Field(ge=0)
    ventilation_loss_w: int = Field(ge=0)
    base_heat_loss_w: int = Field(ge=0)
    thermal_bridge_allowance_w: int = Field(ge=0)


class HeatLossEstimate(StrictProjectModel):
    estimated_heat_loss_w: int = Field(ge=0)
    required_heat_w: int = Field(ge=0)
    breakdown: HeatLossBreakdown


class UFHCoverageIntegration(StrictProjectModel):
    coverage_plan_id: str = Field(min_length=1, max_length=160)
    coverage_plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    coverage_plan_status: Literal["planned", "partial", "impossible"]
    geometry_required_circuit_count: int = Field(ge=0, le=3)
    valid_route_count: int = Field(ge=0, le=3)
    geometric_coverage_ratio: float = Field(ge=0.0, le=1.0)
    required_coverage_ratio: float = Field(ge=0.0)
    accepted: bool
    validated_route_ids: list[str] = Field(max_length=3)


class UFHRequirement(StrictProjectModel):
    schema_version: Literal["1.0"] = "1.0"
    requirement_id: str = Field(min_length=1, max_length=160)
    project_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=128)
    required_heat_w: int = Field(ge=0)
    estimated_heat_loss_w: int = Field(ge=0)
    required_heated_area: float = Field(ge=0.0)
    required_heated_area_mm2: int = Field(ge=0)
    recommended_coverage_ratio: float = Field(ge=0.0)
    recommended_spacing_mm: Literal[100, 200]
    required_circuit_count: int = Field(ge=0)
    coverage_status: Literal["accepted", "insufficient", "impossible"]
    excessive_circuit_count: bool
    minimum_circuit_length_mm: int = Field(gt=0)
    maximum_circuit_length_mm: int = Field(gt=0)
    heat_loss_breakdown: HeatLossBreakdown
    coverage_integration: UFHCoverageIntegration
    diagnostics: list[str] = Field(max_length=64)
    assumptions: list[str] = Field(max_length=64)
    sizing_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


def _decimal(value: float | int) -> Decimal:
    return Decimal(str(value))


def _round_w(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _boundary_area_mm2(request: FloorHeatingCoverageRequest) -> int:
    points = request.boundary.points
    return abs(sum(
        points[index].x_mm * points[index + 1].y_mm
        - points[index + 1].x_mm * points[index].y_mm
        for index in range(len(points) - 1)
    )) // 2


def _opening_area_mm2(opening: HeatLossOpening) -> int:
    return opening.width_mm * opening.height_mm


def _digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


class HeatLossEstimator:
    """Deterministic transmission/ventilation estimate from explicit inputs."""

    @staticmethod
    def estimate(room: RoomModel) -> HeatLossEstimate:
        room_area_mm2 = room.room_area_mm2
        gross_wall_area_mm2 = room.exterior_wall_length_mm * room.room_height_mm
        opening_area_mm2 = sum(_opening_area_mm2(item) for item in room.openings)
        net_wall_area_mm2 = gross_wall_area_mm2 - opening_area_mm2
        room_area_m2 = _decimal(room_area_mm2) / Decimal(1_000_000)
        wall_area_m2 = _decimal(net_wall_area_mm2) / Decimal(1_000_000)
        volume_m3 = room_area_m2 * _decimal(room.room_height_mm) / Decimal(1000)
        outdoor_delta = _decimal(room.indoor_temperature_c) - _decimal(
            room.outdoor_design_temperature_c
        )
        floor_delta = _decimal(room.indoor_temperature_c) - _decimal(
            room.insulation.floor_boundary_temperature_c
        )
        ceiling_delta = _decimal(room.indoor_temperature_c) - _decimal(
            room.insulation.ceiling_boundary_temperature_c
        )

        wall_loss = (
            wall_area_m2
            * _decimal(room.insulation.exterior_wall_u_value_w_m2k)
            * outdoor_delta
        )
        opening_loss = sum(
            _decimal(_opening_area_mm2(item))
            / Decimal(1_000_000)
            * _decimal(item.u_value_w_m2k)
            * outdoor_delta
            for item in room.openings
        )
        floor_loss = (
            room_area_m2
            * _decimal(room.insulation.floor_u_value_w_m2k)
            * floor_delta
        )
        ceiling_loss = (
            room_area_m2
            * _decimal(room.insulation.ceiling_u_value_w_m2k)
            * ceiling_delta
        )
        ventilation_loss = (
            _decimal(room.insulation.ventilation_heat_capacity_factor_wh_m3k)
            * _decimal(room.insulation.air_changes_per_hour)
            * volume_m3
            * outdoor_delta
        )
        base_loss = wall_loss + opening_loss + floor_loss + ceiling_loss + ventilation_loss
        bridge_allowance = base_loss * _decimal(
            room.insulation.thermal_bridge_allowance_percent
        ) / Decimal(100)
        estimated_loss = base_loss + bridge_allowance
        required_heat = estimated_loss * (
            Decimal(1)
            + _decimal(room.insulation.design_margin_percent) / Decimal(100)
        )
        breakdown = HeatLossBreakdown(
            room_area_mm2=room_area_mm2,
            gross_exterior_wall_area_mm2=gross_wall_area_mm2,
            opening_area_mm2=opening_area_mm2,
            net_opaque_wall_area_mm2=net_wall_area_mm2,
            exterior_wall_loss_w=_round_w(wall_loss),
            opening_loss_w=_round_w(opening_loss),
            floor_loss_w=_round_w(floor_loss),
            ceiling_loss_w=_round_w(ceiling_loss),
            ventilation_loss_w=_round_w(ventilation_loss),
            base_heat_loss_w=_round_w(base_loss),
            thermal_bridge_allowance_w=_round_w(bridge_allowance),
        )
        return HeatLossEstimate(
            estimated_heat_loss_w=_round_w(estimated_loss),
            required_heat_w=_round_w(required_heat),
            breakdown=breakdown,
        )


def size_ufh_requirement(request: UFHSizingRequest) -> UFHRequirement:
    return size_ufh_requirement_and_coverage(request)[0]


def size_ufh_requirement_and_coverage(
    request: UFHSizingRequest,
) -> tuple[UFHRequirement, FloorHeatingCoveragePlan]:
    """Expose the actual computed plan without rerouting or changing legacy output."""
    room_area_mm2 = request.room.room_area_mm2
    room_area_m2 = _decimal(room_area_mm2) / Decimal(1_000_000)
    heat_loss = HeatLossEstimator.estimate(request.room)
    required_heat = _decimal(heat_loss.required_heat_w)

    output_200 = _decimal(
        request.floor_construction.declared_output_at_200mm_w_m2
    )
    output_100 = _decimal(
        request.floor_construction.declared_output_at_100mm_w_m2
    )
    area_at_200_m2 = required_heat / output_200
    if area_at_200_m2 <= room_area_m2:
        recommended_spacing: Literal[100, 200] = 200
        required_area_m2 = area_at_200_m2
    else:
        recommended_spacing = 100
        required_area_m2 = required_heat / output_100
    required_area_mm2 = int(
        (required_area_m2 * Decimal(1_000_000)).to_integral_value(
            rounding=ROUND_CEILING
        )
    )
    required_ratio = (
        float(required_area_m2 / room_area_m2)
        if room_area_m2 > 0
        else float("inf")
    )

    coverage: FloorHeatingCoveragePlan = solve_floor_heating_coverage(
        request.coverage_request
    )
    diagnostics: list[str] = []
    if recommended_spacing == 100:
        diagnostics.append("UFH_100MM_FIELD_ROUTE_NOT_AVAILABLE_IN_ACCEPTED_V2")
        diagnostics.append(
            "Declared 200 mm output cannot cover the load over the full room area; "
            "the accepted route engine has no 100 mm field-route mode."
        )
    if required_ratio > 1.0:
        diagnostics.append("UFH_OUTPUT_CAPACITY_INSUFFICIENT")
        diagnostics.append(
            "Required heated area exceeds the full room area at the declared output."
        )
    if coverage.status == "impossible":
        diagnostics.append("UFH_COVERAGE_PLAN_IMPOSSIBLE")
        diagnostics.append("The accepted coverage planner could not produce validated routes.")

    heat_required_count = (
        (
            required_area_mm2 * coverage.collector_port_count
            + coverage.estimated_coverage_mm2
            - 1
        )
        // coverage.estimated_coverage_mm2
        if coverage.collector_port_count and coverage.estimated_coverage_mm2 > 0
        else 0
    )
    required_circuit_count = max(
        coverage.required_circuit_count,
        heat_required_count,
    )
    excessive = required_circuit_count > 3
    if excessive:
        diagnostics.append("UFH_REQUIRED_CIRCUIT_COUNT_EXCEEDS_THREE")
        diagnostics.append(
            f"Heat-area allocation requires {required_circuit_count} circuits; "
            "the accepted bounded coverage planner supports at most 3."
        )

    routes_valid = (
        coverage.collector_port_count == len(coverage.circuit_routes)
        and all(
            route.validation.valid
            and request.coverage_request.minimum_circuit_length_mm
            <= route.length_mm
            <= request.coverage_request.maximum_circuit_length_mm
            for route in coverage.circuit_routes
        )
    )
    accepted = (
        coverage.status != "impossible"
        and routes_valid
        and recommended_spacing == 200
        and required_ratio <= coverage.coverage_ratio
        and not excessive
    )
    if not accepted and coverage.status != "impossible":
        diagnostics.append("UFH_GEOMETRIC_COVERAGE_INSUFFICIENT")
        diagnostics.append(
            "Required coverage ratio "
            f"{required_ratio:.6f} exceeds accepted usable ratio "
            f"{coverage.coverage_ratio:.6f} or requires an unsupported spacing/count."
        )
    coverage_status: Literal["accepted", "insufficient", "impossible"] = (
        "accepted"
        if accepted
        else "impossible"
        if coverage.status == "impossible"
        else "insufficient"
    )

    breakdown = heat_loss.breakdown
    integration = UFHCoverageIntegration(
        coverage_plan_id=coverage.plan_id,
        coverage_plan_digest=coverage.plan_digest,
        coverage_plan_status=coverage.status,
        geometry_required_circuit_count=coverage.required_circuit_count,
        valid_route_count=len(coverage.circuit_routes),
        geometric_coverage_ratio=coverage.coverage_ratio,
        required_coverage_ratio=required_ratio,
        accepted=accepted,
        validated_route_ids=[route.id for route in coverage.circuit_routes],
    )
    assumptions = [
        "All U-values, boundary temperatures, ventilation factors and margins are explicit request inputs.",
        "Area values named required_heated_area are expressed in square metres.",
        f"Floor output basis: {request.floor_construction.output_basis_reference}",
        "This is a deterministic MVP estimate, not normative compliance or professional heat-loss software.",
        "Pump, mixing unit, pipe diameter, flow and hydraulic balancing are not calculated.",
        "Accepted V2 circuit routes remain constrained to 40000-80000 mm.",
    ]
    content = {
        "request": request.model_dump(mode="json"),
        "breakdown": breakdown.model_dump(mode="json"),
        "coverage": integration.model_dump(mode="json"),
        "required_heat_w": heat_loss.required_heat_w,
        "required_heated_area_mm2": required_area_mm2,
        "recommended_spacing_mm": recommended_spacing,
        "required_circuit_count": required_circuit_count,
        "coverage_status": coverage_status,
        "diagnostics": diagnostics,
        "assumptions": assumptions,
    }
    sizing_digest = _digest(content)
    requirement = UFHRequirement(
        requirement_id=f"fh-sizing-{sizing_digest}",
        project_id=request.coverage_request.project_id,
        room_id=request.coverage_request.room_id,
        required_heat_w=heat_loss.required_heat_w,
        estimated_heat_loss_w=heat_loss.estimated_heat_loss_w,
        required_heated_area=float(required_area_m2),
        required_heated_area_mm2=required_area_mm2,
        recommended_coverage_ratio=required_ratio,
        recommended_spacing_mm=recommended_spacing,
        required_circuit_count=required_circuit_count,
        coverage_status=coverage_status,
        excessive_circuit_count=excessive,
        minimum_circuit_length_mm=request.coverage_request.minimum_circuit_length_mm,
        maximum_circuit_length_mm=request.coverage_request.maximum_circuit_length_mm,
        heat_loss_breakdown=breakdown,
        coverage_integration=integration,
        diagnostics=diagnostics,
        assumptions=assumptions,
        sizing_digest=sizing_digest,
    )
    return requirement, coverage


__all__ = [
    "FloorConstructionAssumptions",
    "HeatLossEstimate",
    "HeatLossEstimator",
    "HeatLossInsulationAssumptions",
    "HeatLossOpening",
    "RoomModel",
    "UFHRequirement",
    "UFHSizingRequest",
    "size_ufh_requirement",
    "size_ufh_requirement_and_coverage",
]

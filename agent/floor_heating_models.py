from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from agent.project_models import StrictProjectModel


class FloorHeatingPoint(StrictProjectModel):
    x_mm: int
    y_mm: int


class FloorHeatingPolygon(StrictProjectModel):
    points: list[FloorHeatingPoint] = Field(
        min_length=4,
        max_length=256,
    )


class FloorHeatingWallSegment(StrictProjectModel):
    reference: str = Field(min_length=1, max_length=96)
    start: FloorHeatingPoint
    end: FloorHeatingPoint


class FloorHeatingRequest(StrictProjectModel):
    schema_version: Literal["1.0"] = "1.0"
    project_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=128)
    boundary: FloorHeatingPolygon
    exclusion_zones: list[FloorHeatingPolygon] = Field(
        default_factory=list,
        max_length=64,
    )
    collector_point: FloorHeatingPoint
    wall_offset_mm: int = Field(ge=0, le=10_000)
    spacing_mm: Literal[100, 150, 200]
    maximum_circuit_length_mm: int = Field(
        default=80_000,
        ge=1,
        le=500_000,
    )
    minimum_circuit_length_mm: int = Field(
        default=40_000,
        ge=1,
        le=500_000,
    )
    turn_radius_mm: int = Field(default=100, ge=0, le=500)
    routing_mode: Literal["legacy", "non_crossing_visual"] = "legacy"
    requested_circuit_count: Literal[1, 2, 3] | None = None
    request_reference: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
    )
    field_spacing_mm: Literal[100, 150, 200] | None = None
    perimeter_spacing_mm: Literal[100] | None = None
    perimeter_band_depth_mm: int | None = Field(default=None, ge=1, le=10_000)
    exterior_wall_segments: list[FloorHeatingWallSegment] = Field(
        default_factory=list,
        max_length=16,
    )
    preferred_topology: Literal[
        "HYBRID_PERIMETER_SERPENTINE_COUNTERFLOW_SPIRAL"
    ] | None = None
    installation_grid_spacing_mm: Literal[100] | None = None
    perimeter_priority_mode: bool = True

    @model_validator(mode="after")
    def validate_circuit_length_window(self) -> FloorHeatingRequest:
        if self.minimum_circuit_length_mm > self.maximum_circuit_length_mm:
            raise ValueError(
                "minimum_circuit_length_mm must not exceed maximum_circuit_length_mm"
            )
        return self


class FloorHeatingDiagnostic(StrictProjectModel):
    code: str = Field(min_length=1, max_length=96)
    message: str = Field(min_length=1, max_length=512)
    path: str | None = Field(default=None, max_length=256)


class FloorHeatingLane(StrictProjectModel):
    lane_index: int = Field(ge=0)
    center_y_mm: int
    points: list[FloorHeatingPoint] = Field(min_length=2, max_length=2)
    length_mm: int = Field(ge=0)


class FloorHeatingCircuit(StrictProjectModel):
    circuit_id: str = Field(min_length=1, max_length=96)
    points: list[FloorHeatingPoint] = Field(
        min_length=3,
        max_length=20_000,
    )
    supply_transit: list[FloorHeatingPoint] = Field(
        min_length=1,
        max_length=128,
    )
    return_transit: list[FloorHeatingPoint] = Field(
        min_length=1,
        max_length=128,
    )
    length_mm: int = Field(ge=0)
    zone_role: Literal["PERIMETER_ZONE", "OCCUPIED_FIELD"] | None = None
    topology: Literal["SERPENTINE", "COUNTERFLOW_SPIRAL"] | None = None
    nominal_spacing_mm: int | None = Field(default=None, ge=1)
    perimeter_laying_length_mm: int = Field(default=0, ge=0)
    field_laying_length_mm: int = Field(default=0, ge=0)
    exterior_wall_references: list[str] = Field(default_factory=list, max_length=16)


class CircuitRouteSegment(StrictProjectModel):
    segment_index: int = Field(ge=0)
    start: FloorHeatingPoint
    end: FloorHeatingPoint
    length_mm: int = Field(gt=0)
    nominal_spacing_mm: Literal[100, 200]
    zone_role: Literal["OUTER_WALL_BAND", "FIELD"]


class CircuitSpacingSegment(StrictProjectModel):
    reference: str = Field(min_length=1, max_length=96)
    first_start: FloorHeatingPoint
    first_end: FloorHeatingPoint
    second_start: FloorHeatingPoint
    second_end: FloorHeatingPoint
    spacing_mm: Literal[100, 200]
    zone_role: Literal["OUTER_WALL_BAND", "FIELD"]


class CircuitRouteValidation(StrictProjectModel):
    polyline_count: Literal[1]
    connected: bool
    self_intersection: bool
    branches: bool
    step_valid: bool
    length_valid: bool
    inside_boundary: bool
    exclusion_clear: bool
    endpoints_valid: bool
    calculated_length_mm: int = Field(ge=0)
    polyline_length_mm: int = Field(ge=0)
    valid: bool
    diagnostics: list[str] = Field(default_factory=list, max_length=64)


class CircuitRoute(StrictProjectModel):
    id: str = Field(min_length=1, max_length=96)
    polyline: list[FloorHeatingPoint] = Field(min_length=3, max_length=20_000)
    length_mm: int = Field(ge=0)
    spacing_segments: list[CircuitSpacingSegment] = Field(max_length=64)
    outer_wall_segments: list[CircuitRouteSegment] = Field(max_length=20_000)
    field_segments: list[CircuitRouteSegment] = Field(max_length=20_000)
    collector_supply_point: FloorHeatingPoint
    collector_return_point: FloorHeatingPoint
    validation: CircuitRouteValidation


class FloorHeatingResult(StrictProjectModel):
    schema_version: Literal["1.0"] = "1.0"
    project_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=128)
    status: Literal["ok", "impossible"]
    usable_heated_area_mm2: int = Field(ge=0)
    spacing_mm: Literal[100, 150, 200]
    wall_offset_mm: int = Field(ge=0)
    maximum_circuit_length_mm: int = Field(ge=1)
    circuit_count: int = Field(ge=0, le=3)
    lanes: list[FloorHeatingLane] = Field(max_length=20_000)
    circuits: list[FloorHeatingCircuit] = Field(max_length=3)
    circuit_routes: list[CircuitRoute] = Field(default_factory=list, max_length=3)
    unresolved_regions: list[FloorHeatingPolygon] = Field(
        max_length=64,
    )
    warnings: list[str] = Field(max_length=64)
    assumptions: list[str] = Field(max_length=64)
    diagnostics: list[FloorHeatingDiagnostic] = Field(max_length=64)
    maximum_length_compliant: bool
    result_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    field_spacing_mm: int | None = Field(default=None, ge=1)
    perimeter_spacing_mm: int | None = Field(default=None, ge=1)
    perimeter_band_depth_mm: int | None = Field(default=None, ge=1)
    exterior_wall_segments: list[FloorHeatingWallSegment] = Field(
        default_factory=list,
        max_length=16,
    )
    perimeter_band_polygon: FloorHeatingPolygon | None = None
    perimeter_band_digest: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    turn_radius_mm: int = Field(default=0, ge=0, le=500)
    routing_mode: Literal["legacy", "non_crossing_visual"] = "legacy"
    preferred_topology: str | None = Field(default=None, max_length=96)
    installation_grid_spacing_mm: int | None = Field(default=None, ge=1)
    room_boundary: FloorHeatingPolygon | None = None
    exclusion_zones: list[FloorHeatingPolygon] = Field(default_factory=list, max_length=64)


def model_json(value: Any) -> dict[str, Any]:
    """Return JSON-mode data for deterministic digest construction."""
    if isinstance(value, StrictProjectModel):
        return value.model_dump(mode="json")
    return value

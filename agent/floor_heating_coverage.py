"""Deterministic coverage planning above the validated V2 route engine."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Literal

from pydantic import Field, field_validator
from pydantic_core import PydanticCustomError

from agent.floor_heating_engine import calculate_floor_heating
from agent.floor_heating_models import (
    CircuitRoute,
    FloorHeatingPoint,
    FloorHeatingPolygon,
    FloorHeatingRequest,
    FloorHeatingWallSegment,
)
from agent.project_models import StrictProjectModel


class FloorHeatingCoverageRequest(FloorHeatingRequest):
    """None selects legacy automatic count; 1..3 requests that exact partition."""

    @field_validator("requested_circuit_count", mode="before")
    @classmethod
    def validate_requested_count(cls, value):
        # Literal[int] alone can accept numerically equal bool/float values.
        if value is not None and (type(value) is not int or value not in (1, 2, 3)):
            raise PydanticCustomError(
                "INVALID_REQUESTED_CIRCUIT_COUNT",
                "requested_circuit_count must be null or an integer from 1 to 3",
            )
        return value


class FloorHeatingCoverageZone(StrictProjectModel):
    zone_id: str = Field(min_length=1, max_length=160)
    boundary: FloorHeatingPolygon
    exclusion_zones: list[FloorHeatingPolygon] = Field(max_length=64)
    exterior_wall_segments: list[FloorHeatingWallSegment] = Field(max_length=1)
    route_anchor_point: FloorHeatingPoint
    estimated_required_pipe_length_mm: int = Field(ge=0)
    generated_route_length_mm: int = Field(ge=0)
    estimated_coverage_mm2: int = Field(ge=0)
    circuit_id: str | None = Field(default=None, max_length=96)
    route_valid: bool


class FloorHeatingCircuitBudget(StrictProjectModel):
    circuit_id: str = Field(min_length=1, max_length=96)
    zone_id: str = Field(min_length=1, max_length=160)
    minimum_length_mm: int = Field(gt=0)
    maximum_length_mm: int = Field(gt=0)
    estimated_required_length_mm: int = Field(ge=0)
    generated_length_mm: int = Field(ge=0)
    within_length_window: bool


class FloorHeatingCoveragePlan(StrictProjectModel):
    schema_version: Literal["1.0"] = "1.0"
    plan_id: str = Field(min_length=1, max_length=160)
    project_id: str = Field(min_length=1, max_length=128)
    room_id: str = Field(min_length=1, max_length=128)
    status: Literal["planned", "partial", "impossible"]
    required_circuit_count: int = Field(ge=0, le=3)
    collector_port_count: int = Field(ge=0, le=3)
    heated_area_mm2: int = Field(ge=0)
    estimated_required_pipe_length_mm: int = Field(ge=0)
    estimated_coverage_mm2: int = Field(ge=0)
    coverage_ratio: float = Field(ge=0.0, le=1.0)
    full_coverage_claimed: bool
    zones: list[FloorHeatingCoverageZone] = Field(max_length=3)
    circuit_budget: list[FloorHeatingCircuitBudget] = Field(max_length=3)
    circuit_routes: list[CircuitRoute] = Field(max_length=3)
    diagnostics: list[str] = Field(max_length=64)
    plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


def _area(points: list[FloorHeatingPoint]) -> int:
    return abs(sum(
        points[index].x_mm * points[index + 1].y_mm
        - points[index + 1].x_mm * points[index].y_mm
        for index in range(len(points) - 1)
    )) // 2


def _rectangle_bounds(polygon: FloorHeatingPolygon) -> tuple[int, int, int, int] | None:
    body = polygon.points[:-1] if polygon.points[0] == polygon.points[-1] else polygon.points
    if len(body) != 4:
        return None
    xs = {point.x_mm for point in body}
    ys = {point.y_mm for point in body}
    if len(xs) != 2 or len(ys) != 2:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _point(x: int, y: int) -> FloorHeatingPoint:
    return FloorHeatingPoint(x_mm=x, y_mm=y)


def _rectangle(left: int, bottom: int, right: int, top: int) -> FloorHeatingPolygon:
    return FloorHeatingPolygon(points=[
        _point(left, bottom),
        _point(right, bottom),
        _point(right, top),
        _point(left, top),
        _point(left, bottom),
    ])


def _project_to_zone_grid(
    value: int,
    lower: int,
    upper: int,
    *,
    clearance: int,
    grid: int,
) -> int:
    """Project an editor anchor into a zone without inventing an off-grid point."""
    first_grid = math.ceil((lower + clearance) / grid) * grid
    last_grid = math.floor((upper - clearance) / grid) * grid
    if first_grid > last_grid:
        return (lower + upper) // 2
    snapped = round(value / grid) * grid
    return max(first_grid, min(snapped, last_grid))


def _wall_side(
    request: FloorHeatingCoverageRequest,
    bounds: tuple[int, int, int, int],
) -> str | None:
    if len(request.exterior_wall_segments) != 1:
        return None
    wall = request.exterior_wall_segments[0]
    start = (wall.start.x_mm, wall.start.y_mm)
    end = (wall.end.x_mm, wall.end.y_mm)
    min_x, min_y, max_x, max_y = bounds
    if {start, end} == {(min_x, min_y), (max_x, min_y)}:
        return "bottom"
    if {start, end} == {(min_x, max_y), (max_x, max_y)}:
        return "top"
    if {start, end} == {(min_x, min_y), (min_x, max_y)}:
        return "left"
    if {start, end} == {(max_x, min_y), (max_x, max_y)}:
        return "right"
    return None


def _estimated_required_length(
    area_mm2: int,
    exterior_length_mm: int,
    inward_depth_mm: int,
    band_depth_mm: int,
    perimeter_spacing_mm: int,
    field_spacing_mm: int,
) -> int:
    band_area = min(area_mm2, exterior_length_mm * min(inward_depth_mm, band_depth_mm))
    field_area = max(0, area_mm2 - band_area)
    return math.ceil(
        band_area / perimeter_spacing_mm + field_area / field_spacing_mm
    )


def _digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _empty_plan(
    request: FloorHeatingCoverageRequest,
    diagnostics: list[str],
    *,
    area: int = 0,
    estimated_length: int = 0,
) -> FloorHeatingCoveragePlan:
    if request.requested_circuit_count is not None:
        diagnostics = ["REQUESTED_CIRCUIT_COUNT_NOT_FEASIBLE", *diagnostics]
    content = {
        "request": request.model_dump(mode="json"),
        "status": "impossible",
        "heated_area_mm2": area,
        "estimated_required_pipe_length_mm": estimated_length,
        "diagnostics": diagnostics,
    }
    digest = _digest(content)
    return FloorHeatingCoveragePlan(
        plan_id=f"fh-coverage-{digest}",
        project_id=request.project_id,
        room_id=request.room_id,
        status="impossible",
        required_circuit_count=0,
        collector_port_count=0,
        heated_area_mm2=area,
        estimated_required_pipe_length_mm=estimated_length,
        estimated_coverage_mm2=0,
        coverage_ratio=0.0,
        full_coverage_claimed=False,
        zones=[],
        circuit_budget=[],
        circuit_routes=[],
        diagnostics=diagnostics,
        plan_digest=digest,
    )


def solve_floor_heating_coverage(
    request: FloorHeatingCoverageRequest,
) -> FloorHeatingCoveragePlan:
    bounds = _rectangle_bounds(request.boundary)
    if bounds is None:
        return _empty_plan(request, ["COVERAGE_RECTANGLE_REQUIRED"])
    side = _wall_side(request, bounds)
    if side is None:
        return _empty_plan(request, ["COVERAGE_EXACTLY_ONE_EXTERIOR_WALL_REQUIRED"])
    min_x, min_y, max_x, max_y = bounds
    width = max_x - min_x
    height = max_y - min_y
    exclusions_area = sum(_area(zone.points) for zone in request.exclusion_zones)
    heated_area = max(0, width * height - exclusions_area)
    exterior_length = width if side in {"bottom", "top"} else height
    inward_depth = height if side in {"bottom", "top"} else width
    estimated_length = _estimated_required_length(
        heated_area,
        exterior_length,
        inward_depth,
        request.perimeter_band_depth_mm or 1000,
        request.perimeter_spacing_mm or 100,
        request.field_spacing_mm or 200,
    )
    required_count = (
        request.requested_circuit_count
        if request.requested_circuit_count is not None
        else max(1, math.ceil(estimated_length / request.maximum_circuit_length_mm))
    )
    if required_count > 3:
        return _empty_plan(
            request,
            ["COVERAGE_REQUIRES_MORE_THAN_THREE_CIRCUITS"],
            area=heated_area,
            estimated_length=estimated_length,
        )

    zones: list[FloorHeatingCoverageZone] = []
    budgets: list[FloorHeatingCircuitBudget] = []
    routes: list[CircuitRoute] = []
    diagnostics: list[str] = []
    generated_coverage = 0
    grid = request.installation_grid_spacing_mm or 100
    clearance = max(request.wall_offset_mm, grid)
    for index in range(required_count):
        if side in {"bottom", "top"}:
            zone_min = min_x + round(index * width / required_count / grid) * grid
            zone_max = min_x + round((index + 1) * width / required_count / grid) * grid
            if index == required_count - 1:
                zone_max = max_x
            zone_boundary = _rectangle(zone_min, min_y, zone_max, max_y)
            wall_y = min_y if side == "bottom" else max_y
            zone_wall = FloorHeatingWallSegment(
                reference=f"{request.exterior_wall_segments[0].reference}/zone-{index + 1}",
                start=_point(zone_min, wall_y),
                end=_point(zone_max, wall_y),
            )
            zone_collector = _point(
                _project_to_zone_grid(request.collector_point.x_mm, zone_min, zone_max, clearance=clearance, grid=grid),
                _project_to_zone_grid(request.collector_point.y_mm, min_y, max_y, clearance=clearance, grid=grid),
            )
        else:
            zone_min = min_y + round(index * height / required_count / grid) * grid
            zone_max = min_y + round((index + 1) * height / required_count / grid) * grid
            if index == required_count - 1:
                zone_max = max_y
            zone_boundary = _rectangle(min_x, zone_min, max_x, zone_max)
            wall_x = min_x if side == "left" else max_x
            zone_wall = FloorHeatingWallSegment(
                reference=f"{request.exterior_wall_segments[0].reference}/zone-{index + 1}",
                start=_point(wall_x, zone_min),
                end=_point(wall_x, zone_max),
            )
            zone_collector = _point(
                _project_to_zone_grid(request.collector_point.x_mm, min_x, max_x, clearance=clearance, grid=grid),
                _project_to_zone_grid(request.collector_point.y_mm, zone_min, zone_max, clearance=clearance, grid=grid),
            )

        zone_exclusions: list[FloorHeatingPolygon] = []
        for exclusion in request.exclusion_zones:
            points = exclusion.points[:-1]
            inside = all(
                zone_boundary.points[0].x_mm <= point.x_mm <= zone_boundary.points[2].x_mm
                and zone_boundary.points[0].y_mm <= point.y_mm <= zone_boundary.points[2].y_mm
                for point in points
            )
            if inside:
                zone_exclusions.append(exclusion)
                continue
            overlaps = any(
                zone_boundary.points[0].x_mm < point.x_mm < zone_boundary.points[2].x_mm
                and zone_boundary.points[0].y_mm < point.y_mm < zone_boundary.points[2].y_mm
                for point in points
            )
            if overlaps:
                return _empty_plan(
                    request,
                    ["COVERAGE_EXCLUSION_CROSSES_ZONE_BOUNDARY"],
                    area=heated_area,
                    estimated_length=estimated_length,
                )

        zone_area = _area(zone_boundary.points) - sum(
            _area(zone.points) for zone in zone_exclusions
        )
        zone_external_length = (
            zone_boundary.points[1].x_mm - zone_boundary.points[0].x_mm
            if side in {"bottom", "top"}
            else zone_boundary.points[2].y_mm - zone_boundary.points[1].y_mm
        )
        zone_inward = height if side in {"bottom", "top"} else width
        zone_estimate = _estimated_required_length(
            zone_area,
            zone_external_length,
            zone_inward,
            request.perimeter_band_depth_mm or 1000,
            request.perimeter_spacing_mm or 100,
            request.field_spacing_mm or 200,
        )
        zone_request = FloorHeatingRequest.model_validate({
            **request.model_dump(mode="json"),
            "room_id": f"{request.room_id}/coverage-zone-{index + 1}",
            "boundary": zone_boundary.model_dump(mode="json"),
            "exclusion_zones": [zone.model_dump(mode="json") for zone in zone_exclusions],
            "collector_point": zone_collector.model_dump(mode="json"),
            "exterior_wall_segments": [zone_wall.model_dump(mode="json")],
            "requested_circuit_count": 1,
        })
        result = calculate_floor_heating(zone_request)
        zone_id = f"fh-zone-{index + 1}"
        if result.status != "ok" or len(result.circuit_routes) != 1:
            reasons = [item.code for item in result.diagnostics]
            diagnostics.extend(
                f"{zone_id}:{code}" for code in (reasons or ["ROUTE_NOT_VALID"])
            )
            if request.requested_circuit_count is not None:
                for failed_route in result.circuit_routes:
                    diagnostics.extend(
                        f"{zone_id}:{reason}" for reason in failed_route.validation.diagnostics
                    )
                    diagnostics.append(f"{zone_id}:ACTUAL_LENGTH_MM={failed_route.length_mm}")
            return _empty_plan(
                request,
                diagnostics,
                area=heated_area,
                estimated_length=estimated_length,
            )
        route = result.circuit_routes[0]
        route_coverage = min(
            zone_area,
            sum(item.length_mm * item.nominal_spacing_mm for item in route.outer_wall_segments)
            + sum(item.length_mm * item.nominal_spacing_mm for item in route.field_segments),
        )
        generated_coverage += route_coverage
        routes.append(route)
        zones.append(FloorHeatingCoverageZone(
            zone_id=zone_id,
            boundary=zone_boundary,
            exclusion_zones=zone_exclusions,
            exterior_wall_segments=[zone_wall],
            route_anchor_point=zone_collector,
            estimated_required_pipe_length_mm=zone_estimate,
            generated_route_length_mm=route.length_mm,
            estimated_coverage_mm2=route_coverage,
            circuit_id=route.id,
            route_valid=route.validation.valid,
        ))
        budgets.append(FloorHeatingCircuitBudget(
            circuit_id=route.id,
            zone_id=zone_id,
            minimum_length_mm=request.minimum_circuit_length_mm,
            maximum_length_mm=request.maximum_circuit_length_mm,
            estimated_required_length_mm=zone_estimate,
            generated_length_mm=route.length_mm,
            within_length_window=(
                request.minimum_circuit_length_mm
                <= route.length_mm
                <= request.maximum_circuit_length_mm
            ),
        ))

    ratio = min(1.0, generated_coverage / heated_area) if heated_area else 0.0
    # Length × spacing is an estimate, not a geometric union.  MVP must never
    # promote it into a full-coverage claim.
    full = False
    status: Literal["partial"] = "partial"
    diagnostics.append("COVERAGE_ESTIMATE_ONLY_FULL_COVERAGE_NOT_CLAIMED")
    content = {
        "request": request.model_dump(mode="json"),
        "project_id": request.project_id,
        "room_id": request.room_id,
        "status": status,
        "required_circuit_count": required_count,
        "collector_port_count": len(routes),
        "heated_area_mm2": heated_area,
        "estimated_required_pipe_length_mm": estimated_length,
        "estimated_coverage_mm2": generated_coverage,
        "zones": [zone.model_dump(mode="json") for zone in zones],
        "routes": [route.model_dump(mode="json") for route in routes],
        "circuit_budget": [budget.model_dump(mode="json") for budget in budgets],
        "coverage_ratio": ratio,
        "full_coverage_claimed": full,
        "diagnostics": diagnostics,
    }
    digest = _digest(content)
    return FloorHeatingCoveragePlan(
        plan_id=f"fh-coverage-{digest}",
        project_id=request.project_id,
        room_id=request.room_id,
        status=status,
        required_circuit_count=required_count,
        collector_port_count=len(routes),
        heated_area_mm2=heated_area,
        estimated_required_pipe_length_mm=estimated_length,
        estimated_coverage_mm2=generated_coverage,
        coverage_ratio=ratio,
        full_coverage_claimed=full,
        zones=zones,
        circuit_budget=budgets,
        circuit_routes=routes,
        diagnostics=diagnostics,
        plan_digest=digest,
    )


__all__ = [
    "FloorHeatingCoveragePlan",
    "FloorHeatingCoverageRequest",
    "solve_floor_heating_coverage",
]

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from agent.floor_heating_coverage import (
    FloorHeatingCoveragePlan,
    FloorHeatingCoverageRequest,
    solve_floor_heating_coverage,
)
from agent.ifc_space_preview_api import require_loopback_request
from agent.project_models import ProjectJsonError
from agent.ufh_strategy_selector import select_layout
from agent.ufh_building_routing import route_building_system


MAX_FLOOR_HEATING_COVERAGE_PAYLOAD_BYTES = 2 * 1024 * 1024

router = APIRouter(
    prefix="/api/v1/engineering/floor-heating",
    tags=["floor-heating-coverage-preview"],
)
auto_zone_router = APIRouter()


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


async def _read_request(request: Request) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_FLOOR_HEATING_COVERAGE_PAYLOAD_BYTES:
            raise _error(413, "floor_heating_coverage_payload_too_large", "Floor-heating coverage preview body is too large.")
    if not body.lstrip().startswith(b"{"):
        raise _error(400, "floor_heating_coverage_payload_invalid", "Floor-heating coverage preview body must be an object.")
    return bytes(body)


@router.post("/coverage-preview", response_model=FloorHeatingCoveragePlan)
async def preview_floor_heating_coverage(request: Request) -> Response:
    try:
        require_loopback_request(request)
        raw_body = await _read_request(request)
        coverage_request = FloorHeatingCoverageRequest.model_validate_json(raw_body)
        plan = solve_floor_heating_coverage(coverage_request)
        content = json.dumps(
            plan.model_dump(mode="json"),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return Response(content=content, media_type="application/json")
    except HTTPException:
        raise
    except ProjectJsonError as error:
        raise _error(400, "floor_heating_coverage_payload_invalid", "Floor-heating coverage preview JSON is invalid.") from error
    except ValueError as error:
        raise _error(422, "floor_heating_coverage_request_invalid", "Floor-heating coverage preview request failed validation.") from error
    except Exception as error:
        raise _error(500, "floor_heating_coverage_preview_failed", "Floor-heating coverage preview failed.") from error


@auto_zone_router.post("/zone-preview", include_in_schema=False)
async def preview_floor_heating_zones(request: Request) -> Response:
    """Return materialized independent zone routes for editor AUTO mode."""
    try:
        require_loopback_request(request)
        raw_body = await _read_request(request)
        payload = json.loads(raw_body)
        boundary = payload.get("boundary", {}).get("points", [])
        boundary_points = [(int(point["x_mm"]), int(point["y_mm"])) for point in boundary]
        result = select_layout(
            boundary_points,
            mode=str(payload.get("mode", "AUTO")),
            maximum_circuit_length_mm=int(payload.get("maximum_circuit_length_mm", 90_000)),
            spacing_mm=int(payload.get("spacing_mm", 200)),
            wall_offset_mm=int(payload.get("wall_offset_mm", 100)),
            bend_radius_mm=int(payload.get("turn_radius_mm", 80)),
            maximum_zones=int(payload.get("maximum_zones", 3)),
            preferred_exit_mm=(
                (int(payload["preferred_exit_mm"][0]), int(payload["preferred_exit_mm"][1]))
                if isinstance(payload.get("preferred_exit_mm"), list) and len(payload["preferred_exit_mm"]) == 2
                else None
            ),
            preferred_exit_segment=(
                ((int(payload["preferred_exit_segment_mm"][0][0]), int(payload["preferred_exit_segment_mm"][0][1])), (int(payload["preferred_exit_segment_mm"][1][0]), int(payload["preferred_exit_segment_mm"][1][1])))
                if isinstance(payload.get("preferred_exit_segment_mm"), list) and len(payload["preferred_exit_segment_mm"]) == 2 and all(isinstance(p, list) and len(p) == 2 for p in payload["preferred_exit_segment_mm"])
                else None
            ),
        )
        result["preferred_exit_mm"] = payload.get("preferred_exit_mm")
        result["preferred_exit_status"] = "USER_SELECTED_GEOMETRIC_POINT_UNVERIFIED" if payload.get("preferred_exit_mm") else "NOT_SET"
        if payload.get("preferred_exit_segment_mm"):
            result["preferred_exit_status"] = "USER_SELECTED_OPENING_SEGMENT_UNVERIFIED"
        if result.get("routes"):
            # The editor consumes a candidate object.  Do not point it back
            # at the response itself: that creates a circular JSON graph and
            # turns valid AUTO responses into a misleading 422.
            result["recommended"] = {
                "strategy": result.get("strategy"),
                "strategy_reason": result.get("strategy_reason"),
                "routes": result.get("routes", []),
                "rejected_candidates": result.get("rejected_candidates", []),
            }
        result["project_id"] = payload.get("project_id", "Test_01")
        result["room_id"] = payload.get("room_id", "unknown")
        result["requested_mode"] = str(payload.get("mode", "AUTO")).upper()
        content = json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return Response(content=content, media_type="application/json")
    except HTTPException:
        raise
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise _error(422, "floor_heating_zone_request_invalid", "Zone preview request failed validation.") from error
    except Exception as error:
        raise _error(500, "floor_heating_zone_preview_failed", "Zone preview failed.") from error


@auto_zone_router.post("/building-preview", include_in_schema=False)
async def preview_floor_heating_building(request: Request) -> Response:
    """Route selected room circuits toward explicit doors/corridor geometry."""
    try:
        require_loopback_request(request)
        payload = json.loads(await _read_request(request))
        result = route_building_system(
            payload.get("circuits", []),
            openings=payload.get("openings", {}),
            corridor_polygons=payload.get("corridor_polygons", {}),
            vertical_transit_mm=payload.get("vertical_transit_mm", {}),
        )
        result["project_id"] = payload.get("project_id", "Test_01")
        result["requested_mode"] = "BUILDING_TRANSIT_PREVIEW"
        return Response(content=json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8"), media_type="application/json")
    except HTTPException:
        raise
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise _error(422, "floor_heating_building_request_invalid", "Building routing request failed validation.") from error
    except Exception as error:
        raise _error(500, "floor_heating_building_preview_failed", "Building routing preview failed.") from error


__all__ = ["router", "auto_zone_router"]

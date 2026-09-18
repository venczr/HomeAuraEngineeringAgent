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


MAX_FLOOR_HEATING_COVERAGE_PAYLOAD_BYTES = 2 * 1024 * 1024

router = APIRouter(
    prefix="/api/v1/engineering/floor-heating",
    tags=["floor-heating-coverage-preview"],
)


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


__all__ = ["router"]

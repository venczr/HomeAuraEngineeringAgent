from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from agent.floor_heating_engine import calculate_floor_heating
from agent.floor_heating_models import FloorHeatingRequest, FloorHeatingResult
from agent.ifc_space_preview_api import require_loopback_request
from agent.project_models import ProjectJsonError


MAX_FLOOR_HEATING_PAYLOAD_BYTES = 2 * 1024 * 1024

router = APIRouter(
    prefix="/api/v1/engineering/floor-heating",
    tags=["floor-heating-preview"],
)


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


async def _read_request(request: Request) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_FLOOR_HEATING_PAYLOAD_BYTES:
            raise _error(
                413,
                "floor_heating_payload_too_large",
                "Floor-heating preview body is too large.",
            )
    if not body.lstrip().startswith(b"{"):
        raise _error(
            400,
            "floor_heating_payload_invalid",
            "Floor-heating preview body must be an object.",
        )
    return bytes(body)


@router.post(
    "/preview",
    response_model=FloorHeatingResult,
)
async def preview_floor_heating(request: Request) -> FloorHeatingResult:
    try:
        require_loopback_request(request)
        raw_body = await _read_request(request)
        payload = FloorHeatingRequest.model_validate_json(raw_body)
        return calculate_floor_heating(payload)
    except HTTPException:
        raise
    except ProjectJsonError as error:
        raise _error(
            400,
            "floor_heating_payload_invalid",
            "Floor-heating preview JSON is invalid.",
        ) from error
    except ValueError as error:
        raise _error(
            422,
            "floor_heating_request_invalid",
            "Floor-heating preview request failed validation.",
        ) from error
    except Exception as error:
        raise _error(
            500,
            "floor_heating_preview_failed",
            "Floor-heating preview failed.",
        ) from error

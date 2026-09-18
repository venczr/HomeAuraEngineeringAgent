from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from agent.floor_heating_engine import calculate_floor_heating
from agent.floor_heating_models import FloorHeatingRequest
from agent.floor_heating_system_graph import (
    FloorHeatingProjectPreview,
    build_floor_heating_project_preview,
)
from agent.ifc_space_preview_api import require_loopback_request
from agent.project_models import ProjectJsonError


MAX_FLOOR_HEATING_PROJECT_PREVIEW_BYTES = 2 * 1024 * 1024

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/engineering/floor-heating",
    tags=["floor-heating-project-preview"],
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
        if len(body) > MAX_FLOOR_HEATING_PROJECT_PREVIEW_BYTES:
            raise _error(
                413,
                "floor_heating_project_payload_too_large",
                "Floor-heating project preview body is too large.",
            )
    if not body.lstrip().startswith(b"{"):
        raise _error(
            400,
            "floor_heating_project_payload_invalid",
            "Floor-heating project preview body must be an object.",
        )
    return bytes(body)


@router.post(
    "/system-preview",
    response_model=FloorHeatingProjectPreview,
)
async def preview_floor_heating_system(
    project_id: str,
    request: Request,
) -> Response:
    try:
        require_loopback_request(request)
        raw_body = await _read_request(request)
        floor_request = FloorHeatingRequest.model_validate_json(raw_body)
        if floor_request.project_id != project_id:
            raise _error(
                422,
                "floor_heating_project_id_mismatch",
                "Path project_id does not match the request project_id.",
            )
        result = calculate_floor_heating(floor_request)
        preview = build_floor_heating_project_preview(
            result,
            collector_point=floor_request.collector_point,
        )
        content = json.dumps(
            preview.model_dump(mode="json"),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return Response(content=content, media_type="application/json")
    except HTTPException:
        raise
    except ProjectJsonError as error:
        raise _error(
            400,
            "floor_heating_project_payload_invalid",
            "Floor-heating project preview JSON is invalid.",
        ) from error
    except ValueError as error:
        raise _error(
            422,
            "floor_heating_project_request_invalid",
            "Floor-heating project preview request failed validation.",
        ) from error
    except Exception as error:
        raise _error(
            500,
            "floor_heating_project_preview_failed",
            "Floor-heating project preview failed.",
        ) from error


__all__ = ["router"]

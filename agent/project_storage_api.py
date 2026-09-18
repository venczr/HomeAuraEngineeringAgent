from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from agent.project_preview_api import (
    parse_project_preview_request,
    require_project_loopback_request,
)
from agent.project_storage import (
    ProjectStorageError,
    ProjectStore,
)


router = APIRouter(
    prefix="/api/v1/projects",
    tags=["project-storage"],
)
project_store = ProjectStore()

ERROR_STATUS = {
    "project_name_invalid": 400,
    "project_path_escape": 400,
    "project_json_invalid": 400,
    "project_payload_too_large": 413,
    "project_not_found": 404,
    "project_identity_conflict": 409,
    "project_revision_conflict": 409,
    "project_history_conflict": 409,
    "project_storage_corrupt": 500,
    "project_storage_io": 500,
}


def _storage_http_error(error: ProjectStorageError) -> HTTPException:
    return HTTPException(
        status_code=ERROR_STATUS[error.code],
        detail={
            "code": error.code,
            "message": error.message,
        },
    )


@router.post("/{project_name}/canonical")
async def save_canonical_project(
    project_name: str,
    request: Request,
) -> JSONResponse:
    require_project_loopback_request(request)
    project = await parse_project_preview_request(request)
    try:
        record = project_store.save_current_revision(
            project_name,
            project,
        )
    except ProjectStorageError as error:
        raise _storage_http_error(error) from error
    return JSONResponse(
        status_code=201 if record.created else 200,
        content={
            "project_id": str(record.project_id),
            "revision": record.revision,
            "sha256": record.sha256,
        },
    )


@router.get("/{project_name}/canonical")
def get_canonical_project(
    project_name: str,
    request: Request,
) -> Response:
    require_project_loopback_request(request)
    try:
        record = project_store.load_current(project_name)
    except ProjectStorageError as error:
        raise _storage_http_error(error) from error
    return Response(
        content=record.canonical_bytes,
        media_type="application/json",
        status_code=200,
    )

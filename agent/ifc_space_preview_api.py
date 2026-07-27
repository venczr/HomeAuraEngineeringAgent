from __future__ import annotations

import ipaddress
import re

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from agent.ifc_space_importer import (
    IfcOpenShellUnavailable,
    IfcSpaceImportError,
    run_import,
)
from agent.ifc_space_models import (
    IfcSpaceGeometry,
    IfcSpaceImportSummary,
)


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
PROJECTS_DIRECTORY = ROOT_DIRECTORY / "projects"

MAX_PROJECT_ID_LENGTH = 128
MAX_RELATIVE_PATH_LENGTH = 512
MAX_IFC_FILE_BYTES = 50 * 1024 * 1024
MAX_ROOMS_FILE_BYTES = 10 * 1024 * 1024
WINDOWS_ABSOLUTE_PATH = re.compile(
    r"(?i)(?:[A-Z]:[\\/]|\\\\)"
)

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["ifc-space-preview"],
)


class IfcSpacePreviewRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    ifc_relative_path: str = Field(
        min_length=1,
        max_length=MAX_RELATIVE_PATH_LENGTH,
    )
    rooms_relative_path: str = Field(
        min_length=1,
        max_length=MAX_RELATIVE_PATH_LENGTH,
    )


class IfcSpacePreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    project_id: str
    ifc_relative_path: str
    rooms_relative_path: str
    IfcSpaceImportReport: IfcSpaceImportSummary
    IfcSpaceGeometryCandidates: list[IfcSpaceGeometry] = Field(
        default_factory=list
    )


def _error(
    status_code: int,
    code: str,
    message: str,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
        },
    )


def _is_loopback_host(host: str | None) -> bool:
    if not isinstance(host, str) or not host:
        return False
    try:
        address = ipaddress.ip_address(
            host.split("%", maxsplit=1)[0]
        )
    except ValueError:
        return False
    if address.is_loopback:
        return True
    mapped = getattr(address, "ipv4_mapped", None)
    return bool(mapped and mapped.is_loopback)


def require_loopback_request(request: Request) -> None:
    client = request.client
    if client is None or not _is_loopback_host(client.host):
        raise _error(
            403,
            "local_access_required",
            "IfcSpace preview доступен только через loopback.",
        )


def _resolve_strict(path: Path) -> Path:
    return path.resolve(strict=True)


def _is_within(
    candidate: Path,
    root: Path,
) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def resolve_registered_project_directory(
    project_id: str,
) -> Path:
    if (
        not project_id
        or len(project_id) > MAX_PROJECT_ID_LENGTH
        or project_id in {".", ".."}
        or Path(project_id).name != project_id
        or Path(project_id).drive
        or Path(project_id).anchor
    ):
        raise _error(
            400,
            "invalid_project_id",
            "Некорректный project_id.",
        )

    try:
        projects_root = _resolve_strict(PROJECTS_DIRECTORY)
    except (FileNotFoundError, OSError) as error:
        raise _error(
            503,
            "project_registry_unavailable",
            "Каталог зарегистрированных проектов недоступен.",
        ) from error

    try:
        project_directory = _resolve_strict(
            PROJECTS_DIRECTORY / project_id
        )
    except (FileNotFoundError, OSError) as error:
        raise _error(
            404,
            "unknown_project_id",
            "Зарегистрированный проект не найден.",
        ) from error

    if (
        not _is_within(project_directory, projects_root)
        or not project_directory.is_dir()
    ):
        raise _error(
            404,
            "unknown_project_id",
            "Зарегистрированный проект не найден.",
        )
    return project_directory


def _relative_path(
    value: str,
) -> Path:
    if "\x00" in value or value.casefold().startswith("file:"):
        raise _error(
            400,
            "invalid_relative_path",
            "Путь должен быть относительным и безопасным.",
        )

    path = Path(value)
    if (
        value in {".", ".."}
        or path.is_absolute()
        or bool(path.drive)
        or bool(path.anchor)
        or ".." in path.parts
    ):
        raise _error(
            400,
            "invalid_relative_path",
            "Путь должен быть относительным и безопасным.",
        )
    return path


def resolve_project_file(
    project_directory: Path,
    relative_value: str,
    *,
    expected_suffix: str,
    maximum_bytes: int,
) -> tuple[Path, str]:
    relative_path = _relative_path(relative_value)
    if relative_path.suffix.casefold() != expected_suffix:
        raise _error(
            400,
            "invalid_file_extension",
            f"Ожидается файл {expected_suffix}.",
        )

    try:
        project_root = _resolve_strict(project_directory)
    except (FileNotFoundError, OSError) as error:
        raise _error(
            404,
            "unknown_project_id",
            "Зарегистрированный проект не найден.",
        ) from error
    try:
        resolved = _resolve_strict(
            project_directory / relative_path
        )
    except FileNotFoundError as error:
        raise _error(
            404,
            "input_file_not_found",
            "Входной файл не найден.",
        ) from error
    except OSError as error:
        raise _error(
            400,
            "invalid_relative_path",
            "Не удалось безопасно разрешить входной путь.",
        ) from error

    if not _is_within(resolved, project_root):
        raise _error(
            400,
            "path_outside_project",
            "Входной путь выходит за каталог проекта.",
        )
    if not resolved.is_file():
        raise _error(
            400,
            "input_not_file",
            "Входной путь должен указывать на файл.",
        )

    try:
        size = resolved.stat().st_size
    except OSError as error:
        raise _error(
            400,
            "input_file_unreadable",
            "Не удалось прочитать метаданные входного файла.",
        ) from error
    if size <= 0:
        raise _error(
            422,
            "input_file_empty",
            "Входной файл пуст.",
        )
    if size > maximum_bytes:
        raise _error(
            413,
            "input_file_too_large",
            "Входной файл превышает допустимый размер.",
        )

    return resolved, relative_path.as_posix()


def _safe_preview_response(
    project_id: str,
    ifc_relative_path: str,
    rooms_relative_path: str,
    outcome: Any,
) -> IfcSpacePreviewResponse:
    summary = outcome.summary.model_copy(deep=True)
    summary.InputIfcPath = ifc_relative_path
    summary.InputRoomsPath = rooms_relative_path
    summary.OutputPath = None

    candidates: list[IfcSpaceGeometry] = []
    for source in outcome.matched_geometries:
        candidate = source.model_copy(deep=True)
        candidate.IfcFile.Path = ifc_relative_path
        candidates.append(candidate)

    return IfcSpacePreviewResponse(
        project_id=project_id,
        ifc_relative_path=ifc_relative_path,
        rooms_relative_path=rooms_relative_path,
        IfcSpaceImportReport=summary,
        IfcSpaceGeometryCandidates=candidates,
    )


def _response_strings(value: Any):
    if isinstance(value, BaseModel):
        yield from _response_strings(
            value.model_dump(mode="json")
        )
    elif isinstance(value, dict):
        for item in value.values():
            yield from _response_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _response_strings(item)
    elif isinstance(value, str):
        yield value


def _ensure_safe_response(
    response: IfcSpacePreviewResponse,
    *,
    forbidden_roots: tuple[Path, ...],
) -> IfcSpacePreviewResponse:
    roots = tuple(
        str(root).casefold()
        for root in forbidden_roots
        if str(root)
    )
    for text in _response_strings(response):
        folded = text.casefold()
        if (
            "file://" in folded
            or "traceback" in folded
            or WINDOWS_ABSOLUTE_PATH.search(text)
            or any(root in folded for root in roots)
        ):
            raise _error(
                500,
                "unsafe_preview_response",
                "IfcSpace preview сформировал небезопасный ответ.",
            )
    return response


@router.post(
    "/{project_id}/rooms/ifc-space/preview",
    response_model=IfcSpacePreviewResponse,
)
def preview_ifc_space(
    project_id: str,
    payload: IfcSpacePreviewRequest,
    _local_request: None = Depends(require_loopback_request),
) -> IfcSpacePreviewResponse:
    project_directory = resolve_registered_project_directory(
        project_id
    )
    ifc_path, ifc_relative_path = resolve_project_file(
        project_directory,
        payload.ifc_relative_path,
        expected_suffix=".ifc",
        maximum_bytes=MAX_IFC_FILE_BYTES,
    )
    rooms_path, rooms_relative_path = resolve_project_file(
        project_directory,
        payload.rooms_relative_path,
        expected_suffix=".json",
        maximum_bytes=MAX_ROOMS_FILE_BYTES,
    )

    try:
        outcome = run_import(
            ifc_path,
            rooms_path,
            analyze_only=True,
        )
    except IfcOpenShellUnavailable as error:
        raise _error(
            503,
            "ifcopenshell_unavailable",
            "IfcSpace preview временно недоступен.",
        ) from error
    except IfcSpaceImportError as error:
        raise _error(
            422,
            "ifc_preview_invalid",
            "IFC или rooms JSON не прошли проверку.",
        ) from error
    except (OSError, ValueError) as error:
        raise _error(
            422,
            "ifc_preview_invalid",
            "IFC или rooms JSON не прошли проверку.",
        ) from error
    except Exception as error:
        raise _error(
            500,
            "ifc_preview_failed",
            "Не удалось выполнить IfcSpace preview.",
        ) from error

    response = _safe_preview_response(
        project_id,
        ifc_relative_path,
        rooms_relative_path,
        outcome,
    )
    return _ensure_safe_response(
        response,
        forbidden_roots=(project_directory,),
    )

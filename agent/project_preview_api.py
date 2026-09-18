from __future__ import annotations

import ipaddress

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import ValidationError

from agent import domain_adapter
from agent.project_foundation import (
    build_canonical_project_preview,
    canonical_json_bytes,
)
from agent.project_models import (
    CanonicalProjectModel,
    DomainProjectPreviewRequest,
    ProjectJsonError,
    _load_strict_project_json,
)


MAX_PROJECT_PAYLOAD_BYTES = 10 * 1024 * 1024

LOOPBACK_REQUIRED_MESSAGE = (
    "Project preview доступен только через loopback."
)
CONTENT_TYPE_INVALID_MESSAGE = (
    "Project preview принимает только application/json."
)
PAYLOAD_INVALID_MESSAGE = (
    "Некорректное тело Project preview."
)
PAYLOAD_TOO_LARGE_MESSAGE = (
    "Тело Project preview превышает 10 MiB."
)
MODEL_INVALID_MESSAGE = (
    "Canonical project не прошёл проверку."
)
PREVIEW_FAILED_MESSAGE = (
    "Не удалось выполнить Project preview."
)

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["project-preview"],
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


def _raw_header_values(
    request: Request,
    header_name: bytes,
) -> list[bytes]:
    values: list[bytes] = []
    for name, value in request.scope.get("headers", []):
        if (
            isinstance(name, bytes)
            and isinstance(value, bytes)
            and name.lower() == header_name
        ):
            values.append(value)
    return values


def _is_loopback_host(host: Any) -> bool:
    if not isinstance(host, str) or not host:
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if address.is_loopback:
        return True
    mapped = getattr(address, "ipv4_mapped", None)
    return bool(mapped and mapped.is_loopback)


def _raise_loopback_required() -> None:
    raise _error(
        403,
        "loopback_required",
        LOOPBACK_REQUIRED_MESSAGE,
    )


def _validate_port(port: bytes | None) -> None:
    if port is None:
        return
    if (
        not port
        or any(
            byte_value < ord("0") or byte_value > ord("9")
            for byte_value in port
        )
    ):
        _raise_loopback_required()
    normalized = port.lstrip(b"0") or b"0"
    if (
        len(normalized) > 5
        or int(normalized) < 1
        or int(normalized) > 65535
    ):
        _raise_loopback_required()


def _validate_local_host(request: Request) -> None:
    values = _raw_header_values(request, b"host")
    if len(values) != 1:
        _raise_loopback_required()

    raw_host = values[0]
    if (
        not raw_host
        or any(
            byte_value < 33 or byte_value > 126
            for byte_value in raw_host
        )
        or b"," in raw_host
        or b"@" in raw_host
    ):
        _raise_loopback_required()

    port: bytes | None = None
    if raw_host.startswith(b"["):
        if not raw_host.startswith(b"[::1]"):
            _raise_loopback_required()
        remainder = raw_host[len(b"[::1]") :]
        if remainder:
            if not remainder.startswith(b":"):
                _raise_loopback_required()
            port = remainder[1:]
    else:
        if raw_host.count(b":") > 1:
            _raise_loopback_required()
        if b":" in raw_host:
            host, port = raw_host.split(b":", maxsplit=1)
        else:
            host = raw_host
        if host.lower() not in {
            b"localhost",
            b"127.0.0.1",
        }:
            _raise_loopback_required()

    _validate_port(port)


def require_project_loopback_request(request: Request) -> None:
    client = request.client
    if client is None or not _is_loopback_host(client.host):
        _raise_loopback_required()
    _validate_local_host(request)


def _validate_content_type(request: Request) -> None:
    values = _raw_header_values(request, b"content-type")
    if len(values) != 1:
        raise _error(
            415,
            "project_content_type_invalid",
            CONTENT_TYPE_INVALID_MESSAGE,
        )

    try:
        content_type = values[0].decode("ascii")
    except UnicodeDecodeError as error:
        raise _error(
            415,
            "project_content_type_invalid",
            CONTENT_TYPE_INVALID_MESSAGE,
        ) from error

    parts = content_type.split(";")
    if parts[0].strip().casefold() != "application/json":
        raise _error(
            415,
            "project_content_type_invalid",
            CONTENT_TYPE_INVALID_MESSAGE,
        )

    if len(parts) == 1:
        return
    if len(parts) != 2:
        raise _error(
            415,
            "project_content_type_invalid",
            CONTENT_TYPE_INVALID_MESSAGE,
        )

    parameter = parts[1].strip()
    name, separator, value = parameter.partition("=")
    if (
        separator != "="
        or name.strip().casefold() != "charset"
        or value.strip().casefold() != "utf-8"
    ):
        raise _error(
            415,
            "project_content_type_invalid",
            CONTENT_TYPE_INVALID_MESSAGE,
        )


def _validate_content_length(request: Request) -> int | None:
    values = _raw_header_values(request, b"content-length")
    if len(values) > 1:
        raise _error(
            400,
            "project_payload_invalid",
            PAYLOAD_INVALID_MESSAGE,
        )
    if not values:
        return None

    raw_value = values[0]
    if (
        not raw_value
        or any(
            byte_value < ord("0") or byte_value > ord("9")
            for byte_value in raw_value
        )
    ):
        raise _error(
            400,
            "project_payload_invalid",
            PAYLOAD_INVALID_MESSAGE,
        )

    normalized = raw_value.lstrip(b"0") or b"0"
    maximum = str(MAX_PROJECT_PAYLOAD_BYTES).encode("ascii")
    if (
        len(normalized) > len(maximum)
        or (
            len(normalized) == len(maximum)
            and normalized > maximum
        )
    ):
        raise _error(
            413,
            "project_payload_too_large",
            PAYLOAD_TOO_LARGE_MESSAGE,
        )
    return int(normalized)


def _has_object_root(raw_payload: bytes) -> bool:
    return raw_payload.lstrip().startswith(b"{")


async def parse_project_preview_request(
    request: Request,
) -> CanonicalProjectModel:
    _validate_content_type(request)
    _validate_content_length(request)

    raw_payload = bytearray()
    async for chunk in request.stream():
        raw_payload.extend(chunk)
        if len(raw_payload) > MAX_PROJECT_PAYLOAD_BYTES:
            raise _error(
                413,
                "project_payload_too_large",
                PAYLOAD_TOO_LARGE_MESSAGE,
            )

    raw_bytes = bytes(raw_payload)
    if not _has_object_root(raw_bytes):
        raise _error(
            400,
            "project_payload_invalid",
            PAYLOAD_INVALID_MESSAGE,
        )

    try:
        parsed = _load_strict_project_json(raw_bytes)
    except ProjectJsonError as error:
        raise _error(
            400,
            "project_payload_invalid",
            PAYLOAD_INVALID_MESSAGE,
        ) from error

    if not isinstance(parsed, dict):
        raise _error(
            400,
            "project_payload_invalid",
            PAYLOAD_INVALID_MESSAGE,
        )

    canonical_markers = {
        "revision",
        "status",
        "domain",
        "seed",
        "sheet_manifest",
    }
    domain_candidate = (
        "rooms_payload" in parsed
        or (
            "project_id" in parsed
            and not canonical_markers.intersection(parsed)
        )
    )
    if domain_candidate:
        try:
            domain_request = DomainProjectPreviewRequest.model_validate_json(
                raw_bytes
            )
            domain = domain_adapter.adapt_rooms_payload(
                domain_request.rooms_payload,
                project_id=domain_request.project_id,
            )
            return build_canonical_project_preview(
                domain,
                domain_request.source_points,
                sheet_manifest=domain_request.sheet_manifest,
                created_at=domain_request.created_at,
                revision=domain_request.revision,
                status=domain_request.status,
            )
        except ValidationError as error:
            raise _error(
                422,
                "project_domain_request_invalid",
                MODEL_INVALID_MESSAGE,
            ) from error

    try:
        return CanonicalProjectModel.model_validate_json(raw_bytes)
    except ValidationError as error:
        raise _error(
            422,
            "project_model_invalid",
            MODEL_INVALID_MESSAGE,
        ) from error


@router.post(
    "/canonical/preview",
    response_model=CanonicalProjectModel,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": (
                        CanonicalProjectModel.model_json_schema()
                    ),
                },
            },
        },
    },
)
async def preview_canonical_project(
    request: Request,
) -> Response:
    try:
        require_project_loopback_request(request)
        project = await parse_project_preview_request(request)
        return Response(
            content=canonical_json_bytes(project),
            media_type="application/json",
            status_code=200,
        )
    except HTTPException:
        raise
    except domain_adapter.DomainAdaptationError as error:
        if error.code == "unsafe_identity_path":
            raise _error(
                422,
                "unsafe_identity_path",
                "DOMAIN identity содержит недопустимое значение.",
            ) from error
        raise _error(
            422,
            "project_domain_payload_invalid",
            "Rooms payload не прошёл DOMAIN-проверку.",
        ) from error
    except Exception as error:
        raise _error(
            500,
            "project_preview_failed",
            PREVIEW_FAILED_MESSAGE,
        ) from error

from __future__ import annotations

import json

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agent.domain_adapter import (
    DomainAdaptationError,
    adapt_rooms_payload,
)
from agent.domain_models import DomainDocument
from agent.ifc_space_preview_api import require_loopback_request


MAX_DOMAIN_PAYLOAD_BYTES = 10 * 1024 * 1024

router = APIRouter(
    prefix="/api/v1/rooms",
    tags=["domain-preview"],
)


class DomainPreviewRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    project_id: str = Field(
        min_length=1,
        max_length=128,
        strict=True,
    )
    rooms_payload: dict[str, Any]


class _InvalidJsonValue(ValueError):
    pass


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


def require_domain_loopback_request(request: Request) -> None:
    try:
        require_loopback_request(request)
    except HTTPException as error:
        raise _error(
            403,
            "loopback_required",
            "DOMAIN preview доступен только через loopback.",
        ) from error
    _validate_local_host(request)


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


def _raise_loopback_required() -> None:
    raise _error(
        403,
        "loopback_required",
        "DOMAIN preview доступен только через loopback.",
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


def _validate_content_type(request: Request) -> None:
    values = _raw_header_values(request, b"content-type")
    if len(values) != 1:
        raise _error(
            415,
            "domain_content_type_invalid",
            "DOMAIN preview принимает только application/json.",
        )

    try:
        content_type = values[0].decode("ascii")
    except UnicodeDecodeError as error:
        raise _error(
            415,
            "domain_content_type_invalid",
            "DOMAIN preview принимает только application/json.",
        ) from error

    parts = content_type.split(";")
    if parts[0].strip().casefold() != "application/json":
        raise _error(
            415,
            "domain_content_type_invalid",
            "DOMAIN preview принимает только application/json.",
        )

    if len(parts) == 1:
        return
    if len(parts) != 2:
        raise _error(
            415,
            "domain_content_type_invalid",
            "DOMAIN preview принимает только application/json.",
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
            "domain_content_type_invalid",
            "DOMAIN preview принимает только application/json.",
        )


def _validate_content_length(request: Request) -> int | None:
    values = _raw_header_values(request, b"content-length")
    if len(values) > 1:
        raise _error(
            400,
            "domain_payload_invalid",
            "Некорректное тело DOMAIN preview.",
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
            "domain_payload_invalid",
            "Некорректное тело DOMAIN preview.",
        )

    normalized = raw_value.lstrip(b"0") or b"0"
    maximum = str(MAX_DOMAIN_PAYLOAD_BYTES).encode("ascii")
    if (
        len(normalized) > len(maximum)
        or (
            len(normalized) == len(maximum)
            and normalized > maximum
        )
    ):
        raise _error(
            413,
            "domain_payload_too_large",
            "Тело DOMAIN preview превышает 10 MiB.",
        )
    return int(normalized)


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidJsonValue("duplicate JSON key")
        result[key] = value
    return result


def _reject_non_finite(_value: str) -> None:
    raise _InvalidJsonValue("non-finite JSON number")


async def parse_domain_preview_request(
    request: Request,
) -> DomainPreviewRequest:
    _validate_content_type(request)
    _validate_content_length(request)

    raw_payload = bytearray()
    async for chunk in request.stream():
        raw_payload.extend(chunk)
        if len(raw_payload) > MAX_DOMAIN_PAYLOAD_BYTES:
            raise _error(
                413,
                "domain_payload_too_large",
                "Тело DOMAIN preview превышает 10 MiB.",
            )

    try:
        text = bytes(raw_payload).decode("utf-8", errors="strict")
        parsed = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except (
        UnicodeDecodeError,
        ValueError,
        RecursionError,
    ) as error:
        raise _error(
            400,
            "domain_payload_invalid",
            "Некорректное тело DOMAIN preview.",
        ) from error

    if not isinstance(parsed, dict):
        raise _error(
            400,
            "domain_payload_invalid",
            "Некорректное тело DOMAIN preview.",
        )

    try:
        return DomainPreviewRequest.model_validate(parsed)
    except ValidationError as error:
        raise _error(
            422,
            "domain_request_invalid",
            "Некорректный запрос DOMAIN preview.",
        ) from error


@router.post(
    "/domain/preview",
    response_model=DomainDocument,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": (
                        DomainPreviewRequest.model_json_schema()
                    ),
                },
            },
        },
    },
)
async def preview_domain_rooms(
    request: Request,
) -> DomainDocument:
    try:
        require_domain_loopback_request(request)
        payload = await parse_domain_preview_request(request)
        return adapt_rooms_payload(
            payload.rooms_payload,
            project_id=payload.project_id,
        )
    except HTTPException:
        raise
    except DomainAdaptationError as error:
        if error.code == "unsafe_identity_path":
            raise _error(
                422,
                "unsafe_identity_path",
                "DOMAIN identity содержит недопустимое значение.",
            ) from error
        raise _error(
            422,
            "domain_rooms_payload_invalid",
            "Rooms payload не прошёл DOMAIN-проверку.",
        ) from error
    except Exception as error:
        raise _error(
            500,
            "domain_preview_failed",
            "Не удалось выполнить DOMAIN preview.",
        ) from error

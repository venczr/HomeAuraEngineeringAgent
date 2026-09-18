from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.responses import JSONResponse
from starlette.routing import Match
from starlette.types import Message, Receive, Scope, Send

from agent.project_preview_api import MAX_PROJECT_PAYLOAD_BYTES


MAX_REQUEST_BODY_BYTES = MAX_PROJECT_PAYLOAD_BYTES
PROTECTED_POST_ROUTES = frozenset(
    {
        "/api/v1/projects/{project_name}/snapshot",
        "/api/v1/projects/{project_name}/rooms",
        (
            "/api/v1/projects/{project_id}/rooms/"
            "ifc-space/preview"
        ),
        "/api/v1/projects/{project_name}/canonical",
    }
)

INVALID_BODY_DETAIL = "Некорректная длина тела запроса."
BODY_TOO_LARGE_DETAIL = "Тело запроса превышает 10 MiB."

ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class _BodyLimitExceeded(Exception):
    pass


class _InvalidContentLength(Exception):
    pass


def _content_length(scope: Scope) -> int | None:
    values = [
        value
        for name, value in scope.get("headers", [])
        if isinstance(name, bytes)
        and isinstance(value, bytes)
        and name.lower() == b"content-length"
    ]
    if len(values) > 1:
        raise _InvalidContentLength
    if not values:
        return None

    raw_value = values[0]
    if not raw_value or any(
        byte_value < ord("0") or byte_value > ord("9")
        for byte_value in raw_value
    ):
        raise _InvalidContentLength

    normalized = raw_value.lstrip(b"0") or b"0"
    maximum = str(MAX_REQUEST_BODY_BYTES).encode("ascii")
    if len(normalized) > len(maximum) or (
        len(normalized) == len(maximum)
        and normalized > maximum
    ):
        raise _BodyLimitExceeded
    return int(normalized)


def _is_protected_route(scope: Scope, route_source: Any) -> bool:
    if scope.get("type") != "http" or scope.get("method") != "POST":
        return False

    pending = [route_source]
    visited: set[int] = set()
    while pending:
        candidate = pending.pop()
        candidate_id = id(candidate)
        if candidate_id in visited:
            continue
        visited.add(candidate_id)

        nested_routes = getattr(candidate, "routes", None)
        if nested_routes is not None:
            pending.extend(nested_routes)

        original_router = getattr(candidate, "original_router", None)
        if original_router is not None:
            pending.append(original_router)

        route = candidate
        if (
            getattr(route, "path", None) in PROTECTED_POST_ROUTES
            and route.matches(scope)[0] is Match.FULL
        ):
            return True
    return False


async def _send_error(
    scope: Scope,
    send: Send,
    *,
    status_code: int,
    code: str,
    message: str,
) -> None:
    response = JSONResponse(
        status_code=status_code,
        content={
            "detail": {
                "code": code,
                "message": message,
            }
        },
    )
    await response(scope, receive=None, send=send)


class BoundedRequestBodyMiddleware:
    """Bound selected project writes before downstream body parsing."""

    def __init__(self, app: ASGIApp, *, route_source: Any) -> None:
        self.app = app
        self.route_source = route_source

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if not _is_protected_route(scope, self.route_source):
            await self.app(scope, receive, send)
            return

        try:
            _content_length(scope)
        except _InvalidContentLength:
            await _send_error(
                scope,
                send,
                status_code=400,
                code="project_payload_invalid",
                message=INVALID_BODY_DETAIL,
            )
            return
        except _BodyLimitExceeded:
            await _send_error(
                scope,
                send,
                status_code=413,
                code="project_payload_too_large",
                message=BODY_TOO_LARGE_DETAIL,
            )
            return

        messages: list[Message] = []
        total = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.disconnect":
                break
            if message["type"] != "http.request":
                continue

            total += len(message.get("body", b""))
            if total > MAX_REQUEST_BODY_BYTES:
                await _send_error(
                    scope,
                    send,
                    status_code=413,
                    code="project_payload_too_large",
                    message=BODY_TOO_LARGE_DETAIL,
                )
                return
            if not message.get("more_body", False):
                break

        index = 0

        async def replay_receive() -> Message:
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return {"type": "http.disconnect"}

        await self.app(scope, replay_receive, send)

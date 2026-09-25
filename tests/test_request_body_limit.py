from __future__ import annotations

import asyncio
import json

from typing import Any

import pytest

from starlette.routing import Route
from starlette.testclient import TestClient

from agent.api import app
from agent.request_body_limit import (
    BoundedRequestBodyMiddleware,
    MAX_REQUEST_BODY_BYTES,
    PROTECTED_POST_ROUTES,
)


async def _endpoint(_request: Any) -> None:
    return None


class _RouteSource:
    def __init__(self) -> None:
        self.routes = [
            Route(path, _endpoint, methods=["POST"])
            for path in PROTECTED_POST_ROUTES
        ]


def test_protected_post_routes_exist_in_live_application() -> None:
    live_post_routes = {
        path
        for path, operations in app.openapi()["paths"].items()
        if "post" in operations
    }

    assert len(PROTECTED_POST_ROUTES) == 4
    assert PROTECTED_POST_ROUTES <= live_post_routes


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/projects/SafeProject/canonical",
        "/api/v1/projects/SafeProject/rooms",
        (
            "/api/v1/projects/project-id/rooms/"
            "ifc-space/preview"
        ),
    ],
)
def test_live_application_rejects_oversized_protected_routes(
    path: str,
) -> None:
    with TestClient(app) as client:
        response = client.post(
            path,
            content=b"x" * (MAX_REQUEST_BODY_BYTES + 1),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == (
        "project_payload_too_large"
    )


def _scope(
    path: str,
    *,
    method: str = "POST",
    headers: list[tuple[bytes, bytes]] | None = None,
    query_string: bytes = b"",
) -> dict[str, Any]:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string,
        "root_path": "",
        "headers": list(headers or []),
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 80),
    }


def _run(
    path: str,
    chunks: list[bytes],
    *,
    method: str = "POST",
    headers: list[tuple[bytes, bytes]] | None = None,
    inner_error: Exception | None = None,
    query_string: bytes = b"",
) -> tuple[list[dict[str, Any]], bytes]:
    received = bytearray()

    async def inner(scope, receive, send) -> None:
        if inner_error is not None:
            raise inner_error
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                break
            received.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 204})
        await send({"type": "http.response.body", "body": b""})

    messages = [
        {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(chunks) - 1,
        }
        for index, chunk in enumerate(chunks)
    ]
    index = 0

    async def receive() -> dict[str, Any]:
        nonlocal index
        if index < len(messages):
            message = messages[index]
            index += 1
            return message
        return {"type": "http.disconnect"}

    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    middleware = BoundedRequestBodyMiddleware(
        inner,
        route_source=_RouteSource(),
    )
    asyncio.run(
        middleware(
            _scope(
                path,
                method=method,
                headers=headers,
                query_string=query_string,
            ),
            receive,
            send,
        )
    )
    return sent, bytes(received)


def _status(messages: list[dict[str, Any]]) -> int:
    return next(
        message["status"]
        for message in messages
        if message["type"] == "http.response.start"
    )


def _response_json(messages: list[dict[str, Any]]) -> Any:
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return json.loads(body)


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/projects/SafeProject/snapshot",
        "/api/v1/projects/SafeProject/rooms",
        (
            "/api/v1/projects/project-id/rooms/"
            "ifc-space/preview"
        ),
        "/api/v1/projects/SafeProject/canonical",
    ],
)
def test_all_protected_route_templates_are_matched(path: str) -> None:
    sent, received = _run(path, [b"{}"])

    assert _status(sent) == 204
    assert received == b"{}"


def test_exact_limit_passes_and_chunks_are_replayed() -> None:
    body = b"x" * MAX_REQUEST_BODY_BYTES
    chunks = [body[:17], body[17:]]

    sent, received = _run(
        "/api/v1/projects/SafeProject/canonical",
        chunks,
        headers=[
            (
                b"content-length",
                str(MAX_REQUEST_BODY_BYTES).encode("ascii"),
            )
        ],
    )

    assert _status(sent) == 204
    assert received == body


def test_streamed_limit_plus_one_is_rejected_before_downstream() -> None:
    sent, received = _run(
        "/api/v1/projects/SafeProject/rooms",
        [b"x" * MAX_REQUEST_BODY_BYTES, b"y"],
    )

    assert _status(sent) == 413
    assert received == b""
    assert _response_json(sent)["detail"]["code"] == (
        "project_payload_too_large"
    )


@pytest.mark.parametrize(
    "headers,status",
    [
        ([(b"content-length", b"abc")], 400),
        ([(b"content-length", b"1,2")], 400),
        (
            [
                (b"content-length", b"1"),
                (b"content-length", b"1"),
            ],
            400,
        ),
        (
            [
                (
                    b"content-length",
                    str(MAX_REQUEST_BODY_BYTES + 1).encode("ascii"),
                )
            ],
            413,
        ),
        (
            [
                (
                    b"content-length",
                    (b"0" * 20)
                    + str(MAX_REQUEST_BODY_BYTES).encode("ascii"),
                )
            ],
            204,
        ),
    ],
)
def test_content_length_uses_bounded_lexical_validation(
    headers: list[tuple[bytes, bytes]],
    status: int,
) -> None:
    sent, _ = _run(
        "/api/v1/projects/SafeProject/snapshot",
        [b"x"],
        headers=headers,
    )

    assert _status(sent) == status


def test_query_string_does_not_bypass_route_match() -> None:
    sent, _ = _run(
        "/api/v1/projects/SafeProject/canonical",
        [b"x" * (MAX_REQUEST_BODY_BYTES + 1)],
        query_string=b"mode=replace",
    )

    assert _status(sent) == 413


@pytest.mark.parametrize(
    "path,method",
    [
        ("/api/v1/projects/SafeProject/analyze", "POST"),
        ("/api/v1/projects/SafeProject/canonical", "GET"),
        ("/api/v1/projects/SafeProject/canonical/", "POST"),
    ],
)
def test_nonprotected_requests_pass_through(
    path: str,
    method: str,
) -> None:
    sent, received = _run(
        path,
        [b"x" * (MAX_REQUEST_BODY_BYTES + 1)],
        method=method,
    )

    assert _status(sent) == 204
    assert len(received) == MAX_REQUEST_BODY_BYTES + 1


def test_unrelated_downstream_exception_is_not_reshaped() -> None:
    marker = RuntimeError("downstream-marker")

    with pytest.raises(RuntimeError, match="downstream-marker"):
        _run(
            "/api/v1/projects/SafeProject/canonical",
            [b"{}"],
            inner_error=marker,
        )

from __future__ import annotations

import asyncio
import ast
import copy
import hashlib
import importlib
import json
import socket
import subprocess
import unittest

from pathlib import Path
from typing import Any
from unittest.mock import patch

from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

import agent.domain_preview_api as domain_preview_api
from agent.api import app
from agent.domain_adapter import adapt_rooms_payload
from agent.domain_models import DomainDocument
from agent.domain_preview_api import (
    MAX_DOMAIN_PAYLOAD_BYTES,
    parse_domain_preview_request,
)


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
if not (ROOT_DIRECTORY / "tests" / "fixtures").is_dir():
    ROOT_DIRECTORY = Path.cwd()

FIXTURE_PATH = (
    ROOT_DIRECTORY / "tests" / "fixtures" / "rooms_v1_0.json"
)
CURRENT_ROOMS_PATH = (
    ROOT_DIRECTORY
    / "projects"
    / "Test_01"
    / "exports"
    / "rooms"
    / "rooms.json"
)
ROUTER_PATH = ROOT_DIRECTORY / "agent" / "domain_preview_api.py"
ENDPOINT_PATH = "/api/v1/rooms/domain/preview"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_rooms_payload(
    *,
    format_version: str = "1.0",
) -> dict[str, Any]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload["FormatVersion"] = format_version
    return payload


def envelope(
    *,
    format_version: str = "1.0",
    project_id: Any = "Test_01",
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "rooms_payload": base_rooms_payload(
            format_version=format_version
        ),
    }


def json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def raw_request(
    body: bytes,
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
    chunks: list[bytes] | None = None,
    client: tuple[str, int] = ("127.0.0.1", 50000),
    receive_count: dict[str, int] | None = None,
) -> Request:
    raw_headers = list(headers or [])
    messages = list(chunks if chunks is not None else [body])
    if not messages:
        messages = [b""]
    index = 0

    async def receive() -> dict[str, Any]:
        nonlocal index
        if receive_count is not None:
            receive_count["value"] = (
                receive_count.get("value", 0) + 1
            )
        if index >= len(messages):
            return {
                "type": "http.request",
                "body": b"",
                "more_body": False,
            }
        chunk = messages[index]
        index += 1
        return {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(messages),
        }

    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": ENDPOINT_PATH,
            "raw_path": ENDPOINT_PATH.encode("ascii"),
            "query_string": b"",
            "root_path": "",
            "headers": raw_headers,
            "client": client,
            "server": ("testserver", 80),
        },
        receive,
    )


def parse_raw(
    body: bytes,
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
    chunks: list[bytes] | None = None,
    receive_count: dict[str, int] | None = None,
):
    request = raw_request(
        body,
        headers=headers,
        chunks=chunks,
        receive_count=receive_count,
    )
    return asyncio.run(parse_domain_preview_request(request))


class DomainPreviewApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("127.0.0.1", 50000),
        )
        self.addCleanup(self.client.close)

    def assert_safe_response(
        self,
        response,
        status_code: int,
        code: str,
        *forbidden: str,
    ) -> None:
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(
            response.json(),
            {
                "detail": {
                    "code": code,
                    "message": response.json()["detail"]["message"],
                }
            },
        )
        serialized = json.dumps(
            response.json(),
            ensure_ascii=False,
        ).casefold()
        self.assertNotIn("traceback", serialized)
        self.assertNotIn("file:", serialized)
        for value in forbidden:
            self.assertNotIn(value.casefold(), serialized)

    def assert_safe_exception(
        self,
        error: HTTPException,
        status_code: int,
        code: str,
        *forbidden: str,
    ) -> None:
        self.assertEqual(error.status_code, status_code)
        self.assertEqual(error.detail["code"], code)
        serialized = json.dumps(
            error.detail,
            ensure_ascii=False,
        ).casefold()
        self.assertNotIn("traceback", serialized)
        self.assertNotIn("file:", serialized)
        for value in forbidden:
            self.assertNotIn(value.casefold(), serialized)

    def test_success_legacy_1_0_strict_domain_document(self) -> None:
        response = self.client.post(
            ENDPOINT_PATH,
            json=envelope(format_version="1.0"),
        )

        self.assertEqual(response.status_code, 200)
        document = DomainDocument.model_validate(response.json())
        self.assertEqual(document.schema_version, "1.0")
        self.assertEqual(document.legacy_format_version, "1.0")
        self.assertEqual(
            set(response.json()),
            {
                "schema_version",
                "legacy_format_version",
                "project",
                "diagnostics",
            },
        )

    def test_success_legacy_1_1(self) -> None:
        response = self.client.post(
            ENDPOINT_PATH,
            json=envelope(format_version="1.1"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["legacy_format_version"],
            "1.1",
        )

    def test_adapter_receives_and_preserves_mapping(self) -> None:
        original_adapter = adapt_rooms_payload
        observed: dict[str, Any] = {}

        def guarded_adapter(
            payload,
            *,
            project_id,
        ):
            before = copy.deepcopy(payload)
            result = original_adapter(
                payload,
                project_id=project_id,
            )
            observed["unchanged"] = payload == before
            return result

        request_envelope = envelope()
        before = copy.deepcopy(request_envelope)
        with patch.object(
            domain_preview_api,
            "adapt_rooms_payload",
            side_effect=guarded_adapter,
        ):
            response = self.client.post(
                ENDPOINT_PATH,
                json=request_envelope,
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(observed["unchanged"])
        self.assertEqual(request_envelope, before)

    def test_endpoint_has_no_file_network_or_subprocess_actions(
        self,
    ) -> None:
        request_envelope = envelope()
        with (
            patch(
                "builtins.open",
                side_effect=AssertionError("file open"),
            ),
            patch.object(
                Path,
                "read_text",
                side_effect=AssertionError("file read"),
            ),
            patch.object(
                Path,
                "write_text",
                side_effect=AssertionError("file write"),
            ),
            patch.object(
                Path,
                "mkdir",
                side_effect=AssertionError("directory write"),
            ),
            patch.object(
                socket,
                "create_connection",
                side_effect=AssertionError("network"),
            ),
            patch.object(
                subprocess,
                "Popen",
                side_effect=AssertionError("subprocess"),
            ),
            patch.object(
                subprocess,
                "run",
                side_effect=AssertionError("subprocess"),
            ),
        ):
            response = self.client.post(
                ENDPOINT_PATH,
                json=request_envelope,
            )

        self.assertEqual(response.status_code, 200)

    def test_project_registry_helpers_are_not_called(self) -> None:
        with (
            patch(
                "agent.api.resolve_project_directory",
                side_effect=AssertionError("api project access"),
            ),
            patch(
                "agent.rooms_api.resolve_project_directory",
                side_effect=AssertionError("rooms project access"),
            ),
            patch(
                "agent.ifc_space_preview_api."
                "resolve_registered_project_directory",
                side_effect=AssertionError("ifc project access"),
            ),
        ):
            response = self.client.post(
                ENDPOINT_PATH,
                json=envelope(),
            )

        self.assertEqual(response.status_code, 200)

    def test_actual_rooms_json_is_unchanged(self) -> None:
        before = sha256(CURRENT_ROOMS_PATH)
        payload = json.loads(
            CURRENT_ROOMS_PATH.read_text(encoding="utf-8")
        )

        response = self.client.post(
            ENDPOINT_PATH,
            json={
                "project_id": "Test_01",
                "rooms_payload": payload,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(sha256(CURRENT_ROOMS_PATH), before)

    def test_content_length_exactly_limit_is_allowed(self) -> None:
        request_envelope = envelope()
        request_envelope["rooms_payload"]["Padding"] = ""
        initial = json_bytes(request_envelope)
        padding_size = MAX_DOMAIN_PAYLOAD_BYTES - len(initial)
        self.assertGreater(padding_size, 0)
        request_envelope["rooms_payload"]["Padding"] = (
            "x" * padding_size
        )
        body = json_bytes(request_envelope)
        self.assertEqual(len(body), MAX_DOMAIN_PAYLOAD_BYTES)

        parsed = parse_raw(
            body,
            headers=[
                (b"content-type", b"application/json"),
                (
                    b"content-length",
                    str(len(body)).encode("ascii"),
                ),
            ],
        )

        self.assertEqual(parsed.project_id, "Test_01")

    def test_declared_content_length_above_limit_precedes_read(
        self,
    ) -> None:
        receive_count: dict[str, int] = {}
        body = json_bytes(envelope())

        with self.assertRaises(HTTPException) as context:
            parse_raw(
                body,
                headers=[
                    (b"content-type", b"application/json"),
                    (
                        b"content-length",
                        str(
                            MAX_DOMAIN_PAYLOAD_BYTES + 1
                        ).encode("ascii"),
                    ),
                ],
                receive_count=receive_count,
            )

        self.assert_safe_exception(
            context.exception,
            413,
            "domain_payload_too_large",
        )
        self.assertEqual(receive_count.get("value", 0), 0)

    def test_extremely_long_content_length_is_safe_413(
        self,
    ) -> None:
        receive_count: dict[str, int] = {}
        with self.assertRaises(HTTPException) as context:
            parse_raw(
                json_bytes(envelope()),
                headers=[
                    (b"content-type", b"application/json"),
                    (b"content-length", b"9" * 5000),
                ],
                receive_count=receive_count,
            )

        self.assert_safe_exception(
            context.exception,
            413,
            "domain_payload_too_large",
        )
        self.assertEqual(receive_count.get("value", 0), 0)

    def test_actual_oversized_stream_beats_small_length(self) -> None:
        chunks = [
            b"x" * MAX_DOMAIN_PAYLOAD_BYTES,
            b"x",
        ]

        with self.assertRaises(HTTPException) as context:
            parse_raw(
                b"",
                headers=[
                    (b"content-type", b"application/json"),
                    (b"content-length", b"1"),
                ],
                chunks=chunks,
            )

        self.assert_safe_exception(
            context.exception,
            413,
            "domain_payload_too_large",
        )

    def test_actual_oversized_stream_without_length(self) -> None:
        with self.assertRaises(HTTPException) as context:
            parse_raw(
                b"",
                headers=[
                    (b"content-type", b"application/json"),
                ],
                chunks=[
                    b"x" * MAX_DOMAIN_PAYLOAD_BYTES,
                    b"x",
                ],
            )

        self.assert_safe_exception(
            context.exception,
            413,
            "domain_payload_too_large",
        )

    def test_duplicate_content_length_is_rejected(self) -> None:
        body = json_bytes(envelope())
        with self.assertRaises(HTTPException) as context:
            parse_raw(
                body,
                headers=[
                    (b"content-type", b"application/json"),
                    (b"content-length", b"1"),
                    (b"content-length", b"1"),
                ],
            )

        self.assert_safe_exception(
            context.exception,
            400,
            "domain_payload_invalid",
        )

    def test_conflicting_content_length_is_rejected(self) -> None:
        body = json_bytes(envelope())
        with self.assertRaises(HTTPException) as context:
            parse_raw(
                body,
                headers=[
                    (b"content-type", b"application/json"),
                    (b"content-length", b"1"),
                    (b"content-length", b"2"),
                ],
            )

        self.assert_safe_exception(
            context.exception,
            400,
            "domain_payload_invalid",
        )

    def test_malformed_content_lengths_are_rejected(self) -> None:
        body = json_bytes(envelope())
        for value in (
            b"",
            b"-1",
            b"+1",
            b" 1",
            b"1 ",
            b"1,2",
            b"\xff",
        ):
            with self.subTest(value=value):
                with self.assertRaises(
                    HTTPException
                ) as context:
                    parse_raw(
                        body,
                        headers=[
                            (
                                b"content-type",
                                b"application/json",
                            ),
                            (b"content-length", value),
                        ],
                    )
                self.assert_safe_exception(
                    context.exception,
                    400,
                    "domain_payload_invalid",
                )

    def test_malformed_utf8_and_json_are_rejected(self) -> None:
        for body in (
            b"\xff",
            b"{",
            b'{"project_id":}',
        ):
            with self.subTest(body=body):
                with self.assertRaises(
                    HTTPException
                ) as context:
                    parse_raw(
                        body,
                        headers=[
                            (
                                b"content-type",
                                b"application/json",
                            ),
                        ],
                    )
                self.assert_safe_exception(
                    context.exception,
                    400,
                    "domain_payload_invalid",
                )

    def test_duplicate_json_keys_at_all_levels_are_rejected(
        self,
    ) -> None:
        bodies = (
            (
                b'{"project_id":"one","project_id":"two",'
                b'"rooms_payload":{}}'
            ),
            (
                b'{"project_id":"one","rooms_payload":'
                b'{"Rooms":[],"Rooms":[]}}'
            ),
        )
        for body in bodies:
            with self.subTest(body=body):
                with self.assertRaises(
                    HTTPException
                ) as context:
                    parse_raw(
                        body,
                        headers=[
                            (
                                b"content-type",
                                b"application/json",
                            ),
                        ],
                    )
                self.assert_safe_exception(
                    context.exception,
                    400,
                    "domain_payload_invalid",
                    "one",
                    "two",
                )

    def test_non_finite_json_numbers_are_rejected(self) -> None:
        for constant in (
            b"NaN",
            b"Infinity",
            b"-Infinity",
        ):
            body = (
                b'{"project_id":"Test_01","rooms_payload":'
                b'{"value":' + constant + b"}}"
            )
            with self.subTest(constant=constant):
                with self.assertRaises(
                    HTTPException
                ) as context:
                    parse_raw(
                        body,
                        headers=[
                            (
                                b"content-type",
                                b"application/json",
                            ),
                        ],
                    )
                self.assert_safe_exception(
                    context.exception,
                    400,
                    "domain_payload_invalid",
                )

    def test_non_object_top_level_values_are_rejected(self) -> None:
        for body in (
            b"[]",
            b'"text"',
            b"null",
        ):
            with self.subTest(body=body):
                with self.assertRaises(
                    HTTPException
                ) as context:
                    parse_raw(
                        body,
                        headers=[
                            (
                                b"content-type",
                                b"application/json",
                            ),
                        ],
                    )
                self.assert_safe_exception(
                    context.exception,
                    400,
                    "domain_payload_invalid",
                )

    def test_parser_recursion_error_is_safe_400(self) -> None:
        marker = "recursion-marker-must-not-echo"
        body = json_bytes(envelope())
        with patch.object(
            domain_preview_api.json,
            "loads",
            side_effect=RecursionError(marker),
        ):
            with self.assertRaises(HTTPException) as context:
                parse_raw(
                    body,
                    headers=[
                        (b"content-type", b"application/json"),
                    ],
                )

        self.assert_safe_exception(
            context.exception,
            400,
            "domain_payload_invalid",
            marker,
        )

    def test_content_type_is_required_and_strict(self) -> None:
        body = json_bytes(envelope())
        invalid_header_sets = (
            [],
            [(b"content-type", b"text/plain")],
            [
                (
                    b"content-type",
                    b"application/x-www-form-urlencoded",
                )
            ],
            [
                (
                    b"content-type",
                    b"multipart/form-data; boundary=x",
                )
            ],
            [
                (
                    b"content-type",
                    b"application/json; charset=latin-1",
                )
            ],
            [
                (
                    b"content-type",
                    b"application/json; charset=utf-8; x=y",
                )
            ],
        )
        for headers in invalid_header_sets:
            with self.subTest(headers=headers):
                with self.assertRaises(
                    HTTPException
                ) as context:
                    parse_raw(body, headers=headers)
                self.assert_safe_exception(
                    context.exception,
                    415,
                    "domain_content_type_invalid",
                )

    def test_duplicate_content_type_is_rejected_before_read(
        self,
    ) -> None:
        body = json_bytes(envelope())
        for values in (
            (b"application/json", b"application/json"),
            (b"application/json", b"text/plain"),
        ):
            receive_count: dict[str, int] = {}
            request = raw_request(
                body,
                headers=[
                    (b"host", b"127.0.0.1"),
                    (b"content-type", values[0]),
                    (b"content-type", values[1]),
                ],
                receive_count=receive_count,
            )
            with self.subTest(values=values):
                with (
                    patch.object(
                        domain_preview_api,
                        "adapt_rooms_payload",
                        side_effect=AssertionError("adapter called"),
                    ),
                    self.assertRaises(HTTPException) as context,
                ):
                    asyncio.run(
                        domain_preview_api.preview_domain_rooms(
                            request
                        )
                    )
                self.assert_safe_exception(
                    context.exception,
                    415,
                    "domain_content_type_invalid",
                )
                self.assertEqual(
                    receive_count.get("value", 0),
                    0,
                )

    def test_browser_simple_text_plain_is_rejected_before_read(
        self,
    ) -> None:
        receive_count: dict[str, int] = {}
        with self.assertRaises(HTTPException) as context:
            parse_raw(
                json_bytes(envelope()),
                headers=[
                    (b"content-type", b"text/plain"),
                ],
                receive_count=receive_count,
            )

        self.assert_safe_exception(
            context.exception,
            415,
            "domain_content_type_invalid",
        )
        self.assertEqual(receive_count.get("value", 0), 0)

    def test_application_json_and_utf8_charset_are_allowed(
        self,
    ) -> None:
        body = json_bytes(envelope())
        for value in (
            b"application/json",
            b"application/json; charset=utf-8",
            b"Application/JSON; Charset=UTF-8",
        ):
            with self.subTest(value=value):
                parsed = parse_raw(
                    body,
                    headers=[(b"content-type", value)],
                )
                self.assertEqual(parsed.project_id, "Test_01")

    def test_invalid_envelope_is_safe(self) -> None:
        credential_marker = (
            "sk" + "-" + "proj" + "-" + ("x" * 32)
        )
        cases = (
            {
                **envelope(),
                "unexpected": credential_marker,
            },
            {
                **envelope(),
                "project_id": "",
            },
            {
                **envelope(),
                "project_id": "x" * 129,
            },
            {
                **envelope(),
                "project_id": 123,
            },
            {
                "project_id": credential_marker,
                "rooms_payload": [],
            },
        )
        for request_envelope in cases:
            with self.subTest(case=request_envelope):
                response = self.client.post(
                    ENDPOINT_PATH,
                    json=request_envelope,
                )
                self.assert_safe_response(
                    response,
                    422,
                    "domain_request_invalid",
                    credential_marker,
                )

    def test_path_shaped_project_id_is_not_reflected(self) -> None:
        separator = "\\"
        identities = (
            "C:" + separator + "private" + separator + "project",
            separator
            + separator
            + "server"
            + separator
            + "share"
            + separator
            + "project",
            "/" + "private/project",
            separator
            + separator
            + "?"
            + separator
            + "C:"
            + separator
            + "private"
            + separator
            + "project",
            "file:" + "///private/project",
        )

        for identity in identities:
            with self.subTest(identity=identity):
                response = self.client.post(
                    ENDPOINT_PATH,
                    json=envelope(project_id=identity),
                )
                self.assert_safe_response(
                    response,
                    422,
                    "unsafe_identity_path",
                    identity,
                    "private",
                    "server",
                    "share",
                )

    def test_unsafe_room_code_fallback_is_not_reflected(
        self,
    ) -> None:
        request_envelope = envelope()
        room = request_envelope["rooms_payload"]["Rooms"][0]
        room.pop("SourceHandle")
        unsafe_code = (
            "C:" + "\\" + "private" + "\\" + "room-code"
        )
        room["Code"] = unsafe_code

        response = self.client.post(
            ENDPOINT_PATH,
            json=request_envelope,
        )

        self.assert_safe_response(
            response,
            422,
            "unsafe_identity_path",
            unsafe_code,
            "room-code",
            "private",
        )

    def test_malformed_rooms_payload_is_safe(self) -> None:
        request_envelope = envelope()
        request_envelope["rooms_payload"].pop("ParserVersion")

        response = self.client.post(
            ENDPOINT_PATH,
            json=request_envelope,
        )

        self.assert_safe_response(
            response,
            422,
            "domain_rooms_payload_invalid",
            "ParserVersion",
        )

    def test_unsupported_format_is_safe(self) -> None:
        response = self.client.post(
            ENDPOINT_PATH,
            json=envelope(format_version="1.2"),
        )

        self.assert_safe_response(
            response,
            422,
            "domain_rooms_payload_invalid",
            "1.2",
        )

    def test_non_loopback_client_is_rejected(self) -> None:
        remote_client = TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("203.0.113.10", 50000),
        )
        self.addCleanup(remote_client.close)

        response = remote_client.post(
            ENDPOINT_PATH,
            json=envelope(),
        )

        self.assert_safe_response(
            response,
            403,
            "loopback_required",
            "203.0.113.10",
        )

    def test_forwarded_headers_cannot_bypass_loopback(self) -> None:
        remote_client = TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("203.0.113.10", 50000),
        )
        self.addCleanup(remote_client.close)

        response = remote_client.post(
            ENDPOINT_PATH,
            json=envelope(),
            headers={
                "Forwarded": "for=127.0.0.1",
                "X-Forwarded-For": "127.0.0.1",
            },
        )

        self.assert_safe_response(
            response,
            403,
            "loopback_required",
            "127.0.0.1",
            "203.0.113.10",
        )

    def test_attacker_and_rebinding_hosts_are_rejected(
        self,
    ) -> None:
        hosts = (
            "attacker.example",
            "localhost.evil",
            "localhost.",
            "127.0.0.1.attacker.example",
        )
        for host in hosts:
            with self.subTest(host=host):
                response = self.client.post(
                    ENDPOINT_PATH,
                    json=envelope(),
                    headers={"Host": host},
                )
                self.assert_safe_response(
                    response,
                    403,
                    "loopback_required",
                    host,
                    "attacker",
                )

    def test_missing_duplicate_and_conflicting_host_rejected(
        self,
    ) -> None:
        body = json_bytes(envelope())
        header_sets = (
            [
                (b"content-type", b"application/json"),
            ],
            [
                (b"host", b"localhost"),
                (b"host", b"localhost"),
                (b"content-type", b"application/json"),
            ],
            [
                (b"host", b"localhost"),
                (b"host", b"127.0.0.1"),
                (b"content-type", b"application/json"),
            ],
            [
                (b"host", b"attacker.example"),
                (b"content-type", b"application/json"),
            ],
        )
        for headers in header_sets:
            receive_count: dict[str, int] = {}
            request = raw_request(
                body,
                headers=headers,
                receive_count=receive_count,
            )
            with self.subTest(headers=headers):
                with (
                    patch.object(
                        domain_preview_api,
                        "adapt_rooms_payload",
                        side_effect=AssertionError("adapter called"),
                    ),
                    self.assertRaises(HTTPException) as context,
                ):
                    asyncio.run(
                        domain_preview_api.preview_domain_rooms(
                            request
                        )
                    )
                self.assert_safe_exception(
                    context.exception,
                    403,
                    "loopback_required",
                )
                self.assertEqual(
                    receive_count.get("value", 0),
                    0,
                )

    def test_malformed_hosts_and_ports_are_rejected(self) -> None:
        malformed_hosts = (
            b"",
            b" localhost",
            b"localhost ",
            b"local\thost",
            b"local\x00host",
            b"localhost,127.0.0.1",
            b"user@localhost",
            b"localhost.",
            b"[::1%25zone]",
            b"::1",
            b"2130706433",
            b"0x7f000001",
            b"0177.0.0.1",
            b"127.000.000.001",
            b"localhost:",
            b"localhost:0",
            b"localhost:65536",
            b"localhost:+80",
            b"localhost:-1",
            b"localhost:80:90",
            b"[::1]:",
            b"[::1]:0",
            b"[::1]:65536",
        )
        body = json_bytes(envelope())
        for host in malformed_hosts:
            request = raw_request(
                body,
                headers=[
                    (b"host", host),
                    (b"content-type", b"application/json"),
                ],
            )
            with self.subTest(host=host):
                with self.assertRaises(
                    HTTPException
                ) as context:
                    asyncio.run(
                        domain_preview_api.preview_domain_rooms(
                            request
                        )
                    )
                self.assert_safe_exception(
                    context.exception,
                    403,
                    "loopback_required",
                )

    def test_allowed_local_hosts_with_optional_ports(self) -> None:
        allowed_hosts = (
            b"localhost",
            b"LOCALHOST",
            b"localhost:80",
            b"localhost:65535",
            b"127.0.0.1",
            b"127.0.0.1:8765",
            b"[::1]",
            b"[::1]:8765",
        )
        body = json_bytes(envelope())
        for host in allowed_hosts:
            request = raw_request(
                body,
                headers=[
                    (b"host", host),
                    (b"content-type", b"application/json"),
                    (
                        b"content-length",
                        str(len(body)).encode("ascii"),
                    ),
                ],
            )
            with self.subTest(host=host):
                document = asyncio.run(
                    domain_preview_api.preview_domain_rooms(
                        request
                    )
                )
                self.assertIsInstance(document, DomainDocument)

    def test_proxy_headers_do_not_override_rejected_host(
        self,
    ) -> None:
        attacker_host = "attacker.example"
        response = self.client.post(
            ENDPOINT_PATH,
            json=envelope(),
            headers={
                "Host": attacker_host,
                "Forwarded": "host=localhost;for=127.0.0.1",
                "X-Forwarded-Host": "localhost",
                "X-Forwarded-For": "127.0.0.1",
            },
        )

        self.assert_safe_response(
            response,
            403,
            "loopback_required",
            attacker_host,
            "attacker",
        )

    def test_no_permissive_cors_middleware(self) -> None:
        middleware_names = {
            item.cls.__name__
            for item in app.user_middleware
        }
        self.assertNotIn("CORSMiddleware", middleware_names)

    def test_unexpected_adapter_error_returns_safe_500(
        self,
    ) -> None:
        separator = "\\"
        path_marker = (
            "C:" + separator + "private" + separator + "failure"
        )
        credential_marker = (
            "sk" + "-" + "proj" + "-" + ("y" * 32)
        )
        error_text = path_marker + " " + credential_marker

        with patch.object(
            domain_preview_api,
            "adapt_rooms_payload",
            side_effect=RuntimeError(error_text),
        ):
            response = self.client.post(
                ENDPOINT_PATH,
                json=envelope(),
            )

        self.assert_safe_response(
            response,
            500,
            "domain_preview_failed",
            path_marker,
            credential_marker,
            "failure",
        )

    def test_unexpected_stream_error_returns_safe_500(
        self,
    ) -> None:
        marker = "stream-marker-must-not-echo"

        async def receive() -> dict[str, Any]:
            raise RuntimeError(marker)

        request = Request(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": ENDPOINT_PATH,
                "raw_path": ENDPOINT_PATH.encode("ascii"),
                "query_string": b"",
                "root_path": "",
                "headers": [
                    (b"host", b"127.0.0.1"),
                    (b"content-type", b"application/json"),
                ],
                "client": ("127.0.0.1", 50000),
                "server": ("testserver", 80),
            },
            receive,
        )

        with self.assertRaises(HTTPException) as context:
            asyncio.run(
                domain_preview_api.preview_domain_rooms(request)
            )

        self.assert_safe_exception(
            context.exception,
            500,
            "domain_preview_failed",
            marker,
        )

    def test_existing_route_map_and_api_version_are_preserved(
        self,
    ) -> None:
        openapi_paths = app.openapi()["paths"]
        route_methods = {
            (method.upper(), path)
            for path, operations in openapi_paths.items()
            for method in operations
            if method
            in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "options",
                "head",
                "trace",
            }
        }
        expected_existing = {
            ("GET", "/health"),
            ("GET", "/api/v1/projects"),
            (
                "GET",
                "/api/v1/projects/{project_name}/snapshot",
            ),
            (
                "POST",
                "/api/v1/projects/{project_name}/snapshot",
            ),
            (
                "POST",
                "/api/v1/projects/{project_name}/analyze",
            ),
            (
                "POST",
                "/api/v1/projects/{project_name}/rooms",
            ),
            (
                "GET",
                "/api/v1/projects/{project_name}/rooms",
            ),
            (
                "POST",
                "/api/v1/projects/{project_id}/"
                "rooms/ifc-space/preview",
            ),
        }

        self.assertTrue(expected_existing.issubset(route_methods))
        self.assertIn(("POST", ENDPOINT_PATH), route_methods)
        self.assertEqual(app.version, "0.6.0")

    def test_openapi_has_manual_request_and_domain_response(
        self,
    ) -> None:
        operation = app.openapi()["paths"][ENDPOINT_PATH]["post"]
        request_body = operation["requestBody"]
        request_schema = request_body["content"][
            "application/json"
        ]["schema"]
        response_schema = operation["responses"]["200"]["content"][
            "application/json"
        ]["schema"]

        self.assertTrue(request_body["required"])
        self.assertEqual(
            request_schema["title"],
            "DomainPreviewRequest",
        )
        self.assertEqual(
            set(request_schema["required"]),
            {"project_id", "rooms_payload"},
        )
        self.assertFalse(
            request_schema["additionalProperties"]
        )
        self.assertTrue(
            response_schema["$ref"].endswith(
                "/DomainDocument"
            )
        )

    def test_router_import_is_side_effect_free(self) -> None:
        source = ROUTER_PATH.read_text(encoding="utf-8")
        ast.parse(source, filename=str(ROUTER_PATH))
        before = sha256(CURRENT_ROOMS_PATH)

        with (
            patch.object(
                Path,
                "write_text",
                side_effect=AssertionError("file write"),
            ),
            patch.object(
                Path,
                "write_bytes",
                side_effect=AssertionError("file write"),
            ),
            patch.object(
                Path,
                "mkdir",
                side_effect=AssertionError("directory write"),
            ),
            patch.object(
                socket,
                "create_connection",
                side_effect=AssertionError("network"),
            ),
            patch.object(
                subprocess,
                "Popen",
                side_effect=AssertionError("subprocess"),
            ),
            patch.object(
                subprocess,
                "run",
                side_effect=AssertionError("subprocess"),
            ),
        ):
            importlib.reload(domain_preview_api)

        self.assertEqual(sha256(CURRENT_ROOMS_PATH), before)


if __name__ == "__main__":
    unittest.main()

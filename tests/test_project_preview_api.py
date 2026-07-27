from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
import unittest

from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import UUID

from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import ValidationError

import agent.project_preview_api as project_preview_api
from agent.api import app
from agent.domain_adapter import adapt_rooms_payload
from agent.project_foundation import (
    build_project_seed,
    canonical_json_bytes,
    sheet_manifest_reference,
)
from agent.project_models import (
    CatalogSourceType,
    CatalogSourceVerificationStatus,
    CatalogVerificationStatus,
    CanonicalProjectModel,
    EquipmentCatalogItem,
    EquipmentCatalogSource,
    Issue,
    IssueSeverity,
    IssueStatus,
    Point3D,
    ProjectLifecycleStatus,
    ProjectSeedStatus,
    SourceEvidenceKind,
    SourcePoint,
    SourcePointEvidence,
    SourcePointKind,
    SourcePointState,
    UnitVector3D,
)
from agent.project_preview_api import (
    MAX_PROJECT_PAYLOAD_BYTES,
    parse_project_preview_request,
    preview_canonical_project,
)


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
ROOMS_FIXTURE = (
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
ROUTER_PATH = ROOT_DIRECTORY / "agent" / "project_preview_api.py"
ENDPOINT_PATH = "/api/v1/projects/canonical/preview"
FIXED_TIME = datetime(
    2026,
    7,
    27,
    8,
    0,
    tzinfo=timezone.utc,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def raw_request(
    body: bytes,
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
    chunks: list[bytes] | None = None,
    client: tuple[str, int] | None = ("127.0.0.1", 50000),
    receive_count: dict[str, int] | None = None,
) -> Request:
    messages = list(chunks if chunks is not None else [body])
    if not messages:
        messages = [b""]
    index = 0

    async def receive() -> dict[str, Any]:
        nonlocal index
        if receive_count is not None:
            receive_count["count"] = (
                receive_count.get("count", 0) + 1
            )
        if index >= len(messages):
            return {"type": "http.disconnect"}
        chunk = messages[index]
        index += 1
        return {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(messages),
        }

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": ENDPOINT_PATH,
        "raw_path": ENDPOINT_PATH.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": list(headers or []),
        "server": ("127.0.0.1", 80),
    }
    if client is not None:
        scope["client"] = client
    return Request(scope, receive)


def request_headers(
    body: bytes,
    *,
    host: bytes = b"127.0.0.1",
    include_length: bool = True,
) -> list[tuple[bytes, bytes]]:
    result = [
        (b"host", host),
        (b"content-type", b"application/json"),
    ]
    if include_length:
        result.append(
            (b"content-length", str(len(body)).encode("ascii"))
        )
    return result


class ProjectPreviewApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        rooms_payload = json.loads(
            ROOMS_FIXTURE.read_text(encoding="utf-8")
        )
        cls.domain = adapt_rooms_payload(
            rooms_payload,
            project_id="project-preview-test",
        )
        cls.level = cls.domain.project.buildings[0].levels[0]
        cls.room = cls.level.rooms[0]
        cls.project = cls.make_project()
        cls.project_bytes = canonical_json_bytes(cls.project)

    @classmethod
    def boiler_point(
        cls,
        *,
        state: SourcePointState = SourcePointState.MARKED,
        evidence_kind: SourceEvidenceKind = (
            SourceEvidenceKind.USER_MARKED
        ),
    ) -> SourcePoint:
        return SourcePoint(
            source_point_id=UUID(
                "346cceae-69fb-59e5-a2c4-4f96e34431c9"
            ),
            kind=SourcePointKind.BOILER_ROOM,
            revision=1,
            state=state,
            world_coordinates_m=Point3D(
                x_m=1.0,
                y_m=2.0,
                z_m=0.0,
            ),
            local_coordinates_m=Point3D(
                x_m=1.0,
                y_m=2.0,
                z_m=0.0,
            ),
            level_id=cls.level.stable_id,
            room_id=cls.room.stable_id,
            confidence=1.0,
            evidence=SourcePointEvidence(
                kind=evidence_kind,
                method="closed_room_selection",
                drawing_name=cls.domain.project.drawing_name,
                source_handle=cls.room.source_handle,
                observed_at=FIXED_TIME,
            ),
        )

    @classmethod
    def water_point(cls) -> SourcePoint:
        return SourcePoint(
            source_point_id=UUID(
                "848f32d1-e459-522f-b0ad-ea8ea81ec8c1"
            ),
            kind=SourcePointKind.WATER_INLET,
            revision=1,
            state=SourcePointState.MARKED,
            world_coordinates_m=Point3D(
                x_m=4.0,
                y_m=5.0,
                z_m=0.2,
            ),
            local_coordinates_m=Point3D(
                x_m=4.0,
                y_m=0.0,
                z_m=0.2,
            ),
            level_id=cls.level.stable_id,
            level_elevation_m=0.0,
            wall_normal=UnitVector3D(
                x=1.0,
                y=0.0,
                z=0.0,
            ),
            confidence=0.95,
            evidence=SourcePointEvidence(
                kind=SourceEvidenceKind.USER_MARKED,
                method="nearest_allowed_wall_snap",
                drawing_name=cls.domain.project.drawing_name,
                source_handle="WALL-101",
                observed_at=FIXED_TIME,
            ),
        )

    @classmethod
    def make_project(
        cls,
        *,
        boiler: SourcePoint | None = None,
        status: ProjectLifecycleStatus = (
            ProjectLifecycleStatus.READY_FOR_DESIGN
        ),
    ) -> CanonicalProjectModel:
        seed = build_project_seed(
            cls.domain,
            [boiler or cls.boiler_point(), cls.water_point()],
            created_at=FIXED_TIME,
        )
        return CanonicalProjectModel(
            project_id=cls.domain.project.stable_id,
            revision=1,
            status=status,
            domain=cls.domain,
            seed=seed,
            sheet_manifest=sheet_manifest_reference(),
        )

    def setUp(self) -> None:
        self.client = TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("127.0.0.1", 50000),
        )
        self.addCleanup(self.client.close)

    def post(
        self,
        body: bytes | None = None,
        *,
        headers: dict[str, str] | None = None,
    ):
        return self.client.post(
            ENDPOINT_PATH,
            content=body if body is not None else self.project_bytes,
            headers=headers or {"Content-Type": "application/json"},
        )

    def assert_safe_response(
        self,
        response,
        status_code: int,
        code: str,
        *forbidden: str,
    ) -> None:
        self.assertEqual(response.status_code, status_code, response.text)
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
        )
        for value in forbidden:
            self.assertNotIn(value, serialized)

    def assert_safe_exception(
        self,
        error: HTTPException,
        status_code: int,
        code: str,
    ) -> None:
        self.assertEqual(error.status_code, status_code)
        self.assertEqual(error.detail["code"], code)
        self.assertEqual(set(error.detail), {"code", "message"})

    def test_valid_canonical_project_returns_200(self) -> None:
        response = self.post()

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.headers["content-type"],
            "application/json",
        )

    def test_raw_response_revalidates_as_canonical_project(self) -> None:
        response = self.post()

        validated = CanonicalProjectModel.model_validate_json(
            response.content
        )
        self.assertIsInstance(validated, CanonicalProjectModel)

    def test_response_is_semantically_equal_to_request(self) -> None:
        response = self.post()

        validated = CanonicalProjectModel.model_validate_json(
            response.content
        )
        self.assertEqual(validated, self.project)

    def test_response_is_deterministic_and_byte_identical(self) -> None:
        first = self.post()
        second = self.post()

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.content, second.content)
        self.assertEqual(first.content, self.project_bytes)

    def test_unicode_is_preserved_as_utf8(self) -> None:
        payload = self.project.model_dump(mode="json")
        payload["domain"]["project"]["name"] = "Дом Ω — Bränd"
        body = json_bytes(payload)

        response = self.post(body)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("Дом Ω — Bränd".encode("utf-8"), response.content)
        self.assertNotIn(b"\\u03a9", response.content)

    def test_constructor_validate_json_and_endpoint_parity(self) -> None:
        python_payload = self.project.model_dump(mode="python")
        constructed = CanonicalProjectModel(**python_payload)
        validated = CanonicalProjectModel.model_validate(
            python_payload
        )
        json_validated = CanonicalProjectModel.model_validate_json(
            self.project_bytes
        )
        response = self.post()
        endpoint_validated = (
            CanonicalProjectModel.model_validate_json(response.content)
        )

        self.assertEqual(constructed, validated)
        self.assertEqual(validated, json_validated)
        self.assertEqual(json_validated, endpoint_validated)

    def test_malformed_utf8_and_json_return_safe_400(self) -> None:
        cases = (
            b"{",
            b'{"project_id":',
            b'{"value":"\xff"}',
        )
        for body in cases:
            with self.subTest(body=repr(body)):
                response = self.post(body)
                self.assert_safe_response(
                    response,
                    400,
                    "project_payload_invalid",
                    repr(body),
                )

    def test_array_scalar_and_null_roots_return_400(self) -> None:
        for body in (b"[]", b"1", b'"value"', b"true", b"null"):
            with self.subTest(body=body):
                response = self.post(body)
                self.assert_safe_response(
                    response,
                    400,
                    "project_payload_invalid",
                    body.decode("ascii"),
                )

    def test_duplicate_root_and_nested_keys_return_400(self) -> None:
        cases = (
            b'{"schema_version":"1.0","schema_version":"1.0"}',
            b'{"domain":{"project_id":"a","project_id":"b"}}',
        )
        for body in cases:
            with self.subTest(body=body):
                response = self.post(body)
                self.assert_safe_response(
                    response,
                    400,
                    "project_payload_invalid",
                )

    def test_non_finite_json_constants_return_400(self) -> None:
        for value in (b"NaN", b"Infinity", b"-Infinity"):
            body = b'{"revision":' + value + b"}"
            with self.subTest(value=value):
                response = self.post(body)
                self.assert_safe_response(
                    response,
                    400,
                    "project_payload_invalid",
                    value.decode("ascii"),
                )

    def test_extra_model_field_returns_422(self) -> None:
        payload = self.project.model_dump(mode="json")
        payload["unexpected_field"] = "PRIVATE_MARKER"

        response = self.post(json_bytes(payload))

        self.assert_safe_response(
            response,
            422,
            "project_model_invalid",
            "unexpected_field",
            "PRIVATE_MARKER",
        )

    def test_invalid_coordinates_return_422(self) -> None:
        payload = self.project.model_dump(mode="json")
        payload["seed"]["source_points"][0][
            "world_coordinates_m"
        ]["x_m"] = True

        response = self.post(json_bytes(payload))

        self.assert_safe_response(
            response,
            422,
            "project_model_invalid",
        )

    def test_unknown_domain_reference_returns_422(self) -> None:
        payload = self.project.model_dump(mode="json")
        payload["seed"]["source_points"][0]["room_id"] = (
            "11111111-1111-4111-8111-111111111111"
        )

        response = self.post(json_bytes(payload))

        self.assert_safe_response(
            response,
            422,
            "project_model_invalid",
            "11111111-1111-4111-8111-111111111111",
        )

    def test_blocking_issue_prevents_ready_project(self) -> None:
        issue = Issue(
            issue_id=UUID(
                "7f513f3e-48a7-4bf9-a0fa-69842c0b5b4c"
            ),
            code="BLOCKING_TEST",
            severity=IssueSeverity.BLOCKING,
            status=IssueStatus.OPEN,
            message="PRIVATE_BLOCKING_MESSAGE",
            created_at=FIXED_TIME,
        )
        payload = self.project.model_dump(mode="json")
        payload["issues"] = [issue.model_dump(mode="json")]

        response = self.post(json_bytes(payload))

        self.assert_safe_response(
            response,
            422,
            "project_model_invalid",
            "PRIVATE_BLOCKING_MESSAGE",
        )

    def test_invalid_manufacturer_identity_is_not_accepted(
        self,
    ) -> None:
        source = EquipmentCatalogSource(
            source_type=CatalogSourceType.OFFICIAL_MANUFACTURER,
            document_title="Product data",
            publisher="Publisher",
            manufacturer_identity="Other Manufacturer",
            locator="manufacturer:example/model:EX-1",
            retrieved_at=FIXED_TIME,
            verification_status=(
                CatalogSourceVerificationStatus.VERIFIED
            ),
            verification_completed_at=FIXED_TIME,
            evidence_sha256="1" * 64,
            confirmed_fields=["model"],
        )
        with self.assertRaises(ValidationError):
            EquipmentCatalogItem(
                catalog_item_id=UUID(
                    "9fd3cf65-7461-554a-9099-26318cf7c4b1"
                ),
                manufacturer="Example Manufacturing",
                brand="Example",
                model="EX-1",
                article="EX-1",
                category="test",
                verification_status=CatalogVerificationStatus.VERIFIED,
                sources=[source],
                verified_fields=["model"],
            )

        payload = self.project.model_dump(mode="json")
        payload["equipment_catalog_items"] = [
            {"manufacturer_identity": "Other Manufacturer"}
        ]
        response = self.post(json_bytes(payload))
        self.assert_safe_response(
            response,
            422,
            "project_model_invalid",
            "Other Manufacturer",
        )

    def test_whitespace_only_verified_catalog_fields_are_rejected(
        self,
    ) -> None:
        for field_name in (
            "manufacturer",
            "brand",
            "model",
            "article",
            "category",
        ):
            with self.subTest(field_name=field_name):
                kwargs = {
                    "catalog_item_id": UUID(
                        "9fd3cf65-7461-554a-9099-26318cf7c4b1"
                    ),
                    "manufacturer": "Example Manufacturing",
                    "brand": "Example",
                    "model": "EX-1",
                    "article": "EX-1",
                    "category": "test",
                    "verification_status": (
                        CatalogVerificationStatus.UNVERIFIED
                    ),
                    field_name: " \t ",
                }
                with self.assertRaises(ValidationError):
                    EquipmentCatalogItem(**kwargs)

        payload = self.project.model_dump(mode="json")
        payload["equipment_catalog_items"] = [{"model": "   "}]
        response = self.post(json_bytes(payload))
        self.assert_safe_response(
            response,
            422,
            "project_model_invalid",
        )

    def test_complete_proposed_point_is_not_promoted(self) -> None:
        proposed = self.boiler_point(
            state=SourcePointState.PROPOSED,
            evidence_kind=SourceEvidenceKind.RULE_PROPOSED,
        )
        project = self.make_project(
            boiler=proposed,
            status=ProjectLifecycleStatus.DRAFT,
        )
        self.assertEqual(
            project.seed.status,
            ProjectSeedStatus.INCOMPLETE,
        )

        response = self.post(canonical_json_bytes(project))

        self.assertEqual(response.status_code, 200, response.text)
        validated = CanonicalProjectModel.model_validate_json(
            response.content
        )
        boiler = next(
            point
            for point in validated.seed.source_points
            if point.kind == SourcePointKind.BOILER_ROOM
        )
        self.assertEqual(boiler.state, SourcePointState.PROPOSED)
        self.assertEqual(
            boiler.evidence.kind,
            SourceEvidenceKind.RULE_PROPOSED,
        )
        self.assertEqual(
            validated.seed.status,
            ProjectSeedStatus.INCOMPLETE,
        )
        self.assertNotEqual(
            validated.status,
            ProjectLifecycleStatus.READY_FOR_DESIGN,
        )

    def test_missing_and_wrong_content_type_rejected_before_read(
        self,
    ) -> None:
        header_sets = (
            [
                (b"host", b"127.0.0.1"),
                (b"content-length", b"0"),
            ],
            [
                (b"host", b"127.0.0.1"),
                (b"content-type", b"text/plain"),
                (b"content-length", b"0"),
            ],
        )
        for headers in header_sets:
            receive_count: dict[str, int] = {}
            request = raw_request(
                b"",
                headers=headers,
                receive_count=receive_count,
            )
            with (
                self.assertRaises(HTTPException) as context,
            ):
                asyncio.run(
                    parse_project_preview_request(request)
                )
            self.assert_safe_exception(
                context.exception,
                415,
                "project_content_type_invalid",
            )
            self.assertEqual(receive_count.get("count", 0), 0)

    def test_duplicate_content_type_rejected_before_read(
        self,
    ) -> None:
        for values in (
            (b"application/json", b"application/json"),
            (b"application/json", b"text/plain"),
        ):
            receive_count: dict[str, int] = {}
            request = raw_request(
                b"",
                headers=[
                    (b"host", b"127.0.0.1"),
                    (b"content-type", values[0]),
                    (b"content-type", values[1]),
                ],
                receive_count=receive_count,
            )
            with self.assertRaises(HTTPException) as context:
                asyncio.run(
                    parse_project_preview_request(request)
                )
            self.assert_safe_exception(
                context.exception,
                415,
                "project_content_type_invalid",
            )
            self.assertEqual(receive_count.get("count", 0), 0)

    def test_application_json_utf8_charset_is_allowed(self) -> None:
        request = raw_request(
            self.project_bytes,
            headers=[
                (b"host", b"127.0.0.1"),
                (
                    b"content-type",
                    b"Application/JSON; Charset=UTF-8",
                ),
            ],
        )

        parsed = asyncio.run(
            parse_project_preview_request(request)
        )

        self.assertEqual(parsed, self.project)

    def test_missing_content_length_is_allowed(self) -> None:
        request = raw_request(
            self.project_bytes,
            headers=request_headers(
                self.project_bytes,
                include_length=False,
            ),
        )

        parsed = asyncio.run(
            parse_project_preview_request(request)
        )

        self.assertEqual(parsed, self.project)

    def test_invalid_content_lengths_rejected_before_read(
        self,
    ) -> None:
        values = (
            b"",
            b"-1",
            b"+1",
            b" 1",
            b"1 ",
            b"1,1",
            b"abc",
        )
        for value in values:
            with self.subTest(value=value):
                receive_count: dict[str, int] = {}
                request = raw_request(
                    b"",
                    headers=[
                        (b"host", b"127.0.0.1"),
                        (b"content-type", b"application/json"),
                        (b"content-length", value),
                    ],
                    receive_count=receive_count,
                )
                with self.assertRaises(HTTPException) as context:
                    asyncio.run(
                        parse_project_preview_request(request)
                    )
                self.assert_safe_exception(
                    context.exception,
                    400,
                    "project_payload_invalid",
                )
                self.assertEqual(
                    receive_count.get("count", 0),
                    0,
                )

    def test_duplicate_content_lengths_rejected_before_read(
        self,
    ) -> None:
        for values in ((b"1", b"1"), (b"1", b"2")):
            receive_count: dict[str, int] = {}
            request = raw_request(
                b"",
                headers=[
                    (b"host", b"127.0.0.1"),
                    (b"content-type", b"application/json"),
                    (b"content-length", values[0]),
                    (b"content-length", values[1]),
                ],
                receive_count=receive_count,
            )
            with self.assertRaises(HTTPException) as context:
                asyncio.run(
                    parse_project_preview_request(request)
                )
            self.assert_safe_exception(
                context.exception,
                400,
                "project_payload_invalid",
            )
            self.assertEqual(receive_count.get("count", 0), 0)

    def test_declared_over_limit_rejected_before_read(self) -> None:
        receive_count: dict[str, int] = {}
        request = raw_request(
            b"",
            headers=[
                (b"host", b"127.0.0.1"),
                (b"content-type", b"application/json"),
                (
                    b"content-length",
                    str(
                        MAX_PROJECT_PAYLOAD_BYTES + 1
                    ).encode("ascii"),
                ),
            ],
            receive_count=receive_count,
        )

        with self.assertRaises(HTTPException) as context:
            asyncio.run(parse_project_preview_request(request))

        self.assert_safe_exception(
            context.exception,
            413,
            "project_payload_too_large",
        )
        self.assertEqual(receive_count.get("count", 0), 0)

    def test_actual_stream_over_limit_is_rejected(self) -> None:
        chunk = b"{" + (b" " * MAX_PROJECT_PAYLOAD_BYTES)
        request = raw_request(
            chunk,
            headers=[
                (b"host", b"127.0.0.1"),
                (b"content-type", b"application/json"),
            ],
        )

        with self.assertRaises(HTTPException) as context:
            asyncio.run(parse_project_preview_request(request))

        self.assert_safe_exception(
            context.exception,
            413,
            "project_payload_too_large",
        )

    def test_body_exactly_at_limit_is_accepted(self) -> None:
        self.assertLess(len(self.project_bytes), MAX_PROJECT_PAYLOAD_BYTES)
        body = self.project_bytes + (
            b" "
            * (MAX_PROJECT_PAYLOAD_BYTES - len(self.project_bytes))
        )
        request = raw_request(
            body,
            headers=request_headers(body),
        )

        parsed = asyncio.run(
            parse_project_preview_request(request)
        )

        self.assertEqual(parsed, self.project)

    def test_local_ipv4_ipv6_and_localhost_hosts_are_allowed(
        self,
    ) -> None:
        cases = (
            (b"localhost", ("127.0.0.1", 50000)),
            (b"LOCALHOST:8765", ("127.42.10.7", 50000)),
            (b"127.0.0.1", ("127.0.0.1", 50000)),
            (b"127.0.0.1:65535", ("127.0.0.1", 50000)),
            (b"[::1]", ("::1", 50000)),
            (b"[::1]:8765", ("::ffff:127.0.0.1", 50000)),
        )
        for host, client in cases:
            request = raw_request(
                self.project_bytes,
                headers=request_headers(
                    self.project_bytes,
                    host=host,
                ),
                client=client,
            )
            with self.subTest(host=host, client=client):
                response = asyncio.run(
                    preview_canonical_project(request)
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.body, self.project_bytes)

    def test_missing_duplicate_nonlocal_and_malformed_host_rejected(
        self,
    ) -> None:
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
                (b"host", b"attacker.example"),
                (b"content-type", b"application/json"),
            ],
            [
                (b"host", b"localhost:0"),
                (b"content-type", b"application/json"),
            ],
            [
                (b"host", b"localhost,127.0.0.1"),
                (b"content-type", b"application/json"),
            ],
        )
        for headers in header_sets:
            receive_count: dict[str, int] = {}
            request = raw_request(
                self.project_bytes,
                headers=headers,
                receive_count=receive_count,
            )
            with self.assertRaises(HTTPException) as context:
                asyncio.run(preview_canonical_project(request))
            self.assert_safe_exception(
                context.exception,
                403,
                "loopback_required",
            )
            self.assertEqual(receive_count.get("count", 0), 0)

        request = raw_request(
            self.project_bytes,
            headers=request_headers(self.project_bytes),
            client=("203.0.113.10", 50000),
        )
        with self.assertRaises(HTTPException) as context:
            asyncio.run(preview_canonical_project(request))
        self.assert_safe_exception(
            context.exception,
            403,
            "loopback_required",
        )

    def test_forwarded_headers_cannot_bypass_loopback_or_host(
        self,
    ) -> None:
        request = raw_request(
            self.project_bytes,
            headers=request_headers(
                self.project_bytes,
                host=b"attacker.example",
            )
            + [
                (b"forwarded", b"for=127.0.0.1;host=localhost"),
                (b"x-forwarded-for", b"127.0.0.1"),
                (b"x-forwarded-host", b"localhost"),
            ],
        )

        with self.assertRaises(HTTPException) as context:
            asyncio.run(preview_canonical_project(request))

        self.assert_safe_exception(
            context.exception,
            403,
            "loopback_required",
        )

    def test_fixed_safe_error_envelope_does_not_reflect_input(
        self,
    ) -> None:
        marker = "PRIVATE_INPUT_MARKER_7824"
        payload = self.project.model_dump(mode="json")
        payload["unexpected"] = marker

        response = self.post(json_bytes(payload))

        self.assert_safe_response(
            response,
            422,
            "project_model_invalid",
            marker,
            "unexpected",
        )

    def test_unexpected_internal_error_is_safe_500(self) -> None:
        marker = "PRIVATE_INTERNAL_MARKER_9381"
        with patch.object(
            project_preview_api.CanonicalProjectModel,
            "model_validate_json",
            side_effect=RuntimeError(marker),
        ):
            response = self.post()

        self.assert_safe_response(
            response,
            500,
            "project_preview_failed",
            marker,
        )

    def test_no_permissive_cors_middleware(self) -> None:
        middleware_names = {
            item.cls.__name__
            for item in app.user_middleware
        }
        self.assertNotIn("CORSMiddleware", middleware_names)

    def test_new_route_is_registered_exactly_once(self) -> None:
        routes = []
        for route in app.routes:
            routes.append(route)
            original = getattr(route, "original_router", None)
            if original is not None:
                routes.extend(original.routes)
        matches = [
            route
            for route in routes
            if getattr(route, "path", None) == ENDPOINT_PATH
            and getattr(route, "methods", None) == {"POST"}
        ]
        self.assertEqual(len(matches), 1)

    def test_all_old_routes_and_api_version_are_preserved(self) -> None:
        all_routes = list(app.routes)
        for route in app.routes:
            original = getattr(route, "original_router", None)
            if original is not None:
                all_routes.extend(original.routes)
        routes = {
            (
                route.path,
                tuple(sorted(route.methods or [])),
            )
            for route in all_routes
            if getattr(route, "path", None) == "/health"
            or getattr(route, "path", "").startswith("/api/")
        }
        expected = {
            ("/health", ("GET",)),
            ("/api/v1/projects", ("GET",)),
            (
                "/api/v1/projects/{project_name}/snapshot",
                ("GET",),
            ),
            (
                "/api/v1/projects/{project_name}/snapshot",
                ("POST",),
            ),
            (
                "/api/v1/projects/{project_name}/rooms",
                ("GET",),
            ),
            (
                "/api/v1/projects/{project_name}/rooms",
                ("POST",),
            ),
            (
                "/api/v1/projects/{project_name}/analyze",
                ("POST",),
            ),
            (
                "/api/v1/projects/{project_id}/rooms/"
                "ifc-space/preview",
                ("POST",),
            ),
            (
                "/api/v1/rooms/domain/preview",
                ("POST",),
            ),
            (ENDPOINT_PATH, ("POST",)),
        }
        self.assertEqual(routes, expected)
        self.assertEqual(app.version, "0.6.0")

    def test_import_agent_api_does_not_start_listener(self) -> None:
        before_fixture = sha256(ROOMS_FIXTURE)
        before_rooms = sha256(CURRENT_ROOMS_PATH)
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"

        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import agent.project_preview_api; "
                    "import agent.api"
                ),
            ],
            cwd=ROOT_DIRECTORY,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(sha256(ROOMS_FIXTURE), before_fixture)
        self.assertEqual(sha256(CURRENT_ROOMS_PATH), before_rooms)

    def test_preview_has_no_file_network_process_or_adapter_actions(
        self,
    ) -> None:
        request = raw_request(
            self.project_bytes,
            headers=request_headers(self.project_bytes),
        )
        forbidden = AssertionError("forbidden side effect")
        patchers = [
            patch.object(Path, "read_text", side_effect=forbidden),
            patch.object(Path, "read_bytes", side_effect=forbidden),
            patch.object(Path, "write_text", side_effect=forbidden),
            patch.object(Path, "write_bytes", side_effect=forbidden),
            patch.object(Path, "mkdir", side_effect=forbidden),
            patch("builtins.open", side_effect=forbidden),
            patch.object(
                socket,
                "create_connection",
                side_effect=forbidden,
            ),
            patch.object(
                socket.socket,
                "connect",
                side_effect=forbidden,
            ),
            patch.object(
                socket.socket,
                "connect_ex",
                side_effect=forbidden,
            ),
            patch.object(
                subprocess,
                "run",
                side_effect=forbidden,
            ),
            patch.object(
                subprocess,
                "Popen",
                side_effect=forbidden,
            ),
            patch(
                "agent.api.resolve_project_directory",
                side_effect=forbidden,
            ),
            patch(
                "agent.api.persist_snapshot",
                side_effect=forbidden,
            ),
            patch(
                "agent.api.persist_analysis_report",
                side_effect=forbidden,
            ),
            patch(
                "agent.rooms_api.resolve_project_directory",
                side_effect=forbidden,
            ),
            patch(
                "agent.domain_adapter.adapt_rooms_payload",
                side_effect=forbidden,
            ),
            patch(
                "agent.ifc_space_preview_api."
                "resolve_registered_project_directory",
                side_effect=forbidden,
            ),
            patch(
                "agent.ifc_space_preview_api.run_import",
                side_effect=forbidden,
            ),
            patch(
                "agent.project_foundation.load_sheet_manifest",
                side_effect=forbidden,
            ),
            patch(
                "agent.project_foundation.sheet_manifest_reference",
                side_effect=forbidden,
            ),
        ]
        loop = asyncio.new_event_loop()
        try:
            with ExitStack() as stack:
                for patcher in patchers:
                    stack.enter_context(patcher)
                response = loop.run_until_complete(
                    preview_canonical_project(request)
                )
        finally:
            loop.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, self.project_bytes)

    def test_project_and_rooms_fixtures_are_unchanged(self) -> None:
        before_fixture = sha256(ROOMS_FIXTURE)
        before_rooms = sha256(CURRENT_ROOMS_PATH)
        before_payload = copy.deepcopy(
            self.project.model_dump(mode="json")
        )

        response = self.post()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(sha256(ROOMS_FIXTURE), before_fixture)
        self.assertEqual(sha256(CURRENT_ROOMS_PATH), before_rooms)
        self.assertEqual(
            self.project.model_dump(mode="json"),
            before_payload,
        )

    def test_openapi_uses_canonical_project_request_and_response(
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
            "CanonicalProjectModel",
        )
        self.assertEqual(
            set(request_schema["required"]),
            {
                "project_id",
                "revision",
                "status",
                "domain",
                "seed",
                "sheet_manifest",
            },
        )
        self.assertFalse(request_schema["additionalProperties"])
        self.assertTrue(
            response_schema["$ref"].endswith(
                "/CanonicalProjectModel"
            )
        )

    def test_router_source_has_no_forbidden_runtime_imports(
        self,
    ) -> None:
        source = ROUTER_PATH.read_text(encoding="utf-8")
        forbidden_imports = (
            "agent.api",
            "agent.rooms_api",
            "agent.domain_preview_api",
            "agent.domain_adapter",
            "agent.ifc_space_preview_api",
            "agent.ifc_space_importer",
        )
        for name in forbidden_imports:
            self.assertNotIn(
                f"from {name} import",
                source,
            )
            self.assertNotIn(f"import {name}", source)


if __name__ == "__main__":
    unittest.main()

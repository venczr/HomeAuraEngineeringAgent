from __future__ import annotations

import copy
import hashlib
import json
import re
import tempfile
import unittest

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from agent.api import app
from agent.ifc_space_importer import (
    IfcOpenShellUnavailable,
    run_import as importer_run_import,
)
from agent.ifc_space_preview_api import (
    require_loopback_request,
)
from tests.test_ifc_space_importer import (
    room_document,
    synthetic_ifc,
)


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
RESEARCH_IFC = Path(
    r"C:\AI\HomeAuraEngineeringAgent-ifc-research"
    r"\manual-export\Test_01_rooms_ifc4.ifc"
)
PROTECTED_CANDIDATES = (
    RESEARCH_IFC,
    ROOT_DIRECTORY / "projects" / "Test_01" / "Test_01.dwg",
    ROOT_DIRECTORY / "projects" / "Test_01" / "Test_01.bak",
)
PROTECTED_PATHS = tuple(
    path
    for path in PROTECTED_CANDIDATES
    if path.is_file()
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


class IfcSpacePreviewApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.temporary_root = Path(self.temporary_directory.name)
        self.projects_root = self.temporary_root / "projects"
        self.project_directory = self.projects_root / "Test_01"
        self.project_directory.mkdir(parents=True)

        self.ifc_path = self.project_directory / "room101.ifc"
        self.rooms_path = self.project_directory / "rooms.json"
        self.outside_path = self.temporary_root / "outside.ifc"

        self.preview_root_patch = patch(
            "agent.ifc_space_preview_api.PROJECTS_DIRECTORY",
            self.projects_root,
        )
        self.api_root_patch = patch(
            "agent.api.PROJECTS_DIRECTORY",
            self.projects_root,
        )
        self.rooms_root_patch = patch(
            "agent.rooms_api.PROJECTS_DIRECTORY",
            self.projects_root,
        )
        self.preview_root_patch.start()
        self.api_root_patch.start()
        self.rooms_root_patch.start()

        app.dependency_overrides[require_loopback_request] = (
            lambda: None
        )
        self.client = TestClient(app)
        self.protected_before = {
            path: sha256(path)
            for path in PROTECTED_PATHS
        }
        self.addCleanup(self.client.close)
        self.addCleanup(
            app.dependency_overrides.pop,
            require_loopback_request,
            None,
        )
        self.addCleanup(self.rooms_root_patch.stop)
        self.addCleanup(self.api_root_patch.stop)
        self.addCleanup(self.preview_root_patch.stop)
        self.addCleanup(self.temporary_directory.cleanup)

    def tearDown(self) -> None:
        for path, expected in self.protected_before.items():
            self.assertEqual(sha256(path), expected, str(path))

    def write_inputs(
        self,
        ifc_content: str | None = None,
        rooms: dict | None = None,
    ) -> None:
        if ifc_content is None:
            ifc_content = synthetic_ifc(
                spaces=[
                    {
                        "name": "101",
                        "global_id": "3Vmsu$eoz6VAzSuuOWXaVz",
                        "long_name": "Тестовая комната",
                        "outer": [
                            (153.17888, 152.75076),
                            (4846.507, 152.75076),
                            (4846.507, 3843.40652),
                            (153.17888, 3843.40652),
                            (153.17888, 152.75076),
                        ],
                        "height": 2800.0,
                    }
                ]
            )
        if rooms is None:
            rooms = room_document(
                name="Тестовая комната",
                net_area=17.231460571289062,
                boundary_area=19.926653652183532,
            )
        self.ifc_path.write_text(ifc_content, encoding="utf-8")
        self.rooms_path.write_text(
            json.dumps(rooms, ensure_ascii=False),
            encoding="utf-8",
        )

    def post_preview(
        self,
        *,
        project_id: str = "Test_01",
        ifc_relative_path: str = "room101.ifc",
        rooms_relative_path: str = "rooms.json",
        extra_payload: dict[str, object] | None = None,
    ):
        inputs = [
            path
            for path in (self.ifc_path, self.rooms_path)
            if path.is_file()
        ]
        before = {
            path: sha256(path)
            for path in inputs
        }
        payload: dict[str, object] = {
            "ifc_relative_path": ifc_relative_path,
            "rooms_relative_path": rooms_relative_path,
        }
        if extra_payload:
            payload.update(extra_payload)
        response = self.client.post(
            (
                f"/api/v1/projects/{project_id}/"
                "rooms/ifc-space/preview"
            ),
            json=payload,
        )
        for path, expected in before.items():
            self.assertEqual(sha256(path), expected, str(path))
        for path, expected in self.protected_before.items():
            self.assertEqual(sha256(path), expected, str(path))
        return response

    def response_strings(self, value: object):
        if isinstance(value, dict):
            for item in value.values():
                yield from self.response_strings(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                yield from self.response_strings(item)
        elif isinstance(value, str):
            yield value

    def assert_sanitized(self, payload: object) -> None:
        forbidden = (
            str(ROOT_DIRECTORY),
            str(self.temporary_root),
            str(self.project_directory),
            "INTERNAL_SENTINEL",
            "damaged IFC",
            "not installed",
        )
        for text in self.response_strings(payload):
            folded = text.casefold()
            for value in forbidden:
                self.assertNotIn(value.casefold(), folded, text)
            self.assertNotIn("traceback", folded, text)
            self.assertNotIn("file://", folded, text)
            self.assertIsNone(
                re.search(r"(?:[A-Za-z]:[\\/]|\\\\)", text),
                text,
            )

    def test_successful_room_101_preview_is_read_only(self) -> None:
        self.write_inputs()
        source_document = json.loads(
            self.rooms_path.read_text(encoding="utf-8")
        )
        source_boundary = copy.deepcopy(
            source_document["Rooms"][0]["Boundary"]
        )

        response = self.post_preview()

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        report = payload["IfcSpaceImportReport"]
        candidate = payload["IfcSpaceGeometryCandidates"][0]
        self.assertEqual(report["FoundIfcSpaces"], 1)
        self.assertEqual(report["MatchedIfcSpaces"], 1)
        self.assertEqual(
            candidate["IfcSpace"]["GlobalId"],
            "3Vmsu$eoz6VAzSuuOWXaVz",
        )
        self.assertAlmostEqual(
            candidate["AreaM2"],
            17.321458459647975,
            places=12,
        )
        self.assertAlmostEqual(
            candidate["PerimeterM"],
            16.76796776,
            places=10,
        )
        self.assertAlmostEqual(candidate["HeightM"], 2.8)
        self.assertEqual(
            candidate["geometry_status"],
            "validated_candidate",
        )
        self.assertEqual(
            candidate["IfcFile"]["Path"],
            "room101.ifc",
        )
        after_document = json.loads(
            self.rooms_path.read_text(encoding="utf-8")
        )
        self.assertEqual(
            after_document["Rooms"][0]["Boundary"],
            source_boundary,
        )
        self.assert_sanitized(payload)

    @unittest.skipUnless(
        RESEARCH_IFC.is_file(),
        "research IFC is not available",
    )
    def test_research_ifc_room_101_preview(self) -> None:
        self.ifc_path.write_bytes(RESEARCH_IFC.read_bytes())
        rooms = room_document(
            name="Тестовая комната",
            net_area=17.231460571289062,
            boundary_area=19.926653652183532,
        )
        self.rooms_path.write_text(
            json.dumps(rooms, ensure_ascii=False),
            encoding="utf-8",
        )

        response = self.post_preview()

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        report = payload["IfcSpaceImportReport"]
        candidate = payload["IfcSpaceGeometryCandidates"][0]
        self.assertEqual(report["FoundIfcSpaces"], 1)
        self.assertEqual(report["MatchedIfcSpaces"], 1)
        self.assertEqual(
            candidate["IfcSpace"]["GlobalId"],
            "3Vmsu$eoz6VAzSuuOWXaVz",
        )
        self.assertAlmostEqual(
            candidate["AreaM2"],
            17.321458459647975,
            places=12,
        )
        self.assertAlmostEqual(
            candidate["PerimeterM"],
            16.76796776,
            places=10,
        )
        self.assertAlmostEqual(candidate["HeightM"], 2.8)
        self.assertEqual(
            candidate["geometry_status"],
            "validated_candidate",
        )
        self.assert_sanitized(payload)

    def test_ifcopenshell_unavailable_returns_503(self) -> None:
        self.write_inputs()
        with patch(
            "agent.ifc_space_importer._load_ifcopenshell",
            side_effect=IfcOpenShellUnavailable("not installed"),
        ):
            response = self.post_preview()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"]["code"],
            "ifcopenshell_unavailable",
        )
        self.assert_sanitized(response.json())

    def test_unknown_project_id_returns_404(self) -> None:
        response = self.post_preview(project_id="Unknown")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"]["code"],
            "unknown_project_id",
        )

    def test_absolute_path_is_rejected(self) -> None:
        self.write_inputs()
        response = self.post_preview(
            ifc_relative_path=str(self.ifc_path.resolve())
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"]["code"],
            "invalid_relative_path",
        )
        self.assert_sanitized(response.json())

    def test_parent_traversal_is_rejected(self) -> None:
        self.write_inputs()
        response = self.post_preview(
            ifc_relative_path=r"..\outside.ifc"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"]["code"],
            "invalid_relative_path",
        )

    def test_file_uri_is_rejected(self) -> None:
        self.write_inputs()
        response = self.post_preview(
            ifc_relative_path="file:///C:/private/room.ifc"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"]["code"],
            "invalid_relative_path",
        )
        self.assert_sanitized(response.json())

    def test_resolved_path_outside_project_is_rejected(self) -> None:
        self.write_inputs()
        self.outside_path.write_text(
            self.ifc_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        original_resolve = Path.resolve

        def escaped_resolve(path: Path) -> Path:
            if path.name == "room101.ifc":
                return original_resolve(
                    self.outside_path,
                    strict=True,
                )
            return original_resolve(path, strict=True)

        with patch(
            "agent.ifc_space_preview_api._resolve_strict",
            side_effect=escaped_resolve,
        ):
            response = self.post_preview()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"]["code"],
            "path_outside_project",
        )

    def test_wrong_extension_is_rejected(self) -> None:
        self.write_inputs()
        response = self.post_preview(
            ifc_relative_path="room101.txt"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"]["code"],
            "invalid_file_extension",
        )

    def test_wrong_rooms_extension_is_rejected(self) -> None:
        self.write_inputs()
        response = self.post_preview(
            rooms_relative_path="rooms.txt"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"]["code"],
            "invalid_file_extension",
        )

    def test_missing_file_returns_404(self) -> None:
        self.write_inputs()
        response = self.post_preview(
            ifc_relative_path="missing.ifc"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"]["code"],
            "input_file_not_found",
        )
        self.assert_sanitized(response.json())

    def test_oversized_file_returns_413(self) -> None:
        self.write_inputs()
        with patch(
            "agent.ifc_space_preview_api.MAX_IFC_FILE_BYTES",
            1,
        ):
            response = self.post_preview()
        self.assertEqual(response.status_code, 413)
        self.assertEqual(
            response.json()["detail"]["code"],
            "input_file_too_large",
        )

    def test_output_path_is_not_accepted(self) -> None:
        self.write_inputs()
        response = self.post_preview(
            extra_payload={"output_path": "result.json"}
        )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(
            (self.project_directory / "result.json").exists()
        )
        self.assert_sanitized(response.json())

    def test_damaged_json_returns_controlled_422(self) -> None:
        self.write_inputs()
        self.rooms_path.write_text("{damaged", encoding="utf-8")
        response = self.post_preview()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["code"],
            "ifc_preview_invalid",
        )
        self.assert_sanitized(response.json())

    def test_damaged_ifc_returns_controlled_422(self) -> None:
        self.write_inputs(ifc_content="not an IFC file")
        with patch(
            "ifcopenshell.open",
            side_effect=RuntimeError("damaged IFC"),
        ):
            response = self.post_preview()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["code"],
            "ifc_preview_invalid",
        )
        self.assert_sanitized(response.json())

    def test_generic_internal_failure_is_sanitized(self) -> None:
        self.write_inputs()
        internal = (
            r"INTERNAL_SENTINEL C:\private\room.ifc "
            "file://private Traceback"
        )
        with patch(
            "agent.ifc_space_preview_api.run_import",
            side_effect=RuntimeError(internal),
        ):
            response = self.post_preview()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"]["code"],
            "ifc_preview_failed",
        )
        self.assert_sanitized(response.json())

    def test_nested_diagnostic_path_is_blocked(self) -> None:
        self.write_inputs()

        def contaminated(*args, **kwargs):
            outcome = importer_run_import(*args, **kwargs)
            outcome.summary.Diagnostics.append(
                str(self.project_directory / "private.txt")
            )
            return outcome

        with patch(
            "agent.ifc_space_preview_api.run_import",
            side_effect=contaminated,
        ):
            response = self.post_preview()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"]["code"],
            "unsafe_preview_response",
        )
        self.assert_sanitized(response.json())

    def test_unsupported_geometry_is_diagnostic_result(self) -> None:
        content = synthetic_ifc(
            spaces=[
                {
                    "name": "101",
                    "outer": [
                        (0, 0),
                        (4000, 0),
                        (4000, 3000),
                        (0, 3000),
                    ],
                    "height": 2800,
                    "unsupported": True,
                }
            ]
        )
        self.write_inputs(content)
        response = self.post_preview()
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        result = payload["IfcSpaceImportReport"]["Results"][0]
        self.assertEqual(result["GeometryStatus"], "unsupported")
        self.assertEqual(
            payload["IfcSpaceGeometryCandidates"],
            [],
        )
        self.assert_sanitized(payload)

    def test_ambiguous_spaces_are_diagnostic_results(self) -> None:
        specification = {
            "name": "101",
            "outer": [
                (0, 0),
                (4000, 0),
                (4000, 3000),
                (0, 3000),
            ],
            "height": 2800,
        }
        content = synthetic_ifc(
            spaces=[
                {
                    **specification,
                    "global_id": "3Vmsu$eoz6VAzSuuOWXaV0",
                },
                {
                    **specification,
                    "global_id": "3Vmsu$eoz6VAzSuuOWXaV1",
                },
            ]
        )
        self.write_inputs(content)
        response = self.post_preview()
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(
            payload["IfcSpaceImportReport"]["AmbiguousIfcSpaces"],
            2,
        )
        self.assertEqual(
            payload["IfcSpaceGeometryCandidates"],
            [],
        )

    def test_unmatched_space_is_diagnostic_result(self) -> None:
        self.write_inputs(rooms=room_document(code="999"))
        response = self.post_preview()
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(
            payload["IfcSpaceImportReport"]["UnmatchedIfcSpaces"],
            1,
        )
        self.assertEqual(
            payload["IfcSpaceGeometryCandidates"],
            [],
        )

    def test_existing_api_routes_remain_available(self) -> None:
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["version"], "0.6.0")

        projects = self.client.get("/api/v1/projects")
        self.assertEqual(projects.status_code, 200)
        self.assertEqual(projects.json()["projects"], ["Test_01"])

        snapshot = self.client.get(
            "/api/v1/projects/Test_01/snapshot"
        )
        self.assertEqual(snapshot.status_code, 404)

        rooms = self.client.get(
            "/api/v1/projects/Test_01/rooms"
        )
        self.assertEqual(rooms.status_code, 404)

    def test_non_loopback_request_is_rejected(self) -> None:
        request = SimpleNamespace(
            client=SimpleNamespace(host="203.0.113.10"),
            headers={
                "host": "127.0.0.1",
                "x-forwarded-for": "127.0.0.1",
                "forwarded": "for=127.0.0.1",
            },
        )
        with self.assertRaises(HTTPException) as context:
            require_loopback_request(request)
        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(
            context.exception.detail["code"],
            "local_access_required",
        )

    def test_loopback_addresses_are_allowed(self) -> None:
        for host in (
            "127.0.0.1",
            "127.42.10.7",
            "::1",
            "::ffff:127.0.0.1",
        ):
            with self.subTest(host=host):
                require_loopback_request(
                    SimpleNamespace(
                        client=SimpleNamespace(host=host)
                    )
                )

    def test_missing_invalid_and_test_client_are_rejected(self) -> None:
        clients = (
            None,
            SimpleNamespace(host=None),
            SimpleNamespace(host="not-an-ip"),
            SimpleNamespace(host="testclient"),
        )
        for client in clients:
            with self.subTest(client=client):
                with self.assertRaises(HTTPException) as context:
                    require_loopback_request(
                        SimpleNamespace(client=client)
                    )
                self.assertEqual(
                    context.exception.detail["code"],
                    "local_access_required",
                )


if __name__ == "__main__":
    unittest.main()

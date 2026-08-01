from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from agent import api
from agent.model_reader import ModelSnapshot


def snapshot() -> ModelSnapshot:
    return ModelSnapshot(
        GeneratedAtUtc="2026-08-01T00:00:00Z",
        DrawingName="test.dwg",
        DrawingFullPath="C:\\test.dwg",
        AcadVersion="test",
        PluginVersion="test",
        Is64BitProcess=True,
        DrawingUnits="Meters",
        Extents={
            "Minimum": {},
            "Maximum": {},
        },
        ModelSpaceEntityCount=0,
        Layers=[],
        EntityTypes=[],
        BlockDefinitions=[],
    )


class ApiPersistenceTests(unittest.TestCase):
    def test_snapshot_rejects_non_finite_extents(self) -> None:
        with self.assertRaises(ValidationError):
            ModelSnapshot(
                GeneratedAtUtc="2026-08-01T00:00:00Z",
                DrawingName="test.dwg",
                DrawingFullPath="C:\\test.dwg",
                AcadVersion="test",
                PluginVersion="test",
                Is64BitProcess=True,
                DrawingUnits="Meters",
                Extents={
                    "Minimum": {"X": float("nan")},
                    "Maximum": {},
                },
                ModelSpaceEntityCount=0,
                Layers=[],
                EntityTypes=[],
                BlockDefinitions=[],
            )

    def test_snapshot_rejects_non_finite_opaque_payload(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            projects = Path(directory) / "projects"
            payload = snapshot().model_dump(mode="json")
            payload["Entities"] = [
                {"OpaqueMetric": float("inf")}
            ]

            with patch.object(
                api,
                "PROJECTS_DIRECTORY",
                projects,
            ):
                with self.assertRaises(ValueError):
                    api.persist_snapshot(
                        "SafeProject",
                        snapshot(),
                        payload,
                    )

            self.assertFalse(projects.exists())

    def test_snapshot_endpoint_reports_non_finite_opaque_payload(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            projects = Path(directory) / "projects"
            payload = snapshot().model_dump(mode="json")
            payload["Entities"] = [
                {"OpaqueMetric": float("-inf")}
            ]

            with patch.object(
                api,
                "PROJECTS_DIRECTORY",
                projects,
            ):
                with self.assertRaises(HTTPException) as raised:
                    api.save_project_snapshot(
                        "SafeProject",
                        payload,
                    )

            self.assertEqual(raised.exception.status_code, 422)
            self.assertEqual(
                raised.exception.detail,
                (
                    "Снимок модели содержит недопустимое "
                    "числовое значение."
                ),
            )
            self.assertFalse(projects.exists())

    def test_snapshot_storage_failure_uses_safe_http_contract(
        self,
    ) -> None:
        sensitive_detail = r"C:\private\snapshot.json"

        with patch.object(
            api,
            "persist_snapshot",
            side_effect=OSError(sensitive_detail),
        ):
            response = TestClient(
                api.app,
                raise_server_exceptions=False,
            ).post(
                "/api/v1/projects/SafeProject/snapshot",
                json=snapshot().model_dump(mode="json"),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {"detail": api.STORAGE_ERROR_DETAIL},
        )
        self.assertNotIn(
            sensitive_detail,
            response.json()["detail"],
        )

    def test_analysis_storage_failure_uses_safe_http_contract(
        self,
    ) -> None:
        sensitive_detail = r"C:\private\analysis_report.json"
        payload = snapshot().model_dump(mode="json")

        with (
            patch.object(
                api,
                "load_project_snapshot_payload",
                return_value=payload,
            ),
            patch.object(
                api,
                "load_project_rooms",
                return_value=None,
            ),
            patch.object(
                api,
                "analyze_snapshot",
                return_value={"status": "passed"},
            ),
            patch.object(
                api,
                "persist_analysis_report",
                side_effect=OSError(sensitive_detail),
            ),
        ):
            response = TestClient(
                api.app,
                raise_server_exceptions=False,
            ).post(
                "/api/v1/projects/SafeProject/analyze"
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {"detail": api.STORAGE_ERROR_DETAIL},
        )
        self.assertNotIn(
            sensitive_detail,
            response.json()["detail"],
        )

    def test_snapshot_loader_rejects_json_constants(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            projects = Path(directory) / "projects"
            snapshot_path = (
                projects
                / "SafeProject"
                / "exports"
                / "model_snapshot.json"
            )
            snapshot_path.parent.mkdir(parents=True)
            snapshot_path.write_text(
                '{"OpaqueMetric": NaN}',
                encoding="utf-8",
            )

            with patch.object(
                api,
                "PROJECTS_DIRECTORY",
                projects,
            ):
                with self.assertRaises(HTTPException) as raised:
                    api.load_project_snapshot_payload(
                        "SafeProject"
                    )

            self.assertEqual(raised.exception.status_code, 422)
            self.assertEqual(
                raised.exception.detail,
                (
                    "Снимок модели проекта 'SafeProject' "
                    "содержит недопустимые данные."
                ),
            )
            self.assertNotIn(
                str(snapshot_path),
                str(raised.exception.detail),
            )

    def test_atomic_write_replaces_and_cleans_temp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "current.json"
            destination.write_text("old", encoding="utf-8")

            api._write_text_atomically(destination, "new")

            self.assertEqual(
                destination.read_text(encoding="utf-8"),
                "new",
            )
            self.assertEqual(
                list(root.glob(".current.json.*.tmp")),
                [],
            )

    def test_atomic_write_cleans_temp_after_replace_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "current.json"

            with patch.object(
                Path,
                "replace",
                side_effect=OSError("synthetic replace failure"),
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "synthetic replace failure",
                ):
                    api._write_text_atomically(
                        destination,
                        "new",
                    )

            self.assertFalse(destination.exists())
            self.assertEqual(
                list(root.glob(".current.json.*.tmp")),
                [],
            )

    def test_snapshot_publishes_history_and_current(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            projects = Path(directory) / "projects"

            with patch.object(
                api,
                "PROJECTS_DIRECTORY",
                projects,
            ):
                current, history = api.persist_snapshot(
                    "SafeProject",
                    snapshot(),
                )

            self.assertTrue(current.is_file())
            self.assertTrue(history.is_file())
            self.assertEqual(
                current.read_bytes(),
                history.read_bytes(),
            )
            self.assertEqual(
                json.loads(
                    current.read_text(encoding="utf-8")
                )["DrawingName"],
                "test.dwg",
            )
            self.assertEqual(
                list(projects.rglob("*.tmp")),
                [],
            )

    def test_snapshot_history_failure_preserves_current(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            projects = Path(directory) / "projects"
            current = (
                projects
                / "SafeProject"
                / "exports"
                / "model_snapshot.json"
            )
            current.parent.mkdir(parents=True)
            current.write_text("old", encoding="utf-8")
            calls: list[Path] = []

            def fail_history(
                destination: Path,
                text: str,
            ) -> None:
                calls.append(destination)
                raise OSError("synthetic history failure")

            with (
                patch.object(
                    api,
                    "PROJECTS_DIRECTORY",
                    projects,
                ),
                patch.object(
                    api,
                    "_write_text_atomically",
                    side_effect=fail_history,
                ),
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "synthetic history failure",
                ):
                    api.persist_snapshot(
                        "SafeProject",
                        snapshot(),
                    )

            self.assertEqual(
                current.read_text(encoding="utf-8"),
                "old",
            )
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0].parent.name, "history")

    def test_analysis_publishes_paths_history_and_current(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            projects = Path(directory) / "projects"
            report: dict[str, object] = {"status": "passed"}

            with patch.object(
                api,
                "PROJECTS_DIRECTORY",
                projects,
            ):
                current, history = api.persist_analysis_report(
                    "SafeProject",
                    report,
                )

            self.assertEqual(report["report_path"], str(current))
            self.assertEqual(report["history_path"], str(history))
            self.assertEqual(
                current.read_bytes(),
                history.read_bytes(),
            )
            payload = json.loads(
                current.read_text(encoding="utf-8")
            )
            self.assertEqual(payload["report_path"], str(current))
            self.assertEqual(payload["history_path"], str(history))
            self.assertEqual(
                list(projects.rglob("*.tmp")),
                [],
            )

    def test_analysis_rejects_non_finite_report_before_write(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            projects = Path(directory) / "projects"

            with patch.object(
                api,
                "PROJECTS_DIRECTORY",
                projects,
            ):
                with self.assertRaises(ValueError):
                    api.persist_analysis_report(
                        "SafeProject",
                        {"metric": float("nan")},
                    )

            self.assertFalse(projects.exists())

    def test_analysis_history_failure_preserves_current(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            projects = Path(directory) / "projects"
            current = (
                projects
                / "SafeProject"
                / "exports"
                / "analysis"
                / "analysis_report.json"
            )
            current.parent.mkdir(parents=True)
            current.write_text("old", encoding="utf-8")
            calls: list[Path] = []

            def fail_history(
                destination: Path,
                text: str,
            ) -> None:
                calls.append(destination)
                raise OSError("synthetic history failure")

            with (
                patch.object(
                    api,
                    "PROJECTS_DIRECTORY",
                    projects,
                ),
                patch.object(
                    api,
                    "_write_text_atomically",
                    side_effect=fail_history,
                ),
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "synthetic history failure",
                ):
                    api.persist_analysis_report(
                        "SafeProject",
                        {"status": "passed"},
                    )

            self.assertEqual(
                current.read_text(encoding="utf-8"),
                "old",
            )
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0].parent.name, "history")

    def test_resolver_rejects_resolved_path_outside_projects(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            projects = root / "projects"
            outside = root / "outside"
            candidate = projects / "linked"
            projects.mkdir()
            outside.mkdir()
            original_resolve = Path.resolve

            def resolve_with_escape(
                path: Path,
                *args: object,
                **kwargs: object,
            ) -> Path:
                if path == candidate:
                    return outside
                return original_resolve(
                    path,
                    *args,
                    **kwargs,
                )

            with (
                patch.object(
                    api,
                    "PROJECTS_DIRECTORY",
                    projects,
                ),
                patch.object(
                    Path,
                    "resolve",
                    autospec=True,
                    side_effect=resolve_with_escape,
                ),
            ):
                with self.assertRaises(HTTPException) as raised:
                    api.resolve_project_directory("linked")

            self.assertEqual(raised.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()

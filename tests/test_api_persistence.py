from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

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

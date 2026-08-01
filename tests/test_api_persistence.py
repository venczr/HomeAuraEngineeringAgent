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
from agent.model_reader import (
    MAX_LAYER_COLOR_INDEX,
    MAX_SNAPSHOT_COUNT,
    MIN_LAYER_COLOR_INDEX,
    ModelSnapshot,
)


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
    def test_snapshot_accepts_large_finite_and_reversed_extents(
        self,
    ) -> None:
        payload = snapshot().model_dump()
        payload["Extents"] = {
            "Minimum": {"X": -1e307, "Y": 10, "Z": -5},
            "Maximum": {"X": 1e307, "Y": -10, "Z": 5},
        }

        validated = ModelSnapshot.model_validate(payload)

        self.assertEqual(-1e307, validated.Extents.Minimum.X)
        self.assertEqual(1e307, validated.Extents.Maximum.X)
        self.assertEqual(10.0, validated.Extents.Minimum.Y)
        self.assertEqual(-10.0, validated.Extents.Maximum.Y)

    def test_snapshot_rejects_finite_endpoint_span_overflow(
        self,
    ) -> None:
        for axis in ("X", "Y", "Z"):
            with self.subTest(axis=axis):
                payload = snapshot().model_dump()
                payload["Extents"] = {
                    "Minimum": {axis: -1e308},
                    "Maximum": {axis: 1e308},
                }

                with self.assertRaises(ValidationError):
                    ModelSnapshot.model_validate(payload)

    def test_snapshot_coordinates_accept_numeric_tokens(self) -> None:
        payload = snapshot().model_dump()
        payload["Extents"] = {
            "Minimum": {"X": 0, "Y": -2, "Z": 1.25},
            "Maximum": {"X": 3, "Y": 4.5, "Z": 6},
        }

        validated = ModelSnapshot.model_validate(payload)

        self.assertEqual(0.0, validated.Extents.Minimum.X)
        self.assertEqual(-2.0, validated.Extents.Minimum.Y)
        self.assertEqual(1.25, validated.Extents.Minimum.Z)
        self.assertEqual(3.0, validated.Extents.Maximum.X)
        self.assertEqual(4.5, validated.Extents.Maximum.Y)
        self.assertEqual(6.0, validated.Extents.Maximum.Z)

    def test_snapshot_coordinates_reject_coercion(self) -> None:
        for axis in ("X", "Y", "Z"):
            for invalid_value in (True, False, "1.25"):
                with self.subTest(
                    axis=axis,
                    invalid_value=invalid_value,
                ):
                    payload = snapshot().model_dump()
                    payload["Extents"] = {
                        "Minimum": {axis: invalid_value},
                        "Maximum": {},
                    }

                    with self.assertRaises(ValidationError):
                        ModelSnapshot.model_validate(payload)

    def test_snapshot_scalars_accept_producer_boundaries(self) -> None:
        payload = snapshot().model_dump()
        payload["Is64BitProcess"] = False
        payload["Layers"] = [
            {
                "Name": "minimum-color",
                "IsOff": True,
                "IsFrozen": False,
                "IsLocked": True,
                "ColorIndex": MIN_LAYER_COLOR_INDEX,
            },
            {
                "Name": "maximum-color",
                "ColorIndex": MAX_LAYER_COLOR_INDEX,
            },
        ]
        payload["BlockDefinitions"] = [
            {
                "Name": "stateful-block",
                "IsAnonymous": True,
                "IsExternalReference": False,
            }
        ]

        validated = ModelSnapshot.model_validate(payload)

        self.assertFalse(validated.Is64BitProcess)
        self.assertTrue(validated.Layers[0].IsOff)
        self.assertFalse(validated.Layers[0].IsFrozen)
        self.assertTrue(validated.Layers[0].IsLocked)
        self.assertEqual(
            MIN_LAYER_COLOR_INDEX,
            validated.Layers[0].ColorIndex,
        )
        self.assertEqual(
            MAX_LAYER_COLOR_INDEX,
            validated.Layers[1].ColorIndex,
        )
        self.assertTrue(validated.BlockDefinitions[0].IsAnonymous)
        self.assertFalse(
            validated.BlockDefinitions[0].IsExternalReference
        )

    def test_snapshot_booleans_reject_coercion(self) -> None:
        invalid_values = (0, 1, "false", "true", "yes")
        targets = (
            "Is64BitProcess",
            "LayerSnapshot.IsOff",
            "LayerSnapshot.IsFrozen",
            "LayerSnapshot.IsLocked",
            "BlockSnapshot.IsAnonymous",
            "BlockSnapshot.IsExternalReference",
        )

        for target in targets:
            for invalid_value in invalid_values:
                with self.subTest(
                    target=target,
                    invalid_value=invalid_value,
                ):
                    payload = snapshot().model_dump()
                    if target == "Is64BitProcess":
                        payload[target] = invalid_value
                    elif target.startswith("LayerSnapshot."):
                        field_name = target.rsplit(".", 1)[1]
                        payload["Layers"] = [
                            {
                                "Name": "invalid-bool-layer",
                                field_name: invalid_value,
                            }
                        ]
                    else:
                        field_name = target.rsplit(".", 1)[1]
                        payload["BlockDefinitions"] = [
                            {
                                "Name": "invalid-bool-block",
                                field_name: invalid_value,
                            }
                        ]

                    with self.assertRaises(ValidationError):
                        ModelSnapshot.model_validate(payload)

    def test_snapshot_color_index_rejects_non_producer_values(
        self,
    ) -> None:
        invalid_values = (
            MIN_LAYER_COLOR_INDEX - 1,
            MAX_LAYER_COLOR_INDEX + 1,
            True,
            1.0,
            "1",
        )

        for invalid_value in invalid_values:
            with self.subTest(invalid_value=invalid_value):
                payload = snapshot().model_dump()
                payload["Layers"] = [
                    {
                        "Name": "invalid-color-layer",
                        "ColorIndex": invalid_value,
                    }
                ]

                with self.assertRaises(ValidationError):
                    ModelSnapshot.model_validate(payload)

    def test_snapshot_counts_accept_producer_boundaries(self) -> None:
        payload = snapshot().model_dump()
        payload["ModelSpaceEntityCount"] = MAX_SNAPSHOT_COUNT
        payload["EntityTypes"] = [
            {"Count": MAX_SNAPSHOT_COUNT}
        ]
        payload["BlockDefinitions"] = [
            {
                "Name": "maximum-count-block",
                "EntityCount": MAX_SNAPSHOT_COUNT,
            }
        ]

        validated = ModelSnapshot.model_validate(payload)

        self.assertEqual(
            MAX_SNAPSHOT_COUNT,
            validated.ModelSpaceEntityCount,
        )
        self.assertEqual(
            MAX_SNAPSHOT_COUNT,
            validated.EntityTypes[0].Count,
        )
        self.assertEqual(
            MAX_SNAPSHOT_COUNT,
            validated.BlockDefinitions[0].EntityCount,
        )

    def test_snapshot_counts_reject_non_producer_values(self) -> None:
        invalid_values = (
            -1,
            MAX_SNAPSHOT_COUNT + 1,
            True,
            1.0,
            "1",
        )
        targets = (
            "ModelSpaceEntityCount",
            "EntityTypeSnapshot.Count",
            "BlockSnapshot.EntityCount",
        )

        for target in targets:
            for invalid_value in invalid_values:
                with self.subTest(
                    target=target,
                    invalid_value=invalid_value,
                ):
                    payload = snapshot().model_dump()
                    if target == "ModelSpaceEntityCount":
                        payload[target] = invalid_value
                    elif target == "EntityTypeSnapshot.Count":
                        payload["EntityTypes"] = [
                            {"Count": invalid_value}
                        ]
                    else:
                        payload["BlockDefinitions"] = [
                            {
                                "Name": "invalid-count-block",
                                "EntityCount": invalid_value,
                            }
                        ]

                    with self.assertRaises(ValidationError):
                        ModelSnapshot.model_validate(payload)

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

    def test_snapshot_write_rejects_descendant_escape(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            projects = root / "projects"
            project = projects / "SafeProject"
            escaped_exports = project / "exports"
            outside = root / "outside"
            projects.mkdir()
            outside.mkdir()
            original_resolve = Path.resolve

            def resolve_with_escape(
                path: Path,
                *args: object,
                **kwargs: object,
            ) -> Path:
                if path == escaped_exports:
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
                    api.persist_snapshot(
                        "SafeProject",
                        snapshot(),
                    )

            self.assertEqual(raised.exception.status_code, 400)
            self.assertEqual(
                raised.exception.detail,
                api.PROJECT_PATH_ESCAPE_DETAIL,
            )
            self.assertEqual(list(outside.iterdir()), [])
            self.assertFalse(project.exists())

    def test_snapshot_read_rejects_descendant_escape(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            projects = root / "projects"
            project = projects / "SafeProject"
            escaped_snapshot = (
                project / "exports" / "model_snapshot.json"
            )
            outside = root / "outside.json"
            project.mkdir(parents=True)
            outside.write_text("{}", encoding="utf-8")
            original_resolve = Path.resolve

            def resolve_with_escape(
                path: Path,
                *args: object,
                **kwargs: object,
            ) -> Path:
                if path == escaped_snapshot:
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
                    api.load_project_snapshot_payload("SafeProject")

            self.assertEqual(raised.exception.status_code, 400)
            self.assertEqual(
                raised.exception.detail,
                api.PROJECT_PATH_ESCAPE_DETAIL,
            )

    def test_analysis_write_rejects_descendant_escape(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            projects = root / "projects"
            project = projects / "SafeProject"
            escaped_analysis = (
                project / "exports" / "analysis"
            )
            outside = root / "outside"
            projects.mkdir()
            outside.mkdir()
            original_resolve = Path.resolve

            def resolve_with_escape(
                path: Path,
                *args: object,
                **kwargs: object,
            ) -> Path:
                if path == escaped_analysis:
                    return outside
                return original_resolve(
                    path,
                    *args,
                    **kwargs,
                )

            report: dict[str, object] = {"status": "passed"}
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
                    api.persist_analysis_report(
                        "SafeProject",
                        report,
                    )

            self.assertEqual(raised.exception.status_code, 400)
            self.assertEqual(
                raised.exception.detail,
                api.PROJECT_PATH_ESCAPE_DETAIL,
            )
            self.assertEqual(list(outside.iterdir()), [])
            self.assertFalse(project.exists())

    def test_analysis_room_read_rejects_descendant_escape(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            projects = root / "projects"
            project = projects / "SafeProject"
            escaped_rooms = (
                project
                / "exports"
                / "rooms"
                / "rooms.json"
            )
            outside = root / "outside.json"
            project.mkdir(parents=True)
            outside.write_text("{}", encoding="utf-8")
            original_resolve = Path.resolve

            def resolve_with_escape(
                path: Path,
                *args: object,
                **kwargs: object,
            ) -> Path:
                if path == escaped_rooms:
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
                    api.load_project_rooms("SafeProject")

            self.assertEqual(raised.exception.status_code, 400)
            self.assertEqual(
                raised.exception.detail,
                api.PROJECT_PATH_ESCAPE_DETAIL,
            )


if __name__ == "__main__":
    unittest.main()

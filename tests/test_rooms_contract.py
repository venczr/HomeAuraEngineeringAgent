from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from agent import rooms_api
from agent.rooms_api import RoomExportReport


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]


class RoomContractTests(unittest.TestCase):
    def test_non_finite_room_numerics_are_rejected(self) -> None:
        room = {
            "SourceHandle": "MARKER",
            "SourceLayer": "MAGIROOMTAG",
            "Position": {"X": 2.0, "Y": 1.5, "Z": 0.0},
            "Code": "101",
            "Name": "Geometry room",
            "NetAreaM2": 11.5,
        }
        report = {
            "FormatVersion": "1.1",
            "ParserVersion": "test",
            "GeneratedAtUtc": "2026-08-01T00:00:00Z",
            "DrawingName": "Geometry.dwg",
            "DrawingFullPath": "C:\\Projects\\Geometry.dwg",
            "FoundMarkers": 1,
            "Rooms": [room],
        }

        cases = (
            ("room area", ("NetAreaM2",), float("nan")),
            ("room position", ("Position", "X"), float("inf")),
        )
        for label, path, value in cases:
            candidate = json.loads(json.dumps(report))
            target = candidate["Rooms"][0]
            for component in path[:-1]:
                target = target[component]
            target[path[-1]] = value

            with self.subTest(label=label):
                with self.assertRaises(ValidationError):
                    RoomExportReport.model_validate(candidate)

    def test_old_json_without_boundary_is_readable(self) -> None:
        fixture_path = (
            ROOT_DIRECTORY
            / "tests"
            / "fixtures"
            / "rooms_v1_0.json"
        )

        report = RoomExportReport.model_validate_json(
            fixture_path.read_text(encoding="utf-8")
        )

        self.assertEqual(report.FormatVersion, "1.0")
        self.assertEqual(report.FoundBoundaryCandidates, 0)
        self.assertEqual(report.ValidBoundaryCandidates, 0)
        self.assertEqual(report.BoundaryDiagnostics, [])
        self.assertIsNone(report.Rooms[0].Boundary)
        self.assertEqual(report.Rooms[0].NetAreaM2, 17.25)
        self.assertEqual(
            report.Rooms[0].MagiCadNetAreaM2,
            17.25,
        )

    def test_extended_boundary_contract_round_trip(self) -> None:
        payload = {
            "FormatVersion": "1.1",
            "ParserVersion": "MagiCAD-R-2024-UR2-rev2",
            "GeneratedAtUtc": "2026-07-25T20:00:00Z",
            "DrawingName": "Geometry.dwg",
            "DrawingFullPath": "C:\\Projects\\Geometry.dwg",
            "FoundMarkers": 1,
            "FoundBoundaryCandidates": 1,
            "ValidBoundaryCandidates": 1,
            "BoundaryDiagnostics": [],
            "Rooms": [
                {
                    "SourceHandle": "MARKER",
                    "SourceLayer": "MAGIROOMTAG",
                    "Position": {
                        "X": 2.0,
                        "Y": 1.5,
                        "Z": 0.0,
                    },
                    "Code": "101",
                    "Name": "Geometry room",
                    "NetAreaM2": 11.5,
                    "MagiCadNetAreaM2": 11.5,
                    "BoundaryAreaDifferenceM2": 0.5,
                    "BoundaryAreaDifferencePercent": (
                        0.5 / 11.5 * 100
                    ),
                    "Boundary": {
                        "SourceHandle": "BOUNDARY",
                        "SourceObjectType": "LWPOLYLINE",
                        "SourceLayer": "ROOMS",
                        "Vertices": [
                            {
                                "X": 0.0,
                                "Y": 0.0,
                                "Z": 0.0,
                                "Bulge": 0.0,
                                "SegmentType": "Line",
                            },
                            {
                                "X": 4.0,
                                "Y": 0.0,
                                "Z": 0.0,
                                "Bulge": 0.0,
                                "SegmentType": "Line",
                            },
                            {
                                "X": 4.0,
                                "Y": 3.0,
                                "Z": 0.0,
                                "Bulge": 0.0,
                                "SegmentType": "Line",
                            },
                            {
                                "X": 0.0,
                                "Y": 3.0,
                                "Z": 0.0,
                                "Bulge": 0.0,
                                "SegmentType": "Line",
                            },
                        ],
                        "IsClosed": True,
                        "ContourAreaDrawingUnits2": 12.0,
                        "ContourAreaM2": 12.0,
                        "PerimeterDrawingUnits": 14.0,
                        "PerimeterM": 14.0,
                        "OriginalDirection": "CCW",
                        "Direction": "CCW",
                        "DrawingUnits": "Meters",
                        "MetersPerDrawingUnit": 1.0,
                        "GeometrySource": (
                            "AutoCAD.ModelSpace.Polyline"
                        ),
                        "SourceVertices": [],
                        "OriginalClosedFlag": True,
                        "LogicalClosureMethod": "AutoCAD Closed flag",
                        "ZDeviationDrawingUnits": 0.0,
                        "ZDeviationM": 0.0,
                        "IsPlanar": True,
                        "Polyline3dType": None,
                        "HasMagiCadData": False,
                        "Diagnostics": {
                            "IsSupported": True,
                            "IsValid": True,
                            "DuplicateVerticesRemoved": 0,
                            "IsSelfIntersecting": False,
                            "MinimumVertexCount": 3,
                            "VertexToleranceDrawingUnits": (
                                0.0001
                            ),
                            "ArcChordToleranceDrawingUnits": (
                                0.001
                            ),
                            "ContainingMarkerHandles": [
                                "MARKER"
                            ],
                            "Messages": [],
                        },
                    },
                    "BoundaryAreaM2": 12.0,
                    "geometry_status": "validated",
                    "area_match_status": "ok",
                    "boundary_selection_status": "selected",
                    "boundary_selection_warning": None,
                    "boundary_candidates": [
                        {
                            "SourceHandle": "BOUNDARY",
                            "SourceObjectType": "LWPOLYLINE",
                            "SourceLayer": "ROOMS",
                            "GeometrySource": (
                                "AutoCAD.ModelSpace.Polyline"
                            ),
                            "HasMagiCadData": False,
                            "PriorityTier": 2,
                            "PriorityReason": (
                                "Other containing boundary"
                            ),
                            "BoundaryAreaM2": 12.0,
                            "AreaDifferenceM2": 0.5,
                            "AreaDifferencePercent": (
                                0.5 / 11.5 * 100
                            ),
                            "AreaMatchStatus": "ok",
                            "GeometryStatus": "validated",
                            "IsSelected": True,
                        }
                    ],
                    "Warnings": [],
                }
            ],
            "Warnings": [],
        }

        report = RoomExportReport.model_validate(payload)
        serialized = report.model_dump_json(indent=2)
        restored = json.loads(serialized)

        room = restored["Rooms"][0]
        self.assertEqual(room["NetAreaM2"], 11.5)
        self.assertEqual(room["MagiCadNetAreaM2"], 11.5)
        self.assertEqual(
            room["Boundary"]["ContourAreaM2"],
            12.0,
        )
        self.assertAlmostEqual(
            room["BoundaryAreaDifferenceM2"],
            0.5,
        )
        self.assertEqual(
            room["Boundary"]["LogicalClosureMethod"],
            "AutoCAD Closed flag",
        )
        self.assertEqual(
            room["geometry_status"],
            "validated",
        )
        self.assertEqual(
            room["area_match_status"],
            "ok",
        )
        self.assertEqual(
            room["boundary_candidates"][0]["PriorityTier"],
            2,
        )

    def test_atomic_write_replaces_complete_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "rooms.json"
            destination.write_text("old", encoding="utf-8")

            rooms_api._write_text_atomically(
                destination,
                '{"status":"new"}',
            )

            self.assertEqual(
                destination.read_text(encoding="utf-8"),
                '{"status":"new"}',
            )
            self.assertEqual(
                list(root.glob(".rooms.json.*.tmp")),
                [],
            )

    def test_atomic_write_cleans_temporary_file_on_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "rooms.json"

            with patch.object(
                Path,
                "replace",
                side_effect=OSError("synthetic replace failure"),
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "synthetic replace failure",
                ):
                    rooms_api._write_text_atomically(
                        destination,
                        "new",
                    )

            self.assertFalse(destination.exists())
            self.assertEqual(
                list(root.glob(".rooms.json.*.tmp")),
                [],
            )

    def test_history_failure_preserves_current_rooms(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            projects = Path(directory) / "projects"
            current = (
                projects
                / "SafeProject"
                / "exports"
                / "rooms"
                / "rooms.json"
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

            report = RoomExportReport(
                FormatVersion="1.1",
                ParserVersion="test",
                GeneratedAtUtc="2026-08-01T00:00:00Z",
                DrawingName="test.dwg",
                DrawingFullPath="C:\\test.dwg",
                FoundMarkers=0,
            )

            with (
                patch.object(
                    rooms_api,
                    "PROJECTS_DIRECTORY",
                    projects,
                ),
                patch.object(
                    rooms_api,
                    "_write_text_atomically",
                    side_effect=fail_history,
                ),
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "synthetic history failure",
                ):
                    rooms_api.save_rooms(
                        "SafeProject",
                        report,
                    )

            self.assertEqual(
                current.read_text(encoding="utf-8"),
                "old",
            )
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0].parent.name, "history")

    def test_save_rooms_publishes_history_and_current(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            projects = Path(directory) / "projects"
            report = RoomExportReport(
                FormatVersion="1.1",
                ParserVersion="test",
                GeneratedAtUtc="2026-08-01T00:00:00Z",
                DrawingName="test.dwg",
                DrawingFullPath="C:\\test.dwg",
                FoundMarkers=0,
            )

            with patch.object(
                rooms_api,
                "PROJECTS_DIRECTORY",
                projects,
            ):
                result = rooms_api.save_rooms(
                    "SafeProject",
                    report,
                )

            current = Path(result["rooms_path"])
            history = Path(result["history_path"])
            self.assertTrue(current.is_file())
            self.assertTrue(history.is_file())
            self.assertEqual(
                current.read_bytes(),
                history.read_bytes(),
            )
            self.assertEqual(
                list(projects.rglob("*.tmp")),
                [],
            )

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
                    rooms_api,
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
                    rooms_api.resolve_project_directory(
                        "linked"
                    )

            self.assertEqual(raised.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()

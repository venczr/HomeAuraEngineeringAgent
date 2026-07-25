from __future__ import annotations

import json
import unittest
from pathlib import Path

from agent.rooms_api import RoomExportReport


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]


class RoomContractTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

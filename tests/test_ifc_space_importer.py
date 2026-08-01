from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from agent.ifc_space_models import (
    IfcPoint3D,
    IfcSpaceGeometry,
    IfcUnitInfo,
)
from agent.ifc_space_importer import (
    IfcGeometryUnsupported,
    IfcOpenShellUnavailable,
    IfcSpaceImportError,
    MAX_ROOMS_JSON_BYTES,
    _indexed_curve_points,
    _load_ifcopenshell,
    _read_rooms_document,
    analyze_ifc_spaces,
    run_import,
)
from agent.rooms_api import RoomExportReport


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]


class StepBuilder:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def add(self, expression: str) -> str:
        reference = f"#{len(self.lines) + 1}"
        self.lines.append(f"{reference}={expression};")
        return reference


def number(value: float) -> str:
    result = f"{float(value):.12g}"
    return result if "." in result else f"{result}."


def point_list(points: list[tuple[float, float]]) -> str:
    return ",".join(
        f"({number(x)},{number(y)})"
        for x, y in points
    )


def synthetic_ifc(
    *,
    length_unit: str = "millimetre",
    spaces: list[dict] | None = None,
    site_translation: tuple[float, float, float] = (0, 0, 0),
    building_translation: tuple[float, float, float] = (0, 0, 0),
    storey_translation: tuple[float, float, float] = (0, 0, 0),
) -> str:
    if spaces is None:
        scale = 1000.0 if length_unit == "millimetre" else 1.0
        spaces = [
            {
                "name": "101",
                "global_id": "3Vmsu$eoz6VAzSuuOWXaVz",
                "long_name": "Test room",
                "outer": [
                    (0, 0),
                    (4 * scale, 0),
                    (4 * scale, 3 * scale),
                    (0, 3 * scale),
                    (0, 0),
                ],
                "height": 2.8 * scale,
            }
        ]

    builder = StepBuilder()
    origin = builder.add("IFCCARTESIANPOINT((0.,0.,0.))")
    direction_x = builder.add("IFCDIRECTION((1.,0.,0.))")
    direction_y = builder.add("IFCDIRECTION((0.,1.,0.))")
    direction_z = builder.add("IFCDIRECTION((0.,0.,1.))")

    prefix = ".MILLI." if length_unit == "millimetre" else "$"
    length = builder.add(
        f"IFCSIUNIT(*,.LENGTHUNIT.,{prefix},.METRE.)"
    )
    area = builder.add(
        "IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.)"
    )
    units = builder.add(
        f"IFCUNITASSIGNMENT(({length},{area}))"
    )
    world_axis = builder.add(
        f"IFCAXIS2PLACEMENT3D({origin},{direction_z},{direction_x})"
    )
    world_2d = builder.add("IFCDIRECTION((0.,1.))")
    context = builder.add(
        "IFCGEOMETRICREPRESENTATIONCONTEXT("
        f"$,'Model',3,1.E-05,{world_axis},{world_2d})"
    )
    project = builder.add(
        "IFCPROJECT('2OWEq6mDnAGvFCIDPiA97p',$,'Project',$,$,$,$,"
        f"({context}),{units})"
    )

    def placement(
        parent: str | None,
        translation: tuple[float, float, float],
    ) -> str:
        point = builder.add(
            "IFCCARTESIANPOINT(("
            + ",".join(number(value) for value in translation)
            + "))"
        )
        axis = builder.add(
            f"IFCAXIS2PLACEMENT3D({point},{direction_z},{direction_x})"
        )
        return builder.add(
            f"IFCLOCALPLACEMENT({parent or '$'},{axis})"
        )

    site_placement = placement(None, site_translation)
    site = builder.add(
        "IFCSITE('2Xyt0Dtjb66AM00Vnw9lpG',$,'Site',$,$,"
        f"{site_placement},$,$,.ELEMENT.,$,$,$,$,$)"
    )
    building_placement = placement(
        site_placement,
        building_translation,
    )
    building = builder.add(
        "IFCBUILDING('1kDE4UYl903ebi3UdgvjXG',$,'Building',$,$,"
        f"{building_placement},$,$,.ELEMENT.,$,$,$)"
    )
    storey_placement = placement(
        building_placement,
        storey_translation,
    )
    storey = builder.add(
        "IFCBUILDINGSTOREY('0oQei_Jnn60QnqOIJ3NBzE',$,'Level 1',$,$,"
        f"{storey_placement},$,'Level 1',.ELEMENT.,"
        f"{number(storey_translation[2])})"
    )

    builder.add(
        "IFCRELAGGREGATES('1UM6whrE53pxORh$ShuIqY',$,'ProjectSites',$,"
        f"{project},({site}))"
    )
    builder.add(
        "IFCRELAGGREGATES('0axds$rTr2Tf65pT5k3zIJ',$,'SiteBuildings',$,"
        f"{site},({building}))"
    )
    builder.add(
        "IFCRELAGGREGATES('28$GHloeX7BBCa$cs7Ehsa',$,'BuildingStoreys',$,"
        f"{building},({storey}))"
    )

    space_references: list[str] = []
    for index, specification in enumerate(spaces):
        space_placement = placement(
            storey_placement,
            specification.get("translation", (0, 0, 0)),
        )
        outer_points = builder.add(
            "IFCCARTESIANPOINTLIST2D(("
            + point_list(specification["outer"])
            + "))"
        )
        outer_curve = builder.add(
            f"IFCINDEXEDPOLYCURVE({outer_points},$,$)"
        )

        inner_curves: list[str] = []
        for hole in specification.get("holes", []):
            hole_points = builder.add(
                "IFCCARTESIANPOINTLIST2D(("
                + point_list(hole)
                + "))"
            )
            inner_curves.append(
                builder.add(
                    f"IFCINDEXEDPOLYCURVE({hole_points},$,$)"
                )
            )

        if inner_curves:
            profile = builder.add(
                "IFCARBITRARYPROFILEDEFWITHVOIDS("
                f".AREA.,$,{outer_curve},"
                f"({','.join(inner_curves)}))"
            )
        else:
            profile = builder.add(
                "IFCARBITRARYCLOSEDPROFILEDEF("
                f".AREA.,$,{outer_curve})"
            )

        if specification.get("unsupported", False):
            item = builder.add(
                "IFCBOUNDINGBOX("
                f"{origin},{number(1)},{number(1)},{number(1)})"
            )
            representation_type = "BoundingBox"
        else:
            item = builder.add(
                "IFCEXTRUDEDAREASOLID("
                f"{profile},{world_axis},{direction_z},"
                f"{number(specification['height'])})"
            )
            representation_type = "SweptSolid"

        representation = builder.add(
            "IFCSHAPEREPRESENTATION("
            f"{context},'Body','{representation_type}',({item}))"
        )
        shape = builder.add(
            f"IFCPRODUCTDEFINITIONSHAPE($,$,({representation}))"
        )
        global_id = specification.get(
            "global_id",
            f"3Vmsu$eoz6VAzSuuOWXaV{index}",
        )
        name = specification.get("name", "101")
        long_name = specification.get("long_name", "Test room")
        space = builder.add(
            "IFCSPACE("
            f"'{global_id}',$,'{name}',$,'RoomType',"
            f"{space_placement},{shape},'{long_name}',"
            ".ELEMENT.,.INTERNAL.,$)"
        )
        space_references.append(space)

    builder.add(
        "IFCRELAGGREGATES('2WcsdoY5fEi92TV4bEFqav',$,'StoreySpaces',$,"
        f"{storey},({','.join(space_references)}))"
    )

    return "\n".join(
        [
            "ISO-10303-21;",
            "HEADER;",
            "FILE_DESCRIPTION(('ViewDefinition[ReferenceView_V1.2]'),'2;1');",
            "FILE_NAME('synthetic.ifc','2026-07-26T00:00:00',(' '),(' '),'HomeAura tests',' ','');",
            "FILE_SCHEMA(('IFC4'));",
            "ENDSEC;",
            "DATA;",
            *builder.lines,
            "ENDSEC;",
            "END-ISO-10303-21;",
        ]
    )


def room_document(
    *,
    code: str = "101",
    name: str = "Test room",
    net_area: float = 12.0,
    boundary_area: float | None = 13.0,
    saved_global_id: str | None = None,
) -> dict:
    room = {
        "SourceHandle": "MARKER",
        "SourceLayer": "MAGIROOMTAG",
        "Position": {"X": 1.0, "Y": 1.0, "Z": 0.0},
        "Code": code,
        "Name": name,
        "NetAreaM2": net_area,
        "MagiCadNetAreaM2": net_area,
        "BoundaryAreaM2": boundary_area,
        "Boundary": {
            "SourceHandle": "101DA95",
            "ContourAreaM2": boundary_area,
        }
        if boundary_area is not None
        else None,
        "geometry_status": "provisional",
    }
    if saved_global_id is not None:
        room["IfcSpaceGeometry"] = {
            "source": "MagiCADRoomIfcSpace",
            "geometry_status": "validated_candidate",
            "IfcSpace": {"GlobalId": saved_global_id},
        }
    return {
        "FormatVersion": "1.1",
        "ParserVersion": "test",
        "GeneratedAtUtc": "2026-07-26T00:00:00Z",
        "DrawingName": "synthetic.dwg",
        "DrawingFullPath": "C:\\Tests\\synthetic.dwg",
        "FoundMarkers": 1,
        "Rooms": [room],
        "Warnings": [],
    }


class IfcSpaceImporterTests(unittest.TestCase):
    def test_non_finite_ifc_geometry_numerics_are_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValidationError):
            IfcPoint3D(X=float("nan"), Y=0.0, Z=0.0)

        with self.assertRaises(ValidationError):
            IfcUnitInfo(
                LengthUnit="Meters",
                MetersPerLengthUnit=float("inf"),
            )

        geometry = {
            "geometry_status": "validated",
            "IfcFile": {
                "Path": "model.ifc",
                "Sha256": "0" * 64,
                "Schema": "IFC4",
            },
            "IfcSpace": {"StepId": 1, "GlobalId": "SPACE"},
            "Units": {
                "LengthUnit": "Meters",
                "MetersPerLengthUnit": 1.0,
            },
            "Representation": {},
            "LocalToWorldMatrix": [[1.0, float("-inf")]],
            "MatrixLengthUnit": "Meters",
            "MatchStatus": "matched",
        }
        with self.assertRaises(ValidationError):
            IfcSpaceGeometry.model_validate(geometry)

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_ifc(self, content: str) -> Path:
        path = self.directory / "fixture.ifc"
        path.write_text(content, encoding="utf-8")
        return path

    def geometry(
        self,
        content: str,
        rooms: dict | None = None,
    ):
        path = self.write_ifc(content)
        outcome = analyze_ifc_spaces(
            path,
            rooms or room_document(),
        )
        self.assertEqual(outcome.summary.MatchedIfcSpaces, 1)
        return outcome.matched_geometries[0]

    def test_old_rooms_json_without_ifc_geometry_is_readable(self) -> None:
        fixture = (
            ROOT_DIRECTORY / "tests" / "fixtures" / "rooms_v1_0.json"
        )
        report = RoomExportReport.model_validate_json(
            fixture.read_text(encoding="utf-8")
        )
        self.assertIsNone(report.Rooms[0].IfcSpaceGeometry)
        self.assertIsNone(report.IfcSpaceImport)

    def test_rooms_document_read_is_actual_byte_bounded(self) -> None:
        self.assertEqual(MAX_ROOMS_JSON_BYTES, 10 * 1024 * 1024)

        rooms_path = self.directory / "rooms.json"
        exact_payload = b'{"Rooms":[]}'

        with patch(
            "agent.ifc_space_importer.MAX_ROOMS_JSON_BYTES",
            len(exact_payload),
        ):
            rooms_path.write_bytes(exact_payload)
            self.assertEqual(
                _read_rooms_document(rooms_path),
                {"Rooms": []},
            )

            rooms_path.write_bytes(exact_payload + b" ")
            with self.assertRaisesRegex(
                IfcSpaceImportError,
                "превышает допустимый размер",
            ):
                _read_rooms_document(rooms_path)

    def test_rooms_document_invalid_utf8_is_normalized(self) -> None:
        rooms_path = self.directory / "rooms.json"
        rooms_path.write_bytes(b"\xff")

        with self.assertRaisesRegex(
            IfcSpaceImportError,
            "Не удалось прочитать rooms.json",
        ):
            _read_rooms_document(rooms_path)

    def test_api_starts_when_ifcopenshell_is_unavailable(self) -> None:
        script = """
import importlib.abc
import sys

class BlockIfcOpenShell(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "ifcopenshell" or fullname.startswith("ifcopenshell."):
            raise ModuleNotFoundError(fullname)
        return None

sys.meta_path.insert(0, BlockIfcOpenShell())
from agent.api import app
assert app.version == "0.6.0"
assert not any(
    name == "ifcopenshell" or name.startswith("ifcopenshell.")
    for name in sys.modules
)
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT_DIRECTORY,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )

    def test_current_room_101_rectangle(self) -> None:
        outer = [
            (153.17888, 152.75076),
            (4846.507, 152.75076),
            (4846.507, 3843.40652),
            (153.17888, 3843.40652),
            (153.17888, 152.75076),
        ]
        geometry = self.geometry(
            synthetic_ifc(
                spaces=[
                    {
                        "name": "101",
                        "global_id": "3Vmsu$eoz6VAzSuuOWXaVz",
                        "long_name": "Тестовая комната",
                        "outer": outer,
                        "height": 2800.0,
                    }
                ]
            ),
            room_document(
                name="Тестовая комната",
                net_area=17.231460571289062,
                boundary_area=19.926653652183532,
            ),
        )
        self.assertEqual(geometry.source, "MagiCADRoomIfcSpace")
        self.assertEqual(
            geometry.geometry_status,
            "validated_candidate",
        )
        self.assertEqual(
            geometry.IfcSpace.GlobalId,
            "3Vmsu$eoz6VAzSuuOWXaVz",
        )
        self.assertAlmostEqual(
            geometry.AreaM2,
            17.321458459647975,
            places=12,
        )
        self.assertAlmostEqual(
            geometry.PerimeterM,
            16.76796776,
            places=10,
        )
        self.assertAlmostEqual(geometry.HeightM, 2.8)
        self.assertEqual(len(geometry.InnerBoundaryLoops), 0)
        self.assertAlmostEqual(
            geometry.NetAreaDifferenceM2,
            0.08999788835891209,
            places=12,
        )
        self.assertAlmostEqual(
            geometry.NetAreaDifferencePercent,
            0.5222882180333914,
            places=10,
        )

    def test_millimetre_units(self) -> None:
        geometry = self.geometry(
            synthetic_ifc(length_unit="millimetre")
        )
        self.assertEqual(geometry.Units.LengthUnit, "millimetre")
        self.assertEqual(geometry.Units.MetersPerLengthUnit, 0.001)
        self.assertAlmostEqual(geometry.AreaM2, 12.0)
        self.assertAlmostEqual(geometry.PerimeterM, 14.0)

    def test_metre_units(self) -> None:
        geometry = self.geometry(
            synthetic_ifc(length_unit="metre")
        )
        self.assertEqual(geometry.Units.LengthUnit, "metre")
        self.assertEqual(geometry.Units.MetersPerLengthUnit, 1.0)
        self.assertAlmostEqual(geometry.AreaM2, 12.0)
        self.assertAlmostEqual(geometry.PerimeterM, 14.0)

    def test_nonzero_space_placement(self) -> None:
        scale = 1000.0
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
                    "translation": (10000, 20000, 1000),
                }
            ]
        )
        geometry = self.geometry(content)
        first = geometry.OuterBoundaryLoop.WorldVertices[0]
        self.assertEqual((first.X, first.Y, first.Z), (10.0, 20.0, 1.0))
        self.assertAlmostEqual(geometry.AreaM2, 12.0)

    def test_nested_placements(self) -> None:
        content = synthetic_ifc(
            site_translation=(1000, 2000, 0),
            building_translation=(3000, 4000, 0),
            storey_translation=(5000, 6000, 3000),
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
                    "translation": (7000, 8000, 0),
                }
            ],
        )
        geometry = self.geometry(content)
        first = geometry.OuterBoundaryLoop.WorldVertices[0]
        self.assertEqual((first.X, first.Y, first.Z), (16.0, 20.0, 3.0))
        self.assertEqual(geometry.IfcSpace.StoreyElevationM, 3.0)
        self.assertEqual(geometry.MatrixLengthUnit, "metre")
        self.assertEqual(
            [
                geometry.LocalToWorldMatrix[0][3],
                geometry.LocalToWorldMatrix[1][3],
                geometry.LocalToWorldMatrix[2][3],
            ],
            [16.0, 20.0, 3.0],
        )

    def test_repeated_first_vertex_closure(self) -> None:
        geometry = self.geometry(synthetic_ifc())
        loop = geometry.OuterBoundaryLoop
        self.assertTrue(loop.SourceHadRepeatedEndpoint)
        self.assertEqual(
            loop.ClosureMethod,
            "explicit_repeated_endpoint",
        )
        self.assertEqual(loop.DistinctVertexCount, 4)

    def test_profile_without_repeated_endpoint(self) -> None:
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
                }
            ]
        )
        geometry = self.geometry(content)
        loop = geometry.OuterBoundaryLoop
        self.assertFalse(loop.SourceHadRepeatedEndpoint)
        self.assertEqual(
            loop.ClosureMethod,
            "ifc_closed_profile_semantics",
        )

    def test_inner_hole(self) -> None:
        content = synthetic_ifc(
            length_unit="metre",
            spaces=[
                {
                    "name": "101",
                    "outer": [
                        (0, 0),
                        (4, 0),
                        (4, 4),
                        (0, 4),
                    ],
                    "holes": [
                        [
                            (1, 1),
                            (2, 1),
                            (2, 2),
                            (1, 2),
                        ]
                    ],
                    "height": 2.8,
                }
            ],
        )
        geometry = self.geometry(content, room_document(net_area=15))
        self.assertAlmostEqual(geometry.AreaM2, 15.0)
        self.assertAlmostEqual(geometry.PerimeterM, 20.0)
        self.assertEqual(len(geometry.InnerBoundaryLoops), 1)
        self.assertEqual(
            geometry.InnerBoundaryLoops[0].Direction,
            "CW",
        )

    def test_hole_crossing_outer_boundary_is_invalid(self) -> None:
        content = synthetic_ifc(
            length_unit="metre",
            spaces=[
                {
                    "name": "101",
                    "outer": [(0, 0), (4, 0), (4, 4), (0, 4)],
                    "holes": [
                        [(3, 1), (5, 1), (5, 2), (3, 2)]
                    ],
                    "height": 2.8,
                }
            ],
        )
        outcome = analyze_ifc_spaces(
            self.write_ifc(content),
            room_document(),
        )
        result = outcome.summary.Results[0]
        self.assertEqual(result.GeometryStatus, "invalid")
        self.assertIn("пересекает", result.Diagnostics[0])

    def test_overlapping_holes_are_invalid(self) -> None:
        content = synthetic_ifc(
            length_unit="metre",
            spaces=[
                {
                    "name": "101",
                    "outer": [(0, 0), (5, 0), (5, 5), (0, 5)],
                    "holes": [
                        [(1, 1), (3, 1), (3, 3), (1, 3)],
                        [(2, 2), (4, 2), (4, 4), (2, 4)],
                    ],
                    "height": 2.8,
                }
            ],
        )
        outcome = analyze_ifc_spaces(
            self.write_ifc(content),
            room_document(),
        )
        result = outcome.summary.Results[0]
        self.assertEqual(result.GeometryStatus, "invalid")
        self.assertIn("пересекаются", result.Diagnostics[0])

    def test_cw_and_ccw_are_normalized(self) -> None:
        ccw = self.geometry(synthetic_ifc())
        self.assertEqual(
            ccw.OuterBoundaryLoop.OriginalDirection,
            "CCW",
        )
        clockwise_content = synthetic_ifc(
            spaces=[
                {
                    "name": "101",
                    "outer": [
                        (0, 0),
                        (0, 3000),
                        (4000, 3000),
                        (4000, 0),
                    ],
                    "height": 2800,
                }
            ]
        )
        clockwise = self.geometry(clockwise_content)
        self.assertEqual(
            clockwise.OuterBoundaryLoop.OriginalDirection,
            "CW",
        )
        self.assertEqual(clockwise.OuterBoundaryLoop.Direction, "CCW")
        self.assertAlmostEqual(clockwise.AreaM2, 12.0)

    def test_self_intersection_is_invalid(self) -> None:
        content = synthetic_ifc(
            spaces=[
                {
                    "name": "101",
                    "outer": [
                        (0, 0),
                        (4000, 3000),
                        (0, 3000),
                        (4000, 0),
                    ],
                    "height": 2800,
                }
            ]
        )
        outcome = analyze_ifc_spaces(
            self.write_ifc(content),
            room_document(),
        )
        self.assertEqual(outcome.summary.MatchedIfcSpaces, 0)
        self.assertEqual(
            outcome.summary.Results[0].GeometryStatus,
            "invalid",
        )
        self.assertIn(
            "самопересечение",
            outcome.summary.Results[0].Diagnostics[0],
        )

    def test_multiple_spaces_with_same_name_are_ambiguous(self) -> None:
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
        outcome = analyze_ifc_spaces(
            self.write_ifc(content),
            room_document(),
        )
        self.assertEqual(outcome.summary.MatchedIfcSpaces, 0)
        self.assertEqual(outcome.summary.AmbiguousIfcSpaces, 2)
        self.assertNotIn(
            "IfcSpaceGeometry",
            outcome.rooms_document["Rooms"][0],
        )

    def test_unmatched_space(self) -> None:
        outcome = analyze_ifc_spaces(
            self.write_ifc(synthetic_ifc()),
            room_document(code="999"),
        )
        self.assertEqual(outcome.summary.UnmatchedIfcSpaces, 1)
        self.assertEqual(outcome.summary.Results[0].Status, "unmatched")

    def test_saved_global_id_has_priority(self) -> None:
        rooms = room_document(
            code="999",
            saved_global_id="3Vmsu$eoz6VAzSuuOWXaVz",
        )
        outcome = analyze_ifc_spaces(
            self.write_ifc(synthetic_ifc()),
            rooms,
        )
        self.assertEqual(outcome.summary.MatchedIfcSpaces, 1)
        self.assertEqual(
            outcome.summary.Results[0].MatchMethod,
            "saved_global_id",
        )

    def test_unsupported_representation_is_reported(self) -> None:
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
        outcome = analyze_ifc_spaces(
            self.write_ifc(content),
            room_document(),
        )
        result = outcome.summary.Results[0]
        self.assertEqual(result.GeometryStatus, "unsupported")
        self.assertIn(
            "IfcExtrudedAreaSolid",
            result.Diagnostics[0],
        )

    def test_only_cartesian_point_list_2d_is_supported(self) -> None:
        class FakeEntity:
            def __init__(self, type_name: str) -> None:
                self.type_name = type_name

            def is_a(self, expected: str | None = None):
                if expected is None:
                    return self.type_name
                return self.type_name == expected

        curve = FakeEntity("IfcIndexedPolyCurve")
        curve.Points = FakeEntity("IfcCartesianPointList3D")
        with self.assertRaises(IfcGeometryUnsupported) as context:
            _indexed_curve_points(curve)
        self.assertIn(
            "IfcCartesianPointList2D",
            str(context.exception),
        )

    def test_damaged_profile_is_invalid(self) -> None:
        content = synthetic_ifc(
            spaces=[
                {
                    "name": "101",
                    "outer": [(0, 0), (4000, 0), (0, 0)],
                    "height": 2800,
                }
            ]
        )
        outcome = analyze_ifc_spaces(
            self.write_ifc(content),
            room_document(),
        )
        result = outcome.summary.Results[0]
        self.assertEqual(result.GeometryStatus, "invalid")
        self.assertIn(
            "не менее трёх",
            result.Diagnostics[0],
        )

    def test_analysis_does_not_write_and_write_preserves_boundary(self) -> None:
        ifc_path = self.write_ifc(synthetic_ifc())
        rooms_path = self.directory / "rooms.json"
        source = room_document()
        rooms_path.write_text(
            json.dumps(source, ensure_ascii=False),
            encoding="utf-8",
        )

        analysis = run_import(
            ifc_path,
            rooms_path,
            analyze_only=True,
        )
        self.assertEqual(
            json.loads(rooms_path.read_text(encoding="utf-8")),
            source,
        )
        self.assertEqual(analysis.summary.Mode, "analysis")

        output = self.directory / "rooms.with-ifc.json"
        written = run_import(
            ifc_path,
            rooms_path,
            output_path=output,
        )
        result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(
            result["Rooms"][0]["Boundary"],
            source["Rooms"][0]["Boundary"],
        )
        self.assertEqual(
            result["Rooms"][0]["geometry_status"],
            "provisional",
        )
        self.assertEqual(written.summary.Mode, "write")

        with self.assertRaises(IfcSpaceImportError):
            run_import(
                ifc_path,
                rooms_path,
                output_path=rooms_path,
            )

    def test_failed_overwrite_preserves_existing_output(self) -> None:
        ifc_path = self.write_ifc(synthetic_ifc())
        rooms_path = self.directory / "rooms.json"
        rooms_path.write_text(
            json.dumps(room_document(), ensure_ascii=False),
            encoding="utf-8",
        )
        output = self.directory / "rooms.with-ifc.json"
        output.write_text("old", encoding="utf-8")

        with patch.object(
            Path,
            "replace",
            side_effect=OSError("synthetic replace failure"),
        ):
            with self.assertRaisesRegex(
                OSError,
                "synthetic replace failure",
            ):
                run_import(
                    ifc_path,
                    rooms_path,
                    output_path=output,
                    overwrite=True,
                )

        self.assertEqual(
            output.read_text(encoding="utf-8"),
            "old",
        )
        self.assertEqual(
            list(
                self.directory.glob(
                    ".rooms.with-ifc.json.*.tmp"
                )
            ),
            [],
        )

    def test_missing_ifcopenshell_is_optional(self) -> None:
        with patch(
            "agent.ifc_space_importer.importlib.import_module",
            side_effect=ModuleNotFoundError("ifcopenshell"),
        ):
            with self.assertRaises(IfcOpenShellUnavailable) as context:
                _load_ifcopenshell()
        self.assertIn(
            "Основной API продолжает работать",
            str(context.exception),
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import builtins
import copy
import hashlib
import importlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from agent.domain_adapter import (
    DOMAIN_NAMESPACE,
    DomainAdaptationError,
    adapt_rooms_payload,
    canonical_handle,
    canonical_text,
    domain_uuid_name,
    domain_uuidv5,
)
from agent.domain_models import (
    DomainDocument,
    SourceKind,
    ValidationStatus,
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


def base_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def boundary_payload(
    *,
    geometry_status: str = "validated",
    source_object_type: str = "LWPOLYLINE",
) -> dict:
    return {
        "SourceHandle": "BND-01",
        "SourceObjectType": source_object_type,
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
        ],
        "IsClosed": True,
        "ContourAreaDrawingUnits2": 6.0,
        "ContourAreaM2": 6.0,
        "PerimeterDrawingUnits": 12.0,
        "PerimeterM": 12.0,
        "OriginalDirection": "CCW",
        "Direction": "CCW",
        "DrawingUnits": "Meters",
        "MetersPerDrawingUnit": 1.0,
        "GeometrySource": (
            "AutoCAD.ModelSpace.Polyline"
            if source_object_type == "LWPOLYLINE"
            else "AutoCAD.ModelSpace.Polyline3d"
        ),
        "Diagnostics": {
            "IsSupported": True,
            "IsValid": geometry_status == "validated",
            "DuplicateVerticesRemoved": 0,
            "IsSelfIntersecting": False,
            "MinimumVertexCount": 3,
            "VertexToleranceDrawingUnits": 0.0001,
            "ArcChordToleranceDrawingUnits": 0.001,
            "ContainingMarkerHandles": ["ABC"],
            "Messages": [],
        },
        "SourceVertices": [],
        "OriginalClosedFlag": True,
        "LogicalClosureMethod": "AutoCAD Closed flag",
        "ZDeviationDrawingUnits": 0.0,
        "ZDeviationM": 0.0,
        "IsPlanar": True,
        "Polyline3dType": (
            "SimplePoly"
            if source_object_type == "POLYLINE3D"
            else None
        ),
        "HasMagiCadData": False,
    }


def ifc_candidate(
    path: str = r"C:\Models\Room101.ifc",
) -> dict:
    return {
        "source": "MagiCADRoomIfcSpace",
        "geometry_status": "validated_candidate",
        "IfcFile": {
            "Path": path,
            "Sha256": "a" * 64,
            "Schema": "IFC4",
        },
        "IfcSpace": {
            "StepId": 42,
            "GlobalId": "3Vmsu$eoz6VAzSuuOWXaVz",
            "Name": "101",
            "LongName": "Room 101",
            "ObjectType": None,
            "PredefinedType": "INTERNAL",
            "StoreyName": "First floor",
            "StoreyElevationModelUnits": 0.0,
            "StoreyElevationM": 0.0,
        },
        "Units": {
            "LengthUnit": "MILLIMETRE",
            "MetersPerLengthUnit": 0.001,
            "AreaUnit": "SQUARE_METRE",
        },
        "Representation": {
            "Identifier": "Body",
            "Type": "SweptSolid",
            "SolidType": "IfcExtrudedAreaSolid",
            "ProfileType": "IfcArbitraryClosedProfileDef",
            "CurveType": "IfcPolyline",
            "ExtrusionDirection": {
                "X": 0.0,
                "Y": 0.0,
                "Z": 1.0,
            },
        },
        "LocalToWorldMatrix": [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        "MatrixLengthUnit": "MILLIMETRE",
        "OuterBoundaryLoop": {
            "SourceVertices": [],
            "LocalVertices": [],
            "WorldVertices": [
                {"X": 0.0, "Y": 0.0, "Z": 0.0},
                {"X": 4.0, "Y": 0.0, "Z": 0.0},
                {"X": 4.0, "Y": 3.0, "Z": 0.0},
            ],
            "IsClosed": True,
            "ClosureMethod": "Repeated endpoint",
            "SourceHadRepeatedEndpoint": True,
            "DuplicateVerticesRemoved": 1,
            "DistinctVertexCount": 3,
            "OriginalDirection": "CCW",
            "Direction": "CCW",
            "IsSelfIntersecting": False,
            "IsPlanar": True,
            "ZDeviationM": 0.0,
            "AreaM2": 6.0,
            "PerimeterM": 12.0,
        },
        "InnerBoundaryLoops": [],
        "AreaM2": 6.0,
        "PerimeterM": 12.0,
        "HeightM": 2.8,
        "MatchStatus": "matched",
        "MatchMethod": "GlobalId",
        "MatchedRoomCode": "101",
        "Warnings": [],
        "Diagnostics": [],
    }


def room_from(document: DomainDocument):
    return (
        document.project.buildings[0]
        .levels[0]
        .rooms[0]
    )


def nested_strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from nested_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from nested_strings(item)
    elif isinstance(value, str):
        yield value


class DomainContractTests(unittest.TestCase):
    def test_namespace_is_fixed_literal(self) -> None:
        self.assertEqual(
            str(DOMAIN_NAMESPACE),
            "b62d9c24-0c2f-5e2a-8c7d-2d4bb9c98772",
        )

    def test_uuid_name_is_canonical_json_array(self) -> None:
        name = domain_uuid_name(
            "project",
            "дом",
            "a|drawing|b",
        )

        self.assertEqual(
            name,
            '["homeaura-domain-id",1,"project",'
            '"дом","a|drawing|b"]',
        )

    def test_separator_adversarial_project_ids_do_not_collide(
        self,
    ) -> None:
        first_payload = base_payload()
        second_payload = base_payload()
        first_payload["DrawingName"] = "c"
        second_payload["DrawingName"] = "b|drawing|c"

        old_first = (
            "project|project_id|a|drawing|b|drawing|c"
        )
        old_second = (
            "project|project_id|a|drawing|b|drawing|c"
        )
        self.assertEqual(old_first, old_second)

        first = adapt_rooms_payload(
            first_payload,
            project_id="a|drawing|b",
        )
        second = adapt_rooms_payload(
            second_payload,
            project_id="a",
        )

        self.assertNotEqual(
            first.project.stable_id,
            second.project.stable_id,
        )

    def test_separator_adversarial_drawing_and_code_do_not_collide(
        self,
    ) -> None:
        first = domain_uuidv5(
            "room",
            "project-uuid",
            "a|code|b",
            "c",
        )
        second = domain_uuidv5(
            "room",
            "project-uuid",
            "a",
            "b|code|c",
        )

        self.assertNotEqual(first, second)

    def test_same_canonical_uuid_components_stay_equal(self) -> None:
        first = domain_uuidv5(
            "room",
            "project-uuid",
            canonical_text(" ＬＥＧＡＣＹ．ＤＷＧ "),
            "handle",
            canonical_handle(" ａｂｃ "),
        )
        second = domain_uuidv5(
            "room",
            "project-uuid",
            "legacy.dwg",
            "handle",
            "ABC",
        )

        self.assertEqual(first, second)

    def test_legacy_1_0_maps_to_domain_hierarchy(self) -> None:
        document = adapt_rooms_payload(
            base_payload(),
            project_id="LegacyProject",
        )

        self.assertEqual(document.schema_version, "1.0")
        self.assertEqual(document.legacy_format_version, "1.0")
        self.assertEqual(len(document.project.buildings), 1)
        self.assertEqual(
            len(document.project.buildings[0].levels),
            1,
        )
        self.assertEqual(
            len(
                document.project.buildings[0]
                .levels[0]
                .rooms
            ),
            1,
        )
        self.assertIsNone(room_from(document).boundary)

    def test_legacy_1_1_boundary_is_mapped(self) -> None:
        payload = base_payload()
        payload["FormatVersion"] = "1.1"
        payload["Rooms"][0]["Boundary"] = boundary_payload()
        payload["Rooms"][0]["geometry_status"] = "validated"

        boundary = room_from(
            adapt_rooms_payload(payload, project_id="P1")
        ).boundary

        self.assertIsNotNone(boundary)
        assert boundary is not None
        self.assertEqual(boundary.source_handle, "BND-01")
        self.assertEqual(
            boundary.source.kind,
            SourceKind.LEGACY_BOUNDARY,
        )

    def test_adapter_does_not_write_files(self) -> None:
        with patch(
            "pathlib.Path.write_text",
            side_effect=AssertionError("write attempted"),
        ):
            document = adapt_rooms_payload(
                base_payload(),
                project_id="P1",
            )
        self.assertEqual(document.schema_version, "1.0")

    def test_input_mapping_is_unchanged(self) -> None:
        payload = base_payload()
        payload["Rooms"][0]["IfcSpaceGeometry"] = ifc_candidate()
        before = copy.deepcopy(payload)

        adapt_rooms_payload(payload, project_id="P1")

        self.assertEqual(payload, before)

    def test_source_json_bytes_are_unchanged(self) -> None:
        before = FIXTURE_PATH.read_bytes()
        payload = json.loads(before.decode("utf-8"))

        adapt_rooms_payload(payload, project_id="P1")

        self.assertEqual(FIXTURE_PATH.read_bytes(), before)

    def test_current_rooms_json_is_read_only_and_adapts(
        self,
    ) -> None:
        before = CURRENT_ROOMS_PATH.read_bytes()
        before_hash = hashlib.sha256(before).hexdigest()
        payload = json.loads(before.decode("utf-8"))

        document = adapt_rooms_payload(
            payload,
            project_id="Test_01",
        )

        self.assertEqual(document.schema_version, "1.0")
        self.assertEqual(
            len(
                document.project.buildings[0]
                .levels[0]
                .rooms
            ),
            1,
        )
        self.assertEqual(CURRENT_ROOMS_PATH.read_bytes(), before)
        self.assertEqual(
            before_hash,
            "30ee1828e74ecbf1e1b46064c39ce3075"
            "5a4692fc4cd972d1e38328affe0992e",
        )

    def test_result_is_deeply_independent_from_input(self) -> None:
        payload = base_payload()
        payload["FormatVersion"] = "1.1"
        payload["Rooms"][0]["Boundary"] = boundary_payload()
        payload["Rooms"][0]["geometry_status"] = "validated"
        payload["Rooms"][0]["IfcSpaceGeometry"] = ifc_candidate()
        document = adapt_rooms_payload(payload, project_id="P1")
        room = room_from(document)

        payload["Rooms"][0]["Position"]["X"] = 999.0
        payload["Rooms"][0]["Boundary"]["Vertices"][0]["X"] = 999.0
        payload["Rooms"][0]["IfcSpaceGeometry"][
            "OuterBoundaryLoop"
        ]["WorldVertices"][0]["X"] = 999.0

        self.assertEqual(room.position["X"], 1000.0)
        assert room.boundary is not None
        self.assertEqual(
            room.boundary.legacy_geometry["Vertices"][0]["X"],
            0.0,
        )
        assert room.ifc_space_candidate is not None
        self.assertEqual(
            room.ifc_space_candidate.portable_payload[
                "OuterBoundaryLoop"
            ]["WorldVertices"][0]["X"],
            0.0,
        )

    def test_validated_boundary_status_is_preserved(self) -> None:
        payload = base_payload()
        payload["FormatVersion"] = "1.1"
        payload["Rooms"][0]["Boundary"] = boundary_payload()
        payload["Rooms"][0]["geometry_status"] = "validated"

        boundary = room_from(
            adapt_rooms_payload(payload, project_id="P1")
        ).boundary

        assert boundary is not None
        self.assertEqual(
            boundary.validation_status,
            ValidationStatus.VALIDATED,
        )
        self.assertEqual(boundary.geometry_status, "validated")

    def test_provisional_polyline3d_status_is_preserved(self) -> None:
        payload = base_payload()
        payload["FormatVersion"] = "1.1"
        payload["Rooms"][0]["Boundary"] = boundary_payload(
            geometry_status="provisional",
            source_object_type="POLYLINE3D",
        )
        payload["Rooms"][0]["geometry_status"] = "provisional"

        boundary = room_from(
            adapt_rooms_payload(payload, project_id="P1")
        ).boundary

        assert boundary is not None
        self.assertEqual(
            boundary.validation_status,
            ValidationStatus.PROVISIONAL,
        )
        self.assertEqual(
            boundary.legacy_geometry["SourceObjectType"],
            "POLYLINE3D",
        )

    def test_ambiguous_boundary_never_becomes_validated(self) -> None:
        payload = base_payload()
        payload["FormatVersion"] = "1.1"
        payload["Rooms"][0]["Boundary"] = boundary_payload()
        payload["Rooms"][0]["geometry_status"] = "ambiguous"

        boundary = room_from(
            adapt_rooms_payload(payload, project_id="P1")
        ).boundary

        assert boundary is not None
        self.assertEqual(
            boundary.validation_status,
            ValidationStatus.INVALID,
        )

    def test_ifc_candidate_is_separate_and_provisional(self) -> None:
        payload = base_payload()
        payload["Rooms"][0]["IfcSpaceGeometry"] = ifc_candidate()

        room = room_from(
            adapt_rooms_payload(payload, project_id="P1")
        )

        self.assertIsNone(room.boundary)
        self.assertIsNotNone(room.ifc_space_candidate)
        assert room.ifc_space_candidate is not None
        self.assertEqual(
            room.ifc_space_candidate.validation_status,
            ValidationStatus.PROVISIONAL,
        )
        self.assertEqual(
            room.ifc_space_candidate.geometry_status,
            "validated_candidate",
        )
        self.assertEqual(room.aliases[0].kind, "ifc_global_id")

    def test_ifc_candidate_does_not_replace_boundary(self) -> None:
        payload = base_payload()
        payload["FormatVersion"] = "1.1"
        payload["Rooms"][0]["Boundary"] = boundary_payload()
        payload["Rooms"][0]["geometry_status"] = "validated"
        payload["Rooms"][0]["IfcSpaceGeometry"] = ifc_candidate()

        room = room_from(
            adapt_rooms_payload(payload, project_id="P1")
        )

        self.assertIsNotNone(room.boundary)
        self.assertIsNotNone(room.ifc_space_candidate)
        assert room.boundary is not None
        self.assertEqual(
            room.boundary.validation_status,
            ValidationStatus.VALIDATED,
        )

    def test_raw_ifc_candidate_survives_extra_ignore(self) -> None:
        payload = base_payload()
        candidate = ifc_candidate()
        candidate["RawOnlyEvidence"] = {
            "portable": {"value": 7}
        }
        payload["Rooms"][0]["IfcSpaceGeometry"] = candidate

        room = room_from(
            adapt_rooms_payload(payload, project_id="P1")
        )

        assert room.ifc_space_candidate is not None
        self.assertEqual(
            room.ifc_space_candidate.portable_payload[
                "RawOnlyEvidence"
            ]["portable"]["value"],
            7,
        )
        self.assertTrue(
            any(
                "RawOnlyEvidence" in item
                for item in room.ifc_space_candidate.diagnostics
            )
        )

    def test_absolute_ifc_path_is_removed_but_evidence_remains(
        self,
    ) -> None:
        payload = base_payload()
        payload["Rooms"][0]["IfcSpaceGeometry"] = ifc_candidate(
            r"C:\Private\Models\Room101.ifc"
        )

        room = room_from(
            adapt_rooms_payload(payload, project_id="P1")
        )
        assert room.ifc_space_candidate is not None
        candidate = room.ifc_space_candidate
        serialized = json.dumps(
            candidate.model_dump(mode="json"),
            ensure_ascii=False,
        )

        self.assertEqual(candidate.file.file_name, "Room101.ifc")
        self.assertEqual(candidate.file.sha256, "a" * 64)
        self.assertNotIn(r"C:\Private", serialized)
        self.assertNotIn(
            "Path",
            candidate.portable_payload["IfcFile"],
        )
        self.assertTrue(
            any(
                "absolute path removed" in item
                for item in candidate.diagnostics
            )
        )

    def test_uuidv5_is_deterministic(self) -> None:
        first = adapt_rooms_payload(
            base_payload(),
            project_id="P1",
        )
        second = adapt_rooms_payload(
            base_payload(),
            project_id="P1",
        )

        self.assertEqual(
            first.project.stable_id,
            second.project.stable_id,
        )
        self.assertEqual(
            room_from(first).stable_id,
            room_from(second).stable_id,
        )

    def test_valid_identity_uuids_are_unchanged_by_domain_1b(
        self,
    ) -> None:
        payload = base_payload()
        document = adapt_rooms_payload(
            payload,
            project_id="P1",
        )

        self.assertEqual(
            str(document.project.stable_id),
            "5d1645ef-07aa-55f5-9af1-dbd8d4b95bbb",
        )
        self.assertEqual(
            str(room_from(document).stable_id),
            "a2cf5e7e-fe55-56de-8f2e-9ff2ce55f35b",
        )

        payload["FormatVersion"] = "1.1"
        payload["Rooms"][0]["Boundary"] = boundary_payload()
        payload["Rooms"][0]["geometry_status"] = "validated"
        document = adapt_rooms_payload(
            payload,
            project_id="P1",
        )
        boundary = room_from(document).boundary
        assert boundary is not None
        self.assertEqual(
            str(boundary.stable_id),
            "bc1f9348-ce27-59ca-bc8a-428ef6a1fedb",
        )

    def test_exact_nfkc_trim_casefold_canonicalization(self) -> None:
        first_payload = base_payload()
        second_payload = base_payload()
        second_payload["DrawingName"] = "  ＬＥＧＡＣＹ．ＤＷＧ "
        second_payload["Rooms"][0]["SourceHandle"] = "  ａｂｃ  "

        first = adapt_rooms_payload(
            first_payload,
            project_id="project",
        )
        second = adapt_rooms_payload(
            second_payload,
            project_id="  ＰＲＯＪＥＣＴ ",
        )

        self.assertEqual(
            canonical_text("  ＰＲＯＪＥＣＴ "),
            "project",
        )
        self.assertEqual(canonical_handle(" ａｂｃ "), "ABC")
        self.assertEqual(
            first.project.stable_id,
            second.project.stable_id,
        )
        self.assertEqual(
            room_from(first).stable_id,
            room_from(second).stable_id,
        )

    def test_different_project_ids_have_different_ids(self) -> None:
        first = adapt_rooms_payload(
            base_payload(),
            project_id="P1",
        )
        second = adapt_rooms_payload(
            base_payload(),
            project_id="P2",
        )

        self.assertNotEqual(
            first.project.stable_id,
            second.project.stable_id,
        )
        self.assertNotEqual(
            room_from(first).stable_id,
            room_from(second).stable_id,
        )

    def test_absolute_paths_are_absent_from_complete_output(
        self,
    ) -> None:
        payload = base_payload()
        payload["Rooms"][0]["IfcSpaceGeometry"] = ifc_candidate()
        document = adapt_rooms_payload(
            payload,
            project_id="LegacyProject",
        )
        serialized = json.dumps(
            document.model_dump(mode="json"),
            ensure_ascii=False,
        )

        self.assertNotRegex(serialized, r"[A-Za-z]:[\\/]")
        self.assertNotIn(r"\\server\share", serialized)
        self.assertEqual(document.project.name, "LegacyProject")

    def test_all_identity_path_forms_are_rejected_safely(
        self,
    ) -> None:
        path_variants = [
            r"C:\audit_a\shared",
            r"D:\audit_b\shared",
            "/audit_a/shared",
            "/audit_b/shared",
            r"\\audit-server\share\shared",
            r"\\?\C:\audit_a\shared",
            r"\\.\C:\audit_a\shared",
            "file:///C:/audit_a/shared",
            "file://audit-server/share/shared",
        ]
        identity_fields = (
            ("project_id", "project_id"),
            ("drawing", "DrawingName"),
            ("room_handle", "Rooms[0].SourceHandle"),
            (
                "boundary_handle",
                "Room.Boundary.SourceHandle",
            ),
        )

        for identity_field, expected_field in identity_fields:
            for path_value in path_variants:
                with self.subTest(
                    field=identity_field,
                    path=path_value,
                ):
                    payload = base_payload()
                    project_id = "audit-project"
                    if identity_field == "project_id":
                        project_id = path_value
                    elif identity_field == "drawing":
                        payload["DrawingName"] = path_value
                    elif identity_field == "room_handle":
                        payload["Rooms"][0][
                            "SourceHandle"
                        ] = path_value
                    else:
                        payload["FormatVersion"] = "1.1"
                        payload["Rooms"][0][
                            "Boundary"
                        ] = boundary_payload()
                        payload["Rooms"][0]["Boundary"][
                            "SourceHandle"
                        ] = path_value
                        payload["Rooms"][0][
                            "geometry_status"
                        ] = "validated"
                    before = copy.deepcopy(payload)

                    with self.assertRaises(
                        DomainAdaptationError
                    ) as context:
                        adapt_rooms_payload(
                            payload,
                            project_id=project_id,
                        )

                    error = context.exception
                    error_text = (
                        str(error)
                        + "\n"
                        + "\n".join(error.diagnostics)
                    )
                    self.assertEqual(
                        error.code,
                        "unsafe_identity_path",
                    )
                    self.assertIn(expected_field, error_text)
                    self.assertNotIn(path_value, error_text)
                    self.assertEqual(payload, before)

    def test_same_basename_path_code_fallbacks_are_rejected(
        self,
    ) -> None:
        path_pairs = {
            "windows": (
                r"C:\first\ROOM-101",
                r"D:\second\ROOM-101",
            ),
            "posix": (
                "/first/ROOM-101",
                "/second/ROOM-101",
            ),
            "unc": (
                r"\\server-one\share-one\ROOM-101",
                r"\\server-two\share-two\ROOM-101",
            ),
            "device": (
                r"\\?\C:\first\ROOM-101",
                r"\\.\D:\second\ROOM-101",
            ),
            "file_uri": (
                "file:///C:/first/ROOM-101",
                "file:///D:/second/ROOM-101",
            ),
        }
        safe_error = "unsafe_identity_path field=Room.Code"

        for version in ("1.0", "1.1"):
            for path_kind, path_values in path_pairs.items():
                for path_value in path_values:
                    with self.subTest(
                        version=version,
                        path_kind=path_kind,
                    ):
                        payload = base_payload()
                        payload["FormatVersion"] = version
                        payload["Rooms"][0].pop(
                            "SourceHandle",
                            None,
                        )
                        payload["Rooms"][0]["Code"] = path_value
                        before = copy.deepcopy(payload)

                        with self.assertRaises(
                            DomainAdaptationError
                        ) as context:
                            adapt_rooms_payload(
                                payload,
                                project_id="identity-audit",
                            )

                        error = context.exception
                        self.assertEqual(
                            error.code,
                            "unsafe_identity_path",
                        )
                        self.assertEqual(str(error), safe_error)
                        self.assertEqual(
                            error.diagnostics,
                            [safe_error],
                        )
                        self.assertNotIn(
                            "ROOM-101",
                            str(error)
                            + "\n"
                            + "\n".join(error.diagnostics),
                        )
                        self.assertEqual(payload, before)

    def test_valid_code_fallback_uuid_is_unchanged_in_1_0_and_1_1(
        self,
    ) -> None:
        expected_uuid = "043c393a-cbb8-5a64-8c42-ad1aa32a825c"

        for version in ("1.0", "1.1"):
            with self.subTest(version=version):
                payload = base_payload()
                payload["FormatVersion"] = version
                payload["Rooms"][0].pop("SourceHandle", None)
                payload["Rooms"][0]["Code"] = "ROOM-101"

                room = room_from(
                    adapt_rooms_payload(
                        payload,
                        project_id="identity-audit",
                    )
                )

                self.assertEqual(str(room.stable_id), expected_uuid)
                self.assertEqual(room.code, "ROOM-101")
                self.assertIsNone(room.source_handle)
                self.assertEqual(
                    room.source.identifiers["fallback_code"],
                    "room-101",
                )

    def test_unsafe_mapping_keys_are_excluded_without_loss(
        self,
    ) -> None:
        path_a = r"C:\audit_a\shared.txt"
        path_b = r"D:\audit_b\shared.txt"
        placeholder = "<absolute_field_name_redacted>"
        payload = base_payload()
        candidate = ifc_candidate()
        candidate["RawOnlyEvidence"] = {
            path_a: {"marker": "unsafe-first"},
            path_b: {"marker": "unsafe-second"},
            "safe": {"marker": "safe-root"},
            placeholder: {"marker": "placeholder"},
            "nested": {
                path_a: {"marker": "nested-first"},
                path_b: {"marker": "nested-second"},
                "safe_nested": {"marker": "safe-nested"},
            },
        }
        payload["Rooms"][0]["IfcSpaceGeometry"] = candidate
        before = copy.deepcopy(payload)

        document = adapt_rooms_payload(
            payload,
            project_id="audit-project",
        )
        room = room_from(document)
        assert room.ifc_space_candidate is not None
        ifc = room.ifc_space_candidate
        portable = ifc.portable_payload[
            "RawOnlyEvidence"
        ]
        nested = portable["nested"]

        self.assertEqual(
            portable["safe"]["marker"],
            "safe-root",
        )
        self.assertEqual(
            portable[placeholder]["marker"],
            "placeholder",
        )
        self.assertEqual(
            nested["safe_nested"]["marker"],
            "safe-nested",
        )
        self.assertEqual(
            set(portable),
            {"safe", placeholder, "nested"},
        )
        self.assertEqual(set(nested), {"safe_nested"})
        removed = [
            item
            for item in ifc.diagnostics
            if "unsafe_mapping_key_excluded" in item
        ]
        self.assertEqual(len(removed), 2)
        self.assertTrue(
            all("removed_count=2" in item for item in removed)
        )
        output_strings = list(
            nested_strings(document.model_dump(mode="json"))
        )
        self.assertFalse(
            any(
                path_a in item or path_b in item
                for item in output_strings
            )
        )
        self.assertEqual(payload, before)

    def test_unassigned_building_and_level_require_confirmation(
        self,
    ) -> None:
        document = adapt_rooms_payload(
            base_payload(),
            project_id="P1",
        )
        building = document.project.buildings[0]
        level = building.levels[0]

        self.assertEqual(
            building.validation_status,
            ValidationStatus.REQUIRES_CONFIRMATION,
        )
        self.assertEqual(
            level.validation_status,
            ValidationStatus.REQUIRES_CONFIRMATION,
        )
        self.assertEqual(
            building.source.kind,
            SourceKind.LEGACY_PLACEHOLDER,
        )
        self.assertEqual(
            level.source.kind,
            SourceKind.LEGACY_PLACEHOLDER,
        )

    def test_derived_project_requires_confirmation(self) -> None:
        project = adapt_rooms_payload(
            base_payload(),
            project_id="P1",
        ).project

        self.assertEqual(
            project.validation_status,
            ValidationStatus.REQUIRES_CONFIRMATION,
        )
        self.assertEqual(
            project.source.kind,
            SourceKind.DERIVED_DETERMINISTIC,
        )

    def test_code_fallback_requires_confirmation(self) -> None:
        payload = base_payload()
        payload["Rooms"][0].pop("SourceHandle")

        room = room_from(
            adapt_rooms_payload(payload, project_id="P1")
        )

        self.assertIsNone(room.source_handle)
        self.assertEqual(
            room.validation_status,
            ValidationStatus.REQUIRES_CONFIRMATION,
        )
        self.assertIn(
            "fallback_code",
            room.source.identifiers,
        )

    def test_duplicate_fallback_codes_are_rejected(self) -> None:
        for version in ("1.0", "1.1"):
            with self.subTest(version=version):
                payload = base_payload()
                payload["FormatVersion"] = version
                first = payload["Rooms"][0]
                first.pop("SourceHandle")
                second = copy.deepcopy(first)
                second["Code"] = "  １０１ "
                payload["Rooms"].append(second)

                with self.assertRaises(
                    DomainAdaptationError
                ) as context:
                    adapt_rooms_payload(payload, project_id="P1")

                self.assertEqual(
                    context.exception.code,
                    "duplicate_fallback_code",
                )

    def test_empty_fallback_identity_is_rejected(self) -> None:
        payload = base_payload()
        payload["Rooms"][0].pop("SourceHandle")
        payload["Rooms"][0]["Code"] = "   "

        with self.assertRaises(DomainAdaptationError) as context:
            adapt_rooms_payload(payload, project_id="P1")

        self.assertEqual(
            context.exception.code,
            "empty_room_code",
        )

    def test_explicit_empty_handle_is_rejected(self) -> None:
        payload = base_payload()
        payload["Rooms"][0]["SourceHandle"] = " \u3000 "

        with self.assertRaises(DomainAdaptationError) as context:
            adapt_rooms_payload(payload, project_id="P1")

        self.assertEqual(
            context.exception.code,
            "empty_source_handle",
        )

    def test_duplicate_source_handles_are_rejected(self) -> None:
        payload = base_payload()
        duplicate = copy.deepcopy(payload["Rooms"][0])
        duplicate["SourceHandle"] = "  ａｂｃ "
        duplicate["Code"] = "102"
        payload["Rooms"].append(duplicate)

        with self.assertRaises(DomainAdaptationError) as context:
            adapt_rooms_payload(payload, project_id="P1")

        self.assertEqual(
            context.exception.code,
            "duplicate_source_handle",
        )

    def test_duplicate_normalized_room_codes_are_rejected(
        self,
    ) -> None:
        payload = base_payload()
        duplicate = copy.deepcopy(payload["Rooms"][0])
        duplicate["SourceHandle"] = "DEF"
        duplicate["Code"] = "  １０１ "
        payload["Rooms"].append(duplicate)

        with self.assertRaises(DomainAdaptationError) as context:
            adapt_rooms_payload(payload, project_id="P1")

        self.assertEqual(
            context.exception.code,
            "duplicate_room_code",
        )

    def test_unknown_fields_are_reported_in_diagnostics(self) -> None:
        payload = base_payload()
        payload["CustomRoot"] = {"value": 1}
        payload["Rooms"][0]["CustomRoom"] = "value"

        document = adapt_rooms_payload(
            payload,
            project_id="P1",
        )

        self.assertTrue(
            any(
                "CustomRoot" in item
                for item in document.diagnostics
            )
        )
        self.assertTrue(
            any(
                "CustomRoom" in item
                for item in room_from(document).diagnostics
            )
        )

    def test_unknown_major_version_is_rejected(self) -> None:
        payload = base_payload()
        payload["FormatVersion"] = "2.0"

        with self.assertRaises(DomainAdaptationError) as context:
            adapt_rooms_payload(payload, project_id="P1")

        self.assertEqual(
            context.exception.code,
            "unsupported_format_version",
        )

    def test_unknown_minor_1_x_version_is_rejected(self) -> None:
        payload = base_payload()
        payload["FormatVersion"] = "1.2"

        with self.assertRaises(DomainAdaptationError) as context:
            adapt_rooms_payload(payload, project_id="P1")

        self.assertEqual(
            context.exception.code,
            "unsupported_format_version",
        )

    def test_domain_document_round_trip(self) -> None:
        payload = base_payload()
        payload["Rooms"][0]["IfcSpaceGeometry"] = ifc_candidate()
        document = adapt_rooms_payload(payload, project_id="P1")

        restored = DomainDocument.model_validate_json(
            document.model_dump_json()
        )

        self.assertEqual(restored, document)

    def test_domain_document_rejects_non_finite_opaque_values(
        self,
    ) -> None:
        document = adapt_rooms_payload(
            base_payload(),
            project_id="P1",
        )
        dumped = document.model_dump(mode="json")
        room = dumped["project"]["buildings"][0]["levels"][
            0
        ]["rooms"][0]
        room["legacy_attributes"]["opaque"] = {
            "metric": float("-inf")
        }

        with self.assertRaises(ValidationError):
            DomainDocument.model_validate(dumped)

    def test_domain_document_forbids_extra_fields(self) -> None:
        document = adapt_rooms_payload(
            base_payload(),
            project_id="P1",
        )
        dumped = document.model_dump(mode="json")
        dumped["unexpected"] = True

        with self.assertRaises(ValidationError):
            DomainDocument.model_validate(dumped)

    def test_nested_domain_models_forbid_extra_fields(self) -> None:
        document = adapt_rooms_payload(
            base_payload(),
            project_id="P1",
        )
        dumped = document.model_dump(mode="json")
        dumped["project"]["unexpected"] = True

        with self.assertRaises(ValidationError):
            DomainDocument.model_validate(dumped)

    def test_domain_import_does_not_need_ifcopenshell(self) -> None:
        real_import = builtins.__import__
        module_path = (
            Path(__file__).resolve().parents[1]
            / "agent"
            / "domain_adapter.py"
        )

        def guarded_import(name, *args, **kwargs):
            if (
                name.startswith("ifcopenshell")
                or name == "agent.ifc_space_importer"
            ):
                raise AssertionError(
                    f"forbidden optional import: {name}"
                )
            return real_import(name, *args, **kwargs)

        with patch(
            "builtins.__import__",
            side_effect=guarded_import,
        ):
            spec = importlib.util.spec_from_file_location(
                "domain_adapter_without_ifc",
                module_path,
            )
            assert spec is not None
            assert spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        self.assertTrue(
            callable(module.adapt_rooms_payload)
        )

    def test_api_version_and_routes_are_unchanged(self) -> None:
        from agent.api import app

        all_routes = list(app.routes)
        for route in app.routes:
            original_router = getattr(
                route,
                "original_router",
                None,
            )
            if original_router is not None:
                all_routes.extend(original_router.routes)

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
            (
                "/api/v1/projects/canonical/preview",
                ("POST",),
            ),
        }

        self.assertEqual(app.version, "0.6.0")
        self.assertEqual(routes, expected)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
TMP = ROOT / "tmp"

ARTIFACT_ID = "HA_TWO_FLOOR_ATTIC_VERIFIED_PHYSICAL_INPUT_GATE_186"
SOURCE_ARTIFACT_ID = "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185"
SOURCE_DIRECTORY = PROPOSALS / SOURCE_ARTIFACT_ID
SOURCE_PROJECT = SOURCE_DIRECTORY / "HomeAura_TwoFloor_C12BoundedTerminal_D185.homeaura.json"
SOURCE_CONTRACT = SOURCE_DIRECTORY / "floor1_c12_bounded_terminal_contract.json"
SOURCE_DIAGNOSTICS = SOURCE_DIRECTORY / "engineering_diagnostics.json"
SOURCE_MANIFEST = SOURCE_DIRECTORY / "artifact_manifest.json"
SOURCE_PACKAGE = PROPOSALS / "packages" / f"{SOURCE_ARTIFACT_ID}.zip"

D181_CONTRACT = PROPOSALS / "HA_TWO_FLOOR_ATTIC_SOURCE_WALL_DOMAINS_181" / "attic_source_wall_domains_contract.json"
D137_EVIDENCE = PROPOSALS / "HA_TWO_FLOOR_PRIMARY_RELEASE_STATE_BINDING_137" / "primary_release_state_binding.json"
D166_EVIDENCE = PROPOSALS / "HA_TWO_FLOOR_K2_SERVICE_LAYER_166" / "k2_service_layer_contract.json"

OUTPUT = TMP / "D186_scaffold"
PACKAGE = TMP / f"{ARTIFACT_ID}_SCAFFOLD.zip"
GATE_NAME = "attic_verified_physical_input_gate.json"
TEMPLATE_NAME = "attic_as_built_input_template.json"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)

BLOCKED_REASON = "BLOCKED_VERIFIED_ATTIC_ARCHITECTURE_AND_INTERFLOOR_OPENING_INPUTS"
EXPECTED_HISTORICAL_HASHES = {
    D181_CONTRACT: "3F165409B96208BA5F2E5C190D2B185A1CA867CC874B863595ECB294A5D5FBF5",
    D137_EVIDENCE: "22A88220A1C5DFF0030813220DF13666DABB08B3282693238B8C9C1847C3E125",
    D166_EVIDENCE: "5C28BA2C31DC4343D9742EDABBEBBE38E0057928ED701B637B480957BF1A170D",
}
EXPECTED_D185_HASHES = {
    SOURCE_PROJECT: "558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4",
    SOURCE_CONTRACT: "4C794B3F632C00DF790F743FECBA488DA378C69A5CBED988A34EB3DF4B4CC726",
    SOURCE_DIAGNOSTICS: "FBC6BEDDECE6828102D4AAAA951B0FB20CAE7E13AE845391667CCCFC377A43B9",
    SOURCE_MANIFEST: "0D4EDA2C54B63D3D7DE69F67D4310CBBEB14C11CA7687814CF7D9EAF6DA57347",
    SOURCE_PACKAGE: "A2B1F9D5DE8171B0546D00CBDA29F9902EB47AC276F27616942FACD00E58DB99",
}
SCHEMA11_IMPLEMENTATION_HASHES = {
    ROOT / "homeaura-native-editor" / "ProjectModel.cs":
        "0667BC7D39EBF9CB399CDBFB0114B228BA21D1DB0795F513633B08C38D6FD294",
    ROOT / "homeaura-native-editor" / "CircuitAnalyzer.cs":
        "084C3D8CB72D4F4A1150B2C663EA30E6F971320336BDD7E0EE3262CE8EF1908E",
    ROOT / "homeaura-native-editor" / "EditorCanvas.cs":
        "DF37729621BFA4406EEC12F751895F10DFE3C15428D5DCC4795331A88E5AE863",
    ROOT / "homeaura-native-editor" / "MainForm.cs":
        "C0FF02B661F322F1D2D7D0B7F91EB0C2AD4AEFCB57441BF12DDE4C54044D423A",
    ROOT / "homeaura-native-editor" / "OwnerStyleProposalGenerator.cs":
        "A4B863C543FB635163ECB3F678D95D22437EFB5B80B74A092873E5CDD24183D2",
    ROOT / "homeaura-native-editor" / "README.md":
        "0BA4C3F4D70FD3215EA269118C3C7726A9D6E608043A66080662DE2ECEBBEA6F",
    ROOT / "homeaura-native-editor-tests" / "PhysicalInputSchemaValidation.cs":
        "B32110561728D46F23C167ECA63813050DE88AB0174F06C6AD8C89EDA247BF0C",
    ROOT / "homeaura-native-editor-tests" / "PhysicalInputRendererValidation.cs":
        "FD8FEA3D28D325ACA4205AAC0798DC02EEC568A0C244F06C9AEEA871375889B7",
    ROOT / "homeaura-native-editor-tests" / "Program.cs":
        "6EE05E55746AA2F4031D111BAF94D25C1271AB262C327D264F78EC398DE867A0",
}
EXPECTED_ATTIC_ROOM_IDS = [
    "A-R09", "A-R10", "A-R11", "A-R12", "A-R13", "A-R14", "A-R15", "A-R16",
]
TOP_LEVEL_SCHEMA11_KEYS = [
    "shared_spatial_datum",
    "door_openings",
    "interfloor_openings",
    "floor_architecture_registry_verifications",
    "interfloor_opening_registry_verifications",
]
NESTED_SCHEMA11_KEYS = {
    "levels": ["shared_datum_id", "finished_floor_elevation_mm_shared_datum"],
    "walls": [
        "floor_id", "verified_finish_face_a_outline_mm", "verified_finish_face_b_outline_mm",
        "base_elevation_mm_shared_datum", "top_elevation_mm_shared_datum", "physical_verification",
    ],
    "windows": [
        "floor_id", "verified_plan_outline_mm", "clear_width_mm",
        "sill_elevation_mm_shared_datum", "physical_verification",
    ],
    "floor_build_ups": [
        "build_up_id", "layer_registry", "total_build_up_thickness_mm",
        "allowed_pipe_axis_elevation_mm_shared_datum", "allowed_pipe_axis_tolerance_mm",
        "physical_verification",
    ],
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def deterministic_zip(directory: Path, package: Path) -> None:
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in directory.iterdir() if item.is_file()):
            info = zipfile.ZipInfo(path.name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def validate_sources() -> tuple[dict, dict, dict[str, str]]:
    required = [*EXPECTED_D185_HASHES, *EXPECTED_HISTORICAL_HASHES, *SCHEMA11_IMPLEMENTATION_HASHES]
    missing = [relative(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("D186 inputs are absent: " + ", ".join(missing))

    for path, expected in {
        **EXPECTED_D185_HASHES,
        **EXPECTED_HISTORICAL_HASHES,
        **SCHEMA11_IMPLEMENTATION_HASHES,
    }.items():
        actual = sha(path)
        if actual != expected:
            raise RuntimeError({"D186_pinned_input_changed": {
                "path": relative(path), "actual": actual, "expected": expected,
            }})

    contract = load(SOURCE_CONTRACT)
    manifest = load(SOURCE_MANIFEST)
    project = load(SOURCE_PROJECT)
    if contract.get("artifact_id") != SOURCE_ARTIFACT_ID or \
            contract.get("publication_state") != "OFFICIAL_BOUNDED_TERMINAL_D185" or \
            contract.get("status") != "OFFICIAL_BOUNDED_TERMINAL_D185":
        raise RuntimeError("D186 requires the official D185 contract, not a scaffold")
    if manifest.get("artifact_id") != SOURCE_ARTIFACT_ID or \
            manifest.get("publication_state") != "OFFICIAL_BOUNDED_TERMINAL_D185" or \
            manifest.get("publication_guard_active") is not False:
        raise RuntimeError("D186 requires the official frozen D185 manifest")
    if manifest.get("project_sha256") != sha(SOURCE_PROJECT):
        raise RuntimeError("D185 official manifest/project hash parity failed")
    if contract.get("publishable_as_installation_project") is not False or \
            contract.get("installation_truth", {}).get("installation_ready") is not False or \
            contract.get("installation_truth", {}).get("structured_sleeve_geometry_count") != 0:
        raise RuntimeError("D185 installation/sleeve boundary changed")

    if project.get("schema_version") != "1.0":
        raise RuntimeError("D186 audit is bound to the unchanged schema 1.0 D185 source")
    for name in TOP_LEVEL_SCHEMA11_KEYS:
        if name in project:
            raise RuntimeError(f"D185 unexpectedly acquired schema 1.1 member {name}")
    for collection, names in NESTED_SCHEMA11_KEYS.items():
        for item in project.get(collection, []):
            unexpected = [name for name in names if name in item]
            if unexpected:
                raise RuntimeError(f"D185 {collection} acquired schema 1.1 members {unexpected}")

    attic_rooms = sorted(item["id"] for item in project.get("rooms", []) if item.get("floor_id") == "ATTIC")
    attic_exclusions = sorted(item["id"] for item in project.get("exclusions", []) if item.get("floor_id") == "ATTIC")
    if sorted(item.get("id") for item in project.get("levels", [])) != ["ATTIC", "FLOOR_1"] or \
            attic_rooms != EXPECTED_ATTIC_ROOM_IDS:
        raise RuntimeError("D185 two-floor/ATTIC room baseline changed")
    if attic_exclusions != ["A-X-STAIR"]:
        raise RuntimeError("D185 must retain exactly one A-X-STAIR exclusion")

    walls = project.get("walls", [])
    windows = project.get("windows", [])
    if len(walls) != 33 or len(windows) != 8 or \
            any(not item.get("id", "").startswith("FLOOR_1-") for item in walls) or \
            any(not (item.get("wall_id") or "").startswith("FLOOR_1-") for item in windows):
        raise RuntimeError("D185 legacy wall/window registry changed")
    if any("floor_id" in item for item in [*walls, *windows]):
        raise RuntimeError("D185 legacy wall/window objects must remain unscoped")

    k2 = [item for item in project.get("collectors", []) if item.get("id") == "K2"]
    if len(k2) != 1 or k2[0].get("floor_id") != "FLOOR_1" or k2[0].get("served_floor_id") != "ATTIC":
        raise RuntimeError("D185 K2 cross-floor applicability changed")
    if any(item.get("floor_id") == "ATTIC" for item in project.get("service_zones", [])) or \
            any(item.get("floor_id") == "ATTIC" for item in project.get("floor_build_ups", [])) or \
            any(item.get("collector_id") == "K2" for item in project.get("circuits", [])):
        raise RuntimeError("D185 unexpectedly materialized ATTIC physical/routing input")

    return project, contract, {
        "D185_project": sha(SOURCE_PROJECT),
        "D185_contract": sha(SOURCE_CONTRACT),
        "D185_diagnostics": sha(SOURCE_DIAGNOSTICS),
        "D185_manifest": sha(SOURCE_MANIFEST),
        "D185_package": sha(SOURCE_PACKAGE),
    }


def catalog_entry(
        fields: list[str],
        field_rules: dict[str, str] | None = None,
        whole_record_rule: str =
        "null_or_omitted_until_all_required_populated_fields_are_measured") -> dict:
    entry = {
        "json_fields": fields,
        "unknown_whole_record": None,
        "whole_record_rule": whole_record_rule,
    }
    if field_rules:
        entry["per_field_unknown_or_population_rules"] = field_rules
    return entry


def build_field_catalog() -> dict:
    return {
        "PointMm": catalog_entry(
            ["x_mm", "y_mm", "z_mm"],
            {"object": "null_or_omitted_when_unknown; when present x_mm/y_mm are numeric and z_mm is numeric_or_omitted"},
        ),
        "Point3Mm": catalog_entry(
            ["x_mm", "y_mm", "z_mm"],
            {"object": "null_or_omitted_when_unknown; when present x_mm/y_mm/z_mm are all finite numeric values"},
        ),
        "PhysicalVerification": catalog_entry(
            [
                "status", "measurement_source_type", "source_document_id", "source_document_paths",
                "photo_evidence_paths", "measured_by", "measurement_date", "survey_tolerance_mm",
                "independent_verification_record_ids",
            ],
            {
                "source_document_paths": "omit_when_source_document_id_is_used; otherwise_nonempty_array_no_blank_elements",
                "photo_evidence_paths": "nonempty_array_no_blank_elements_for_independently_verified_record",
                "independent_verification_record_ids": "nonempty_array_no_blank_elements_for_independently_verified_record",
            },
        ),
        "DatumControlPoint": catalog_entry(["id", "floor_id", "position_mm", "reference_description"]),
        "SharedSpatialDatum": catalog_entry(
            [
                "id", "coordinate_reference_description", "horizontal_origin_reference",
                "vertical_zero_reference", "floor_ids_bound_to_datum", "control_points",
                "physical_verification",
            ]
        ),
        "FloorLevel": catalog_entry(
            [
                "id", "name", "origin", "outline", "label_position", "shared_datum_id",
                "finished_floor_elevation_mm_shared_datum",
            ]
        ),
        "WallSegment": catalog_entry(
            [
                "id", "start", "end", "wall_type", "thickness_mm", "floor_id",
                "verified_finish_face_a_outline_mm", "verified_finish_face_b_outline_mm",
                "base_elevation_mm_shared_datum", "top_elevation_mm_shared_datum", "physical_verification",
            ],
            {
                "verified_finish_face_a_outline_mm": "null_or_omitted_when_unknown; measured_nonempty_array_when_present",
                "verified_finish_face_b_outline_mm": "null_or_omitted_when_unknown; measured_nonempty_array_when_present",
            },
        ),
        "WindowOpening": catalog_entry(
            [
                "id", "wall_id", "start", "end", "sill_height_mm", "opening_height_mm", "floor_id",
                "verified_plan_outline_mm", "clear_width_mm", "sill_elevation_mm_shared_datum",
                "physical_verification",
            ],
            {"verified_plan_outline_mm": "null_or_omitted_when_unknown; measured_nonempty_polygon_array_when_present"},
        ),
        "DoorOpening": catalog_entry(
            [
                "id", "floor_id", "wall_id", "start", "end", "verified_plan_outline_mm",
                "clear_width_mm", "clear_height_mm", "threshold_disposition", "threshold_height_mm",
                "threshold_elevation_mm_shared_datum", "physical_verification",
            ],
            {"verified_plan_outline_mm": "null_or_omitted_when_unknown; measured_nonempty_polygon_array_when_present"},
        ),
        "InterfloorOpeningFace": catalog_entry(
            [
                "floor_id", "verified_plan_outline_mm", "center_mm_shared_datum",
                "face_elevation_min_mm_shared_datum", "face_elevation_max_mm_shared_datum",
            ],
            {
                "verified_plan_outline_mm": "null_or_omitted_when_unknown; measured_nonempty_polygon_array_when_present",
                "center_mm_shared_datum": "null_or_omitted_when_unknown; never_a_Point3_object_with_null_components",
            },
        ),
        "StructuralDisposition": catalog_entry(
            [
                "status", "record_id", "authority_name", "authority_document_id",
                "authority_document_paths", "approved_clear_outline_mm", "approval_date", "conditions",
            ],
            {
                "approved_clear_outline_mm":
                    "whole_disposition_unknown=null_or_omitted; "
                    "UNREVIEWED_record=omitted_or_empty_array_never_null; "
                    "EXISTING_OPENING_ACCEPTED_or_NEW_OPENING_APPROVED=nonempty_simple_polygon",
            },
            "null_or_omitted_while_unknown; when_present_status_controls_approved_clear_outline_mm_encoding",
        ),
        "InterfloorOpening": catalog_entry(
            [
                "id", "opening_type", "shape_type", "from_floor_id", "to_floor_id", "shared_datum_id",
                "from_floor_face", "to_floor_face", "clear_depth_mm", "clear_diameter_mm", "clear_width_mm",
                "clear_length_mm", "clear_bottom_elevation_mm_shared_datum",
                "clear_top_elevation_mm_shared_datum", "clear_axis_definition_method",
                "centerline_mm_shared_datum", "clear_axis_vector",
                "clear_axis_azimuth_degrees_shared_datum",
                "clear_axis_inclination_degrees_shared_datum",
                "clear_axis_orientation_tolerance_degrees", "clear_axis_direction",
                "physical_verification", "structural_disposition",
            ],
            {
                "centerline_mm_shared_datum": "null_or_omitted_when_unknown_or_unused; populated_nonempty_numeric_array_only_for_CENTERLINE_POLYLINE",
                "clear_axis_vector": "null_or_omitted_when_unknown_or_unused; populated_finite_Point3_only_for_VECTOR_AND_ORIENTATION",
                "structural_disposition":
                    "null_or_omitted_while_unknown; when_present_follow_StructuralDisposition_state_contract",
            },
        ),
        "FloorLayer": catalog_entry(["id", "material", "thickness_mm"]),
        "FloorBuildUp": catalog_entry(
            [
                "floor_id", "installed_insulation_mm", "remaining_height_mm", "build_up_id",
                "layer_registry", "total_build_up_thickness_mm",
                "allowed_pipe_axis_elevation_mm_shared_datum", "allowed_pipe_axis_tolerance_mm",
                "physical_verification",
            ],
            {"layer_registry": "null_or_omitted_when_unknown; nonempty_array_when_verified"},
        ),
        "FloorArchitectureRegistryVerification": catalog_entry(
            [
                "floor_id", "shared_datum_id", "walls_complete", "windows_complete",
                "doors_and_thresholds_complete", "floor_build_up_complete",
                "allowed_pipe_axis_complete", "physical_verification",
            ]
        ),
        "InterfloorOpeningRegistryVerification": catalog_entry(
            ["from_floor_id", "to_floor_id", "shared_datum_id", "population_complete", "physical_verification"]
        ),
    }


def axis_method_skeleton(method: str, required: list[str], unused: list[str]) -> dict:
    representation_fields = [
        "centerline_mm_shared_datum", "clear_axis_vector",
        "clear_axis_azimuth_degrees_shared_datum",
        "clear_axis_inclination_degrees_shared_datum",
        "clear_axis_orientation_tolerance_degrees", "clear_axis_direction",
    ]
    return {
        "clear_axis_definition_method": method,
        "unpopulated_representation_values": {field: None for field in representation_fields},
        "required_when_independently_verified": required,
        "unused_nullable_fields_must_remain_null_or_be_omitted": unused,
        "required_null_placeholders_must_be_replaced_by_fully_numeric_values_before_submission": True,
        "non_axis_structural_disposition_rule_reference":
            "$.structural_disposition_state_skeletons",
    }


def build_template() -> dict:
    template = {
        "schema": "homeaura.attic.as_built_schema11_input_template.v3",
        "artifact_id": ARTIFACT_ID,
        "target_native_schema_version": "1.1",
        "template_status": "EMPTY_UNVERIFIED_OWNER_SITE_INPUT_TEMPLATE",
        "template_is_directly_loadable_homeaura_project": False,
        "encoding_contract": {
            "unknown_nullable_scalar_or_object": "null_or_omitted",
            "unknown_optional_outline":
                "null_or_omitted_except_StructuralDisposition.approved_clear_outline_mm_on_existing_UNREVIEWED_record",
            "unknown_layer_registry": "null_or_omitted",
            "present_empty_submission_registry_or_declaration": "empty_array",
            "StructuralDisposition_unknown_whole_record": "null_or_omitted",
            "StructuralDisposition_UNREVIEWED_approved_clear_outline_mm":
                "omitted_or_empty_array_never_explicit_null",
            "StructuralDisposition_approved_status_approved_clear_outline_mm": "nonempty_simple_polygon",
            "empty_array_allowed_only_for":
                "present_empty_submission_registry_or_declaration_or_UNREVIEWED_approved_clear_outline_mm",
            "no_global_unknown_collection_default": True,
            "partially_populated_PointMm_or_Point3Mm_forbidden": True,
            "zero_is_never_an_unknown_numeric_sentinel": True,
            "records_must_describe_measured_reality_not_candidate_geometry": True,
        },
        "required_cross_floor_context": {
            "collector_id": "K2", "installed_floor_id": "FLOOR_1", "served_floor_id": "ATTIC",
            "both_required_floors_must_have_complete_verified_architecture": True,
        },
        "native_enum_contract": {
            "physical_verification_status": ["UNVERIFIED", "MEASURED", "INDEPENDENTLY_VERIFIED"],
            "opening_type": ["SLAB_OPENING", "CORE_PENETRATION", "SHAFT", "STAIR_VOID"],
            "shape_type": ["CIRCULAR", "RECTANGULAR", "NONRECTANGULAR"],
            "clear_axis_definition_method": ["FACE_CENTERS", "CENTERLINE_POLYLINE", "VECTOR_AND_ORIENTATION"],
            "clear_axis_direction": ["FROM_TO", "TO_FROM"],
            "threshold_disposition": ["NONE", "FLUSH", "RAISED"],
            "structural_disposition_status": [
                "UNREVIEWED", "EXISTING_OPENING_ACCEPTED", "NEW_OPENING_APPROVED", "PROHIBITED",
            ],
        },
        "native_field_catalog": build_field_catalog(),
        "axis_method_skeletons": {
            "FACE_CENTERS": axis_method_skeleton(
                "FACE_CENTERS",
                ["from_floor_face.center_mm_shared_datum", "to_floor_face.center_mm_shared_datum"],
                [
                    "centerline_mm_shared_datum", "clear_axis_vector",
                    "clear_axis_azimuth_degrees_shared_datum",
                    "clear_axis_inclination_degrees_shared_datum",
                    "clear_axis_orientation_tolerance_degrees", "clear_axis_direction",
                ],
            ),
            "CENTERLINE_POLYLINE": axis_method_skeleton(
                "CENTERLINE_POLYLINE",
                ["centerline_mm_shared_datum"],
                [
                    "clear_axis_vector", "clear_axis_azimuth_degrees_shared_datum",
                    "clear_axis_inclination_degrees_shared_datum",
                    "clear_axis_orientation_tolerance_degrees", "clear_axis_direction",
                ],
            ),
            "VECTOR_AND_ORIENTATION": axis_method_skeleton(
                "VECTOR_AND_ORIENTATION",
                [
                    "clear_axis_vector", "clear_axis_azimuth_degrees_shared_datum",
                    "clear_axis_inclination_degrees_shared_datum",
                    "clear_axis_orientation_tolerance_degrees", "clear_axis_direction",
                ],
                ["centerline_mm_shared_datum"],
            ),
        },
        "structural_disposition_state_skeletons": {
            "UNKNOWN": {
                "structural_disposition": None,
                "whole_field_may_be_omitted": True,
            },
            "UNREVIEWED_RECORD": {
                "structural_disposition": {
                    "status": "UNREVIEWED",
                    "approved_clear_outline_mm": [],
                },
                "approved_clear_outline_mm_encoding":
                    "shown_as_present_empty_array; property_may_instead_be_omitted; explicit_null_forbidden",
            },
            "APPROVED_RECORD": {
                "allowed_statuses": ["EXISTING_OPENING_ACCEPTED", "NEW_OPENING_APPROVED"],
                "approved_clear_outline_mm_encoding": "required_nonempty_simple_polygon",
            },
        },
        "empty_input_records": {
            "level_physical_input_records": [], "shared_spatial_datum": None, "walls": [], "windows": [],
            "door_openings": [], "floor_build_ups": [], "floor_architecture_registry_verifications": [],
            "interfloor_openings": [], "interfloor_opening_registry_verifications": [],
        },
        "physical_verification_semantics": [
            "Routing readiness accepts only INDEPENDENTLY_VERIFIED records with measurement_source_type, measured_by, yyyy-MM-dd measurement_date, positive survey_tolerance_mm, and source_document_id OR a nonempty source_document_paths array.",
            "photo_evidence_paths and independent_verification_record_ids are nonempty for independently verified records; every evidence array contains no blank element.",
            "A verified shared datum requires nonempty coordinate/horizontal/vertical references, a resolvable horizontal-origin control-point id, and at least one finite control point on every bound floor.",
        ],
        "opening_shape_and_axis_semantics": [
            "CIRCULAR requires clear_diameter_mm, forbids width/length, and requires at least eight distinct measured points on each declared circle; each axis-aligned X/Y face extent equals the diameter within survey tolerance.",
            "RECTANGULAR requires clear_width_mm and clear_length_mm, forbids diameter, and each face is exactly the four axis-aligned bbox corners; width is maxX-minX and length is maxY-minY with no swapped or rotated interpretation.",
            "NONRECTANGULAR forbids diameter/width/length; its two verified_plan_outline_mm face polygons are the complete shape records.",
            "center_mm_shared_datum is the only face-center representation: bbox midpoint for CIRCULAR/RECTANGULAR and polygon centroid for NONRECTANGULAR, within survey tolerance.",
            "FACE_CENTERS forbids centerline and every vector/orientation field; clear_depth_mm is the Euclidean 3D distance between face centers.",
            "CENTERLINE_POLYLINE requires centerline_mm_shared_datum endpoints at the face centers, forbids every vector/orientation field, and clear_depth_mm is the sum of its nonzero 3D segment lengths.",
            "VECTOR_AND_ORIENTATION forbids centerline, requires nonzero clear_axis_vector plus numeric azimuth, inclination, declared angular tolerance, and FROM_TO/TO_FROM direction; clear_depth_mm remains the 3D face-center distance rather than vector magnitude.",
            "clear_bottom/top elevations equal the minimum/maximum face-center Z values within survey tolerance; their vertical span cannot exceed clear_depth_mm.",
            "Every CENTERLINE_POLYLINE point has finite numeric XYZ, XY inside the project canvas, and Z inside the declared clear_bottom/top interval within survey tolerance.",
            "Each face elevation min/max range lies inside the declared clear_bottom/top interval, and center_mm_shared_datum.Z lies inside its own face range within survey tolerance.",
            "For VECTOR_AND_ORIENTATION, vector-derived azimuth and inclination agree with declared numeric angles within clear_axis_orientation_tolerance_degrees.",
            "For VECTOR_AND_ORIENTATION, clear_axis_vector is collinear/aligned with the from-face-to-to-face center displacement within clear_axis_orientation_tolerance_degrees, and clear_axis_direction agrees with the sign of their dot product.",
        ],
        "architecture_and_floor_semantics": [
            "All 33 legacy walls and 8 legacy windows must receive truthful floor scope before the cross-floor architecture scope gate can pass; filename/id prefixes are not floor attribution.",
            "Each verified wall is a nonzero orthogonal centerline with two measured collinear finish-face spans symmetric about it, separated by thickness_mm, plus base/top shared-datum elevations.",
            "Every verified polygon is nondegenerate, has nonzero area, is simple, and has no self-intersection.",
            "Each verified window/door references a verified wall on the same floor; start/end, clear width, four-corner wall-body outline, heights, sill/threshold elevation, and evidence agree within survey tolerance.",
            "A window vertical interval [sill_elevation_mm_shared_datum, sill_elevation_mm_shared_datum + opening_height_mm] lies fully inside its parent wall [base_elevation_mm_shared_datum, top_elevation_mm_shared_datum] within survey tolerance.",
            "Door NONE requires threshold_height_mm null_or_zero and threshold_elevation_mm_shared_datum null; resolved_bottom is floor FFL. FLUSH requires height null_or_zero and threshold elevation equal to FFL within tolerance; resolved_bottom is threshold elevation. RAISED requires positive height and threshold elevation equal to FFL plus height within tolerance; resolved_bottom is threshold elevation.",
            "A door vertical interval [resolved_bottom, resolved_bottom + clear_height_mm] lies fully inside its parent wall [base_elevation_mm_shared_datum, top_elevation_mm_shared_datum] within survey tolerance.",
            "Door thresholds are fields of DoorOpening; schema 1.1 has no standalone threshold collection.",
            "Floor total_build_up_thickness_mm equals both the layer_registry sum and installed_insulation_mm plus remaining_height_mm; the allowed pipe-axis elevation plus/minus tolerance lies inside [FFL-total, FFL].",
            "Exactly one independently verified FloorBuildUp exists for each required physical floor.",
            "Complete, independently verified floor and interfloor population declarations are required; an exclusion or out-of-plane length is never proof of an opening.",
        ],
        "structural_disposition_boundary": {
            "required_for_empty_evidence_gate": False,
            "required_before_installation_input_readiness": True,
            "approved_status_requires_record_authority_date_document_and_outline_covering_both_faces": True,
            "unknown_structural_disposition_is_null_or_omitted": True,
            "UNREVIEWED_record_approved_clear_outline_is_omitted_or_empty_array_never_null": True,
            "approved_status_requires_nonempty_simple_approved_clear_outline": True,
            "approved_outline_is_nondegenerate_simple_and_contains_both_full_face_polygon_areas": True,
            "approved_outline_contains_the_full_projected_axis_not_only_axis_vertices": True,
        },
        "native_capability_limit": {
            "segment_to_opening_route_binding_modeled": False,
            "physical_installation_completeness_can_pass_for_cross_floor_D185_upgrade": False,
        },
        "template_populated": False,
        "owner_style_route_release": False,
        "installation_ready": False,
    }
    template["template_digest"] = digest(template)
    return template


def build_gate(project: dict, source_hashes: dict[str, str]) -> dict:
    attic_rooms = sorted(item["id"] for item in project["rooms"] if item.get("floor_id") == "ATTIC")
    implementation_binding = [
        {"path": relative(path), "sha256": expected}
        for path, expected in SCHEMA11_IMPLEMENTATION_HASHES.items()
    ]
    gate = {
        "schema": "homeaura.attic.verified_physical_input_gate.v3",
        "artifact_id": ARTIFACT_ID,
        "status": BLOCKED_REASON,
        "blocked_reason": BLOCKED_REASON,
        "scope": "EVIDENCE_ONLY_NO_HOMEAURA_GEOMETRY",
        "publication_state": "SCAFFOLD_REVIEW_REQUIRED_NOT_OFFICIAL",
        "source_records": [
            {
                "source_key": "D185_PROJECT", "artifact_id": SOURCE_ARTIFACT_ID,
                "classification": "AUTHORITATIVE_CURRENT_NATIVE_PROJECT_SCHEMA_1_0",
                "path": relative(SOURCE_PROJECT), "sha256": source_hashes["D185_project"],
            },
            {
                "source_key": "D185_CONTRACT", "artifact_id": SOURCE_ARTIFACT_ID,
                "classification": "AUTHORITATIVE_BOUNDED_TERMINAL_RELEASE_CONTRACT",
                "path": relative(SOURCE_CONTRACT), "sha256": source_hashes["D185_contract"],
            },
            {
                "source_key": "D185_DIAGNOSTICS", "artifact_id": SOURCE_ARTIFACT_ID,
                "classification": "AUTHORITATIVE_EXACT_ENGINEERING_DIAGNOSTICS",
                "path": relative(SOURCE_DIAGNOSTICS), "sha256": source_hashes["D185_diagnostics"],
            },
            {
                "source_key": "D185_MANIFEST", "artifact_id": SOURCE_ARTIFACT_ID,
                "classification": "AUTHORITATIVE_OFFICIAL_MANIFEST",
                "path": relative(SOURCE_MANIFEST), "sha256": source_hashes["D185_manifest"],
            },
            {
                "source_key": "D185_PACKAGE", "artifact_id": SOURCE_ARTIFACT_ID,
                "classification": "AUTHORITATIVE_OFFICIAL_PACKAGE",
                "path": relative(SOURCE_PACKAGE), "sha256": source_hashes["D185_package"],
            },
            {
                "source_key": "D181", "artifact_id": "HA_TWO_FLOOR_ATTIC_SOURCE_WALL_DOMAINS_181",
                "classification": "NON_AUTHORITATIVE_WALL_DOMAIN_CANDIDATES", "path": relative(D181_CONTRACT),
                "sha256": EXPECTED_HISTORICAL_HASHES[D181_CONTRACT],
                "allowed_use": "candidate comparison only; never wall thickness/opening/materialization input",
            },
            {
                "source_key": "D137", "artifact_id": "HA_TWO_FLOOR_PRIMARY_RELEASE_STATE_BINDING_137",
                "classification": "NON_AUTHORITATIVE_EVIDENCE", "path": relative(D137_EVIDENCE),
                "sha256": EXPECTED_HISTORICAL_HASHES[D137_EVIDENCE],
                "allowed_use": "historical evidence only; no ATTIC coordinates, sizes, elevations, or release",
            },
            {
                "source_key": "D166", "artifact_id": "HA_TWO_FLOOR_K2_SERVICE_LAYER_166",
                "classification": "NON_AUTHORITATIVE_EVIDENCE", "path": relative(D166_EVIDENCE),
                "sha256": EXPECTED_HISTORICAL_HASHES[D166_EVIDENCE],
                "allowed_use": "historical evidence only; no K2 route, opening, service-zone, or installation release",
            },
        ],
        "native_schema_11_capability_binding": {
            "implemented": True,
            "reader_accepts_schema_versions": ["1.0", "1.1"],
            "typed_shared_datum_architecture_opening_build_up_and_registry_input": True,
            "physical_input_readiness_analyzer": True,
            "active_floor_physical_renderer": True,
            "owner_style_transform_rejects_schema_11": True,
            "segment_to_opening_route_binding_modeled": False,
            "runtime_test_doc_surface_file_count": len(implementation_binding),
            "implementation_files": implementation_binding,
            "acceptance_evidence_binding": {
                "surface_binding_digest": digest(implementation_binding),
                "release_build_result": "PASS_0_WARNINGS_0_ERRORS",
                "registered_suite_result": "RESULT_56_OF_56_PASSED",
                "registered_suite_program_path": relative(ROOT / "homeaura-native-editor-tests" / "Program.cs"),
                "registered_suite_program_sha256": SCHEMA11_IMPLEMENTATION_HASHES[
                    ROOT / "homeaura-native-editor-tests" / "Program.cs"
                ],
                "D185_diagnostics_exact_path": relative(SOURCE_DIAGNOSTICS),
                "D185_diagnostics_exact_sha256": source_hashes["D185_diagnostics"],
                "D185_manifest_sha256": source_hashes["D185_manifest"],
                "D185_package_sha256": source_hashes["D185_package"],
            },
            "schema11_final_GO_received": True,
            "independent_D186_package_reviewer_GO_required_before_official_freeze": True,
        },
        "verified_current_native_state": {
            "source_project_schema_version": "1.0",
            "ATTIC_level_count": 1,
            "ATTIC_finish_face_room_count": len(attic_rooms),
            "ATTIC_finish_face_room_ids": attic_rooms,
            "ATTIC_stair_exclusion_count": 1,
            "ATTIC_stair_exclusion_ids": ["A-X-STAIR"],
            "source_project_legacy_wall_count": len(project["walls"]),
            "source_project_legacy_window_count": len(project["windows"]),
            "unscoped_wall_count": len(project["walls"]),
            "unscoped_window_count": len(project["windows"]),
            "schema_11_typed_values_present": False,
            "shared_spatial_datum": None,
            "door_openings": [],
            "interfloor_openings": [],
            "floor_architecture_registry_verifications": [],
            "interfloor_opening_registry_verifications": [],
            "ATTIC_service_zone_count": 0,
            "ATTIC_floor_build_up_count": 0,
            "K2_route_count": 0,
        },
        "direct_physical_input_readiness_expected_from_D185": {
            "applicable": True,
            "cross_floor_collector_ids": ["K2"],
            "architecture_floor_scope_pass": False,
            "unscoped_wall_count": 33,
            "unscoped_window_count": 8,
            "verified_architecture_input_pass": False,
            "verified_interfloor_opening_input_pass": False,
            "routing_input_readiness_pass": False,
            "structural_disposition_pass": False,
            "route_opening_binding_pass": False,
            "installation_input_readiness_pass": False,
            "reason_codes": [
                "UNSCOPED_ARCHITECTURE_OBJECTS",
                "VERIFIED_FLOOR_ARCHITECTURE_INCOMPLETE",
                "VERIFIED_INTERFLOOR_OPENING_INPUT_INCOMPLETE",
                "STRUCTURAL_DISPOSITION_INCOMPLETE",
                "MATERIALIZED_ROUTE_OPENING_BINDING_NOT_MODELED",
            ],
        },
        "required_verified_input": {
            "template_file": TEMPLATE_NAME,
            "source_upgrade_target": "schema_version 1.1 only after measured values exist",
            "shared_spatial_datum_and_control_points_for_both_floors": "REQUIRED",
            "truthful_floor_scope_for_all_33_walls_and_8_windows": "REQUIRED",
            "complete_verified_FLOOR_1_and_ATTIC_architecture_registries": "REQUIRED",
            "each_real_FLOOR_1_ATTIC_opening_with_paired_faces_shape_centers_axis_depth_and_evidence": "REQUIRED",
            "complete_verified_interfloor_opening_population_declaration": "REQUIRED",
            "verified_floor_build_up_FFL_and_allowed_pipe_axis_for_both_required_floors": "REQUIRED",
            "structural_disposition": "REQUIRED_BEFORE_INSTALLATION_INPUT_READINESS",
            "segment_to_opening_binding": "NOT_MODELED_IN_SCHEMA_1_1",
        },
        "release_boundary": {
            "verified_architecture_input_pass": False,
            "verified_interfloor_opening_input_pass": False,
            "routing_input_readiness_pass": False,
            "structural_disposition_pass": False,
            "route_opening_binding_pass": False,
            "installation_input_readiness_pass": False,
            "physical_installation_completeness_pass": False,
            "owner_style_route_release": False,
            "K2_route_release": False,
            "installation_ready": False,
            "install": False,
            "official_D186_freeze_allowed": False,
            "root_review_required": True,
            "independent_D186_package_reviewer_GO_received": False,
        },
        "materialization_boundary": {
            "added_geometry_count": 0,
            "homeaura_geometry_created_or_changed": False,
            "homeaura_file_count_in_D186": 0,
            "render_file_count_in_D186": 0,
            "sleeves_added": False,
            "walls_added": 0,
            "windows_added": 0,
            "doors_added": 0,
            "holes_or_penetrations_added": 0,
            "service_zones_added": 0,
            "floor_build_ups_added": 0,
            "K2_routes_added": 0,
        },
        "result": BLOCKED_REASON,
    }
    gate["gate_digest"] = digest(gate)
    return gate


def build_payload(stage: Path, project: dict, source_hashes: dict[str, str]) -> None:
    dump(stage / GATE_NAME, build_gate(project, source_hashes))
    dump(stage / TEMPLATE_NAME, build_template())

    readme = (
        "# D186 scaffold · verified physical input gate мансарды\n\n"
        "Это evidence-only scaffold после официального D185. Native schema 1.1 уже реализована и "
        "поддерживает typed shared datum, физически проверенную архитектуру, DoorOpening, InterfloorOpening, "
        "пирог пола, декларации полноты, fail-closed readiness и active-floor rendering. Файлы реализации "
        "привязаны SHA256 в gate. Это исправляет прежнее устаревшее утверждение о пробеле native schema.\n\n"
        f"Источник D185 остаётся schema 1.0 и не меняется: project SHA256 `{source_hashes['D185_project']}`, "
        f"contract SHA256 `{source_hashes['D185_contract']}`. В нём отсутствуют все typed значения 1.1. "
        "K2 по-прежнему объявлен FLOOR_1→ATTIC, поэтому прямой PhysicalInputReadiness applicable=true, но "
        "33 стены и 8 окон не имеют floor_id; verified architecture/openings/routing/structural/install=false.\n\n"
        f"Diagnostics SHA256 `{source_hashes['D185_diagnostics']}`, manifest SHA256 "
        f"`{source_hashes['D185_manifest']}`, официальный ZIP SHA256 `{source_hashes['D185_package']}`. "
        "Девять runtime/test/doc файлов schema 1.1 привязаны полными SHA256; только для этой поверхности "
        "зафиксированы Release 0/0, registered 56/56 и exact D185 diagnostics.\n\n"
        "Шаблон зеркалит фактические JSON DTO schema 1.1. В нём нет придуманных bbox, face_id, отдельного "
        "реестра порогов, альтернативного Point2-центра или старых enum оси. Допустимые способы оси: "
        "FACE_CENTERS, CENTERLINE_POLYLINE, VECTOR_AND_ORIENTATION. RECTANGULAR width/length — строго "
        "axis-aligned X/Y bbox spans без перестановки. Door threshold хранится внутри DoorOpening. "
        "Неизвестный nullable объект/скаляр и обычный optional outline/layer_registry — null или omitted; "
        "исключение точно следует DTO: неизвестный StructuralDisposition целиком null/omitted, но если запись "
        "уже существует со статусом UNREVIEWED, approved_clear_outline_mm только omitted или [], никогда null; "
        "approved status требует непустой простой polygon. Частично заполненный PointMm/Point3Mm запрещён. "
        "Пустые [] используются только для реально присутствующих пустых submission registries/declarations "
        "и approved_clear_outline_mm существующей UNREVIEWED записи. Три axis skeleton разделены, неиспользуемые nullable "
        "представления оси равны null/omitted; числовые подстановки-сентинелы запрещены.\n\n"
        "Strict contract требует простые невырожденные полигоны; полную XY/Z оболочку centerline и граней; "
        "согласованные vector/azimuth/inclination/direction и коллинеарность вектора смещению центров граней "
        "в пределах clear_axis_orientation_tolerance_degrees; конструктивный контур, содержащий площади обеих "
        "граней и всю проекцию оси; вертикальные интервалы окон/дверей внутри стены; точные NONE/FLUSH/RAISED; "
        "ровно один independently verified build-up на каждый требуемый этаж.\n\n"
        "Даже после полного verified input schema 1.1 не содержит segment-to-opening binding, поэтому "
        "physical installation completeness для cross-floor остаётся false. D186 не содержит `.homeaura`, "
        "PNG/PDF, стен, трасс, гильз или K2 materialization. Official freeze и регистрация теста заблокированы "
        "до независимого D186 package reviewer GO и root review.\n"
    )
    (stage / "README.md").write_text(readme, encoding="utf-8")

    implementation_binding = [
        {"path": relative(path), "sha256": expected}
        for path, expected in SCHEMA11_IMPLEMENTATION_HASHES.items()
    ]
    status = {
        "artifact_id": ARTIFACT_ID,
        "result": BLOCKED_REASON,
        "blocked_reason": BLOCKED_REASON,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_project_schema_version": "1.0",
        "source_project_sha256": source_hashes["D185_project"],
        "source_contract_sha256": source_hashes["D185_contract"],
        "source_diagnostics_sha256": source_hashes["D185_diagnostics"],
        "source_manifest_sha256": source_hashes["D185_manifest"],
        "source_package_sha256": source_hashes["D185_package"],
        "native_schema_11_implemented": True,
        "runtime_test_doc_surface_file_count": len(implementation_binding),
        "implementation_binding_digest": digest(implementation_binding),
        "release_build_result": "PASS_0_WARNINGS_0_ERRORS",
        "registered_suite_result": "RESULT_56_OF_56_PASSED",
        "registered_suite_program_path": relative(ROOT / "homeaura-native-editor-tests" / "Program.cs"),
        "registered_suite_program_sha256": SCHEMA11_IMPLEMENTATION_HASHES[
            ROOT / "homeaura-native-editor-tests" / "Program.cs"
        ],
        "direct_D185_physical_input_applicable": True,
        "direct_D185_verified_architecture_pass": False,
        "direct_D185_verified_interfloor_opening_pass": False,
        "direct_D185_route_opening_binding_pass": False,
        "direct_D185_installation_input_pass": False,
        "evidence_only": True,
        "added_geometry_count": 0,
        "homeaura_file_count": 0,
        "render_file_count": 0,
        "sleeves_added": False,
        "owner_style_route_release": False,
        "K2_route_release": False,
        "install": False,
        "installation_ready": False,
        "template_populated": False,
        "publication_state": "SCAFFOLD_REVIEW_REQUIRED_NOT_OFFICIAL",
        "publishable": False,
        "official_files_modified": False,
        "root_review_required": True,
        "schema11_final_GO_received": True,
        "independent_D186_package_reviewer_GO_received": False,
        "official_D186_freeze_allowed": False,
    }
    dump(stage / "status.json", status)

    payloads = sorted(path for path in stage.iterdir() if path.is_file())
    manifest = {
        "artifact_id": ARTIFACT_ID,
        "append_only": True,
        "evidence_only": True,
        "publication_state": "SCAFFOLD_REVIEW_REQUIRED_NOT_OFFICIAL",
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_project_sha256": source_hashes["D185_project"],
        "source_contract_sha256": source_hashes["D185_contract"],
        "source_diagnostics_sha256": source_hashes["D185_diagnostics"],
        "source_manifest_sha256": source_hashes["D185_manifest"],
        "source_package_sha256": source_hashes["D185_package"],
        "deterministic_generator": {"path": relative(Path(__file__)), "sha256": sha(Path(__file__))},
        "runtime_test_doc_surface_file_count": len(implementation_binding),
        "schema11_implementation_files": implementation_binding,
        "acceptance_evidence_binding": {
            "surface_binding_digest": digest(implementation_binding),
            "release_build_result": "PASS_0_WARNINGS_0_ERRORS",
            "registered_suite_result": "RESULT_56_OF_56_PASSED",
            "registered_suite_program_path": relative(ROOT / "homeaura-native-editor-tests" / "Program.cs"),
            "registered_suite_program_sha256": SCHEMA11_IMPLEMENTATION_HASHES[
                ROOT / "homeaura-native-editor-tests" / "Program.cs"
            ],
            "D185_diagnostics_exact_sha256": source_hashes["D185_diagnostics"],
            "D185_manifest_sha256": source_hashes["D185_manifest"],
            "D185_package_sha256": source_hashes["D185_package"],
        },
        "zip_contract": {
            "member_order": "LEXICOGRAPHIC_FILENAME",
            "timestamp": "1980-01-01T00:00:00",
            "compression": "DEFLATE_LEVEL_9",
            "directory_prefix": False,
        },
        "homeaura_file_count": 0,
        "render_file_count": 0,
        "files": [
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}
            for path in payloads
        ],
    }
    dump(stage / "artifact_manifest.json", manifest)


def compare_existing(stage: Path, staged_package: Path) -> None:
    if not OUTPUT.is_dir() or not PACKAGE.is_file():
        raise RuntimeError("D186 append-only output/package is only partially present")
    expected_names = sorted(path.name for path in stage.iterdir() if path.is_file())
    actual_names = sorted(path.name for path in OUTPUT.iterdir() if path.is_file())
    if actual_names != expected_names:
        raise RuntimeError("D186 append-only payload member set changed")
    for name in expected_names:
        if (OUTPUT / name).read_bytes() != (stage / name).read_bytes():
            raise RuntimeError(f"D186 deterministic payload parity failed: {name}")
    if PACKAGE.read_bytes() != staged_package.read_bytes():
        raise RuntimeError("D186 deterministic ZIP parity failed")


def safe_refresh_scaffold() -> None:
    expected_output = (ROOT / "tmp" / "D186_scaffold").resolve()
    expected_package = (ROOT / "tmp" / f"{ARTIFACT_ID}_SCAFFOLD.zip").resolve()
    if OUTPUT.resolve() != expected_output or PACKAGE.resolve() != expected_package:
        raise RuntimeError("Unsafe D186 scaffold refresh target")
    if OUTPUT.exists():
        if not OUTPUT.is_dir():
            raise RuntimeError("D186 scaffold output target is not a directory")
        shutil.rmtree(OUTPUT)
    if PACKAGE.exists():
        if not PACKAGE.is_file():
            raise RuntimeError("D186 scaffold package target is not a file")
        PACKAGE.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-scaffold", action="store_true")
    args = parser.parse_args()
    project, _contract, source_hashes = validate_sources()
    TMP.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="D186_stage_", dir=TMP) as temporary:
        stage = Path(temporary) / ARTIFACT_ID
        stage.mkdir()
        build_payload(stage, project, source_hashes)
        staged_package = Path(temporary) / PACKAGE.name
        deterministic_zip(stage, staged_package)

        if OUTPUT.exists() or PACKAGE.exists():
            if args.refresh_scaffold:
                safe_refresh_scaffold()
                shutil.move(str(stage), str(OUTPUT))
                shutil.move(str(staged_package), str(PACKAGE))
                action = "REFRESHED_OWNED_REVIEWABLE_SCAFFOLD_OFFICIAL_FREEZE_BLOCKED"
            else:
                compare_existing(stage, staged_package)
                action = "DETERMINISTIC_PARITY_PASS_EXISTING_SCAFFOLD_UNCHANGED"
        else:
            shutil.move(str(stage), str(OUTPUT))
            shutil.move(str(staged_package), str(PACKAGE))
            action = "CREATED_REVIEWABLE_SCAFFOLD_OFFICIAL_FREEZE_BLOCKED"

    print(json.dumps({
        "artifact_id": ARTIFACT_ID,
        "action": action,
        "result": BLOCKED_REASON,
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "source_project_sha256": source_hashes["D185_project"],
        "source_contract_sha256": source_hashes["D185_contract"],
        "added_geometry_count": 0,
        "homeaura_file_count": 0,
        "render_file_count": 0,
        "package_sha256": sha(PACKAGE),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

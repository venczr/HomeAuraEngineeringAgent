from __future__ import annotations

import hashlib
import json
import copy
from uuid import UUID
from pathlib import Path

from agent.rooms_api import MagiCadRoom, RoomExportReport
from agent.domain_adapter import adapt_rooms_payload
from agent.domain_models import EntitySource, SourceKind, ValidationStatus
from agent.ufh_auto_retry import assess_with_automatic_split_retry
from agent.ufh_project_adapter import (
    ProjectFieldProvenance,
    ProjectRoomUfhSource,
    build_ufh_sizing_request_from_project_room,
)
from agent.ufh_project_engineering_profile import ProfileValueProvenance
from agent.ufh_project_engineering_profile_authoring import (
    load_ufh_project_engineering_authoring_template,
    synthetic_complete_authoring_payload,
)
from tests.test_floor_heating_sizing import sizing_request
from tests.test_ufh_candidate_adapter import engineering_inputs


ROOT = Path(__file__).resolve().parents[1]
TEST01_ROOMS = ROOT / "projects" / "Test_01" / "exports" / "rooms" / "rooms.json"


def _provenance(source_kind: str, source_file: str, digest: str, path: str):
    return ProjectFieldProvenance(
        source_kind=source_kind,
        source_file=source_file,
        source_sha256=digest,
        source_path=path,
    )


def _leaves(value, path):
    if isinstance(value, dict) and value:
        for key, child in value.items():
            yield from _leaves(child, f"{path}.{key}")
    elif isinstance(value, list) and value:
        for index, child in enumerate(value):
            yield from _leaves(child, f"{path}[{index}]")
    else:
        yield path


def _source_test01():
    raw = TEST01_ROOMS.read_bytes()
    report = RoomExportReport.model_validate_json(raw)
    room = next(item for item in report.Rooms if item.SourceHandle == "101DAA3")
    return ProjectRoomUfhSource(
        project_id="Test_01",
        building_id=None,
        level_id=None,
        room_id=room.SourceHandle,
        room_export=report,
        selected_room=room,
        source_file=str(TEST01_ROOMS),
        source_sha256=hashlib.sha256(raw).hexdigest(),
        source_kind="room_extraction",
    )


def _complete_test_source():
    request = sizing_request(4000, 3000)
    eng = engineering_inputs()
    report = RoomExportReport(
        FormatVersion="1.0",
        ParserVersion="test-only",
        GeneratedAtUtc="2026-01-01T00:00:00Z",
        DrawingName="test-only.dwg",
        DrawingFullPath="test-only://project.dwg",
        FoundMarkers=1,
        Rooms=[MagiCadRoom(
            SourceHandle="room-4000x3000",
            SourceLayer="TEST_ONLY",
            Position={"X": 0, "Y": 0, "Z": 0},
            Code="T-01",
            Name="Synthetic complete adapter room",
            HeatingTemperatureC=21.0,
            RoomHeightMm=2700.0,
            NetAreaM2=12.0,
            AirExchangeRate=0.4,
            Boundary={
                "SourceHandle": "boundary-01",
                "SourceObjectType": "Polyline",
                "SourceLayer": "ROOM_BOUNDARY",
                "Vertices": [
                    {"X": 0, "Y": 0, "Z": 0, "Bulge": 0, "SegmentType": "Line"},
                    {"X": 4000, "Y": 0, "Z": 0, "Bulge": 0, "SegmentType": "Line"},
                    {"X": 4000, "Y": 3000, "Z": 0, "Bulge": 0, "SegmentType": "Line"},
                    {"X": 0, "Y": 3000, "Z": 0, "Bulge": 0, "SegmentType": "Line"},
                    {"X": 0, "Y": 0, "Z": 0, "Bulge": 0, "SegmentType": "Line"},
                ],
                "IsClosed": True,
                "DrawingUnits": "Millimeters",
                "GeometrySource": "TEST_ONLY",
                "IsPlanar": True,
                "Diagnostics": {"IsSupported": True, "IsValid": True},
            },
        )],
    )
    report_bytes = report.model_dump_json(by_alias=True).encode()
    digest = hashlib.sha256(report_bytes).hexdigest()
    domain = adapt_rooms_payload(
        report.model_dump(mode="json", by_alias=True),
        project_id="synthetic-ufh-project",
    )
    building = domain.project.buildings[0].model_copy(update={
        "stable_id": UUID("00000000-0000-4000-8000-000000000101"),
        "name": "Test building",
        "source": EntitySource(
            kind=SourceKind.DERIVED_DETERMINISTIC,
            system="test-only project fixture",
            identifiers={"fixture": "UFH_PROJECT_TO_SIZING_ADAPTER_V1"},
        ),
        "validation_status": ValidationStatus.VALIDATED,
        "diagnostics": [],
    })
    level = building.levels[0].model_copy(update={
        "stable_id": UUID("00000000-0000-4000-8000-000000000102"),
        "name": "Level 1",
        "source": EntitySource(
            kind=SourceKind.DERIVED_DETERMINISTIC,
            system="test-only project fixture",
            identifiers={"fixture": "UFH_PROJECT_TO_SIZING_ADAPTER_V1"},
        ),
        "validation_status": ValidationStatus.VALIDATED,
        "diagnostics": [],
    })
    building = building.model_copy(update={"levels": [level]})
    project = domain.project.model_copy(update={"buildings": [building]})
    domain = domain.model_copy(update={"project": project})
    project_id = domain.project.name
    building_id = str(domain.project.buildings[0].stable_id)
    level_id = str(domain.project.buildings[0].levels[0].stable_id)
    domain_room = domain.project.buildings[0].levels[0].rooms[0]
    room_id = domain_room.source_handle
    domain_bytes = json.dumps(
        domain.model_dump(mode="json"), ensure_ascii=False,
        sort_keys=True, separators=(",", ":"),
    ).encode()
    domain_digest = hashlib.sha256(domain_bytes).hexdigest()
    coverage = request.coverage_request.model_copy(update={
        "project_id": project_id,
        "room_id": room_id,
    })
    request = request.model_copy(update={"coverage_request": coverage})
    sizing_values = request.model_dump(mode="python")
    engineering_values = eng.model_dump(mode="python")
    sizing_json = request.model_dump(mode="json")
    engineering_json = eng.model_dump(mode="json")
    prov = {}
    for path in _leaves(sizing_json, "sizing"):
        prov[path] = _provenance(
            "test_only", "tests/test_ufh_project_adapter.py#complete-project-room",
            digest, f"synthetic-source:{path}",
        )
    for path in _leaves(engineering_json, "engineering"):
        prov[path] = _provenance(
            "test_only", "tests/test_ufh_project_adapter.py#complete-project-room",
            digest, f"synthetic-source:{path}",
        )
    return ProjectRoomUfhSource(
        project_id=project_id,
        building_id=building_id,
        level_id=level_id,
        room_id=room_id,
        room_source_handle=report.Rooms[0].SourceHandle,
        room_export=report,
        project_domain=domain,
        project_domain_source_file="tests/test_ufh_project_adapter.py#synthetic-domain-object",
        project_domain_sha256=domain_digest,
        selected_room=report.Rooms[0],
        source_file="tests/test_ufh_project_adapter.py#complete-project-room",
        source_sha256=digest,
        source_kind="test_only",
        identity_provenance={
            "identity.project_id": _provenance(
                "test_only", "tests/test_ufh_project_adapter.py", domain_digest,
                "synthetic-project.project.name",
            ),
            "identity.building_id": _provenance(
                "test_only", "tests/test_ufh_project_adapter.py", domain_digest,
                "synthetic-project.project.buildings[0].stable_id",
            ),
            "identity.level_id": _provenance(
                "test_only", "tests/test_ufh_project_adapter.py", domain_digest,
                "synthetic-project.project.buildings[0].levels[0].stable_id",
            ),
            "identity.room_id": _provenance(
                "test_only", "tests/test_ufh_project_adapter.py", domain_digest,
                "synthetic-project.project.buildings[0].levels[0].rooms[0].source_handle",
            ),
        },
        sizing_inputs=sizing_values,
        engineering_inputs=engineering_values,
        input_provenance=prov,
    )


def test_discovers_real_test01_room_and_maps_only_present_project_values():
    source = _source_test01()
    result = build_ufh_sizing_request_from_project_room(source)

    assert source.selected_room.Code == "101"
    assert result.project_id == "Test_01"
    assert result.room_id == "101DAA3"
    assert result.status == "INCOMPLETE"
    assert result.sizing_request is None
    mapped = {field.target_path: field for field in result.mapped_fields}
    assert mapped["room.room_height_mm"].value == 2800
    assert mapped["room.indoor_temperature_c"].value == 20.0
    assert mapped["room.insulation.air_changes_per_hour"].value == 1.0714285373687744
    assert mapped["room.room_area_mm2"].value == 17_231_461
    assert mapped["room.room_area_mm2"].applied_to_request is False
    assert all(not field.applied_to_request for field in result.mapped_fields)
    assert result.room_geometry_digest is None
    assert "identity.building_id" in result.missing_inputs
    assert "identity.level_id" in result.missing_inputs
    assert "sizing.coverage_request.boundary.points" in result.missing_inputs
    assert any(d.code == "PROJECT_UFH_INPUT_INCOMPLETE" for d in result.diagnostics)


def test_test01_does_not_promote_observed_outdoor_or_precomputed_heat_loss():
    result = build_ufh_sizing_request_from_project_room(_source_test01())
    mapped = {field.target_path: field for field in result.mapped_fields}

    assert "room.outdoor_design_temperature_c" not in mapped
    assert "sizing.room.insulation.exterior_wall_u_value_w_m2k" in result.missing_inputs
    assert "sizing.room.insulation.floor_u_value_w_m2k" in result.missing_inputs
    assert "sizing.floor_construction.declared_output_at_100mm_w_m2" in result.missing_inputs
    assert "engineering.common_circuit.inner_diameter_m" in result.missing_inputs
    assert mapped["room_source.TotalHeatLossW"].value == 1398.87060546875
    assert mapped["room_source.TotalHeatLossW"].applied_to_request is False
    for legacy_load in ("TotalHeatLossW", "HeatLossWM2", "StructuralHeatLossW"):
        if f"room_source.{legacy_load}" in mapped:
            assert mapped[f"room_source.{legacy_load}"].applied_to_request is False
    for field in (
        "wall_offset_mm", "spacing_mm",
        "collector_point", "exclusion_zones",
    ):
        expected_path = f"sizing.coverage_request.{field}"
        if field == "collector_point":
            expected_path += ".x_mm"
        assert expected_path in result.missing_inputs


def test_every_mapped_test01_field_has_source_digest_and_field_reference():
    result = build_ufh_sizing_request_from_project_room(_source_test01())
    assert result.source_digest == hashlib.sha256(TEST01_ROOMS.read_bytes()).hexdigest()
    assert result.adapter_digest
    for field in result.mapped_fields:
        if field.provenance.source_kind in {"SYSTEM_STRUCTURAL_DEFAULT", "SYSTEM_ROUTING_POLICY"}:
            expected_source = (
                "LEGACY_MVP_ROUTING_POLICY"
                if field.provenance.source_file == "LEGACY_MVP_ROUTING_POLICY"
                else "HOMEAURA_UFH_ROUTING_POLICY:V1"
                if field.provenance.source_kind == "SYSTEM_ROUTING_POLICY"
                else "SYSTEM_STRUCTURAL_DEFAULT"
            )
            assert field.provenance.source_file == expected_source
            continue
        assert field.provenance.source_file == str(TEST01_ROOMS)
        assert field.provenance.source_sha256 == result.source_digest
        assert field.provenance.source_path.startswith("$")


def test_adapter_is_deterministic_for_identical_project_source():
    source = _source_test01()
    first = build_ufh_sizing_request_from_project_room(source)
    second = build_ufh_sizing_request_from_project_room(source)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_complete_test_only_project_domain_source_builds_request_and_pipeline_runs():
    source = _complete_test_source()
    adapted = build_ufh_sizing_request_from_project_room(source)

    assert adapted.status == "READY"
    assert adapted.sizing_request is not None
    assert adapted.engineering_inputs is not None
    expected = sizing_request(4000, 3000)
    expected = expected.model_copy(update={
        "coverage_request": expected.coverage_request.model_copy(update={
            "project_id": source.project_id,
            "room_id": source.room_id,
        }),
    })
    assert adapted.sizing_request == expected
    assert adapted.project_domain_digest == source.project_domain_sha256
    assert adapted.room_geometry_digest is not None
    assert all(field.provenance.source_kind == "test_only" for field in adapted.mapped_fields if field.target_path.startswith(("sizing.", "engineering.")))
    boundary_field = next(
        field for field in adapted.mapped_fields
        if field.target_path == "coverage_request.boundary"
    )
    assert boundary_field.value["points"][1] == {"x_mm": 4000, "y_mm": 0}
    assert boundary_field.provenance.transformation is not None
    assert "identity.project_id" in adapted.identity_provenance
    assert "identity.room_id" in adapted.identity_provenance

    # This synthetic complete fixture proves adapter contract compatibility
    # with the existing sizing/routing/engineering/retry pipeline only; it is
    # not evidence of real-project validation.
    outcome = assess_with_automatic_split_retry(
        adapted.sizing_request, adapted.engineering_inputs,
    )
    assert outcome.status == "ACCEPTED_INITIAL"
    assert len(outcome.attempts) == 1


def test_missing_provenance_fails_closed_even_when_values_are_complete():
    source = _complete_test_source()
    provenance = dict(source.input_provenance)
    provenance.pop("sizing.room.insulation.floor_u_value_w_m2k")
    incomplete = source.model_copy(update={"input_provenance": provenance})

    result = build_ufh_sizing_request_from_project_room(incomplete)
    assert result.status == "INCOMPLETE"
    assert result.sizing_request is None
    assert any(
        d.code == "MISSING_PROVENANCE"
        and d.path == "sizing.room.insulation.floor_u_value_w_m2k"
        for d in result.diagnostics
    )


def test_explicit_input_conflict_with_higher_priority_room_source_is_invalid():
    source = _complete_test_source()
    sizing_values = copy.deepcopy(source.sizing_inputs)
    sizing_values["room"]["indoor_temperature_c"] = 22.0
    changed = source.model_copy(update={"sizing_inputs": sizing_values})

    result = build_ufh_sizing_request_from_project_room(changed)
    assert result.status == "INVALID"


def test_profile_provenance_mismatch_returns_diagnostic_not_exception():
    loaded = load_ufh_project_engineering_authoring_template(
        synthetic_complete_authoring_payload()
    )
    assert loaded.status == "READY"
    profile = loaded.profile.model_copy(deep=True)
    provenance = dict(profile.provenance)
    provenance["sizing.room.insulation.floor_boundary_temperature_c"] = (
        ProfileValueProvenance.model_construct(
            source_file="bad://profile-provenance",
            source_sha256="not-a-sha",
            source_path="bad",
            source_kind="linked_engineering_metadata",
            transformation="intentionally invalid test value",
        )
    )
    profile = profile.model_copy(update={"provenance": provenance})
    source = _complete_test_source().model_copy(update={
        "engineering_profile": profile,
        "sizing_inputs": None,
        "engineering_inputs": None,
        "input_provenance": {},
    })

    result = build_ufh_sizing_request_from_project_room(source)
    assert result.status == "INVALID"
    assert any(
        d.code == "PROFILE_PROVENANCE_INVALID"
        and d.path == "engineering.theta_below_c"
        for d in result.diagnostics
    )


def test_project_domain_identity_mismatch_is_rejected():
    source = _complete_test_source()
    changed = source.model_copy(update={"room_id": "not-the-domain-room"})
    result = build_ufh_sizing_request_from_project_room(changed)
    assert result.status == "INVALID"
    assert any(
        item.code == "PROJECT_DOMAIN_IDENTITY_MISMATCH"
        for item in result.diagnostics
    )

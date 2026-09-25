from pathlib import Path

import pytest

from agent.test01_geometry_source_authority import assess_test01_geometry_authority
from agent.ufh_project_engineering_source_completion import (
    PROFILE_SOURCE_FILENAMES,
    complete_project_engineering_profile_sources,
)
from tests.test_ufh_project_adapter import _source_test01


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects/Test_01"
IFC = ROOT.parent / "HomeAuraEngineeringAgent-ifc-research/manual-export"


@pytest.fixture(scope="module")
def authoritative_test01_source():
    if not (IFC / "Test_01_rooms_ifc4.ifc").is_file():
        pytest.skip("Real external IFC evidence set unavailable; no synthetic substitute")
    decision = assess_test01_geometry_authority(PROJECT, IFC)
    assert decision.status == "AUTHORITATIVE"
    return decision.ufh_source


def test_source_completion_keeps_test01_fail_closed(authoritative_test01_source):
    result = complete_project_engineering_profile_sources(
        authoritative_test01_source, PROJECT,
    )

    assert result.status == "UNCHANGED_INCOMPLETE"
    assert result.adapter_before.status == "INCOMPLETE"
    assert result.adapter_after.status == "INCOMPLETE"
    assert result.adapter_before.missing_inputs == result.adapter_after.missing_inputs
    assert result.adapter_after.sizing_request is None
    assert result.adapter_after.engineering_inputs is None


def test_no_hidden_physical_defaults_are_added(authoritative_test01_source):
    result = complete_project_engineering_profile_sources(
        authoritative_test01_source, PROJECT,
    )
    remaining = set(result.adapter_after.missing_inputs)

    assert "sizing.room.outdoor_design_temperature_c" in remaining
    assert "sizing.room.insulation.exterior_wall_u_value_w_m2k" in remaining
    assert "sizing.floor_construction.declared_output_at_100mm_w_m2" in remaining
    assert "engineering.common_circuit.inner_diameter_m" in remaining
    assert not result.new_bindings
    assert result.provenance_coverage["newly_covered_gap_count"] == 0
    assert result.provenance_coverage["percent"] == 0.0


def test_room_observations_are_audited_but_not_promoted(authoritative_test01_source):
    result = complete_project_engineering_profile_sources(
        authoritative_test01_source, PROJECT,
    )
    by_field = {
        item.source_path: item for item in result.inspected_candidates
        if item.source_path.startswith("$.Rooms[]")
    }

    assert by_field["$.Rooms[].OutdoorTemperatureC"].status == "INSPECTED_NOT_AUTHORITY"
    assert by_field["$.Rooms[].OutdoorTemperatureC"].target_path == (
        "sizing.room.outdoor_design_temperature_c"
    )
    assert by_field["$.Rooms[].StructuralHeatLossW"].status == "INSPECTED_NOT_AUTHORITY"
    assert by_field["$.Rooms[].HeatLossWM2"].status == "INSPECTED_NOT_AUTHORITY"


def test_existing_bound_room_values_are_recognized(authoritative_test01_source):
    result = complete_project_engineering_profile_sources(
        authoritative_test01_source, PROJECT,
    )
    already = {
        item.target_path: item for item in result.inspected_candidates
        if item.status == "ALREADY_BOUND"
    }

    assert already["sizing.room.indoor_temperature_c"].observed_value == 20.0
    assert already["sizing.room.insulation.air_changes_per_hour"].observed_value == pytest.approx(
        1.0714285373687744
    )
    assert all(item.source_sha256 == result.adapter_after.source_digest
               for item in already.values())


def test_absent_profile_sources_are_reported_without_placeholders(authoritative_test01_source):
    result = complete_project_engineering_profile_sources(
        authoritative_test01_source, PROJECT,
    )
    missing_profiles = [
        item for item in result.inspected_candidates
        if item.status == "SOURCE_NOT_FOUND"
    ]

    assert len(missing_profiles) == len(PROFILE_SOURCE_FILENAMES)
    assert {Path(item.source_file).name for item in missing_profiles} == {
        Path(name).name for name in PROFILE_SOURCE_FILENAMES
    }


def test_completion_is_deterministic(authoritative_test01_source):
    first = complete_project_engineering_profile_sources(
        authoritative_test01_source, PROJECT,
    )
    second = complete_project_engineering_profile_sources(
        authoritative_test01_source, PROJECT,
    )

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_unbound_test01_source_is_not_silently_completed():
    result = complete_project_engineering_profile_sources(_source_test01(), PROJECT)

    assert result.status == "UNCHANGED_INCOMPLETE"
    assert "identity.building_id" in result.adapter_after.missing_inputs
    assert "sizing.coverage_request.boundary.points" in result.adapter_after.missing_inputs

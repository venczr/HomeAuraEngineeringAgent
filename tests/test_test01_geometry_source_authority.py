"""Actual-source authority tests; no fabricated room geometry or routing."""
from pathlib import Path
import hashlib
import shutil

import pytest
from pydantic import ValidationError

from agent.test01_geometry_source_authority import assess_test01_geometry_authority
from agent.ufh_project_adapter import build_ufh_sizing_request_from_project_room
from tests.test_ufh_project_adapter import _source_test01

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects/Test_01"
IFC = ROOT.parent / "HomeAuraEngineeringAgent-ifc-research/manual-export"


@pytest.fixture(scope="module")
def decision():
    if not (IFC / "Test_01_rooms_ifc4.ifc").is_file():
        pytest.skip("Real external IFC evidence set unavailable; no synthetic substitute")
    return assess_test01_geometry_authority(PROJECT, IFC)


def test_reviewed_revision_and_mrd_difference(decision):
    assert decision.status == "AUTHORITATIVE"
    assert decision.evidence["dwg_byte_identical"]
    assert not decision.evidence["mrd_byte_identical"]
    assert max(decision.evidence["wall_side_deltas_mm"].values()) < 0.000005
    assert decision.evidence["direct_ifc_cad_handle_link"] is False
    assert decision.evidence["match_method"] == "normalized_name_to_room_code"


def test_room_and_ifc_hierarchy_provenance(decision):
    source = decision.ufh_source
    assert source.room_id == "101DAA3"
    assert source.building_id == "1kDE4UYl903ebi3UdgvjXG"
    assert source.level_id == "0oQei_Jnn60QnqOIJ3NBzE"
    assert source.selected_room.Boundary is None
    for prov in [source.boundary_provenance, *source.identity_provenance.values()]:
        assert prov.source_sha256 == decision.evidence["hashes"]["ifc"]
        assert "#31" in prov.source_path
        assert "authority evidence SHA256" in prov.transformation


def test_boundary_area_and_gap_reduction_without_engineering_defaults(decision):
    before = build_ufh_sizing_request_from_project_room(_source_test01())
    after = build_ufh_sizing_request_from_project_room(decision.ufh_source)
    removed = set(before.missing_inputs) - set(after.missing_inputs)
    assert removed == {"identity.building_id", "identity.level_id",
                       "sizing.coverage_request.boundary.points", "sizing.room.room_area_mm2"}
    assert after.status == "INCOMPLETE" and after.sizing_request is None
    assert len(after.missing_inputs) == 41
    assert [d.code for d in after.diagnostics] == ["PROJECT_UFH_INPUT_INCOMPLETE"]
    # Existing adapter marks all fields unapplied until the complete request
    # can be built. The later area record is the boundary-derived mapping.
    mapped = {f.target_path: f for f in after.mapped_fields}
    assert not mapped["coverage_request.boundary"].applied_to_request
    points = mapped["coverage_request.boundary"].value["points"]
    assert points == [{"x_mm":153,"y_mm":153},{"x_mm":4847,"y_mm":153},
                      {"x_mm":4847,"y_mm":3843},{"x_mm":153,"y_mm":3843},
                      {"x_mm":153,"y_mm":153}]
    assert mapped["room.room_area_mm2"].value == 4694 * 3690
    assert mapped["room.room_area_mm2"].value != round(decision.ufh_source.selected_room.NetAreaM2 * 1e6)
    assert "shoelace" in mapped["room.room_area_mm2"].provenance.transformation
    assert "engineering.common_circuit.inner_diameter_m" in after.missing_inputs


def test_deterministic_and_read_only(decision):
    paths = [Path(p) for p in decision.evidence["source_paths"].values()]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    repeated = assess_test01_geometry_authority(PROJECT, IFC)
    assert repeated.decision_digest == decision.decision_digest
    a = build_ufh_sizing_request_from_project_room(decision.ufh_source)
    b = build_ufh_sizing_request_from_project_room(repeated.ufh_source)
    assert a.adapter_digest == b.adapter_digest
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


@pytest.mark.parametrize("changed_key, filename", [
    ("current_mrd", "HomeAura_Test_01.mrd"), ("current_dwg", "Test_01.dwg"),
])
def test_revision_change_requires_fresh_evidence(tmp_path, decision, changed_key, filename):
    for name, value in decision.evidence["source_paths"].items():
        if name in {"current_dwg", "current_mrd", "rooms", "snapshot"}:
            source = Path(value)
            target = tmp_path / source.relative_to(PROJECT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    # Only a temporary test copy is changed; the actual project is untouched.
    (tmp_path / filename).write_bytes(b"unreviewed revision")
    first = assess_test01_geometry_authority(tmp_path, IFC)
    second = assess_test01_geometry_authority(tmp_path, IFC)
    assert first.status == "NEEDS_FRESH_NATIVE_EXPORT"
    assert first.ufh_source is None
    assert first.reasons == (f"UNREVIEWED_SOURCE_REVISION:{changed_key}",)
    assert first.decision_digest == second.decision_digest


def test_boundary_requires_provenance(decision):
    payload = decision.ufh_source.model_dump()
    payload["boundary_provenance"] = None
    with pytest.raises(ValidationError, match="requires its source provenance"):
        type(decision.ufh_source).model_validate(payload)


def test_no_routing_or_engineering_execution(monkeypatch, decision):
    import agent.ufh_auto_retry as retry
    import agent.floor_heating_sizing as sizing

    def forbidden(*args, **kwargs):
        raise AssertionError("Authority binding must not run UFH sizing/routing/retry")

    monkeypatch.setattr(retry, "assess_with_automatic_split_retry", forbidden)
    monkeypatch.setattr(sizing, "size_ufh_requirement", forbidden)
    result = assess_test01_geometry_authority(PROJECT, IFC)
    assert build_ufh_sizing_request_from_project_room(result.ufh_source).status == "INCOMPLETE"

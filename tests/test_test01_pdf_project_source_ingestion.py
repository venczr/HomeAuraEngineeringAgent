from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from agent.test01_pdf_project_source_ingestion import (
    MANIFEST_RELATIVE_PATH,
    load_test01_pdf_project_source_ingestion,
)
from agent.test01_sp60_engineering_binding import build_test01_sp60_engineering_binding
from agent.test01_interactive_engineering_intake import create_test01_engineering_intake_session


PROJECT = Path(__file__).resolve().parents[1] / "projects/Test_01"
IFC = PROJECT.parents[1].parent / "HomeAuraEngineeringAgent-ifc-research/manual-export"


def test_ingests_exact_two_library_plans_with_hash_checked_archives():
    package = load_test01_pdf_project_source_ingestion(PROJECT)
    assert package is not None
    assert [item.document_id for item in package.documents] == ["ATTIC_PLAN", "FLOOR_1_PLAN"]
    assert all(item.page_count == 1 and item.page_size == "A4 portrait" for item in package.documents)
    assert package.room_101_linkage_status == "NOT_ESTABLISHED"
    assert package.engineering_bindings == []


def test_pdf_manifest_and_archives_fail_closed_on_tampering(tmp_path):
    source = PROJECT
    shutil.copytree(source / "engineering/source_documents", tmp_path / "engineering/source_documents")
    shutil.copy2(source / MANIFEST_RELATIVE_PATH, tmp_path / MANIFEST_RELATIVE_PATH)
    target = tmp_path / "engineering/source_documents/Test_01_floor_1_plan.pdf"
    target.write_bytes(target.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="PDF_ARCHIVE_SIZE_MISMATCH|PDF_ARCHIVE_HASH_MISMATCH"):
        load_test01_pdf_project_source_ingestion(tmp_path)


def test_pdf_observations_cannot_promote_room_or_physical_inputs():
    raw = json.loads((PROJECT / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert raw["authority_class"] == "PROJECT_DOCUMENT_OBSERVATION"
    assert raw["room_101_linkage_status"] == "NOT_ESTABLISHED"
    assert raw["engineering_bindings"] == []
    assert all(item["status"] != "RESOLVED" for item in raw["observations"])
    assert not any("outdoor_design_temperature" in str(item).casefold()
                   or "u_value" in str(item).casefold()
                   or "construction_assembly" in str(item).casefold()
                   for item in raw["observations"])


def test_source_binding_exposes_plan_evidence_but_keeps_engineering_gaps():
    binding = build_test01_sp60_engineering_binding(PROJECT, IFC)
    inventory = binding.source_inventory["pdf_project_source_ingestion"]
    assert inventory["status"] == "PRESENT_VERIFIED"
    package = inventory["package"]
    assert package["room_101_linkage_status"] == "NOT_ESTABLISHED"
    matrix = {item.input_id: item for item in binding.input_matrix}
    assert matrix["CLIMATE_LOCALITY"].status == "UNRESOLVED"
    assert matrix["THERMAL_BOUNDARY_INVENTORY"].status == "UNRESOLVED"
    assert matrix["OPENING_INVENTORY"].status == "UNRESOLVED"
    assert matrix["CONSTRUCTION_ASSEMBLIES"].status == "UNRESOLVED"


def test_intake_shows_plan_location_as_unbound_context_without_completing_climate():
    session = create_test01_engineering_intake_session(PROJECT, IFC)
    question = next(item for item in session.current_questions if item.question_id == "climate")
    observation = question.ui_context["project_document_observation"]
    assert observation["status"] == "OBSERVED_NOT_BOUND"
    assert "Узигонты" in question.prompt
    assert session.dashboard["CLIMATE"].status == "BLOCKED"
    assert session.status == "INCOMPLETE"

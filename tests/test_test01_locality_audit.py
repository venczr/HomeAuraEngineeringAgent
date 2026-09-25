from pathlib import Path

from agent.test01_locality_audit import audit_test01_locality

PROJECT = Path(__file__).resolve().parents[1] / "projects/Test_01"


def test_exact_pdf_locality_audit_distinguishes_external_claim_from_project_conflict():
    audit = audit_test01_locality(PROJECT)
    assert audit.status == "NO_PROJECT_SOURCE_CONFLICT"
    assert audit.selected_locality is None and audit.climate_resolution_allowed is False
    assert len(audit.project_source_evidence) == 3
    assert all("Узигонты" in e.exact_value for e in audit.project_source_evidence)
    assert audit.classification == "EXTERNAL_CLAIM_CONTRADICTED_BY_EXACT_PDF_RENDER"
    assert "Знаменка" in audit.external_claims[0].exact_value

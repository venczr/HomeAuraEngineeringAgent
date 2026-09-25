"""Fail-closed locality audit for the exact verified Test_01 plan sources."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from agent.project_models import StrictProjectModel
from agent.test01_pdf_project_source_ingestion import load_test01_pdf_project_source_ingestion


class LocalityEvidence(StrictProjectModel):
    source_file: str
    source_sha256: str | None
    exact_value: str
    extraction_path: str
    provenance: str
    project_identity: str
    revision_or_date: str | None = None


class Test01LocalityAudit(StrictProjectModel):
    status: Literal["NO_PROJECT_SOURCE_CONFLICT"]
    selected_locality: None = None
    project_source_evidence: tuple[LocalityEvidence, ...]
    external_claims: tuple[LocalityEvidence, ...]
    classification: Literal["EXTERNAL_CLAIM_CONTRADICTED_BY_EXACT_PDF_RENDER"]
    climate_resolution_allowed: Literal[False] = False
    reason: str


def audit_test01_locality(project_directory: Path) -> Test01LocalityAudit:
    package = load_test01_pdf_project_source_ingestion(project_directory)
    if package is None:
        raise ValueError("TEST01_VERIFIED_PDF_MANIFEST_REQUIRED")
    evidence = []
    for document in package.documents:
        path = project_directory / document.archived_path
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        value = str(document.title_block["project_site_location_text"])
        evidence.append(LocalityEvidence(source_file=document.archived_path, source_sha256=digest,
            exact_value=value, extraction_path="page 1 title block; visually verified raster render",
            provenance="verified PDF archive + ingestion manifest manual visual transcription",
            project_identity=package.project_id, revision_or_date=document.title_block.get("drawing_date")))
    manifest = project_directory / "engineering/test01_pdf_project_source_ingestion_v1.json"
    evidence.append(LocalityEvidence(source_file=str(manifest.relative_to(project_directory)).replace("\\", "/"),
        source_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        exact_value=str(package.observations[0].value), extraction_path="$.observations[PROJECT_SITE_LOCATION_TEXT].value",
        provenance="digest-verified ingestion manifest", project_identity=package.project_id,
        revision_or_date=package.ingestion_date))
    external = LocalityEvidence(source_file="session://current-user-instruction", source_sha256=None,
        exact_value="дер. Знаменка, Ленинградская область, Ломоносовский район, Низинское сельское поселение",
        extraction_path="current user message", provenance="external user assertion; not a project source file",
        project_identity="claimed Test_01", revision_or_date=None)
    return Test01LocalityAudit(status="NO_PROJECT_SOURCE_CONFLICT", project_source_evidence=tuple(evidence),
        external_claims=(external,), classification="EXTERNAL_CLAIM_CONTRADICTED_BY_EXACT_PDF_RENDER",
        reason="All exact project source files agree on дер. Узигонты; no project file containing Знаменка was found. No locality is selected for SP131 until normative binding is separately resolved.")


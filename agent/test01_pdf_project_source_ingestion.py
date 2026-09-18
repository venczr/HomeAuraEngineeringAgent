"""Integrity-checked ingestion of user-designated Test_01 PDF plans.

The plans are project-document evidence. This module does not infer room
identity, thermal semantics, construction properties, or engineering values.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from agent.project_models import StrictProjectModel


MANIFEST_RELATIVE_PATH = Path("engineering/test01_pdf_project_source_ingestion_v1.json")
SOURCE_DIRECTORY = Path("engineering/source_documents")


def _canonical(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def _digest(value: Any) -> str:
    payload = json.dumps(_canonical(value), sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class PdfPlanSource(StrictProjectModel):
    document_id: Literal["FLOOR_1_PLAN", "ATTIC_PLAN"]
    original_filename: str = Field(min_length=1, max_length=256)
    archived_path: str = Field(min_length=1, max_length=512)
    library_reference: str = Field(min_length=1, max_length=512)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    byte_length: int = Field(gt=0)
    pdf_header: Literal["%PDF-"]
    page_count: Literal[1]
    page_size: Literal["A4 portrait"]
    title_block: dict[str, Any]
    visual_observations: list[str]
    text_layer_status: Literal["NO_EXTRACTABLE_TEXT_VISUALLY_REVIEWED"]

    @model_validator(mode="after")
    def controlled_archive_path(self):
        path = Path(self.archived_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("PDF_ARCHIVE_PATH_MUST_BE_PROJECT_RELATIVE")
        if not self.archived_path.startswith(SOURCE_DIRECTORY.as_posix() + "/"):
            raise ValueError("PDF_ARCHIVE_PATH_OUTSIDE_SOURCE_DIRECTORY")
        return self


class PdfProjectObservation(StrictProjectModel):
    observation_id: str = Field(min_length=1, max_length=96)
    scope: Literal["PROJECT_DOCUMENT", "ROOM_LINKAGE", "ENGINEERING_DATA"]
    value: Any
    status: Literal["OBSERVED_NOT_BOUND", "NOT_ESTABLISHED", "NOT_PRESENT_IN_SOURCE"]
    source_document_ids: list[Literal["FLOOR_1_PLAN", "ATTIC_PLAN"]]
    source_reference: str = Field(min_length=1, max_length=512)
    extraction_method: str = Field(min_length=1, max_length=512)
    limitation: str = Field(min_length=1, max_length=1024)


class Test01PdfProjectSourceIngestion(StrictProjectModel):
    schema_version: Literal["1.0"]
    project_id: Literal["Test_01"]
    target_room_id: Literal["101DAA3"]
    source_library_path: str
    ingestion_date: str
    authority_class: Literal["PROJECT_DOCUMENT_OBSERVATION"]
    documents: list[PdfPlanSource]
    observations: list[PdfProjectObservation]
    room_101_linkage_status: Literal["NOT_ESTABLISHED"]
    engineering_bindings: list[Any]
    protected_source_policy: Literal["SOURCE_FILES_READ_ONLY"]
    manifest_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def exact_pair_and_no_promotions(self):
        expected = {"FLOOR_1_PLAN", "ATTIC_PLAN"}
        if len(self.documents) != 2 or {item.document_id for item in self.documents} != expected:
            raise ValueError("EXPECTED_EXACTLY_TWO_TEST01_PLAN_DOCUMENTS")
        if self.engineering_bindings:
            raise ValueError("PDF_INGESTION_MUST_NOT_CREATE_ENGINEERING_BINDINGS")
        return self

    def verify_manifest_digest(self) -> None:
        body = self.model_dump(mode="json", exclude={"manifest_digest"})
        if _digest(body) != self.manifest_digest:
            raise ValueError("PDF_INGESTION_MANIFEST_DIGEST_INVALID")


def load_test01_pdf_project_source_ingestion(
    project_directory: Path,
) -> Test01PdfProjectSourceIngestion | None:
    """Load and verify the exact two archived PDFs and their manifest."""
    project_directory = project_directory.resolve()
    manifest_path = project_directory / MANIFEST_RELATIVE_PATH
    if not manifest_path.is_file():
        return None
    package = Test01PdfProjectSourceIngestion.model_validate_json(
        manifest_path.read_text(encoding="utf-8"))
    package.verify_manifest_digest()
    for document in package.documents:
        archived = (project_directory / document.archived_path).resolve()
        try:
            archived.relative_to(project_directory)
        except ValueError as error:
            raise ValueError("PDF_ARCHIVE_PATH_ESCAPES_PROJECT") from error
        if not archived.is_file():
            raise ValueError("PDF_ARCHIVE_FILE_MISSING:" + document.document_id)
        data = archived.read_bytes()
        if len(data) != document.byte_length:
            raise ValueError("PDF_ARCHIVE_SIZE_MISMATCH:" + document.document_id)
        if not data.startswith(b"%PDF-"):
            raise ValueError("PDF_ARCHIVE_HEADER_INVALID:" + document.document_id)
        if hashlib.sha256(data).hexdigest() != document.sha256:
            raise ValueError("PDF_ARCHIVE_HASH_MISMATCH:" + document.document_id)
    return package


__all__ = [
    "MANIFEST_RELATIVE_PATH", "PdfPlanSource", "PdfProjectObservation",
    "Test01PdfProjectSourceIngestion", "load_test01_pdf_project_source_ingestion",
]

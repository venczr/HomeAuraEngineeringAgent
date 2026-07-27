from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ValidationStatus(str, Enum):
    VALIDATED = "validated"
    PROVISIONAL = "provisional"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    INVALID = "invalid"
    MISSING = "missing"


class SourceKind(str, Enum):
    DERIVED_DETERMINISTIC = "derived_deterministic"
    LEGACY_PLACEHOLDER = "legacy_placeholder"
    LEGACY_ROOM = "legacy_room"
    LEGACY_BOUNDARY = "legacy_boundary"
    IFC_SPACE_CANDIDATE = "ifc_space_candidate"


class StrictDomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EntitySource(StrictDomainModel):
    kind: SourceKind
    system: str
    identifiers: dict[str, str] = Field(default_factory=dict)


class EntityAlias(StrictDomainModel):
    kind: str
    value: str
    source_kind: SourceKind


class DomainFileEvidence(StrictDomainModel):
    file_name: str | None = None
    sha256: str | None = None
    ifc_schema: str | None = None


class IfcSpaceCandidate(StrictDomainModel):
    source: EntitySource
    validation_status: ValidationStatus
    geometry_status: str
    file: DomainFileEvidence
    global_id: str | None = None
    step_id: int | None = None
    name: str | None = None
    storey_name: str | None = None
    area_m2: float | None = None
    perimeter_m: float | None = None
    height_m: float | None = None
    match_status: str | None = None
    match_method: str | None = None
    portable_payload: dict[str, Any] = Field(default_factory=dict)
    diagnostics: list[str] = Field(default_factory=list)


class DomainBoundary(StrictDomainModel):
    stable_id: UUID
    source_handle: str
    source: EntitySource
    validation_status: ValidationStatus
    geometry_status: str
    legacy_geometry: dict[str, Any] = Field(default_factory=dict)
    diagnostics: list[str] = Field(default_factory=list)


class DomainRoom(StrictDomainModel):
    stable_id: UUID
    code: str
    name: str
    source_handle: str | None = None
    source: EntitySource
    validation_status: ValidationStatus
    aliases: list[EntityAlias] = Field(default_factory=list)
    position: dict[str, float] | None = None
    legacy_attributes: dict[str, Any] = Field(default_factory=dict)
    boundary: DomainBoundary | None = None
    ifc_space_candidate: IfcSpaceCandidate | None = None
    diagnostics: list[str] = Field(default_factory=list)


class DomainLevel(StrictDomainModel):
    stable_id: UUID
    name: str
    source: EntitySource
    validation_status: ValidationStatus
    rooms: list[DomainRoom] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class DomainBuilding(StrictDomainModel):
    stable_id: UUID
    name: str
    source: EntitySource
    validation_status: ValidationStatus
    levels: list[DomainLevel] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class DomainProject(StrictDomainModel):
    stable_id: UUID
    name: str
    drawing_name: str
    source: EntitySource
    validation_status: ValidationStatus
    buildings: list[DomainBuilding] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class DomainDocument(StrictDomainModel):
    schema_version: Literal["1.0"] = "1.0"
    legacy_format_version: str
    project: DomainProject
    diagnostics: list[str] = Field(default_factory=list)

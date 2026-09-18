from __future__ import annotations

import json
import math
import unicodedata

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from agent.domain_models import DomainDocument


SHA256_PATTERN = r"^[0-9a-f]{64}$"
EVIDENCE_SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
SHEET_CODE_PATTERN = (
    r"^HA-(GEN|OV|TM|VK|VENT|EM|AUT|SPEC)-[0-9]{3}$"
)
EQUIPMENT_VERIFIABLE_FIELDS = frozenset(
    {
        "manufacturer",
        "brand",
        "model",
        "article",
        "category",
        "compatible_systems",
        "properties",
        "service_clearances_m",
        "connection_ports",
    }
)


class ProjectJsonError(ValueError):
    pass


class _DuplicateProjectJsonKey(ValueError):
    pass


def _reject_project_json_duplicates(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateProjectJsonKey(key)
        result[key] = value
    return result


def _reject_project_json_constant(value: str) -> Any:
    raise ValueError(value)


def _load_strict_project_json(
    json_data: str | bytes | bytearray,
) -> Any:
    try:
        if isinstance(json_data, str):
            text = json_data
        elif isinstance(json_data, (bytes, bytearray)):
            text = bytes(json_data).decode(
                "utf-8",
                errors="strict",
            )
        else:
            raise TypeError("JSON input must be text or UTF-8 bytes")
        return json.loads(
            text,
            object_pairs_hook=_reject_project_json_duplicates,
            parse_constant=_reject_project_json_constant,
        )
    except (
        TypeError,
        UnicodeDecodeError,
        ValueError,
        RecursionError,
    ) as error:
        raise ProjectJsonError(
            "PROJECT JSON must be strict UTF-8 without duplicate "
            "keys or non-finite constants"
        ) from error


def _require_finite_numbers(
    value: Any,
    *,
    path: str,
) -> None:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(
                f"non-finite number is not allowed at {path}"
            )
        return
    if isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            _require_finite_numbers(
                getattr(value, field_name),
                path=f"{path}.{field_name}",
            )
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _require_finite_numbers(
                item,
                path=f"{path}.{key}",
            )
        return
    if isinstance(value, (list, tuple, set, frozenset)):
        for index, item in enumerate(value):
            _require_finite_numbers(
                item,
                path=f"{path}[{index}]",
            )


def _normalize_verified_field_names(value: Any) -> Any:
    if not isinstance(value, list):
        return value
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(
                "verified field names must be strings"
            )
        field_name = item.strip().casefold()
        if not field_name:
            raise ValueError(
                "verified field name must not be blank"
            )
        if field_name not in EQUIPMENT_VERIFIABLE_FIELDS:
            raise ValueError(
                f"unknown verified equipment field: {field_name}"
            )
        if field_name in normalized:
            raise ValueError(
                f"duplicate verified equipment field: {field_name}"
            )
        normalized.append(field_name)
    return normalized


def _require_nonblank_equipment_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if not value.strip():
        raise ValueError("equipment text value must not be blank")
    return value


def _normalize_manufacturer_identity(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = unicodedata.normalize("NFKC", value)
    normalized = " ".join(normalized.split())
    if not normalized:
        raise ValueError("manufacturer identity must not be blank")
    return normalized.casefold()


def _is_substantive_verified_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value) and all(
            isinstance(key, str)
            and bool(key.strip())
            and _is_substantive_verified_value(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set, frozenset)):
        return bool(value) and all(
            _is_substantive_verified_value(item)
            for item in value
        )
    return True


def _has_timezone(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


class StrictProjectModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        validate_assignment=True,
    )

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: Any | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Any:
        payload = _load_strict_project_json(json_data)
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return super().model_validate_json(
            canonical,
            strict=strict,
            extra=extra,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    @model_validator(mode="after")
    def reject_non_finite_numbers(self) -> StrictProjectModel:
        _require_finite_numbers(self, path="$")
        return self


class Point3D(StrictProjectModel):
    x_m: float = Field(allow_inf_nan=False)
    y_m: float = Field(allow_inf_nan=False)
    z_m: float = Field(allow_inf_nan=False)


class UnitVector3D(StrictProjectModel):
    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)
    z: float = Field(allow_inf_nan=False)

    @model_validator(mode="after")
    def require_unit_length(self) -> UnitVector3D:
        magnitude = math.sqrt(
            self.x * self.x
            + self.y * self.y
            + self.z * self.z
        )
        if not math.isclose(
            magnitude,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise ValueError("vector must have unit length")
        return self


class SourcePointKind(str, Enum):
    BOILER_ROOM = "boiler_room"
    WATER_INLET = "water_inlet"
    SEWER_OUTLET = "sewer_outlet"
    AIR_INTAKE = "air_intake"
    AIR_EXHAUST = "air_exhaust"
    ELECTRICAL_SOURCE = "electrical_source"


class SourcePointState(str, Enum):
    PROPOSED = "proposed"
    MARKED = "marked"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REPLACED = "replaced"


class SourceEvidenceKind(str, Enum):
    USER_MARKED = "user_marked"
    USER_APPROVED = "user_approved"
    MODEL_DERIVED = "model_derived"
    RULE_PROPOSED = "rule_proposed"
    IMPORTED = "imported"


class SourcePointEvidence(StrictProjectModel):
    kind: SourceEvidenceKind
    method: str = Field(min_length=1, max_length=128)
    drawing_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    source_handle: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
    )
    observed_at: datetime

    @model_validator(mode="after")
    def reject_path_shaped_drawing_name(
        self,
    ) -> SourcePointEvidence:
        value = self.drawing_name
        if value is not None and (
            value in {".", ".."}
            or "/" in value
            or "\\" in value
            or ":" in value
            or "\x00" in value
        ):
            raise ValueError(
                "drawing_name must not contain a local path"
            )
        return self


class SourcePoint(StrictProjectModel):
    source_point_id: UUID
    kind: SourcePointKind
    revision: int = Field(ge=1)
    state: SourcePointState
    active: bool = True
    world_coordinates_m: Point3D | None = None
    local_coordinates_m: Point3D | None = None
    level_id: UUID | None = None
    room_id: UUID | None = None
    level_elevation_m: float | None = Field(
        default=None,
        allow_inf_nan=False,
    )
    wall_normal: UnitVector3D | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: SourcePointEvidence
    notes: list[str] = Field(default_factory=list)

    def is_human_confirmed(self) -> bool:
        return (
            self.state == SourcePointState.MARKED
            and self.evidence.kind == SourceEvidenceKind.USER_MARKED
        ) or (
            self.state == SourcePointState.ACCEPTED
            and self.evidence.kind == SourceEvidenceKind.USER_APPROVED
        )

    @model_validator(mode="after")
    def require_marked_point_context(self) -> SourcePoint:
        if not self.active:
            if (
                self.kind == SourcePointKind.BOILER_ROOM
                and self.state == SourcePointState.PROPOSED
            ):
                return self
            if self.state not in {
                SourcePointState.REPLACED,
                SourcePointState.REJECTED,
            }:
                raise ValueError(
                    "inactive source point must be replaced or rejected"
                )
            return self

        if self.state in {
            SourcePointState.REPLACED,
            SourcePointState.REJECTED,
        }:
            raise ValueError(
                "replaced or rejected source point cannot be active"
            )

        if self.kind == SourcePointKind.BOILER_ROOM:
            missing = [
                field_name
                for field_name, value in (
                    ("world_coordinates_m", self.world_coordinates_m),
                    ("local_coordinates_m", self.local_coordinates_m),
                    ("level_id", self.level_id),
                    ("room_id", self.room_id),
                )
                if value is None
            ]
            if missing:
                raise ValueError(
                    "active boiler room is missing: "
                    + ", ".join(missing)
                )

        if self.state not in {
            SourcePointState.MARKED,
            SourcePointState.ACCEPTED,
        }:
            return self

        if self.world_coordinates_m is None:
            raise ValueError(
                "marked source point requires world coordinates"
            )

        if self.kind == SourcePointKind.WATER_INLET:
            missing = [
                field_name
                for field_name, value in (
                    ("local_coordinates_m", self.local_coordinates_m),
                    ("level_id", self.level_id),
                    ("level_elevation_m", self.level_elevation_m),
                    ("wall_normal", self.wall_normal),
                )
                if value is None
            ]
            if missing:
                raise ValueError(
                    "marked water inlet is missing: "
                    + ", ".join(missing)
                )

        return self


class ProjectSeedStatus(str, Enum):
    INCOMPLETE = "incomplete"
    READY = "ready"


class ProjectSeed(StrictProjectModel):
    schema_version: Literal["1.0"] = "1.0"
    seed_id: UUID
    revision: int = Field(ge=1)
    project_stable_id: UUID
    drawing_name: str = Field(min_length=1, max_length=255)
    domain_schema_version: str = Field(min_length=1, max_length=32)
    domain_sha256: str = Field(pattern=SHA256_PATTERN)
    input_sha256: str = Field(pattern=SHA256_PATTERN)
    source_points: list[SourcePoint] = Field(default_factory=list)
    required_source_point_kinds: list[SourcePointKind] = Field(
        default_factory=lambda: [
            SourcePointKind.BOILER_ROOM,
            SourcePointKind.WATER_INLET,
        ]
    )
    missing_required_source_points: list[SourcePointKind] = Field(
        default_factory=list
    )
    status: ProjectSeedStatus
    created_at: datetime

    @model_validator(mode="after")
    def validate_readiness(self) -> ProjectSeed:
        required_values = [
            item.value
            for item in self.required_source_point_kinds
        ]
        if len(required_values) != len(set(required_values)):
            raise ValueError(
                "required source point kinds must be unique"
            )

        active_by_kind: dict[SourcePointKind, SourcePoint] = {}
        point_ids = [
            point.source_point_id
            for point in self.source_points
        ]
        if len(point_ids) != len(set(point_ids)):
            raise ValueError("source point ids must be unique")
        point_revisions = [
            (point.kind, point.revision)
            for point in self.source_points
        ]
        if len(point_revisions) != len(set(point_revisions)):
            raise ValueError(
                "source point revisions must be unique per kind"
            )
        for point in self.source_points:
            if not point.active:
                continue
            if point.kind in active_by_kind:
                raise ValueError(
                    "only one active source point per kind is allowed"
                )
            active_by_kind[point.kind] = point

        available = {
            kind
            for kind, point in active_by_kind.items()
            if point.is_human_confirmed()
        }
        expected_missing = sorted(
            (
                kind
                for kind in self.required_source_point_kinds
                if kind not in available
            ),
            key=lambda item: item.value,
        )
        actual_missing = sorted(
            self.missing_required_source_points,
            key=lambda item: item.value,
        )
        if actual_missing != expected_missing:
            raise ValueError(
                "missing source point list does not match active points"
            )

        expected_status = (
            ProjectSeedStatus.READY
            if not expected_missing
            else ProjectSeedStatus.INCOMPLETE
        )
        if self.status != expected_status:
            raise ValueError(
                "project seed status does not match source point readiness"
            )
        return self


class AssumptionCriticality(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class AssumptionStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REPLACED = "replaced"


class Assumption(StrictProjectModel):
    assumption_id: UUID
    description: str = Field(min_length=1, max_length=2000)
    proposed_value: JsonValue
    source_rule: str = Field(min_length=1, max_length=512)
    confidence: float = Field(ge=0.0, le=1.0)
    criticality: AssumptionCriticality
    affects_calculations: list[str] = Field(default_factory=list)
    affects_sheets: list[str] = Field(default_factory=list)
    status: AssumptionStatus = AssumptionStatus.PROPOSED
    created_at: datetime
    decided_at: datetime | None = None

    def blocks_readiness(self) -> bool:
        return (
            self.criticality == AssumptionCriticality.BLOCKING
            and self.status == AssumptionStatus.PROPOSED
        )

    @model_validator(mode="after")
    def validate_decision_time(self) -> Assumption:
        is_decided = self.status != AssumptionStatus.PROPOSED
        if is_decided != (self.decided_at is not None):
            raise ValueError(
                "assumption decision time must match its status"
            )
        return self


class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKING = "blocking"


class IssueStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    WAIVED = "waived"


class Issue(StrictProjectModel):
    issue_id: UUID
    code: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Z0-9_]+$",
    )
    severity: IssueSeverity
    status: IssueStatus = IssueStatus.OPEN
    message: str = Field(min_length=1, max_length=2000)
    entity_ids: list[UUID] = Field(default_factory=list)
    rule_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
    )
    actual_value: JsonValue | None = None
    allowed_value: JsonValue | None = None
    recommendation: str | None = Field(
        default=None,
        min_length=1,
        max_length=2000,
    )
    affects_variants: list[str] = Field(default_factory=list)
    affects_sheets: list[str] = Field(default_factory=list)
    created_at: datetime
    resolved_at: datetime | None = None

    def blocks_readiness(self) -> bool:
        return (
            self.severity == IssueSeverity.BLOCKING
            and self.status == IssueStatus.OPEN
        )

    @model_validator(mode="after")
    def validate_resolution_time(self) -> Issue:
        is_closed = self.status in {
            IssueStatus.RESOLVED,
            IssueStatus.WAIVED,
        }
        if is_closed != (self.resolved_at is not None):
            raise ValueError(
                "issue resolution time must match its status"
            )
        return self


class RuleStatus(str, Enum):
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    DEPRECATED = "deprecated"


class RuleRegistryEntry(StrictProjectModel):
    rule_id: str = Field(min_length=1, max_length=256)
    document_id: str = Field(min_length=1, max_length=256)
    edition: str = Field(min_length=1, max_length=128)
    effective_from: date | None = None
    effective_to: date | None = None
    jurisdiction: list[str] = Field(default_factory=list)
    building_types: list[str] = Field(default_factory=list)
    mandatory: bool
    clause_reference: str = Field(min_length=1, max_length=256)
    condition_key: str = Field(min_length=1, max_length=256)
    units: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )
    tolerance: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )
    exceptions: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    source_title: str = Field(min_length=1, max_length=512)
    source_reference: str = Field(min_length=1, max_length=1000)
    source_checked_at: datetime
    status: RuleStatus

    @model_validator(mode="after")
    def validate_effective_period(self) -> RuleRegistryEntry:
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError(
                "rule effective_to precedes effective_from"
            )
        return self


class CatalogVerificationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    UNVERIFIED = "unverified"
    DEPRECATED = "deprecated"


class CatalogSourceType(str, Enum):
    OFFICIAL_MANUFACTURER = "official_manufacturer"
    OFFICIAL_PUBLISHER = "official_publisher"
    THIRD_PARTY = "third_party"


class CatalogSourceVerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"


class EquipmentCatalogSource(StrictProjectModel):
    source_type: CatalogSourceType
    document_title: str = Field(min_length=1, max_length=512)
    document_version: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
    )
    document_date: date | None = None
    publisher: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
    )
    manufacturer_identity: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
    )
    locator: str = Field(min_length=1, max_length=1000)
    retrieved_at: datetime
    verification_status: CatalogSourceVerificationStatus = (
        CatalogSourceVerificationStatus.UNVERIFIED
    )
    verification_completed_at: datetime | None = None
    evidence_sha256: str | None = Field(
        default=None,
        pattern=EVIDENCE_SHA256_PATTERN,
    )
    confirmed_fields: list[str] = Field(default_factory=list)

    @field_validator(
        "publisher",
        "locator",
        mode="before",
    )
    @classmethod
    def normalize_source_identity(
        cls,
        value: Any,
    ) -> Any:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError(
                "source publisher and locator must not be blank"
            )
        return normalized

    @field_validator("manufacturer_identity", mode="before")
    @classmethod
    def normalize_manufacturer_identity(
        cls,
        value: Any,
    ) -> Any:
        if value is None:
            return None
        return _normalize_manufacturer_identity(value)

    @field_validator("evidence_sha256", mode="after")
    @classmethod
    def normalize_evidence_sha256(
        cls,
        value: str | None,
    ) -> str | None:
        return value.lower() if value is not None else None

    @field_validator("confirmed_fields", mode="before")
    @classmethod
    def normalize_confirmed_fields(
        cls,
        value: Any,
    ) -> Any:
        return _normalize_verified_field_names(value)

    @model_validator(mode="after")
    def require_complete_verification_metadata(
        self,
    ) -> EquipmentCatalogSource:
        if (
            self.source_type
            == CatalogSourceType.OFFICIAL_MANUFACTURER
            and self.manufacturer_identity is None
        ):
            raise ValueError(
                "official manufacturer source requires "
                "manufacturer_identity"
            )
        if not _has_timezone(self.retrieved_at):
            raise ValueError(
                "source retrieval time must include a timezone"
            )
        if (
            self.verification_completed_at is not None
            and not _has_timezone(self.verification_completed_at)
        ):
            raise ValueError(
                "source verification time must include a timezone"
            )
        if (
            self.verification_status
            == CatalogSourceVerificationStatus.VERIFIED
            and (
                self.publisher is None
                or self.verification_completed_at is None
                or self.evidence_sha256 is None
                or not self.confirmed_fields
            )
        ):
            raise ValueError(
                "verified source requires publisher, completion time, "
                "locator, evidence sha256, and confirmed fields"
            )
        if (
            self.verification_status
            == CatalogSourceVerificationStatus.UNVERIFIED
            and (
                self.verification_completed_at is not None
                or self.confirmed_fields
            )
        ):
            raise ValueError(
                "unverified source cannot claim completed verification "
                "or confirmed fields"
            )
        return self


class EquipmentCatalogItem(StrictProjectModel):
    catalog_item_id: UUID
    manufacturer: str = Field(min_length=1, max_length=256)
    brand: str = Field(min_length=1, max_length=256)
    model: str = Field(min_length=1, max_length=256)
    article: str = Field(min_length=1, max_length=256)
    category: str = Field(min_length=1, max_length=256)
    compatible_systems: list[str] = Field(default_factory=list)
    verification_status: CatalogVerificationStatus
    sources: list[EquipmentCatalogSource] = Field(
        default_factory=list
    )
    verified_fields: list[str] = Field(default_factory=list)
    properties: dict[str, JsonValue] = Field(default_factory=dict)
    service_clearances_m: dict[str, float] = Field(
        default_factory=dict
    )
    connection_ports: list[dict[str, JsonValue]] = Field(
        default_factory=list
    )

    @field_validator(
        "manufacturer",
        "brand",
        "model",
        "article",
        "category",
        mode="before",
    )
    @classmethod
    def require_nonblank_equipment_text(
        cls,
        value: Any,
    ) -> Any:
        return _require_nonblank_equipment_text(value)

    @field_validator("verified_fields", mode="before")
    @classmethod
    def normalize_verified_fields(
        cls,
        value: Any,
    ) -> Any:
        return _normalize_verified_field_names(value)

    @model_validator(mode="after")
    def require_verified_sources(self) -> EquipmentCatalogItem:
        if self.verification_status == CatalogVerificationStatus.VERIFIED:
            if not self.verified_fields:
                raise ValueError(
                    "verified catalog item requires verified fields"
                )
        if (
            self.verification_status
            in {
                CatalogVerificationStatus.UNVERIFIED,
                CatalogVerificationStatus.DEPRECATED,
            }
            and self.verified_fields
        ):
            raise ValueError(
                "unverified or deprecated item cannot claim "
                "verified fields"
            )
        official_types = {
            CatalogSourceType.OFFICIAL_MANUFACTURER,
            CatalogSourceType.OFFICIAL_PUBLISHER,
        }
        normalized_manufacturer = _normalize_manufacturer_identity(
            self.manufacturer
        )
        for source in self.sources:
            if (
                source.source_type
                == CatalogSourceType.OFFICIAL_MANUFACTURER
                and source.manufacturer_identity
                != normalized_manufacturer
            ):
                raise ValueError(
                    "official manufacturer source identity does not "
                    "match equipment manufacturer"
                )
        for field_name in self.verified_fields:
            if not _is_substantive_verified_value(
                getattr(self, field_name)
            ):
                raise ValueError(
                    "verified equipment field has no substantive "
                    f"value: {field_name}"
                )
            if not any(
                source.source_type in official_types
                and source.verification_status
                == CatalogSourceVerificationStatus.VERIFIED
                and field_name in source.confirmed_fields
                for source in self.sources
            ):
                raise ValueError(
                    "verified equipment field lacks completed "
                    f"official-source coverage: {field_name}"
                )
        if any(
            not math.isfinite(value) or value < 0.0
            for value in self.service_clearances_m.values()
        ):
            raise ValueError(
                "service clearances must be finite non-negative values"
            )
        return self


class DesignVariantKind(str, Enum):
    BUDGET = "budget"
    COMFORT = "comfort"
    PREMIUM = "premium"


class DesignVariantStatus(str, Enum):
    NOT_IMPLEMENTED = "not_implemented"
    DRAFT = "draft"
    CALCULATED = "calculated"
    VALIDATED = "validated"


class DesignVariantMetadata(StrictProjectModel):
    variant_id: UUID
    kind: DesignVariantKind
    revision: int = Field(ge=1)
    status: DesignVariantStatus = (
        DesignVariantStatus.NOT_IMPLEMENTED
    )
    objective: str = Field(min_length=1, max_length=1000)
    safety_baseline_sha256: str = Field(pattern=SHA256_PATTERN)
    calculation_case_ids: list[UUID] = Field(default_factory=list)
    issue_ids: list[UUID] = Field(default_factory=list)
    generated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_generation_time(self) -> DesignVariantMetadata:
        if len(self.issue_ids) != len(set(self.issue_ids)):
            raise ValueError(
                "variant issue references must be unique"
            )
        is_generated = self.status != DesignVariantStatus.NOT_IMPLEMENTED
        if is_generated != (self.generated_at is not None):
            raise ValueError(
                "variant generated_at must match its status"
            )
        if (
            self.status == DesignVariantStatus.NOT_IMPLEMENTED
            and self.calculation_case_ids
        ):
            raise ValueError(
                "not-implemented variant cannot reference calculations"
            )
        return self


class SheetDiscipline(str, Enum):
    GENERAL = "general"
    HEATING = "heating"
    PLANT_ROOM = "plant_room"
    WATER_SEWER = "water_sewer"
    VENTILATION_COOLING = "ventilation_cooling"
    ELECTRICAL = "electrical"
    AUTOMATION = "automation"
    SPECIFICATIONS = "specifications"


class SheetManifestSource(StrictProjectModel):
    title: str = Field(min_length=1, max_length=512)
    version: str = Field(min_length=1, max_length=64)
    sha256: str = Field(pattern=SHA256_PATTERN)


class SheetManifestEntry(StrictProjectModel):
    number: int = Field(ge=1)
    code: str = Field(pattern=SHEET_CODE_PATTERN)
    discipline: SheetDiscipline
    title: str = Field(min_length=1, max_length=512)
    required_content: str = Field(min_length=1, max_length=4000)
    primary_user: str = Field(min_length=1, max_length=1000)
    default_included: bool = True


class SheetManifest(StrictProjectModel):
    schema_version: Literal["1.0"] = "1.0"
    manifest_id: str = Field(min_length=1, max_length=256)
    manifest_version: str = Field(min_length=1, max_length=64)
    source: SheetManifestSource
    base_sheet_count: int = Field(ge=1)
    base_building_type: str = Field(min_length=1, max_length=256)
    selection_policy: str = Field(min_length=1, max_length=2000)
    sheets: list[SheetManifestEntry]

    @model_validator(mode="after")
    def validate_sheet_inventory(self) -> SheetManifest:
        if len(self.sheets) != self.base_sheet_count:
            raise ValueError(
                "sheet count does not match base_sheet_count"
            )
        numbers = [sheet.number for sheet in self.sheets]
        expected = list(range(1, self.base_sheet_count + 1))
        if numbers != expected:
            raise ValueError(
                "sheet numbers must be sequential and ordered"
            )
        codes = [sheet.code for sheet in self.sheets]
        if len(codes) != len(set(codes)):
            raise ValueError("sheet codes must be unique")
        expected_disciplines = {
            "GEN": SheetDiscipline.GENERAL,
            "OV": SheetDiscipline.HEATING,
            "TM": SheetDiscipline.PLANT_ROOM,
            "VK": SheetDiscipline.WATER_SEWER,
            "VENT": SheetDiscipline.VENTILATION_COOLING,
            "EM": SheetDiscipline.ELECTRICAL,
            "AUT": SheetDiscipline.AUTOMATION,
            "SPEC": SheetDiscipline.SPECIFICATIONS,
        }
        for sheet in self.sheets:
            group = sheet.code.split("-")[1]
            if sheet.discipline != expected_disciplines[group]:
                raise ValueError(
                    "sheet discipline does not match its code"
                )
        return self


class SheetManifestReference(StrictProjectModel):
    manifest_id: str = Field(min_length=1, max_length=256)
    manifest_version: str = Field(min_length=1, max_length=64)
    manifest_sha256: str = Field(pattern=SHA256_PATTERN)


class AuditActorKind(str, Enum):
    HUMAN = "human"
    LOCAL_AGENT = "local_agent"
    SYSTEM = "system"


class AuditEvent(StrictProjectModel):
    event_id: UUID
    occurred_at: datetime
    actor_kind: AuditActorKind
    event_type: str = Field(min_length=1, max_length=256)
    entity_ids: list[UUID] = Field(default_factory=list)
    details: dict[str, JsonValue] = Field(default_factory=dict)
    input_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    output_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )


class ProjectLifecycleStatus(str, Enum):
    DRAFT = "draft"
    BLOCKED = "blocked"
    READY_FOR_DESIGN = "ready_for_design"
    NOT_IMPLEMENTED = "not_implemented"


class DomainProjectPreviewRequest(StrictProjectModel):
    """Strict in-memory DOMAIN input for the existing project preview route."""

    project_id: str = Field(
        min_length=1,
        max_length=128,
        strict=True,
    )
    rooms_payload: dict[str, Any]
    source_points: list[SourcePoint] = Field(default_factory=list)
    sheet_manifest: SheetManifestReference
    created_at: datetime
    revision: int = Field(default=1, ge=1)
    status: ProjectLifecycleStatus = ProjectLifecycleStatus.DRAFT


class CanonicalProjectModel(StrictProjectModel):
    schema_version: Literal["1.0"] = "1.0"
    project_id: UUID
    revision: int = Field(ge=1)
    status: ProjectLifecycleStatus
    domain: DomainDocument
    seed: ProjectSeed
    sheet_manifest: SheetManifestReference
    assumptions: list[Assumption] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    variants: list[DesignVariantMetadata] = Field(
        default_factory=list
    )
    audit_events: list[AuditEvent] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_project_identity(self) -> CanonicalProjectModel:
        domain_project_id = self.domain.project.stable_id
        if self.project_id != domain_project_id:
            raise ValueError(
                "canonical project id must match domain project id"
            )
        if self.seed.project_stable_id != domain_project_id:
            raise ValueError(
                "project seed id must match domain project id"
            )
        if self.seed.domain_schema_version != (
            self.domain.schema_version
        ):
            raise ValueError(
                "project seed domain schema version mismatch"
            )

        level_ids: set[UUID] = set()
        room_level_ids: dict[UUID, UUID] = {}
        for building in self.domain.project.buildings:
            for level in building.levels:
                if level.stable_id in level_ids:
                    raise ValueError(
                        "DOMAIN level ids must be unique"
                    )
                level_ids.add(level.stable_id)
                for room in level.rooms:
                    if room.stable_id in room_level_ids:
                        raise ValueError(
                            "DOMAIN room ids must be unique"
                        )
                    room_level_ids[room.stable_id] = (
                        level.stable_id
                    )

        for point in self.seed.source_points:
            if (
                point.level_id is not None
                and point.level_id not in level_ids
            ):
                raise ValueError(
                    "source point references an unknown DOMAIN level"
                )
            if point.room_id is not None:
                room_level_id = room_level_ids.get(point.room_id)
                if room_level_id is None:
                    raise ValueError(
                        "source point references an unknown DOMAIN room"
                    )
                if point.level_id != room_level_id:
                    raise ValueError(
                        "source point level does not match DOMAIN room"
                    )

        issue_by_id: dict[UUID, Issue] = {}
        for issue in self.issues:
            if issue.issue_id in issue_by_id:
                raise ValueError(
                    "project issue ids must be unique"
                )
            issue_by_id[issue.issue_id] = issue
        for variant in self.variants:
            for issue_id in variant.issue_ids:
                issue = issue_by_id.get(issue_id)
                if issue is None:
                    raise ValueError(
                        "variant references an unknown project issue"
                    )
                if not issue.blocks_readiness():
                    raise ValueError(
                        "variant issue must be an active blocking issue"
                    )

        if self.status == ProjectLifecycleStatus.READY_FOR_DESIGN:
            if self.seed.status != ProjectSeedStatus.READY:
                raise ValueError(
                    "ready project requires a ready project seed"
                )
            if any(
                assumption.blocks_readiness()
                for assumption in self.assumptions
            ):
                raise ValueError(
                    "ready project has a blocking assumption"
                )
            if any(
                issue.blocks_readiness()
                for issue in self.issues
            ):
                raise ValueError(
                    "ready project has a blocking issue"
                )
        return self

"""Versioned, fail-closed climate lookup using the existing resolver envelope."""
from __future__ import annotations

import json
import re
import unicodedata
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator

from agent.ufh_pre_generation_questionnaire import Model, QuestionnaireState, digest
from agent.ufh_project_engineering_profile_authoring import AuthoredValue, AuthoringProvenance
from agent.ufh_questionnaire_resolver_contract import (
    ResolverRequest,
    ResolverResult,
    ResolvedValue,
    make_resolver_request,
)


DATASET_PATH = Path(__file__).resolve().parents[1] / "standards-rag" / "climate" / "sp131_2025_table_5_1_extract.json"
TARGET_FIELD = "design_conditions.outdoor_design_temperature_c"


class ClimateExtractSource(Model):
    url: str
    host: str
    source_role: str
    publisher_is_official: bool
    source_file_sha256: str | None = None
    extraction_reference: str
    retrieved_on: str


class ClimateNormativeRecord(Model):
    country: str
    region: str
    region_semantics: str
    locality: str
    aliases: list[str] = Field(default_factory=list)
    parameter_id: Literal["coldest_five_day_temperature"]
    probability: Decimal
    column_values_c: tuple[Decimal, Decimal, Decimal, Decimal]
    value_c: Decimal
    units: Literal["°C"]
    table_id: str
    row_label: str
    column_label: str
    document_edition: str

    @field_validator("probability", "value_c", mode="before")
    @classmethod
    def parse_decimal_from_dataset(cls, value):
        if isinstance(value, Decimal):
            return value
        if type(value) in (int, float, str):
            return Decimal(str(value))
        return value

    @field_validator("column_values_c", mode="before")
    @classmethod
    def parse_decimal_columns_from_dataset(cls, value):
        if isinstance(value, (list, tuple)) and len(value) == 4:
            return tuple(item if isinstance(item, Decimal) else Decimal(str(item)) for item in value)
        return value

    @model_validator(mode="after")
    def target_value_is_exact_column(self):
        if self.probability != Decimal("0.92"):
            raise ValueError("CLIMATE_PROBABILITY_MISMATCH")
        if self.locality != self.row_label:
            raise ValueError("CLIMATE_ROW_IDENTITY_MISMATCH")
        return self

    @property
    def record_digest(self) -> str:
        return digest(self.model_dump(mode="json"))


class ClimateNormativeDataset(Model):
    schema_version: Literal["1.0"]
    dataset_id: str
    normative_document_id: str
    normative_title: str
    normative_edition: str
    approval_order: str
    approved_date: str
    effective_from: str
    effective_to: str | None
    replaces: str
    amendment_status_at_acquisition: str
    normative_profile: str
    normative_profile_aliases: dict[str, str]
    source_authority: str
    official_status_source: dict
    extract_sources: list[ClimateExtractSource]
    authority_class: Literal["PROJECT_APPROVED_NORMATIVE_EXTRACT"]
    approval_basis: str
    verification: dict
    records: list[ClimateNormativeRecord]

    @model_validator(mode="after")
    def approved_two_layer_source(self):
        if self.official_status_source.get("authority_class") != "NORMATIVE_DOCUMENT_IDENTITY_AUTHORITY":
            raise ValueError("OFFICIAL_IDENTITY_EVIDENCE_REQUIRED")
        if self.official_status_source.get("document_status") != "ACTIVE":
            raise ValueError("OFFICIAL_CURRENT_STATUS_REQUIRED")
        if self.official_status_source.get("source_file_sha256") is not None:
            raise ValueError("OFFICIAL_SOURCE_DIGEST_MUST_NOT_BE_INVENTED")
        if len(self.extract_sources) < 2:
            raise ValueError("TWO_TEXT_CARRIERS_REQUIRED_FOR_CROSSCHECK")
        if any(source.publisher_is_official for source in self.extract_sources):
            raise ValueError("THIRD_PARTY_TEXT_CARRIER_MISLABELLED_OFFICIAL")
        if self.verification.get("all_record_cells_agree_across_sources") not in (True, False):
            raise ValueError("SOURCE_CROSSCHECK_STATUS_REQUIRED")
        if self.verification.get("column_order") != [
            "coldest_day_probability_0_98",
            "coldest_day_probability_0_92",
            "coldest_five_day_probability_0_98",
            "coldest_five_day_probability_0_92",
        ]:
            raise ValueError("TABLE_COLUMN_ORDER_UNVERIFIED")
        target_index = self.verification.get("target_column_index_zero_based")
        if type(target_index) is not int or target_index < 0 or target_index >= 4:
            raise ValueError("TABLE_TARGET_COLUMN_INDEX_INVALID")
        target_label = self.verification.get("target_column_label")
        if not isinstance(target_label, str) or any(row.column_label != target_label for row in self.records):
            raise ValueError("CLIMATE_COLUMN_LABEL_MISMATCH")
        if any(row.value_c != row.column_values_c[target_index] for row in self.records):
            raise ValueError("CLIMATE_VALUE_NOT_TARGET_COLUMN")
        if not self.records:
            raise ValueError("CLIMATE_DATASET_EMPTY")
        return self

    @property
    def dataset_digest(self) -> str:
        return digest(self.model_dump(mode="json"))

    @property
    def extraction_digest(self) -> str:
        return digest([row.model_dump(mode="json") for row in self.records])


def normalize_text(value: str) -> str:
    """Exact Unicode/case/spacing normalization; deliberately no fuzzy matching."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value).strip()).casefold()


@lru_cache(maxsize=1)
def load_climate_dataset() -> ClimateNormativeDataset:
    raw = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    return ClimateNormativeDataset.model_validate(raw)


def resolved_normative_profile(profile: str, dataset: ClimateNormativeDataset) -> str | None:
    if profile == dataset.normative_profile:
        return profile
    return dataset.normative_profile_aliases.get(profile)


def climate_resolver_context(dataset: ClimateNormativeDataset, normative_profile: str) -> dict[str, str]:
    resolved_profile = resolved_normative_profile(normative_profile, dataset)
    if resolved_profile is None:
        raise ValueError("UNSUPPORTED_NORMATIVE_PROFILE")
    if resolved_profile != dataset.normative_profile:
        raise ValueError("NORMATIVE_DATASET_PROFILE_CONFLICT")
    return {
        "requested_normative_profile": normative_profile,
        "resolved_normative_profile": resolved_profile,
        "dataset_id": dataset.dataset_id,
        "dataset_digest": dataset.dataset_digest,
        "edition": dataset.normative_edition,
    }


def make_climate_resolver_request(
    project_id: str,
    room_id: str,
    project_source_digest: str,
    state: QuestionnaireState,
    normative_profile: str,
    dataset: ClimateNormativeDataset | None = None,
) -> ResolverRequest:
    dataset = dataset or load_climate_dataset()
    context = climate_resolver_context(dataset, normative_profile)
    return make_resolver_request("CLIMATE_RESOLVER", project_id, room_id,
                                 project_source_digest, state.decisions,
                                 resolver_context=context)


def _location_input(request: ResolverRequest) -> tuple[str | None, str | None, str | None]:
    decision = request.normalized_decisions.get("climate")
    if not isinstance(decision, dict):
        return None, None, None
    value = decision.get("value")
    if not isinstance(value, dict):
        return None, None, None
    settlement, region = value.get("settlement"), value.get("region")
    if settlement is not None and not isinstance(settlement, str):
        return None, None, "INVALID_LOCATION_INPUT"
    if region is not None and not isinstance(region, str):
        return None, None, "INVALID_LOCATION_INPUT"
    return settlement, region, None


def _not_resolved(request: ResolverRequest, status: str, diagnostic: str) -> ResolverResult:
    return ResolverResult(resolver_request_id=request.resolver_request_id,
                          status=status, dependency_digest=request.dependency_digest,
                          diagnostics=[diagnostic])


def resolve_climate_request(
    request: ResolverRequest,
    dataset: ClimateNormativeDataset | None = None,
) -> ResolverResult:
    dataset = dataset or load_climate_dataset()
    if request.resolver_type != "CLIMATE_RESOLVER":
        raise ValueError("CLIMATE_RESOLVER_REQUEST_REQUIRED")
    context = request.resolver_context
    if not context or context.get("dataset_digest") != dataset.dataset_digest:
        return _not_resolved(request, "STALE_INPUT", "CLIMATE_DATASET_REVISION_MISMATCH")
    if dataset.verification.get("all_record_cells_agree_across_sources") is False:
        return _not_resolved(request, "AMBIGUOUS", "SOURCE_AMBIGUOUS")
    if dataset.verification.get("all_record_cells_agree_across_sources") is not True:
        return _not_resolved(request, "SOURCE_UNAVAILABLE", "CLIMATE_SOURCE_CROSSCHECK_UNAVAILABLE")
    resolved_profile = resolved_normative_profile(context.get("requested_normative_profile", ""), dataset)
    if resolved_profile is None or context.get("resolved_normative_profile") != resolved_profile:
        return _not_resolved(request, "UNSUPPORTED", "NORMATIVE_PROFILE_UNSUPPORTED")
    if context.get("dataset_id") != dataset.dataset_id or resolved_profile != dataset.normative_profile:
        return _not_resolved(request, "SOURCE_UNAVAILABLE", "NORMATIVE_DATASET_NOT_AVAILABLE")

    settlement, region, invalid = _location_input(request)
    if invalid:
        return _not_resolved(request, "INSUFFICIENT_INPUT", invalid)
    region_labels = {normalize_text(record.region) for record in dataset.records}
    if settlement and normalize_text(settlement) in region_labels:
        return _not_resolved(request, "INSUFFICIENT_INPUT", "LOCALITY_REQUIRED_FOR_REGION")
    if not settlement or not settlement.strip():
        return _not_resolved(request, "INSUFFICIENT_INPUT", "CLIMATE_LOCALITY_REQUIRED")
    normalized_settlement = normalize_text(settlement)
    candidates = [record for record in dataset.records
                  if normalized_settlement in {normalize_text(record.locality),
                                               *(normalize_text(alias) for alias in record.aliases)}]
    if len(candidates) > 1:
        return _not_resolved(request, "AMBIGUOUS", "CLIMATE_LOCALITY_AMBIGUOUS")
    if not candidates:
        return _not_resolved(request, "NOT_FOUND", "CLIMATE_LOCALITY_NOT_FOUND")
    record = candidates[0]
    if region and normalize_text(region) != normalize_text(record.region):
        return _not_resolved(request, "NOT_FOUND", "CLIMATE_REGION_LOCALITY_MISMATCH")

    column_values = ",".join(str(value) for value in record.column_values_c)
    urls = "; ".join(source.url for source in dataset.extract_sources)
    provenance = AuthoringProvenance(
        source_type="project_approved_normative_extract",
        source_reference=f"{dataset.dataset_id}; dataset_digest={dataset.dataset_digest}; sources={urls}",
        source_sha256=dataset.dataset_digest,
        source_field=(f"Table {record.table_id}; section={record.region}; row={record.row_label}; "
                      f"column={record.column_label}; ordered_values_c=[{column_values}]"),
        author_or_confirmation="Owner-approved two-layer normative extract policy",
        transformation=(f"Exact row lookup; selected column {dataset.verification['target_column_index_zero_based'] + 1} "
                        "of the verified ordered cold-day/five-day probability columns; no conversion."),
        units="degC",
    )
    authored = AuthoredValue(status="EXPLICIT_VALUE", value=float(record.value_c),
                              unit="degC", provenance=provenance)
    resolved = ResolvedValue(
        target_authoring_field=TARGET_FIELD,
        authored_value=authored,
        authority_class="PROJECT_APPROVED_NORMATIVE_EXTRACT",
        dependency_digest=request.dependency_digest,
        source_revision=f"{dataset.normative_document_id}:{dataset.dataset_digest}",
        source_date=dataset.verification["verified_on"],
        authoritative_input_references=[dataset.official_status_source["url"], *[s.url for s in dataset.extract_sources]],
    )
    return ResolverResult(resolver_request_id=request.resolver_request_id,
                          status="RESOLVED", dependency_digest=request.dependency_digest,
                          values=[resolved])


def resolve_climate_for_questionnaire(
    project_id: str,
    room_id: str,
    project_source_digest: str,
    state: QuestionnaireState,
    normative_profile: str,
    dataset: ClimateNormativeDataset | None = None,
) -> tuple[ResolverRequest, ResolverResult]:
    """Build the climate request from questionnaire state and resolve its dataset record."""
    dataset = dataset or load_climate_dataset()
    request = make_climate_resolver_request(project_id, room_id, project_source_digest,
                                             state, normative_profile, dataset)
    return request, resolve_climate_request(request, dataset)

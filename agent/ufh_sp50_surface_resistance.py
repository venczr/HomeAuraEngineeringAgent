"""Revision-pinned SP 50.13330.2024 surface-coefficient extract and resolver.

The published copies are text carriers; official Rosstandart metadata establishes
document identity/status. No room heat-loss calculation is performed here.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from agent.project_models import StrictProjectModel
from agent.ufh_envelope_construction_resolver import SurfaceResistanceMethod
from agent.ufh_project_engineering_profile_authoring import AuthoringProvenance


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


class InternalSurfaceCategory(str, Enum):
    WALL_FLOOR_SMOOTH_CEILING_LOW_RIB = "WALL_FLOOR_SMOOTH_CEILING_LOW_RIB"
    RIBBED_CEILING_HIGH_RATIO = "RIBBED_CEILING_HIGH_RATIO"
    WINDOW = "WINDOW"
    ROOFLIGHT = "ROOFLIGHT"


class ExternalSurfaceCategory(str, Enum):
    EXTERIOR_WALL_ROOF_EXPOSED_FLOOR_NORTHERN_ZONE = "EXTERIOR_WALL_ROOF_EXPOSED_FLOOR_NORTHERN_ZONE"
    COLD_BASEMENT_OR_CRAWLSPACE_OPEN_TO_OUTSIDE_NORTHERN_ZONE = "COLD_BASEMENT_OR_CRAWLSPACE_OPEN_TO_OUTSIDE_NORTHERN_ZONE"
    ATTIC_FLOOR_OR_UNHEATED_BASEMENT_WITH_WALL_OPENINGS = "ATTIC_FLOOR_OR_UNHEATED_BASEMENT_WITH_WALL_OPENINGS"
    EXTERIOR_WALL_WITH_OUTSIDE_VENTILATED_AIR_LAYER = "EXTERIOR_WALL_WITH_OUTSIDE_VENTILATED_AIR_LAYER"
    UNVENTILATED_COLD_BASEMENT_OR_TECHNICAL_CRAWLSPACE = "UNVENTILATED_COLD_BASEMENT_OR_TECHNICAL_CRAWLSPACE"
    GROUND_COUPLED = "GROUND_COUPLED"


class SurfaceCoefficientRecord(StrictProjectModel):
    record_id: str
    table_id: str
    row_id: str
    surface_category: str
    applicability: str
    alpha_w_m2k: Decimal = Field(gt=0)
    units: str = "W/(m2*K)"
    normative_document: str = "SP 50.13330.2024"
    authority_class: str = "PROJECT_APPROVED_NORMATIVE_EXTRACT"
    source_references: list[str]
    parameter_label: str
    record_digest: str

    @field_validator("alpha_w_m2k", mode="before")
    @classmethod
    def parse_alpha(cls, value):
        return value if isinstance(value, Decimal) else Decimal(str(value))


class SurfaceHeatTransferDataset(StrictProjectModel):
    dataset_id: str
    normative_document: str
    edition: str
    approval_order: str
    approval_date: str
    effective_from: str
    replaced_edition: str
    current_status: str
    official_status_source: str
    official_status_checked: str
    extract_sources: list[str]
    extract_verified_on: str
    extraction_revision: str
    authority_class: str = "PROJECT_APPROVED_NORMATIVE_EXTRACT"
    records: list[SurfaceCoefficientRecord]
    dataset_digest: str


OFFICIAL_STATUS_SOURCE = "https://protect.gost.ru/sp/details/5081dae9-9ee9-455f-80e8-d093d495361c"
EXTRACT_SOURCES = [
    "https://nav.tn.ru/cloud/iblock/290/290dfb2330a62dde8969a39056b6e1fe/SP_50.13330.2024.pdf",
    "https://base.garant.ru/409274974/",
    "https://kmdrus.ru/uploads/sp/%D0%A1%D0%9F_50.13330.2024.pdf",
    "https://storage.consultant.ru/ondb/attachments/202407/19/iddoc_283336_idnews_54381_SP-50_zCc.pdf",
    "https://rsoserv.ru/wp-content/uploads/2025/02/SP-50.13330.2024-Svod-Pravil.-Teplovaya-zashhita-zdanij.pdf",
]


def _record(rid: str, table: str, row: str, category: str, applicability: str,
            alpha: str, label: str) -> SurfaceCoefficientRecord:
    body = {"record_id": rid, "table_id": table, "row_id": row,
        "surface_category": category, "applicability": applicability,
        "alpha_w_m2k": alpha, "units": "W/(m2*K)", "normative_document": "SP 50.13330.2024",
        "authority_class": "PROJECT_APPROVED_NORMATIVE_EXTRACT",
        "source_references": EXTRACT_SOURCES, "parameter_label": label}
    return SurfaceCoefficientRecord(**body, record_digest=_digest(body))


_RECORDS = [
    _record("SP50-2024-T4-R1", "Table 4", "row 1", "WALL_FLOOR_SMOOTH_CEILING_LOW_RIB",
        "Walls, floors, smooth ceilings; ribbed ceilings only when h/a <= 0.3", "8.7", "alpha_v"),
    _record("SP50-2024-T4-R2", "Table 4", "row 2", "RIBBED_CEILING_HIGH_RATIO",
        "Ribbed ceilings when h/a > 0.3", "7.6", "alpha_v"),
    _record("SP50-2024-T4-R3", "Table 4", "row 3", "WINDOW", "Windows", "8.0", "alpha_v"),
    _record("SP50-2024-T4-R4", "Table 4", "row 4", "ROOFLIGHT", "Rooflights", "9.9", "alpha_v"),
    _record("SP50-2024-T6-R1", "Table 6", "row 1", "EXTERIOR_WALL_ROOF_EXPOSED_FLOOR_NORTHERN_ZONE",
        "Exterior walls, coverings, overpasses, and floors over cold crawlspaces without enclosure walls; Northern construction-climatic zone", "23", "alpha_n winter"),
    _record("SP50-2024-T6-R2", "Table 6", "row 2", "COLD_BASEMENT_OR_CRAWLSPACE_OPEN_TO_OUTSIDE_NORTHERN_ZONE",
        "Floors over cold basements communicating with outdoor air; cold crawlspaces with enclosure walls; cold floors; Northern construction-climatic zone", "17", "alpha_n winter"),
    _record("SP50-2024-T6-R3", "Table 6", "row 3", "ATTIC_FLOOR_OR_UNHEATED_BASEMENT_WITH_WALL_OPENINGS_OR_OUTSIDE_VENTILATED_AIR_LAYER",
        "Attic floors; floors over unheated basements with wall openings; exterior walls with air layer ventilated by outdoor air", "12", "alpha_n winter"),
    _record("SP50-2024-T6-R4", "Table 6", "row 4", "UNVENTILATED_COLD_BASEMENT_OR_TECHNICAL_CRAWLSPACE",
        "Floors over unheated basements and technical crawlspaces not ventilated by outdoor air", "6", "alpha_n winter"),
]

_DATASET_BODY = {
    "dataset_id": "SP50_2024_SURFACE_HEAT_TRANSFER_V1",
    "normative_document": "SP 50.13330.2024 — Тепловая защита зданий",
    "edition": "2024", "approval_order": "327/пр", "approval_date": "2024-05-15",
    "effective_from": "2024-06-16", "replaced_edition": "SP 50.13330.2012",
    "current_status": "ACTIVE",
    "official_status_source": OFFICIAL_STATUS_SOURCE, "official_status_checked": "2026-09-15",
    "extract_sources": EXTRACT_SOURCES, "extract_verified_on": "2026-09-15",
    "extraction_revision": "table4-table6-extract-v1",
    "authority_class": "PROJECT_APPROVED_NORMATIVE_EXTRACT",
    "records": [r.model_dump(mode="json") for r in _RECORDS],
}
SURFACE_HEAT_TRANSFER_DATASET = SurfaceHeatTransferDataset(
    **_DATASET_BODY, dataset_digest=_digest(_DATASET_BODY))


class SurfaceApplicability(StrictProjectModel):
    internal_category: InternalSurfaceCategory | None = None
    external_category: ExternalSurfaceCategory | None = None
    rib_height_to_spacing: Decimal | None = None
    northern_climatic_zone_confirmed: bool | None = None
    climatic_zone_source_reference: str | None = None
    climatic_zone_source_field: str | None = None
    source_reference: str | None = None
    source_field: str | None = None

    @field_validator("internal_category", mode="before")
    @classmethod
    def parse_internal_category(cls, value):
        return value if value is None or isinstance(value, InternalSurfaceCategory) else InternalSurfaceCategory(value)

    @field_validator("external_category", mode="before")
    @classmethod
    def parse_external_category(cls, value):
        return value if value is None or isinstance(value, ExternalSurfaceCategory) else ExternalSurfaceCategory(value)

    @field_validator("rib_height_to_spacing", mode="before")
    @classmethod
    def parse_ratio(cls, value):
        return None if value is None else (value if isinstance(value, Decimal) else Decimal(str(value)))


class DerivedSurfaceResistance(StrictProjectModel):
    resistance_m2k_w: Decimal
    alpha_w_m2k: Decimal
    record_id: str
    provenance_class: str = "DERIVED_FROM_NORMATIVE_COEFFICIENT"
    transformation: str
    source_references: list[str]
    source_record_digest: str


class SurfaceResistanceResolution(StrictProjectModel):
    status: str
    internal: DerivedSurfaceResistance | None = None
    external: DerivedSurfaceResistance | None = None
    method: SurfaceResistanceMethod | None = None
    diagnostics: list[str] = Field(default_factory=list)
    dependency_digest: str
    dataset_digest: str


def _find(table: str, row: str) -> SurfaceCoefficientRecord:
    return next(r for r in SURFACE_HEAT_TRANSFER_DATASET.records
                if r.table_id == table and r.row_id == row)


def verify_independent_extract_values(values: list[Decimal | str | int]) -> Decimal:
    """Accept a structured table cell only when all independent extracts agree."""
    normalized = [Decimal(str(value)) for value in values]
    if len(normalized) < 2:
        raise ValueError("INDEPENDENT_SOURCE_CROSS_CHECK_REQUIRED")
    if any(not value.is_finite() for value in normalized):
        raise ValueError("FINITE_EXTRACT_VALUE_REQUIRED")
    if len(set(normalized)) != 1:
        raise ValueError("SOURCE_AMBIGUOUS")
    return normalized[0]


def resolve_surface_resistances(applicability: SurfaceApplicability) -> SurfaceResistanceResolution:
    """Resolve exact Table 4/6 rows; incomplete or ground paths fail closed."""
    diagnostics: list[str] = []
    internal = external = None
    ic = applicability.internal_category
    ec = applicability.external_category
    if ((ic is not None or ec is not None)
            and (not applicability.source_reference or not applicability.source_field)):
        return SurfaceResistanceResolution(status="INSUFFICIENT_INPUT",
            diagnostics=["SURFACE_APPLICABILITY_PROVENANCE_REQUIRED"],
            dependency_digest=_digest({"applicability": applicability.model_dump(mode="json"),
                                       "dataset": SURFACE_HEAT_TRANSFER_DATASET.dataset_digest}),
            dataset_digest=SURFACE_HEAT_TRANSFER_DATASET.dataset_digest)
    if ic is None:
        diagnostics.append("INTERNAL_SURFACE_APPLICABILITY_UNRESOLVED")
    else:
        if ic == InternalSurfaceCategory.WALL_FLOOR_SMOOTH_CEILING_LOW_RIB:
            if (applicability.rib_height_to_spacing is not None
                    and applicability.rib_height_to_spacing > Decimal("0.3")):
                diagnostics.append("RIBBED_CEILING_H_OVER_A_APPLICABILITY_UNRESOLVED")
                record = None
            else:
                record = _find("Table 4", "row 1")
        elif ic == InternalSurfaceCategory.RIBBED_CEILING_HIGH_RATIO:
            if applicability.rib_height_to_spacing is None or applicability.rib_height_to_spacing <= Decimal("0.3"):
                diagnostics.append("RIBBED_CEILING_H_OVER_A_APPLICABILITY_UNRESOLVED")
                record = None
            else:
                record = _find("Table 4", "row 2")
        else:
            record = _find("Table 4", "row 3" if ic == InternalSurfaceCategory.WINDOW else "row 4")
        if record is not None:
            alpha = record.alpha_w_m2k
            internal = DerivedSurfaceResistance(resistance_m2k_w=Decimal(1)/alpha,
                alpha_w_m2k=alpha, record_id=record.record_id,
                transformation="R_si = 1 / alpha_i",
                source_references=record.source_references, source_record_digest=record.record_digest)
    if ec is None:
        diagnostics.append("EXTERNAL_SURFACE_APPLICABILITY_UNRESOLVED")
    elif ec == ExternalSurfaceCategory.GROUND_COUPLED:
        diagnostics.append("GROUND_BOUNDARY_MODEL_REQUIRED")
    else:
        if ec in {ExternalSurfaceCategory.EXTERIOR_WALL_ROOF_EXPOSED_FLOOR_NORTHERN_ZONE,
                  ExternalSurfaceCategory.COLD_BASEMENT_OR_CRAWLSPACE_OPEN_TO_OUTSIDE_NORTHERN_ZONE}:
            if (applicability.northern_climatic_zone_confirmed is not True
                    or not applicability.climatic_zone_source_reference
                    or not applicability.climatic_zone_source_field):
                diagnostics.append("SURFACE_RESISTANCE_APPLICABILITY_UNRESOLVED")
                record = None
            else:
                record = _find("Table 6", "row 1" if ec == ExternalSurfaceCategory.EXTERIOR_WALL_ROOF_EXPOSED_FLOOR_NORTHERN_ZONE else "row 2")
        elif ec == ExternalSurfaceCategory.ATTIC_FLOOR_OR_UNHEATED_BASEMENT_WITH_WALL_OPENINGS:
            record = _find("Table 6", "row 3")
        elif ec == ExternalSurfaceCategory.EXTERIOR_WALL_WITH_OUTSIDE_VENTILATED_AIR_LAYER:
            record = _find("Table 6", "row 3")
            diagnostics.append("VENTILATED_CONSTRUCTION_METHODOLOGY_SCOPE_REVIEW_REQUIRED")
        else:
            record = _find("Table 6", "row 4")
        if record is not None:
            alpha = record.alpha_w_m2k
            external = DerivedSurfaceResistance(resistance_m2k_w=Decimal(1)/alpha,
                alpha_w_m2k=alpha, record_id=record.record_id,
                transformation="R_se = 1 / alpha_e",
                source_references=record.source_references, source_record_digest=record.record_digest)
    # Only the selectors, ratio and zone assertion affect coefficient choice.
    # Project provenance labels and climate locality do not.
    dep_payload = {"applicability": {
                       "internal_category": applicability.internal_category.value if applicability.internal_category else None,
                       "external_category": applicability.external_category.value if applicability.external_category else None,
                       "rib_height_to_spacing": str(applicability.rib_height_to_spacing) if applicability.rib_height_to_spacing is not None else None,
                       "northern_climatic_zone_confirmed": applicability.northern_climatic_zone_confirmed,
                       "climatic_zone_source_reference": applicability.climatic_zone_source_reference,
                       "climatic_zone_source_field": applicability.climatic_zone_source_field,
                   },
                   "dataset_digest": SURFACE_HEAT_TRANSFER_DATASET.dataset_digest,
                   "internal_record": internal.record_id if internal else None,
                   "external_record": external.record_id if external else None}
    dep = _digest(dep_payload)
    method = None
    # Row 3 expressly concerns ventilated constructions; retain the flagged
    # methodology scope instead of automatically applying the homogeneous-layer formula.
    if internal is not None and external is not None and not diagnostics:
        provenance = AuthoringProvenance(source_type="project_approved_normative_extract",
            source_reference=EXTRACT_SOURCES[0],
            source_sha256=SURFACE_HEAT_TRANSFER_DATASET.dataset_digest,
            source_field=(f"{internal.record_id};{external.record_id};official_identity="
                          f"{OFFICIAL_STATUS_SOURCE}"),
            author_or_confirmation="SP50 Table 4/6 extract cross-checked against independent published copies",
            transformation="Derived Rsi=1/alpha_i and Rse=1/alpha_e from selected table rows",
            units="m2*K/W")
        method = SurfaceResistanceMethod(method_id="SP50.13330.2024_TABLE4_TABLE6",
            method_revision=SURFACE_HEAT_TRANSFER_DATASET.dataset_digest,
            r_si_m2k_w=internal.resistance_m2k_w, r_se_m2k_w=external.resistance_m2k_w,
            provenance=provenance)
    return SurfaceResistanceResolution(status="RESOLVED" if method else "INSUFFICIENT_INPUT",
        internal=internal, external=external, method=method,
        diagnostics=sorted(set(diagnostics)), dependency_digest=dep,
        dataset_digest=SURFACE_HEAT_TRANSFER_DATASET.dataset_digest)


__all__ = ["ExternalSurfaceCategory", "InternalSurfaceCategory", "SurfaceApplicability",
    "SurfaceCoefficientRecord", "SurfaceHeatTransferDataset", "SurfaceResistanceResolution",
    "DerivedSurfaceResistance", "SURFACE_HEAT_TRANSFER_DATASET", "resolve_surface_resistances",
    "verify_independent_extract_values"]

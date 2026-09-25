"""Version-pinned material property source package and fail-closed resolver.

Only a verified subset of SP 50.13330.2024 Appendix M, Table M.1 is bundled.
Thermal insulation is routed to SP 345.1325800.2017 as required by SP 50 clause 5.4.
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from agent.project_models import StrictProjectModel
from agent.ufh_project_engineering_profile_authoring import AuthoringProvenance


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")).hexdigest()


def _dec(value):
    if value is None:
        return None
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("DECIMAL_VALUE_REQUIRED") from exc
    if not result.is_finite():
        raise ValueError("FINITE_DECIMAL_REQUIRED")
    return result


class EnvelopeOperatingCondition(str, Enum):
    A = "A"
    B = "B"
    UNRESOLVED = "UNRESOLVED"


class MaterialPropertyRoute(str, Enum):
    SP50_APPENDIX_M = "SP50_APPENDIX_M"
    SP345_THERMAL_INSULATION = "SP345_THERMAL_INSULATION"


class MaterialThermalPropertyRecord(StrictProjectModel):
    record_id: str
    row_number: int = Field(gt=0)
    material_family: str
    material_description: str
    aliases: list[str] = Field(default_factory=list)
    density_min_kg_m3: Decimal | None = None
    density_max_kg_m3: Decimal | None = None
    density_exact_kg_m3: Decimal | None = None
    heat_capacity_kj_kgk: Decimal | None = None
    lambda_dry_w_mk: Decimal | None = None
    moisture_a_percent: Decimal | None = None
    moisture_b_percent: Decimal | None = None
    lambda_a_w_mk: Decimal | None = None
    lambda_b_w_mk: Decimal | None = None
    heat_absorption_a_w_m2k: Decimal | None = None
    heat_absorption_b_w_m2k: Decimal | None = None
    vapor_permeability_mg_mhpa: Decimal | None = None
    lambda_units_original: str = "W/(m·°C)"
    density_units: str = "kg/m3"
    heat_capacity_units: str = "kJ/(kg·°C)"
    moisture_units: str = "%"
    source_route: MaterialPropertyRoute
    applicability_notes: list[str] = Field(default_factory=list)
    source_references: list[str]
    authority_class: Literal["PROJECT_APPROVED_NORMATIVE_EXTRACT"] = "PROJECT_APPROVED_NORMATIVE_EXTRACT"
    record_digest: str

    @field_validator("source_route", mode="before")
    @classmethod
    def parse_source_route(cls, value):
        return value if isinstance(value, MaterialPropertyRoute) else MaterialPropertyRoute(value)

    @field_validator(
        "density_min_kg_m3", "density_max_kg_m3", "density_exact_kg_m3",
        "heat_capacity_kj_kgk", "lambda_dry_w_mk", "moisture_a_percent",
        "moisture_b_percent", "lambda_a_w_mk", "lambda_b_w_mk",
        "heat_absorption_a_w_m2k", "heat_absorption_b_w_m2k",
        "vapor_permeability_mg_mhpa", mode="before")
    @classmethod
    def parse_decimals(cls, value):
        return _dec(value)


class MaterialThermalPropertyDataset(StrictProjectModel):
    dataset_id: str
    normative_document: str
    edition: str
    appendix_id: str
    table_id: str
    effective_from: str
    official_identity_source: str
    extract_sources: list[str]
    verification_date: str
    extraction_revision: str
    full_table_numbered_rows: int
    bundled_record_count: int
    authority_class: Literal["PROJECT_APPROVED_NORMATIVE_EXTRACT"]
    records: list[MaterialThermalPropertyRecord]
    dataset_digest: str


SP50_IDENTITY_SOURCE = "https://protect.gost.ru/sp/details/5081dae9-9ee9-455f-80e8-d093d495361c"
SP50_EXTRACT_SOURCES = [
    "https://nav.tn.ru/cloud/iblock/2f5/2f5f0066dd005cc71ece191025e5daa2/SP_50.13330.2024.pdf",
    "https://nav.tn.ru/cloud/iblock/d57/d5707456ab7938757343bc60d4d8a787/SP_50.13330.2024.pdf",
    "https://moodle.ivgpu.ru/pluginfile.php/348415/mod_resource/content/1/SP-50.pdf",
    "https://rsoserv.ru/wp-content/uploads/2025/02/SP-50.13330.2024-Svod-Pravil.-Teplovaya-zashhita-zdanii.pdf",
    "https://base.garant.ru/409274974/",
    "https://kmdrus.ru/uploads/sp/%D0%A1%D0%9F_50.13330.2024.pdf",
    "https://tk-expert.ru/uploads/files/docs/%D0%A1%D0%9F%20%D0%A2%D0%95%D0%9F%D0%9B%D0%9E%D0%92%D0%90%D0%AF%20%D0%97%D0%90%D0%A9%D0%98%D0%A2%D0%90%20%D0%97%D0%94%D0%90%D0%9D%D0%98%D0%99%20%D0%90%D0%9A%D0%A2%D0%A3%D0%90%D0%9B%D0%98%D0%97%D0%98%D0%A0%D0%9E%D0%92%D0%90%D0%9D%D0%9D%D0%90%D0%AF%20%D0%A0%D0%95%D0%94%D0%90%D0%9A%D0%A6%D0%98%D0%AF%20%D0%A1%D0%9D%D0%98%D0%9F%2023-02-2003%20%D0%A1%D0%9F%2050.13330.2024.pdf",
    "https://storage.consultant.ru/ondb/attachments/202407/19/iddoc_283336_idnews_54381_SP-50_zCc.pdf",
]
SP345_IDENTITY_SOURCE = "https://protect.gost.ru/sp/details/c020552a-f741-47c3-a588-491af35f8b88"
SP345_CHANGE_1_SOURCE = "https://protect.gost.ru/sp/changesdetails/a4b65c2b-82c0-40cf-a463-083c0561be01"
SP345_CHANGE_2_SOURCE = "https://protect.gost.ru/sp/changesdetails/cbf2eee3-4a10-4f6e-9977-69f335e914fd"
SP345_EXTRACT_SOURCES = [
    "https://base.garant.ru/71984330/",
    "https://base.garant.ru/406604193/",
    "https://t-j.ru/media/teplodom-pdf-006.pdf",
]


def _make_record(row_number: int, family: str, description: str, density_min=None,
                 density_max=None, density_exact=None, cp=None, lambda0=None,
                 wa=None, wb=None, la=None, lb=None, sa=None, sb=None, mu=None,
                 route=MaterialPropertyRoute.SP50_APPENDIX_M, notes=(), aliases=()):
    body = {
        "record_id": f"SP50-2024-M1-R{row_number}", "row_number": row_number,
        "material_family": family, "material_description": description,
        "aliases": list(aliases), "density_min_kg_m3": density_min,
        "density_max_kg_m3": density_max, "density_exact_kg_m3": density_exact,
        "heat_capacity_kj_kgk": cp, "lambda_dry_w_mk": lambda0,
        "moisture_a_percent": wa, "moisture_b_percent": wb,
        "lambda_a_w_mk": la, "lambda_b_w_mk": lb,
        "heat_absorption_a_w_m2k": sa, "heat_absorption_b_w_m2k": sb,
        "vapor_permeability_mg_mhpa": mu,
        "source_route": route.value,
        "applicability_notes": list(notes), "source_references": SP50_EXTRACT_SOURCES,
        "authority_class": "PROJECT_APPROVED_NORMATIVE_EXTRACT",
    }
    return MaterialThermalPropertyRecord(**{**body, "source_route": route}, record_digest=_digest(body))


# EPS/XPS rows remain identifiable, but SP 50 clause 5.4 assigns design lambda
# for thermal insulation to SP 345 Appendix D. They are not lambda fallbacks here.
_RECORDS = [
    _make_record(1, "EPS_BOARD", "Плиты из пенополистирола", 25, 35, cp="1.34", lambda0="0.038", wa=2, wb=10, la="0.040", lb="0.049", sa="0.34", sb="0.38", mu="0.05", route=MaterialPropertyRoute.SP345_THERMAL_INSULATION, aliases=["пенополистирол"], notes=["Design conductivity routed to SP 345.1325800.2017 Appendix D per SP 50 clause 5.4."]),
    _make_record(2, "EPS_BOARD", "То же", 17, 25, cp="1.34", lambda0="0.039", wa=2, wb=10, la="0.041", lb="0.051", sa="0.29", sb="0.32", mu="0.05", route=MaterialPropertyRoute.SP345_THERMAL_INSULATION, aliases=["пенополистирол"], notes=["Same material description as preceding table row; density discriminator is required."]),
    _make_record(3, "EPS_BOARD", "То же", 13, 17, cp="1.34", lambda0="0.041", wa=2, wb=10, la="0.043", lb="0.053", sa="0.25", sb="0.28", mu="0.05", route=MaterialPropertyRoute.SP345_THERMAL_INSULATION, aliases=["пенополистирол"]),
    _make_record(4, "EPS_BOARD", "То же", 10, 13, cp="1.34", lambda0="0.044", wa=2, wb=10, la="0.047", lb="0.057", sa="0.23", sb="0.25", mu="0.05", route=MaterialPropertyRoute.SP345_THERMAL_INSULATION, aliases=["пенополистирол"]),
    _make_record(5, "EPS_BOARD", "То же", density_max=10, cp="1.34", lambda0="0.055", wa=2, wb=10, la="0.058", lb="0.072", sa="0.22", sb="0.24", mu="0.05", route=MaterialPropertyRoute.SP345_THERMAL_INSULATION, aliases=["пенополистирол"]),
    _make_record(6, "EPS_FACADE_BOARD", "Плиты из пенополистирола фасадные", 16, "18.5", cp="1.34", lambda0="0.037", wa=2, wb=10, la="0.039", lb="0.048", sa="0.26", sb="0.29", mu="0.05", route=MaterialPropertyRoute.SP345_THERMAL_INSULATION, aliases=["пенополистирол фасадный"]),
    _make_record(7, "XPS_BOARD", "Плиты из экструзионного пенополистирола", density_max=35, cp="1.5", lambda0="0.033", wa=1, wb=2, la="0.034", lb="0.035", sa="0.33", sb="0.34", mu="0.005", route=MaterialPropertyRoute.SP345_THERMAL_INSULATION, aliases=["экструзионный пенополистирол"]),
    _make_record(8, "XPS_BOARD", "То же", 35, 45, cp="1.7", lambda0="0.034", wa=1, wb=2, la="0.035", lb="0.036", sa="0.42", sb="0.42", mu="0.005", route=MaterialPropertyRoute.SP345_THERMAL_INSULATION, aliases=["экструзионный пенополистирол"]),
    _make_record(51, "GYPSUM_TONGUE_GROOVE_BOARD", "Плиты гипсовые пазогребневые", density_exact=1350, cp="0.84", lambda0="0.35", wa=4, wb=6, la="0.50", lb="0.56", sa="7.04", sb="7.76", mu="0.1"),
    _make_record(52, "GYPSUM_TONGUE_GROOVE_BOARD", "То же", density_exact=1100, cp="0.84", lambda0="0.23", wa=4, wb=6, la="0.35", lb="0.41", sa="5.32", sb="5.99", mu="0.11"),
    _make_record(216, "REINFORCED_CONCRETE", "Железобетон", density_exact=2500, cp="0.84", lambda0="1.69", wa=2, wb=3, la="1.92", lb="2.04", sa="17.98", sb="18.95", mu="0.03"),
    _make_record(217, "NATURAL_AGGREGATE_CONCRETE", "Бетон на гравии или щебне из природного камня", density_exact=2400, cp="0.84", lambda0="1.51", wa=2, wb=3, la="1.74", lb="1.86", sa="16.77", sb="17.88", mu="0.03"),
    _make_record(218, "CEMENT_SAND_MORTAR", "Раствор цементно-песчаный", density_exact=1800, cp="0.84", lambda0="0.58", wa=2, wb=4, la="0.76", lb="0.93", sa="9.6", sb="11.09", mu="0.09"),
]


def build_verified_material_dataset(primary_records, corroborating_records) -> MaterialThermalPropertyDataset:
    """Deterministic source-package compiler. Conflicting row values fail closed.

    Inputs are parsed table extracts normalized to the record field schema; this
    does not scrape webpages or guess row/column order.
    """
    def index_rows(rows):
        indexed = {}
        for row in rows:
            row_number = int(row["row_number"])
            if row_number in indexed:
                raise ValueError("DUPLICATE_TABLE_ROW")
            indexed[row_number] = row
        return indexed

    primary = index_rows(primary_records)
    secondary = index_rows(corroborating_records)
    if not primary or set(primary) != set(secondary):
        raise ValueError("SOURCE_ROW_SET_MISMATCH")
    if primary != secondary:
        raise ValueError("SOURCE_AMBIGUOUS")
    records = []
    for row_number in sorted(primary):
        raw = dict(primary[row_number])
        raw.pop("record_digest", None)
        records.append(MaterialThermalPropertyRecord(**raw, record_digest=_digest(raw)))
    return _dataset(records)


def _dataset(records):
    body = {
        "dataset_id": "SP50_2024_APPENDIX_M_TABLE_M1_SUBSET_V1",
        "normative_document": "SP 50.13330.2024",
        "edition": "2024", "appendix_id": "M", "table_id": "M.1",
        "effective_from": "2024-06-16", "official_identity_source": SP50_IDENTITY_SOURCE,
        "extract_sources": SP50_EXTRACT_SOURCES,
        "verification_date": "2026-09-15", "extraction_revision": "verified-selected-rows-v1",
        "full_table_numbered_rows": 246, "bundled_record_count": len(records),
        "authority_class": "PROJECT_APPROVED_NORMATIVE_EXTRACT",
        "records": [record.model_dump(mode="json") for record in records],
    }
    return MaterialThermalPropertyDataset(**body, dataset_digest=_digest(body))


SP50_MATERIAL_DATASET = _dataset(_RECORDS)


class MaterialPropertyClaim(StrictProjectModel):
    source_type: Literal[
        "project_data", "building_construction_data", "product_document",
        "normative_source", "project_approved_normative_extract", "project_decision", "test_only",
    ]
    authority_class: Literal[
        "PROJECT_AUTHORITATIVE", "MANUFACTURER_AUTHORITATIVE",
        "NORMATIVE_AUTHORITATIVE", "PROJECT_APPROVED_NORMATIVE_EXTRACT",
        "USER_CONFIRMED_PROJECT_DECISION", "TEST_ONLY",
    ]
    lambda_value: Decimal
    units: str
    source_reference: str
    source_field: str
    source_revision: str | None = None
    source_sha256: str | None = None

    @field_validator("lambda_value", mode="before")
    @classmethod
    def parse_lambda(cls, value):
        return _dec(value)

    @model_validator(mode="after")
    def authority_matches_source_kind(self):
        expected = {
            "project_data": "PROJECT_AUTHORITATIVE",
            "building_construction_data": "PROJECT_AUTHORITATIVE",
            "product_document": "MANUFACTURER_AUTHORITATIVE",
            "normative_source": "NORMATIVE_AUTHORITATIVE",
            "project_approved_normative_extract": "PROJECT_APPROVED_NORMATIVE_EXTRACT",
            "project_decision": "USER_CONFIRMED_PROJECT_DECISION",
            "test_only": "TEST_ONLY",
        }[self.source_type]
        if self.authority_class != expected:
            raise ValueError("MATERIAL_SOURCE_AUTHORITY_MISMATCH")
        if not self.source_reference.strip() or not self.source_field.strip():
            raise ValueError("MATERIAL_PROPERTY_PROVENANCE_REQUIRED")
        if self.source_sha256 is not None and not re.fullmatch(r"[a-f0-9]{64}", self.source_sha256):
            raise ValueError("MATERIAL_SOURCE_DIGEST_INVALID")
        return self


class MaterialResolutionRequest(StrictProjectModel):
    material_product_id: str = Field(min_length=1, max_length=256)
    canonical_material_id: str | None = None
    material_family: str | None = None
    exact_normative_record_id: str | None = None
    density_kg_m3: Decimal | None = None
    operating_condition: EnvelopeOperatingCondition = EnvelopeOperatingCondition.UNRESOLVED
    operating_condition_source_reference: str | None = None
    operating_condition_source_field: str | None = None
    operating_condition_authority_class: Literal[
        "PROJECT_AUTHORITATIVE", "NORMATIVE_AUTHORITATIVE",
        "PROJECT_APPROVED_NORMATIVE_EXTRACT", "DERIVED_FROM_AUTHORITATIVE_INPUTS",
        "TEST_ONLY",
    ] | None = None
    source_revision: str | None = None
    property_claims: list[MaterialPropertyClaim] = Field(default_factory=list)
    allow_test_only_condition: bool = False
    sp345_construction_scope: str | None = None
    sp345_lambda_route: Literal["DIRECT_REFERENCE", "APPENDIX_D_CALCULATED"] | None = None
    sp345_lambda0_claim_reference: str | None = None
    sp345_gamma_project_claim: dict[str, Any] | None = None
    sp345_gamma_appendix_e_claim: dict[str, Any] | None = None

    @field_validator("density_kg_m3", mode="before")
    @classmethod
    def parse_density(cls, value):
        return _dec(value)

    @field_validator("operating_condition", mode="before")
    @classmethod
    def parse_condition(cls, value):
        return value if isinstance(value, EnvelopeOperatingCondition) else EnvelopeOperatingCondition(value)


class ResolvedMaterialThermalProperty(StrictProjectModel):
    status: Literal["RESOLVED", "RECORD_RESOLVED", "AMBIGUOUS_MATERIAL", "NOT_FOUND", "SOURCE_VALUE_CONFLICT", "INSUFFICIENT_INPUT", "SP345_SOURCE_REQUIRED", "SP345_GAMMA_SCOPE_REQUIRED", "APPENDIX_E_RESULT_REQUIRED", "LAMBDA0_SOURCE_REQUIRED", "LAMBDA_ROUTE_SELECTION_REQUIRED"]
    material_product_id: str
    record: MaterialThermalPropertyRecord | None = None
    candidate_record_ids: list[str] = Field(default_factory=list)
    operating_condition: EnvelopeOperatingCondition
    lambda_dry_w_mk: Decimal | None = None
    lambda_a_w_mk: Decimal | None = None
    lambda_b_w_mk: Decimal | None = None
    design_lambda_w_mk: Decimal | None = None
    units: str = "W/(m*K)"
    authority_class: str | None = None
    provenance: AuthoringProvenance | None = None
    operating_condition_source_reference: str | None = None
    operating_condition_source_field: str | None = None
    operating_condition_authority_class: str | None = None
    source_revision: str | None = None
    dependency_digest: str
    diagnostics: list[str] = Field(default_factory=list)
    layer_coefficient: Decimal | None = None
    layer_coefficient_provenance: AuthoringProvenance | None = None
    resistance_method: Literal["SP345_FORMULA_5_1A"] | None = None


def _density_matches(row: MaterialThermalPropertyRecord, density: Decimal) -> bool:
    if row.density_exact_kg_m3 is not None:
        return row.density_exact_kg_m3 == density
    if row.density_min_kg_m3 is not None and density < row.density_min_kg_m3:
        return False
    if row.density_max_kg_m3 is not None and density > row.density_max_kg_m3:
        return False
    return row.density_min_kg_m3 is not None or row.density_max_kg_m3 is not None


def _result(request, status, *, record=None, candidates=(), design=None,
            provenance=None, authority=None, diagnostics=(), dataset_dependency=True):
    dep = _digest({"request": request.model_dump(mode="json"),
                   "dataset_digest": (SP50_MATERIAL_DATASET.dataset_digest
                                      if dataset_dependency else None),
                   "record_id": record.record_id if record else None,
                   "record_digest": record.record_digest if record else None})
    return ResolvedMaterialThermalProperty(status=status,
        material_product_id=request.material_product_id, record=record,
        candidate_record_ids=list(candidates), operating_condition=request.operating_condition,
        lambda_dry_w_mk=record.lambda_dry_w_mk if record else None,
        lambda_a_w_mk=record.lambda_a_w_mk if record else None,
        lambda_b_w_mk=record.lambda_b_w_mk if record else None,
        design_lambda_w_mk=design, authority_class=authority,
        provenance=provenance,
        operating_condition_source_reference=request.operating_condition_source_reference,
        operating_condition_source_field=request.operating_condition_source_field,
        operating_condition_authority_class=request.operating_condition_authority_class,
        source_revision=request.source_revision,
        dependency_digest=dep, diagnostics=list(diagnostics))


def resolve_material_thermal_property(request: MaterialResolutionRequest) -> ResolvedMaterialThermalProperty:
    claims = request.property_claims
    for claim in claims:
        if claim.lambda_value <= 0 or claim.units not in {"W/(m*K)", "W/(m·°C)"}:
            return _result(request, "INSUFFICIENT_INPUT", diagnostics=["INVALID_LAMBDA_CLAIM"])
        if claim.authority_class == "TEST_ONLY" and not request.allow_test_only_condition:
            return _result(request, "INSUFFICIENT_INPUT", diagnostics=["TEST_ONLY_SOURCE_NOT_BINDABLE"])
    if claims:
        if len({claim.lambda_value for claim in claims}) > 1:
            return _result(request, "SOURCE_VALUE_CONFLICT", diagnostics=["SOURCE_VALUE_CONFLICT"])
        priority = {"PROJECT_AUTHORITATIVE": 0, "MANUFACTURER_AUTHORITATIVE": 1,
                    "NORMATIVE_AUTHORITATIVE": 2, "PROJECT_APPROVED_NORMATIVE_EXTRACT": 3,
                    "USER_CONFIRMED_PROJECT_DECISION": 4, "TEST_ONLY": 5}
        claim = min(claims, key=lambda item: priority[item.authority_class])
        provenance = AuthoringProvenance(
            source_type=claim.source_type, source_reference=claim.source_reference,
            source_sha256=claim.source_sha256, source_field=claim.source_field,
            author_or_confirmation=claim.source_revision,
            transformation=f"explicit material property; original units={claim.units}; normalized to W/(m*K)",
            units="W/(m*K)")
        if request.operating_condition == EnvelopeOperatingCondition.UNRESOLVED:
            return _result(request, "RECORD_RESOLVED", provenance=provenance,
                           authority=claim.authority_class, diagnostics=["OPERATING_CONDITION_REQUIRED"],
                           dataset_dependency=False)
        if (request.operating_condition_source_reference is None
                or request.operating_condition_source_field is None
                or request.operating_condition_authority_class is None):
            if not request.allow_test_only_condition:
                return _result(request, "INSUFFICIENT_INPUT", provenance=provenance,
                    authority=claim.authority_class, diagnostics=["OPERATING_CONDITION_PROVENANCE_REQUIRED"],
                    dataset_dependency=False)
        if (request.operating_condition_authority_class == "TEST_ONLY"
                and not request.allow_test_only_condition):
            return _result(request, "INSUFFICIENT_INPUT", provenance=provenance,
                authority=claim.authority_class, diagnostics=["TEST_ONLY_CONDITION_NOT_BINDABLE"],
                dataset_dependency=False)
        return _result(request, "RESOLVED", design=claim.lambda_value,
                       provenance=provenance, authority=claim.authority_class,
                       dataset_dependency=False)

    if request.exact_normative_record_id:
        rows = [r for r in SP50_MATERIAL_DATASET.records
                if r.record_id == request.exact_normative_record_id]
    elif request.canonical_material_id:
        key = request.canonical_material_id.strip().casefold()
        rows = [r for r in SP50_MATERIAL_DATASET.records
                if key in {r.record_id.casefold(), r.material_family.casefold(),
                           r.material_description.strip().casefold(),
                           *(alias.strip().casefold() for alias in r.aliases)}]
    else:
        key = request.material_family.strip().casefold() if request.material_family else None
        rows = [r for r in SP50_MATERIAL_DATASET.records
                if key and (r.material_family.casefold() == key
                            or r.material_description.strip().casefold() == key
                            or key in {alias.strip().casefold() for alias in r.aliases})]
    if request.material_family and not request.canonical_material_id:
        key = request.material_family.strip().casefold()
        rows = [r for r in rows if r.material_family.casefold() == key]
        # Family labels select a family; registered names/aliases are exact
        # selectors and remain row-specific.
        if not rows:
            rows = [r for r in SP50_MATERIAL_DATASET.records
                    if key in {r.material_description.strip().casefold(),
                               *(alias.strip().casefold() for alias in r.aliases)}]
    if request.density_kg_m3 is not None:
        rows = [r for r in rows if _density_matches(r, request.density_kg_m3)]
    if len(rows) > 1:
        return _result(request, "AMBIGUOUS_MATERIAL", candidates=[r.record_id for r in rows],
                       diagnostics=["MATERIAL_RECORD_SELECTION_REQUIRED"])
    if not rows:
        return _result(request, "NOT_FOUND", diagnostics=["MATERIAL_RECORD_NOT_FOUND"])
    record = rows[0]
    if record.source_route == MaterialPropertyRoute.SP345_THERMAL_INSULATION:
        from agent.ufh_sp345_insulation_property_resolver import (
            SP345ConstructionScope, SP345InsulationRequest, resolve_sp345_insulation_property,
        )
        if request.operating_condition == EnvelopeOperatingCondition.UNRESOLVED:
            return _result(request, "RECORD_RESOLVED", record=record, authority=record.authority_class,
                diagnostics=["ENVELOPE_OPERATING_CONDITION_RESULT_REQUIRED"])
        try:
            scope = SP345ConstructionScope(request.sp345_construction_scope) if request.sp345_construction_scope else None
        except ValueError:
            return _result(request, "INSUFFICIENT_INPUT", record=record, diagnostics=["SP345_CONSTRUCTION_SCOPE_INVALID"])
        sp345 = resolve_sp345_insulation_property(SP345InsulationRequest(
            material_record_id=record.record_id, operating_condition=request.operating_condition,
            operating_condition_source_reference=request.operating_condition_source_reference,
            operating_condition_source_field=request.operating_condition_source_field,
            operating_condition_authority_class=request.operating_condition_authority_class,
            lambda0_claim_reference=request.sp345_lambda0_claim_reference,
            source_revision=request.source_revision, construction_scope=scope,
            gamma_project_or_test_claim=request.sp345_gamma_project_claim,
            gamma_appendix_e_claim=request.sp345_gamma_appendix_e_claim,
            lambda_route=request.sp345_lambda_route))
        status_map = {"OPERATING_CONDITION_REQUIRED": "INSUFFICIENT_INPUT",
            "SP345_GAMMA_SCOPE_REQUIRED": "SP345_GAMMA_SCOPE_REQUIRED",
            "APPENDIX_E_RESULT_REQUIRED": "APPENDIX_E_RESULT_REQUIRED",
            "LAMBDA0_SOURCE_REQUIRED": "LAMBDA0_SOURCE_REQUIRED",
            "LAMBDA_ROUTE_SELECTION_REQUIRED": "LAMBDA_ROUTE_SELECTION_REQUIRED",
            "RESOLVED": "RESOLVED"}
        provenance = None
        gamma_provenance = None
        if sp345.status == "RESOLVED" and sp345.legacy_record and sp345.gamma:
            provenance = AuthoringProvenance(source_type="project_approved_normative_extract",
                source_reference=sp345.legacy_record.source_references[0], source_sha256=None,
                source_field=f"SP 50.13330.2012 Appendix T Table T.1 row {sp345.legacy_record.row_number} lambda_{request.operating_condition.value}",
                author_or_confirmation=f"record_digest={sp345.legacy_record.record_digest}; dataset_digest={sp345.dependency_digest}",
                transformation=f"SP345 D direct-reference route {sp345.lambda_route}; selected lambda_{request.operating_condition.value}",
                units="W/(m*K)")
            gamma_source_types = {"PROJECT_APPROVED_NORMATIVE_EXTRACT": "project_approved_normative_extract",
                "NORMATIVE_AUTHORITATIVE": "normative_source", "PROJECT_AUTHORITATIVE": "building_construction_data",
                "TEST_ONLY": "test_only"}
            gamma_provenance = AuthoringProvenance(source_type=gamma_source_types[sp345.gamma.authority_class],
                source_reference=sp345.gamma.source_reference, source_sha256=None,
                source_field=sp345.gamma.source_field, author_or_confirmation=sp345.gamma.clause_id,
                transformation=f"SP345 gamma source={sp345.gamma.source.value}; digest={sp345.gamma.digest}", units="1")
        return ResolvedMaterialThermalProperty(status=status_map[sp345.status],
            material_product_id=request.material_product_id, record=record, operating_condition=request.operating_condition,
            lambda_dry_w_mk=sp345.legacy_record.lambda0_w_mk if sp345.legacy_record else record.lambda_dry_w_mk,
            lambda_a_w_mk=sp345.legacy_record.lambda_a_w_mk if sp345.legacy_record else None,
            lambda_b_w_mk=sp345.legacy_record.lambda_b_w_mk if sp345.legacy_record else None,
            design_lambda_w_mk=sp345.design_lambda_w_mk,
            units="W/(m*K)", authority_class=sp345.authority_class, provenance=provenance,
            operating_condition_source_reference=request.operating_condition_source_reference,
            operating_condition_source_field=request.operating_condition_source_field,
            operating_condition_authority_class=request.operating_condition_authority_class,
            source_revision=request.source_revision, dependency_digest=sp345.dependency_digest,
            diagnostics=sp345.diagnostics, layer_coefficient=sp345.gamma.value if sp345.gamma else None,
            layer_coefficient_provenance=gamma_provenance,
            resistance_method="SP345_FORMULA_5_1A" if sp345.status == "RESOLVED" else None)
    if request.operating_condition == EnvelopeOperatingCondition.UNRESOLVED:
        return _result(request, "RECORD_RESOLVED", record=record,
                       authority=record.authority_class,
                       diagnostics=["OPERATING_CONDITION_REQUIRED"])
    if (request.operating_condition_source_reference is None
            or request.operating_condition_source_field is None
            or request.operating_condition_authority_class is None):
        if not request.allow_test_only_condition:
            return _result(request, "INSUFFICIENT_INPUT", record=record,
                diagnostics=["OPERATING_CONDITION_PROVENANCE_REQUIRED"])
    if request.operating_condition_authority_class == "TEST_ONLY" and not request.allow_test_only_condition:
        return _result(request, "INSUFFICIENT_INPUT", record=record,
                       diagnostics=["TEST_ONLY_CONDITION_NOT_BINDABLE"])
    if (request.operating_condition_authority_class == "TEST_ONLY"
            and (request.operating_condition_source_reference is None
                 or request.operating_condition_source_field is None)):
        return _result(request, "INSUFFICIENT_INPUT", record=record,
                       diagnostics=["OPERATING_CONDITION_PROVENANCE_REQUIRED"])
    design = record.lambda_a_w_mk if request.operating_condition == EnvelopeOperatingCondition.A else record.lambda_b_w_mk
    if design is None:
        return _result(request, "INSUFFICIENT_INPUT", record=record,
                       diagnostics=["DESIGN_LAMBDA_NOT_PRESENT_IN_SOURCE_ROW"])
    provenance = AuthoringProvenance(
        source_type="project_approved_normative_extract",
        source_reference=record.source_references[0], source_sha256=None,
        source_field=f"SP 50.13330.2024 Appendix M Table M.1 row {record.row_number} lambda_{request.operating_condition.value}",
        author_or_confirmation=f"Cross-checked structured row extract; record_digest={record.record_digest}",
        transformation=f"select lambda_{request.operating_condition.value} from exact normative row; dataset_digest={SP50_MATERIAL_DATASET.dataset_digest}; no dry-lambda fallback",
        units="W/(m*K)")
    return _result(request, "RESOLVED", record=record, design=design,
                   provenance=provenance, authority=record.authority_class)


def construction_layer_from_resolution(material_product_id: str, thickness_m,
                                       result: ResolvedMaterialThermalProperty):
    """Create an existing envelope layer only when design lambda is resolved."""
    if result.status != "RESOLVED" or result.design_lambda_w_mk is None or result.provenance is None:
        raise ValueError("MATERIAL_DESIGN_LAMBDA_UNRESOLVED")
    from agent.ufh_envelope_construction_resolver import ConstructionLayer
    return ConstructionLayer(material_product_id=material_product_id, thickness_m=thickness_m,
        lambda_w_mk=result.design_lambda_w_mk, lambda_provenance=result.provenance,
        material_record_id=result.record.record_id if result.record else None,
        material_resolution_digest=result.dependency_digest,
        property_condition=result.operating_condition.value,
        condition_source_reference=result.operating_condition_source_reference,
        condition_source_field=result.operating_condition_source_field,
        condition_authority_class=result.operating_condition_authority_class,
        resistance_method=result.resistance_method or "GENERIC_D_OVER_LAMBDA",
        layer_operating_coefficient=result.layer_coefficient,
        layer_coefficient_provenance=result.layer_coefficient_provenance)


__all__ = ["EnvelopeOperatingCondition", "MaterialPropertyRoute", "MaterialThermalPropertyRecord",
    "MaterialThermalPropertyDataset", "MaterialPropertyClaim", "MaterialResolutionRequest",
    "ResolvedMaterialThermalProperty", "SP50_MATERIAL_DATASET", "resolve_material_thermal_property",
    "construction_layer_from_resolution", "build_verified_material_dataset", "SP50_IDENTITY_SOURCE",
    "SP50_EXTRACT_SOURCES", "SP345_IDENTITY_SOURCE", "SP345_CHANGE_1_SOURCE",
    "SP345_CHANGE_2_SOURCE", "SP345_EXTRACT_SOURCES"]

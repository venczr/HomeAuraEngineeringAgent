"""SP 50.13330.2024 room moisture and envelope operating-condition resolver.

Only Table 1 and Table 2 structured extracts are packaged here. Appendix A is
a graphical moisture-zone map; locality mapping intentionally fails closed.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Literal

from pydantic import Field
from agent.project_models import StrictProjectModel


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), default=str).encode()).hexdigest()


DOCUMENT_ID = "SP 50.13330.2024"
OFFICIAL_IDENTITY_SOURCE = "https://protect.gost.ru/sp/details/5081dae9-9ee9-455f-80e8-d093d495361c"
EXTRACT_SOURCES = (
    "https://base.garant.ru/409274974/",
    "https://mooml.com/d/normativno-pravovye-dokumenty/proektirovanie-inzhenernye-izyskaniya/55765/",
    "https://gostcheck.ru/sp/sp-50-13330-2024/table/sp-50-13330-2024-table-1",
    "https://gostcheck.ru/sp/sp-50-13330-2024/table/sp-50-13330-2024-table-2",
)
AUTHORITY = "PROJECT_APPROVED_NORMATIVE_EXTRACT"
NORMATIVE_METADATA = {
    "document": DOCUMENT_ID, "title": "Тепловая защита зданий",
    "approval_order": "Минстрой России № 327/пр",
    "approval_date": "2024-05-15", "effective_from": "2024-06-16",
    "official_identity_source": OFFICIAL_IDENTITY_SOURCE,
    "text_extract_authority": AUTHORITY,
    "verification_date": "2026-09-15",
}


class MoistureRegimeRow(StrictProjectModel):
    temperature_band_id: Literal["T_LE_12", "T_GT_12_LE_24", "T_GT_24"]
    temperature_lower_c: Decimal | None
    temperature_lower_inclusive: bool
    temperature_upper_c: Decimal | None
    temperature_upper_inclusive: bool
    dry_rh_upper_percent: Decimal
    normal_rh_upper_percent: Decimal
    humid_rh_upper_percent: Decimal | None
    wet_rh_lower_exclusive_percent: Decimal | None
    wet_applicable: bool
    table_id: str = "Table 1"


TABLE1_ROWS = (
    MoistureRegimeRow(temperature_band_id="T_LE_12", temperature_lower_c=None,
        temperature_lower_inclusive=False, temperature_upper_c=Decimal("12"),
        temperature_upper_inclusive=True, dry_rh_upper_percent=Decimal("60"),
        normal_rh_upper_percent=Decimal("75"), humid_rh_upper_percent=None,
        wet_rh_lower_exclusive_percent=None, wet_applicable=False),
    MoistureRegimeRow(temperature_band_id="T_GT_12_LE_24", temperature_lower_c=Decimal("12"),
        temperature_lower_inclusive=False, temperature_upper_c=Decimal("24"),
        temperature_upper_inclusive=True, dry_rh_upper_percent=Decimal("50"),
        normal_rh_upper_percent=Decimal("60"), humid_rh_upper_percent=Decimal("75"),
        wet_rh_lower_exclusive_percent=Decimal("75"), wet_applicable=True),
    MoistureRegimeRow(temperature_band_id="T_GT_24", temperature_lower_c=Decimal("24"),
        temperature_lower_inclusive=False, temperature_upper_c=None,
        temperature_upper_inclusive=False, dry_rh_upper_percent=Decimal("40"),
        normal_rh_upper_percent=Decimal("50"), humid_rh_upper_percent=Decimal("60"),
        wet_rh_lower_exclusive_percent=Decimal("60"), wet_applicable=True),
)


class Table2Row(StrictProjectModel):
    room_regime: Literal["DRY", "NORMAL", "HUMID", "WET"]
    moisture_zone: Literal["DRY", "NORMAL", "HUMID"]
    condition: Literal["A", "B"]
    table_id: str = "Table 2"


_TABLE2_MATRIX = {
    "DRY": ("A", "A", "B"),
    "NORMAL": ("A", "B", "B"),
    "HUMID": ("B", "B", "B"),
    "WET": ("B", "B", "B"),
}
TABLE2_ROWS = tuple(Table2Row(room_regime=r, moisture_zone=z, condition=c)
    for r, vals in _TABLE2_MATRIX.items()
    for z, c in zip(("DRY", "NORMAL", "HUMID"), vals))
SOURCE_PACKAGE_DIGEST = _digest({
    "document": DOCUMENT_ID, "effective_from": "2024-06-16", "table1": TABLE1_ROWS,
    "table2": TABLE2_ROWS, "authority": AUTHORITY, "sources": EXTRACT_SOURCES,
    "metadata": NORMATIVE_METADATA,
})


class ConstructionMoistureZoneInput(StrictProjectModel):
    zone: Literal["DRY", "NORMAL", "HUMID"]
    source_reference: str = Field(min_length=1)
    source_field: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    authority_class: Literal["PROJECT_AUTHORITATIVE", "PROJECT_APPROVED_NORMATIVE_EXTRACT"]


class OperatingConditionResult(StrictProjectModel):
    status: Literal["RESOLVED", "INSUFFICIENT_INPUT", "MOISTURE_ZONE_SOURCE_REQUIRED", "OPERATING_CONDITION_NOT_APPLICABLE", "OUT_OF_DOMAIN"]
    construction_scope: Literal["EXTERIOR_ENVELOPE", "INTERIOR", "UNKNOWN"]
    indoor_design_temperature_c: Decimal | None = None
    indoor_design_relative_humidity_percent: Decimal | None = None
    room_moisture_regime: Literal["DRY", "NORMAL", "HUMID", "WET"] | None = None
    construction_moisture_zone: Literal["DRY", "NORMAL", "HUMID"] | None = None
    operating_condition: Literal["A", "B"] | None = None
    table1_row_id: str | None = None
    table2_row_id: str | None = None
    source_authority: Literal["PROJECT_APPROVED_NORMATIVE_EXTRACT"] = AUTHORITY
    dependency_digest: str
    source_package_digest: str = SOURCE_PACKAGE_DIGEST
    diagnostics: list[str] = Field(default_factory=list)


def _dec(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def classify_room_moisture_regime(temperature_c, relative_humidity_percent):
    t, rh = _dec(temperature_c), _dec(relative_humidity_percent)
    if not t.is_finite() or not rh.is_finite() or not Decimal("0") <= rh <= Decimal("100"):
        raise ValueError("INVALID_DESIGN_TEMPERATURE_OR_RELATIVE_HUMIDITY")
    row = next(r for r in TABLE1_ROWS if
        (r.temperature_lower_c is None or t > r.temperature_lower_c) and
        (r.temperature_upper_c is None or t <= r.temperature_upper_c))
    if rh <= row.dry_rh_upper_percent:
        regime = "DRY"
    elif rh <= row.normal_rh_upper_percent:
        regime = "NORMAL"
    elif row.wet_applicable and rh > row.wet_rh_lower_exclusive_percent:
        regime = "WET"
    else:
        regime = "HUMID"
    return regime, row


def resolve_envelope_operating_condition(*, indoor_design_temperature_c,
        indoor_design_relative_humidity_percent, moisture_zone: ConstructionMoistureZoneInput | None,
        construction_scope: Literal["EXTERIOR_ENVELOPE", "INTERIOR", "UNKNOWN"],
        project_id: str, room_id: str, project_revision: str,
        temperature_provenance: str, humidity_provenance: str):
    deps = {"project": project_id, "room": room_id,
        "temperature": str(indoor_design_temperature_c), "temperature_source": temperature_provenance,
        "rh": str(indoor_design_relative_humidity_percent), "rh_source": humidity_provenance,
        "zone": moisture_zone.model_dump(mode="json") if moisture_zone else None,
        "scope": construction_scope, "dataset": SOURCE_PACKAGE_DIGEST}
    dep = _digest(deps)
    if construction_scope == "INTERIOR":
        return OperatingConditionResult(status="OPERATING_CONDITION_NOT_APPLICABLE",
            construction_scope=construction_scope, dependency_digest=dep,
            diagnostics=["TABLE2_APPLIES_TO_OUTER_ENVELOPE_MATERIAL_SELECTION"])
    if construction_scope != "EXTERIOR_ENVELOPE":
        return OperatingConditionResult(status="INSUFFICIENT_INPUT", construction_scope=construction_scope,
            dependency_digest=dep, diagnostics=["CONSTRUCTION_SCOPE_REQUIRED"])
    if indoor_design_temperature_c is None or indoor_design_relative_humidity_percent is None:
        return OperatingConditionResult(status="INSUFFICIENT_INPUT", construction_scope=construction_scope,
            dependency_digest=dep, diagnostics=["INDOOR_DESIGN_TEMPERATURE_AND_DESIGN_RH_REQUIRED"])
    try:
        regime, trow = classify_room_moisture_regime(indoor_design_temperature_c,
            indoor_design_relative_humidity_percent)
    except ValueError:
        return OperatingConditionResult(status="OUT_OF_DOMAIN", construction_scope=construction_scope,
            dependency_digest=dep, diagnostics=["INVALID_DESIGN_TEMPERATURE_OR_RELATIVE_HUMIDITY"])
    if moisture_zone is None:
        return OperatingConditionResult(status="MOISTURE_ZONE_SOURCE_REQUIRED",
            construction_scope=construction_scope,
            indoor_design_temperature_c=_dec(indoor_design_temperature_c),
            indoor_design_relative_humidity_percent=_dec(indoor_design_relative_humidity_percent),
            room_moisture_regime=regime, table1_row_id=trow.temperature_band_id,
            dependency_digest=dep, diagnostics=["APPENDIX_A_LOCALITY_MAPPING_NOT_AUTOMATED"])
    match = next(r for r in TABLE2_ROWS if r.room_regime == regime and r.moisture_zone == moisture_zone.zone)
    return OperatingConditionResult(status="RESOLVED", construction_scope=construction_scope,
        indoor_design_temperature_c=_dec(indoor_design_temperature_c),
        indoor_design_relative_humidity_percent=_dec(indoor_design_relative_humidity_percent),
        room_moisture_regime=regime, construction_moisture_zone=moisture_zone.zone,
        operating_condition=match.condition, table1_row_id=trow.temperature_band_id,
        table2_row_id=f"{regime}:{moisture_zone.zone}", dependency_digest=dep)


def resolver_contract_result(request):
    """Adapt to the existing ResolverResult handoff; no direct profile writes."""
    from agent.ufh_questionnaire_resolver_contract import ResolvedValue, ResolverResult
    from agent.ufh_project_engineering_profile_authoring import AuthoredValue, AuthoringProvenance

    def decision_value(key):
        item = request.normalized_decisions.get(key)
        return item.get("value") if isinstance(item, dict) else None

    temp = request.resolver_context.get("indoor_design_temperature_c") or None
    temp_ref = request.resolver_context.get("indoor_temperature_source") or None
    scope = request.resolver_context.get("construction_scope", "UNKNOWN")
    raw_zone = decision_value("moisture_zone")
    zone = None
    if isinstance(raw_zone, dict):
        try:
            zone = ConstructionMoistureZoneInput.model_validate(raw_zone)
        except Exception:
            pass
    rh_raw = decision_value("indoor_rh")
    rh = rh_raw.get("value") if isinstance(rh_raw, dict) else None
    humidity_provenance = (request.normalized_decisions.get("indoor_rh") or {}).get(
        "source_reference", "missing")
    if (rh_raw is not None and (not isinstance(rh_raw, dict) or rh_raw.get("unit") != "%")):
        return ResolverResult(resolver_request_id=request.resolver_request_id,
            status="OUT_OF_DOMAIN", dependency_digest=request.dependency_digest,
            diagnostics=["INDOOR_RH_UNIT_MUST_BE_PERCENT"])
    result = resolve_envelope_operating_condition(
        indoor_design_temperature_c=temp, indoor_design_relative_humidity_percent=rh,
        moisture_zone=zone, construction_scope=scope,
        project_id=request.project_id, room_id=request.room_id,
        project_revision=request.project_source_digest,
        temperature_provenance=temp_ref or "missing-project-temperature-provenance",
        humidity_provenance=humidity_provenance,
    )
    if result.status != "RESOLVED":
        status = "SOURCE_UNAVAILABLE" if result.status == "MOISTURE_ZONE_SOURCE_REQUIRED" else (
            "OUT_OF_DOMAIN" if result.status == "OUT_OF_DOMAIN" else "INSUFFICIENT_INPUT")
        return ResolverResult(resolver_request_id=request.resolver_request_id,
            status=status, dependency_digest=request.dependency_digest,
            diagnostics=result.diagnostics + [result.status])
    if temp_ref is None or zone is None:
        return ResolverResult(resolver_request_id=request.resolver_request_id,
            status="INSUFFICIENT_INPUT", dependency_digest=request.dependency_digest,
            diagnostics=["AUTHORITATIVE_TEMPERATURE_AND_MOISTURE_ZONE_PROVENANCE_REQUIRED"])
    provenance = AuthoringProvenance(
        source_type="project_approved_normative_extract",
        source_reference=OFFICIAL_IDENTITY_SOURCE,
        source_sha256=SOURCE_PACKAGE_DIGEST,
        source_field=f"{DOCUMENT_ID} Table 1 row {result.table1_row_id}; Table 2 row {result.table2_row_id}",
        author_or_confirmation="normative lookup over sourced project design inputs",
        transformation=(f"SP50 T1:{result.table1_row_id}; T2:{result.table2_row_id}="
            f"{result.operating_condition}; temp={temp}C@{temp_ref}; "
            f"temp-src={request.resolver_context.get('indoor_temperature_source_digest', '')[:16]}; "
            f"RH={rh}%@{humidity_provenance}; zone={zone.zone}@{zone.source_reference}"
            f"#{zone.source_field}@{zone.source_revision}; authority={zone.authority_class}"),
        units="none",
    )
    value = AuthoredValue(status="DERIVED", value=result.operating_condition,
        unit="none", provenance=provenance)
    return ResolverResult(resolver_request_id=request.resolver_request_id,
        status="RESOLVED", dependency_digest=request.dependency_digest,
        values=[ResolvedValue(target_authoring_field="envelope_constructions.operating_condition",
            authored_value=value, authority_class="PROJECT_APPROVED_NORMATIVE_EXTRACT",
            dependency_digest=request.dependency_digest, source_revision=SOURCE_PACKAGE_DIGEST,
            authoritative_input_references=[temp_ref or "missing temperature source", humidity_provenance,
                zone.source_reference if zone else "missing zone source"])])


def apply_condition_to_material_request(material_request, condition_value):
    """Copy resolved shared A/B context into an existing material request."""
    if condition_value.status != "RESOLVED" or condition_value.operating_condition not in {"A", "B"}:
        raise ValueError("OPERATING_CONDITION_NOT_RESOLVED")
    from agent.ufh_material_thermal_property_resolver import EnvelopeOperatingCondition
    return material_request.model_copy(update={
        "operating_condition": EnvelopeOperatingCondition(condition_value.operating_condition),
        "operating_condition_source_reference": OFFICIAL_IDENTITY_SOURCE,
        "operating_condition_source_field": f"{DOCUMENT_ID} Table 1/Table 2; dependency={condition_value.dependency_digest}",
        "operating_condition_authority_class": AUTHORITY,
    })

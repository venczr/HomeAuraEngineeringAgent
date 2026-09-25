"""Source-pinned SP345 insulation lambda and layer-resistance path."""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from agent.project_models import StrictProjectModel
from agent.ufh_material_thermal_property_resolver import EnvelopeOperatingCondition


def _digest(value) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class LegacyAppendixTStatus(str, Enum):
    DATED_REFERENCE_EXPLICITLY_RETAINED = "DATED_REFERENCE_EXPLICITLY_RETAINED"
    LEGACY_REFERENCE_INCORPORATED_BY_SP345 = "LEGACY_REFERENCE_INCORPORATED_BY_SP345"
    SUCCESSOR_NOT_EQUIVALENT = "SUCCESSOR_NOT_EQUIVALENT"


class SP345GammaSource(str, Enum):
    PROJECT_OR_TEST_RESULT = "PROJECT_OR_TEST_RESULT"
    APPENDIX_E_METHOD_RESULT = "APPENDIX_E_METHOD_RESULT"
    NORMATIVE_FALLBACK_SP345_5_2 = "NORMATIVE_FALLBACK_SP345_5_2"


class SP345ConstructionScope(str, Enum):
    OTHER_OR_UNLISTED = "OTHER_OR_UNLISTED"
    ROOF = "ROOF"
    SFTK = "SFTK"
    LAYERED_MASONRY = "LAYERED_MASONRY"
    NFS_MINERAL_WOOL = "NFS_MINERAL_WOOL"
    BURIED_OR_GROUND_CONTACT_POLYMER = "BURIED_OR_GROUND_CONTACT_POLYMER"


class SP345GammaClaim(StrictProjectModel):
    value: Decimal = Field(gt=0)
    units: Literal["1"] = "1"
    source: SP345GammaSource
    scope: SP345ConstructionScope
    source_reference: str = Field(min_length=1)
    source_field: str = Field(min_length=1)
    source_revision: str | None = None
    authority_class: Literal["PROJECT_AUTHORITATIVE", "NORMATIVE_AUTHORITATIVE",
                             "PROJECT_APPROVED_NORMATIVE_EXTRACT", "TEST_ONLY"]
    clause_id: str | None = None
    digest: str = ""

    @field_validator("source", mode="before")
    @classmethod
    def parse_source(cls, value):
        return value if isinstance(value, SP345GammaSource) else SP345GammaSource(value)

    @field_validator("scope", mode="before")
    @classmethod
    def parse_scope(cls, value):
        return value if isinstance(value, SP345ConstructionScope) else SP345ConstructionScope(value)

    @field_validator("value", mode="before")
    @classmethod
    def decimal_value(cls, value):
        return value if isinstance(value, Decimal) else Decimal(str(value))

    @model_validator(mode="after")
    def source_semantics(self):
        if self.source == SP345GammaSource.NORMATIVE_FALLBACK_SP345_5_2:
            if (self.value != Decimal("1") or self.authority_class != "PROJECT_APPROVED_NORMATIVE_EXTRACT"
                    or self.clause_id != "SP345:2017+AMD1+AMD2:5.2"):
                raise ValueError("SP345_GAMMA_FALLBACK_PROVENANCE_INVALID")
        elif self.authority_class == "TEST_ONLY":
            pass
        elif self.source == SP345GammaSource.APPENDIX_E_METHOD_RESULT and not self.source_field:
            raise ValueError("APPENDIX_E_RESULT_PROVENANCE_REQUIRED")
        elif self.source == SP345GammaSource.PROJECT_OR_TEST_RESULT and self.authority_class not in {
            "PROJECT_AUTHORITATIVE", "TEST_ONLY",
        }:
            raise ValueError("PROJECT_GAMMA_AUTHORITY_INVALID")
        body = self.model_dump(mode="json", exclude={"digest"})
        expected = _digest(body)
        if self.digest and self.digest != expected:
            raise ValueError("SP345_GAMMA_DIGEST_MISMATCH")
        object.__setattr__(self, "digest", expected)
        return self


class SP345GammaResolution(StrictProjectModel):
    status: Literal["RESOLVED", "APPENDIX_E_RESULT_REQUIRED"]
    claim: SP345GammaClaim | None = None
    diagnostics: list[str] = Field(default_factory=list)


def resolve_sp345_gamma(scope: SP345ConstructionScope, *, project_or_test: SP345GammaClaim | None = None,
                        appendix_e: SP345GammaClaim | None = None) -> SP345GammaResolution:
    """Resolve gamma by explicit precedence; special Appendix-E scopes fail closed."""
    special = scope != SP345ConstructionScope.OTHER_OR_UNLISTED
    for candidate in (project_or_test, appendix_e):
        if candidate is not None:
            if candidate.scope != scope:
                continue
            expected = (SP345GammaSource.PROJECT_OR_TEST_RESULT if candidate is project_or_test
                        else SP345GammaSource.APPENDIX_E_METHOD_RESULT)
            if candidate.source != expected:
                return SP345GammaResolution(status="APPENDIX_E_RESULT_REQUIRED",
                    diagnostics=["GAMMA_SOURCE_PRECEDENCE_OR_TYPE_INVALID"])
            return SP345GammaResolution(status="RESOLVED", claim=candidate)
    if special:
        return SP345GammaResolution(status="APPENDIX_E_RESULT_REQUIRED",
            diagnostics=["APPENDIX_E_METHOD_OR_TEST_RESULT_REQUIRED", scope.value])
    claim = SP345GammaClaim(value=Decimal("1"), source=SP345GammaSource.NORMATIVE_FALLBACK_SP345_5_2,
        scope=scope, source_reference="SP345.1325800.2017 consolidated text §5.2",
        source_field="5.2: absence of layer operating-coefficient data", source_revision="2017+Amendment1+Amendment2",
        authority_class="PROJECT_APPROVED_NORMATIVE_EXTRACT", clause_id="SP345:2017+AMD1+AMD2:5.2")
    return SP345GammaResolution(status="RESOLVED", claim=claim)


class SP345MethodIdentity(StrictProjectModel):
    document: Literal["SP 345.1325800.2017"] = "SP 345.1325800.2017"
    consolidated_revision: Literal["2017+Amendment1+Amendment2"] = "2017+Amendment1+Amendment2"
    amendment_1_order: Literal["664/pr"] = "664/pr"
    amendment_1_effective: Literal["2020-05-01"] = "2020-05-01"
    amendment_2_order: Literal["1117/pr"] = "1117/pr"
    amendment_2_effective: Literal["2023-01-24"] = "2023-01-24"
    official_identity_source: str = "https://protect.gost.ru/sp/details/c020552a-f741-47c3-a588-491af35f8b88"
    amendment_1_source: str = "https://protect.gost.ru/sp/changesdetails/a4b65c2b-82c0-40cf-a463-083c0561be01"
    amendment_2_source: str = "https://protect.gost.ru/sp/changesdetails/cbf2eee3-4a10-4f6e-9977-69f335e914fd"
    text_extract_sources: list[str] = Field(default_factory=lambda: [
        "https://base.garant.ru/406604193/",
        "https://meganorm.ru/mega_doc/norm/prikaz/13/izmenenie_N_2_k_sp_345_1325800_2017_zdaniya_zhilye_i.html",
        "https://nav.tn.ru/cloud/iblock/35d/35d43b1905f8bf403320d18880b40e81/SP-345.1325800.2017-_Izmenenie-_-2_.pdf",
    ])
    formulas_d1_d2: Literal[
        "lambda_A=lambda_0*(1+eta*w_A); lambda_B=lambda_0*(1+eta*w_B)"
    ] = "lambda_A=lambda_0*(1+eta*w_A); lambda_B=lambda_0*(1+eta*w_B)"
    formula_5_1a: Literal["R_s=(delta_s/lambda_s)*gamma_s_operating"] = "R_s=(delta_s/lambda_s)*gamma_s_operating"
    formula_5_1a_clause: Literal["5.2"] = "5.2"
    formula_5_1a_image_reference: str = "https://meganorm.ru/mega_doc/norm/metodika/0/sp_345_1325800_2017_svod_pravil_zdaniya_zhilye_i_/meganorm_521077.png"
    formula_5_1a_image_sha256: Literal["628bd41eeea68aa6c7238dc15d45358f1cd9e1b192e65351617fd5ed1e3a6dbe"] = "628bd41eeea68aa6c7238dc15d45358f1cd9e1b192e65351617fd5ed1e3a6dbe"
    lambda0_method: Literal["GOST 7076"] = "GOST 7076"
    moisture_reference: Literal["SP 50.13330.2012 Appendix T, or measurements where Table T lacks the material"] = (
        "SP 50.13330.2012 Appendix T, or measurements where Table T lacks the material")
    identity_digest: str = ""


class SP345EtaRecord(StrictProjectModel):
    record_id: str
    material_class: Literal[
        "MINERAL_WOOL", "CELLULAR_CONCRETE", "XPS", "EPS", "PIR_PUR"
    ]
    normative_description: str
    eta_per_percent: Decimal = Field(gt=0)
    units: Literal["1/%"] = "1/%"
    table_id: Literal["D.1"] = "D.1"
    normative_document: Literal["SP 345.1325800.2017"] = "SP 345.1325800.2017"
    authority_class: Literal["PROJECT_APPROVED_NORMATIVE_EXTRACT"] = "PROJECT_APPROVED_NORMATIVE_EXTRACT"
    source_references: list[str]
    record_digest: str

    @field_validator("eta_per_percent", mode="before")
    @classmethod
    def decimal_eta(cls, value):
        return value if isinstance(value, Decimal) else Decimal(str(value))


class SP345InsulationDataset(StrictProjectModel):
    dataset_id: Literal["SP345_2017_AMD1_AMD2_TABLE_D1_VERIFIED_SUBSET_V1"] = (
        "SP345_2017_AMD1_AMD2_TABLE_D1_VERIFIED_SUBSET_V1")
    method: SP345MethodIdentity
    table_id: Literal["D.1"] = "D.1"
    authority_class: Literal["PROJECT_APPROVED_NORMATIVE_EXTRACT"] = "PROJECT_APPROVED_NORMATIVE_EXTRACT"
    records: list[SP345EtaRecord]
    dataset_digest: str


class SP50LegacyAppendixTRecord(StrictProjectModel):
    record_id: str
    row_number: int
    material_description: str
    density_text: str
    lambda0_w_mk: Decimal
    moisture_a_percent: Decimal
    moisture_b_percent: Decimal
    lambda_a_w_mk: Decimal
    lambda_b_w_mk: Decimal
    lambda_units: Literal["W/(m·°C)"] = "W/(m·°C)"
    density_units: Literal["kg/m³"] = "kg/m³"
    moisture_units: Literal["%"] = "%"
    table_id: Literal["T.1"] = "T.1"
    revision: Literal["2012+Amendment1+Amendment2"] = "2012+Amendment1+Amendment2"
    authority_class: Literal["PROJECT_APPROVED_NORMATIVE_EXTRACT"] = "PROJECT_APPROVED_NORMATIVE_EXTRACT"
    source_references: list[str]
    record_digest: str

    @field_validator("lambda0_w_mk", "moisture_a_percent", "moisture_b_percent",
                     "lambda_a_w_mk", "lambda_b_w_mk", mode="before")
    @classmethod
    def parse_decimal(cls, value):
        return value if isinstance(value, Decimal) else Decimal(str(value))


class SP50LegacyAppendixTDataset(StrictProjectModel):
    dataset_id: Literal["SP50_2012_APPENDIX_T_AMENDMENTS_1_2"] = "SP50_2012_APPENDIX_T_AMENDMENTS_1_2"
    normative_document: Literal["SP 50.13330.2012"] = "SP 50.13330.2012"
    table_id: Literal["T.1"] = "T.1"
    amendments: tuple[str, str] = ("1", "2")
    official_identity_source: str
    text_carriers: list[str]
    records: list[SP50LegacyAppendixTRecord]
    authority_class: Literal["PROJECT_APPROVED_NORMATIVE_EXTRACT"] = "PROJECT_APPROVED_NORMATIVE_EXTRACT"
    dataset_digest: str


class SP50LegacyComparison(StrictProjectModel):
    legacy_table_row: str
    legacy_material: str
    legacy_density_kg_m3: str
    legacy_lambda0_w_mk: Decimal
    legacy_moisture_a_percent: Decimal
    legacy_moisture_b_percent: Decimal
    legacy_lambda_a_w_mk: Decimal
    legacy_lambda_b_w_mk: Decimal
    current_table_row: str
    current_material: str
    current_density_kg_m3: str
    current_lambda0_w_mk: Decimal
    current_moisture_a_percent: Decimal
    current_moisture_b_percent: Decimal
    current_lambda_a_w_mk: Decimal
    current_lambda_b_w_mk: Decimal
    comparison_status: Literal["CHANGED", "IDENTICAL_RELEVANT_FIELDS", "NO_DIRECT_COUNTERPART", "IDENTITY_AMBIGUOUS"] = "CHANGED"
    comparison_scope: Literal["AUDIT_ONLY_NOT_A_SUBSTITUTION"] = "AUDIT_ONLY_NOT_A_SUBSTITUTION"
    source_references: list[str]
    comparison_digest: str

    @field_validator("legacy_lambda0_w_mk", "legacy_moisture_a_percent", "legacy_moisture_b_percent",
                     "legacy_lambda_a_w_mk", "legacy_lambda_b_w_mk", "current_lambda0_w_mk",
                     "current_moisture_a_percent", "current_moisture_b_percent",
                     "current_lambda_a_w_mk", "current_lambda_b_w_mk", mode="before")
    @classmethod
    def decimal_fields(cls, value):
        return value if isinstance(value, Decimal) else Decimal(str(value))


SP345_IDENTITY = SP345MethodIdentity()
SP345_METHOD_DIGEST = _digest(SP345_IDENTITY.model_dump(mode="json", exclude={"identity_digest"}))
SP345_IDENTITY = SP345_IDENTITY.model_copy(update={"identity_digest": SP345_METHOD_DIGEST})

_ETA_TEXT_SOURCES = [
    "https://base.garant.ru/406604193/",
    "https://moodle.ivgpu.ru/pluginfile.php/302225/mod_resource/content/1/SP%20345.1325800.2017.%20%D0%A1%D0%B2%D0%BE%D0%B4%20%D0%BF%D1%80%D0%B0%D0%B2%D0%B8%D0%BB.%20%D0%97%D0%B4%D0%B0%D0%BD%D0%B8%D1%8F%20%D0%B6%D0%B8%D0%BB%D1%8B%D0%B5%20%D0%B8%20%D0%BE%D0%B1%D1%89%D0%B5%D1%81%D1%82%D0%B2%D0%B5%D0%BD%D0%BD%D1%8B%D0%B5.%20%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0%20%D0%BF%D1%80%D0%BE%D0%B5%D0%BA%D1%82%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D1%8F%20%D1%82%D0%B5%D0%BF%D0%BB%D0%BE%D0%B2%D0%BE%D0%B9%20%D0%B7%D0%B0%D1%89%D0%B8%D1%82%D1%8B%20%28%D1%83%D1%82%D0%B2.%20%D0%B8%20%D0%B2%D0%B2%D0%B5%D0%B4%D0%B5%D0%BD%20%D0%B2%20%D0%B4%D0%B5%D0%B9%D1%81%D1%82%D0%B2%D0%B8%D0%B5%20%D0%9F%D1%80%D0%B8%D0%BA%D0%B0%D0%B7%D0%BE%D0%BC%20%D0%9C%D0%B8%D0%BD%D1%81%D1%82%D1%80%D0%BE%D1%8F%20%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D0%B8%20%D0%BE%D1%82%2014.11.2.pdf",
]


def _eta_record(key: str, description: str, eta: str) -> SP345EtaRecord:
    body = {"record_id": f"SP345-2017-D1-{key}", "material_class": key,
            "normative_description": description, "eta_per_percent": eta,
            "units": "1/%", "table_id": "D.1",
            "normative_document": "SP 345.1325800.2017",
            "authority_class": "PROJECT_APPROVED_NORMATIVE_EXTRACT",
            "source_references": _ETA_TEXT_SOURCES}
    return SP345EtaRecord(**body, record_digest=_digest(body))


_eta_records = [
    _eta_record("MINERAL_WOOL", "Минеральная вата (из каменного или стеклянного волокна)", "0.04"),
    _eta_record("CELLULAR_CONCRETE", "Ячеистый бетон", "0.04"),
    _eta_record("XPS", "Экструдированный пенополистирол", "0.035"),
    _eta_record("EPS", "Пенополистирол", "0.03"),
    _eta_record("PIR_PUR", "Пенополиизоцианурат/пенополиуретан", "0.03"),
]
_dataset_body = {"dataset_id": "SP345_2017_AMD1_AMD2_TABLE_D1_VERIFIED_SUBSET_V1",
                 "method": SP345_IDENTITY.model_dump(mode="json"), "table_id": "D.1",
                 "authority_class": "PROJECT_APPROVED_NORMATIVE_EXTRACT",
                 "records": [r.model_dump(mode="json") for r in _eta_records]}
SP345_ETA_DATASET = SP345InsulationDataset(**_dataset_body, dataset_digest=_digest(_dataset_body))

_LEGACY_TABLE_SOURCE = "https://files.stroyinf.ru/Data2/1/4293799/4293799306.pdf"
_CURRENT_TABLE_SOURCE = "https://nav.tn.ru/cloud/iblock/2f5/2f5f0066dd005cc71ece191025e5daa2/SP_50.13330.2024.pdf"


def _comparison(legacy_row, legacy_material, density, legacy_values,
                current_row, current_material, current_density, current_values):
    same = (density == current_density and legacy_values == current_values)
    body = {"legacy_table_row": legacy_row, "legacy_material": legacy_material,
            "legacy_density_kg_m3": density,
            "legacy_lambda0_w_mk": legacy_values[0], "legacy_moisture_a_percent": legacy_values[1],
            "legacy_moisture_b_percent": legacy_values[2], "legacy_lambda_a_w_mk": legacy_values[3],
            "legacy_lambda_b_w_mk": legacy_values[4], "current_table_row": current_row,
            "current_material": current_material, "current_density_kg_m3": current_density,
            "current_lambda0_w_mk": current_values[0], "current_moisture_a_percent": current_values[1],
            "current_moisture_b_percent": current_values[2], "current_lambda_a_w_mk": current_values[3],
            "current_lambda_b_w_mk": current_values[4],
            "comparison_status": "IDENTICAL_RELEVANT_FIELDS" if same else "CHANGED",
            "comparison_scope": "AUDIT_ONLY_NOT_A_SUBSTITUTION",
            "source_references": [_LEGACY_TABLE_SOURCE, _CURRENT_TABLE_SOURCE]}
    return SP50LegacyComparison(**body, comparison_digest=_digest(body))


SP50_2012_2024_INSULATION_COMPARISONS = [
    _comparison("T.1-R1-AMD1-2", "Плиты из пенополистирола", "25-35",
        ("0.038", "2", "10", "0.040", "0.049"),
        "M.1-R1", "Плиты из пенополистирола", "25-35",
        ("0.038", "2", "10", "0.040", "0.049")),
    _comparison("T.1-R7-AMD1-2", "Плиты из экструзионного пенополистирола", "до 35",
        ("0.033", "1", "2", "0.034", "0.035"),
        "M.1-R7", "Плиты из экструзионного пенополистирола", "до 35",
        ("0.033", "1", "2", "0.034", "0.035")),
    _comparison("T.1-R8-AMD1-2", "Плиты из экструзионного пенополистирола", "35-45",
        ("0.034", "1", "2", "0.035", "0.036"),
        "M.1-R8", "То же", "35-45",
        ("0.034", "1", "2", "0.035", "0.036")),
]
# Preserve the earlier, unamended-2012 comparison as historical audit only.
# It is not an input to the dated SP345 dependency (which explicitly includes
# Amendments 1 and 2).
SP50_2012_ORIGINAL_VS_2024_INSULATION_COMPARISONS = [
    _comparison("T.1-R8-original", "Плиты из пенополистирола", "25-30",
        ("0.036", "2", "10", "0.038", "0.044"),
        "M.1-R1", "Плиты из пенополистирола", "25-35",
        ("0.038", "2", "10", "0.040", "0.049")),
    _comparison("T.1-R13-original", "Экструдированный пенополистирол", "25-33",
        ("0.029", "1", "2", "0.030", "0.031"),
        "M.1-R7", "Плиты из экструзионного пенополистирола", "до 35",
        ("0.033", "1", "2", "0.034", "0.035")),
]


class LegacyReferenceAudit(StrictProjectModel):
    sp345_text_dependency: Literal["SP50_2012_APPENDIX_T"] = "SP50_2012_APPENDIX_T"
    textual_status: Literal["DATED_REFERENCE_EXPLICITLY_RETAINED"] = "DATED_REFERENCE_EXPLICITLY_RETAINED"
    applicability_status: LegacyAppendixTStatus = LegacyAppendixTStatus.DATED_REFERENCE_EXPLICITLY_RETAINED
    reason: str = (
        "SP345 clause 2 recommends the stated approval-year edition for a replaced dated reference. Its insulation text cites SP50.2012; "
        "Amendment 2 explicitly updates the citation to SP50.2012 with Amendments 1 and 2. SP50.2024 does not replace this dated dependency."
    )
    dated_reference_clause: str = "SP345:2017+AMD1+AMD2:clause 2"
    amendment_2_intent_evidence: str = "SP50.2012 with Amendment 1 changed to SP50.2012 with Amendments 1 and 2; other cited standards were advanced to newer editions."
    official_sp345_reference: str = "https://protect.gost.ru/sp/changesdetails/cbf2eee3-4a10-4f6e-9977-69f335e914fd"
    official_sp50_2012_status: str = "https://protect.gost.ru/sp/details/1e4f6a14-4010-46ef-a0c3-76189b93fa01"
    current_sp50_replacement: str = "https://protect.gost.ru/sp/details/5081dae9-9ee9-455f-80e8-d093d495361c"
    audit_digest: str = ""


SP345_LEGACY_REFERENCE_AUDIT = LegacyReferenceAudit()
SP345_LEGACY_REFERENCE_AUDIT = SP345_LEGACY_REFERENCE_AUDIT.model_copy(update={
    "audit_digest": _digest(SP345_LEGACY_REFERENCE_AUDIT.model_dump(mode="json", exclude={"audit_digest"}))})


_APPENDIX_T_CARRIERS = [
    "https://buildingbook.ru/sp-50-13330-2012.html",
    "https://kritery.ru/storage/files/5.EE/35-%D0%A1%D0%9F_50.13330.2012.pdf",
    "https://nav.tn.ru/upload/directions/SNiP-23-02-2003.-Teplovaya-zaschita-zdanii.pdf",
]
_LEGACY_ROWS = [
    (1, "Плиты из пенополистирола", "25–35", ".038", "2", "10", ".040", ".049"),
    (2, "Плиты из пенополистирола (то же)", "17–25", ".039", "2", "10", ".041", ".051"),
    (3, "Плиты из пенополистирола (то же)", "13–17", ".041", "2", "10", ".043", ".053"),
    (4, "Плиты из пенополистирола (то же)", "10–13", ".044", "2", "10", ".047", ".057"),
    (5, "Плиты из пенополистирола (то же)", "до 10", ".055", "2", "10", ".058", ".072"),
    (6, "Плиты из пенополистирола фасадные", "16–18.5", ".037", "2", "10", ".039", ".048"),
    (7, "Плиты из экструзионного пенополистирола", "до 35", ".033", "1", "2", ".034", ".035"),
    (8, "Плиты из экструзионного пенополистирола (то же)", "35–45", ".034", "1", "2", ".035", ".036"),
]
def _legacy_record(row):
    n, description, density, lam0, wa, wb, lama, lamb = row
    body = {"record_id": f"SP50-2012-T1-R{n}-AMD1-AMD2", "row_number": n,
        "material_description": description, "density_text": density,
        "lambda0_w_mk": lam0, "moisture_a_percent": wa, "moisture_b_percent": wb,
        "lambda_a_w_mk": lama, "lambda_b_w_mk": lamb,
        "lambda_units": "W/(m·°C)", "density_units": "kg/m³", "moisture_units": "%",
        "table_id": "T.1", "revision": "2012+Amendment1+Amendment2",
        "authority_class": "PROJECT_APPROVED_NORMATIVE_EXTRACT",
        "source_references": _APPENDIX_T_CARRIERS}
    return SP50LegacyAppendixTRecord(**body, record_digest=_digest(body))
_legacy_records = [_legacy_record(row) for row in _LEGACY_ROWS]
_legacy_body = {"dataset_id": "SP50_2012_APPENDIX_T_AMENDMENTS_1_2",
    "normative_document": "SP 50.13330.2012", "table_id": "T.1", "amendments": ("1", "2"),
    "official_identity_source": "https://protect.gost.ru/sp/details/1e4f6a14-4010-46ef-a0c3-76189b93fa01",
    "text_carriers": _APPENDIX_T_CARRIERS,
    "authority_class": "PROJECT_APPROVED_NORMATIVE_EXTRACT",
    "records": [r.model_dump(mode="json") for r in _legacy_records]}
SP50_2012_APPENDIX_T_DATASET = SP50LegacyAppendixTDataset(**_legacy_body,
    dataset_digest=_digest(_legacy_body))


class SP345InsulationRequest(StrictProjectModel):
    material_record_id: str = Field(min_length=1)
    operating_condition: EnvelopeOperatingCondition = EnvelopeOperatingCondition.UNRESOLVED
    operating_condition_source_reference: str | None = None
    operating_condition_source_field: str | None = None
    operating_condition_authority_class: str | None = None
    lambda0_claim_reference: str | None = None
    source_revision: str | None = None
    construction_scope: SP345ConstructionScope | None = None
    gamma_project_or_test_claim: SP345GammaClaim | None = None
    gamma_appendix_e_claim: SP345GammaClaim | None = None
    lambda_route: Literal["DIRECT_REFERENCE", "APPENDIX_D_CALCULATED"] | None = None

    @field_validator("operating_condition", mode="before")
    @classmethod
    def parse_operating_condition(cls, value):
        return value if isinstance(value, EnvelopeOperatingCondition) else EnvelopeOperatingCondition(value)

    @field_validator("construction_scope", mode="before")
    @classmethod
    def parse_construction_scope(cls, value):
        return None if value is None else (value if isinstance(value, SP345ConstructionScope)
                                           else SP345ConstructionScope(value))


class SP345InsulationResult(StrictProjectModel):
    status: Literal["OPERATING_CONDITION_REQUIRED", "SP345_GAMMA_SCOPE_REQUIRED",
                    "APPENDIX_E_RESULT_REQUIRED", "LAMBDA0_SOURCE_REQUIRED",
                    "LAMBDA_ROUTE_SELECTION_REQUIRED", "RESOLVED"]
    material_record_id: str
    operating_condition: EnvelopeOperatingCondition
    design_lambda_w_mk: Decimal | None = None
    direct_reference_lambda_w_mk: Decimal | None = None
    appendix_d_lambda_w_mk: Decimal | None = None
    authority_class: str | None = None
    legacy_record: SP50LegacyAppendixTRecord | None = None
    gamma: SP345GammaClaim | None = None
    lambda_route: Literal["DIRECT_REFERENCE", "APPENDIX_D_CALCULATED"] | None = None
    route_difference_w_mk: Decimal | None = None
    route_comparison: Literal["ONLY_DIRECT_AVAILABLE", "ONLY_CALCULATED_AVAILABLE",
                              "BOTH_EXACT", "BOTH_DIFFERENCE_REPORTED_NO_TOLERANCE"] | None = None
    provenance: dict[str, str] = Field(default_factory=dict)
    dependency_digest: str
    diagnostics: list[str]


def resolve_sp345_insulation_property(request: SP345InsulationRequest) -> SP345InsulationResult:
    """Resolve exact Appendix-T row and requested lambda path, without substitution."""
    payload = {"request": request.model_dump(mode="json"),
               "method_digest": SP345_METHOD_DIGEST,
               "eta_dataset_digest": SP345_ETA_DATASET.dataset_digest,
               "legacy_dataset_digest": SP50_2012_APPENDIX_T_DATASET.dataset_digest,
               "legacy_audit_digest": SP345_LEGACY_REFERENCE_AUDIT.audit_digest,
               "sp50_2024_dataset_is_not_substitute": True}
    def result(status, diagnostics, **kwargs):
        return SP345InsulationResult(status=status, material_record_id=request.material_record_id,
            operating_condition=request.operating_condition, dependency_digest=_digest(payload),
            diagnostics=diagnostics, **kwargs)
    if request.operating_condition == EnvelopeOperatingCondition.UNRESOLVED:
        return result("OPERATING_CONDITION_REQUIRED", ["ENVELOPE_OPERATING_CONDITION_RESULT_REQUIRED"])
    if (not request.operating_condition_source_reference or not request.operating_condition_source_field
            or request.operating_condition_authority_class not in {
                "PROJECT_AUTHORITATIVE", "NORMATIVE_AUTHORITATIVE", "PROJECT_APPROVED_NORMATIVE_EXTRACT",
                "DERIVED_FROM_AUTHORITATIVE_INPUTS", "TEST_ONLY",
            }):
        return result("OPERATING_CONDITION_REQUIRED", ["OPERATING_CONDITION_PROVENANCE_REQUIRED"])
    try:
        row_number = int(request.material_record_id.rsplit("R", 1)[1])
    except (ValueError, IndexError):
        return result("SP345_GAMMA_SCOPE_REQUIRED", ["EXACT_SUPPORTED_INSULATION_RECORD_REQUIRED"])
    row = next((item for item in SP50_2012_APPENDIX_T_DATASET.records if item.row_number == row_number), None)
    if row is None:
        return result("SP345_GAMMA_SCOPE_REQUIRED", ["SP50_2012_APPENDIX_T_RECORD_UNAVAILABLE"])
    if request.construction_scope is None:
        return result("SP345_GAMMA_SCOPE_REQUIRED", ["SP345_CONSTRUCTION_SCOPE_REQUIRED"], legacy_record=row)
    gamma_resolution = resolve_sp345_gamma(request.construction_scope,
        project_or_test=request.gamma_project_or_test_claim, appendix_e=request.gamma_appendix_e_claim)
    if gamma_resolution.status != "RESOLVED" or gamma_resolution.claim is None:
        return result("APPENDIX_E_RESULT_REQUIRED", gamma_resolution.diagnostics, legacy_record=row)
    direct = row.lambda_a_w_mk if request.operating_condition == EnvelopeOperatingCondition.A else row.lambda_b_w_mk
    eta_class = "EPS" if row.row_number <= 6 else "XPS"
    eta = next(r for r in SP345_ETA_DATASET.records if r.material_class == eta_class)
    calculated = row.lambda0_w_mk * (Decimal(1) + eta.eta_per_percent *
        (row.moisture_a_percent if request.operating_condition == EnvelopeOperatingCondition.A
         else row.moisture_b_percent))
    if request.lambda_route is None:
        return result("LAMBDA_ROUTE_SELECTION_REQUIRED", ["DIRECT_AND_APPENDIX_D_ROUTES_AVAILABLE; EXPLICIT_ROUTE_SELECTION_REQUIRED"],
            legacy_record=row, gamma=gamma_resolution.claim, direct_reference_lambda_w_mk=direct,
            appendix_d_lambda_w_mk=calculated, route_comparison=("BOTH_EXACT" if direct == calculated
                else "BOTH_DIFFERENCE_REPORTED_NO_TOLERANCE"), route_difference_w_mk=calculated-direct)
    # The exact dated Appendix-T record is itself the sourced lambda_0 input
    # for D.1/D.2; no parallel free-form claim is needed for this route.
    chosen = direct if request.lambda_route == "DIRECT_REFERENCE" else calculated
    comparison = "BOTH_EXACT" if direct == calculated else "BOTH_DIFFERENCE_REPORTED_NO_TOLERANCE"
    return result("RESOLVED", ["SP345_FORMULA_5_1A_APPLIES", "DATED_SP50_2012_SOURCE_USED"],
        legacy_record=row, gamma=gamma_resolution.claim, lambda_route=request.lambda_route,
        design_lambda_w_mk=chosen, direct_reference_lambda_w_mk=direct,
        appendix_d_lambda_w_mk=calculated,
        route_difference_w_mk=calculated-direct, route_comparison=comparison,
        authority_class="PROJECT_APPROVED_NORMATIVE_EXTRACT",
        provenance={"lambda": f"{row.record_id}; row digest {row.record_digest}; selected={request.lambda_route}",
                    "gamma": f"{gamma_resolution.claim.source.value}; {gamma_resolution.claim.source_reference}; {gamma_resolution.claim.digest}"})


__all__ = ["LegacyAppendixTStatus", "SP345MethodIdentity", "SP345EtaRecord",
    "SP345InsulationDataset", "SP345InsulationRequest", "SP345InsulationResult",
    "SP345GammaSource", "SP345ConstructionScope", "SP345GammaClaim", "SP345GammaResolution",
    "resolve_sp345_gamma", "SP50LegacyAppendixTRecord", "SP50LegacyAppendixTDataset",
    "SP50_2012_APPENDIX_T_DATASET", "SP345_ETA_DATASET", "SP345_LEGACY_REFERENCE_AUDIT", "SP345_METHOD_DIGEST",
    "SP50LegacyComparison", "SP50_2012_2024_INSULATION_COMPARISONS",
    "SP50_2012_ORIGINAL_VS_2024_INSULATION_COMPARISONS",
    "resolve_sp345_insulation_property"]

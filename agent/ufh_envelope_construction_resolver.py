"""Provenance-first envelope assembly resolution; not a room heat-loss engine."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from agent.project_models import StrictProjectModel
from agent.ufh_project_engineering_profile_authoring import AuthoringProvenance


def _digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise ValueError("DECIMAL_VALUE_REQUIRED") from error
    if not result.is_finite():
        raise ValueError("FINITE_DECIMAL_REQUIRED")
    return result


class ConstructionBoundaryKind(str, Enum):
    EXTERIOR_WALL = "EXTERIOR_WALL"
    INTERIOR_WALL_DIFFERENT_ZONE = "INTERIOR_WALL_DIFFERENT_ZONE"
    FLOOR_SLAB = "FLOOR_SLAB"
    CEILING_ROOF = "CEILING_ROOF"
    WINDOW = "WINDOW"
    EXTERIOR_DOOR = "EXTERIOR_DOOR"
    OTHER_OPENING = "OTHER_OPENING"


class ConstructionSourceMode(str, Enum):
    PROJECT_ASSEMBLY = "PROJECT_ASSEMBLY"
    CATALOG_SYSTEM = "CATALOG_SYSTEM"
    LAYERED_CUSTOM_ASSEMBLY = "LAYERED_CUSTOM_ASSEMBLY"
    EXPLICIT_U_VALUE_WITH_PROVENANCE = "EXPLICIT_U_VALUE_WITH_PROVENANCE"
    UNKNOWN = "UNKNOWN"


class ConstructionLayer(StrictProjectModel):
    material_product_id: str = Field(min_length=1, max_length=256)
    thickness_m: Decimal
    lambda_w_mk: Decimal | None = None
    lambda_provenance: AuthoringProvenance | None = None
    property_condition: str | None = Field(default=None, max_length=256)
    material_record_id: str | None = Field(default=None, max_length=160)
    material_resolution_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    condition_source_reference: str | None = None
    condition_source_field: str | None = None
    condition_authority_class: str | None = None
    resistance_method: Literal["GENERIC_D_OVER_LAMBDA", "SP345_FORMULA_5_1A"] = "GENERIC_D_OVER_LAMBDA"
    layer_operating_coefficient: Decimal | None = None
    layer_coefficient_provenance: AuthoringProvenance | None = None

    @field_validator("thickness_m", "lambda_w_mk", "layer_operating_coefficient", mode="before")
    @classmethod
    def decimal_values(cls, value):
        return _decimal(value)

    @model_validator(mode="after")
    def sourced_positive_properties(self):
        if self.thickness_m <= 0:
            raise ValueError("LAYER_THICKNESS_MUST_BE_POSITIVE")
        if (self.lambda_w_mk is None) != (self.lambda_provenance is None):
            raise ValueError("LAMBDA_VALUE_AND_PROVENANCE_MUST_BE_PAIRED")
        if self.lambda_w_mk is not None:
            if self.lambda_w_mk <= 0:
                raise ValueError("LAMBDA_MUST_BE_POSITIVE")
            if self.lambda_provenance.units != "W/(m*K)":
                raise ValueError("LAMBDA_UNIT_INVALID")
            if self.lambda_provenance.source_type == "test_only":
                return self
            if self.lambda_provenance.source_type not in {
                "building_construction_data", "product_document", "normative_source",
                "project_approved_normative_extract", "project_data", "project_decision",
            }:
                raise ValueError("LAMBDA_SOURCE_NOT_BINDABLE")
        if self.resistance_method == "SP345_FORMULA_5_1A":
            if self.layer_operating_coefficient is None or self.layer_coefficient_provenance is None:
                raise ValueError("SP345_LAYER_COEFFICIENT_PROVENANCE_REQUIRED")
            if self.layer_operating_coefficient <= 0:
                raise ValueError("SP345_LAYER_COEFFICIENT_MUST_BE_POSITIVE")
            if self.layer_coefficient_provenance.units != "1":
                raise ValueError("SP345_LAYER_COEFFICIENT_UNIT_INVALID")
            if self.layer_coefficient_provenance.source_type not in {
                "project_approved_normative_extract", "normative_source", "building_construction_data", "test_only",
            }:
                raise ValueError("SP345_LAYER_COEFFICIENT_SOURCE_NOT_BINDABLE")
        elif self.layer_operating_coefficient is not None or self.layer_coefficient_provenance is not None:
            raise ValueError("LAYER_COEFFICIENT_REQUIRES_SP345_METHOD")
        if self.material_record_id is not None and self.property_condition in {"A", "B"}:
            if not all((self.condition_source_reference,
                        self.condition_source_field,
                        self.condition_authority_class)):
                raise ValueError("OPERATING_CONDITION_PROVENANCE_REQUIRED")
        return self


class ExplicitUValue(StrictProjectModel):
    value_w_m2k: Decimal
    provenance: AuthoringProvenance

    @field_validator("value_w_m2k", mode="before")
    @classmethod
    def decimal_value(cls, value):
        return _decimal(value)

    @model_validator(mode="after")
    def valid_sourced_u(self):
        if self.value_w_m2k <= 0:
            raise ValueError("U_VALUE_MUST_BE_POSITIVE")
        if self.provenance.units != "W/(m2*K)":
            raise ValueError("U_VALUE_UNIT_INVALID")
        if self.provenance.source_type == "test_only":
            return self
        if self.provenance.source_type not in {
            "building_construction_data", "product_document", "normative_source",
            "project_approved_normative_extract", "project_data", "project_decision",
        }:
            raise ValueError("U_VALUE_SOURCE_NOT_BINDABLE")
        return self


class SurfaceResistanceMethod(StrictProjectModel):
    """Explicit sourced method input; no bundled default values in V1."""
    method_id: str = Field(min_length=1, max_length=160)
    method_revision: str = Field(min_length=1, max_length=80)
    r_si_m2k_w: Decimal
    r_se_m2k_w: Decimal
    provenance: AuthoringProvenance

    @field_validator("r_si_m2k_w", "r_se_m2k_w", mode="before")
    @classmethod
    def decimal_values(cls, value):
        return _decimal(value)

    @model_validator(mode="after")
    def sourced_positive_resistances(self):
        if min(self.r_si_m2k_w, self.r_se_m2k_w) <= 0:
            raise ValueError("SURFACE_RESISTANCES_MUST_BE_POSITIVE")
        if self.provenance.units != "m2*K/W":
            raise ValueError("SURFACE_RESISTANCE_UNIT_INVALID")
        if self.provenance.source_type not in {
            "normative_source", "project_approved_normative_extract", "test_only",
        }:
            raise ValueError("SURFACE_RESISTANCE_NORMATIVE_SOURCE_REQUIRED")
        return self


class EnvelopeAssemblyDefinition(StrictProjectModel):
    assembly_id: str = Field(min_length=1, max_length=160)
    boundary_kind: ConstructionBoundaryKind
    layers: list[ConstructionLayer] = Field(default_factory=list)
    explicit_u_value: ExplicitUValue | None = None
    source_reference: str = Field(min_length=1, max_length=512)
    source_field: str = Field(min_length=1, max_length=256)
    source_revision: str | None = Field(default=None, max_length=128)
    # Exact Table 4/6 applicability is explicit; boundary kind alone cannot
    # choose an external coefficient. Kept JSON-shaped here to avoid a module cycle.
    surface_applicability: dict[str, Any] | None = None

    @field_validator("boundary_kind", mode="before")
    @classmethod
    def parse_boundary_kind(cls, value):
        return value if isinstance(value, ConstructionBoundaryKind) else ConstructionBoundaryKind(value)

    @model_validator(mode="after")
    def valid_boundary_representation(self):
        is_opening = self.boundary_kind in {
            ConstructionBoundaryKind.WINDOW, ConstructionBoundaryKind.EXTERIOR_DOOR,
            ConstructionBoundaryKind.OTHER_OPENING,
        }
        if is_opening and self.layers:
            raise ValueError("GENERIC_OPENING_INFERENCE_PROHIBITED")
        if not self.layers and self.explicit_u_value is None:
            raise ValueError("ASSEMBLY_HAS_NO_SOURCED_CONSTRUCTION_DATA")
        return self


class EnvelopeConstructionSubmission(StrictProjectModel):
    source_mode: ConstructionSourceMode
    source_reference: str = Field(min_length=1, max_length=512)
    source_field: str = Field(min_length=1, max_length=256)
    source_revision: str | None = Field(default=None, max_length=128)
    assemblies: list[EnvelopeAssemblyDefinition] = Field(default_factory=list)

    @field_validator("source_mode", mode="before")
    @classmethod
    def parse_source_mode(cls, value):
        return value if isinstance(value, ConstructionSourceMode) else ConstructionSourceMode(value)

    @model_validator(mode="after")
    def coherent_submission(self):
        if self.source_mode == ConstructionSourceMode.UNKNOWN:
            if self.assemblies:
                raise ValueError("UNKNOWN_SOURCE_CANNOT_CARRY_ASSEMBLIES")
            return self
        if self.source_mode in {ConstructionSourceMode.PROJECT_ASSEMBLY,
                                ConstructionSourceMode.CATALOG_SYSTEM}:
            if self.assemblies:
                raise ValueError("UNRESOLVED_EXTERNAL_SOURCE_CANNOT_CLAIM_ASSEMBLIES")
            return self
        if not self.assemblies:
            raise ValueError("ASSEMBLY_DATA_REQUIRED")
        if len({item.assembly_id for item in self.assemblies}) != len(self.assemblies):
            raise ValueError("DUPLICATE_ASSEMBLY_ID")
        if self.source_mode == ConstructionSourceMode.LAYERED_CUSTOM_ASSEMBLY and any(
            not item.layers for item in self.assemblies
        ):
            raise ValueError("LAYERED_ASSEMBLY_LAYERS_REQUIRED")
        if self.source_mode == ConstructionSourceMode.EXPLICIT_U_VALUE_WITH_PROVENANCE and any(
            item.explicit_u_value is None for item in self.assemblies
        ):
            raise ValueError("EXPLICIT_U_VALUE_REQUIRED")
        return self


class EnvelopeConstructionAssembly(StrictProjectModel):
    assembly_id: str
    boundary_kind: ConstructionBoundaryKind
    source_mode: ConstructionSourceMode
    layers: list[ConstructionLayer]
    layered_resistance_m2k_w: Decimal | None
    total_resistance_m2k_w: Decimal | None
    u_value_w_m2k: Decimal | None
    explicit_u_value: ExplicitUValue | None
    calculation_status: Literal[
        "LAYERED_RESISTANCE_RESOLVED", "NORMATIVE_SOURCE_REQUIRED",
        "MATERIAL_PROPERTY_REQUIRED", "EXPLICIT_U_VALUE_RESOLVED",
        "SOURCE_VALUE_CONFLICT", "SOURCE_UNAVAILABLE",
    ]
    resistance_scope: Literal["HOMOGENEOUS_SECTION_CONDITIONAL_RESISTANCE"] | None = None
    unresolved_dependencies: list[str]
    provenance_references: list[str]
    dependency_digest: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("layered_resistance_m2k_w", "total_resistance_m2k_w", "u_value_w_m2k", mode="before")
    @classmethod
    def decimal_values(cls, value):
        return _decimal(value)


class EnvelopeConstructionBundle(StrictProjectModel):
    schema_version: Literal["1.0"] = "1.0"
    source_mode: ConstructionSourceMode
    assemblies: list[EnvelopeConstructionAssembly]
    comparison_policy: Literal["EXACT_DECIMAL_MATCH_V1"] = "EXACT_DECIMAL_MATCH_V1"
    dependency_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


def calculate_assembly(
    definition: EnvelopeAssemblyDefinition,
    source_mode: ConstructionSourceMode,
    *,
    surface_method: SurfaceResistanceMethod | None = None,
) -> EnvelopeConstructionAssembly:
    """Calculate sourced layer resistance and, only with sourced surfaces, R/U."""
    payload = {
        "definition": definition.model_dump(mode="json"),
        "source_mode": source_mode.value,
        "surface_method": surface_method.model_dump(mode="json") if surface_method else None,
    }
    dep = _digest(payload)
    provenance_refs = sorted({
        layer.lambda_provenance.source_reference
        for layer in definition.layers if layer.lambda_provenance is not None
    } | ({definition.explicit_u_value.provenance.source_reference}
         if definition.explicit_u_value is not None else set())
      | {layer.layer_coefficient_provenance.source_reference for layer in definition.layers
         if layer.layer_coefficient_provenance is not None}
      | ({surface_method.provenance.source_reference} if surface_method else set()))
    if not definition.layers:
        return EnvelopeConstructionAssembly(
            assembly_id=definition.assembly_id, boundary_kind=definition.boundary_kind,
            source_mode=source_mode, layers=[], layered_resistance_m2k_w=None,
            total_resistance_m2k_w=None,
            u_value_w_m2k=(definition.explicit_u_value.value_w_m2k
                           if definition.explicit_u_value else None),
            explicit_u_value=definition.explicit_u_value,
            calculation_status=("EXPLICIT_U_VALUE_RESOLVED" if definition.explicit_u_value
                                else "MATERIAL_PROPERTY_REQUIRED"),
            resistance_scope=None,
            unresolved_dependencies=([] if definition.explicit_u_value else
                                     ["MATERIAL_THERMAL_PROPERTY_RESOLVER"]),
            provenance_references=provenance_refs, dependency_digest=dep,
        )
    if any(layer.lambda_w_mk is None for layer in definition.layers):
        return EnvelopeConstructionAssembly(
            assembly_id=definition.assembly_id, boundary_kind=definition.boundary_kind,
            source_mode=source_mode, layers=definition.layers,
            layered_resistance_m2k_w=None, total_resistance_m2k_w=None,
            u_value_w_m2k=(definition.explicit_u_value.value_w_m2k
                           if definition.explicit_u_value else None),
            explicit_u_value=definition.explicit_u_value,
            calculation_status=("EXPLICIT_U_VALUE_RESOLVED" if definition.explicit_u_value
                                else "MATERIAL_PROPERTY_REQUIRED"),
            resistance_scope=None,
            unresolved_dependencies=(
                (["MATERIAL_THERMAL_PROPERTY_RESOLVER"] if definition.layers else [])
                if definition.explicit_u_value else ["MATERIAL_THERMAL_PROPERTY_RESOLVER"]
            ),
            provenance_references=provenance_refs, dependency_digest=dep,
        )

    r_layers = sum(((layer.thickness_m / layer.lambda_w_mk) *
                    (layer.layer_operating_coefficient if layer.resistance_method == "SP345_FORMULA_5_1A"
                     else Decimal(1))
                    for layer in definition.layers if layer.lambda_w_mk is not None), Decimal(0))
    r_total = None
    calculated_u = None
    if surface_method is not None:
        r_total = surface_method.r_si_m2k_w + r_layers + surface_method.r_se_m2k_w
        calculated_u = Decimal(1) / r_total
    if definition.explicit_u_value is not None and calculated_u is not None:
        if definition.explicit_u_value.value_w_m2k != calculated_u:
            status = "SOURCE_VALUE_CONFLICT"
            unresolved = ["SOURCE_VALUE_CONFLICT"]
            u_value = None
        else:
            status = "LAYERED_RESISTANCE_RESOLVED"
            unresolved = []
            u_value = calculated_u
    elif definition.explicit_u_value is not None:
        status = "EXPLICIT_U_VALUE_RESOLVED"
        unresolved = ([] if definition.boundary_kind not in {
            ConstructionBoundaryKind.EXTERIOR_WALL, ConstructionBoundaryKind.FLOOR_SLAB,
            ConstructionBoundaryKind.CEILING_ROOF,
        } else ["THERMAL_BRIDGES_REMAIN_SEPARATE"])
        u_value = definition.explicit_u_value.value_w_m2k
    elif calculated_u is not None:
        status = "LAYERED_RESISTANCE_RESOLVED"
        unresolved = ([] if definition.boundary_kind not in {
            ConstructionBoundaryKind.EXTERIOR_WALL, ConstructionBoundaryKind.FLOOR_SLAB,
            ConstructionBoundaryKind.CEILING_ROOF,
        } else ["THERMAL_BRIDGES_REMAIN_SEPARATE"])
        u_value = calculated_u
    else:
        status = "NORMATIVE_SOURCE_REQUIRED"
        unresolved = ["NORMATIVE_SURFACE_RESISTANCE_SOURCE_REQUIRED"]
        if definition.boundary_kind in {
            ConstructionBoundaryKind.EXTERIOR_WALL, ConstructionBoundaryKind.FLOOR_SLAB,
            ConstructionBoundaryKind.CEILING_ROOF,
        }:
            unresolved.append("THERMAL_BRIDGES_REMAIN_SEPARATE")
        u_value = None
    return EnvelopeConstructionAssembly(
        assembly_id=definition.assembly_id, boundary_kind=definition.boundary_kind,
        source_mode=source_mode, layers=definition.layers,
        layered_resistance_m2k_w=r_layers, total_resistance_m2k_w=r_total,
        u_value_w_m2k=u_value, explicit_u_value=definition.explicit_u_value,
        calculation_status=status,
        resistance_scope=("HOMOGENEOUS_SECTION_CONDITIONAL_RESISTANCE"
                          if calculated_u is not None else None),
        unresolved_dependencies=unresolved,
        provenance_references=provenance_refs, dependency_digest=dep,
    )


def calculate_bundle(
    submission: EnvelopeConstructionSubmission,
    *,
    surface_methods: dict[str, SurfaceResistanceMethod] | None = None,
) -> EnvelopeConstructionBundle:
    if submission.source_mode in {ConstructionSourceMode.PROJECT_ASSEMBLY,
                                  ConstructionSourceMode.CATALOG_SYSTEM}:
        raise ValueError("SOURCE_UNAVAILABLE")
    if submission.source_mode == ConstructionSourceMode.UNKNOWN:
        raise ValueError("INSUFFICIENT_INPUT")
    methods = surface_methods or {}
    assemblies = [calculate_assembly(item, submission.source_mode,
                                     surface_method=methods.get(item.assembly_id))
                  for item in submission.assemblies]
    body = {"source_mode": submission.source_mode.value,
            "assemblies": [item.model_dump(mode="json") for item in assemblies],
            "comparison_policy": "EXACT_DECIMAL_MATCH_V1"}
    return EnvelopeConstructionBundle(source_mode=submission.source_mode,
                                      assemblies=assemblies, dependency_digest=_digest(body))


def make_envelope_construction_request(
    project_id, room_id, project_source_digest, decisions, normative_profile: str,
    operating_condition_dependency: str | None = None,
):
    from agent.ufh_questionnaire_resolver_contract import make_resolver_request

    return make_resolver_request(
        "BUILDING_CONSTRUCTION_RESOLVER", project_id, room_id,
        project_source_digest, decisions,
        {"construction_bundle": "V1", "normative_profile": normative_profile,
         "operating_condition_dependency": operating_condition_dependency or "UNRESOLVED"},
    )


def resolve_envelope_construction_submission(
    request,
    state,
):
    """Return an existing ResolverResult envelope; bindings still use common handoff."""
    from agent.ufh_questionnaire_resolver_contract import ResolvedValue, ResolverResult
    decisions = state.decisions
    root, source = decisions.get("envelope"), decisions.get("envelope.source")
    if root is None or source is None:
        return ResolverResult(resolver_request_id=request.resolver_request_id,
                              status="INSUFFICIENT_INPUT",
                              dependency_digest=request.dependency_digest,
                              diagnostics=["CONSTRUCTION_METHOD_AND_SOURCE_REQUIRED"])
    mode_map = {
        "PROJECT_ASSEMBLY": ConstructionSourceMode.PROJECT_ASSEMBLY,
        "PROJECT_CONSTRUCTION": ConstructionSourceMode.PROJECT_ASSEMBLY,
        "CATALOG_SYSTEM": ConstructionSourceMode.CATALOG_SYSTEM,
        "LAYERS": ConstructionSourceMode.LAYERED_CUSTOM_ASSEMBLY,
        "LAYERED_CUSTOM_ASSEMBLY": ConstructionSourceMode.LAYERED_CUSTOM_ASSEMBLY,
        "EXPLICIT_U_VALUE_WITH_PROVENANCE": ConstructionSourceMode.EXPLICIT_U_VALUE_WITH_PROVENANCE,
        "APPROVED_BASELINE": ConstructionSourceMode.PROJECT_ASSEMBLY,
        "UNKNOWN": ConstructionSourceMode.UNKNOWN,
    }
    raw_mode = str(root.value)
    mode = mode_map.get(raw_mode)
    if mode is None:
        return ResolverResult(resolver_request_id=request.resolver_request_id,
                              status="OUT_OF_DOMAIN",
                              dependency_digest=request.dependency_digest,
                              diagnostics=["CONSTRUCTION_SOURCE_MODE_UNKNOWN"])
    if mode == ConstructionSourceMode.PROJECT_ASSEMBLY:
        return ResolverResult(resolver_request_id=request.resolver_request_id,
                              status="SOURCE_UNAVAILABLE",
                              dependency_digest=request.dependency_digest,
                              diagnostics=["PROJECT_ASSEMBLY_SOURCE_ADAPTER_NOT_AVAILABLE"])
    if mode == ConstructionSourceMode.CATALOG_SYSTEM:
        return ResolverResult(resolver_request_id=request.resolver_request_id,
                              status="SOURCE_UNAVAILABLE",
                              dependency_digest=request.dependency_digest,
                              diagnostics=["APPROVED_CONSTRUCTION_CATALOG_NOT_AVAILABLE"])
    raw = source.value
    if not isinstance(raw, dict):
        return ResolverResult(resolver_request_id=request.resolver_request_id,
                              status="INSUFFICIENT_INPUT",
                              dependency_digest=request.dependency_digest,
                              diagnostics=["STRUCTURED_CONSTRUCTION_SOURCE_REQUIRED"])
    # Resolver enrichment must never mutate the questionnaire decision that
    # was hashed into the request. In-place edits make the request stale before
    # its ordinary authoring handoff can verify the same dependency digest.
    raw = deepcopy(raw)
    material_diagnostics: list[str] = []
    material_results = []
    for assembly_payload in raw.get("assemblies", []):
        assembly_payload["layers"] = list(assembly_payload.get("layers", []))
        for layer_payload in assembly_payload["layers"]:
            query_payload = layer_payload.pop("material_query", None)
            if query_payload is None:
                continue
            authored_condition = state.authoring.envelope_constructions.get("operating_condition")
            if (authored_condition is not None and authored_condition.status == "DERIVED"
                    and assembly_payload.get("boundary_kind") in {
                        "EXTERIOR_WALL", "WINDOW", "EXTERIOR_DOOR"}):
                provenance = authored_condition.provenance
                query_payload.update({
                    "operating_condition": authored_condition.value,
                    "operating_condition_source_reference": provenance.source_reference,
                    "operating_condition_source_field": provenance.source_field,
                    "operating_condition_authority_class": "PROJECT_APPROVED_NORMATIVE_EXTRACT",
                })
            from agent.ufh_material_thermal_property_resolver import (
                MaterialResolutionRequest, construction_layer_from_resolution,
                resolve_material_thermal_property,
            )
            try:
                query = MaterialResolutionRequest.model_validate({
                    **query_payload,
                    "material_product_id": layer_payload["material_product_id"],
                    "allow_test_only_condition": False,
                })
                property_result = resolve_material_thermal_property(query)
            except ValueError as error:
                code = str(error).splitlines()[0][:160]
                return ResolverResult(resolver_request_id=request.resolver_request_id,
                    status="INSUFFICIENT_INPUT", dependency_digest=request.dependency_digest,
                    diagnostics=["MATERIAL_PROPERTY_REQUEST_INVALID", code])
            material_results.append(property_result)
            if property_result.status == "RESOLVED":
                resolved_layer = construction_layer_from_resolution(
                    layer_payload["material_product_id"], layer_payload["thickness_m"],
                    property_result)
                layer_payload.update(resolved_layer.model_dump(mode="python"))
            else:
                layer_payload.update({
                    "lambda_w_mk": None, "lambda_provenance": None,
                    "material_record_id": (property_result.record.record_id
                                           if property_result.record else None),
                    "material_resolution_digest": property_result.dependency_digest,
                    "property_condition": property_result.operating_condition.value,
                })
                codes = list(property_result.diagnostics)
                if property_result.candidate_record_ids:
                    codes.append("CANDIDATE_RECORDS=" + ",".join(property_result.candidate_record_ids))
                material_diagnostics.extend(codes)
    try:
        submission = EnvelopeConstructionSubmission.model_validate({
            "source_mode": mode.value,
            "source_reference": source.source_reference,
            "source_field": source.question_id,
            "source_revision": source.revision,
            **raw,
        })
        if any(
            provenance.source_type == "test_only"
            for assembly in submission.assemblies
            for provenance in (
                [layer.lambda_provenance for layer in assembly.layers]
                + ([assembly.explicit_u_value.provenance]
                   if assembly.explicit_u_value is not None else [])
            )
            if provenance is not None
        ):
            return ResolverResult(
                resolver_request_id=request.resolver_request_id,
                status="OUT_OF_DOMAIN", dependency_digest=request.dependency_digest,
                diagnostics=["TEST_ONLY_SOURCE_NOT_BINDABLE"],
            )
        surface_methods = {}
        surface_diagnostics = {}
        for assembly in submission.assemblies:
            if assembly.surface_applicability is not None:
                from agent.ufh_sp50_surface_resistance import (
                    SurfaceApplicability, resolve_surface_resistances,
                )
                raw_applicability = dict(assembly.surface_applicability)
                raw_applicability.setdefault("source_reference", assembly.source_reference)
                raw_applicability.setdefault(
                    "source_field", f"{assembly.source_field}.surface_applicability")
                resolution = resolve_surface_resistances(
                    SurfaceApplicability.model_validate(raw_applicability))
                if resolution.method is not None:
                    surface_methods[assembly.assembly_id] = resolution.method
                surface_diagnostics[assembly.assembly_id] = resolution.diagnostics
        bundle = calculate_bundle(submission, surface_methods=surface_methods)
    except ValueError as error:
        error_code = str(error).splitlines()[0][:160]
        if hasattr(error, "errors"):
            details = error.errors()
            if details:
                underlying = details[0].get("ctx", {}).get("error")
                if underlying is not None:
                    error_code = str(underlying)[:160]
        status = "AMBIGUOUS" if error_code in {"SOURCE_VALUE_CONFLICT", "AMBIGUOUS_MATERIAL"} else "INSUFFICIENT_INPUT"
        return ResolverResult(resolver_request_id=request.resolver_request_id,
                              status=status, dependency_digest=request.dependency_digest,
                              diagnostics=[error_code])
    if any(item.calculation_status == "SOURCE_VALUE_CONFLICT" for item in bundle.assemblies):
        return ResolverResult(resolver_request_id=request.resolver_request_id,
                              status="AMBIGUOUS", dependency_digest=request.dependency_digest,
                              diagnostics=["SOURCE_VALUE_CONFLICT"])
    if material_diagnostics:
        status = "AMBIGUOUS" if any(code in {
            "AMBIGUOUS_MATERIAL", "SOURCE_VALUE_CONFLICT"} for code in material_diagnostics) else "INSUFFICIENT_INPUT"
        return ResolverResult(resolver_request_id=request.resolver_request_id,
            status=status, dependency_digest=request.dependency_digest,
            diagnostics=sorted(set(material_diagnostics + [
                dependency for assembly in bundle.assemblies
                for dependency in assembly.unresolved_dependencies
            ])))
    refs = sorted({ref for item in bundle.assemblies for ref in item.provenance_references})
    if mode == ConstructionSourceMode.EXPLICIT_U_VALUE_WITH_PROVENANCE:
        authority = "USER_CONFIRMED_PROJECT_DECISION"
        source_type = "project_decision"
    else:
        authority = "USER_CONFIRMED_PROJECT_DECISION"
        source_type = "project_decision"
    provenance = AuthoringProvenance(
        source_type=source_type, source_reference=source.source_reference,
        source_field=source.question_id, author_or_confirmation=source.revision,
        transformation="record construction submission; retain per-property provenance; no boundary or heat-loss inference",
        units="none",
    )
    authored = {
        "status": "DERIVED", "value": bundle.model_dump(mode="json"),
        "unit": "none", "provenance": provenance.model_dump(mode="python"),
    }
    return ResolverResult(
        resolver_request_id=request.resolver_request_id, status="RESOLVED",
        dependency_digest=request.dependency_digest,
        values=[ResolvedValue(
            target_authoring_field="envelope_constructions.selected",
            authored_value=authored, authority_class=authority,
            dependency_digest=request.dependency_digest,
            source_revision=source.revision,
            authoritative_input_references=refs or [source.source_reference],
        )],
        diagnostics=sorted({
            dependency for assembly in bundle.assemblies
            for dependency in assembly.unresolved_dependencies
        } | {diagnostic for values in surface_diagnostics.values() for diagnostic in values}),
    )


__all__ = [
    "ConstructionBoundaryKind", "ConstructionLayer", "ConstructionSourceMode",
    "EnvelopeAssemblyDefinition", "EnvelopeConstructionAssembly",
    "EnvelopeConstructionBundle", "EnvelopeConstructionSubmission",
    "ExplicitUValue", "SurfaceResistanceMethod", "calculate_assembly",
    "calculate_bundle", "make_envelope_construction_request",
    "resolve_envelope_construction_submission",
]

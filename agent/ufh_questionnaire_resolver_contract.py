"""Resolver envelopes and fail-closed authoring binding. No resolver calculations."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import Field, model_validator
from agent.ufh_pre_generation_questionnaire import Model, Decision, QuestionnaireState, digest
from agent.ufh_project_engineering_profile_authoring import AuthoredValue, AuthoringProvenance

ResolverType = Literal["CLIMATE_RESOLVER", "BUILDING_CONSTRUCTION_RESOLVER",
    "BOUNDARY_CONDITION_RESOLVER", "FLOOR_FINISH_RESOLVER", "UFH_PRODUCT_RESOLVER",
    "PIPE_PRODUCT_RESOLVER", "MANIFOLD_PRODUCT_RESOLVER", "FLUID_PROPERTY_RESOLVER",
    "CONTROL_CHARACTERISTIC_RESOLVER", "SURFACE_LIMIT_RESOLVER",
    "ENVELOPE_OPERATING_CONDITION_RESOLVER"]
Status = Literal["RESOLVED", "NOT_FOUND", "AMBIGUOUS", "OUT_OF_DOMAIN",
    "SOURCE_UNAVAILABLE", "SELECTION_REQUIRED", "INSUFFICIENT_INPUT", "STALE_INPUT", "UNSUPPORTED"]
Authority = Literal["PROJECT_AUTHORITATIVE", "NORMATIVE_AUTHORITATIVE",
    "MANUFACTURER_AUTHORITATIVE", "USER_CONFIRMED_PROJECT_DECISION",
    "DERIVED_FROM_AUTHORITATIVE_INPUTS", "PROJECT_APPROVED_NORMATIVE_EXTRACT",
    "REFERENCE_ONLY", "UNACCEPTABLE_FOR_BINDING"]

# Closed field policies: a resolver cannot request arbitrary kernel paths.
POLICIES = {
    "CLIMATE_RESOLVER": ({"design_conditions.outdoor_design_temperature_c": "degC"}, ["climate"]),
    "BOUNDARY_CONDITION_RESOLVER": ({"design_conditions.floor_boundary_temperature_c": "degC", "design_conditions.ceiling_boundary_temperature_c": "degC"}, ["below", "below.source", "below.details", "above", "above.details"]),
    "BUILDING_CONSTRUCTION_RESOLVER": ({"building_physics.exterior_wall_u_value_w_m2k": "W/(m2*K)", "building_physics.floor_u_value_w_m2k": "W/(m2*K)", "building_physics.ceiling_u_value_w_m2k": "W/(m2*K)", "building_physics.thermal_bridge_allowance_percent": "%", "building_physics.ventilation_heat_capacity_factor_wh_m3k": "Wh/(m3*K)"}, ["envelope", "envelope.source", "below", "below.source", "above"]),
    "FLOOR_FINISH_RESOLVER": ({"floor_system_product.r_o_m2k_w": "m2*K/W"}, ["finish", "finish.source"]),
    "UFH_PRODUCT_RESOLVER": ({"floor_system_product.declared_output_at_100mm_w_m2": "W/m2", "floor_system_product.declared_output_at_200mm_w_m2": "W/m2", "floor_system_product.output_basis_reference": "none", "floor_system_product.k_h_w_m2k": "W/(m2*K)", "floor_system_product.r_u_m2k_w": "m2*K/W"}, ["system", "system.source", "finish", "finish.source"]),
    "PIPE_PRODUCT_RESOLVER": ({"pipe_product.inner_diameter_m": "m", "pipe_product.roughness_m": "m", "pipe_product.embedded_losses_continuous_bends_pa": "Pa", "pipe_product.embedded_losses_pipe_fittings_pa": "Pa", "pipe_product.embedded_losses_other_fixed_pipe_path_pa": "Pa"}, ["system", "system.source"]),
    "MANIFOLD_PRODUCT_RESOLVER": ({"manifold_product.fixed_manifold_losses": "none", "manifold_product.manufacturer_max_circuit_pressure_pa": "Pa"}, ["system", "system.source"]),
    "FLUID_PROPERTY_RESOLVER": ({"fluid_definition.c_w_j_kgk": "J/(kg*K)", "fluid_definition.density_kg_m3": "kg/m3", "fluid_definition.dynamic_viscosity_pa_s": "Pa*s", "fluid_definition.specific_gravity": "none"}, ["fluid", "fluid.temperature", "fluid.source"]),
    "CONTROL_CHARACTERISTIC_RESOLVER": ({"control_model.control_characteristic": "none"}, ["system", "system.source"]),
    "SURFACE_LIMIT_RESOLVER": ({"control_model.surface_limit_w_m2": "W/m2"}, ["surface", "surface.source"]),
    "ENVELOPE_OPERATING_CONDITION_RESOLVER": ({"envelope_constructions.operating_condition": "none"}, ["indoor_rh", "moisture_zone"]),
}

TEST01_QUESTION_RESOLVER_MAP = {
    "climate": {"handoff": "CLIMATE_RESOLVER", "outputs": ["design_conditions.outdoor_design_temperature_c"], "invalidates": ["CLIMATE_RESOLVER"], "count_class": "ALWAYS_REQUIRED"},
    "below": {"handoff": "BOUNDARY_CONDITION_RESOLVER", "outputs": ["thermal_boundary_conditions.below"], "invalidates": ["BOUNDARY_CONDITION_RESOLVER:below"], "count_class": "ALWAYS_REQUIRED"},
    "below.source": {"handoff": "BUILDING_CONSTRUCTION_RESOLVER", "outputs": ["building_physics.floor_u_value_w_m2k"], "invalidates": ["BUILDING_CONSTRUCTION_RESOLVER"], "count_class": "CONDITIONAL_ONLY"},
    "below.details": {"handoff": "BOUNDARY_CONDITION_RESOLVER", "outputs": ["thermal_boundary_conditions.below"], "invalidates": ["BOUNDARY_CONDITION_RESOLVER:below"], "count_class": "CONDITIONAL_ONLY"},
    "above": {"handoff": "BOUNDARY_CONDITION_RESOLVER", "outputs": ["thermal_boundary_conditions.above"], "invalidates": ["BOUNDARY_CONDITION_RESOLVER:above"], "count_class": "ALWAYS_REQUIRED"},
    "above.details": {"handoff": "BOUNDARY_CONDITION_RESOLVER", "outputs": ["thermal_boundary_conditions.above"], "invalidates": ["BOUNDARY_CONDITION_RESOLVER:above"], "count_class": "CONDITIONAL_ONLY"},
    "envelope": {"handoff": "BUILDING_CONSTRUCTION_RESOLVER", "outputs": ["envelope_constructions.selected"], "invalidates": ["BUILDING_CONSTRUCTION_RESOLVER"], "count_class": "ALWAYS_REQUIRED"},
    "envelope.source": {"handoff": "BUILDING_CONSTRUCTION_RESOLVER", "outputs": ["envelope_constructions.selected"], "invalidates": ["BUILDING_CONSTRUCTION_RESOLVER"], "count_class": "CONDITIONAL_ONLY"},
    "finish": {"handoff": "FLOOR_FINISH_RESOLVER", "outputs": ["floor_system_product.r_o_m2k_w"], "invalidates": ["FLOOR_FINISH_RESOLVER", "UFH_PRODUCT_RESOLVER"], "count_class": "ALWAYS_REQUIRED"},
    "finish.source": {"handoff": "FLOOR_FINISH_RESOLVER", "outputs": ["floor_system_product.r_o_m2k_w"], "invalidates": ["FLOOR_FINISH_RESOLVER"], "count_class": "CONDITIONAL_ONLY"},
    "exclusions": {"handoff": "DIRECT_AUTHORING_UPDATE", "outputs": ["explicit_confirmations.exclusion_zones"], "invalidates": ["DOWNSTREAM_ROUTING_CANDIDATE"], "count_class": "ALWAYS_REQUIRED"},
    "collector": {"handoff": "DIRECT_AUTHORING_UPDATE", "outputs": ["ufh_design_settings.collector_point_x_mm", "ufh_design_settings.collector_point_y_mm"], "invalidates": ["DOWNSTREAM_ROUTING_CANDIDATE"], "count_class": "ALWAYS_REQUIRED"},
    "system": {"handoff": "UFH_PRODUCT_RESOLVER", "outputs": ["floor_system_product", "pipe_product", "manifold_product", "control_model.control_characteristic"], "invalidates": ["UFH_PRODUCT_RESOLVER", "PIPE_PRODUCT_RESOLVER", "MANIFOLD_PRODUCT_RESOLVER", "CONTROL_CHARACTERISTIC_RESOLVER"], "count_class": "ALWAYS_REQUIRED"},
    "system.source": {"handoff": "UFH_PRODUCT_RESOLVER", "outputs": ["floor_system_product", "pipe_product", "manifold_product", "control_model.control_characteristic"], "invalidates": ["UFH_PRODUCT_RESOLVER", "PIPE_PRODUCT_RESOLVER", "MANIFOLD_PRODUCT_RESOLVER", "CONTROL_CHARACTERISTIC_RESOLVER"], "count_class": "CONDITIONAL_ONLY"},
    "layout": {"handoff": "DIRECT_AUTHORING_UPDATE_OR_LAYOUT_POLICY_RESOLVER", "outputs": ["ufh_design_settings.spacing_mm", "ufh_design_settings.wall_offset_mm", "ufh_design_settings.design_margin_percent", "ufh_design_settings.area_basis"], "invalidates": ["DOWNSTREAM_ROUTING_CANDIDATE"], "count_class": "ALWAYS_REQUIRED"},
    "layout.spacing": {"handoff": "DIRECT_AUTHORING_UPDATE", "outputs": ["ufh_design_settings.spacing_mm"], "invalidates": ["DOWNSTREAM_ROUTING_CANDIDATE"], "count_class": "CONDITIONAL_ONLY"},
    "layout.offset": {"handoff": "DIRECT_AUTHORING_UPDATE", "outputs": ["ufh_design_settings.wall_offset_mm"], "invalidates": ["DOWNSTREAM_ROUTING_CANDIDATE"], "count_class": "CONDITIONAL_ONLY"},
    "fluid": {"handoff": "FLUID_PROPERTY_RESOLVER", "outputs": ["fluid_definition"], "invalidates": ["FLUID_PROPERTY_RESOLVER"], "count_class": "ALWAYS_REQUIRED"},
    "fluid.temperature": {"handoff": "FLUID_PROPERTY_RESOLVER", "outputs": ["fluid_definition.c_w_j_kgk", "fluid_definition.density_kg_m3", "fluid_definition.dynamic_viscosity_pa_s", "fluid_definition.specific_gravity"], "invalidates": ["FLUID_PROPERTY_RESOLVER"], "count_class": "CONDITIONAL_ONLY"},
    "fluid.source": {"handoff": "FLUID_PROPERTY_RESOLVER", "outputs": ["fluid_definition"], "invalidates": ["FLUID_PROPERTY_RESOLVER"], "count_class": "CONDITIONAL_ONLY"},
    "thermal": {"handoff": "DIRECT_AUTHORING_UPDATE_OR_THERMAL_RESOLVER", "outputs": ["ufh_design_settings.mode"], "invalidates": ["THERMAL_SOLVE_INPUTS"], "count_class": "ALWAYS_REQUIRED"},
    "thermal.supply": {"handoff": "DIRECT_AUTHORING_UPDATE", "outputs": ["design_conditions.theta_supply_c"], "invalidates": ["THERMAL_SOLVE_INPUTS"], "count_class": "CONDITIONAL_ONLY"},
    "thermal.delta": {"handoff": "DIRECT_AUTHORING_UPDATE", "outputs": ["design_conditions.sigma_k"], "invalidates": ["THERMAL_SOLVE_INPUTS"], "count_class": "CONDITIONAL_ONLY"},
    "surface": {"handoff": "SURFACE_LIMIT_RESOLVER", "outputs": ["control_model.surface_limit_w_m2"], "invalidates": ["SURFACE_LIMIT_RESOLVER"], "count_class": "ALWAYS_REQUIRED"},
    "surface.source": {"handoff": "SURFACE_LIMIT_RESOLVER", "outputs": ["control_model.surface_limit_w_m2"], "invalidates": ["SURFACE_LIMIT_RESOLVER"], "count_class": "CONDITIONAL_ONLY"},
    "openings": {"handoff": "DIRECT_AUTHORING_UPDATE", "outputs": ["explicit_confirmations.openings"], "invalidates": ["BUILDING_CONSTRUCTION_RESOLVER"], "count_class": "CAN_BE_DEFERRED"},
    "indoor_rh": {"handoff": "ENVELOPE_OPERATING_CONDITION_RESOLVER", "outputs": ["envelope_constructions.operating_condition"], "invalidates": ["ENVELOPE_OPERATING_CONDITION_RESOLVER"], "count_class": "CONDITIONAL_ONLY"},
    "moisture_zone": {"handoff": "ENVELOPE_OPERATING_CONDITION_RESOLVER", "outputs": ["envelope_constructions.operating_condition"], "invalidates": ["ENVELOPE_OPERATING_CONDITION_RESOLVER"], "count_class": "CONDITIONAL_ONLY"},
}


def _policy_for(kind: str, context: dict[str, str] | None = None):
    if kind == "BUILDING_CONSTRUCTION_RESOLVER" and context and context.get("construction_bundle") == "V1":
        return {"envelope_constructions.selected": "none"}, ["envelope", "envelope.source"]
    if kind == "BOUNDARY_CONDITION_RESOLVER" and context and context.get("boundary_side") in {"BELOW", "ABOVE"}:
        side = context["boundary_side"]
        question_ids = ["below", "below.details"] if side == "BELOW" else ["above", "above.details"]
        target = f"thermal_boundary_conditions.{side.lower()}"
        return {target: "none"}, question_ids
    return POLICIES[kind]

INHERITED_ASSUMPTION_AUDIT = [
    {"path": "sizing.room.insulation.air_changes_per_hour", "value": None, "location": "agent/ufh_project_engineering_profile_authoring.py:444", "classification": "PROJECT_DATA_VALUE", "reason": "No production fallback. Loader requires authoritative project ACH or explicit test fixture ACH."},
    {"path": "sizing.coverage_request.requested_circuit_count", "value": None, "location": "agent/ufh_project_engineering_profile_authoring.py:419; agent/ufh_project_adapter.py:714", "classification": "API_COMPATIBILITY_DEFAULT", "reason": "None means existing automatic circuit-count semantics."},
    {"path": "sizing.coverage_request.routing_mode", "value": "legacy", "location": "agent/ufh_project_engineering_profile_authoring.py:419; agent/ufh_project_adapter.py:717", "classification": "API_COMPATIBILITY_DEFAULT", "reason": "Existing production routing mode selector; not a physical design value."},
    {"path": "sizing.coverage_request.turn_radius_mm", "value": 100, "location": "agent/ufh_project_engineering_profile_authoring.py:330; agent/ufh_project_adapter.py:716", "classification": "ROUTING_ALGORITHM_POLICY", "reason": "Versioned HOMEAURA_UFH_ROUTING_POLICY:V1 value; geometry semantics unchanged."},
    {"path": "sizing.coverage_request.field_spacing_mm", "value": None, "location": "agent/ufh_project_engineering_profile_authoring.py:420; agent/ufh_project_adapter.py:718", "classification": "STRUCTURAL_SOFTWARE_DEFAULT", "reason": "Unset optional refinement; effective spacing is separately authored as spacing_mm."},
    {"path": "sizing.coverage_request.perimeter_spacing_mm", "value": None, "location": "agent/ufh_project_engineering_profile_authoring.py:420; agent/ufh_project_adapter.py:719", "classification": "STRUCTURAL_SOFTWARE_DEFAULT", "reason": "Unset optional perimeter refinement."},
    {"path": "sizing.coverage_request.perimeter_band_depth_mm", "value": None, "location": "agent/ufh_project_engineering_profile_authoring.py:421; agent/ufh_project_adapter.py:720", "classification": "STRUCTURAL_SOFTWARE_DEFAULT", "reason": "Unset optional perimeter refinement."},
    {"path": "sizing.coverage_request.preferred_topology", "value": None, "location": "agent/ufh_project_engineering_profile_authoring.py:421; agent/ufh_project_adapter.py:721", "classification": "STRUCTURAL_SOFTWARE_DEFAULT", "reason": "Unset optional topology selector."},
    {"path": "sizing.coverage_request.installation_grid_spacing_mm", "value": None, "location": "agent/ufh_project_engineering_profile_authoring.py:422; agent/ufh_project_adapter.py:722", "classification": "STRUCTURAL_SOFTWARE_DEFAULT", "reason": "Unset optional grid selector."},
    {"path": "sizing.coverage_request.perimeter_priority_mode", "value": True, "location": "agent/ufh_project_engineering_profile_authoring.py:330; agent/ufh_project_adapter.py:723", "classification": "ROUTING_ALGORITHM_POLICY", "reason": "Versioned HOMEAURA_UFH_ROUTING_POLICY:V1 value; geometry semantics unchanged."},
    {"path": "sizing.coverage_request.minimum_circuit_length_mm", "value": 40000, "location": "agent/floor_heating_models.py:45; agent/ufh_project_adapter.py:724", "classification": "LEGACY_ROUTING_POLICY", "reason": "LEGACY_MVP_ROUTING_POLICY, not an EN1264 physical limit."},
    {"path": "sizing.coverage_request.maximum_circuit_length_mm", "value": 80000, "location": "agent/floor_heating_models.py:41; agent/ufh_project_adapter.py:725", "classification": "LEGACY_ROUTING_POLICY", "reason": "LEGACY_MVP_ROUTING_POLICY, not an EN1264 physical limit."},
    {"path": "sizing.schema_version", "value": "1.0", "location": "agent/ufh_project_adapter.py:712", "classification": "STRUCTURAL_SOFTWARE_DEFAULT", "reason": "Fixed schema tag; no physical calculation effect."},
    {"path": "sizing.coverage_request.schema_version", "value": "1.0", "location": "agent/ufh_project_adapter.py:713", "classification": "STRUCTURAL_SOFTWARE_DEFAULT", "reason": "Fixed schema tag; no physical calculation effect."},
]


def allowed_authorities(kind: str) -> list[str]:
    if kind == "BOUNDARY_CONDITION_RESOLVER":
        return ["USER_CONFIRMED_PROJECT_DECISION", "PROJECT_AUTHORITATIVE"]
    if kind == "BUILDING_CONSTRUCTION_RESOLVER":
        return ["PROJECT_AUTHORITATIVE", "MANUFACTURER_AUTHORITATIVE", "NORMATIVE_AUTHORITATIVE",
                "PROJECT_APPROVED_NORMATIVE_EXTRACT", "DERIVED_FROM_AUTHORITATIVE_INPUTS",
                "USER_CONFIRMED_PROJECT_DECISION"]
    if kind in {"PIPE_PRODUCT_RESOLVER", "UFH_PRODUCT_RESOLVER", "MANIFOLD_PRODUCT_RESOLVER", "CONTROL_CHARACTERISTIC_RESOLVER"}:
        return ["MANUFACTURER_AUTHORITATIVE", "DERIVED_FROM_AUTHORITATIVE_INPUTS"]
    if kind == "CLIMATE_RESOLVER":
        return ["NORMATIVE_AUTHORITATIVE", "PROJECT_APPROVED_NORMATIVE_EXTRACT",
                "DERIVED_FROM_AUTHORITATIVE_INPUTS"]
    if kind == "ENVELOPE_OPERATING_CONDITION_RESOLVER":
        return ["PROJECT_APPROVED_NORMATIVE_EXTRACT"]
    if kind == "SURFACE_LIMIT_RESOLVER":
        return ["NORMATIVE_AUTHORITATIVE", "DERIVED_FROM_AUTHORITATIVE_INPUTS"]
    return ["PROJECT_AUTHORITATIVE", "NORMATIVE_AUTHORITATIVE", "MANUFACTURER_AUTHORITATIVE", "DERIVED_FROM_AUTHORITATIVE_INPUTS"]


def _authority_matches_provenance(authority: str, provenance: AuthoringProvenance) -> bool:
    if authority == "PROJECT_AUTHORITATIVE":
        return provenance.source_type in {"building_construction_data", "project_decision", "project_data"}
    if authority == "NORMATIVE_AUTHORITATIVE":
        return provenance.source_type == "normative_source"
    if authority == "PROJECT_APPROVED_NORMATIVE_EXTRACT":
        return provenance.source_type == "project_approved_normative_extract"
    if authority == "MANUFACTURER_AUTHORITATIVE":
        return provenance.source_type in {"product_document", "control_product_document"}
    if authority == "USER_CONFIRMED_PROJECT_DECISION":
        return provenance.source_type == "project_decision"
    if authority == "DERIVED_FROM_AUTHORITATIVE_INPUTS":
        return provenance.source_type in {"building_construction_data", "normative_source", "product_document", "fluid_property_source", "control_product_document", "project_decision"}
    return False


class ResolverRequest(Model):
    resolver_request_id: str
    resolver_type: ResolverType
    source_question_ids: list[str]
    project_id: str = Field(min_length=1)
    room_id: str = Field(min_length=1)
    project_source_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    normalized_decisions: dict[str, Any]
    required_output_fields: list[str]
    expected_units: dict[str, str]
    source_policy_requirements: list[str]
    dependency_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    resolver_context: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def coherent(self):
        fields, questions = _policy_for(self.resolver_type, self.resolver_context)
        if self.source_question_ids != questions or set(self.normalized_decisions) != set(questions):
            raise ValueError("DEPENDENCY_SET_INVALID")
        if self.required_output_fields != list(fields) or self.expected_units != fields:
            raise ValueError("FIELD_POLICY_INVALID")
        if self.source_policy_requirements != allowed_authorities(self.resolver_type):
            raise ValueError("AUTHORITY_POLICY_INVALID")
        if self.dependency_digest != self.calculate_dependency_digest():
            raise ValueError("DEPENDENCY_DIGEST_INVALID")
        if self.resolver_request_id != digest({"type": self.resolver_type, "dependency": self.dependency_digest}):
            raise ValueError("REQUEST_ID_INVALID")
        return self

    def calculate_dependency_digest(self):
        source_identity = self.project_source_digest
        if self.resolver_type == "ENVELOPE_OPERATING_CONDITION_RESOLVER":
            source_identity = self.resolver_context.get(
                "relevant_project_input_digest", self.project_source_digest)
        payload = {"type": self.resolver_type, "project": self.project_id, "room": self.room_id,
                   "source": source_identity, "inputs": self.normalized_decisions}
        if self.resolver_context:
            payload["resolver_context"] = self.resolver_context
        return digest(payload)


def make_resolver_request(kind: ResolverType, project_id: str, room_id: str,
                          project_source_digest: str, decisions: dict[str, Decision],
                          resolver_context: dict[str, str] | None = None) -> ResolverRequest:
    context = resolver_context or {}
    fields, questions = _policy_for(kind, context)
    normalized = {key: decisions[key].model_dump(mode="json") if key in decisions else None for key in questions}
    dependency_payload = {"type": kind, "project": project_id, "room": room_id,
                          "source": (context.get("relevant_project_input_digest", project_source_digest)
                              if kind == "ENVELOPE_OPERATING_CONDITION_RESOLVER"
                              else project_source_digest), "inputs": normalized}
    if context:
        dependency_payload["resolver_context"] = context
    dep = digest(dependency_payload)
    return ResolverRequest(resolver_request_id=digest({"type": kind, "dependency": dep}),
        resolver_type=kind, source_question_ids=questions, project_id=project_id, room_id=room_id,
        project_source_digest=project_source_digest, normalized_decisions=normalized,
        required_output_fields=list(fields), expected_units=fields,
        source_policy_requirements=allowed_authorities(kind), dependency_digest=dep,
        resolver_context=context)


class ResolvedValue(Model):
    target_authoring_field: str
    authored_value: AuthoredValue
    authority_class: Authority
    dependency_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_revision: str | None = None
    source_date: str | None = None
    authoritative_input_references: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def physical_provenance(self):
        item = self.authored_value
        if item.value is None or item.provenance is None or item.unit is None or item.status == "UNSET":
            raise ValueError("RESOLVED_PROVENANCE_REQUIRED")
        if self.authority_class in {"REFERENCE_ONLY", "UNACCEPTABLE_FOR_BINDING"}:
            raise ValueError("AUTHORITY_NOT_BINDABLE")
        if not _authority_matches_provenance(self.authority_class, item.provenance):
            raise ValueError("AUTHORITY_PROVENANCE_MISMATCH")
        if item.unit != item.provenance.units:
            raise ValueError("PROVENANCE_UNIT_CONFLICT")
        digest(item.model_dump(mode="json"))  # Reject non-JSON/nonfinite data.
        if self.authority_class == "DERIVED_FROM_AUTHORITATIVE_INPUTS" and not self.authoritative_input_references:
            raise ValueError("DERIVATION_INPUT_REFERENCES_REQUIRED")
        return self


class ResolverResult(Model):
    resolver_request_id: str
    status: Status
    dependency_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    values: list[ResolvedValue] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent(self):
        if (self.status == "RESOLVED") != bool(self.values):
            raise ValueError("RESULT_STATUS_VALUES_CONFLICT")
        if len({v.target_authoring_field for v in self.values}) != len(self.values):
            raise ValueError("DUPLICATE_OUTPUT")
        if any(v.dependency_digest != self.dependency_digest for v in self.values):
            raise ValueError("VALUE_DEPENDENCY_CONFLICT")
        return self

    @property
    def envelope_digest(self):
        return digest(self.model_dump(mode="json"))


class Binding(Model):
    request: ResolverRequest
    result: ResolverResult

    @model_validator(mode="after")
    def consistent(self):
        if self.result.resolver_request_id != self.request.resolver_request_id:
            raise ValueError("BINDING_REQUEST_ID_CONFLICT")
        if self.result.dependency_digest != self.request.dependency_digest:
            raise ValueError("BINDING_DEPENDENCY_CONFLICT")
        return self


def apply_resolver_result(state: QuestionnaireState, request: ResolverRequest,
                          result: ResolverResult) -> tuple[QuestionnaireState, Binding]:
    project_context = state.authoring.project_context
    if project_context.get("project_id") != request.project_id or project_context.get("room_id") != request.room_id:
        raise ValueError("PROJECT_CONTEXT_CONFLICT")
    current = make_resolver_request(request.resolver_type, request.project_id, request.room_id,
                                    request.project_source_digest, state.decisions,
                                    request.resolver_context)
    if current.dependency_digest != request.dependency_digest or result.dependency_digest != request.dependency_digest or result.resolver_request_id != request.resolver_request_id:
        raise ValueError("STALE_INPUT")
    if result.status != "RESOLVED":
        raise ValueError("RESULT_NOT_RESOLVED:" + result.status)
    if {v.target_authoring_field for v in result.values} != set(request.required_output_fields):
        raise ValueError("OUTPUT_SET_INVALID")
    updated = state.model_copy(deep=True)
    for v in result.values:
        if v.authority_class not in request.source_policy_requirements:
            raise ValueError("AUTHORITY_NOT_ACCEPTED")
        if v.authored_value.provenance.source_type == "test_only":
            raise ValueError("TEST_SOURCE_NOT_BINDABLE")
        if v.authored_value.unit != request.expected_units[v.target_authoring_field]:
            raise ValueError("UNIT_INVALID")
        group, field = v.target_authoring_field.split(".")
        target = getattr(updated.authoring, group)
        if target[field].status != "UNSET" and target[field] != v.authored_value:
            raise ValueError("AUTHORING_SOURCE_CONFLICT")
        target[field] = AuthoredValue.model_validate(v.authored_value.model_dump(mode="python"))
    return updated, Binding(request=request, result=result)


def invalidate_bindings(state: QuestionnaireState, bindings: list[Binding],
                        project_source_digest: str,
                        resolver_contexts: dict[str, dict[str, str]] | None = None) -> tuple[QuestionnaireState, list[Binding]]:
    """Call after replacing decisions, before any authoring/profile consumption."""
    updated, history = state.model_copy(deep=True), []
    for binding in bindings:
        req = binding.request
        resolver_context = (resolver_contexts or {}).get(
            f"{req.resolver_type}:{req.resolver_context.get('boundary_side', '')}",
            (resolver_contexts or {}).get(req.resolver_type, req.resolver_context),
        )
        current = make_resolver_request(req.resolver_type, req.project_id, req.room_id,
                                        project_source_digest, state.decisions,
                                        resolver_context)
        if current.dependency_digest == req.dependency_digest:
            history.append(binding)
            continue
        for value in binding.result.values:
            group, field = value.target_authoring_field.split(".")
            target = getattr(updated.authoring, group)
            if target[field] == value.authored_value:
                target[field] = AuthoredValue()
        history.append(Binding(request=req, result=ResolverResult(
            resolver_request_id=req.resolver_request_id, status="STALE_INPUT",
            dependency_digest=req.dependency_digest, diagnostics=["Dependent input changed; authoring outputs cleared."])))
    return updated, history


def replace_questionnaire_decisions_and_invalidate(
    state: QuestionnaireState,
    replacements: dict[str, Decision],
    bindings: list[Binding],
    project_source_digest: str,
    resolver_contexts: dict[str, dict[str, str]] | None = None,
) -> tuple[QuestionnaireState, list[Binding]]:
    """Atomically replace answers, then clear any resolver values made stale."""
    updated = state.model_copy(deep=True)
    updated.decisions.update(replacements)
    return invalidate_bindings(updated, bindings, project_source_digest, resolver_contexts)


def assumption_audit_by_class() -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in INHERITED_ASSUMPTION_AUDIT:
        counts[item["classification"]] = counts.get(item["classification"], 0) + 1
    return counts

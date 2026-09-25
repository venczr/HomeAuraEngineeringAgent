"""Semantic, fail-closed classification of the room's thermal boundaries."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from agent.ufh_pre_generation_questionnaire import Model, QuestionnaireState, digest
from agent.ufh_project_engineering_profile_authoring import (
    AuthoredValue,
    AuthoringProvenance,
)
from agent.ufh_questionnaire_resolver_contract import (
    ResolverRequest,
    ResolverResult,
    ResolvedValue,
    make_resolver_request,
)


BoundarySide = Literal["BELOW", "ABOVE"]
BoundaryType = Literal[
    "HEATED_INTERIOR_SPACE", "UNHEATED_INTERIOR_SPACE", "OUTDOOR_AIR",
    "GROUND", "VENTILATED_VOID", "UNKNOWN_PROJECT_SPECIFIC",
]

BOUNDARY_QUESTION = {"BELOW": "below", "ABOVE": "above"}
BOUNDARY_DETAILS_QUESTION = {"BELOW": "below.details", "ABOVE": "above.details"}
BOUNDARY_TARGET = {
    "BELOW": "thermal_boundary_conditions.below",
    "ABOVE": "thermal_boundary_conditions.above",
}


class ThermalBoundaryCondition(Model):
    boundary_side: BoundarySide
    boundary_type: BoundaryType
    adjacent_zone_id: str | None = None
    source_question_ids: list[str] = Field(min_length=1)
    source_authority: Literal["USER_CONFIRMED_PROJECT_DECISION"]
    thermal_reference_kind: Literal[
        "PROJECT_ZONE_TEMPERATURE", "CLIMATE_DESIGN_TEMPERATURE",
        "GROUND_BOUNDARY_MODEL", "UNHEATED_SPACE_METHOD", "VENTILATED_VOID_METHOD",
        "PROJECT_SPECIFIC_METHOD",
    ]
    requires_explicit_temperature: bool
    requires_construction_assembly: bool
    may_use_project_zone_temperature: bool
    may_use_climate_design_temperature: bool
    dependency_requirements: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    climate_dependency_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    dependency_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


def make_boundary_resolver_request(
    project_id: str,
    room_id: str,
    project_source_digest: str,
    state: QuestionnaireState,
    side: BoundarySide,
    *,
    climate_dependency_digest: str | None = None,
) -> ResolverRequest:
    context = boundary_resolver_context(state, side, climate_dependency_digest)
    return make_resolver_request(
        "BOUNDARY_CONDITION_RESOLVER", project_id, room_id,
        project_source_digest, state.decisions, resolver_context=context,
    )


def boundary_resolver_context(
    state: QuestionnaireState,
    side: BoundarySide,
    climate_dependency_digest: str | None = None,
) -> dict[str, str]:
    context = {"boundary_side": side}
    decision = state.decisions.get(BOUNDARY_QUESTION[side].lower())
    category = decision.value if decision is not None else None
    if category in {"OUTDOOR", "ROOF_OUTDOOR"} and climate_dependency_digest is not None:
        context["climate_dependency_digest"] = climate_dependency_digest
        climate_value = state.authoring.design_conditions.get("outdoor_design_temperature_c")
        context["climate_condition_status"] = (
            "RESOLVED" if climate_value is not None and climate_value.status != "UNSET"
            else "UNRESOLVED"
        )
    return context


def _not_resolved(request: ResolverRequest, status: str, diagnostic: str) -> ResolverResult:
    return ResolverResult(
        resolver_request_id=request.resolver_request_id,
        status=status,
        dependency_digest=request.dependency_digest,
        diagnostics=[diagnostic],
    )


def resolve_boundary_request(
    request: ResolverRequest,
    state: QuestionnaireState,
) -> ResolverResult:
    if request.resolver_type != "BOUNDARY_CONDITION_RESOLVER":
        raise ValueError("BOUNDARY_CONDITION_RESOLVER_REQUEST_REQUIRED")
    side = request.resolver_context.get("boundary_side")
    if side not in BOUNDARY_QUESTION:
        return _not_resolved(request, "UNSUPPORTED", "BOUNDARY_SIDE_REQUIRED")
    question_id = BOUNDARY_QUESTION[side]
    decision = state.decisions.get(question_id)
    if decision is None:
        return _not_resolved(request, "INSUFFICIENT_INPUT", "BOUNDARY_CATEGORY_REQUIRED")

    category_map = {
        "HEATED_ROOM": "HEATED_INTERIOR_SPACE",
        "UNHEATED_BASEMENT": "UNHEATED_INTERIOR_SPACE",
        "UNHEATED_ATTIC": "UNHEATED_INTERIOR_SPACE",
        "OUTDOOR": "OUTDOOR_AIR",
        "ROOF_OUTDOOR": "OUTDOOR_AIR",
        "GROUND": "GROUND",
        "VENTILATED_VOID": "VENTILATED_VOID",
        "OTHER": "UNKNOWN_PROJECT_SPECIFIC",
    }
    boundary_type = category_map.get(decision.value)
    if boundary_type is None:
        return _not_resolved(request, "OUT_OF_DOMAIN", "BOUNDARY_CATEGORY_UNSUPPORTED")

    category = boundary_type
    source_questions = [question_id]
    detail_id = BOUNDARY_DETAILS_QUESTION[side]
    if detail_id in state.decisions:
        source_questions.append(detail_id)

    reference_kind = {
        "HEATED_INTERIOR_SPACE": "PROJECT_ZONE_TEMPERATURE",
        "UNHEATED_INTERIOR_SPACE": "UNHEATED_SPACE_METHOD",
        "OUTDOOR_AIR": "CLIMATE_DESIGN_TEMPERATURE",
        "GROUND": "GROUND_BOUNDARY_MODEL",
        "VENTILATED_VOID": "VENTILATED_VOID_METHOD",
        "UNKNOWN_PROJECT_SPECIFIC": "PROJECT_SPECIFIC_METHOD",
    }[category]
    requirements = {
        "HEATED_INTERIOR_SPACE": [
            "ADJACENT_ZONE_ID_REQUIRED_IF_AVAILABLE",
            "ADJACENT_ZONE_DESIGN_TEMPERATURE_REQUIRED",
            "NUMERIC_BOUNDARY_TEMPERATURE_UNRESOLVED",
        ],
        "UNHEATED_INTERIOR_SPACE": [
            "UNHEATED_SPACE_REFERENCE_TEMPERATURE_OR_NORMATIVE_METHOD_REQUIRED",
            "NUMERIC_BOUNDARY_TEMPERATURE_UNRESOLVED",
        ],
        "OUTDOOR_AIR": [
            "CLIMATE_DESIGN_CONDITION_REQUIRED",
            "NUMERIC_BOUNDARY_TEMPERATURE_REMAINS_PROFILE_OWNED",
        ],
        "GROUND": [
            "GROUND_BOUNDARY_MODEL_REQUIRED",
            "NUMERIC_BOUNDARY_TEMPERATURE_UNRESOLVED",
        ],
        "VENTILATED_VOID": [
            "VENTILATED_VOID_THERMAL_METHOD_REQUIRED",
            "NUMERIC_BOUNDARY_TEMPERATURE_UNRESOLVED",
        ],
        "UNKNOWN_PROJECT_SPECIFIC": [
            "PROJECT_SPECIFIC_BOUNDARY_CLASSIFICATION_REQUIRED",
            "REFERENCE_TEMPERATURE_METHOD_REQUIRED",
        ],
    }[category]
    climate_digest = request.resolver_context.get("climate_dependency_digest")
    climate_resolved = request.resolver_context.get("climate_condition_status") == "RESOLVED"
    if category == "OUTDOOR_AIR" and climate_resolved:
        requirements = [
            "CLIMATE_DESIGN_CONDITION_DEPENDENCY_TRACKED",
            "NUMERIC_BOUNDARY_TEMPERATURE_REMAINS_PROFILE_OWNED",
        ]
    elif category == "OUTDOOR_AIR":
        requirements = [
            "CLIMATE_DESIGN_CONDITION_REQUIRED",
            "NUMERIC_BOUNDARY_TEMPERATURE_REMAINS_PROFILE_OWNED",
        ]

    condition = ThermalBoundaryCondition(
        boundary_side=side,
        boundary_type=category,
        adjacent_zone_id=None,
        source_question_ids=source_questions,
        source_authority="USER_CONFIRMED_PROJECT_DECISION",
        thermal_reference_kind=reference_kind,
        requires_explicit_temperature=category != "OUTDOOR_AIR",
        requires_construction_assembly=True,
        may_use_project_zone_temperature=category == "HEATED_INTERIOR_SPACE",
        may_use_climate_design_temperature=category == "OUTDOOR_AIR",
        dependency_requirements=requirements,
        diagnostics=(
            ["ADJACENT_ZONE_NOT_IDENTIFIED_FROM_AUTHORITATIVE_PROJECT_DATA"]
            if category == "HEATED_INTERIOR_SPACE" else []
        ),
        climate_dependency_digest=climate_digest if category == "OUTDOOR_AIR" else None,
        dependency_digest=request.dependency_digest,
    )
    provenance = AuthoringProvenance(
        source_type="project_decision",
        source_reference=decision.source_reference,
        source_field=question_id,
        author_or_confirmation=decision.revision,
        transformation=(
            f"Explicit questionnaire category {decision.value!r} mapped to "
            f"semantic boundary type {category}; no temperature or U-value inferred."
        ),
        units="none",
    )
    value = ResolvedValue(
        target_authoring_field=BOUNDARY_TARGET[side],
        authored_value=AuthoredValue(
            status="EXPLICIT_VALUE",
            value=condition.model_dump(mode="json"),
            unit="none",
            provenance=provenance,
        ),
        authority_class="USER_CONFIRMED_PROJECT_DECISION",
        dependency_digest=request.dependency_digest,
    )
    return ResolverResult(
        resolver_request_id=request.resolver_request_id,
        status="RESOLVED",
        dependency_digest=request.dependency_digest,
        values=[value],
    )


__all__ = [
    "BOUNDARY_TARGET", "ThermalBoundaryCondition",
    "boundary_resolver_context", "make_boundary_resolver_request",
    "resolve_boundary_request",
]

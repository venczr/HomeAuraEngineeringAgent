"""Application orchestration for project-backed UFH pre-generation inputs.

This layer composes existing project, questionnaire, resolver, and authoring
components. It intentionally never starts sizing, routing, or engineering.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from agent.ufh_boundary_condition_resolver import (
    boundary_resolver_context,
    make_boundary_resolver_request,
    resolve_boundary_request,
)
from agent.ufh_climate_resolver import (
    climate_resolver_context,
    load_climate_dataset,
    make_climate_resolver_request,
    resolve_climate_request,
)
from agent.ufh_envelope_construction_resolver import (
    make_envelope_construction_request,
    resolve_envelope_construction_submission,
)
from agent.ufh_envelope_operating_condition_resolver import resolver_contract_result
from agent.ufh_pre_generation_questionnaire import (
    Decision,
    Model,
    ProjectContext,
    QuestionnaireResult,
    QuestionnaireState,
    Question,
    apply_ufh_questionnaire_answers,
    build_ufh_pre_generation_questions,
    digest,
    load_questionnaire_authoring,
    project_context_from_adapter_result,
)
from agent.ufh_pre_generation_questionnaire import QUESTIONS as QUESTION_CATALOG
from agent.ufh_project_adapter import (
    ProjectRoomUfhSource,
    ProjectUfhAdapterResult,
    build_ufh_sizing_request_from_project_room,
)
from agent.ufh_project_engineering_profile_authoring import (
    AuthoredValue,
    Test01UfhEngineeringAuthoringTemplate,
    test01_authoring_template_payload,
)
from agent.ufh_questionnaire_resolver_contract import (
    Binding,
    ResolverRequest,
    ResolverResult,
    TEST01_QUESTION_RESOLVER_MAP,
    apply_resolver_result,
    invalidate_bindings,
    make_resolver_request,
)


SessionStatus = Literal[
    "AWAITING_USER_INPUT", "AWAITING_RESOLVER", "INCOMPLETE",
    "READY_FOR_ENGINEERING", "INVALID", "STALE",
]


class ResolverExecution(Model):
    resolver_request: ResolverRequest
    resolver_result: ResolverResult


class UFHPreGenerationSession(Model):
    project_id: str
    room_id: str
    project_revision: str
    normative_profile: str
    adapter_result: ProjectUfhAdapterResult
    project_context: ProjectContext
    questionnaire_state: QuestionnaireState
    bindings: list[Binding] = Field(default_factory=list)
    resolver_executions: list[ResolverExecution] = Field(default_factory=list)
    active_questions: list[Question] = Field(default_factory=list)
    resolver_requirements: list[str] = Field(default_factory=list)
    remaining_required_engineering_fields: list[str] = Field(default_factory=list)
    status: SessionStatus
    diagnostics: list[str] = Field(default_factory=list)
    session_digest: str


def _authoring_payload(
    payload: dict[str, Any], adapter: ProjectUfhAdapterResult,
) -> dict[str, Any]:
    """Bind authoritative identity/context only; do not author physical values."""
    result = {**payload}
    result["project_context"] = {
        **payload.get("project_context", {}),
        "project_id": adapter.project_id,
        "building_id": adapter.building_id,
        "level_id": adapter.level_id,
        "room_id": adapter.room_id,
        "project_source_digest": adapter.adapter_digest,
        "room_geometry_digest": adapter.room_geometry_digest,
    }
    return result


def _template_for(adapter: ProjectUfhAdapterResult) -> dict[str, Any]:
    payload = test01_authoring_template_payload()
    payload["template_id"] = f"{adapter.project_id}:{adapter.room_id}:UFH_ENGINEERING_PROFILE_AUTHORING_V1"
    return _authoring_payload(payload, adapter)


def _session_digest(session: UFHPreGenerationSession) -> str:
    body = session.model_dump(mode="json", exclude={"session_digest"})
    return digest(body)


def _with_digest(session: UFHPreGenerationSession) -> UFHPreGenerationSession:
    session.session_digest = _session_digest(session)
    return session


def _resolve_required_paths(state: QuestionnaireState, context: ProjectContext):
    authoring = load_questionnaire_authoring(state, context)
    return authoring


def _recompute(session: UFHPreGenerationSession) -> UFHPreGenerationSession:
    state = session.questionnaire_state
    questionnaire = build_ufh_pre_generation_questions(session.project_context, state)
    # Failed local lookups remain actionable. The questionnaire core records a
    # decision as a resolver requirement; re-expose its active question until
    # a successful binding supplies the target.
    active = list(questionnaire.questions)
    successful_question_ids = {
        key for key, item in TEST01_QUESTION_RESOLVER_MAP.items()
        if any(binding.request.resolver_type == item["handoff"]
               and key in binding.request.source_question_ids
               and binding.result.status == "RESOLVED"
               and set(item["outputs"]) <= {
                   value.target_authoring_field for value in binding.result.values
               } for binding in session.bindings)
    }
    question_catalog = {q.question_id: q for q in QUESTION_CATALOG}
    for requirement in questionnaire.resolver_requirements:
        question_id = requirement.split(":", 1)[-1]
        if question_id == "envelope" and any(q.question_id == "envelope.source" for q in active):
            continue
        if (question_id not in successful_question_ids
                and question_id in state.decisions
                and question_id in question_catalog
                and all(q.question_id != question_id for q in active)):
            active.append(question_catalog[question_id])

    authoring_result = _resolve_required_paths(state, session.project_context)
    required_gaps = sorted(set(
        authoring_result.missing_authoring_paths
        + session.adapter_result.missing_inputs
    ))
    resolver_requirements = [
        (f"THERMAL_BOUNDARY_TEMPERATURE_UNRESOLVED:{item.split(':', 1)[-1]}"
         if item.split(":", 1)[-1] in {"below", "above"}
         and item.split(":", 1)[-1] in successful_question_ids else item)
        for item in questionnaire.resolver_requirements
    ]
    status: SessionStatus
    if session.adapter_result.status == "INVALID" or authoring_result.status == "INVALID":
        status = "INVALID"
    elif authoring_result.status == "READY" and session.adapter_result.status == "READY":
        status = "READY_FOR_ENGINEERING"
    elif active:
        status = "AWAITING_USER_INPUT"
    elif resolver_requirements:
        status = "AWAITING_RESOLVER"
    else:
        status = "INCOMPLETE"
    session.active_questions = active
    session.resolver_requirements = resolver_requirements
    session.remaining_required_engineering_fields = required_gaps
    session.status = status
    session.diagnostics = sorted({
        *session.diagnostics,
        *(f"{item.code}:{item.path or ''}" for item in session.adapter_result.diagnostics),
        *(f"{item.code}:{item.path or ''}" for item in authoring_result.diagnostics),
        *(f"RESOLVER:{execution.resolver_result.status}:{diagnostic}"
          for execution in session.resolver_executions
          for diagnostic in execution.resolver_result.diagnostics),
    })
    return _with_digest(session)


def create_ufh_pre_generation_session(
    source: ProjectRoomUfhSource,
    *,
    normative_profile: str,
    authoring_payload: dict[str, Any] | None = None,
    known_decisions: dict[str, Decision] | None = None,
) -> UFHPreGenerationSession:
    """Adapt one project room and prepare its unresolved pre-generation state."""
    adapter = build_ufh_sizing_request_from_project_room(source)
    payload = _authoring_payload(
        _template_for(adapter) if authoring_payload is None else authoring_payload,
        adapter,
    )
    state = QuestionnaireState(
        authoring=Test01UfhEngineeringAuthoringTemplate.model_validate(payload)
    )
    context = project_context_from_adapter_result(
        adapter,
        payload["project_context"].get("coordinate_system", "authoritative room boundary integer millimetres"),
        known_decisions,
    )
    session = UFHPreGenerationSession(
        project_id=adapter.project_id,
        room_id=adapter.room_id,
        project_revision=adapter.adapter_digest,
        normative_profile=normative_profile,
        adapter_result=adapter,
        project_context=context,
        questionnaire_state=state,
        status="INCOMPLETE",
        session_digest="0" * 64,
    )
    return _recompute(session)


def create_test01_ufh_pre_generation_session(
    project_directory: Path,
    ifc_directory: Path,
    *,
    normative_profile: str,
) -> UFHPreGenerationSession:
    """Read the explicitly supplied Test_01 revision binding and create a session."""
    from agent.test01_geometry_source_authority import assess_test01_geometry_authority

    decision = assess_test01_geometry_authority(project_directory, ifc_directory)
    if decision.status != "AUTHORITATIVE" or decision.ufh_source is None:
        raise ValueError("TEST01_GEOMETRY_AUTHORITY_" + decision.status + ":" + ",".join(decision.reasons))
    return create_ufh_pre_generation_session(
        decision.ufh_source, normative_profile=normative_profile,
    )


def _question_for(session: UFHPreGenerationSession, question_id: str) -> Question:
    for question in session.active_questions:
        if question.question_id == question_id:
            return question
    raise ValueError("QUESTION_NOT_ACTIVE:" + question_id)


def _resolver_contexts(
    project_id: str,
    room_id: str,
    project_revision: str,
    state: QuestionnaireState,
    normative_profile: str,
    adapter_result: ProjectUfhAdapterResult | None = None,
) -> dict[str, dict[str, str]]:
    dataset = load_climate_dataset()
    climate_request = make_climate_resolver_request(
        project_id, room_id, project_revision, state, normative_profile, dataset
    )
    contexts = {"CLIMATE_RESOLVER": climate_resolver_context(dataset, normative_profile)}
    contexts["BUILDING_CONSTRUCTION_RESOLVER"] = {"construction_bundle": "V1"}
    temp_field = next((item for item in (adapter_result.mapped_fields if adapter_result else [])
                       if item.target_path == "room.indoor_temperature_c"), None)
    decisions = state.decisions
    scope = "UNKNOWN"
    envelope_source = decisions.get("envelope.source")
    if envelope_source is not None and isinstance(envelope_source.value, dict):
        scope = envelope_source.value.get("construction_scope", "UNKNOWN")
        assemblies = envelope_source.value.get("assemblies", [])
        kinds = {item.get("boundary_kind") for item in assemblies if isinstance(item, dict)}
        if kinds and kinds <= {"EXTERIOR_WALL", "WINDOW", "EXTERIOR_DOOR"}:
            scope = "EXTERIOR_ENVELOPE"
        elif kinds and kinds == {"INTERIOR_WALL_DIFFERENT_ZONE"}:
            scope = "INTERIOR"
    contexts["ENVELOPE_OPERATING_CONDITION_RESOLVER"] = {
        "indoor_design_temperature_c": str(temp_field.value) if temp_field else "",
        "indoor_temperature_source": (f"{temp_field.provenance.source_file}#{temp_field.provenance.source_path}"
            if temp_field else ""),
        "indoor_temperature_source_digest": temp_field.provenance.source_sha256 if temp_field else "",
        "construction_scope": scope,
        "dataset_digest": __import__("agent.ufh_envelope_operating_condition_resolver",
            fromlist=["SOURCE_PACKAGE_DIGEST"]).SOURCE_PACKAGE_DIGEST,
        "relevant_project_input_digest": digest({
            "indoor_design_temperature_c": str(temp_field.value) if temp_field else None,
            "source_reference": temp_field.provenance.source_file if temp_field else None,
            "source_field": temp_field.provenance.source_path if temp_field else None,
            "construction_scope": scope,
        }),
    }
    for side in ("BELOW", "ABOVE"):
        contexts[f"BOUNDARY_CONDITION_RESOLVER:{side}"] = boundary_resolver_context(
            state, side, climate_request.dependency_digest
        )
    return contexts


def _run_one(
    session: UFHPreGenerationSession,
    request: ResolverRequest,
    result: ResolverResult,
) -> None:
    if any(item.resolver_request.resolver_request_id == request.resolver_request_id
           and item.resolver_result.status != "STALE_INPUT"
           for item in session.resolver_executions):
        return
    session.resolver_executions.append(
        ResolverExecution(resolver_request=request, resolver_result=result)
    )
    if result.status != "RESOLVED":
        return
    try:
        updated_state, binding = apply_resolver_result(
            session.questionnaire_state, request, result
        )
    except ValueError as error:
        session.diagnostics.append(str(error))
        return
    session.questionnaire_state = updated_state
    session.bindings = [
        item for item in session.bindings
        if item.request.resolver_request_id != request.resolver_request_id
    ] + [binding]


def _run_available_resolvers(
    session: UFHPreGenerationSession,
    trigger_question_id: str | None = None,
) -> UFHPreGenerationSession:
    """Execute local deterministic resolvers; never starts engineering."""
    state = session.questionnaire_state
    climate_request = make_climate_resolver_request(
        session.project_id, session.room_id, session.project_revision,
        state, session.normative_profile,
    )
    if "climate" in state.decisions:
        _run_one(session, climate_request, resolve_climate_request(climate_request))

    for side, question_id in (("BELOW", "below"), ("ABOVE", "above")):
        if question_id not in session.questionnaire_state.decisions:
            continue
        request = make_boundary_resolver_request(
            session.project_id, session.room_id, session.project_revision,
            session.questionnaire_state, side,
            climate_dependency_digest=climate_request.dependency_digest,
        )
        _run_one(session, request,
                 resolve_boundary_request(request, session.questionnaire_state))

    if {"indoor_rh", "moisture_zone"}.issubset(session.questionnaire_state.decisions):
        contexts = _resolver_contexts(session.project_id, session.room_id,
            session.project_revision, session.questionnaire_state,
            session.normative_profile, session.adapter_result)
        request = make_resolver_request(
            "ENVELOPE_OPERATING_CONDITION_RESOLVER", session.project_id,
            session.room_id, session.project_revision,
            session.questionnaire_state.decisions,
            contexts["ENVELOPE_OPERATING_CONDITION_RESOLVER"],
        )
        _run_one(session, request, resolver_contract_result(request))

    if ("envelope" in session.questionnaire_state.decisions
            and "envelope.source" in session.questionnaire_state.decisions):
        condition_dependency = next((binding.result.dependency_digest
            for binding in reversed(session.bindings)
            if binding.request.resolver_type == "ENVELOPE_OPERATING_CONDITION_RESOLVER"
            and binding.result.status == "RESOLVED"), None)
        construction_request = make_envelope_construction_request(
            session.project_id, session.room_id, session.project_revision,
            session.questionnaire_state.decisions, session.normative_profile,
            operating_condition_dependency=condition_dependency,
        )
        _run_one(session, construction_request,
                 resolve_envelope_construction_submission(
                     construction_request, session.questionnaire_state
                 ))

    mapping = TEST01_QUESTION_RESOLVER_MAP.get(trigger_question_id or "")
    if mapping is not None:
        resolver_type = mapping["handoff"]
        direct = {
            "DIRECT_AUTHORING_UPDATE",
            "DIRECT_AUTHORING_UPDATE_OR_THERMAL_RESOLVER",
            "DIRECT_AUTHORING_UPDATE_OR_LAYOUT_POLICY_RESOLVER",
        }
        if resolver_type not in {"CLIMATE_RESOLVER", "BOUNDARY_CONDITION_RESOLVER",
                                 "ENVELOPE_OPERATING_CONDITION_RESOLVER",
                                 "BUILDING_CONSTRUCTION_RESOLVER", *direct}:
            request = make_resolver_request(
                resolver_type, session.project_id, session.room_id,
                session.project_revision, session.questionnaire_state.decisions,
            )
            _run_one(session, request, ResolverResult(
                resolver_request_id=request.resolver_request_id,
                status="UNSUPPORTED",
                dependency_digest=request.dependency_digest,
                diagnostics=["RESOLVER_NOT_REGISTERED:" + resolver_type],
            ))
    return session


def apply_ufh_questionnaire_answer(
    session: UFHPreGenerationSession,
    answer: Decision,
) -> UFHPreGenerationSession:
    """Apply one active answer atomically, execute supported resolvers, refresh UI state."""
    previous = session.questionnaire_state.decisions.get(answer.question_id)
    if previous == answer:
        # Exact replay is idempotent, including after the question was resolved.
        return session.model_copy(deep=True)
    _question_for(session, answer.question_id)
    base = session.model_copy(deep=True)
    if previous is not None:
        # A failed resolution re-exposes the same question. Clear its prior
        # decision so the underlying questionnaire validator sees an active
        # unanswered item before applying the correction.
        base.questionnaire_state.decisions.pop(answer.question_id, None)

    next_state = apply_ufh_questionnaire_answers(
        base.project_context, base.questionnaire_state, [answer]
    )
    # Existing bindings are invalidated against the new answer and project
    # revision before any new resolver is run.
    next_state, invalidated = invalidate_bindings(
        next_state, base.bindings, base.project_revision,
        _resolver_contexts(base.project_id, base.room_id, base.project_revision,
                           next_state, base.normative_profile, base.adapter_result),
    )
    updated = base.model_copy(deep=True)
    updated.questionnaire_state = next_state
    updated.bindings = invalidated
    updated.diagnostics = []
    updated.resolver_executions = [
        item for item in updated.resolver_executions
        if not (answer.question_id in item.resolver_request.source_question_ids
                and item.resolver_result.status != "STALE_INPUT")
    ]
    _run_available_resolvers(updated, answer.question_id)
    return _recompute(updated)


def replace_ufh_questionnaire_answer(
    session: UFHPreGenerationSession,
    answer: Decision,
) -> UFHPreGenerationSession:
    """Replace a prior answer explicitly, invalidating dependent resolver outputs."""
    previous = session.questionnaire_state.decisions.get(answer.question_id)
    if previous is None:
        raise ValueError("QUESTION_HAS_NO_PRIOR_ANSWER:" + answer.question_id)
    if answer == previous:
        return session.model_copy(deep=True)
    question_catalog = {question.question_id: question for question in QUESTION_CATALOG}
    if answer.question_id not in question_catalog:
        raise ValueError("UNKNOWN_QUESTION:" + answer.question_id)
    base = session.model_copy(deep=True)
    state = base.questionnaire_state.model_copy(deep=True)
    state.decisions.pop(answer.question_id, None)
    state, stale = invalidate_bindings(
        state, base.bindings, base.project_revision,
        _resolver_contexts(base.project_id, base.room_id, base.project_revision,
                           state, base.normative_profile, base.adapter_result),
    )
    base.questionnaire_state = state
    base.bindings = stale
    # Once cleared, the original dependency becomes active again through the
    # existing dynamic question engine; this validates answer type/options.
    base = _recompute(base)
    return apply_ufh_questionnaire_answer(base, answer)


def rebuild_ufh_pre_generation_session(
    session: UFHPreGenerationSession,
    source: ProjectRoomUfhSource,
) -> UFHPreGenerationSession:
    """Re-evaluate a changed project revision while preserving user decisions."""
    adapter = build_ufh_sizing_request_from_project_room(source)
    state = session.questionnaire_state.model_copy(deep=True)
    state.authoring.project_context.update({
        "project_id": adapter.project_id,
        "building_id": adapter.building_id,
        "level_id": adapter.level_id,
        "room_id": adapter.room_id,
        "project_source_digest": adapter.adapter_digest,
        "room_geometry_digest": adapter.room_geometry_digest,
    })
    values = __import__("agent.ufh_project_adapter", fromlist=["collect_project_owned_ufh_values"]).collect_project_owned_ufh_values(adapter)
    context = ProjectContext(
        source_reference=adapter.source_file,
        coordinate_system=session.project_context.coordinate_system,
        known_decisions=session.project_context.known_decisions,
        project_owned_values=values,
    )
    state, stale = invalidate_bindings(
        state, session.bindings, adapter.adapter_digest,
        _resolver_contexts(adapter.project_id, adapter.room_id,
                           adapter.adapter_digest, state, session.normative_profile, adapter),
    )
    updated = session.model_copy(deep=True)
    updated.adapter_result = adapter
    updated.project_id, updated.room_id = adapter.project_id, adapter.room_id
    updated.project_revision = adapter.adapter_digest
    updated.project_context = context
    updated.questionnaire_state = state
    updated.bindings = stale
    updated.resolver_executions = [
        ResolverExecution(resolver_request=b.request, resolver_result=b.result)
        for b in stale
    ]
    updated.diagnostics = []
    if adapter.adapter_digest != session.project_revision:
        updated.resolver_executions = [
            item for item in updated.resolver_executions
            if item.resolver_result.status != "STALE_INPUT"
        ]
        _run_available_resolvers(updated)
    return _recompute(updated)


def profile_readiness(session: UFHPreGenerationSession):
    """Return the existing authoring-loader result; never runs engineering."""
    return load_questionnaire_authoring(session.questionnaire_state, session.project_context)


__all__ = [
    "ResolverExecution", "UFHPreGenerationSession",
    "apply_ufh_questionnaire_answer", "create_test01_ufh_pre_generation_session",
    "create_ufh_pre_generation_session", "profile_readiness",
    "rebuild_ufh_pre_generation_session", "replace_ufh_questionnaire_answer",
]

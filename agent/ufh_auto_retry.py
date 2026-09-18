"""Bounded exact-count retry from hydraulic split recommendation to reassessment."""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field

from agent.floor_heating_sizing import UFHSizingRequest, UFHRequirement
from agent.ufh_candidate_adapter import (
    IntegrationAssessment,
    SizingEngineeringResult,
    UFHEngineeringIntegrationInputs,
    size_ufh_requirement_with_engineering,
)
from agent.ufh_engineering_models import EngineeringModel, Status


class UFHRetryAttempt(EngineeringModel):
    attempt_index: int = Field(ge=0, le=2)
    requested_circuit_count: int | None = Field(default=None, ge=1, le=3)
    actual_circuit_count: int = Field(ge=0, le=3)
    routing_status: Literal["planned", "partial", "impossible"]
    circuit_ids: tuple[str, ...] = ()
    circuit_lengths_mm: tuple[int, ...] = ()
    circuit_served_areas_m2: tuple[float | None, ...] = ()
    circuit_allocated_heat_w: tuple[float | None, ...] = ()
    circuit_heat_flux_w_m2: tuple[float | None, ...] = ()
    engineering_status: str = Field(min_length=1, max_length=96)
    retry_reason: str | None = Field(default=None, max_length=128)
    circuit_flows_kg_h: tuple[float | None, ...] = ()
    circuit_pressures_pa: tuple[float | None, ...] = ()
    diagnostics: tuple[str, ...] = ()
    sizing_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    routing_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    engineering_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class UFHAutoRetryResult(EngineeringModel):
    project_id: str
    room_id: str
    initial_circuit_count: int = Field(ge=0, le=3)
    status: Literal[
        "ACCEPTED_INITIAL",
        "ACCEPTED_AFTER_RETRY",
        "FAILED_NO_ENGINEERING_FEASIBLE_CANDIDATE",
    ]
    attempts: tuple[UFHRetryAttempt, ...] = Field(min_length=1, max_length=3)
    final_accepted_candidate: SizingEngineeringResult | None = None
    diagnostics: tuple[str, ...] = ()
    result_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


_RETRYABLE_PRESSURE_STATUSES = {
    Status.REJECTED_CIRCUIT_PRESSURE.value,
    Status.REJECTED_MANUFACTURER_PRESSURE_LIMIT.value,
}


def _status(value: object) -> str:
    return value.value if isinstance(value, Status) else str(value)


def _attempt_diagnostics(
    result: SizingEngineeringResult,
) -> tuple[str, ...]:
    route = tuple(
        f"ROUTING:{code}" for code in result.coverage.diagnostics
    )
    engineering = tuple(
        f"ENGINEERING:{item.code}:{item.message}"
        for item in result.engineering.diagnostics
    )
    return route + engineering


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _attempt(
    result: SizingEngineeringResult,
    index: int,
    requested_count: int | None,
    retry_reason: str | None,
) -> UFHRetryAttempt:
    sizing = result.sizing
    coverage = result.coverage
    engineering = result.engineering
    actual_count = len(coverage.circuit_routes)
    circuit_by_id = {c.candidate.circuit_id: c for c in engineering.circuits}
    ordered_ids = tuple(route.id for route in coverage.circuit_routes)
    flows = tuple(
        circuit_by_id[circuit_id].mass_flow_kg_h
        if circuit_id in circuit_by_id else None
        for circuit_id in ordered_ids
    )
    pressures = tuple(
        circuit_by_id[circuit_id].pressure.en_circuit_pressure_pa
        if circuit_id in circuit_by_id and circuit_by_id[circuit_id].pressure
        else None
        for circuit_id in ordered_ids
    )
    areas = tuple(
        circuit_by_id[circuit_id].candidate.served_area_m2
        if circuit_id in circuit_by_id else None
        for circuit_id in ordered_ids
    )
    allocated_heat = tuple(
        circuit_by_id[circuit_id].candidate.allocated_required_heat_w
        if circuit_id in circuit_by_id else None
        for circuit_id in ordered_ids
    )
    heat_flux = tuple(
        circuit_by_id[circuit_id].candidate.required_heat_flux_w_m2
        if circuit_id in circuit_by_id else None
        for circuit_id in ordered_ids
    )
    candidate_digest = _digest({
        "sizing_digest": sizing.sizing_digest,
        "routing_digest": coverage.plan_digest,
        "engineering_digest": engineering.assessment_digest,
        "requested_circuit_count": requested_count,
        "actual_circuit_count": actual_count,
        "circuit_ids": ordered_ids,
        "circuit_lengths_mm": tuple(r.length_mm for r in coverage.circuit_routes),
    })
    return UFHRetryAttempt(
        attempt_index=index,
        requested_circuit_count=requested_count,
        actual_circuit_count=actual_count,
        routing_status=coverage.status,
        circuit_ids=ordered_ids,
        circuit_lengths_mm=tuple(r.length_mm for r in coverage.circuit_routes),
        circuit_served_areas_m2=areas,
        circuit_allocated_heat_w=allocated_heat,
        circuit_heat_flux_w_m2=heat_flux,
        engineering_status=_status(engineering.engineering_status),
        retry_reason=retry_reason,
        circuit_flows_kg_h=flows,
        circuit_pressures_pa=pressures,
        diagnostics=_attempt_diagnostics(result),
        sizing_digest=sizing.sizing_digest,
        routing_digest=coverage.plan_digest,
        engineering_digest=engineering.assessment_digest,
        candidate_digest=candidate_digest,
    )


def _is_accepted(result: SizingEngineeringResult) -> bool:
    assessment = result.engineering
    return (
        _status(assessment.engineering_status) == Status.ACCEPTED.value
        and assessment.routing_accepted_legacy_policy
        and assessment.sizing_coverage_accepted
    )


def _retry_cause(assessment: IntegrationAssessment) -> str | None:
    """Only explicit hydraulic pressure/SPLIT_REQUIRED semantics permit retry."""
    status = _status(assessment.engineering_status)
    if (
        assessment.recommendation != "SPLIT_REQUIRED"
        or status not in _RETRYABLE_PRESSURE_STATUSES
        or not assessment.routing_accepted_legacy_policy
        or not assessment.sizing_coverage_accepted
    ):
        return None
    codes = {item.code for item in assessment.diagnostics}
    if "EN_CIRCUIT_PRESSURE_LIMIT_EXCEEDED" in codes:
        return "EN_CIRCUIT_PRESSURE_LIMIT_EXCEEDED"
    if "MANUFACTURER_PRESSURE_LIMIT_EXCEEDED" in codes:
        return "MANUFACTURER_PRESSURE_LIMIT_EXCEEDED"
    return "SPLIT_REQUIRED"


def _legacy_minimum_blocked(
    source: SizingEngineeringResult,
    requested_count: int,
) -> str | None:
    minimum = source.coverage.circuit_budget[0].minimum_length_mm if source.coverage.circuit_budget else 40_000
    available = sum(route.length_mm for route in source.coverage.circuit_routes)
    required = requested_count * minimum
    if available < required:
        return (
            "LEGACY_MINIMUM_CIRCUIT_LENGTH_BLOCKED_SPLIT: "
            f"source route length total {available} mm is below {required} mm "
            f"needed for {requested_count} circuits at the {minimum} mm minimum"
        )
    return None


def _finish(
    *,
    request: UFHSizingRequest,
    initial_count: int,
    attempts: list[UFHRetryAttempt],
    status: Literal[
        "ACCEPTED_INITIAL",
        "ACCEPTED_AFTER_RETRY",
        "FAILED_NO_ENGINEERING_FEASIBLE_CANDIDATE",
    ],
    accepted: SizingEngineeringResult | None,
    diagnostics: list[str],
) -> UFHAutoRetryResult:
    content = {
        "project_id": request.coverage_request.project_id,
        "room_id": request.coverage_request.room_id,
        "initial_circuit_count": initial_count,
        "status": status,
        "attempts": [item.model_dump(mode="json") for item in attempts],
        "final_accepted_candidate": (
            {
                "sizing": accepted.sizing.sizing_digest,
                "coverage": accepted.coverage.plan_digest,
                "engineering": accepted.engineering.assessment_digest,
            }
            if accepted else None
        ),
        "diagnostics": diagnostics,
    }
    return UFHAutoRetryResult(
        project_id=request.coverage_request.project_id,
        room_id=request.coverage_request.room_id,
        initial_circuit_count=initial_count,
        status=status,
        attempts=tuple(attempts),
        final_accepted_candidate=accepted,
        diagnostics=tuple(diagnostics),
        result_digest=_digest(content),
    )


def assess_with_automatic_split_retry(
    request: UFHSizingRequest,
    inputs: UFHEngineeringIntegrationInputs,
) -> UFHAutoRetryResult:
    """Run one initial candidate and at most two exact-count retries, through 3 circuits."""
    initial_requested = request.coverage_request.requested_circuit_count
    current_request = request
    current = size_ufh_requirement_with_engineering(
        current_request, inputs, assess_balance_after_pressure_failure=True
    )
    initial_count = len(current.coverage.circuit_routes)
    attempts: list[UFHRetryAttempt] = [
        _attempt(current, 0, initial_requested, None)
    ]
    diagnostics = list(attempts[0].diagnostics)

    if _is_accepted(current):
        return _finish(
            request=request,
            initial_count=initial_count,
            attempts=attempts,
            status="ACCEPTED_INITIAL",
            accepted=current,
            diagnostics=diagnostics,
        )

    count = initial_count
    previous = current
    trigger = _retry_cause(previous.engineering)
    while trigger is not None and count < 3:
        requested = count + 1
        source = previous
        legacy_block = _legacy_minimum_blocked(source, requested)
        retry_coverage = request.coverage_request.model_copy(
            update={"requested_circuit_count": requested}
        )
        retry_request = request.model_copy(update={"coverage_request": retry_coverage})
        current = size_ufh_requirement_with_engineering(
            retry_request, inputs, assess_balance_after_pressure_failure=True
        )
        attempt = _attempt(current, len(attempts), requested, trigger)
        if (
            legacy_block
            and "REQUESTED_CIRCUIT_COUNT_NOT_FEASIBLE"
            in current.coverage.diagnostics
        ):
            attempt = attempt.model_copy(update={
                "diagnostics": (*attempt.diagnostics, legacy_block),
            })
            diagnostics.append(legacy_block)
        attempts.append(attempt)
        diagnostics.extend(attempt.diagnostics)

        if _is_accepted(current):
            return _finish(
                request=request,
                initial_count=initial_count,
                attempts=attempts,
                status="ACCEPTED_AFTER_RETRY",
                accepted=current,
                diagnostics=list(dict.fromkeys(diagnostics)),
            )

        if "REQUESTED_CIRCUIT_COUNT_NOT_FEASIBLE" in current.coverage.diagnostics:
            diagnostics.append("REQUESTED_CIRCUIT_COUNT_NOT_FEASIBLE")
            break
        trigger = _retry_cause(current.engineering)
        if trigger is None:
            break
        count = requested
        previous = current

    if count >= 3 and trigger is not None:
        diagnostics.append("MAX_CIRCUIT_COUNT_REACHED")
    diagnostics.append("FAILED_NO_ENGINEERING_FEASIBLE_CANDIDATE")
    return _finish(
        request=request,
        initial_count=initial_count,
        attempts=attempts,
        status="FAILED_NO_ENGINEERING_FEASIBLE_CANDIDATE",
        accepted=None,
        diagnostics=list(dict.fromkeys(diagnostics)),
    )


__all__ = [
    "UFHAutoRetryResult",
    "UFHRetryAttempt",
    "assess_with_automatic_split_retry",
]

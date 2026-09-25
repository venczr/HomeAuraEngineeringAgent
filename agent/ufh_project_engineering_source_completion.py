"""Read-only completion audit for Test_01 UFH engineering profile sources.

The module intentionally binds only explicit, provenance-bearing project
engineering metadata. Room-extraction observations such as precomputed heat
loss or outdoor temperature are reported as inspected candidates, but are not
promoted into the UFH engineering profile unless the source already carries
the contract semantics required by UFH_PROJECT_ENGINEERING_INPUT_CONTRACT_V1.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import Field

from agent.project_models import StrictProjectModel
from agent.ufh_project_adapter import (
    ProjectFieldProvenance,
    ProjectRoomUfhSource,
    ProjectUfhAdapterResult,
    build_ufh_sizing_request_from_project_room,
)


PROFILE_SOURCE_FILENAMES = (
    "ufh_project_engineering_profile.json",
    "exports/engineering/ufh_project_engineering_profile.json",
    "exports/ufh/ufh_project_engineering_profile.json",
)


class SourceCandidateAudit(StrictProjectModel):
    source_file: str = Field(min_length=1, max_length=1024)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_path: str = Field(min_length=1, max_length=512)
    observed_value: object | None = None
    target_path: str | None = Field(default=None, max_length=256)
    status: Literal["BOUND", "ALREADY_BOUND", "INSPECTED_NOT_AUTHORITY", "SOURCE_NOT_FOUND"]
    reason: str = Field(min_length=1, max_length=512)


class SourceCompletionResult(StrictProjectModel):
    status: Literal["UNCHANGED_INCOMPLETE", "IMPROVED_INCOMPLETE", "READY", "INVALID"]
    project_id: str
    room_id: str
    source_before_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_after_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    adapter_before: ProjectUfhAdapterResult
    adapter_after: ProjectUfhAdapterResult
    inspected_candidates: list[SourceCandidateAudit] = Field(default_factory=list)
    new_bindings: list[SourceCandidateAudit] = Field(default_factory=list)
    provenance_coverage: dict[str, object]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _gap_counts(adapter_result: ProjectUfhAdapterResult) -> dict[str, int]:
    counts: dict[str, int] = {}
    for gap in adapter_result.classified_gaps:
        counts[gap.source_class] = counts.get(gap.source_class, 0) + 1
    return dict(sorted(counts.items()))


def _true_external_gap_paths(adapter_result: ProjectUfhAdapterResult) -> set[str]:
    return {
        gap.path for gap in adapter_result.classified_gaps
        if gap.required_externally
    }


def _candidate(
    *,
    path: Path,
    source_path: str,
    observed_value: object | None,
    target_path: str | None,
    status: Literal["BOUND", "ALREADY_BOUND", "INSPECTED_NOT_AUTHORITY", "SOURCE_NOT_FOUND"],
    reason: str,
) -> SourceCandidateAudit:
    digest = _sha256(path) if path.is_file() else hashlib.sha256(
        f"missing:{path}".encode("utf-8")
    ).hexdigest()
    return SourceCandidateAudit(
        source_file=str(path),
        source_sha256=digest,
        source_path=source_path,
        observed_value=observed_value,
        target_path=target_path,
        status=status,
        reason=reason,
    )


def complete_project_engineering_profile_sources(
    source: ProjectRoomUfhSource,
    project_directory: Path,
) -> SourceCompletionResult:
    """Inspect existing project sources and bind only authoritative UFH inputs.

    For Test_01 this function is deliberately conservative: the current
    project directory contains room extraction observations, but no linked UFH
    engineering profile source. The returned source remains unchanged and the
    adapter keeps failing closed.
    """
    project_directory = project_directory.resolve()
    before = build_ufh_sizing_request_from_project_room(source)
    source_before_digest = source.source_sha256
    candidates: list[SourceCandidateAudit] = []
    bindings: list[SourceCandidateAudit] = []

    rooms_path = Path(source.source_file)
    mapped = {item.target_path: item for item in before.mapped_fields}

    for target_path, source_field, reason in (
        (
            "sizing.room.indoor_temperature_c",
            "HeatingTemperatureC",
            "Room extraction already provides the indoor design setpoint; no new profile binding is needed.",
        ),
        (
            "sizing.room.insulation.air_changes_per_hour",
            "AirExchangeRate",
            "Room extraction already provides ACH with provenance; remaining ventilation heat-capacity factor is a separate building-physics input.",
        ),
    ):
        field = mapped.get(target_path.removeprefix("sizing."))
        if field is not None:
            candidates.append(_candidate(
                path=rooms_path,
                source_path=field.provenance.source_path,
                observed_value=field.value,
                target_path=target_path,
                status="ALREADY_BOUND",
                reason=reason,
            ))

    for target_path, source_field, reason in (
        (
            "sizing.room.outdoor_design_temperature_c",
            "OutdoorTemperatureC",
            "Stored room extraction value lacks outdoor design-condition authority under the current contract.",
        ),
        (
            "sizing.room.insulation.floor_boundary_temperature_c",
            "SupplyAirTemperatureC",
            "Supply-air temperature is not a floor-boundary or below-room design condition.",
        ),
        (
            "sizing.room.insulation.exterior_wall_u_value_w_m2k",
            "StructuralHeatLossW",
            "Precomputed heat-loss output is a calculation result, not a wall U-value source.",
        ),
        (
            "sizing.floor_construction.declared_output_at_100mm_w_m2",
            "HeatLossWM2",
            "Room heat-loss intensity is not a floor-construction product output declaration.",
        ),
    ):
        value = getattr(source.selected_room, source_field, None)
        if value is not None:
            candidates.append(_candidate(
                path=rooms_path,
                source_path=f"$.Rooms[].{source_field}",
                observed_value=value,
                target_path=target_path,
                status="INSPECTED_NOT_AUTHORITY",
                reason=reason,
            ))

    for relative_name in PROFILE_SOURCE_FILENAMES:
        profile_path = project_directory / relative_name
        if not profile_path.is_file():
            candidates.append(_candidate(
                path=profile_path,
                source_path="$",
                observed_value=None,
                target_path=None,
                status="SOURCE_NOT_FOUND",
                reason="No explicit linked UFHProjectEngineeringProfile source exists at this reviewed project path.",
            ))

    # No mutation: if a profile source is introduced later, it should be parsed
    # by a separate bounded block with schema-specific tests.
    completed_source = source
    after = build_ufh_sizing_request_from_project_room(completed_source)
    before_external = _true_external_gap_paths(before)
    after_external = _true_external_gap_paths(after)
    newly_covered = sorted(before_external - after_external)
    status: Literal["UNCHANGED_INCOMPLETE", "IMPROVED_INCOMPLETE", "READY", "INVALID"]
    if after.status == "READY":
        status = "READY"
    elif after.status == "INVALID":
        status = "INVALID"
    elif newly_covered:
        status = "IMPROVED_INCOMPLETE"
    else:
        status = "UNCHANGED_INCOMPLETE"
    denominator = len(before_external)
    coverage_percent = (len(newly_covered) / denominator * 100.0) if denominator else 100.0

    return SourceCompletionResult(
        status=status,
        project_id=source.project_id,
        room_id=source.room_id,
        source_before_digest=source_before_digest,
        source_after_digest=completed_source.source_sha256,
        adapter_before=before,
        adapter_after=after,
        inspected_candidates=candidates,
        new_bindings=bindings,
        provenance_coverage={
            "definition": "newly covered required-external classified gap paths divided by required-external gap paths before completion",
            "before_required_external_gap_count": denominator,
            "after_required_external_gap_count": len(after_external),
            "newly_covered_gap_count": len(newly_covered),
            "newly_covered_paths": newly_covered,
            "percent": round(coverage_percent, 6),
            "before_by_category": _gap_counts(before),
            "after_by_category": _gap_counts(after),
            "accepted_new_bindings_with_provenance": len(bindings),
        },
    )


__all__ = [
    "PROFILE_SOURCE_FILENAMES",
    "SourceCandidateAudit",
    "SourceCompletionResult",
    "complete_project_engineering_profile_sources",
]

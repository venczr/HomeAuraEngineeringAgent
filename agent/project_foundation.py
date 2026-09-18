from __future__ import annotations

import hashlib
import json

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel, ValidationError

from agent.domain_models import DomainDocument
from agent.project_models import (
    CanonicalProjectModel,
    ProjectJsonError,
    ProjectSeed,
    ProjectLifecycleStatus,
    ProjectSeedStatus,
    SheetManifest,
    SheetManifestReference,
    SourcePoint,
    SourcePointKind,
    SourcePointState,
)


PROJECT_FOUNDATION_NAMESPACE = UUID(
    "c387674e-b912-52a1-8e72-a5e7e03d8387"
)
ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_SHEET_MANIFEST_PATH = (
    ROOT_DIRECTORY / "config" / "sheet_manifest.v1.json"
)


class ProjectFoundationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def canonical_json_bytes(value: BaseModel | Any) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise ProjectFoundationError(
            "canonical_json_invalid",
            "Value cannot be serialized as canonical JSON.",
        ) from error
    return text.encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_sheet_manifest(
    path: Path | None = None,
) -> SheetManifest:
    manifest_path = path or DEFAULT_SHEET_MANIFEST_PATH
    try:
        raw_bytes = manifest_path.read_bytes()
        return SheetManifest.model_validate_json(raw_bytes)
    except (
        OSError,
        ProjectJsonError,
        ValidationError,
        RecursionError,
    ) as error:
        raise ProjectFoundationError(
            "sheet_manifest_invalid",
            "Sheet manifest cannot be read as strict JSON.",
        ) from error


def sheet_manifest_reference(
    path: Path | None = None,
) -> SheetManifestReference:
    manifest = load_sheet_manifest(path)
    manifest_hash = sha256_hex(canonical_json_bytes(manifest))
    return SheetManifestReference(
        manifest_id=manifest.manifest_id,
        manifest_version=manifest.manifest_version,
        manifest_sha256=manifest_hash,
    )


def _point_identity_payload(
    point: SourcePoint,
) -> dict[str, Any]:
    payload = point.model_dump(mode="json")
    payload["evidence"].pop("observed_at", None)
    return payload


def _build_seed(
    *,
    project_stable_id: UUID,
    drawing_name: str,
    domain_schema_version: str,
    domain_sha256: str,
    source_points: list[SourcePoint],
    required_source_point_kinds: list[SourcePointKind],
    revision: int,
    created_at: datetime,
) -> ProjectSeed:
    ordered_points = sorted(
        source_points,
        key=lambda point: (
            point.kind.value,
            point.revision,
            str(point.source_point_id),
        ),
    )
    ordered_required = sorted(
        required_source_point_kinds,
        key=lambda item: item.value,
    )

    active_ready_kinds = {
        point.kind
        for point in ordered_points
        if point.active
        and point.is_human_confirmed()
    }
    missing = [
        kind
        for kind in ordered_required
        if kind not in active_ready_kinds
    ]
    status = (
        ProjectSeedStatus.READY
        if not missing
        else ProjectSeedStatus.INCOMPLETE
    )

    identity_payload = {
        "schema_version": "1.0",
        "revision": revision,
        "project_stable_id": str(project_stable_id),
        "drawing_name": drawing_name,
        "domain_schema_version": domain_schema_version,
        "domain_sha256": domain_sha256,
        "source_points": [
            _point_identity_payload(point)
            for point in ordered_points
        ],
        "required_source_point_kinds": [
            item.value
            for item in ordered_required
        ],
    }
    input_sha256 = sha256_hex(
        canonical_json_bytes(identity_payload)
    )
    seed_id = uuid5(
        PROJECT_FOUNDATION_NAMESPACE,
        (
            f"project/{project_stable_id}/"
            f"seed/{revision}/{input_sha256}"
        ),
    )

    return ProjectSeed(
        seed_id=seed_id,
        revision=revision,
        project_stable_id=project_stable_id,
        drawing_name=drawing_name,
        domain_schema_version=domain_schema_version,
        domain_sha256=domain_sha256,
        input_sha256=input_sha256,
        source_points=ordered_points,
        required_source_point_kinds=ordered_required,
        missing_required_source_points=missing,
        status=status,
        created_at=created_at,
    )


def build_project_seed(
    domain: DomainDocument,
    source_points: list[SourcePoint],
    *,
    created_at: datetime,
    revision: int = 1,
) -> ProjectSeed:
    return _build_seed(
        project_stable_id=domain.project.stable_id,
        drawing_name=domain.project.drawing_name,
        domain_schema_version=domain.schema_version,
        domain_sha256=sha256_hex(
            canonical_json_bytes(domain)
        ),
        source_points=source_points,
        required_source_point_kinds=[
            SourcePointKind.BOILER_ROOM,
            SourcePointKind.WATER_INLET,
        ],
        revision=revision,
        created_at=created_at,
    )


def build_canonical_project_preview(
    domain: DomainDocument,
    source_points: list[SourcePoint],
    *,
    sheet_manifest: SheetManifestReference,
    created_at: datetime,
    revision: int = 1,
    status: ProjectLifecycleStatus = ProjectLifecycleStatus.DRAFT,
) -> CanonicalProjectModel:
    """Build a deterministic, in-memory PROJECT preview from DOMAIN output.

    The caller supplies the already-adapted DOMAIN document and manifest
    reference.  This keeps preview construction read-only while making the
    DOMAIN-to-PROJECT boundary explicit and reusable by future preview
    consumers.
    """
    seed = build_project_seed(
        domain,
        source_points,
        created_at=created_at,
        revision=revision,
    )
    return CanonicalProjectModel(
        project_id=domain.project.stable_id,
        revision=revision,
        status=status,
        domain=domain,
        seed=seed,
        sheet_manifest=sheet_manifest,
    )


def replace_active_source_point(
    seed: ProjectSeed,
    replacement: SourcePoint,
    *,
    created_at: datetime,
) -> ProjectSeed:
    if not replacement.active:
        raise ProjectFoundationError(
            "source_point_replacement_invalid",
            "Replacement source point must be active.",
        )
    if replacement.state not in {
        SourcePointState.MARKED,
        SourcePointState.ACCEPTED,
    }:
        raise ProjectFoundationError(
            "source_point_replacement_invalid",
            "Replacement source point must be marked or accepted.",
        )

    same_kind = [
        point
        for point in seed.source_points
        if point.kind == replacement.kind
    ]
    expected_revision = (
        max(
            (point.revision for point in same_kind),
            default=0,
        )
        + 1
    )
    if replacement.revision != expected_revision:
        raise ProjectFoundationError(
            "source_point_revision_invalid",
            "Replacement source point revision is not sequential.",
        )
    if any(
        point.source_point_id == replacement.source_point_id
        for point in seed.source_points
    ):
        raise ProjectFoundationError(
            "source_point_identity_duplicate",
            "Replacement source point id already exists.",
        )

    updated: list[SourcePoint] = []
    for point in seed.source_points:
        if point.kind == replacement.kind and point.active:
            updated.append(
                SourcePoint.model_validate(
                    {
                        **point.model_dump(),
                        "active": False,
                        "state": SourcePointState.REPLACED,
                    }
                )
            )
        else:
            updated.append(point)
    updated.append(replacement)

    return _build_seed(
        project_stable_id=seed.project_stable_id,
        drawing_name=seed.drawing_name,
        domain_schema_version=seed.domain_schema_version,
        domain_sha256=seed.domain_sha256,
        source_points=updated,
        required_source_point_kinds=(
            seed.required_source_point_kinds
        ),
        revision=seed.revision + 1,
        created_at=created_at,
    )

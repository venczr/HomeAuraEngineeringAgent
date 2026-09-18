"""Generic import of frozen, explicitly attributed visual/OCR review evidence."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field, JsonValue

from agent.drawing_understanding import (
    Model, ObservationKind, Geometry, Point, Observation, ObservationArtifact, SourceEvidence,
)
from agent.drawing_perception import merge_reviewed_observations


class ReviewedItem(Model):
    item_id: str
    kind: ObservationKind
    text: str | None = None
    geometry_kind: Literal["POINT", "SEGMENT", "POLYLINE", "POLYGON", "BBOX"] | None = None
    coordinates: tuple[tuple[Decimal, Decimal], ...] = ()
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    limitation: str


class ReviewedPage(Model):
    source_id: str
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    page_or_frame: int = Field(ge=0)
    coordinate_unit: Literal["pt", "px", "m", "mm"]
    items: tuple[ReviewedItem, ...]


class VisualReviewPackage(Model):
    schema_version: Literal["1.0"]
    reviewer: str
    reviewed_at: str
    method: str
    artifact_role: Literal["FROZEN_PERCEPTION_REVIEW_FIXTURE"]
    pages: tuple[ReviewedPage, ...]


def apply_visual_review(artifact: ObservationArtifact, package: VisualReviewPackage) -> ObservationArtifact:
    matches = [p for p in package.pages if p.source_id == artifact.source.source_id and
               p.page_or_frame == artifact.source.page_or_frame]
    if len(matches) != 1:
        raise ValueError("REVIEW_SOURCE_PAGE_NOT_UNIQUE")
    page = matches[0]
    if page.source_hash != artifact.source.source_hash or page.coordinate_unit != artifact.source.coordinate_frame.unit:
        raise ValueError("STALE_OR_INCOMPATIBLE_VISUAL_REVIEW")
    evidence = SourceEvidence(source_id=page.source_id, source_hash=page.source_hash,
        reference=artifact.source.provenance.reference+f"; page {page.page_or_frame}; review {package.reviewed_at}",
        method=package.reviewer+": "+package.method, authority="PROJECT_DOCUMENT_OBSERVATION")
    observations = []
    for item in page.items:
        geometry = (Geometry(frame=artifact.source.coordinate_frame, kind=item.geometry_kind,
            points=tuple(Point(x=x, y=y) for x, y in item.coordinates)) if item.geometry_kind else None)
        if item.coordinates and geometry is None:
            raise ValueError("REVIEW_GEOMETRY_KIND_REQUIRED")
        observations.append(Observation(observation_id=page.source_id+":review:"+item.item_id,
            kind=item.kind, evidence=evidence, geometry=geometry, text=item.text,
            attributes=item.attributes, quality="MEDIUM", limitation=item.limitation))
    return merge_reviewed_observations(artifact, tuple(observations))

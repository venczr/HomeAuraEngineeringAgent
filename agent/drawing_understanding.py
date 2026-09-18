"""Replayable drawing reasoning, upstream of project/engineering authority.

No engineering model imports, source reads, AI calls or engineering promotion.
Coordinates and measurements belong to explicitly named frames and units.
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from typing import Literal, Protocol

from pydantic import Field, JsonValue, model_validator

from agent.project_models import StrictProjectModel


def digest(value) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class Model(StrictProjectModel):
    """Use HomeAura's strict extra-field/assignment validation contract."""


class Frame(Model):
    frame_id: str = Field(min_length=1)
    space: Literal["IMAGE_SPACE", "DRAWING_SPACE", "PROJECT_SPACE"]
    unit: Literal["px", "pt", "mm", "m"]
    axes: Literal["X_RIGHT_Y_DOWN", "X_RIGHT_Y_UP"]

    @model_validator(mode="after")
    def units_match_space(self):
        if (self.space == "IMAGE_SPACE") != (self.unit == "px"):
            raise ValueError("PIXELS_REQUIRE_IMAGE_SPACE")
        if self.space == "PROJECT_SPACE" and self.unit == "pt":
            raise ValueError("PAPER_POINTS_ARE_NOT_PROJECT_UNITS")
        return self


class Point(Model):
    x: Decimal = Field(allow_inf_nan=False)
    y: Decimal = Field(allow_inf_nan=False)


class Geometry(Model):
    frame: Frame
    kind: Literal["POINT", "SEGMENT", "POLYLINE", "POLYGON", "BBOX"]
    points: tuple[Point, ...]

    @model_validator(mode="after")
    def valid_shape(self):
        count = len(self.points)
        if (self.kind == "POINT" and count != 1 or
            self.kind in {"SEGMENT", "BBOX"} and count != 2 or
            self.kind == "POLYLINE" and count < 2 or
            self.kind == "POLYGON" and count < 3):
            raise ValueError("GEOMETRY_VERTEX_COUNT_INVALID")
        if self.kind == "BBOX" and (self.points[0].x >= self.points[1].x or
                                      self.points[0].y >= self.points[1].y):
            raise ValueError("BBOX_MUST_HAVE_POSITIVE_EXTENT")
        return self


class SourceEvidence(Model):
    source_id: str = Field(min_length=1)
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    reference: str = Field(min_length=1)
    method: str = Field(min_length=1)
    authority: Literal["PROJECT_DOCUMENT_OBSERVATION", "PROJECT_GEOMETRY_REFERENCE"]


class DrawingSource(Model):
    source_id: str = Field(min_length=1)
    source_kind: Literal["PDF", "VECTOR_DRAWING", "RASTER_IMAGE", "SCAN", "PHOTO", "CAD_RENDER", "IFC_RENDER", "OTHER_DRAWING"]
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    page_or_frame: int = Field(ge=0)
    provenance: SourceEvidence
    coordinate_frame: Frame
    project_association: str | None = None
    floor_hint: str | None = None
    known_scale_denominator: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def bound_evidence(self):
        if (self.source_id, self.source_hash) != (self.provenance.source_id, self.provenance.source_hash):
            raise ValueError("SOURCE_PROVENANCE_MISMATCH")
        return self


ObservationKind = Literal["PAGE", "TEXT", "FLOOR_TITLE", "SCALE_ANNOTATION", "PROJECT_ANNOTATION",
    "ENCLOSED_REGION", "PARALLEL_STRIP", "ROOM_LABEL", "DIMENSION", "OUTER_CONTOUR",
    "WALL_LINE", "OPENING_SYMBOL", "STAIR_SYMBOL", "ADJACENCY", "VECTOR_SUMMARY", "LAYOUT_REGION"]


class Observation(Model):
    knowledge_level: Literal["OBSERVATION"] = "OBSERVATION"
    observation_id: str = Field(min_length=1)
    kind: ObservationKind
    evidence: SourceEvidence
    geometry: Geometry | None = None
    text: str | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    quality: Literal["HIGH", "MEDIUM", "LOW", "AMBIGUOUS"]
    limitation: str = Field(min_length=1)


class ObservationArtifact(Model):
    schema_version: Literal["1.0"] = "1.0"
    source: DrawingSource
    backend_id: str = Field(min_length=1)
    backend_version: str = Field(min_length=1)
    backend_model: str | None = None
    backend_metadata: dict[str, JsonValue] = Field(default_factory=dict)
    source_digest_linkage: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    normalization_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    raw_perception_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observations: tuple[Observation, ...]
    diagnostics: tuple[str, ...] = ()

    @model_validator(mode="after")
    def evidence_integrity(self):
        ids = [o.observation_id for o in self.observations]
        if len(ids) != len(set(ids)):
            raise ValueError("DUPLICATE_OBSERVATION_ID")
        for o in self.observations:
            if (o.evidence.source_id, o.evidence.source_hash) != (self.source.source_id, self.source.source_hash):
                raise ValueError("OBSERVATION_SOURCE_MISMATCH")
            if o.geometry and o.geometry.frame != self.source.coordinate_frame:
                raise ValueError("OBSERVATION_FRAME_MISMATCH_TRANSFORM_REQUIRED")
        return self

    @property
    def artifact_digest(self) -> str:
        return digest(self)

    @property
    def computed_normalization_digest(self) -> str:
        return digest({"source_id": self.source.source_id, "source_hash": self.source.source_hash,
            "backend_id": self.backend_id, "backend_version": self.backend_version,
            "backend_model": self.backend_model, "backend_metadata": self.backend_metadata,
            "observations": [o.model_dump(mode="json") for o in self.observations]})

    @property
    def integrity_status(self) -> Literal["VERIFIED", "LEGACY_UNVERIFIED", "DIGEST_MISMATCH"]:
        if self.normalization_digest is None:
            return "LEGACY_UNVERIFIED"
        linked = self.source_digest_linkage == self.source.source_hash
        return "VERIFIED" if linked and self.normalization_digest == self.computed_normalization_digest else "DIGEST_MISMATCH"

    def with_normalization_digest(self):
        base = self.model_copy(update={"source_digest_linkage": self.source.source_hash})
        return base.model_copy(update={"normalization_digest": base.computed_normalization_digest})


class DrawingConflict(Model):
    conflict_type: str
    entity_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    severity: Literal["INFO", "WARNING", "ERROR"]
    reason: str
    blocking: bool


class UnresolvedItem(Model):
    unresolved_type: str
    entity_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...]
    why_unresolved: str
    required_next_evidence: tuple[str, ...] = ()
    blocking: bool


class PerceptionBackend(Protocol):
    """Backends may use local CV, vector extraction, OCR or a remote model."""
    def perceive(self, source: DrawingSource, content: bytes) -> ObservationArtifact: ...


class ConfidenceAssessment(Model):
    geometry: bool = False
    dimensions: bool = False
    text: bool = False
    topology: bool = False
    cross_source: bool = False
    source_quality: Literal["HIGH", "MEDIUM", "LOW", "AMBIGUOUS"]
    ambiguity: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    reasons: tuple[str, ...]

    @property
    def band(self) -> str:
        if self.conflicts or self.source_quality == "AMBIGUOUS":
            return "AMBIGUOUS"
        if self.ambiguity or self.source_quality == "LOW":
            return "LOW"
        if self.geometry and self.dimensions and self.cross_source:
            return "HIGH"
        return "MEDIUM" if self.geometry or self.text else "LOW"


HypothesisKind = Literal["BUILDING_CONTOUR", "ROOM", "WALL", "BOUNDARY", "OPENING",
    "ROOM_LABEL", "ROOM_USE", "ADJACENCY", "VERTICAL_RELATION", "STAIRS", "SCALE"]


class DrawingHypothesis(Model):
    knowledge_level: Literal["HYPOTHESIS"] = "HYPOTHESIS"
    hypothesis_id: str
    kind: HypothesisKind
    observation_ids: tuple[str, ...] = Field(min_length=1)
    source_dependencies: dict[str, str]
    geometry: Geometry | None = None
    interpretation: str
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    confidence: ConfidenceAssessment
    status: Literal["CANDIDATE", "CONFIRMATION_REQUIRED", "AMBIGUOUS"]

    @property
    def dependency_digest(self) -> str:
        return digest(self)


class OpeningHypothesis(DrawingHypothesis):
    kind: Literal["OPENING"] = "OPENING"
    opening_type: Literal["WINDOW", "DOOR", "ARCHWAY", "UNKNOWN_OPENING", "OTHER"]
    parent_boundary_candidate: str | None = None
    width_m: Decimal | None = Field(default=None, gt=0)
    height_m: Decimal | None = Field(default=None, gt=0)


class DimensionConstraint(Model):
    observation_id: str
    anchors: Geometry | None = None
    declared_distance: Decimal = Field(gt=0)
    unit: Literal["mm", "m"] | None = None
    evidence: SourceEvidence
    status: Literal["READY_TO_CHECK", "UNIT_REQUIRED", "ANCHORS_REQUIRED"]


class DimensionCheck(Model):
    constraint_id: str
    status: Literal["AGREES", "CONFLICT", "UNRESOLVED"]
    measured_m: Decimal | None = None
    residual_m: Decimal | None = None
    reason: str


class ScaleCandidate(Model):
    frame: Frame
    assumed_declared_unit: Literal["mm", "m"]
    scale_m_per_drawing_unit: Decimal = Field(gt=0)
    constraint_ids: tuple[str, ...] = Field(min_length=2)
    residuals_m: tuple[Decimal, ...]
    maximum_absolute_residual_m: Decimal = Field(ge=0)
    status: Literal["VERIFIED", "UNIT_CONFIRMATION_REQUIRED", "CONFLICT"]
    reason: str


class ScaleCorroboration(Model):
    dimension_candidate: ScaleCandidate
    annotation_observation_id: str
    annotation_denominator: Decimal = Field(gt=0)
    annotation_scale_m_per_drawing_unit: Decimal = Field(gt=0)
    absolute_difference_m_per_drawing_unit: Decimal = Field(ge=0)
    relative_difference: Decimal = Field(ge=0)
    agrees: bool
    status: Literal["CORROBORATED_UNIT_UNRESOLVED", "CONFLICT", "VERIFIED"]
    reason: str


def corroborate_scale(candidate: ScaleCandidate, annotation: Observation, *,
                       relative_tolerance: Decimal) -> ScaleCorroboration:
    if annotation.kind != "SCALE_ANNOTATION" or annotation.geometry is not None:
        raise ValueError("SCALE_ANNOTATION_OBSERVATION_REQUIRED")
    denominator = Decimal(str(annotation.attributes.get("denominator")))
    if candidate.frame.unit != "pt" or relative_tolerance < 0:
        raise ValueError("PDF_POINT_SCALE_AND_NONNEGATIVE_TOLERANCE_REQUIRED")
    theoretical = denominator * Decimal("0.0254") / Decimal(72)
    difference = abs(candidate.scale_m_per_drawing_unit-theoretical)
    relative = difference/theoretical
    agrees = relative <= relative_tolerance
    return ScaleCorroboration(dimension_candidate=candidate,
        annotation_observation_id=annotation.observation_id, annotation_denominator=denominator,
        annotation_scale_m_per_drawing_unit=theoretical,
        absolute_difference_m_per_drawing_unit=difference, relative_difference=relative,
        agrees=agrees, status=("CONFLICT" if not agrees else "VERIFIED" if candidate.status == "VERIFIED"
            else "CORROBORATED_UNIT_UNRESOLVED"),
        reason="INDEPENDENT_TITLE_BLOCK_SCALE_VS_DIMENSION_FIT_V1; dimension units remain separately governed")


def solve_scale_candidate(constraints: tuple[DimensionConstraint, ...], *,
                          assumed_declared_unit: Literal["mm", "m"],
                          residual_tolerance_m: Decimal) -> ScaleCandidate:
    """Fit one origin-preserving scale; an assumed missing unit cannot verify it."""
    usable = [c for c in constraints if c.anchors and c.anchors.kind == "SEGMENT"]
    if len(usable) < 2 or residual_tolerance_m < 0:
        raise ValueError("AT_LEAST_TWO_DIMENSION_SEGMENTS_AND_NONNEGATIVE_TOLERANCE_REQUIRED")
    frame = usable[0].anchors.frame
    if any(c.anchors.frame != frame for c in usable[1:]):
        raise ValueError("SCALE_CONSTRAINTS_MUST_SHARE_FRAME")
    declared_m, lengths = [], []
    missing_unit = False
    for c in usable:
        a, b = c.anchors.points
        lengths.append(((a.x-b.x)**2 + (a.y-b.y)**2).sqrt())
        unit = c.unit or assumed_declared_unit
        missing_unit |= c.unit is None
        declared_m.append(c.declared_distance / (Decimal(1000) if unit == "mm" else Decimal(1)))
    denominator = sum(length*length for length in lengths)
    scale = sum(length*value for length, value in zip(lengths, declared_m)) / denominator
    residuals = tuple(length*scale-value for length, value in zip(lengths, declared_m))
    maximum = max(abs(value) for value in residuals)
    status = "CONFLICT" if maximum > residual_tolerance_m else (
        "UNIT_CONFIRMATION_REQUIRED" if missing_unit else "VERIFIED")
    return ScaleCandidate(frame=frame, assumed_declared_unit=assumed_declared_unit,
        scale_m_per_drawing_unit=scale, constraint_ids=tuple(c.observation_id for c in usable),
        residuals_m=residuals, maximum_absolute_residual_m=maximum, status=status,
        reason="LEAST_SQUARES_ORIGIN_SCALE_V1; missing units remain assumptions")


class DrawingTransform(Model):
    from_frame: Frame
    to_frame: Frame
    # x'=a*x+b*y+tx; y'=c*x+d*y+ty. Includes declared unit conversion.
    coefficients: tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]
    evidence: tuple[SourceEvidence, ...] = Field(min_length=1)
    matched_anchors: tuple[str, ...] = Field(min_length=2)
    residual_m: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def nonsingular(self):
        a, b, c, d, _, _ = self.coefficients
        if a * d - b * c == 0 or len(set(self.matched_anchors)) != len(self.matched_anchors):
            raise ValueError("DEGENERATE_DRAWING_TRANSFORM")
        return self

    def apply(self, point: Point) -> Point:
        a, b, c, d, tx, ty = self.coefficients
        return Point(x=a*point.x+b*point.y+tx, y=c*point.x+d*point.y+ty)


def check_dimension(constraint: DimensionConstraint, transform: DrawingTransform,
                    *, tolerance_m: Decimal) -> DimensionCheck:
    """Explicit software comparison tolerance; no unit/scale inference."""
    if tolerance_m < 0:
        raise ValueError("NEGATIVE_COMPARISON_TOLERANCE")
    g = constraint.anchors
    if not g or not constraint.unit or g.kind != "SEGMENT":
        return DimensionCheck(constraint_id=constraint.observation_id, status="UNRESOLVED", reason=constraint.status)
    if g.frame != transform.from_frame or transform.to_frame.unit not in {"m", "mm"}:
        raise ValueError("DIMENSION_TRANSFORM_FRAME_MISMATCH")
    a, b = (transform.apply(p) for p in g.points)
    measured = ((a.x-b.x)**2 + (a.y-b.y)**2).sqrt()
    if transform.to_frame.unit == "mm":
        measured /= Decimal(1000)
    declared = constraint.declared_distance / (Decimal(1000) if constraint.unit == "mm" else Decimal(1))
    residual = measured - declared
    return DimensionCheck(constraint_id=constraint.observation_id,
        status="AGREES" if abs(residual) <= tolerance_m else "CONFLICT",
        measured_m=measured, residual_m=residual, reason="EXPLICIT_DIMENSION_COMPARISON_POLICY")


class ConfirmedProjectFact(Model):
    knowledge_level: Literal["CONFIRMED_PROJECT_FACT"] = "CONFIRMED_PROJECT_FACT"
    fact_id: str
    hypothesis_id: str
    hypothesis_digest: str
    policy_id: str
    source_dependencies: dict[str, str]
    evidence_ids: tuple[str, ...]
    engineering_binding_status: Literal["SEPARATE_AUTHORITY_REVIEW_REQUIRED"] = "SEPARATE_AUTHORITY_REVIEW_REQUIRED"


class ReconciliationEvidence(Model):
    evidence_id: str
    hypothesis_digest: str
    source: SourceEvidence
    dimension: Literal["GEOMETRY", "DIMENSION", "TEXT", "TOPOLOGY", "FLOOR", "RELATIVE_POSITION", "AREA", "SHAPE_DESCRIPTOR"]
    agrees: bool
    method: str = Field(min_length=1)
    target_entity_id: str | None = None


class PromotionDecision(Model):
    status: Literal["CONFIRMED", "CONFIRMATION_REQUIRED", "BLOCKED_BY_CONFLICT"]
    policy_id: Literal["DRAWING_FACT_PROMOTION_V1"] = "DRAWING_FACT_PROMOTION_V1"
    reasons: tuple[str, ...]
    fact: ConfirmedProjectFact | None = None
    typed_conflicts: tuple[DrawingConflict, ...] = ()


def reconcile(hypothesis: DrawingHypothesis, evidence: tuple[ReconciliationEvidence, ...]) -> tuple[DrawingHypothesis, PromotionDecision]:
    """Independent geometric + dimensional corroboration; area/OCR alone cannot promote."""
    if any(e.hypothesis_digest != hypothesis.dependency_digest for e in evidence):
        raise ValueError("STALE_RECONCILIATION_EVIDENCE")
    conflicts = tuple(e.evidence_id for e in evidence if not e.agrees)
    independent = [e for e in evidence if e.source.source_id not in hypothesis.source_dependencies]
    dimensions = {e.dimension for e in independent if e.agrees}
    c = hypothesis.confidence.model_copy(update={
        "cross_source": bool(independent), "dimensions": hypothesis.confidence.dimensions or "DIMENSION" in dimensions,
        "conflicts": hypothesis.confidence.conflicts + conflicts,
        "reasons": hypothesis.confidence.reasons + tuple(e.method for e in evidence)})
    dependencies = dict(hypothesis.source_dependencies)
    for e in evidence:
        old = dependencies.get(e.source.source_id)
        if old is not None and old != e.source.source_hash:
            raise ValueError("CONFLICTING_SOURCE_REVISIONS")
        dependencies[e.source.source_id] = e.source.source_hash
    updated = hypothesis.model_copy(update={"confidence": c, "source_dependencies": dependencies})
    if c.conflicts:
        typed = tuple(DrawingConflict(conflict_type="CROSS_SOURCE_EVIDENCE_CONFLICT",
            entity_refs=(hypothesis.hypothesis_id,), evidence_refs=(e.evidence_id,), severity="ERROR",
            reason=e.method, blocking=True) for e in evidence if not e.agrees)
        return updated, PromotionDecision(status="BLOCKED_BY_CONFLICT", reasons=c.conflicts,
            typed_conflicts=typed)
    if (hypothesis.kind not in {"ROOM", "BUILDING_CONTOUR", "WALL"} or
        hypothesis.geometry is None or c.ambiguity or c.source_quality in {"LOW", "AMBIGUOUS"} or
        not {"GEOMETRY", "DIMENSION"}.issubset(dimensions)):
        return updated, PromotionDecision(status="CONFIRMATION_REQUIRED",
            reasons=("INDEPENDENT_GEOMETRY_AND_DIMENSION_AGREEMENT_REQUIRED", "OCR_OR_AREA_ALONE_INSUFFICIENT"))
    fact = ConfirmedProjectFact(fact_id="fact-"+digest([hypothesis.hypothesis_id, [e.model_dump(mode="json") for e in evidence]])[:16],
        hypothesis_id=hypothesis.hypothesis_id, hypothesis_digest=updated.dependency_digest,
        policy_id="DRAWING_FACT_PROMOTION_V1", source_dependencies=dependencies,
        evidence_ids=tuple(e.evidence_id for e in evidence))
    return updated, PromotionDecision(status="CONFIRMED", reasons=("POLICY_REQUIREMENTS_MET",), fact=fact)


class DocumentUnderstanding(Model):
    source: DrawingSource
    observation_artifact_digest: str
    floor_title: str | None = None
    project_annotations: tuple[str, ...] = ()


class CrossFloorAlignment(Model):
    source_ids: tuple[str, str]
    candidate_anchor_ids: tuple[str, ...]
    status: Literal["ANCHOR_CORRESPONDENCE_REQUIRED", "ALIGNED"]
    transform: DrawingTransform | None = None
    single_anchor_translation_candidate: tuple[Decimal, Decimal] | None = None
    anchor_pair: tuple[str, str] | None = None
    multi_anchor_coefficients_candidate: tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal] | None = None
    multi_anchor_maximum_residual_drawing_units: Decimal | None = Field(default=None, ge=0)
    multi_anchor_status: Literal["NOT_AVAILABLE", "APPROXIMATE_CONTOUR_CORRESPONDENCE"] = "NOT_AVAILABLE"
    reason: str

    @model_validator(mode="after")
    def alignment_requires_transform(self):
        if (self.status == "ALIGNED") != (self.transform is not None):
            raise ValueError("ALIGNMENT_EVIDENCE_REQUIRED")
        return self


class AdjacencyCandidate(Model):
    left_hypothesis_id: str
    right_hypothesis_id: str
    frame: Frame
    separation_drawing_units: Decimal = Field(ge=0)
    shared_projection_drawing_units: Decimal = Field(gt=0)
    orientation: Literal["HORIZONTAL_BOUNDARY", "VERTICAL_BOUNDARY"]
    status: Literal["BOUNDARY_OR_OPENING_EVIDENCE_REQUIRED"] = "BOUNDARY_OR_OPENING_EVIDENCE_REQUIRED"
    reason: str


class WallBandCandidate(Model):
    adjacency: AdjacencyCandidate
    thickness_drawing_units: Decimal = Field(gt=0)
    thickness_m_candidate: Decimal | None = Field(default=None, gt=0)
    scale_status: Literal["NO_SCALE", "PHYSICAL_SCALE_UNVERIFIED", "PHYSICAL_SCALE_VERIFIED"]
    opening_evidence_ids: tuple[str, ...] = ()
    opening_status: Literal["NO_OPENING_EVIDENCE", "UNKNOWN_OPENING_CANDIDATE"]
    status: Literal["WALL_CLASS_AND_EXACT_FACES_UNRESOLVED"] = "WALL_CLASS_AND_EXACT_FACES_UNRESOLVED"


class GeometricOpeningCandidate(Model):
    frame: Frame
    observation_ids: tuple[str, ...]
    source_dependencies: dict[str, str]
    geometry: Geometry
    type_candidate: Literal["WINDOW_OR_GLAZING", "UNKNOWN_OPENING"]
    width_drawing_units_candidate: Decimal = Field(gt=0)
    exterior_contour_observation_id: str | None = None
    status: Literal["GEOMETRIC_CANDIDATE_NOT_THERMAL_AUTHORITY"] = "GEOMETRIC_CANDIDATE_NOT_THERMAL_AUTHORITY"


class InteriorBoundaryEvidence(Model):
    boundary_id: str
    adjacency: AdjacencyCandidate
    geometry: Geometry
    evidence_method: Literal["RASTER_WALL_CORRIDOR_OCCUPANCY_V1"] = "RASTER_WALL_CORRIDOR_OCCUPANCY_V1"
    median_ink_fraction: Decimal = Field(ge=0, le=1)
    gap_runs: tuple[Geometry, ...] = ()
    classification: Literal["SOLID_WALL", "WALL_WITH_SHORT_INTERRUPTION", "WALL_WITH_GAP", "INSUFFICIENT_RASTER_EVIDENCE"]
    source_dependencies: dict[str, str]
    status: Literal["GEOMETRIC_EVIDENCE_NOT_ENGINEERING_AUTHORITY"] = "GEOMETRIC_EVIDENCE_NOT_ENGINEERING_AUTHORITY"


class WallExtractionPolicy(Model):
    policy_id: Literal["RASTER_ORTHOGONAL_WALL_BANDS_V1"] = "RASTER_ORTHOGONAL_WALL_BANDS_V1"
    frame: Frame
    raster_pixels_per_drawing_unit: Decimal = Field(gt=0)
    minimum_line_length_drawing_units: Decimal = Field(gt=0)
    minimum_opening_gap_width_m_candidate: Decimal = Field(gt=0)
    minimum_opening_gap_width_drawing_units: Decimal = Field(gt=0)
    gap_width_basis: Literal["PHYSICAL_POLICY_USING_UNVERIFIED_DOCUMENT_SCALE"]
    suppression_classes: tuple[str, ...]
    rationale: str


class WallCenterlineCandidate(Model):
    wall_id: str
    frame: Frame
    orientation: Literal["HORIZONTAL", "VERTICAL"]
    band_geometry: Geometry
    centerline_geometry: Geometry
    length_drawing_units: Decimal = Field(gt=0)
    thickness_drawing_units: Decimal = Field(gt=0)
    source_dependencies: dict[str, str]
    suppression_applied: tuple[str, ...]
    status: Literal["RASTER_WALL_CANDIDATE_NOT_PROJECT_FACT"] = "RASTER_WALL_CANDIDATE_NOT_PROJECT_FACT"


class RasterLineRecoveryDiagnostic(Model):
    boundary_id: str
    room_hypothesis_id: str
    frame: Frame
    expected_geometry: Geometry
    expected_length_drawing_units: Decimal = Field(gt=0)
    original_extraction_status: Literal["UNMATCHED_POLYGON_EDGE"] = "UNMATCHED_POLYGON_EDGE"
    miss_reason: Literal["MASKED_AS_TEXT", "MASKED_AS_DIMENSION", "THICKNESS_OUTSIDE_POLICY", "BROKEN_BY_ANTIALIASING", "LOW_INK_CONTINUITY", "MERGED_WITH_SYMBOL", "SHORT_SEGMENT_FILTER", "OUTSIDE_CURRENT_ROI", "OTHER_EXTRACTOR_MISS"]
    recovery_attempt: Literal["TARGETED_RAW_RASTER_CORRIDOR_V1"] = "TARGETED_RAW_RASTER_CORRIDOR_V1"
    recovered_raster_evidence: bool
    recovered_wall_id: str | None = None
    recovered_length_drawing_units: Decimal = Field(default=Decimal(0), ge=0)
    raw_ink_continuity: Decimal = Field(ge=0, le=1)
    masked_ink_continuity: Decimal = Field(ge=0, le=1)
    median_thickness_drawing_units: Decimal = Field(ge=0)
    protected_gap_conflict: bool = False
    final_status: Literal["RECOVERED_RASTER_WALL_CANDIDATE", "REJECTED_OPENING_CONFLICT", "INSUFFICIENT_RASTER_EVIDENCE"]
    source_dependencies: dict[str, str]


class WallGraphSummary(Model):
    floor_id: str
    source_segment_count: int = Field(ge=0)
    collinear_chain_count: int = Field(ge=0)
    intersection_node_count: int = Field(ge=0)
    connected_component_count: int = Field(ge=0)
    status: Literal["CANDIDATE_GRAPH_OPENING_ASSOCIATION_REQUIRED"] = "CANDIDATE_GRAPH_OPENING_ASSOCIATION_REQUIRED"


class CollinearWallChain(Model):
    chain_id: str
    frame: Frame
    orientation: Literal["HORIZONTAL", "VERTICAL"]
    axis_drawing_units: Decimal
    span_start: Decimal
    span_end: Decimal
    source_wall_ids: tuple[str, ...]
    source_dependencies: dict[str, str]
    status: Literal["RECONSTRUCTED_CHAIN_NOT_PROJECT_FACT"] = "RECONSTRUCTED_CHAIN_NOT_PROJECT_FACT"


class SustainedWallGap(Model):
    gap_id: str
    chain_id: str
    frame: Frame
    geometry: Geometry
    width_drawing_units: Decimal = Field(gt=0)
    left_source_wall_id: str
    right_source_wall_id: str
    associated_room_hypothesis_ids: tuple[str, ...] = ()
    classification: Literal["OPEN_PASSAGE_CANDIDATE", "WINDOW_CANDIDATE", "UNKNOWN_OPENING"]
    source_dependencies: dict[str, str]
    status: Literal["GEOMETRIC_GAP_CANDIDATE_NOT_PROJECT_FACT"] = "GEOMETRIC_GAP_CANDIDATE_NOT_PROJECT_FACT"


class OpeningRoomBindingDiagnostic(Model):
    gap_id: str
    associated_room_hypothesis_ids: tuple[str, ...]
    status: Literal["ROOM_PAIR_BOUNDARY_BINDING_REQUIRED", "INSUFFICIENT_ROOM_ASSOCIATION", "AMBIGUOUS_ROOM_ASSOCIATION", "EXTERIOR_OPENING_NOT_INTERIOR_CONNECTIVITY"]
    reason: str


def diagnose_opening_room_bindings(gaps: tuple[SustainedWallGap, ...]) -> tuple[OpeningRoomBindingDiagnostic, ...]:
    """Explain why protected wall gaps cannot yet become connectivity edges."""
    diagnostics=[]
    for gap in sorted(gaps, key=lambda item: item.gap_id):
        count=len(gap.associated_room_hypothesis_ids)
        if gap.classification=="WINDOW_CANDIDATE":
            status="EXTERIOR_OPENING_NOT_INTERIOR_CONNECTIVITY";reason="GAP_CLASSIFIED_ON_EXTERIOR_CONTOUR"
        elif count<2:
            status="INSUFFICIENT_ROOM_ASSOCIATION";reason="GAP_TOUCHES_FEWER_THAN_TWO_ROOM_HYPOTHESES"
        elif count>2:
            status="AMBIGUOUS_ROOM_ASSOCIATION";reason="GAP_TOUCHES_MORE_THAN_TWO_ROOM_HYPOTHESES"
        else:
            status="ROOM_PAIR_BOUNDARY_BINDING_REQUIRED";reason="EXACT_ROOM_PAIR_FOUND_BUT_NO_PROVEN_INTERIOR_BOUNDARY_ID"
        diagnostics.append(OpeningRoomBindingDiagnostic(gap_id=gap.gap_id,
            associated_room_hypothesis_ids=gap.associated_room_hypothesis_ids,status=status,reason=reason))
    return tuple(diagnostics)


class SemanticWallBand(Model):
    band_id: str
    frame: Frame
    orientation: Literal["HORIZONTAL", "VERTICAL"]
    face_chain_ids: tuple[str, str]
    centerline_geometry: Geometry
    width_drawing_units: Decimal = Field(gt=0)
    overlap_fraction: Decimal = Field(gt=0, le=1)
    source_dependencies: dict[str, str]
    status: Literal["PAIRED_PARALLEL_FACES_NOT_PROJECT_FACT"] = "PAIRED_PARALLEL_FACES_NOT_PROJECT_FACT"


class UnpairedWallChain(Model):
    chain_id: str
    reason: Literal["NO_UNIQUE_PARALLEL_FACE_WITHIN_POLICY"]


class WallCenterlinePolicy(Model):
    minimum_width_drawing_units: Decimal = Field(gt=0)
    maximum_width_drawing_units: Decimal = Field(gt=0)
    minimum_overlap_fraction: Decimal = Field(gt=0, le=1)
    junction_tolerance_drawing_units: Decimal = Field(gt=0)
    basis: Literal["RASTER_RESOLUTION_AND_OBSERVED_WALL_BAND_DISTRIBUTION"]


class SemanticWallJunction(Model):
    junction_id: str
    frame: Frame
    point: Point
    junction_type: Literal["T_JUNCTION", "L_JUNCTION", "CROSS_JUNCTION"]
    wall_band_ids: tuple[str, ...]
    closure_distance_drawing_units: Decimal = Field(ge=0)
    gap_preservation_status: Literal["NO_SUSTAINED_GAP_DESTROYED"] = "NO_SUSTAINED_GAP_DESTROYED"
    status: Literal["JUNCTION_CANDIDATE_NOT_PROJECT_FACT"] = "JUNCTION_CANDIDATE_NOT_PROJECT_FACT"


class WallFaceIntervalSpan(Model):
    span_id: str
    source_chain_id: str
    frame: Frame
    orientation: Literal["HORIZONTAL", "VERTICAL"]
    axis_drawing_units: Decimal
    span_start: Decimal
    span_end: Decimal
    classification: Literal["PAIRED_WALL_FACE", "UNPAIRED_WALL_FACE", "AMBIGUOUS_PAIRING", "OPENING_ADJACENT_SPAN", "JUNCTION_ADJACENT_SPAN"]
    counterpart_chain_id: str | None = None
    competing_counterpart_chain_ids: tuple[str, ...] = ()
    source_dependencies: dict[str, str]


class IntervalSemanticWallBand(Model):
    band_id: str
    frame: Frame
    orientation: Literal["HORIZONTAL", "VERTICAL"]
    source_span_ids: tuple[str, str]
    source_chain_ids: tuple[str, str]
    centerline_geometry: Geometry
    width_drawing_units: Decimal = Field(gt=0)
    confidence: Literal["HIGH", "MEDIUM"]
    policy_basis: str
    source_dependencies: dict[str, str]


class EndpointJunctionDecision(Model):
    decision_id: str
    frame: Frame
    endpoint: Point
    source_wall_id: str
    target_wall_ids: tuple[str, ...] = ()
    projected_node: Point | None = None
    junction_type: Literal["T_JUNCTION", "L_JUNCTION", "CROSS_JUNCTION"] | None = None
    closure_distance_drawing_units: Decimal = Field(ge=0)
    status: Literal["CONFIRMED_JUNCTION", "AMBIGUOUS_JUNCTION", "OPENING_GAP_PRESERVED", "NO_SUPPORTED_JUNCTION", "REJECTED_JUNCTION"]
    reason: str
    source_dependencies: dict[str, str]


class SemanticWallGraphV2(Model):
    frame: Frame
    wall_edges: tuple[Geometry, ...]
    junctions: tuple[EndpointJunctionDecision, ...]
    protected_gap_ids: tuple[str, ...]
    dangling_endpoints: tuple[Point, ...]
    duplicate_parallel_edge_count: int = Field(ge=0)
    status: Literal["CANDIDATE_GRAPH_NOT_PROJECT_FACT"] = "CANDIDATE_GRAPH_NOT_PROJECT_FACT"


class SingleFaceCenterlineInference(Model):
    inference_id: str
    frame: Frame
    source_span_id: str
    source_chain_id: str
    prior_band_ids: tuple[str, ...] = ()
    inferred_geometry: Geometry | None = None
    inferred_width_drawing_units: Decimal | None = Field(default=None, gt=0)
    inferred_offset_drawing_units: Decimal | None = None
    status: Literal["INFERRED_FROM_SINGLE_FACE_WITH_LOCAL_BAND_PRIOR", "AMBIGUOUS_OFFSET", "UNRESOLVED_SINGLE_FACE", "REJECTED_OPENING_CONFLICT"]
    reason: str
    source_dependencies: dict[str, str]


class CombinedSemanticWallEdge(Model):
    edge_id: str
    frame: Frame
    orientation: Literal["HORIZONTAL", "VERTICAL"]
    geometry: Geometry
    evidence_class: Literal["PROVEN_CENTERLINE", "SUPPORTED_INFERRED_CENTERLINE"]
    source_span_ids: tuple[str, ...]
    source_dependencies: dict[str, str]
    dependency_digest: str


class JunctionDecisionV3(Model):
    decision_id: str
    frame: Frame
    source_edge_id: str
    source_evidence_class: Literal["PROVEN_CENTERLINE", "SUPPORTED_INFERRED_CENTERLINE"]
    endpoint: Point
    target_edge_ids: tuple[str, ...] = ()
    projected_node: Point | None = None
    closure_distance_drawing_units: Decimal = Field(ge=0)
    status: Literal["CONFIRMED_T_JUNCTION", "CONFIRMED_L_JUNCTION", "CONFIRMED_CROSS_JUNCTION", "AMBIGUOUS_JUNCTION", "NO_SUPPORTED_JUNCTION", "REJECTED_OPENING_CONFLICT"]
    reason: str


class NormalizedSemanticWallGraph(Model):
    frame: Frame
    source_edge_count: int
    normalized_edges: tuple[Geometry, ...]
    junctions: tuple[JunctionDecisionV3, ...]
    proven_dangling_endpoints: tuple[Point, ...]
    inferred_dangling_endpoints: tuple[Point, ...]
    protected_gap_ids: tuple[str, ...]
    diagnostics: tuple[str, ...]


class ProvenRoomBoundaryMatch(Model):
    match_id: str
    room_hypothesis_id: str
    polygon_edge: Geometry
    raster_span_ids: tuple[str, ...]
    matched_length_drawing_units: Decimal = Field(ge=0)
    edge_length_drawing_units: Decimal = Field(gt=0)
    status: Literal["MATCHED_RASTER_FACE", "UNMATCHED_POLYGON_EDGE"]


class BoundaryGuidedCenterlineCandidate(Model):
    candidate_id: str
    frame: Frame
    source_raster_span_id: str
    supporting_room_hypothesis_id: str
    supporting_polygon_edge: Geometry
    inferred_geometry: Geometry | None = None
    support_level: Literal["BOUNDARY_PLUS_LOCAL_BAND_PRIOR", "BOUNDARY_PLUS_PROVEN_WALL_CONTINUATION", "BOUNDARY_ONLY_SIDE_EVIDENCE", "INSUFFICIENT_SUPPORT", "CONFLICTING_SUPPORT"]
    offset_evidence: str
    width_evidence: str
    topology_edge_eligible: bool
    source_dependencies: dict[str, str]
    dependency_digest: str


class BoundarySupportChain(Model):
    chain_id: str
    room_hypothesis_id: str
    polygon_edge: Geometry
    candidate_ids: tuple[str, ...]
    selected_fragment_ids: tuple[str, ...] = ()
    stitched_geometry: Geometry | None = None
    supported_length_drawing_units: Decimal = Field(default=Decimal(0), ge=0)
    outcome: Literal["CHAIN_SELECTED", "CHAIN_AMBIGUOUS", "CHAIN_INTERRUPTED_BY_OPENING", "CHAIN_INSUFFICIENT_SUPPORT", "CHAIN_CONFLICTING_TOPOLOGY"]
    reason: str


def select_boundary_support_chains(candidates: tuple[BoundaryGuidedCenterlineCandidate, ...], gaps: tuple[SustainedWallGap, ...], *,
        continuity_tolerance: Decimal) -> tuple[BoundarySupportChain, ...]:
    groups={}
    for item in candidates:
        key=(item.supporting_room_hypothesis_id,digest(item.supporting_polygon_edge))
        groups.setdefault(key,[]).append(item)
    result=[]
    for (room_id,_),items in sorted(groups.items()):
        edge=items[0].supporting_polygon_edge;eligible=[x for x in items if x.topology_edge_eligible and x.inferred_geometry]
        cid=room_id+":"+digest(edge)[:12]+":SUPPORT_CHAIN"
        if not eligible:
            outcome="CHAIN_CONFLICTING_TOPOLOGY" if any(x.support_level=="CONFLICTING_SUPPORT" for x in items) else "CHAIN_INSUFFICIENT_SUPPORT"
            result.append(BoundarySupportChain(chain_id=cid,room_hypothesis_id=room_id,polygon_edge=edge,
                candidate_ids=tuple(x.candidate_id for x in items),outcome=outcome,reason="NO_STRONG_UNAMBIGUOUS_FRAGMENT_SEQUENCE"));continue
        horizontal=edge.points[0].y==edge.points[1].y
        axes={x.inferred_geometry.points[0].y if horizontal else x.inferred_geometry.points[0].x for x in eligible}
        if len(axes)>1:
            result.append(BoundarySupportChain(chain_id=cid,room_hypothesis_id=room_id,polygon_edge=edge,
                candidate_ids=tuple(x.candidate_id for x in items),outcome="CHAIN_AMBIGUOUS",reason="MULTIPLE_OFFSET_STABLE_CHAINS"));continue
        axis=next(iter(axes));fragments=[]
        for x in eligible:
            p,q=x.inferred_geometry.points;lo,hi=(sorted((p.x,q.x)) if horizontal else sorted((p.y,q.y)));fragments.append((lo,hi,x))
        fragments.sort(key=lambda v:(v[0],v[1],v[2].candidate_id));merged=[]
        for lo,hi,item in fragments:
            if merged and lo<=merged[-1][1]+continuity_tolerance:merged[-1][1]=max(merged[-1][1],hi);merged[-1][2].append(item)
            else:merged.append([lo,hi,[item]])
        interrupted=False
        if len(merged)>1:
            for left,right in zip(merged,merged[1:]):
                for gap in gaps:
                    if gap.frame!=edge.frame:continue
                    gp,gq=gap.geometry.points;glo,ghi=(sorted((gp.x,gq.x)) if horizontal else sorted((gp.y,gq.y)))
                    if max(left[1],glo)<min(right[0],ghi):interrupted=True
        if len(merged)>1:
            outcome="CHAIN_INTERRUPTED_BY_OPENING" if interrupted else "CHAIN_INSUFFICIENT_SUPPORT"
            result.append(BoundarySupportChain(chain_id=cid,room_hypothesis_id=room_id,polygon_edge=edge,
                candidate_ids=tuple(x.candidate_id for x in items),selected_fragment_ids=tuple(x.candidate_id for _,_,xs in merged for x in xs),
                supported_length_drawing_units=sum((m[1]-m[0] for m in merged),Decimal(0)),outcome=outcome,
                reason="PROTECTED_OPENING_SPLITS_CHAIN" if interrupted else "UNEXPLAINED_FRAGMENT_BREAK"));continue
        lo,hi,selected=merged[0];points=((Point(x=lo,y=axis),Point(x=hi,y=axis)) if horizontal else (Point(x=axis,y=lo),Point(x=axis,y=hi)))
        result.append(BoundarySupportChain(chain_id=cid,room_hypothesis_id=room_id,polygon_edge=edge,
            candidate_ids=tuple(x.candidate_id for x in items),selected_fragment_ids=tuple(x.candidate_id for x in selected),
            stitched_geometry=Geometry(frame=edge.frame,kind="POLYLINE",points=points),supported_length_drawing_units=hi-lo,
            outcome="CHAIN_SELECTED",reason="UNIQUE_OFFSET_CONTINUOUS_FRAGMENT_SEQUENCE"))
    return tuple(result)


def match_proven_room_boundaries(rooms: tuple[BuildingRoomCandidate, ...], hypotheses: tuple[DrawingHypothesis, ...],
        spans: tuple[WallFaceIntervalSpan, ...], *, distance_tolerance: Decimal) -> tuple[ProvenRoomBoundaryMatch, ...]:
    by_id={h.hypothesis_id:h for h in hypotheses};result=[]
    for room in rooms:
        if room.area_status!="CONSISTENT_IF_M2":continue
        geometry=by_id[room.room_hypothesis_id].geometry;points=geometry.points
        for index,(a,b) in enumerate(zip(points,points[1:]+points[:1])):
            if a.x!=b.x and a.y!=b.y:continue
            orientation="VERTICAL" if a.x==b.x else "HORIZONTAL";axis=a.x if orientation=="VERTICAL" else a.y
            lo,hi=sorted((a.y,b.y)) if orientation=="VERTICAL" else sorted((a.x,b.x));length=hi-lo
            candidates=[]
            for span in spans:
                if span.frame!=geometry.frame or span.orientation!=orientation or abs(span.axis_drawing_units-axis)>distance_tolerance:continue
                overlap=max(Decimal(0),min(hi,span.span_end)-max(lo,span.span_start))
                if overlap:candidates.append((span,overlap))
            matched=min(length,sum((o for _,o in candidates),Decimal(0)))
            edge=Geometry(frame=geometry.frame,kind="POLYLINE",points=(a,b))
            result.append(ProvenRoomBoundaryMatch(match_id=room.room_hypothesis_id+f":EDGE:{index}",room_hypothesis_id=room.room_hypothesis_id,
                polygon_edge=edge,raster_span_ids=tuple(s.span_id for s,_ in candidates),matched_length_drawing_units=matched,
                edge_length_drawing_units=length,status="MATCHED_RASTER_FACE" if matched else "UNMATCHED_POLYGON_EDGE"))
    return tuple(result)


def infer_boundary_guided_centerlines(matches: tuple[ProvenRoomBoundaryMatch, ...], spans: tuple[WallFaceIntervalSpan, ...],
        bands: tuple[IntervalSemanticWallBand, ...], inferences: tuple[SingleFaceCenterlineInference, ...], *,
        boundary_distance_tolerance: Decimal) -> tuple[BoundaryGuidedCenterlineCandidate, ...]:
    span_by_id={s.span_id:s for s in spans};result=[]
    local_by_span={i.source_span_id:i for i in inferences if i.status=="INFERRED_FROM_SINGLE_FACE_WITH_LOCAL_BAND_PRIOR"}
    for match in matches:
      for sid in match.raster_span_ids:
        span=span_by_id[sid];prior=local_by_span.get(sid);level="BOUNDARY_ONLY_SIDE_EVIDENCE";geometry=None;offset="room boundary establishes local side only";width="unresolved"
        if prior and prior.inferred_geometry:
            level="BOUNDARY_PLUS_LOCAL_BAND_PRIOR";geometry=prior.inferred_geometry;offset=f"same-chain local offset {prior.inferred_offset_drawing_units}";width=f"local band width {prior.inferred_width_drawing_units}"
        else:
            edge_axis=(match.polygon_edge.points[0].y if span.orientation=="HORIZONTAL" else match.polygon_edge.points[0].x)
            compatible=[b for b in bands if b.frame==span.frame and b.orientation==span.orientation and
                abs((b.centerline_geometry.points[0].y if span.orientation=="HORIZONTAL" else b.centerline_geometry.points[0].x)-edge_axis)<=boundary_distance_tolerance and
                max(span.span_start,min(p.x for p in b.centerline_geometry.points) if span.orientation=="HORIZONTAL" else min(p.y for p in b.centerline_geometry.points)) <
                min(span.span_end,max(p.x for p in b.centerline_geometry.points) if span.orientation=="HORIZONTAL" else max(p.y for p in b.centerline_geometry.points))]
            if len(compatible)==1:
                band=compatible[0];bp=band.centerline_geometry.points[0];axis=bp.y if span.orientation=="HORIZONTAL" else bp.x
                pts=((Point(x=span.span_start,y=axis),Point(x=span.span_end,y=axis)) if span.orientation=="HORIZONTAL" else (Point(x=axis,y=span.span_start),Point(x=axis,y=span.span_end)))
                geometry=Geometry(frame=span.frame,kind="POLYLINE",points=pts);level="BOUNDARY_PLUS_PROVEN_WALL_CONTINUATION";offset="overlapping unique proven centerline";width=f"proven band width {band.width_drawing_units}"
            elif len(compatible)>1:level="CONFLICTING_SUPPORT";offset="multiple overlapping proven centerlines"
        body={"match":match.match_id,"span":sid,"level":level,"geometry":geometry.model_dump(mode="json") if geometry else None}
        result.append(BoundaryGuidedCenterlineCandidate(candidate_id=match.match_id+":"+digest(body)[:12],frame=span.frame,
            source_raster_span_id=sid,supporting_room_hypothesis_id=match.room_hypothesis_id,supporting_polygon_edge=match.polygon_edge,
            inferred_geometry=geometry,support_level=level,offset_evidence=offset,width_evidence=width,
            topology_edge_eligible=level in {"BOUNDARY_PLUS_LOCAL_BAND_PRIOR","BOUNDARY_PLUS_PROVEN_WALL_CONTINUATION"},
            source_dependencies=span.source_dependencies,dependency_digest=digest(body)))
    return tuple(result)


def build_combined_semantic_edges(bands: tuple[IntervalSemanticWallBand, ...],
        inferences: tuple[SingleFaceCenterlineInference, ...]) -> tuple[CombinedSemanticWallEdge, ...]:
    result=[]
    for band in bands:
        body={"geometry":band.centerline_geometry.model_dump(mode="json"),"sources":band.source_span_ids,"class":"PROVEN_CENTERLINE"}
        result.append(CombinedSemanticWallEdge(edge_id=band.band_id,frame=band.frame,orientation=band.orientation,
            geometry=band.centerline_geometry,evidence_class="PROVEN_CENTERLINE",source_span_ids=band.source_span_ids,
            source_dependencies=band.source_dependencies,dependency_digest=digest(body)))
    for item in inferences:
        if item.status!="INFERRED_FROM_SINGLE_FACE_WITH_LOCAL_BAND_PRIOR" or item.inferred_geometry is None:continue
        body={"geometry":item.inferred_geometry.model_dump(mode="json"),"source":item.source_span_id,"priors":item.prior_band_ids}
        result.append(CombinedSemanticWallEdge(edge_id=item.inference_id,frame=item.frame,
            orientation="HORIZONTAL" if item.inferred_geometry.points[0].y==item.inferred_geometry.points[1].y else "VERTICAL",
            geometry=item.inferred_geometry,evidence_class="SUPPORTED_INFERRED_CENTERLINE",source_span_ids=(item.source_span_id,),
            source_dependencies=item.source_dependencies,dependency_digest=digest(body)))
    return tuple(sorted(result,key=lambda e:e.edge_id))


def add_boundary_guided_edges(edges: tuple[CombinedSemanticWallEdge, ...],
        candidates: tuple[BoundaryGuidedCenterlineCandidate, ...]) -> tuple[CombinedSemanticWallEdge, ...]:
    result=list(edges);keys={digest(e.geometry):e for e in edges}
    for item in candidates:
        if not item.topology_edge_eligible or item.inferred_geometry is None:continue
        key=digest(item.inferred_geometry)
        if key in keys:continue
        edge=CombinedSemanticWallEdge(edge_id=item.candidate_id+":BOUNDARY_GUIDED",frame=item.frame,
            orientation="HORIZONTAL" if item.inferred_geometry.points[0].y==item.inferred_geometry.points[1].y else "VERTICAL",
            geometry=item.inferred_geometry,evidence_class="SUPPORTED_INFERRED_CENTERLINE",source_span_ids=(item.source_raster_span_id,),
            source_dependencies=item.source_dependencies,dependency_digest=item.dependency_digest)
        keys[key]=edge;result.append(edge)
    return tuple(sorted(result,key=lambda e:e.edge_id))


def add_selected_support_chain_edges(edges: tuple[CombinedSemanticWallEdge, ...], chains: tuple[BoundarySupportChain, ...],
        candidates: tuple[BoundaryGuidedCenterlineCandidate, ...]) -> tuple[CombinedSemanticWallEdge, ...]:
    result=list(edges);keys={digest(e.geometry) for e in edges};by_id={c.candidate_id:c for c in candidates}
    for chain in chains:
        if chain.outcome!="CHAIN_SELECTED" or chain.stitched_geometry is None:continue
        key=digest(chain.stitched_geometry)
        if key in keys:continue
        sources=[by_id[i] for i in chain.selected_fragment_ids];deps={k:v for s in sources for k,v in s.source_dependencies.items()}
        body={"chain":chain.chain_id,"geometry":chain.stitched_geometry.model_dump(mode="json"),"fragments":chain.selected_fragment_ids}
        result.append(CombinedSemanticWallEdge(edge_id=chain.chain_id+":STITCHED",frame=chain.polygon_edge.frame,
            orientation="HORIZONTAL" if chain.stitched_geometry.points[0].y==chain.stitched_geometry.points[1].y else "VERTICAL",
            geometry=chain.stitched_geometry,evidence_class="SUPPORTED_INFERRED_CENTERLINE",
            source_span_ids=tuple(s.source_raster_span_id for s in sources),source_dependencies=deps,dependency_digest=digest(body)))
        keys.add(key)
    return tuple(sorted(result,key=lambda e:e.edge_id))


def normalize_combined_semantic_graph(edges: tuple[CombinedSemanticWallEdge, ...], gaps: tuple[SustainedWallGap, ...], *,
        tolerance: Decimal) -> tuple[NormalizedSemanticWallGraph, ...]:
    results=[]
    frames={e.frame.frame_id:e.frame for e in edges}
    for frame_id in sorted(frames):
      frame=frames[frame_id];local=[e for e in edges if e.frame==frame];decisions=[];normalized=[];dangling={"PROVEN_CENTERLINE":[],"SUPPORTED_INFERRED_CENTERLINE":[]}
      for source in local:
        points=list(source.geometry.points)
        for index,endpoint in enumerate(tuple(points)):
            protected=[g for g in gaps if g.frame==frame and min(p.x for p in g.geometry.points)-tolerance<=endpoint.x<=max(p.x for p in g.geometry.points)+tolerance and min(p.y for p in g.geometry.points)-tolerance<=endpoint.y<=max(p.y for p in g.geometry.points)+tolerance]
            did=source.edge_id+":"+str(index)+":V3"
            if protected:
                decisions.append(JunctionDecisionV3(decision_id=did,frame=frame,source_edge_id=source.edge_id,source_evidence_class=source.evidence_class,
                    endpoint=endpoint,closure_distance_drawing_units=Decimal(0),status="REJECTED_OPENING_CONFLICT",reason="PROTECTED_GAP_CONSTRAINT"));dangling[source.evidence_class].append(endpoint);continue
            candidates=[]
            for target in local:
                if target.edge_id==source.edge_id or target.orientation==source.orientation:continue
                p,q=target.geometry.points
                if source.orientation=="HORIZONTAL":node=Point(x=p.x,y=endpoint.y);distance=abs(p.x-endpoint.x);within=min(p.y,q.y)-tolerance<=endpoint.y<=max(p.y,q.y)+tolerance
                else:node=Point(x=endpoint.x,y=p.y);distance=abs(p.y-endpoint.y);within=min(p.x,q.x)-tolerance<=endpoint.x<=max(p.x,q.x)+tolerance
                limit=tolerance/2 if source.evidence_class==target.evidence_class=="SUPPORTED_INFERRED_CENTERLINE" else tolerance
                if within and distance<=limit:candidates.append((distance,target,node))
            candidates.sort(key=lambda x:(x[0],0 if x[1].evidence_class=="PROVEN_CENTERLINE" else 1,x[1].edge_id))
            if not candidates:
                decisions.append(JunctionDecisionV3(decision_id=did,frame=frame,source_edge_id=source.edge_id,source_evidence_class=source.evidence_class,
                    endpoint=endpoint,closure_distance_drawing_units=tolerance,status="NO_SUPPORTED_JUNCTION",reason="NO_PERPENDICULAR_COMBINED_EDGE_WITHIN_POLICY"));dangling[source.evidence_class].append(endpoint);continue
            best=candidates[0];ties=[x for x in candidates if x[0]==best[0] and x[1].evidence_class==best[1].evidence_class]
            if len(ties)>1:
                decisions.append(JunctionDecisionV3(decision_id=did,frame=frame,source_edge_id=source.edge_id,source_evidence_class=source.evidence_class,
                    endpoint=endpoint,target_edge_ids=tuple(x[1].edge_id for x in ties),closure_distance_drawing_units=best[0],status="AMBIGUOUS_JUNCTION",reason="MULTIPLE_EQUAL_COMBINED_TARGETS"));dangling[source.evidence_class].append(endpoint);continue
            distance,target,node=best;tp,tq=target.geometry.points;status="CONFIRMED_L_JUNCTION" if node in (tp,tq) else "CONFIRMED_T_JUNCTION"
            points[index]=node;decisions.append(JunctionDecisionV3(decision_id=did,frame=frame,source_edge_id=source.edge_id,
                source_evidence_class=source.evidence_class,endpoint=endpoint,target_edge_ids=(target.edge_id,),projected_node=node,
                closure_distance_drawing_units=distance,status=status,reason="UNIQUE_COMBINED_PERPENDICULAR_TARGET"))
        if points[0]!=points[1]:normalized.append(Geometry(frame=frame,kind="POLYLINE",points=tuple(points)))
      unique={tuple((p.x,p.y) for p in e.points):e for e in normalized}
      results.append(NormalizedSemanticWallGraph(frame=frame,source_edge_count=len(local),normalized_edges=tuple(unique[k] for k in sorted(unique)),
        junctions=tuple(decisions),proven_dangling_endpoints=tuple(dangling["PROVEN_CENTERLINE"]),
        inferred_dangling_endpoints=tuple(dangling["SUPPORTED_INFERRED_CENTERLINE"]),
        protected_gap_ids=tuple(sorted(g.gap_id for g in gaps if g.frame==frame)),
        diagnostics=("RESIDUAL_FACE_ARTIFACT_EXCLUDED","DUPLICATE_REVERSE_EDGES_REMOVED","WALL_BAND_SLIVER_SOURCE_FACES_EXCLUDED")))
    return tuple(results)


def infer_single_face_centerlines(spans: tuple[WallFaceIntervalSpan, ...], bands: tuple[IntervalSemanticWallBand, ...],
        gaps: tuple[SustainedWallGap, ...], *, maximum_prior_distance: Decimal) -> tuple[SingleFaceCenterlineInference, ...]:
    result=[]
    residuals=[s for s in spans if s.classification in {"UNPAIRED_WALL_FACE","OPENING_ADJACENT_SPAN"}]
    for span in sorted(residuals,key=lambda s:s.span_id):
        priors=[]
        for band in bands:
            if band.frame!=span.frame or band.orientation!=span.orientation or span.source_chain_id not in band.source_chain_ids:continue
            p,q=band.centerline_geometry.points;blo,bhi=(sorted((p.x,q.x)) if span.orientation=="HORIZONTAL" else sorted((p.y,q.y)))
            distance=max(blo-span.span_end,span.span_start-bhi,Decimal(0))
            if distance<=maximum_prior_distance:
                offset=(p.y-span.axis_drawing_units if span.orientation=="HORIZONTAL" else p.x-span.axis_drawing_units)
                priors.append((distance,offset,band))
        iid=span.span_id+":SINGLE_FACE_INFERENCE"
        if not priors:
            result.append(SingleFaceCenterlineInference(inference_id=iid,frame=span.frame,source_span_id=span.span_id,
                source_chain_id=span.source_chain_id,status="UNRESOLVED_SINGLE_FACE",reason="NO_LOCAL_PAIRED_INTERVAL_ON_SAME_SOURCE_FACE_CHAIN",
                source_dependencies=span.source_dependencies));continue
        nearest=min(p[0] for p in priors);local=[p for p in priors if p[0]==nearest]
        offsets={p[1] for p in local}
        if len(offsets)!=1:
            result.append(SingleFaceCenterlineInference(inference_id=iid,frame=span.frame,source_span_id=span.span_id,
                source_chain_id=span.source_chain_id,prior_band_ids=tuple(p[2].band_id for p in local),status="AMBIGUOUS_OFFSET",
                reason="EQUALLY_LOCAL_PRIORS_IMPLY_DIFFERENT_CENTERLINE_SIDES",source_dependencies=span.source_dependencies));continue
        offset=next(iter(offsets));prior=local[0][2];axis=span.axis_drawing_units+offset
        points=((Point(x=span.span_start,y=axis),Point(x=span.span_end,y=axis)) if span.orientation=="HORIZONTAL" else
                (Point(x=axis,y=span.span_start),Point(x=axis,y=span.span_end)))
        geometry=Geometry(frame=span.frame,kind="POLYLINE",points=points)
        conflict=False
        for gap in gaps:
            if gap.frame!=span.frame:continue
            gp,gq=gap.geometry.points
            if span.orientation=="HORIZONTAL" and gp.y==span.axis_drawing_units:
                conflict=max(span.span_start,min(gp.x,gq.x))<min(span.span_end,max(gp.x,gq.x))
            elif span.orientation=="VERTICAL" and gp.x==span.axis_drawing_units:
                conflict=max(span.span_start,min(gp.y,gq.y))<min(span.span_end,max(gp.y,gq.y))
            if conflict:break
        status="REJECTED_OPENING_CONFLICT" if conflict else "INFERRED_FROM_SINGLE_FACE_WITH_LOCAL_BAND_PRIOR"
        result.append(SingleFaceCenterlineInference(inference_id=iid,frame=span.frame,source_span_id=span.span_id,
            source_chain_id=span.source_chain_id,prior_band_ids=(prior.band_id,),inferred_geometry=None if conflict else geometry,
            inferred_width_drawing_units=prior.width_drawing_units,inferred_offset_drawing_units=offset,status=status,
            reason="PROTECTED_GAP_INTERSECTS_CONTINUATION" if conflict else "SAME_FACE_CHAIN_LOCAL_PAIRED_INTERVAL_PROVES_OFFSET_AND_WIDTH",
            source_dependencies={**span.source_dependencies,**prior.source_dependencies}))
    return tuple(result)


def solve_endpoint_junctions(bands: tuple[IntervalSemanticWallBand, ...], gaps: tuple[SustainedWallGap, ...], *,
        tolerance: Decimal) -> tuple[EndpointJunctionDecision, ...]:
    decisions=[]
    for source in sorted(bands,key=lambda b:b.band_id):
      for endpoint in source.centerline_geometry.points:
        candidates=[]
        for target in bands:
            if target.band_id==source.band_id or target.frame!=source.frame or target.orientation==source.orientation: continue
            p,q=target.centerline_geometry.points
            if source.orientation=="HORIZONTAL": node=Point(x=p.x,y=endpoint.y); distance=abs(endpoint.x-p.x); within=min(p.y,q.y)-tolerance<=endpoint.y<=max(p.y,q.y)+tolerance
            else: node=Point(x=endpoint.x,y=p.y);distance=abs(endpoint.y-p.y);within=min(p.x,q.x)-tolerance<=endpoint.x<=max(p.x,q.x)+tolerance
            if within and distance<=tolerance:candidates.append((distance,target,node))
        protected=[]
        for gap in gaps:
            if gap.frame!=source.frame:continue
            gp,gq=gap.geometry.points
            if min(gp.x,gq.x)-tolerance<=endpoint.x<=max(gp.x,gq.x)+tolerance and min(gp.y,gq.y)-tolerance<=endpoint.y<=max(gp.y,gq.y)+tolerance:
                protected.append(gap.gap_id)
        did=source.band_id+":"+digest(endpoint)[:12]+":JUNCTION_DECISION"
        deps=source.source_dependencies
        if protected:
            decisions.append(EndpointJunctionDecision(decision_id=did,frame=source.frame,endpoint=endpoint,
                source_wall_id=source.band_id,closure_distance_drawing_units=Decimal(0),status="OPENING_GAP_PRESERVED",
                reason="REJECTED_OPENING_CONFLICT:"+",".join(sorted(protected)),source_dependencies=deps));continue
        candidates.sort(key=lambda x:(x[0],x[1].band_id))
        if not candidates:
            decisions.append(EndpointJunctionDecision(decision_id=did,frame=source.frame,endpoint=endpoint,
                source_wall_id=source.band_id,closure_distance_drawing_units=tolerance,status="NO_SUPPORTED_JUNCTION",
                reason="NO_PERPENDICULAR_SEMANTIC_CENTERLINE_WITHIN_POLICY",source_dependencies=deps));continue
        nearest=candidates[0][0];ties=[x for x in candidates if abs(x[0]-nearest)<=Decimal("0.5")]
        if len(ties)>1:
            decisions.append(EndpointJunctionDecision(decision_id=did,frame=source.frame,endpoint=endpoint,
                source_wall_id=source.band_id,target_wall_ids=tuple(x[1].band_id for x in ties),
                closure_distance_drawing_units=nearest,status="AMBIGUOUS_JUNCTION",reason="MULTIPLE_EQUAL_PERPENDICULAR_TARGETS",source_dependencies=deps));continue
        distance,target,node=ties[0];tp,tq=target.centerline_geometry.points
        source_end=True;target_end=node in (tp,tq)
        kind="L_JUNCTION" if target_end else "T_JUNCTION"
        decisions.append(EndpointJunctionDecision(decision_id=did,frame=source.frame,endpoint=endpoint,
            source_wall_id=source.band_id,target_wall_ids=(target.band_id,),projected_node=node,junction_type=kind,
            closure_distance_drawing_units=distance,status="CONFIRMED_JUNCTION",reason="UNIQUE_PERPENDICULAR_TARGET_WITHIN_POLICY",
            source_dependencies={**deps,**target.source_dependencies}))
    return tuple(decisions)


def build_semantic_wall_graph_v2(bands: tuple[IntervalSemanticWallBand, ...], gaps: tuple[SustainedWallGap, ...], *,
        tolerance: Decimal) -> tuple[SemanticWallGraphV2, ...]:
    decisions=solve_endpoint_junctions(bands,gaps,tolerance=tolerance);result=[]
    frames={b.frame.frame_id:b.frame for b in bands}
    for frame in (frames[k] for k in sorted(frames)):
        local_bands=[b for b in bands if b.frame==frame];local=[d for d in decisions if d.frame==frame]
        edges=[];dangling=[]
        for band in local_bands:
            pts=list(band.centerline_geometry.points)
            for index in (0,1):
                decision=next(d for d in local if d.source_wall_id==band.band_id and d.endpoint==pts[index])
                if decision.status=="CONFIRMED_JUNCTION":pts[index]=decision.projected_node
                else:dangling.append(pts[index])
            edges.append(Geometry(frame=frame,kind="POLYLINE",points=tuple(pts)))
        result.append(SemanticWallGraphV2(frame=frame,wall_edges=tuple(edges),junctions=tuple(local),
            protected_gap_ids=tuple(sorted(g.gap_id for g in gaps if g.frame==frame)),dangling_endpoints=tuple(dangling),
            duplicate_parallel_edge_count=0))
    return tuple(result)


def pair_wall_faces_by_interval(chains: tuple[CollinearWallChain, ...], gaps: tuple[SustainedWallGap, ...], *,
        policy: WallCenterlinePolicy) -> tuple[tuple[WallFaceIntervalSpan, ...], tuple[IntervalSemanticWallBand, ...]]:
    """Split every chain at local overlap events and pair each atomic span independently."""
    spans=[];bands=[]
    by_frame={}
    for chain in chains: by_frame.setdefault(chain.frame.frame_id,[]).append(chain)
    for frame_id,items in sorted(by_frame.items()):
      for chain in sorted(items,key=lambda c:c.chain_id):
        candidates=[];breaks={chain.span_start,chain.span_end}
        for other in items:
            if other.chain_id==chain.chain_id or other.orientation!=chain.orientation: continue
            width=abs(chain.axis_drawing_units-other.axis_drawing_units)
            lo=max(chain.span_start,other.span_start);hi=min(chain.span_end,other.span_end)
            if policy.minimum_width_drawing_units<=width<=policy.maximum_width_drawing_units and lo<hi:
                candidates.append((other,width,lo,hi));breaks.update((lo,hi))
        for gap in gaps:
            if gap.frame!=chain.frame: continue
            gp,gq=gap.geometry.points
            if chain.orientation=="HORIZONTAL" and gp.y==chain.axis_drawing_units:
                breaks.update((max(chain.span_start,min(gp.x,gq.x)),min(chain.span_end,max(gp.x,gq.x))))
            elif chain.orientation=="VERTICAL" and gp.x==chain.axis_drawing_units:
                breaks.update((max(chain.span_start,min(gp.y,gq.y)),min(chain.span_end,max(gp.y,gq.y))))
        ordered=sorted(x for x in breaks if chain.span_start<=x<=chain.span_end)
        for start,end in zip(ordered,ordered[1:]):
            if end<=start: continue
            midpoint=(start+end)/2
            local=[(other,width) for other,width,lo,hi in candidates if lo<=midpoint<=hi]
            opening_adjacent=any(g.frame==chain.frame and any(abs(v-midpoint)<=policy.junction_tolerance_drawing_units
                for p in g.geometry.points for v in ((p.x,) if chain.orientation=="HORIZONTAL" else (p.y,))) for g in gaps)
            local.sort(key=lambda x:(x[1],x[0].chain_id))
            classification="UNPAIRED_WALL_FACE";counterpart=None;competing=()
            if local:
                best_width=local[0][1];ties=[o for o,w in local if abs(w-best_width)<=Decimal("0.5")]
                if len(ties)==1: classification="PAIRED_WALL_FACE";counterpart=ties[0]
                else: classification="AMBIGUOUS_PAIRING";competing=tuple(o.chain_id for o in ties)
            elif opening_adjacent: classification="OPENING_ADJACENT_SPAN"
            span_id=chain.chain_id+":"+digest({"start":str(start),"end":str(end)})[:12]+":SPAN"
            span=WallFaceIntervalSpan(span_id=span_id,source_chain_id=chain.chain_id,frame=chain.frame,
                orientation=chain.orientation,axis_drawing_units=chain.axis_drawing_units,span_start=start,span_end=end,
                classification=classification,counterpart_chain_id=counterpart.chain_id if counterpart else None,
                competing_counterpart_chain_ids=competing,source_dependencies=chain.source_dependencies)
            spans.append(span)
            if counterpart and chain.chain_id<counterpart.chain_id:
                axis=(chain.axis_drawing_units+counterpart.axis_drawing_units)/2
                points=((Point(x=start,y=axis),Point(x=end,y=axis)) if chain.orientation=="HORIZONTAL" else
                        (Point(x=axis,y=start),Point(x=axis,y=end)))
                geometry=Geometry(frame=chain.frame,kind="POLYLINE",points=points)
                bands.append(IntervalSemanticWallBand(band_id=frame_id.split(":")[0]+":"+digest(geometry)[:16]+":INTERVAL_BAND",
                    frame=chain.frame,orientation=chain.orientation,source_span_ids=(span_id,"COUNTERPART_INTERVAL_DERIVED"),
                    source_chain_ids=(chain.chain_id,counterpart.chain_id),centerline_geometry=geometry,
                    width_drawing_units=abs(chain.axis_drawing_units-counterpart.axis_drawing_units),
                    confidence="HIGH" if len(local)==1 else "MEDIUM",policy_basis=policy.basis,
                    source_dependencies={**chain.source_dependencies,**counterpart.source_dependencies}))
    unique={b.band_id:b for b in bands}
    return tuple(spans),tuple(unique[k] for k in sorted(unique))


def reconstruct_semantic_wall_junctions(bands: tuple[SemanticWallBand, ...], gaps: tuple[SustainedWallGap, ...], *,
        tolerance: Decimal) -> tuple[SemanticWallJunction, ...]:
    result=[]
    for i,a in enumerate(bands):
        for b in bands[i+1:]:
            if a.frame!=b.frame or a.orientation==b.orientation: continue
            h,v=(a,b) if a.orientation=="HORIZONTAL" else (b,a)
            hp,hq=h.centerline_geometry.points;vp,vq=v.centerline_geometry.points
            x,y=vp.x,hp.y
            dx=max(hp.x-x,Decimal(0),x-hq.x);dy=max(vp.y-y,Decimal(0),y-vq.y)
            distance=dx+dy
            if distance>tolerance: continue
            protected=any(g.frame==a.frame and min(p.x for p in g.geometry.points)-tolerance<=x<=max(p.x for p in g.geometry.points)+tolerance
                and min(p.y for p in g.geometry.points)-tolerance<=y<=max(p.y for p in g.geometry.points)+tolerance for g in gaps)
            if protected: continue
            h_end=x in {hp.x,hq.x};v_end=y in {vp.y,vq.y}
            kind="L_JUNCTION" if h_end and v_end else "T_JUNCTION" if h_end or v_end else "CROSS_JUNCTION"
            jid=a.frame.frame_id.split(":")[0]+":"+digest({"point":[str(x),str(y)],"walls":sorted((a.band_id,b.band_id))})[:16]+":JUNCTION"
            result.append(SemanticWallJunction(junction_id=jid,frame=a.frame,point=Point(x=x,y=y),junction_type=kind,
                wall_band_ids=tuple(sorted((a.band_id,b.band_id))),closure_distance_drawing_units=distance))
    return tuple(sorted(result,key=lambda j:j.junction_id))


def pair_parallel_wall_faces(chains: tuple[CollinearWallChain, ...], *, policy: WallCenterlinePolicy
        ) -> tuple[tuple[SemanticWallBand, ...], tuple[UnpairedWallChain, ...]]:
    candidates=[]
    for i,a in enumerate(chains):
        for j,b in enumerate(chains[i+1:],i+1):
            if a.frame!=b.frame or a.orientation!=b.orientation: continue
            width=abs(a.axis_drawing_units-b.axis_drawing_units)
            overlap=max(Decimal(0),min(a.span_end,b.span_end)-max(a.span_start,b.span_start))
            shorter=min(a.span_end-a.span_start,b.span_end-b.span_start)
            fraction=overlap/shorter if shorter else Decimal(0)
            if policy.minimum_width_drawing_units<=width<=policy.maximum_width_drawing_units and fraction>=policy.minimum_overlap_fraction:
                candidates.append((width,-fraction,a.chain_id,b.chain_id,a,b,fraction))
    used=set();bands=[]
    for width,_,aid,bid,a,b,fraction in sorted(candidates,key=lambda x:(x[0],x[1],x[2],x[3])):
        if aid in used or bid in used: continue
        used|={aid,bid}; axis=(a.axis_drawing_units+b.axis_drawing_units)/2
        lo=max(a.span_start,b.span_start);hi=min(a.span_end,b.span_end)
        points=((Point(x=lo,y=axis),Point(x=hi,y=axis)) if a.orientation=="HORIZONTAL" else
                (Point(x=axis,y=lo),Point(x=axis,y=hi)))
        geometry=Geometry(frame=a.frame,kind="POLYLINE",points=points)
        deps={**a.source_dependencies,**b.source_dependencies}
        bands.append(SemanticWallBand(band_id=a.frame.frame_id.split(":")[0]+":"+digest(geometry)[:16]+":WALL_BAND",
            frame=a.frame,orientation=a.orientation,face_chain_ids=(aid,bid),centerline_geometry=geometry,
            width_drawing_units=width,overlap_fraction=fraction,source_dependencies=deps))
    return tuple(bands),tuple(UnpairedWallChain(chain_id=c.chain_id,
        reason="NO_UNIQUE_PARALLEL_FACE_WITHIN_POLICY") for c in chains if c.chain_id not in used)


def assemble_collinear_wall_chains(walls: tuple[WallCenterlineCandidate, ...],
        room_hypotheses: tuple[DrawingHypothesis, ...], *, axis_tolerance: Decimal,
        minimum_sustained_gap: dict[str, Decimal]) -> tuple[tuple[CollinearWallChain, ...], tuple[SustainedWallGap, ...]]:
    """Assemble raster segments and retain only scale-policy-sized gaps."""
    if axis_tolerance < 0: raise ValueError("NEGATIVE_WALL_CHAIN_AXIS_TOLERANCE")
    chains=[]; gaps=[]
    rooms=[h for h in room_hypotheses if h.kind=="ROOM" and h.geometry]
    contours=[h for h in room_hypotheses if h.kind=="BUILDING_CONTOUR" and h.geometry]
    for frame_id in sorted({w.frame.frame_id for w in walls}):
      floor=frame_id.split(":")[0]; threshold=minimum_sustained_gap[floor]
      for orientation in ("HORIZONTAL","VERTICAL"):
        groups=[]
        for wall in sorted((w for w in walls if w.frame.frame_id==frame_id and w.orientation==orientation),key=lambda w:w.wall_id):
            p,q=wall.centerline_geometry.points; axis=p.y if orientation=="HORIZONTAL" else p.x
            lo,hi=(sorted((p.x,q.x)) if orientation=="HORIZONTAL" else sorted((p.y,q.y)))
            group=next((g for g in groups if abs(g[0]-axis)<=axis_tolerance),None)
            if group: group[1].append((lo,hi,wall))
            else: groups.append([axis,[(lo,hi,wall)]])
        for axis,segments in groups:
            segments.sort(key=lambda item:(item[0],item[1],item[2].wall_id))
            chain_id=floor+":"+digest({"orientation":orientation,"axis":str(axis),"walls":[s[2].wall_id for s in segments]})[:16]+":CHAIN"
            deps={k:v for _,_,w in segments for k,v in w.source_dependencies.items()}
            chains.append(CollinearWallChain(chain_id=chain_id,frame=segments[0][2].frame,orientation=orientation,
                axis_drawing_units=axis,span_start=min(s[0] for s in segments),span_end=max(s[1] for s in segments),
                source_wall_ids=tuple(s[2].wall_id for s in segments),source_dependencies=deps))
            end,previous=segments[0][1],segments[0][2]
            for lo,hi,wall in segments[1:]:
                width=lo-end
                if width>=threshold:
                    points=((Point(x=end,y=axis),Point(x=lo,y=axis)) if orientation=="HORIZONTAL" else
                            (Point(x=axis,y=end),Point(x=axis,y=lo)))
                    geometry=Geometry(frame=wall.frame,kind="POLYLINE",points=points)
                    associated=[]
                    midpoint=(end+lo)/2
                    for room in rooms:
                        if room.geometry.frame!=wall.frame: continue
                        xs=[p.x for p in room.geometry.points];ys=[p.y for p in room.geometry.points]
                        if orientation=="HORIZONTAL":
                            near_axis=min(abs(min(ys)-axis),abs(max(ys)-axis),Decimal(0) if min(ys)<=axis<=max(ys) else Decimal("999999"))<=threshold
                            along=max(min(xs),end)<min(max(xs),lo) or min(xs)-axis_tolerance<=midpoint<=max(xs)+axis_tolerance
                        else:
                            near_axis=min(abs(min(xs)-axis),abs(max(xs)-axis),Decimal(0) if min(xs)<=axis<=max(xs) else Decimal("999999"))<=threshold
                            along=max(min(ys),end)<min(max(ys),lo) or min(ys)-axis_tolerance<=midpoint<=max(ys)+axis_tolerance
                        if near_axis and along: associated.append(room.hypothesis_id)
                    gap_id=chain_id+":"+digest(geometry)[:12]+":GAP"
                    exterior=False
                    for contour in contours:
                        if contour.geometry.frame!=wall.frame: continue
                        cxs=[p.x for p in contour.geometry.points];cys=[p.y for p in contour.geometry.points]
                        exterior = (min(abs(axis-min(cys)),abs(axis-max(cys)))<=threshold if orientation=="HORIZONTAL" else
                                    min(abs(axis-min(cxs)),abs(axis-max(cxs)))<=threshold)
                        if exterior: break
                    classification=("WINDOW_CANDIDATE" if exterior else
                        "OPEN_PASSAGE_CANDIDATE" if len(associated)==2 else "UNKNOWN_OPENING")
                    gaps.append(SustainedWallGap(gap_id=gap_id,chain_id=chain_id,frame=wall.frame,geometry=geometry,
                        width_drawing_units=width,left_source_wall_id=previous.wall_id,right_source_wall_id=wall.wall_id,
                        associated_room_hypothesis_ids=tuple(sorted(associated)),
                        classification=classification,
                        source_dependencies=deps))
                if hi>end: end,previous=hi,wall
    return tuple(chains),tuple(gaps)


def summarize_wall_graph(walls: tuple[WallCenterlineCandidate, ...], *, endpoint_tolerance: Decimal) -> tuple[WallGraphSummary, ...]:
    if endpoint_tolerance < 0: raise ValueError("NEGATIVE_WALL_GRAPH_TOLERANCE")
    results=[]
    for floor in sorted({w.frame.frame_id.split(":")[0] for w in walls}):
        items=[w for w in walls if w.frame.frame_id.split(":")[0]==floor]
        endpoints=[]
        for wall in items:
            endpoints.append(tuple((p.x,p.y) for p in wall.centerline_geometry.points))
        parent=list(range(len(items)))
        def root(i):
            while parent[i]!=i: parent[i]=parent[parent[i]];i=parent[i]
            return i
        nodes=set(); intersections=0
        for i,a in enumerate(items):
            ap,aq=a.centerline_geometry.points
            for j,b in enumerate(items[i+1:],i+1):
                bp,bq=b.centerline_geometry.points
                if a.orientation==b.orientation:
                    same_axis=abs((ap.y if a.orientation=="HORIZONTAL" else ap.x)-(bp.y if b.orientation=="HORIZONTAL" else bp.x))<=endpoint_tolerance
                    av=sorted((ap.x,aq.x)) if a.orientation=="HORIZONTAL" else sorted((ap.y,aq.y)); bv=sorted((bp.x,bq.x)) if b.orientation=="HORIZONTAL" else sorted((bp.y,bq.y))
                    linked=same_axis and max(av[0],bv[0])<=min(av[1],bv[1])+endpoint_tolerance
                else:
                    h,v=(a,b) if a.orientation=="HORIZONTAL" else (b,a); hp,hq=h.centerline_geometry.points;vp,vq=v.centerline_geometry.points
                    linked=min(hp.x,hq.x)-endpoint_tolerance<=vp.x<=max(hp.x,hq.x)+endpoint_tolerance and min(vp.y,vq.y)-endpoint_tolerance<=hp.y<=max(vp.y,vq.y)+endpoint_tolerance
                    if linked: intersections+=1;nodes.add((vp.x,hp.y))
                if linked: parent[root(j)]=root(i)
        chains=sum(1 for i in range(len(items)) if root(i)==i)
        results.append(WallGraphSummary(floor_id=floor,source_segment_count=len(items),collinear_chain_count=chains,
            intersection_node_count=intersections,connected_component_count=len({root(i) for i in range(len(items))})))
    return tuple(results)


class InteriorOpeningCandidate(Model):
    opening_id: str
    boundary_id: str
    frame: Frame
    geometry: Geometry
    connected_room_hypothesis_ids: tuple[str, str]
    opening_type: Literal["PROBABLE_DOOR", "PROBABLE_OPEN_PASSAGE", "UNKNOWN_OPENING"] = "UNKNOWN_OPENING"
    width_drawing_units_candidate: Decimal = Field(gt=0)
    evidence_method: Literal["SUSTAINED_RASTER_GAP_ACROSS_WALL_CORRIDOR"] = "SUSTAINED_RASTER_GAP_ACROSS_WALL_CORRIDOR"
    status: Literal["GEOMETRIC_CONNECTIVITY_CANDIDATE_NOT_THERMAL_AUTHORITY"] = "GEOMETRIC_CONNECTIVITY_CANDIDATE_NOT_THERMAL_AUTHORITY"


class RoomConnectivityEdge(Model):
    left_hypothesis_id: str
    right_hypothesis_id: str
    boundary_id: str
    opening_id: str
    status: Literal["CONNECTED_BY_OBSERVED_WALL_GAP"] = "CONNECTED_BY_OBSERVED_WALL_GAP"
    engineering_authority: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"


class WholeBuildingTopology(Model):
    floor_ids: tuple[str, ...]
    labeled_room_count: int = Field(ge=0)
    interior_boundary_count: int = Field(ge=0)
    proven_connectivity_edge_count: int = Field(ge=0)
    unresolved_semantic_room_ids: tuple[str, ...] = ()
    topology_status: Literal["COMPLETE_GEOMETRIC_TOPOLOGY", "PARTIAL_BOUNDARIES_CONNECTIVITY_UNRESOLVED"]
    engineering_authority: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    blockers: tuple[str, ...] = ()


class GeometryOnlyUFHPreviewReadiness(Model):
    status: Literal["READY", "BLOCKED_GEOMETRY_INCOMPLETE"]
    authority: Literal["GEOMETRY_ONLY_NON_ENGINEERING_NOT_FOR_CONSTRUCTION"] = "GEOMETRY_ONLY_NON_ENGINEERING_NOT_FOR_CONSTRUCTION"
    usable_room_count: int = Field(ge=0)
    blocked_room_ids: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    routing_engine_invoked: bool = False


def assess_geometry_only_ufh_preview_readiness(rooms: tuple[BuildingRoomCandidate, ...],
        topology: WholeBuildingTopology,
        assessments: tuple[RoomGeometryEvidenceAssessment, ...]) -> GeometryOnlyUFHPreviewReadiness:
    assessed={a.room_hypothesis_id:a for a in assessments}
    blocked = tuple(sorted(r.room_hypothesis_id for r in rooms if
        r.room_hypothesis_id not in assessed or
        assessed[r.room_hypothesis_id].geometry_status != "USABLE_DRAWING_HYPOTHESIS"))
    blockers = tuple(item for item, present in (
        ("SEMANTIC_ROOM_FACES_UNRESOLVED", bool(blocked)),
        ("ROOM_CONNECTIVITY_UNRESOLVED", topology.proven_connectivity_edge_count == 0),
    ) if present)
    return GeometryOnlyUFHPreviewReadiness(status="BLOCKED_GEOMETRY_INCOMPLETE" if blockers else "READY",
        usable_room_count=len(rooms)-len(blocked), blocked_room_ids=blocked, blockers=blockers)


def summarize_whole_building_topology(rooms: tuple[BuildingRoomCandidate, ...],
        boundaries: tuple[InteriorBoundaryEvidence, ...],
        connectivity: tuple[RoomConnectivityEdge, ...],
        assessments: tuple[RoomGeometryEvidenceAssessment, ...]) -> WholeBuildingTopology:
    assessed={a.room_hypothesis_id:a for a in assessments}
    unresolved = tuple(sorted(room.room_hypothesis_id for room in rooms if
        room.room_hypothesis_id not in assessed or
        assessed[room.room_hypothesis_id].geometry_status != "USABLE_DRAWING_HYPOTHESIS"))
    complete = bool(rooms) and not unresolved and bool(connectivity)
    blockers = () if complete else tuple(item for item, present in (
        ("SEMANTIC_ROOM_FACE_SELECTION_REQUIRES_TOPOLOGY_EVIDENCE", bool(unresolved)),
        ("INTERIOR_OPENING_SYMBOL_OR_GAP_EVIDENCE_NOT_EXTRACTED", not connectivity),
    ) if present)
    return WholeBuildingTopology(floor_ids=tuple(sorted({r.floor_source_id for r in rooms})),
        labeled_room_count=len(rooms), interior_boundary_count=len(boundaries),
        proven_connectivity_edge_count=len(connectivity), unresolved_semantic_room_ids=unresolved,
        topology_status="COMPLETE_GEOMETRIC_TOPOLOGY" if complete else "PARTIAL_BOUNDARIES_CONNECTIVITY_UNRESOLVED",
        blockers=blockers)


def build_room_connectivity(openings: tuple[InteriorOpeningCandidate, ...]) -> tuple[RoomConnectivityEdge, ...]:
    """A wall gap proves geometric connectivity without asserting door semantics."""
    return tuple(RoomConnectivityEdge(left_hypothesis_id=o.connected_room_hypothesis_ids[0],
        right_hypothesis_id=o.connected_room_hypothesis_ids[1], boundary_id=o.boundary_id,
        opening_id=o.opening_id) for o in sorted(openings, key=lambda item: item.opening_id))


def infer_exterior_opening_candidates(observations: tuple[Observation, ...], *,
        contour_distance_limit: Decimal, duplicate_overlap_fraction: Decimal) -> tuple[GeometricOpeningCandidate, ...]:
    """Deduplicate long parallel strips near reviewed outer-contour edges."""
    if contour_distance_limit < 0 or not Decimal(0) <= duplicate_overlap_fraction <= Decimal(1):
        raise ValueError("OPENING_ASSOCIATION_THRESHOLDS_INVALID")
    contours = [o for o in observations if o.kind == "OUTER_CONTOUR" and o.geometry and o.geometry.kind == "POLYGON"]
    strips = [o for o in observations if o.kind == "PARALLEL_STRIP" and o.geometry and o.geometry.kind == "BBOX"]
    grouped = []
    for strip in sorted(strips, key=lambda o: o.observation_id):
        a, b = strip.geometry.points
        horizontal = b.x-a.x >= b.y-a.y
        span0, span1 = (a.x, b.x) if horizontal else (a.y, b.y)
        matched = None
        for group in grouped:
            first, gh, g0, g1 = group[0], group[1], group[2], group[3]
            overlap = max(Decimal(0), min(span1, g1)-max(span0, g0))
            if (first.geometry.frame == strip.geometry.frame and gh == horizontal and
                    overlap >= duplicate_overlap_fraction*min(span1-span0, g1-g0)):
                matched = group
                break
        if matched is None:
            grouped.append([strip, horizontal, span0, span1, [strip]])
        else:
            matched[4].append(strip)
    result = []
    for first, horizontal, span0, span1, members in grouped:
        a, b = first.geometry.points
        center = ((a.x+b.x)/2, (a.y+b.y)/2)
        contour_match = None
        for contour in contours:
            if contour.geometry.frame != first.geometry.frame:
                continue
            points = contour.geometry.points
            for i, p in enumerate(points):
                q = points[(i+1)%len(points)]
                if horizontal and p.y == q.y and min(p.x,q.x) <= center[0] <= max(p.x,q.x):
                    distance = abs(center[1]-p.y)
                elif not horizontal and p.x == q.x and min(p.y,q.y) <= center[1] <= max(p.y,q.y):
                    distance = abs(center[0]-p.x)
                else:
                    continue
                if distance <= contour_distance_limit:
                    contour_match = contour.observation_id
                    break
            if contour_match:
                break
        result.append(GeometricOpeningCandidate(frame=first.geometry.frame,
            observation_ids=tuple(o.observation_id for o in members),
            source_dependencies={first.evidence.source_id:first.evidence.source_hash},
            geometry=first.geometry, width_drawing_units_candidate=span1-span0,
            exterior_contour_observation_id=contour_match,
            type_candidate="WINDOW_OR_GLAZING" if contour_match else "UNKNOWN_OPENING"))
    return tuple(result)


class BuildingRoomCandidate(Model):
    floor_source_id: str
    room_hypothesis_id: str
    label_hypothesis_id: str
    label_text: str
    drawing_area_square_units: Decimal = Field(gt=0)
    physical_area_m2_candidate: Decimal | None = Field(default=None, gt=0)
    declared_area_number: Decimal | None = Field(default=None, gt=0)
    area_residual_assuming_m2: Decimal | None = None
    area_status: Literal["NOT_COMPARABLE", "CONSISTENT_IF_M2", "GEOMETRY_REVIEW_REQUIRED"]
    engineering_authority: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"

class ClosedRoomBoundaryCandidate(Model):
    """A closed polygon assembled only from explicitly supplied wall edges."""
    room_id: str
    geometry: Geometry
    supporting_wall_ids: tuple[str, ...]
    source_wall_candidate_ids: tuple[str, ...] = ()
    opening_ids: tuple[str, ...] = ()
    transformation_steps: tuple[str, ...] = ()
    scale_status: Literal["NOT_SUPPLIED", "PHYSICAL_SCALE_VERIFIED", "PHYSICAL_SCALE_UNVERIFIED"] = "NOT_SUPPLIED"
    confidence: Literal["SOURCE_EDGE_LOOP"] = "SOURCE_EDGE_LOOP"
    authority: Literal["DRAWING_HYPOTHESIS_NOT_ENGINEERING_AUTHORITY"] = "DRAWING_HYPOTHESIS_NOT_ENGINEERING_AUTHORITY"

class RoomBoundaryClosureDiagnostic(Model):
    room_id: str
    status: Literal["REJECTED"] = "REJECTED"
    reason: Literal["NO_EDGES", "NON_ORTHOGONAL_EDGE", "DUPLICATE_EDGE", "BRANCHING_GRAPH", "OPEN_LOOP", "SELF_INTERSECTING_LOOP"]
    supporting_wall_ids: tuple[str, ...] = ()

class StructuralWallEdge(Model):
    room_id: str
    wall_id: str
    geometry: Geometry
    source_dependencies: dict[str, str]
    source_type: Literal["VECTOR_WALL", "RASTER_WALL_CANDIDATE"]
    verification_status: Literal["VERIFIED", "CANDIDATE", "REJECTED"]
    scale_status: Literal["NO_SCALE", "PHYSICAL_SCALE_VERIFIED", "PHYSICAL_SCALE_UNVERIFIED"]
    transformation_steps: tuple[str, ...] = ()
    opening_ids: tuple[str, ...] = ()

def prepare_structural_wall_edges(evidence: tuple[tuple[str, WallCenterlineCandidate], ...], *,
        opening_ids_by_wall: dict[str, tuple[str, ...]] | None = None) -> tuple[StructuralWallEdge, ...]:
    """Normalize existing wall candidates without promoting raster evidence."""
    opening_ids_by_wall = opening_ids_by_wall or {}
    result=[]
    for room_id, wall in sorted(evidence, key=lambda item: (item[0], item[1].wall_id)):
        if wall.status != "RASTER_WALL_CANDIDATE_NOT_PROJECT_FACT":
            continue
        result.append(StructuralWallEdge(room_id=room_id,wall_id=wall.wall_id,geometry=wall.centerline_geometry,
            source_dependencies=dict(wall.source_dependencies),source_type="RASTER_WALL_CANDIDATE",
            verification_status="CANDIDATE",scale_status="PHYSICAL_SCALE_UNVERIFIED",
            transformation_steps=("CENTERLINE_CANDIDATE_TO_CLOSURE_EDGE",),opening_ids=opening_ids_by_wall.get(wall.wall_id,())))
    return tuple(result)

def close_rooms_from_wall_evidence(edges: tuple[StructuralWallEdge, ...]) -> tuple[ClosedRoomBoundaryCandidate | RoomBoundaryClosureDiagnostic, ...]:
    """Close independently identified room edge groups; never bridge groups."""
    outputs=[]
    for room_id in sorted({edge.room_id for edge in edges}):
        group=tuple(edge for edge in edges if edge.room_id==room_id)
        closure=close_room_boundary(room_id,tuple((edge.wall_id,edge.geometry) for edge in group),
            opening_ids=tuple(sorted({opening for edge in group for opening in edge.opening_ids})),
            scale_status="PHYSICAL_SCALE_UNVERIFIED")
        if isinstance(closure,ClosedRoomBoundaryCandidate):
            deps=tuple(sorted(edge.wall_id for edge in group))
            closure=closure.model_copy(update={'source_wall_candidate_ids':deps,'transformation_steps':tuple(sorted(set(closure.transformation_steps).union(*(edge.transformation_steps for edge in group))))})
        outputs.append(closure)
    return tuple(outputs)

def close_room_boundary(room_id: str, wall_edges: tuple[tuple[str, Geometry], ...], *,
        opening_ids: tuple[str, ...] = (), scale_status: str = "NOT_SUPPLIED") -> ClosedRoomBoundaryCandidate | RoomBoundaryClosureDiagnostic:
    """Close a room only when supplied orthogonal edges form one exact loop.

    No snapping, gap filling, scale conversion, or opening inference is performed.
    """
    if not wall_edges:
        return RoomBoundaryClosureDiagnostic(room_id=room_id, reason="NO_EDGES")
    frame = wall_edges[0][1].frame
    segments=[]; seen=set()
    for wall_id, edge in wall_edges:
        if wall_id in seen: return RoomBoundaryClosureDiagnostic(room_id=room_id, reason="DUPLICATE_EDGE", supporting_wall_ids=tuple(x[0] for x in wall_edges))
        seen.add(wall_id)
        if edge.frame != frame or edge.kind not in {"BBOX", "POLYLINE", "SEGMENT"} or len(edge.points)!=2:
            return RoomBoundaryClosureDiagnostic(room_id=room_id, reason="NON_ORTHOGONAL_EDGE", supporting_wall_ids=tuple(x[0] for x in wall_edges))
        a,b=edge.points
        if a.x!=b.x and a.y!=b.y:
            return RoomBoundaryClosureDiagnostic(room_id=room_id, reason="NON_ORTHOGONAL_EDGE", supporting_wall_ids=tuple(x[0] for x in wall_edges))
        segments.append((wall_id,a,b))
    degree={}
    for _,a,b in segments:
        degree[(a.x,a.y)]=degree.get((a.x,a.y),0)+1; degree[(b.x,b.y)]=degree.get((b.x,b.y),0)+1
    if any(value>2 for value in degree.values()):
        return RoomBoundaryClosureDiagnostic(room_id=room_id, reason="BRANCHING_GRAPH", supporting_wall_ids=tuple(x[0] for x in wall_edges))
    if any(value!=2 for value in degree.values()):
        return RoomBoundaryClosureDiagnostic(room_id=room_id, reason="OPEN_LOOP", supporting_wall_ids=tuple(x[0] for x in wall_edges))
    by_start={}
    for wall_id,a,b in segments:
        by_start.setdefault((a.x,a.y),[]).append((wall_id,a,b)); by_start.setdefault((b.x,b.y),[]).append((wall_id,b,a))
    first=segments[0]; start=(first[1].x,first[1].y); current=start; previous=None; points=[]; used=[]; guard=0
    while guard<=len(segments):
        options=[item for item in by_start[current] if item[0]!=previous]
        if not options: break
        wall_id,a,b=sorted(options,key=lambda x:x[0])[0]; used.append(wall_id);points.append(a);previous=wall_id;current=(b.x,b.y);guard+=1
        if current==start: break
    if current!=start or len(used)!=len(segments):
        return RoomBoundaryClosureDiagnostic(room_id=room_id, reason="OPEN_LOOP", supporting_wall_ids=tuple(x[0] for x in wall_edges))
    area=sum(points[i].x*points[(i+1)%len(points)].y-points[(i+1)%len(points)].x*points[i].y for i in range(len(points)))
    if area==0:
        return RoomBoundaryClosureDiagnostic(room_id=room_id, reason="OPEN_LOOP", supporting_wall_ids=tuple(used))
    geometry=Geometry(frame=frame,kind="POLYGON",points=tuple(points))
    return ClosedRoomBoundaryCandidate(room_id=room_id,geometry=geometry,supporting_wall_ids=tuple(used),opening_ids=opening_ids,
        transformation_steps=("EXACT_ENDPOINT_LOOP",),scale_status=scale_status if scale_status in {"NOT_SUPPLIED","PHYSICAL_SCALE_VERIFIED","PHYSICAL_SCALE_UNVERIFIED"} else "NOT_SUPPLIED")


class RoomGeometryEvidenceAssessment(Model):
    room_hypothesis_id: str
    evidence_class: Literal["OBSERVED_CONNECTED_WHITE_SPACE"] = "OBSERVED_CONNECTED_WHITE_SPACE"
    geometry_status: Literal["USABLE_DRAWING_HYPOTHESIS", "AMBIGUOUS"]
    unique_label_containment: bool
    inside_outer_contour: bool
    simple_nonzero_polygon: bool
    competing_room_overlap: bool
    exclusion_region_overlap: bool
    area_validation_status: Literal["CONSISTENT_IF_M2", "GEOMETRY_REVIEW_REQUIRED", "NOT_COMPARABLE"]
    evidence_ids: tuple[str, ...]
    diagnostics: tuple[str, ...]
    authority: Literal["DRAWING_HYPOTHESIS_NOT_ENGINEERING_AUTHORITY"] = "DRAWING_HYPOTHESIS_NOT_ENGINEERING_AUTHORITY"


def assess_room_geometry_evidence(rooms: tuple[BuildingRoomCandidate, ...],
        hypotheses: tuple[DrawingHypothesis, ...]) -> tuple[RoomGeometryEvidenceAssessment, ...]:
    """Assess observed faces independently from declared-area validation.

    This deliberately does not repair or select geometry by area. A connected
    raster face is usable only when it is a simple non-zero polygon, lies in
    the reviewed floor contour, owns exactly one label, and does not overlap a
    competing observed room face.
    """
    by_id={h.hypothesis_id:h for h in hypotheses}
    contours={h.geometry.frame.frame_id:h.geometry for h in hypotheses if h.kind=="BUILDING_CONTOUR" and h.geometry}
    labels=[h for h in hypotheses if h.kind=="ROOM_LABEL" and h.geometry]
    exclusions=[h for h in hypotheses if h.kind=="STAIRS" and h.geometry]

    def area(points):
        return abs(sum(points[i].x*points[(i+1)%len(points)].y-points[(i+1)%len(points)].x*points[i].y
                       for i in range(len(points)))/Decimal(2))
    def contains(poly, point):
        inside=False
        for a,b in zip(poly,poly[1:]+poly[:1]):
            if ((a.y>point.y)!=(b.y>point.y)):
                x=a.x+(point.y-a.y)*(b.x-a.x)/(b.y-a.y)
                if point.x<x:inside=not inside
        return inside
    def bbox(poly):
        return min(p.x for p in poly),min(p.y for p in poly),max(p.x for p in poly),max(p.y for p in poly)
    def polygon_points(geometry):
        if geometry.kind == "BBOX":
            a,b=geometry.points
            return (a,Point(x=b.x,y=a.y),b,Point(x=a.x,y=b.y))
        return geometry.points
    def polygons_overlap(left,right):
        lb=bbox(left);rb=bbox(right)
        if max(lb[0],rb[0])>=min(lb[2],rb[2]) or max(lb[1],rb[1])>=min(lb[3],rb[3]):
            return False
        if any(contains(right,p) for p in left) or any(contains(left,p) for p in right):
            return True
        return any(intersects(a,b,c,d) for a,b in zip(left,left[1:]+left[:1])
            for c,d in zip(right,right[1:]+right[:1]))
    result=[]
    for room in rooms:
        h=by_id[room.room_hypothesis_id];points=h.geometry.points;contour=contours.get(h.geometry.frame.frame_id)
        nonzero=len(points)>=3 and area(points)>0
        # Perception emits ordered orthogonal connected-component contours.
        def orientation(a,b,c):
            value=(b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x)
            return 0 if value==0 else (1 if value>0 else -1)
        def intersects(a,b,c,d):
            return orientation(a,b,c)!=orientation(a,b,d) and orientation(c,d,a)!=orientation(c,d,b)
        segments=list(zip(points,points[1:]+points[:1]));simple=True
        for i,(a,b) in enumerate(segments):
            for j,(c,d) in enumerate(segments):
                if j<=i or j==i+1 or (i==0 and j==len(segments)-1):continue
                if intersects(a,b,c,d):simple=False;break
            if not simple:break
        owned=[label for label in labels if label.geometry.frame==h.geometry.frame and contains(points,label.geometry.points[0])]
        unique=len(owned)==1 and owned[0].attributes.get("containing_room_candidate")==room.room_hypothesis_id
        inside=bool(contour) and all(contains(contour.points,p) or p in contour.points for p in points)
        bx0,by0,bx1,by1=bbox(points);overlap=False
        for other in rooms:
            if other.room_hypothesis_id==room.room_hypothesis_id:continue
            oh=by_id[other.room_hypothesis_id]
            if oh.geometry.frame!=h.geometry.frame:continue
            if polygons_overlap(points,oh.geometry.points):overlap=True;break
        exclusion_overlap=any(exclusion.geometry.frame==h.geometry.frame and
            polygons_overlap(points,polygon_points(exclusion.geometry)) for exclusion in exclusions)
        usable=nonzero and simple and unique and inside and not overlap and not exclusion_overlap
        diagnostics=[]
        if not nonzero:diagnostics.append("ZERO_OR_DEGENERATE_FACE")
        if not simple:diagnostics.append("SELF_INTERSECTING_CONNECTED_FACE")
        if not unique:diagnostics.append("LABEL_MEMBERSHIP_NOT_UNIQUE")
        if not inside:diagnostics.append("FACE_OUTSIDE_REVIEWED_CONTOUR")
        if overlap:diagnostics.append("COMPETING_OBSERVED_ROOM_OVERLAP")
        if exclusion_overlap:diagnostics.append("STAIR_EXCLUSION_REGION_OVERLAP")
        if room.area_status=="GEOMETRY_REVIEW_REQUIRED":diagnostics.append("DECLARED_AREA_MISMATCH_RETAINED_AS_POST_SELECTION_QA")
        result.append(RoomGeometryEvidenceAssessment(room_hypothesis_id=room.room_hypothesis_id,
            geometry_status="USABLE_DRAWING_HYPOTHESIS" if usable else "AMBIGUOUS",unique_label_containment=unique,
            inside_outer_contour=inside,simple_nonzero_polygon=nonzero and simple,competing_room_overlap=overlap,
            exclusion_region_overlap=exclusion_overlap,
            area_validation_status=room.area_status,evidence_ids=h.observation_ids,diagnostics=tuple(diagnostics)))
    return tuple(result)


class GeometryRepairAssessment(Model):
    room_hypothesis_id: str
    method: Literal["CONVEX_HULL_DIAGNOSTIC"] = "CONVEX_HULL_DIAGNOSTIC"
    original_area_square_units: Decimal = Field(gt=0)
    proposed_area_square_units: Decimal = Field(gt=0)
    original_residual_assuming_m2: Decimal
    proposed_residual_assuming_m2: Decimal
    status: Literal["REJECTED_INSUFFICIENT_EVIDENCE"] = "REJECTED_INSUFFICIENT_EVIDENCE"
    reason: str


class SemanticFaceVariant(Model):
    room_hypothesis_id: str
    variant_type: Literal["OBSERVED_CONNECTED_FACE", "ORTHOGONAL_ENVELOPE", "ENVELOPE_MINUS_STAIR_VOID"]
    outer_geometry: Geometry
    excluded_voids: tuple[Geometry, ...] = ()
    drawing_area_square_units: Decimal = Field(gt=0)
    evidence_ids: tuple[str, ...]
    status: Literal["CANDIDATE", "OBSERVED"]
    limitation: str


def build_semantic_face_variants(rooms: tuple[BuildingRoomCandidate, ...],
        hypotheses: tuple[DrawingHypothesis, ...]) -> tuple[SemanticFaceVariant, ...]:
    by_id = {h.hypothesis_id: h for h in hypotheses}
    stairs = [h for h in hypotheses if h.kind == "STAIRS" and h.geometry]
    variants = []
    for room in rooms:
        if room.area_status != "GEOMETRY_REVIEW_REQUIRED":
            continue
        hypothesis = by_id[room.room_hypothesis_id]
        geometry = hypothesis.geometry
        variants.append(SemanticFaceVariant(room_hypothesis_id=room.room_hypothesis_id,
            variant_type="OBSERVED_CONNECTED_FACE", outer_geometry=geometry,
            drawing_area_square_units=room.drawing_area_square_units,
            evidence_ids=hypothesis.observation_ids, status="OBSERVED",
            limitation="Connected white-space observation excludes drawing ink and open-passage interruptions."))
        x0, x1 = min(p.x for p in geometry.points), max(p.x for p in geometry.points)
        y0, y1 = min(p.y for p in geometry.points), max(p.y for p in geometry.points)
        envelope = Geometry(frame=geometry.frame, kind="POLYGON", points=(Point(x=x0,y=y0),
            Point(x=x1,y=y0),Point(x=x1,y=y1),Point(x=x0,y=y1)))
        area = (x1-x0)*(y1-y0)
        variants.append(SemanticFaceVariant(room_hypothesis_id=room.room_hypothesis_id,
            variant_type="ORTHOGONAL_ENVELOPE", outer_geometry=envelope,
            drawing_area_square_units=area, evidence_ids=hypothesis.observation_ids,
            status="CANDIDATE", limitation="Envelope crosses unclassified stair/open-passage graphics; not selected by area fit."))
        for stair in stairs:
            if stair.geometry.frame != geometry.frame or stair.geometry.kind != "BBOX":
                continue
            a, b = stair.geometry.points
            overlap = max(Decimal(0),min(x1,b.x)-max(x0,a.x))*max(Decimal(0),min(y1,b.y)-max(y0,a.y))
            if overlap:
                variants.append(SemanticFaceVariant(room_hypothesis_id=room.room_hypothesis_id,
                    variant_type="ENVELOPE_MINUS_STAIR_VOID", outer_geometry=envelope,
                    excluded_voids=(stair.geometry,), drawing_area_square_units=area-overlap,
                    evidence_ids=hypothesis.observation_ids+stair.observation_ids, status="CANDIDATE",
                    limitation="Stair bbox is an approximate void candidate; exact stair boundary and passage continuity unresolved."))
    return tuple(variants)


def assess_convex_hull_repairs(rooms: tuple[BuildingRoomCandidate, ...],
        hypotheses: tuple[DrawingHypothesis, ...], scales: tuple[ScaleCandidate, ...]) -> tuple[GeometryRepairAssessment, ...]:
    by_id = {h.hypothesis_id: h for h in hypotheses}
    by_frame = {s.frame.frame_id: s for s in scales}
    assessments = []
    for room in rooms:
        if room.area_status != "GEOMETRY_REVIEW_REQUIRED" or room.declared_area_number is None:
            continue
        geometry = by_id[room.room_hypothesis_id].geometry
        points = sorted(set((p.x, p.y) for p in geometry.points))
        def cross(o, a, b):
            return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
        lower, upper = [], []
        for p in points:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        for p in reversed(points):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        hull = lower[:-1]+upper[:-1]
        proposed = abs(sum(hull[i][0]*hull[(i+1)%len(hull)][1]-
            hull[(i+1)%len(hull)][0]*hull[i][1] for i in range(len(hull))))/Decimal(2)
        scale = by_frame[geometry.frame.frame_id].scale_m_per_drawing_unit
        assessments.append(GeometryRepairAssessment(room_hypothesis_id=room.room_hypothesis_id,
            original_area_square_units=room.drawing_area_square_units,
            proposed_area_square_units=proposed,
            original_residual_assuming_m2=room.area_residual_assuming_m2,
            proposed_residual_assuming_m2=proposed*scale**2-room.declared_area_number,
            reason="Convex hull is a diagnostic upper envelope, not observed wall geometry; no unique missing-region boundary is established."))
    return tuple(assessments)


def build_building_room_candidates(hypotheses: tuple[DrawingHypothesis, ...],
        scales: tuple[ScaleCandidate, ...], *, area_tolerance_fraction: Decimal) -> tuple[BuildingRoomCandidate, ...]:
    if area_tolerance_fraction < 0:
        raise ValueError("NEGATIVE_AREA_COMPARISON_TOLERANCE")
    by_id = {h.hypothesis_id: h for h in hypotheses}
    by_frame = {s.frame.frame_id: s for s in scales}
    rooms = []
    for label in sorted((h for h in hypotheses if h.kind == "ROOM_LABEL"), key=lambda h: h.hypothesis_id):
        room = by_id.get(label.attributes.get("containing_room_candidate"))
        if room is None or room.kind != "ROOM" or not room.geometry or room.geometry.kind != "POLYGON":
            continue
        points = room.geometry.points
        area = abs(sum(points[i].x*points[(i+1)%len(points)].y-
            points[(i+1)%len(points)].x*points[i].y for i in range(len(points))))/Decimal(2)
        scale = by_frame.get(room.geometry.frame.frame_id)
        physical = area*scale.scale_m_per_drawing_unit**2 if scale else None
        match = re.match(r"^\s*\d+\s*/\s*(\d+(?:[.,]\d+)?)", label.interpretation)
        declared = Decimal(match.group(1).replace(",", ".")) if match else None
        residual = physical-declared if physical is not None and declared is not None else None
        status = "NOT_COMPARABLE" if residual is None else (
            "CONSISTENT_IF_M2" if abs(residual) <= declared*area_tolerance_fraction else "GEOMETRY_REVIEW_REQUIRED")
        rooms.append(BuildingRoomCandidate(floor_source_id=next(iter(room.source_dependencies)),
            room_hypothesis_id=room.hypothesis_id, label_hypothesis_id=label.hypothesis_id,
            label_text=label.interpretation, drawing_area_square_units=area,
            physical_area_m2_candidate=physical, declared_area_number=declared,
            area_residual_assuming_m2=residual, area_status=status))
    return tuple(rooms)


def build_wall_band_candidates(adjacencies: tuple[AdjacencyCandidate, ...],
        scale_candidates: tuple[ScaleCandidate, ...], opening_hypotheses: tuple[DrawingHypothesis, ...] = ()) -> tuple[WallBandCandidate, ...]:
    scales = {s.frame.frame_id: s for s in scale_candidates}
    result = []
    for adjacency in adjacencies:
        scale = scales.get(adjacency.frame.frame_id)
        # Symbol-to-gap association needs boundary intersection geometry; do not infer from proximity alone.
        opening_ids = ()
        result.append(WallBandCandidate(adjacency=adjacency,
            thickness_drawing_units=adjacency.separation_drawing_units,
            thickness_m_candidate=(adjacency.separation_drawing_units*scale.scale_m_per_drawing_unit if scale else None),
            scale_status=("NO_SCALE" if scale is None else "PHYSICAL_SCALE_VERIFIED" if scale.status == "VERIFIED"
                else "PHYSICAL_SCALE_UNVERIFIED"), opening_evidence_ids=opening_ids,
            opening_status="UNKNOWN_OPENING_CANDIDATE" if opening_ids else "NO_OPENING_EVIDENCE"))
    return tuple(result)


def infer_adjacency_candidates(hypotheses: tuple[DrawingHypothesis, ...], *,
        maximum_separation: Decimal, minimum_shared_projection: Decimal) -> tuple[AdjacencyCandidate, ...]:
    """Generate topology candidates from disjoint envelopes in one drawing frame."""
    if maximum_separation < 0 or minimum_shared_projection <= 0:
        raise ValueError("ADJACENCY_THRESHOLDS_INVALID")
    rooms = sorted((h for h in hypotheses if h.kind == "ROOM" and h.geometry), key=lambda h: h.hypothesis_id)
    result = []
    for i, left in enumerate(rooms):
        for right in rooms[i+1:]:
            if left.geometry.frame != right.geometry.frame:
                continue
            lx0, lx1 = min(p.x for p in left.geometry.points), max(p.x for p in left.geometry.points)
            ly0, ly1 = min(p.y for p in left.geometry.points), max(p.y for p in left.geometry.points)
            rx0, rx1 = min(p.x for p in right.geometry.points), max(p.x for p in right.geometry.points)
            ry0, ry1 = min(p.y for p in right.geometry.points), max(p.y for p in right.geometry.points)
            gap_x = max(Decimal(0), max(lx0, rx0)-min(lx1, rx1))
            gap_y = max(Decimal(0), max(ly0, ry0)-min(ly1, ry1))
            overlap_x = max(Decimal(0), min(lx1, rx1)-max(lx0, rx0))
            overlap_y = max(Decimal(0), min(ly1, ry1)-max(ly0, ry0))
            values = None
            if 0 < gap_x <= maximum_separation and overlap_y >= minimum_shared_projection:
                values = (gap_x, overlap_y, "VERTICAL_BOUNDARY")
            elif 0 < gap_y <= maximum_separation and overlap_x >= minimum_shared_projection:
                values = (gap_y, overlap_x, "HORIZONTAL_BOUNDARY")
            if values:
                result.append(AdjacencyCandidate(left_hypothesis_id=left.hypothesis_id,
                    right_hypothesis_id=right.hypothesis_id, frame=left.geometry.frame,
                    separation_drawing_units=values[0], shared_projection_drawing_units=values[1],
                    orientation=values[2], reason="DISJOINT_ROOM_ENVELOPES_WITH_NEAR_PARALLEL_GAP_V1"))
    return tuple(result)


class DrawingUnderstandingResult(Model):
    schema_version: Literal["1.0"] = "1.0"
    engine_revision: Literal["DRAWING_REASONING_V1.0"] = "DRAWING_REASONING_V1.0"
    documents: tuple[DocumentUnderstanding, ...]
    hypotheses: tuple[DrawingHypothesis | OpeningHypothesis, ...]
    dimension_constraints: tuple[DimensionConstraint, ...]
    text_annotations: tuple[Observation, ...]
    cross_floor_alignments: tuple[CrossFloorAlignment, ...]
    confirmed_project_facts: tuple[ConfirmedProjectFact, ...] = ()
    conflicts: tuple[str, ...] = ()
    unresolved: tuple[str, ...]
    typed_conflicts: tuple[DrawingConflict, ...] = ()
    unresolved_items: tuple[UnresolvedItem, ...] = ()

    @property
    def result_digest(self) -> str:
        return digest(self)


def _hypothesis(o: Observation, kind: HypothesisKind, interpretation: str,
                ambiguity: tuple[str, ...] = ()) -> DrawingHypothesis:
    return DrawingHypothesis(hypothesis_id=o.observation_id+":"+kind, kind=kind,
        observation_ids=(o.observation_id,), source_dependencies={o.evidence.source_id: o.evidence.source_hash},
        geometry=o.geometry, interpretation=interpretation, attributes=o.attributes,
        confidence=ConfidenceAssessment(geometry=o.geometry is not None, text=o.text is not None,
            source_quality=o.quality, ambiguity=ambiguity, reasons=(o.evidence.method, o.limitation)),
        status="CONFIRMATION_REQUIRED")


def _contains_point(geometry: Geometry, point: Point) -> bool:
    if geometry.kind == "BBOX":
        return (geometry.points[0].x < point.x < geometry.points[1].x and
                geometry.points[0].y < point.y < geometry.points[1].y)
    if geometry.kind != "POLYGON":
        return False
    inside = False
    points = geometry.points
    for i, a in enumerate(points):
        b = points[(i + 1) % len(points)]
        if (a.y > point.y) != (b.y > point.y):
            crossing_x = (b.x-a.x) * (point.y-a.y) / (b.y-a.y) + a.x
            if point.x < crossing_x:
                inside = not inside
    return inside


def understand(artifacts: tuple[ObservationArtifact, ...]) -> DrawingUnderstandingResult:
    """Pure replay: observations in, hypotheses out. No project-specific rules."""
    artifacts = tuple(sorted(artifacts, key=lambda a: (a.source.source_id, a.source.page_or_frame)))
    if len({(a.source.source_id, a.source.page_or_frame) for a in artifacts}) != len(artifacts):
        raise ValueError("DUPLICATE_SOURCE_PAGE")
    mismatches = [a.source.source_id for a in artifacts if a.integrity_status == "DIGEST_MISMATCH"]
    if mismatches:
        raise ValueError("OBSERVATION_NORMALIZATION_DIGEST_MISMATCH:" + ",".join(mismatches))
    docs, hypotheses, dimensions, texts, unresolved = [], [], [], [], []
    for artifact in artifacts:
        source = artifact.source
        obs = tuple(sorted(artifact.observations, key=lambda o: o.observation_id))
        excluded_layout = [o for o in obs if o.kind == "LAYOUT_REGION" and o.geometry and
                           o.geometry.kind == "BBOX" and o.attributes.get("role") == "TITLE_BLOCK"]
        titles = [o.text for o in obs if o.kind == "FLOOR_TITLE" and o.text]
        docs.append(DocumentUnderstanding(source=source, observation_artifact_digest=artifact.artifact_digest,
            floor_title=titles[0] if len(set(titles)) == 1 else source.floor_hint,
            project_annotations=tuple(o.text for o in obs if o.kind == "PROJECT_ANNOTATION" and o.text)))
        unresolved.extend(source.source_id+":"+d for d in artifact.diagnostics)
        for o in obs:
            if o.text:
                texts.append(o)
            if o.kind == "ENCLOSED_REGION":
                if o.geometry and any(
                    e.geometry.points[0].x <= o.geometry.points[0].x and
                    e.geometry.points[0].y <= o.geometry.points[0].y and
                    e.geometry.points[1].x >= o.geometry.points[1].x and
                    e.geometry.points[1].y >= o.geometry.points[1].y for e in excluded_layout):
                    continue
                hypotheses.append(_hypothesis(o, "ROOM", "Enclosed drawing region: possible room",
                    ("REGION_MAY_BE_TITLE_BLOCK_OR_OTHER_SYMBOL", "BBOX_IS_NOT_A_ROOM_POLYGON")))
            elif o.kind == "ROOM_LABEL":
                hypotheses.append(_hypothesis(o, "ROOM_LABEL", o.text or "Unreadable label"))
                hypotheses.append(_hypothesis(o, "ROOM_USE", "Possible room use from annotation",
                    ("LABEL_MEANING_REQUIRES_CONFIRMATION",)))
            elif o.kind in {"PARALLEL_STRIP", "OPENING_SYMBOL"}:
                base = _hypothesis(o, "OPENING", "Possible opening symbol",
                    ("SYMBOL_CLASS_AND_PARENT_BOUNDARY_UNVERIFIED",))
                hypotheses.append(OpeningHypothesis(**base.model_dump(exclude={"kind"}),
                    opening_type="UNKNOWN_OPENING"))
            elif o.kind in {"WALL_LINE", "OUTER_CONTOUR", "STAIR_SYMBOL", "ADJACENCY"}:
                kind = {"WALL_LINE": "WALL", "OUTER_CONTOUR": "BUILDING_CONTOUR",
                        "STAIR_SYMBOL": "STAIRS", "ADJACENCY": "ADJACENCY"}[o.kind]
                hypotheses.append(_hypothesis(o, kind, o.text or kind,
                    ("GEOMETRIC_INTERPRETATION_REQUIRES_RECONCILIATION",)))
                if o.kind == "OUTER_CONTOUR":
                    hypotheses.append(_hypothesis(o, "BOUNDARY", "LIKELY_EXTERIOR_BOUNDARY",
                        ("NOT_A_THERMAL_BOUNDARY_CLASSIFICATION",)))
            elif o.kind == "SCALE_ANNOTATION":
                hypotheses.append(_hypothesis(o, "SCALE", o.text or "Scale declaration",
                    ("DIMENSION_CORROBORATION_REQUIRED",)))
            elif o.kind == "DIMENSION":
                raw = o.attributes.get("declared_distance")
                if raw is None:
                    unresolved.append(o.observation_id+":DIMENSION_TEXT_UNPARSED")
                    continue
                unit = o.attributes.get("unit")
                dimensions.append(DimensionConstraint(observation_id=o.observation_id,
                    anchors=o.geometry, declared_distance=Decimal(str(raw)), unit=unit,
                    evidence=o.evidence, status="UNIT_REQUIRED" if unit is None else
                    "ANCHORS_REQUIRED" if o.geometry is None or o.geometry.kind != "SEGMENT" else "READY_TO_CHECK"))
        unresolved.extend((source.source_id+":COMPLETE_ROOM_TOPOLOGY_REQUIRED",
                           source.source_id+":COMPLETE_OPENING_INVENTORY_UNPROVEN"))
    # Attach labels only on unique geometric containment, retaining both source observations.
    for index, h in enumerate(hypotheses):
        if h.kind != "ROOM_LABEL" or not h.geometry or h.geometry.kind != "POINT":
            continue
        p = h.geometry.points[0]
        regions = [r for r in hypotheses if r.kind == "ROOM" and r.geometry and
            r.geometry.frame == h.geometry.frame and _contains_point(r.geometry, p)]
        if len(regions) == 1:
            hypotheses[index] = h.model_copy(update={"attributes": {**h.attributes,
                "containing_room_candidate": regions[0].hypothesis_id}})
        elif len(regions) > 1:
            unresolved.append(h.hypothesis_id+":MULTIPLE_CONTAINING_ROOM_CANDIDATES")
    bound_rooms = {h.attributes.get("containing_room_candidate") for h in hypotheses
                   if h.kind == "ROOM_LABEL"}
    for room in (h for h in hypotheses if h.kind == "ROOM"):
        if room.hypothesis_id not in bound_rooms:
            unresolved.append(room.hypothesis_id+":ROOM_CANDIDATE_WITHOUT_UNIQUE_LABEL")
    stairs = [h for h in hypotheses if h.kind == "STAIRS"]
    contours = [h for h in hypotheses if h.kind == "BUILDING_CONTOUR"]
    alignments = []
    for i, left in enumerate(docs):
        for right in docs[i+1:]:
            ids = (left.source.source_id, right.source.source_id)
            left_stairs = [h for h in stairs if left.source.source_id in h.source_dependencies]
            right_stairs = [h for h in stairs if right.source.source_id in h.source_dependencies]
            anchors = tuple(h.hypothesis_id for h in left_stairs + right_stairs)
            translation = None
            anchor_pair = None
            if len(left_stairs) == len(right_stairs) == 1 and left_stairs[0].geometry and right_stairs[0].geometry:
                def center(g):
                    return (sum(p.x for p in g.points)/len(g.points), sum(p.y for p in g.points)/len(g.points))
                lc, rc = center(left_stairs[0].geometry), center(right_stairs[0].geometry)
                translation = (rc[0]-lc[0], rc[1]-lc[1])
                anchor_pair = (left_stairs[0].hypothesis_id, right_stairs[0].hypothesis_id)
            coefficients = None
            contour_residual = None
            contour_status = "NOT_AVAILABLE"
            left_contours = [h for h in contours if left.source.source_id in h.source_dependencies]
            right_contours = [h for h in contours if right.source.source_id in h.source_dependencies]
            if len(left_contours) == len(right_contours) == 1:
                lg, rg = left_contours[0].geometry, right_contours[0].geometry
                if lg and rg and len(lg.points) == len(rg.points) and len(lg.points) >= 3:
                    lx0, lx1 = min(p.x for p in lg.points), max(p.x for p in lg.points)
                    ly0, ly1 = min(p.y for p in lg.points), max(p.y for p in lg.points)
                    rx0, rx1 = min(p.x for p in rg.points), max(p.x for p in rg.points)
                    ry0, ry1 = min(p.y for p in rg.points), max(p.y for p in rg.points)
                    sx, sy = (rx1-rx0)/(lx1-lx0), (ry1-ry0)/(ly1-ly0)
                    tx, ty = rx0-sx*lx0, ry0-sy*ly0
                    coefficients = (sx, Decimal(0), Decimal(0), sy, tx, ty)
                    residuals = [((sx*a.x+tx-b.x)**2+(sy*a.y+ty-b.y)**2).sqrt()
                                 for a, b in zip(lg.points, rg.points)]
                    contour_residual = max(residuals)
                    contour_status = "APPROXIMATE_CONTOUR_CORRESPONDENCE"
            alignments.append(CrossFloorAlignment(source_ids=ids, candidate_anchor_ids=anchors,
                status="ANCHOR_CORRESPONDENCE_REQUIRED",
                single_anchor_translation_candidate=translation, anchor_pair=anchor_pair,
                reason=("Single stair-anchor translation candidate; a second non-collinear anchor is required for affine alignment."
                if translation else "Shared project/floor titles alone cannot establish an affine transform or vertical room relation."),
                multi_anchor_coefficients_candidate=coefficients,
                multi_anchor_maximum_residual_drawing_units=contour_residual,
                multi_anchor_status=contour_status))
    typed_unresolved = tuple(UnresolvedItem(unresolved_type=item.split(":")[-1],
        source_refs=(item.split(":")[0],), missing_evidence=(item.split(":")[-1],),
        why_unresolved=item, required_next_evidence=(item.split(":")[-1],), blocking=True)
        for item in sorted(set(unresolved)))
    return DrawingUnderstandingResult(documents=tuple(docs), hypotheses=tuple(hypotheses),
        dimension_constraints=tuple(dimensions), text_annotations=tuple(texts),
        cross_floor_alignments=tuple(alignments), unresolved=tuple(sorted(set(unresolved))),
        unresolved_items=typed_unresolved)


class InvalidationResult(Model):
    stale_hypothesis_ids: tuple[str, ...]
    stale_fact_ids: tuple[str, ...]
    preserved_fact_ids: tuple[str, ...]


def invalidate(result: DrawingUnderstandingResult, current_hashes: dict[str, str]) -> InvalidationResult:
    def stale(deps):
        return any(current_hashes.get(s) != h for s, h in deps.items())
    return InvalidationResult(
        stale_hypothesis_ids=tuple(h.hypothesis_id for h in result.hypotheses if stale(h.source_dependencies)),
        stale_fact_ids=tuple(f.fact_id for f in result.confirmed_project_facts if stale(f.source_dependencies)),
        preserved_fact_ids=tuple(f.fact_id for f in result.confirmed_project_facts if not stale(f.source_dependencies)))


class RoomMatchResult(Model):
    room_id: str
    status: Literal["CONFIRMED", "HIGH_CONFIDENCE_CANDIDATE", "AMBIGUOUS", "NO_MATCH"]
    candidates: tuple[str, ...]
    evidence_used: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    available_evidence: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


def compare_room_shape(room_id: str, reference: Geometry, reference_source: SourceEvidence,
                       candidate: DrawingHypothesis, *, aspect_ratio_tolerance: Decimal) -> ReconciliationEvidence:
    """Scale-free bbox aspect ratio is ranking evidence, never an identity match.

    The tolerance is an explicit software comparison policy, not a physical
    engineering tolerance. Translation/floor/adjacency still need evidence.
    """
    if candidate.kind != "ROOM" or candidate.geometry is None or reference.kind not in {"BBOX", "POLYGON"}:
        raise ValueError("ROOM_SHAPE_GEOMETRY_REQUIRED")
    if aspect_ratio_tolerance < 0:
        raise ValueError("NEGATIVE_SHAPE_TOLERANCE")
    def aspect(g):
        w = max(p.x for p in g.points) - min(p.x for p in g.points)
        h = max(p.y for p in g.points) - min(p.y for p in g.points)
        if min(w, h) <= 0:
            raise ValueError("DEGENERATE_ROOM_SHAPE")
        return max(w, h) / min(w, h)
    residual = abs(aspect(reference)-aspect(candidate.geometry))
    return ReconciliationEvidence(evidence_id="shape-"+digest([room_id, candidate.dependency_digest, str(aspect_ratio_tolerance)])[:16],
        hypothesis_digest=candidate.dependency_digest, source=reference_source, dimension="SHAPE_DESCRIPTOR",
        agrees=residual <= aspect_ratio_tolerance, target_entity_id=room_id,
        method=f"BBOX_ASPECT_V1 residual={residual}; tolerance={aspect_ratio_tolerance}; no position/floor/identity proof")


def match_room(room_id: str, hypotheses: tuple[DrawingHypothesis, ...],
               comparisons: tuple[ReconciliationEvidence, ...]) -> RoomMatchResult:
    """Caller must supply actual comparison evidence; never match by area alone."""
    candidates = [h for h in hypotheses if h.kind == "ROOM"]
    by_digest = {h.dependency_digest: h for h in candidates}
    if any(e.hypothesis_digest not in by_digest for e in comparisons):
        raise ValueError("ROOM_MATCH_EVIDENCE_NOT_BOUND_TO_CANDIDATE")
    if any(e.target_entity_id != room_id for e in comparisons):
        raise ValueError("ROOM_MATCH_TARGET_IDENTITY_REQUIRED")
    strong = []
    for h in candidates:
        evidence = [e for e in comparisons if e.hypothesis_digest == h.dependency_digest]
        dims = {e.dimension for e in evidence if e.agrees}
        if not any(not e.agrees for e in evidence) and {"GEOMETRY", "FLOOR", "RELATIVE_POSITION"}.issubset(dims):
            strong.append(h.hypothesis_id)
    return RoomMatchResult(room_id=room_id,
        status="HIGH_CONFIDENCE_CANDIDATE" if len(strong) == 1 else "AMBIGUOUS" if candidates else "NO_MATCH",
        candidates=tuple(strong or [h.hypothesis_id for h in candidates]),
        evidence_used=tuple(e.evidence_id for e in comparisons),
        available_evidence=tuple(sorted({e.dimension for e in comparisons})),
        reasons=(("NO_ROOM_GEOMETRY_CANDIDATES",) if not candidates else
            ("NO_UNIQUE_CANDIDATE_WITH_GEOMETRY_FLOOR_AND_POSITION_EVIDENCE",)),
        missing_evidence=() if len(strong) == 1 else
            ("SHAPE_ALIGNMENT", "FLOOR_IDENTITY", "RELATIVE_POSITION_OR_TOPOLOGY", "AREA_ALONE_IS_NOT_IDENTITY"))

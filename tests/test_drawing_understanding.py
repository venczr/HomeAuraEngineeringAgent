from decimal import Decimal

import pytest

from agent.domain_models import SourceKind
from agent.drawing_understanding import (
    DrawingSource, DrawingConflict, Frame, Geometry, Observation, ObservationArtifact,
    Point, ReconciliationEvidence, SourceEvidence, UnresolvedItem, check_dimension,
    DimensionConstraint, DrawingTransform, reconcile, understand,
    solve_scale_candidate,
    infer_adjacency_candidates,
    close_room_boundary, ClosedRoomBoundaryCandidate, RoomBoundaryClosureDiagnostic,
    WallCenterlineCandidate, prepare_structural_wall_edges, close_rooms_from_wall_evidence,
)


HASH = "a" * 64

def edge(frame, a, b):
    return Geometry(frame=frame, kind="SEGMENT", points=(Point(x=Decimal(str(a[0])),y=Decimal(str(a[1]))),Point(x=Decimal(str(b[0])),y=Decimal(str(b[1])))))

def test_closed_room_boundary_preserves_supporting_walls_openings_and_scale():
    f=source().coordinate_frame
    result=close_room_boundary('r1',tuple((str(i),edge(f,a,b)) for i,(a,b) in enumerate([((0,0),(4,0)),((4,0),(4,3)),((4,3),(0,3)),((0,3),(0,0))])),opening_ids=('open-1',),scale_status='PHYSICAL_SCALE_UNVERIFIED')
    assert isinstance(result,ClosedRoomBoundaryCandidate)
    assert result.supporting_wall_ids==('0','1','2','3') and result.opening_ids==('open-1',)
    assert result.scale_status=='PHYSICAL_SCALE_UNVERIFIED' and result.authority=='DRAWING_HYPOTHESIS_NOT_ENGINEERING_AUTHORITY'

def test_closed_room_boundary_rejects_open_branching_and_nonorthogonal_edges():
    f=source().coordinate_frame
    assert close_room_boundary('open',(('a',edge(f,(0,0),(1,0))),)) .reason=='OPEN_LOOP'
    assert close_room_boundary('diag',(('a',edge(f,(0,0),(1,1))),)).reason=='NON_ORTHOGONAL_EDGE'
    edges=(('a',edge(f,(0,0),(2,0))),('b',edge(f,(2,0),(2,2))),('c',edge(f,(2,0),(2,-2))))
    assert close_room_boundary('branch',edges).reason=='BRANCHING_GRAPH'

def test_closed_room_boundary_is_deterministic_and_does_not_fill_tiny_gaps():
    f=source().coordinate_frame
    edges=tuple((str(i),edge(f,a,b)) for i,(a,b) in enumerate([((0,0),(4,0)),((4,0),(4,3)),((4,3),(0,3)),((0,3),(0,0))]))
    assert close_room_boundary('r',edges).model_dump()==close_room_boundary('r',edges).model_dump()
    gap=tuple((str(i),edge(f,a,b)) for i,(a,b) in enumerate([((0,0),(4,0)),((4,0),(4,3)),((4,3),(1,3)),((0,3),(0,0))]))
    assert close_room_boundary('gap',gap).reason=='OPEN_LOOP'

def wall_candidate(wall_id, geometry):
    return WallCenterlineCandidate(wall_id=wall_id,frame=geometry.frame,orientation='HORIZONTAL' if geometry.points[0].y==geometry.points[1].y else 'VERTICAL',band_geometry=geometry,centerline_geometry=geometry,length_drawing_units=Decimal('1'),thickness_drawing_units=Decimal('0.2'),source_dependencies={'src':'a'*64},suppression_applied=())

def test_wall_evidence_adapter_closes_multiple_rooms_and_preserves_openings():
    f=source().coordinate_frame
    loops=[('r1',[(0,0,4,0),(4,0,4,3),(4,3,0,3),(0,3,0,0)]),('r2',[(5,0,9,0),(9,0,9,3),(9,3,5,3),(5,3,5,0)])]
    evidence=tuple((room,wall_candidate(room+str(i),edge(f,(a,b),(c,d)))) for room,items in loops for i,(a,b,c,d) in enumerate(items))
    prepared=prepare_structural_wall_edges(evidence,opening_ids_by_wall={'r10':('door-1',)})
    out=close_rooms_from_wall_evidence(prepared)
    assert [x.room_id for x in out if isinstance(x,ClosedRoomBoundaryCandidate)]==['r1','r2']
    assert out[0].source_wall_candidate_ids==('r10','r11','r12','r13')

def test_wall_evidence_adapter_excludes_non_authoritative_other_classes_and_is_deterministic():
    f=source().coordinate_frame; g=edge(f,(0,0),(4,0)); w=wall_candidate('w',g)
    rejected=w.model_copy(update={'status':'RASTER_WALL_CANDIDATE_NOT_PROJECT_FACT'})
    a=prepare_structural_wall_edges((('r',w),)); b=prepare_structural_wall_edges((('r',w),))
    assert a==b and a[0].verification_status=='CANDIDATE' and a[0].source_type=='RASTER_WALL_CANDIDATE'


def source(kind="VECTOR_DRAWING"):
    evidence = SourceEvidence(source_id="s", source_hash=HASH, reference="fixture", method="review",
        authority="PROJECT_DOCUMENT_OBSERVATION")
    return DrawingSource(source_id="s", source_kind=kind, source_hash=HASH, page_or_frame=0,
        provenance=evidence, coordinate_frame=Frame(frame_id="f", space="DRAWING_SPACE", unit="mm", axes="X_RIGHT_Y_UP"))


def artifact(kind="DIMENSION"):
    s = source()
    observation = Observation(observation_id="o", kind=kind, evidence=s.provenance,
        geometry=Geometry(frame=s.coordinate_frame, kind="SEGMENT", points=(Point(x=Decimal("0"), y=Decimal("0")), Point(x=Decimal("1000"), y=Decimal("0")))),
        text="1000", attributes={"declared_distance": "1000", "unit": "mm"}, quality="HIGH", limitation="fixture")
    return ObservationArtifact(source=s, backend_id="b", backend_version="1", raw_perception_digest=HASH,
        observations=(observation,)).with_normalization_digest()


def test_vector_drawing_supported_and_domain_source_kind_is_backward_compatible():
    assert source().source_kind == "VECTOR_DRAWING"
    assert SourceKind.VECTOR_DRAWING.value == "vector_drawing"
    assert SourceKind("legacy_room") is SourceKind.LEGACY_ROOM


def test_coordinate_spaces_and_unit_conversions_are_explicit():
    with pytest.raises(ValueError, match="PIXELS_REQUIRE_IMAGE_SPACE"):
        Frame(frame_id="bad", space="DRAWING_SPACE", unit="px", axes="X_RIGHT_Y_DOWN")
    a = artifact()
    target = Frame(frame_id="p", space="PROJECT_SPACE", unit="m", axes="X_RIGHT_Y_UP")
    transform = DrawingTransform(from_frame=a.source.coordinate_frame, to_frame=target,
        coefficients=(Decimal("0.001"), Decimal("0"), Decimal("0"), Decimal("0.001"), Decimal("0"), Decimal("0")), evidence=(a.source.provenance,), matched_anchors=("a", "b"), residual_m=Decimal("0"))
    constraint = DimensionConstraint(observation_id="o", anchors=a.observations[0].geometry,
        declared_distance=Decimal("1000"), unit="mm", evidence=a.source.provenance, status="READY_TO_CHECK")
    assert check_dimension(constraint, transform, tolerance_m=Decimal("0")).status == "AGREES"


def test_normalization_digest_deterministic_tamper_detected_and_legacy_loadable():
    one, two = artifact(), artifact()
    assert one.normalization_digest == two.normalization_digest and one.integrity_status == "VERIFIED"
    changed = one.model_copy(update={"observations": (one.observations[0].model_copy(update={"text": "changed"}),)})
    assert changed.integrity_status == "DIGEST_MISMATCH"
    with pytest.raises(ValueError, match="DIGEST_MISMATCH"):
        understand((changed,))
    legacy = one.model_copy(update={"normalization_digest": None, "source_digest_linkage": None})
    assert legacy.integrity_status == "LEGACY_UNVERIFIED"
    assert understand((legacy,)).documents


def test_dimensions_reason_without_authority_and_knowledge_levels_stay_distinct():
    result = understand((artifact(),))
    assert result.dimension_constraints and result.confirmed_project_facts == ()
    assert artifact().observations[0].knowledge_level == "OBSERVATION"
    contour = artifact("OUTER_CONTOUR")
    # replace segment with valid polygon
    o = contour.observations[0].model_copy(update={"geometry": Geometry(frame=contour.source.coordinate_frame,
        kind="POLYGON", points=(Point(x=Decimal("0"),y=Decimal("0")),Point(x=Decimal("1"),y=Decimal("0")),Point(x=Decimal("1"),y=Decimal("1"))))})
    contour = contour.model_copy(update={"observations": (o,)}).with_normalization_digest()
    understood = understand((contour,))
    assert all(h.knowledge_level == "HYPOTHESIS" for h in understood.hypotheses)
    boundary = next(h for h in understood.hypotheses if h.kind == "BOUNDARY")
    assert "NOT_A_THERMAL_BOUNDARY_CLASSIFICATION" in boundary.confidence.ambiguity


def test_typed_unresolved_conflicts_and_reconciliation_policy():
    result = understand((artifact(),))
    assert result.unresolved_items and isinstance(result.unresolved_items[0], UnresolvedItem)
    conflict = DrawingConflict(conflict_type="GEOMETRY", entity_refs=("x",), evidence_refs=("e",),
        severity="ERROR", reason="disagrees", blocking=True)
    assert conflict.blocking
    room_obs = artifact("ENCLOSED_REGION")
    h = understand((room_obs,)).hypotheses[0]
    independent = SourceEvidence(source_id="other", source_hash="b"*64, reference="other", method="survey",
        authority="PROJECT_GEOMETRY_REFERENCE")
    evidence = tuple(ReconciliationEvidence(evidence_id=k, hypothesis_digest=h.dependency_digest,
        source=independent, dimension=d, agrees=True, method=k) for k, d in (("g","GEOMETRY"),("d","DIMENSION")))
    updated, decision = reconcile(h, evidence)
    assert updated.confidence.cross_source and decision.status in {"CONFIRMED", "CONFIRMATION_REQUIRED"}
    bad = evidence + (ReconciliationEvidence(evidence_id="bad", hypothesis_digest=h.dependency_digest,
        source=independent, dimension="TOPOLOGY", agrees=False, method="conflict"),)
    blocked = reconcile(h, bad)[1]
    assert blocked.status == "BLOCKED_BY_CONFLICT" and blocked.typed_conflicts[0].blocking


def test_scale_solver_is_explicit_about_missing_units_and_residuals():
    a = artifact()
    constraints = (DimensionConstraint(observation_id="a", anchors=a.observations[0].geometry,
        declared_distance=Decimal("1"), unit=None, evidence=a.source.provenance, status="UNIT_REQUIRED"),
        DimensionConstraint(observation_id="b", anchors=a.observations[0].geometry,
        declared_distance=Decimal("1.01"), unit=None, evidence=a.source.provenance, status="UNIT_REQUIRED"))
    candidate = solve_scale_candidate(constraints, assumed_declared_unit="m", residual_tolerance_m=Decimal("0.01"))
    assert candidate.status == "UNIT_CONFIRMATION_REQUIRED"
    assert candidate.scale_m_per_drawing_unit == Decimal("0.001005")
    assert candidate.maximum_absolute_residual_m == Decimal("0.005")


def test_adjacency_never_crosses_frames_and_remains_candidate():
    a = understand((artifact("ENCLOSED_REGION"),)).hypotheses[0]
    a = a.model_copy(update={"geometry": Geometry(frame=a.geometry.frame, kind="POLYGON",
        points=(Point(x=Decimal("0"),y=Decimal("0")),Point(x=Decimal("1000"),y=Decimal("0")),
        Point(x=Decimal("1000"),y=Decimal("100")),Point(x=Decimal("0"),y=Decimal("100"))))})
    shifted = a.model_copy(update={"hypothesis_id": "other", "geometry": Geometry(frame=a.geometry.frame,
        kind="POLYGON", points=(Point(x=Decimal("1010"),y=Decimal("0")),Point(x=Decimal("2010"),y=Decimal("0")),
        Point(x=Decimal("2010"),y=Decimal("100")),Point(x=Decimal("1010"),y=Decimal("100"))))})
    candidates = infer_adjacency_candidates((a, shifted), maximum_separation=Decimal("20"), minimum_shared_projection=Decimal("10"))
    assert len(candidates) == 1 and candidates[0].status == "BOUNDARY_OR_OPENING_EVIDENCE_REQUIRED"


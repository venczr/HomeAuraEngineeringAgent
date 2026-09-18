"""Fail-closed deterministic replay of the frozen Test_01 drawing review."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from agent.drawing_observation_review import VisualReviewPackage, apply_visual_review
from agent.drawing_perception import LocalDrawingPerceptionBackend
from agent.drawing_understanding import (
    DrawingSource, DrawingUnderstandingResult, Frame, ObservationArtifact,
    RoomMatchResult, SourceEvidence, digest, match_room, understand,
    ScaleCandidate, solve_scale_candidate,
    AdjacencyCandidate, infer_adjacency_candidates,
    ScaleCorroboration, corroborate_scale,
    WallBandCandidate, build_wall_band_candidates,
    BuildingRoomCandidate, build_building_room_candidates,
    GeometryRepairAssessment, assess_convex_hull_repairs,
    GeometricOpeningCandidate, infer_exterior_opening_candidates,
    SemanticFaceVariant, build_semantic_face_variants,
    InteriorBoundaryEvidence, InteriorOpeningCandidate, RoomConnectivityEdge, build_room_connectivity,
    WholeBuildingTopology, summarize_whole_building_topology,
    WallCenterlineCandidate, WallExtractionPolicy, RasterLineRecoveryDiagnostic,
    GeometryOnlyUFHPreviewReadiness, assess_geometry_only_ufh_preview_readiness,
    WallGraphSummary, summarize_wall_graph,
    CollinearWallChain, SustainedWallGap, OpeningRoomBindingDiagnostic, assemble_collinear_wall_chains, diagnose_opening_room_bindings,
    SemanticWallBand, UnpairedWallChain, WallCenterlinePolicy, pair_parallel_wall_faces,
    SemanticWallJunction, reconstruct_semantic_wall_junctions,
    WallFaceIntervalSpan, IntervalSemanticWallBand, pair_wall_faces_by_interval,
    EndpointJunctionDecision, SemanticWallGraphV2, build_semantic_wall_graph_v2,
    SingleFaceCenterlineInference, infer_single_face_centerlines,
    CombinedSemanticWallEdge, NormalizedSemanticWallGraph, build_combined_semantic_edges, normalize_combined_semantic_graph,
    ProvenRoomBoundaryMatch, BoundaryGuidedCenterlineCandidate, match_proven_room_boundaries, infer_boundary_guided_centerlines,
    add_boundary_guided_edges,
    BoundarySupportChain, select_boundary_support_chains,
    add_selected_support_chain_edges,
    RoomGeometryEvidenceAssessment, assess_room_geometry_evidence,
)
from agent.drawing_perception import analyze_interior_boundary_raster, extract_raster_wall_centerlines, recover_targeted_raster_wall_lines
from agent.project_models import StrictProjectModel
from agent.test01_pdf_project_source_ingestion import load_test01_pdf_project_source_ingestion


DEFAULT_FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/drawing_understanding/test01_visual_review_v1.json"


class Test01DrawingUnderstandingResult(StrictProjectModel):
    status: Literal["SUCCEEDED"] = "SUCCEEDED"
    source_hashes: dict[str, str]
    observation_integrity: dict[str, Literal["VERIFIED"]]
    understanding: DrawingUnderstandingResult
    room101_match: RoomMatchResult
    engineering_calculations_run: Literal[False] = False
    replay_digest: str
    perception_mode: Literal["FROZEN_REVIEW_ONLY", "LOCAL_DETERMINISTIC_PLUS_FROZEN_REVIEW"] = "FROZEN_REVIEW_ONLY"
    room_candidate_count: int = 0
    labels_bound_to_room_candidates: int = 0
    scale_candidates: tuple[ScaleCandidate, ...] = ()
    adjacency_candidates: tuple[AdjacencyCandidate, ...] = ()
    scale_corroborations: tuple[ScaleCorroboration, ...] = ()
    project_correspondence_status: Literal["NOT_EVALUATED", "INSUFFICIENT_GEOMETRY"] = "NOT_EVALUATED"
    project_correspondence_available: tuple[str, ...] = ()
    project_correspondence_missing: tuple[str, ...] = ()
    wall_band_candidates: tuple[WallBandCandidate, ...] = ()
    building_rooms: tuple[BuildingRoomCandidate, ...] = ()
    geometry_repair_assessments: tuple[GeometryRepairAssessment, ...] = ()
    document_unit_interpretation: dict[str, str] = {}
    source_discovery: dict[str, object] = {}
    geometric_openings: tuple[GeometricOpeningCandidate, ...] = ()
    semantic_face_variants: tuple[SemanticFaceVariant, ...] = ()
    interior_boundaries: tuple[InteriorBoundaryEvidence, ...] = ()
    interior_openings: tuple[InteriorOpeningCandidate, ...] = ()
    room_connectivity: tuple[RoomConnectivityEdge, ...] = ()
    whole_building_topology: WholeBuildingTopology | None = None
    wall_centerlines: tuple[WallCenterlineCandidate, ...] = ()
    wall_extraction_policies: tuple[WallExtractionPolicy, ...] = ()
    geometry_only_ufh_preview_readiness: GeometryOnlyUFHPreviewReadiness | None = None
    wall_graph_summaries: tuple[WallGraphSummary, ...] = ()
    collinear_wall_chains: tuple[CollinearWallChain, ...] = ()
    sustained_wall_gaps: tuple[SustainedWallGap, ...] = ()
    opening_room_binding_diagnostics: tuple[OpeningRoomBindingDiagnostic, ...] = ()
    semantic_wall_bands: tuple[SemanticWallBand, ...] = ()
    unpaired_wall_chains: tuple[UnpairedWallChain, ...] = ()
    wall_centerline_policy: WallCenterlinePolicy | None = None
    semantic_wall_junctions: tuple[SemanticWallJunction, ...] = ()
    wall_face_interval_spans: tuple[WallFaceIntervalSpan, ...] = ()
    interval_semantic_wall_bands: tuple[IntervalSemanticWallBand, ...] = ()
    semantic_wall_graphs_v2: tuple[SemanticWallGraphV2, ...] = ()
    single_face_centerline_inferences: tuple[SingleFaceCenterlineInference, ...] = ()
    combined_semantic_wall_edges: tuple[CombinedSemanticWallEdge, ...] = ()
    normalized_semantic_wall_graphs: tuple[NormalizedSemanticWallGraph, ...] = ()
    proven_room_boundary_matches: tuple[ProvenRoomBoundaryMatch, ...] = ()
    boundary_guided_centerline_candidates: tuple[BoundaryGuidedCenterlineCandidate, ...] = ()
    semantic_wall_graph_v4_edges: tuple[CombinedSemanticWallEdge, ...] = ()
    normalized_semantic_wall_graphs_v4: tuple[NormalizedSemanticWallGraph, ...] = ()
    boundary_support_chains: tuple[BoundarySupportChain, ...] = ()
    semantic_wall_graph_v5_edges: tuple[CombinedSemanticWallEdge, ...] = ()
    normalized_semantic_wall_graphs_v5: tuple[NormalizedSemanticWallGraph, ...] = ()
    raster_line_recovery_diagnostics: tuple[RasterLineRecoveryDiagnostic, ...] = ()
    room_geometry_evidence_assessments: tuple[RoomGeometryEvidenceAssessment, ...] = ()


def _source(package, page, document) -> DrawingSource:
    evidence = SourceEvidence(source_id=page.source_id, source_hash=document.sha256,
        reference=document.archived_path, method="verified Test_01 PDF ingestion manifest",
        authority="PROJECT_DOCUMENT_OBSERVATION")
    scale_text = document.title_block.get("scale")
    denominator = __import__("decimal").Decimal(scale_text.split(":", 1)[1]) if isinstance(scale_text, str) and scale_text.startswith("1:") else None
    return DrawingSource(source_id=page.source_id, source_kind="PDF", source_hash=document.sha256,
        page_or_frame=page.page_or_frame, provenance=evidence,
        coordinate_frame=Frame(frame_id=page.source_id+":PAGE_0", space="DRAWING_SPACE",
            unit=page.coordinate_unit, axes="X_RIGHT_Y_DOWN"), project_association=package.project_id,
        floor_hint=document.title_block.get("drawing_title"), known_scale_denominator=denominator)


def replay_test01_drawing_understanding(project_directory: Path, fixture_path: Path = DEFAULT_FIXTURE) -> Test01DrawingUnderstandingResult:
    package = load_test01_pdf_project_source_ingestion(project_directory)
    if package is None:
        raise ValueError("TEST01_VERIFIED_PDF_MANIFEST_REQUIRED")
    review = VisualReviewPackage.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    documents = {item.document_id: item for item in package.documents}
    if {page.source_id for page in review.pages} != set(documents):
        raise ValueError("REVIEW_AND_MANIFEST_SOURCE_SET_MISMATCH")
    artifacts = []
    for page in review.pages:
        document = documents[page.source_id]
        if page.source_hash != document.sha256:
            raise ValueError("REVIEW_SOURCE_HASH_MISMATCH:" + page.source_id)
        source = _source(package, page, document)
        base = ObservationArtifact(source=source, backend_id="FROZEN_REVIEW_IMPORT",
            backend_version=review.schema_version, backend_model=None,
            backend_metadata={"reviewer": review.reviewer, "reviewed_at": review.reviewed_at},
            raw_perception_digest=digest({"fixture": fixture_path.name, "source_hash": document.sha256}),
            observations=()).with_normalization_digest()
        artifact = apply_visual_review(base, review)
        if artifact.integrity_status != "VERIFIED":
            raise ValueError("REVIEWED_OBSERVATION_INTEGRITY_NOT_VERIFIED:" + page.source_id)
        artifacts.append(artifact)
    result = understand(tuple(artifacts))
    room_match = match_room("101DAA3", result.hypotheses, ())
    body = {"source_hashes": {a.source.source_id: a.source.source_hash for a in artifacts},
        "observation_integrity": {a.source.source_id: a.integrity_status for a in artifacts},
        "understanding": result, "room101_match": room_match,
        "engineering_calculations_run": False}
    digest_body = {**body, "understanding": result.model_dump(mode="json"),
        "room101_match": room_match.model_dump(mode="json")}
    return Test01DrawingUnderstandingResult(**body, replay_digest=digest(digest_body))


def reconstruct_test01_room_candidates(project_directory: Path, fixture_path: Path = DEFAULT_FIXTURE) -> Test01DrawingUnderstandingResult:
    """Run local deterministic perception on verified PDFs, then add frozen review.

    Enclosed white regions remain bbox room hypotheses. A reviewed room label is
    bound only when its point is contained by exactly one candidate. Neither
    operation promotes the candidate to a project fact or engineering input.
    """
    package = load_test01_pdf_project_source_ingestion(project_directory)
    if package is None:
        raise ValueError("TEST01_VERIFIED_PDF_MANIFEST_REQUIRED")
    review = VisualReviewPackage.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    documents = {item.document_id: item for item in package.documents}
    artifacts = []
    backend = LocalDrawingPerceptionBackend()
    for page in review.pages:
        document = documents.get(page.source_id)
        if document is None or page.source_hash != document.sha256:
            raise ValueError("REVIEW_SOURCE_HASH_MISMATCH:" + page.source_id)
        source = _source(package, page, document)
        content = (project_directory / document.archived_path).read_bytes()
        artifact = apply_visual_review(backend.perceive(source, content), review)
        if artifact.integrity_status != "VERIFIED":
            raise ValueError("RECONSTRUCTED_OBSERVATION_INTEGRITY_NOT_VERIFIED:" + page.source_id)
        artifacts.append(artifact)
    result = understand(tuple(artifacts))
    rooms = tuple(h for h in result.hypotheses if h.kind == "ROOM")
    bound = sum(h.kind == "ROOM_LABEL" and "containing_room_candidate" in h.attributes
                for h in result.hypotheses)
    room_match = match_room("101DAA3", result.hypotheses, ())
    scale_candidates = tuple(solve_scale_candidate(tuple(c for c in result.dimension_constraints
        if c.evidence.source_id == source_id), assumed_declared_unit="m",
        residual_tolerance_m=__import__("decimal").Decimal("0.03"))
        for source_id in sorted({c.evidence.source_id for c in result.dimension_constraints}))
    adjacency_candidates = infer_adjacency_candidates(result.hypotheses,
        maximum_separation=__import__("decimal").Decimal("12"),
        minimum_shared_projection=__import__("decimal").Decimal("10"))
    annotations = {o.evidence.source_id: o for o in result.text_annotations if o.kind == "SCALE_ANNOTATION"}
    scale_corroborations = tuple(corroborate_scale(candidate, annotations[candidate.frame.frame_id.split(":")[0]],
        relative_tolerance=__import__("decimal").Decimal("0.005")) for candidate in scale_candidates)
    wall_bands = build_wall_band_candidates(adjacency_candidates, scale_candidates,
        tuple(h for h in result.hypotheses if h.kind == "OPENING"))
    geometric_openings = infer_exterior_opening_candidates(tuple(o for a in artifacts for o in a.observations),
        contour_distance_limit=__import__("decimal").Decimal("15"),
        duplicate_overlap_fraction=__import__("decimal").Decimal("0.8"))
    building_rooms = build_building_room_candidates(result.hypotheses, scale_candidates,
        area_tolerance_fraction=__import__("decimal").Decimal("0.05"))
    geometry_assessments = assess_room_geometry_evidence(building_rooms, result.hypotheses)
    repair_assessments = assess_convex_hull_repairs(building_rooms, result.hypotheses, scale_candidates)
    semantic_variants = build_semantic_face_variants(building_rooms, result.hypotheses)
    interior_boundaries, interior_openings, wall_centerlines, wall_policies = [], [], [], []
    for artifact in artifacts:
        document = documents[artifact.source.source_id]
        scale = next(s for s in scale_candidates if s.frame == artifact.source.coordinate_frame)
        gap_m = __import__("decimal").Decimal("0.45")
        gap_drawing = gap_m/scale.scale_m_per_drawing_unit
        policy = WallExtractionPolicy(frame=artifact.source.coordinate_frame,
            raster_pixels_per_drawing_unit=__import__("decimal").Decimal(2),
            minimum_line_length_drawing_units=__import__("decimal").Decimal(20), minimum_opening_gap_width_m_candidate=gap_m,
            minimum_opening_gap_width_drawing_units=gap_drawing,
            gap_width_basis="PHYSICAL_POLICY_USING_UNVERIFIED_DOCUMENT_SCALE",
            suppression_classes=("PDF_TEXT_SPANS", "STAIR_GRAPHICS", "PAGE_OUTSIDE_OUTER_CONTOUR", "SUB_PIXEL_STROKES"),
            rationale="Extraction policy: reject interruptions smaller than a 0.45 m candidate passage; this is a geometric noise filter, not a normative door width or engineering unit confirmation.")
        wall_policies.append(policy)
        content = (project_directory / document.archived_path).read_bytes()
        stair_masks = tuple(h.geometry for h in result.hypotheses if h.kind == "STAIRS" and h.geometry
            and h.geometry.frame == artifact.source.coordinate_frame)
        contour = next((h.geometry for h in result.hypotheses if h.kind == "BUILDING_CONTOUR" and h.geometry
            and h.geometry.frame == artifact.source.coordinate_frame), None)
        wall_centerlines.extend(extract_raster_wall_centerlines(artifact.source, content,
            stair_masks, outer_contour=contour))
        boundaries, openings = analyze_interior_boundary_raster(artifact.source,
            content, result.hypotheses, adjacency_candidates, minimum_gap_width_drawing_units=gap_drawing)
        interior_boundaries.extend(boundaries); interior_openings.extend(openings)
    connectivity = build_room_connectivity(tuple(interior_openings))
    topology = summarize_whole_building_topology(building_rooms, tuple(interior_boundaries), connectivity,
        geometry_assessments)
    routing_readiness = assess_geometry_only_ufh_preview_readiness(building_rooms, topology,
        geometry_assessments)
    wall_graphs = summarize_wall_graph(tuple(wall_centerlines), endpoint_tolerance=__import__("decimal").Decimal("2"))
    chains,gaps=assemble_collinear_wall_chains(tuple(wall_centerlines),result.hypotheses,
        axis_tolerance=__import__("decimal").Decimal("1"),minimum_sustained_gap={
            p.frame.frame_id.split(":")[0]:p.minimum_opening_gap_width_drawing_units
            for p in wall_policies})
    opening_binding_diagnostics=diagnose_opening_room_bindings(gaps)
    centerline_policy=WallCenterlinePolicy(minimum_width_drawing_units=__import__("decimal").Decimal("4"),
        maximum_width_drawing_units=__import__("decimal").Decimal("12"),minimum_overlap_fraction=__import__("decimal").Decimal("0.8"),
        junction_tolerance_drawing_units=__import__("decimal").Decimal("6"),basis="RASTER_RESOLUTION_AND_OBSERVED_WALL_BAND_DISTRIBUTION")
    semantic_bands,unpaired_chains=pair_parallel_wall_faces(chains,policy=centerline_policy)
    semantic_junctions=reconstruct_semantic_wall_junctions(semantic_bands,gaps,
        tolerance=centerline_policy.junction_tolerance_drawing_units)
    interval_spans,interval_bands=pair_wall_faces_by_interval(chains,gaps,policy=centerline_policy)
    semantic_graphs=build_semantic_wall_graph_v2(interval_bands,gaps,
        tolerance=centerline_policy.junction_tolerance_drawing_units)
    single_face_inferences=infer_single_face_centerlines(interval_spans,interval_bands,gaps,
        maximum_prior_distance=centerline_policy.maximum_width_drawing_units)
    combined_edges=build_combined_semantic_edges(interval_bands,single_face_inferences)
    normalized_graphs=normalize_combined_semantic_graph(combined_edges,gaps,tolerance=centerline_policy.junction_tolerance_drawing_units)
    boundary_matches=match_proven_room_boundaries(building_rooms,result.hypotheses,interval_spans,
        distance_tolerance=centerline_policy.junction_tolerance_drawing_units)
    # Recovery is deliberately second-pass: independently proven room edges
    # define only narrow search corridors; raw raster ink must supply the line.
    recovery_diagnostics=[];recovered_walls=[]
    unmatched=tuple(m for m in boundary_matches if m.status=="UNMATCHED_POLYGON_EDGE")
    for artifact in artifacts:
        document=documents[artifact.source.source_id]
        content=(project_directory/document.archived_path).read_bytes()
        stair_masks=tuple(h.geometry for h in result.hypotheses if h.kind=="STAIRS" and h.geometry and h.geometry.frame==artifact.source.coordinate_frame)
        walls,diagnostics=recover_targeted_raster_wall_lines(artifact.source,content,unmatched,gaps,
            suppression_geometries=stair_masks)
        recovered_walls.extend(walls);recovery_diagnostics.extend(diagnostics)
    if recovered_walls:
        wall_centerlines.extend(recovered_walls)
        wall_graphs=summarize_wall_graph(tuple(wall_centerlines),endpoint_tolerance=__import__("decimal").Decimal("2"))
        chains,gaps=assemble_collinear_wall_chains(tuple(wall_centerlines),result.hypotheses,
            axis_tolerance=__import__("decimal").Decimal("1"),minimum_sustained_gap={p.frame.frame_id.split(":")[0]:p.minimum_opening_gap_width_drawing_units for p in wall_policies})
        semantic_bands,unpaired_chains=pair_parallel_wall_faces(chains,policy=centerline_policy)
        semantic_junctions=reconstruct_semantic_wall_junctions(semantic_bands,gaps,tolerance=centerline_policy.junction_tolerance_drawing_units)
        interval_spans,interval_bands=pair_wall_faces_by_interval(chains,gaps,policy=centerline_policy)
        semantic_graphs=build_semantic_wall_graph_v2(interval_bands,gaps,tolerance=centerline_policy.junction_tolerance_drawing_units)
        single_face_inferences=infer_single_face_centerlines(interval_spans,interval_bands,gaps,maximum_prior_distance=centerline_policy.maximum_width_drawing_units)
        combined_edges=build_combined_semantic_edges(interval_bands,single_face_inferences)
        normalized_graphs=normalize_combined_semantic_graph(combined_edges,gaps,tolerance=centerline_policy.junction_tolerance_drawing_units)
        boundary_matches=match_proven_room_boundaries(building_rooms,result.hypotheses,interval_spans,distance_tolerance=centerline_policy.junction_tolerance_drawing_units)
    boundary_candidates=infer_boundary_guided_centerlines(boundary_matches,interval_spans,interval_bands,single_face_inferences,
        boundary_distance_tolerance=centerline_policy.maximum_width_drawing_units)
    v4_edges=add_boundary_guided_edges(combined_edges,boundary_candidates)
    v4_graphs=normalize_combined_semantic_graph(v4_edges,gaps,tolerance=centerline_policy.junction_tolerance_drawing_units)
    support_chains=select_boundary_support_chains(boundary_candidates,gaps,
        continuity_tolerance=centerline_policy.junction_tolerance_drawing_units)
    v5_edges=add_selected_support_chain_edges(combined_edges,support_chains,boundary_candidates)
    v5_graphs=normalize_combined_semantic_graph(v5_edges,gaps,tolerance=centerline_policy.junction_tolerance_drawing_units)
    rooms_path = project_directory / "exports/rooms/rooms.json"
    snapshot_path = project_directory / "exports/model_snapshot.json"
    correspondence_available, correspondence_missing = [], []
    if rooms_path.is_file():
        room_payload = json.loads(rooms_path.read_text(encoding="utf-8"))
        target = next((room for room in room_payload.get("Rooms", []) if room.get("SourceHandle") == "101DAA3"), None)
        if target:
            correspondence_available.extend(("ROOM_TAG_POSITION", "ROOM_REPORTED_AREA"))
    if snapshot_path.is_file():
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        borders = [e for e in snapshot.get("Entities", []) if e.get("Layer") == "MAGIROOMBORDERS"]
        if borders:
            correspondence_available.append("ROOM_BORDER_EXTENTS")
        if not any(e.get("Vertices") for e in borders):
            correspondence_missing.append("ROOM_BORDER_VERTICES")
    correspondence_missing.extend(("TAG_TO_BORDER_IDENTITY_BINDING", "DRAWING_TO_PROJECT_ANCHORS"))
    locality = next((o.value for o in package.observations if o.observation_id == "PROJECT_SITE_LOCATION_TEXT"), None)
    source_discovery = {
        "verified_pdf_documents": tuple(d.archived_path for d in package.documents),
        "project_native_sources": tuple(str(p.relative_to(project_directory)) for p in
            (project_directory/"Test_01.dwg", project_directory/"HomeAura_Test_01.mrd") if p.is_file()),
        "project_exports": tuple(str(p.relative_to(project_directory)) for p in
            (rooms_path, snapshot_path) if p.is_file()),
        "locality_evidence": locality,
        "opening_layers_declared": ("MAGIDOORS", "MAGIWINDOWS"),
        "opening_entities_in_snapshot": 0,
        "construction_properties_status": "SOURCE_MISSING_FROM_REVIEWED_PDFS",
        "geometric_openings_status": "PARTIALLY_EXTRACTED_EXTERIOR_WINDOWS; INTERIOR_DOORS_NOT_YET_EXTRACTED",
        "central_room_faces_status": "ALGORITHM_LIMITATION",
    }
    unit_interpretation = {
        "hypothesis": "DOCUMENT_DIMENSIONS_IN_METRES",
        "status": "CORROBORATED_PROJECT_DOCUMENT_INTERPRETATION_NOT_ENGINEERING_AUTHORITY",
        "scale_annotation_evidence": "verified title block 1:100",
        "dimension_consistency_evidence": "eight dimension observations; two per-floor least-squares fits",
        "room_area_consistency_evidence": "14 of 16 labeled room polygons within 5 percent if labels are square metres",
        "remaining_gap": "no explicit unit glyph or reviewed unit declaration",
    }
    body = {"source_hashes": {a.source.source_id: a.source.source_hash for a in artifacts},
        "observation_integrity": {a.source.source_id: a.integrity_status for a in artifacts},
        "understanding": result, "room101_match": room_match, "engineering_calculations_run": False,
        "perception_mode": "LOCAL_DETERMINISTIC_PLUS_FROZEN_REVIEW",
        "room_candidate_count": len(rooms), "labels_bound_to_room_candidates": bound,
        "scale_candidates": scale_candidates, "adjacency_candidates": adjacency_candidates,
        "scale_corroborations": scale_corroborations,
        "project_correspondence_status": "INSUFFICIENT_GEOMETRY",
        "project_correspondence_available": tuple(correspondence_available),
        "project_correspondence_missing": tuple(correspondence_missing)}
    body["wall_band_candidates"] = wall_bands
    body["building_rooms"] = building_rooms
    body["room_geometry_evidence_assessments"] = geometry_assessments
    body["geometry_repair_assessments"] = repair_assessments
    body["document_unit_interpretation"] = unit_interpretation
    body["source_discovery"] = source_discovery
    body["geometric_openings"] = geometric_openings
    body["semantic_face_variants"] = semantic_variants
    body["interior_boundaries"] = tuple(interior_boundaries)
    body["interior_openings"] = tuple(interior_openings)
    body["room_connectivity"] = connectivity
    body["whole_building_topology"] = topology
    body["wall_centerlines"] = tuple(wall_centerlines)
    body["wall_extraction_policies"] = tuple(wall_policies)
    body["geometry_only_ufh_preview_readiness"] = routing_readiness
    body["wall_graph_summaries"] = wall_graphs
    body["collinear_wall_chains"] = chains
    body["sustained_wall_gaps"] = gaps
    body["opening_room_binding_diagnostics"] = opening_binding_diagnostics
    body["semantic_wall_bands"] = semantic_bands
    body["unpaired_wall_chains"] = unpaired_chains
    body["wall_centerline_policy"] = centerline_policy
    body["semantic_wall_junctions"] = semantic_junctions
    body["wall_face_interval_spans"] = interval_spans
    body["interval_semantic_wall_bands"] = interval_bands
    body["semantic_wall_graphs_v2"] = semantic_graphs
    body["single_face_centerline_inferences"] = single_face_inferences
    body["combined_semantic_wall_edges"] = combined_edges
    body["normalized_semantic_wall_graphs"] = normalized_graphs
    body["proven_room_boundary_matches"] = boundary_matches
    body["boundary_guided_centerline_candidates"] = boundary_candidates
    body["semantic_wall_graph_v4_edges"] = v4_edges
    body["normalized_semantic_wall_graphs_v4"] = v4_graphs
    body["boundary_support_chains"] = support_chains
    body["semantic_wall_graph_v5_edges"] = v5_edges
    body["normalized_semantic_wall_graphs_v5"] = v5_graphs
    body["raster_line_recovery_diagnostics"] = tuple(recovery_diagnostics)
    digest_body = {**body, "understanding": result.model_dump(mode="json"),
        "room101_match": room_match.model_dump(mode="json"),
        "scale_candidates": [s.model_dump(mode="json") for s in scale_candidates],
        "adjacency_candidates": [a.model_dump(mode="json") for a in adjacency_candidates]}
    digest_body["scale_corroborations"] = [c.model_dump(mode="json") for c in scale_corroborations]
    digest_body["wall_band_candidates"] = [w.model_dump(mode="json") for w in wall_bands]
    digest_body["building_rooms"] = [r.model_dump(mode="json") for r in building_rooms]
    digest_body["room_geometry_evidence_assessments"] = [a.model_dump(mode="json") for a in geometry_assessments]
    digest_body["geometry_repair_assessments"] = [a.model_dump(mode="json") for a in repair_assessments]
    digest_body["geometric_openings"] = [o.model_dump(mode="json") for o in geometric_openings]
    digest_body["semantic_face_variants"] = [v.model_dump(mode="json") for v in semantic_variants]
    digest_body["interior_boundaries"] = [v.model_dump(mode="json") for v in interior_boundaries]
    digest_body["interior_openings"] = [v.model_dump(mode="json") for v in interior_openings]
    digest_body["room_connectivity"] = [v.model_dump(mode="json") for v in connectivity]
    digest_body["whole_building_topology"] = topology.model_dump(mode="json")
    digest_body["wall_centerlines"] = [w.model_dump(mode="json") for w in wall_centerlines]
    digest_body["wall_extraction_policies"] = [p.model_dump(mode="json") for p in wall_policies]
    digest_body["geometry_only_ufh_preview_readiness"] = routing_readiness.model_dump(mode="json")
    digest_body["wall_graph_summaries"] = [g.model_dump(mode="json") for g in wall_graphs]
    digest_body["collinear_wall_chains"] = [g.model_dump(mode="json") for g in chains]
    digest_body["sustained_wall_gaps"] = [g.model_dump(mode="json") for g in gaps]
    digest_body["opening_room_binding_diagnostics"] = [g.model_dump(mode="json") for g in opening_binding_diagnostics]
    digest_body["semantic_wall_bands"] = [g.model_dump(mode="json") for g in semantic_bands]
    digest_body["unpaired_wall_chains"] = [g.model_dump(mode="json") for g in unpaired_chains]
    digest_body["wall_centerline_policy"] = centerline_policy.model_dump(mode="json")
    digest_body["semantic_wall_junctions"] = [j.model_dump(mode="json") for j in semantic_junctions]
    digest_body["wall_face_interval_spans"] = [j.model_dump(mode="json") for j in interval_spans]
    digest_body["interval_semantic_wall_bands"] = [j.model_dump(mode="json") for j in interval_bands]
    digest_body["semantic_wall_graphs_v2"] = [j.model_dump(mode="json") for j in semantic_graphs]
    digest_body["single_face_centerline_inferences"] = [j.model_dump(mode="json") for j in single_face_inferences]
    digest_body["combined_semantic_wall_edges"] = [j.model_dump(mode="json") for j in combined_edges]
    digest_body["normalized_semantic_wall_graphs"] = [j.model_dump(mode="json") for j in normalized_graphs]
    digest_body["proven_room_boundary_matches"] = [j.model_dump(mode="json") for j in boundary_matches]
    digest_body["boundary_guided_centerline_candidates"] = [j.model_dump(mode="json") for j in boundary_candidates]
    digest_body["semantic_wall_graph_v4_edges"] = [j.model_dump(mode="json") for j in v4_edges]
    digest_body["normalized_semantic_wall_graphs_v4"] = [j.model_dump(mode="json") for j in v4_graphs]
    digest_body["boundary_support_chains"] = [j.model_dump(mode="json") for j in support_chains]
    digest_body["semantic_wall_graph_v5_edges"] = [j.model_dump(mode="json") for j in v5_edges]
    digest_body["normalized_semantic_wall_graphs_v5"] = [j.model_dump(mode="json") for j in v5_graphs]
    digest_body["raster_line_recovery_diagnostics"] = [j.model_dump(mode="json") for j in recovery_diagnostics]
    return Test01DrawingUnderstandingResult(**body, replay_digest=digest(digest_body))


__all__ = ["Test01DrawingUnderstandingResult", "replay_test01_drawing_understanding",
           "reconstruct_test01_room_candidates"]

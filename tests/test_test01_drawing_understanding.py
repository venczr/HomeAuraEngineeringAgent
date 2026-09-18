from pathlib import Path
from unittest.mock import patch

from agent.test01_drawing_understanding import (replay_test01_drawing_understanding,
    reconstruct_test01_room_candidates)


PROJECT = Path(__file__).resolve().parents[1] / "projects/Test_01"


def test_test01_replay_is_frozen_deterministic_and_never_invokes_perception():
    with patch("agent.drawing_perception.LocalDrawingPerceptionBackend.perceive", side_effect=AssertionError("perception invoked")):
        first = replay_test01_drawing_understanding(PROJECT)
        second = replay_test01_drawing_understanding(PROJECT)
    assert first.replay_digest == second.replay_digest
    assert set(first.observation_integrity.values()) == {"VERIFIED"}
    assert first.engineering_calculations_run is False


def test_both_test01_floors_and_reviewed_observations_remain_distinct():
    replay = replay_test01_drawing_understanding(PROJECT)
    documents = {d.source.source_id: d for d in replay.understanding.documents}
    assert set(documents) == {"FLOOR_1_PLAN", "ATTIC_PLAN"}
    labels = [o for o in replay.understanding.text_annotations if o.kind == "ROOM_LABEL"]
    contours = [h for h in replay.understanding.hypotheses if h.kind == "BUILDING_CONTOUR"]
    stairs = [h for h in replay.understanding.hypotheses if h.kind == "STAIRS"]
    dimensions = replay.understanding.dimension_constraints
    assert len(labels) == 16 and len(contours) == 2 and len(stairs) == 2 and len(dimensions) == 8
    assert {o.evidence.source_id for o in labels} == {"FLOOR_1_PLAN", "ATTIC_PLAN"}
    assert replay.understanding.cross_floor_alignments[0].status == "ANCHOR_CORRESPONDENCE_REQUIRED"


def test_room101_matching_remains_fail_closed():
    result = replay_test01_drawing_understanding(PROJECT)
    assert result.room101_match.status in {"NO_MATCH", "AMBIGUOUS"}
    assert "FLOOR_IDENTITY" in result.room101_match.missing_evidence
    assert result.room101_match.reasons == ("NO_ROOM_GEOMETRY_CANDIDATES",)
    assert result.understanding.confirmed_project_facts == ()


def test_verified_pdfs_reconstruct_room_candidates_and_bind_all_reviewed_labels():
    result = reconstruct_test01_room_candidates(PROJECT)
    assert result.perception_mode == "LOCAL_DETERMINISTIC_PLUS_FROZEN_REVIEW"
    assert result.room_candidate_count == 18
    assert result.labels_bound_to_room_candidates == 16
    assert result.understanding.confirmed_project_facts == ()
    assert result.engineering_calculations_run is False
    assert len(result.wall_graph_summaries) == 2
    assert sum(g.source_segment_count for g in result.wall_graph_summaries) == len(result.wall_centerlines)
    assert all(g.intersection_node_count > 0 for g in result.wall_graph_summaries)
    assert result.collinear_wall_chains
    assert result.sustained_wall_gaps
    assert any(g.classification == "WINDOW_CANDIDATE" for g in result.sustained_wall_gaps)
    assert any(g.classification == "OPEN_PASSAGE_CANDIDATE" for g in result.sustained_wall_gaps)
    assert len(result.opening_room_binding_diagnostics) == len(result.sustained_wall_gaps) == 14
    assert {d.status for d in result.opening_room_binding_diagnostics} == {
        "ROOM_PAIR_BOUNDARY_BINDING_REQUIRED", "INSUFFICIENT_ROOM_ASSOCIATION",
        "AMBIGUOUS_ROOM_ASSOCIATION", "EXTERIOR_OPENING_NOT_INTERIOR_CONNECTIVITY"}
    assert sum(d.status == "ROOM_PAIR_BOUNDARY_BINDING_REQUIRED"
        for d in result.opening_room_binding_diagnostics) == 1
    assert all(g.width_drawing_units >= next(p.minimum_opening_gap_width_drawing_units
        for p in result.wall_extraction_policies if p.frame == g.frame) for g in result.sustained_wall_gaps)
    assert result.semantic_wall_bands
    assert result.unpaired_wall_chains
    assert all(b.status == "PAIRED_PARALLEL_FACES_NOT_PROJECT_FACT" for b in result.semantic_wall_bands)
    assert all(result.wall_centerline_policy.minimum_width_drawing_units <= b.width_drawing_units <=
        result.wall_centerline_policy.maximum_width_drawing_units for b in result.semantic_wall_bands)
    assert result.semantic_wall_junctions
    assert all(j.gap_preservation_status == "NO_SUSTAINED_GAP_DESTROYED" for j in result.semantic_wall_junctions)
    assert result.wall_face_interval_spans
    assert result.interval_semantic_wall_bands
    classifications = {s.classification for s in result.wall_face_interval_spans}
    assert {"PAIRED_WALL_FACE", "UNPAIRED_WALL_FACE", "OPENING_ADJACENT_SPAN"} <= classifications
    assert len(result.combined_semantic_wall_edges) >= 55
    assert sum(e.evidence_class == "PROVEN_CENTERLINE" for e in result.combined_semantic_wall_edges) >= 35
    assert sum(e.evidence_class == "SUPPORTED_INFERRED_CENTERLINE" for e in result.combined_semantic_wall_edges) >= 20
    assert len(result.normalized_semantic_wall_graphs) == 2
    assert all("RESIDUAL_FACE_ARTIFACT_EXCLUDED" in g.diagnostics for g in result.normalized_semantic_wall_graphs)
    assert all(len(g.protected_gap_ids) > 0 for g in result.normalized_semantic_wall_graphs)
    assert len(result.proven_room_boundary_matches) == 70
    assert sum(m.status == "MATCHED_RASTER_FACE" for m in result.proven_room_boundary_matches) == 66
    assert len(result.raster_line_recovery_diagnostics) == 6
    assert all(d.final_status == "RECOVERED_RASTER_WALL_CANDIDATE"
        for d in result.raster_line_recovery_diagnostics)
    assert all(not d.protected_gap_conflict for d in result.raster_line_recovery_diagnostics)
    assert all(d.raw_ink_continuity >= __import__("decimal").Decimal("0.92")
        for d in result.raster_line_recovery_diagnostics)
    assert len(result.room_geometry_evidence_assessments) == 16
    exclusion_overlaps = [a for a in result.room_geometry_evidence_assessments
        if a.exclusion_region_overlap]
    assert len(exclusion_overlaps) == 2
    assert all(a.geometry_status == "AMBIGUOUS" and
        "STAIR_EXCLUSION_REGION_OVERLAP" in a.diagnostics for a in exclusion_overlaps)
    assert all(a.geometry_status == "USABLE_DRAWING_HYPOTHESIS"
        for a in result.room_geometry_evidence_assessments if not a.exclusion_region_overlap)
    area_mismatch = [a for a in result.room_geometry_evidence_assessments
        if a.area_validation_status == "GEOMETRY_REVIEW_REQUIRED"]
    assert len(area_mismatch) == 2
    assert {a.room_hypothesis_id for a in area_mismatch} == {
        a.room_hypothesis_id for a in exclusion_overlaps}
    assert all("DECLARED_AREA_MISMATCH_RETAINED_AS_POST_SELECTION_QA" in a.diagnostics
        for a in area_mismatch)
    assert all(c.supporting_room_hypothesis_id not in {
        room.room_hypothesis_id for room in result.building_rooms if room.area_status == "GEOMETRY_REVIEW_REQUIRED"}
        for c in result.boundary_guided_centerline_candidates)
    assert any(c.topology_edge_eligible for c in result.boundary_guided_centerline_candidates)
    assert len(result.normalized_semantic_wall_graphs_v4) == 2
    assert result.boundary_support_chains
    assert any(c.outcome == "CHAIN_SELECTED" for c in result.boundary_support_chains)
    assert all(c.room_hypothesis_id not in {room.room_hypothesis_id for room in result.building_rooms
        if room.area_status == "GEOMETRY_REVIEW_REQUIRED"} for c in result.boundary_support_chains)
    assert len(result.normalized_semantic_wall_graphs_v5) == 2
    labels = [h for h in result.understanding.hypotheses if h.kind == "ROOM_LABEL"]
    assert all("containing_room_candidate" in h.attributes for h in labels)
    by_id = {h.hypothesis_id: h for h in result.understanding.hypotheses}
    assert all(by_id[h.attributes["containing_room_candidate"]].geometry.frame == h.geometry.frame for h in labels)
    unlabeled = [u for u in result.understanding.unresolved_items
        if u.unresolved_type == "ROOM_CANDIDATE_WITHOUT_UNIQUE_LABEL"]
    assert len(unlabeled) == 2 and all(u.blocking for u in unlabeled)
    assert len(result.scale_candidates) == 2
    assert all(s.status == "UNIT_CONFIRMATION_REQUIRED" for s in result.scale_candidates)
    assert all(s.maximum_absolute_residual_m < __import__("decimal").Decimal("0.03") for s in result.scale_candidates)
    assert len(result.scale_corroborations) == 2
    assert all(c.agrees and c.status == "CORROBORATED_UNIT_UNRESOLVED" for c in result.scale_corroborations)
    assert all(c.annotation_denominator == 100 for c in result.scale_corroborations)
    assert result.adjacency_candidates
    assert all(a.status == "BOUNDARY_OR_OPENING_EVIDENCE_REQUIRED" for a in result.adjacency_candidates)
    assert all(a.left_hypothesis_id.split(":")[0] == a.right_hypothesis_id.split(":")[0]
        for a in result.adjacency_candidates)
    alignment = result.understanding.cross_floor_alignments[0]
    assert alignment.single_anchor_translation_candidate is not None
    assert alignment.anchor_pair is not None
    assert alignment.transform is None and alignment.status == "ANCHOR_CORRESPONDENCE_REQUIRED"
    assert alignment.multi_anchor_status == "APPROXIMATE_CONTOUR_CORRESPONDENCE"
    assert alignment.multi_anchor_coefficients_candidate is not None
    assert alignment.multi_anchor_maximum_residual_drawing_units is not None
    assert alignment.multi_anchor_maximum_residual_drawing_units < 2
    assert result.project_correspondence_status == "INSUFFICIENT_GEOMETRY"
    assert "ROOM_TAG_POSITION" in result.project_correspondence_available
    assert "ROOM_BORDER_VERTICES" in result.project_correspondence_missing
    assert "TAG_TO_BORDER_IDENTITY_BINDING" in result.project_correspondence_missing
    assert len(result.wall_band_candidates) == len(result.adjacency_candidates)
    assert all(w.scale_status == "PHYSICAL_SCALE_UNVERIFIED" for w in result.wall_band_candidates)
    assert all(w.opening_status == "NO_OPENING_EVIDENCE" for w in result.wall_band_candidates)
    assert all(w.status == "WALL_CLASS_AND_EXACT_FACES_UNRESOLVED" for w in result.wall_band_candidates)
    assert len(result.building_rooms) == 16
    assert sum(r.area_status == "GEOMETRY_REVIEW_REQUIRED" for r in result.building_rooms) == 2
    assert all(r.engineering_authority == "NOT_AUTHORIZED" for r in result.building_rooms)
    assert len(result.geometry_repair_assessments) == 2
    assert all(a.status == "REJECTED_INSUFFICIENT_EVIDENCE" for a in result.geometry_repair_assessments)
    assert result.document_unit_interpretation["hypothesis"] == "DOCUMENT_DIMENSIONS_IN_METRES"
    assert "Узигонты" in result.source_discovery["locality_evidence"]
    assert result.source_discovery["central_room_faces_status"] == "ALGORITHM_LIMITATION"
    assert "PARTIALLY_EXTRACTED_EXTERIOR_WINDOWS" in result.source_discovery["geometric_openings_status"]
    assert result.geometric_openings
    assert any(o.type_candidate == "WINDOW_OR_GLAZING" for o in result.geometric_openings)
    assert all(o.status == "GEOMETRIC_CANDIDATE_NOT_THERMAL_AUTHORITY" for o in result.geometric_openings)
    assert len(result.semantic_face_variants) >= 5
    assert {v.room_hypothesis_id for v in result.semantic_face_variants} == {
        r.room_hypothesis_id for r in result.building_rooms if r.area_status == "GEOMETRY_REVIEW_REQUIRED"}
    assert not any(v.status == "CANDIDATE" and v.variant_type == "OBSERVED_CONNECTED_FACE"
        for v in result.semantic_face_variants)
    assert len(result.interior_boundaries) == len(result.adjacency_candidates)
    # Short interruptions at dimension text are retained as diagnostics, not
    # silently promoted into door/connectivity evidence.
    assert any(b.classification == "WALL_WITH_SHORT_INTERRUPTION" for b in result.interior_boundaries)
    assert not result.interior_openings
    assert len(result.room_connectivity) == len(result.interior_openings)
    assert all(edge.engineering_authority == "NOT_AUTHORIZED" for edge in result.room_connectivity)
    assert all(edge.opening_id in {o.opening_id for o in result.interior_openings}
        for edge in result.room_connectivity)
    assert result.whole_building_topology.labeled_room_count == 16
    assert result.whole_building_topology.interior_boundary_count == 20
    assert result.whole_building_topology.topology_status == "PARTIAL_BOUNDARIES_CONNECTIVITY_UNRESOLVED"
    assert len(result.whole_building_topology.unresolved_semantic_room_ids) == 2
    assert "INTERIOR_OPENING_SYMBOL_OR_GAP_EVIDENCE_NOT_EXTRACTED" in result.whole_building_topology.blockers
    assert result.wall_centerlines
    assert {w.orientation for w in result.wall_centerlines} == {"HORIZONTAL", "VERTICAL"}
    assert all(w.status == "RASTER_WALL_CANDIDATE_NOT_PROJECT_FACT" for w in result.wall_centerlines)
    assert len(result.wall_extraction_policies) == 2
    assert all(p.minimum_opening_gap_width_m_candidate == __import__("decimal").Decimal("0.45")
        for p in result.wall_extraction_policies)
    assert all(p.gap_width_basis == "PHYSICAL_POLICY_USING_UNVERIFIED_DOCUMENT_SCALE"
        for p in result.wall_extraction_policies)
    assert result.geometry_only_ufh_preview_readiness.status == "BLOCKED_GEOMETRY_INCOMPLETE"
    assert result.geometry_only_ufh_preview_readiness.usable_room_count == 14
    assert result.geometry_only_ufh_preview_readiness.routing_engine_invoked is False
    assert result.engineering_calculations_run is False


def test_room_candidate_reconstruction_is_deterministic_and_room101_stays_ambiguous():
    first = reconstruct_test01_room_candidates(PROJECT)
    second = reconstruct_test01_room_candidates(PROJECT)
    assert first.replay_digest == second.replay_digest
    assert first.room101_match.status == "AMBIGUOUS"
    assert "FLOOR_IDENTITY" in first.room101_match.missing_evidence

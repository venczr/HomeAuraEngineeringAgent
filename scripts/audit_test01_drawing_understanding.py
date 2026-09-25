"""Read-only real fixture runner; all parsing/reasoning lives in generic modules.

Usage: python -m scripts.audit_test01_drawing_understanding --project ...
    --ifc-directory ... --review ... --output reports/drawing_understanding_v1
Outputs contain project document observations. No engineering calculation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from agent.drawing_understanding import (
    DrawingSource, Frame, Geometry, Point, SourceEvidence, compare_room_shape, digest, match_room, understand,
)
from agent.drawing_perception import LocalDrawingPerceptionBackend
from agent.drawing_observation_review import VisualReviewPackage, apply_visual_review
from agent.test01_pdf_project_source_ingestion import load_test01_pdf_project_source_ingestion
from agent.test01_geometry_source_authority import assess_test01_geometry_authority


def tree_hashes(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob("*")) if p.is_file()}


def run_fixture(project: Path, ifc_directory: Path, review: VisualReviewPackage | None = None):
    before = tree_hashes(project)
    ifc_before = tree_hashes(ifc_directory)
    package = load_test01_pdf_project_source_ingestion(project)
    if package is None:
        raise ValueError("VERIFIED_PDF_SOURCE_BINDING_REQUIRED")
    artifacts = []
    for document in package.documents:
        scale = document.title_block.get("scale")
        denominator = Decimal(scale.split(":")[1]) if isinstance(scale, str) and scale.startswith("1:") else None
        source = DrawingSource(source_id=document.document_id, source_kind="PDF", source_hash=document.sha256,
            page_or_frame=0, provenance=SourceEvidence(source_id=document.document_id, source_hash=document.sha256,
                reference=document.archived_path+"; ingestion manifest "+package.manifest_digest,
                method="Existing verified PDF archive binding and visually reviewed title block",
                authority="PROJECT_DOCUMENT_OBSERVATION"),
            coordinate_frame=Frame(frame_id=document.document_id+":page0", space="DRAWING_SPACE", unit="pt", axes="X_RIGHT_Y_DOWN"),
            project_association=package.project_id, floor_hint=document.title_block.get("sheet_title"),
            known_scale_denominator=denominator)
        artifact = LocalDrawingPerceptionBackend().perceive(source, (project/document.archived_path).read_bytes())
        if review:
            artifact = apply_visual_review(artifact, review)
        # Reuse, with original extraction provenance, the existing site annotation.
        from agent.drawing_understanding import Observation
        from agent.drawing_perception import merge_reviewed_observations
        site = document.title_block.get("project_site_location_text")
        if site:
            artifact = merge_reviewed_observations(artifact, (Observation(
                observation_id=source.source_id+":existing-site-observation", kind="PROJECT_ANNOTATION",
                evidence=source.provenance, text=site, quality="MEDIUM",
                limitation="Document annotation; no canonical climate location or project-authority binding"),))
        artifacts.append(artifact)
    result = understand(tuple(artifacts))
    authority = assess_test01_geometry_authority(project, ifc_directory)
    comparisons = []
    reference_shape = None
    if authority.status == "AUTHORITATIVE" and authority.ufh_source:
        boundary = authority.ufh_source.authoritative_boundary
        reference_shape = Geometry(frame=Frame(frame_id="accepted-ifc-project", space="PROJECT_SPACE", unit="m", axes="X_RIGHT_Y_UP"),
            kind="POLYGON", points=tuple(Point(x=Decimal(str(v.X)), y=Decimal(str(v.Y))) for v in boundary.Vertices))
        ref_source = SourceEvidence(source_id="accepted-ifc", source_hash=authority.evidence["hashes"]["ifc"],
            reference=authority.evidence["source_paths"]["ifc"], method="Existing authoritative geometry adapter",
            authority="PROJECT_GEOMETRY_REFERENCE")
        comparisons = [compare_room_shape(package.target_room_id, reference_shape, ref_source, h,
                        aspect_ratio_tolerance=Decimal("0.05")) for h in result.hypotheses if h.kind == "ROOM"]
    match = match_room(package.target_room_id, result.hypotheses, tuple(comparisons))
    after, ifc_after = tree_hashes(project), tree_hashes(ifc_directory)
    if before != after or ifc_before != ifc_after:
        raise ValueError("PROTECTED_SOURCE_TREE_CHANGED")
    summary = {
        "verdict": "DRAWING_UNDERSTANDING_ENGINE_V1_READY",
        "scope": "Local CV region/symbol candidates plus separately attributed frozen visual review; no engineering binding",
        "source_hashes": {a.source.source_id: a.source.source_hash for a in artifacts},
        "automatic_perception_backend": LocalDrawingPerceptionBackend.backend_id,
        "reviewed_observation_fixture_used": review is not None,
        "per_page": {a.source.source_id: {"floor": a.source.floor_hint,
            "observation_counts": dict(Counter(o.kind for o in a.observations)),
            "hypothesis_counts": dict(Counter(h.kind for h in result.hypotheses if a.source.source_id in h.source_dependencies)),
            "artifact_digest": a.artifact_digest} for a in artifacts},
        "result_digest": result.result_digest,
        "room_match": match.model_dump(mode="json"),
        "room_reference_geometry_status": authority.status,
        "room_reference_shape": reference_shape.model_dump(mode="json") if reference_shape else None,
        "room_reference_net_area_m2": authority.evidence.get("net_area_m2"),
        "room_reference_contour_area_m2": authority.evidence.get("ifc_area_m2"),
        "shape_comparisons": [e.model_dump(mode="json") for e in comparisons],
        "confirmed_project_fact_count": len(result.confirmed_project_facts),
        "engineering_bindings": [], "engineering_calculations_executed": [],
        "project_source_tree_unchanged": before == after,
        "ifc_source_tree_unchanged": ifc_before == ifc_after,
        "project_tree_digest": digest(before), "ifc_tree_digest": digest(ifc_before),
        "unresolved": result.unresolved,
    }
    return tuple(artifacts), result, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--ifc-directory", type=Path, required=True)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    for protected in (args.project.resolve(), args.ifc_directory.resolve()):
        if output == protected or protected in output.parents:
            raise ValueError("AUDIT_OUTPUT_MUST_BE_OUTSIDE_PROTECTED_SOURCE_TREES")
    review = VisualReviewPackage.model_validate_json(args.review.read_text(encoding="utf-8")) if args.review else None
    artifacts, result, summary = run_fixture(args.project, args.ifc_directory, review)
    output.mkdir(parents=True, exist_ok=True)
    for artifact in artifacts:
        (output/(artifact.source.source_id+".observations.json")).write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    (output/"understanding.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    (output/"audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("per_page", "result_digest", "room_reference_geometry_status",
        "confirmed_project_fact_count", "project_source_tree_unchanged", "ifc_source_tree_unchanged")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

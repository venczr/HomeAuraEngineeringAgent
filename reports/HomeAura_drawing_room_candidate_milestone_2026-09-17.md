# Drawing understanding room-candidate milestone — 2026-09-17

## Outcome
A real verified Test_01 PDF can now flow through local deterministic perception, normalized observations, frozen reviewed labels, drawing-space room candidates, and unique label containment. This path creates hypotheses only; it creates no confirmed project facts or engineering inputs.

## Measured Test_01 result
- 2 manifest-verified PDFs, hashes checked before perception.
- 18 enclosed-region room candidates across two distinct PDF page frames.
- 16/16 reviewed room labels uniquely bound to a candidate in the same frame.
- 2 unlabeled candidates retained as typed blocking unresolved items.
- 8 dimension constraints, 2 reviewed outer contours, and 2 stair candidates preserved.
- Room 101 / 101DAA3: AMBIGUOUS. Drawing candidates now exist, but no cross-source transform, floor identity, relative position, topology, adjacency, DWG/IFC geometry correspondence, or model-snapshot anchor establishes identity.
- No confirmed project facts and no engineering calculations.

## Architecture decision
The PDFs contain roughly 10,000 tiny filled glyph/path drawings each and no useful long wall-line paths. Direct wall graph reconstruction from their raw vector path stream is therefore not supported by the actual source structure. Deterministic raster connected-region extraction is currently the evidence-producing path; its bbox geometry remains explicitly approximate.

## Validation
- Drawing + replay + PDF ingestion targeted suite: 15 passed.
- Drawing + replay + PDF ingestion + intake + room artifact suite: 37 passed.
- Related project/domain regression suite passed with the two known dirty-baseline route-contract assertions excluded.
- Python compile and UTF-8 reads passed.

## Next direction
Upgrade bbox candidates to traced interior polygons with explicit raster-to-PDF-point transform and boundary quality diagnostics; then associate dimension constraints and derive scale candidates before any project-space reconciliation.

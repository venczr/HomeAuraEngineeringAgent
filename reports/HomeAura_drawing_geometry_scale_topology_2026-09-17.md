# Drawing geometry, scale and topology milestone — 2026-09-17

## End-to-end result
Verified Test_01 PDFs now produce deterministic traced drawing-space polygons, room-label bindings, scale candidates, same-floor adjacency candidates, and a single-stair cross-floor translation candidate. All outputs remain hypotheses or unresolved candidates; no project fact or engineering authority is created.

## Geometry
- 18 connected-space outer polygons replace bbox room geometry.
- 16/16 reviewed labels bind uniquely by polygon point containment.
- Polygon provenance includes raster px to PDF pt scale (0.5 pt/px), closure, gap count, vertex count, contour/bbox area ratio, and a 0.25 pt simplification-error bound.
- Maximum observed polygon complexity: 139 vertices.
- Two unlabeled candidates remain typed blocking unresolved items.

## Scale
- Least-squares scale candidates from 4 dimension constraints per floor:
  - Attic: 0.0351922643 assumed m/pt; max residual 0.01385 m.
  - Floor 1: 0.0352769631 assumed m/pt; max residual 0.00225 m.
- Frozen dimensions omit units, so both remain UNIT_CONFIRMATION_REQUIRED and cannot create physical authority.

## Topology and openings
- 20 deterministic same-floor adjacency candidates from near, non-overlapping polygon envelopes.
- Every candidate remains BOUNDARY_OR_OPENING_EVIDENCE_REQUIRED.
- Existing parallel-strip observations continue to generate unknown-opening hypotheses; no door/window class or connectivity is promoted.

## Cross-floor and project transform
- One reviewed stair candidate per floor yields a single-anchor translation candidate.
- A second non-collinear correspondence is required; affine alignment and project transform remain unresolved.
- Room101 / 101DAA3 remains AMBIGUOUS because no DWG/IFC/model-snapshot correspondence binds any drawing room identity.

## Validation
- Drawing/PDF/intake/room targeted suite: 39 passed.
- Related project/domain suite excluding two documented dirty-baseline route assertions: 166 passed.
- Python compile, UTF-8 reread and scoped diff checks passed.

## Next direction
Extract wall bands and opening gaps around traced spaces, convert adjacency candidates into boundary relationships with evidence, then seek a second cross-floor anchor and DWG/IFC correspondence. Physical areas may be computed as candidates only after dimension units are independently established.

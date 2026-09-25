# Whole-building drawing model milestone — 2026-09-17

## Verdict
The Test_01 two-floor pipeline now creates a deterministic whole-building candidate model from both verified PDFs. Room 101 / 101DAA3 is optional regression evidence only and is not a readiness blocker.

## Scale evidence
The verified ingestion manifest independently records title-block scale 1:100 for both PDFs. This yields 0.035277777777... m/pt from paper-point conversion. Separate least-squares dimension fits yield 0.0352769631 on floor 1 and 0.0351922643 on the attic. Both corroborate the annotation within policy tolerance. Dimension labels still have no independently proven unit, so status remains CORROBORATED_UNIT_UNRESOLVED / UNIT_CONFIRMATION_REQUIRED.

## Whole-building model
- 2 distinct floors.
- 16 labeled room candidates with traced drawing-space polygons.
- 14 area candidates agree with label numbers within 5% if labels are m2.
- 2 candidates are GEOMETRY_REVIEW_REQUIRED due to large area residuals; values are not fabricated or fitted.
- 20 same-floor adjacency and wall-band candidates.
- Repeated candidate wall bands are approximately 6.5 pt and 9.5 pt; physical thickness candidates remain unverified.
- No adjacency is promoted to connected-by-opening.
- All building rooms remain NOT_AUTHORIZED for engineering use.

## Cross-floor
The reviewed eight-vertex outer contours provide a multi-anchor axis-aligned transform candidate with sub-2-point maximum residual. Stair centers provide an independent single-anchor translation candidate. Because contours are approximate reviewed observations, the alignment remains a candidate rather than a confirmed transform.

## Project correspondence
The Test_01 room export contains tag position and reported area. The model snapshot contains room-border extents but no vertices and no tag-to-border identity binding. This is insufficient for polygon correspondence. 101DAA3 remains an optional AMBIGUOUS regression result and does not block the whole-building PDF pipeline.

## Validation
- Drawing/PDF/intake/room suite: 39 passed.
- Related project/domain suite excluding two documented dirty-baseline route assertions: 166 passed.
- No new regressions.

## Continuation boundary
Repair the two area-outlier polygons using deterministic region merging / boundary tracing constrained by their reviewed label positions and outer contour. Then associate opening gaps with wall bands, prove room connectivity, and promote physical geometry only after dimension-unit evidence is independently established.

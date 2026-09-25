# Observed face containment QA ? 2026-09-17

## Result
Observed-face qualification now detects boundary crossings between polygons and treats overlaps with explicit stair evidence as unresolved exclusion regions. Test_01 rooms 2 and 9 overlap reviewed stair bounding boxes, so their faces are AMBIGUOUS and geometry-only routing skips them. No void is inferred or silently subtracted.

## Validation
- 15 targeted drawing-understanding and geometry-preview tests passed.
- The remaining 14 observed faces still generate geometry-only preview routes.
- Engineering authority remains NOT_AUTHORIZED / NOT_FOR_CONSTRUCTION.

## Next bounded block
P3 should bind whole-building unresolved-room accounting to the observed geometry-evidence assessments, while preserving the current zero-connectivity result until sustained opening evidence is extracted.

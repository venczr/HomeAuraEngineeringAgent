# Semantic wall centerlines ? 2026-09-17

## Result
The 61 collinear chains now produce 19 uniquely paired semantic wall bands (11 floor 1, 8 attic), with inferred centerline, width, overlap, source chain IDs and source hashes. Twenty-three chains remain explicitly unpaired with NO_UNIQUE_PARALLEL_FACE_WITHIN_POLICY.

The explicit policy accepts 4?12 drawing-point band widths, at least 0.8 overlap, and 6 drawing-point junction tolerance. The tolerance is bounded by 2x raster resolution and observed wall-band thickness distribution. Three gap-preserving cross-junction candidates were reconstructed. Sustained opening gaps are protected from closure.

## Planar subdivision
Before: floor 1 = 3 faces, attic = 8. A diagnostic centerline-only polygonization gives floor 1 = 6 and attic = 3, but remains incomplete because greedy whole-chain pairing truncates partially overlapping wall faces. This diagnostic is not promoted. Interval-wise chain splitting is required before subdivision V2.

Rooms 2 and 9 remain AMBIGUOUS and skipped. Routing remains 14/16 successful; existing preview artifacts are unchanged.

## Tests
28 targeted drawing, routing, coverage and room-geometry tests passed. Compile and whitespace checks passed.

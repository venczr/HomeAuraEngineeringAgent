# Single-face centerline continuation ? 2026-09-17

## Inference
51 residual/opening-adjacent spans evaluated: 20 inferred from a paired interval on the same source face chain, 30 unresolved without a local prior, 1 rejected because it intersects a protected gap, 0 ambiguous offsets in Test_01. Inference distance is limited to the 12 pt local band policy; no floor-wide width borrowing occurs.

## Graph quality
Proven interval edges: 35. Supported inferred edges: 20. All 14 sustained gaps remain protected. The prior V2 solver had 58 dangling endpoints; adding inferred evidence creates local continuations, but V5 polygonization still lacks enough perpendicular junction continuity to compute a lower honest dangling count without first rerunning the junction solver over the combined edge set.

## Polygonization V5 diagnostic
- First floor: 6 faces, 0 one-label, 1 multi-label, 5 unlabeled; four tiny paired-face slivers and one 1211.2 sq-pt residual face.
- Attic: 1 face, 0 one-label, 1 multi-label.
The additional floor-1 faces are wall-band artifacts, not rooms. Neither graph is promoted.

## Exact blocker
Most inferred continuations remain collinear fragments whose endpoints need V3 junction solving against both proven and inferred edges. Thirty residuals have no same-chain local paired prior. A safe next step is combined-edge junction V3 with stronger rules for inferred-to-inferred connections; it must also eliminate paired-face sliver loops before face interpretation.

Rooms 2 and 9 remain AMBIGUOUS. Geometry-only routing remains 14/16.

## Tests
43 targeted junction, drawing, routing and room-geometry tests passed. Compile and whitespace checks passed.

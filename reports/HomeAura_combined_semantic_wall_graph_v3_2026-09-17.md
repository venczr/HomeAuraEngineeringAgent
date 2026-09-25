# Combined semantic wall graph V3 ? 2026-09-17

## Combined edges
55 topology edges: 35 PROVEN_CENTERLINE and 20 SUPPORTED_INFERRED_CENTERLINE. Residual wall faces remain evidence only. Every edge retains evidence class, source spans, source hash dependencies and dependency digest.

## Junction V3
- First floor: 12 confirmed T, 48 no-supported, 2 rejected opening conflicts; dangling proven=31, inferred=19.
- Attic: 5 confirmed T, 21 no-supported, 22 rejected opening conflicts; dangling proven=27, inferred=16.
- Total confirmed T=17; L=0; cross=0; ambiguous=0.
The prior V2 dangling count was 58 proven endpoints. In V3, proven remains 58 and inferred adds 35 dangling endpoints. This is not an improvement, but it is exact and shows inferred collinear continuity alone does not supply missing perpendicular closures.

## Normalization
Zero-length and duplicate reverse edges are removed. Residual face artifacts are excluded. Source wall-band faces remain preserved outside topology. All 14 sustained gaps remain constraints; no protected gap is closed.

## Polygonization V6
- First floor: 6 faces; 0 one-label; 1 multi-label; 5 unlabeled; 4 tiny wall-band slivers; 0 stair faces.
- Attic: 1 face; 0 one-label; 1 multi-label; 0 unlabeled/sliver/stair faces.
Rooms 2 and 9 remain AMBIGUOUS; routing remains 14/16.

## Exact blocker
The drawing visibly contains room boundaries, but the raster extractor represents many as single isolated faces whose chains have no local paired prior and no perpendicular semantic target within policy. This is ALGORITHM_MISSED_EXISTING_EVIDENCE. The next minimal task is boundary-guided centerline inference using the already proven 14 room polygons as local side/offset evidence, with no area fitting and with all openings protected.

## Tests
43 targeted junction, drawing, routing, coverage and room-geometry tests passed. Compile and whitespace checks passed.

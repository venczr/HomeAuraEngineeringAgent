# Interval-wise wall face pairing ? 2026-09-17

## Interval result
The 61 collinear chains split into 121 atomic spans at overlap endpoints and sustained-gap events. Classification: 70 PAIRED_WALL_FACE, 39 UNPAIRED_WALL_FACE, 12 OPENING_ADJACENT_SPAN, 0 ambiguous under the baseline policy. They produce 35 source-linked interval centerline bands. Residual spans are retained rather than discarded.

## Policy sensitivity
Neighboring policies remain broadly stable:
- permissive 3.5?11.5 pt: 68 paired, 39 unpaired, 12 opening-adjacent, 2 ambiguous, 34 bands;
- baseline 4?12 pt: 70 paired, 39 unpaired, 12 opening-adjacent, 0 ambiguous, 35 bands;
- strict 4.5?12.5 pt: 64 paired, 37 unpaired, 14 opening-adjacent, 30 bands.
Topology is moderately sensitive but does not collapse; ambiguity appears under the permissive boundary.

## Subdivision V3
Using interval centerlines plus residual evidence without invented closures yields first floor 1 outer face and attic 3 faces. This is worse than the raw-line baseline (3/8) and whole-chain diagnostic (6/3). The cause is now precise: centerline endpoints do not meet at T/L junctions after independent pairing, and residual spans often represent wall faces rather than centerlines. Automatically including them mixes representations.

Rooms 2 and 9 remain AMBIGUOUS. No face is promoted and routing remains 14/16. The next step is a typed endpoint-to-perpendicular-chain junction solver that selects either centerline or residual face representation per local node, never both, while preserving the 14 sustained gaps.

## Tests
38 targeted drawing, routing, coverage and room-geometry tests passed. Compile and whitespace checks passed.

# Boundary-guided semantic graph V4 ? 2026-09-17

## Boundary matches
Only the 14 proven CONSISTENT_IF_M2 room polygons participate; rooms 2/9 are excluded to prevent circular evidence. 60/70 polygon edges match raster face spans. Matched/reference lengths: floor 1 2678.5/3250.0 pt; attic 2924.0/3070.5 pt.

## Candidates
100 boundary-guided candidates: 6 BOUNDARY_PLUS_LOCAL_BAND_PRIOR, 16 BOUNDARY_PLUS_PROVEN_WALL_CONTINUATION, 78 CONFLICTING_SUPPORT, 0 boundary-only. Only 22 strong candidates are eligible. Deduplication adds one genuinely new topology edge, giving V4 56 edges. Source spans, supporting room identity/edge, offset and width evidence, hashes and dependency digest are retained.

## Junction V4
First floor unchanged: 12 confirmed T, 48 unresolved, 2 opening conflicts; dangling 31 proven + 19 inferred. Attic: 6 confirmed T, 22 unresolved, 22 opening conflicts; dangling 27 proven + 17 inferred. Thus one prior no-supported case is resolved, but the new edge adds two inferred endpoints.

## Polygonization V7
First floor: 6 faces, 0 one-label, 1 multi-label, 5 unlabeled, 4 slivers. Attic: 1 face, 0 one-label, 1 multi-label. Rooms 2/9 remain ambiguous; routing remains 14/16.

## Exact blocker and visual diagnostics
Most polygon-boundary matches have CONFLICTING_SUPPORT because multiple short interval centerlines overlap the same boundary. The matcher needs continuity-based chain selection across adjacent polygon edges, not independent candidate counting. Red marks show unmatched proven-room boundaries, orange dots dangling endpoints, blue semantic edges and magenta protected gaps.

## Tests
43 targeted tests passed; compile and whitespace checks passed.

# Continuity-based boundary chains V5 ? 2026-09-17

## Candidate graph and selection
Distance-filter correction reduced local conflicts from 78 to 24. Sixty proven-room boundary chains were evaluated: 43 CHAIN_SELECTED, 13 CHAIN_INSUFFICIENT_SUPPORT, 4 CHAIN_CONFLICTING_TOPOLOGY, 0 ambiguous/opening-interrupted. Selected chains stitch 62 original fragments. Rooms 2/9 never participate as support.

## Metrics
Baseline remains 60/70 matched polygon edges and 10 unmatched. Matched length remains floor 1 2678.5/3250.0 pt and attic 2924.0/3070.5 pt: chain selection resolves ambiguity but does not invent missing raster evidence.

## Graph V5 and V8 faces
59 combined topology edges after stitching/deduplication. First floor: 13 confirmed T, 49 unsupported, 2 opening conflicts; V8 = 6 faces, 0 one-label, 1 multi-label, 5 unlabeled, 4 slivers. Attic: 5 confirmed T, 26 unsupported, 23 opening conflicts; V8 = 1 multi-label face.

## Exact remaining gaps
Unmatched long boundaries: attic WC room 11 top edge 71 pt; room 13 top 75 pt. Floor 1: room 4 right edge 83.5 pt; room 5 left 53 pt; room 7 top 142.5 pt; room 8 bottom 142.5 pt. Four additional 0.5 pt edges are raster contour artifacts. These long visible drawing lines are absent from current raster wall-segment extraction, so chain selection cannot reconstruct them without new source evidence extraction.

## Diagnostics
Blue: semantic topology edges. Green: selected boundary chains. Red: insufficient/conflicting chains. Magenta: protected gaps.

Rooms 2 and 9 remain AMBIGUOUS. Routing remains 14/16.

## Tests
34 targeted tests passed; compile and whitespace checks passed.

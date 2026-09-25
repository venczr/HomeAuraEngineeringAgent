# Semantic topology boundary evidence ? 2026-09-17

## Implemented
- Typed interior boundary evidence, interior geometric openings, connectivity edges, and whole-building topology summary.
- Deterministic 2x PDF raster wall-corridor occupancy analysis with explicit PDF-point transform.
- Short raster interruptions are retained as diagnostics and cannot create connectivity edges.
- Only sustained gaps at least 12 drawing points wide may create UNKNOWN_OPENING connectivity candidates; door/open-passage semantics remain unresolved without symbol evidence.

## Test_01 result
- 20 candidate interior boundaries now have source-hash-linked raster evidence.
- 19 classify as SOLID_WALL under the current bounded corridor model.
- One boundary (room 2 / room 6) contains four short interruptions, 2.5?8 pt, in dimension/text linework; it classifies WALL_WITH_SHORT_INTERRUPTION.
- Zero sustained interior gaps pass the connectivity threshold. Therefore zero interior openings and zero room-connectivity edges are promoted.
- Rooms 2 and 9 remain unresolved semantic faces. No candidate is selected from area agreement.
- Whole-building topology status: PARTIAL_BOUNDARIES_CONNECTIVITY_UNRESOLVED; engineering authority remains NOT_AUTHORIZED.

## Validation
40 targeted drawing, locality, PDF ingestion, intake and room-geometry tests passed. Python compilation and git diff whitespace checks passed.

## Next bounded task
Current adjacency corridors only compare connected-white region envelopes and miss visible doorway ticks/openings where room faces meet a circulation face. Reconstruct wall centerline segments directly from raster line evidence, suppress text/dimension strokes using length/parallelism, split segments at sustained discontinuities, then associate those gaps to room labels and semantic face variants. Keep all types UNKNOWN_OPENING unless arc/swing or explicit symbol evidence is independently detected.

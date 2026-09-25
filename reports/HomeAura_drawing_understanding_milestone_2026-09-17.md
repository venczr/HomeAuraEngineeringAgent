# Drawing understanding milestone — 2026-09-17

## Verdict
Completed integrity, typed reasoning output, and fail-closed Test_01 deterministic replay on the existing drawing architecture.

## Evidence
- Frozen review: 2 distinct floors, 16 room labels, 8 dimensions, 2 outer contours, 2 stair candidates.
- Both archived PDFs and manifest hashes reverified during every replay.
- Observation normalization integrity: VERIFIED for both sources.
- Replay is deterministic and does not invoke perception or engineering calculations.
- Room 101 / 101DAA3: NO_MATCH; no room polygon candidates, cross-source transform, floor identity, position, or topology evidence.

## Validation
- Targeted drawing/replay: 8 passed.
- Drawing + PDF ingestion + intake + room artifact: 35 passed.
- Related project/domain regressions excluding two pre-existing route expectation failures: 166 passed.
- Full related attempt: 207 passed, 2 failed because dirty baseline API exposes coverage-preview while old route expectations omit it.

## Next highest value work
1. Reconstruct room polygons in drawing space from vector/raster wall evidence.
2. Solve scale from anchored dimensions while preserving explicit units and residuals.
3. Establish cross-floor anchors and drawing-to-project transform before Room101 matching.

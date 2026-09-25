# Targeted raster line recovery — 2026-09-17

## Result

The post-strict recovery pass examined all six long unmatched boundaries from independently proven rooms. Raw raster ink confirmed all six at continuity 1.0. Each source stroke is 0.5 drawing pt thick and was therefore rejected by the strict extractor's 0.75 pt wall-band threshold. Recovery emits source-linked `WallCenterlineCandidate` observations and feeds them through the existing chain, interval-pairing, semantic-centerline, support-chain, junction, normalization, and polygonization pipeline. It does not insert final topology edges.

Rooms 2 and 9 never participate as support evidence. Room area labels are not used. All 14 protected sustained gaps remain present and none intersects a recovered candidate.

## Six-boundary report

| Boundary | Room | Expected | Original | Miss reason | Attempt | Raster evidence | Recovered | Gap conflict | Final |
|---|---:|---:|---|---|---|---|---:|---|---|
| floor room 4 right | 4 | 83.5 pt | unmatched | THICKNESS_OUTSIDE_POLICY | TARGETED_RAW_RASTER_CORRIDOR_V1 | continuity 1.0, thickness 0.5 pt | 83.5 pt | false | recovered |
| floor room 5 left | 5 | 53 pt | unmatched | THICKNESS_OUTSIDE_POLICY | TARGETED_RAW_RASTER_CORRIDOR_V1 | continuity 1.0, thickness 0.5 pt | 53 pt | false | recovered |
| floor room 7 top | 7 | 142.5 pt | unmatched | THICKNESS_OUTSIDE_POLICY | TARGETED_RAW_RASTER_CORRIDOR_V1 | continuity 1.0, thickness 0.5 pt | 142.5 pt | false | recovered |
| floor room 8 bottom | 8 | 142.5 pt | unmatched | THICKNESS_OUTSIDE_POLICY | TARGETED_RAW_RASTER_CORRIDOR_V1 | continuity 1.0, thickness 0.5 pt | 142.5 pt | false | recovered |
| attic room 11 top | 11 | 71 pt | unmatched | THICKNESS_OUTSIDE_POLICY | TARGETED_RAW_RASTER_CORRIDOR_V1 | continuity 1.0, thickness 0.5 pt | 71 pt | false | recovered |
| attic room 13 top | 13 | 75 pt | unmatched | THICKNESS_OUTSIDE_POLICY | TARGETED_RAW_RASTER_CORRIDOR_V1 | continuity 1.0, thickness 0.5 pt | 75 pt | false | recovered |

## Metrics

- Recovered source segments: 6.
- Strict + recovered raster candidates: 102 (previously 96).
- Matched proven-room boundary edges: 66/70 (previously 60/70).
- First floor matched length: 3100.0/3250.0 pt (previously 2678.5/3250.0 pt).
- Mansard matched length: 3070.0/3070.5 pt (previously 2924.0/3070.5 pt).
- Protected sustained gaps: 14/14 preserved.

## Polygonization after full replay

- First floor: 5 faces; 0 one-label; 1 multi-label; 4 unlabeled wall-band slivers.
- Mansard: 2 faces; 1 one-label (room 13); 1 multi-label; 0 unlabeled.

The recovered lines improve source coverage and independently isolate room 13, but they do not produce a unique topology-consistent face for room 2 or room 9. Both remain `AMBIGUOUS`; geometry-only routing remains 14/16. The new localized blocker is semantic continuity at the remaining unmatched/unsupported critical boundaries, not missing ink on these six recovered spans.

## Diagnostics and validation

- `reports/tmp/floor_1_plan_targeted_raster_recovery_diagnostic.png`
- `reports/tmp/attic_plan_targeted_raster_recovery_diagnostic.png`
- 34 related tests passed.
- Python compilation passed.
- Scoped whitespace check passed.


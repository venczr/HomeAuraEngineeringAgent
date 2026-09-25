# UFH geometry router expansion ? 2026-09-17

Authority: GEOMETRY_ONLY / NON_ENGINEERING / NOT_FOR_CONSTRUCTION. Spacing remains 200 mm VISUAL_TEST_POLICY.

## Result
Before: 10 generated, 4 failed, 2 skipped. After: 14 generated, 0 failed, 2 skipped.

## Visual QA
Counterflow layouts remain contained with consistent tracks. Compact sweeps for small rooms remain inside 100 mm inset, keep 200 mm lane spacing, and have no self intersections. Room 6 follows its cleaned orthogonal L-like face. Central U-turns in counterflow are preview artifacts and require later installation-quality review.

## Per room
| Room | Status | Length mm | Legacy | Diagnostics |
|---|---|---:|---|---|
| 10 / 26.0; Детская | GENERATED | 69044 | WOULD_ACCEPT | CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE |
| 11 / 5.1; WC | GENERATED | 22291 | WOULD_REJECT | CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE |
| 12 / 20.6; Детская | GENERATED | 61164 | WOULD_ACCEPT | CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE |
| 13 / 5.3; WC | GENERATED | 23551 | WOULD_REJECT | CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE |
| 14 / 28.7; Спальня | GENERATED | 73268 | WOULD_ACCEPT | CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE |
| 15 / 13.0; Гардероб | GENERATED | 48772 | WOULD_ACCEPT | CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE |
| 16 / 12.9; Ванна + WC | GENERATED | 48628 | WOULD_ACCEPT | CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE |
| 9 / 39.9; Назначение не подписано | SKIPPED_GEOMETRY_UNRESOLVED | - | NOT_EVALUATED_FOR_GEOMETRY_PREVIEW | SEMANTIC_FACE_UNRESOLVED |
| 1 / 12.9; Вх. гр. | GENERATED | 47364 | WOULD_ACCEPT | CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE |
| 2 / 30.7; Назначение не подписано | SKIPPED_GEOMETRY_UNRESOLVED | - | NOT_EVALUATED_FOR_GEOMETRY_PREVIEW | SEMANTIC_FACE_UNRESOLVED |
| 3 / 40.9; Кухня / зал | GENERATED | 91676 | WOULD_REJECT | CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE |
| 4 / 15.9; Котельная | GENERATED | 53860 | WOULD_ACCEPT | CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE |
| 5 / 4.4; Подпись частично неразборчива | GENERATED | 18000 | WOULD_REJECT | CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE |
| 6 / 16.9; Ванна + туалет | GENERATED | 77056 | WOULD_ACCEPT | RASTER_CONTOUR_CLEANUP_WITHIN_ONE_DRAWING_POINT |
| 7 / 15.6; Спальня | GENERATED | 52588 | WOULD_ACCEPT | CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE |
| 8 / 17.3; Спальня | GENERATED | 55412 | WOULD_ACCEPT | CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE |

## Implementation
Existing floor_heating_engine now falls back to its existing scanline lane primitives for compact 200 mm serpentine routing when the four-ring counterflow pattern cannot fit. The same containment, exclusion, spacing, length and self-intersection validator runs. Raster contour cleanup is bounded to one drawing point before adapting a proven orthogonal face.

## Topology
Rooms 2 and 9 remain unresolved and skipped. Wall graph remains 96 candidates; opening association is the next bottleneck.

## Validation
68 related routing, drawing, PDF and room-geometry tests passed. Compile and whitespace checks passed.

# First geometry-only UFH routing preview ? 2026-09-17

Authority: **GEOMETRY_ONLY / NON_ENGINEERING / NOT_FOR_CONSTRUCTION**. Preview spacing is 200 mm under `VISUAL_TEST_POLICY_NOT_ENGINEERING_DESIGN_INPUT`. No heat load, hydraulics, manifold selection or engineering feasibility claim was computed.

Attempted: 14; generated: 10; failed: 4; skipped unresolved: 2.

| Room | Geometry | Attempted | Routing | Circuits | Lengths mm | Coverage | Legacy |
|---|---|---:|---|---:|---|---:|---|
| 10 / 26.0; Детская | USABLE | true | GENERATED | 1 | 69044 | 1 | WOULD_ACCEPT |
| 11 / 5.1; WC | USABLE | true | FAILED | 0 | - | 0 | WOULD_REJECT |
| 12 / 20.6; Детская | USABLE | true | GENERATED | 1 | 61164 | 1 | WOULD_ACCEPT |
| 13 / 5.3; WC | USABLE | true | FAILED | 0 | - | 0 | WOULD_REJECT |
| 14 / 28.7; Спальня | USABLE | true | GENERATED | 1 | 73268 | 1 | WOULD_ACCEPT |
| 15 / 13.0; Гардероб | USABLE | true | GENERATED | 1 | 48772 | 1 | WOULD_ACCEPT |
| 16 / 12.9; Ванна + WC | USABLE | true | GENERATED | 1 | 48628 | 1 | WOULD_ACCEPT |
| 9 / 39.9; Назначение не подписано | GEOMETRY_UNRESOLVED | false | SKIPPED_GEOMETRY_UNRESOLVED | 0 | - | - | NOT_EVALUATED_FOR_GEOMETRY_PREVIEW |
| 1 / 12.9; Вх. гр. | USABLE | true | GENERATED | 1 | 47364 | 1 | WOULD_ACCEPT |
| 2 / 30.7; Назначение не подписано | GEOMETRY_UNRESOLVED | false | SKIPPED_GEOMETRY_UNRESOLVED | 0 | - | - | NOT_EVALUATED_FOR_GEOMETRY_PREVIEW |
| 3 / 40.9; Кухня / зал | USABLE | true | GENERATED | 1 | 91676 | 1 | WOULD_REJECT |
| 4 / 15.9; Котельная | USABLE | true | GENERATED | 1 | 53860 | 1 | WOULD_ACCEPT |
| 5 / 4.4; Подпись частично неразборчива | USABLE | true | FAILED | 0 | - | 0 | WOULD_REJECT |
| 6 / 16.9; Ванна + туалет | USABLE | true | FAILED | 0 | - | 0 | WOULD_REJECT |
| 7 / 15.6; Спальня | USABLE | true | GENERATED | 1 | 52588 | 1 | WOULD_ACCEPT |
| 8 / 17.3; Спальня | USABLE | true | GENERATED | 1 | 55412 | 1 | WOULD_ACCEPT |

## Legacy policy
Generated room 3 is 91,676 mm and therefore `WOULD_REJECT` under legacy 40?80 m, while its geometry route remains successful.

## Wall graph
ATTIC_PLAN: 47 segments, 34 intersections, 17 components; FLOOR_1_PLAN: 49 segments, 28 intersections, 21 components. Candidate graph still needs opening association and semantic-face closure.

## Validation
50 targeted tests passed. Compile and whitespace checks passed.

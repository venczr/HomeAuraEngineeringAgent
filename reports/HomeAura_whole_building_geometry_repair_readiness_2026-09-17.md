# Whole-building geometry repair and readiness checkpoint — 2026-09-17

## Outcome
The two-floor drawing candidate model remains deterministic and fail-closed. Generic repair assessment rejected convex-hull replacement for both area outliers because it neither follows observed wall evidence nor reliably resolves the area residual. No Test_01-specific polygon was fabricated.

## Geometry readiness
- 16 labeled polygon candidates; 14 area-consistent under the still-unverified m2 interpretation.
- 2 rooms require focused geometry review: first-floor label 2 / 30.7 and attic label 9 / 39.9.
- Two unlabeled narrow regions are retained separately and are not automatically merged.
- Before/after convex-hull areas and residuals are recorded as REJECTED_INSUFFICIENT_EVIDENCE.

## Evidence and authority
- Title-block 1:100 evidence and dimension-fit evidence are independent and corroborating.
- Dimension units remain unproven, so physical areas/wall thicknesses remain candidates.
- 20 wall-band/adjacency candidates exist; opening symbols are not geometrically bound to their gaps.
- Cross-floor contour and stair alignment remain candidates.
- Room101 is optional regression only.

## Minimum questions / missing evidence
1. Confirm dimension-label convention/units shown on these plans (proposed confirmation: metres).
2. Resolve the exact boundary of the two area-outlier spaces, preferably from a higher-quality/vector source or owner confirmation overlay.
3. Confirm or provide the opening schedule/types and heights; plan evidence alone does not establish exhaustive doors/windows or heights.
4. Provide/confirm envelope constructions and thermal properties, floor/roof boundary conditions, project locality, and ventilation/infiltration design basis.

## Engineering readiness
SP60/UFH execution remains blocked by envelope/opening/construction authority and two unresolved room geometries. The 14 consistent rooms are usable for review and confirmation, not calculation authority.

## Validation
Drawing/PDF/intake/room targeted suite passed. Python compile and UTF-8 checks passed. No new regression identified.

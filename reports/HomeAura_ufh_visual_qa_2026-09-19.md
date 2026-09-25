# UFH visual QA — 2026-09-19

## Visual reference: accepted spiral

- Artifact: `projects/Test_01/exports/floor_heating_svg/HA-FH-VIS-008-CORE-R3/core-debug.png`.
- Result: `PASS`.
- Connected components: 1; endpoints: 2; branches: 0.
- Self-intersections: 0; invalid pairs: 0.
- Centre hairpin segments: 2; installed spacing: 200 mm.
- Visual reading: one continuous rectangular inward spiral, one central hairpin, and an interleaved outward return.

## Current Test_01 floor preview

- Artifacts: `dev/ufh_real_plan/first_floor_ufh.svg` and `dev/ufh_real_plan/mansard_ufh.svg` (the regenerated current preview outputs).
- Current selected strategy: `MEANDER`; the generator explicitly does not label these paths as completed spirals.
- First-floor room 2 now has an explicit `OWNER_REQUESTED_UNDER_STAIR_HEATING_PREVIEW` route. It follows the observed room contour and includes the area under the diagonal stair run; the room remains geometry-unresolved for construction authority.
- The isolated spiral gate contains 6 candidates; accepted: 0; rejected: 6.
- Rejection reason for the regular fixtures: `CENTER_TURN_AND_INTERLEAVED_RETURN_NOT_MATERIALIZED`.
- The rejection is now evidence-backed: each candidate has one component, two endpoints, zero self-intersections, valid containment, and valid R80 leg lengths, but the measured center-hairpin and interleaved-return gates both fail. The narrow fixture is rejected as an empty route.
- Visual reading: the current real-floor paths are dense rectangular sweeps, not the accepted central-hairpin spiral pattern.

## Gate

Do not publish the current Test_01 floor preview as a correct «улитка». Promote a spiral only after the route has one connected component, two endpoints, zero self-intersections, a center hairpin, and the interleaved return is visible in the rendered artifact.

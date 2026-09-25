# HomeAura UFH physical routing continuation — rounded bends and zone candidates — 2026-09-20

## Rounded bend model

The earlier `BEND_VALID` check only inspected adjacent straight-leg lengths. `agent/ufh_bend_geometry.py` now derives a second centerline with explicit quarter-circle fillets at every orthogonal corner. For the current preview assumptions it uses pipe 16×2 mm, centerline bend radius R80 mm and outer pipe radius 8 mm. It checks tangent clearance, safe-area containment after outer-radius offset, obstacle clearance, non-adjacent pipe clearance, rounded topology and rounded path length. The legacy sharp polyline remains available for compatibility; the rounded result is separately reported as `BEND_GEOMETRY_VALID` and rendered in `first_floor_ufh_rounded.svg` / `mansard_ufh_rounded.svg`.

Control checks pass for a real R80 quarter turn and reject short tangent legs and narrow safe areas. The rounded model does not claim manufacturer approval; R80 remains a project assumption until the selected pipe data is bound.

## Zone candidates

The previous 36 fragments were not independent circuits. The new `agent/ufh_zone_layout.py` proposes geometric zone candidates using separate meanders for regular areas, validates each route and rounded bend, checks zone overlap and route length, and leaves both endpoint access and manifold connection `UNVERIFIED`. It never creates a transit line through a wall or another room.

For the 12 rooms requiring length-driven review:

- `zone_decomposition_review.json` records 12 room analyses.
- Rectangular rooms receive independent-zone candidates where geometry passes.
- Rooms 2 and 6 remain `UNVERIFIED_COMPLEX_BOUNDARY`; their stair/irregular geometry is not replaced by rectangles.
- Room 4's former internal split is not promoted; its shared point remains diagnostic evidence only.
- No zone candidate is a construction-ready circuit until both endpoint paths are authorized.

## Current status

- Preliminary continuous coverage routes: 15.
- Previous automatic fragments: 36.
- Split candidates blocked by endpoint access: 12.
- Manifold connections: 0/15 confirmed.
- Each circuit now exposes `GEOMETRY_VALID`, `TOPOLOGY_VALID`, `BEND_VALID`, `CIRCUIT_SPLIT_VALID`, `PIPE_LENGTH_VALID`, `ENDPOINT_ACCESS_VALID`, `MANIFOLD_CONNECTED`, `HYDRAULIC_VALID`, and `VISUALIZATION_VALID` as separate `VALID`/`INVALID`/`UNVERIFIED` states.
- `visualization_validation.json` remains `VALID` against the calculated sharp centerline. Rounded previews are separate and retain room/circuit identifiers.
- Full repository tests and targeted UFH tests pass.

Remaining limits are authoritative openings, corridor/riser paths, manifold location, pipe manufacturer bend data, hydraulic sizing, and exact stair geometry for rooms 2 and 9.

## Follow-up correction — exact arc length and rendered geometry

The first rounded implementation correctly checked sampled quarter-circle
points, but its length correction was applied to the chord sum with an
incorrect per-arc term. `agent/ufh_bend_geometry.py` now computes route length
from the sharp polyline using the exact fillet identity:

`L_rounded = L_sharp - 2R·N_bends + (πR/2)·N_bends`.

The module also emits `svg_path_data` containing SVG `A` commands for the
actual R80 arcs. The rounded floor and control SVGs now render this path; the
sampled points remain in JSON for numeric inspection. Containment and obstacle
checks include pipe outer radius (8 mm) and the arc sampling sagitta margin.
Adjacent-turn tangent consumption is checked on each shared straight leg.

The exact quarter-turn regression is covered by
`tests/test_ufh_physical_control_scenarios.py` and the targeted physical UFH
suite passes. A full repository run completed with all tests passing after the
length correction; the final artifact-only regeneration was followed by the
targeted UFH regression (`26 passed`).

## Current evidence snapshot

- A1, A2 and A3: duplicate centerline length 0; rounded R80 geometry valid.
- A4 and A5: rejected from the existing non-rectangular spiral gate; no
  geometry was altered to force acceptance.
- A6: rejected because the narrow room cannot satisfy the bend constraints.
- Real plan: 15 preliminary coverage routes; rounded bend gate 15/15; preview
  pipe-length policy 5/15; manifold-confirmed 0/15.
- Zone review: 12 long-route rooms retain geometry-only zone candidates;
  endpoint access and manifold connection remain `UNVERIFIED`.
- Rooms 2 and 9 retain the exact stair-boundary and passage-continuity blocker.
- ZIP: `dev/ufh_handoff/HomeAura_UFH_latest_review.zip` contains the rounded
  floor plans, rounded controls, spiral validation, zone review and authority
  intake artifacts.

# HomeAura UFH zone endpoint access review — 2026-09-20

This stage reviewed the existing `zone_decomposition_review.json` candidates
without regenerating the building and without changing the spiral or rounded
bend algorithms.

## Method

Each candidate endpoint was connected by the shortest straight in-room segment
to the nearest point on that zone's room boundary. The segment was checked for
room containment, 16x2 mm pipe outer-radius clearance and collision with the
other candidate routes. This is a geometric boundary-exit test only. It does
not infer a door, wall opening, riser, corridor route or manifold connection.

## Room 12, attic children's room

The existing two-zone candidate contains two routes of 50.762 m and 50.743 m.
All four endpoints reach their own zone boundary through a 100 mm in-room path
without an occupied-route or obstacle conflict. Therefore:

- `ENDPOINT_ACCESS_GEOMETRY = VALID` for both zones.
- `OPENING_AUTHORITY = UNVERIFIED_NO_AUTHORIZED_OPENING`.
- `MANIFOLD_CONNECTED = UNVERIFIED`.

The two-zone candidate remains a geometry candidate, not a construction circuit.
The new visualisation marks route endpoints red, geometric room-boundary exits
blue, and the candidate exit segments amber.

## All existing candidates

The review contains 20 zone candidates across 12 long-route rooms. All 20 have
geometrically reachable endpoints under this in-room test; none has an internal
exit-path blocker. This narrows the current failure mode: the candidates are
blocked at the building-authority boundary, where openings, corridors, riser
paths and collector location remain unverified. Candidate statuses are not
promoted as a result.

The original review file remains unchanged for before/after comparison. The
enriched result is `dev/ufh_real_plan/zone_endpoint_access_review.json`.

## Source handoff

The algorithm sources and focused tests are packaged in
`dev/ufh_handoff/HomeAura_UFH_algorithm_sources.zip`, including
`agent/ufh_zone_layout.py`, `agent/ufh_bend_geometry.py`,
`agent/ufh_endpoint_access.py`, `agent/ufh_layout_engine.py`, physical
validation, and the focused UFH tests.

Remaining blockers are authoritative openings and transit paths, manifold and
riser evidence, hydraulic inputs, and unresolved stair geometry in rooms 2 and
9. No construction-ready status is asserted.

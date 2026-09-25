# Autonomous turns and compact sweep — 2026-09-17

## Supervisor

The hang came from PowerShell retaining the full streaming Codex stdout/stderr pipeline while the nested process and MCP children remained attached to inherited handles. The bounded Python runner now closes stdin, redirects JSONL directly to a file, tracks PID and file-growth heartbeat, records exit/timeout/session state atomically, sends CTRL_BREAK before kill, and uses official `codex exec resume`.

TURN A read router configuration/tests, ran 3 tests, and wrote checkpoint A. TURN B started automatically, resumed the same Codex session from compact state, audited a different queue subsystem, ran 6 tests, and wrote checkpoint B. Restart recovery converts stale RUNNING tasks to FAILED_RETRYABLE with evidence.

## HomeAura P0

`_body_for_segments` previously traversed a full parity lane and then backtracked to the overlap connector when adjacent scan intervals shifted. The replacement chooses all overlap connectors first and emits each lane monotonically between its incoming and outgoing connector. It fails closed when a connector is outside the allowed domain or the completed path intersects itself.

Result: all 16 independently observed room geometries now produce validated geometry-only routes. Rooms 2 and 9 changed from route-validation failure to generated. This remains NON_ENGINEERING / NOT_FOR_CONSTRUCTION. A generic shifted-lane regression protects the invariant; no room IDs, coordinates, or area labels influence routing.

## Verification

- Codex TURN A: completed, checkpoint written, 3 passed.
- Codex TURN B: automatically resumed, checkpoint written, 6 passed.
- Combined supervisor/router/routing checks: 21 passed.
- Test_01 geometry-only routing: 16/16 generated.
- MCP stdio integration remains verified and unchanged.

## Continued queue

P2 started automatically after P0. Twelve drawing-understanding tests pass. Inspection confirms current assessment checks simple/nonzero geometry, unique label containment, outer-contour containment, and competing observed-room overlap; holes/stair/passage cleanup authority remains the next bounded QA task.


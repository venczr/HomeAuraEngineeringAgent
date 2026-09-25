# Persistent autonomous supervisor — 2026-09-17

## Persistence root cause

The prior supervisor existed only as a bounded foreground smoke script owned by the interactive turn. It had no durable `run` entrypoint, detached launcher, PID ownership, heartbeat, or continuous queue loop. Consequently nothing remained after the parent turn ended.

## Persistent process

`python -m tools.autonomous_supervisor.cli run` now restores stale tasks, selects READY/retryable work, launches bounded Codex turns, consumes machine JSON results, checkpoints state, and immediately selects the next task. It observes wall-clock and turn limits and handles SIGINT/SIGTERM/stop requests.

Windows launchers provide idempotent start, status, and owned graceful stop. Output is redirected to compact files; PID and heartbeat are persisted. No Windows policy was modified. The obsolete diagnostic HTTP router was stopped; stdio MCP remains unchanged.

## Persistence proof

The detached launcher returned while supervisor PID 20280 remained alive. The process completed P4, wrote `P4-attempt-2.json`, selected P5 without a user message, started its Codex turn, and wrote its checkpoint. PID 20280 remains running in `IDLE_NO_READY_TASKS`, independent of the launcher/interactive workflow.

The result artifact is now a terminal turn contract: once valid JSON appears, the runner ends the child process gracefully and checkpoints rather than allowing it to drift into another queue task.

## HomeAura autonomous progress

- P2 completed observed-face containment/stair-overlap QA and fails affected geometry closed.
- P3 completed topology/readiness binding; connectivity remains explicitly unresolved and not promoted to authority.
- P4 verified typed engineering blockers: 19 focused tests passed without invoking calculations on missing inputs.
- P5 completed automatically after P4.
- Independent combined verification: 42 passed.

The current geometry assessment is stricter after P2; source-observed faces overlapping stair exclusion evidence remain ambiguous. This is an evidence-discipline correction and is distinct from the earlier compact-sweep capability milestone.

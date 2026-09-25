# Autonomous infrastructure bootstrap — 2026-09-17

## Verified

- Codex CLI v0.154.0, Python 3.12, Node 24.21.0.
- TokenWave uses its existing environment secret; no credential was written or logged.
- Model catalog: 119 models. Mappings: CHEAP `gpt-5.6-luna`, ANALYSIS `deepseek-v4-pro`, REVIEW `claude-haiku-4-5`, HARD `gpt-5.6-sol`, ESCALATION `gpt-6-astra`.
- Direct worker smoke calls succeeded for ANALYSIS, REVIEW and HARD.
- `homeaura_tokenwave` stdio MCP server is registered without removing existing servers.
- Persistent state and queue exist at `dev/autonomous/state.json`.
- Two-task smoke passed: compile, checkpoint, dependent tests, checkpoint, with no user input.

## Reliability

The isolated router implements packet and response limits, discovery/fallback, retries/backoff, deterministic cache, task/run budgets, parallel concurrency limit, circuit breaker, malformed-response normalization, request/task IDs, latency and usage logging. Logs exclude headers and environment values.

## Integration blocker

`codex exec` discovered `homeaura_tokenwave/router_status`, but Codex v0.154.0 rejected the MCP call because the tool required approval while the invocation used `approval policy = never`. Direct stdio and TokenWave transports are healthy. Full Codex-to-MCP acceptance is therefore not claimed.

## HomeAura continuation

The queue contains P0 compact-sweep self-intersection, P2 observed-face containment QA and P3 semantic topology. Current product state remains 16 usable observed faces, 16 routing attempts, 14 validated routes; rooms 2/9 fail route self-intersection validation.

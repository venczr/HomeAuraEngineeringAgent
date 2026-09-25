# HomeAura MCP transport fix — 2026-09-17

## Result

The empty HTTP 503 was produced before Uvicorn: with an empty `NO_PROXY`, the installed HTTP client sent `127.0.0.1` through the machine proxy. `curl` reached FastMCP and returned its expected 406 for a missing SSE Accept header, while httpx returned proxy headers and an empty 503. Setting `NO_PROXY=127.0.0.1,localhost` made the standard MCP client initialize successfully.

The durable integration now uses Codex's officially supported stdio MCP transport. `start_stdio.ps1` reads only the named per-user `OPENAI_API_KEY` when Codex sanitizes the child environment; it never prints or persists the value. HTTP lifecycle scripts retain loopback binding, PID ownership, stale-listener detection, and graceful stop for diagnostics, but Codex does not depend on them.

## Verification

- Codex exec -> `homeaura_tokenwave/router_status`: PASS; `tokenwave_available=true`; ANALYSIS=`deepseek-v4-pro`.
- Codex exec -> `delegate_task` -> TokenWave -> `deepseek-v4-pro` -> Codex: PASS. Unique marker `HA-MCP-E2E-3bac25ea77d6` returned with unique task/request IDs.
- Product routing regressions: 11 passed.
- Current geometry-only state remains 14/16 validated. Rooms 2 and 9 fail compact-sweep validation.

## Remaining autonomous-runtime blocker

The first official `codex exec` / `exec resume` wrapper attempt hung while capturing nested CLI output before TURN A wrote its checkpoint. It was stopped without product edits. Persistent queue/state remain recoverable. The next runtime task is to replace synchronous pipeline capture with a bounded process runner and explicit timeout/checkpoint protocol, then prove TURN A -> resumed TURN B.

## P0 progress

The failure was reproduced from current artifacts. The generic invariant is localized in `_body_for_segments`: when consecutive scanline intervals have shifted endpoints, its connector travels back along an already traversed lane before descending, creating overlapping/self-intersecting route segments. Fix requires connectivity-aware lane-fragment ordering/decomposition; no room-specific correction was applied.

# HomeAura Codex quota-aware instructions

You are the Codex integration/writer agent for HomeAura. Read `00_COMMON_ROUTING_POLICY.md` completely and obey it.

## Session contract

- Use the model and effort selected before this session started. Do not switch with `/model` during the session.
- Treat the task prompt as exactly one atomic unit. Do not start the next broad phase in the same session.
- Read the active task, artifact index, exact changed files, and exact tests first. Do not recursively load historical reports.
- Prefer local deterministic tools over model reasoning for hashes, inventories, builds, tests, formatting, and receipt generation.
- Do not spawn subagents unless an explicit authority names their bounded scopes and budget.
- Preserve user changes and immutable HomeAura evidence.

## Codex routing ladder

1. `gpt-5.6-luna` + `low`: mechanical work and clear repeatable transformations.
2. `gpt-5.6-terra` + `medium`: ordinary implementation and test fixes.
3. `gpt-5.6-terra` + `high`: multi-file debugging and complex implementation.
4. `gpt-5.6-sol` + `high`: credentials, claims, fencing, security boundaries, governance, or a demonstrated Terra capability failure.

Do not use Max or Ultra by default. If Luna is unavailable, request a fresh Terra-low session and record the substitution; do not silently continue on a different model.

## Quota behavior

- GREEN: complete the one atomic unit, verify it, and checkpoint.
- AMBER: finish only the already-started atomic unit, run its tests, checkpoint, release the writer lease, and stop.
- RED or unknown: do not implement. Produce only a compact handoff/checkpoint.
- Never use Claude as a rescue writer. Claude remains the independent reviewer.

## Handoff behavior

When a different model or provider is appropriate, do not change the current session. Produce:

```json
{"schema":"homeaura.model-route-request.v1","task_class":"<class>","current_agent":"codex","requested_agent":"<codex|kimi|claude>","reason":"<exact reason>","checkpoint_path":"<absolute path>","checkpoint_sha256":"<sha256>","writer_lease_released":true,"no_provider_retry":true}
```

After emitting it, make no more edits.

## Current HomeAura safety

No production provider request, real credential read, attempt-011 creation, claim creation, rev-008/rev-004 transaction retry, attempt-010 modification, or R0B1 acceptance is implied by this routing prompt. Those actions still require their exact governance authority.


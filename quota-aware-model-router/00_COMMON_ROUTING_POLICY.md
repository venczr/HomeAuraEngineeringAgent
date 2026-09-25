# HOMEAURA_QUOTA_AWARE_ROUTING_POLICY_V1

## Purpose

Complete HomeAura safely while minimizing quota consumption. Route work at atomic task boundaries. Never trade away tests, evidence, independent review, or immutable boundaries for quota savings.

## Non-negotiable invariants

1. Exactly one active writer lease exists. The writer is either Codex or Kimi, never both.
2. Claude is an independent read-only reviewer. Claude must not edit bytes it later accepts.
3. No model may self-accept its own work.
4. A model, effort, or provider change happens only in a fresh session after a verified checkpoint.
5. Never retry an ambiguous, max-token, rate-limited, or already-claimed provider transaction automatically.
6. Never enable paid fallback, Extra Usage, automatic top-up, HighSpeed, or an unapproved endpoint.
7. Unknown quota, unknown provenance, missing checkpoint, hash drift, or lease conflict is RED and fails closed.
8. Prefer deterministic local commands for builds, tests, hashes, inventories, schema validation, formatting, and receipt generation.
9. Load only the artifact index, active task, changed files, exact requirements, and required evidence. Do not reread full history.
10. Do not use model subagents or swarm mode by default. They multiply context and quota. They require explicit scope and budget authorization.

## Atomic task classes

- `local_deterministic`: a known local command can produce and verify the result without model judgment.
- `mechanical`: narrow, repeatable, low-ambiguity text or code manipulation.
- `routine_code`: bounded implementation with established patterns and tests.
- `complex_code`: multi-file reasoning, debugging, architecture, or uncertain design.
- `security_critical`: credentials, claims, fencing, DACL, timeout/retry semantics, immutable evidence, or stage-gate logic.
- `independent_review`: read-only review of frozen exact bytes.
- `owner_gate`: proposal/confirmation/checkpoint preparation with no executable action.

## Quota bands

- GREEN: effective remaining allowance is at least 30%, no provider-limit signal exists, and capacity is at least twice the estimated atomic-unit cost.
- AMBER: 15–29%, or capacity is only one to two estimated atomic units. Finish only the current atomic unit, verify it, checkpoint, and stop.
- RED: below 15%, insufficient or unknown capacity, stale telemetry, or any rate-limit/billing/overload signal. Do not begin model-intensive work.

Claude independent review additionally requires capacity for two complete review passes plus a 20% reserve. This reserve is for one corrected re-review, not repeated advisory audits.

## Context bands

- Kimi: checkpoint at 25%, start a new session at 35%, hard-stop the old session at 50%.
- Codex and Claude: checkpoint at 50%, start a new session at 60%, hard-stop the old session at 75%.
- A compact is not a substitute for an exact checkpoint. If compaction may lose provenance, end the session and use a selective handoff.

## Model routing

### Codex

- mechanical: `gpt-5.6-luna`, `low`;
- routine: `gpt-5.6-terra`, `medium`;
- complex: `gpt-5.6-terra`, `high`;
- security-critical: `gpt-5.6-sol`, `high`;
- use Sol for complex work only after Terra shows a real capability failure or when risk is security/governance;
- Max and Ultra are prohibited by default. Ultra spawns agents and consumes quota nonlinearly.

If Luna is unavailable, use Terra `low`. Never silently substitute a model: record the substitution before work begins.

### Kimi

- mechanical/routine: `k3-256k`, `low`;
- complex/security-critical: `k3-256k`, `high`;
- keep one effort for the entire session;
- use `k3` 1M only after selective loading and a measured fit failure for 256k;
- `k3-256k` requires estimated input no greater than 200,000 tokens and at least 40,000 tokens left for reasoning, output, and protocol overhead;
- do not use `kimi-for-coding-highspeed`: it consumes about three times the quota;
- do not disable thinking to “save” quota when K3 identity is required; official Kimi routing may switch to K2.6;
- no Kimi subagents unless separately authorized.

### Claude

- mechanical independent validation only: `haiku`;
- ordinary code review: `sonnet`, `high`;
- security/governance/claim/credential/stage-gate review: `opus`, `high`;
- no fallback chain during an acceptance review;
- no Fable, Max, Ultracode, agent teams, or OpusPlan by default;
- run every Claude review in a new visible PowerShell window with only read-only tools;
- record the resolved model, effort, raw output, normalized output, exit code, and exact reviewed hashes.

## Boundary protocol

Before changing agent/model/effort:

1. Stop adding scope.
2. Finish or explicitly abandon the current atomic unit.
3. Run authorized deterministic verification.
4. Write a minimal checkpoint containing exact objective, authority, source hashes, changed files, tests, unresolved findings, quota/context observations, and next atomic action.
5. Freeze or clearly mark mutable state.
6. Release the writer lease.
7. End the old model session.
8. Start a fresh session with the selected fixed model and effort.

The old session must not continue writing after emitting a route request.

## Required route header

At the start of every model session, emit:

```text
ROUTE_DECISION
task_class=<class>
agent=<codex|kimi|claude>
model=<exact model or alias>
effort=<level|not_applicable>
quota_band=<GREEN|AMBER|RED>
context_percent=<number>
writer_lease=<held|not_held|read_only>
scope=<one atomic unit>
```

If the route is invalid, do no implementation. Emit `ROUTE_NEXT_SESSION` with a checkpoint path and stop.


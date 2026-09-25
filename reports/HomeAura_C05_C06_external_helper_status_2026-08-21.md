# HomeAura C05/C06 — external-helper coordination status

Updated: 2026-08-21 04:05 MSK.

## Shared input package

All helpers are instructed to read the full owner routing manual, both owner
reference PDFs, the official D185 project, native diagnostics, the clean floor
render and the rejected diagnostic render. They must first restate the rules.

Critical owner clarification: furniture/kitchen voids visible in older owner
references are not reusable. Every allowed heated part of the current project
must be covered; a void is allowed only when it is an explicit verified
exclusion.

## ChatGPT 5.6 Sol / Very high

The initial coordinate proposal was withdrawn by ChatGPT after it read the full
manual. Current honest verdict:

- C05/C06 BODY: `CANDIDATE_UNPROVEN`.
- Both POST_TRANSIT adapters: rejected for diagonal geometry and an
  unmaterialized Z change.
- No complete Point3/Eurocone continuity proof.
- No native physical coverage/length proof.
- Overall: `NO-GO_PENDING_FULL_MODEL_AND_NATIVE_VALIDATION`.

## Claude web / Claude Code CLI

The Claude Opus 5 Max web draft contains all eight attachments and the exact
prompt, but submission remains blocked by the account monthly spend limit. No
paid-limit change is authorized.

Claude Code CLI 2.1.220 became available at 01:09 MSK. A bounded read-only
Opus/max audit of the actual D185 C05/C06 finished successfully and is saved as
`reports/HomeAura_C05_C06_ClaudeCode_readonly_audit_2026-08-21.md`. Its
independent verdict is `CURRENT_OFFICIAL=NO-GO`: dominant sequential snakes,
eight S-bends inside wall solids, insufficient tangent reserves, twelve
unverified wall crossings and no physical Eurocone tails. The report is the
acceptance matrix for the future Kimi candidate, not a new design.

## Kimi K3 / High

Submitted in the dedicated chat `Координатный Solver` with all eight
attachments. It was asked for an independent alternative, exact ordered
Point3/XY arrays, BODY/TRANSIT ranges, materialized S_BEND_R80 records and an
honest GO/NO-GO. Codex has polled the unchanged active generation every five
minutes without sending duplicate prompts. Status at this update: still
processing/waiting for the first completed response after poll 36. The tab was
not reloaded, stopped or resubmitted.

## Configured multi-model API

The configured credential was reused through the local bounded broker without
printing any secret. Each provider call was a new independent one-shot session;
the broker does not create durable web chats and does not transport the image
attachments.

- Kimi Code K2.7 received the full text package and exact D185 subset. Its sole
  provider call ended `UNCERTAIN/TIMEOUT`; no response was recovered and replay
  is prohibited.
- Claude Opus 5 received a compact independent audit package. Its sole call
  likewise ended `UNCERTAIN/TIMEOUT`; no result is claimed.
- GPT-5.6 Sol completed successfully and returned a fail-closed acceptance
  checklist. It independently states that no Kimi answer can be accepted
  without exact native diagnostics and segment-level evidence.

Durable evidence:

- `reports/HomeAura_C05_C06_API_session_log_2026-08-21.md`
- `reports/HomeAura_C05_C06_API_GPT56Sol_acceptance_2026-08-21.md`

## Kimi Code scratch left before quota stop

Static read-only inspection found no candidate. The Python file is syntactically
invalid at line 222 and ends after helper definitions, with no main search,
native run, output artifact or verdict. The accompanying `source_diag_check.json`
is byte-identical to the existing D185 diagnostics, not a new result. Exact
evidence is in
`reports/HomeAura_C05_C06_KimiCode_scratch_static_audit_2026-08-21.md`.

An independent Claude Code audit of this scratch was attempted once in
Opus/max read-only mode, but the account monthly limit was reached before a
response. It was not retried and no Claude result is claimed.

## Publication boundary

No helper output is publishable until the actual candidate artifact is checked
by the native analyzer and independently reproduced by Claude Code CLI. Codex
is coordinating only and must not substitute its own unreviewed geometry.

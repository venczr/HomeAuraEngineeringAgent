# HomeAura C05/C06 — split-v3b DRAFT-hypothesis results

Date: 2026-08-21  
Status: no usable candidate; both roles terminal and non-replayable.

## C05 — GPT-5.3 Codex

- Request: `ha-c05c06/split-v3b-hyp-c05/BCF5AB29AD17/0AA200340012/gpt-5.3-codex/v1`
- Terminal result: `REJECTED / HTTP_400`
- Reserved/charged: `9,216`; no response body or digest
- No geometry was produced. The exact request is not retried.

## C06 — Claude Sonnet 4.6

- Request: `ha-c05c06/split-v3b-hyp-c06/BCF5AB29AD17/0AA200340012/claude-sonnet-4-6/v1`
- HTTP 200; latency `20,297 ms`; provider reported `16,381 + 423` tokens; local conservative charge `9,216`
- Response digest: `00174f421f71808e7fc573bdd7b65b2126875c5e37b4fd6a366f3f47a69a67ec`
- Sonnet returned a complete JSON object containing coordinates, but explicitly marked it `DRAFT_HYPOTHESIS|BLOCKED`, stated that expansion self-overlaps/degenerates, and ordered that the incomplete geometry must not be used.
- The fail-closed harness therefore rejects it before scratch materialization.

BODY remains `DRAFT|NO_GO`; SERVICE/FULL remain `NO_GO`. The next distinct lane is a compact parametric search/algorithm specification, not another direct point-array retry.

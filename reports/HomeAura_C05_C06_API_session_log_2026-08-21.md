# C05/C06 — external API session log

Date: 2026-08-21. Provider credentials were reused through the configured child-process broker; no secret value was printed or copied.

## Kimi Code K2.7

- Two local preflight attempts were rejected before any provider call because the requested output reservation exceeded the broker's 1024-token local cap. They consumed no provider tokens.
- The one actual provider request was `homeaura-c05c06-k27-sent-cd1c2dede56e474bbbac9674e403eea4`.
- It received the full owner routing rules, focused C05/C06 task, current Claude Code audit and exact D185 subset.
- Terminal broker result: `UNCERTAIN / TIMEOUT` after the bounded 60-second provider lifecycle.
- Reserved charge recorded: 15024 tokens.
- No raw response or digest exists; replay is prohibited. The request is not treated as an engineering result.

## Claude Opus 5

- Request: `homeaura-c05c06-claude-opus5-ee528e4c2ddd44b7a97d81606016b52c`.
- Scope: compact independent topology/acceptance review with the full owner-rule manual and current audit.
- Terminal broker result: `UNCERTAIN / TIMEOUT` after the bounded provider lifecycle.
- Reserved charge recorded: 4900 tokens.
- No raw response or digest exists; replay is prohibited. The request is not treated as an engineering result.

## GPT-5.6 Sol

- Request: `homeaura-c05c06-gpt56sol-99ce9ab3116c4b78af534bbd8cc70135`.
- Terminal result: HTTP 200 / `RESPONSE`.
- Charged tokens: 3368.
- Response digest: `e743cf017481f5529949da359cc73909bf8a910b4d6de943ae8bf4df80b63a50`.
- Result saved separately in `HomeAura_C05_C06_API_GPT56Sol_acceptance_2026-08-21.md`.
- Verdict: no C05/C06 candidate may be accepted without exact native diagnostics and segment-level evidence.

## Ledger continuation and owner entitlement

- The owner reported the external multi-model API as unlimited; fresh discovery exposed 35 model IDs.
- This provider-account statement is intentionally separate from Codex, browser, Claude Code and Kimi CLI quotas.
- The canonical broker ledger was continued append-only after two-stage review. Its effective local safety ceiling is 47,500,000 tokens (50,000,000 global accounting ceiling minus the protected 2,500,000 reserve).
- Ledger UUID, 68 historical rows, 999,641 spent tokens and all 160 no-replay tombstones were preserved. Formal final review: P1=0, P2=0.

## GPT-5.5 independent topology

- Request: `ha-c05c06/topology-shadow/EB1471F85DD6/558304DF7C9F/gpt-5.5/v1`.
- This is a planned independent shadow role, not a retry or copy of the still-running K3 web task.
- Terminal result: HTTP 200 / `RESPONSE` in 51,390 ms.
- Provider usage: 9,810 prompt + 1,838 completion = 11,648 charged tokens.
- Response digest: `744aeb59666247d4a9b86c382ca35c82bc588e16b8f96114b8bfe7af4ae0cb28`.
- Saved report SHA256: `0AA200340012589E4B1951FB4DD072100BB24897F8858A9DBBE65BFE309E7D93`.
- Contract validation: PASS. It proposes west/east compact bifilar territories with full allowed-area heating and no furniture/kitchen void, but keeps BODY/SERVICE/FULL at NO-GO because the authoritative finish-face domain, openings and Eurocone tails are unresolved.
- Transport caveat: the provider reported 1,838 completion tokens despite `max_tokens=1024`; therefore this endpoint is not claimed to enforce the requested output cap.

## Kimi Code K2.7 exact expansion of GPT-5.5 topology

- Request: `ha-c05c06/exact-expand/EB1471F85DD6/0AA200340012/k2.7-code/v1`.
- This was a new narrow SHA-bound BODY expansion of the saved GPT-5.5 topology, not a retry of the earlier broad K2.7 solver.
- Terminal broker result: `UNCERTAIN / TIMEOUT` after the bounded provider lifecycle.
- Reserved charge recorded: `33792` tokens.
- No raw response or digest exists; replay is prohibited.
- This request is not an engineering result and K2.7 will not be called again for the same topology/task semantics.

## GPT-5.6 Terra BODY fallback

- Request: `ha-c05c06/body-candidate/EB1471F85DD6/0AA200340012/gpt-5.6-terra/v1`.
- This was a new cross-model fallback, explicitly bound to the GPT-5.5 topology and the K2.7 timeout tombstone; it was not a replay of an absent K2.7 result.
- Terminal broker result: `UNCERTAIN / TIMEOUT` after the bounded provider lifecycle.
- Reserved charge recorded: `33792` tokens.
- No raw response or digest exists; replay is prohibited.
- Terra will not be called again for the same topology/task semantics.

## GPT-5.6 Luna fast BODY fallback

- Request: `ha-c05c06/body-fast/EB1471F85DD6/0AA200340012/gpt-5.6-luna/v1`.
- The outer command ended without stdout while the shared broker timeout stage was in progress; the canonical ledger and journal were therefore audited before any further request.
- Authoritative terminal state: `REJECTED / HTTP_502` (one journal record only), not an open or retryable request.
- Ledger row is reconciled: reserved/charged `33792`, `usage_known=false`, open reservations `0`, replay permitted `false`.
- No raw response or digest exists. Luna will not be retried for the same topology/task semantics.

## GPT-5.5 self-consistent topology-to-BODY compiler

- Request: `ha-c05c06/body-self/EB1471F85DD6/0AA200340012/gpt-5.5/v1`.
- Input tokenizer preflight: `11635` (`o200k_base`) and `13819` (`cl100k_base`), both below the 32768 broker limit.
- It was the first exact BODY role for GPT-5.5, bound to its own saved topology and all three earlier no-response tombstones.
- Terminal result under the independently approved 180-second transport: `REJECTED / HTTP_502` after approximately 138 seconds.
- Reserved/charged `33792`; no raw response or digest; replay is prohibited.
- This confirms an upstream gateway/latency limit for this high-reasoning exact-compilation path, not an input-token or local-ledger limit.

## DeepSeek V4 Pro cross-family exact BODY compiler

- Request: `ha-c05c06/body-cross/EB1471F85DD6/0AA200340012/deepseek-v4-pro/v1`.
- New independent model family; bound to the GPT-5.5 topology and four prior no-response tombstones.
- Terminal result: `REJECTED / HTTP_502` after approximately 139 seconds under the approved 180-second transport.
- Reserved/charged `33792`; no raw response or digest; replay is prohibited.
- The repeated ~138-second HTTP 502 pattern is classified as an upstream gateway/latency boundary, not a local token-budget failure.

## GPT-5.4 Mini deterministic compact BODY fallback

- Request: `ha-c05c06/body-mini/EB1471F85DD6/0AA200340012/gpt-5.4-mini/v1`.
- New fixed-split role (`split_x=18700`) bound to the GPT-5.5 topology and five no-response tombstones.
- Terminal result: `REJECTED / HTTP_502` after approximately 138 seconds.
- Reserved/charged `33792`; no raw response or digest; replay is prohibited.
- No model in the full-manual exact-compilation group produced a candidate. Any further line must use a genuinely different compact-input contract and a previously unused model, not retry these requests.

## Claim boundary

The common API is synchronous one-shot chat-completions, not a durable chat UI and not an attachment transport. Each call above was a fresh independent session. The two timeouts are not retried. The long-running web Kimi job remains separate and is still monitored without interruption.

## DeepSeek V4 Flash compact normative v2

- Request: `ha-c05c06/body-compact-v2/BCF5AB29AD17/0AA200340012/deepseek-v4-flash/v1`.
- This was a genuinely new compact-input contract: exact compact packet + saved GPT-5.5 topology + Flash-specific prompt, with six earlier terminal tombstones bound and no failed C05/C06 point arrays included.
- Use-time tokenizer preflight: `7324` (`o200k_base`) / `7291` (`cl100k_base`); conservative wrapper allowance `7836 < 8000`.
- Terminal result: HTTP 200 / `RESPONSE` in `18,828 ms`; provider usage `7300` prompt + `1` completion = `7301` charged tokens.
- Response digest: `932ae372e0d84769f1c96c96efdc36e5c46e837b24558d928bacc27460f7b424`.
- The response had an empty `message.content` and only `reasoning_content: {}`. It therefore contains no BODY candidate or engineering evidence and is rejected as unusable.
- This exact request and semantic role are terminal and will not be retried.

## Kimi Code CLI compact normative v2

- Durable task: `HA-C05C06-COMPACT-V2-KIMI-20260821-001`; task SHA-256 `58942de535ff585fbdf91a5fb90bbf5c05286b8147248cb48bb59f7f0531b7ad`.
- The queue was inspected before launch: all earlier Kimi tasks were terminal, so the one-shot worker could target this exact new READ_ONLY task without consuming an older pending task.
- Terminal result: `BLOCKED` in `4610 ms`, exit code `1`, provider HTTP 403 because the separate Kimi Code billing-cycle usage limit is exhausted.
- No stdout, BODY geometry or provider engineering response was produced. The task is terminal and will not be retried.
- This CLI quota is separate from the owner's multi-model API entitlement. Evidence report: `HomeAura_C05_C06_KimiCode_compact_normative_v2_result_2026-08-21.md`, SHA-256 `BFACB5D74FA0835C81CE5794F515C4CE7C1B4BD193AFF68C2B8DA99E2C622572`.

## GLM-5.2 compact normative v2

- Request: `ha-c05c06/body-compact-v2-glm/BCF5AB29AD17/0AA200340012/glm-5.2/v1`.
- Terminal HTTP 200 response in `60,531 ms`; response digest `a116e5b75f5ac47adb1234ca4af73220dddcae33e57d1e6867fd6eb3469b31ac`.
- GLM returned a complete valid `BLOCKED` JSON with empty arrays rather than truncating or inventing geometry.
- Exact blockers: the 1,024-token cap cannot hold both lossless arrays; R04 area/domain is contradictory; W024-W026 gates and exact Eurocone frame/tails remain unresolved.
- Saved result: `HomeAura_C05_C06_API_GLM52_compact_v2_result_2026-08-21.md`. BODY/SERVICE/FULL remain NO_GO; request is terminal and not replayable.

## MiniMax M2.7 Highspeed compact normative v2

- Request: `ha-c05c06/body-compact-v2-selfcheck/BCF5AB29AD17/0AA200340012/minimax-m2.7-highspeed/v1`.
- Terminal HTTP 200 response in `42,438 ms`; usage `7,537 + 1,024 = 8,561`; digest `58aaba90d7fef21ca05fbb2bf91400552cbf707b41b034ef4bcaad8b4cf16688`.
- Finish reason was `length`; `message.content` was empty and internal reasoning ended mid-sentence before any JSON or complete arrays.
- No reconstruction or retry is allowed. Saved result: `HomeAura_C05_C06_API_MiniMax_compact_v2_result_2026-08-21.md`; BODY/SERVICE/FULL remain NO_GO.

## Split-v3 single-circuit compiler pair

- C05 Claude Sonnet 5 request `ha-c05c06/split-v3-c05/BCF5AB29AD17/0AA200340012/claude-sonnet-5/v1` returned HTTP 200 BLOCKED; digest `92f22f708bf21ed804a3344e923955bd0ac6f391218030ae37e8cd6ef6696525`. It refused to claim cryptographic or executable geometry proof.
- C06 GPT-5.4 request `ha-c05c06/split-v3-c06/BCF5AB29AD17/0AA200340012/gpt-5.4/v1` returned HTTP 200 BLOCKED; digest `06e4e3e07f6f7c3d3796f4dafdb11545133b917044e77c47da191b1f7c1a4a5e`. It refused to compute SHA from the embedded stream and left `ph` empty.
- Both are terminal; no coordinate candidate was produced. Saved report: `HomeAura_C05_C06_API_split_v3_results_2026-08-21.md`.

## Split-v3b DRAFT-hypothesis pair

- C05 GPT-5.3 Codex request `ha-c05c06/split-v3b-hyp-c05/BCF5AB29AD17/0AA200340012/gpt-5.3-codex/v1` was terminal `REJECTED / HTTP_400`, charged `9,216`, with no response geometry or digest.
- C06 Claude Sonnet 4.6 request `ha-c05c06/split-v3b-hyp-c06/BCF5AB29AD17/0AA200340012/claude-sonnet-4-6/v1` returned HTTP 200 in `20,297 ms`, digest `00174f421f71808e7fc573bdd7b65b2126875c5e37b4fd6a366f3f47a69a67ec`.
- Sonnet supplied an array but explicitly classified it `DRAFT_HYPOTHESIS|BLOCKED`, self-overlapping/degenerate and incomplete, with a MUST NOT USE instruction. The harness rejects it before project materialization.
- Saved report: `HomeAura_C05_C06_API_split_v3b_results_2026-08-21.md`. No retry/reconstruction; BODY/SERVICE/FULL remain NO_GO.

## GPT-5.5 Pro parametric-search specification

- Request: `ha-c05c06/parametric-search-spec/BCF5AB29AD17/0AA200340012/gpt-5.5-pro/v1`.
- This was a new algorithm-specification role, not a coordinate solver retry.
- Terminal result: `REJECTED / HTTP_400`; no response body, geometry, or digest was produced.
- The request is terminal and will not be retried.

## GPT-5.5 parametric-search implementation handoff

- Request: `ha-c05c06/parametric-search-handoff/BCF5AB29AD17/0AA200340012/gpt-5.5/v1`.
- Terminal HTTP 200 response in `42,281 ms`; usage `7,759 + 1,270 = 9,029`; response digest `9a890b67a6b605f5f7272559c5d941c71ea06d6ece4b6480eb55bcaad0c1619a`.
- The returned JSON is a complete deterministic search/state-machine handoff, not pipe coordinates and not native proof. It defines territory split, exterior bands, contracting rings, centre reversal/interleaving, pruning, serialization, and the native analyze/reject loop.
- Response artifact: `reports/tmp/HomeAura_C05_C06_API_GPT55_parametric_search_handoff_response.json`, SHA-256 `5F38FBF659940000C6279A0563907CD8B3E476D61F87C5D0944291BA6708007A`.
- Human-readable handoff: `reports/HomeAura_C05_C06_API_GPT55_parametric_search_handoff_2026-08-21.md`, SHA-256 `0927C7DFF47E608908A84CE714732504B60F6B9427A9F867621327CD06ABC243`.
- This specification is now delegated to Claude Code at maximum effort for a bounded tmp-only deterministic search and independent evidence recomputation. BODY remains `DRAFT|NO_GO`; SERVICE/FULL remain `NO_GO` until actual native evidence exists.

## Claude Code Opus/max deterministic solver

- Task: `HA-C05C06-CLAUDECODE-SOLVER-20260821-001`; Claude Code `2.1.220`, `--model opus --effort max`.
- The single immutable invocation ran about 43 minutes. The outer capture reached its 2,400,000 ms timeout and exited `124`; the child stayed live briefly and later exited, but produced zero Claude scratch files and no recoverable stdout/stderr or child exit code.
- No retry was performed, and no provider/quota cause is invented.
- Terminal blocker report: `reports/HomeAura_C05_C06_ClaudeCode_solver_result_2026-08-21.md`, SHA-256 `28EE4916EB5AEF93107CF18D4809A7E199194A5379598B8AF4E850897A9E1298`.
- No candidate, native evidence, or proof was created; official D185 remains `558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4`. BODY/SERVICE/FULL remain `NO_GO`.

## K2.7-Code search-script compiler stage

- A new role was started after the Claude task terminalized: compile the saved GPT-5.5 deterministic state machine into a compact fail-closed tmp-only search script.
- This is not a coordinate-solver retry and cannot reconstruct any missing Claude output. It is bound to the frozen owner rules, compact packet, native-axis evidence, GPT-5.5 handoff, Claude blocker, and current harness.
- Immutable broker request: `ha-c05c06/search-script-compiler/BCF5AB29AD17/5F38FBF65994/k2.7-code/v1`; exactly one wire call, at-most-once/no-replay.
- Exact prompt SHA-256: `6798110DB8F9A033298629D913C48D1C6372B8A331E5F5378555C273FDDF9B5F`; conservative reservation `26,608` input plus `1,024` output tokens.
- Terminal result: `REJECTED / HTTP_502` after `99.3 s`; no provider body, response content, digest, script, partial code, or candidate was produced. The full `27,632`-token reservation was charged conservatively because usage was unknown.
- Broker-result artifact SHA-256: `52343B70026EC226DDBA0DE306E95D24E79E0AE1C3999C4FB1705C24A0AFA85B`.
- Evidence report: `reports/HomeAura_C05_C06_API_K27_search_script_compiler_result_2026-08-21.md`, SHA-256 `9BDF70874A6F5D997B6BCF7F51E6E70C6656080F2F291588320FB325917A6DAB`.
- This request is terminal and will not be retried. No harness/native run occurred; BODY/SERVICE/FULL remain `NO_GO`.

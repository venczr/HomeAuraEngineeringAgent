# HomeAura C05/C06 — GLM-5.2 compact-v2 result

Date: 2026-08-21  
Scope: independent compact normative BODY compiler; no project/code mutation.  
Status: `NO_GO_BLOCKED`.

## Transport evidence

- Request ID: `ha-c05c06/body-compact-v2-glm/BCF5AB29AD17/0AA200340012/glm-5.2/v1`
- Terminal result: HTTP 200 / `RESPONSE`
- Provider model: `am/glm-5.2`
- Latency: `60,531 ms`
- Provider-reported usage: `9,544` prompt + `404` completion tokens
- Local reserved/charged: `9,216`; usage was conservatively classified unknown
- Response digest: `a116e5b75f5ac47adb1234ca4af73220dddcae33e57d1e6867fd6eb3469b31ac`
- Replay permitted: `false`

## Engineering result

GLM returned a complete valid JSON refusal with both BODY arrays empty. It did not invent or truncate coordinates. Exact blockers:

- two complete lossless bifilar arrays could not fit the 1,024-token response cap;
- authoritative R04 finish-face area/domain remains contradictory (`15.9`, `14.4`, `16.83 m²`);
- W024/W025/W026 gate and Eurocone world-frame/tails remain unverified.

Therefore BODY remains `DRAFT|NO_GO`; SERVICE and FULL remain `NO_GO`. The response is saved byte-for-text in `reports/tmp/HomeAura_C05_C06_API_GLM52_compact_v2_response.json`.

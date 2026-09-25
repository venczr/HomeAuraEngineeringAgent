# HomeAura C05/C06 — MiniMax M2.7 Highspeed compact-v2 result

Date: 2026-08-21  
Scope: independent generate-then-self-check BODY compiler; no project/code mutation.  
Status: `NO_GO_TRUNCATED_NO_CANDIDATE`.

## Transport evidence

- Request ID: `ha-c05c06/body-compact-v2-selfcheck/BCF5AB29AD17/0AA200340012/minimax-m2.7-highspeed/v1`
- Terminal result: HTTP 200 / `RESPONSE`
- Provider model: `minimax/minimax-m2.7-highspeed`
- Latency: `42,438 ms`
- Usage: `7,537` prompt + `1,024` completion = `8,561` charged tokens
- Finish reason: `length`
- Response digest: `58aaba90d7fef21ca05fbb2bf91400552cbf707b41b034ef4bcaad8b4cf16688`
- Replay permitted: `false`

## Engineering result

`message.content` is empty. The entire completion was consumed by truncated internal reasoning and stopped mid-sentence before the required JSON or any complete `p0+runs` arrays. It is neither a BODY candidate nor engineering evidence and must not be expanded, reconstructed or retried.

The truncated reasoning also demonstrated why the next bounded stage must pin the native wall-face orientation explicitly: W022 interior normal is `+Y`, W023 interior normal is `-X`, and the native lane formula uses wall centerline plus `normal * (thickness/2 + lane*100)`.

BODY remains `DRAFT|NO_GO`; SERVICE and FULL remain `NO_GO`.

# HomeAura C05/C06 — GPT-5.5 parametric search handoff

Date: 2026-08-21  
Status: useful implementation specification; geometry and every physical claim remain unproven.

- Request: `ha-c05c06/parametric-search-handoff/BCF5AB29AD17/0AA200340012/gpt-5.5/v1`
- HTTP 200; latency `42,281 ms`
- Provider usage: `7,759` prompt + `1,270` completion = `9,029`
- Response digest: `9a890b67a6b605f5f7272559c5d941c71ea06d6ece4b6480eb55bcaad0c1619a`
- Replay permitted: `false`

The response defines a deterministic BODY-only search DSL: parameter enumeration, state transitions, hard pruning, lexicographic objectives, lossless `p0+runs` emission and a native rounded-R80 reject/advance loop. It explicitly preserves zero furniture/kitchen/equipment voids and labels BODY/SERVICE/FULL `NO_GO`, native metrics `UNPROVEN`.

Exact JSON: `reports/tmp/HomeAura_C05_C06_API_GPT55_parametric_search_handoff_response.json`.

Next bounded action: Claude Code CLI may implement and execute this specification only in `tmp/`, then independently recompute native evidence. No official project edit or acceptance follows automatically.

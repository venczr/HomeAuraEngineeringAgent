# HomeAura C05/C06 — split-v3 API results

Date: 2026-08-21  
Scope: two independent single-circuit compact compiler roles; no project/code mutation.  
Status: both terminal `BLOCKED`; no geometry candidate.

## C05 — Claude Sonnet 5

- Request: `ha-c05c06/split-v3-c05/BCF5AB29AD17/0AA200340012/claude-sonnet-5/v1`
- HTTP 200; latency `60,422 ms`; provider usage `25,185 + 671`; local conservative charge `9,216`
- Response digest: `92f22f708bf21ed804a3344e923955bd0ac6f391218030ae37e8cd6ef6696525`
- Sonnet returned a complete BLOCKED JSON. It refused to assert cryptographic verification or invent R80/contact proof without executable geometry tools.

## C06 — GPT-5.4

- Request: `ha-c05c06/split-v3-c06/BCF5AB29AD17/0AA200340012/gpt-5.4/v1`
- HTTP 200; latency `27,797 ms`; usage `7,741 + 441 = 8,182`
- Response digest: `06e4e3e07f6f7c3d3796f4dafdb11545133b917044e77c47da191b1f7c1a4a5e`
- GPT-5.4 returned a complete BLOCKED JSON. It left `ph` empty because it would not claim it had independently hashed the embedded packet.

## Next contract boundary

Both roles are terminal and will not be retried. A new role may only generate an explicitly unproven DRAFT coordinate hypothesis after the local controller verifies source hashes. The model merely echoes those controller-bound hashes; native geometry, R80, contact, wall, coverage and length checks remain downstream and unproven. BODY remains `DRAFT|NO_GO`; SERVICE/FULL remain `NO_GO`.

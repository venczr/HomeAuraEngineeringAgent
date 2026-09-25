# HomeAura C05/C06 — Opus 4.8 static-search decomposition

Recorded: 2026-08-21T07:40:31+03:00  
Authority: consultation only; no geometry, execution, evidence, or acceptance.

## Terminal provider evidence

- Request ID: `ha-c05c06/search-decomposition/BCF5AB29AD17/5F38FBF65994/claude-opus-4-8/v1`
- Model/role: `claude-opus-4-8` / `STATIC_SEARCH_IMPLEMENTATION_DECOMPOSER`.
- Action: `READ_ONLY_REVIEW` through the approved `ChildBrokerClient`.
- Wire calls: exactly `1`; canonical journal matches: exactly `1`; retry: forbidden and not attempted.
- Terminal state: `RESPONSE`, HTTP `200`, finish reason `stop`.
- Latency: `105,547 ms`; provider timeout: `180 s`; lifecycle bound: `270 s`.
- Provider response digest: `473de895a6dec4008099bc2f71e585833be27288beff8cd989a5b8a358b9c032`.
- Provider usage: prompt `56,753`, completion `1,884`, total `58,637`; broker charged the reserved `28,364` and marked usage `unknown` because reported usage exceeded the reservation contract.
- Requested output was `1,024` tokens, but the provider returned `1,884`; the endpoint did not enforce the cap. Local counts are `1,880` o200k / `1,842` cl100k tokens. This is an explicit output-contract failure.

## Exact artifacts

| Artifact | SHA-256 |
|---|---|
| Exact prompt `reports/tmp/HomeAura_C05_C06_Opus48_static_search_decomposer_exact_prompt_2026-08-21.txt` | `5CE2CAD5BD423EF9CB67EFAC2204748B41B53BAF106416E584A61577FB4FB647` |
| Prompt manifest `reports/tmp/HomeAura_C05_C06_Opus48_static_search_decomposer_prompt_manifest_2026-08-21.json` | `4F932CADF4D88849848FB62B82CC71C6A7A60BF888D9FD4EA99AEB04A3317951` |
| Exact parsed broker result, including provider body, `reports/tmp/HomeAura_C05_C06_Opus48_static_search_decomposer_broker_result_2026-08-21.json` | `A0A379F85DA1120E4A83B0DEA54722014EC0C977EBE19AE61DA8F1292954910E` |
| Exact raw assistant response JSON `reports/tmp/HomeAura_C05_C06_Opus48_static_search_decomposer_raw_response_2026-08-21.json` | `417B8F624E919921AC1D71512BF3F5829D433C07A1167BD0E2B9DDA2EBF2F928` |
| One-shot runner `tmp/c05c06_opus48_search_decomposer_20260821/invoke_broker_once.py` | `6D1C0E88ACF550684E457FDC76B50B68CC31E7D0EEF698390CC5565D74D26869` |
| Prompt assembler `tmp/c05c06_opus48_search_decomposer_20260821/assemble_prompt.py` | `0516A48CFF61B76BB7A142DE34C52FD6EDFAF197427C8D3059FCCBBDE12BABE6` |

Prompt preflight was `24,688` o200k / `26,828` cl100k plus a `512` wrapper allowance; reserved input `27,340 < 32,768`. No unsupported reasoning wire field was invented.

## Validation

The raw response is one complete parseable JSON object. Schema, request ID,
all six frozen hashes, K2.7 tombstone, BODY/SERVICE/FULL statuses and empty
blocker match exactly. Structural checks passed with 12 unique module
signatures, 7 parameter records and 16 named tests. It contains no candidate
route arrays and makes no SERVICE/FULL acceptance claim.

It is not a complete executable implementation contract. Seven gaps remain:

1. `split_x` has no exact finite value list.
2. Both ring-count parameters have no exact integer bounds.
3. The global candidate-count/runtime bound is absent.
4. No exact `enumerate_params(...)` function signature is defined.
5. Acceptance tests are names only, without fixtures and expected results.
6. The evidence reducer does not specify an independent recomputation algorithm from artifacts.
7. The required per-loop physical length interval `40,000..80,000 mm` is not explicit.

## Claim and mutation boundary

- Classification: `CONSULTATION_DRAFT / STRUCTURE_VALID / OUTPUT_CAP_FAIL / SEMANTIC_GAPS`.
- BODY: `DRAFT|NO_GO`; SERVICE: `NO_GO`; FULL/install/publication: `NO_GO`.
- The JSON may inform a later tmp-only implementation split but is not code,
  geometry, native evidence, proof, or authorization to publish.
- No further provider call was made.
- Official/source/tests changed: `0`.
- Official D185 remains SHA-256
  `558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4`.

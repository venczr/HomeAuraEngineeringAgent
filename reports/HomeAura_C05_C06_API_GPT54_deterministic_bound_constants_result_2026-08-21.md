# HomeAura C05/C06 — GPT-5.4 deterministic bound constants

Recorded: 2026-08-21 (Europe/Moscow)  
Authority: consultation draft only; no geometry, implementation, native evidence acceptance, or publication authorization.

## Canonical provider outcome

- Request ID: `ha-c05c06/search-bound-constants/BCF5AB29AD17/417B8F624E91/gpt-5.4/v1`.
- Model/role: `gpt-5.4` / `DETERMINISTIC_BOUND_CONSTANTS`.
- Action: `READ_ONLY_REVIEW` through the approved `ChildBrokerClient` only.
- Reasoning wire field: omitted. The owner did not request one for this role; official GPT-5.4 default is `none`.
- Exactly one provider call; retry/replay forbidden and not attempted. All three older request tombstones were bound as inputs and remain unchanged.
- Terminal state: `RESPONSE`, HTTP `200`, finish reason `stop`.
- Latency: `72,625 ms`; provider timeout `180 s`; lifecycle bound `270 s`.
- Provider response digest: `c1c646f418f53ce75aa15ad8d04d54553282f3fea95a6260d54a8fbaae77f6f6`.
- Reservation: input `22,229`, output `1,024`, total `23,253`.
- Reported and charged usage: prompt `19,869`, completion `1,305`, total `21,174`; usage known because the total fits inside the reservation.
- Strict output-contract finding: provider-reported completion `1,305 > 1,024`. The visible JSON itself is `722` o200k / `706` cl100k tokens and is complete. The provider usage overrun is nevertheless recorded as an output-cap failure.

Official OpenAI documentation identifies GPT-5.4 as supporting Chat Completions and a default `none` reasoning effort: <https://developers.openai.com/api/docs/models/gpt-5.4>.

## Response validation

The preserved response is one parseable JSON object with the exact required field order and identity. It contains no forbidden `SERVICE`, `PASS`, `Point3`, `p0`, or `runs` substring and no route-coordinate arrays.

Useful bounded results:

- candidate cap: `5,000`;
- global wall-clock cap: `900 s`;
- per-native-call cap: `30 s`;
- per-loop length: inclusive `40,000..80,000 mm`;
- paired spread: at most `2,000 mm`;
- exact typed `enumerate_params(...)` signature and deterministic parameter-major order are present;
- Sonnet F1 is corrected to require every independent physical/evidence gate before draft eligibility;
- Sonnet F4 explicitly recomputes continuity;
- recomputation/native disagreement is fail-closed as `REJECT_RECOMPUTE_NATIVE_MISMATCH`;
- simultaneous timeout handling uses the earliest provable breach, otherwise `REJECT_TIMEOUT_PRECEDENCE_AMBIGUOUS`.

The response correctly classified itself `BLOCKED_NO_GO` instead of inventing unsupported constants:

1. no exact finite numeric split set is authoritatively fixed by the supplied sources;
2. no exact inclusive integer ring ranges for C05/C06 are authoritatively fixed.

Therefore it is not the complete requested search contract. Classification: `STRUCTURE_VALID / BLOCKED_EXACT_BOUNDS / VISIBLE_CAP_OK / PROVIDER_COMPLETION_OVERRUN / NO_GO`.

## Exact artifacts

| Artifact | SHA-256 |
|---|---|
| Task suffix `reports/tmp/HomeAura_C05_C06_GPT54_deterministic_bound_constants_suffix_2026-08-21.txt` | `A365E74E1EF62598282396F888245DFD492BE78FE60FDB02DAE48A94CFE64C83` |
| Exact prompt `reports/tmp/HomeAura_C05_C06_GPT54_deterministic_bound_constants_exact_prompt_2026-08-21.txt` | `D3249E6435B42960E8C70EF3A5067B889DDA6E4B60F1D4DF19917AD850788435` |
| Prompt manifest `reports/tmp/HomeAura_C05_C06_GPT54_deterministic_bound_constants_prompt_manifest_2026-08-21.json` | `5C4E5FC92778BE23B9459ED3A73445FA98409CC7054631764FCE8D6D47486771` |
| Exact broker result `reports/tmp/HomeAura_C05_C06_GPT54_deterministic_bound_constants_broker_result_2026-08-21.json` | `1DD493D328681781FFF7F4A028BAABB0B391F7B227CBE21A298A0285BCBB4538` |
| Exact raw JSON `reports/tmp/HomeAura_C05_C06_GPT54_deterministic_bound_constants_raw_response_2026-08-21.json` | `F84A7F634857D214B1D60658A0879A2AE75DDA89373F1EC8825842E2232AA46D` |
| Deterministic validation `reports/tmp/HomeAura_C05_C06_GPT54_deterministic_bound_constants_validation_2026-08-21.json` | `A34C7B7484B29AF8C8C1ED4D86D5BB6EEF55104F89DDB0D11FD879193774BA4F` |
| Prompt assembler `tmp/c05c06_gpt54_deterministic_bound_constants_20260821/assemble_prompt.py` | `8DAE2AC05226EE97C6A03D6F261903D54E8EF2C527B2549C3D26056A9A296EBB` |
| One-shot runner `tmp/c05c06_gpt54_deterministic_bound_constants_20260821/invoke_broker_once.py` | `EE62950E1466CC54E4A0A1CA1D0D4A69933FA5D6D34CBF90DB313087F7FBC776` |
| Validator `tmp/c05c06_gpt54_deterministic_bound_constants_20260821/validate_response.py` | `3F5D88B81AC2D53F846B9480419E72919704F11F6720A8972C02DD8F3E337BDD` |

## Claim and mutation boundary

- Sonnet normalized oracle remains SHA-256 `1433AC2515A7A400F8EDCDA32E3D25D361B38BFEB69B1FE1CD39E23F4C930706`.
- No coordinate candidate, executable implementation, native proof, or acceptance was produced.
- BODY remains `DRAFT|NO_GO`.
- Official/source/tests changed: `0`.
- Official D185 remains SHA-256 `558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4`.

# HomeAura C05/C06 — GPT-5.6 Sol minimal numeric search contract

Recorded: 2026-08-21 (Europe/Moscow)  
Authority: consultation attempt only; no geometry, implementation, evidence acceptance, or publication authorization.

## Terminal provider result

- New role/request: `MINIMAL_NUMERIC_SEARCH_CONTRACT` / `ha-c05c06/search-contract-repair/BCF5AB29AD17/417B8F624E91/gpt-5.6-sol/minimal-v1`.
- Model: `gpt-5.6-sol`; requested top-level Chat Completions `reasoning_effort=max`; `temperature` omitted.
- Output reservation: exactly `1,024`, equal to the canonical token-ledger maximum.
- Action: `READ_ONLY_REVIEW` through the approved `ChildBrokerClient` only.
- Exactly one provider HTTPS attempt ended terminally `REJECTED / HTTP_502` after approximately 138 seconds. No provider JSON body, digest, assistant content, or usage record was returned.
- Canonical reservation `19,905 + 1,024 = 20,929` was reconciled and charged with usage unknown. Provider journal matches: exactly `1`.
- Retry/replay: forbidden and not attempted. The earlier `/v1` local OUTPUT_LIMIT tombstone remains unchanged and was not replayed.

Official OpenAI documentation supports Chat Completions and reasoning effort `max` for `gpt-5.6-sol`: <https://developers.openai.com/api/docs/models/gpt-5.6-sol>. The configured external provider returned no body, so this attempt does not establish its acceptance of the reasoning parameter.

## Exact artifacts

| Artifact | SHA-256 |
|---|---|
| Exact prompt `reports/tmp/HomeAura_C05_C06_GPT56Sol_minimal_numeric_search_contract_exact_prompt_2026-08-21.txt` | `CA0C02501729E8A40260310830F3BCCE24D5D04A9750A9EAF3A9B3035C028A42` |
| Prompt manifest `reports/tmp/HomeAura_C05_C06_GPT56Sol_minimal_numeric_search_contract_prompt_manifest_2026-08-21.json` | `91F98E25B94A48CDEAE1C8C79E0459AE15DBA9ADEA918B280EA855534F9FB318` |
| Exact broker result `reports/tmp/HomeAura_C05_C06_GPT56Sol_minimal_numeric_search_contract_broker_result_2026-08-21.json` | `E875767C3ADA3D29A6C67249EF174DB1D764B74EB9237867C89D771203B874D1` |
| No-provider-response tombstone `reports/tmp/HomeAura_C05_C06_GPT56Sol_minimal_numeric_search_contract_raw_response_absence_tombstone_2026-08-21.json` | `F513E1A0CBDC4DA8583DAB42369CF3AD7513655A0FC0406B419F42A5A8C10FC9` |
| Task suffix `reports/tmp/HomeAura_C05_C06_GPT56Sol_minimal_numeric_search_contract_suffix_2026-08-21.txt` | `160E387E985DDD06B48EF4109120310348C4E25F07FC11306D2670F98F6FCEE0` |
| One-shot runner `tmp/c05c06_gpt56_minimal_numeric_contract_20260821/invoke_broker_once.py` | `9D9D02078A16FAA074A5DAA8B78E2329EF7429D677E3A0CB68BDF332D90A484C` |
| Prompt assembler `tmp/c05c06_gpt56_minimal_numeric_contract_20260821/assemble_prompt.py` | `9897461A02F79121E711C741A06C8B449B3A92D91BB831B4787C2ECC5275B7CA` |

There is intentionally no artifact presented as a raw model response. The explicit tombstone records that no response body existed; no response was fabricated.

## Semantic and mutation result

- No compact JSON contract was produced. The seven Opus gaps remain open.
- Classification: `TERMINAL_PROVIDER_HTTP_502 / NO_RESPONSE_BODY / NO_RETRY / CONTRACT_NOT_REPAIRED`.
- BODY remains `DRAFT|NO_GO`; no downstream implementation or evidence use is authorized from this attempt.
- Official/source/tests changed: `0`.
- Official D185 remains SHA-256 `558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4`.

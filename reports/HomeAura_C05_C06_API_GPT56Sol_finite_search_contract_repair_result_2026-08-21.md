# HomeAura C05/C06 — GPT-5.6 Sol finite-search contract repair

Recorded: 2026-08-21 (Europe/Moscow)  
Authority: consultation attempt only; no geometry, implementation, evidence acceptance, or publication authorization.

## Terminal outcome

- Request ID: `ha-c05c06/search-contract-repair/BCF5AB29AD17/417B8F624E91/gpt-5.6-sol/v1`.
- Intended model/role: `gpt-5.6-sol` / `FINITE_SEARCH_CONTRACT_REPAIR`.
- Requested reasoning: top-level Chat Completions `reasoning_effort=max`; `temperature` was deliberately omitted.
- Action: `READ_ONLY_REVIEW` through the approved `ChildBrokerClient` only.
- Exactly one broker IPC request was made. It ended `REJECTED / OUTPUT_LIMIT` before provider HTTPS; provider calls: `0`.
- Retry/replay: forbidden and not attempted. No replacement request ID was created.
- Provider response, digest, usage and assistant content: absent. No token reservation row or provider-journal entry exists for this request ID, consistent with rejection before `_provider_call(...)`.

Official OpenAI documentation identifies `gpt-5.6-sol` as supporting Chat Completions and reasoning effort `max`: <https://developers.openai.com/api/docs/models/gpt-5.6-sol>. The approved broker accepts and forwards the top-level Chat Completions payload. This attempt does **not** prove that the configured external provider accepts the parameter, because the local canonical ledger rejected the reservation first.

## Exact failure boundary

- Prompt input preflight passed: `16,843` o200k / `18,995` cl100k raw tokens plus `512` wrapper reserve = `19,507 < 32,768`.
- Requested output reservation was `2,048`, matching the IPC schema ceiling in `provider_broker_runtime.py`.
- The canonical ledger has the narrower authoritative bound `MAX_OUTPUT_TOKENS = 1_024` and rejected the request before network activity.
- This is a local pre-provider contract mismatch, not a model answer and not a provider HTTP failure.

## Exact artifacts

| Artifact | SHA-256 |
|---|---|
| Exact prompt `reports/tmp/HomeAura_C05_C06_GPT56Sol_finite_search_contract_repair_exact_prompt_2026-08-21.txt` | `BD35721BEF8A63A0E3342A4F5DB83900DE26A41669482A1E3481782AF6090C12` |
| Corrected prompt manifest `reports/tmp/HomeAura_C05_C06_GPT56Sol_finite_search_contract_repair_prompt_manifest_2026-08-21.json` | `0403111E788A6EA36A3D1CBC5664C8BEA99730242F656439425D674AB1D99E09` |
| Exact broker terminal result `reports/tmp/HomeAura_C05_C06_GPT56Sol_finite_search_contract_repair_broker_result_2026-08-21.json` | `471994B758FA0E849FDF03A6BD9ACBC80BA5191EF49EA99F0F85BC945CDA10EF` |
| Explicit no-provider-response tombstone `reports/tmp/HomeAura_C05_C06_GPT56Sol_finite_search_contract_repair_raw_response_absence_tombstone_2026-08-21.json` | `2885CA50AD14A62A37B98075AF8942ED810E8535A0BDE19E6E024614FD3AB806` |
| Task suffix `reports/tmp/HomeAura_C05_C06_GPT56Sol_finite_search_contract_repair_suffix_2026-08-21.txt` | `D5CBC97F7E1EFCA966D5D8277704034DA8C7CFA607AA4266FFBB538203B0E6F5` |
| One-shot runner `tmp/c05c06_gpt56_search_contract_repair_20260821/invoke_broker_once.py` | `6AB68D08F36E025C05C52846A2035CBE860A31A8B84AFB1FF8C51CCA91F4A4BD` |
| Prompt assembler `tmp/c05c06_gpt56_search_contract_repair_20260821/assemble_prompt.py` | `012257ED6F979F06844E3947E217022D2B4E03B9AE7469A98289CFB343526C92` |
| Approved broker runtime | `B040480B29126D13D28F1F431FF76A9416C8C1B9620182297DA26E6BAC9A732B` |
| Canonical token-ledger runtime | `71C38B91A185C5674C07C490142D0B6DEB2BB530BE1AB6C16167CD0A52F9AA87` |

There is intentionally no file presented as a raw model response. The tombstone states explicitly that no provider response existed; fabricating a response file would violate the evidence boundary.

## Semantic and mutation result

- No JSON repair contract was produced. All seven Opus gaps remain open.
- Classification: `TERMINAL_LOCAL_OUTPUT_LIMIT / NO_PROVIDER_RESPONSE / NO_RETRY / CONTRACT_NOT_REPAIRED`.
- BODY remains `DRAFT|NO_GO`; no downstream implementation or evidence use is authorized from this attempt.
- Official/source/tests changed: `0`.
- Official D185 remains SHA-256 `558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4`.

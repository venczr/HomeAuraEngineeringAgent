# HomeAura C05/C06 — GPT-5.5 hypothesis enumeration bounds

Recorded: 2026-08-21 (Europe/Moscow)  
Authority: rejected search-hypothesis consultation only; no geometry, implementation, evidence acceptance, or publication authorization.

## Canonical provider outcome

- Request ID: `ha-c05c06/search-hypothesis-bounds/BCF5AB29AD17/F84A7F634857/gpt-5.5/v1`.
- Model/role: `gpt-5.5` / `HYPOTHESIS_ENUMERATION_BOUNDS`.
- Action: `READ_ONLY_REVIEW` through the approved `ChildBrokerClient` only.
- Reasoning wire field: omitted; the owner did not request a level for this role and official GPT-5.5 default is `medium`.
- Exactly one provider call; retry/replay forbidden and not attempted.
- Terminal state: `RESPONSE`, HTTP `200`, finish reason `stop`.
- Latency: `48,141 ms`; provider timeout `180 s`; lifecycle bound `270 s`.
- Provider response digest: `9e21ca5ec4b231af0be3fbe10f6bfd6e1ccad76ea429dc607ed38ca6f9507851`.
- Reservation: input `17,468`, output `1,024`, total `18,492`.
- Reported and charged usage: prompt `15,072`, completion `1,564`, total `16,636`; usage known because total fits inside the reservation.
- Output-cap failure: provider completion `1,564 > 1,024`; visible JSON is also over the hard cap at `1,042` o200k / `1,025` cl100k tokens.

Official OpenAI documentation identifies GPT-5.5 as supporting Chat Completions with default `medium` reasoning effort: <https://developers.openai.com/api/docs/models/gpt-5.5>.

## Deterministic validation

The preserved response is one parseable JSON object with exact identity and status `SEARCH_HYPOTHESIS_ONLY`. Its split formula deterministically yields the listed ascending set:

`[18300,18400,18500,18600,18700,18800,18900,19000,19100]`.

The response is rejected for implementation use because its ring derivation is internally inconsistent:

| split_x | Formula maxima C05/C06 | Emitted table maxima C05/C06 |
|---:|---:|---:|
| 18300 | 7 / 11 | 10 / 12 |
| 18400 | 8 / 11 | 10 / 12 |
| 18500 | 8 / 10 | 11 / 12 |
| 18600 | 9 / 10 | 11 / 12 |
| 18700 | 9 / 9 | 12 / 12 |
| 18800 | 10 / 9 | 12 / 11 |
| 18900 | 10 / 8 | 12 / 11 |
| 19000 | 11 / 8 | 12 / 10 |
| 19100 | 11 / 7 | 12 / 10 |

Additional defects:

- the response labels `R80 + >=200 tangent reserve` as a `240 mm` margin, while the stated arithmetic operands total `280 mm`;
- it emits the forbidden substring `service` inside enumeration values;
- both visible and provider-reported output counts exceed `1,024`.

The hard cap `5,000`, GPT-5.4 constants, four oracle corrections and native reject-loop boundary are present, but they do not cure the contradictory ring table. Classification: `STRUCTURE_VALID / SEARCH_HYPOTHESIS_ONLY / REJECT_DERIVATION_TABLE_MISMATCH / ARITHMETIC_ERROR / OUTPUT_CAP_FAIL / FORBIDDEN_SUBSTRING / NO_GO`.

This artifact must not seed the search-enumerator implementation. No local correction of its numbers is treated as model output or authority.

## Exact artifacts

| Artifact | SHA-256 |
|---|---|
| Task suffix `reports/tmp/HomeAura_C05_C06_GPT55_hypothesis_enumeration_bounds_suffix_2026-08-21.txt` | `E2E483A3A2ACF80D30F0A6FD020FC49AE47C55BD8E8B189E8E357E21F93623D6` |
| Exact prompt `reports/tmp/HomeAura_C05_C06_GPT55_hypothesis_enumeration_bounds_exact_prompt_2026-08-21.txt` | `201EEDF80EB80D8B10288A206C4681B34B67E045981D9B0149B82392951419C3` |
| Prompt manifest `reports/tmp/HomeAura_C05_C06_GPT55_hypothesis_enumeration_bounds_prompt_manifest_2026-08-21.json` | `245A1E04290A6705F9C784F6A4F404ED9231B1DED145B645C934637D8CD9F805` |
| Exact broker result `reports/tmp/HomeAura_C05_C06_GPT55_hypothesis_enumeration_bounds_broker_result_2026-08-21.json` | `E6858AA81C20D50ADCA07AB8D4C56B30E68DB8DA36CD05C1E25A17ED77DA23E1` |
| Exact raw JSON `reports/tmp/HomeAura_C05_C06_GPT55_hypothesis_enumeration_bounds_raw_response_2026-08-21.json` | `2134CFFEC502FD8260B46C7A2633FA0FB28B9C6BE249B80F0617667514A2509C` |
| Deterministic validation `reports/tmp/HomeAura_C05_C06_GPT55_hypothesis_enumeration_bounds_validation_2026-08-21.json` | `5EFFDA8CC67A2F8B99426068FF9C2E92B92A0D5264A0D3EA7F3F149D109EBBAB` |
| Prompt assembler `tmp/c05c06_gpt55_hypothesis_enumeration_bounds_20260821/assemble_prompt.py` | `C67C7387CB67F107AF0B4AC0A85FCEB54A3BAA13D3D9B69CAAB727E56F33259B` |
| One-shot runner `tmp/c05c06_gpt55_hypothesis_enumeration_bounds_20260821/invoke_broker_once.py` | `286C7B54C38AA6BA5C1186316ED40D269D69636EC7393BBB5CEA25A6A16398DC` |
| Validator `tmp/c05c06_gpt55_hypothesis_enumeration_bounds_20260821/validate_response.py` | `DCD8770F938268DEBB313245159197DBA4A7059563EAF088FB83B900DC40C1AB` |

## Claim and mutation boundary

- GPT-5.4 raw input remains SHA-256 `F84A7F634857D214B1D60658A0879A2AE75DDA89373F1EC8825842E2232AA46D`.
- No BODY point candidate, executable implementation, native proof, or acceptance was produced.
- BODY remains `DRAFT|NO_GO`.
- Official/source/tests changed: `0`.
- Official D185 remains SHA-256 `558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4`.

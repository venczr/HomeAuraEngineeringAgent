# HomeAura C05/C06 — Claude Sonnet 5 independent search-test oracle result

Recorded: 2026-08-21T07:46:48+03:00  
Authority: consultation only; no geometry, implementation, native evidence, or acceptance.

## Terminal broker outcome

- Request ID: `ha-c05c06/search-test-oracle/BCF5AB29AD17/417B8F624E91/claude-sonnet-5/v1`.
- Model/role: `claude-sonnet-5` / `INDEPENDENT_SEARCH_TEST_ORACLE`.
- Action: `READ_ONLY_REVIEW` through the approved `ChildBrokerClient`.
- Child broker invocations: exactly `1`; retry: forbidden and not attempted.
- Terminal state: `REJECTED`; safe error: `OUTPUT_LIMIT`.
- Cause: the task requested an output reservation of `2,048` tokens, which is inside the child transport schema ceiling but above the canonical token-ledger ceiling of `1,024` tokens.
- Rejection occurred before ledger reservation and before any provider call: matching canonical reservation rows `0`, matching provider-journal lines `0`, charged tokens `0`.
- Provider response/body/digest and assistant content do not exist. The explicit absence tombstone records this; it is not represented as an invented response.
- Replay is false. The immutable request ID must never be retried with a smaller output allowance.

## Exact frozen bindings supplied to the rejected job

| Input | SHA-256 |
|---|---|
| Full owner routing manual | `B2C4526B3BB8E8CF9212C9C7899C971BF6AABA980A543F50853FF75AFE058D06` |
| Compact normative v2 packet | `BCF5AB29AD17120111801C665058319474331991FFA27AB343D0707418BF5C19` |
| Native exterior-axis evidence | `C38358F795C8F64F4ADF919811ED1E1991523C42535F16D04B262A8FCF20F516` |
| GPT-5.5 parametric-search handoff | `5F38FBF659940000C6279A0563907CD8B3E476D61F87C5D0944291BA6708007A` |
| Exact Opus 4.8 decomposition raw JSON | `417B8F624E919921AC1D71512BF3F5829D433C07A1167BD0E2B9DDA2EBF2F928` |
| Official D185 | `558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4` |

The exact prompt required a JSON-only oracle/test contract with fixtures and exact outcomes, independent artifact recomputation, fail-closed negatives, finite candidate/time limits, and append-only observability. It prohibited route coordinates, executable code, implementation pseudocode, acceptance, and official/source/test mutation. No unsupported reasoning wire field was added.

## Exact local artifacts

| Artifact | SHA-256 |
|---|---|
| Task suffix `reports/tmp/HomeAura_C05_C06_ClaudeSonnet5_search_test_oracle_suffix_2026-08-21.txt` | `194A00E990CEF98E941C35AAB3A26FF4BEED794B0174B3E2FD41EE6BCD3D09F0` |
| Exact prompt `reports/tmp/HomeAura_C05_C06_ClaudeSonnet5_search_test_oracle_exact_prompt_2026-08-21.txt` | `615743D656C6DE5A6A362D939B2B274BD80E7D0A3E5FE448E7D8F51B08ED0C66` |
| Corrected prompt/preflight manifest `reports/tmp/HomeAura_C05_C06_ClaudeSonnet5_search_test_oracle_prompt_manifest_2026-08-21.json` | `F9D9E3CA547503212CA94C69B8B8FFBE46F76CE3D3B9B725B66FEE50B8F4F28B` |
| Exact broker result `reports/tmp/HomeAura_C05_C06_ClaudeSonnet5_search_test_oracle_broker_result_2026-08-21.json` | `AA1DDDA18E8233B6025C359A9589047C5879823610F8B27EA20379DC6D017989` |
| Raw-response absence tombstone `reports/tmp/HomeAura_C05_C06_ClaudeSonnet5_search_test_oracle_raw_response_absence_2026-08-21.json` | `BCE60981CBDED2B76F34EFCA309D0406E68F1385A4C8F7C3637DA26014EB55AD` |
| Prompt assembler `tmp/c05c06_sonnet5_search_test_oracle_20260821/assemble_prompt.py` | `9B6C97B569B5702DDC5228B79AB8941EE3E48CD84600B06FCCC20FF0E26B9E79` |
| One-shot runner `tmp/c05c06_sonnet5_search_test_oracle_20260821/invoke_broker_once.py` | `FB4524A9A9A05BCCBE50559D58C80EDD50B97773F02BE0701419DB52ED973B1B` |

Prompt preflight was `14,019` o200k / `16,167` cl100k tokens plus a `512` wrapper allowance, so the input reservation was valid at `16,679 < 32,768`. The failed dimension was solely the canonical output-reservation ceiling.

## Claim and mutation boundary

- Classification: `TERMINAL_PRE_PROVIDER_REJECTION / NO_ORACLE_RESPONSE / NO_REPLAY`.
- No oracle contract, fixtures, reducer, limit policy, code, candidate geometry, or evidence was obtained.
- BODY remains `DRAFT|NO_GO`; no downstream gate may treat this attempt as evidence.
- No official or source/test write was performed by this task.
- Official D185 remains SHA-256 `558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4`.

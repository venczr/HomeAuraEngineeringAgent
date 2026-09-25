# HomeAura C05/C06 — Claude Sonnet 5 minimal search-oracle matrix

Recorded: 2026-08-21T07:55:19+03:00  
Authority: consultation draft only; no geometry, implementation, native evidence, or acceptance.

## Canonical provider outcome

- Request ID: `ha-c05c06/search-test-oracle/BCF5AB29AD17/417B8F624E91/claude-sonnet-5/minimal-v1`.
- Model/role: `claude-sonnet-5` / `MINIMAL_SEARCH_ORACLE_MATRIX`.
- This was a genuinely new narrow task. The older `/v1` `OUTPUT_LIMIT` request remains tombstoned and was not replayed.
- Action: `READ_ONLY_REVIEW` through the approved `ChildBrokerClient`; unsupported reasoning field omitted.
- Wire calls: exactly `1`; canonical ledger rows: exactly `1`; canonical journal lines: exactly `1`; retry: forbidden and not attempted.
- Terminal state: `RESPONSE`, HTTP `200`, finish reason `stop`.
- Latency: `136,218 ms`; provider timeout: `180 s`; lifecycle bound: `270 s`.
- Provider response digest: `274821c8a3f61cb4d469b7b23691c34ebcd5f95f1171b263688bee4574526c74`.
- Reservation/charge: input `16,661`, output `1,024`, total `17,685`; charged `17,685`; reconciled. Usage is marked unknown because provider-reported usage exceeded the reservation contract.
- Provider usage: prompt `44,800`, completion `1,050`, total `45,850`. The provider exceeded requested `max_tokens=1,024`; local raw counts are `1,046` o200k / `1,022` cl100k tokens. This is an explicit output-cap contract failure.

## Exact SHA-bound inputs

| Input | SHA-256 |
|---|---|
| Full owner routing manual | `B2C4526B3BB8E8CF9212C9C7899C971BF6AABA980A543F50853FF75AFE058D06` |
| Compact normative v2 packet | `BCF5AB29AD17120111801C665058319474331991FFA27AB343D0707418BF5C19` |
| Native exterior-axis evidence | `C38358F795C8F64F4ADF919811ED1E1991523C42535F16D04B262A8FCF20F516` |
| GPT-5.5 parametric-search handoff | `5F38FBF659940000C6279A0563907CD8B3E476D61F87C5D0944291BA6708007A` |
| Exact Opus 4.8 decomposition raw JSON | `417B8F624E919921AC1D71512BF3F5829D433C07A1167BD0E2B9DDA2EBF2F928` |
| Older `/v1` absence tombstone | `BCE60981CBDED2B76F34EFCA309D0406E68F1385A4C8F7C3637DA26014EB55AD` |
| Official D185 | `558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4` |

## Response validation

The raw assistant content was preserved byte-for-byte. It is not directly parseable as the required JSON array because Sonnet wrapped it in a `json` Markdown fence. A deterministic fence-only normalization produced one parseable array with:

- 11 fixtures, within the required 8..12 range;
- four exact keys per fixture, unique IDs, valid field types, nonempty recomputation assertions, and allowed expected-code vocabulary;
- no forbidden `SERVICE`, `PASS`, or `Point3` substring and no route coordinate arrays.

The normalized matrix is useful only as test-design input. It has four substantive gaps:

1. F1 labels a draft eligible without independently recomputing every physical, coverage, length, contact, and immutability gate.
2. F4 does not explicitly recompute continuity.
3. No fixture isolates disagreement between independent recomputation and native diagnostics.
4. F11 exceeds both global and per-native timeouts but provides one terminal code, leaving precedence ambiguous.

Therefore strict classification is `DRAFT_MATRIX_ONLY / RAW_FORMAT_FAIL / OUTPUT_CAP_FAIL / SEMANTIC_GAPS`. It is not a complete oracle and cannot authorize a machine-precheck result.

## Exact local artifacts

| Artifact | SHA-256 |
|---|---|
| Task suffix `reports/tmp/HomeAura_C05_C06_ClaudeSonnet5_minimal_search_oracle_matrix_suffix_2026-08-21.txt` | `6691AD2BD84B154529D35109A6E469C670D6C44FF73585D69E461C8026EEECF5` |
| Exact prompt `reports/tmp/HomeAura_C05_C06_ClaudeSonnet5_minimal_search_oracle_matrix_exact_prompt_2026-08-21.txt` | `9E2810E51C3EAF3B341978719FF0A84AB0D6C5E0808E92F8085A5544947EB611` |
| Prompt manifest `reports/tmp/HomeAura_C05_C06_ClaudeSonnet5_minimal_search_oracle_matrix_prompt_manifest_2026-08-21.json` | `5C38D70AD35D5B584B9B25A624EB77FA0D2CE6FC486C51933004C694025150D7` |
| Exact broker result `reports/tmp/HomeAura_C05_C06_ClaudeSonnet5_minimal_search_oracle_matrix_broker_result_2026-08-21.json` | `1A34D69337F51ABA8F88FEFB77C4E3633BC9193479172DF7573B1980E40C2052` |
| Exact raw assistant response `reports/tmp/HomeAura_C05_C06_ClaudeSonnet5_minimal_search_oracle_matrix_raw_response_2026-08-21.json` | `3D41330636CD76BBBFB96FFB01AA8EC2E85674C44DE29DE88C792FEDD3D31539` |
| Deterministically normalized JSON `reports/tmp/HomeAura_C05_C06_ClaudeSonnet5_minimal_search_oracle_matrix_normalized_response_2026-08-21.json` | `1433AC2515A7A400F8EDCDA32E3D25D361B38BFEB69B1FE1CD39E23F4C930706` |
| Validation result `reports/tmp/HomeAura_C05_C06_ClaudeSonnet5_minimal_search_oracle_matrix_validation_2026-08-21.json` | `D52C6CE2C5001BD9069F7FD2A7E1D92353A37D0A3E4B3E99FE4BEDC21F203A56` |
| Prompt assembler `tmp/c05c06_sonnet5_minimal_search_oracle_matrix_20260821/assemble_prompt.py` | `046E75EF40BFE59A0D85C9C394FBEDE8106DAC3A2C3956E0EE01BE5498910221` |
| One-shot runner `tmp/c05c06_sonnet5_minimal_search_oracle_matrix_20260821/invoke_broker_once.py` | `DA0C86D12C28455F7E1E2330F13DF4D68FD00C46B7E840ECDD9023018A8E4669` |
| Deterministic validator `tmp/c05c06_sonnet5_minimal_search_oracle_matrix_20260821/validate_response.py` | `245BC6218C2807A0F5925BDFC1F65398B2D9F19A541C1159E6FFDF8058D31E44` |

## Claim and mutation boundary

- No retry or corrective provider call was made.
- No coordinate candidate, implementation, native proof, or acceptance was produced.
- BODY remains `DRAFT|NO_GO`.
- No official or source/test write was performed by this task.
- Official D185 remains SHA-256 `558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4`.

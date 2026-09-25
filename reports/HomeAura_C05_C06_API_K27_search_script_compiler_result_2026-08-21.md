# HomeAura C05/C06 — K2.7-Code search-script compiler result

Date: 2026-08-21  
Role: deterministic GPT-5.5 BODY-search state-machine compiler, not a coordinate-solver retry.

## Terminal result

- Request ID: `ha-c05c06/search-script-compiler/BCF5AB29AD17/5F38FBF65994/k2.7-code/v1`
- Model: `k2.7-code`
- Action: `READ_ONLY_REVIEW` through the approved `ChildBrokerClient` only.
- Wire calls: exactly `1`; journal matches for this request ID: exactly `1`.
- Terminal broker status: `REJECTED`.
- Safe provider error: `HTTP_502`.
- Provider timeout: `180 s`; child lifecycle bound: `270 s`.
- Charged reservation: `27,632` tokens; provider usage was not available.
- Provider body/content/digest: absent.
- Replay permitted: `false`; no retry was attempted or is allowed.

This is a terminal upstream failure with no assistant response. It contains no
script, patch, coordinates, candidate, diagnostic, or engineering evidence.
No partial output exists to reconstruct. Therefore nothing was materialized or
executed, and the existing harness/native analyzer was not invoked for this
stage.

## Frozen input and preflight evidence

- Exact prompt: `reports/tmp/HomeAura_C05_C06_K27_search_script_compiler_exact_prompt_2026-08-21.txt`
  - SHA-256: `6798110DB8F9A033298629D913C48D1C6372B8A331E5F5378555C273FDDF9B5F`
  - `90,340` characters / `100,530` UTF-8 bytes.
  - Local tokenizer preflight: `23,947` o200k tokens; `26,096` cl100k tokens;
    `512` wrapper reserve; broker input reservation `26,608 < 32,768`.
- Prompt manifest: `reports/tmp/HomeAura_C05_C06_K27_search_script_compiler_prompt_manifest_2026-08-21.json`
  - SHA-256: `363698C2A32DC6B20C062123206D3F01C7DA915BDFD70521BC3D0FBBEDCBC553`.
- Exact parsed broker result: `reports/tmp/HomeAura_C05_C06_K27_search_script_compiler_broker_result_2026-08-21.json`
  - SHA-256: `52343B70026EC226DDBA0DE306E95D24E79E0AE1C3999C4FB1705C24A0AFA85B`.
- One-shot runner: `tmp/c05c06_k27_search_compiler_20260821/invoke_broker_once.py`
  - SHA-256: `C7B718CAAA230503C437D9973018028646D7D39A1F60ECAAF81DA3FEC4356AB6`.
- Approved broker runtime was verified immediately before the call:
  `B040480B29126D13D28F1F431FF76A9416C8C1B9620182297DA26E6BAC9A732B`.

The prompt contained the full owner manual plus the compact normative packet,
native exterior-axis evidence, GPT-5.5 topology, GPT-5.5 parametric handoff,
Claude Code terminal blocker, harness README and current evaluator source. It
explicitly required the helper to encode the owner-rule restatement, including
zero kitchen/furniture/equipment voids in current R04, and permitted only one
complete Python script or a fail-closed `BLOCKED` JSON. The provider returned
neither.

## Mutation and claim boundary

- Official D185 remains unchanged at SHA-256
  `558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4`.
- Official/source/test files changed: `0`.
- Generated K2.7 script: absent.
- Scratch candidate/native evidence: absent.
- BODY: `DRAFT|NO_GO`.
- SERVICE: `NO_GO`.
- FULL/install/publication: `NO_GO`.

## Next genuinely different unused model/role proposal

Do not call it without a new root handoff. If `claude-opus-4-8` is still in the
live advertised catalog, use it once under the new role
`STATIC_SEARCH_IMPLEMENTATION_DECOMPOSER`: it should not generate coordinates
or retry K2.7 compilation, but return a compact, exact function/invariant split
for local implementation and independent testing of the GPT-5.5 state machine.
Bind it to the K2.7 HTTP-502 tombstone and keep all BODY/SERVICE/FULL claims
NO-GO. If that model is not currently advertised, perform no substitute call
without a newly authorized model identity.

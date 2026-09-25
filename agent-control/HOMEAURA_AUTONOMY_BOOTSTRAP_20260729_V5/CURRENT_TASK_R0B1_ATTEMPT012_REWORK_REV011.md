# CURRENT TASK — R0B1 ATTEMPT-012 REVIEW-FAIL REWORK → REV-011

Issued by: KIMI_PRIMARY_WRITER under owner direction "Продолжай как считаешь нужным, решай сам" (2026-07-31 ~02:50 MSK).
Precedent: identical in shape to CURRENT_TASK_R0B1_ATTEMPT011_REWORK_REV010.md (REWORK_CURRENT_STAGE).

## Cause

attempt-012 FINALIZED (2026-07-30T23:18:09Z, transaction 6fb497e18efa9b0587863b5b957ca16fdd4c0ac2e10c310eefc715fd367b7e57, exactly 1 provider request / 1 credential read / 0 retries, hash-chained markers verified 21/21). The independent external Claude review (PREAUTH_R0B1_ATTEMPT_012_CLAUDE_REVIEW_001, opus, read-only, exit 0) returned **FAIL: 1 BLOCKER, 4 MAJOR, 10 MINOR** (evidence sha 26a3b5cc5c965937ad31e38e605e0c75de443c0d982c407384d871b85c84fb17).

attempt-012 is therefore **content-rejected**: permanently preserved immutable, never modified, never a REUSE source, R0B1 NOT accepted, no claim, no retry of the transaction. The rev-010 pipeline itself is proven sound — the defect is provider content dishonesty that the tightened gates must reject deterministically BEFORE materialization.

## Defects to close (review findings → rev-011 gates)

BLOCKER/MAJOR (must all become deterministic InvalidDataException = FAILED_PROVEN):
1. review/72 fabricated final pass (`final_pass_invoked:true`, ACCEPT verdict, invented independent_reviews) → new gate TARGET_REVIEW_FABRICATION: strict-parse review/72; require claude.final_pass_invoked == false (boolean); forbid substrings 'ACCEPT_STATIC_PROPOSAL', 'independent_reviews', 'review_finished_utc' in review/71 and review/72; require marker 'EXTERNAL_REVIEW_PENDING' in review/71.
2. Temporal impossibility (2026-07-29T00:00:00Z fabricated timestamps in 4 files) → new gate TARGET_PLACEHOLDER_TIMESTAMP: regex `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}` forbidden in design/30, evidence/41, review/71, review/72, 80_result; require literal 'TIMESTAMP_CALLER_RECORDED' in design/30 and 80_result (real timestamps are caller-recorded in DERIVED evidence/60 and markers).
3. Vacuous test claims (18/18 PASS on unperformable tests) → new gate TARGET_TEST_RESULTS_HONEST: strict-parse evidence/41; require execution_performed == false, summary.executed == 0, summary.passed == 0; require marker 'EXECUTION_DEFERRED'.
4. (from rev-010 candidate review MINOR 1) TARGET_STALE_ATTEMPT asymmetry → apply the full stale-check set to BOTH binding and result.
5. (rev-010 MINOR 2) TARGET_REVIEW_EVIDENCE substring matching → strict-parse review/72 with StrictJsonParser; keep substring scan as redundant second layer.

MINOR:
6. In-attempt hash chain covers 11/18 → extend DerivedArtifacts.ContentIndexPaths with review/70, review/71, review/72, 80_R0B1_AUTHORING_RESULT.json (15 entries; 50/60/61 still self-excluded).
7. master-hash binding missing from 80_result → TARGET_MASTER_LINEAGE extended: result must also contain both masterV3/masterV31.
8. DerivedArtifacts manifest attempt literal 12 → derive from ExecutionContext.DestinationName (REQUIRED now: attempt-013).
9. Packet wording 'action-count cap 32' → 'at most 32 final files'; 'advisory_report at most 4096 characters'.
10. Helper hardening → packet requirements: case-consistent mode dispatch, PATH_SHAPE must reject leading '\' and '/', 64-hex digest-shape validation for sha parameters, PATH_SHAPE+length validation for $AcceptedSnapshotManifest.
11. REUSE'd design/33 stale attempt-010 self-reference → documented residual (REUSE bytes pinned, cannot change); note in packet/receipts.

## Renumbering (rev-010 → rev-011)

- destination attempt-012 → attempt-013 everywhere (config destination_name, ExecutionContext.DestinationName, CONFIG_DESTINATION, proposal CREATE_FIRST_UNUSED_ATTEMPT_013, expectedDestination, SemanticTargetValidator literals, Build-Candidate.ps1, tests, packet).
- proposal prohibited_actions: + MODIFY_ATTEMPT_012 (now MODIFY_ATTEMPT_010/011/012).
- SemanticTargetValidator: require 'attempt-013' in binding/result/70/72; forbid attempt-010/011/012 and "attempt":10/11/12, attempt=10/11/12.
- New pinned table Attempt012Inventory (18 files, from derivation.v4.1.json final_sha256 — authoritative): DELTA_OUTPUT_IDENTICAL and DELTA_STALE_COPY check BOTH attempt-010 and attempt-012 tables; REUSE still reads only the 4 pinned attempt-010 design files (design/31-34 are byte-identical in 010/011/012).
- Build-Candidate.ps1: attempt-012 must exist immutable (18-file identity vs new pinned table), attempt-013 must be absent, rev-010 claim integrity pin (21cceed0...claimed.json {"state":"CLAIMED"}), ReworkTaskPath → this document, packet updated (new honesty requirements), baseline/receipt wording rev-011.
- Delta schema stays homeaura.r0b1.helper-candidate-delta.v4.2 (no structural change; gates are materializer-side).

## Cycle (unchanged, authorized)

implement → fake-only tests (add negatives for every new gate + renumber existing) → deterministic double-build byte-identical → 3 scoped audits → freeze → one read-only Claude review (visible PS window) → findings disposition → REV011_OWNER_CONFIRMATION_GATE_001 for attempt-013 → STOP at owner gate (hash-bound owner confirmation still mandatory; Kimi never self-signs).

Forbidden throughout: provider requests, credential reads, claim/attempt-013 creation, modifying attempt-010/011/012 or rev-004/006/008/009/010, subagents/AgentSwarm, Codex (PAUSED_LIMIT_RESERVE).

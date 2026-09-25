# HOMEAURA R0B1 attempt-011 decision and rev-010 task

## Decision

`REWORK_CURRENT_STAGE`

`attempt-011` is immutable rejected evidence. It must not be deleted, renamed, overwritten, accepted, or used to open R0B2.

This task authorizes local, reversible authoring and validation of `candidate-rev-010` only. It does not authorize a production provider request, Credential Manager read, claim, canonical `attempt-012`, R0B1 acceptance, or a later-stage transition.

## Exact evidence

- Master V3 SHA-256: `7e12b93fbab892bf6421163b552dc70f6e78bdb27732cf3957d299bbe4b9865f`
- Master V3.1 SHA-256: `d3a85afbb8c0b085e25739257033f6dc3bb28ae96965c4118c20b8c146eb2820`
- `attempt-010`: 18 files, 85,996 bytes, immutable and NOT_ACCEPTED.
- `attempt-011`: 18 files, 85,996 bytes; all 18 files are byte-identical to `attempt-010`.
- `attempt-011/80_R0B1_AUTHORING_RESULT.json` SHA-256: `2596f4c5650cb84c2b0504889155f0daf00c3d5ba10f99843dee6e4f465c8331`
- Rev-009 derivation SHA-256: `c637e3795e5dad74759f40521d2532add1feea81897a5bdd01f8af2f1cf93891`; every action is `REUSE`.
- Rev-009 final-package manifest SHA-256: `f404fb968c973e75a59eeaa87b60465bc695db4f76ae7ef0ef5403b89ec84491`.
- Rev-009 transaction is FINALIZED and consumed. Never retry or resume it.
- `attempt-012` is absent and is the next first-unused monotonic destination.

## Acceptance blockers found by exact readback

1. The copied binding/result/manifests still say `attempt=10`, point to `attempt-010`, and bind only Master V3.
2. Master V3.1 lineage is absent.
3. Both helper sources remain `SCHEMA_ONLY_NON_EXECUTABLE_PROPOSAL` with unconditional denial; the package is not the required installable-but-not-executed helper.
4. Embedded Claude evidence is the old attempt-010 waiver (`final_pass_invoked=false`), not a mandatory exact-byte PASS of the new attempt.
5. Rev-009 Claude PASS reviewed the pre-execution materializer candidate, not the resulting `attempt-011`.
6. The output provenance remains old Codex-authored bytes and does not establish a new independent package.
7. Rev-009 validation explicitly accepted an all-`REUSE` delta and performed only structural postchecks.

## Rev-010 implementation requirements

1. Create a new isolated `candidate-rev-010`; preserve candidate-rev-009 and every prior artifact byte-for-byte.
2. Set the future destination to `attempt-012` and prove it remains absent during all fake-only tests.
3. Keep the consumed rev-009 claim, transaction, spool, derivation, and `attempt-011` permanently immutable.
4. Reject an all-`REUSE` response as deterministic `FAILED_PROVEN` before canonical materialization.
5. Reject any proposed final package whose complete inventory is byte-identical to attempt-010 or attempt-011.
6. Add semantic target validation before materialization:
   - exact attempt number and destination root;
   - exact V3 and V3.1 hashes;
   - new derivation/provenance;
   - installable-but-not-executed helper state;
   - no `SCHEMA_ONLY_NON_EXECUTABLE_PROPOSAL`, unconditional-deny implementation, old waiver, old review, or stale attempt path;
   - locally recomputed content index, snapshot/package manifests, sizes, and hashes.
7. Require a non-empty mandatory replacement/create set for target-specific binding, provenance, tests/results, manifests, review request/evidence state, and authoring result. Reuse helper source bytes only if exact requirements analysis proves they are already the required installable implementation; current exact bytes do not satisfy that condition.
8. Ensure review evidence for the new canonical attempt cannot be copied from a parent. The final independent Claude review must inspect the exact newly materialized/frozen bytes; design the evidence boundary without circular self-hashing.
9. Add deterministic fake-only negative tests for:
   - all-REUSE rejection;
   - byte-identical output rejection;
   - stale attempt number/path;
   - missing V3.1 lineage;
   - schema-only/unconditional-deny source;
   - copied old review waiver/evidence;
   - stale content/snapshot/package hashes;
   - occupied attempt-011 and absent attempt-012;
   - zero production provider requests and zero real credential reads.
10. Run all tests, deterministic double-build, and three scoped local audits. Freeze exact rev-010 bytes.
11. Launch Claude Code once in a visible PowerShell window as a read-only reviewer of the stable rev-010 package and these exact blockers.
12. If Claude reports BLOCKER/MAJOR, correct only within an explicitly authorized monotonic successor; do not silently mutate frozen rev-010.
13. If Claude PASSes with zero BLOCKER/MAJOR, prepare a fresh hash-bound owner gate for one future attempt-012 materialization and stop only at that genuine gate.

## Continuous behavior

Do not stop after reporting implementation, tests, audits, freeze, or review completion. Immediately continue to the next authorized item. Do not ask the owner general technical questions. Stop only at the fresh owner confirmation gate or an uncorrectable BLOCKER/MAJOR.

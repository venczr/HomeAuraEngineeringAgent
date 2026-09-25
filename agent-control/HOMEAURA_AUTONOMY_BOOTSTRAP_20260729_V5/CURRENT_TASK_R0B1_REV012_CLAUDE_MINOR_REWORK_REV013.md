# CURRENT_TASK_R0B1_REV012_CLAUDE_MINOR_REWORK_REV013

TASK_ID: HA-AUTO-R0B1-REV013-CLAUDE-MINOR-REWORK-AND-BUILD-014
DECISION: AUTHORIZE_NEW_REVISION_FOR_MANDATORY_MINOR_CLOSURE
EXECUTOR: Kimi K3 Code (TEMPORARY_IMPLEMENTATION_WRITER)
STAGE: HA-AUTO-R0B1
FROZEN_PARENT: candidate-rev-012 (freeze SHA-256 9edac08aad118b85d81e6367f347cbc8731c4fb5d8ad19c881a6d1a2e81eb901, aggregate a036a645d94878da82b29361c63eaa7638eb73a11461e2cf9dd13c34c11ab622)
NEW_CANDIDATE: candidate-rev-013
PLANNED_IMMUTABLE_ATTEMPT: attempt-013

## Recorded state

- candidate-rev-012 remains frozen and immutable; no byte of it is modified.
- rev-012 independent Claude verdict is PASS_WITH_MINOR (BLOCKER 0 / MAJOR 0 / MINOR 3 / INFO 4), raw SHA-256 afc13be251204523e3386d3d933414a53842bac6b6f6e7c4a95b5192e0b49e95, normalized evidence JSON 3e940915e3b7d704a5617511ed756ce81f88c7565f7c14a0f34493433d08e4c3, TXT 2508a58a8344321ad560757cf58f87a274b6e541340f9652781385c10ca295d1.
- rev-013 supersedes rev-012 only as a candidate; rev-012 is not accepted as R0B1.
- Planned immutable destination remains attempt-013 (candidate-rev-013 is NOT attempt-013).
- No owner gate exists; no claim exists; attempt-013 does not exist; R0B1 is not accepted.
- No materialization is authorized by this document. The exact future owner-gate action CREATE_FIRST_UNUSED_ATTEMPT_013 is required later and is not authorized, consumed or executed.
- Underlying accepted source lineage rev-010 is retained.

## Finding-to-change mapping

### MINOR-REV012-001 REVIEW71_COMPLETION_TOKENS_NOT_SYMMETRIC (CONFIRMED_MINOR, MANDATORY_REV013_FIX)

- Source path: src/HomeAuraR0B1Materializer.cs, SemanticTargetValidator (rev-012 lines 1185-1187 and 1209-1216).
- Affected behavior: the four forbidden completion tokens were enforced on review/70 and review/72 but only FINAL_VERDICT was enforced on review/71, the semantic review-result artifact.
- Deterministic remediation: apply the full token set (FINAL_VERDICT, ACCEPT_STATIC_PROPOSAL, independent_reviews, review_finished_utc) case-insensitively to review/71 as well; review/71 must still contain EXTERNAL_REVIEW_PENDING. The pre-existing plain TARGET_REVIEW_FABRICATION rejection for a FINAL_VERDICT token in review/71 is preserved unchanged so the retained rev-011 test keeps passing; the other three tokens on review/71 raise the new stable identifier.
- Stable failure identifier: TARGET_REVIEW_FABRICATION:review71_forbidden_token.
- Isolated test: rev013_review71_forbidden_token_rejected — review/71 contains EXTERNAL_REVIEW_PENDING plus "recommendation: ACCEPT_STATIC_PROPOSAL" and no FINAL_VERDICT; asserts exactly TARGET_REVIEW_FABRICATION:review71_forbidden_token.
- Generated evidence change: semantic-gate descriptions list review/71 token symmetry.
- Acceptance criterion: negative test reaches the exact new failure ID; no earlier unrelated gate masks the branch.

### MINOR-REV012-002 REVIEW72_NESTED_VERDICT_KEYS_NOT_REJECTED (CONFIRMED_MINOR, MANDATORY_REV013_FIX)

- Source path: src/HomeAuraR0B1Materializer.cs (rev-012 lines 1195-1208, flat root/claude key loops).
- Affected behavior: verdict / final_verdict keys were rejected only at the review/72 root and the direct claude child; depth-2+ nesting escaped.
- Deterministic remediation: bounded recursive scan (explicit max depth 32, explicit max visited nodes 4096, fail closed TARGET_REVIEW_FABRICATION:review72_unbounded when either bound is exceeded) rejecting verdict and final_verdict case-insensitively at any depth. Root-level and direct-claude-level keys keep their existing detailed identifiers (review72_root_verdict, review72_root_final_verdict, review72_claude_verdict, review72_claude_final_verdict); any other location raises the nested identifiers. claude.final_pass_invoked exactly false remains mandatory.
- Stable failure identifiers: TARGET_REVIEW_FABRICATION:review72_nested_verdict, TARGET_REVIEW_FABRICATION:review72_nested_final_verdict, TARGET_REVIEW_FABRICATION:review72_unbounded.
- Isolated tests: rev013_review72_nested_verdict_rejected (claude.summary.verdict), rev013_review72_nested_final_verdict_rejected (metadata.final_verdict), rev013_review72_array_verdict_rejected (verdict key inside an array-contained object); every fixture retains final_pass_invoked=false so the nested-key gate is the isolated rejection reason.
- Generated evidence change: gate descriptions state bounded recursive rejection.
- Acceptance criterion: all three tests assert their exact nested failure IDs; the four rev-012 per-location tests keep passing unchanged.

### MINOR-REV012-003 STALE_ATTEMPT_STRUCTURED_SCAN_HAS_PARSE_AND_RECURSION_GAPS (CONFIRMED_MINOR, MANDATORY_REV013_FIX)

- Source path: src/HomeAuraR0B1Materializer.cs (rev-012 lines 1147-1161, catch-and-continue plus root-only field scan).
- Affected behavior: a strict-parse failure of binding/00 or the authoring result silently skipped the structured stale-attempt check, and only root-level attempt / target_attempt / destination_attempt fields were inspected.
- Deterministic remediation: binding/00 and the authoring result are required JSON; a strict-parse failure is now rejected fail-closed with TARGET_STALE_ATTEMPT:unparsed (no silent catch-and-continue remains for required current-target JSON). The structured scan is recursive over nested objects and arrays for the keys attempt, target_attempt and destination_attempt, rejecting numeric or string values 10/11/12. Whitespace-tolerant textual checks are preserved unchanged. No broad historical exemption: these two documents are fresh provider-authored content; historical references exist only inside pinned immutable blocks that are not scanned by this gate.
- Stable failure identifiers: TARGET_STALE_ATTEMPT:unparsed (parse failure), TARGET_STALE_ATTEMPT (any stale reference, retained).
- Isolated tests: rev013_stale_attempt_nested_target_rejected (config.target_attempt = 12), rev013_stale_attempt_array_destination_rejected (destination_attempt "11" inside an array object), rev013_stale_attempt_unparsed_rejected (malformed binding carrying a stale target field rejected as TARGET_STALE_ATTEMPT:unparsed).
- Generated evidence change: gate descriptions state fail-closed parse and recursive scan.
- Acceptance criterion: all three tests assert their exact failure IDs; all retained stale-attempt tests keep passing.

### INFO-REV012-001 TEST_RUNNER_DOES_NOT_EMIT_SKIPPED_FIELD (FIX_OPPORTUNISTICALLY_IN_REV013)

- Source path: tests/MaterializerTests.cs result object; Build-Candidate.ps1 receipt validation.
- Remediation: the runner emits explicit "skipped": 0 and total = passed + failed + skipped; Build-Candidate.ps1 requires skipped = 0 in addition to failed = 0 and the exact registered count.
- Acceptance criterion: build validation fails if skipped is nonzero or absent.

### INFO-REV012-002 CLAUDE_OUTPUT_CONTRACT_CONFLICT (FIX_OPPORTUNISTICALLY_IN_REV013)

- Source path: Build-Candidate.ps1 generated review/CLAUDE_READ_ONLY_REVIEW_INSTRUCTIONS.txt.
- Remediation: one unambiguous rev-013 review contract — exactly one begin marker HOMEAURA_CLAUDE_REV013_INDEPENDENT_REVIEW_BEGIN, exactly one end marker HOMEAURA_CLAUDE_REV013_INDEPENDENT_REVIEW_END, one structured review block inside, no text outside the markers; normalized JSON evidence is created later by the transport/evidence recorder (Kimi), not by the reviewer. The competing raw JSON-only requirement is removed. The future rev-013 transport wrapper must follow the same frozen contract.
- Acceptance criterion: generated instructions contain no JSON-only response requirement and exactly one output contract.

### INFO-REV012-003 / INFO-REV012-004

Transport/environment observations; no candidate change; preserved as historical evidence only.

## Revision and lineage adaptation

- Build-Candidate.ps1 adapted to revision 13: candidate-rev-013 root, candidate-rev-013.claims, runtime identity HA-R0B1-R9-013, revision = 13, supersedes_revision = 12, recovery-revision-013-baseline.json.
- Pinned and hash-verified at build: rev-012 freeze SHA-256, rev-012 aggregate, rev-012 Claude raw review, rev-012 normalized evidence JSON/TXT, rev-012 verdict PASS_WITH_MINOR with counts 0/0/3/4, and this rework design document.
- Generated rev-013 evidence states: rev-012 is frozen and permanently preserved; rev-012 is not accepted as R0B1; rev-013 is an unfrozen rework candidate; rev-013 Claude review is pending; owner gate does not exist; claim does not exist; attempt-013 does not exist.
- The exact future owner-gate action CREATE_FIRST_UNUSED_ATTEMPT_013 is retained and stated as required later but not authorized, consumed or executed.

## Test plan

- All 90 rev-012 tests retained unchanged.
- 7 new isolated tests (1 + 3 + 3 above) -> 97 registered tests, every one executed, failed = 0, skipped = 0, FAKE_ONLY.
- Build-Candidate.ps1 derives and enforces the exact final registered count (97).

## Explicit non-goals for this task

No rev-013 formal audits, no rev-013 freeze, no Claude invocation, no owner gate, no claim, no provider invocation, no real credential reads, no attempt-013 creation, no R0B1 acceptance, no R0B2, no Git mutation.

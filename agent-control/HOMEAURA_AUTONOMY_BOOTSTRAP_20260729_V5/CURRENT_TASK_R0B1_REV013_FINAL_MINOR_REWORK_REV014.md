# CURRENT_TASK_R0B1_REV013_FINAL_MINOR_REWORK_REV014

TASK_ID: HA-AUTO-R0B1-REV014-FINAL-MINOR-CLOSURE-016
DECISION: AUTHORIZE_FINAL_BOUNDED_REWORK_AND_FAST_TRACK
STAGE: HA-AUTO-R0B1
PARENT: candidate-rev-013 (frozen, immutable, NEVER modified)
NEW CANDIDATE: candidate-rev-014
PLANNED ATTEMPT: attempt-013 (unchanged)

## Reason

Independent read-only Claude review of frozen candidate-rev-013 returned
PASS_WITH_MINOR (BLOCKER 0 / MAJOR 0 / MINOR 2 / INFO 4). ChatGPT disposition:

- MINOR-1 STALE_ATTEMPT_FIELD_NAMES_CASE_SENSITIVE — CONFIRMED_EXECUTABLE_EVIDENCE_BYPASS,
  MANDATORY_REV014_FIX. Keys "Attempt", "Target_Attempt", "Destination_Attempt"
  (any case variant) evade the literal scan, both textual regexes and the
  recursive structured scan simultaneously. It does not redirect the actual
  materialization destination but violates the anti-stale evidence contract.
- MINOR-2 SOURCE_PACKET_ADVISORY_WEAKER_THAN_ENFORCED_REVIEW_GATE —
  CONFIRMED_DOCUMENTATION_CONTRACT_GAP, FIX_IN_SAME_REVISION.
- INFO findings accepted and tracked; no independent candidate change.

## Scope (bounded)

1. Materializer.cs: stale-attempt key comparisons (attempt, target_attempt,
   destination_attempt) -> StringComparison.OrdinalIgnoreCase in the recursive
   structured scan; both textual stale-attempt regexes ->
   RegexOptions.IgnoreCase | RegexOptions.CultureInvariant. Preserve:
   unparsed fail-closed, recursion, bounds, unbounded fail-closed, historical
   allowlist boundaries, attempt-013 destination enforcement. No broad
   historical exemption.
2. MaterializerTests.cs: three isolated fake-only tests — root "Attempt": 12,
   nested "Target_Attempt": 12, array-contained "Destination_Attempt": "11" —
   each rejected solely with the intended stale-attempt code. Expected
   registered tests: 100.
3. Build-Candidate.ps1: provider packet instructions state the enforced
   predicate exactly — all five completion tokens (FINAL_VERDICT, final_verdict,
   ACCEPT_STATIC_PROPOSAL, independent_reviews, review_finished_utc) prohibited
   case-insensitively on review/70, review/71 and review/72; review/70 must not
   enumerate verdict vocabulary; review/71 states EXTERNAL_REVIEW_PENDING;
   review/72 has final_pass_invoked=false and no verdict/final_verdict key at
   any depth. The validator is NOT weakened.
4. Revision adaptation: candidate-rev-014, revision 14, supersedes 13, runtime
   HA-R0B1-R9-014, planned attempt attempt-013; binds rev-013 freeze/aggregate,
   rev-013 Claude raw + normalized evidence, verdict PASS_WITH_MINOR counts
   0/0/2/4, this design doc; rev-010/011/012 lineage retained.

## Then (same task, fast-track)

Transformers (one-shot, pinned pre-hashes, occurrence asserts, unified diffs)
-> static check -> deterministic build (release-a==release-b) -> ONE targeted
final audit (REV014_TARGETED_AUDIT_PASS) -> freeze (CreateNew) -> ONE
independent Claude review with fixed hash-helper transport (forward-slash
single-quoted path) -> findings policy -> owner-gate proposal ONLY if
BLOCKER=0/MAJOR=0 and no executable security MINOR -> stop at
OWNER_CONFIRMATION_REQUIRED. Never: provider request, credential read, claim,
attempt-013, git mutation, rev-013 modification.

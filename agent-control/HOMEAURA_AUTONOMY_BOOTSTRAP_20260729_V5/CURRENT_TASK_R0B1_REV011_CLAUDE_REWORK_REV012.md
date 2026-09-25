# CURRENT_TASK_R0B1_REV011_CLAUDE_REWORK_REV012

TASK_ID: HA-AUTO-R0B1-REV012-CLAUDE-REWORK-AND-BUILD-008
KIND: OWNER_REWORK_TASK_REV012
STATUS: ACTIVE_REWORK_IN_PROGRESS
STAGE: HA-AUTO-R0B1 (unchanged)

## Authority chain

- ChatGPT coordination prompt 008 (stored:
  `.tmp_router_help\CHATGPT_TO_KIMI_NEXT_PROMPT.txt`,
  sha256 `5f5730383f27857bc0f25de2bc42b04452932624df782b9131d3d2a0a007f681`)
  DECISION: AUTHORIZE_NEW_REVISION_REWORK.
- Scope authorized by prompt 008: author candidate-rev-012 from frozen rev-011,
  fix MAJOR-1 + MINOR-1..5, add isolated tests (total >= 89), deterministic
  double build, then STOP after build validation. No audits, no freeze, no
  Claude review, no owner gate, no claim, no attempt-013, no provider request,
  no credential read, no git mutation.

## Immutable predecessor state (verified prestate, do not modify)

- candidate-rev-011 FREEZE sha256:
  `8496737ecc23bbd64c6b9086b5de6cf07652ef4465772f0a0381992d8fe03c50`
- candidate-rev-011 aggregate (43 files):
  `9928a81688845406d88a4e105f92ccca61e5f8d0d63120763161ebade3b5182b`
- Claude independent review of rev-011: verdict REWORK
  (0 BLOCKER / 1 MAJOR / 5 MINOR / 4 INFO).
  - Claude raw output sha256:
    `4ce38d0209726b0b25a2188baca9c3f49387208589de8adecf4e9823d0be589a`
    (path: `.tmp_router_help\REV011_CLAUDE_REVIEW_RAW_001.txt`)
  - Claude evidence JSON sha256:
    `90177c5e638516dd4581585edd0298cd032f3456b6e0da5bc71b35f592842b01`
    (path: `.tmp_router_help\REV011_CLAUDE_REVIEW_EVIDENCE_001.json`)
  - Claude evidence TXT sha256:
    `fafa3e2ee480839dbe525e9707d725722f6e5057fa49a9957665bd0f5caa6db9`
    (path: `.tmp_router_help\REV011_CLAUDE_REVIEW_EVIDENCE_001.txt`)
- attempt-012: exists, 18/18 hash checks PASS, immutable, content-REJECTED.
  Never modified, never retried.
- attempt-013: ABSENT. Planned future attempt for candidate-rev-012 only after
  a fresh hash-bound owner confirmation. Not authorized, not consumed, not
  executed by this task.
- Claims/gates for rev-012: ABSENT and must remain absent during this task.
- Git HEAD at task start: `c11205f9a4f8379d2f2cbd7a9bd38013bf0e4db7`
  (must remain unchanged; no git mutations).

## Findings -> changes -> gates -> tests mapping

### MAJOR-1 CONFIRMED_MAJOR — TARGET_REVIEW_FABRICATION_VERDICT_CONDITION_UNENFORCED

- Location: rev-011 `src/HomeAuraR0B1Materializer.cs` (~1154-1174),
  SemanticTargetValidator review gates.
- Defect: `review/72_claude_final_pass.md` was not rejected when it carried
  verdict keys (`verdict` / `final_verdict`) or final-verdict tokens.
- Rev-012 change (REV012_BYTE_CHANGE_REQUIRED):
  - review/72 root object AND nested `claude` object reject case-insensitively
    keys `verdict` and `final_verdict`.
  - Tokens `FINAL_VERDICT`, `ACCEPT_STATIC_PROPOSAL`,
    `independent_reviews`, `review_finished_utc` rejected on review/72 and
    symmetrically on review/70.
  - Failure IDs:
    - `TARGET_REVIEW_FABRICATION:review72_root_verdict`
    - `TARGET_REVIEW_FABRICATION:review72_root_final_verdict`
    - `TARGET_REVIEW_FABRICATION:review72_claude_verdict`
    - `TARGET_REVIEW_FABRICATION:review72_claude_final_verdict`
    - `TARGET_REVIEW_FABRICATION:review72_forbidden_token`
    - `TARGET_REVIEW_FABRICATION:review70_forbidden_token`
  - Compliant fixture remains `final_pass_invoked=false` without verdict keys.
- Tests: new isolated tests rev012_review72_root_verdict_rejected,
  rev012_review72_root_final_verdict_rejected,
  rev012_review72_claude_verdict_rejected,
  rev012_review72_claude_final_verdict_rejected,
  rev012_review_forbidden_tokens_rejected.

### MINOR-1 FIX_IN_REV012 — required owner-gate action not machine-readable

- Change: add machine-readable field
  `required_owner_gate_action: CREATE_FIRST_UNUSED_ATTEMPT_013`
  (required in future; not yet authorized/consumed/executed) into generated
  evidence: `configuration\literal-command-manifest.json` (preconditions,
  Build-Candidate.ps1 ~1064) and `artifacts\capability-policy-binding.json`
  (semantic_guards ~1027).
- Gate: static check that both generated artifacts contain the field.

### MINOR-2 FIX_IN_REV012 — stale test name/comment/scope

- Change: rename test `canonical_attempt_011_occupied_attempt_012_absent`
  (MaterializerTests.cs ~828) to
  `canonical_attempt_012_occupied_attempt_013_absent`; fix comment
  (attempt-012 exists immutable content-rejected; attempt-013 absent) and the
  scope string in $TestReceipt (Build-Candidate.ps1 ~1177).

### MINOR-3 FIX_IN_REV012 — timestamp-gate too narrow

- Change (Materializer.cs ~1178-1183): extend placeholder-timestamp detection
  to shapes `YYYY-MM-DDTHH:MM:SS`, `YYYY-MM-DD HH:MM:SS`, `YYYY-MM-DDTHH:MM`,
  compact `YYYYMMDDTHHMMSS`, and epoch-like numbers on timestamp fields.
  Scan set extended: binding/00, provenance, evidence/40, evidence/41,
  review/70, review/71, review/72, result. Historical pinned blocks are not
  rejected. Marker `TIMESTAMP_CALLER_RECORDED` preserved.
- Tests: rev012_placeholder_timestamp_space_separator_rejected,
  rev012_placeholder_timestamp_minute_precision_rejected,
  rev012_placeholder_timestamp_epoch_like_rejected.

### MINOR-4 FIX_IN_REV012 — stale-attempt check whitespace-intolerant

- Change (Materializer.cs ~1133-1139):
  - JSON: structured parse of fields `attempt`, `target_attempt`,
    `destination_attempt`; reject numeric or string 10/11/12.
  - Text: regex with `\s*` for `attempt=10/11/12` and `"attempt"\s*:\s*12`.
  - Historical contexts (historical/superseded/immutable/rejected/prohibited)
    remain allowed.
- Test: rev012_stale_attempt_whitespace_rejected (`"attempt" : 12` must fail).

### MINOR-5 FIX_IN_REV012 — rollback spec documents non-existent WAITING_LIMIT_RESET resume

- Change (Build-Candidate.ps1 ~750, rollback-specification.json): rewrite
  `waiting_limit_reset` entry to actual behavior: quota exhaustion -> terminal
  FAILED_PROVEN, detail begins WAITING_LIMIT_RESET, transaction NOT resumable,
  retry requires fresh nonce + fresh owner gate. Consistent with
  claim-directory-policy transaction_state_machine (no WAITING_LIMIT_RESET)
  and Recovery.cs (429 -> FAILED_PROVEN, detail WAITING_LIMIT_RESET, exit 20).
  Documentation-only change; Recovery.cs behavior unchanged.

### INFO-1..4 — no changes required (per prompt 008 disposition).

## Revision identity renumbering (rev-012)

- ExpectedRoot candidate-rev-012; claim directory
  `candidate-rev-012.claims`; guard `REVISION12_CLAIM_DIRECTORY_PREEXISTS`.
- $TestRuntime `HA-R0B1-R9-012`.
- Recovery baseline: revision=12, supersedes=11; add
  `superseded_revision_011` block (freeze/aggregate/Claude evidence hashes,
  verdict REWORK, counts 0/1/5/4, frozen permanently preserved, rev-012 is a
  rework candidate, not accepted); rename `revision_011_corrections` to
  `revision_012_corrections` describing MAJOR-1 + MINOR-1..5 fixes; root_cause
  gains a revision-11 entry (REWORK verdict).
- $ReworkTaskPath -> this document; $ReworkTaskSha256 -> sha256 of this file.
- $CreatedUtc -> fresh caller-recorded UTC fixed at transform time.
- Test gate: passed count updated to exact total (>= 89).
- $TestReceipt scope: MINOR-2 rename + new rev-012 scope rows.
- $PackageManifest / $Inventory revision 11 -> 12.
- $ReviewInstructions: candidate revision 012, rework task filename,
  revision-012 corrections list, updated gate-2 description (review/72 no
  verdict/final_verdict keys case-insensitive root+claude; forbidden tokens on
  review/70+72), new tests listed, lineage with rev-011 freeze/aggregate and
  Claude evidence hashes + verdict REWORK.
- Post-transform grep control: no `rev-011` / `revision 11` / `R9-011` /
  `REVISION11` outside historical contexts (superseded_revision_011 etc.).

## Acceptance gates for this task (all required before report)

1. Design doc written; sha256 recorded.
2. candidate-rev-012 created new (fail if exists) with exactly 4 dev inputs:
   Build-Candidate.ps1, src/HomeAuraR0B1Materializer.cs,
   src/HomeAuraR0B1Recovery.cs, tests/MaterializerTests.cs.
3. Transformers exact-match applied once each; before/after hashes + diffs
   preserved under `.tmp_router_help`.
4. Total isolated tests >= 89; gate mapping updated.
5. Static validation: PS parse OK, test count matches gate, no stale rev-011
   identity refs, CREATE_FIRST_UNUSED_ATTEMPT_013 present in both templates,
   rollback doc consistent.
6. Build-Candidate.ps1 executed once from candidate-rev-012: exit 0, all
   tests pass, failed=0, FAKE_ONLY, zero provider requests, zero credential
   reads, BYTE_IDENTICAL double build, production exe never executed.
   At most ONE repair iteration allowed (only the 4 rev-012 files).
7. Post-build: rev-011 verify (28 checks) PASS, attempt-012 18/18 PASS,
   attempt-013 absent, rev-012 claim/freeze/gate absent, HEAD unchanged.
8. Report `KIMI_REV012_REWORK_BUILD_REPORT.txt` (markers
   HOMEAURA_KIMI_REV012_REWORK_BUILD_REPORT_BEGIN/END) sent once to the
   verified chat, then STOP.

## Explicit non-goals for this task

- No audits of rev-012, no freeze, no Claude review, no owner gate, no claim,
  no attempt-013 materialization.
- No production provider request, no credential read, no git mutation.
- No modification of rev-011, attempt-010..012, or any historical artifact.

## Stop codes

- REV012_PARENT_PRESTATE_DRIFT — any prestate mismatch; stop immediately.
- REV012_DESTINATION_ALREADY_EXISTS — candidate-rev-012 preexists; stop.
- REV012_BUILD_VALIDATION_FAILED — build fails after one repair iteration;
  preserve evidence and stop fail-closed.

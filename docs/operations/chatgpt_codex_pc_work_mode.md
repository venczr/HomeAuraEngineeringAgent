# HomeAura ChatGPT ↔ Codex ↔ PC work mode

Version: 1.0
Scope: operational coordination only

## Purpose

This work mode lets ChatGPT provide a bounded job, Codex execute it on the
Windows workstation, collect local evidence, and return a report through
Project Bridge. It does not grant permission to alter engineering models,
drawings, external accounts, or system configuration.

## Job lifecycle

1. Receive one `HOMEAURA_CHATGPT_TO_CODEX_JOB` envelope.
2. Record repository root, branch, HEAD, `git status --short`, and
   `git diff --stat`.
3. Check the allowed and forbidden scopes before every write or UI action.
4. Preserve all pre-existing changes as user-owned.
5. Execute only the current job and collect evidence locally.
6. Validate artifacts, compare the worktree before and after, and issue a
   PASS/FAIL/BLOCKED report.
7. Send the report through Project Bridge.
8. Do not start another phase until a new job is received.

## Safety rules

- Never reveal tokens, credentials, chat identifiers, private messages, or
  personal window content.
- Never run `git reset`, `git clean`, `git checkout`, branch switching,
  commit, push, merge, or destructive equivalents unless a later job
  explicitly authorizes the exact action.
- Never overwrite an existing user file when a new evidence file can be used.
- Never touch DWG, BAK, IFC, MRD, AutoCAD, or MagiCAD unless the current job
  explicitly authorizes a safe copy and exact operation.
- Stop for CAPTCHA, 2FA, account login, device confirmation, security/privacy
  permission prompts, UAC, or dangerous irreversible actions.
- Use local-only evidence capture. Do not upload screenshots to an external
  service.

## Transport

- Codex `notify` is the primary event path.
- Lifecycle hooks are supplementary and must be fail-open: input, dispatch, or
  downstream errors must not block Codex.
- Project Bridge is the report/request exchange path.
- Telegram Control is used for concise human-action notifications, not for
  publishing secrets or full diagnostic payloads.

## Evidence requirements

Each job evidence directory must contain:

- a preflight record;
- logs for each smoke test;
- PNG metadata with timestamp, dimensions, bytes, SHA-256, test name, and
  capture method;
- validation results;
- a SHA-256 manifest covering all evidence files.

The report must identify the evidence by relative path and state which
acceptance criterion it proves.

## Status meanings

- `AVAILABLE`: tested successfully in the current environment.
- `PARTIAL`: some required behavior was tested, but an important part remains
  unverified or unavailable.
- `MISSING`: the executable, module, configuration, or artifact was not found.
- `BROKEN`: present but failed its safe test.
- `NOT_TESTED`: deliberately not exercised, with an exact reason.

## Failure handling

Use up to three safe diagnostic attempts when an operation fails. Record the
command, exit code, safe error type, and last confirmed stage. Do not repeat
the same failing action indefinitely. If a missing capability would require an
install or elevated permission, create a `TOOL_REQUEST`; do not install it.

## Human action

Human action is required for:

- CAPTCHA or 2FA;
- account sign-in or device confirmation;
- UAC or security/privacy permission;
- any dangerous irreversible action;
- a decision that materially changes the approved scope.

The notification must be short and begin with `ТРЕБУЕТСЯ ДЕЙСТВИЕ ЧЕЛОВЕКА`.

## OPS-1 acceptance

OPS-1 is complete only when the capability matrix, safe screenshot evidence,
GUI smoke, terminal smoke, task envelope/schema, TOOL_REQUEST simulation,
Project Bridge evidence, fail-open hooks, final report, and SHA-256 manifest
are all present and validated. AutoCAD/MagiCAD may be `NOT_TESTED` when the
reason is recorded honestly.

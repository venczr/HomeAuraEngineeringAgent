# HomeAura AI orchestration: current state

Generated: 2026-07-27T19:54:39+03:00  
Updated: 2026-07-30T00:21:17+03:00  
Task: `HA-ORCH-CLINE-001`  
Evidence basis: local files, Git objects, working-tree status and executable
validation commands. Earlier AI reports were used only as navigation aids.

## Repository baseline

- Repository: `C:\AI\HomeAuraEngineeringAgent`
- Branch: `feature/room-geometry`
- START_COMMIT: `c11205f9a4f8379d2f2cbd7a9bd38013bf0e4db7`
- Parent: `c33f5e8cbf0e0b23e1d5800dd23d99e71d893df9`
- Upstream: `origin/feature/room-geometry`
- Index: empty
- API version found in `agent/api.py`: `0.6.0`
- AutoCAD plug-in version found in `Properties/AssemblyInfo.cs`: `1.2.0.0`

Git reported five tracked unstaged paths. They predate this task and remain
owner-controlled:

1. `README.md`
2. `docs/COMPATIBILITY.md`
3. `docs/ROOM_GEOMETRY.md`
4. `projects/Test_01/Test_01.bak`
5. `projects/Test_01/Test_01.dwg`

The repository also contains pre-existing untracked reports. This task does not
adopt, stage, delete, rewrite or publish them.

All nine requested files under `docs/ai_orchestration/**` were already
untracked when this task began. The safety gate stopped the task until the
owner explicitly confirmed that they may be adopted as the editable baseline.
They remain untracked; no commit is authorized.

## Protected hashes at start

| Path | SHA-256 |
| --- | --- |
| `README.md` | `5B4CBDF2BAFFE8093E523FD0DA8C1F2DA9479A34657C5A80F29ACECADADEF95B` |
| `docs/COMPATIBILITY.md` | `B6D072900778C6FCB14DD4692DC0FE62FF5550316B0C19789A4BF7283ECD5835` |
| `docs/ROOM_GEOMETRY.md` | `8496B395A34EFE4EA8B54F9A3FE78DFBA6F4E58CDF6ACA38039573AB44DA8874` |
| `projects/Test_01/Test_01.bak` | `5D1907FAD42F2B930573BAED082A4677503E5225330629602817EA77C5A9D149` |
| `projects/Test_01/Test_01.dwg` | `5A673AAA50F8D29C21555D60D7FEC740FF3CE214CD7EB65AE329DC3B701397AC` |
| `projects/Test_01/exports/rooms/rooms.json` | `30EE1828E74ECBF1E1B46064C39CE30755A4692FC4CD972D1E38328AFFE0992E` |

## Verified implementation state

- DOMAIN models and adapter exist in `agent/domain_models.py` and
  `agent/domain_adapter.py`.
- PROJECT foundation and strict `CanonicalProjectModel` exist in
  `agent/project_models.py` and `agent/project_foundation.py`.
- Read-only DOMAIN and PROJECT preview APIs exist.
- Optional read-only `IfcSpaceGeometry` support exists.
- Python tests exist for rooms, IFC import/preview, DOMAIN and PROJECT.
- Draft standalone room and project JSON Schemas now exist under `schemas/`
  and are generated deterministically from the verified runtime models.
  The remaining central engineering schemas are still `MISSING` or
  `NOT_EXPORTED` as recorded in `contracts_registry.json`.
- A whole-token repository scan found no references to Gemini, Claude Pro,
  Claude Code or Cline outside `docs/ai_orchestration/**`. Therefore no
  obsolete Gemini assignment outside this package was found to migrate.

This document does not claim that the API, engineering calculations or
AutoCAD integration are complete. It records only the facts above.

## Test and build status

- Safe package checks are limited to JSON parsing, file-scope checks, exact
  orchestration-reference scans, secret-pattern scanning and Markdown
  consistency review.
- Both registries passed Python 3.12 `json.load`, duplicate-key rejection and
  PowerShell `ConvertFrom-Json`.
- All five prompts contain the required task fields; the four local-executor
  prompts contain the mandatory agent report fields.
- The guarded PowerShell worktree template parsed successfully without being
  executed, and the package secret-pattern scan found no secret-like value.
- The committed repository contains Python test suites for rooms, IFC, DOMAIN
  and PROJECT plus a C# RoomGeometry test project.
- Engineering tests, the AutoCAD plug-in build and runtime application tests
  were not rerun by `HA-ORCH-CLINE-001`; prior report claims are not substituted
  for current execution evidence.
- On 2026-07-30, the schema exporter check and all 9 contract-schema tests
  passed. The related rooms, DOMAIN, PROJECT foundation and schema suites
  passed 136 tests. This is focused contract evidence, not a full repository
  regression or AutoCAD runtime result.
- Independent Claude and Kimi read-only reviews completed. Their actionable
  missing-schema, Windows LF-normalization and full-document version-test
  findings were corrected and rerun; neither reviewer was granted write access.
- AutoCAD, MagiCAD, NETLOAD and working engineering files were not opened.

## Orchestration state

- `CLINE_READY=false`
- `CLINE_PROVIDER_TARGET=CLAUDE_CODE`
- `CLINE_EXECUTION_MODE=PREPARED_ONLY`
- `CLINE_AUTHORIZATION_VERIFIED=false`
- `CLINEPASS_PURCHASE_ALLOWED=false`
- `FOREIGN_CARD_PURCHASE_ALLOWED=false`
- `CLINE_AUTO_APPROVE_ALLOWED=false`
- `CLAUDE_MODE=PRO_READ_ONLY`
- `GEMINI_ENABLED=false`
- Codex remains the owner of central PROJECT/DOMAIN contracts and integration.
- Claude Pro may audit supplied evidence but is not assumed to have local
  repository access.
- Cline is treated as a VS Code agent environment, not as a model.
- No Cline subscription, provider, model, login or API key is configured by
  this task.
- The three prepared Cline branch names and worktree paths were checked and
  were absent. No worktree or branch was created.
- Claude Code is only the target provider. Existing Claude Pro access is not
  evidence that Claude Code authorization or Cline integration will work.
- If provider verification requires ClinePass, an API key, another paid plan or
  payment-card action, the result is `BLOCKED` until the owner gives separate
  permission.

## Contract readiness

Parallel write execution is not ready. The room and project standalone schemas
are exported drafts but are not frozen. `contracts_registry.json` records the
verified source model, if one exists, and uses `NOT_EXPORTED` or `MISSING`
instead of inventing the remaining schemas.

Initial independent compatibility review is complete. The immediate contract
milestone is owner acceptance and a separate freeze decision for the room and
project drafts, then RFCs for floor-heating, system graph and scene contracts.
Export and review do not authorize downstream parallel writers or declare
either draft frozen.

## History-cleanup boundary

An isolated `git-filter-repo` 2.47.0 installation was verified at
`C:\AI\HomeAuraTools\git-filter-repo\2.47.0`. Its retained wheel SHA-256 is
`2CD04929B9024E83E65DB571CBE36AEC65EAD0CB5F9EC5ABE42158654AF5AD83`,
matching the recorded acquisition evidence. Gate A/R4 has not been authorized
in this task. The general orchestration rules prohibit history rewriting. A
future disposable-copy cleanup requires its own explicit authorization and
must not be mixed with Cline worktree creation.

Recommended sequencing:

1. resolve the separately gated history-cleanup decision;
2. freeze the minimum contracts;
3. explicitly set `CLINE_READY=true` only after user installation and approval;
4. create one checked worktree for one independent module;
5. integrate only after diff, tests, audit and explicit merge approval.

## Unverified areas

- Cline installation, provider, model, subscription and authorization.
- Actual state of Cline Auto Approve in VS Code; the package only forbids
  enabling it.
- Claude Pro audit of this package.
- Owner freeze decision for the reviewed room/project drafts, plus all
  remaining standalone engineering JSON Schemas.
- Future execution of the prepared Cline worktree commands.
- AutoCAD/MagiCAD runtime behavior.
- Full engineering calculations, rendering and catalog data.
- Current full Python and C# regression results and current plug-in build.
- Remote GitHub state after the last verified remote check.

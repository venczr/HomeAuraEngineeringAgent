# T-002 — Verification gate handoff (for Codex)

**TASK_ID:** `CLAUDE_ONLY_T002_CI_VERIFICATION_GATE`
**Status:** reconciled, locally verified and integrated with exact-path commits
**Branch:** `feature/room-geometry` (local commits only; not pushed)
**Authors:** Claude Code (initial implementation) and Codex (audit, CI fix,
regression tests and Git integration)

---

## L0 — the one thing to know

There is now **one authoritative verification command**. Use it everywhere:

```bash
python scripts/verify.py
```

Exit `0` = green. Never re-implement the checks anywhere else; if CI and local
disagree, the entry point is the bug.

---

## L1 — what was delivered

| File | Purpose | State |
|---|---|---|
| `scripts/verify.py` | authoritative entry point: pytest → schema drift | integrated |
| `.github/workflows/verification.yml` | CI calling the same entry point | integrated |
| `tests/test_verification_gate.py` | workflow and entry-point regression tests | integrated |
| `.tmp_router_help/T002_CODEX_VERIFICATION_HANDOFF.md` | this file | integrated |

No push, PR, merge or remote mutation was performed.

### `scripts/verify.py`
Runs, in fixed order:
1. `python -m pytest` — full suite through the pinned `pytest.ini` harness
2. `python -m agent.schema_export --check` — generated JSON Schemas still match the
   Pydantic models (read-only)

Deliberate properties:
- **never installs anything** — a missing dependency is a reported failure, so CI
  cannot silently drift from the lock files
- **no network**, **no schema or worktree mutation**
- **propagates the first non-zero exit code**; failures print verbatim (stdio is
  inherited, nothing is captured or swallowed)
- identical behaviour from any working directory
- exit codes: `0` pass · `1` a check failed · `2` environment unusable
- flags: `--list`, `--fail-fast`

### `.github/workflows/verification.yml`
- triggers: push to `feature/room-geometry`, any PR, manual dispatch
- `permissions: contents: read` only — no packages, no deployments, no id-token
- `persist-credentials: false`, concurrency-cancelling, 15-minute timeout
- Windows runner because the pinned runtime lock contains `pywin32`; Python
  **3.12** matches the local `.venv`, which reports 3.12.0
- installs strictly from `requirements.lock.txt` + `requirements-dev.lock.txt`
- runs `python scripts/verify.py`
- final step asserts `git status --porcelain` is empty, so a side effect or a stale
  schema fails the build loudly
- **no secrets, no publish, no deploy, no commit, no push**

---

## L2 — verification evidence (all local)

| Check | Result |
|---|---|
| `verify.py --list` | exit 0, both checks listed |
| `verify.py` full run | **272 passed, 236 subtests, 0 failed** + schema check → `ALL CHECKS PASSED`, exit 0 |
| Exit-code propagation | run with an interpreter lacking pytest → **exit 2**, clear message, nothing hidden |
| Working-directory independence | run from `%TEMP%` → exit 0, identical result |
| Reproducibility | consecutive run → exit 0, identical result |
| No mutation | schema hashes unchanged; deterministic regeneration byte-identical |
| YAML static parse | parses; `permissions={'contents':'read'}`; calls `scripts/verify.py`; no secrets / deploy / push |

**Not claimed:** the workflow has **never run on GitHub**. It is statically valid
only. Remote CI success must not be asserted until an actual run exists.

---

## Codex reconciliation update (2026-08-01)

Codex found and fixed one blocking static CI defect before integration: the
original `ubuntu-latest` runner could not install the unconditional
`pywin32==312` pin in `requirements.lock.txt`. The workflow now uses
`windows-latest`, and its clean-tree assertion is native PowerShell. A regression
test binds the runner choice to the platform-specific lock.

## Remaining external validation

The local gate is complete. A real GitHub Actions result requires a future push,
which is outside Codex's authority in this stage. Until then, only local and static
workflow validation is claimed.

### Known context
- `agent/schema_export.py`, `tests/test_contract_schemas.py` and `schemas/*.json`
  were integrated in a prerequisite exact-path commit; `--check` passes and
  regeneration is byte-identical.
- `pytest` is intentionally **not** in `requirements.lock.txt`; it lives in
  `requirements-dev.lock.txt`. CI must install both.
- `agent/chatgpt_bridge/selectors.py` in `C:\AI\HomeAuraOrchestrator` carries an
  uncommitted fix (removed a hidden-fallback selector that broke every Bridge send).
  Backup: `selectors.py.bak_20260731T212410Z`. A checkout there would lose it.

### Standing prohibitions (unchanged)
`candidate-rev-014` never re-executed · its claim never deleted or emptied ·
attempts 001–012, GATE_001, GATE_002 immutable · `attempt-013` must stay ABSENT ·
no official `candidate-rev-015` until Kimi capacity is verified restored ·
no `GATE_003` · no Kimi credential read or provider request · **R0B1 NOT ACCEPTED**.

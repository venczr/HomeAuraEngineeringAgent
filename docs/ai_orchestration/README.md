# HomeAura multi-AI orchestration

This directory defines a prepared, evidence-driven collaboration model for
Codex, Cline and Claude Pro.

It does not install or authorize Cline. It does not grant Claude Pro local
repository access. Gemini is disabled and has no active task.

Current provider intent is `CLINE_PROVIDER_TARGET=CLAUDE_CODE`, but provider
availability and authorization have not been verified. Until the owner
completes installation, authorization and a read-only worktree check:

- `CLINE_READY=false`;
- `CLINE_EXECUTION_MODE=PREPARED_ONLY`;
- `CLINEPASS_PURCHASE_ALLOWED=false`;
- `FOREIGN_CARD_PURCHASE_ALLOWED=false`;
- Auto Approve remains off.

If Claude Code is unavailable to the owner's existing Claude Pro account, or
Cline requests a separate subscription, API key or payment, stop as `BLOCKED`.
Do not buy, register or store credentials from this package.

## Files

- `current_state.md` — verified repository and orchestration baseline.
- `task_registry.json` — task ownership, execution mode and readiness.
- `contracts_registry.json` — factual contract inventory and freeze blockers.
- `prompts/codex_core.txt` — core implementation/integration prompt.
- `prompts/cline_floor_heating.txt` — prepared floor-heating task.
- `prompts/cline_visualization.txt` — prepared scene/Blender task.
- `prompts/cline_catalog.txt` — prepared equipment-catalog task.
- `prompts/claude_audit.txt` — independent read-only audit prompt.

## Authority model

| Actor | Role | Local writes | Contract authority |
| --- | --- | --- | --- |
| Codex | Architect, primary implementer, integrator | Explicitly scoped | Owns central contracts |
| Cline | VS Code local executor | Only after `CLINE_READY=true`, in its own worktree | RFC only |
| Claude Pro | Independent auditor | None assumed | Findings and RFC only |
| Owner | Accepts risk and approves external or destructive actions | Human decision | Approves incompatible changes |

## Mandatory workflow

1. Record branch, START_COMMIT, status, diff and protected files.
2. Freeze the contracts required by the task.
3. Limit allowed files and define stop conditions.
4. Implement in one owned worktree.
5. Review the complete diff and run mandatory tests.
6. Produce evidence; do not trust an AI status label alone.
7. Obtain independent audit.
8. Integrate only after compatibility review and explicit merge approval.

No task may silently change central schemas, AutoCAD writer behavior, IDs,
secret handling, Git history or user engineering files.

## Prepared worktree commands — do not run yet

The commands below are templates. They intentionally stop if either the branch
or directory already exists. Run one module only after:

- the owner confirms `CLINE_READY=true`;
- cleanup gates are resolved;
- required contracts are frozen;
- the exact START_COMMIT is reconfirmed;
- the owner approves worktree creation.

```powershell
$homeAuraRepo = 'C:\AI\HomeAuraEngineeringAgent'
$homeAuraSafeRepo = 'C:/AI/HomeAuraEngineeringAgent'
$homeAuraStartCommit = 'c11205f9a4f8379d2f2cbd7a9bd38013bf0e4db7'
$clineReady = $false

function New-HomeAuraCheckedWorktree {
    param(
        [Parameter(Mandatory = $true)][string]$Branch,
        [Parameter(Mandatory = $true)][string]$Worktree
    )

    if (-not $clineReady) {
        throw 'CLINE_READY is false; installation and READ_ONLY verification are incomplete.'
    }
    if (Test-Path -LiteralPath $Worktree) {
        throw "Worktree path already exists: $Worktree"
    }

    git -c safe.directory=$homeAuraSafeRepo -C $homeAuraRepo `
        show-ref --verify --quiet "refs/heads/$Branch"
    if ($LASTEXITCODE -eq 0) {
        throw "Branch already exists: $Branch"
    }

    $actualCommit = (
        git -c safe.directory=$homeAuraSafeRepo -C $homeAuraRepo rev-parse HEAD
    ).Trim()
    if ($actualCommit -ne $homeAuraStartCommit) {
        throw "START_COMMIT mismatch: $actualCommit"
    }

    git -c safe.directory=$homeAuraSafeRepo -C $homeAuraRepo worktree add `
        -b $Branch $Worktree $homeAuraStartCommit
}

# Run exactly one only after all readiness and owner-approval gates pass:
# New-HomeAuraCheckedWorktree -Branch 'feature/floor-heating-engine' `
#     -Worktree 'C:\AI\HomeAura-Cline-FH'
# New-HomeAuraCheckedWorktree -Branch 'feature/blender-visualization' `
#     -Worktree 'C:\AI\HomeAura-Cline-VIS'
# New-HomeAuraCheckedWorktree -Branch 'feature/equipment-catalog' `
#     -Worktree 'C:\AI\HomeAura-Cline-CAT'
```

Prepared branch/worktree mappings:

| Task | Branch | Worktree |
| --- | --- | --- |
| `HA-FH-001` | `feature/floor-heating-engine` | `C:\AI\HomeAura-Cline-FH` |
| `HA-VIS-001` | `feature/blender-visualization` | `C:\AI\HomeAura-Cline-VIS` |
| `HA-CAT-001` | `feature/equipment-catalog` | `C:\AI\HomeAura-Cline-CAT` |

At the 2026-07-27 audit, all three branches and all three paths were absent.
This is a historical check, not permission to run the commands later.

No worktree command was executed by `HA-ORCH-CLINE-001`.

## Validation

Both registries must pass Python `json.load` and PowerShell
`ConvertFrom-Json`. Review scope with Git and verify that only
`docs/ai_orchestration/**` is new or modified by this task.

Before reporting readiness, scan this directory for secret-like values. A scan
is supporting evidence, not proof that the rest of the repository contains no
secret.

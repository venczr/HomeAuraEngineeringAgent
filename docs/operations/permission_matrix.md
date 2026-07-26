# HomeAura operational permission matrix

Version: 1.0

| Action | Default | Conditions |
|---|---|---|
| Read repository files and Git metadata | ALLOW | Hide secrets; do not invoke write filters intentionally |
| Create a new file in an explicitly allowed evidence/report path | ALLOW | Verify the destination does not exist |
| Modify an existing user file | BLOCK | Requires a new job naming the exact file and change |
| Git status, diff, log, rev-parse | ALLOW | Read-only only |
| Git reset, clean, checkout, branch switch, commit, push, merge | BLOCK | Requires separate explicit authorization |
| Local screenshot of a new safe test window | ALLOW | No personal data; save locally; record SHA-256 |
| Interact with existing personal windows, mail, chats, or documents | BLOCK | Use a dedicated safe test window |
| Open AutoCAD, MagiCAD, DWG, BAK, IFC, or MRD | BLOCK | Requires a separate safe-copy job |
| Run an installed terminal command | ALLOW | Command must be bounded and non-destructive |
| Install software, modules, extensions, or drivers | ASK | Create TOOL_REQUEST; human approves exact source and rights |
| CAPTCHA, 2FA, sign-in, device confirmation | HUMAN | Stop and request intervention |
| UAC or security/privacy permission | HUMAN | Do not accept or bypass |
| Send a report through the configured Project Bridge | ALLOW | Current project channel only; secret scan first |
| Send a concise Telegram human-action notice | ALLOW | No token, chat ID, or sensitive diagnostic payload |
| Delete local/cloud user data | HUMAN | Confirm exact target immediately before action |
| Destructive or irreversible system action | HUMAN | Stop; require explicit approval |

## Ownership rule

Every file or worktree change that existed before a job belongs to the user.
Codex must not restore, normalize, reformat, stage, move, or delete it.

## Fail-open rule

Notification and lifecycle-hook failures must be logged using safe exception
types and must return success to Codex. They must never block the main task.

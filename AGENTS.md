# HomeAura project operating rule

## Continuous stage progression

- Treat the user's project authorization as standing permission to continue
  through the current bounded workflow.
- When one stage, milestone, review, or validation block is complete, start the
  next applicable stage immediately without asking the user between stages.
- Apply the same rule between blocks inside one stage: after a bounded block
  completes, immediately begin the next safe block instead of ending the turn.
- Keep moving through sequential stages in the same turn/session whenever the
  next scope and write boundary are known.
- Use API, Claude, and the configured Project Bridge/Edge ChatGPT lane as the
  primary planning, review, and large-context channels whenever available
  (target roughly 90% of such consultations) to conserve Codex limits.
- Prefer the smallest useful bounded task, stop early when its acceptance bar
  is proven, and then advance immediately. Do not repeat completed T-01,
  T-055, broad full-suite cycles, or spent attempts.
- Preserve existing user changes and use evidence-backed validation after each
  implementation block.

## Autonomous continuation protocol

- This is a standing project instruction: do not stop merely because a stage,
  sub-stage, block, review, or handoff has ended. Read the resulting handoff
  immediately and continue to the next applicable safe block in the same
  session.
- Do not ask for an ordinary confirmation between sequential blocks. Use the
  user's standing project authorization and the already-defined scope and
  change boundary.
- If one path is blocked, do not end the whole workflow: record the exact
  blocker, avoid the blocked action, and continue every independent local,
  read-only, test, documentation, review, or preparation block that remains
  safe and in scope.
- After receiving a Bridge/ChatGPT/Claude handoff, verify its status and
  artifact locally, apply its next bounded task, run its narrow acceptance
  checks, and forward the next completion handoff without waiting for the
  user.
- Never finish a turn while a required Bridge/ChatGPT job is in
  `queued`, `sending`, `submitted`, or `waiting_response`. Poll the durable
  job state until it reaches `completed`, `failed`, or `needs_human`, then
  read the matching response file and continue its next safe block before
  returning control.
- Only pause the active workflow when no safe in-scope work remains or when a
  genuine owner/external action is required. A pause is not a completion: keep
  the project state explicit so the next invocation resumes at the exact
  blocked boundary.

## Non-overridable boundaries

This rule does not authorize inventing missing values, secrets, commands,
credentials, identity bindings, or external facts. It does not bypass platform
permissions, billing, CAPTCHA/login, safety controls, owner-only ceremonies,
manual administrative actions, or genuine external approval gates. When such a
boundary is reached, continue all safe preparation automatically and report the
exact boundary instead of pretending the next stage was completed.

## External-AI coordination for floor-heating routing

- Codex is the coordinator, not the sole route designer. Delegate planning and
  alternative generation to the configured high-reasoning ChatGPT/Kimi lanes;
  use Claude Code CLI as the independent evidence auditor whenever its quota is
  available.
- Before any helper works, provide the full owner routing manual, both owner
  reference projects, current clean/diagnostic views, exact domains, source
  project and diagnostics. Require the helper to restate the rules first.
- Never copy the deliberate kitchen/furniture voids visible in older owner
  references. In the current project every allowed heated area must be covered;
  any void requires a separately verified exclusion.
- Claude Code CLI must independently recompute geometry, R80, wall/contact,
  coverage, length, continuity and claim-boundary evidence from the actual
  artifacts. Do not accept prose or screenshots as proof.
- The durable role/checklist is
  `reports/HomeAura_AI_coordination_policy_2026-08-20.md` and is mandatory for
  future floor-heating stages.

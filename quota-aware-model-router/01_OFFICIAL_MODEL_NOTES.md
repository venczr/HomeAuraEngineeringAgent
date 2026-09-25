# Official model and CLI notes

Verified on 2026-07-30. Model aliases can move over time; acceptance evidence must record the exact resolved model.

## Codex

- Installed CLI: `codex-cli 0.146.0`.
- Fresh session: `codex.cmd -m <model> -c 'model_reasoning_effort="<level>"'`.
- Official families:
  - `gpt-5.6-luna`: lowest-cost clear/repeatable work;
  - `gpt-5.6-terra`: everyday workhorse;
  - `gpt-5.6-sol`: complex/open-ended/security work.
- Higher effort costs more. Ultra uses subagents and is not a quota-saving setting.
- Official references:
  - https://developers.openai.com/codex/models
  - https://developers.openai.com/codex/pricing
  - https://developers.openai.com/api/docs/guides/latest-model

## Kimi Code

- Installed CLI: `0.31.0`.
- Fresh session: set process-scoped `KIMI_MODEL_THINKING_EFFORT`, then run `kimi.cmd --model <id>` without `--continue` or `--session`.
- `k3-256k` gives the same K3 results within 256k and consumes less quota than `k3` 1M.
- `k3` 1M consumes about twice the quota of `k3-256k`.
- `kimi-for-coding-highspeed` consumes about three times the quota.
- K3 supports `low`, `high`, and `max`; default is `high`.
- Changing model or effort invalidates the existing context cache. Start a new session.
- Official references:
  - https://www.kimi.com/code/docs/en/kimi-code/models.html
  - https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/env-vars.html
  - https://www.kimi.com/code/docs/en/kimi-code-cli/reference/kimi-command.html

## Claude Code

- Installed CLI: `2.1.220`.
- Fresh session: `claude.cmd --model <alias> --effort <level>`.
- Current official aliases on the Anthropic API:
  - `haiku`: fast/efficient simple work;
  - `sonnet`: daily coding;
  - `opus`: complex reasoning;
  - `fable`/`best`: hardest/long-running work, not selected by this policy.
- The aliases currently resolve to current provider-specific versions; use `/status` and record the resolved model.
- Changing model or effort causes the next request to reread the history without the prior cached context.
- Claude review windows must be visible PowerShell sessions.
- Official references:
  - https://code.claude.com/docs/en/model-config
  - https://code.claude.com/docs/en/prompt-caching
  - https://code.claude.com/docs/en/cli-usage


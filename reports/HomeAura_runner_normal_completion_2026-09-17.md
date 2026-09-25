# Runner normal completion fix — 2026-09-17

- Valid task result is recorded separately from process completion.
- After result receipt runner waits up to 20 seconds for natural Codex exit, then uses bounded graceful termination and forced kill only as last resort.
- `termination_reason`, `terminal_event`, `task_result_status`, `process_exit_code_known`, and real `exit_code` are persisted.
- `turn.completed` usage parsing captures actual input, cached input, output, session and elapsed values.
- Regression coverage includes natural exit, grace termination, provider failure, usage parsing, Astra guard, packet and budget guards.

Final fresh Luna B probe: run `cheap-b-natural-70d4edcc30`, task result COMPLETED, real exit code 0, `turn.completed` present, NATURAL_EXIT, actual usage captured (input 41976; cached input 39168; output 710). The child process is absent after completion. Supervisor remained STOPPED and queue remained unchanged; P7 was not executed.

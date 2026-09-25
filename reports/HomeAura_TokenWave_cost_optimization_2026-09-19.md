# HomeAura TokenWave cost optimization — 2026-09-19

## Observed usage

- Final live capture: 925,445,436 billing tokens spent; 534,554,564 remaining.
- GPT-6 Astra: 782,061,978 (84.5% of spend).
- GPT-5.6 Terra: 124,533,922 (13.5%).
- GPT-5.6 Luna: 17,784,170 (1.9%).
- Daily spend: 613,915,620 on Sep 17; 156,893,970 on Sep 18; 154,635,846 on Sep 19 at final capture.
- The live counter increased by 72,757,922 during this Astra-backed diagnostic session. Further optimization work should run on Luna by default and Terra only for bounded hard tasks.

## Root causes found

- Known P8 sessions consumed at least 1,995,260 input tokens while no durable task-result contract was written. One reused attempt ID hid a second 371,533-token session by overwriting its JSONL artifact.
- An orphaned P8 attempt survived its launcher and emitted 1,258 repeated network reconnect events until terminated on Sep 19.
- The autonomous limits allowed broad tool exploration (40 agent items, 15 commands, 1 MiB JSONL) and two failed attempts per task.
- The task-result prompt omitted mandatory `TASK_ID` even though the validator required it, turning successful exit-zero work into a retry candidate.
- Attempt IDs were reused, so later runs could overwrite earlier diagnostic artifacts.
- The TokenWave router retried every exception twice, counted only successful calls, and fetched the model catalog before every call.

## Applied controls

- Autonomous primary: at most 3 turns/hour, 6/run, 1 failed turn/task, 60 seconds, 12 agent items, 6 commands, 256 KiB JSONL, 20 seconds without progress.
- TokenWave: 3 calls/task, 12/hour, 24/run, 12k context chars, 1.6k output tokens, no automatic paid retries, no autonomous Astra escalation.
- Calls are reserved before provider execution and logged as started, so failed attempts consume the budget.
- Model discovery is cached for one hour.
- Windows orphan recovery now finds a child `codex.exe` by recorded run ID even after its launcher PID has died.
- The result contract now explicitly requires the assigned `TASK_ID`, keeps the child within that task, and gives every execution a unique artifact ID.
- Contract completion is accepted only for a full result with the assigned task ID; global rollback no longer rewrites unrelated run logs.
- MCP callers can supply a stable task ID; hourly and task budgets use durable `worker_started` events, and disabled escalation fails before a provider request.
- Five consecutive provider/reconnect errors now stop the turn as `PROVIDER_ERROR_STORM`; network error output no longer resets the progress timer.

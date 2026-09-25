# HomeAura API contract synchronization — 2026-09-19

The existing `/api/v1/engineering/floor-heating/coverage-preview` endpoint is now represented in the domain and project preview route contracts. The generated project schema was refreshed after the `vector_drawing` source kind update.

Validation: `python -m pytest -q` — full suite passed. Supervisor PID 22468 remains running in UFH continuous mode with `UFH_QUEUE_IDLE` and zero stderr output.

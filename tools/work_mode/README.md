# HomeAura work-mode artifacts

This directory contains machine-readable contracts and reusable templates for
the ChatGPT ↔ Codex ↔ PC workflow.

Files:

- `capabilities.json` — factual capability inventory with verification method
  and timestamp.
- `task_envelope.schema.json` — JSON Schema for ChatGPT-to-Codex jobs.
- `job_state.schema.json` — JSON Schema for local job state.
- `tool_request.template.txt` — safe missing-tool request template.
- `report.template.md` — final evidence report template.

Validation requirements:

1. Parse every JSON file with Python `json.load`.
2. Parse every JSON file with PowerShell `ConvertFrom-Json`.
3. Validate schemas as JSON Schema documents.
4. Validate the task example against `task_envelope.schema.json`.
5. Run a secret scan and create `manifest.sha256`.

No file in this directory grants permission beyond the current user/ChatGPT
job.

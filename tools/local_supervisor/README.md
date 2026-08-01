# HomeAura Local Supervisor

A thin, local-only client that lets a coding subtask be delegated to the local
`qwen2.5-coder:7b` model running under Ollama, without touching Claude Code's
own model configuration.

## What this is

- A direct client of the local Ollama HTTP API (`POST /api/generate`), fixed to
  `http://127.0.0.1:11434`. The base URL is hardcoded, not configurable via a
  flag or environment variable, so this cannot be silently repointed at a
  remote host or a gateway.
- Model-allowlisted: only `qwen2.5-coder:7b` may be called
  (`tools/local_supervisor/supervisor.py::ALLOWED_MODELS`). Any other model
  name is rejected before any network call is made.
- Evidence-generating: every call writes the prompt, response, a sha256 of the
  response and Ollama's own timing stats to
  `reports/local_supervisor/last_call.json` (latest) and
  `reports/local_supervisor/history/call_<timestamp>.json` (history), mirroring
  the snapshot/history pattern already used by `agent/api.py`.

## What this is not

- Not an Anthropic-Messages-compatible gateway, and not a replacement for
  Claude Code's own provider configuration. `ANTHROPIC_BASE_URL` and the
  active Claude Pro session/credentials are never touched by this tool.
- Not a FastAPI endpoint and not wired into `agent/api.py` — it stays off the
  versioned public API surface and its contract obligations.
- Not an autonomous executor. It returns text; nothing here writes to the
  repository, AutoCAD, or engineering project files. Claude Code (or the
  owner) reviews the response before using it for anything.

## Usage

```powershell
& "$root\.venv\Scripts\python.exe" -m tools.local_supervisor.cli --prompt "reply with the single word OK"
& "$root\.venv\Scripts\python.exe" -m tools.local_supervisor.cli --prompt-file task.txt --timeout 180
```

Requires Ollama to be running locally with `qwen2.5-coder:7b` pulled
(`ollama list`).

## Tests

`tests/test_local_supervisor.py` mocks the Ollama transport, so the suite does
not require a live Ollama server.

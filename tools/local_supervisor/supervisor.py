from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
REPORTS_DIRECTORY = ROOT_DIRECTORY / "reports" / "local_supervisor"
HISTORY_DIRECTORY = REPORTS_DIRECTORY / "history"
LAST_CALL_PATH = REPORTS_DIRECTORY / "last_call.json"

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"

DEFAULT_MODEL = "qwen2.5-coder:7b"
ALLOWED_MODELS = frozenset({"qwen2.5-coder:7b"})

DEFAULT_TIMEOUT_SECONDS = 120.0


class LocalSupervisorError(Exception):
    pass


@dataclass(frozen=True)
class LocalSupervisorResult:
    model: str
    prompt: str
    response: str
    total_duration_ns: int | None
    eval_count: int | None
    response_sha256: str
    history_path: Path
    last_call_path: Path


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def _validate_model(model: str) -> str:
    if model not in ALLOWED_MODELS:
        raise LocalSupervisorError(
            "Model '"
            + model
            + "' is not in the HomeAura Local Supervisor allowlist "
            + str(sorted(ALLOWED_MODELS))
            + ". Refusing to call Ollama."
        )
    return model


def _call_ollama(
    model: str,
    prompt: str,
    timeout: float,
) -> dict[str, Any]:
    request_body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_GENERATE_URL,
        data=request_body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            status = getattr(response, "status", 200)
            raw_body = response.read()
    except urllib.error.HTTPError as error:
        raise LocalSupervisorError(
            "Ollama returned HTTP "
            + str(error.code)
            + " for model '"
            + model
            + "'."
        ) from error
    except urllib.error.URLError as error:
        raise LocalSupervisorError(
            "Could not reach local Ollama at "
            + OLLAMA_BASE_URL
            + ": "
            + str(error.reason)
        ) from error
    except TimeoutError as error:
        raise LocalSupervisorError(
            "Local Ollama call timed out after "
            + str(timeout)
            + "s for model '"
            + model
            + "'."
        ) from error

    if status != 200:
        raise LocalSupervisorError(
            "Ollama returned unexpected HTTP status "
            + str(status)
            + " for model '"
            + model
            + "'."
        )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise LocalSupervisorError(
            "Ollama response was not valid JSON."
        ) from error

    if not isinstance(payload, dict):
        raise LocalSupervisorError(
            "Ollama response must be a JSON object."
        )

    return payload


def _write_evidence(
    model: str,
    prompt: str,
    payload: dict[str, Any],
    response_text: str,
    response_sha256: str,
) -> tuple[Path, Path]:
    HISTORY_DIRECTORY.mkdir(parents=True, exist_ok=True)

    record = {
        "supervisor": "HomeAura Local Supervisor",
        "base_url": OLLAMA_BASE_URL,
        "model": model,
        "prompt": prompt,
        "response": response_text,
        "response_sha256": response_sha256,
        "total_duration_ns": payload.get("total_duration"),
        "eval_count": payload.get("eval_count"),
        "eval_duration_ns": payload.get("eval_duration"),
        "done": payload.get("done"),
        "recorded_at": _timestamp(),
    }

    json_text = json.dumps(record, ensure_ascii=False, indent=2)

    history_path = HISTORY_DIRECTORY / f"call_{_timestamp()}.json"
    history_path.write_text(json_text, encoding="utf-8")

    LAST_CALL_PATH.write_text(json_text, encoding="utf-8")

    return LAST_CALL_PATH, history_path


def run_local_task(
    prompt: str,
    model: str = DEFAULT_MODEL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> LocalSupervisorResult:
    validated_model = _validate_model(model)

    payload = _call_ollama(validated_model, prompt, timeout)

    response_text = payload.get("response")
    if not isinstance(response_text, str):
        raise LocalSupervisorError(
            "Ollama response payload has no 'response' text field."
        )

    response_sha256 = hashlib.sha256(
        response_text.encode("utf-8")
    ).hexdigest()

    last_call_path, history_path = _write_evidence(
        validated_model,
        prompt,
        payload,
        response_text,
        response_sha256,
    )

    return LocalSupervisorResult(
        model=validated_model,
        prompt=prompt,
        response=response_text,
        total_duration_ns=payload.get("total_duration"),
        eval_count=payload.get("eval_count"),
        response_sha256=response_sha256,
        history_path=history_path,
        last_call_path=last_call_path,
    )

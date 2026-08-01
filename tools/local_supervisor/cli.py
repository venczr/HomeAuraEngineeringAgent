from __future__ import annotations

import argparse
import sys

from pathlib import Path

from tools.local_supervisor.supervisor import (
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    LocalSupervisorError,
    run_local_task,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local_supervisor",
        description=(
            "HomeAura Local Supervisor: send one coding subtask to the "
            "local qwen2.5-coder:7b model through Ollama at 127.0.0.1. "
            "Claude Code stays the coordinator; review the response "
            "before using it."
        ),
    )

    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument(
        "--prompt",
        type=str,
        help="Prompt text to send to the local model.",
    )
    prompt_group.add_argument(
        "--prompt-file",
        type=Path,
        help="Path to a UTF-8 text file containing the prompt.",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Allowlisted local model name (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=(
            "Request timeout in seconds "
            f"(default: {DEFAULT_TIMEOUT_SECONDS})."
        ),
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.prompt is not None:
        prompt = args.prompt
    else:
        prompt = args.prompt_file.read_text(encoding="utf-8")

    try:
        result = run_local_task(
            prompt=prompt,
            model=args.model,
            timeout=args.timeout,
        )
    except LocalSupervisorError as error:
        print(f"[local_supervisor] error: {error}", file=sys.stderr)
        return 1

    print(result.response)
    print(
        f"[local_supervisor] model={result.model} "
        f"response_sha256={result.response_sha256} "
        f"evidence={result.history_path}",
        file=sys.stderr,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

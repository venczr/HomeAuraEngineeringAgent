#!/usr/bin/env python3
"""HomeAura authoritative verification entry point.

One command that every agent, every developer and CI must use, so a green run
means the same thing everywhere:

    python scripts/verify.py

Checks, in order:
  1. pytest      - the full suite via the pinned pytest.ini harness
  2. schema_export --check - the generated JSON Schemas match the Pydantic models

Design rules this script obeys:
  * never installs anything - a missing dependency is a reported failure, not a
    silent fix, so CI cannot drift from the lock file;
  * never touches the network;
  * never mutates the schemas or the working tree - `--check` is read-only;
  * never hides a failure - the first non-zero exit code is propagated;
  * behaves identically regardless of the caller's working directory;
  * deterministic ordering, no parallelism, no randomised seeds.

Exit codes:
    0  every check passed
    1  at least one check failed (see the summary)
    2  the environment is unusable (wrong interpreter, missing dependency)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

EXIT_OK = 0
EXIT_CHECK_FAILED = 1
EXIT_ENVIRONMENT = 2


class Check:
    def __init__(self, name: str, argv: list[str], description: str) -> None:
        self.name = name
        self.argv = argv
        self.description = description
        self.returncode: int | None = None
        self.duration: float = 0.0


def build_checks(python: str) -> list[Check]:
    return [
        Check(
            "pytest",
            [python, "-m", "pytest"],
            "full test suite via the pinned pytest.ini harness",
        ),
        Check(
            "schema_export",
            [python, "-m", "agent.schema_export", "--check"],
            "generated JSON Schemas match the runtime models (read-only)",
        ),
    ]


def verify_environment(python: str) -> list[str]:
    """Return a list of problems. Empty means the environment is usable."""
    problems: list[str] = []

    if sys.version_info < (3, 12):
        problems.append(
            f"Python 3.12+ required, running {sys.version_info.major}."
            f"{sys.version_info.minor}"
        )

    if not (REPO_ROOT / "pytest.ini").is_file():
        problems.append("pytest.ini is missing - the harness is not pinned")

    if not (REPO_ROOT / "agent" / "schema_export.py").is_file():
        problems.append("agent/schema_export.py is missing")

    probe = subprocess.run(
        [python, "-c", "import pytest"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        problems.append(
            "pytest is not importable. Install the pinned dev dependencies:\n"
            "    python -m pip install -r requirements-dev.lock.txt\n"
            "This script deliberately does NOT install anything for you."
        )

    return problems


def run_check(check: Check, echo: bool) -> int:
    banner = f"[verify] {check.name}: {check.description}"
    print(banner, flush=True)
    print(f"[verify] $ {' '.join(check.argv)}", flush=True)

    started = time.monotonic()
    # Inherit stdio so failures are visible verbatim and nothing is swallowed.
    completed = subprocess.run(check.argv, cwd=REPO_ROOT)
    check.duration = time.monotonic() - started
    check.returncode = completed.returncode

    status = "PASS" if completed.returncode == 0 else f"FAIL (exit {completed.returncode})"
    print(f"[verify] {check.name}: {status} in {check.duration:.2f}s\n", flush=True)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the authoritative HomeAura verification suite."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the checks without running them.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop at the first failing check instead of running them all.",
    )
    args = parser.parse_args(argv)

    python = sys.executable or shutil.which("python") or "python"
    checks = build_checks(python)

    if args.list:
        for check in checks:
            print(f"{check.name}: {check.description}")
        return EXIT_OK

    print(f"[verify] repository: {REPO_ROOT}")
    print(f"[verify] interpreter: {python}")
    print(f"[verify] python: {sys.version.split()[0]}\n", flush=True)

    problems = verify_environment(python)
    if problems:
        print("[verify] ENVIRONMENT NOT USABLE:", flush=True)
        for problem in problems:
            print(f"  - {problem}", flush=True)
        return EXIT_ENVIRONMENT

    failed: list[Check] = []
    for check in checks:
        if run_check(check, echo=True) != 0:
            failed.append(check)
            if args.fail_fast:
                break

    print("[verify] " + "-" * 60)
    for check in checks:
        if check.returncode is None:
            print(f"[verify]   {check.name:<16} SKIPPED")
        else:
            state = "PASS" if check.returncode == 0 else "FAIL"
            print(f"[verify]   {check.name:<16} {state:<4} ({check.duration:.2f}s)")

    if failed:
        names = ", ".join(check.name for check in failed)
        print(f"[verify] RESULT: FAILED ({names})", flush=True)
        return EXIT_CHECK_FAILED

    print("[verify] RESULT: ALL CHECKS PASSED", flush=True)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import subprocess
import sys

from pathlib import Path

import yaml


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT_DIRECTORY / ".github" / "workflows" / "verification.yml"
RUNTIME_LOCK_PATH = ROOT_DIRECTORY / "requirements.lock.txt"
DEV_INPUT_PATH = ROOT_DIRECTORY / "requirements-dev.in"
DEV_LOCK_PATH = ROOT_DIRECTORY / "requirements-dev.lock.txt"


def _workflow() -> dict:
    # BaseLoader follows GitHub's string-oriented YAML interpretation and avoids
    # YAML 1.1 treating the key `on` as the boolean True.
    return yaml.load(
        WORKFLOW_PATH.read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )


def test_workflow_has_read_only_permissions_and_expected_triggers() -> None:
    workflow = _workflow()

    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["on"]) == {
        "push",
        "pull_request",
        "workflow_dispatch",
    }
    assert workflow["on"]["push"]["branches"] == [
        "feature/room-geometry"
    ]


def test_workflow_runner_matches_platform_specific_runtime_lock() -> None:
    runtime_requirements = RUNTIME_LOCK_PATH.read_text(
        encoding="utf-8"
    ).splitlines()
    assert "pywin32==312" in runtime_requirements
    assert _workflow()["jobs"]["verify"]["runs-on"] == "windows-latest"


def test_workflow_uses_authoritative_gate_without_write_credentials() -> None:
    steps = _workflow()["jobs"]["verify"]["steps"]

    checkout = next(
        step
        for step in steps
        if step.get("uses", "").startswith("actions/checkout@")
    )
    assert checkout["with"]["persist-credentials"] == "false"
    assert any(
        step.get("run") == "python scripts/verify.py" for step in steps
    )

    executable_text = "\n".join(
        str(step.get(field, ""))
        for step in steps
        for field in ("uses", "run")
    ).lower()
    for forbidden in ("secrets.", "id-token:", "git push", "gh ", "deploy"):
        assert forbidden not in executable_text


def test_dev_requirements_are_constrained_and_pytest_is_pinned() -> None:
    assert DEV_INPUT_PATH.read_text(encoding="utf-8").splitlines() == [
        "-c requirements.lock.txt",
        "",
        "pytest",
    ]
    assert "pytest==9.1.1" in DEV_LOCK_PATH.read_text(
        encoding="utf-8"
    ).splitlines()


def test_authoritative_gate_lists_checks_from_unrelated_directory(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT_DIRECTORY / "scripts" / "verify.py"), "--list"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "pytest: full test suite via the pinned pytest.ini harness",
        "schema_export: generated JSON Schemas match the runtime models (read-only)",
        (
            "room_geometry_build: rebuild the .NET Framework 4.8 "
            "room geometry harness"
        ),
        "room_geometry_tests: execute the rebuilt C# room geometry regressions",
    ]

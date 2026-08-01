from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = ROOT_DIRECTORY / "scripts" / "start_agent_api.ps1"
MISSING_VALUE_MARKER = "__HOMEAURA_TEST_MISSING__"


@pytest.mark.parametrize("initial_python_utf8", [None, "sentinel-value"])
def test_launcher_restores_caller_state_with_fake_executable(
    tmp_path: Path,
    initial_python_utf8: str | None,
) -> None:
    fake_executable = shutil.which("where.exe")
    assert fake_executable is not None

    synthetic_root = tmp_path / "synthetic-project"
    scripts_directory = synthetic_root / "scripts"
    python_directory = synthetic_root / ".venv" / "Scripts"
    scripts_directory.mkdir(parents=True)
    python_directory.mkdir(parents=True)

    launcher_copy = scripts_directory / LAUNCHER_PATH.name
    shutil.copy2(LAUNCHER_PATH, launcher_copy)
    shutil.copy2(fake_executable, python_directory / "python.exe")

    command = r"""
$tokens = $null
$parseErrors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    $env:HOMEAURA_TEST_LAUNCHER,
    [ref]$tokens,
    [ref]$parseErrors
) | Out-Null
if ($parseErrors.Count -ne 0) {
    throw "launcher parser errors: $($parseErrors.Count)"
}

$originalLocation = (Get-Location).Path
$originalEncoding = [Console]::OutputEncoding.CodePage
if ($env:HOMEAURA_TEST_INITIAL_UTF8 -eq $env:HOMEAURA_TEST_MISSING) {
    Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue
}
else {
    $env:PYTHONUTF8 = $env:HOMEAURA_TEST_INITIAL_UTF8
}

& $env:HOMEAURA_TEST_LAUNCHER *> $null

if ((Get-Location).Path -ne $originalLocation) {
    throw "working directory was not restored"
}
if ([Console]::OutputEncoding.CodePage -ne $originalEncoding) {
    throw "console output encoding was not restored"
}
if ($env:HOMEAURA_TEST_INITIAL_UTF8 -eq $env:HOMEAURA_TEST_MISSING) {
    if (Test-Path Env:PYTHONUTF8) {
        throw "absent PYTHONUTF8 was not restored"
    }
}
elseif ($env:PYTHONUTF8 -ne $env:HOMEAURA_TEST_INITIAL_UTF8) {
    throw "existing PYTHONUTF8 was not restored"
}
"PASS"
"""

    environment = os.environ.copy()
    environment["HOMEAURA_TEST_LAUNCHER"] = str(launcher_copy)
    environment["HOMEAURA_TEST_MISSING"] = MISSING_VALUE_MARKER
    environment["HOMEAURA_TEST_INITIAL_UTF8"] = (
        MISSING_VALUE_MARKER
        if initial_python_utf8 is None
        else initial_python_utf8
    )

    completed = subprocess.run(
        [
            "powershell",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            command,
        ],
        cwd=ROOT_DIRECTORY,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, (
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
    assert completed.stdout.strip() == "PASS"

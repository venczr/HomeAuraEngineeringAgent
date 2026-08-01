from __future__ import annotations

from pathlib import Path

import pytest


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
PLUGIN_DIRECTORY = (
    ROOT_DIRECTORY
    / "autocad-plugin"
    / "HomeAura.AutoCAD.Agent"
    / "HomeAura.AutoCAD.Agent"
)
HTTP_CALL_SITES = (
    "AgentApiProcessManager.cs",
    "SyncCommands.cs",
    "RoomSyncCommands.cs",
    "AnalyzeCommands.cs",
)


@pytest.mark.parametrize("file_name", HTTP_CALL_SITES)
def test_local_http_calls_complete_after_headers(file_name: str) -> None:
    source = (PLUGIN_DIRECTORY / file_name).read_text(encoding="utf-8")

    assert ".GetAsync(" not in source
    assert ".PostAsync(" not in source
    assert source.count("ResponseHeadersRead") == 1

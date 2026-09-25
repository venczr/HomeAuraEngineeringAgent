import json
from pathlib import Path

from tools.autonomous_supervisor.ufh_queue import sync_ufh_queue
from tools.autonomous_supervisor.supervisor import select_ufh


def test_ufh_queue_bridge_creates_ready_and_deferred_tasks(tmp_path: Path):
    queue = tmp_path / "continuation_queue.json"
    state = tmp_path / "state.json"
    queue.write_text(json.dumps({"last_completed_block": "x", "queue": [
        {"id": "READY", "status": "READY", "next_action": "do ready", "completion_condition": "done"},
        {"id": "BLOCKED", "status": "BLOCKED_BY_SOURCE", "next_action": "wait", "completion_condition": "source"},
    ]}), encoding="utf-8")
    state.write_text(json.dumps({"TASK_QUEUE": [], "DONE": [], "BLOCKED": [], "FAILED": []}), encoding="utf-8")
    result = sync_ufh_queue(queue_path=queue, state_path=state)
    assert result["created"] == ["UFH-READY", "UFH-BLOCKED"]
    payload = json.loads(state.read_text(encoding="utf-8"))
    assert payload["TASK_QUEUE"][0]["status"] == "READY"
    assert payload["TASK_QUEUE"][1]["status"] == "DEFERRED"


def test_ufh_queue_bridge_is_idempotent(tmp_path: Path):
    queue = tmp_path / "continuation_queue.json"
    state = tmp_path / "state.json"
    queue.write_text(json.dumps({"queue": [{"id": "ONE", "status": "READY", "next_action": "do", "completion_condition": "done"}]}), encoding="utf-8")
    state.write_text(json.dumps({"TASK_QUEUE": [], "DONE": [], "BLOCKED": [], "FAILED": []}), encoding="utf-8")
    assert len(sync_ufh_queue(queue_path=queue, state_path=state)["created"]) == 1
    assert sync_ufh_queue(queue_path=queue, state_path=state)["created"] == []


def test_detached_launcher_exposes_ufh_switch():
    source = (Path(__file__).resolve().parents[1] / "tools" / "autonomous_supervisor" / "detached_launcher.py").read_text(encoding="utf-8")
    assert "--ufh" in source
    assert "--hours" in source
    assert "default=0" in source


def test_ufh_mode_selects_only_ufh_tasks():
    state = {"TASK_QUEUE": [
        {"id": "P9", "status": "READY", "attempt_count": 0, "dependencies": [], "priority": 0},
        {"id": "UFH-STAIR", "status": "READY", "attempt_count": 0, "dependencies": [], "priority": 1},
    ], "DONE": []}
    assert select_ufh(state)["id"] == "UFH-STAIR"


def test_ufh_sync_rearms_budget_only_block(tmp_path: Path):
    queue = tmp_path / "continuation_queue.json"
    state = tmp_path / "state.json"
    queue.write_text(json.dumps({"queue": [{"id": "STAIR", "status": "READY", "next_action": "retry", "completion_condition": "done"}]}), encoding="utf-8")
    state.write_text(json.dumps({"TASK_QUEUE": [{"id": "UFH-STAIR", "status": "BLOCKED", "blockers": ["PRIMARY_CONSECUTIVE_FAILURE_BUDGET"], "attempt_count": 1}], "DONE": [], "BLOCKED": [], "FAILED": []}), encoding="utf-8")
    sync_ufh_queue(queue_path=queue, state_path=state)
    payload = json.loads(state.read_text(encoding="utf-8"))
    assert payload["TASK_QUEUE"][0]["status"] == "READY"


def test_ufh_profile_does_not_use_global_one_failure_stop():
    source = (Path(__file__).resolve().parents[1] / "tools" / "autonomous_supervisor" / "cli.py").read_text(encoding="utf-8")
    assert "and not ufh" in source

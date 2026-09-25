"""Bridge the UFH continuation queue into the durable autonomous supervisor."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "dev" / "ufh_real_plan" / "continuation_queue.json"
STATE_PATH = ROOT / "dev" / "autonomous" / "state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_ufh_queue(path: Path = QUEUE_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sync_ufh_queue(*, queue_path: Path = QUEUE_PATH, state_path: Path = STATE_PATH) -> dict:
    queue = load_ufh_queue(queue_path)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {
        "TASK_QUEUE": [], "DONE": [], "BLOCKED": [], "FAILED": []
    }
    tasks = state.setdefault("TASK_QUEUE", [])
    existing = {task.get("id"): task for task in tasks}
    created = []
    for index, item in enumerate(queue.get("queue", []), start=1):
        task_id = item['id'] if item['id'].startswith('UFH-') else f"UFH-{item['id']}"
        source_status = item.get("status", "READY")
        if task_id in existing:
            task = existing[task_id]
            task["goal"] = item["next_action"]
            task["completion_condition"] = item["completion_condition"]
            task["source_queue_status"] = item["status"]
            if source_status == "READY" and task.get("status") == "BLOCKED" and task.get("blockers") == ["PRIMARY_CONSECUTIVE_FAILURE_BUDGET"]:
                task["status"] = "READY"
                task["blockers"] = []
                task["next_retry_condition"] = "UFH bounded profile retry."
            task["updated_at"] = _now()
            continue
        task = {
            "id": task_id,
            "title": item["id"],
            "goal": item["next_action"],
            "completion_condition": item["completion_condition"],
            "priority": index,
            "status": "READY" if source_status == "READY" else "DEFERRED",
            "dependencies": [],
            "blockers": [] if source_status == "READY" else [source_status],
            "evidence": [f"UFH continuation queue: {queue.get('last_completed_block', '')}"],
            "files": ["dev/ufh_real_plan/continuation_queue.json", "scripts/build_real_floor_ufh_artifacts.py"],
            "tests": ["tests/test_ufh_physical_artifacts.py"],
            "attempt_count": 0,
            "last_attempt": None,
            "next_retry_condition": None,
            "created_at": _now(),
            "updated_at": _now(),
            "source_queue_status": source_status,
        }
        tasks.append(task)
        created.append(task_id)
    state["UFH_QUEUE_SYNC_AT"] = _now()
    state["UFH_QUEUE_SOURCE"] = _display_path(queue_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(state_path)
    return {"created": created, "task_count": len(tasks), "queue_source": _display_path(queue_path)}


if __name__ == "__main__":
    print(json.dumps(sync_ufh_queue(), ensure_ascii=False, indent=2))

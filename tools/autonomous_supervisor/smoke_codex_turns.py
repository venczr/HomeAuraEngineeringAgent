from __future__ import annotations
import json
from pathlib import Path
from tools.autonomous_supervisor.codex_runner import ROOT, run_codex

tmp = ROOT / "reports" / "tmp"
tmp.mkdir(parents=True, exist_ok=True)
packet = "AUTONOMOUS_RUN_ID=codex-turn-smoke; MCP_AVAILABLE=true; STOP_RULES=bounded task only. "
turn_a = run_codex(packet + "CURRENT_TASK=TURN-A. Read tools/tokenwave_mcp/config.json and tests/test_tokenwave_router.py. Create reports/tmp/codex_turn_a_checkpoint.json with TASK_STATUS=COMPLETED, a deterministic count of configured role mappings, VERIFIED facts, TEST_RESULT after running pytest -q tests/test_tokenwave_router.py, NEW_BLOCKERS, NEXT_RECOMMENDATION. Do not edit product code.", run_id="turn-a", timeout_seconds=240)
if turn_a.exit_code != 0 or turn_a.timed_out or not (tmp / "codex_turn_a_checkpoint.json").exists() or not turn_a.session_id:
    raise SystemExit("TURN_A_FAILED")
turn_b = run_codex(packet + "CURRENT_TASK=TURN-B. Restore facts from reports/tmp/codex_turn_a_checkpoint.json. Perform a different repository task: inspect dev/autonomous/state.json queue consistency, run pytest -q tests/test_local_supervisor.py tests/test_autonomous_codex_runner.py, and create reports/tmp/codex_turn_b_checkpoint.json with TASK_STATUS=COMPLETED, restored_from, VERIFIED, TEST_RESULT, NEW_BLOCKERS, NEXT_RECOMMENDATION. Do not edit product code.", run_id="turn-b", timeout_seconds=240, resume_session=turn_a.session_id)
if turn_b.exit_code != 0 or turn_b.timed_out or not (tmp / "codex_turn_b_checkpoint.json").exists():
    raise SystemExit("TURN_B_FAILED")
artifact = {"turn_a": turn_a.__dict__, "checkpoint_a": json.loads((tmp / "codex_turn_a_checkpoint.json").read_text(encoding="utf-8")), "turn_b": turn_b.__dict__, "checkpoint_b": json.loads((tmp / "codex_turn_b_checkpoint.json").read_text(encoding="utf-8"))}
(tmp / "autonomous_codex_turn_smoke.json").write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"turn_a":"COMPLETED","turn_b":"COMPLETED","artifact":"reports/tmp/autonomous_codex_turn_smoke.json"}))

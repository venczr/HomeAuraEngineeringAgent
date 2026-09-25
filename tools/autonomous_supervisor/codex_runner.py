from __future__ import annotations

import json
import os
import signal
import subprocess
import time
import shutil
import copy
import sys
import ctypes
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "dev" / "autonomous" / "codex_runs"
POLICY_PATH = Path(__file__).with_name("policy.json")
TELEMETRY = ROOT / "dev" / "autonomous" / "primary_turns.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _path_string(path: Path) -> str:
    try:return str(path.relative_to(ROOT))
    except ValueError:return str(path)

def is_process_alive(pid: int) -> bool:
    """Existence probe; never uses signal 0 on native Windows."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if sys.platform != 'win32':
        try: os.kill(pid, 0); return True
        except ProcessLookupError: return False
        except PermissionError: return True
        except OSError: return False
    PROCESS_QUERY_LIMITED_INFORMATION=0x1000
    ERROR_INVALID_PARAMETER=87
    kernel32=ctypes.WinDLL('kernel32', use_last_error=True)
    handle=kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        error=ctypes.get_last_error()
        if error==ERROR_INVALID_PARAMETER: return False
        if error in (5,): return True
        return False
    try:
        exit_code=ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return True
        return exit_code.value==259
    finally:
        kernel32.CloseHandle(handle)


@dataclass
class CodexRun:
    run_id: str
    pid: int
    command: list[str]
    started_at: str
    completed_at: str | None
    last_progress_at: str
    exit_code: int | None
    timed_out: bool
    output_path: str
    last_message_path: str
    session_id: str | None
    primary_model: str
    fresh_or_resume: str
    packet_chars: int
    input_tokens: int | None
    output_tokens: int | None
    cached_input_tokens: int | None
    usage_actual: bool
    elapsed_seconds: float | None
    completion_contract_seen: bool = False
    process_exit_code_known: bool = True
    task_result_status: str | None = None
    terminal_event: str | None = None
    termination_reason: str = "UNKNOWN"
    protected_paths_changed: list[str] = None
    item_count: int = 0
    command_item_count: int = 0
    jsonl_bytes: int = 0
    budget_exceeded: bool = False
    control_plane_mutation_detected: bool = False
    descendant_pids: list[int] = None


def _session_id(log_path: Path) -> str | None:
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("type") == "thread.started":
            return item.get("thread_id")
    return None

def _usage(log_path: Path) -> dict:
    for line in reversed(log_path.read_text(encoding="utf-8", errors="replace").splitlines()):
        try:item=json.loads(line)
        except json.JSONDecodeError:continue
        if item.get("type")=="turn.completed" and isinstance(item.get("usage"),dict):return item["usage"]
    return {}

def _task_result(path: Path | None, assigned_task_id: str | None = None) -> dict:
    if path is None or not path.is_file():return {}
    try:value=json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError,json.JSONDecodeError):return {}
    if not isinstance(value,dict) or value.get("TASK_STATUS") not in {"COMPLETED","BLOCKED","FAILED_RETRYABLE"}:return {}
    if assigned_task_id is not None:
        if value.get('TASK_ID')!=assigned_task_id:return {}
        required=('PROGRESS','VERIFIED','TEST_RESULT','NEW_BLOCKERS','NEXT_RECOMMENDATION','FILES_CHANGED')
        if any(key not in value for key in required):return {}
        if not isinstance(value['VERIFIED'],list) or not isinstance(value['NEW_BLOCKERS'],list):return {}
    return value

def _harvest_final_contract(message_path: Path | None, completion_path: Path | None,
                            assigned_task_id: str | None) -> dict:
    """Accept a valid task contract returned as final text when child tools are unavailable."""
    if message_path is None or completion_path is None or not message_path.is_file():
        return {}
    try:
        text = message_path.read_text(encoding='utf-8-sig', errors='replace')
    except OSError:
        return {}
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != '{':
            continue
        try:
            candidate, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if not isinstance(candidate, dict):
            continue
        if candidate.get('TASK_ID') != assigned_task_id:
            continue
        if candidate.get('TASK_STATUS') not in {'COMPLETED','BLOCKED','FAILED_RETRYABLE'}:
            continue
        required=('PROGRESS','VERIFIED','TEST_RESULT','NEW_BLOCKERS','NEXT_RECOMMENDATION','FILES_CHANGED')
        if any(key not in candidate for key in required):
            continue
        completion_path.parent.mkdir(parents=True, exist_ok=True)
        completion_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding='utf-8')
        return candidate
    return {}

def protected_snapshot() -> dict:
    paths=[Path('dev/autonomous/state.json'),Path('dev/autonomous/supervisor.pid'),Path('dev/autonomous/supervisor_heartbeat.json'),Path('dev/autonomous/supervisor_events.jsonl'),Path('dev/autonomous/primary_turns.jsonl'),Path('tools/autonomous_supervisor/policy.json')]
    result={}
    for path in paths:
        absolute=ROOT/path
        result[str(path)]={'exists': absolute.is_file(), 'data': absolute.read_bytes().hex() if absolute.is_file() else None}
    return result

def restore_protected_snapshot(snapshot: dict, *, allowed_run_id: str | None = None) -> list[str]:
    changed=[]
    for relative,entry in snapshot.items():
        path=ROOT/relative
        expected_exists=entry.get('exists',False); encoded=entry.get('data')
        current=path.read_bytes().hex() if path.is_file() else None
        if expected_exists and current != encoded:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(bytes.fromhex(encoded));changed.append(relative)
        elif not expected_exists and path.exists():
            path.unlink();changed.append(relative)
    return changed

def validate_task_result(result: dict, assigned_task_id: str, run: CodexRun) -> tuple[bool,str]:
    if not isinstance(result, dict): return False, 'CONTRACT_NOT_SATISFIED'
    if not run.completion_contract_seen: return False, 'CONTRACT_NOT_SATISFIED'
    if result.get('TASK_ID') != assigned_task_id: return False, 'TASK_ID_MISMATCH'
    if result.get('TASK_STATUS') not in {'COMPLETED','BLOCKED','FAILED_RETRYABLE'}: return False, 'CONTRACT_NOT_SATISFIED'
    for key in ('PROGRESS','VERIFIED','TEST_RESULT','NEW_BLOCKERS','NEXT_RECOMMENDATION','FILES_CHANGED'):
        if key not in result: return False, 'CONTRACT_NOT_SATISFIED'
    if not isinstance(result['VERIFIED'],list) or not isinstance(result['NEW_BLOCKERS'],list): return False, 'CONTRACT_NOT_SATISFIED'
    if run.protected_paths_changed: return False, 'CONTROL_PLANE_MUTATION_ATTEMPT'
    return True, 'OK'

def classify_termination(*, exited_naturally: bool, grace_expired: bool,
                         forced: bool, provider_failed: bool = False) -> str:
    if forced: return "FORCED_TERMINATION"
    if provider_failed: return "PROVIDER_FAILURE"
    if exited_naturally: return "NATURAL_EXIT"
    if grace_expired: return "GRACEFUL_TIMEOUT_TERMINATION"
    return "UNKNOWN"

def _terminate_bounded(process, *, graceful_reason="GRACEFUL_TERMINATION") -> str:
    """Best-effort termination; signal/handle failures never escape."""
    if process.poll() is not None:
        return "NATURAL_EXIT"
    try:
        process.send_signal(signal.CTRL_BREAK_EVENT)
    except BaseException:
        try:
            process.terminate()
        except BaseException:
            pass
        try:
            process.wait(timeout=5)
            return "TERMINATION_SIGNAL_FAILED_RECOVERED"
        except BaseException:
            pass
    else:
        try:
            process.wait(timeout=5)
            return graceful_reason
        except BaseException:
            pass
    try:
        process.kill()
    except BaseException:
        pass
    try:
        process.wait(timeout=5)
    except BaseException:
        pass
    return "FORCED_PROCESS_TREE_KILL"

def load_policy() -> dict:
 return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

def codex_capabilities() -> dict:
    codex=shutil.which('codex.cmd') or shutil.which('codex')
    if not codex: return {'model_override_supported':False,'reasoning_override_supported':False}
    try: help_text=subprocess.run([codex,'exec','--help'],capture_output=True,text=True,timeout=10).stdout
    except (OSError,subprocess.SubprocessError): help_text=''
    return {'model_override_supported':'-m, --model' in help_text,
            'reasoning_override_supported':True}

def build_child_argv(*, model: str, reasoning_effort: str | None = None,
                     message_path: Path, prompt: str) -> list[str]:
    codex=shutil.which('codex.cmd') or shutil.which('codex') or 'codex.cmd'
    argv=[codex,'exec','--approve-for-me','--skip-git-repo-check','-m',model,'--json','-C',str(ROOT),'-o',str(message_path)]
    if reasoning_effort: argv += ['-c',f'model_reasoning_effort="{reasoning_effort}"']
    argv.append(prompt); return argv

def validate_primary_budget(policy: dict, *, run_count: int, recent_count: int,
                            astra_count: int, packet_chars: int,
                            requested_model: str | None = None) -> str:
    budget = policy["budgets"]
    if requested_model == policy["models"]["ESCALATION"] and astra_count >= budget["max_primary_astra_turns_per_run"]:
        return "PRIMARY_ASTRA_BUDGET_EXHAUSTED"
    if run_count >= budget["max_primary_turns_per_run"]:
        return "PRIMARY_RUN_BUDGET_EXHAUSTED"
    if recent_count >= budget["max_primary_turns_per_hour"]:
        return "PRIMARY_HOURLY_BUDGET_EXHAUSTED"
    if packet_chars > budget["max_primary_packet_chars"]:
        return "PRIMARY_TASK_PACKET_LIMIT_EXCEEDED"
    return "OK"


def run_codex(prompt: str, *, run_id: str, timeout_seconds: int = 300,
              resume_session: str | None = None,
              completion_path: Path | None = None,
              assigned_task_id: str | None = None,
              primary_model: str | None = None,
              allow_astra: bool = False, completion_grace_seconds: int = 20,
              limits: dict | None = None, reasoning_effort: str | None = None) -> CodexRun:
    policy=load_policy();model=primary_model or policy["models"]["AUTONOMOUS_PRIMARY"]
    limit=policy["budgets"]["max_primary_packet_chars"]
    if len(prompt)>limit:raise ValueError(f"PRIMARY_TASK_PACKET_LIMIT_EXCEEDED:{len(prompt)}>{limit}")
    if model==policy["models"]["ESCALATION"]:
        if not allow_astra:raise ValueError("PRIMARY_ASTRA_NOT_AUTHORIZED")
        if policy["budgets"]["max_primary_astra_turns_per_run"] <= 0:raise ValueError("PRIMARY_ASTRA_BUDGET_EXHAUSTED")
    RUNS.mkdir(parents=True, exist_ok=True)
    log_path = RUNS / f"{run_id}.jsonl"
    message_path = RUNS / f"{run_id}.last.txt"
    state_path = RUNS / f"{run_id}.state.json"
    codex = shutil.which("codex.cmd") or shutil.which("codex")
    if not codex:
        raise FileNotFoundError("Codex CLI executable was not found.")
    if resume_session:
        command = [codex, "exec", "resume", "--skip-git-repo-check", "--json", "-m", model,
                   "-o", str(message_path), resume_session, prompt]
    else:
        command = build_child_argv(model=model,reasoning_effort=reasoning_effort,message_path=message_path,prompt=prompt)
    started = _now(); protected_before=protected_snapshot()
    with log_path.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                   stdout=output, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        result = CodexRun(
            run_id=run_id, pid=process.pid, command=command, started_at=started,
            completed_at=None, last_progress_at=started, exit_code=None,
            timed_out=False, output_path=_path_string(log_path),
            last_message_path=_path_string(message_path), session_id=None,
            primary_model=model, fresh_or_resume="resume" if resume_session else "fresh",
            packet_chars=len(prompt), input_tokens=None, output_tokens=None,
            cached_input_tokens=None, usage_actual=False, elapsed_seconds=None,
            completion_contract_seen=False, process_exit_code_known=False,
            task_result_status=None, terminal_event=None, termination_reason="UNKNOWN",
            protected_paths_changed=[], item_count=0, command_item_count=0, jsonl_bytes=0,
        )
        state_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
        deadline = time.monotonic() + timeout_seconds
        previous_size = -1
        turn_started_monotonic = time.monotonic();last_progress_monotonic=turn_started_monotonic
        seen_lines=0;consecutive_provider_errors=0;provider_error_storm=False
        budget=limits or policy["budgets"]
        max_seconds=budget.get("max_primary_wall_seconds",timeout_seconds)
        max_items=budget.get("max_primary_agent_items",10**9)
        max_commands=budget.get("max_primary_command_items",10**9)
        max_bytes=budget.get("max_primary_jsonl_bytes",10**12)
        no_progress=budget.get("max_primary_no_progress_seconds",timeout_seconds)
        budget_exceeded=False
        completed_by_contract = False
        while process.poll() is None and time.monotonic() < deadline:
            size = log_path.stat().st_size
            if size != previous_size:
                previous_size = size
                state_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
            lines=log_path.read_text(encoding="utf-8",errors="replace").splitlines()
            for line in lines[seen_lines:]:
                try:item=json.loads(line)
                except json.JSONDecodeError:continue
                if item.get('type')=='error':
                    consecutive_provider_errors+=1
                else:
                    consecutive_provider_errors=0;last_progress_monotonic=time.monotonic();result.last_progress_at=_now()
            seen_lines=len(lines)
            result.item_count=sum('"type":"item.' in line for line in lines)
            result.command_item_count=sum('"type":"item.completed"' in line and '"type":"command_execution"' in line for line in lines)
            result.jsonl_bytes=size
            if consecutive_provider_errors>=5:
                provider_error_storm=True;result.termination_reason="PROVIDER_ERROR_STORM";break
            if (time.monotonic()-turn_started_monotonic>max_seconds or result.item_count>max_items or result.command_item_count>max_commands or size>max_bytes or time.monotonic()-last_progress_monotonic>no_progress):
                budget_exceeded=True;result.termination_reason="PRIMARY_INTRA_TURN_BUDGET_EXCEEDED";break
            task_result=_task_result(completion_path,assigned_task_id)
            if task_result:
                completed_by_contract = True
                result.task_result_status=task_result["TASK_STATUS"]
                grace_deadline = time.monotonic() + completion_grace_seconds
                while process.poll() is None and time.monotonic() < grace_deadline: time.sleep(0.5)
                if process.poll() is None:
                    result.termination_reason = _terminate_bounded(process, graceful_reason="GRACEFUL_TIMEOUT_TERMINATION")
                else: result.termination_reason="NATURAL_EXIT"
                break
            time.sleep(1)
        result.budget_exceeded = budget_exceeded
        if provider_error_storm and process.poll() is None:
            result.timed_out=False
            _terminate_bounded(process, graceful_reason="PROVIDER_ERROR_STORM")
            result.termination_reason="PROVIDER_ERROR_STORM"
        elif budget_exceeded and process.poll() is None:
            result.timed_out=False
            result.termination_reason = _terminate_bounded(process, graceful_reason="GRACEFUL_TERMINATION")
        elif process.poll() is None:
            result.timed_out = True
            result.termination_reason = "HARD_TIMEOUT"
            result.termination_reason = _terminate_bounded(process, graceful_reason="GRACEFUL_TERMINATION")
        result.exit_code = process.returncode
        result.completion_contract_seen = completed_by_contract
        result.process_exit_code_known = process.returncode is not None
    if not completed_by_contract:
        harvested = _harvest_final_contract(message_path, completion_path, assigned_task_id)
        if harvested:
            completed_by_contract = True
            result.task_result_status = harvested.get('TASK_STATUS')
    result.completed_at = _now()
    result.session_id = _session_id(log_path)
    result.protected_paths_changed=restore_protected_snapshot(protected_before, allowed_run_id=run_id)
    result.control_plane_mutation_detected=bool(result.protected_paths_changed)
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:item=json.loads(line)
        except json.JSONDecodeError:continue
        if item.get("type") in {"turn.completed","turn.failed"}: result.terminal_event=item["type"]
    usage=_usage(log_path);result.input_tokens=usage.get("input_tokens");result.output_tokens=usage.get("output_tokens");result.cached_input_tokens=usage.get("cached_input_tokens");result.usage_actual=bool(usage)
    result.elapsed_seconds=(datetime.fromisoformat(result.completed_at)-datetime.fromisoformat(result.started_at)).total_seconds()
    if result.termination_reason == "UNKNOWN": result.termination_reason = "PROVIDER_FAILURE" if result.exit_code not in (0,None) else "NATURAL_EXIT"
    state_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    TELEMETRY.parent.mkdir(parents=True,exist_ok=True)
    with TELEMETRY.open("a",encoding="utf-8") as f:f.write(json.dumps(asdict(result),ensure_ascii=False)+"\n")
    return result


def recover_stale_tasks(state: dict) -> list[str]:
    recovered = []
    for task in state.get("TASK_QUEUE", []):
        if task.get("status") == "RUNNING":
            task["status"] = "FAILED_RETRYABLE"
            task["blockers"] = list(task.get("blockers", [])) + ["STALE_RUNNING_RECOVERED_AFTER_SUPERVISOR_RESTART"]
            task["next_retry_condition"] = "Supervisor restart completed; retry with bounded runner."
            task["updated_at"] = _now()
            recovered.append(task["id"])
    if recovered:
        state["CURRENT_TASK"] = None
        state["CONSECUTIVE_FAILURES"] = state.get("CONSECUTIVE_FAILURES", 0) + len(recovered)
    return recovered

def recover_owned_orphans(*, runs_dir: Path = RUNS, dry_run: bool = False) -> list[int]:
    """Terminate only recorded autonomous Codex roots whose command carries run identity."""
    recovered=[]; records=[]
    if not runs_dir.exists(): return recovered
    for state_path in runs_dir.glob('*.state.json'):
        try: record=json.loads(state_path.read_text(encoding='utf-8-sig'))
        except (OSError,json.JSONDecodeError): continue
        pid=record.get('pid'); run_id=record.get('run_id')
        if not isinstance(pid,int) or not run_id: continue
        records.append((pid,run_id,state_path))
    candidates=[]
    for pid,run_id,state_path in records:
        if is_process_alive(pid): candidates.append((pid,run_id,state_path))
    if sys.platform == 'win32' and records:
        script="Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress"
        try:
            probe=subprocess.run(['powershell','-NoProfile','-Command',script],capture_output=True,text=True,timeout=5)
            rows=json.loads(probe.stdout or '[]'); rows=rows if isinstance(rows,list) else [rows]
        except Exception: rows=[]
        for row in rows:
            command=str(row.get('CommandLine') or ''); candidate_pid=row.get('ProcessId')
            if str(row.get('Name') or '').lower() not in {'codex.exe','node.exe'}: continue
            for _,run_id,state_path in records:
                if isinstance(candidate_pid,int) and run_id in command and '.last.txt' in command:
                    candidates.append((candidate_pid,run_id,state_path));break
    for pid,run_id,state_path in candidates:
        if pid in recovered: continue
        recovered.append(pid)
        if not dry_run:
            subprocess.run(['taskkill','/PID',str(pid),'/T','/F'],capture_output=True,timeout=10)
    return recovered

import pytest
import json
from tools.autonomous_supervisor.codex_runner import recover_stale_tasks,run_codex,load_policy,validate_primary_budget,classify_termination,is_process_alive,recover_owned_orphans,_task_result
from tools.autonomous_supervisor.codex_runner import _terminate_bounded


def test_restart_recovers_stale_running_task() -> None:
    state = {"CURRENT_TASK": "A", "CONSECUTIVE_FAILURES": 0,
             "TASK_QUEUE": [{"id": "A", "status": "RUNNING", "blockers": []}]}
    assert recover_stale_tasks(state) == ["A"]
    assert state["CURRENT_TASK"] is None
    assert state["TASK_QUEUE"][0]["status"] == "FAILED_RETRYABLE"

def test_primary_model_is_cheap_and_astra_requires_authorization() -> None:
    policy=load_policy()
    assert policy["models"]["AUTONOMOUS_PRIMARY"] != policy["models"]["ESCALATION"]
    with pytest.raises(ValueError,match="PRIMARY_ASTRA_NOT_AUTHORIZED"):
        run_codex("x",run_id="guard",primary_model=policy["models"]["ESCALATION"])
    with pytest.raises(ValueError,match="PRIMARY_ASTRA_BUDGET_EXHAUSTED"):
        run_codex("x",run_id="guard-budget",primary_model=policy["models"]["ESCALATION"],allow_astra=True)

def test_primary_packet_limit_is_enforced() -> None:
    policy=load_policy();limit=policy["budgets"]["max_primary_packet_chars"]
    with pytest.raises(ValueError,match="PRIMARY_TASK_PACKET_LIMIT_EXCEEDED"):
        run_codex("x"*(limit+1),run_id="packet-limit")

def test_primary_budget_guards_are_enforced() -> None:
    p=load_policy(); b=p["budgets"]
    assert validate_primary_budget(p,run_count=b["max_primary_turns_per_run"],recent_count=0,astra_count=0,packet_chars=1)=="PRIMARY_RUN_BUDGET_EXHAUSTED"
    assert validate_primary_budget(p,run_count=0,recent_count=b["max_primary_turns_per_hour"],astra_count=0,packet_chars=1)=="PRIMARY_HOURLY_BUDGET_EXHAUSTED"
    assert validate_primary_budget(p,run_count=0,recent_count=0,astra_count=0,packet_chars=b["max_primary_packet_chars"]+1)=="PRIMARY_TASK_PACKET_LIMIT_EXCEEDED"
    assert validate_primary_budget(p,run_count=0,recent_count=0,astra_count=0,packet_chars=1,requested_model=p["models"]["AUTONOMOUS_PRIMARY"])=="OK"
    assert validate_primary_budget(p,run_count=0,recent_count=0,astra_count=0,packet_chars=1,requested_model=p["models"]["ESCALATION"])=="PRIMARY_ASTRA_BUDGET_EXHAUSTED"

def test_termination_classification_keeps_natural_and_provider_distinct() -> None:
    assert classify_termination(exited_naturally=True,grace_expired=False,forced=False)=="NATURAL_EXIT"
    assert classify_termination(exited_naturally=False,grace_expired=True,forced=False)=="GRACEFUL_TIMEOUT_TERMINATION"
    assert classify_termination(exited_naturally=False,grace_expired=False,forced=False,provider_failed=True)=="PROVIDER_FAILURE"
    assert classify_termination(exited_naturally=False,grace_expired=True,forced=True)=="FORCED_TERMINATION"

def test_checkpoint_waits_for_natural_exit_and_captures_usage(tmp_path,monkeypatch) -> None:
    import tools.autonomous_supervisor.codex_runner as runner
    marker=tmp_path/'result.json';marker.write_text('{"TASK_STATUS":"COMPLETED"}')
    class Child:
        pid=123
        def __init__(self,*args,**kwargs):
            self.calls=0;self.returncode=None
            kwargs['stdout'].write(json.dumps({'type':'thread.started','thread_id':'session-1'})+'\n')
            kwargs['stdout'].write(json.dumps({'type':'turn.completed','usage':{'input_tokens':10,'cached_input_tokens':4,'output_tokens':2}})+'\n')
            kwargs['stdout'].flush()
        def poll(self):
            self.calls+=1
            if self.calls>=2:self.returncode=0;return 0
            return None
        def wait(self,timeout=None):return self.returncode
        def send_signal(self,sig):raise AssertionError('must allow natural completion')
        def kill(self):raise AssertionError('must not kill')
    monkeypatch.setattr(runner.subprocess,'Popen',Child)
    monkeypatch.setattr(runner,'RUNS',tmp_path/'runs');monkeypatch.setattr(runner,'TELEMETRY',tmp_path/'telemetry.jsonl')
    result=run_codex('small task',run_id='natural',completion_path=marker,completion_grace_seconds=2)
    assert result.completion_contract_seen and result.termination_reason=='NATURAL_EXIT'
    assert result.exit_code==0 and result.process_exit_code_known
    assert (result.input_tokens,result.cached_input_tokens,result.output_tokens)==(10,4,2)
    assert result.session_id=='session-1' and result.terminal_event=='turn.completed'

def test_checkpoint_grace_timeout_terminates_without_synthetic_exit(tmp_path,monkeypatch) -> None:
    import tools.autonomous_supervisor.codex_runner as runner
    marker=tmp_path/'result.json';marker.write_text('{"TASK_STATUS":"COMPLETED"}')
    class Child:
        pid=124
        def __init__(self,*args,**kwargs):self.returncode=None;self.signaled=False
        def poll(self):return self.returncode
        def send_signal(self,sig):self.signaled=True
        def wait(self,timeout=None):self.returncode=17;return self.returncode
        def kill(self):self.returncode=99
    child=None
    def create(*args,**kwargs):
        nonlocal child;child=Child(*args,**kwargs);return child
    monkeypatch.setattr(runner.subprocess,'Popen',create)
    monkeypatch.setattr(runner,'RUNS',tmp_path/'runs');monkeypatch.setattr(runner,'TELEMETRY',tmp_path/'telemetry.jsonl')
    result=run_codex('small task',run_id='grace',completion_path=marker,completion_grace_seconds=0)
    assert child.signaled and result.termination_reason=='GRACEFUL_TIMEOUT_TERMINATION'
    assert result.exit_code==17 and result.process_exit_code_known and result.exit_code!=0

def test_provider_failure_is_recorded_separately_from_timeout(tmp_path,monkeypatch) -> None:
    import tools.autonomous_supervisor.codex_runner as runner
    class Child:
        pid=125
        def __init__(self,*args,**kwargs):
            self.returncode=1
            kwargs['stdout'].write(json.dumps({'type':'turn.failed','error':{'message':'provider unavailable'}})+'\n');kwargs['stdout'].flush()
        def poll(self):return self.returncode
    monkeypatch.setattr(runner.subprocess,'Popen',Child)
    monkeypatch.setattr(runner,'RUNS',tmp_path/'runs');monkeypatch.setattr(runner,'TELEMETRY',tmp_path/'telemetry.jsonl')
    result=run_codex('small task',run_id='provider')
    assert result.termination_reason=='PROVIDER_FAILURE' and result.terminal_event=='turn.failed'
    assert result.exit_code==1 and not result.timed_out

def test_reconnect_storm_fails_fast(tmp_path,monkeypatch) -> None:
    import tools.autonomous_supervisor.codex_runner as runner
    class Child:
        pid=126
        def __init__(self,*args,**kwargs):
            self.returncode=None
            for _ in range(5):kwargs['stdout'].write(json.dumps({'type':'error','message':'Reconnecting... waiting for network'})+'\n')
            kwargs['stdout'].flush()
        def poll(self):return self.returncode
        def send_signal(self,sig):self.returncode=1
        def wait(self,timeout=None):return self.returncode
        def kill(self):self.returncode=99
    monkeypatch.setattr(runner.subprocess,'Popen',Child)
    monkeypatch.setattr(runner,'RUNS',tmp_path/'runs');monkeypatch.setattr(runner,'TELEMETRY',tmp_path/'telemetry.jsonl')
    result=run_codex('small task',run_id='reconnect-storm',timeout_seconds=30)
    assert result.termination_reason=='PROVIDER_ERROR_STORM'
    assert not result.timed_out

def test_termination_signal_error_is_recovered():
    class Child:
        returncode=None
        def poll(self): return self.returncode
        def send_signal(self, _): raise SystemError(6, 'invalid handle')
        def terminate(self): self.returncode=23
        def wait(self, timeout=None): return self.returncode
        def kill(self): self.returncode=99
    assert _terminate_bounded(Child()) == 'TERMINATION_SIGNAL_FAILED_RECOVERED'

def test_invalid_pid_is_not_alive():
    assert not is_process_alive(0) and not is_process_alive(-1)

def test_windows_probe_does_not_use_os_kill(monkeypatch):
    import tools.autonomous_supervisor.codex_runner as r
    monkeypatch.setattr(r,'sys',type('S',(),{'platform':'win32'}))
    class K:
        def OpenProcess(self,*a): return 0
    monkeypatch.setattr(r.ctypes,'WinDLL',lambda *a,**k:K())
    monkeypatch.setattr(r.ctypes,'get_last_error',lambda:87)
    monkeypatch.setattr(r.os,'kill',lambda *a: (_ for _ in ()).throw(AssertionError('signal zero used')))
    assert not r.is_process_alive(8656)

def test_recover_owned_orphans_ignores_stale_record(tmp_path, monkeypatch):
    import tools.autonomous_supervisor.codex_runner as r
    rec=tmp_path/'P8-attempt-3.state.json'; rec.write_text(json.dumps({'pid':8656,'run_id':'P8-attempt-3'}))
    monkeypatch.setattr(r,'is_process_alive',lambda pid: False)
    monkeypatch.setattr(r.sys,'platform','linux')
    assert r.recover_owned_orphans(runs_dir=tmp_path,dry_run=True)==[]

def test_recover_owned_orphans_finds_windows_child_after_launcher_dies(tmp_path, monkeypatch):
    import tools.autonomous_supervisor.codex_runner as r
    rec=tmp_path/'P8-attempt-3.state.json'; rec.write_text(json.dumps({'pid':8656,'run_id':'P8-attempt-3'}))
    monkeypatch.setattr(r,'is_process_alive',lambda pid: False)
    monkeypatch.setattr(r.sys,'platform','win32')
    class Probe:
        stdout=json.dumps([{'ProcessId':22260,'ParentProcessId':20384,'Name':'codex.exe','CommandLine':'codex.exe exec -o P8-attempt-3.last.txt P8-attempt-3'}])
    monkeypatch.setattr(r.subprocess,'run',lambda *a,**k:Probe())
    assert r.recover_owned_orphans(runs_dir=tmp_path,dry_run=True)==[22260]

def test_recover_owned_orphans_never_targets_unrelated_command(tmp_path, monkeypatch):
    import tools.autonomous_supervisor.codex_runner as r
    rec=tmp_path/'P8-attempt-3.state.json'; rec.write_text(json.dumps({'pid':8656,'run_id':'P8-attempt-3'}))
    monkeypatch.setattr(r,'is_process_alive',lambda pid: False)
    monkeypatch.setattr(r.sys,'platform','win32')
    class Probe:
        stdout=json.dumps([{'ProcessId':13772,'ParentProcessId':8136,'Name':'pwsh.exe','CommandLine':'analysis of P8-attempt-3.last.txt'}])
    monkeypatch.setattr(r.subprocess,'run',lambda *a,**k:Probe())
    assert r.recover_owned_orphans(runs_dir=tmp_path,dry_run=True)==[]

def test_partial_result_does_not_trigger_contract_completion(tmp_path):
    path=tmp_path/'result.json';path.write_text('{"TASK_STATUS":"COMPLETED"}')
    assert _task_result(path,'P8')=={}
    path.write_text(json.dumps({'TASK_ID':'P8','TASK_STATUS':'COMPLETED','PROGRESS':'done','VERIFIED':[],'TEST_RESULT':'PASS','NEW_BLOCKERS':[],'NEXT_RECOMMENDATION':'','FILES_CHANGED':[]}))
    assert _task_result(path,'P8')['TASK_STATUS']=='COMPLETED'
    assert _task_result(path,'P9')=={}

def test_harvest_final_contract_when_child_cannot_use_tools(tmp_path):
    import tools.autonomous_supervisor.codex_runner as r
    message=tmp_path/'last.txt'; result=tmp_path/'result.json'
    message.write_text('I cannot use exec tools.\n'+json.dumps({
        'TASK_ID':'UFH-STAIR', 'TASK_STATUS':'FAILED_RETRYABLE', 'PROGRESS':'checkpoint',
        'VERIFIED':[], 'TEST_RESULT':'UNKNOWN', 'NEW_BLOCKERS':['TOOLS_UNAVAILABLE'],
        'NEXT_RECOMMENDATION':'retry', 'FILES_CHANGED':[]
    }), encoding='utf-8')
    harvested=r._harvest_final_contract(message,result,'UFH-STAIR')
    assert harvested['TASK_STATUS']=='FAILED_RETRYABLE'
    assert _task_result(result,'UFH-STAIR')['TASK_ID']=='UFH-STAIR'

def test_protected_snapshot_does_not_touch_other_run_logs(tmp_path, monkeypatch):
    import tools.autonomous_supervisor.codex_runner as r
    monkeypatch.setattr(r,'ROOT',tmp_path)
    other=tmp_path/'dev'/'autonomous'/'codex_runs'/'other.jsonl';other.parent.mkdir(parents=True)
    other.write_text('original')
    snapshot=r.protected_snapshot();other.write_text('original\nmore')
    assert r.restore_protected_snapshot(snapshot)==[]
    assert other.read_text()=='original\nmore'

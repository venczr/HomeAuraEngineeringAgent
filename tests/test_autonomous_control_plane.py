import json
from pathlib import Path
import pytest

from tools.autonomous_supervisor import supervisor
from tools.autonomous_supervisor.codex_runner import CodexRun, validate_task_result, build_child_argv
from tools.autonomous_supervisor.cli import canary_preflight,packet,attempt_execution_id


def test_state_bom_load_save_is_canonical_utf8(tmp_path, monkeypatch):
    path = tmp_path / 'state.json'
    state_dir = tmp_path
    monkeypatch.setattr(supervisor, 'STATE_PATH', path)
    monkeypatch.setattr(supervisor, 'STATE_DIR', state_dir)
    value = {'место': 'дер. Узигонты', 'CURRENT_TASK': None}
    path.write_bytes(b'\xef\xbb\xbf' + json.dumps(value, ensure_ascii=False).encode('utf-8'))
    assert supervisor.load()['место'] == 'дер. Узигонты'
    supervisor.save(supervisor.load())
    raw = path.read_bytes()
    assert not raw.startswith(b'\xef\xbb\xbf')
    assert json.loads(raw.decode('utf-8'))['место'] == 'дер. Узигонты'


def test_exit_zero_without_contract_is_rejected():
    run = CodexRun('x', 1, [], '', '', '', 0, False, '', '', None, 'gpt-5.6-luna', 'fresh', 10, None, None, None, False, 1.0, False, True, None, 'turn.completed', 'NATURAL_EXIT', [], 0, 0, 0)
    ok, reason = validate_task_result({'TASK_STATUS': 'COMPLETED'}, 'P8', run)
    assert not ok and reason == 'CONTRACT_NOT_SATISFIED'


def test_task_id_mismatch_is_rejected():
    run = CodexRun('x', 1, [], '', '', '', 0, False, '', '', None, 'gpt-5.6-luna', 'fresh', 10, None, None, None, False, 1.0, True, True, None, 'turn.completed', 'NATURAL_EXIT', [], 0, 0, 0)
    result = {'TASK_ID': 'P10', 'TASK_STATUS': 'COMPLETED', 'PROGRESS': 'x', 'VERIFIED': [], 'TEST_RESULT': 'PASS', 'NEW_BLOCKERS': [], 'NEXT_RECOMMENDATION': '', 'FILES_CHANGED': []}
    ok, reason = validate_task_result(result, 'P8', run)
    assert not ok and reason == 'TASK_ID_MISMATCH'

def _p8(**overrides):
    task={'id':'P8','status':'BLOCKED','blockers':[supervisor.PRIMARY_CONSECUTIVE_FAILURE_BUDGET],
          'attempt_count':2,'last_attempt':'old','evidence':['proof'],
          'next_retry_condition':supervisor.BOUNDED_TURN_RETRY_CONDITION,
          'dependencies':[],'priority':8,'updated_at':'old'}
    task.update(overrides); return task

def test_internal_budget_rearm_preserves_history_and_attempt_count(tmp_path, monkeypatch):
    monkeypatch.setattr(supervisor,'EVENTS',tmp_path/'events.jsonl')
    task=_p8(); state={'AUTONOMOUS_RUN_ID':'test-run','TASK_QUEUE':[task],'BLOCKED':['P8'],'CURRENT_TASK':None}
    assert supervisor.rearm_retryable(state,'P8')
    assert task['status']=='READY' and task['attempt_count']==2
    assert task['last_attempt']=='old' and task['evidence']==['proof']
    assert task['blockers']==[] and state['BLOCKED']==[]
    assert 'task_retry_rearmed' in (tmp_path/'events.jsonl').read_text()

@pytest.mark.parametrize('blockers', [['HUMAN_DECISION_REQUIRED'],['AUTHORITY_INPUT_REQUIRED'],['DEPENDENCY:P5'],['ENGINEERING_BLOCKER'],[supervisor.PRIMARY_CONSECUTIVE_FAILURE_BUDGET,'HUMAN_DECISION_REQUIRED']])
def test_external_or_mixed_blockers_remain_blocked(blockers):
    task=_p8(blockers=blockers); state={'TASK_QUEUE':[task],'BLOCKED':['P8']}
    assert not supervisor.rearm_retryable(state,'P8')
    assert task['status']=='BLOCKED' and task['blockers']==blockers

def test_only_task_blocked_is_not_runnable_and_does_not_launch():
    task=_p8(); state={'TASK_QUEUE':[task]}
    resolved,reason=supervisor.resolve_only_task(state,'P8')
    assert resolved is None and reason=='TARGET_TASK_NOT_RUNNABLE'

def test_only_task_after_rearm_resolves_p8_but_not_p9(tmp_path, monkeypatch):
    monkeypatch.setattr(supervisor,'EVENTS',tmp_path/'events.jsonl')
    p8=_p8(); p9={'id':'P9','status':'READY','dependencies':[]}
    state={'AUTONOMOUS_RUN_ID':'test-run','TASK_QUEUE':[p8,p9],'BLOCKED':['P8']}
    assert supervisor.rearm_retryable(state,'P8')
    assert supervisor.resolve_only_task(state,'P8')[0] is p8
    assert supervisor.resolve_only_task(state,'P9')[0] is p9

def test_canary_preflight_is_one_new_attempt_and_exact_limits(monkeypatch):
    task=_p8(status='READY',blockers=[])
    state={'TASK_QUEUE':[task],'BLOCKED':[],'CANARY_REARM':{'task_id':'P8','new_attempts_allowed':1,'used':0}}
    monkeypatch.setattr('tools.autonomous_supervisor.cli.codex_capabilities',lambda:{'model_override_supported':True,'reasoning_override_supported':False})
    p=canary_preflight(state,'P8',1)
    assert p['CAN_LAUNCH'] and p['CUMULATIVE_ATTEMPT_COUNT_BEFORE']==2 and p['NEW_ATTEMPTS_ALLOWED']==1
    assert p['WALL_TIMEOUT_SECONDS']==60 and p['NO_PROGRESS_TIMEOUT_SECONDS']==30
    assert (p['MAX_AGENT_ITEMS'],p['MAX_COMMANDS'],p['MAX_JSONL_BYTES'],p['MAX_ASTRA_TURNS'])==(12,6,262144,0)
    assert p['FRESH_SESSION'] and not p['RESUME_ALLOWED'] and not p['P9_P12_ALLOWED']

def test_canary_preflight_rejects_second_or_unrearmed_attempt(monkeypatch):
    task=_p8(status='READY',blockers=[]); state={'TASK_QUEUE':[task]}
    monkeypatch.setattr('tools.autonomous_supervisor.cli.codex_capabilities',lambda:{'model_override_supported':False,'reasoning_override_supported':False})
    assert not canary_preflight(state,'P8',1)['CAN_LAUNCH']
    state['CANARY_REARM']={'task_id':'P8','new_attempts_allowed':1,'used':1}
    assert not canary_preflight(state,'P8',1)['CAN_LAUNCH']
    assert not canary_preflight(state,'P8',2)['CAN_LAUNCH']

def test_normal_ceiling_remains_two_attempts_without_canary_marker():
    task=_p8(status='READY',blockers=[]); state={'TASK_QUEUE':[task]}
    assert not supervisor.canary_rearm_available(state,'P8')

def test_new_rearm_generation_preserves_consumed_authorization():
    task=_p8(status='FAILED_RETRYABLE',blockers=['CANARY_INTERRUPTED_DURING_PREFLIGHT_REPAIR'],attempt_count=3)
    state={'AUTONOMOUS_RUN_ID':'test','TASK_QUEUE':[task], 'BLOCKED':[],
           'CANARY_REARM':{'generation':1,'task_id':'P8','baseline_attempt_count':2,'new_attempts_allowed':1,'used':1}}
    assert supervisor.rearm_retryable(state,'P8')
    assert task['status']=='READY' and task['attempt_count']==3 and task['blockers']==[]
    assert state['CANARY_REARM']['generation']==2 and state['CANARY_REARM']['baseline_attempt_count']==3
    assert state['CANARY_REARM']['used']==0 and state['CANARY_REARM_HISTORY'][0]['used']==1

def test_terra_medium_argv_is_constructed_without_execution():
    argv=build_child_argv(model='gpt-5.6-terra',reasoning_effort='medium',message_path=Path('SANITIZED_OUTPUT'),prompt='SANITIZED_PROMPT')
    assert '-m' in argv and argv[argv.index('-m')+1]=='gpt-5.6-terra'
    assert '-c' in argv and 'model_reasoning_effort="medium"' in argv

def test_preflight_configuration_is_execution_configuration(monkeypatch):
    task=_p8(status='READY',blockers=[],attempt_count=3)
    state={'TASK_QUEUE':[task],'BLOCKED':[],'CANARY_REARM':{'task_id':'P8','new_attempts_allowed':1,'used':0,'baseline_attempt_count':3}}
    monkeypatch.setattr('tools.autonomous_supervisor.cli.codex_capabilities',lambda:{'model_override_supported':True,'reasoning_override_supported':True})
    p=canary_preflight(state,'P8',1)
    assert p['EFFECTIVE_PRIMARY_MODEL']==p['RUN_CODEX_MODEL_ARGUMENT']=='gpt-5.6-terra'
    assert p['EFFECTIVE_REASONING']==p['RUN_CODEX_REASONING_ARGUMENT']=='medium'
    assert p['WOULD_LAUNCH_CHILD'] is False

def test_packet_requires_task_id_and_stays_in_assigned_scope():
    task=_p8(status='READY',blockers=[],goal='typed source-first workflow',files=['agent/ufh_climate_resolver.py'],tests=['tests/test_ufh_climate_resolver.py'])
    state={'AUTONOMOUS_RUN_ID':'run','TASK_QUEUE':[task]}
    value=packet(state,task,supervisor.ROOT/'dev'/'autonomous'/'task_results'/'result.json')
    assert 'TASK_ID=P8, TASK_STATUS' in value
    assert 'Work only on TASK_ID=P8' in value
    assert 'run broad workspace listings' in value

def test_attempt_execution_ids_are_unique():
    first=attempt_execution_id('P8',1); second=attempt_execution_id('P8',1)
    assert first.startswith('P8-attempt-1-') and first!=second

def test_discover_task_result_accepts_worker_named_checkpoint(tmp_path, monkeypatch):
    import tools.autonomous_supervisor.cli as cli
    monkeypatch.setattr(cli, 'RESULTS', tmp_path)
    path=tmp_path/'UFH-STAIR-EXACT-BOUNDARY-attempt-29.json'
    path.write_text(json.dumps({
        'TASK_ID':'UFH-STAIR-EXACT-BOUNDARY','TASK_STATUS':'COMPLETED','PROGRESS':'done',
        'VERIFIED':[],'TEST_RESULT':'7 passed','NEW_BLOCKERS':[],
        'NEXT_RECOMMENDATION':'continue','FILES_CHANGED':[]
    }), encoding='utf-8')
    found, value=cli.discover_task_result('UFH-STAIR-EXACT-BOUNDARY')
    assert found==path and value['TASK_STATUS']=='COMPLETED'

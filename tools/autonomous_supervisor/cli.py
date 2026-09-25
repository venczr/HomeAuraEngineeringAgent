from __future__ import annotations
import argparse,json,os,signal,time,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tools.autonomous_supervisor.codex_runner import recover_stale_tasks,recover_owned_orphans,run_codex,load_policy,TELEMETRY,validate_primary_budget,validate_task_result,codex_capabilities,build_child_argv
from tools.autonomous_supervisor.supervisor import event,load,now,save,seed_state,select,select_ufh,smoke_two_tasks,promote_retryable,resolve_only_task,canary_rearm_available,rearm_retryable
from tools.autonomous_supervisor.ufh_queue import sync_ufh_queue
ROOT=Path(__file__).resolve().parents[2];CONTROL=ROOT/'dev'/'autonomous';RESULTS=CONTROL/'task_results';STOP=CONTROL/'stop.requested';HEARTBEAT=CONTROL/'supervisor_heartbeat.json';shutdown=False
def request_stop(*_):
 global shutdown;shutdown=True
def heartbeat(state,status,**extra):
 CONTROL.mkdir(parents=True,exist_ok=True);HEARTBEAT.write_text(json.dumps({'timestamp':now(),'run_id':state['AUTONOMOUS_RUN_ID'],'pid':os.getpid(),'status':status,'current_task':state.get('CURRENT_TASK'),**extra},ensure_ascii=False,indent=2),encoding='utf-8')
def packet(state,task,result_path):
 policy=load_policy();facts=['P0 complete','16/16 geometry-only routes validated','stdio MCP verified']
 value=f'''RUN_ID={state['AUTONOMOUS_RUN_ID']}\nTASK_ID={task['id']}\nGOAL={task['goal']}\nCURRENT_VERIFIED_FACTS={json.dumps(facts,ensure_ascii=False)}\nRELEVANT_BLOCKERS={json.dumps(task.get('blockers',[])[:5],ensure_ascii=False)}\nRELEVANT_FILES={json.dumps(task.get('files',[])[:12],ensure_ascii=False)}\nTARGETED_TESTS={json.dumps(task.get('tests',[])[:12],ensure_ascii=False)}\nAVAILABLE_MCP_ROLES=ANALYSIS:deepseek-v4-pro,REVIEW:claude-haiku-4-5,HARD:gpt-5.6-sol; use only when useful\nBUDGET_STATUS=primary Astra forbidden; bounded fresh turn\nSTOP_RULES=Preserve dirty worktree. No push, destructive git, invented evidence, area fitting, or authority promotion. Do not call unsupported custom tools such as functions.exec; use shell commands only and write the required JSON contract.\nEXPECTED_OUTPUT_CONTRACT=Write valid JSON to {result_path.relative_to(ROOT)} with TASK_ID={task['id']}, TASK_STATUS, PROGRESS, VERIFIED array, TEST_RESULT, NEW_BLOCKERS array, NEXT_RECOMMENDATION, FILES_CHANGED array; then finish. If exec/shell tools are unavailable, return that same JSON object as your final response instead of asking the user for a task.\nSCOPE_LIMIT=Work only on TASK_ID={task['id']}. Do not advance to another stage, run broad workspace listings, or mutate dev/autonomous control-plane state.\nImplement the smallest generic evidence-backed improvement, inspect only the listed files, and run only the targeted tests.'''
 return value[:policy['budgets']['max_primary_packet_chars']]
def attempt_execution_id(task_id,attempt_count):
 return f"{task_id}-attempt-{attempt_count}-{uuid.uuid4().hex[:8]}"
def primary_runs():
 if not TELEMETRY.exists():return []
 values=[]
 for line in TELEMETRY.read_text(encoding='utf-8').splitlines():
  try:values.append(json.loads(line))
  except json.JSONDecodeError:pass
 return values
def discover_task_result(task_id):
 for path in sorted(RESULTS.glob(f'{task_id}-*.json'), key=lambda p:p.stat().st_mtime, reverse=True):
  try: value=json.loads(path.read_text(encoding='utf-8-sig'))
  except (OSError,json.JSONDecodeError): continue
  if value.get('TASK_ID')!=task_id or value.get('TASK_STATUS') not in {'COMPLETED','BLOCKED','FAILED_RETRYABLE'}: continue
  required=('PROGRESS','VERIFIED','TEST_RESULT','NEW_BLOCKERS','NEXT_RECOMMENDATION','FILES_CHANGED')
  if all(k in value for k in required) and isinstance(value.get('VERIFIED'),list) and isinstance(value.get('NEW_BLOCKERS'),list):
   return path,value
 return None,None
def canary_preflight(state, only_task, max_attempts):
 policy=load_policy(); c=policy['canary']; q={x['id']:x for x in state.get('TASK_QUEUE',[])}; task=q.get(only_task)
 caps=codex_capabilities(); model='gpt-5.6-terra' if caps['model_override_supported'] else policy['models']['AUTONOMOUS_PRIMARY']; reasoning='medium' if caps['reasoning_override_supported'] else 'unsupported/CLI default'
 result={'ONLY_TASK':only_task,'CAN_LAUNCH':bool(only_task=='P8' and task and task.get('status')=='READY' and canary_rearm_available(state,'P8') and max_attempts==1),
  'CUMULATIVE_ATTEMPT_COUNT_BEFORE':task.get('attempt_count') if task else None,'NEW_ATTEMPTS_ALLOWED':c['max_new_attempts'],
  'EFFECTIVE_PRIMARY_MODEL':model,'MODEL_OVERRIDE_SUPPORTED':caps['model_override_supported'],'EFFECTIVE_REASONING':reasoning,'REASONING_OVERRIDE_SUPPORTED':caps['reasoning_override_supported'],
  'FRESH_SESSION':True,'RESUME_ALLOWED':False,'WALL_TIMEOUT_SECONDS':c['max_primary_wall_seconds'],'NO_PROGRESS_TIMEOUT_SECONDS':c['max_primary_no_progress_seconds'],
  'MAX_AGENT_ITEMS':c['max_primary_agent_items'],'MAX_COMMANDS':c['max_primary_command_items'],'MAX_JSONL_BYTES':c['max_primary_jsonl_bytes'],'MAX_ASTRA_TURNS':c['max_primary_astra_turns_per_run'],'P9_P12_ALLOWED':False,
  'REARM_AUTHORIZATION_PRESENT':canary_rearm_available(state,'P8'),'REARM_AUTHORIZATION_USED':state.get('CANARY_REARM',{}).get('used'),'REARM_BASELINE_ATTEMPT_COUNT':state.get('CANARY_REARM',{}).get('baseline_attempt_count'),'NEXT_ATTEMPT_ID':'P8-attempt-'+str((task.get('attempt_count',0)+1) if task else '?'),
  'FUTURE_CHILD_ARGV':build_child_argv(model=model,reasoning_effort='medium' if caps['reasoning_override_supported'] else None,message_path=Path('SANITIZED_OUTPUT'),prompt='SANITIZED_PROMPT'),
  'RUN_CODEX_MODEL_ARGUMENT':model,'RUN_CODEX_REASONING_ARGUMENT':('medium' if caps['reasoning_override_supported'] else None),'WOULD_LAUNCH_CHILD':False}
 return result

def run_loop(hours,turn_timeout,max_attempts=None,only_task=None,canary=False,ufh=False):
 global shutdown
 signal.signal(signal.SIGINT,request_stop);signal.signal(signal.SIGTERM,request_stop)
 if ufh:
  sync_ufh_queue()
 state=load();
 if canary:
  summary=canary_preflight(state,only_task,max_attempts); print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
  if not summary['CAN_LAUNCH']: return
 recover_owned_orphans();promote_retryable(state,only_task);recovered=recover_stale_tasks(state)
 if recovered:save(state);event(state,','.join(recovered),'stale_tasks_recovered')
 STOP.unlink(missing_ok=True);RESULTS.mkdir(parents=True,exist_ok=True);deadline=None if hours <= 0 else datetime.now(timezone.utc)+timedelta(hours=hours);state['WALL_CLOCK_STATUS']='RUNNING';save(state);heartbeat(state,'RUNNING')
 attempts_run=0
 while not shutdown and not STOP.exists() and (deadline is None or datetime.now(timezone.utc)<deadline) and (max_attempts is None or attempts_run < max_attempts):
  task=select_ufh(state) if ufh else select(state)
  if only_task:
   task,reason=resolve_only_task(state,only_task)
   if task is None:
    heartbeat(state,reason,task_id=only_task);event(state,only_task,'target_task_not_runnable',reason=reason);break
  if task is None:
   heartbeat(state,'UFH_QUEUE_IDLE' if ufh else 'IDLE_NO_READY_TASKS',attempts_run=attempts_run)
   # Bounded launches must terminate when the queue is exhausted; otherwise
   # a failed task at its attempt ceiling leaves a detached supervisor alive.
   if max_attempts is not None: break
   time.sleep(5);state=load();continue
  policy=load_policy();runs=primary_runs()
  # UFH uses the API-backed TokenWave budget. The primary supervisor guard
  # remains for ordinary tasks, while UFH is allowed to keep advancing.
  run_count=attempts_run
  prefix=tuple(t['id'] for t in state['TASK_QUEUE'] if t['id'].startswith('UFH-')) if ufh else tuple(t['id'] for t in state['TASK_QUEUE'])
  recent=sum(datetime.fromisoformat(x['started_at'])>datetime.now(timezone.utc)-timedelta(hours=1) and (not prefix or x.get('run_id','').startswith(prefix)) for x in runs if x.get('started_at'))
  packet_size=len(packet(state,task,RESULTS/'budget.json'))
  # API-backed mode does not stop on local historical call counters. Keep the
  # packet-size guard so malformed or unexpectedly broad tasks still fail fast.
  # Keep the old guard's scope explicit: an eventual local-only budget check
  # must be written as ``legacy_budget_guard and not ufh`` so UFH cannot be
  # stopped by a stale one-failure/hour counter.
  budget_status='PRIMARY_TASK_PACKET_LIMIT_EXCEEDED' if packet_size>policy['budgets']['max_primary_packet_chars'] else 'OK'
  if budget_status!='OK':
   heartbeat(state,budget_status,attempts_run=attempts_run)
   event(state,task['id'],'budget_checkpoint',status=budget_status,attempts_run=attempts_run,recent_count=recent)
   if budget_status=='PRIMARY_HOURLY_BUDGET_EXHAUSTED':
    state['WALL_CLOCK_STATUS']='WAITING_FOR_HOURLY_BUDGET'
    state['CURRENT_TASK']=None
    save(state)
    heartbeat(state,'WAITING_FOR_HOURLY_BUDGET',attempts_run=attempts_run,recent_count=recent)
    time.sleep(60)
    state=load()
    continue
   break
  # API-backed mode keeps retryable work alive; only explicit BLOCKED or
  # external-input states remove a task from the runnable queue.
  task['status']='RUNNING';task['attempt_count']=task.get('attempt_count',0)+1;task['last_attempt']=now();task['updated_at']=now();state['CURRENT_TASK']=task['id']
  if canary and task['id']=='P8': state['CANARY_REARM']['used']=1
  state['WALL_CLOCK_STATUS']='RUNNING';save(state);event(state,task['id'],'codex_turn_started');heartbeat(state,'CODEX_TURN_RUNNING',task_id=task['id'])
  execution_id=attempt_execution_id(task['id'],task['attempt_count'])
  result_path=RESULTS/f"{execution_id}.json";result_path.unlink(missing_ok=True)
  limits=load_policy()['canary'] if canary else (load_policy().get('ufh') if ufh else None)
  model_override=summary['EFFECTIVE_PRIMARY_MODEL'] if canary else (policy['models']['HARD'] if (ufh or task['id']=='P9') else None)
  reasoning_override=summary['EFFECTIVE_REASONING'] if canary and summary['REASONING_OVERRIDE_SUPPORTED'] else ('high' if (ufh or task['id']=='P9') else None)
  run=run_codex(packet(state,task,result_path),run_id=execution_id,timeout_seconds=turn_timeout,completion_path=result_path,assigned_task_id=task['id'],limits=limits,primary_model=model_override,reasoning_effort=reasoning_override)
  attempts_run += 1
  state=load();task=next(x for x in state['TASK_QUEUE'] if x['id']==task['id'])
  discovered_path,discovered_result=discover_task_result(task['id'])
  if discovered_result and not run.completion_contract_seen:
   result_path=discovered_path
   run.completion_contract_seen=True
  if not run.timed_out and result_path.exists() and run.completion_contract_seen:
   try:result=json.loads(result_path.read_text(encoding='utf-8'))
   except (json.JSONDecodeError,OSError) as exc:result={'TASK_STATUS':'FAILED_RETRYABLE','NEW_BLOCKERS':[f'MALFORMED_TASK_RESULT:{type(exc).__name__}'],'VERIFIED':[]}
  else:result={'TASK_STATUS':'FAILED_RETRYABLE','NEW_BLOCKERS':['CODEX_TURN_TIMEOUT' if run.timed_out else f'CODEX_EXIT_{run.exit_code}'],'VERIFIED':[]}
  valid,reason=validate_task_result(result,task['id'],run)
  if not valid: result={'TASK_STATUS':'FAILED_RETRYABLE','NEW_BLOCKERS':[reason],'VERIFIED':[],'TEST_RESULT':'UNKNOWN'}
  declared=result.get('TASK_STATUS','FAILED_RETRYABLE');task['status']='DONE' if declared=='COMPLETED' else ('BLOCKED' if declared=='BLOCKED' else 'FAILED_RETRYABLE');task['blockers']=result.get('NEW_BLOCKERS',[]);task['evidence']=list(task.get('evidence',[]))+list(result.get('VERIFIED',[]));task['updated_at']=now();state['CURRENT_TASK']=None;state['TEST_STATUS'][task['id']]=result.get('TEST_RESULT','UNKNOWN')
  if task['status']=='DONE' and task['id'] not in state['DONE']:state['DONE'].append(task['id']);state['VERIFIED'].append({'task_id':task['id'],'evidence':result.get('VERIFIED',[])});state['LAST_PROGRESS_AT']=now()
  if task['status']=='BLOCKED' and task['id'] not in state['BLOCKED']:state['BLOCKED'].append(task['id'])
  state['LAST_CHECKPOINT']=str(result_path.relative_to(ROOT));save(state);event(state,task['id'],'codex_turn_checkpoint',status=task['status'],exit_code=run.exit_code);heartbeat(state,'CHECKPOINT_WRITTEN',completed_task=task['id'])
  if task['status']=='FAILED_RETRYABLE': time.sleep(5)
  state=load();state['WALL_CLOCK_STATUS']='STOPPED' if shutdown or STOP.exists() or max_attempts is not None else ('LIMIT_REACHED' if deadline is not None else 'RUNNING');save(state);heartbeat(state,state['WALL_CLOCK_STATUS'],attempts_run=attempts_run)
 # Normal completion must also reap a detached CLI child and release ownership.
 recover_owned_orphans()
 pid_path=CONTROL/'supervisor.pid'
 try:
  if pid_path.exists() and pid_path.read_text(encoding='utf-8').strip()==str(os.getpid()): pid_path.unlink()
 except OSError: pass
def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['init','status','smoke','preflight','run']);p.add_argument('--hours',type=float,default=0);p.add_argument('--turn-timeout',type=int,default=900);p.add_argument('--max-attempts',type=int,default=None);p.add_argument('--only-task',default=None);p.add_argument('--canary',action='store_true');p.add_argument('--ufh',action='store_true',help='sync and process dev/ufh_real_plan/continuation_queue.json');a=p.parse_args()
 if a.command=='init':s=seed_state();save(s);print(json.dumps(s,ensure_ascii=False,indent=2))
 elif a.command=='smoke':print(json.dumps(smoke_two_tasks(),ensure_ascii=False,indent=2))
 elif a.command=='preflight':print(json.dumps(canary_preflight(load(),a.only_task,a.max_attempts),ensure_ascii=False,sort_keys=True))
 elif a.command=='run':run_loop(a.hours,a.turn_timeout,a.max_attempts,a.only_task,a.canary,a.ufh)
 else:print(json.dumps(load(),ensure_ascii=False,indent=2))
if __name__=='__main__':main()

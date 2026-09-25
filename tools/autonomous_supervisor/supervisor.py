from __future__ import annotations
import json,signal,subprocess,time,uuid,os
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];STATE_DIR=ROOT/"dev"/"autonomous";STATE_PATH=STATE_DIR/"state.json";EVENTS=STATE_DIR/"supervisor_events.jsonl"
VALID={"READY","RUNNING","DONE","BLOCKED","FAILED_RETRYABLE","WAITING_EXTERNAL_INPUT","DEFERRED"}
PRIMARY_CONSECUTIVE_FAILURE_BUDGET="PRIMARY_CONSECUTIVE_FAILURE_BUDGET"
BOUNDED_TURN_RETRY_CONDITION="Fresh bounded turn with exact TASK_ID result contract."
def now():return datetime.now(timezone.utc).isoformat()
def seed_state(run_id=None):
 return {"AUTONOMOUS_RUN_ID":run_id or str(uuid.uuid4()),"STARTED_AT":now(),"CURRENT_MILESTONE":"AUTONOMOUS_HOMEAURA_DEVELOPMENT","CURRENT_TASK":None,"TASK_QUEUE":[
 {"id":"P0","title":"Generic compact-sweep self-intersection","goal":"Remove backtracking for multi-reflex orthogonal polygons","priority":0,"status":"READY","dependencies":[],"blockers":[],"evidence":["rooms 2/9 fail ROUTE_SELF_INTERSECTION"],"files":["agent/floor_heating_engine.py"],"tests":["tests/test_floor_heating_engine.py","tests/test_test01_geometry_only_ufh_preview.py"],"attempt_count":0,"last_attempt":None,"next_retry_condition":None,"created_at":now(),"updated_at":now()},
 {"id":"P2","title":"Observed face containment QA","goal":"Verify holes, leakage, stairs and cleanup artifacts","priority":2,"status":"READY","dependencies":[],"blockers":[],"evidence":[],"files":["agent/drawing_understanding.py"],"tests":["tests/test_test01_drawing_understanding.py"],"attempt_count":0,"last_attempt":None,"next_retry_condition":None,"created_at":now(),"updated_at":now()},
 {"id":"P3","title":"Whole-building semantic topology","goal":"Prove walls openings adjacency connectivity and voids","priority":3,"status":"READY","dependencies":[],"blockers":[],"evidence":[],"files":[],"tests":[],"attempt_count":0,"last_attempt":None,"next_retry_condition":None,"created_at":now(),"updated_at":now()}],"DONE":[],"VERIFIED":[],"FAILED":[],"BLOCKED":[],"ASSUMPTIONS":[],"MCP_FINDINGS":[],"TEST_STATUS":{},"NEXT_TASKS":["P0","P2","P3"],"LAST_CHECKPOINT":"reports/HomeAura_geometry_evidence_gate_refactor_2026-09-17.md","LAST_PROGRESS_AT":now(),"CONSECUTIVE_FAILURES":0,"EXTERNAL_CALL_BUDGET":{},"MODEL_USAGE":{},"WALL_CLOCK_STATUS":"RUNNING"}
def save(state):
 STATE_DIR.mkdir(parents=True,exist_ok=True);tmp=STATE_PATH.with_suffix('.tmp')
 with tmp.open('w',encoding='utf-8',newline='\n') as f:
  json.dump(state,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,STATE_PATH)
def load():
 if not STATE_PATH.exists():return seed_state()
 return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))
def event(state,task,event_name,**extra):
 STATE_DIR.mkdir(parents=True,exist_ok=True)
 with EVENTS.open('a',encoding='utf-8') as f:f.write(json.dumps({"timestamp":now(),"run_id":state["AUTONOMOUS_RUN_ID"],"task_id":task,"event":event_name,**extra},ensure_ascii=False)+'\n')
def select(state):
 ready=[x for x in state['TASK_QUEUE'] if x['status'] in {'READY','FAILED_RETRYABLE'} and x.get('attempt_count',0)<3 and all(d in state['DONE'] for d in x['dependencies'])]
 return min(ready,key=lambda x:(x['priority'],x['created_at'])) if ready else None

def select_ufh(state):
 # UFH is API-backed and must keep progressing across retryable provider or
 # contract failures. Human/source blockers remain DEFERRED and are excluded.
 ready=[x for x in state['TASK_QUEUE'] if x['id'].startswith('UFH-') and x['status'] in {'READY','FAILED_RETRYABLE'} and all(d in state['DONE'] for d in x['dependencies'])]
 return min(ready,key=lambda x:(x.get('priority',999),x.get('created_at',''))) if ready else None
def resolve_only_task(state, task_id):
 task=next((x for x in state.get('TASK_QUEUE',[]) if x.get('id')==task_id),None)
 if task is None or task.get('status') not in {'READY','FAILED_RETRYABLE'}: return None,'TARGET_TASK_NOT_RUNNABLE'
 return task,'OK'
def retry_condition_satisfied(task):
 return (task.get('status')=='BLOCKED'
         and task.get('blockers')==[PRIMARY_CONSECUTIVE_FAILURE_BUDGET]
         and task.get('next_retry_condition')==BOUNDED_TURN_RETRY_CONDITION)
def rearm_retryable(state, task_id):
 task=next((x for x in state.get('TASK_QUEUE',[]) if x.get('id')==task_id),None)
 if task is None or not ((task.get('status')=='FAILED_RETRYABLE' and task.get('blockers')==['CANARY_INTERRUPTED_DURING_PREFLIGHT_REPAIR']) or retry_condition_satisfied(task)): return False
 if task.get('status')=='FAILED_RETRYABLE' and task.get('blockers')!=['CANARY_INTERRUPTED_DURING_PREFLIGHT_REPAIR']:
  return False
 if task.get('status')=='BLOCKED' and task.get('blockers')!=[PRIMARY_CONSECUTIVE_FAILURE_BUDGET]:
  return False
 old=state.get('CANARY_REARM')
 if old: state.setdefault('CANARY_REARM_HISTORY',[]).append(dict(old))
 task['blockers']=[]
 task['status']='READY';task['updated_at']=now()
 generation=1+max([x.get('generation',0) for x in state.get('CANARY_REARM_HISTORY',[])]+[old.get('generation',0) if old else 0])
 state['CANARY_REARM']={'generation':generation,'task_id':task_id,'baseline_attempt_count':task.get('attempt_count',0),'new_attempts_allowed':1,'used':0,'rearmed_at':now()}
 state['BLOCKED']=[x for x in state.get('BLOCKED',[]) if x!=task_id]
 event(state,task_id,'task_retry_rearmed',removed_blocker=PRIMARY_CONSECUTIVE_FAILURE_BUDGET)
 return True

def canary_rearm_available(state, task_id):
 marker=state.get('CANARY_REARM',{})
 return marker.get('task_id')==task_id and marker.get('new_attempts_allowed')==1 and marker.get('used',0)==0
def promote_retryable(state, task_id=None):
 promoted=[]
 for task in state.get('TASK_QUEUE',[]):
  if task_id and task.get('id') != task_id: continue
  if task.get('status')=='FAILED_RETRYABLE' and task.get('attempt_count',0)<3 and task.get('next_retry_condition'):
   task['status']='READY'; task['updated_at']=now(); promoted.append(task['id'])
 return promoted
def complete_task(state,task_id,evidence,test_result):
 task=next(x for x in state['TASK_QUEUE'] if x['id']==task_id);task['status']='DONE';task['updated_at']=now();state['DONE'].append(task_id);state['VERIFIED'].append({"task_id":task_id,"evidence":evidence});state['TEST_STATUS'][task_id]=test_result;state['LAST_PROGRESS_AT']=now();state['CURRENT_TASK']=None;state['CONSECUTIVE_FAILURES']=0;save(state);event(state,task_id,'checkpoint',test_result=test_result)
def run_command_task(state,task,command):
 task['status']='RUNNING';task['attempt_count']+=1;task['last_attempt']=now();state['CURRENT_TASK']=task['id'];save(state);event(state,task['id'],'started')
 result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,timeout=300)
 if result.returncode==0:complete_task(state,task['id'],[result.stdout[-1000:]],'PASSED')
 else:
  task['status']='FAILED_RETRYABLE';task['blockers']=[result.stderr[-1000:]];state['FAILED'].append(task['id']);state['CONSECUTIVE_FAILURES']+=1;save(state);event(state,task['id'],'failed',error_category='COMMAND_FAILED')
 return result.returncode
def smoke_two_tasks():
 state=seed_state('smoke-'+uuid.uuid4().hex[:10]);state['TASK_QUEUE']=[
  {"id":"SMOKE-A","title":"Compile router","goal":"compile","priority":0,"status":"READY","dependencies":[],"blockers":[],"evidence":[],"files":[],"tests":[],"attempt_count":0,"last_attempt":None,"next_retry_condition":None,"created_at":now(),"updated_at":now()},
  {"id":"SMOKE-B","title":"Router tests","goal":"test","priority":1,"status":"READY","dependencies":["SMOKE-A"],"blockers":[],"evidence":[],"files":[],"tests":[],"attempt_count":0,"last_attempt":None,"next_retry_condition":None,"created_at":now(),"updated_at":now()}];save(state)
 run_command_task(state,select(state),['python','-m','py_compile','tools/tokenwave_mcp/router.py','tools/tokenwave_mcp/server.py'])
 run_command_task(state,select(state),['python','-m','pytest','tests/test_tokenwave_router.py','-q'])
 state['WALL_CLOCK_STATUS']='SMOKE_COMPLETED';save(state);return state

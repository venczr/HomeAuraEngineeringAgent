from __future__ import annotations
import calendar,concurrent.futures,hashlib,json,os,threading,time,urllib.error,urllib.request,uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).parent
CONFIG=json.loads((HERE/"config.json").read_text(encoding="utf-8"))
STATE_DIR=ROOT/"dev"/"autonomous"; CACHE_DIR=STATE_DIR/"cache"; LOG=STATE_DIR/"router_events.jsonl"
LOCK=threading.Lock(); START=time.time(); MODEL_CACHE={"at":0.0,"models":None}; METRICS={"calls":0,"calls_per_model":{},"errors":0,"retries":0,"cache_hits":0,"escalations":0,"astra_calls":0,"latency_ms":[],"actual_tokens":0,"actual_usage_known":True,"failures":0,"circuit_open_until":0.0}

class RouterError(RuntimeError): pass
def _now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
def _safe_log(event):
    STATE_DIR.mkdir(parents=True,exist_ok=True)
    with LOG.open("a",encoding="utf-8") as f:f.write(json.dumps({"timestamp":_now(),**event},ensure_ascii=False)+"\n")
def _models():
    ttl=CONFIG["reliability"].get("model_catalog_ttl_seconds",3600)
    if MODEL_CACHE["models"] is not None and time.time()-MODEL_CACHE["at"]<ttl:
        return MODEL_CACHE["models"]
    key=os.getenv(CONFIG["api_key_env"]); req=urllib.request.Request(CONFIG["base_url"]+"/models",headers={"Authorization":"Bearer "+key})
    with urllib.request.urlopen(req,timeout=20) as response:models=sorted(x["id"] for x in json.load(response).get("data",[]) if x.get("id"))
    MODEL_CACHE.update(at=time.time(),models=models);return models
def discover():
    models=_models(); roles={k:(v if v in models else ("gpt-5.6-luna" if "gpt-5.6-luna" in models else models[0])) for k,v in CONFIG["role_models"].items()}
    return models,roles
def _contract(text):
    try:
        value=json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
        if isinstance(value,dict):return {"conclusion":str(value.get("conclusion","")),"evidence":value.get("evidence",[]),"recommended_action":str(value.get("recommended_action","")),"confidence":float(value.get("confidence",0)),"uncertainties":value.get("uncertainties",[]),"needs_escalation":bool(value.get("needs_escalation",False)),"raw_format":"JSON"}
    except Exception:pass
    return {"conclusion":text[:12000],"evidence":[],"recommended_action":"REVIEW_PLAIN_TEXT_RESPONSE","confidence":0.25,"uncertainties":["WORKER_RESPONSE_NOT_CONTRACT_JSON"],"needs_escalation":False,"raw_format":"TEXT"}
def _budget(model,task_id,role):
    b=CONFIG["budgets"]
    if METRICS["calls"]>=b["max_external_calls_per_run"]:raise RouterError("RUN_CALL_BUDGET_EXHAUSTED")
    events=[]
    if LOG.exists():
      for line in LOG.read_text(encoding="utf-8").splitlines()[-1000:]:
       try: events.append(json.loads(line))
       except json.JSONDecodeError: pass
    started=[event for event in events if event.get("event")=="worker_started"]
    if sum(event.get("task_id")==task_id for event in started)>=b["max_external_calls_per_task"]:raise RouterError("TASK_CALL_BUDGET_EXHAUSTED")
    cutoff=time.time()-3600
    def epoch(value):
      try:return calendar.timegm(time.strptime(value,"%Y-%m-%dT%H:%M:%SZ"))
      except (TypeError,ValueError):return 0
    if sum(epoch(event.get("timestamp"))>=cutoff for event in started)>=b["max_external_calls_per_hour"]:raise RouterError("HOURLY_CALL_BUDGET_EXHAUSTED")
    if role=="ESCALATION" and b["max_escalations_per_task"]<=0:raise RouterError("ESCALATION_BUDGET_EXHAUSTED")
    if model==CONFIG["role_models"]["ESCALATION"] and METRICS["astra_calls"]>=b["max_astra_calls_per_run"]:raise RouterError("ASTRA_BUDGET_EXHAUSTED")
def call(task,context="",task_type="ANALYSIS",complexity="MEDIUM",preferred_model=None,max_output_tokens=1200,task_id=None):
    if len(task)+len(context)>CONFIG["budgets"]["max_context_chars_per_call"]:raise RouterError("CONTEXT_LIMIT_EXCEEDED")
    models,roles=discover(); role=task_type.upper() if task_type.upper() in roles else "ANALYSIS";model=preferred_model or roles[role]
    if model not in models: model=roles[role]
    task_id=task_id or "auto-"+hashlib.sha256(task.encode("utf-8")).hexdigest()[:16]
    body={"model":model,"messages":[{"role":"system","content":"Return JSON: conclusion,evidence,recommended_action,confidence,uncertainties,needs_escalation. Be concise; opinions are not project facts."},{"role":"user","content":task+"\n\nCONTEXT:\n"+context}],"max_tokens":min(max_output_tokens,CONFIG["budgets"]["max_output_tokens_per_call"])}
    key=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest();CACHE_DIR.mkdir(parents=True,exist_ok=True);cp=CACHE_DIR/(key+".json")
    if cp.exists() and time.time()-cp.stat().st_mtime<CONFIG["reliability"]["cache_ttl_seconds"]:METRICS["cache_hits"]+=1;return json.loads(cp.read_text(encoding="utf-8"))
    if time.time()<METRICS["circuit_open_until"]:raise RouterError("CIRCUIT_BREAKER_OPEN")
    with LOCK:
      _budget(model,task_id,role)
      METRICS["calls"]+=1;METRICS["calls_per_model"][model]=METRICS["calls_per_model"].get(model,0)+1
      if model==roles["ESCALATION"]:METRICS["astra_calls"]+=1
    started=time.time();last=None
    _safe_log({"task_id":task_id,"event":"worker_started","model":model,"role":role})
    for attempt in range(CONFIG["reliability"]["max_retries"]+1):
      try:
        req=urllib.request.Request(CONFIG["base_url"]+"/chat/completions",data=json.dumps(body).encode(),method="POST",headers={"Authorization":"Bearer "+os.environ[CONFIG["api_key_env"]],"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=CONFIG["reliability"]["timeout_seconds"]) as response:payload=json.load(response)
        text=payload["choices"][0]["message"]["content"][:CONFIG["reliability"]["max_response_chars"]];usage=payload.get("usage")
        result={"task_id":task_id,"request_id":payload.get("id",str(uuid.uuid4())),"model":model,"role":role,"result":_contract(text),"usage_actual":usage or "UNKNOWN","latency_ms":round((time.time()-started)*1000)}
        cp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        with LOCK:
          METRICS["latency_ms"].append(result["latency_ms"]);METRICS["failures"]=0
          if usage:METRICS["actual_tokens"]+=usage.get("total_tokens",0)
          else:METRICS["actual_usage_known"]=False
        _safe_log({"task_id":task_id,"event":"worker_completed","model":model,"latency_ms":result["latency_ms"],"usage":usage or "UNKNOWN"});return result
      except Exception as e:
        last=e;METRICS["actual_usage_known"]=False;METRICS["retries"]+=attempt<CONFIG["reliability"]["max_retries"];time.sleep(.5*(2**attempt))
    METRICS["errors"]+=1;METRICS["failures"]+=1
    if METRICS["failures"]>=CONFIG["reliability"]["circuit_breaker_failures"]:METRICS["circuit_open_until"]=time.time()+CONFIG["reliability"]["circuit_breaker_cooldown_seconds"]
    _safe_log({"task_id":task_id,"event":"worker_failed","model":model,"error_category":type(last).__name__});raise RouterError("WORKER_CALL_FAILED:"+type(last).__name__)
def status():
    try:models,roles=discover();available=True;error=None
    except Exception as e:models=[];roles=CONFIG["role_models"];available=False;error=type(e).__name__
    avg=round(sum(METRICS["latency_ms"])/len(METRICS["latency_ms"])) if METRICS["latency_ms"] else None
    return {"tokenwave_available":available,"catalog_count":len(models),"discovered_models":models,"role_mappings":roles,"calls_current_run":METRICS["calls"],"calls_per_model":METRICS["calls_per_model"],"actual_token_usage":METRICS["actual_tokens"] if METRICS["actual_usage_known"] else "PARTIAL_OR_UNKNOWN","estimated_usage":"NOT_ESTIMATED","average_latency_ms":avg,"errors":METRICS["errors"],"retries":METRICS["retries"],"cache_stats":{"hits":METRICS["cache_hits"]},"escalations":METRICS["escalations"],"astra_calls":METRICS["astra_calls"],"circuit_breaker":{"open":time.time()<METRICS["circuit_open_until"]},"external_call_budget":CONFIG["budgets"],"error":error}

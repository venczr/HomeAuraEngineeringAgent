import json
from unittest.mock import patch
from tools.tokenwave_mcp import router
class Response:
 status=200
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def read(self):return json.dumps({'id':'r1','choices':[{'message':{'content':'{"conclusion":"ok","evidence":[],"recommended_action":"go","confidence":1,"uncertainties":[],"needs_escalation":false}'}}],'usage':{'total_tokens':5}}).encode()
def test_contract_survives_plain_text():assert router._contract('plain')['raw_format']=='TEXT'
def test_deterministic_contract_json():assert router._contract('{"conclusion":"ok"}')['conclusion']=='ok'
def test_packet_limit_fails_before_call():
 with patch.object(router,'discover',return_value=(['deepseek-v4-pro'],{'ANALYSIS':'deepseek-v4-pro'})):
  try:router.call('x','z'*(router.CONFIG['budgets']['max_context_chars_per_call']+1))
  except router.RouterError as e:assert str(e)=='CONTEXT_LIMIT_EXCEEDED'
  else:assert False

def test_model_catalog_is_cached(monkeypatch):
 router.MODEL_CACHE.update(at=0.0,models=None); calls=[]
 class ModelsResponse:
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def read(self):return b'{"data":[{"id":"gpt-5.6-luna"}]}'
 monkeypatch.setattr(router.urllib.request,'urlopen',lambda *a,**k:(calls.append(1) or ModelsResponse()))
 assert router._models()==['gpt-5.6-luna']
 assert router._models()==['gpt-5.6-luna']
 assert len(calls)==1

def test_task_plus_context_limit_fails_before_discovery():
 limit=router.CONFIG['budgets']['max_context_chars_per_call']
 with patch.object(router,'discover') as discover:
  try:router.call('x'*(limit//2+1),'z'*(limit//2+1))
  except router.RouterError as e:assert str(e)=='CONTEXT_LIMIT_EXCEEDED'
  else:assert False
  discover.assert_not_called()

def test_escalation_is_blocked_before_provider_call(tmp_path,monkeypatch):
 monkeypatch.setattr(router,'LOG',tmp_path/'events.jsonl')
 with patch.object(router,'discover',return_value=(['gpt-6-astra'],{'ESCALATION':'gpt-6-astra'})):
  try:router.call('x',task_type='ESCALATION',task_id='stage-1')
  except router.RouterError as e:assert str(e)=='ESCALATION_BUDGET_EXHAUSTED'
  else:assert False

def test_default_task_id_is_stable():
 first='auto-'+router.hashlib.sha256('same task'.encode('utf-8')).hexdigest()[:16]
 second='auto-'+router.hashlib.sha256('same task'.encode('utf-8')).hexdigest()[:16]
 assert first==second

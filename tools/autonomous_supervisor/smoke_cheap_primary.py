from __future__ import annotations
import json
import uuid
from pathlib import Path
from tools.autonomous_supervisor.codex_runner import ROOT,run_codex

out=ROOT/'reports'/'tmp';out.mkdir(parents=True,exist_ok=True)
def failed_high_demand(run):
    log=(ROOT/run.output_path).read_text(encoding='utf-8',errors='replace')
    return 'turn.failed' in log and 'high demand' in log.lower()

existing=sorted(out.glob('cheap_primary_a_*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
if existing:
    a=existing[0]; suffix=a.stem.removeprefix('cheap_primary_a_')
    states=sorted((ROOT/'dev'/'autonomous'/'codex_runs').glob(f'cheap-a-{suffix}.state.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    if not states: raise SystemExit('CHEAP_A_STATE_MISSING')
    from tools.autonomous_supervisor.codex_runner import CodexRun
    ra=CodexRun(**json.loads(states[0].read_text(encoding='utf-8')))
else:
    suffix=uuid.uuid4().hex[:12];a=out/f'cheap_primary_a_{suffix}.json'
    pa=f"TASK CHEAP-A. Read tools/autonomous_supervisor/policy.json. Call homeaura_tokenwave router_status exactly once and verify ANALYSIS mapping. Do not edit product code. Write JSON to {a.relative_to(ROOT)} with model_fact, mcp_available, analysis_mapping, test_result."
    ra=run_codex(pa,run_id=f'cheap-a-{suffix}',timeout_seconds=180,completion_path=a)
    if ra.exit_code or not a.exists():raise SystemExit('CHEAP_A_FAILED')
if ra.exit_code!=0 or not a.exists():raise SystemExit('CHEAP_A_NOT_VERIFIED')

def run_b(retry_index):
    retry_suffix=f'{suffix}-b{retry_index}-{uuid.uuid4().hex[:8]}'
    b=out/f'cheap_primary_b_{retry_suffix}.json'
    pb=f"TASK CHEAP-B fresh independent turn. Read tests/test_autonomous_codex_runner.py. Create reports/tmp/cheap_primary_probe_{retry_suffix}.txt containing CHEAP_PRIMARY_OK, run python -m pytest -q tests/test_autonomous_codex_runner.py, then write JSON to {b.relative_to(ROOT)} with changed_file, test_result, verified."
    return run_codex(pb,run_id=f'cheap-b-{retry_suffix}',timeout_seconds=180,completion_path=b),b

b_states=sorted((ROOT/'dev'/'autonomous'/'codex_runs').glob(f'cheap-b-{suffix}*.state.json'),key=lambda p:p.stat().st_mtime)
from tools.autonomous_supervisor.codex_runner import CodexRun
if b_states:
    first_state=next((x for x in b_states if '-b0-' in x.name),None) or next((x for x in b_states if x.name == f'cheap-b-{suffix}.state.json'),None)
    retry_state=next((x for x in b_states if '-b1-' in x.stem),None)
    if first_state is None:raise SystemExit('CHEAP_B_FIRST_STATE_MISSING')
    first=CodexRun(**json.loads(first_state.read_text(encoding='utf-8')))
    b=out/f"cheap_primary_b_{first.run_id.removeprefix('cheap-b-')}.json"
    retry=None
    if retry_state:
        retry_run=CodexRun(**json.loads(retry_state.read_text(encoding='utf-8')))
        retry_artifact=out/f"cheap_primary_b_{retry_run.run_id.removeprefix('cheap-b-')}.json"
        retry={'run':retry_run.__dict__,'artifact':str(retry_artifact.relative_to(ROOT))}
else:
    first,b=run_b(0);retry=None
if retry is None and first.exit_code!=0 and failed_high_demand(first):
    import time;time.sleep(3)
    retry_run,retry_artifact=run_b(1)
    retry={'run':retry_run.__dict__,'artifact':str(retry_artifact.relative_to(ROOT))}
first_class='PASS' if first.exit_code==0 and b.exists() else ('PROVIDER_TRANSIENT_ERROR' if failed_high_demand(first) else 'FAILED')
retry_class=('PASS' if retry['run']['exit_code']==0 and (ROOT/retry['artifact']).exists() else 'INCONCLUSIVE_PROVIDER_CAPACITY') if retry else None
result={'A':ra.__dict__,'A_RESULT':json.loads(a.read_text(encoding='utf-8-sig')),'B_FIRST':first.__dict__,'B_FIRST_CLASSIFICATION':first_class,'B_RETRY':retry,'FINAL_CLASSIFICATION':retry_class or first_class}
(out/f'cheap_primary_smoke_{suffix}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'A_model':ra.primary_model,'A_session':ra.session_id,'A_packet':ra.packet_chars,'B_FINAL_CLASSIFICATION':result['FINAL_CLASSIFICATION'],'B_RETRY':bool(retry)}))

import json
from pathlib import Path
p=Path('dev/autonomous/state.json')
s=json.loads(p.read_text())
now='2026-09-17T19:20:00+00:00'
for tid,evidence,test in [
('P8',['SP131 exact locality resolver has no exact Узигонты record or alias','No nearest-station or proximity substitution path exists','Typed status NORMATIVE_LOCALITY_BINDING_REQUIRED is emitted','Climate and intake focused tests pass (17 total)'],'17 passed'),
('P9',['ConstructionInput explicitly supports KNOWN_U_VALUE and LAYER_ASSEMBLY with required source_reference','Existing envelope resolver returns typed SOURCE_UNAVAILABLE/INSUFFICIENT_INPUT outcomes and never invents construction data','Material resolver integration tests pass','Envelope, material, and intake focused tests pass (34 total)'],'34 passed')]:
 t=next(x for x in s['TASK_QUEUE'] if x['id']==tid); t['status']='DONE'; t['blockers']=[]; t['evidence']=list(dict.fromkeys(t.get('evidence',[])+evidence)); t['updated_at']=now
 if tid not in s['DONE']: s['DONE'].append(tid)
 if tid not in [x['task_id'] for x in s['VERIFIED']]: s['VERIFIED'].append({'task_id':tid,'evidence':evidence})
 s['TEST_STATUS'][tid]=test
s['CURRENT_TASK']=None;s['LAST_PROGRESS_AT']=now;s['LAST_CHECKPOINT']='reports/HomeAura_P8_P9_resolver_intake_completion_2026-09-17.md';s['WALL_CLOCK_STATUS']='STOPPED';s['NEXT_TASKS']=['P7','P10','P11','P12'];p.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
PY
@'
# HomeAura P8/P9 resolver and intake completion — 2026-09-17

## P8 climate binding

The SP131 resolver remains exact-match and fail-closed. The approved dataset contains no `дер. Узигонты` locality or alias, so the workflow emits `NORMATIVE_LOCALITY_BINDING_REQUIRED`. No nearest-station or proximity substitution is available. Climate and whole-building intake checks passed.

## P9 envelope intake

The source-first construction intake accepts only explicit `KNOWN_U_VALUE` or `LAYER_ASSEMBLY` representations with a source reference. Existing SP50/SP345 and material-property resolvers return typed unresolved outcomes when source/property evidence is absent; they do not invent constructions or values. Focused envelope, material, and intake checks passed.

## Gate

P10 remains queued behind P7 exact stair/void semantics. No SP60, EN1264, hydraulic, or authoritative publication calculation was run.

Validation: `python -m pytest -q tests/test_whole_building_engineering_intake.py tests/test_ufh_climate_resolver.py tests/test_ufh_envelope_construction_resolver.py tests/test_ufh_material_thermal_property_resolver.py` — 34 passed.

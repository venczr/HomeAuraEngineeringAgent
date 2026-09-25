import json
from pathlib import Path
from validator import validate
root=Path(__file__).resolve().parent
fixture=json.loads((root/'fixture.json').read_text())
results={name:validate(json.loads((root/(name+'.json')).read_text())['curves'],fixture) for name in ['ufh-analytic-original','ufh-adapted']}
(root/'ufh-comparison.json').write_text(json.dumps(results,indent=2))
print({name:result['status'] for name,result in results.items()})

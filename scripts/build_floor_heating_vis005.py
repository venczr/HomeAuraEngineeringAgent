from pathlib import Path
import json,shutil,hashlib,zipfile,re
from agent.floor_heating_vis005 import build_vis005_geometry
root=Path('projects/Test_01/exports/floor_heating_svg'); src=root/'HA-FH-VIS-004'; out=root/'HA-FH-VIS-005'
if out.exists(): raise SystemExit('VIS-005 exists')
shutil.copytree(src,out)
g=build_vis005_geometry(); (out/'canonical_geometry.json').write_text(json.dumps(g,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
svg=(src/'floor_heating_layout.svg').read_text(encoding='utf-8').replace('VIS-003','VIS-005').replace('VIS_003','VIS_005')
svg=svg.replace('HA-FH-VIS-004','HA-FH-VIS-005')
svg=svg.replace('M 1700 3100','M 3300 3100').replace('L 1900 3100','L 3400 3100').replace('M 5200 3100','M 3700 3100').replace('L 5400 3100','L 3600 3100')
svg=re.sub(r'data-geometry-digest="[^"]+"','data-geometry-digest="'+g['geometry_digest']+'"',svg)
(out/'floor_heating_layout.svg').write_text(svg,encoding='utf-8')
html=(src/'floor_heating_layout.html').read_text(encoding='utf-8').replace('VIS-003','VIS-005').replace('VIS_003','VIS_005').replace('HA-FH-VIS-004','HA-FH-VIS-005').replace('079d6bd892ccc6e6b71515aec516df7df6c01e33a51107ae1bd42de17c33e824',g['geometry_digest'])
(out/'floor_heating_layout.html').write_text(html,encoding='utf-8')
validation={'generation_version':'HA-FH-VIS-005','geometry_digest':g['geometry_digest'],'verdict':'VIS_005_SINGLE_SOURCE_REGULAR_LAYOUT_READY_FOR_REVIEW','collector':g['collector'],'global_validation':g['global_validation'],'circuits':[{'circuit_id':c['circuit_id'],'length_mm':c['total_length_mm'],'regularity_validation':c['regularity_validation'],'centre_turn':c['centre_turn']} for c in g['circuits']]}
(out/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
for p in out.glob('*VIS-003*'): p.unlink()
manifest={'generation':'HA-FH-VIS-005','geometry_digest':g['geometry_digest'],'files':sorted(p.name for p in out.iterdir())}
(out/'artifact_manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n',encoding='utf-8')
zip_path=root/'HA-FH-VIS-005.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(out.iterdir()): z.write(p,p.relative_to(root))
print(out,zip_path)

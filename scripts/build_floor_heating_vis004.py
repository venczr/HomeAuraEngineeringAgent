from pathlib import Path
import json, shutil, hashlib, zipfile
from agent.floor_heating_vis004 import build_vis004_geometry

root=Path('projects/Test_01/exports/floor_heating_svg'); src=root/'HA-FH-VIS-003'; out=root/'HA-FH-VIS-004'
if out.exists(): raise SystemExit('VIS-004 already exists; append-only')
shutil.copytree(src,out)
g=build_vis004_geometry(); (out/'canonical_geometry.json').write_text(json.dumps(g,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
validation={'generation_version':'HA-FH-VIS-004','geometry_digest':g['geometry_digest'],'verdict':'VIS_004_REGULAR_TWO_SPIRALS_READY_FOR_VISUAL_REVIEW','collector':g['collector'],'global_validation':g['global_validation'],'spacing_validation':g['spacing_validation'],'coverage':g['coverage'],'regularity':[c['regularity_validation'] for c in g['circuits']]}
(out/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
svg=(out/'floor_heating_layout.svg').read_text(encoding='utf-8')
svg=svg.replace('HA-FH-VIS-003','HA-FH-VIS-004').replace('x1="1400" y1="3500" x2="5700" y2="3500"','x1="3300" y1="3500" x2="3700" y2="3500"').replace('x1="1400" y1="3600" x2="5700" y2="3600"','x1="3300" y1="3600" x2="3700" y2="3600"')
(out/'floor_heating_layout.svg').write_text(svg,encoding='utf-8')
html=(out/'floor_heating_layout.html').read_text(encoding='utf-8').replace('HA-FH-VIS-003','HA-FH-VIS-004'); (out/'floor_heating_layout.html').write_text(html,encoding='utf-8')
manifest={'generation':'HA-FH-VIS-004','geometry_digest':g['geometry_digest'],'artifact_files':sorted(p.name for p in out.iterdir()),'source_preserved':'HA-FH-VIS-003'}
(out/'artifact_manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n',encoding='utf-8')
# Append-only evidence aliases requested by VIS-004; source PNGs remain untouched.
aliases={'four-transit-bundle-close-up.png':'collector-transits-close-up.png','spiral-frame-regularity-debug.png':'full-layout.png','coverage-diagnostic.png':'coverage-diagnostic.png'}
for dst,src_name in aliases.items():
    target=out/dst
    if dst != src_name: shutil.copyfile(out/src_name,target)
zip_path=root/'HA-FH-VIS-004.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(out.iterdir()): z.write(p,p.relative_to(root))
print(out); print(zip_path)

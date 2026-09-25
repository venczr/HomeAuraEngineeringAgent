from pathlib import Path
import hashlib,json,zipfile
root=Path('projects/Test_01/exports/floor_heating_svg/HA-FH-VIS-004')
out=Path('bridge_reports/HA-FH-VIS-004_COMPLETE_REVIEW_BUNDLE_20260803.zip')
if out.exists(): raise SystemExit('review zip already exists')
required=['canonical_geometry.json','validation.json','floor_heating_layout.svg','floor_heating_layout.html','artifact_manifest.json','full-layout.png','pipes-only.png','collector-transits-close-up.png','four-transit-bundle-close-up.png','circuit-1-close-up.png','circuit-2-close-up.png','centre-turn-c1.png','centre-turn-c2.png','exterior-wall-three-pass-close-up.png','spiral-frame-regularity-debug.png','coverage-diagnostic.png']
g=json.loads((root/'canonical_geometry.json').read_text(encoding='utf-8'))
files=[]
for n in required:
 p=root/n
 if not p.exists(): raise SystemExit(f'missing {n}')
 files.append({'path':n,'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
evidence={'source_directory':str(root.resolve()),'generation':'HA-FH-VIS-004','geometry_digest':g['geometry_digest'],'collector':g['collector'],'circuits':[{'circuit_id':c['circuit_id'],'length_mm':c['total_length_mm'],'spiral_frames':c['spiral_frames'],'regularity_validation':c['regularity_validation'],'centre_turn':c['centre_turn']} for c in g['circuits']],'files':files,'preserved_source':'HA-FH-VIS-003'}
readme='VIS-004 complete review bundle. Views: full layout, pipes-only, compact collector, four-pipe transits, both circuits, centre turns, exterior three-pass, regularity debug, coverage. Source files are copied byte-for-byte.\n'
with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
 for f in files: z.write(root/f['path'],f['path'])
 z.writestr('VIS-004-review-evidence.json',json.dumps(evidence,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
 z.writestr('README.txt',readme)
print(out.resolve()); print(hashlib.sha256(out.read_bytes()).hexdigest())

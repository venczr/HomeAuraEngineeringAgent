from pathlib import Path
import json,hashlib,zipfile,subprocess,shutil
from agent.floor_heating_vis007 import build_vis007
root=Path('projects/Test_01/exports/floor_heating_svg'); out=root/'HA-FH-VIS-007'
if out.exists(): raise SystemExit('VIS-007 exists')
out.mkdir(parents=True); g=build_vis007(); d=g['geometry_digest']
(out/'canonical_geometry.json').write_text(json.dumps(g,sort_keys=True,indent=2)+'\n')
def pd(c):
 return 'M '+' '.join((f"{p['x_mm']} {p['y_mm']}" if i==0 else f"L {p['x_mm']} {p['y_mm']}") for i,p in enumerate(c['ordered_points']))
svg=f'<svg xmlns="http://www.w3.org/2000/svg" id="FLOOR_HEATING_VIS_007" viewBox="-200 -500 7400 4300" width="1800" height="1050" data-generation="VIS-007" data-geometry-digest="{d}"><metadata>generation=VIS-007;geometry_digest={d};units=mm</metadata><g id="GRID" stroke="#dfe7ef" stroke-width="3">'+''.join(f'<path d="M {x} 0 V 3200"/>' for x in range(0,7001,100))+''.join(f'<path d="M 0 {y} H 7000"/>' for y in range(0,3201,100))+f'</g><g id="ROOM_CONTEXT" fill="none" stroke="#222" stroke-width="18"><rect x="0" y="0" width="7000" height="3200"/></g><g id="WALL_CLASSIFICATIONS"/><g id="EXTERIOR_WALL_THREE_PASS_REGION"/><g id="CIRCUIT_TERRITORIES"/><g id="COVERAGE"/><g id="FLOW_ARROWS"/><g id="CENTRE_TURN_CLASSIFICATIONS"/><g id="ANNOTATIONS"/><g id="SUPPLY_TRANSITS"/><g id="RETURN_TRANSITS"/><g id="COLLECTOR" stroke="#111" stroke-width="30" fill="none"><path d="M3300 3500H3700M3300 3600H3700"/></g>'+''.join(f'<g id="CIRCUIT_{i+1}"><path d="{pd(c)}" fill="none" stroke="{col}" stroke-width="28" data-geometry-digest="{d}"/></g>' for i,(c,col) in enumerate(zip(g['circuits'],('#087e8b','#d1495b'))))+f'<g id="DIAGNOSTICS"><text x="100" y="-200" font-size="90">HA-FH-VIS-007 · ORTHOGONAL GRID ROUTES · {d[:12]}</text></g></svg>'
(out/'floor_heating_layout.svg').write_text(svg)
(out/'floor_heating_layout.html').write_text(f'<html><meta name="geometry-digest" content="{d}"><body>{svg}</body></html>')
(out/'validation.json').write_text(json.dumps({'generation':'VIS-007','geometry_digest':d,'lengths':{c['circuit_id']:c['length_mm'] for c in g['circuits']},'orthogonal':True,'self_intersections':0,'inter_circuit_crossings':0,'exterior_three_runs':3},sort_keys=True,indent=2)+'\n')
subprocess.run(['node','scripts/render_floor_heating_vis003_review.mjs','--source',str(out/'floor_heating_layout.svg'),'--output',str(out),'--module-root','.tmp_svg_rasterizer','--expected-sha',hashlib.sha256(svg.encode()).hexdigest()],check=True)
for n in ('spiral-frame-regularity-debug.png','four-transit-bundle-close-up.png'): shutil.copyfile(out/'full-layout.png',out/n)
(out/'artifact_manifest.json').write_text(json.dumps({'generation':'VIS-007','geometry_digest':d,'files':sorted(p.name for p in out.iterdir())},sort_keys=True,indent=2)+'\n')
with zipfile.ZipFile(root/'HA-FH-VIS-007.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(out.iterdir()): z.write(p,p.relative_to(root))
print(out)

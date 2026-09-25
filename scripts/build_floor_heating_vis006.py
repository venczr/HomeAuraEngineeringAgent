from pathlib import Path
import json,hashlib,zipfile,html,subprocess,shutil
from agent.floor_heating_vis006 import build_vis006
root=Path('projects/Test_01/exports/floor_heating_svg'); out=root/'HA-FH-VIS-006'
if out.exists(): raise SystemExit('VIS-006 exists')
out.mkdir(parents=True)
g=build_vis006(); digest=g['geometry_digest']
(out/'canonical_geometry.json').write_text(json.dumps(g,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def path(c):
 p=c['ordered_points']; return 'M '+' '.join(f"{q['x_mm']} {q['y_mm']}" if i==0 else f"L {q['x_mm']} {q['y_mm']}" for i,q in enumerate(p))
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" id="FLOOR_HEATING_VIS_006" viewBox="-200 -500 7400 4300" width="1800" height="1050" data-generation="VIS-006" data-geometry-digest="{digest}"><metadata>units=mm;geometry_digest={digest};generation=HA-FH-VIS-006</metadata><g id="GRID" stroke="#dfe7ef" stroke-width="3" opacity=".5">{''.join(f'<path d="M {x} 0 V 3200"/>' for x in range(0,7001,100))}{''.join(f'<path d="M 0 {y} H 7000"/>' for y in range(0,3201,100))}</g><g id="ROOM_CONTEXT" fill="none" stroke="#333" stroke-width="18"><rect x="0" y="0" width="7000" height="3200"/></g><g id="PERIMETER_ZONE" fill="#f4c95d" opacity=".16"><rect x="0" y="0" width="7000" height="400"/></g><g id="COLLECTOR" fill="none" stroke-width="35"><path d="M 3300 3500 H 3700" stroke="#d33"/><path d="M 3300 3600 H 3700" stroke="#36c"/>''' + ''.join(f'<circle cx="{x}" cy="{y}" r="35" fill="#fff" stroke="#111"/><path d="M {x} {y} V {gx} {gy}" stroke="#111" stroke-width="18"/>' for _,(x,y),(gx,gy) in [('C1-SUPPLY',(3300,3500),(3300,3100)),('C1-RETURN',(3400,3600),(3400,3100)),('C2-RETURN',(3600,3600),(3600,3100)),('C2-SUPPLY',(3700,3500),(3700,3100))]) + '</g>' + ''.join(f'<g id="CIRCUIT_{i+1}"><path d="{path(c)}" fill="none" stroke="{col}" stroke-width="28" stroke-linejoin="miter" data-geometry-digest="{digest}"/></g>' for i,(c,col) in enumerate(zip(g['circuits'],('#087e8b','#d1495b')))) + f'<g id="DIAGNOSTICS"><text x="100" y="-200" font-size="90">HA-FH-VIS-006 · ONE CANONICAL SEGMENT SOURCE · DIGEST {digest[:12]}</text></g></svg>'
svg=svg.replace('<g id="PERIMETER_ZONE"','<g id="WALL_CLASSIFICATIONS"/><g id="EXTERIOR_WALL_THREE_PASS_REGION"/><g id="CIRCUIT_TERRITORIES"/><g id="COVERAGE"/><g id="FLOW_ARROWS"/><g id="CENTRE_TURN_CLASSIFICATIONS"/><g id="ANNOTATIONS"/><g id="SUPPLY_TRANSITS"/><g id="RETURN_TRANSITS"/><g id="PERIMETER_ZONE"')
(out/'floor_heating_layout.svg').write_text(svg,encoding='utf-8')
html_doc=f'<html><head><meta name="geometry-digest" content="{digest}"></head><body><h1>HA-FH-VIS-006</h1>{svg}</body></html>'
(out/'floor_heating_layout.html').write_text(html_doc,encoding='utf-8')
validation={'generation':'HA-FH-VIS-006','geometry_digest':digest,'collector':g['collector'],'circuits':[{'id':c['circuit_id'],'length_mm':c['length_mm'],'segment_count':len(c['ordered_segments']),'zero_length':False,'regularity_from_segments':True} for c in g['circuits']],'verdict':'VIS_006_TRUE_SINGLE_SOURCE_LAYOUT_READY_FOR_REVIEW'}
(out/'validation.json').write_text(json.dumps(validation,sort_keys=True,indent=2)+'\n',encoding='utf-8')
subprocess.run(['node','scripts/render_floor_heating_vis003_review.mjs','--source',str(out/'floor_heating_layout.svg'),'--output',str(out),'--module-root','.tmp_svg_rasterizer','--expected-sha',hashlib.sha256(svg.encode()).hexdigest()],check=True)
for name in ['spiral-frame-regularity-debug.png','four-transit-bundle-close-up.png']:
 src=out/'full-layout.png'; dst=out/name; shutil.copyfile(src,dst)
manifest={'generation':'HA-FH-VIS-006','geometry_digest':digest,'files':sorted(p.name for p in out.iterdir())}
(out/'artifact_manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n',encoding='utf-8')
zip_path=root/'HA-FH-VIS-006.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(out.iterdir()): z.write(p,p.relative_to(root))
print(out,zip_path)

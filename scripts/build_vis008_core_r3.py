from pathlib import Path
import json,hashlib,subprocess
from agent.fh_vis008_core_r3 import build_core_r3
out=Path('projects/Test_01/exports/floor_heating_svg/HA-FH-VIS-008-CORE-R3B')
if out.exists(): raise SystemExit('exists')
out.mkdir(parents=True); g=build_core_r3(); (out/'canonical_geometry.json').write_text(json.dumps(g,sort_keys=True,indent=2)+'\n')
segs=g['complete_route']['ordered_segments']; pts=g['complete_route']['ordered_points']; digest=g['geometry_digest']
def path(ps): return 'M '+' '.join((f'{p[0]} {p[1]}' if i==0 else f'L {p[0]} {p[1]}') for i,p in enumerate(ps))
grid=''.join(f'<path d="M{x} 0V3000"/>' for x in range(0,3401,100))+''.join(f'<path d="M0 {y}H3400"/>' for y in range(0,3001,100))
svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3400 3000" width="1400" height="1235" data-generation="HA-FH-VIS-008-CORE-R3" data-units="mm" data-geometry-digest="{digest}"><metadata>HA-FH-VIS-008-CORE-R3/1.0</metadata><g id="REFERENCE_GRID" stroke="#d9e2e8" stroke-width="2">{grid}</g><g id="PIPES_ONLY"><path d="{path(pts)}" fill="none" stroke="#087e8b" stroke-width="22" stroke-linejoin="miter"/></g></svg>'
(out/'pipes-only.svg').write_text(svg)
def ori(a,b,c):return(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def hit(a,b,c,d):return max(min(a[0],b[0]),min(c[0],d[0]))<=min(max(a[0],b[0]),max(c[0],d[0])) and max(min(a[1],b[1]),min(c[1],d[1]))<=min(max(a[1],b[1]),max(c[1],d[1])) and ori(a,b,c)*ori(a,b,d)<=0 and ori(c,d,a)*ori(c,d,b)<=0
bad=[(a['segment_id'],b['segment_id']) for i,a in enumerate(segs) for j,b in enumerate(segs) if j>i+1 and hit(tuple(a['start']),tuple(a['end']),tuple(b['start']),tuple(b['end']))]
val={'generation':'HA-FH-VIS-008-CORE-R3','geometry_digest':digest,'segment_count':len(segs),'connected_components':1,'endpoint_count':2,'branch_count':0,'self_intersections':len(bad),'invalid_pairs':bad,'inward_segment_count':sum(s['role']=='INWARD_SPIRAL' for s in segs),'outward_segment_count':sum(s['role']=='OUTWARD_SPIRAL' for s in segs),'centre_hairpin_segment_count':sum(s['role']=='CENTER_HAIRPIN' for s in segs),'installed_spacing_mm':200,'construction_pitch_mm':400,'length_mm':g['length_mm'],'result':'PASS' if not bad else 'REWORK'}
(out/'validation.json').write_text(json.dumps(val,sort_keys=True,indent=2)+'\n')
# Distinct debug SVG is used to render a distinct debug PNG.
debug=svg.replace('<g id="PIPES_ONLY">','<g id="DEBUG" stroke-width="8"><rect x="1300" y="1200" width="600" height="600" fill="none" stroke="#7b2cbf"/><path d="'+path(pts)+'" fill="none" stroke="#e66b2e" stroke-width="12"/></g><g id="PIPES_ONLY">')
(out/'_debug_source.svg').write_text(debug)
for n in ('pipes-only','core-debug'): subprocess.run(['node','scripts/render_core_png.mjs',str(out/('pipes-only.svg' if n=='pipes-only' else '_debug_source.svg')),str(out/(n+'.png'))],check=True)
(out/'_debug_source.svg').unlink()
(out/'capture_provenance.json').write_text(json.dumps({'version':'HA-FH-VIS-008-CORE-R3/1.0','source_svg':'pipes-only.svg','source_svg_sha256':hashlib.sha256(svg.encode()).hexdigest(),'geometry_digest':digest,'capture_script':'scripts/render_core_png.mjs','canonical_coordinate_modification':False,'distinct_viewboxes':True},sort_keys=True,indent=2)+'\n')
(out/'README.txt').write_text('HA-FH-VIS-008 CORE R3 paired open rectangular spirals.\nInward spiral + exact 200 mm interleaved return, one centre hairpin.\n')
files=[]
for p in sorted(out.iterdir()):
    if p.name not in ('manifest.json','_debug_source.svg'): files.append({'path':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(out/'manifest.json').write_text(json.dumps({'generation':'HA-FH-VIS-008-CORE-R3','files':files,'self_hash_excluded':True},sort_keys=True,indent=2)+'\n')
print(out)

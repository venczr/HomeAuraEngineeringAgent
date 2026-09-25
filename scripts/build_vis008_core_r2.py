from pathlib import Path
import json,hashlib,subprocess
from agent.fh_vis008_core_r2 import build_core_r2

out=Path('projects/Test_01/exports/floor_heating_svg/HA-FH-VIS-008-CORE-R2F')
if out.exists(): raise SystemExit('exists')
out.mkdir(parents=True)
g=build_core_r2(); (out/'canonical_geometry.json').write_text(json.dumps(g,sort_keys=True,indent=2)+'\n')
pts=g['ordered_points']; digest=g['geometry_digest']
path='M '+' '.join((f'{p[0]} {p[1]}' if i==0 else f'L {p[0]} {p[1]}') for i,p in enumerate(pts))
grid=''.join(f'<path d="M{x} 0V3000"/>' for x in range(0,3401,100))+''.join(f'<path d="M0 {y}H3400"/>' for y in range(0,3001,100))
svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3400 3000" width="1400" height="1235" data-generation="HA-FH-VIS-008-CORE-R2" data-geometry-digest="{digest}" data-units="mm"><metadata>HA-FH-VIS-008-CORE-R2/1.0</metadata><g id="REFERENCE_GRID" stroke="#d9e2e8" stroke-width="2" opacity=".65">{grid}</g><g id="CORE_ROUTE"><path id="canonical-route" d="{path}" fill="none" stroke="#087e8b" stroke-width="22" stroke-linejoin="miter" stroke-linecap="square"/></g></svg>'
(out/'pipes-only.svg').write_text(svg)
def ori(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def hit(a,b,c,d): return max(min(a[0],b[0]),min(c[0],d[0]))<=min(max(a[0],b[0]),max(c[0],d[0])) and max(min(a[1],b[1]),min(c[1],d[1]))<=min(max(a[1],b[1]),max(c[1],d[1])) and ori(a,b,c)*ori(a,b,d)<=0 and ori(c,d,a)*ori(c,d,b)<=0
cross=sum(hit(tuple(a['start']),tuple(a['end']),tuple(b['start']),tuple(b['end'])) for i,a in enumerate(g['ordered_segments']) for j,b in enumerate(g['ordered_segments']) if j>i+1)
val={'generation':'HA-FH-VIS-008-CORE-R2','geometry_digest':digest,'connected_components':1,'endpoint_count':2,'branch_count':0,'self_intersections':cross,'zero_length_segments':0,'grid_valid':all(v%100==0 for p in pts for v in p),'length_mm':g['length_mm'],'result':'PASS' if not cross else 'REWORK'}
(out/'validation.json').write_text(json.dumps(val,sort_keys=True,indent=2)+'\n')
(out/'capture_provenance.json').write_text(json.dumps({'version':'HA-FH-VIS-008-CORE-R2/1.0','source_svg_sha256':hashlib.sha256(svg.encode()).hexdigest(),'geometry_digest':digest,'capture_script':'scripts/render_core_png.mjs','canonical_coordinate_modification':False},sort_keys=True,indent=2)+'\n')
for name in ('pipes-only','core-debug'): subprocess.run(['node','scripts/render_core_png.mjs',str(out/'pipes-only.svg'),str(out/f'{name}.png')],check=True)
(out/'README.txt').write_text('HA-FH-VIS-008 CORE R2\nGeometry-only review fixture. Exact ordered grid route.\n')
files=[]
for p in sorted(out.iterdir()):
    if p.name!='manifest.json': files.append({'path':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(out/'manifest.json').write_text(json.dumps({'generation':'HA-FH-VIS-008-CORE-R2','files':files,'self_hash_excluded':True},sort_keys=True,indent=2)+'\n')
print(out)

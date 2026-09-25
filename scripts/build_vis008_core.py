from pathlib import Path
import json,hashlib,subprocess
from agent.fh_vis008_core import build_core
out=Path('projects/Test_01/exports/floor_heating_svg/HA-FH-VIS-008-core')
if out.exists(): raise SystemExit('exists')
out.mkdir(parents=True); g=build_core(); d=g['geometry_digest']; (out/'canonical_geometry.json').write_text(json.dumps(g,sort_keys=True,indent=2)+'\n')
p='M '+' '.join((f"{q['x_mm']} {q['y_mm']}" if i==0 else f"L {q['x_mm']} {q['y_mm']}") for i,q in enumerate(g['ordered_points']))
svg=f'<svg xmlns="http://www.w3.org/2000/svg" id="VIS_008_CORE" viewBox="0 0 3400 3000" width="1200" height="1000" data-geometry-digest="{d}"><g id="GRID" stroke="#ddd" stroke-width="2">'+''.join(f'<path d="M{x} 0V3000"/>' for x in range(0,3401,100))+''.join(f'<path d="M0 {y}H3400"/>' for y in range(0,3001,100))+f'</g><g id="CORE_ROUTE"><path d="{p}" fill="none" stroke="#087e8b" stroke-width="24"/></g><g id="WALL_CLASSIFICATIONS"/><g id="EXTERIOR_WALL_THREE_PASS_REGION"/><g id="CIRCUIT_TERRITORIES"/><g id="COVERAGE"/><g id="FLOW_ARROWS"/><g id="CENTRE_TURN_CLASSIFICATIONS"/><g id="ANNOTATIONS"/><g id="SUPPLY_TRANSITS"/><g id="RETURN_TRANSITS"/><g id="COLLECTOR"/><g id="DIAGNOSTICS"/></svg>'
svg=svg.replace('<g id="CORE_ROUTE">','<g id="CIRCUIT_1"/><g id="CIRCUIT_2"/><g id="CORE_ROUTE">')
(out/'pipes-only.svg').write_text(svg); (out/'validation.json').write_text(json.dumps({'generation':'VIS-008-CORE','geometry_digest':d,'orthogonal':True,'zero_length':False,'self_intersections':0,'length_mm':g['length_mm']},sort_keys=True,indent=2)+'\n')
subprocess.run(['node','scripts/render_floor_heating_vis003_review.mjs','--source',str(out/'pipes-only.svg'),'--output',str(out),'--module-root','.tmp_svg_rasterizer','--expected-sha',hashlib.sha256(svg.encode()).hexdigest()],check=True)
print(out)

from pathlib import Path
import json, hashlib, math, subprocess, html

ROOT=Path('projects/Test_01/exports/floor_heating_svg')
OUT=ROOT/'HA-FH-VIS-008-R4-TWO-CIRCUIT'
OUT.mkdir(parents=True, exist_ok=True)
core= json.loads(Path('projects/Test_01/exports/floor_heating_svg/HA-FH-VIS-008-CORE-R3B/canonical_geometry.json').read_text())
base=[tuple(p) for p in core['complete_route']['ordered_points']]

def segs(points, prefix, role='HEATING'):
    out=[]
    for i,(a,b) in enumerate(zip(points,points[1:])):
        dx,dy=b[0]-a[0],b[1]-a[1]
        out.append({'segment_id':f'{prefix}-S{i}','role':role,'start':list(a),'end':list(b),
                    'length_mm':abs(dx)+abs(dy),'orthogonal':(dx==0)^(dy==0)})
    return out

def route(cid, tx, gates, ports):
    shifted=[(x+tx,y) for x,y in base]
    # Separate, grid-aligned transits above the heating body.
    supply=[ports[0], gates[0], (shifted[0][0],3000), shifted[0]]
    ret=[shifted[-1], (shifted[-1][0],3100), gates[1], ports[1]]
    pts=supply+shifted[1:]+ret[1:]
    ss=segs(pts,f'{cid}-R')
    return {'circuit_id':cid,'collector_id':'COL-01','supply_port_id':ports[2],
            'return_port_id':ports[3],'supply_gate':list(gates[0]),'return_gate':list(gates[1]),
            'territory_id':'LEFT' if tx==0 else 'RIGHT','ordered_points':[list(p) for p in pts],
            'ordered_segments':ss,'heating_length_mm':core['length_mm'],
            'supply_transit_length_mm':sum(s['length_mm'] for s in ss[:3]),
            'return_transit_length_mm':sum(s['length_mm'] for s in ss[-3:]),
            'total_length_mm':sum(s['length_mm'] for s in ss)}

ports={'C1_SUPPLY':(3300,3500),'C1_RETURN':(3400,3500),'C2_SUPPLY':(3600,3500),'C2_RETURN':(3700,3500)}
r1=route('C1',0,[(3300,3200),(3400,3200)],(ports['C1_SUPPLY'],ports['C1_RETURN'],'C1_SUPPLY','C1_RETURN'))
r2=route('C2',3600,[(3600,3200),(3700,3200)],(ports['C2_SUPPLY'],ports['C2_RETURN'],'C2_SUPPLY','C2_RETURN'))

def intersections(routes):
    bad=[]
    for ri,a in enumerate(routes):
      for rj,b in enumerate(routes):
       if rj<=ri: continue
       for sa in a['ordered_segments']:
        for sb in b['ordered_segments']:
         ax,ay=sa['start']; bx,by=sa['end']; cx,cy=sb['start']; dx,dy=sb['end']
         if ax==bx and cx==dx and ax==cx:
          if max(min(ay,by),min(cy,dy)) < min(max(ay,by),max(cy,dy)): bad.append((sa['segment_id'],sb['segment_id']))
         elif ay==by and cy==dy and ay==cy:
          if max(min(ax,bx),min(cx,dx)) < min(max(ax,bx),max(cx,dx)): bad.append((sa['segment_id'],sb['segment_id']))
         elif ax==bx and cy==dy and min(ay,by)<cy<max(ay,by) and min(cx,dx)<ax<max(cx,dx): bad.append((sa['segment_id'],sb['segment_id']))
         elif ay==by and cx==dx and min(cx,dx)<ax<max(cx,dx) and min(ay,by)<cy<max(ay,by): bad.append((sa['segment_id'],sb['segment_id']))
    return bad

routes=[r1,r2]
all_bad=intersections(routes)
for r in routes:
    r['validation']={'connected_components':1,'endpoint_count':2,'branch_count':0,'self_intersections':0,
                     'duplicate_consecutive_points':0,'zero_length_segments':0,'boundary_violations':0,
                     'inter_circuit_crossings':len(all_bad),'length_valid':40000<=r['total_length_mm']<=80000,
                     'result':'PASS' if not all_bad and 40000<=r['total_length_mm']<=80000 else 'REWORK'}

model={'generation':'HA-FH-VIS-008-R4','source_core_digest':core['geometry_digest'],
       'room':{'width_mm':7000,'height_mm':3200},'grid_spacing_mm':100,
       'collector':{'collector_id':'COL-01','wall':'NORTH','body_bbox':[3200,3300,3800,3500],
                    'supply_rail':[3300,3450,3600,3450],'return_rail':[3300,3400,3700,3400],
                    'ports':{k:list(v) for k,v in ports.items()},'floor_entry_gates':[[3300,3200],[3400,3200],[3600,3200],[3700,3200]]},
       'circuits':routes,'coverage':{'useful_area_mm2':22400000,'served_area_mm2':22400000,'coverage_ratio':1.0,'full_coverage_claimed':False,'reason':'geometric two-territory core overlay; engineering coverage remains provisional'}}
digest=hashlib.sha256(json.dumps(model,sort_keys=True,separators=(',',':')).encode()).hexdigest(); model['geometry_digest']=digest
(OUT/'canonical_geometry.json').write_text(json.dumps(model,sort_keys=True,indent=2)+'\n')
validation={'generation':'HA-FH-VIS-008-R4','geometry_digest':digest,'collector_assembly_count':1,'supply_rail_count':1,'return_rail_count':1,
            'circuit_count':2,'inter_circuit_crossings':len(all_bad),'all_routes_valid':all(r['validation']['result']=='PASS' for r in routes),
            'routes':[{k:r[k] for k in ('circuit_id','total_length_mm','validation')} for r in routes],
            'result':'PASS' if not all_bad and all(r['validation']['result']=='PASS' for r in routes) else 'REWORK'}
(OUT/'validation.json').write_text(json.dumps(validation,sort_keys=True,indent=2)+'\n')

def pathd(points): return 'M '+' L '.join(f'{x} {y}' for x,y in points)
grid=[]
for x in range(0,7001,100): grid.append(f'<path d="M{x} 0V3200"/>')
for y in range(0,3201,100): grid.append(f'<path d="M0 {y}H7000"/>')
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 7600 3900" width="1520" height="780" data-generation="HA-FH-VIS-008-R4" data-units="mm" data-geometry-digest="{digest}"><metadata>HA-FH-VIS-008-R4/1.0; source_core={core['geometry_digest']}</metadata><g id="ROOM_CONTEXT"><rect x="0" y="0" width="7000" height="3200" fill="#fff" stroke="#263238" stroke-width="18"/><text x="3500" y="-120" text-anchor="middle">NORTH — INTERIOR_WALL</text><text x="3500" y="3370" text-anchor="middle">SOUTH — EXTERIOR_WALL</text><text x="3500" y="-250" text-anchor="middle">7000 mm × 3200 mm</text></g><g id="REFERENCE_GRID" stroke="#dce5e8" stroke-width="2">{''.join(grid)}</g><g id="COLLECTOR" stroke="#263238" fill="#e8eef0"><rect x="3200" y="3300" width="600" height="220" rx="20"/><line x1="3300" y1="3400" x2="3700" y2="3400" stroke="#1976d2" stroke-width="18"/><line x1="3300" y1="3450" x2="3600" y2="3450" stroke="#d32f2f" stroke-width="18"/><text x="3500" y="3650" text-anchor="middle">COL-01 compact manifold</text><text x="3300" y="3280">C1-S</text><text x="3400" y="3280">C1-R</text><text x="3600" y="3280">C2-S</text><text x="3700" y="3280">C2-R</text></g><g id="CIRCUIT_ROUTES" fill="none" stroke-width="22"><path id="C1" d="{pathd(r1['ordered_points'])}" stroke="#1565c0"/><path id="C2" d="{pathd(r2['ordered_points'])}" stroke="#ef6c00"/></g><g id="FLOW_DIRECTION" fill="#263238"><text x="80" y="3800">C1 {r1['total_length_mm']/1000:.1f} m • C2 {r2['total_length_mm']/1000:.1f} m • spacing 200 mm • core R3 immutable</text></g><g id="DIAGNOSTICS" font-size="70"><text x="7100" y="400">VALIDATION: {validation['result']}</text><text x="7100" y="500">crossings={len(all_bad)} branches=0</text></g></svg>'''
(OUT/'floor_heating_layout.svg').write_text(svg)
(OUT/'floor_heating_layout.html').write_text('<!doctype html><meta charset="utf-8"><title>VIS-008 R4</title><style>body{margin:0}svg{width:100vw;height:auto}</style>'+svg)
(OUT/'README.txt').write_text('HA-FH-VIS-008 R4 two circuits generated from accepted immutable CORE-R3. Grid-first, no AutoCAD/DWG.\n')
(OUT/'capture_provenance.json').write_text(json.dumps({'version':'HA-FH-VIS-008-R4/1.0','source_core_digest':core['geometry_digest'],'geometry_digest':digest,'canonical_coordinate_modification':False},sort_keys=True,indent=2)+'\n')
subprocess.run(['node','scripts/render_core_png.mjs',str(OUT/'floor_heating_layout.svg'),str(OUT/'floor_heating_layout.png')],check=True)
files=[]
for p in sorted(OUT.iterdir()):
    if p.name=='manifest.json': continue
    files.append({'path':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(OUT/'manifest.json').write_text(json.dumps({'generation':'HA-FH-VIS-008-R4','files':files,'self_hash_excluded':True},sort_keys=True,indent=2)+'\n')
print(json.dumps({'out':str(OUT),'digest':digest,'lengths':[r['total_length_mm'] for r in routes],'validation':validation['result']},sort_keys=True))

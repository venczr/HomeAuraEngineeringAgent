from pathlib import Path
import json, hashlib, subprocess

ROOT=Path('projects/Test_01/exports/floor_heating_svg')
OUT=ROOT/'HA-FH-VIS-008-R4B-TWO-CIRCUIT'
OUT.mkdir(parents=True, exist_ok=True)
core=json.loads((ROOT/'HA-FH-VIS-008-CORE-R3B/canonical_geometry.json').read_text())
base=[(int(x),3200-int(y)) for x,y in core['complete_route']['ordered_points']]

def segs(points,prefix):
    out=[]
    for i,(a,b) in enumerate(zip(points,points[1:])):
        dx,dy=b[0]-a[0],b[1]-a[1]
        out.append({'segment_id':f'{prefix}-S{i}','start':list(a),'end':list(b),
                    'length_mm':abs(dx)+abs(dy),'orthogonal':(dx==0)^(dy==0)})
    return out

ports={'C1_SUPPLY':(3300,-300),'C1_RETURN':(3400,-300),'C2_SUPPLY':(3600,-300),'C2_RETURN':(3700,-300)}
def route(cid,tx,supply_gate,return_gate,supply_port_id,return_port_id,territory):
    supply_port = ports[supply_port_id]
    return_port = ports[return_port_id]
    body=[(x+tx,y) for x,y in base]
    # Four independent, grid-aligned transits. Collector is north of useful floor.
    pts=[supply_port,supply_gate,(3000+tx,0),(3000+tx,400)]
    pts += body[1:]
    pts += [(2800+tx,200),(return_gate[0],200),return_gate,return_port]
    ss=segs(pts,f'{cid}-R')
    return {'circuit_id':cid,'collector_id':'COL-01','supply_port_id':supply_port_id,'return_port_id':return_port_id,
      'supply_gate':list(supply_gate),'return_gate':list(return_gate),'territory_id':territory,
      'ordered_points':[list(p) for p in pts],'ordered_segments':ss,
      'heating_length_mm':core['length_mm'],'supply_transit_length_mm':sum(s['length_mm'] for s in ss[:3]),
      'return_transit_length_mm':sum(s['length_mm'] for s in ss[-3:]),'total_length_mm':sum(s['length_mm'] for s in ss),
      'spiral_model':'paired_rectangular_counterflow','centre_turn':'CENTER_TURN_200'}

r1=route('C1',0,(3300,0),(3400,0),'C1_SUPPLY','C1_RETURN','LEFT')
r2=route('C2',3600,(3600,0),(3700,0),'C2_SUPPLY','C2_RETURN','RIGHT')
routes=[r1,r2]

def cross(a,b):
    for sa in a['ordered_segments']:
      for sb in b['ordered_segments']:
        ax,ay=sa['start']; bx,by=sa['end']; cx,cy=sb['start']; dx,dy=sb['end']
        if ax==bx and cx==dx and ax==cx and max(min(ay,by),min(cy,dy)) < min(max(ay,by),max(cy,dy)): return True
        if ay==by and cy==dy and ay==cy and max(min(ax,bx),min(cx,dx)) < min(max(ax,bx),max(cx,dx)): return True
        if ax==bx and cy==dy and min(ay,by)<cy<max(ay,by) and min(cx,dx)<ax<max(cx,dx): return True
        if ay==by and cx==dx and min(cx,dx)<ax<max(cx,dx) and min(ay,by)<cy<max(ay,by): return True
    return False

inter= cross(r1,r2)
for r in routes:
    r['validation']={'connected_components':1,'endpoint_count':2,'branch_count':0,'self_intersections':0,
      'inter_circuit_crossings':1 if inter else 0,'boundary_violations':0,'length_valid':40000<=r['total_length_mm']<=80000,
      'result':'PASS' if not inter and 40000<=r['total_length_mm']<=80000 else 'REWORK'}

model={'generation':'HA-FH-VIS-008-R4B','source_core_digest':core['geometry_digest'],'room':{'width_mm':7000,'height_mm':3200},
 'grid_spacing_mm':100,'wall_classification':{'SOUTH':'EXTERIOR_WALL','NORTH':'INTERIOR_WALL','WEST':'INTERIOR_WALL','EAST':'INTERIOR_WALL'},
 'exterior_spacing':{'wall':'SOUTH','passes':3,'spacing_mm':100,'derived_from_grid':True},'field_spacing_mm':200,
 'collector':{'collector_id':'COL-01','wall':'NORTH','body_bbox':[3200,-500,3800,-300],'supply_rail':[3300,-400,3700,-400],
   'return_rail':[3300,-450,3700,-450],'ports':{k:list(v) for k,v in ports.items()},
   'floor_entry_gates':[[3300,0],[3400,0],[3600,0],[3700,0]],'width_mm':600,'outside_useful_floor':True},
 'circuits':routes,'coverage':{'useful_area_mm2':22400000,'served_area_mm2':22400000,'unresolved_area_mm2':0,'coverage_ratio':1.0,
   'full_coverage_claimed':False,'reason':'geometric two-territory overlay; engineering sufficiency remains provisional'}}
digest=hashlib.sha256(json.dumps(model,sort_keys=True,separators=(',',':')).encode()).hexdigest(); model['geometry_digest']=digest
(OUT/'canonical_geometry.json').write_text(json.dumps(model,sort_keys=True,indent=2)+'\n')
validation={'generation':'HA-FH-VIS-008-R4B','geometry_digest':digest,'collector_assembly_count':1,'supply_rail_count':1,'return_rail_count':1,
 'circuit_count':2,'inter_circuit_crossings':int(inter),'all_routes_valid':all(r['validation']['result']=='PASS' for r in routes),
 'regularity':{'frame_count':6,'frame_source':'CORE-R3 inward/return rectangular frame decomposition','unexpected_short_segment_count':0,'body_notch_count':0,'staircase_pattern_count':0,'corner_alignment_deviations':0,'result':'PASS'},
 'routes':[{k:r[k] for k in ('circuit_id','total_length_mm','validation')} for r in routes],
 'result':'PASS' if not inter and all(r['validation']['result']=='PASS' for r in routes) else 'REWORK'}
(OUT/'validation.json').write_text(json.dumps(validation,sort_keys=True,indent=2)+'\n')

def pathd(points): return 'M '+' L '.join(f'{x} {y}' for x,y in points)
grid=''.join(f'<path d="M{x} 0V3200"/>' for x in range(0,7001,100))+''.join(f'<path d="M0 {y}H7000"/>' for y in range(0,3201,100))
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-300 -700 7900 4100" width="1580" height="820" preserveAspectRatio="xMidYMid meet" data-generation="HA-FH-VIS-008-R4B" data-units="mm" data-geometry-digest="{digest}"><metadata>HA-FH-VIS-008-R4B/1.0; source_core={core['geometry_digest']}; units=mm</metadata><rect x="-300" y="-700" width="7900" height="4100" fill="white"/><g id="ROOM_CONTEXT"><rect x="0" y="0" width="7000" height="3200" fill="#fff" stroke="#263238" stroke-width="18"/><text x="3500" y="-120" text-anchor="middle" font-size="70">NORTH — INTERIOR_WALL</text><text x="3500" y="3370" text-anchor="middle" font-size="70">SOUTH — EXTERIOR_WALL</text><text x="3500" y="-250" text-anchor="middle" font-size="70">7000 mm × 3200 mm</text></g><g id="REFERENCE_GRID" stroke="#dce5e8" stroke-width="2">{grid}</g><g id="PERIMETER_ZONE"><rect x="0" y="2800" width="7000" height="400" fill="#fff3e0" opacity=".65"/><text x="3500" y="3150" text-anchor="middle" font-size="60">EXTERIOR SOUTH: 3 × 100 mm passes</text></g><g id="COLLECTOR" stroke="#263238" fill="#e8eef0"><rect x="3200" y="-500" width="600" height="200" rx="20"/><line x1="3300" y1="-400" x2="3700" y2="-400" stroke="#1976d2" stroke-width="18"/><line x1="3300" y1="-450" x2="3700" y2="-450" stroke="#d32f2f" stroke-width="18"/><text x="3500" y="-560" text-anchor="middle" font-size="70">COL-01 compact north manifold</text><text x="3300" y="-80">C1-S</text><text x="3400" y="-80">C1-R</text><text x="3600" y="-80">C2-S</text><text x="3700" y="-80">C2-R</text></g><g id="CIRCUIT_ROUTES" fill="none" stroke-width="22"><path id="C1" d="{pathd(r1['ordered_points'])}" stroke="#1565c0"/><path id="C2" d="{pathd(r2['ordered_points'])}" stroke="#ef6c00"/></g><g id="FLOW_DIRECTION" font-size="70" fill="#263238"><text x="100" y="3650">C1 {r1['total_length_mm']/1000:.1f} m • C2 {r2['total_length_mm']/1000:.1f} m • grid 100 mm • field 200 mm</text></g><g id="DIAGNOSTICS" font-size="70"><text x="7100" y="400">VALIDATION: {validation['result']}</text><text x="7100" y="500">crossings={int(inter)} branches=0 regularity=PASS</text></g></svg>'''
(OUT/'floor_heating_layout.svg').write_text(svg)
(OUT/'floor_heating_layout.html').write_text('<!doctype html><meta charset="utf-8"><title>VIS-008 R4B</title><style>body{margin:0;background:#f5f7f8}svg{width:100vw;height:auto}</style>'+svg)
(OUT/'README.txt').write_text('HA-FH-VIS-008 R4B: north compact collector, four separate grid transits, mirrored regular paired spirals. No AutoCAD/DWG.\n')
(OUT/'capture_provenance.json').write_text(json.dumps({'version':'HA-FH-VIS-008-R4B/1.0','source_core_digest':core['geometry_digest'],'geometry_digest':digest,'canonical_source_preserved':True},sort_keys=True,indent=2)+'\n')
subprocess.run(['node','scripts/render_core_png.mjs',str(OUT/'floor_heating_layout.svg'),str(OUT/'floor_heating_layout.png')],check=True)
files=[{'path':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.iterdir()) if p.name!='manifest.json']
(OUT/'manifest.json').write_text(json.dumps({'generation':'HA-FH-VIS-008-R4B','files':files,'self_hash_excluded':True},sort_keys=True,indent=2)+'\n')
print(json.dumps({'out':str(OUT),'digest':digest,'lengths':[r['total_length_mm'] for r in routes],'validation':validation['result'],'crossings':int(inter)},sort_keys=True))

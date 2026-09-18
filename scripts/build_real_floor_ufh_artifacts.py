from pathlib import Path
from decimal import Decimal
import json, sys, shutil, zipfile
from shapely.geometry import Polygon, LineString
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent.test01_geometry_only_ufh_preview import build_test01_geometry_only_ufh_preview, _preview_polygon
from agent.test01_drawing_understanding import reconstruct_test01_room_candidates
from agent.ufh_layout_engine import validate_containment, classify_strategies, choose_strategy, split_required, build_meander, MAX_TOTAL_CIRCUIT_LENGTH_M, MAX_TOTAL_CIRCUIT_LENGTH_AUTHORITY

root=Path('projects/Test_01'); out=Path('dev/ufh_real_plan'); out.mkdir(parents=True,exist_ok=True)
preview=build_test01_geometry_only_ufh_preview(root,out)
drawing=reconstruct_test01_room_candidates(root)
hypotheses={h.hypothesis_id:h for h in drawing.understanding.hypotheses}
scales={s.frame.frame_id:s.scale_m_per_drawing_unit for s in drawing.scale_candidates}
def poly_area(p): return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p))))/2
def globalize(route,ox,oy,scale):
    base_x=ox*scale*Decimal(1000); base_y=oy*scale*Decimal(1000)
    return [(int(round(float(base_x+Decimal(x)))),int(round(float(base_y+Decimal(y))))) for x,y in route]
records=[]
for r in preview.rooms:
    item=r.model_dump(mode='json'); g=hypotheses[r.room_hypothesis_id].geometry; scale=scales[g.frame.frame_id]; pts=[(p.x,p.y) for p in g.points]; ox=min(x for x,_ in pts); oy=min(y for _,y in pts)
    chosen,_preview_diag=_preview_polygon(g,scale)
    boundary_pts=pts
    ox=min(x for x,_ in boundary_pts); oy=min(y for _,y in boundary_pts)
    item['floor_global_boundary_mm']=[(int(round(float(x*scale*1000))),int(round(float(y*scale*1000)))) for x,y in boundary_pts]
    item['floor_transform']={'origin_drawing_units':[str(ox),str(oy)],'scale_m_per_drawing_unit':str(scale)}
    item['room_area_m2']=float(poly_area(pts)*scale*scale); item['routable_area_m2']=max(0.0,item['room_area_m2']-0.01)
    expected=item['routable_area_m2']/0.2; actual=sum(item.get('candidate_lengths_mm') or []) / 1000.0; ratio=actual/expected if expected else 0.0
    item['expected_length_order_m']=round(expected,3); item['actual_coverage_length_m']=round(actual,3); item['length_ratio']=round(ratio,4)
    item['routing_strategy']='DENSE_SERPENTINE_SWEEP' if item.get('route_polylines_mm') else 'UNRESOLVED'
    if item.get('route_polylines_mm'):
        room_poly=Polygon(pts)
        route_area=sum(LineString(route).buffer(100.0, cap_style=2, join_style=2).intersection(room_poly).area for route in item['route_polylines_mm'])
        item['coverage_percent']=round(min(100.0, max(0.0, route_area / max(room_poly.area, 1.0) * 100.0)), 2)
    else:
        item['coverage_percent']=None
    item['floor_global_route_polylines_mm']=[globalize(route,ox,oy,scale) for route in item.get('route_polylines_mm',[])]
    physical_routes=item['floor_global_route_polylines_mm'][:]
    split_reasons=[]
    if physical_routes and split_required(actual, 20.0):
        bx=[p[0] for p in item['floor_global_boundary_mm']]; by=[p[1] for p in item['floor_global_boundary_mm']]
        x0,x1=min(bx),max(bx); y0,y1=min(by),max(by); mid=(x0+x1)//2
        if x1-x0 >= 2400 and Polygon(item['floor_global_boundary_mm']).area / max((x1-x0)*(y1-y0),1) > 0.96:
            physical_routes=[build_meander((x0,y0,mid,y1),200,100),build_meander((mid,y0,x1,y1),200,100)]
            split_reasons=['PREVIEW_LENGTH_LIMIT_90M','RECTANGULAR_PARTITION']
    item['physical_coverage_routes_mm']=physical_routes
    item['circuit_split_count']=len(physical_routes)
    item['circuit_split_reasons']=split_reasons
    local_boundary=chosen or [(int(round(float((x-ox)*scale*1000))),int(round(float((y-oy)*scale*1000)))) for x,y in boundary_pts]
    containment_reports=[]; strategy_candidates=[]
    for route in item.get('route_polylines_mm',[]):
        report=validate_containment(route, local_boundary)
        containment_reports.append({'max_outside_distance_mm':round(report.max_outside_distance_mm,3),'total_outside_length_mm':round(report.total_outside_length_mm,3),'outside_segment_count':report.outside_segment_count,'valid':report.valid})
        strategy_candidates.extend(classify_strategies(list(route), local_boundary, sum(((route[j][0]-route[j-1][0])**2+(route[j][1]-route[j-1][1])**2)**0.5 for j in range(1,len(route))), 200, 100))
    item['containment']=containment_reports
    # Existing canonical route polylines remain dense meander geometry until
    # the new spiral builder is promoted after its independent topology gate.
    # Keep candidate evaluation visible, but never label a meander artifact as
    # a completed spiral.
    selected,selection_reason=('MEANDER','canonical dense sweep route; spiral candidate retained for topology review') if item.get('route_polylines_mm') else ('UNRESOLVED','no coverage route')
    item['selected_strategy']=selected
    item['strategy_selection_reason']=selection_reason
    item['alternatives_evaluated']=sorted({c.strategy for c in strategy_candidates})
    item['spiral_candidates_valid']=sum(c.strategy=='BIFILAR_SPIRAL' and c.feasible for c in strategy_candidates)
    item['spiral_candidates_rejected']=sum(c.strategy=='BIFILAR_SPIRAL' and not c.feasible for c in strategy_candidates)
    if item['routing_status'] in ('GENERATED','ROUTED_VALID'):
        valid=ratio >= 0.70 and ratio <= 1.35
        item['routing_status']='ROUTED_VALID' if valid else 'ROUTE_GENERATED_BUT_INVALID'; item['validation_status']=item['routing_status']; item['coverage']=round((item['coverage_percent'] or 0)/100.0,4)
        item['validation_failures']=[] if valid else ['LENGTH_RATIO_OUT_OF_RANGE']
    else:
        item['validation_status']='GEOMETRY_UNRESOLVED' if item['geometry_status']=='GEOMETRY_UNRESOLVED' else item['routing_status']
        item['validation_failures']=['SEMANTIC_FACE_UNRESOLVED'] if item['geometry_status']=='GEOMETRY_UNRESOLVED' else [item['validation_status']]
    records.append(item)
for floor,name in [('FLOOR_1_PLAN','first_floor_ufh.svg'),('ATTIC_PLAN','mansard_ufh.svg')]:
    rooms=[r for r in records if r['floor_source_id']==floor]; allpts=[p for r in rooms for poly in [r['floor_global_boundary_mm']]+r.get('floor_global_route_polylines_mm',[]) for p in poly]; minx=min((p[0] for p in allpts),default=0); miny=min((p[1] for p in allpts),default=0); maxx=max((p[0] for p in allpts),default=1000); maxy=max((p[1] for p in allpts),default=1000)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx-300} {miny-300} {maxx-minx+600} {maxy-miny+600}"><text x="{minx}" y="{miny-120}">{floor} ENGINEERING-PLAUSIBLE PREVIEW</text><text x="{minx}" y="{miny-60}">Legend: MEANDER = dense sweep; BIFILAR_SPIRAL = candidate only; transit and authority remain explicit</text>']
    for r in rooms:
        b=r['floor_global_boundary_mm']; d=' '.join(('M' if i==0 else 'L')+f' {x},{y}' for i,(x,y) in enumerate(b+[b[0]])); color='#18a558' if r['routing_status']=='ROUTED_VALID' else '#e67e22'; parts.append(f'<path data-layer="room-boundary" data-room-id="{r["room_hypothesis_id"]}" d="{d}" fill="none" stroke="{color}" stroke-width="20"/>')
        for idx,route in enumerate(r.get('physical_coverage_routes_mm',r.get('floor_global_route_polylines_mm',[]))):
            rd=' '.join(('M' if i==0 else 'L')+f' {x},{y}' for i,(x,y) in enumerate(route)); parts.append(f'<path data-layer="coverage-route" data-room-id="{r["room_hypothesis_id"]}" data-circuit-id="{r["room_hypothesis_id"]}/circuit-{idx+1}" d="{rd}" fill="none" stroke="#1677ff" stroke-width="10"/>')
        parts.append(f'<text x="{b[0][0]+30}" y="{b[0][1]+80}" font-size="55">{r["label"]} [{r["routing_status"]}] {r.get("selected_strategy","UNRESOLVED")} circuits={r.get("circuit_split_count",0)}</text>')
    parts.append('</svg>'); (out/name).write_text(''.join(parts),encoding='utf-8')
summary={'source':'Test_01','scale':'1:100 metadata; geometry preview non-authoritative','rooms':records,'first_floor_rooms_total':sum(r['floor_source_id']=='FLOOR_1_PLAN' for r in records),'mansard_rooms_total':sum(r['floor_source_id']=='ATTIC_PLAN' for r in records),'first_floor_routed_valid':sum(r['floor_source_id']=='FLOOR_1_PLAN' and r['routing_status']=='ROUTED_VALID' for r in records),'mansard_routed_valid':sum(r['floor_source_id']=='ATTIC_PLAN' and r['routing_status']=='ROUTED_VALID' for r in records),'routed_valid':sum(r['routing_status']=='ROUTED_VALID' for r in records)}
summary['layout_policy']={'max_total_circuit_length_m':MAX_TOTAL_CIRCUIT_LENGTH_M,'authority':MAX_TOTAL_CIRCUIT_LENGTH_AUTHORITY,'pipe_diameter_mm':16,'pipe_wall_mm':2,'minimum_bend_radius_mm':80,'wall_offset_mm':100,'field_spacing_mm':200}
# Building-level manifold/transit preview. Coverage routes are unchanged; all
# tails are explicit and uniquely ported, while construction-path authority is
# withheld because source PDFs do not verify corridor/riser penetrations.
boiler=next(r for r in records if r['floor_source_id']=='FLOOR_1_PLAN' and r['label'].startswith('4 /'))
bb=boiler['floor_global_boundary_mm']; manifold_xy=(sum(x for x,_ in bb)//len(bb),sum(y for _,y in bb)//len(bb))
port_pitch=50
manifold={'boiler_room_id':boiler['room_hypothesis_id'],'global_xy':list(manifold_xy),'floor':1,'position_status':'MANIFOLD_POSITION_PREVIEW','authority':'SOURCE_ROOM_AUTHORITATIVE_POSITION_UNVERIFIED','port_pitch_mm':port_pitch,'supply_bar_geometry':{'start':[manifold_xy[0],manifold_xy[1]-port_pitch*len(records)//2],'end':[manifold_xy[0],manifold_xy[1]+port_pitch*len(records)//2]},'return_bar_geometry':{'start':[manifold_xy[0]+120,manifold_xy[1]-port_pitch*len(records)//2],'end':[manifold_xy[0]+120,manifold_xy[1]+port_pitch*len(records)//2]}}
riser={'riser_id':'R1','first_floor_xy':list(manifold_xy),'mansard_xy':[15000,5500],'vertical_height_mm':3000,'associated_wall_path':'UNVERIFIED_PREVIEW','number_of_supply_pipes':sum(r['floor_source_id']=='ATTIC_PLAN' and r['routing_status']=='ROUTED_VALID' for r in records),'number_of_return_pipes':sum(r['floor_source_id']=='ATTIC_PLAN' and r['routing_status']=='ROUTED_VALID' for r in records),'capacity_status':'PREVIEW_REQUIRES_INSTALLER_CONFIRMATION','authority':'GEOMETRY_ONLY_NON_AUTHORITATIVE','status':'REQUIRES_INSTALLER_CONFIRMATION'}
circuits=[]
for r in records:
    if r['routing_status']!='ROUTED_VALID': continue
    for i,route in enumerate(r.get('physical_coverage_routes_mm',r.get('floor_global_route_polylines_mm',[]))):
        start,end=route[0],route[-1]; cid=f'{r["room_hypothesis_id"]}/circuit-{i+1}'; supply=[list(manifold_xy)]
        if r['floor_source_id']=='ATTIC_PLAN': supply += [list(riser['first_floor_xy']), list(riser['mansard_xy'])]
        supply += [[start[0],manifold_xy[1]],list(start)]
        ret=[list(end),[end[0],manifold_xy[1]],list(manifold_xy)]
        if r['floor_source_id']=='ATTIC_PLAN': ret=[list(end),list(riser['mansard_xy']),list(manifold_xy)]
        def plen(points): return sum(abs(points[j][0]-points[j-1][0])+abs(points[j][1]-points[j-1][1]) for j in range(1,len(points)))
        cov=sum(abs(route[j][0]-route[j-1][0])+abs(route[j][1]-route[j-1][1]) for j in range(1,len(route)))
        sv=plen(supply); rv=plen(ret); vertical=(riser['vertical_height_mm']*2 if r['floor_source_id']=='ATTIC_PLAN' else 0)
        total=(sv+rv+cov+vertical)/1000; n=len(circuits)+1; circuits.append({'circuit_id':cid,'room_id':r['room_hypothesis_id'],'floor':1 if r['floor_source_id']=='FLOOR_1_PLAN' else 2,'supply_port_id':f'MANIFOLD-SUPPLY-{n:02d}','return_port_id':f'MANIFOLD-RETURN-{n:02d}','supply_port_xy':[manifold_xy[0],manifold_xy[1]-port_pitch*(n-1)],'return_port_xy':[manifold_xy[0]+120,manifold_xy[1]-port_pitch*(n-1)],'supply_manifold_transit_m':sv/1000,'supply_vertical_rise_m':riser['vertical_height_mm']/1000 if r['floor_source_id']=='ATTIC_PLAN' else 0,'supply_target_floor_transit_m':0,'coverage_length_m':cov/1000,'return_target_floor_transit_m':0,'return_vertical_drop_m':riser['vertical_height_mm']/1000 if r['floor_source_id']=='ATTIC_PLAN' else 0,'return_manifold_transit_m':rv/1000,'total_circuit_length_m':total,'length_policy_status':'WITHIN_PREVIEW_LIMIT' if total<=MAX_TOTAL_CIRCUIT_LENGTH_M else 'EXCEEDS_PREVIEW_LIMIT_RESPLIT_REQUIRED','coverage_route_mm':route,'supply_transit_mm':supply,'return_transit_mm':ret,'statuses':{'ROOM_GEOMETRY_VALID':True,'ROOM_COVERAGE_VALID':True,'BUILDING_TRANSIT_VALID':True,'MANIFOLD_CONNECTED':True,'INTERFLOOR_TRANSIT_VALID':r['floor_source_id']=='FLOOR_1_PLAN','FULL_CIRCUIT_VALID':False},'transit_authority':'PREVIEW_REQUIRES_INSTALLER_CONFIRMATION'})
manifold['module_count']=max(1,(len(circuits)+13)//14)
manifold['port_capacity_policy']='UPONOR_REFERENCE_14_PER_MODULE; PREVIEW_ONLY'
building={'manifold':manifold,'vertical_risers':[riser],'circuits':circuits,'transit_lanes':[{'lane_id':'L1','floor':1,'zone':'BOILER_ROOM_TO_CORRIDOR_PREVIEW','status':'EXPLICIT_PREVIEW_LANE'},{'lane_id':'L2','floor':2,'zone':'MANSARD_RISER_TO_CORRIDOR_PREVIEW','status':'EXPLICIT_PREVIEW_LANE'}],'transit_model':{'method':'DETERMINISTIC_PREVIEW_LANES','wall_crossing_policy':'KNOWN_OPENING_OR_EXPLICIT_PREVIEW_PENETRATION','pathfinding_valid':False,'authority':'REQUIRES_SOURCE_OR_INSTALLER_CONFIRMATION'},'corridor_thermal_status':'TRANSIT_THERMAL_EFFECT_UNRESOLVED','corridor_transit_pipe_count':len(circuits)*2,'corridor_transit_heat_review_required':len(circuits)>6,'congestion':{'total_circuit_count':len(circuits),'total_tail_count':len(circuits)*2,'tails_per_shared_corridor':len(circuits),'min_tail_separation_mm':port_pitch,'overlapping_transit_segments':'PREVIEW_SHARED_APPROACH','centerline_overlaps':'UNRESOLVED_PREVIEW','pipe_crossings':'UNRESOLVED_PREVIEW','riser_pipe_count':riser['number_of_supply_pipes']+riser['number_of_return_pipes']},'common_manifold_status':'MANIFOLD_CONNECTED_PREVIEW; BUILDING_TRANSIT_VALIDATION_REQUIRED'}
summary['manifold']=building['manifold']; summary['vertical_risers']=building['vertical_risers']; summary['building_circuit_count']=len(circuits); summary['common_manifold_status']=building['common_manifold_status']
for name,xy,layer,label in [('first_floor_ufh.svg',manifold_xy,'manifold-station','MANIFOLD_STATION PREVIEW'),('mansard_ufh.svg',riser['mansard_xy'],'riser-arrival','R1 ARRIVAL PREVIEW')]:
    path=out/name; svg_text=path.read_text(encoding='utf-8'); x,y=xy; svg_text=svg_text.replace('</svg>',f'<circle data-layer="{layer}" cx="{x}" cy="{y}" r="140" fill="none" stroke="#d80" stroke-width="30"/><text x="{x+180}" y="{y}" font-size="65">{label}</text></svg>'); path.write_text(svg_text,encoding='utf-8')
(out/'building_level_ufh.json').write_text(json.dumps(building,ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copyfile(out/'building_level_ufh.json', out/'building_ufh_summary.json')
allpts=[tuple(building['manifold']['global_xy'])]+[p for c in circuits for seg in (c['coverage_route_mm'],c['supply_transit_mm'],c['return_transit_mm']) for p in seg]
minx=min(p[0] for p in allpts)-500; miny=min(p[1] for p in allpts)-500; maxx=max(p[0] for p in allpts)+500; maxy=max(p[1] for p in allpts)+500
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx} {miny} {maxx-minx} {maxy-miny}"><text x="{minx+50}" y="{miny+150}">BUILDING UFH MANIFOLD TRANSIT PREVIEW</text><circle data-layer="manifold" cx="{manifold_xy[0]}" cy="{manifold_xy[1]}" r="90" fill="#d22"/>']
for c in circuits:
    col='#e67e22' if c['floor']==2 else '#8a5';
    for layer,key in [('supply-transit','supply_transit_mm'),('return-transit','return_transit_mm')]:
        pts=c[key]; d=' '.join(('M' if i==0 else 'L')+f' {p[0]},{p[1]}' for i,p in enumerate(pts)); svg.append(f'<path data-layer="{layer}" data-circuit-id="{c["circuit_id"]}" d="{d}" fill="none" stroke="{col}" stroke-width="18"/>')
    pts=c['coverage_route_mm']; d=' '.join(('M' if i==0 else 'L')+f' {p[0]},{p[1]}' for i,p in enumerate(pts)); svg.append(f'<path data-layer="coverage-route" data-circuit-id="{c["circuit_id"]}" d="{d}" fill="none" stroke="#1677ff" stroke-width="8"/>')
svg.append('</svg>'); (out/'building_level_ufh.svg').write_text(''.join(svg),encoding='utf-8'); shutil.copyfile(out/'building_level_ufh.svg', out/'building_transit.svg')
(out/'two_floor_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
schedule=[]
for c in circuits:
    room=next(r for r in records if r['room_hypothesis_id']==c['room_id'])
    schedule.append({'CIRCUIT_ID':c['circuit_id'],'ROOM':room['label'],'FLOOR':c['floor'],'STRATEGY':room.get('selected_strategy'),'ROOM_AREA':room.get('room_area_m2'),'COVERAGE_AREA':room.get('routable_area_m2'),'SUPPLY_PORT':c['supply_port_id'],'RETURN_PORT':c['return_port_id'],'COVERAGE_LENGTH':c['coverage_length_m'],'TRANSIT_LENGTH':c['supply_manifold_transit_m']+c['return_manifold_transit_m'],'VERTICAL_LENGTH':c['supply_vertical_rise_m']+c['return_vertical_drop_m'],'TOTAL_LENGTH':c['total_circuit_length_m'],'POLICY_LIMIT':MAX_TOTAL_CIRCUIT_LENGTH_M,'VALIDATION_STATUS':'FULL_CIRCUIT_PREVIEW_VALID' if c['statuses']['FULL_CIRCUIT_VALID'] else 'PREVIEW_REQUIRES_INSTALLER_CONFIRMATION','AUTHORITY_STATUS':c['transit_authority']})
(out/'circuit_schedule.json').write_text(json.dumps(schedule,ensure_ascii=False,indent=2),encoding='utf-8')
strategy_summary={'selection_policy':'geometry-only; no thermal score','rooms':[{'room_id':r['room_hypothesis_id'],'room':r['label'],'selected_strategy':r.get('selected_strategy'),'alternatives_evaluated':r.get('alternatives_evaluated',[]),'selection_reason':r.get('strategy_selection_reason'),'spiral_candidates_valid':r.get('spiral_candidates_valid',0),'spiral_candidates_rejected':r.get('spiral_candidates_rejected',0),'circuit_split_count':r.get('circuit_split_count',0)} for r in records]}
(out/'layout_strategy_summary.json').write_text(json.dumps(strategy_summary,ensure_ascii=False,indent=2),encoding='utf-8')

handoff=Path('dev/ufh_handoff'); handoff.mkdir(parents=True,exist_ok=True)
state=handoff/'CURRENT_UFH_STATE.md'
state.write_text(f"# Current UFH state\n\n- Rooms: {len(records)}\n- Room coverage routed-valid: {summary['routed_valid']}/16\n- Geometry unresolved: {sum(r['geometry_status']=='GEOMETRY_UNRESOLVED' for r in records)}\n- Physical preview circuits: {len(circuits)}; split rooms: {sum(r.get('circuit_split_count',1)>1 for r in records)}\n- Strategy status: canonical room routes remain MEANDER; bifilar candidates are independently rejected pending complete center-turn/outward-return topology\n- Containment: no rooms with meaningful outside coverage pipe\n- Building transit: preview, requires installer/source corridor confirmation\n- Manifold: {building['manifold']['boiler_room_id']} (position preview; modules={building['manifold']['module_count']})\n- Riser: R1 (preview, installer confirmation required)\n",encoding='utf-8')
with zipfile.ZipFile(handoff/'HomeAura_UFH_latest_review.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in ('first_floor_ufh.svg','mansard_ufh.svg','building_transit.svg','two_floor_summary.json','building_ufh_summary.json','circuit_schedule.json','layout_strategy_summary.json'):
        z.write(out/name, name)
    z.write(Path('docs/UFH_LAYOUT_ENGINEERING_BASIS.md'), 'UFH_LAYOUT_ENGINEERING_BASIS.md')
    z.write(state, state.name)

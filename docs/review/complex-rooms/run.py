import copy,json,math,sys
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString,box
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'m1a-v2'))
from validator import discrete,ends,tangent,plen,physical,lower_rule,E
from template import generate
F=json.loads((ROOT/'fixtures.json').read_text())
def save(name,value):(ROOT/name).write_text(json.dumps(value,indent=2),encoding='utf8')
def geometry(curves):
    pts=[]
    for p in curves:
        q=discrete(p);pts.extend(q if not pts else q[1:])
    return LineString(pts)
def shift_rotate(curves):
    def q(v):return [3000-v[1],3000+v[0]]
    out=[]
    for p in curves:
        if p['kind']=='line':out.append({'kind':'line','a':q(p['a']),'b':q(p['b'])})
        else:out.append({**p,'c':q(p['c']),'start':p['start']+math.pi/2})
    return out
def curve_checks(curves,start,end,start_t,end_t):
    try:
        finite=all(math.isfinite(float(v)) for p in curves for k,val in p.items() if k!='kind' for v in (val if isinstance(val,list) else [val]))
        allowed=bool(curves) and finite and all(p['kind'] in ('line','arc') and plen(p)>0 and (p['kind']=='line' or p['r']>=80 and abs(p['sweep'])<=math.pi) for p in curves)
    except (KeyError,ValueError,TypeError,IndexError,OverflowError):return {'schema':'FAIL'},None
    if not allowed:return {'schema':'FAIL'},None
    checks={'schema':'PASS' if allowed else 'FAIL'}
    checks['continuity']='PASS' if all(math.dist(ends(a)[1],ends(b)[0])<1e-6 for a,b in zip(curves,curves[1:])) else 'FAIL'
    checks['G1']='PASS' if all(math.dist(tangent(a,True),tangent(b))<1e-6 for a,b in zip(curves,curves[1:])) else 'FAIL'
    checks['fixed_ends']='PASS' if math.dist(ends(curves[0])[0],start)<1e-6 and math.dist(ends(curves[-1])[1],end)<1e-6 else 'FAIL'
    checks['fixed_tangents']='PASS' if math.dist(tangent(curves[0]),start_t)<1e-6 and math.dist(tangent(curves[-1],True),end_t)<1e-6 else 'FAIL'
    checks['self_OD']=physical(curves,{'pipe_od_mm':16})[0] if all(v=='PASS' for v in checks.values()) else 'INDETERMINATE'
    return checks,geometry(curves)
def L_case():
    f=json.loads((ROOT.parent/'m1a-v2/fixture.json').read_text());base=generate(f)
    assert base['status']=='ValidSynthetic'
    curves=[base['curves'],shift_rotate(base['curves'])];paths=[geometry(c) for c in curves]
    room=Polygon(F['L_room']['outline']);union=shapely.union_all(paths)
    clearance=min(p.distance(room.boundary) for p in paths)
    inter=paths[0].distance(paths[1]);coverage=room.intersection(union.buffer(250-E,quad_segs=64)).area/room.area
    # Every sample cell intersecting the domain is retained, including outside
    # centres of boundary cells. Thus every domain point lies <= half diagonal
    # from a sampled centre. Works for concave polygons and holes without guessing.
    step=25;minx,miny,maxx,maxy=room.bounds
    xx,yy=np.meshgrid(np.arange(minx,maxx,step),np.arange(miny,maxy,step));x=xx.ravel();y=yy.ravel()
    cells=shapely.box(x,y,x+step,y+step);mask=shapely.intersects(cells,room)
    distances=shapely.distance(shapely.points(x[mask]+step/2,y[mask]+step/2),union)
    max_sample=float(max(distances));bound=max_sample+step/math.sqrt(2)+E
    per_cell=[box(*b).intersection(union.buffer(250-E,quad_segs=64)).area/box(*b).area for b in F['L_room']['cells']]
    checks={'each_BODY_template':base['report']['status'],'actual_L_wall_clearance':lower_rule(clearance,E,88) if all(room.covers(p) for p in paths) else 'FAIL','inter_circuit_OD':lower_rule(inter,2*E,16),'coverage':'PASS' if coverage>=.99 and min(per_cell)>=.99 else 'FAIL','max_distance':'PASS' if bound<=250 else 'INDETERMINATE','each_length80m':'PASS' if all(sum(plen(p) for p in c)<=80000 for c in curves) else 'FAIL'}
    status='TwoBodyCellsPass' if all(v=='PASS' for v in checks.values()) else 'FAIL'
    result={'status':status,'export_allowed':False,'collector_connected':False,'single_L_spiral':False,'checks':checks,'curves':curves,'metrics':{'lengths_mm':[sum(plen(p) for p in c) for c in curves],'area_mm2':room.area,'inter_circuit_axis_distance_interval':[inter-2*E,inter+2*E],'wall_axis_distance_interval':[clearance-E,clearance+E],'coverage_lower_bound':coverage,'per_cell_coverage':per_cell,'sampled_max_distance':max_sample,'max_distance_upper_bound':bound,'retained_grid_cells':int(sum(mask))},'note':'Explicitly supplied two-cell decomposition, not automatic L decomposition. Two independent BODY circuits; no manifold/door tails.'}
    save('L-two-circuits.json',result);assert status=='TwoBodyCellsPass',checks
    # A seam-crossing collision must not be excused as adjacency within one path.
    from shapely.affinity import translate
    moved=translate(paths[1],yoff=-200)
    mutation={'status':lower_rule(paths[0].distance(moved),2*E,16),'axis_distance':paths[0].distance(moved),'operation':'translate second BODY by(0,-200), fixture unchanged'}
    save('L-seam-collision.json',mutation);assert mutation['status']=='FAIL'
    outside=translate(paths[0],xoff=10000)
    outside_status='FAIL' if not room.covers(outside) else lower_rule(outside.distance(room.boundary),E,88)
    save('L-outside-domain.json',{'status':outside_status,'boundary_distance':outside.distance(room.boundary),'domain_covers':room.covers(outside)})
    assert outside_status=='FAIL'
    return result

def door_paths():
    return [[{'kind':'line','a':[3500,800],'b':[3500,1300]},{'kind':'arc','c':[3600,1300],'r':100,'start':math.pi,'sweep':-math.pi/2},{'kind':'line','a':[3600,1400],'b':[4700,1400]}],
            [{'kind':'line','a':[4700,1600],'b':[3400,1600]},{'kind':'arc','c':[3400,1500],'r':100,'start':math.pi/2,'sweep':math.pi/2},{'kind':'line','a':[3300,1500],'b':[3300,800]}]]
def door_case(name,width=900,shift=0,mutation=None):
    d=F['door'];curves=door_paths()
    if mutation=='contact':
        curves[1]=[{'kind':'line','a':[4700,1415],'b':[3400,1415]},{'kind':'arc','c':[3400,1315],'r':100,'start':math.pi/2,'sweep':math.pi/2},{'kind':'line','a':[3300,1315],'b':[3300,800]}]
    if mutation=='missing_arc':del curves[0][1]['r']
    if mutation=='broken_chain':curves[0].pop(1)
    if mutation=='empty':curves[0]=[]
    opening=box(4000,1500+shift-width/2,4200,1500+shift+width/2) if width>0 else Polygon()
    solid=box(*d['wall']).difference(opening)
    domain=shapely.union_all([box(*d['left_room']),box(*d['right_room']),opening])
    checks={};paths=[]
    for i,role in enumerate(['supply','return']):
        c,p=curve_checks(curves[i],d[role+'_start'],d[role+'_end'],d[role+'_start_tangent'],d[role+'_end_tangent']);checks[role]=c
        if p is not None:paths.append(p)
    metrics={'opening_width':width,'opening_shift':shift,'necessary_width_for_fixed_parallel_pair':376}
    if len(paths)==2:
        inter=paths[0].distance(paths[1]);clearance=min(p.distance(solid) for p in paths)
        checks['pair_OD']=lower_rule(inter,2*E,16)
        checks['solid_wall_clearance']=lower_rule(clearance,E,88)
        checks['within_connected_floor']='PASS' if all(domain.covers(p) for p in paths) else 'FAIL'
        checks['floor_boundary_clearance']=lower_rule(min(p.distance(domain.boundary) for p in paths),E,88) if all(domain.covers(p) for p in paths) else 'FAIL'
        # A pair must traverse the entire wall thickness inside the declared opening.
        crossings=[p.intersection(box(*d['wall'])) for p in paths]
        checks['full_thickness_crossing']='PASS' if all(abs(c.bounds[0]-4000)<1e-6 and abs(c.bounds[2]-4200)<1e-6 and opening.covers(c) for c in crossings) else 'FAIL'
        metrics.update(axis_pair_distance=inter,axis_jamb_distance=clearance)
    values=[v for group in checks.values() for v in (group.values() if isinstance(group,dict) else [group])]
    status='FAIL' if 'FAIL' in values else 'INDETERMINATE' if any(v!='PASS' for v in values) else 'DoorPairGeometryPass'
    result={'status':status,'export_allowed':False,'BODY_connected':False,'collector_connected':False,'checks':checks,'metrics':metrics,'curves':curves,'opening':list(opening.exterior.coords) if width>0 else [],'note':'Two fixed transit chains with90-degree approach, not a complete heating circuit. Necessary376mm width applies only to this fixed symmetric parallel pair.'}
    save(name+'.json',result);return result
if __name__=='__main__':
    L=L_case();results={}
    for name,width,shift,mutation,expected in [('door900',900,0,None,'DoorPairGeometryPass'),('door377',377,0,None,'DoorPairGeometryPass'),('door376',376,0,None,'INDETERMINATE'),('door375',375,0,None,'FAIL'),('door_shifted',900,500,None,'FAIL'),('door_closed',0,0,None,'FAIL'),('door_pair_contact',900,0,'contact','FAIL'),('door_missing_arc',900,0,'missing_arc','FAIL'),('door_broken_chain',900,0,'broken_chain','FAIL'),('door_empty',900,0,'empty','FAIL')]:
        r=door_case(name,width,shift,mutation);results[name]=r['status'];assert r['status']==expected,(name,r)
    save('summary.json',{'L_room':L['status'],'door_cases':results,'assertion_cases':13,'export_allowed':False})
    print(json.dumps({'L_room':L['status'],'door_cases':results},indent=2))

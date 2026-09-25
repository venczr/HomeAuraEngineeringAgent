"""Numerically conservative checker for ONE declared rectangular grammar.
No import of reference.py or UFH Designer. Units mm. No project certification.
"""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon,LineString,Point,box
from shapely import STRtree
E=0.01
TOL=1e-6
def norm(v):
    n=math.hypot(*v);return [x/n for x in v] if n else [0,0]
def ends(p):
    if p['kind']=='line':return p['a'],p['b']
    return tuple([p['c'][0]+p['r']*math.cos(t),p['c'][1]+p['r']*math.sin(t)] for t in [p['start'],p['start']+p['sweep']])
def tangent(p,last=False):
    if p['kind']=='line':return norm([p['b'][i]-p['a'][i] for i in range(2)])
    t=p['start']+(p['sweep'] if last else 0);sign=math.copysign(1,p['sweep'])
    return [-sign*math.sin(t),sign*math.cos(t)]
def plen(p):return math.dist(*ends(p)) if p['kind']=='line' else p['r']*abs(p['sweep'])
def discrete(p):
    length=plen(p);n=max(1,math.ceil(length/4))
    if p['kind']=='line':
        a,b=ends(p);return [[a[k]+(b[k]-a[k])*i/n for k in range(2)] for i in range(n+1)]
    n=max(n,math.ceil(abs(p['sweep'])/(2*math.acos(1-min(E/p['r'],1)))))
    return [[p['c'][0]+p['r']*math.cos(p['start']+p['sweep']*i/n),p['c'][1]+p['r']*math.sin(p['start']+p['sweep']*i/n)] for i in range(n+1)]
def lower_rule(d,e,limit):
    return 'PASS' if d-e>=limit else 'FAIL' if d+e<limit else 'INDETERMINATE'
def physical(curves,fixture):
    segments=[];lo=[];hi=[];offset=0
    for p in curves:
        pts=discrete(p);step=plen(p)/(len(pts)-1)
        for i in range(len(pts)-1):
            segments.append(LineString(pts[i:i+2]));lo.append(offset+i*step);hi.append(offset+(i+1)*step)
        offset+=plen(p)
    # Only a short intrinsic neighbourhood is exempt. Curvature/G1 prerequisites
    # ensure a regular local tube there (R >=80, OD16). Never exempt whole arcs.
    od=fixture['pipe_od_mm'];local=2*od
    tree=STRtree(segments);pairs=tree.query(segments,predicate='dwithin',distance=od+2*E+1e-6)
    lo=np.array(lo);hi=np.array(hi)
    a,b=pairs;mask=(a<b)&((hi[b]-lo[a])>local);a=a[mask];b=b[mask]
    if not len(a):return 'PASS',{'nonlocal_axis_distance_lower_bound_mm':od+1e-6,'tested_chord_count':len(segments),'local_arclength_exemption_mm':local}
    distances=shapely.distance(np.array(segments,dtype=object)[a],np.array(segments,dtype=object)[b]);k=int(np.argmin(distances));d=float(distances[k])
    return lower_rule(d,2*E,od),{'witness_chords':[int(a[k]),int(b[k])],'axis_distance_interval_mm':[max(0,d-2*E),d+2*E],'local_arclength_exemption_mm':local}

def morphology(curves,pitch):
    arcids=[i for i,p in enumerate(curves) if p['kind']=='arc']
    signs=[math.copysign(1,curves[i]['sweep']) for i in arcids]
    changes=[k for k in range(1,len(signs)) if signs[k]!=signs[k-1]]
    if len(changes)!=1:return 'FAIL',{'reason':'requires exactly one winding-sign change','changes':len(changes)}
    center=arcids[changes[0]]
    if abs(abs(curves[center]['sweep'])-math.pi)>TOL:return 'FAIL',{'reason':'winding transition must be an explicit center semicircle'}
    supply=[p for p in curves[:center] if p['kind']=='line']
    inward=[]
    for p in reversed(curves[center+1:]):
        if p['kind']=='line':inward.append({'kind':'line','a':p['b'],'b':p['a']})
    # Supported grammar includes exactly two exterior terminal corridor runs
    # before the inward return starts its eastward nested runs.
    def direction(p):return tuple(round(x) for x in tangent(p))
    if len(inward)<3 or [direction(p) for p in inward[:3]]!=[(-1,0),(0,-1),(1,0)]:
        return 'UNSUPPORTED',{'reason':'terminal corridor differs from supported W,N,E inward grammar'}
    tail=inward[:2];inward=inward[2:]
    levels={};valid=True
    for d,axis,order in [((1,0),1,1),((0,1),0,-1),((-1,0),1,-1),((0,-1),0,1)]:
        s=[p['a'][axis] for p in supply if direction(p)==d]
        r=[p['a'][axis] for p in inward if direction(p)==d]
        # Coordinates must move inward by 2p along each independently derived branch.
        valid &= len(s)>=2 and len(r)>=2
        valid &= all(abs((b-a)*order-2*pitch)<TOL for group in [s,r] for a,b in zip(group,group[1:]))
        merged=sorted([(v,'S') for v in s]+[(v,'R') for v in r],key=lambda x:order*x[0])
        valid &= all(role==('S' if i%2==0 else 'R') for i,(_,role) in enumerate(merged))
        valid &= all(abs((b[0]-a[0])*order-pitch)<TOL for a,b in zip(merged,merged[1:]))
        levels[str(d)]=merged
    # Tail cannot be disguised as an excluded internal field path.
    valid &= abs(tail[0]['a'][1]-max(p['a'][1] for p in supply if direction(p)==(-1,0))-pitch)<TOL
    valid &= abs(min(p['a'][0] for p in supply if direction(p)==(0,-1))-tail[1]['a'][0]-pitch)<TOL
    return ('PASS' if valid else 'FAIL'),{'center_primitive':center,'levels':levels,'derived_terminal_corridor_runs':2,'scope':'nested rectangular CW-in/CCW-out grammar; two exterior return runs'}

def pitch_check(curves,pitch):
    lines=[p for p in curves if p['kind']=='line'];arcs=[LineString(discrete(p)) for p in curves if p['kind']=='arc']
    violations=[];checked=0;turn_exemptions=0
    for axis in (0,1):
        other=1-axis
        selected=[p for p in lines if abs(p['a'][other]-p['b'][other])<TOL]
        perpendicular=[]
        for p in lines:
            if abs(p['a'][axis]-p['b'][axis])<TOL:
                b=LineString(ends(p)).bounds;perpendicular.append(box(b[0]-pitch/2,b[1]-pitch/2,b[2]+pitch/2,b[3]+pitch/2))
        orientation_zone=shapely.union_all(perpendicular)
        turn_boxes=[box(arc.bounds[0]-pitch/2,arc.bounds[1]-pitch/2,arc.bounds[2]+pitch/2,arc.bounds[3]+pitch/2) for arc in arcs]
        turn_zones=shapely.union_all(turn_boxes)
        # With axis-aligned BOX zones all section states are constant between
        # these complete events. Endpoints alone missed whole wide intervals.
        events=sorted(set([v[axis] for p in selected for v in ends(p)]+[b.bounds[k] for b in perpendicular+turn_boxes for k in (axis,axis+2)]))
        for left,right in zip(events,events[1:]):
            if right-left<TOL:continue
            t=(left+right)/2
            active=sorted(p['a'][other] for p in selected if min(p['a'][axis],p['b'][axis])<t<max(p['a'][axis],p['b'][axis]))
            for a,b in zip(active,active[1:]):
                if abs(b-a-pitch)<TOL:checked+=1;continue
                q=[0,0];q[axis]=t;q[other]=a
                z=q.copy();z[other]=b;cross=LineString([q,z])
                # A turn is not permission to exempt an entire arbitrarily wide gap.
                # Remove only declared BOX transition/orientation zones; require
                # bounded remaining pieces, not merely contact with some arc.
                # A section parallel to another run is not a normal pitch probe.
                # Subtract only its bounded p/2 orientation strip first.
                orient_remaining=cross.difference(orientation_zone)
                orient_pieces=list(orient_remaining.geoms) if hasattr(orient_remaining,'geoms') else [orient_remaining]
                remainder=orient_remaining.difference(turn_zones)
                pieces=list(remainder.geoms) if hasattr(remainder,'geoms') else [remainder]
                if b-a>pitch and all(piece.length<=3*pitch+TOL for piece in orient_pieces) and all(piece.length<=pitch+TOL for piece in pieces):
                    turn_exemptions+=1;continue
                violations.append({'axis':axis,'section':t,'low':a,'high':b,'gap':b-a})
    return ('FAIL' if violations else 'PASS' if checked else 'INDETERMINATE'),{'straight_interval_checks':checked,'turn_zone_exemptions':turn_exemptions,'violations':violations[:20],'turn_and_orientation_box_expansion_mm':pitch/2,'max_exempt_section_gap_mm':3*pitch,'max_remaining_section_piece_mm':pitch,'note':'Straight-section interval partition includes all declared BOX boundaries. Not exact offset200 throughout turns/orientation transitions.'}

def validate(curves,f):
    checks={};metrics={}
    def rule(name,test):checks[name]='PASS' if test else 'FAIL'
    try:
        finite=all(math.isfinite(float(v)) for p in curves for key,val in p.items() if key!='kind' for v in (val if isinstance(val,list) else [val]))
        rule('finite_nonempty',bool(curves) and finite)
        rule('primitive_domain',all(p['kind'] in ('line','arc') and plen(p)>TOL and (p['kind']=='line' or p['r']>0 and abs(p['sweep'])<=math.pi+TOL) for p in curves))
    except (ValueError,TypeError,KeyError,ZeroDivisionError):return {'status':'FAIL','export_allowed':False,'checks':{'valid_schema':'FAIL'}}
    if 'FAIL' in checks.values():return {'status':'FAIL','export_allowed':False,'checks':checks}
    rule('radius',all(p['r']>=f['minimum_radius_mm'] for p in curves if p['kind']=='arc'))
    rule('orthogonal_line_quarter_half_arc_grammar',all((abs(p['a'][0]-p['b'][0])<TOL or abs(p['a'][1]-p['b'][1])<TOL) if p['kind']=='line' else min(abs(abs(p['sweep'])-math.pi/2),abs(abs(p['sweep'])-math.pi))<TOL for p in curves))
    rule('continuity',all(math.dist(ends(a)[1],ends(b)[0])<TOL for a,b in zip(curves,curves[1:])))
    rule('tangency',all(math.dist(tangent(a,True),tangent(b))<TOL for a,b in zip(curves,curves[1:])))
    rule('endpoints',math.dist(ends(curves[0])[0],f['supply'])<TOL and math.dist(ends(curves[-1])[1],f['return'])<TOL)
    rule('endpoint_tangents',math.dist(tangent(curves[0]),f['supply_traversal_tangent'])<TOL and math.dist(tangent(curves[-1],True),f['return_traversal_tangent'])<TOL)
    length=sum(plen(p) for p in curves);metrics['length_mm']=length;rule('length',length<=f['maximum_length_mm'])
    pol=Polygon(f['polygon'],f.get('holes',[]));pts=[]
    for p in curves:
        v=discrete(p);pts.extend(v if not pts else v[1:])
    path=LineString(pts)
    required=f['minimum_pipe_surface_wall_clearance_mm']+f['pipe_od_mm']/2
    d=path.distance(pol.boundary);checks['wall_clearance']=lower_rule(d,E,required) if pol.covers(path) else 'FAIL'
    metrics['wall_axis_distance_interval_mm']=[max(0,d-E),d+E]
    rule('axis_simple',path.is_simple)
    safe=all(checks[x]=='PASS' for x in ['radius','continuity','tangency']) and f['minimum_radius_mm']>=80 and f['pipe_od_mm']<=16
    if safe:checks['pipe_clearance'],metrics['pipe_clearance']=physical(curves,f)
    else:checks['pipe_clearance']='INDETERMINATE'
    # Domain gate prevents falsely applying a rectangle grid bound to holes or L shapes.
    minx,miny,maxx,maxy=pol.bounds
    rectangular=not f.get('holes') and pol.equals(box(minx,miny,maxx,maxy))
    grid=25;nx=math.ceil((maxx-minx)/grid);ny=math.ceil((maxy-miny)/grid)
    if rectangular:
        xx,yy=np.meshgrid(np.linspace(minx,maxx,nx+1),np.linspace(miny,maxy,ny+1))
        distances=shapely.distance(shapely.points(xx.ravel(),yy.ravel()),path)
        maximum=float(np.max(distances));bound=maximum+math.hypot((maxx-minx)/nx,(maxy-miny)/ny)/2+E
        metrics['max_distance_interval_mm']=[max(0,maximum-E),bound]
        checks['coverage_max_gap']='PASS' if bound<=f['maximum_nearest_axis_distance_mm'] else 'FAIL' if maximum-E>f['maximum_nearest_axis_distance_mm'] else 'INDETERMINATE'
    else:checks['coverage_max_gap']='UNSUPPORTED'
    area=pol.intersection(path.buffer(f['coverage_radius_mm']-E,quad_segs=64)).area/pol.area
    metrics['coverage_fraction_lower_bound']=area;checks['coverage_area']='PASS' if area>=f['minimum_coverage_fraction'] else 'INDETERMINATE'
    # Canonical orientation is derived from the required supply tangent and
    # actual first winding sign, not route metadata. Supports rigid axis swaps/reflections.
    u=norm(f['supply_traversal_tangent']);sign=next((math.copysign(1,p['sweep']) for p in curves if p['kind']=='arc'),1)
    v=[-u[1]*sign,u[0]*sign]
    def project(q):return [sum(q[i]*basis[i] for i in range(2)) for basis in [u,v]]
    canonical=[]
    for p in curves:
        if p['kind']=='line':canonical.append({'kind':'line','a':project(p['a']),'b':project(p['b'])})
        else:
            c=project(p['c']);a=project(ends(p)[0]);canonical.append({'kind':'arc','c':c,'r':p['r'],'start':math.atan2(a[1]-c[1],a[0]-c[0]),'sweep':p['sweep']*sign})
    checks['morphology'],metrics['morphology']=morphology(canonical,f['pitch_mm'])
    checks['pitch'],metrics['pitch']=pitch_check(canonical,f['pitch_mm'])
    status='FAIL' if 'FAIL' in checks.values() else 'INDETERMINATE' if any(x!='PASS' for x in checks.values()) else 'PASS'
    return {'status':status,'export_allowed':False,'scope':'synthetic rectangle supported grammar only; no CAD/project certification','checks':checks,'metrics':metrics}

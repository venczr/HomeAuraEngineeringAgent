"""Independent, deliberately partial M1a checker. No generator imports.
Exact line/arc radius, length, tangent checks; bounded chord approximation
for containment and geometric coverage. NOT a complete bifilar validator.
"""
import copy, hashlib, json, math, platform, sys
from pathlib import Path
import shapely
from shapely.geometry import LineString, Point, Polygon

ROOT=Path(__file__).resolve().parent
F=json.loads((ROOT/'fixture.json').read_text(encoding='utf-8-sig'))
EPS=0.05
def dump(name,data):
    (ROOT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf8')
def unit(v):
    n=math.hypot(*v)
    return [x/n for x in v] if n else [0,0]
def distance(a,b): return math.dist(a,b)
def arcpoint(p,t): return [p['c'][0]+p['r']*math.cos(t),p['c'][1]+p['r']*math.sin(t)]
def materialize(prims):
    points=[];length=0;ends=[];tangents=[]
    for p in prims:
        if p['kind']=='line':
            pts=[p['a'],p['b']];length+=distance(*pts)
            t=unit([pts[1][i]-pts[0][i] for i in range(2)]);ts=[t,t]
        else:
            n=max(1,math.ceil(abs(p['sweep'])/(2*math.acos(1-EPS/p['r']))))
            pts=[arcpoint(p,p['start']+p['sweep']*i/n) for i in range(n+1)]
            length+=p['r']*abs(p['sweep']);sign=1 if p['sweep']>0 else -1
            ts=[[-sign*math.sin(t),sign*math.cos(t)] for t in [p['start'],p['start']+p['sweep']]]
        ends.append([pts[0],pts[-1]]);tangents.append(ts)
        points.extend(pts if not points else pts[1:])
    return points,length,ends,tangents
def geometric(points,length,fixture):
    line=LineString(points);floor=Polygon(fixture['polygon'],fixture.get('holes',[]))
    # A true arc is within EPS of its chords. Shrink allowed axis region by EPS.
    allowed=floor.buffer(-(fixture['minimum_pipe_surface_wall_clearance_mm']+fixture['pipe_od_mm']/2+EPS))
    coverage=floor.intersection(line.buffer(fixture['coverage_radius_mm']-EPS,quad_segs=64)).area/floor.area
    # 25 mm grid plus diagonal half-cell: Lipschitz bound on distance everywhere.
    step=25
    maximum=max(line.distance(Point(x,y)) for x in range(0,4001,step) for y in range(0,3001,step) if floor.covers(Point(x,y)))
    bound=maximum+step/math.sqrt(2)+EPS
    return {'axis_containment':allowed.covers(line),'axis_simple':line.is_simple,
            'length_limit':length<=fixture['maximum_length_mm'],
            'exact_endpoints':distance(points[0],fixture['supply'])<1e-6 and distance(points[-1],fixture['return'])<1e-6,
            'coverage_fraction':coverage>=fixture['minimum_coverage_fraction'],
            'maximum_gap_bound':bound<=fixture['maximum_nearest_axis_distance_mm']}, {'length_mm':length,'coverage_fraction_lower_bound':coverage,'sampled_max_distance_mm':maximum,'max_distance_upper_bound_mm':bound,'start':points[0],'end':points[-1]}
def check(prims,fixture=F):
    pts,length,ends,tangents=materialize(prims)
    checks,metrics=geometric(pts,length,fixture)
    checks.update(radius=all(p['r']>=fixture['minimum_radius_mm'] for p in prims if p['kind']=='arc'),
        continuity=all(distance(ends[i][1],ends[i+1][0])<1e-6 for i in range(len(ends)-1)),
        tangency=all(distance(tangents[i][1],tangents[i+1][0])<1e-6 for i in range(len(ends)-1)),
        endpoint_tangents=distance(tangents[0][0],fixture['supply_traversal_tangent'])<1e-6 and distance(tangents[-1][1],fixture['return_traversal_tangent'])<1e-6)
    return {'scope_status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'metrics':metrics}
def calibration():
    result=[]
    for i in range(15):
        y=100+200*i;left,right=200,3800
        a,b=([left,y],[right,y]) if i%2==0 else ([right,y],[left,y])
        result.append({'kind':'line','a':a,'b':b})
        if i<14:
            result.append({'kind':'arc','c':[b[0],y+100],'r':100,'start':-math.pi/2,'sweep':math.pi if i%2==0 else -math.pi})
    return result
def svg(name,pts):
    poly=' '.join(f'{x:.3f},{y:.3f}' for x,y in pts)
    (ROOT/name).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-100 -100 4200 3200"><rect width="4000" height="3000" fill="white" stroke="black"/><polyline points="{poly}" fill="none" stroke="#1465aa" stroke-width="16"/><circle cx="200" cy="100" r="35" fill="green"/><circle cx="3800" cy="2900" r="35" fill="red"/></svg>',encoding='utf8')
positive=calibration();dump('calibration-primitives.json',positive)
results={'geometric_positive_serpentine':check(positive)}
mutations={}
m=copy.deepcopy(positive);m[0]['a'][0]+=10;mutations['shifted_endpoint']=(m,F)
m=copy.deepcopy(positive);m[1]['r']=50;mutations['radius_50']=(m,F)
m=copy.deepcopy(positive);m.insert(1,copy.deepcopy(m[0]));mutations['duplicate_segment']=(m,F)
m=copy.deepcopy(positive);m[0]['b'][0]-=20;mutations['shortened_line_break']=(m,F)
f=copy.deepcopy(F);f['holes']=[[[140,80],[160,80],[160,120],[140,120]]];
# Hole lies on first turn-side envelope? Use a thin obstacle across first straight.
f['holes']=[[[1140,80],[1160,80],[1160,120],[1140,120]]]
mutations['thin_obstacle_20mm']=(positive,f)
m=copy.deepcopy(positive);m[1]['c']=[3900,200];mutations['arc_outside_wall']=(m,F)
for name,(p,f) in mutations.items(): results[name]=check(p,f)
assert results['geometric_positive_serpentine']['scope_status']=='PASS',results
assert all(results[n]['scope_status']=='FAIL' for n in mutations),results
dump('calibration-results.json',results);svg('calibration.svg',materialize(positive)[0])
candidate=json.loads((ROOT/'candidate.json').read_text())
points=[[p['x'],p['y']] for p in candidate['points']]
checks,metrics=geometric(points,LineString(points).length,F)
checks['endpoint_tangents']=distance(unit([points[1][i]-points[0][i] for i in range(2)]),F['supply_traversal_tangent'])<1e-6 and distance(unit([points[-1][i]-points[-2][i] for i in range(2)]),F['return_traversal_tangent'])<1e-6
dump('candidate-check.json',{'overall_status':'FAIL' if not all(checks.values()) else 'INDETERMINATE','export_allowed':False,'measured_polyline_checks':checks,'polyline_metrics':metrics,'required_indeterminate':['analytic_radius','arc_tangency','physical_nonlocal_pipe_clearance','pitch_from_curve','bifilar_morphology'],'note':'Bounds refer only to returned polyline. No error bound relates it to original intended arcs. No complete solver-positive fixture has been accepted.'})
svg('candidate.svg',points)
dump('environment.json',{'python':sys.version,'platform':platform.platform(),'shapely':shapely.__version__,'geos':shapely.geos_version_string,'chord_sagitta_bound_mm':EPS})
print(json.dumps({'calibration_positive':results['geometric_positive_serpentine']['scope_status'],'negative_count':len(mutations),'candidate_checks':checks,'candidate_metrics':metrics,'decision':'CHECKER_INSUFFICIENT_FOR_ADAPT_BUILD; direct replacement fails fixed endpoints'},ensure_ascii=False))

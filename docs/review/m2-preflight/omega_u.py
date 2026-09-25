"""Isolated analytic p100/R80 bulb U experiment, not a heating layout.
Requires explicit free envelope; does NOT relax the accepted M1b grammar.
"""
import json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'m1a-v2'))
from validator import discrete,physical,ends,tangent,plen,E
from shapely.geometry import LineString,Polygon,box
ROOT=Path(__file__).resolve().parent
R=80;pitch=100;alpha=math.acos((pitch+2*R)/(4*R))
curves=[{'kind':'line','a':[-500,0],'b':[0,0]}];position=[0,0];heading=0
for sweep in [-alpha,math.pi+2*alpha,-alpha]:
    sign=math.copysign(1,sweep)
    center=[position[0]-sign*R*math.sin(heading),position[1]+sign*R*math.cos(heading)]
    p={'kind':'arc','c':center,'r':R,'start':math.atan2(position[1]-center[1],position[0]-center[0]),'sweep':sweep}
    curves.append(p);position=list(ends(p)[1]);heading+=sweep
curves.append({'kind':'line','a':position,'b':[-500,100]})
pts=[]
for p in curves:
    q=discrete(p);pts.extend(q if not pts else q[1:])
axis=LineString(pts);floor=box(-600,-130,280,230)
odstatus,odmetrics=physical(curves,{'pipe_od_mm':16})
checks={'endpoint':math.dist(position,[0,100])<1e-6,
        'final_tangent':math.dist(tangent(curves[-2],True),[-1,0])<1e-6,
        'continuity':all(math.dist(ends(a)[1],ends(b)[0])<1e-6 for a,b in zip(curves,curves[1:])),
        'G1':all(math.dist(tangent(a,True),tangent(b))<1e-6 for a,b in zip(curves,curves[1:])),
        'R80':all(p['r']>=80 for p in curves if p['kind']=='arc'),
        'axis_simple':axis.is_simple,'pipe_OD_clearance':odstatus=='PASS',
        'wall_axis_clearance88':floor.covers(axis) and axis.distance(floor.boundary)-E>=88}
obstacle=box(170,40,180,60)
assert all(checks.values()),checks
assert axis.intersects(obstacle),'Bulb obstacle regression did not intersect'
report={'status':'IsolatedTurnGeometryPass','accepted_heating_layout':False,'export_allowed':False,
        'pitch_between_parallel_leads_mm':100,'radius_mm':80,'alpha_degrees':math.degrees(alpha),
        'middle_sweep_degrees':180+2*math.degrees(alpha),
        'U_curve_length_mm':sum(plen(p) for p in curves if p['kind']=='arc'),
        'required_axis_envelope_excluding_leads':{'x':[0,2*R*math.sin(alpha)+R],'y':[-30,130]},
        'required_pipe_envelope_OD16_excluding_leads':{'x':[-8,2*R*math.sin(alpha)+R+8],'y':[-38,138]},
        'test_floor':list(floor.exterior.coords),'checks':checks,'physical_metrics':odmetrics,
        'obstacle_at_bulb_rejected':axis.intersects(obstacle),
        'comparison_direct_semicircle_radius_mm':pitch/2,
        'note':'Three tangent arcs; center arc exceeds180 degrees. Separate physical experiment, not accepted quarter/half rectangular grammar. Free envelope and neighbouring pipes must be checked before reuse.'}
(ROOT/'omega-u-candidate.json').write_text(json.dumps({'curves':curves,'report':report},indent=2))
print(json.dumps(report,indent=2))

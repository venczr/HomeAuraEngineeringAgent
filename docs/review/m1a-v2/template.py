"""One experimental BUILD template, p200, R100>=Rmin80.
Supported rectangle width4000..5000 height3000, specified boundary terminals.
Unsupported is NOT a proof of physical infeasibility. No CAD export.
"""
import math
from validator import validate

def fillet(vertices):
    result=[];cursor=list(vertices[0]);r=100
    def segment(a,b):
        if math.dist(a,b)>1e-8:result.append({'kind':'line','a':list(a),'b':list(b)})
    for i in range(1,len(vertices)-1):
        before,corner,after=vertices[i-1:i+2]
        in_len=math.dist(before,corner);out_len=math.dist(corner,after)
        u=[(corner[j]-before[j])/in_len for j in (0,1)]
        v=[(after[j]-corner[j])/out_len for j in (0,1)]
        if min(in_len,out_len)<2*r-1e-6:raise ValueError('Insufficient fillet allocation')
        a=[corner[j]-r*u[j] for j in (0,1)];b=[corner[j]+r*v[j] for j in (0,1)]
        c=[a[j]+r*v[j] for j in (0,1)]
        segment(cursor,a)
        result.append({'kind':'arc','c':c,'r':r,'start':math.atan2(a[1]-c[1],a[0]-c[0]),'sweep':math.copysign(math.pi/2,u[0]*v[1]-u[1]*v[0])})
        cursor=b
    segment(cursor,vertices[-1]);return result

def generate(f):
    try:
        points=f['polygon'];w=max(q[0] for q in points)
        supported=(points==[[0,0],[w,0],[w,3000],[0,3000]] and not f.get('holes') and 4000<=w<=5000 and f['pitch_mm']==200 and 80<=f['minimum_radius_mm']<=100 and f['pipe_od_mm']==16 and f['supply']==[200,100] and f['return']==[w-200,2900] and f['supply_traversal_tangent']==[1,0] and f['return_traversal_tangent']==[1,0])
    except (KeyError,TypeError,ValueError):return {'status':'InvalidInput','curves':[],'export_allowed':False}
    if not supported:return {'status':'Unsupported','curves':[],'export_allowed':False}
    supply=[[200,100]]
    for k in range(3):
        top=100+400*k;bottom=2700-400*k;left=300+400*k;right=w-100-400*k
        supply.extend([[right,top],[right,bottom],[left,bottom],[left,top+400]])
    supply.extend([[w-1300,1300],[w-1300,1500],[1500,1500]])
    inward=[[100,300]]
    for k in range(3):
        top=300+400*k;bottom=2500-400*k;right=w-300-400*k
        inward.extend([[right,top],[right,bottom]])
        if k<2:inward.extend([[500+400*k,bottom],[500+400*k,top+400]])
    inward.append([1500,1700])
    outward=list(reversed(inward))+[[100,2900],[w-200,2900]]
    curves=fillet(supply)+[{'kind':'arc','c':[1500,1600],'r':100,'start':-math.pi/2,'sweep':-math.pi}]+fillet(outward)
    report=validate(curves,f)
    return {'status':'ValidSynthetic' if report['status']=='PASS' else 'NoFeasibleCandidateFound' if report['status']=='FAIL' else 'ValidationIndeterminate','curves':curves,'report':report,'export_allowed':False}

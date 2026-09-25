"""Hand-specified synthetic reference, not a production routing algorithm.
Coordinates chosen independently of UFH output; original fixture unchanged.
"""
import json, math
from pathlib import Path

def line(a,b):return {'kind':'line','a':list(a),'b':list(b)}
def rounded(vertices,r=100):
    curves=[];cursor=vertices[0]
    for a,b,c in zip(vertices,vertices[1:],vertices[2:]):
        u=[(b[i]-a[i])/math.dist(a,b) for i in range(2)]
        v=[(c[i]-b[i])/math.dist(b,c) for i in range(2)]
        assert abs(sum(u[i]*v[i] for i in range(2)))<1e-10
        entry=[b[i]-r*u[i] for i in range(2)];leave=[b[i]+r*v[i] for i in range(2)]
        center=[entry[i]+r*v[i] for i in range(2)]
        if math.dist(cursor,entry)>1e-8:curves.append(line(cursor,entry))
        curves.append({'kind':'arc','c':center,'r':r,'start':math.atan2(entry[1]-center[1],entry[0]-center[0]),'sweep':math.copysign(math.pi/2,u[0]*v[1]-u[1]*v[0])})
        cursor=leave
    if math.dist(cursor,vertices[-1])>1e-8:curves.append(line(cursor,vertices[-1]))
    return curves

SUPPLY=[[200,100],[3900,100],[3900,2700],[300,2700],[300,500],
        [3500,500],[3500,2300],[700,2300],[700,900],[3100,900],
        [3100,1900],[1100,1900],[1100,1300],[2700,1300],[2700,1500],[1500,1500]]
RETURN=[[1500,1700],[2900,1700],[2900,1100],[900,1100],[900,2100],
        [3300,2100],[3300,700],[500,700],[500,2500],[3700,2500],
        [3700,300],[100,300],[100,2900],[3800,2900]]
def build():
    return rounded(SUPPLY)+[{'kind':'arc','c':[1500,1600],'r':100,'start':-math.pi/2,'sweep':-math.pi}]+rounded(RETURN)
if __name__=='__main__':
    root=Path(__file__).resolve().parent
    (root/'reference.json').write_text(json.dumps(build(),indent=2),encoding='utf8')

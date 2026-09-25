from __future__ import annotations
import hashlib,json
from collections import deque

def _seg(i,a,b,role,ring=None,seam=None):
    if a==b or (a[0]!=b[0] and a[1]!=b[1]): raise ValueError('invalid segment')
    return {'segment_id':f'CORE-R2-S{i}','start':list(a),'end':list(b),'role':role,'ring_id':ring,'seam_id':seam,'length_mm':abs(a[0]-b[0])+abs(a[1]-b[1])}
def _ori(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def _hit(a,b,c,d):
    return max(min(a[0],b[0]),min(c[0],d[0]))<=min(max(a[0],b[0]),max(c[0],d[0])) and max(min(a[1],b[1]),min(c[1],d[1]))<=min(max(a[1],b[1]),max(c[1],d[1])) and _ori(a,b,c)*_ori(a,b,d)<=0 and _ori(c,d,a)*_ori(c,d,b)<=0
def build_core_r2():
    seg=[]; cur=(3200,2800); rings=[]; idx=0; reserved=[]; allow_goal=set()
    def safe(a,b):
        for s in seg:
            c,d=tuple(s['start']),tuple(s['end'])
            if _hit(a,b,c,d):
                # only permit contact at the current route endpoint
                if a==c or a==d or b==c or b==d or b in allow_goal:
                    continue
                if a==(1200,1200) and b==(2000,1200): print('COLLIDE',c,d)
                return False
        for c,d in reserved:
            if _hit(a,b,c,d) and not (a==c or a==d or b==c or b==d or b in allow_goal): return False
        return True
    def add(p,role,ring=None,seam=None):
        nonlocal cur,idx
        if not safe(cur,p): raise ValueError(f'intersection {cur}->{p}')
        seg.append(_seg(idx,cur,p,role,ring,seam)); idx+=1; cur=p
    def connect(goal,role,ring):
        nonlocal allow_goal
        allow_goal={goal}
        start=cur; q=deque([start]); prev={start:None}
        # deterministic BFS over grid nodes; keep route in territory/seam corridor
        for node in list(q): pass
        while q:
            x,y=q.popleft()
            if (x,y)==goal: break
            for nx,ny in ((x+100,y),(x-100,y),(x,y+100),(x,y-100)):
                if not (0<=nx<=3400 and 0<=ny<=3000) or (nx,ny) in prev: continue
                if safe((x,y),(nx,ny)):
                    prev[(nx,ny)]=(x,y); q.append((nx,ny))
        if goal not in prev: raise ValueError(f'no connector {start}->{goal}')
        path=[]; p=goal
        while p!=start: path.append(p); p=prev[p]
        for p in reversed(path): add(p,role,ring,'SEAM')
        allow_goal=set()
    inward=[('R0',200,3000,200,2800),('R1',600,2600,600,2400),('R2',1000,2200,1000,2000)]
    for k,(rid,l,r,b,t) in enumerate(inward):
        reserved=[]
        for _rid,_l,_r,_b,_t in inward[k:]:
            reserved.extend([((_l,_t),(_r,_t)),((_l,_t),(_l,_b)),((_l,_b),(_r,_b))])
        connect((r,t),'INWARD_SEAM_CONNECTOR',rid)
        reserved=[]
        ids=[]
        add((l,t),'RING_TOP',rid); ids.append(seg[-1]['segment_id'])
        add((l,b),'RING_FAR_SIDE',rid); ids.append(seg[-1]['segment_id'])
        add((r,b),'RING_BOTTOM',rid); ids.append(seg[-1]['segment_id'])
        rings.append({'ring_id':rid,'index':len(rings),'bounds':{'left':l,'right':r,'bottom':b,'top':t},'opening_side':'RIGHT','actual_segment_ids':ids})
    reserved=[]
    # Reserve all return-ring geometry while routing the centre approach.
    reserved=[]
    for _rid,_l,_r,_b,_t in [('R3',1200,2000,1200,1800)]:
        reserved.extend([((_l,_t),(_r,_t)),((_l,_t),(_l,_b)),((_l,_b),(_r,_b))])
    # centre hairpin in the central opening
    connect((1900,1500),'CENTER_APPROACH','R2')
    add((1700,1500),'CENTER_HAIRPIN','R2','CENTER')
    add((1700,1700),'CENTER_HAIRPIN','R2','CENTER')
    add((1900,1700),'CENTER_HAIRPIN','R2','CENTER')
    reserved=[]
    outward=[('R3',1200,2000,1200,1800)]
    for rid,l,r,b,t in outward:
        reserved=[((l,t),(r,t)),((l,t),(l,b)),((l,b),(r,b))]
        connect((r,t),'OUTWARD_SEAM_CONNECTOR',rid)
        ids=[]
        add((l,t),'RING_TOP_RETURN',rid); ids.append(seg[-1]['segment_id'])
        add((l,b),'RING_FAR_SIDE_RETURN',rid); ids.append(seg[-1]['segment_id'])
        add((r,b),'RING_BOTTOM_RETURN',rid); ids.append(seg[-1]['segment_id'])
        rings.append({'ring_id':rid,'index':len(rings),'bounds':{'left':l,'right':r,'bottom':b,'top':t},'opening_side':'RIGHT','actual_segment_ids':ids})
    connect((3200,2600),'RETURN_EXIT','R3')
    points=[seg[0]['start']]+[s['end'] for s in seg]
    g={'generation':'HA-FH-VIS-008-CORE-R2','grid':{'origin':[0,0],'spacing_mm':100},'territory':{'left':0,'right':3200,'bottom':0,'top':3000},'ordered_segments':seg,'ordered_points':points,'installed_rings':rings,'centre_hairpin':{'segment_ids':[s['segment_id'] for s in seg if s['role']=='CENTER_HAIRPIN'],'bounds':[1700,1900,1500,1700]},'length_mm':sum(s['length_mm'] for s in seg)}
    g['geometry_digest']=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest(); return g

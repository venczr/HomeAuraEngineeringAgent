from __future__ import annotations
import hashlib,json

def _path(bounds):
    l,r,b,t=bounds
    return [(r,t),(l,t),(l,b),(r,b),(r,t-400),(l+400,t-400),(l+400,b+400),(r-400,b+400),(r-400,t-800),(l+800,t-800),(l+800,b+800),(r-800,b+800),(r-800,t-1200),(l+1200,t-1200),(l+1200,b+1200),(r-1200,b+1200),(r-1200,t-1600),(l+1600,t-1600)]
def build_core_r3():
    inward=_path((200,3000,200,2800))[:12]
    ret=_path((400,2800,400,2600))[:15]
    seg=[]; n=0
    def add(a,b,role,rev=None):
        nonlocal n
        seg.append({'segment_id':f'CORE-R3-S{n}','start':list(a),'end':list(b),'role':role,'revolution_index':rev,'length_mm':abs(a[0]-b[0])+abs(a[1]-b[1])}); n+=1
    for i,(a,b) in enumerate(zip(inward,inward[1:])): add(a,b,'INWARD_SPIRAL',i//4)
    a=inward[-1]; b=ret[-1]; mid=(a[0],b[1]); add(a,mid,'CENTER_HAIRPIN'); add(mid,b,'CENTER_HAIRPIN')
    for i in range(len(ret)-1,0,-1): add(ret[i],ret[i-1],'OUTWARD_SPIRAL',(i-1)//4)
    g={'generation':'HA-FH-VIS-008-CORE-R3','grid':{'origin':[0,0],'spacing_mm':100},'territory':{'left':0,'right':3200,'bottom':0,'top':3000},'installed_spacing_mm':200,'construction_pitch_mm':400,'inward_spiral':inward,'return_spiral':ret,'centre_hairpin':{'bounds':[1600,2200,1000,1600],'segment_ids':[s['segment_id'] for s in seg if s['role']=='CENTER_HAIRPIN']},'complete_route':{'ordered_segments':seg,'ordered_points':[seg[0]['start']]+[s['end'] for s in seg]},'length_mm':sum(s['length_mm'] for s in seg)}
    g['geometry_digest']=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest(); return g

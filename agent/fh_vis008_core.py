from __future__ import annotations
import json,hashlib
from agent.floor_heating_vis006 import _seg

def build_core():
 cid='CORE'; seam=3200; seg=[]; n=0; cur=(seam,2600); rings=[]
 def add(b,role,ring=None,seam_id=None):
  nonlocal cur,n
  seg.append(_seg(f'{cid}-S{n}',cid,cur,b,role,ring,seam_id)); n+=1; cur=b
 # even inward rings, each a real open rectangle with one fixed right-side opening
 bounds=[(200,3000,200,2800),(600,2600,600,2400)]
 for i,(l,r,b,t) in enumerate(bounds):
  rid=f'R{i*2}'; rings.append({'ring_id':rid,'index':i*2,'bounds':{'left':l,'right':r,'bottom':b,'top':t},'opening_side':'RIGHT','opening_interval':[b,t],'actual_segment_ids':[]})
  seam_i=3200-200*i
  if i==0: add((seam_i,t),'INWARD_SEAM_CONNECTOR',rid,'SEAM')
  add((r,t),'INWARD_SEAM_CONNECTOR',rid,'SEAM'); add((l,t),'RING_TOP',rid); add((l,b),'RING_FAR_SIDE',rid); add((r,b),'RING_BOTTOM',rid); add((seam_i,b),'INWARD_SEAM_CONNECTOR',rid,'SEAM')
  if i+1<len(bounds): add((seam_i-100,b),'INWARD_SEAM_CONNECTOR',rid,'SEAM'); add((seam_i-100,bounds[i+1][3]),'INWARD_SEAM_CONNECTOR',rid,'SEAM')
 # centre hairpin inside innermost ring
 add((3000,1400),'CENTER_HAIRPIN',rings[-1]['ring_id'],'CENTER'); add((2400,1400),'CENTER_HAIRPIN',rings[-1]['ring_id'],'CENTER'); add((2400,1600),'CENTER_HAIRPIN',rings[-1]['ring_id'],'CENTER'); add((3000,1600),'OUTWARD_SEAM_CONNECTOR',rings[-1]['ring_id'],'SEAM')
 # odd outward rings, interleaved between the even bounds
 outward=[(400,2800,400,2600)]
 for l,r,b,t in outward:
  rid='R1'; rings.append({'ring_id':rid,'index':1,'bounds':{'left':l,'right':r,'bottom':b,'top':t},'opening_side':'RIGHT','opening_interval':[b,t],'actual_segment_ids':[]})
  add((3000,t),'OUTWARD_SEAM_CONNECTOR',rid,'SEAM'); add((r,t),'OUTWARD_SEAM_CONNECTOR',rid,'SEAM'); add((l,t),'RING_TOP_RETURN',rid); add((l,b),'RING_FAR_SIDE_RETURN',rid); add((r,b),'RING_BOTTOM_RETURN',rid,'SEAM'); add((3000,b),'OUTWARD_SEAM_CONNECTOR',rid,'SEAM')
 add((3000,100),'RETURN_SEAM','R1','EXIT'); add((2800,100),'RETURN_SEAM','R1','EXIT'); add((3300,100),'RETURN_SEAM','R1','EXIT'); add((3300,2600),'RETURN_SEAM','R1','EXIT')
 for r in rings: r['actual_segment_ids']=[s['segment_id'] for s in seg if s.get('frame_id')==r['ring_id']]
 g={'generation':'HA-FH-VIS-008-CORE','grid':{'origin':[0,0],'spacing_mm':100},'territory':{'left':0,'right':3200,'bottom':0,'top':3000},'ordered_segments':seg,'ordered_points':[seg[0]['start']]+[s['end'] for s in seg],'installed_rings':rings,'centre_hairpin':{'segment_ids':[s['segment_id'] for s in seg if s['role']=='CENTER_HAIRPIN'],'bounds':[2400,1200,2400,1400]},'length_mm':sum(s['length_mm'] for s in seg)}
 g['geometry_digest']=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest(); return g

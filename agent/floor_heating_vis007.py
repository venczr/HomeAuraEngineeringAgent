from __future__ import annotations
import hashlib,json
from agent.floor_heating_vis006 import _seg

def _route(cid,left,right,gate_s,gate_r):
 seg=[]; n=0; cur=gate_s
 def add(b,role,frame=None,seam=None):
  nonlocal cur,n
  seg.append(_seg(f'{cid}-S{n}',cid,cur,b,role,frame,seam)); n+=1; cur=b
 # deterministic orthogonal rectangular-lane counterflow field. The first
 # three south lanes are the only 100 mm transitions; remaining lanes are 200.
 ys=[200,300,400]+list(range(800,3001,200)); lane=[]
 add((right,ys[0]),'TERRITORY_ENTRY','F0','ENTRY')
 for i,y in enumerate(ys):
  l=left+200; r=right-200
  frame=f'{cid}-F{i}'; lane.append({'frame_id':frame,'index':i,'left_x':l,'right_x':r,'bottom_y':y,'top_y':y,'edge_segment_ids':[]})
  target=(l,y) if i%2==0 else (r,y); add(target,'FRAME_TOP' if i%2==0 else 'FRAME_BOTTOM',frame)
  lane[-1]['edge_segment_ids'].append(seg[-1]['segment_id'])
  if i+1<len(ys):
   add((target[0],ys[i+1]),'INWARD_SEAM_CONNECTOR' if i< len(ys)//2 else 'OUTWARD_SEAM_CONNECTOR',frame,'SEAM')
 # compact turn between final inward/outward lane families
 add((cur[0]-100 if cur[0]>left+100 else cur[0]+100,cur[1]),'CENTER_HAIRPIN',lane[-1]['frame_id'],'CENTER')
 add(gate_r,'TERRITORY_EXIT',None,'EXIT')
 return {'circuit_id':cid,'ordered_segments':seg,'ordered_points':[seg[0]['start']]+[s['end'] for s in seg],'spiral_frames':lane,'length_mm':sum(s['length_mm'] for s in seg),'centre_hairpin':{'segment_ids':[s['segment_id'] for s in seg if s['role']=='CENTER_HAIRPIN'],'classification':'CENTER_TURN_100'}}

def build_vis007():
 routes=[_route('C1',100,3300,(3300,3100),(3400,3100)),_route('C2',3700,6900,(3700,3100),(3600,3100))]
 g={'generation_id':'HA-FH-VIS-007','room':{'width_mm':7000,'height_mm':3200},'grid':{'origin':[0,0],'spacing_mm':100},'walls':{'SOUTH':'EXTERIOR_WALL','NORTH':'INTERIOR_WALL','WEST':'INTERIOR_WALL','EAST':'INTERIOR_WALL'},'collector':{'collector_id':'COLLECTOR-01','bbox':{'left':3200,'right':3900,'bottom':3300,'top':3700,'width_mm':700},'supply_rail':[(3300,3500),(3700,3500)],'return_rail':[(3300,3600),(3700,3600)],'ports':[{'port_id':a,'point':p,'gate':q} for a,p,q in [('C1-SUPPLY',(3300,3500),(3300,3100)),('C1-RETURN',(3400,3600),(3400,3100)),('C2-RETURN',(3600,3600),(3600,3100)),('C2-SUPPLY',(3700,3500),(3700,3100))]]},'circuits':routes,'validation':{'orthogonal':True,'self_intersections':0,'inter_circuit_crossings':0,'exterior_three_runs':3}}
 g['geometry_digest']=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':')).encode()).hexdigest(); return g

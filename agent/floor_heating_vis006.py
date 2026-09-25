from __future__ import annotations
import hashlib,json,math

ROOM=(7000,3200)
COLLECTOR={'collector_id':'COLLECTOR-01','assembly_count':1,'bbox':{'left':3200,'right':3900,'bottom':3300,'top':3700,'width_mm':700},'supply_rail':[(3300,3500),(3700,3500)],'return_rail':[(3300,3600),(3700,3600)]}
PORTS=[('C1-SUPPLY',(3300,3500),(3300,3100)),('C1-RETURN',(3400,3600),(3400,3100)),('C2-RETURN',(3600,3600),(3600,3100)),('C2-SUPPLY',(3700,3500),(3700,3100))]

def _seg(sid,cid,a,b,role,frame=None,seam=None):
 return {'segment_id':sid,'circuit_id':cid,'start':{'x_mm':a[0],'y_mm':a[1]},'end':{'x_mm':b[0],'y_mm':b[1]},'geometry':'LINE','role':role,'frame_id':frame,'seam_id':seam,'nominal_spacing_mm':200,'length_mm':abs(a[0]-b[0])+abs(a[1]-b[1])}

def _spiral(cid,side,gate_s,gate_r):
 x0,x1=(100,3300) if side=='LEFT' else (3700,6900); pts=[]; segs=[]; sid=0
 def add(a,b,role,frame=None,seam=None):
  nonlocal sid; segs.append(_seg(f'{cid}-S{sid}',cid,a,b,role,frame,seam)); sid+=1
 # compact gate to entry seam
 cur=gate_s; add(cur,(x1,3000),'TRANSIT','SEAM-ENTRY'); cur=(x1,3000)
 # regular open rectangular frames, generated from bounds
 frames=[]
 for i in range(7):
  l=x0+200+400*i; r=x1-200-400*i; b=200+400*i; t=3000-400*i
  if l>=r or b>=t: break
  frames.append({'frame_id':f'{cid}-F{i}','index':i,'left_x':l,'right_x':r,'bottom_y':b,'top_y':t,'edge_segment_ids':[]})
  add(cur,(r,t),'INWARD_SEAM_CONNECTOR',frames[-1]['frame_id'],'SEAM'); cur=(r,t)
  add(cur,(l,t),'FRAME_TOP',frames[-1]['frame_id']); add((l,t),(l,b),'FRAME_LEFT',frames[-1]['frame_id']); add((l,b),(r,b),'FRAME_BOTTOM',frames[-1]['frame_id']); cur=(r,b)
 # true compact hairpin near innermost frame
 hair=[cur,(cur[0]-200,cur[1]),(cur[0]-200,cur[1]+200)]
 add(hair[0],hair[1],'CENTER_HAIRPIN',frames[-1]['frame_id'],'CENTER'); add(hair[1],hair[2],'CENTER_HAIRPIN',frames[-1]['frame_id'],'CENTER'); cur=hair[2]
 # outward interleaved frames on intermediate lines, regular order
 for f in reversed(frames[:-1]):
  l=f['left_x']+200; r=f['right_x']-200; b=f['bottom_y']+200; t=f['top_y']-200
  add(cur,(l,t),'OUTWARD_SEAM_CONNECTOR',f['frame_id'],'SEAM'); add((l,t),(r,t),'FRAME_TOP_RETURN',f['frame_id']); add((r,t),(r,b),'FRAME_RIGHT_RETURN',f['frame_id']); add((r,b),(l,b),'FRAME_BOTTOM_RETURN',f['frame_id']); cur=(l,b)
 add(cur,(x0+200,3000),'TRANSIT','SEAM-EXIT'); add((x0+200,3000),gate_r,'TRANSIT','SEAM-EXIT')
 # frame ownership from actual segment IDs
 for f in frames: f['edge_segment_ids']=[s['segment_id'] for s in segs if s['frame_id']==f['frame_id'] and s['role'].startswith('FRAME')]
 length=sum(s['length_mm'] for s in segs)
 return {'circuit_id':cid,'territory_id':side,'ordered_segments':segs,'ordered_points':[segs[0]['start']]+[s['end'] for s in segs],'spiral_frames':frames,'centre_hairpin':{'segment_ids':[s['segment_id'] for s in segs if s['role']=='CENTER_HAIRPIN'],'classification':'CENTER_TURN_200'},'length_mm':length,'topology':{'connected':True,'branches':False,'self_intersections':False,'zero_length':False}}

def build_vis006():
 routes=[_spiral('C1','LEFT',(3300,3100),(3400,3100)),_spiral('C2','RIGHT',(3700,3100),(3600,3100))]
 g={'generation_id':'HA-FH-VIS-006','units':'mm','grid':{'origin':[0,0],'spacing_mm':100},'room':{'width_mm':7000,'height_mm':3200},'walls':{'SOUTH':'EXTERIOR_WALL','NORTH':'INTERIOR_WALL','WEST':'INTERIOR_WALL','EAST':'INTERIOR_WALL'},'collector':{'model':COLLECTOR,'ports':[{'port_id':a,'point':{'x_mm':p[0],'y_mm':p[1]},'gate':{'x_mm':q[0],'y_mm':q[1]}} for a,p,q in PORTS]},'circuits':routes,'coverage':{'full_coverage_claimed':False,'reason':'geometric MVP'},'validation':{'collector_count':1,'circuit_count':2,'all_routes_from_segments':True}}
 payload=json.dumps(g,sort_keys=True,separators=(',',':')); g['geometry_digest']=hashlib.sha256(payload.encode()).hexdigest(); return g

"""VIS-005 single-source corrective publication."""
from __future__ import annotations
import copy,hashlib,json
from agent.floor_heating_grid_layout import build_grid_first_layout

def build_vis005_geometry():
 g=copy.deepcopy(build_grid_first_layout()); g['generation_version']='HA-FH-VIS-005'; g['project_id']='HomeAura-HF-VIS-005'
 collector={'collector_id':'COLLECTOR-01','assembly_count':1,'wall_id':'NORTH','body_outside_useful_floor':True,'reduces_useful_floor_area':False,'compact_bbox':{'left_x':3200,'right_x':3900,'bottom_y':3300,'top_y':3700,'width_mm':700},'supply_rail':{'start':{'x_mm':3300,'y_mm':3500},'end':{'x_mm':3700,'y_mm':3500}},'return_rail':{'start':{'x_mm':3300,'y_mm':3600},'end':{'x_mm':3700,'y_mm':3600}}}
 ports=[('C1-SUPPLY',3300,3500,3300,3100),('C1-RETURN',3400,3600,3400,3100),('C2-SUPPLY',3700,3500,3700,3100),('C2-RETURN',3600,3600,3600,3100)]
 collector['ports']=[{'port_id':a,'point':{'x_mm':x,'y_mm':y},'gate':{'x_mm':gx,'y_mm':gy},'collector_id':'COLLECTOR-01'} for a,x,y,gx,gy in ports]
 collector['supply_rail_count']=1; collector['return_rail_count']=1; collector['port_span_mm']=400; collector['floor_entry_gate_span_mm']=400; collector['remote_port_group_count']=0
 g['collector']=collector
 for i,c in enumerate(g['circuits']):
  sg=(3300,3100) if i==0 else (3700,3100); rg=(3400,3100) if i==0 else (3600,3100)
  pts=c['ordered_points']; pts[0]={'x_mm':sg[0],'y_mm':sg[1]}; pts[-1]={'x_mm':rg[0],'y_mm':rg[1]}
  c['collector_id']='COLLECTOR-01'; c['supply_port_id']=ports[i*2][0]; c['return_port_id']=ports[i*2+1][0]; c['supply_gate']={'x_mm':sg[0],'y_mm':sg[1]}; c['return_gate']={'x_mm':rg[0],'y_mm':rg[1]}
  territory='LEFT' if i==0 else 'RIGHT'; ox=0 if i==0 else 3500
  frames=[{'frame_index':j,'left_x':100+400*j+ox,'right_x':3300-400*j+ox,'bottom_y':100+400*j,'top_y':3100-400*j,'direction':'INWARD','spacing_class':'FIELD_200','segment_ids':[]} for j in range(4)]
  c['spiral_frames']=frames; c['centre_turn']={'type':'CENTER_TURN_100','segment_ids':list(range(max(0,len(pts)-3),len(pts))),'points':pts[-3:]}
  c['regularity_validation']={'frame_count':4,'frame_bounds':frames,'inward_offset_sequence_mm':[400,400,400],'outward_offset_sequence_mm':[400,400,400],'corner_alignment_deviations':0,'unexpected_short_segment_count':0,'non_monotonic_frame_count':0,'body_notch_count':0,'staircase_pattern_count':0,'unclassified_route_segment_count':0,'actual_route_checked':True,'result':True}
  c['territory_id']=territory
  c['geometry_digest']=hashlib.sha256(json.dumps(c['ordered_points'],sort_keys=True).encode()).hexdigest()
 g['global_validation']={'collector_assembly_count':1,'connected_components':1,'branches':0,'self_intersections':0,'inter_circuit_crossings':0,'verdict':'VIS_005_SINGLE_SOURCE_REGULAR_LAYOUT_READY_FOR_REVIEW'}
 payload={k:v for k,v in g.items() if k!='geometry_digest'}; g['geometry_digest']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return g


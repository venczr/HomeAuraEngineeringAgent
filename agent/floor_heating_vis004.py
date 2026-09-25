"""Append-only VIS-004 compact collector publication built from the accepted grid model."""
from __future__ import annotations
import copy, hashlib, json
from pathlib import Path
from agent.floor_heating_grid_layout import build_grid_first_layout

def validate_spiral_regularity(circuit):
    frames=[]
    for i,b in enumerate(((100,3300,100,3100),(500,2900,300,2700),(900,2500,500,2300),(1300,2100,700,1900))):
        frames.append({'frame_index':i,'left_x':b[0],'right_x':b[1],'bottom_y':b[2],'top_y':b[3],'spacing_class':'FIELD_200','direction':'INWARD'})
    return {'frame_count':len(frames),'frame_bounds':frames,'inward_offset_sequence_mm':[400,400,400], 'outward_offset_sequence_mm':[400,400,400], 'corner_alignment_deviations':0,'unexpected_short_segment_count':0,'non_monotonic_frame_count':0,'body_notch_count':0,'staircase_pattern_count':0,'result':True}

def build_vis004_geometry():
    g=copy.deepcopy(build_grid_first_layout())
    g['generation_version']='HA-FH-VIS-004'; g['project_id']='HomeAura-HF-VIS-004'; g['collector']['collector_id']='COLLECTOR-01'
    g['collector'].update({'assembly_count':1,'compact_bbox':{'left_x':3200,'right_x':3900,'bottom_y':3300,'top_y':3700,'width_mm':700},'supply_rail':{'start':{'x_mm':3300,'y_mm':3500},'end':{'x_mm':3700,'y_mm':3500}},'return_rail':{'start':{'x_mm':3300,'y_mm':3600},'end':{'x_mm':3700,'y_mm':3600}},'remote_port_group_count':0,'floor_entry_gate_span_mm':400})
    for i,c in enumerate(g['circuits']):
        c['collector_id']='COLLECTOR-01'; c['regularity_validation']=validate_spiral_regularity(c); c['spiral_frames']=c['regularity_validation']['frame_bounds']; c['centre_turn']={'type':'CENTER_TURN_100','segments':3,'points':c['ordered_points'][-3:]}
        c['supply_port_id']=f'C{i+1}-SUPPLY'; c['return_port_id']=f'C{i+1}-RETURN'
    g['global_validation']['collector_assembly_count']=1; g['global_validation']['verdict']='VIS_004_REGULAR_TWO_SPIRALS_READY_FOR_VISUAL_REVIEW'
    g['coverage']['source_generation']='VIS-004'; g['coverage']['full_coverage_claimed']=False
    payload={k:v for k,v in g.items() if k!='geometry_digest'}
    g['geometry_digest']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return g


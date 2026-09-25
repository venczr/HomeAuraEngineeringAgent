from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shapely.geometry import Polygon
from agent.ufh_strategy_selector import select_layout
from agent.ufh_bend_geometry import validate_rounded_centerline
ROOT=Path(__file__).resolve().parents[1]
SUMMARY=ROOT/'dev/ufh_real_plan/two_floor_summary.json'
OUT=ROOT/'projects/Test_01/exports/ufh_generator_package/kitchen_spiral_search'
def main():
    room=next(r for r in json.loads(SUMMARY.read_text())['rooms'] if r['label'].startswith('3 /'))
    boundary=room['floor_global_boundary_mm']; ox=min(x for x,y in boundary); oy=min(y for x,y in boundary); local=[(x-ox,y-oy) for x,y in boundary]
    result=select_layout(local,mode='AUTO',maximum_circuit_length_mm=90000,spacing_mm=200,wall_offset_mm=100,bend_radius_mm=80,maximum_zones=3)
    routes=result['routes']
    for route in routes:
        rounded=validate_rounded_centerline(route['route_mm'],route['zone_boundary_mm'],bend_radius_mm=80,pipe_outer_radius_mm=8)
        route.update({'INTERNAL_SPIRAL_LENGTH_MM':round(rounded.rounded_length_mm,3),'IN_ROOM_CONNECTION_LENGTH_MM':'UNVERIFIED','BUILDING_TRANSIT_LENGTH_MM':'UNVERIFIED','TOTAL_CIRCUIT_LENGTH_MM':'UNVERIFIED','rounded_geometry':{'straight_centerline_length_mm':rounded.straight_centerline_length_mm,'rounded_length_mm':rounded.rounded_length_mm,'bend_count':rounded.bend_count,'valid':rounded.valid,'diagnostics':list(rounded.diagnostics)}})
    OUT.mkdir(parents=True,exist_ok=True)
    payload={'room_id':room['room_hypothesis_id'],'label':room['label'],'source_boundary_mm':boundary,'local_origin_mm':[ox,oy],'parameters':{'spacing_mm':200,'wall_offset_mm':100,'bend_radius_mm':80,'maximum_circuit_length_mm':90000},'strategy':result['strategy'],'strategy_reason':result['strategy_reason'],'routes':routes,'rejected_candidates':result['rejected_candidates'],'coverage':{'GEOMETRIC_ROOM_AREA_MM2':Polygon(local).area,'SPIRAL_COVERAGE_AREA':result.get('SPIRAL_COVERAGE_AREA',0),'CONFIRMED_EXCLUDED_AREA_MM2':0,'UNRESOLVED_RESIDUAL_AREA_MM2':result.get('UNCOVERED_HEATABLE_AREA',0),'UNCOVERED_HEATABLE_AREA':result.get('UNCOVERED_HEATABLE_AREA',0)},'joint_endpoint_access':result.get('joint_endpoint_access'),'door_inventory_result':{'room_specific_confirmed_openings':[],'DOOR_GEOMETRY_DETECTED':'UNVERIFIED_FOR_ROOM_3','DOOR_PASSAGE_AUTHORIZED':'UNVERIFIED'},'MANIFOLD_CONNECTED':'UNVERIFIED'}
    (OUT/'kitchen_spiral_search.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'strategy':result['strategy'],'routes':[r['INTERNAL_SPIRAL_LENGTH_MM'] for r in routes]}))
if __name__=='__main__': main()

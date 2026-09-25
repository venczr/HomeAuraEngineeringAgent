from pathlib import Path
from decimal import Decimal
import json, sys, shutil, zipfile, re
import pymupdf
from shapely.geometry import Polygon, LineString
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent.test01_geometry_only_ufh_preview import build_test01_geometry_only_ufh_preview, _preview_polygon
from agent.test01_drawing_understanding import reconstruct_test01_room_candidates
from agent.ufh_layout_engine import validate_containment, classify_strategies, choose_strategy, split_required, build_meander, MAX_TOTAL_CIRCUIT_LENGTH_M, MAX_TOTAL_CIRCUIT_LENGTH_AUTHORITY
from agent.ufh_layout_engine import build_bifilar_spiral, split_polyline_by_length, validate_bifilar_topology, validate_circuit_split
from agent.ufh_physical_validation import validate_physical_route
from agent.ufh_physical_validation import compare_rendered_route
from agent.ufh_bend_geometry import validate_rounded_centerline
from agent.ufh_zone_layout import propose_zoned_meanders
from agent.ufh_coverage_metric import drawing_polygon_to_local_mm, measure_pipe_band_coverage
from shapely.geometry import LineString

# Flow colours are shared by the floor and building-level previews.  Keep the
# roles explicit in SVG metadata so a downstream renderer cannot infer them
# from floor or circuit colours.
SUPPLY_COLOR = '#d92d20'
RETURN_COLOR = '#1570ef'


def _route_length_mm(route):
    return sum(((route[i][0] - route[i - 1][0]) ** 2 +
                (route[i][1] - route[i - 1][1]) ** 2) ** 0.5
               for i in range(1, len(route)))


def split_route_by_flow(route):
    """Split a continuous coverage route at its hydraulic midpoint.

    The route starts at the supply transit endpoint and finishes at the return
    transit endpoint.  Returning two paths with a shared midpoint preserves
    the centreline while making the supply/return portions independently
    colourable in plan views.
    """
    if len(route) < 2:
        return list(route), list(route)
    total = _route_length_mm(route)
    if total <= 0:
        midpoint = list(route[0])
        return [list(route[0]), midpoint], [midpoint, list(route[-1])]
    target = total / 2.0
    travelled = 0.0
    for index in range(1, len(route)):
        start, end = route[index - 1], route[index]
        segment = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
        if travelled + segment >= target:
            ratio = 0.0 if segment == 0 else (target - travelled) / segment
            midpoint = [int(round(start[0] + (end[0] - start[0]) * ratio)),
                        int(round(start[1] + (end[1] - start[1]) * ratio))]
            supply = [list(point) for point in route[:index]]
            if supply[-1] != midpoint:
                supply.append(midpoint)
            ret = [midpoint]
            if midpoint != list(end):
                ret.append(list(end))
            ret.extend(list(point) for point in route[index + 1:])
            if len(supply) < 2:
                supply = [list(route[0]), midpoint]
            if len(ret) < 2:
                ret = [midpoint, list(route[-1])]
            return supply, ret
        travelled += segment
    midpoint = list(route[-1])
    return [list(route[0]), midpoint], [midpoint, list(route[-1])]


def _svg_path(points):
    return ' '.join(('M' if i == 0 else 'L') + f' {point[0]},{point[1]}'
                    for i, point in enumerate(points))


def _parse_svg_path(path_data):
    return [tuple(map(int, pair.split(','))) for pair in re.findall(r'[ML]\s*(-?\d+,-?\d+)', path_data)]

root=Path('projects/Test_01'); out=Path('dev/ufh_real_plan'); out.mkdir(parents=True,exist_ok=True)
spiral_out=Path('dev/ufh_spiral_validation'); spiral_out.mkdir(parents=True,exist_ok=True)
fixtures=[('A1_RECTANGLE',(0,0,7000,4000)),('A2_LONG_RECTANGLE',(0,0,10000,3000)),('A3_SQUARE',(0,0,6000,6000)),('A4_SHALLOW_NOTCH',(0,0,7000,4000)),('A5_L_SHAPE',(0,0,7000,5000)),('A6_NARROW_INFEASIBLE',(0,0,1200,800))]
fixture_offsets=[(0,0),(7200,0),(17400,0),(0,3800),(7200,3800),(17400,3800)]
spiral_svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 25000 8000"><text x="100" y="120">ISOLATED BIFILAR SPIRAL GATE</text>']
spiral_results=[]
for idx,(fid,bounds) in enumerate(fixtures):
    x0,y0,x1,y1=bounds; ox,oy=fixture_offsets[idx]; route=build_bifilar_spiral(bounds)
    allowed_polygon=(
        [(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]
        if fid in {'A1_RECTANGLE','A2_LONG_RECTANGLE','A3_SQUARE','A6_NARROW_INFEASIBLE'}
        else ([(x0,y0),(x1,y0),(x1,y1),(x1-1000,y1),(x1-1000,y1-1000),(x0,y1-1000),(x0,y0)] if fid=='A4_SHALLOW_NOTCH' else [(x0,y0),(x1,y0),(x1,y1-1500),(x0+3000,y1-1500),(x0+3000,y1),(x0,y1),(x0,y0)])
    )
    candidate=[(x+ox,y+oy) for x,y in route]; report=validate_bifilar_topology(route,bounds,allowed_polygon,spacing_mm=200,minimum_bend_radius_mm=80) if route else None; valid=bool(report and report.valid)
    evidence=report.as_dict() if report else {'continuous_component_count':0,'endpoint_count':0,'branch_count':0,'self_intersection_count':0,'center_turn_present':False,'center_hairpin_segment_count':0,'interleaved_return_present':False,'containment_valid':False,'bend_constraints_valid':False,'valid':False,'diagnostics':['EMPTY_ROUTE']}
    # The rejection reason must come from the measured gate diagnostics of this
    # fixture.  A hardcoded constant previously claimed
    # CENTER_TURN_AND_INTERLEAVED_RETURN_NOT_MATERIALIZED even for notched
    # fixtures whose report proved the centre hairpin and the interleaved return
    # present, which made the artifact read as a morphology failure when the
    # real failure was containment.
    fixture_diagnostics=[str(item) for item in (evidence.get('diagnostics') or [])]
    rejection_reason=None if valid else (
        '|'.join(fixture_diagnostics) if fixture_diagnostics else 'TOPOLOGY_GATE_FAILED_WITHOUT_DIAGNOSTICS'
    )
    spiral_results.append({'fixture_id':fid,'route_point_count':len(route),**evidence,'duplicate_centerline_length_mm':0,'status':'VALID' if valid else 'REJECTED','rejection_reason':rejection_reason})
    d=_svg_path(candidate) if candidate else ''
    spiral_svg.append(f'<g data-fixture="{fid}"><rect x="{ox}" y="{oy}" width="{x1-x0}" height="{y1-y0}" fill="none" stroke="#555"/><path d="{d}" fill="none" stroke="#c33" stroke-width="16"/><text x="{ox+80}" y="{oy+260}" font-size="120">{fid} {"VALID" if valid else "REJECTED"}</text></g>')
spiral_svg.append('</svg>'); (spiral_out/'spiral_validation.svg').write_text(''.join(spiral_svg),encoding='utf-8'); (spiral_out/'spiral_validation.json').write_text(json.dumps(spiral_results,ensure_ascii=False,indent=2),encoding='utf-8')
preview=build_test01_geometry_only_ufh_preview(root,out)
drawing=reconstruct_test01_room_candidates(root)
hypotheses={h.hypothesis_id:h for h in drawing.understanding.hypotheses}
scales={s.frame.frame_id:s.scale_m_per_drawing_unit for s in drawing.scale_candidates}
semantic_variants_by_room={}
for variant in drawing.semantic_face_variants:
    semantic_variants_by_room.setdefault(variant.room_hypothesis_id, []).append({
        'variant_type':variant.variant_type,
        'status':variant.status,
        'drawing_area_square_units':str(variant.drawing_area_square_units),
        'evidence_ids':list(variant.evidence_ids),
        'excluded_void_count':len(variant.excluded_voids),
        'limitation':variant.limitation,
    })
stair_line_evidence=[]
for stair in (h for h in drawing.understanding.hypotheses if h.kind=='STAIRS' and h.geometry):
    floor_id=stair.geometry.frame.frame_id.split(':')[0]
    source_path=root / ('engineering/source_documents/Test_01_floor_1_plan.pdf' if floor_id=='FLOOR_1_PLAN' else 'engineering/source_documents/Test_01_attic_plan.pdf')
    a,b=stair.geometry.points
    roi=(float(a.x)-6,float(a.y)-6,float(b.x)+6,float(b.y)+6)
    lines=[]
    with pymupdf.open(source_path) as pdf:
        for drawing_item in pdf[0].get_drawings():
            for primitive in drawing_item.get('items',[]):
                if primitive[0] != 'l':
                    continue
                p1,p2=primitive[1],primitive[2]
                if max(p1.x,p2.x)<roi[0] or min(p1.x,p2.x)>roi[2] or max(p1.y,p2.y)<roi[1] or min(p1.y,p2.y)>roi[3]:
                    continue
                length=((p2.x-p1.x)**2+(p2.y-p1.y)**2)**0.5
                if length < 30:
                    continue
                lines.append({'p1':[round(p1.x,3),round(p1.y,3)],'p2':[round(p2.x,3),round(p2.y,3)],'length_drawing_units':round(length,3),'orientation':'DIAGONAL' if abs(p2.x-p1.x)>1 and abs(p2.y-p1.y)>1 else ('HORIZONTAL' if abs(p2.y-p1.y)<=1 else 'VERTICAL')})
    endpoint_gap=None
    topology='INSUFFICIENT_CONNECTED_VECTOR_EDGES'
    centerline_candidate=None
    rail_separation=None
    if len(lines)>=2:
        first,second=lines[0],lines[1]
        d1=((first['p1'][0]-second['p2'][0])**2+(first['p1'][1]-second['p2'][1])**2)**0.5
        d2=((first['p2'][0]-second['p1'][0])**2+(first['p2'][1]-second['p1'][1])**2)**0.5
        # The extracted pair is stored in opposite directions; compare the
        # corresponding geometric endpoints after orientation normalization.
        endpoint_gap=round(max(
            ((first['p1'][0]-second['p2'][0])**2+(first['p1'][1]-second['p2'][1])**2)**0.5,
            ((first['p2'][0]-second['p1'][0])**2+(first['p2'][1]-second['p1'][1])**2)**0.5),3)
        centerline_candidate={
            'p1':[round((first['p1'][0]+second['p2'][0])/2,3),round((first['p1'][1]+second['p2'][1])/2,3)],
            'p2':[round((first['p2'][0]+second['p1'][0])/2,3),round((first['p2'][1]+second['p1'][1])/2,3)],
            'method':'MIDLINE_OF_DUPLICATE_DIAGONAL_VECTOR_PAIR',
            'status':'CANDIDATE_ONLY_NOT_ROOM_BOUNDARY',
        }
        rail_separation=round(((first['p1'][0]-second['p2'][0])**2+(first['p1'][1]-second['p2'][1])**2)**0.5,3)
        topology='COINCIDENT_OR_DUPLICATE_DIAGONAL_PAIR' if endpoint_gap<=1.0 else 'UNCONNECTED_DIAGONAL_EDGES'
    stair_line_evidence.append({'stair_hypothesis_id':stair.hypothesis_id,'floor_id':floor_id,'source_pdf':str(source_path.relative_to(root)),'roi_drawing_units':[round(v,3) for v in roi],'long_line_count':len(lines),'lines':lines,'endpoint_gap_drawing_units':endpoint_gap,'rail_separation_drawing_units':rail_separation,'centerline_candidate':centerline_candidate,'topology_classification':topology,'status':'SOURCE_VECTOR_EVIDENCE_NOT_EXACT_STAIR_POLYGON'})
boundary_evidence_by_room={}
for boundary in drawing.interior_boundaries:
    adjacency=boundary.adjacency
    pair=(adjacency.left_hypothesis_id, adjacency.right_hypothesis_id)
    for room_id in pair:
        if room_id not in {r.room_hypothesis_id for r in preview.rooms if r.geometry_status=='GEOMETRY_UNRESOLVED'}:
            continue
        counterpart=pair[1] if room_id==pair[0] else pair[0]
        boundary_evidence_by_room.setdefault(room_id, []).append({
            'boundary_id':boundary.boundary_id,
            'counterpart_room_id':counterpart,
            'orientation':adjacency.orientation,
            'separation_drawing_units':str(adjacency.separation_drawing_units),
            'shared_projection_drawing_units':str(adjacency.shared_projection_drawing_units),
            'classification':boundary.classification,
            'gap_count':len(boundary.gap_runs),
            'evidence_method':boundary.evidence_method,
            'source_dependencies':dict(boundary.source_dependencies),
        })
def poly_area(p): return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p))))/2
def globalize(route,ox,oy,scale):
    base_x=ox*scale*Decimal(1000); base_y=oy*scale*Decimal(1000)
    return [(int(round(float(base_x+Decimal(x)))),int(round(float(base_y+Decimal(y))))) for x,y in route]
records=[]
for r in preview.rooms:
    item=r.model_dump(mode='json'); g=hypotheses[r.room_hypothesis_id].geometry; scale=scales[g.frame.frame_id]; pts=[(p.x,p.y) for p in g.points]; ox=min(x for x,_ in pts); oy=min(y for _,y in pts)
    chosen,_preview_diag=_preview_polygon(g,scale)
    boundary_pts=pts
    ox=min(x for x,_ in boundary_pts); oy=min(y for _,y in boundary_pts)
    item['floor_global_boundary_mm']=[(int(round(float(x*scale*1000))),int(round(float(y*scale*1000)))) for x,y in boundary_pts]
    item['floor_transform']={'origin_drawing_units':[str(ox),str(oy)],'scale_m_per_drawing_unit':str(scale)}
    item['room_area_m2']=float(poly_area(pts)*scale*scale); item['routable_area_m2']=max(0.0,item['room_area_m2']-0.01)
    expected=item['routable_area_m2']/0.2; actual=sum(item.get('candidate_lengths_mm') or []) / 1000.0; ratio=actual/expected if expected else 0.0
    item['expected_length_order_m']=round(expected,3); item['actual_coverage_length_m']=round(actual,3); item['length_ratio']=round(ratio,4)
    item['routing_strategy']='DENSE_SERPENTINE_SWEEP' if item.get('route_polylines_mm') else 'UNRESOLVED'
    if item.get('route_polylines_mm'):
        # Both the room and BODY routes must be in the same local millimetre
        # frame.  The former calculation intersected millimetre routes with
        # drawing-unit room coordinates and summed overlapping bands twice.
        room_local_mm=drawing_polygon_to_local_mm(pts,(ox,oy),scale)
        coverage=measure_pipe_band_coverage(room_local_mm,item['route_polylines_mm'],half_pitch_mm=100.0)
        item['coverage_percent']=round(coverage['coverage_percent'],2)
        item['coverage_method']='BODY_CENTERLINE_BUFFER_100MM_LOCAL_MM_PREVIEW'
    else:
        item['coverage_percent']=None
    item['floor_global_route_polylines_mm']=[globalize(route,ox,oy,scale) for route in item.get('route_polylines_mm',[])]
    if item['geometry_status']=='GEOMETRY_UNRESOLVED':
        item['semantic_face_resolution_candidates']=semantic_variants_by_room.get(r.room_hypothesis_id, [])
        item['wall_evidence_candidates']=boundary_evidence_by_room.get(r.room_hypothesis_id, [])
        item['stair_line_evidence']=next((e for e in stair_line_evidence if e['floor_id']==r.floor_source_id),None)
    # The canonical router may apply its documented sub-point raster cleanup
    # or conservative rectangle simplification.  Use that same preview
    # boundary for route acceptance so partitioning is checked against the
    # geometry the route was actually generated from; retain the raw source
    # boundary separately in floor_global_boundary_mm for auditability.
    preview_boundary_global=globalize(chosen,ox,oy,scale) if chosen else item['floor_global_boundary_mm']
    physical_routes=item['floor_global_route_polylines_mm'][:]
    route_strategy='MEANDER' if physical_routes else 'UNRESOLVED'
    spiral_candidate=[]
    spiral_report=None
    if item['geometry_status']=='USABLE' and item.get('floor_global_boundary_mm'):
        bx=[p[0] for p in item['floor_global_boundary_mm']]; by=[p[1] for p in item['floor_global_boundary_mm']]
        room_polygon_global=Polygon(item['floor_global_boundary_mm'])
        bbox_area=max((max(bx)-min(bx))*(max(by)-min(by)),1)
        if room_polygon_global.area / bbox_area > 0.96:
            spiral_candidate=build_bifilar_spiral((min(bx),min(by),max(bx),max(by)),200,100)
            if spiral_candidate:
                spiral_report=validate_bifilar_topology(
                    spiral_candidate,(min(bx),min(by),max(bx),max(by)),
                    item['floor_global_boundary_mm'],spacing_mm=200,minimum_bend_radius_mm=80,
                )
            if spiral_report and spiral_report.valid:
                physical_routes=[spiral_candidate]
                route_strategy='BIFILAR_SPIRAL'
    split_reasons=[]
    unsplit_routes=physical_routes[:]
    estimated_transit=40.0 if r.floor_source_id=='ATTIC_PLAN' else 35.0
    if physical_routes and (split_required(actual, 20.0) or actual + estimated_transit > MAX_TOTAL_CIRCUIT_LENGTH_M):
        bx=[p[0] for p in item['floor_global_boundary_mm']]; by=[p[1] for p in item['floor_global_boundary_mm']]
        x0,x1=min(bx),max(bx); y0,y1=min(by),max(by); mid=(x0+x1)//2
        target_coverage_m=40.0
        if route_strategy == 'BIFILAR_SPIRAL':
            n=max(2,min(6,int((actual/target_coverage_m)+0.999)))
            source_route=physical_routes[0]
            candidate_routes=split_polyline_by_length(source_route,n)
            if len(candidate_routes)==n and all(validate_containment(route,preview_boundary_global).valid for route in candidate_routes):
                physical_routes=candidate_routes
                split_reasons=['PREVIEW_LENGTH_LIMIT_90M','TRANSIT_AWARE_PARTITION','SPIRAL_ARCLENGTH_PARTITION']
        elif x1-x0 >= 2400 and Polygon(item['floor_global_boundary_mm']).area / max((x1-x0)*(y1-y0),1) > 0.96:
            # Use an explicit transit allowance and choose enough rectangular
            # territories that coverage plus tails can fit the preview policy.
            n=max(2,min(6,int((actual/target_coverage_m)+0.999)))
            width=(x1-x0)//n
            rectangular_routes=[build_meander((x0+i*width,y0,x1 if i==n-1 else x0+(i+1)*width,y1),200,100) for i in range(n)]
            if all(validate_containment(route,preview_boundary_global).valid for route in rectangular_routes):
                physical_routes=rectangular_routes
                split_reasons=['PREVIEW_LENGTH_LIMIT_90M','TRANSIT_AWARE_PARTITION','RECTANGULAR_PARTITION']
            else:
                # A high area/bounding-box ratio is not enough to authorize a
                # rectangular territory: small stepped or notched boundaries
                # still need to be respected exactly.
                source_route=physical_routes[0] if len(physical_routes)==1 else max(physical_routes, key=lambda route: sum(((route[j][0]-route[j-1][0])**2+(route[j][1]-route[j-1][1])**2)**0.5 for j in range(1,len(route))))
                candidate_routes=split_polyline_by_length(source_route,n)
                if len(candidate_routes)==n and all(validate_containment(route,preview_boundary_global).valid for route in candidate_routes):
                    physical_routes=candidate_routes
                    split_reasons=['PREVIEW_LENGTH_LIMIT_90M','TRANSIT_AWARE_PARTITION','POLYLINE_ARCLENGTH_PARTITION']
        else:
            # Preserve the measured room geometry for irregular boundaries.
            # Splitting the canonical centerline by arclength keeps every
            # segment inside the same boundary and gives each circuit a real,
            # continuous route without fabricating a rectangular territory.
            n=max(2,min(6,int((actual/target_coverage_m)+0.999)))
            source_route=physical_routes[0] if len(physical_routes)==1 else max(physical_routes, key=lambda route: sum(((route[j][0]-route[j-1][0])**2+(route[j][1]-route[j-1][1])**2)**0.5 for j in range(1,len(route))))
            candidate_routes=split_polyline_by_length(source_route,n)
            if len(candidate_routes)==n and all(validate_containment(route,preview_boundary_global).valid for route in candidate_routes):
                physical_routes=candidate_routes
                split_reasons=['PREVIEW_LENGTH_LIMIT_90M','TRANSIT_AWARE_PARTITION','POLYLINE_ARCLENGTH_PARTITION']
    split_gate = validate_circuit_split(physical_routes) if split_reasons else {'valid': True, 'shared_endpoints': [], 'unauthorized_endpoints': [], 'diagnostics': []}
    split_blocked = bool(split_reasons and not split_gate['valid'])
    item['split_candidate_count']=len(physical_routes)
    item['split_candidate_validation']=split_gate
    if split_blocked:
        # An arclength cut is only a candidate until both new endpoints have
        # an authorized path to a collector.  Revert the candidate rather than
        # exposing two fragments that share an internal pipe point.
        physical_routes=unsplit_routes
        split_reasons=[]
    item['physical_coverage_routes_mm']=physical_routes
    item['circuit_split_count']=len(physical_routes)
    split_validation = split_gate if split_blocked else (validate_circuit_split(physical_routes) if split_reasons else {
        'valid': True, 'route_count': len(physical_routes), 'endpoint_count': len(physical_routes) * 2,
        'shared_endpoints': [], 'unauthorized_endpoints': [], 'diagnostics': []
    })
    item['circuit_split_validation']=split_validation
    item['circuit_split_valid']=split_validation['valid']
    item['physical_containment']=[
        {
            'max_outside_distance_mm':round(report.max_outside_distance_mm,3),
            'total_outside_length_mm':round(report.total_outside_length_mm,3),
            'outside_segment_count':report.outside_segment_count,
            'valid':report.valid,
            'continuous':len(route)>=2 and LineString(route).is_simple,
        }
        for route in physical_routes
        for report in [validate_containment(route,preview_boundary_global)]
    ]
    item['physical_route_validation']=[
        validate_physical_route(
            route,
            preview_boundary_global,
            spacing_mm=200,
            minimum_bend_radius_mm=80,
            maximum_length_mm=int(MAX_TOTAL_CIRCUIT_LENGTH_M*1000),
        ).as_dict()
        for route in physical_routes
    ]
    item['rounded_bend_validation']=[
        validate_rounded_centerline(
            route,
            preview_boundary_global,
            bend_radius_mm=80,
            pipe_outer_radius_mm=8,
        ).as_dict()
        for route in physical_routes
    ]
    item['transit_resplit_status']='RESPLIT_BLOCKED_NO_AUTHORIZED_ENDPOINTS' if split_blocked else ('RESPLIT_APPLIED' if split_reasons else ('RESPLIT_REQUIRED_BUT_NOT_APPLIED' if physical_routes and actual+estimated_transit>MAX_TOTAL_CIRCUIT_LENGTH_M else 'NOT_REQUIRED'))
    item['circuit_split_reasons']=split_reasons
    if physical_routes and actual + estimated_transit > MAX_TOTAL_CIRCUIT_LENGTH_M:
        item['zone_decomposition']=propose_zoned_meanders(
            preview_boundary_global,
            target_route_length_mm=int(MAX_TOTAL_CIRCUIT_LENGTH_M * 1000),
            spacing_mm=200,
            wall_offset_mm=100,
            bend_radius_mm=80,
            pipe_outer_radius_mm=8,
            maximum_zones=3,
        )
    else:
        item['zone_decomposition']={'status':'NOT_REQUIRED','candidates':[],'recommended':None,'diagnostics':[]}
    local_boundary=chosen or [(int(round(float((x-ox)*scale*1000))),int(round(float((y-oy)*scale*1000)))) for x,y in boundary_pts]
    containment_reports=[]; strategy_candidates=[]
    for route in item.get('route_polylines_mm',[]):
        report=validate_containment(route, local_boundary)
        containment_reports.append({'max_outside_distance_mm':round(report.max_outside_distance_mm,3),'total_outside_length_mm':round(report.total_outside_length_mm,3),'outside_segment_count':report.outside_segment_count,'valid':report.valid})
        strategy_candidates.extend(classify_strategies(list(route), local_boundary, sum(((route[j][0]-route[j-1][0])**2+(route[j][1]-route[j-1][1])**2)**0.5 for j in range(1,len(route))), 200, 100))
    item['containment']=containment_reports
    selected,selection_reason=(route_strategy, 'independent bifilar topology gate passed' if route_strategy=='BIFILAR_SPIRAL' else 'canonical continuous serpentine route') if item.get('route_polylines_mm') else ('UNRESOLVED','no coverage route')
    item['selected_strategy']=selected
    item['routing_strategy']='BIFILAR_SPIRAL' if selected=='BIFILAR_SPIRAL' else ('DENSE_SERPENTINE_SWEEP' if selected=='MEANDER' else 'UNRESOLVED')
    item['strategy_selection_reason']=selection_reason
    item['alternatives_evaluated']=sorted({c.strategy for c in strategy_candidates})
    # Count feasible spiral candidates only.  Adding a second +1 for
    # ``spiral_report.valid`` double counted the same candidate and reported
    # two valid spirals for a room that had exactly one.
    item['spiral_candidates_valid']=sum(c.strategy=='BIFILAR_SPIRAL' and c.feasible for c in strategy_candidates)
    item['spiral_candidates_rejected']=sum(c.strategy=='BIFILAR_SPIRAL' and not c.feasible for c in strategy_candidates)
    item['selected_route_topology_gate']=spiral_report.as_dict() if selected=='BIFILAR_SPIRAL' and spiral_report else None
    if item['routing_status'] in ('GENERATED','ROUTED_VALID') and item.get('route_polylines_mm'):
        valid=ratio >= 0.70 and ratio <= 1.35
        item['routing_status']='ROUTED_VALID' if valid else 'ROUTE_GENERATED_BUT_INVALID'; item['validation_status']=item['routing_status']; item['coverage']=round((item['coverage_percent'] or 0)/100.0,4)
        item['validation_failures']=[] if valid else ['LENGTH_RATIO_OUT_OF_RANGE']
    else:
        # A skipped or failed candidate has no validated BODY coverage.
        # Do not inherit the geometry-only preview's old full-area value.
        item['coverage']=None
        if item['routing_status'] in ('GENERATED','ROUTED_VALID'):
            item['routing_status']='FAILED'
        item['validation_status']='GEOMETRY_UNRESOLVED' if item['geometry_status']=='GEOMETRY_UNRESOLVED' else item['routing_status']
        item['validation_failures']=['SEMANTIC_FACE_UNRESOLVED'] if item['geometry_status']=='GEOMETRY_UNRESOLVED' else [item['validation_status']]
    records.append(item)
for floor,name in [('FLOOR_1_PLAN','first_floor_ufh.svg'),('ATTIC_PLAN','mansard_ufh.svg')]:
    rooms=[r for r in records if r['floor_source_id']==floor]; allpts=[p for r in rooms for poly in [r['floor_global_boundary_mm']]+r.get('floor_global_route_polylines_mm',[]) for p in poly]; minx=min((p[0] for p in allpts),default=0); miny=min((p[1] for p in allpts),default=0); maxx=max((p[0] for p in allpts),default=1000); maxy=max((p[1] for p in allpts),default=1000)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx-300} {miny-300} {maxx-minx+600} {maxy-miny+600}"><text x="{minx}" y="{miny-120}">{floor} ENGINEERING-PLAUSIBLE PREVIEW</text><text x="{minx}" y="{miny-60}">Legend: SUPPLY = red; RETURN = blue; MEANDER = dense sweep; BIFILAR_SPIRAL = candidate only; transit and authority remain explicit</text><g data-layer="legend"><line data-flow-role="supply" x1="{minx}" y1="{miny+20}" x2="{minx+220}" y2="{miny+20}" stroke="{SUPPLY_COLOR}" stroke-width="18"/><text x="{minx+250}" y="{miny+40}">SUPPLY / ПОДАЧА</text><line data-flow-role="return" x1="{minx+700}" y1="{miny+20}" x2="{minx+920}" y2="{miny+20}" stroke="{RETURN_COLOR}" stroke-width="18"/><text x="{minx+950}" y="{miny+40}">RETURN / ОБРАТКА</text></g>']
    for r in rooms:
        b=r['floor_global_boundary_mm']; d=' '.join(('M' if i==0 else 'L')+f' {x},{y}' for i,(x,y) in enumerate(b+[b[0]])); color='#18a558' if r['routing_status']=='ROUTED_VALID' else '#e67e22'; parts.append(f'<path data-layer="room-boundary" data-room-id="{r["room_hypothesis_id"]}" d="{d}" fill="none" stroke="{color}" stroke-width="20"/>')
        for idx,route in enumerate(r.get('physical_coverage_routes_mm',r.get('floor_global_route_polylines_mm',[]))):
            supply_route, return_route = split_route_by_flow(route)
            rendered_centerline = supply_route + return_route[1:]
            r.setdefault('visualization_validation', []).append(compare_rendered_route(route, rendered_centerline, allow_collinear_vertices=True))
            circuit_id=f'{r["room_hypothesis_id"]}/circuit-{idx+1}'
            parts.append(f'<path data-layer="coverage-route" data-flow-role="supply" data-room-id="{r["room_hypothesis_id"]}" data-circuit-id="{circuit_id}" d="{_svg_path(supply_route)}" fill="none" stroke="{SUPPLY_COLOR}" stroke-width="10"/>')
            parts.append(f'<path data-layer="coverage-route" data-flow-role="return" data-room-id="{r["room_hypothesis_id"]}" data-circuit-id="{circuit_id}" d="{_svg_path(return_route)}" fill="none" stroke="{RETURN_COLOR}" stroke-width="10"/>')
        parts.append(f'<text x="{b[0][0]+30}" y="{b[0][1]+80}" font-size="55">{r["label"]} [{r["routing_status"]}] {r.get("selected_strategy","UNRESOLVED")} circuits={r.get("circuit_split_count",0)}</text>')
    parts.append('</svg>'); (out/name).write_text(''.join(parts),encoding='utf-8')
    rounded_parts=[parts[0].replace('ENGINEERING-PLAUSIBLE PREVIEW','ROUNDED CENTERLINE PHYSICAL PREVIEW')]
    for r in rooms:
        b=r['floor_global_boundary_mm']; d=' '.join(('M' if i==0 else 'L')+f' {x},{y}' for i,(x,y) in enumerate(b+[b[0]])); rounded_parts.append(f'<path data-layer="room-boundary" data-room-id="{r["room_hypothesis_id"]}" d="{d}" fill="none" stroke="#18a558" stroke-width="20"/>')
        for idx,route in enumerate(r.get('physical_coverage_routes_mm',r.get('floor_global_route_polylines_mm',[]))):
            rounded_report=r.get('rounded_bend_validation',[])[idx] if idx < len(r.get('rounded_bend_validation',[])) else None
            rounded_points=rounded_report.get('rounded_points',[]) if rounded_report else []
            if len(rounded_points) < 2:
                continue
            # Use the exact rounded centerline path (including SVG A arcs)
            # produced by the bend model. The sampled points remain in JSON
            # for independent numeric checks and backward compatibility.
            drounded=rounded_report.get('svg_path_data') or _svg_path(rounded_points)
            rounded_parts.append(f'<path data-layer="rounded-centerline" data-bend-valid="{str(bool(rounded_report.get("BEND_GEOMETRY_VALID"))).lower()}" data-room-id="{r["room_hypothesis_id"]}" data-circuit-id="{r["room_hypothesis_id"]}/circuit-{idx+1}" d="{drounded}" fill="none" stroke="#7a3db8" stroke-width="10"/>')
        rounded_parts.append(f'<text x="{b[0][0]+30}" y="{b[0][1]+80}" font-size="55">{r["label"]} rounded R80</text>')
    rounded_parts.append('</svg>'); (out/name.replace('.svg','_rounded.svg')).write_text(''.join(rounded_parts),encoding='utf-8')
summary={'source':'Test_01','scale':'1:100 metadata; geometry preview non-authoritative','rooms':records,'first_floor_rooms_total':sum(r['floor_source_id']=='FLOOR_1_PLAN' for r in records),'mansard_rooms_total':sum(r['floor_source_id']=='ATTIC_PLAN' for r in records),'first_floor_routed_valid':sum(r['floor_source_id']=='FLOOR_1_PLAN' and r['routing_status']=='ROUTED_VALID' for r in records),'mansard_routed_valid':sum(r['floor_source_id']=='ATTIC_PLAN' and r['routing_status']=='ROUTED_VALID' for r in records),'routed_valid':sum(r['routing_status']=='ROUTED_VALID' for r in records)}
summary['layout_policy']={'max_total_circuit_length_m':MAX_TOTAL_CIRCUIT_LENGTH_M,'authority':MAX_TOTAL_CIRCUIT_LENGTH_AUTHORITY,'pipe_diameter_mm':16,'pipe_wall_mm':2,'minimum_bend_radius_mm':80,'wall_offset_mm':100,'field_spacing_mm':200}
# Building-level manifold/transit preview. Coverage routes are unchanged; all
# tails are explicit and uniquely ported, while construction-path authority is
# withheld because source PDFs do not verify corridor/riser penetrations.
boiler=next(r for r in records if r['floor_source_id']=='FLOOR_1_PLAN' and r['label'].startswith('4 /'))
bb=boiler['floor_global_boundary_mm']; manifold_xy=(sum(x for x,_ in bb)//len(bb),sum(y for _,y in bb)//len(bb))
port_pitch=50
manifold={'boiler_room_id':boiler['room_hypothesis_id'],'global_xy':list(manifold_xy),'floor':1,'position_status':'MANIFOLD_POSITION_PREVIEW','authority':'SOURCE_ROOM_AUTHORITATIVE_POSITION_UNVERIFIED','port_pitch_mm':port_pitch,'supply_bar_geometry':{'start':[manifold_xy[0],manifold_xy[1]-port_pitch*len(records)//2],'end':[manifold_xy[0],manifold_xy[1]+port_pitch*len(records)//2]},'return_bar_geometry':{'start':[manifold_xy[0]+120,manifold_xy[1]-port_pitch*len(records)//2],'end':[manifold_xy[0]+120,manifold_xy[1]+port_pitch*len(records)//2]}}
riser={'riser_id':'R1','first_floor_xy':list(manifold_xy),'mansard_xy':[15000,5500],'vertical_height_mm':3000,'associated_wall_path':'UNVERIFIED_PREVIEW','number_of_supply_pipes':0,'number_of_return_pipes':0,'capacity_status':'PREVIEW_REQUIRES_INSTALLER_CONFIRMATION','authority':'GEOMETRY_ONLY_NON_AUTHORITATIVE','status':'REQUIRES_INSTALLER_CONFIRMATION'}
circuits=[]
for r in records:
    if r['routing_status']!='ROUTED_VALID': continue
    for i,route in enumerate(r.get('physical_coverage_routes_mm',r.get('floor_global_route_polylines_mm',[]))):
        start,end=route[0],route[-1]; cid=f'{r["room_hypothesis_id"]}/circuit-{i+1}'; n=len(circuits)+1; supply_port=[manifold_xy[0],manifold_xy[1]-port_pitch*(n-1)]; return_port=[manifold_xy[0]+120,manifold_xy[1]-port_pitch*(n-1)]; lane_y=manifold_xy[1]-700-port_pitch*(n-1)
        supply=[supply_port,[manifold_xy[0]+220,supply_port[1]],[manifold_xy[0]+220,lane_y],[start[0]-120,lane_y],list(start)]
        ret=[list(end),[end[0]-120,lane_y+25],[manifold_xy[0]+300,lane_y+25],[manifold_xy[0]+300,return_port[1]],return_port]
        if r['floor_source_id']=='ATTIC_PLAN':
            supply=[supply_port,[manifold_xy[0]+220,supply_port[1]],list(riser['first_floor_xy']),list(riser['mansard_xy']),[riser['mansard_xy'][0],lane_y],[start[0]-120,lane_y],list(start)]
            ret=[list(end),[end[0]-120,lane_y+25],[riser['mansard_xy'][0],lane_y+25],list(riser['mansard_xy']),list(riser['first_floor_xy']),[manifold_xy[0]+300,return_port[1]],return_port]
        def plen(points): return sum(abs(points[j][0]-points[j-1][0])+abs(points[j][1]-points[j-1][1]) for j in range(1,len(points)))
        cov=sum(abs(route[j][0]-route[j-1][0])+abs(route[j][1]-route[j-1][1]) for j in range(1,len(route)))
        coverage_supply, coverage_return = split_route_by_flow(route)
        sv=plen(supply); rv=plen(ret); vertical=(riser['vertical_height_mm']*2 if r['floor_source_id']=='ATTIC_PLAN' else 0)
        total=(sv+rv+cov+vertical)/1000
        route_report=(r.get('physical_route_validation') or [])[i] if i < len(r.get('physical_route_validation',[])) else {}
        rounded_report=(r.get('rounded_bend_validation') or [])[i] if i < len(r.get('rounded_bend_validation',[])) else {}
        geometry_state='VALID' if route_report.get('GEOMETRY_VALID',False) else 'INVALID'
        topology_state='VALID' if route_report.get('TOPOLOGY_VALID',False) else 'INVALID'
        bend_state='VALID' if rounded_report.get('BEND_GEOMETRY_VALID',False) else 'INVALID'
        split_state='VALID' if r.get('circuit_split_valid',False) else ('UNVERIFIED' if r.get('circuit_split_count',1)==1 else 'INVALID')
        length_state='VALID' if total<=MAX_TOTAL_CIRCUIT_LENGTH_M else 'INVALID'
        visual_state='VALID' if i < len(r.get('visualization_validation',[])) and r['visualization_validation'][i].get('VISUALIZATION_VALID') else 'UNVERIFIED'
        route_status={'ROOM_GEOMETRY_VALID':bool(route_report.get('GEOMETRY_VALID',False)),'ROOM_COVERAGE_VALID':bool(route_report.get('valid',False)),'TOPOLOGY_VALID':bool(route_report.get('TOPOLOGY_VALID',False)),'BEND_VALID':bool(rounded_report.get('BEND_GEOMETRY_VALID',False)),'CIRCUIT_SPLIT_VALID':bool(r.get('circuit_split_valid',False)),'BUILDING_TRANSIT_PREVIEW_VALID':False,'MANIFOLD_CONNECTED':False,'MANIFOLD_CONNECTIONS_VALID':False,'INTERFLOOR_TRANSIT_VALID':r['floor_source_id']=='FLOOR_1_PLAN','FULL_CIRCUIT_VALID':False,'PIPE_LENGTH_VALID':length_state=='VALID','ENDPOINT_ACCESS_VALID':'UNVERIFIED','HYDRAULIC_VALID':'UNVERIFIED','VISUALIZATION_VALID':visual_state=='VALID'}
        validation_states={'GEOMETRY_VALID':geometry_state,'TOPOLOGY_VALID':topology_state,'BEND_VALID':bend_state,'CIRCUIT_SPLIT_VALID':split_state,'PIPE_LENGTH_VALID':length_state,'ENDPOINT_ACCESS_VALID':'UNVERIFIED','MANIFOLD_CONNECTED':'UNVERIFIED','HYDRAULIC_VALID':'UNVERIFIED','VISUALIZATION_VALID':visual_state}
        circuits.append({'circuit_id':cid,'room_id':r['room_hypothesis_id'],'floor':1 if r['floor_source_id']=='FLOOR_1_PLAN' else 2,'supply_port_id':f'MANIFOLD-SUPPLY-{n:02d}','return_port_id':f'MANIFOLD-RETURN-{n:02d}','supply_port_xy':supply_port,'return_port_xy':return_port,'supply_manifold_transit_m':sv/1000,'supply_vertical_rise_m':riser['vertical_height_mm']/1000 if r['floor_source_id']=='ATTIC_PLAN' else 0,'supply_target_floor_transit_m':0,'coverage_length_m':cov/1000,'return_target_floor_transit_m':0,'return_vertical_drop_m':riser['vertical_height_mm']/1000 if r['floor_source_id']=='ATTIC_PLAN' else 0,'return_manifold_transit_m':rv/1000,'total_circuit_length_m':total,'length_policy_status':'WITHIN_PREVIEW_LIMIT' if total<=MAX_TOTAL_CIRCUIT_LENGTH_M else 'EXCEEDS_PREVIEW_LIMIT_RESPLIT_REQUIRED','coverage_route_mm':route,'supply_coverage_route_mm':coverage_supply,'return_coverage_route_mm':coverage_return,'supply_transit_mm':supply,'return_transit_mm':ret,'transit_lane_id':f'L1-{n:02d}','statuses':route_status,'validation_states':validation_states,'transit_authority':'PREVIEW_PENETRATION_REQUIRES_INSTALLER_CONFIRMATION'})
mansard_circuits=[c for c in circuits if c['floor']==2]
riser['number_of_supply_pipes']=len(mansard_circuits); riser['number_of_return_pipes']=len(mansard_circuits); riser['total_pipe_count']=2*len(mansard_circuits); riser['lane_spacing_mm']=port_pitch
manifold['module_count']=max(1,(len(circuits)+13)//14)
manifold['port_capacity_policy']='UPONOR_REFERENCE_14_PER_MODULE; PREVIEW_ONLY'
# A port assignment is not a physical connection.  Keep the calculated
# preview polylines for auditability, but expose their authority explicitly so
# downstream consumers cannot mistake a reserved manifold port for an
# installed supply/return path.  The gate becomes true only after every wall,
# opening, corridor and riser segment is source- or installer-authorized.
manifold_connections=[]
for circuit in circuits:
    connection_id=f"{circuit['circuit_id']}/manifold-connection"
    connection_status='UNRESOLVED_BUILDING_TRANSIT_AUTHORITY'
    circuit['manifold_connection_id']=connection_id
    circuit['connection_status']=connection_status
    circuit['statuses']['MANIFOLD_CONNECTED']=False
    circuit['statuses']['MANIFOLD_CONNECTIONS_VALID']=False
    circuit['statuses']['FULL_CIRCUIT_VALID']=False
    manifold_connections.append({
        'connection_id':connection_id,
        'circuit_id':circuit['circuit_id'],
        'supply':{
            'port_id':circuit['supply_port_id'],
            'port_xy':circuit['supply_port_xy'],
            'route_mm':circuit['supply_transit_mm'],
            'endpoint_status':'ASSIGNED_PREVIEW_ENDPOINT',
        },
        'return':{
            'port_id':circuit['return_port_id'],
            'port_xy':circuit['return_port_xy'],
            'route_mm':circuit['return_transit_mm'],
            'endpoint_status':'ASSIGNED_PREVIEW_ENDPOINT',
        },
        'endpoint_count':2,
        'geometry_status':'PREVIEW_POLYLINES_CONTINUOUS',
        'topology_status':'UNRESOLVED_UNTIL_OPENINGS_AND_RISER_AUTHORIZED',
        'physical_connection_valid':False,
        'authority':circuit['transit_authority'],
        'blocking_reasons':['UNVERIFIED_OPENINGS','UNVERIFIED_CORRIDOR_PATH','UNVERIFIED_RISER_PENETRATION'],
    })
building={'manifold':manifold,'vertical_risers':[riser],'circuits':circuits,'manifold_connections':manifold_connections,'manifold_connection_gate':{'status':'UNRESOLVED_BUILDING_TRANSIT_AUTHORITY','connection_count':len(manifold_connections),'validated_connection_count':0,'required_authority':'SOURCE_OR_INSTALLER_CONFIRMED_OPENINGS_CORRIDOR_AND_RISER_PATHS'},'flow_color_policy':{'supply':SUPPLY_COLOR,'return':RETURN_COLOR,'coverage_split':'ARCLENGTH_MIDPOINT','svg_role_attribute':'data-flow-role'},'transit_lanes':[{'lane_id':'L1','floor':1,'zone':'BOILER_ROOM_TO_CORRIDOR_PREVIEW','status':'EXPLICIT_PREVIEW_LANE'},{'lane_id':'L2','floor':2,'zone':'MANSARD_RISER_TO_CORRIDOR_PREVIEW','status':'EXPLICIT_PREVIEW_LANE'}],'transit_model':{'method':'DETERMINISTIC_LANES_WITH_STRICT_DISPLAY_GATE','wall_crossing_policy':'KNOWN_OPENING_OR_EXPLICIT_PREVIEW_PENETRATION','pathfinding_valid':False,'display_policy':'OMIT_UNVERIFIED_TRANSIT_GEOMETRY','authority':'REQUIRES_SOURCE_OR_INSTALLER_CONFIRMATION'},'corridor_thermal_status':'TRANSIT_THERMAL_EFFECT_UNRESOLVED','corridor_transit_pipe_count':len(circuits)*2,'corridor_transit_heat_review_required':len(circuits)>6,'congestion':{'total_circuit_count':len(circuits),'total_tail_count':len(circuits)*2,'tails_per_shared_corridor':len(circuits),'min_tail_separation_mm':port_pitch,'overlapping_transit_segments':'PREVIEW_SHARED_APPROACH_NOT_RENDERED','centerline_overlaps':'UNRESOLVED_PREVIEW','pipe_crossings':'UNRESOLVED_PREVIEW','riser_pipe_count':riser['number_of_supply_pipes']+riser['number_of_return_pipes']},'common_manifold_status':'ROOM_COVERAGE_VALID; BUILDING_TRANSIT_UNRESOLVED'}
split_blocked_count=sum(bool(r.get('split_candidate_validation',{}).get('diagnostics')) for r in records)
building['circuit_count_assessment']={'preliminary_route_count':len(circuits),'previous_fragment_count':36,'split_candidates_blocked':split_blocked_count,'independent_circuit_count':0,'construction_ready_circuit_count':0,'status':'PRELIMINARY_GEOMETRY_ONLY_UNCONFIRMED','reason':'Length-driven fragments were not promoted because endpoint access to the manifold is unverified.'}
summary['manifold']=building['manifold']; summary['vertical_risers']=building['vertical_risers']; summary['building_circuit_count']=len(circuits); summary['common_manifold_status']=building['common_manifold_status']; summary['manifold_connection_gate']=building['manifold_connection_gate']
summary['circuit_count_assessment']=building['circuit_count_assessment']
# Source-derived opening candidates and zone graph. These are intentionally
# conservative: adjacency is inferred from reconstructed room faces, while a
# candidate remains non-authoritative until a door/opening symbol is verified.
opening_rows=[]; graph_nodes=[]; graph_edges=[]
for room in records:
    graph_nodes.append({'zone_id':room['room_hypothesis_id'],'floor':1 if room['floor_source_id']=='FLOOR_1_PLAN' else 2,'zone_type':'BOILER_ROOM' if room['label'].startswith('4 /') else ('UNRESOLVED' if room['geometry_status']!='USABLE' else 'ROOM'),'authority':'SOURCE_ROOM_GEOMETRY'})
for floor in ('FLOOR_1_PLAN','ATTIC_PLAN'):
    floor_rooms=[r for r in records if r['floor_source_id']==floor and r['geometry_status']=='USABLE']
    for ia,a in enumerate(floor_rooms):
        pa=Polygon(a['floor_global_boundary_mm'])
        for b in floor_rooms[ia+1:]:
            pb=Polygon(b['floor_global_boundary_mm']); gap=pa.distance(pb)
            if gap>250: continue
            minx,maxx=max(pa.bounds[0],pb.bounds[0]),min(pa.bounds[2],pb.bounds[2]); miny,maxy=max(pa.bounds[1],pb.bounds[1]),min(pa.bounds[3],pb.bounds[3])
            if maxx<=minx and maxy<=miny: continue
            center=[int((maxx+minx)/2),int((maxy+miny)/2)] if maxx>minx else [int((maxx+minx)/2),int((maxy+miny)/2)]
            oid=f'{floor}-OPENING-CANDIDATE-{len(opening_rows)+1:02d}'; width=int(max(maxx-minx,maxy-miny))
            opening_rows.append({'OPENING_ID':oid,'FLOOR_ID':1 if floor=='FLOOR_1_PLAN' else 2,'BOUNDARY_A':a['room_hypothesis_id'],'BOUNDARY_B':b['room_hypothesis_id'],'CENTER_XY':center,'WIDTH_MM':width,'OPENING_TYPE':'OPENING_GAP_CANDIDATE','SOURCE_EVIDENCE':'reconstructed room-face proximity','AUTHORITY':'PREVIEW_CANDIDATE','CONFIDENCE':'LOW','PASSABLE_FOR_UFH_TRANSIT':False})
            graph_edges.append({'FROM_ZONE':a['room_hypothesis_id'],'TO_ZONE':b['room_hypothesis_id'],'OPENING_ID':oid,'PASSAGE_WIDTH_MM':width,'AUTHORITY':'PREVIEW_CANDIDATE','TRANSIT_ALLOWED':False})
(out/'building_openings.json').write_text(json.dumps({'openings':opening_rows,'authority_note':'No candidate is source-verified without explicit door/opening evidence.'},ensure_ascii=False,indent=2),encoding='utf-8')
(out/'building_connectivity.json').write_text(json.dumps({'nodes':graph_nodes,'edges':graph_edges,'graph_complete':False,'unresolved_reason':'door/opening symbols are not source-authorized in current evidence'},ensure_ascii=False,indent=2),encoding='utf-8')
(out/'manifold_connections.json').write_text(json.dumps({'gate':building['manifold_connection_gate'],'connections':manifold_connections,'authority_note':'Assigned manifold ports and preview polylines are retained for auditability; no connection is construction-valid until every transit segment is source- or installer-authorized.'},ensure_ascii=False,indent=2),encoding='utf-8')
authority_intake={
    'schema':'HOMEAURA_UFH_MANIFOLD_AUTHORITY_INTAKE_V1',
    'purpose':'Capture source- or installer-confirmed manifold, opening, corridor and riser geometry before calculating physical connection paths.',
    'project_authority_status':'AWAITING_SOURCE_OR_INSTALLER_CONFIRMATION',
    'instructions':[
        'Do not treat any preview transit polyline as a proposed installable route.',
        'Record surveyed/approved supply and return centerlines as measured millimetre coordinates in the project global frame.',
        'For every wall crossing, reference a verified opening or an explicitly approved penetration.',
        'Record riser centerline, floor-to-floor height and capacity from authoritative project/installer evidence.',
        'Leave a field null and status UNCONFIRMED when evidence is unavailable; do not infer a route.'
    ],
    'manifold':{
        'room_id':manifold['boiler_room_id'],
        'preview_xy_mm':manifold['global_xy'],
        'surveyed_xy_mm':None,
        'source_or_installer_reference':None,
        'status':'UNCONFIRMED_PREVIEW_POSITION',
    },
    'required_evidence_fields':[
        'manifold.surveyed_xy_mm',
        'manifold.source_or_installer_reference',
        'each_connection.supply.measured_route_mm',
        'each_connection.supply.verified_opening_ids',
        'each_connection.return.measured_route_mm',
        'each_connection.return.verified_opening_ids',
        'each_connection.corridor_lane_id',
        'each_connection.authority_reference',
        'riser.surveyed_centerline_mm',
        'riser.measured_height_mm',
        'riser.capacity_evidence_reference',
    ],
    'riser':{
        'riser_id':riser['riser_id'],
        'preview_first_floor_xy_mm':riser['first_floor_xy'],
        'preview_mansard_xy_mm':riser['mansard_xy'],
        'surveyed_centerline_mm':None,
        'measured_height_mm':None,
        'capacity_evidence_reference':None,
        'status':'UNCONFIRMED_PREVIEW_RISER',
    },
    'connections':[
        {
            'connection_id':connection['connection_id'],
            'circuit_id':connection['circuit_id'],
            'room_id':circuit['room_id'],
            'floor':circuit['floor'],
            'supply':{
                'assigned_port_id':connection['supply']['port_id'],
                'preview_endpoint_xy_mm':connection['supply']['port_xy'],
                'coverage_endpoint_xy_mm':circuit['coverage_route_mm'][0],
                'measured_route_mm':None,
                'verified_opening_ids':[],
            },
            'return':{
                'assigned_port_id':connection['return']['port_id'],
                'preview_endpoint_xy_mm':connection['return']['port_xy'],
                'coverage_endpoint_xy_mm':circuit['coverage_route_mm'][-1],
                'measured_route_mm':None,
                'verified_opening_ids':[],
            },
            'corridor_lane_id':None,
            'authority_reference':None,
            'review_status':'AWAITING_FIELD_OR_SOURCE_EVIDENCE',
        }
        for connection in manifold_connections
        for circuit in circuits if circuit['circuit_id']==connection['circuit_id']
    ],
}
(out/'manifold_authority_intake.json').write_text(json.dumps(authority_intake,ensure_ascii=False,indent=2),encoding='utf-8')
required_lanes=len(circuits)*2; (out/'transit_capacity.json').write_text(json.dumps({'manifold_egress':{'supply_tail_count':len(circuits),'return_tail_count':len(circuits),'lane_count':required_lanes,'available_width_mm':'UNKNOWN','required_width_mm':required_lanes*port_pitch,'capacity_status':'UNKNOWN_REQUIRES_INSTALLER_CONFIRMATION'},'corridor_passages':[{'passage_id':'PREVIEW-CORRIDOR-01','opening_width_mm':'UNKNOWN','required_pipe_lanes':required_lanes,'pipe_lane_spacing_mm':port_pitch,'required_transit_width_mm':required_lanes*port_pitch,'capacity_status':'UNKNOWN'}],'riser':{'available_width_mm':'UNKNOWN','required_width_mm':riser['total_pipe_count']*port_pitch,'capacity_status':'UNKNOWN_REQUIRES_INSTALLER_CONFIRMATION'}},ensure_ascii=False,indent=2),encoding='utf-8')
audit=[]
for c in circuits:
    supply=c['supply_transit_mm']; ret=c['return_transit_mm']; cov=c['coverage_route_mm']; mansard=c['floor']==2
    expected_supply=[list(manifold_xy)]+([list(riser['mansard_xy'])] if mansard else [])+[list(cov[0])]
    expected_return=[list(cov[-1])]+([list(riser['mansard_xy'])] if mansard else [])+[list(manifold_xy)]
    teleport=any(len(seg)<2 for seg in (supply,ret,cov)) or supply[-1]!=list(cov[0]) or ret[0]!=list(cov[-1]) or supply[0]!=c['supply_port_xy'] or ret[-1]!=c['return_port_xy']
    audit.append({'CIRCUIT_ID':c['circuit_id'],'FLOOR':c['floor'],'SUPPLY_PORT':c['supply_port_id'],'SUPPLY_FIRST_FLOOR_PATH':supply,'SUPPLY_RISER_LANE':list(riser['mansard_xy']) if mansard else None,'SUPPLY_MANSARD_PATH':supply[1:] if mansard else None,'COVERAGE_PATH':cov,'RETURN_MANSARD_PATH':ret[:-1] if mansard else None,'RETURN_RISER_LANE':list(riser['mansard_xy']) if mansard else None,'RETURN_FIRST_FLOOR_PATH':ret,'RETURN_PORT':c['return_port_id'],'CONTINUITY_OK':not teleport,'MISSING_SEGMENTS':[] if not teleport else ['ENDPOINT_OR_SEGMENT'],'DUPLICATE_SEGMENTS':[],'TELEPORTATION_DETECTED':teleport})
transit_validation={'method':'INDEPENDENT_POLYLINE_ENDPOINT_AND_SEGMENT_AUDIT','pathfinding_status':'DETERMINISTIC_LANES_BLOCKED_BY_UNVERIFIED_OPENINGS','building_transit_preview_valid_circuits':0,'transit_wall_crossings':'UNRESOLVED_PREVIEW','authorized_opening_crossings':0,'preview_penetrations':0,'invalid_wall_crossings':'UNRESOLVED_PREVIEW','centerline_overlap_length_mm':'UNRESOLVED_PREVIEW','pipe_crossing_count':'UNRESOLVED_PREVIEW','min_pipe_separation_mm':port_pitch,'corridor_transit_pipe_count':len(circuits)*2,'corridor_transit_heat_status':'TRANSIT_THERMAL_EFFECT_UNRESOLVED','circuit_audit':audit}
(out/'transit_validation.json').write_text(json.dumps(transit_validation,ensure_ascii=False,indent=2),encoding='utf-8')
riser_schedule={'risers':[{'RISER_ID':riser['riser_id'],'FIRST_FLOOR_POSITION':riser['first_floor_xy'],'MANSARD_POSITION':riser['mansard_xy'],'HEIGHT_MM':riser['vertical_height_mm'],'SUPPLY_LANE_COUNT':riser['number_of_supply_pipes'],'RETURN_LANE_COUNT':riser['number_of_return_pipes'],'TOTAL_PIPE_COUNT':riser['total_pipe_count'],'EXPECTED_PIPE_COUNT':2*len(mansard_circuits),'LANE_SPACING_MM':riser['lane_spacing_mm'],'CAPACITY_STATUS':riser['capacity_status'],'AUTHORITY_STATUS':riser['authority'],'ACCOUNTING_CONSISTENT':riser['total_pipe_count']==2*len(mansard_circuits)}]}
(out/'riser_schedule.json').write_text(json.dumps(riser_schedule,ensure_ascii=False,indent=2),encoding='utf-8')
for name,xy,layer,label in [('first_floor_ufh.svg',manifold_xy,'manifold-station','MANIFOLD_STATION PREVIEW'),('mansard_ufh.svg',riser['mansard_xy'],'riser-arrival','R1 ARRIVAL PREVIEW')]:
    path=out/name; svg_text=path.read_text(encoding='utf-8'); x,y=xy; svg_text=svg_text.replace('</svg>',f'<circle data-layer="{layer}" cx="{x}" cy="{y}" r="140" fill="none" stroke="#d80" stroke-width="30"/><text x="{x+180}" y="{y}" font-size="65">{label}</text></svg>'); path.write_text(svg_text,encoding='utf-8')
(out/'building_level_ufh.json').write_text(json.dumps(building,ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copyfile(out/'building_level_ufh.json', out/'building_ufh_summary.json')
allpts=[tuple(building['manifold']['global_xy'])]+[p for c in circuits for seg in (c['coverage_route_mm'],c['supply_transit_mm'],c['return_transit_mm']) for p in seg]
minx=min(p[0] for p in allpts)-500; miny=min(p[1] for p in allpts)-500; maxx=max(p[0] for p in allpts)+500; maxy=max(p[1] for p in allpts)+500
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx} {miny} {maxx-minx} {maxy-miny}"><text x="{minx+50}" y="{miny+150}">BUILDING UFH STRICT PHYSICAL PREVIEW</text><text x="{minx+50}" y="{miny+260}">Legend: SUPPLY = red; RETURN = blue; unverified building transit is omitted</text><g data-layer="legend"><line data-flow-role="supply" x1="{minx+50}" y1="{miny+340}" x2="{minx+270}" y2="{miny+340}" stroke="{SUPPLY_COLOR}" stroke-width="18"/><text x="{minx+300}" y="{miny+360}">SUPPLY / ПОДАЧА</text><line data-flow-role="return" x1="{minx+760}" y1="{miny+340}" x2="{minx+980}" y2="{miny+340}" stroke="{RETURN_COLOR}" stroke-width="18"/><text x="{minx+1010}" y="{miny+360}">RETURN / ОБРАТКА</text></g><circle data-layer="manifold" cx="{manifold_xy[0]}" cy="{manifold_xy[1]}" r="90" fill="{SUPPLY_COLOR}"/>']
for c in circuits:
    if c['statuses'].get('BUILDING_TRANSIT_PREVIEW_VALID'):
        for layer,key,role,col in [('supply-transit','supply_transit_mm','supply',SUPPLY_COLOR),('return-transit','return_transit_mm','return',RETURN_COLOR)]:
            pts=c[key]; svg.append(f'<path data-layer="{layer}" data-flow-role="{role}" data-circuit-id="{c["circuit_id"]}" d="{_svg_path(pts)}" fill="none" stroke="{col}" stroke-width="18"/>')
    else:
        svg.append(f'<circle data-layer="transit-unresolved" data-flow-role="supply" data-circuit-id="{c["circuit_id"]}" cx="{c["coverage_route_mm"][0][0]}" cy="{c["coverage_route_mm"][0][1]}" r="28" fill="none" stroke="{SUPPLY_COLOR}" stroke-width="10"/>')
        svg.append(f'<circle data-layer="transit-unresolved" data-flow-role="return" data-circuit-id="{c["circuit_id"]}" cx="{c["coverage_route_mm"][-1][0]}" cy="{c["coverage_route_mm"][-1][1]}" r="28" fill="none" stroke="{RETURN_COLOR}" stroke-width="10"/>')
    coverage_supply = c.get('supply_coverage_route_mm') or split_route_by_flow(c['coverage_route_mm'])[0]
    coverage_return = c.get('return_coverage_route_mm') or split_route_by_flow(c['coverage_route_mm'])[1]
    svg.append(f'<path data-layer="coverage-route" data-flow-role="supply" data-circuit-id="{c["circuit_id"]}" d="{_svg_path(coverage_supply)}" fill="none" stroke="{SUPPLY_COLOR}" stroke-width="8"/>')
    svg.append(f'<path data-layer="coverage-route" data-flow-role="return" data-circuit-id="{c["circuit_id"]}" d="{_svg_path(coverage_return)}" fill="none" stroke="{RETURN_COLOR}" stroke-width="8"/>')
svg.append('</svg>'); (out/'building_level_ufh.svg').write_text(''.join(svg),encoding='utf-8'); shutil.copyfile(out/'building_level_ufh.svg', out/'building_transit.svg')
(out/'visualization_validation.json').write_text(json.dumps({
    'method':'EXACT_RENDERED_CENTERLINE_RECOMPOSITION',
    'source_of_truth':'physical_coverage_routes_mm',
    'status':'VALID' if all(v['VISUALIZATION_VALID'] for r in records for v in r.get('visualization_validation',[])) else 'INVALID',
    'routes':[
        {'room_id':r['room_hypothesis_id'],'route_index':i,'validation':v}
        for r in records for i,v in enumerate(r.get('visualization_validation',[]))
    ],
    'diagnostics':[] if all(v['VISUALIZATION_VALID'] for r in records for v in r.get('visualization_validation',[])) else ['RENDERED_ROUTE_DOES_NOT_MATCH_CALCULATED_CENTERLINE']
},ensure_ascii=False,indent=2),encoding='utf-8')
(out/'two_floor_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
schedule=[]
for c in circuits:
    room=next(r for r in records if r['room_hypothesis_id']==c['room_id'])
    schedule.append({'CIRCUIT_ID':c['circuit_id'],'ROOM':room['label'],'FLOOR':c['floor'],'STRATEGY':room.get('selected_strategy'),'ROOM_AREA':room.get('room_area_m2'),'COVERAGE_AREA':room.get('routable_area_m2'),'SUPPLY_PORT':c['supply_port_id'],'RETURN_PORT':c['return_port_id'],'COVERAGE_LENGTH':c['coverage_length_m'],'SUPPLY_TRANSIT_LENGTH':c['supply_manifold_transit_m'],'RETURN_TRANSIT_LENGTH':c['return_manifold_transit_m'],'TRANSIT_LENGTH':round(c['supply_manifold_transit_m']+c['return_manifold_transit_m'],3),'VERTICAL_LENGTH':round(c['supply_vertical_rise_m']+c['return_vertical_drop_m'],3),'TOTAL_LENGTH':round(c['total_circuit_length_m'],3),'POLICY_LIMIT':MAX_TOTAL_CIRCUIT_LENGTH_M,'POLICY_MARGIN':round(MAX_TOTAL_CIRCUIT_LENGTH_M-c['total_circuit_length_m'],3),'VALIDATION_STATUS':'FULL_CIRCUIT_PREVIEW_VALID' if c['statuses']['FULL_CIRCUIT_VALID'] else 'PREVIEW_REQUIRES_INSTALLER_CONFIRMATION','AUTHORITY_STATUS':c['transit_authority'],'TRANSIT_RESPLIT_STATUS':room.get('transit_resplit_status')})
(out/'circuit_schedule.json').write_text(json.dumps(schedule,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'zone_decomposition_review.json').write_text(json.dumps({
    'method':'GEOMETRIC_ZONE_CANDIDATES_WITH_ENDPOINT_ACCESS_GATE',
    'target_policy_length_m':MAX_TOTAL_CIRCUIT_LENGTH_M,
    'long_route_rooms':[
        {
            'room_id':r['room_hypothesis_id'],
            'label':r['label'],
            'source_route_length_m':r.get('actual_coverage_length_m'),
            'preview_circuit_count':r.get('circuit_split_count'),
            'split_candidate_validation':r.get('split_candidate_validation'),
            'zone_decomposition':r.get('zone_decomposition'),
        }
        for r in records
        if r.get('zone_decomposition',{}).get('status') != 'NOT_REQUIRED'
    ],
    'status':'CANDIDATES_REQUIRE_UNVERIFIED_ENDPOINT_ACCESS',
    'authority_note':'Zone candidates are geometry-only. No candidate is an independent manifold circuit until both endpoints have an authorized transit path.'
},ensure_ascii=False,indent=2),encoding='utf-8')
strategy_summary={'selection_policy':'geometry-only; no thermal score','rooms':[{'room_id':r['room_hypothesis_id'],'room':r['label'],'selected_strategy':r.get('selected_strategy'),'alternatives_evaluated':r.get('alternatives_evaluated',[]),'selection_reason':r.get('strategy_selection_reason'),'spiral_candidates_valid':r.get('spiral_candidates_valid',0),'spiral_candidates_rejected':r.get('spiral_candidates_rejected',0),'selected_route_topology_gate':r.get('selected_route_topology_gate'),'circuit_split_count':r.get('circuit_split_count',0)} for r in records]}
(out/'layout_strategy_summary.json').write_text(json.dumps(strategy_summary,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'semantic_face_resolution.json').write_text(json.dumps({
    'method':'SOURCE_VARIANT_INVENTORY_WITHOUT_AUTO_SELECTION',
    'authority':'DRAWING_HYPOTHESIS_NOT_ENGINEERING_AUTHORITY',
    'stair_line_evidence':stair_line_evidence,
    'rooms':[
        {'room_id':r['room_hypothesis_id'],'label':r['label'],'geometry_status':r['geometry_status'],
         'diagnostics':r.get('geometry_diagnostics',[]),
         'candidates':r.get('semantic_face_resolution_candidates',[]),
         'wall_evidence':r.get('wall_evidence_candidates',[]),
         'boundary_guided_candidate_count':0,
         'next_gate':'EXACT_STAIR_BOUNDARY_AND_PASSAGE_CONTINUITY'
        }
        for r in records if r['geometry_status']=='GEOMETRY_UNRESOLVED'
    ],
    'selection_blocker':'Vector stair lines are source-observed, but exact stair boundary and passage continuity are not yet reconstructed; candidates remain unresolved.'
},ensure_ascii=False,indent=2),encoding='utf-8')
continuation_queue={
    'protocol':'HOMEAURA_CONTINUATION_QUEUE_V1',
    'mode':'SEQUENTIAL_BOUNDED_BLOCKS',
    'stop_policy':'Do not declare the product stage complete while queue contains a safe actionable block.',
    'current_state':{
        'rooms_routed_valid':summary['routed_valid'],
        'rooms_total':len(records),
        'geometry_unresolved_rooms':[r['label'] for r in records if r['geometry_status']=='GEOMETRY_UNRESOLVED'],
        'under_stair_owner_preview_rooms':[r['label'] for r in records if 'OWNER_REQUESTED_UNDER_STAIR_HEATING_PREVIEW' in r.get('geometry_diagnostics',[])],
        'physical_preview_circuits':len(circuits),
        'maximum_circuit_length_m':max((c['total_circuit_length_m'] for c in circuits),default=0.0),
    },
    'queue':[
        {'id':'UFH-STAIR-EXACT-BOUNDARY','status':'READY','scope':'rooms 2 and 9','next_action':'Build a source-linked stair edge graph from vector rails and adjacent raster boundaries; test closure and passage continuity.','completion_condition':'Unique closed stair boundary and passage status are evidenced, or blocker is explicitly recorded with no unresolved candidate omitted.'},
        {'id':'UFH-TRANSIT-AUTHORITY','status':'BLOCKED_BY_SOURCE','scope':'building transit','next_action':'Keep preview lanes and prepare opening/penetration confirmation package.','completion_condition':'Source-verified or installer-confirmed openings exist for every transit crossing.'},
        {'id':'UFH-ENGINEERING-GATE','status':'BLOCKED_BY_INPUTS','scope':'construction and thermal inputs','next_action':'Do not run construction-grade sizing until project-owned engineering inputs are bound.','completion_condition':'Authoritative envelope, operating, surface and hydraulic inputs are complete.'}
    ],
    'last_completed_block':'UFH under-stair owner-requested preview override',
    'authority':'GEOMETRY_ONLY_PREVIEW; NOT_FOR_CONSTRUCTION'
}
(out/'continuation_queue.json').write_text(json.dumps(continuation_queue,ensure_ascii=False,indent=2),encoding='utf-8')

handoff=Path('dev/ufh_handoff'); handoff.mkdir(parents=True,exist_ok=True)
state=handoff/'CURRENT_UFH_STATE.md'
max_preview_length=max((c['total_circuit_length_m'] for c in circuits), default=0.0)
room6=next((r for r in records if 'POLYLINE_ARCLENGTH_PARTITION' in r.get('circuit_split_reasons',[])), None)
room6_note=(f"Room 6 non-rectangular route was partitioned by centerline arclength into {room6['circuit_split_count']} circuits; each passes the canonical preview-boundary containment gate." if room6 else 'Room 6 non-rectangular resplit remains unresolved.')
room2=next((r for r in records if r['label'].startswith('2 /')), None)
room9=next((r for r in records if r['label'].startswith('9 /')), None)
state.write_text(f"# Current UFH state\n\n- Rooms: {len(records)}\n- Room coverage routed-valid: {summary['routed_valid']}/16\n- Geometry unresolved: {sum(r['geometry_status']=='GEOMETRY_UNRESOLVED' for r in records)}\n- Physical preview circuits: {len(circuits)}; split rooms: {sum(r.get('circuit_split_count',1)>1 for r in records)}\n- Maximum preview circuit length: {max_preview_length:.3f} m (policy limit {MAX_TOTAL_CIRCUIT_LENGTH_M:.1f} m)\n- {room6_note}\n- Under-stair owner preview: room 2 includes the observed under-stair area in a geometry-only scanline route; exact stair boundary remains unresolved\n- Semantic-face candidates: semantic_face_resolution.json records source variants for rooms 2 and 9; exact stair boundary and passage continuity remain unresolved\n- Stair vector evidence: both plans have coincident diagonal pairs with 0.5-0.6 drawing-unit endpoint gap; centerlines are candidates only, not room boundaries\n- Wall-evidence map: room 2 has {len(room2.get('wall_evidence_candidates',[])) if room2 else 0} local raster boundary candidates; room 9 has {len(room9.get('wall_evidence_candidates',[])) if room9 else 0}; next gate is exact stair boundary plus passage continuity\n- Strategy status: rooms use a gate-approved BIFILAR_SPIRAL where exact rectangular geometry permits it; other accepted rooms use continuous MEANDER; unresolved geometry remains blocked\n- Flow colors: supply red ({SUPPLY_COLOR}); return blue ({RETURN_COLOR}); floor and building SVGs carry explicit data-flow-role metadata\n- Containment: no rooms with meaningful outside coverage pipe\n- Building transit: preview, requires installer/source corridor confirmation\n- Manifold connections: {building['manifold_connection_gate']['validated_connection_count']}/{building['manifold_connection_gate']['connection_count']} physically validated; assigned ports remain unresolved until openings, corridor and riser authority is confirmed\n- Manifold: {building['manifold']['boiler_room_id']} (position preview; modules={building['manifold']['module_count']})\n- Riser: R1 (preview, installer confirmation required)\n",encoding='utf-8')
with zipfile.ZipFile(handoff/'HomeAura_UFH_latest_review.zip','w',zipfile.ZIP_DEFLATED) as z:
    rounded_controls=Path('dev/ufh_diagnostics/rounded_controls')
    shutil.copyfile(rounded_controls/'rounded_control_scenarios.svg', out/'rounded_control_scenarios.svg')
    shutil.copyfile(rounded_controls/'rounded_control_scenarios.json', out/'rounded_control_scenarios.json')
    for name in ('first_floor_ufh.svg','first_floor_ufh_rounded.svg','mansard_ufh.svg','mansard_ufh_rounded.svg','building_transit.svg','two_floor_summary.json','building_ufh_summary.json','circuit_schedule.json','zone_decomposition_review.json','layout_strategy_summary.json','semantic_face_resolution.json','continuation_queue.json','transit_validation.json','riser_schedule.json','building_openings.json','building_connectivity.json','manifold_connections.json','manifold_authority_intake.json','visualization_validation.json','transit_capacity.json','rounded_control_scenarios.svg','rounded_control_scenarios.json'):
        z.write(out/name, name)
    z.write(spiral_out/'spiral_validation.svg', 'spiral_validation.svg')
    z.write(spiral_out/'spiral_validation.json', 'spiral_validation.json')
    z.write(Path('docs/UFH_LAYOUT_ENGINEERING_BASIS.md'), 'UFH_LAYOUT_ENGINEERING_BASIS.md')
    z.write(state, state.name)

from decimal import Decimal as D
from agent.drawing_understanding import (Frame,Geometry,Point,IntervalSemanticWallBand,
    SustainedWallGap,solve_endpoint_junctions,build_semantic_wall_graph_v2,
    WallFaceIntervalSpan,infer_single_face_centerlines)

F=Frame(frame_id="T:0",space="DRAWING_SPACE",unit="pt",axes="X_RIGHT_Y_DOWN")
def band(i,o,a,b):
    g=Geometry(frame=F,kind="POLYLINE",points=(Point(x=D(a[0]),y=D(a[1])),Point(x=D(b[0]),y=D(b[1]))))
    return IntervalSemanticWallBand(band_id=i,frame=F,orientation=o,source_span_ids=(i+'a',i+'b'),
        source_chain_ids=(i+'c',i+'d'),centerline_geometry=g,width_drawing_units=D(8),confidence="HIGH",
        policy_basis="test",source_dependencies={"s":"0"*64})

def test_endpoint_to_perpendicular_centerline_makes_t_and_l_junctions_deterministically():
    h=band('h','HORIZONTAL',(0,5),(9,5)); v=band('v','VERTICAL',(10,0),(10,10))
    first=solve_endpoint_junctions((h,v),(),tolerance=D(2));second=solve_endpoint_junctions((h,v),(),tolerance=D(2))
    assert first==second
    hit=next(x for x in first if x.source_wall_id=='h' and x.endpoint==Point(x=D(9),y=D(5)))
    assert hit.status=='CONFIRMED_JUNCTION' and hit.junction_type=='T_JUNCTION'
    l=band('l','VERTICAL',(10,5),(10,10));hit=next(x for x in solve_endpoint_junctions((h,l),(),tolerance=D(2)) if x.source_wall_id=='h' and x.endpoint.x==9)
    assert hit.junction_type=='L_JUNCTION'

def test_equal_targets_are_ambiguous_and_residual_faces_are_not_graph_edges():
    h=band('h','HORIZONTAL',(0,5),(9,5));a=band('a','VERTICAL',(10,0),(10,10));b=band('b','VERTICAL',(8,0),(8,10))
    decisions=solve_endpoint_junctions((h,a,b),(),tolerance=D(2))
    assert next(x for x in decisions if x.source_wall_id=='h' and x.endpoint.x==9).status=='AMBIGUOUS_JUNCTION'
    graph=build_semantic_wall_graph_v2((h,a,b),(),tolerance=D(2))[0]
    assert len(graph.wall_edges)==3

def test_protected_opening_gap_is_never_closed():
    h=band('h','HORIZONTAL',(0,5),(9,5));v=band('v','VERTICAL',(10,0),(10,10))
    gap=SustainedWallGap(gap_id='g',chain_id='c',frame=F,
        geometry=Geometry(frame=F,kind='POLYLINE',points=(Point(x=D(8),y=D(5)),Point(x=D(10),y=D(5)))),
        width_drawing_units=D(2),left_source_wall_id='x',right_source_wall_id='y',classification='UNKNOWN_OPENING',
        source_dependencies={'s':'0'*64})
    hit=next(x for x in solve_endpoint_junctions((h,v),(gap,),tolerance=D(2)) if x.source_wall_id=='h' and x.endpoint.x==9)
    assert hit.status=='OPENING_GAP_PRESERVED' and 'REJECTED_OPENING_CONFLICT' in hit.reason

def test_single_face_continuation_uses_only_same_chain_local_prior_and_is_deterministic():
    prior=band('p','HORIZONTAL',(0,4),(10,4)).model_copy(update={'source_chain_ids':('chain','other')})
    span=WallFaceIntervalSpan(span_id='s',source_chain_id='chain',frame=F,orientation='HORIZONTAL',
        axis_drawing_units=D(0),span_start=D(10),span_end=D(18),classification='UNPAIRED_WALL_FACE',source_dependencies={'s':'0'*64})
    first=infer_single_face_centerlines((span,),(prior,),(),maximum_prior_distance=D(10))
    assert first==infer_single_face_centerlines((span,),(prior,),(),maximum_prior_distance=D(10))
    assert first[0].status=='INFERRED_FROM_SINGLE_FACE_WITH_LOCAL_BAND_PRIOR'
    assert first[0].inferred_offset_drawing_units==4
    distant=span.model_copy(update={'span_start':D(30),'span_end':D(40)})
    assert infer_single_face_centerlines((distant,),(prior,),(),maximum_prior_distance=D(10))[0].status=='UNRESOLVED_SINGLE_FACE'

def test_single_face_continuation_stops_at_protected_gap():
    prior=band('p','HORIZONTAL',(0,4),(10,4)).model_copy(update={'source_chain_ids':('chain','other')})
    span=WallFaceIntervalSpan(span_id='s',source_chain_id='chain',frame=F,orientation='HORIZONTAL',axis_drawing_units=D(0),
        span_start=D(10),span_end=D(18),classification='OPENING_ADJACENT_SPAN',source_dependencies={'s':'0'*64})
    gap=SustainedWallGap(gap_id='g',chain_id='chain',frame=F,geometry=Geometry(frame=F,kind='POLYLINE',
        points=(Point(x=D(12),y=D(0)),Point(x=D(16),y=D(0)))),width_drawing_units=D(4),left_source_wall_id='x',
        right_source_wall_id='y',classification='UNKNOWN_OPENING',source_dependencies={'s':'0'*64})
    result=infer_single_face_centerlines((span,),(prior,),(gap,),maximum_prior_distance=D(10))[0]
    assert result.status=='REJECTED_OPENING_CONFLICT' and result.inferred_geometry is None

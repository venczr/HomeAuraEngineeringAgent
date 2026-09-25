"""Non-engineering per-room routing experiment for verified Test_01 drawings."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Literal

from agent.drawing_understanding import Geometry, digest
from agent.floor_heating_engine import calculate_floor_heating
from agent.floor_heating_models import FloorHeatingRequest
from agent.project_models import StrictProjectModel
from agent.test01_drawing_understanding import reconstruct_test01_room_candidates
from agent.ufh_layout_engine import build_polygon_meander, validate_containment


class RoomGeometryRoutingPreview(StrictProjectModel):
    room_hypothesis_id: str
    floor_source_id: str
    label: str
    geometry_status: Literal["USABLE", "GEOMETRY_UNRESOLVED"]
    routing_attempted: bool
    routing_status: Literal["ROUTED_VALID", "ROUTE_GENERATED_BUT_INVALID", "GENERATED", "FAILED", "SKIPPED_GEOMETRY_UNRESOLVED"]
    candidate_circuit_count: int = 0
    candidate_lengths_mm: tuple[int, ...] = ()
    coverage: Decimal | None = None
    geometry_diagnostics: tuple[str, ...] = ()
    legacy_policy_status: Literal["NOT_EVALUATED_FOR_GEOMETRY_PREVIEW", "WOULD_ACCEPT", "WOULD_REJECT"]
    route_polylines_mm: tuple[tuple[tuple[int, int], ...], ...] = ()
    floor_global_route_polylines_mm: tuple[tuple[tuple[int, int], ...], ...] = ()
    floor_global_boundary_mm: tuple[tuple[int, int], ...] = ()
    room_area_m2: Decimal | None = None
    routable_area_m2: Decimal | None = None
    expected_length_order_m: Decimal | None = None
    actual_coverage_length_m: Decimal | None = None
    length_ratio: Decimal | None = None
    coverage_percent: Decimal | None = None
    validation_status: str = "NOT_EVALUATED"
    floor_transform: tuple[Decimal, Decimal, Decimal] | None = None
    authority: Literal["GEOMETRY_ONLY_NON_ENGINEERING_NOT_FOR_CONSTRUCTION"] = "GEOMETRY_ONLY_NON_ENGINEERING_NOT_FOR_CONSTRUCTION"


class Test01GeometryOnlyUFHPreview(StrictProjectModel):
    status: Literal["COMPLETED"] = "COMPLETED"
    spacing_mm: Literal[200] = 200
    spacing_policy: Literal["VISUAL_TEST_POLICY_NOT_ENGINEERING_DESIGN_INPUT"] = "VISUAL_TEST_POLICY_NOT_ENGINEERING_DESIGN_INPUT"
    rooms: tuple[RoomGeometryRoutingPreview, ...]
    first_floor_preview_path: str
    mansard_preview_path: str
    engineering_calculations_run: Literal[False] = False
    digest: str


def _area(points):
    return abs(sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1]
                   for i in range(len(points))))/Decimal(2)


def _interior_collector(polygon: list[tuple[int,int]], wall_offset: int = 100) -> tuple[int,int]:
    body=polygon[:-1]
    def inside(point):
        x,y=point;hit=False
        for (x1,y1),(x2,y2) in zip(polygon,polygon[1:]):
            if (y1>y)!=(y2>y) and x < x1+(y-y1)*(x2-x1)/(y2-y1):hit=not hit
        return hit
    def clearance(point):
        x,y=point;values=[]
        for (x1,y1),(x2,y2) in zip(polygon,polygon[1:]):
            values.append(abs(y-y1) if y1==y2 and min(x1,x2)<=x<=max(x1,x2) else
                          abs(x-x1) if x1==x2 and min(y1,y2)<=y<=max(y1,y2) else 10**9)
        return min(values)
    xs=[x for x,_ in body];ys=[y for _,y in body]
    candidates=((x,y) for y in range(min(ys)+wall_offset,max(ys)-wall_offset+1,100)
               for x in range(min(xs)+wall_offset,max(xs)-wall_offset+1,100))
    valid=[p for p in candidates if inside(p) and clearance(p)>=wall_offset]
    if not valid:return (min(xs)+wall_offset,min(ys)+wall_offset)
    # Prefer an accessible point near the upper-left while retaining clearance.
    return min(valid,key=lambda p:(p[0]+p[1],-clearance(p),p))


def _preview_polygon(geometry: Geometry, scale: Decimal) -> tuple[list[tuple[int,int]] | None, tuple[str,...]]:
    pts=[(p.x,p.y) for p in geometry.points]
    x0,x1=min(x for x,_ in pts),max(x for x,_ in pts); y0,y1=min(y for _,y in pts),max(y for _,y in pts)
    polygon_area=_area(pts); bbox_area=(x1-x0)*(y1-y0)
    diagnostics=[]
    if bbox_area and (bbox_area-polygon_area)/bbox_area <= Decimal("0.035"):
        chosen=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
        diagnostics.append("CONSERVATIVE_RASTER_NOTCH_SIMPLIFICATION_TO_ORTHOGONAL_ENVELOPE")
    else:
        # Collapse sub-point raster stair-steps and a one-run backtracking spike;
        # the 1 pt tolerance is bounded by the perception contour diagnostic.
        values=[]
        for axis in (0,1):
            ordered=sorted({p[axis] for p in pts}); clusters=[]
            for value in ordered:
                if clusters and value-clusters[-1][-1] <= Decimal(1): clusters[-1].append(value)
                else: clusters.append([value])
            values.append({value:sum(group)/len(group) for group in clusters for value in group})
        chosen=[(values[0][x],values[1][y]) for x,y in pts]
        changed=True
        while changed and len(chosen)>4:
            changed=False
            for i in range(len(chosen)):
                a,b,c=chosen[i-1],chosen[i],chosen[(i+1)%len(chosen)]
                if (a[0]==b[0]==c[0]) or (a[1]==b[1]==c[1]) or a[0]==c[0] or a[1]==c[1]:
                    chosen.pop(i);changed=True;break
        diagnostics.append("RASTER_CONTOUR_CLEANUP_WITHIN_ONE_DRAWING_POINT")
    mm=lambda v:int((v*scale*1000).to_integral_value(rounding=ROUND_HALF_UP))
    # Router coordinates are room-local and must remain non-negative. Using
    # the first contour vertex as origin made valid concave faces negative.
    ox=min(x for x,_ in chosen);oy=min(y for _,y in chosen)
    converted=[(mm(x-ox),mm(y-oy)) for x,y in chosen]
    signed=sum(converted[i][0]*converted[(i+1)%len(converted)][1]-converted[(i+1)%len(converted)][0]*converted[i][1]
               for i in range(len(converted)))
    if signed < 0:
        converted.reverse()
        diagnostics.append("CANONICAL_COUNTERCLOCKWISE_ROUTER_ORIENTATION")
    if converted[-1] != converted[0]: converted.append(converted[0])
    return converted,tuple(diagnostics)


def _globalize(points, origin_x, origin_y, scale):
    return tuple((int((origin_x + Decimal(x) / Decimal(1000) / scale).to_integral_value(rounding=ROUND_HALF_UP)),
                  int((origin_y + Decimal(y) / Decimal(1000) / scale).to_integral_value(rounding=ROUND_HALF_UP)))
                 for x, y in points)


def _render(project: Path, understanding, previews, floor_id: str, output: Path) -> None:
    import pymupdf
    from PIL import Image,ImageDraw
    document=next(d for d in understanding["package"].documents if d.document_id==floor_id)
    with pymupdf.open(project/document.archived_path) as pdf:
        pix=pdf[0].get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False)
    image=Image.frombytes("RGB",(pix.width,pix.height),pix.samples); draw=ImageDraw.Draw(image,"RGBA")
    hypotheses=understanding["hypotheses"]
    scales=understanding["scales"]
    scale=next(s.scale_m_per_drawing_unit for s in scales if s.frame.frame_id.startswith(floor_id))
    colors=((230,35,80,210),(0,130,220,210),(30,170,80,210),(150,70,210,210))
    for index,item in enumerate(p for p in previews if p.floor_source_id==floor_id):
        geometry=hypotheses[item.room_hypothesis_id].geometry
        x0=min(p.x for p in geometry.points); y0=min(p.y for p in geometry.points)
        if item.routing_status=="GENERATED":
            for circuit,polyline in enumerate(item.route_polylines_mm):
                points=[(float((x0+Decimal(x)/1000/scale)*2),float((y0+Decimal(y)/1000/scale)*2)) for x,y in polyline]
                draw.line(points,fill=colors[index%len(colors)],width=2)
        else:
            xs=[float(p.x*2) for p in geometry.points]; ys=[float(p.y*2) for p in geometry.points]
            draw.rectangle((min(xs),min(ys),max(xs),max(ys)),outline=(255,120,0,220),width=3)
        draw.text((float(x0*2+3),float(y0*2+3)),item.label.split(";")[0],fill=(20,20,20,255))
    output.parent.mkdir(parents=True,exist_ok=True); image.save(output)


def build_test01_geometry_only_ufh_preview(project: Path, output_directory: Path) -> Test01GeometryOnlyUFHPreview:
    from agent.test01_pdf_project_source_ingestion import load_test01_pdf_project_source_ingestion
    drawing=reconstruct_test01_room_candidates(project)
    hypotheses={h.hypothesis_id:h for h in drawing.understanding.hypotheses}
    scales={s.frame.frame_id:s.scale_m_per_drawing_unit for s in drawing.scale_candidates}
    previews=[]
    geometry_status={a.room_hypothesis_id:a for a in drawing.room_geometry_evidence_assessments}
    for room in drawing.building_rooms:
        assessment=geometry_status[room.room_hypothesis_id]
        if assessment.geometry_status!="USABLE_DRAWING_HYPOTHESIS":
            # The owner explicitly requested heating under the first-floor
            # stair. The observed room-2 contour already contains that area;
            # bypass only the approximate stair-bbox exclusion for a preview
            # route, while retaining the unresolved geometry authority.
            under_stair_preview = (
                room.floor_source_id == "FLOOR_1_PLAN"
                and room.label_text.startswith("2 /")
                and "STAIR_EXCLUSION_REGION_OVERLAP" in assessment.diagnostics
            )
            if under_stair_preview:
                geometry=hypotheses[room.room_hypothesis_id].geometry
                scale=scales[geometry.frame.frame_id]
                polygon,polygon_diagnostics=_preview_polygon(geometry,scale)
                route=build_polygon_meander(polygon or [],200,100)
                containment=validate_containment(route,polygon or []) if route and polygon else None
                generated=bool(route and containment and containment.valid and len(route)>=2)
                previews.append(RoomGeometryRoutingPreview(
                    room_hypothesis_id=room.room_hypothesis_id,
                    floor_source_id=room.floor_source_id,
                    label=room.label_text,
                    geometry_status="GEOMETRY_UNRESOLVED",
                    routing_attempted=True,
                    routing_status="GENERATED" if generated else "FAILED",
                    candidate_circuit_count=1 if generated else 0,
                    candidate_lengths_mm=(int(round(sum(((b[0]-a[0])**2+(b[1]-a[1])**2)**0.5 for a,b in zip(route,route[1:])))),) if generated else (),
                    # This stage draws a route but does not measure the
                    # rounded pipe-band area. Keep coverage unknown.
                    coverage=None,
                    geometry_diagnostics=("OWNER_REQUESTED_UNDER_STAIR_HEATING_PREVIEW",)+tuple(polygon_diagnostics)+tuple(assessment.diagnostics),
                    legacy_policy_status="WOULD_REJECT" if generated else "NOT_EVALUATED_FOR_GEOMETRY_PREVIEW",
                    route_polylines_mm=(tuple(route),) if generated else (),
                ))
                continue
            previews.append(RoomGeometryRoutingPreview(room_hypothesis_id=room.room_hypothesis_id,
                floor_source_id=room.floor_source_id,label=room.label_text,geometry_status="GEOMETRY_UNRESOLVED",
                routing_attempted=False,routing_status="SKIPPED_GEOMETRY_UNRESOLVED",
                geometry_diagnostics=("SEMANTIC_FACE_UNRESOLVED",)+assessment.diagnostics,legacy_policy_status="NOT_EVALUATED_FOR_GEOMETRY_PREVIEW"))
            continue
        geometry=hypotheses[room.room_hypothesis_id].geometry; scale=scales[geometry.frame.frame_id]
        polygon,diagnostics=_preview_polygon(geometry,scale)
        diagnostics=diagnostics+assessment.diagnostics
        if polygon is None:
            previews.append(RoomGeometryRoutingPreview(room_hypothesis_id=room.room_hypothesis_id,
                floor_source_id=room.floor_source_id,label=room.label_text,geometry_status="USABLE",routing_attempted=True,
                routing_status="FAILED",geometry_diagnostics=diagnostics,legacy_policy_status="NOT_EVALUATED_FOR_GEOMETRY_PREVIEW"))
            continue
        xs=[x for x,_ in polygon[:-1]];ys=[y for _,y in polygon[:-1]]
        request=FloorHeatingRequest.model_validate({"project_id":"Test_01","room_id":room.room_hypothesis_id,
            "boundary":{"points":[{"x_mm":x,"y_mm":y} for x,y in polygon]},"exclusion_zones":[],
            "collector_point":dict(zip(("x_mm","y_mm"),_interior_collector(polygon))),"wall_offset_mm":100,"spacing_mm":200,
            "minimum_circuit_length_mm":1,"maximum_circuit_length_mm":500000,"requested_circuit_count":1,
            "routing_mode":"non_crossing_visual","field_spacing_mm":200,"perimeter_spacing_mm":100,
            "perimeter_band_depth_mm":1000,"perimeter_priority_mode":True})
        result=calculate_floor_heating(request)
        routes=tuple(tuple((p.x_mm,p.y_mm) for p in route.polyline) for route in result.circuit_routes)
        lengths=tuple(route.length_mm for route in result.circuit_routes)
        legacy="WOULD_ACCEPT" if lengths and all(40000<=v<=80000 for v in lengths) else "WOULD_REJECT"
        validation=all(route.validation.inside_boundary and not route.validation.self_intersection for route in result.circuit_routes)
        generated=result.status=="ok" and validation
        previews.append(RoomGeometryRoutingPreview(room_hypothesis_id=room.room_hypothesis_id,
            floor_source_id=room.floor_source_id,label=room.label_text,geometry_status="USABLE",routing_attempted=True,
            routing_status="GENERATED" if generated else "FAILED",candidate_circuit_count=len(routes),
            candidate_lengths_mm=lengths,coverage=None,
            geometry_diagnostics=diagnostics+tuple(d.code for d in result.diagnostics),legacy_policy_status=legacy,
            route_polylines_mm=routes))
    package=load_test01_pdf_project_source_ingestion(project)
    context={"package":package,"hypotheses":hypotheses,"scales":drawing.scale_candidates}
    first=output_directory/"test01_first_floor_geometry_only_ufh_preview.png"
    attic=output_directory/"test01_mansard_geometry_only_ufh_preview.png"
    _render(project,context,previews,"FLOOR_1_PLAN",first);_render(project,context,previews,"ATTIC_PLAN",attic)
    body={"rooms":[p.model_dump(mode="json") for p in previews],"first":str(first),"attic":str(attic),"spacing":200}
    return Test01GeometryOnlyUFHPreview(rooms=tuple(previews),first_floor_preview_path=str(first),
        mansard_preview_path=str(attic),digest=digest(body))

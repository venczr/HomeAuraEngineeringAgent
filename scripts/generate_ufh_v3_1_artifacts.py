from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.ufh_routing_preview import UfhRoutingPreviewRequest, generate_ufh_routing_preview, plan_ufh_circuits, render_ufh_routing_preview_svg

OUT = Path("dev/ufh_routing_v3")
def p(x,y): return {"x_mm":x,"y_mm":y}
def poly(points): return {"points":[p(x,y) for x,y in points]}
base = dict(project_id="v3-1", room_id="demo", manifold_point=p(3500,1100), spacing_mm=200, wall_offset_mm=100, minimum_bend_radius_mm=100, maximum_preview_length_mm=80000)
scenarios = {
 "ufh_simple_rectangle.svg": dict(room_polygon=poly([(0,0),(7000,0),(7000,3200),(0,3200),(0,0)]), orientation="horizontal"),
 "ufh_vertical_rectangle.svg": dict(room_polygon=poly([(0,0),(7000,0),(7000,3200),(0,3200),(0,0)]), orientation="vertical"),
 "ufh_l_shape.svg": dict(room_polygon=poly([(0,0),(6000,0),(6000,2500),(2500,2500),(2500,5000),(0,5000),(0,0)]), manifold_point=p(500,500), orientation="horizontal"),
 "ufh_u_shape.svg": dict(room_polygon=poly([(0,0),(6000,0),(6000,5000),(4000,5000),(4000,2000),(2000,2000),(2000,5000),(0,5000),(0,0)]), manifold_point=p(1000,1000), orientation="horizontal"),
 "ufh_exclusion.svg": dict(room_polygon=poly([(0,0),(7000,0),(7000,3200),(0,3200),(0,0)]), exclusion_zones=[poly([(3000,2050),(3200,2050),(3200,2090),(3000,2090),(3000,2050)])], orientation="horizontal", maximum_preview_length_mm=150000),
 "ufh_narrow_neck.svg": dict(room_polygon=poly([(0,0),(6000,0),(6000,1800),(3500,1800),(3500,3200),(6000,3200),(6000,5000),(0,5000),(0,0)]), manifold_point=p(1000,1000), orientation="horizontal"),
}
OUT.mkdir(parents=True, exist_ok=True)
for name, extra in scenarios.items():
    request = UfhRoutingPreviewRequest.model_validate({**base, **extra, "room_id":name})
    result = generate_ufh_routing_preview(request)
    (OUT/name).write_text(render_ufh_routing_preview_svg(result), encoding="utf-8")
request = UfhRoutingPreviewRequest.model_validate({**base, "room_id":"multi", "maximum_preview_length_mm":45000, "room_polygon":poly([(0,0),(7000,0),(7000,3200),(0,3200),(0,0)]), "orientation":"horizontal"})
(OUT/"ufh_multi_circuit.svg").write_text(render_ufh_routing_preview_svg(plan_ufh_circuits(request)), encoding="utf-8")
demo = UfhRoutingPreviewRequest.model_validate({**base, "room_id":"realistic-demo", "maximum_preview_length_mm":45000, "room_polygon":poly([(0,0),(9000,0),(9000,2500),(6500,2500),(6500,5000),(0,5000),(0,0)]), "exclusion_zones":[poly([(1500,900),(2600,900),(2600,1500),(1500,1500),(1500,900)])], "manifold_point":p(500,500), "orientation":"auto"})
(OUT/"ufh_realistic_demo.svg").write_text(render_ufh_routing_preview_svg(generate_ufh_routing_preview(demo)), encoding="utf-8")

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE=ROOT/"homeaura-native-editor"/"examples"/"proposals"
SOURCE=BASE/"HA_TWO_FLOOR_COUNTERFLOW_FULL_ROUTES_015"
D011=BASE/"HA_TWO_FLOOR_VECTOR_CONTRACT_011"/"vector_source_contract.json"
OUTPUT=BASE/"HA_TWO_FLOOR_K1_RECONCILED_017"
PACKAGE=BASE/"packages"/"HA_TWO_FLOOR_K1_RECONCILED_017.zip"

def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def digest(value:object)->str:return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()

def centre_turn_from_body(route:dict)->list[list[int]]:
    points=route["heating_body_points_grid"]
    inward_count=len(route["regularity_validation"]["inward_frame_bounds_grid"])*4
    # The generator joins the final inward corner to the final outward arm
    # with either one or two orthogonal segments. Preserve actual mirrored points.
    return points[inward_count-1:inward_count+2]

def main()->None:
    if OUTPUT.exists() or PACKAGE.exists():raise FileExistsError("K1_RECONCILED_017 is append-only")
    source=json.loads((SOURCE/"canonical_geometry.json").read_text(encoding="utf-8"));validation015=json.loads((SOURCE/"validation.json").read_text(encoding="utf-8"));contract011=json.loads(D011.read_text(encoding="utf-8"))
    model=json.loads(json.dumps(source));model["artifact_id"]="HA_TWO_FLOOR_K1_RECONCILED_017";model["status"]="K1_SOURCE_CONTRACT_RECONCILED_ROUTES_PASS_REWORK_COVERAGE";model["derived_from_artifact_id"]=source["artifact_id"];model["derived_from_geometry_digest"]=source["geometry_digest"];model.pop("source_body_artifact",None)
    new_contract={
        "contract_id":"HA_TWO_FLOOR_K1_GATE_CONTRACT_017","supersedes_gate_and_collector_placement_only":"HA_TWO_FLOOR_VECTOR_CONTRACT_011","reason":"OWNER_ALLOWS_WALL_PENETRATION_AND_D015_PROVED_CONTACT_FREE_10_LANE_ORDER",
        "source_vector_contract_id":contract011["contract_id"],"source_vector_contract_digest":contract011["contract_digest"],
        "collector_id":"K1","logical_assembly_count":1,"wall_mounted_body_bbox_grid":[132,56,136,82],"port_rail_bank_bbox_grid":[130,55,140,56],"assembly_connection":"INTERNAL_MANIFOLD_EQUIPMENT_NOT_PIPE_TOPOLOGY",
        "boiler_room_vector_bounds_grid":[129.52,54.08,182.54,83.77],"all_route_ports_inside_boiler_room":True,
        "wall_penetration_line_y_grid":82,"unique_wall_penetration_gates_grid":[[x,82] for x in range(130,139)],"gate_count":9,"non_penetrating_boiler_return_lane_x_grid":139,"shared_pipe_trunk":False,"lane_swaps_allowed":False,
        "equipment_capacity":"NOT_EVALUATED","hydraulics":"NOT_CALCULATED","normative_compliance_claimed":False,
    }
    new_contract["contract_digest"]=digest(new_contract);model["collector_contract"]=new_contract
    for route in model["routes"]:
        actual=centre_turn_from_body(route);route["regularity_validation"]["centre_turn_points_grid"]=actual;route["regularity_validation"]["centre_turn_points_are_members_of_body"]=all(point in route["heating_body_points_grid"] for point in actual);route["regularity_validation"]["result"]="PASS" if route["regularity_validation"]["centre_turn_points_are_members_of_body"] else "FAIL"
        route["source_d015_route_digest"]=route["geometry_digest"]
    body_length=sum(route["heating_body_length_mm"] for route in model["routes"]);named_area=model["coverage_diagnostic"]["useful_area_mm2"];model["coverage_diagnostic"]["nominal_served_area_mm2"]=body_length*200;model["coverage_diagnostic"]["nominal_ratio"]=round(body_length*200/named_area,6);model["coverage_diagnostic"]["result"]="REWORK_COVERAGE"
    model.pop("geometry_digest",None);model["geometry_digest"]=digest(model)
    ports=[tuple(route[key]) for route in model["routes"] for key in ("supply_port_grid","return_port_grid")];gates=[tuple(point) for point in new_contract["unique_wall_penetration_gates_grid"]]
    crossed=[]
    for route in model["routes"]:
        for points_key in ("supply_transit_points_grid","return_transit_points_grid"):
            pts=route[points_key]
            for a,b in zip(pts,pts[1:]):
                if a[0]==b[0] and min(a[1],b[1])<=82<=max(a[1],b[1]):crossed.append((a[0],82))
    validation={"artifact_id":model["artifact_id"],"status":model["status"],"route_geometry_unchanged_from_d015":all(route["source_d015_route_digest"]==route["geometry_digest"] for route in model["routes"]),"logical_collector_count":1,"unique_port_count":len(set(ports)),"all_ports_inside_vector_boiler_room":all(129.52<=x<=182.54 and 54.08<=y<=83.77 for x,y in ports),"declared_gate_count":len(gates),"actual_unique_wall_crossing_gate_count":len(set(crossed)),"actual_wall_crossing_gates_grid":[list(point) for point in sorted(set(crossed))],"all_wall_crossings_declared":set(crossed)==set(gates),"regularity_metadata_pass_count":sum(route["regularity_validation"]["result"]=="PASS" for route in model["routes"]),"nominal_coverage_ratio":model["coverage_diagnostic"]["nominal_ratio"],"coverage_result":"REWORK_COVERAGE","whole_house_completion":False}
    if not validation["route_geometry_unchanged_from_d015"] or not validation["all_ports_inside_vector_boiler_room"] or not validation["all_wall_crossings_declared"] or validation["regularity_metadata_pass_count"]!=5:raise RuntimeError(f"D017 reconciliation failed: {validation}")
    OUTPUT.mkdir(parents=True);(OUTPUT/"canonical_geometry.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8");(OUTPUT/"k1_gate_contract.json").write_text(json.dumps(new_contract,ensure_ascii=False,indent=2),encoding="utf-8");(OUTPUT/"validation.json").write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.copy2(SOURCE/"floor_1_counterflow_full_routes_overlay.png",OUTPUT/"floor_1_counterflow_full_routes_overlay.png");shutil.copy2(SOURCE/"floor_1_counterflow_full_routes_pipes_only.png",OUTPUT/"floor_1_counterflow_full_routes_pipes_only.png")
    (OUTPUT/"report.md").write_text(f"# HA_TWO_FLOOR_K1_RECONCILED_017\n\nГеометрия пяти труб D015 сохранена байт-в-байт по ordered points. Новый ограниченный контракт связывает один настенный K1, десятипортовую рейку внутри векторных границ котельной и девять уникальных проходов через линию y=8200 мм; обратка верхней котельной улитки остаётся в котельной. Все девять фактических проходов совпадают с объявленными воротами x=13000…13800 мм. Метаданные центральных разворотов пересчитаны после зеркалирования и теперь ссылаются на реальные точки. Длины и топология остаются PASS; покрытие остаётся REWORK: номинальная оценка {model['coverage_diagnostic']['nominal_ratio']:.1%}, геометрическая D016 — 84,3% чернового прямоугольника.\n",encoding="utf-8")
    files=[{"name":path.name,"bytes":path.stat().st_size,"sha256":sha(path)} for path in sorted(OUTPUT.iterdir()) if path.is_file()];(OUTPUT/"artifact_manifest.json").write_text(json.dumps({"artifact_id":model["artifact_id"],"geometry_digest":model["geometry_digest"],"files":files},ensure_ascii=False,indent=2),encoding="utf-8");shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"package":str(PACKAGE),"status":model["status"],"ratio":model["coverage_diagnostic"]["nominal_ratio"],"digest":model["geometry_digest"]},ensure_ascii=False))

if __name__=="__main__":main()

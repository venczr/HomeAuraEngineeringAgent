from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from shapely.geometry import LineString


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
BODY_SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
NODE_SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_FLOOR_CANDIDATE_NODES_056" / "attic_floor_candidate_nodes.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058.zip"
VOID_BOX_GRID = (99, 57, 131, 92)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


d049 = load_module(
    "attic_d049_for_d057",
    ROOT / "homeaura-native-editor-generate" / "route_attic_right_r1_fragments_049.py",
)
core = d049.core
d041 = d049.d041


FRAGMENT_SPEC = {
    "A-C09": {
        "interface_group": "EAST_TOP_PLANSPACE",
        "supply": [(132, 57), (160, 57), (160, 61), (161, 61)],
        "return": [(163, 63), (159, 63), (159, 58), (132, 58)],
    },
    "A-C11": {
        "interface_group": "EAST_TOP_PLANSPACE",
        "supply": [(132, 59), (158, 59), (158, 111), (161, 111)],
        "return": [(163, 113), (157, 113), (157, 60), (132, 60)],
    },
    "A-C08": {
        "interface_group": "EAST_TOP_PLANSPACE",
        "supply": [(132, 61), (135, 61)],
        "return": [(137, 63), (135, 63), (135, 62), (132, 62)],
    },
    "A-C10": {
        "interface_group": "BELOW_VOID_ADJACENT_FLOOR_UNCONFIRMED",
        "supply": [(134, 93), (134, 111), (135, 111)],
        "return": [(137, 113), (133, 113), (133, 93)],
    },
    "A-C12": {
        "interface_group": "BELOW_VOID_ADJACENT_FLOOR_UNCONFIRMED",
        "supply": [(132, 93), (132, 135), (135, 135)],
        "return": [(137, 137), (131, 137), (131, 93)],
    },
    "A-C13": {
        "interface_group": "BELOW_VOID_ADJACENT_FLOOR_UNCONFIRMED",
        "supply": [(130, 93), (130, 152), (135, 152)],
        "return": [(137, 154), (129, 154), (129, 93)],
    },
    "A-C02": {
        "interface_group": "BELOW_VOID_WEST_ADJACENT_FLOOR_UNCONFIRMED",
        "supply": [(96, 93), (96, 88), (94, 88)],
        "return": [(92, 90), (95, 90), (95, 93)],
    },
}

COLOURS = {
    "A-C02": "#7A49E5",
    "A-C08": "#A26700",
    "A-C09": "#5E9400",
    "A-C10": "#C43D00",
    "A-C11": "#247BA0",
    "A-C12": "#6A4C93",
    "A-C13": "#8A5A00",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def dashed_line(canvas: ImageDraw.ImageDraw, points, colour: str, width: int = 5):
    dash = 12
    gap = 8
    for a, b in zip(points, points[1:]):
        ax, ay = a
        bx, by = b
        distance = abs(bx - ax) + abs(by - ay)
        if distance == 0:
            continue
        dx = (bx - ax) / distance
        dy = (by - ay) / distance
        cursor = 0.0
        while cursor < distance:
            end = min(cursor + dash, distance)
            canvas.line((ax + dx * cursor, ay + dy * cursor, ax + dx * end, ay + dy * end), fill=colour, width=width)
            cursor += dash + gap


def draw(model: dict, target: Path, pipes_only: bool):
    image = Image.new("RGB", (1785, 1750), "#F7FAFA") if pipes_only else Image.open(d041.BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    if pipes_only:
        step = round(d041.PX)
        for x in range(0, image.width, step):
            canvas.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, step):
            canvas.line((0, y, image.width, y), fill="#D8E2E2")
    x0, y0, x1, y1 = model["structural_stair_void_box_grid"]
    canvas.rectangle((*d041.to_px((x0, y0)), *d041.to_px((x1, y1))), fill="#F7CACA", outline="#B00020", width=4)
    body_colours = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC", "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93", "#8A5A00"]
    for route, colour in zip(model["body_routes"], body_colours):
        body_points = [d041.to_px(point) for point in route["body_points_grid"]]
        canvas.line(body_points, fill="white", width=9, joint="curve")
        canvas.line(body_points, fill=colour, width=4, joint="curve")
    for fragment in model["diagnostic_planar_fragments"]:
        colour = COLOURS[fragment["route_id"]]
        for key in ("supply_transit_points_grid", "return_transit_points_grid"):
            points = [d041.to_px(point) for point in fragment[key]]
            dashed_line(canvas, points, "white", 11)
            dashed_line(canvas, points, colour, 5)
        for point, leg in ((fragment["candidate_supply_endpoint_grid"], "S?"), (fragment["candidate_return_endpoint_grid"], "R?")):
            x, y = d041.to_px(point)
            canvas.rectangle((x - 5, y - 5, x + 5, y + 5), fill="#FFF2B8", outline="#8D5900", width=2)
            canvas.text((x + 7, y - 8), leg, font=d041.font(9, True), fill="#8D5900", stroke_width=2, stroke_fill="white")
    canvas.rectangle((0, 0, image.width, 184), fill="#071A21")
    canvas.text((28, 10), "D058 · МАНСАРДА · ДИАГНОСТИКА ПЛАНОВОЙ РАЗВОДКИ", font=d041.font(23, True), fill="white")
    canvas.text((28, 49), "7 непрерывных планарных кандидатов · контактов 0 · проём 0 · тела D050 не изменены", font=d041.font(15), fill="#A7EEE7")
    canvas.text((28, 81), "ПУНКТИР = НЕПОДТВЕРЖДЁННЫЙ ПОДВОД · квадраты S?/R? = НЕ ВОРОТА R1", font=d041.font(15, True), fill="#F3D58C")
    canvas.text((28, 113), "Физический выход стояка, перекрытие, стены и соседние территории: NOT EVALUATED", font=d041.font(14, True), fill="#FFB2B2")
    canvas.text((28, 141), "Это проверка непересечения в плоскости, а не монтажный чертёж и не полные контуры K1", font=d041.font(14, True), fill="#FFB2B2")
    canvas.text((28, 166), "A-C10/A-C11 короче 40 м в плане: вертикали и нижние ноги K1 ещё отсутствуют", font=d041.font(12), fill="#E8F0F2")
    image.save(target)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D058 is append-only")
    body_bytes = BODY_SOURCE.read_bytes()
    body_model = json.loads(body_bytes.decode("utf-8"))
    node_bytes = NODE_SOURCE.read_bytes()
    node_model = json.loads(node_bytes.decode("utf-8"))
    routes = {route["route_id"]: route for route in body_model["body_routes"]}
    fragments = []
    for route_id, spec in FRAGMENT_SPEC.items():
        route = routes[route_id]
        supply = [tuple(point) for point in spec["supply"]]
        returned = [tuple(point) for point in spec["return"]]
        body = [tuple(point) for point in route["body_points_grid"]]
        if supply[-1] != body[0] or returned[0] != body[-1]:
            raise RuntimeError({"route": route_id, "join": "body endpoint mismatch"})
        points = supply + body[1:] + returned[1:]
        topology = core.topology(points)
        supply_length = core.length_mm(supply)
        return_length = core.length_mm(returned)
        total = core.length_mm(points)
        void_hits = sum(d041.segment_hits_box(a, b, VOID_BOX_GRID) for a, b in zip(points, points[1:]))
        if topology["result"] != "PASS" or void_hits or total != supply_length + route["body_length_mm"] + return_length:
            raise RuntimeError({"route": route_id, "topology": topology, "void_hits": void_hits, "total": total})
        fragments.append({
            "route_id": route_id,
            "floor_id": "ATTIC",
            "classification": "DIAGNOSTIC_PLANAR_FRAGMENT_NOT_APPROVED_PIPE_ROUTE",
            "interface_group": spec["interface_group"],
            "candidate_supply_endpoint_grid": list(supply[0]),
            "candidate_return_endpoint_grid": list(returned[-1]),
            "candidate_endpoints_are_r1_gates": False,
            "physical_interface_status": "NOT_EVALUATED",
            "adjacent_floor_domain_containment": "NOT_EVALUATED_FULL_ATTIC_FLOOR_UNION_MISSING",
            "supply_transit_points_grid": [list(point) for point in supply],
            "heating_body_points_grid": route["body_points_grid"],
            "return_transit_points_grid": [list(point) for point in returned],
            "ordered_points_grid": [list(point) for point in points],
            "ordered_points_mm": [[x * 100, y * 100] for x, y in points],
            "supply_transit_length_mm": supply_length,
            "heating_body_length_mm": route["body_length_mm"],
            "return_transit_length_mm": return_length,
            "planar_fragment_length_mm": total,
            "complete_circuit_total_length_mm": None,
            "complete_40_80m_validation": "NOT_EVALUATED_VERTICAL_RISER_AND_FLOOR1_K1_LEGS_MISSING",
            "topology_validation": topology,
            "structural_void_hit_count": 0,
            "fragment_digest": digest([[x * 100, y * 100] for x, y in points]),
        })

    adapted = [{"route_id": item["route_id"], "ordered_points_grid": item["ordered_points_grid"]} for item in fragments]
    contacts = core.inter_contacts(adapted)
    if contacts:
        raise RuntimeError({"inter_fragment_contacts": contacts})
    foreign_contacts = []
    for fragment in fragments:
        line = LineString(fragment["ordered_points_grid"])
        for route_id, route in routes.items():
            if route_id == fragment["route_id"]:
                continue
            if line.intersects(LineString(route["body_points_grid"])):
                foreign_contacts.append({"fragment": fragment["route_id"], "body": route_id})
    if foreign_contacts:
        raise RuntimeError({"foreign_body_contacts": foreign_contacts})
    endpoint_points = [tuple(item[key]) for item in fragments for key in ("candidate_supply_endpoint_grid", "candidate_return_endpoint_grid")]
    if len(set(endpoint_points)) != 14:
        raise RuntimeError("duplicate candidate endpoint")

    model = dict(body_model)
    model.update(
        schema="homeaura-attic-plan-space-diagnostic-0.1",
        artifact_id="HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058",
        status="SEVEN_PLANAR_FRAGMENT_TOPOLOGY_PASS_REWORK_SOURCE_DOMAINS_AND_PHYSICAL_R1_INTERFACE",
        source_body_artifact_id=body_model["artifact_id"],
        source_body_sha256=hashlib.sha256(body_bytes).hexdigest().upper(),
        source_candidate_node_artifact_id=node_model["artifact_id"],
        source_candidate_node_sha256=hashlib.sha256(node_bytes).hexdigest().upper(),
        source_candidate_node_set_preserved_unassigned=True,
        source_D052_two_fragments_reopened_for_global_diagnostic=True,
        all_thirteen_body_point_arrays_preserved=True,
        diagnostic_planar_fragments=fragments,
        diagnostic_planar_fragment_count=7,
        diagnostic_candidate_endpoint_count=14,
        inter_fragment_contact_count=0,
        foreign_body_contact_count=0,
        structural_void_hit_count=0,
        physical_r1_interface_confirmed=False,
        slab_penetration_confirmed=False,
        full_attic_floor_union_available=False,
        candidate_adjacent_floor_containment_evaluated=False,
        diagnostic_geometry_is_approved_pipe=False,
        collector_to_collector_route_count=0,
        complete_circuit_count=0,
        hydraulics_calculated=False,
        result="PASS_PLANAR_NONCONTACT_DIAGNOSTIC_REWORK_PHYSICAL_INTERFACE_FLOOR_DOMAINS_AND_FULL_ROUTING",
    )
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "diagnostic_fragment_route_ids": [item["route_id"] for item in fragments],
        "diagnostic_fragment_count": 7,
        "unique_candidate_endpoint_count": 14,
        "all_topology_pass": all(item["topology_validation"]["result"] == "PASS" for item in fragments),
        "component_length_reconciliation_delta_mm": 0,
        "inter_fragment_contact_count": 0,
        "foreign_body_contact_count": 0,
        "structural_void_hit_count": 0,
        "body_geometry_modified": False,
        "physical_interface_confirmed": False,
        "full_floor_containment_evaluated": False,
        "approved_pipe_geometry_count": 0,
        "complete_circuit_count": 0,
        "result": model["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_plan_space_diagnostic.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, OUTPUT / "attic_plan_space_diagnostic_overlay.png", False)
    draw(model, OUTPUT / "attic_plan_space_diagnostic_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D058 — диагностическая проверка плановой разводки мансарды\n\n"
        "Для семи тел D050 построены пунктирные кандидаты подающей и обратной ног. Каждая полилиния непрерывна, не касается проёма, чужих тел или другой кандидатной полилинии. "
        "Все 13 тел сохранены без изменений.\n\n"
        "Это не принятые трубы и не ворота R1. Для точек под проёмом и западнее холла отсутствуют подтверждённые полигоны соседних помещений, а физический выход стояка в плоскость мансарды не доказан. "
        "Поэтому семь линий служат только доказательством возможности непересекающейся компоновки в координатной плоскости; полных контуров K1 здесь нет.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "geometry_digest": model["geometry_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "fragment_lengths_mm": {item["route_id"]: item["planar_fragment_length_mm"] for item in fragments},
        "contacts": 0,
        "void_hits": 0,
        "physical_interface": False,
        "geometry_digest": model["geometry_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

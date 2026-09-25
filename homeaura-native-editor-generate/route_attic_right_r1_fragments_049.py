from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_HALL_COUNTERFLOWS_048"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_RIGHT_R1_FRAGMENTS_049"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_RIGHT_R1_FRAGMENTS_049.zip"
VOID_BOX = (99, 57, 131, 92)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


d043 = load_module(
    "attic_d043_for_d049",
    ROOT / "homeaura-native-editor-generate" / "rebuild_attic_rectangular_counterflows_043.py",
)
core = d043.core
d041 = d043.d041


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def join_fragment(route: dict, supply, returned):
    body = [tuple(point) for point in route["body_points_grid"]]
    if tuple(supply[-1]) != body[0] or tuple(returned[0]) != body[-1]:
        raise RuntimeError({"route": route["route_id"], "join": "endpoint mismatch"})
    return [tuple(point) for point in supply] + body[1:] + [tuple(point) for point in returned[1:]]


FRAGMENT_SPEC = {
    # The farther east territory receives the upper pair, then the nearer body
    # receives the next pair. This monotone assignment prevents lane inversion.
    "A-C09": {
        "supply_gate": (132, 57),
        "return_gate": (132, 58),
        "supply": [(132, 57), (160, 57), (160, 61), (161, 61)],
        "return": [(163, 63), (159, 63), (159, 58), (132, 58)],
    },
    "A-C08": {
        "supply_gate": (132, 59),
        "return_gate": (132, 60),
        "supply": [(132, 59), (134, 59), (134, 61), (135, 61)],
        "return": [(137, 63), (133, 63), (133, 60), (132, 60)],
    },
}


def draw(model, target: Path, pipes_only: bool, fragments_only: bool = False):
    if fragments_only:
        image = Image.new("RGB", (1785, 1100), "#F7FAFA")
        canvas = ImageDraw.Draw(image, "RGBA")
        step = round(d041.PX)
        for x in range(0, image.width, step):
            canvas.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, step):
            canvas.line((0, y, image.width, y), fill="#D8E2E2")
        x0, y0, x1, y1 = model["structural_stair_void_box_grid"]
        canvas.rectangle((*d041.to_px((x0, y0)), *d041.to_px((x1, y1))), fill="#F7CACA", outline="#B00020", width=4)
    else:
        d041.draw(model, target, pipes_only)
        image = Image.open(target).convert("RGB")
        canvas = ImageDraw.Draw(image, "RGBA")
    colours = {"A-C08": "#A26700", "A-C09": "#5E9400"}
    for fragment in model["attic_plane_route_fragments"]:
        points = [d041.to_px(point) for point in fragment["ordered_points_grid"]]
        canvas.line(points, fill="white", width=11, joint="curve")
        canvas.line(points, fill=colours[fragment["route_id"]], width=5, joint="curve")
        canvas.text((points[0][0] + 5, points[0][1] - 24), f'{fragment["route_id"]} {fragment["planar_fragment_length_mm"] / 1000:.1f} м', font=d041.font(11, True), fill=colours[fragment["route_id"]], stroke_width=2, stroke_fill="white")
        canvas.text((points[-1][0] + 5, points[-1][1] + 4), "R", font=d041.font(10, True), fill=colours[fragment["route_id"]], stroke_width=2, stroke_fill="white")
    canvas.rectangle((0, 0, image.width, 166), fill="#071A21")
    canvas.text((28, 10), "D049 · МАНСАРДА · ДВА ПОЛНЫХ ФРАГМЕНТА R1↔ТЕЛО↔R1", font=d041.font(23, True), fill="white")
    canvas.text((28, 49), "A-C09: ворота 57/58 · A-C08: ворота 59/60 · 4 отдельные трубы · общий ствол отсутствует", font=d041.font(15), fill="#A7EEE7")
    canvas.text((28, 81), "2 связных фрагмента · самоконтактов 0 · взаимных контактов 0 · проём не затронут", font=d041.font(15, True), fill="#F3D58C")
    canvas.text((28, 113), "ПЛАН: A-C09 49,3 м · A-C08 41,7 м · вертикальная часть/К1 ещё НЕ ДОБАВЛЕНЫ", font=d041.font(14), fill="#FFB2B2")
    canvas.text((28, 140), "ЭТО ФРАГМЕНТЫ МАНСАРДЫ, НЕ ЗАВЕРШЁННЫЕ КОЛЛЕКТОРНЫЕ КОНТУРЫ", font=d041.font(14, True), fill="#FFB2B2")
    image.save(target)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D049 is append-only")
    source_bytes = (SOURCE / "attic_body_geometry.json").read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    model = deepcopy(source)
    routes = {route["route_id"]: route for route in model["body_routes"]}
    fragments = []
    gate_reassignment = []
    for route_id in ("A-C09", "A-C08"):
        route = routes[route_id]
        spec = FRAGMENT_SPEC[route_id]
        points = join_fragment(route, spec["supply"], spec["return"])
        topology = core.topology(points)
        void_hits = sum(d041.segment_hits_box(a, b, VOID_BOX) for a, b in zip(points, points[1:]))
        supply_length = core.length_mm(spec["supply"])
        return_length = core.length_mm(spec["return"])
        total = core.length_mm(points)
        if topology["result"] != "PASS" or void_hits or total != supply_length + route["body_length_mm"] + return_length:
            raise RuntimeError({"route": route_id, "topology": topology, "void_hits": void_hits, "total": total})
        old_supply = route["planned_riser_supply_gate_grid"]
        old_return = route["planned_riser_return_gate_grid"]
        fragments.append({
            "route_id": route_id,
            "floor_id": "ATTIC",
            "parent_complete_route_status": "NOT_COMPLETE_VERTICAL_RISER_AND_FLOOR1_K1_LEGS_MISSING",
            "riser_id": "R1",
            "supply_gate_id": f"R1-{route_id}-S",
            "return_gate_id": f"R1-{route_id}-R",
            "supply_gate_grid": list(spec["supply_gate"]),
            "return_gate_grid": list(spec["return_gate"]),
            "supply_transit_points_grid": [list(point) for point in spec["supply"]],
            "heating_body_points_grid": route["body_points_grid"],
            "return_transit_points_grid": [list(point) for point in spec["return"]],
            "ordered_points_grid": [list(point) for point in points],
            "ordered_points_mm": [[x * 100, y * 100] for x, y in points],
            "supply_transit_length_mm": supply_length,
            "heating_body_length_mm": route["body_length_mm"],
            "return_transit_length_mm": return_length,
            "planar_fragment_length_mm": total,
            "complete_circuit_total_length_mm": None,
            "complete_40_80m_validation": "NOT_EVALUATED_VERTICAL_AND_K1_LEGS_MISSING",
            "topology_validation": topology,
            "structural_void_hit_count": 0,
            "fragment_digest": digest([[x * 100, y * 100] for x, y in points]),
        })
        gate_reassignment.append({
            "route_id": route_id,
            "source_supply_gate_grid": old_supply,
            "source_return_gate_grid": old_return,
            "current_supply_gate_grid": list(spec["supply_gate"]),
            "current_return_gate_grid": list(spec["return_gate"]),
            "reason": "FARTHER_EAST_PAIR_FIRST_TO_PREVENT_TRANSIT_LANE_INVERSION",
        })

    contacts = core.inter_contacts([{"route_id": item["route_id"], "ordered_points_grid": item["ordered_points_grid"]} for item in fragments])
    if contacts:
        raise RuntimeError({"inter_fragment_contacts": contacts})
    all_gate_points = [tuple(item["supply_gate_grid"]) for item in fragments] + [tuple(item["return_gate_grid"]) for item in fragments]
    if len(set(all_gate_points)) != 4:
        raise RuntimeError("duplicate R1 gate")

    model.update(
        schema="homeaura-attic-right-r1-fragments-0.1",
        artifact_id="HA_TWO_FLOOR_ATTIC_RIGHT_R1_FRAGMENTS_049",
        status="TWO_ATTIC_R1_TO_BODY_TO_R1_FRAGMENTS_PASS_REWORK_REMAINING_TRANSITS_AND_COMPLETE_ROUTES",
        derived_from_artifact_id=source["artifact_id"],
        derived_from_sha256=hashlib.sha256(source_bytes).hexdigest().upper(),
        source_body_geometry_preserved=True,
        gate_assignment_revision="R1_RIGHT_GROUP_FAR_DESTINATION_FIRST_049",
        gate_reassignment=gate_reassignment,
        attic_plane_route_fragments=fragments,
        attic_plane_complete_fragment_count=2,
        distinct_supply_return_transit_count=4,
        inter_fragment_contact_count=0,
        structural_void_hit_count=0,
        shared_pipe_trunk=False,
        full_collector_to_collector_routes_claimed=False,
        complete_circuit_count=0,
        vertical_riser_length_mm=None,
        hydraulics_calculated=False,
        result="PASS_TWO_ATTIC_PLANE_FRAGMENTS_REWORK_VERTICAL_K1_AND_REMAINING_ELEVEN_ROUTES",
    )
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "fragment_route_ids": [item["route_id"] for item in fragments],
        "attic_plane_fragment_count": 2,
        "distinct_gate_count": 4,
        "distinct_transit_count": 4,
        "all_fragment_topology_pass": all(item["topology_validation"]["result"] == "PASS" for item in fragments),
        "inter_fragment_contact_count": 0,
        "structural_void_hit_count": 0,
        "component_length_reconciliation_delta_mm": 0,
        "body_geometry_modified": False,
        "complete_circuit_count": 0,
        "complete_40_80m_result": "NOT_EVALUATED_VERTICAL_AND_K1_LEGS_MISSING",
        "result": model["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_right_r1_fragments.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, OUTPUT / "attic_right_r1_fragments_overlay.png", False)
    draw(model, OUTPUT / "attic_right_r1_fragments_pipes_only.png", True)
    draw(model, OUTPUT / "attic_right_r1_fragments_debug.png", True, fragments_only=True)
    (OUTPUT / "report.md").write_text(
        "# D049 — первые два полных планарных фрагмента мансарды\n\n"
        "A-C09 получил верхнюю пару R1 57/58 как более дальняя правая территория, A-C08 — следующую пару 59/60. "
        "От каждой точки идёт собственная подающая или обратная труба; общего ствола нет. Оба упорядоченных фрагмента проходят R1 → транзит → регулярное тело → обратный транзит → R1 без самоконтактов, взаимных контактов и попаданий в проём. "
        "Их планарные длины 49,3 и 41,7 м, но это ещё не полные коллекторные контуры: не добавлены отдельные вертикальные участки и нижние подключения к K1. Поэтому итоговая проверка 40–80 м остаётся NOT_EVALUATED.\n",
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
        "geometry_digest": model["geometry_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

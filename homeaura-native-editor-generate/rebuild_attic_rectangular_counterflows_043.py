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
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_RIGHT_COUNTERFLOW_042"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_RECTANGULAR_COUNTERFLOWS_043"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_RECTANGULAR_COUNTERFLOWS_043.zip"
VOID_BOX = (99, 57, 131, 92)
BOXES = {
    "A-C01": (49, 61, 94, 79),
    "A-C02": (49, 88, 94, 111),
    "A-C03": (49, 116, 94, 139),
    "A-C04": (49, 145, 94, 165),
    "A-C10": (135, 111, 156, 125),
    "A-C11": (161, 111, 184, 125),
    "A-C12": (135, 135, 184, 147),
    "A-C13": (135, 152, 184, 164),
}
TRANSFORMS = ("IDENTITY", "MIRROR_X", "MIRROR_Y", "ROTATE_180")

spec = importlib.util.spec_from_file_location(
    "attic_d042_for_d043",
    ROOT / "homeaura-native-editor-generate" / "rebuild_attic_right_counterflow_042.py",
)
d042 = importlib.util.module_from_spec(spec)
sys.modules["attic_d042_for_d043"] = d042
assert spec.loader is not None
spec.loader.exec_module(d042)
core = d042.core
d041 = d042.d041


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def transform_point(point, box, name):
    x, y = point
    x0, y0, x1, y1 = box
    if name == "IDENTITY":
        return x, y
    if name == "MIRROR_X":
        return x0 + x1 - x, y
    if name == "MIRROR_Y":
        return x, y0 + y1 - y
    if name == "ROTATE_180":
        return x0 + x1 - x, y0 + y1 - y
    raise ValueError(name)


def transform_points(points, box, name):
    return [transform_point(point, box, name) for point in points]


def transform_frame(item, box, name):
    left, top, right, bottom = item
    corners = [
        transform_point((left, top), box, name),
        transform_point((right, top), box, name),
        transform_point((right, bottom), box, name),
        transform_point((left, bottom), box, name),
    ]
    return [min(x for x, _ in corners), min(y for _, y in corners), max(x for x, _ in corners), max(y for _, y in corners)]


def transform_meta(meta, box, name):
    return {
        "inward_frame_bounds_grid": [transform_frame(item, box, name) for item in meta["inward_frame_bounds_grid"]],
        "outward_frame_bounds_grid": [transform_frame(item, box, name) for item in meta["outward_frame_bounds_grid"]],
        "inward_frame_inset_mm": 400,
        "outward_interleave_offset_mm": 200,
        "centre_turn_points_grid": [list(point) for point in transform_points(meta["centre_turn_points_grid"], box, name)],
        "centre_turn_segment_count": meta["centre_turn_segment_count"],
    }


def choose_orientation(generated, box, supply_gate, return_gate):
    candidates = []
    for transform_index, name in enumerate(TRANSFORMS):
        transformed = transform_points(generated, box, name)
        for reversed_route in (False, True):
            points = list(reversed(transformed)) if reversed_route else transformed
            score = (
                abs(points[0][0] - supply_gate[0]) + abs(points[0][1] - supply_gate[1])
                + abs(points[-1][0] - return_gate[0]) + abs(points[-1][1] - return_gate[1])
            )
            candidates.append((score, reversed_route, transform_index, name, points))
    return min(candidates, key=lambda item: item[:3])


def draw(model, target: Path, pipes_only: bool):
    d041.draw(model, target, pipes_only)
    image = Image.open(target).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 160), fill="#071A21")
    canvas.text((28, 10), "D043 · МАНСАРДА · 10 РЕГУЛЯРНЫХ ПРЯМОУГОЛЬНЫХ УЛИТОК", font=d041.font(24, True), fill="white")
    canvas.text((28, 49), "10 комнатных тел: рамки 400 мм · обратные линии 200 мм · центральный разворот ≤ 2 сегментов", font=d041.font(15), fill="#A7EEE7")
    canvas.text((28, 81), "13 тел · контактов 0 · проём 0 · 26 точек R1 сохранены · подводки и стояк ещё НЕ ПРОВЕДЕНЫ", font=d041.font(15), fill="#F3D58C")
    canvas.text((28, 113), "МОРФОЛОГИЯ: 10 PASS · 3 ТЕЛА ХОЛЛА REWORK · полные длины/покрытие NOT_EVALUATED", font=d041.font(14, True), fill="#FFB2B2")
    for route in model["body_routes"]:
        if route["route_id"] not in set(BOXES) | {"A-C08", "A-C09"}:
            continue
        x0, y0, x1, y1 = route["body_envelope_grid"]
        canvas.rectangle((*d041.to_px((x0, y0)), *d041.to_px((x1, y1))), outline="#00A878", width=3)
    image.save(target)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D043 is append-only")
    source_bytes = (SOURCE / "attic_body_geometry.json").read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    model = deepcopy(source)
    lineage = []
    for route in model["body_routes"]:
        route_id = route["route_id"]
        if route_id not in BOXES:
            continue
        box = BOXES[route_id]
        generated, generated_meta = core.paired_counterflow(box)
        supply_gate = tuple(route["planned_riser_supply_gate_grid"])
        return_gate = tuple(route["planned_riser_return_gate_grid"])
        score, reversed_route, _, orientation, points = choose_orientation(generated, box, supply_gate, return_gate)
        meta = transform_meta(generated_meta, box, orientation)
        if reversed_route:
            meta["centre_turn_points_grid"] = list(reversed(meta["centre_turn_points_grid"]))
        topology = core.topology(points)
        morphology = d042.regularity(points, meta)
        void_hits = sum(d041.segment_hits_box(a, b, VOID_BOX) for a, b in zip(points, points[1:]))
        if topology["result"] != "PASS" or morphology["result"] != "PASS" or void_hits:
            raise RuntimeError({"route": route_id, "topology": topology, "regularity": morphology, "void_hits": void_hits})
        old_digest = route["body_digest"]
        old_length = route["body_length_mm"]
        route.update(
            body_topology="REGULAR_RECTANGULAR_COUNTERFLOW",
            body_envelope_grid=list(box),
            body_envelope_status="D009_BODY_CENTERLINE_ENVELOPE_PROXY_NOT_SURVEYED_ROOM_POLYGON",
            body_points_grid=[list(point) for point in points],
            body_points_mm=[[value * 100 for value in point] for point in points],
            body_length_mm=core.length_mm(points),
            body_topology_validation=topology,
            structural_void_hit_count=0,
            minimum_centerline_to_structural_void_mm=round(d041.distance_to_box(points, VOID_BOX), 6),
            body_digest=digest([[value * 100 for value in point] for point in points]),
            geometry_orientation=orientation + ("_REVERSED" if reversed_route else ""),
            endpoint_gate_manhattan_score_grid=score,
            endpoint_orientation_selection="MINIMIZE_SUPPLY_AND_RETURN_GATE_MANHATTAN_DISTANCE_THEN_NONREVERSED_THEN_FIXED_TRANSFORM_ORDER",
            regularity_validation=morphology,
            owner_style_validation={"result": "PASS", "scope": "BODY_ONLY_REGULAR_COUNTERFLOW"},
        )
        lineage.append({
            "route_id": route_id,
            "source_body_digest": old_digest,
            "current_body_digest": route["body_digest"],
            "source_body_length_mm": old_length,
            "current_body_length_mm": route["body_length_mm"],
            "reason": "REPLACE_LEGACY_BODY_WITH_REGULAR_COUNTERFLOW",
        })

    contacts = core.inter_contacts([
        {"route_id": route["route_id"], "ordered_points_grid": route["body_points_grid"]}
        for route in model["body_routes"]
    ])
    if contacts:
        raise RuntimeError({"inter_body_contacts": contacts})
    pass_ids = [route["route_id"] for route in model["body_routes"] if route["owner_style_validation"]["result"] == "PASS"]
    rework_ids = [route["route_id"] for route in model["body_routes"] if route["owner_style_validation"]["result"] != "PASS"]
    model.update(
        schema="homeaura-attic-rectangular-counterflows-0.1",
        artifact_id="HA_TWO_FLOOR_ATTIC_RECTANGULAR_COUNTERFLOWS_043",
        status="TEN_ATTIC_RECTANGULAR_COUNTERFLOW_BODIES_PASS_REWORK_HALL_AND_FULL_ROUTES",
        derived_from_artifact_id=source["artifact_id"],
        derived_from_sha256=hashlib.sha256(source_bytes).hexdigest().upper(),
        body_lengths_mm={route["route_id"]: route["body_length_mm"] for route in model["body_routes"]},
        body_count_at_least_40000mm=sum(route["body_length_mm"] >= 40_000 for route in model["body_routes"]),
        body_count_below_40000mm=sum(route["body_length_mm"] < 40_000 for route in model["body_routes"]),
        owner_style_body_pass_count=len(pass_ids),
        owner_style_body_rework_count=len(rework_ids),
        owner_style_body_pass_route_ids=pass_ids,
        owner_style_body_rework_route_ids=rework_ids,
        morphology_rebuild_lineage=[*source["morphology_rebuild_lineage"], *lineage],
        inter_body_contact_count=0,
        complete_circuit_count=0,
        full_collector_to_collector_routes_claimed=False,
        whole_attic_coverage_claimed=False,
        result="PASS_TEN_REGULAR_RECTANGULAR_BODIES_REWORK_VOID_CONSTRAINED_HALL_AND_TRANSITS",
    )
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "source_body_artifact_sha256": model["derived_from_sha256"],
        "body_route_count": 13,
        "changed_route_ids": list(BOXES),
        "preserved_route_ids": ["A-C05", "A-C06", "A-C07", "A-C08", "A-C09"],
        "regular_counterflow_pass_route_ids": pass_ids,
        "regular_counterflow_pass_count": len(pass_ids),
        "owner_style_rework_route_ids": rework_ids,
        "owner_style_rework_count": len(rework_ids),
        "inter_body_contact_count": 0,
        "structural_void_hit_count": 0,
        "planned_R1_gate_count": len(model["planned_R1_gate_mapping"]),
        "planned_R1_unique_gate_count": len({tuple(item["gate_point_grid"]) for item in model["planned_R1_gate_mapping"]}),
        "complete_circuit_count": 0,
        "complete_40_80m_result": "NOT_EVALUATED_TRANSITS_AND_VERTICAL_LENGTH_MISSING",
        "result": model["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_body_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, OUTPUT / "attic_rectangular_counterflows_overlay.png", False)
    draw(model, OUTPUT / "attic_rectangular_counterflows_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D043 — десять регулярных тел мансарды\n\n"
        "Десять прямоугольных комнатных территорий теперь имеют регулярные противоточные улитки: A-C01–A-C04 и A-C08–A-C13. "
        "Каждое тело построено непосредственно на сетке, входящие рамки имеют постоянный шаг 400 мм, обратные ветви занимают промежуточные 200-мм линии, а центральный разворот не превышает двух сегментов. "
        "Все 13 тел, включая три пока сохранённых тела холла A-C05/A-C06/A-C07, остаются без самопересечений, взаимных контактов и попаданий в проём. "
        "Три тела холла ещё REWORK: их нельзя независимо заменить короткими прямоугольниками — требуется единая препятствие-ориентированная компоновка вокруг лестничного проёма. "
        "R1, транзиты, вертикальный стояк, полные длины 40–80 м и покрытие пока не заявляются.\n",
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
        "digest": model["geometry_digest"],
        "regular_pass": pass_ids,
        "rework": rework_ids,
        "body_lengths_mm": model["body_lengths_mm"],
        "contacts": 0,
        "void_hits": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

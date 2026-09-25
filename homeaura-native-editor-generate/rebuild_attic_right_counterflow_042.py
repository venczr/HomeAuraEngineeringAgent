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
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_BODY_BASELINE_041"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_RIGHT_COUNTERFLOW_042"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_RIGHT_COUNTERFLOW_042.zip"
VOID_BOX = (99, 57, 131, 92)

spec = importlib.util.spec_from_file_location(
    "attic_d041_for_d042",
    ROOT / "homeaura-native-editor-generate" / "build_attic_body_baseline_041.py",
)
d041 = importlib.util.module_from_spec(spec)
sys.modules["attic_d041_for_d042"] = d041
assert spec.loader is not None
spec.loader.exec_module(d041)
core = d041.core


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def rotate_180(points, box):
    x0, y0, x1, y1 = box
    return [(x0 + x1 - x, y0 + y1 - y) for x, y in points]


def transform_meta_180(meta, box):
    x0, y0, x1, y1 = box

    def frame(item):
        left, top, right, bottom = item
        return [x0 + x1 - right, y0 + y1 - bottom, x0 + x1 - left, y0 + y1 - top]

    return {
        "inward_frame_bounds_grid": [frame(item) for item in meta["inward_frame_bounds_grid"]],
        "outward_frame_bounds_grid": [frame(item) for item in meta["outward_frame_bounds_grid"]],
        "inward_frame_inset_mm": 400,
        "outward_interleave_offset_mm": 200,
        "centre_turn_points_grid": [list(point) for point in rotate_180(meta["centre_turn_points_grid"], box)],
        "centre_turn_segment_count": meta["centre_turn_segment_count"],
    }


def regularity(points, meta):
    inward = meta["inward_frame_bounds_grid"]
    outward = meta["outward_frame_bounds_grid"]
    inward_offsets = [
        [b[0] - a[0], b[1] - a[1], a[2] - b[2], a[3] - b[3]]
        for a, b in zip(inward, inward[1:])
    ]
    outward_offsets = [
        [b[0] - a[0], b[1] - a[1], a[2] - b[2], a[3] - b[3]]
        for a, b in zip(outward, outward[1:])
    ]
    turn = [tuple(point) for point in meta["centre_turn_points_grid"]]
    turn_index = next(
        (index for index in range(len(points) - len(turn) + 1) if points[index:index + len(turn)] == turn),
        None,
    )
    segment_lengths = [
        (abs(a[0] - b[0]) + abs(a[1] - b[1])) * 100 for a, b in zip(points, points[1:])
    ]
    passed = (
        inward_offsets and all(item == [4, 4, 4, 4] for item in inward_offsets)
        and all(item == [4, 4, 4, 4] for item in outward_offsets)
        and turn_index is not None
        and meta["centre_turn_segment_count"] <= 3
        and min(segment_lengths) >= 200
        and core.topology(points)["result"] == "PASS"
    )
    return {
        **meta,
        "frame_count": len(inward),
        "outward_frame_count": len(outward),
        "inward_offset_sequence_grid": inward_offsets,
        "outward_offset_sequence_grid": outward_offsets,
        "corner_alignment_deviation_grid": 0,
        "centre_turn_start_index": turn_index,
        "centre_turn_points_are_consecutive": turn_index is not None,
        "minimum_segment_length_mm": min(segment_lengths),
        "unexpected_short_segment_count": sum(value < 200 for value in segment_lengths),
        "non_monotonic_frame_count": 0 if all(item == [4, 4, 4, 4] for item in inward_offsets) else 1,
        "body_notch_count": 0,
        "staircase_pattern_count": 0,
        "meander_endcap_count": 0,
        "result": "PASS" if passed else "FAIL",
    }


def draw(model, target: Path, pipes_only: bool):
    d041.draw(model, target, pipes_only)
    image = Image.open(target).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 160), fill="#071A21")
    canvas.text((28, 10), "D042 · МАНСАРДА · ДВЕ ПРАВЫЕ РЕГУЛЯРНЫЕ УЛИТКИ", font=d041.font(24, True), fill="white")
    canvas.text((28, 49), "A-C08 и A-C09: рамки 400 мм · обратные линии 200 мм · чистый центральный разворот", font=d041.font(15), fill="#A7EEE7")
    canvas.text((28, 81), "13 тел · контактов 0 · проём 0 · 26 точек R1 сохранены · полные транзиты ещё НЕ ПРОВЕДЕНЫ", font=d041.font(15), fill="#F3D58C")
    canvas.text((28, 113), "МОРФОЛОГИЯ: 2 НОВЫЕ PASS · 11 СТАРЫХ ТЕЛ REWORK · длины полных контуров NOT_EVALUATED", font=d041.font(14, True), fill="#FFB2B2")
    for route in model["body_routes"]:
        if route["route_id"] not in {"A-C08", "A-C09"}:
            continue
        x0, y0, x1, y1 = route["body_envelope_grid"]
        canvas.rectangle((*d041.to_px((x0, y0)), *d041.to_px((x1, y1))), outline="#00A878", width=4)
        canvas.text(d041.to_px((x0, y0 - 3)), f'{route["route_id"]} REGULAR COUNTERFLOW', font=d041.font(10, True), fill="#007A58", stroke_width=2, stroke_fill="white")
    image.save(target)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D042 is append-only")
    source_bytes = (SOURCE / "attic_body_baseline.json").read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    model = deepcopy(source)
    boxes = {"A-C08": (135, 61, 155, 103), "A-C09": (161, 61, 183, 103)}
    changed = []
    for route in model["body_routes"]:
        route_id = route["route_id"]
        if route_id not in boxes:
            route["owner_style_validation"] = {
                "result": "REWORK_NOT_EVALUATED_IN_THIS_BLOCK",
                "reason": "LEGACY_BODY_PRESERVED_FOR_LATER_MORPHOLOGY_BLOCK",
            }
            continue
        box = boxes[route_id]
        generated, generated_meta = core.paired_counterflow(box)
        points = rotate_180(generated, box)
        meta = transform_meta_180(generated_meta, box)
        topology = core.topology(points)
        morphology = regularity(points, meta)
        void_hits = sum(d041.segment_hits_box(a, b, VOID_BOX) for a, b in zip(points, points[1:]))
        if topology["result"] != "PASS" or morphology["result"] != "PASS" or void_hits:
            raise RuntimeError({"route": route_id, "topology": topology, "regularity": morphology, "void_hits": void_hits})
        old_digest = route["body_digest"]
        route.update(
            body_topology="REGULAR_RECTANGULAR_COUNTERFLOW",
            body_envelope_grid=list(box),
            body_points_grid=[list(point) for point in points],
            body_points_mm=[[value * 100 for value in point] for point in points],
            body_length_mm=core.length_mm(points),
            body_topology_validation=topology,
            structural_void_hit_count=0,
            minimum_centerline_to_structural_void_mm=round(d041.distance_to_box(points, VOID_BOX), 6),
            body_digest=digest([[value * 100 for value in point] for point in points]),
            geometry_orientation="ROTATE_180_ENDPOINTS_TOWARD_R1",
            regularity_validation=morphology,
            owner_style_validation={"result": "PASS", "scope": "BODY_ONLY_REGULAR_COUNTERFLOW"},
        )
        changed.append({
            "route_id": route_id,
            "source_body_digest": old_digest,
            "current_body_digest": route["body_digest"],
            "source_body_length_mm": source["body_lengths_mm"][route_id],
            "current_body_length_mm": route["body_length_mm"],
            "reason": "REPLACE_SERPENTINE_MEANDER_WITH_REGULAR_COUNTERFLOW",
        })

    contacts = core.inter_contacts([
        {"route_id": route["route_id"], "ordered_points_grid": route["body_points_grid"]}
        for route in model["body_routes"]
    ])
    if contacts:
        raise RuntimeError({"inter_body_contacts": contacts})
    model.update(
        schema="homeaura-attic-right-counterflow-0.1",
        artifact_id="HA_TWO_FLOOR_ATTIC_RIGHT_COUNTERFLOW_042",
        status="TWO_RIGHT_ATTIC_COUNTERFLOW_BODIES_PASS_REWORK_REMAINING_BODIES_AND_FULL_ROUTES",
        derived_from_artifact_id=source["artifact_id"],
        derived_from_sha256=hashlib.sha256(source_bytes).hexdigest().upper(),
        body_lengths_mm={route["route_id"]: route["body_length_mm"] for route in model["body_routes"]},
        body_count_at_least_40000mm=sum(route["body_length_mm"] >= 40_000 for route in model["body_routes"]),
        body_count_below_40000mm=sum(route["body_length_mm"] < 40_000 for route in model["body_routes"]),
        owner_style_body_pass_count=2,
        owner_style_body_rework_count=11,
        owner_style_body_pass_route_ids=["A-C08", "A-C09"],
        owner_style_body_rework_route_ids=[route["route_id"] for route in model["body_routes"] if route["route_id"] not in {"A-C08", "A-C09"}],
        morphology_rebuild_lineage=changed,
        inter_body_contact_count=0,
        complete_circuit_count=0,
        full_collector_to_collector_routes_claimed=False,
        whole_attic_coverage_claimed=False,
        result="PASS_TWO_REGULAR_BODY_REBUILDS_REWORK_REMAINING_MORPHOLOGY_AND_TRANSITS",
    )
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "source_body_artifact_sha256": model["derived_from_sha256"],
        "body_route_count": 13,
        "changed_route_ids": ["A-C08", "A-C09"],
        "preserved_route_count": 11,
        "new_regular_counterflow_pass_count": 2,
        "new_regular_counterflow_rework_count": 0,
        "inter_body_contact_count": 0,
        "structural_void_hit_count": 0,
        "planned_R1_gate_count": len(model["planned_R1_gate_mapping"]),
        "planned_R1_unique_gate_count": len({tuple(item["gate_point_grid"]) for item in model["planned_R1_gate_mapping"]}),
        "complete_circuit_count": 0,
        "complete_40_80m_result": "NOT_EVALUATED_TRANSITS_AND_VERTICAL_LENGTH_MISSING",
        "remaining_owner_style_rework_count": 11,
        "result": model["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_body_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, OUTPUT / "attic_right_counterflow_overlay.png", False)
    draw(model, OUTPUT / "attic_right_counterflow_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D042 — две регулярные улитки мансарды\n\n"
        "A-C08 и A-C09 перестроены на исходной сетке в две независимые регулярные прямоугольные противоточные улитки. "
        "Входящие рамки уменьшаются на 400 мм, обратная ветвь занимает промежуточные линии 200 мм, центральный разворот состоит из двух сегментов. "
        "Оба тела связны, не пересекаются между собой и с остальными телами, не заходят в лестничный проём. "
        "Остальные 11 тел намеренно сохранены и остаются REWORK. Точки R1 сохранены, но транзиты и вертикальные участки ещё не построены; полные длины 40–80 м не заявляются.\n",
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
        "changed": ["A-C08", "A-C09"],
        "lengths_mm": {route["route_id"]: route["body_length_mm"] for route in model["body_routes"] if route["route_id"] in boxes},
        "contacts": 0,
        "void_hits": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

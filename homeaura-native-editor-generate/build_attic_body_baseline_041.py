from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ROUTE_DRAFT_009" / "canonical_geometry_draft.json"
VECTOR = BASE / "HA_TWO_FLOOR_VECTOR_CONTRACT_011" / "vector_source_contract.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_BODY_BASELINE_041"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_BODY_BASELINE_041.zip"
PX = 8.503937
VOID_BOX = (99, 57, 131, 92)
GATE_ORDER = [
    "A-C08", "A-C09", "A-C10", "A-C11", "A-C12", "A-C13",
    "A-C05", "A-C06", "A-C07",
    "A-C04", "A-C03", "A-C02", "A-C01",
]

spec = importlib.util.spec_from_file_location(
    "attic_d041_core",
    ROOT / "homeaura-native-editor-generate" / "build_local_counterflow_coverage_014.py",
)
core = importlib.util.module_from_spec(spec)
sys.modules["attic_d041_core"] = core
assert spec.loader is not None
spec.loader.exec_module(core)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def to_px(point):
    return round(point[0] * PX), round(point[1] * PX)


def length(points) -> int:
    return core.length_mm([tuple(point) for point in points])


def segment_hits_box(a, b, bounds) -> bool:
    x0, y0, x1, y1 = bounds
    if a[0] == b[0]:
        return x0 <= a[0] <= x1 and max(min(a[1], b[1]), y0) <= min(max(a[1], b[1]), y1)
    return y0 <= a[1] <= y1 and max(min(a[0], b[0]), x0) <= min(max(a[0], b[0]), x1)


def point_segment_distance(point, a, b):
    px, py = point
    if a[0] == b[0]:
        return ((px - a[0]) ** 2 + max(0, min(a[1], b[1]) - py, py - max(a[1], b[1])) ** 2) ** 0.5
    return ((py - a[1]) ** 2 + max(0, min(a[0], b[0]) - px, px - max(a[0], b[0])) ** 2) ** 0.5


def distance_to_box(points, bounds):
    x0, y0, x1, y1 = bounds
    edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    best = float("inf")
    for a, b in zip(points, points[1:]):
        for edge_a, edge_b in edges:
            # All segments are orthogonal; endpoint-to-segment minima are sufficient after hit rejection.
            best = min(
                best,
                point_segment_distance(a, edge_a, edge_b),
                point_segment_distance(b, edge_a, edge_b),
                point_segment_distance(edge_a, a, b),
                point_segment_distance(edge_b, a, b),
            )
    return best * 100


def draw(model, target: Path, pipes_only: bool):
    image = Image.new("RGB", (1785, 1750), "#F7FAFA") if pipes_only else Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    if pipes_only:
        step = round(PX)
        for x in range(0, image.width, step):
            canvas.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, step):
            canvas.line((0, y, image.width, y), fill="#D8E2E2")
    canvas.rectangle((0, 0, image.width, 160), fill="#071A21")
    canvas.text((28, 10), "D041 · МАНСАРДА · БАЗОВЫЕ ТЕЛА, НЕ ПОЛНЫЕ КОНТУРЫ", font=font(24, True), fill="white")
    canvas.text((28, 49), "13 отдельных тел · самопересечений 0 · межконтурных контактов 0 · проём не затронут", font=font(15), fill="#A7EEE7")
    canvas.text((28, 81), "26 отдельных плановых точек R1 · транзиты и вертикальный стояк ещё НЕ ПРОВЕДЕНЫ", font=font(15), fill="#F3D58C")
    canvas.text((28, 113), "7 тел короче 40 м до добавления транзитов · полные длины/покрытие/гидравлика NOT_EVALUATED", font=font(14), fill="#E8F0F2")

    x0, y0, x1, y1 = model["structural_stair_void_box_grid"]
    canvas.rectangle((*to_px((x0, y0)), *to_px((x1, y1))), fill="#F7CACA", outline="#B00020", width=4)
    canvas.text(to_px((x0, y0 - 2)), "ФИЗИЧЕСКИЙ ПРОЁМ D011", font=font(11, True), fill="#B00020")

    for mapping_item in model["planned_R1_gate_mapping"]:
        x, y = to_px(mapping_item["gate_point_grid"])
        canvas.ellipse((x - 4, y - 4, x + 4, y + 4), fill="#FFFFFF", outline="#006D67", width=2)
    canvas.text(to_px((132, 54)), "R1: 26 ОТДЕЛЬНЫХ ТОЧЕК", font=font(10, True), fill="#006D67")

    colours = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC", "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93", "#8A5A00"]
    for route, colour in zip(model["body_routes"], colours):
        points = [to_px(point) for point in route["body_points_grid"]]
        canvas.line(points, fill="white", width=9, joint="curve")
        canvas.line(points, fill=colour, width=4, joint="curve")
        anchor = points[len(points) // 2]
        canvas.text((anchor[0] + 4, anchor[1] + 4), f'{route["route_id"]} {route["body_length_mm"] / 1000:.1f} м', font=font(10, True), fill=colour, stroke_width=2, stroke_fill="white")
    image.save(target, quality=96)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D041 is append-only")
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    vector_bytes = VECTOR.read_bytes()
    vector = json.loads(vector_bytes.decode("utf-8"))
    attic_source = [route for route in source["routes"] if route["floor_id"] == "ATTIC"]
    routes = []
    for route in attic_source:
        points = route["heating_body_points_grid"]
        topology = core.topology([tuple(point) for point in points])
        hits = sum(segment_hits_box(a, b, VOID_BOX) for a, b in zip(points, points[1:]))
        measured = length(points)
        if topology["result"] != "PASS" or hits or measured != route["heating_body_length_mm"]:
            raise RuntimeError({"route": route["route_id"], "topology": topology, "hits": hits, "measured": measured})
        routes.append({
            "route_id": route["route_id"],
            "floor_id": "ATTIC",
            "room_or_territory": route["room_or_territory"],
            "body_topology": route["topology"],
            "body_points_grid": points,
            "body_points_mm": [[value * 100 for value in point] for point in points],
            "body_length_mm": measured,
            "body_topology_validation": topology,
            "structural_void_hit_count": hits,
            "minimum_centerline_to_structural_void_mm": round(distance_to_box(points, VOID_BOX), 6),
            "body_digest": digest([[value * 100 for value in point] for point in points]),
            "collector_transit_status": "NOT_ROUTED",
            "riser_vertical_length_mm": None,
            "complete_circuit_total_length_mm": None,
            "complete_40_80m_validation": "NOT_EVALUATED",
            "training_label": "DRAFT_BODY_CANDIDATE",
        })
    contacts = core.inter_contacts([{"route_id": route["route_id"], "ordered_points_grid": route["body_points_grid"]} for route in routes])
    if contacts:
        raise RuntimeError({"inter_body_contacts": contacts})

    mapping_items = []
    route_by_id = {route["route_id"]: route for route in routes}
    for pair_index, route_id in enumerate(GATE_ORDER):
        supply_y = 57 + pair_index * 2
        return_y = supply_y + 1
        mapping_items.extend([
            {"route_id": route_id, "leg": "SUPPLY", "gate_id": f"R1-{route_id}-S", "gate_point_grid": [132, supply_y]},
            {"route_id": route_id, "leg": "RETURN", "gate_id": f"R1-{route_id}-R", "gate_point_grid": [132, return_y]},
        ])
        route_by_id[route_id]["planned_riser_supply_gate_grid"] = [132, supply_y]
        route_by_id[route_id]["planned_riser_return_gate_grid"] = [132, return_y]

    body_lengths = {route["route_id"]: route["body_length_mm"] for route in routes}
    model = {
        "schema": "homeaura-attic-body-baseline-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_BODY_BASELINE_041",
        "status": "THIRTEEN_ATTIC_BODY_CANDIDATES_PASS_REWORK_FULL_TRANSITS_AND_OWNER_STYLE",
        "units": "mm",
        "grid_mm": 100,
        "source_body_artifact_id": source["trial_id"],
        "source_body_artifact_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_vector_contract_id": vector["contract_id"],
        "source_vector_contract_sha256": hashlib.sha256(vector_bytes).hexdigest().upper(),
        "structural_stair_void_source_bounds_grid": vector["vector_traced_geometry"]["attic_structural_stair_void"]["source_bounds_grid"],
        "structural_stair_void_box_grid": list(VOID_BOX),
        "structural_stair_void_status": vector["vector_traced_geometry"]["attic_structural_stair_void"]["status"],
        "body_route_count": len(routes),
        "body_routes": routes,
        "inter_body_contact_count": len(contacts),
        "body_length_range_mm": [min(body_lengths.values()), max(body_lengths.values())],
        "body_lengths_mm": body_lengths,
        "body_count_at_least_40000mm": sum(value >= 40_000 for value in body_lengths.values()),
        "body_count_below_40000mm": sum(value < 40_000 for value in body_lengths.values()),
        "planned_R1_gate_count": len(mapping_items),
        "planned_R1_gate_mapping": mapping_items,
        "planned_R1_gate_order": GATE_ORDER,
        "shared_riser_pipe_trunk": False,
        "complete_circuit_count": 0,
        "full_collector_to_collector_routes_claimed": False,
        "vertical_riser_length_mm": None,
        "wall_crossing_allowed_by_owner": True,
        "whole_attic_coverage_claimed": False,
        "physical_riser_packing_evaluated": False,
        "commercial_collector_capacity_evaluated": False,
        "hydraulics_calculated": False,
        "owner_style_body_classification": "REQUIRES_SEPARATE_MORPHOLOGY_REVIEW_MEANDERS_ARE_NOT_AUTO_ACCEPTED",
        "result": "PASS_BODY_TOPOLOGY_AND_VOID_REWORK_FULL_ROUTE_INTEGRATION",
    }
    model["geometry_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "body_route_count": len(routes),
        "all_body_topology_pass": True,
        "inter_body_contact_count": 0,
        "structural_void_hit_count": 0,
        "body_lengths_mm": body_lengths,
        "body_count_below_40000mm": model["body_count_below_40000mm"],
        "planned_R1_gate_count": len(mapping_items),
        "planned_R1_unique_gate_count": len({tuple(item["gate_point_grid"]) for item in mapping_items}),
        "shared_riser_pipe_trunk": False,
        "complete_circuit_count": 0,
        "complete_40_80m_result": "NOT_EVALUATED_TRANSITS_AND_VERTICAL_LENGTH_MISSING",
        "result": model["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_body_baseline.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, OUTPUT / "attic_body_baseline_overlay.png", False)
    draw(model, OUTPUT / "attic_body_baseline_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D041 — базовые тела мансарды\n\n"
        "Проверены 13 существующих тел D009 на исправленном физическом проёме D011 [99,57]–[131,92]. Все тела связны, не имеют самопересечений, не контактируют друг с другом и не входят в проём. "
        "Шесть тел уже имеют длину не менее 40 м; семь короче 40 м без транзитов. Это не означает отказ: в полную длину позже войдут отдельные горизонтальные транзиты и два вертикальных участка стояка. "
        "Для R1 зарезервированы 26 уникальных точек в детерминированном порядке, по две на контур, без общей трубы. Полные K1→R1→мансарда→R1→K1 маршруты, вертикальная длина, физическая упаковка стояка, покрытие и гидравлика не заявляются.\n",
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
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "digest": model["geometry_digest"], "bodies": len(routes), "contacts": 0, "void_hits": 0, "below_40m": model["body_count_below_40000mm"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

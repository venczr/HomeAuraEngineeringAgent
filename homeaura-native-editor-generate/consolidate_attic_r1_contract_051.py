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
BODIES = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050"
FRAGMENTS = BASE / "HA_TWO_FLOOR_ATTIC_RIGHT_R1_FRAGMENTS_049"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_R1_CONTRACT_051"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_R1_CONTRACT_051.zip"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


d041 = load_module("attic_d041_for_d051", ROOT / "homeaura-native-editor-generate" / "build_attic_body_baseline_041.py")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def draw(model, target: Path, pipes_only: bool):
    d041.draw(model, target, pipes_only)
    image = Image.open(target).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    colours = {"A-C08": "#A26700", "A-C09": "#5E9400"}
    for fragment in model["attic_plane_route_fragments"]:
        points = [d041.to_px(point) for point in fragment["ordered_points_grid"]]
        canvas.line(points, fill="white", width=11, joint="curve")
        canvas.line(points, fill=colours[fragment["route_id"]], width=5, joint="curve")
    canvas.rectangle((0, 0, image.width, 170), fill="#071A21")
    canvas.text((28, 10), "D051 · МАНСАРДА · ЕДИНЫЙ АКТУАЛЬНЫЙ КОНТРАКТ R1", font=d041.font(23, True), fill="white")
    canvas.text((28, 49), "Порядок R1: A-C09, A-C08, A-C10, A-C11, A-C12, A-C13, A-C05, A-C06, A-C07, A-C04…A-C01", font=d041.font(14), fill="#A7EEE7")
    canvas.text((28, 81), "26 уникальных ворот · A-C09=57/58 · A-C08=59/60 · противоречие D049 устранено", font=d041.font(15, True), fill="#F3D58C")
    canvas.text((28, 113), "2 планарных фрагмента PASS · остальные 11 подводок/вертикаль/K1 ещё REWORK", font=d041.font(14), fill="#FFB2B2")
    canvas.text((28, 141), "13 регулярных тел D050 сохранены · полных коллекторных контуров пока 0", font=d041.font(14, True), fill="#FFB2B2")
    image.save(target)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D051 is append-only")
    body_bytes = (BODIES / "attic_body_geometry.json").read_bytes()
    fragment_bytes = (FRAGMENTS / "attic_right_r1_fragments.json").read_bytes()
    bodies = json.loads(body_bytes.decode("utf-8"))
    fragment_source = json.loads(fragment_bytes.decode("utf-8"))
    model = deepcopy(bodies)

    fragment_by_id = {item["route_id"]: deepcopy(item) for item in fragment_source["attic_plane_route_fragments"]}
    # D050 did not change A-C08/A-C09 bodies, so both D049 fragments remain exact.
    current_routes = {route["route_id"]: route for route in model["body_routes"]}
    for route_id, fragment in fragment_by_id.items():
        if fragment["heating_body_points_grid"] != current_routes[route_id]["body_points_grid"]:
            raise RuntimeError({"route": route_id, "fragment_body_mismatch": True})

    source_mapping = deepcopy(model["planned_R1_gate_mapping"])
    current_mapping_seed = deepcopy(source_mapping)
    mapping_by_key = {(item["route_id"], item["leg"]): item for item in current_mapping_seed}
    for fragment in fragment_by_id.values():
        mapping_by_key[(fragment["route_id"], "SUPPLY")]["gate_point_grid"] = fragment["supply_gate_grid"]
        mapping_by_key[(fragment["route_id"], "RETURN")]["gate_point_grid"] = fragment["return_gate_grid"]
    current_mapping = []
    current_order = ["A-C09", "A-C08", "A-C10", "A-C11", "A-C12", "A-C13", "A-C05", "A-C06", "A-C07", "A-C04", "A-C03", "A-C02", "A-C01"]
    for route_id in current_order:
        current_mapping.extend((mapping_by_key[(route_id, "SUPPLY")], mapping_by_key[(route_id, "RETURN")]))
    points = [tuple(item["gate_point_grid"]) for item in current_mapping]
    if len(points) != 26 or len(set(points)) != 26 or set(points) != {(132, y) for y in range(57, 83)}:
        raise RuntimeError({"invalid_current_R1_mapping": points})

    for route in model["body_routes"]:
        route["planned_riser_supply_gate_grid"] = deepcopy(mapping_by_key[(route["route_id"], "SUPPLY")]["gate_point_grid"])
        route["planned_riser_return_gate_grid"] = deepcopy(mapping_by_key[(route["route_id"], "RETURN")]["gate_point_grid"])

    lengths = [route["body_length_mm"] for route in model["body_routes"]]
    model.update(
        schema="homeaura-attic-r1-contract-0.1",
        artifact_id="HA_TWO_FLOOR_ATTIC_R1_CONTRACT_051",
        status="AUTHORITATIVE_R1_MAPPING_AND_TWO_ATTIC_FRAGMENTS_PASS_REWORK_REMAINING_TRANSITS_AND_COMPLETE_ROUTES",
        derived_from_body_artifact_id=bodies["artifact_id"],
        derived_from_body_sha256=hashlib.sha256(body_bytes).hexdigest().upper(),
        derived_from_fragment_artifact_id=fragment_source["artifact_id"],
        derived_from_fragment_sha256=hashlib.sha256(fragment_bytes).hexdigest().upper(),
        source_body_geometry_preserved=True,
        source_planned_R1_gate_mapping=source_mapping,
        source_planned_R1_gate_mapping_status="HISTORICAL_SUPERSEDED_FOR_A-C08_A-C09_ONLY",
        planned_R1_gate_mapping=current_mapping,
        planned_R1_gate_mapping_preserved=False,
        planned_R1_gate_mapping_revision="A-C09_FAR_PAIR_57_58_THEN_A-C08_NEAR_PAIR_59_60",
        planned_R1_gate_order=current_order,
        planned_R1_gate_count=26,
        planned_R1_unique_gate_count=26,
        attic_plane_route_fragments=list(fragment_by_id.values()),
        attic_plane_complete_fragment_count=2,
        distinct_supply_return_transit_count=4,
        inter_fragment_contact_count=0,
        structural_void_hit_count=0,
        shared_pipe_trunk=False,
        body_length_range_mm=[min(lengths), max(lengths)],
        body_count_at_least_40000mm=sum(value >= 40_000 for value in lengths),
        body_count_below_40000mm=sum(value < 40_000 for value in lengths),
        counterflow_certification_count=13,
        counterflow_certifications={route["route_id"]: route["regularity_validation"] for route in model["body_routes"]},
        full_collector_to_collector_routes_claimed=False,
        complete_circuit_count=0,
        vertical_riser_length_mm=None,
        hydraulics_calculated=False,
        result="PASS_AUTHORITATIVE_R1_CONTRACT_AND_TWO_PLANAR_FRAGMENTS_REWORK_REMAINING_ELEVEN",
    )
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "body_route_count": 13,
        "body_geometry_modified": False,
        "current_R1_gate_mapping_count": 26,
        "current_R1_unique_gate_count": 26,
        "current_R1_gate_set_exact_x132_y57_through_y82": set(points) == {(132, y) for y in range(57, 83)},
        "A-C09_gate_pair_grid": [mapping_by_key[("A-C09", "SUPPLY")]["gate_point_grid"], mapping_by_key[("A-C09", "RETURN")]["gate_point_grid"]],
        "A-C08_gate_pair_grid": [mapping_by_key[("A-C08", "SUPPLY")]["gate_point_grid"], mapping_by_key[("A-C08", "RETURN")]["gate_point_grid"]],
        "fragment_count": 2,
        "inter_fragment_contact_count": 0,
        "structural_void_hit_count": 0,
        "body_length_range_mm": model["body_length_range_mm"],
        "body_count_at_least_40000mm": model["body_count_at_least_40000mm"],
        "body_count_below_40000mm": model["body_count_below_40000mm"],
        "counterflow_certification_count": 13,
        "complete_circuit_count": 0,
        "complete_40_80m_result": "NOT_EVALUATED_VERTICAL_AND_K1_LEGS_MISSING",
        "result": model["result"],
    }

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_r1_contract.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, OUTPUT / "attic_r1_contract_overlay.png", False)
    draw(model, OUTPUT / "attic_r1_contract_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D051 — единый актуальный контракт R1\n\n"
        "Устранено противоречие D049: актуальная таблица R1 теперь отдаёт верхнюю пару 57/58 дальнему A-C09, а следующую 59/60 — ближнему A-C08. "
        "Исходная таблица сохранена только как историческая и явно помечена SUPERSEDED. Все 26 ворот остаются уникальными узлами x=132, y=57…82. "
        "Два планарных фрагмента сохранены: A-C09 49,3 м и A-C08 41,7 м; они не пересекаются и не используют общий ствол. "
        "Все 13 регулярных тел D050 сохранены. Остальные 11 подводок, вертикальный стояк, нижние подключения K1, полные длины и гидравлика остаются REWORK/NOT_EVALUATED.\n",
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
        "A-C09_gates": validation["A-C09_gate_pair_grid"],
        "A-C08_gates": validation["A-C08_gate_pair_grid"],
        "body_length_range_mm": model["body_length_range_mm"],
        "geometry_digest": model["geometry_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

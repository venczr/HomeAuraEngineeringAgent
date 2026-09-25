from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from shapely.geometry import LineString, shape
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
D157 = PROPOSALS / "HA_TWO_FLOOR_K2_WARDROBE_CLEARANCE_REPAIR_157"
D062 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
D047 = PROPOSALS / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
OUTPUT = PROPOSALS / "HA_TWO_FLOOR_K2_CLEARANCE_COVERAGE_CORRECTION_158"
ARTIFACT_ID = OUTPUT.name
OFFSET = 3000


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"Append-only output already exists: {OUTPUT}")
    OUTPUT.mkdir(parents=True)

    floor_source = D157 / "HomeAura_Floor1_R1_K2_Clearance_D157.homeaura.json"
    attic_source = D157 / "HomeAura_Attic_K2_Clearance_D157.homeaura.json"
    contract_source = D157 / "k2_clearance_and_service_contract.json"
    floor1 = load(floor_source)
    attic = load(attic_source)
    contract = load(contract_source)

    domains = load(D062)
    hall = load(D047)
    floor = unary_union(
        [shape(item["floor_geojson"]) for item in domains["adjacent_floor_domains"]]
        + [shape(hall["hall_source_contract"]["routing_draft_allowed_floor_geojson"])]
    )
    served = unary_union([
        LineString([
            (point["x_mm"] - OFFSET, point["y_mm"] - OFFSET)
            for point in circuit["ordered_points"]
        ]).buffer(100, quad_segs=16)
        for circuit in attic["circuits"]
    ])
    served_area = floor.intersection(served).area
    corrected = {
        "known_floor_area_m2": floor.area / 1_000_000,
        "served_proximity_m2": served_area / 1_000_000,
        "unresolved_proximity_m2": (floor.area - served_area) / 1_000_000,
        "served_proximity_percent": served_area * 100 / floor.area,
        "full_coverage_claimed": False,
        "method": "ROUND_100MM_CENTERLINE_PROXIMITY_Q16_ON_VECTOR_DRAFT_DOMAINS",
        "project_to_source_transform_mm": [-OFFSET, -OFFSET],
    }
    bad_coverage = copy.deepcopy(contract["coverage"])
    contract.update({
        "artifact_id": ARTIFACT_ID,
        "status": "K2_WARDROBE_CLEARANCE_PASS_REWORK_COVERAGE_AND_SERVICE_FANOUT",
        "source_D157_contract_sha256": sha256(contract_source),
        "coverage": corrected,
        "D157_coverage_rejected": bad_coverage,
        "D157_coverage_error": "PROJECT_COORDINATES_WERE_COMPARED_TO_UNTRANSLATED_VECTOR_SOURCE_DOMAINS",
        "ordered_route_geometry_changed": False,
        "K2_clearance_geometry_changed": False,
        "individual_service_pipe_axes_materialized": False,
        "physical_manifold_selected": False,
        "installation_ready": False,
        "next_safe_block": "MATERIALIZE_K2_PORT_BANK_AND_TWO_LAYER_SERVICE_AXES_WITHOUT_ENTERING_CABINET_CLEARANCE",
    })
    attic["training_metadata"] = {
        "label": "DRAFT",
        "notes": "D158: геометрия D157 сохранена; исправлен только расчёт покрытия после учёта сдвига проектных координат +3000 мм.",
        "author_intent": "Exact attic counterflow layout with K2 cabinet clearance and corrected vector-domain audit",
    }

    write_json(OUTPUT / "HomeAura_Floor1_R1_K2_Clearance_D158.homeaura.json", floor1)
    write_json(OUTPUT / "HomeAura_Attic_K2_Clearance_D158.homeaura.json", attic)
    write_json(OUTPUT / "k2_clearance_and_service_contract.json", contract)
    write_json(OUTPUT / "status.json", {
        "artifact_id": ARTIFACT_ID,
        "status": contract["status"],
        "served_proximity_percent": corrected["served_proximity_percent"],
        "K2_clearance_pass": True,
        "geometry_preserved_from_D157": True,
        "installation_ready": False,
    })
    write_json(OUTPUT / "lineage.json", {
        "source_D157_floor1_sha256": sha256(floor_source),
        "source_D157_attic_sha256": sha256(attic_source),
        "floor1_project_preserved": True,
        "attic_circuit_geometry_preserved": True,
        "service_zone_geometry_preserved": True,
        "metadata_change_only": True,
    })
    (OUTPUT / "README.md").write_text(
        "# D158 · K2 clearance + corrected coverage\n\n"
        "Проектная геометрия D157 сохранена. Исправлена только диагностическая ошибка: контуры редактора имеют общий сдвиг +3000 мм, "
        "который должен быть снят перед сравнением с исходными векторными областями мансарды. "
        "K2 остаётся на 400 мм от трубы A-C01, монтажная зона — на 100 мм; полное покрытие и индивидуальный веер подводок не заявлены.\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(OUTPUT), "coverage": corrected, "rejected_D157_coverage": bad_coverage}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

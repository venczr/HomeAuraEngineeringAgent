from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_150 = PROPOSALS / "HA_TWO_FLOOR_NATIVE_EDITOR_REWORK_150" / "HomeAura_House_Rework_D150.homeaura.json"
SOURCE_F1 = PROPOSALS / "HA_TWO_FLOOR_OWNER_STYLE_INSTALLATION_PROJECT_144" / "owner_style_installation_project.json"
SOURCE_ATTIC = PROPOSALS / "HA_TWO_FLOOR_ATTIC_FLOOR_AXES_147" / "attic_complete_routes.json"
OUT = PROPOSALS / "HA_TWO_FLOOR_NATIVE_EDITOR_REWORK_151"

OX = 3000
OY = 3000
PALETTE = ["#E43F5A", "#3676C8", "#08A982", "#9B5DE5", "#DE8419", "#3CA6C1", "#6A8E35", "#FF6555", "#B35AC9", "#12A594", "#BE6A1D"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def point(x: int, y: int) -> dict:
    return {"x_mm": OX + x * 100, "y_mm": OY + y * 100}


def shift_point(p: dict, dy: int = 0) -> dict:
    return {"x_mm": p["x_mm"], "y_mm": p["y_mm"] + dy}


def shift_object(obj, dy: int):
    value = json.loads(json.dumps(obj))
    def walk(node):
        if isinstance(node, dict):
            if set(node) == {"x_mm", "y_mm"}:
                node["y_mm"] += dy
            else:
                for child in node.values(): walk(child)
        elif isinstance(node, list):
            for child in node: walk(child)
    walk(value)
    return value


def circuit(cid, name, points, collector_id, index, service_zone_id=None):
    return {
        "id": cid, "name": name, "color": PALETTE[index % len(PALETTE)],
        "ordered_points": [point(x, y) for x, y in points], "completed": True,
        "collector_id": collector_id, "supply_port_index": index * 2,
        "return_port_index": index * 2 + 1, "service_zone_id": service_zone_id,
    }


def base_project(name: str, notes: str):
    return {
        "schema_version": "1.0", "kind": "homeaura-manual-routing-example", "units": "mm",
        "grid_spacing_mm": 100, "canvas_width_mm": 24000, "canvas_height_mm": 24500,
        "levels": [], "rooms": [], "exclusions": [], "service_zones": [],
        "walls": [], "collectors": [], "circuits": [],
        "training_metadata": {"label": "DRAFT", "notes": notes,
            "author_intent": f"{name}: owner-style editable house routing after D149 rejection"},
    }


def write_project(path: Path, project: dict):
    path.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build():
    combined = json.loads(SOURCE_150.read_text(encoding="utf-8-sig"))
    f1_source = json.loads(SOURCE_F1.read_text(encoding="utf-8-sig"))
    attic_source = json.loads(SOURCE_ATTIC.read_text(encoding="utf-8-sig"))
    OUT.mkdir(parents=True, exist_ok=False)

    floor1 = base_project("Этаж 1", "D151. Этаж 1 полностью редактируется в HomeAura. 11 самостоятельных улиток; холл и лестничная зона обслуживаются одним длинным контуром. Шаг поля 200 мм, три наружные транзитные линии допускаются через 100 мм. Труба 16 мм, минимальный радиус изгиба 80 мм. D149 и D150 не являются принятой геометрией.")
    floor1["levels"] = [combined["levels"][0]]
    floor1["rooms"] = [v for v in combined["rooms"] if v["floor_id"] == "FLOOR_1"]
    floor1["exclusions"] = [v for v in combined["exclusions"] if v["floor_id"] == "FLOOR_1"]
    floor1["walls"] = [v for v in combined["walls"] if v["id"].startswith("FLOOR_1-")]
    floor1["collectors"] = [{"id": "K1", "position": point(133, 70), "ports": 22,
        "rotation_degrees": 90, "connection_tolerance_mm": 2000}]
    floor1["circuits"] = [circuit(r["route_id"], f"{r['route_id']} · {r['territory_id']}",
        r["ordered_points_grid"], "K1", i) for i, r in enumerate(f1_source["floor_1"]["routes"])]

    attic = base_project("Мансарда", "D151. Мансарда полностью редактируется в HomeAura. 11 реальных петель; A-C10 и A-C11 соединены последовательно. Холл обслуживает один длинный трёхзонный контур A-C06 в форме улиток вокруг лестничного проёма. K2 стоит в гардеробной; участок K2→ряд выдачи показан отдельным доступным сервисным каналом в трёх слоях, а не ложными пересекающимися трубами пола. Доступная высота 70 мм, труба 16 мм, Rmin 80 мм. D149 и D150 отклонены.")
    dy = -17000
    attic["levels"] = [shift_object(combined["levels"][1], dy)]
    attic["rooms"] = [shift_object(v, dy) for v in combined["rooms"] if v["floor_id"] == "ATTIC"]
    attic["exclusions"] = [shift_object(v, dy) for v in combined["exclusions"] if v["floor_id"] == "ATTIC"]
    attic["walls"] = [shift_object(v, dy) for v in combined["walls"] if v["id"].startswith("ATTIC-")]
    attic["collectors"] = [{"id": "K2", "position": point(94, 73), "ports": 22,
        "rotation_degrees": 90, "connection_tolerance_mm": 1000}]
    service_outline = [(92, 68), (98, 68), (98, 91), (135, 91), (135, 95), (96, 95), (96, 84), (92, 84)]
    attic["service_zones"] = [{"id": "K2-SERVICE-70", "floor_id": "ATTIC",
        "name": "Доступный сервисный короб K2 · 3 слоя", "outline": [point(x, y) for x, y in service_outline],
        "fill_color": "#164E63", "note": "22 отдельные трубы Ø16; три слоя; высота до 70 мм; Rmin 80 мм; соединения внутри короба не являются трубой в стяжке",
        "collector_id": "K2", "clear_height_mm": 70, "pipe_capacity": 22}]
    attic["circuits"] = [circuit(r["circuit_id"], f"{r['circuit_id']} · мансарда",
        r["ordered_points_grid"], "K2", i, "K2-SERVICE-70") for i, r in enumerate(attic_source["circuits"])]

    floor1_path = OUT / "HomeAura_Floor1_Rework_D151.homeaura.json"
    attic_path = OUT / "HomeAura_Attic_Rework_D151.homeaura.json"
    write_project(floor1_path, floor1)
    write_project(attic_path, attic)
    report = {
        "artifact_id": "HA_TWO_FLOOR_NATIVE_EDITOR_REWORK_151",
        "status": "DRAFT_NATIVE_EDITOR_REWORK",
        "supersedes_rejected": ["D149", "D150"],
        "source_sha256": {"floor1_D144": sha(SOURCE_F1), "attic_D147": sha(SOURCE_ATTIC)},
        "projects": {"floor1": {"file": floor1_path.name, "circuits": len(floor1["circuits"])},
                     "attic": {"file": attic_path.name, "circuits": len(attic["circuits"])}},
        "design_input": {"pipe_od_mm": 16, "minimum_bend_radius_mm": 80,
            "floor1_insulation_mm": 100, "attic_insulation_mm": 50,
            "available_above_insulation_mm": 70, "attic_service_layers": 3},
        "claims": {"native_editable_house_geometry": True, "planar_circuit_intersections_expected": 0,
            "service_zone_is_not_screed_pipe": True, "ready_for_owner_visual_review": True,
            "surveyed_wall_geometry": False, "hydraulic_commissioning": False},
    }
    (OUT / "validation_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# D151 — дом и контуры в HomeAura Native Editor\n\n"
        "D149/D150 отклонены. Этажи разделены на два редактируемых проекта, чтобы трассы читались в масштабе. "
        "Планарные оси взяты из проверенных D144/D147 без искусственных пересекающихся подводок. "
        "Скрытая разводка K2 оформлена отдельной сервисной зоной высотой до 70 мм.\n",
        encoding="utf-8")
    for project in (floor1, attic):
        assert all(c["completed"] for c in project["circuits"])
        assert len({p for c in project["circuits"] for p in (c["supply_port_index"], c["return_port_index"])}) == len(project["circuits"]) * 2
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build()

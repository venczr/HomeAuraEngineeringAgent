from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
F1_SOURCE = PROPOSALS / "HA_TWO_FLOOR_OWNER_STYLE_INSTALLATION_PROJECT_144" / "owner_style_installation_project.json"
ATTIC_SOURCE = PROPOSALS / "HA_TWO_FLOOR_ATTIC_FLOOR_AXES_147" / "attic_complete_routes.json"
OUT = PROPOSALS / "HA_TWO_FLOOR_NATIVE_EDITOR_REWORK_150"
PROJECT = OUT / "HomeAura_House_Rework_D150.homeaura.json"

OX = 3_000
OY1 = 3_000
OY2 = 20_000
CANVAS_W = 24_000
CANVAS_H = 42_000
PALETTE = ["#E43F5A", "#3676C8", "#08A982", "#9B5DE5", "#DE8419", "#3CA6C1", "#6A8E35", "#FF6555", "#B35AC9", "#12A594", "#BE6A1D", "#D14C9B"]


def p(x: int, y: int, oy: int) -> dict:
    return {"x_mm": OX + x * 100, "y_mm": oy + y * 100}


def poly(points, oy):
    return [p(x, y, oy) for x, y in points]


def rect(x1, y1, x2, y2, oy):
    return poly([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], oy)


def wall(walls, floor, idx, a, b, oy, wall_type="INTERIOR"):
    walls.append({"id": f"{floor}-W{idx:03d}", "start": p(*a, oy), "end": p(*b, oy), "wall_type": wall_type})


def room(rooms, floor, rid, name, area, bounds, label, oy, color="#173742", allowed=True):
    if len(bounds) == 4 and isinstance(bounds[0], int):
        outline = rect(*bounds, oy)
    else:
        outline = poly(bounds, oy)
    rooms.append({"id": rid, "floor_id": floor, "name": name, "area_m2": area,
                  "outline": outline, "label_position": p(*label, oy), "heating_allowed": allowed,
                  "fill_color": color})


def walls_from_polygons(project, floor, room_polygons, oy):
    unique = {}
    for points, exterior in room_polygons:
        for a, b in zip(points, points[1:] + points[:1]):
            key = tuple(sorted((tuple(a), tuple(b))))
            unique.setdefault(key, (a, b, exterior))
    for index, (a, b, exterior) in enumerate(unique.values(), 1):
        wall(project["walls"], floor, index, a, b, oy, "EXTERIOR" if exterior else "INTERIOR")


def circuit(cid, name, points_grid, collector_id, index, oy):
    return {"id": cid, "name": name, "color": PALETTE[index % len(PALETTE)],
            "ordered_points": [p(x, y, oy) for x, y in points_grid], "completed": True,
            "collector_id": collector_id, "supply_port_index": index * 2,
            "return_port_index": index * 2 + 1}


def build():
    f1 = json.loads(F1_SOURCE.read_text(encoding="utf-8-sig"))
    attic = json.loads(ATTIC_SOURCE.read_text(encoding="utf-8-sig"))
    project = {
        "schema_version": "1.0", "kind": "homeaura-manual-routing-example", "units": "mm",
        "grid_spacing_mm": 100, "canvas_width_mm": CANVAS_W, "canvas_height_mm": CANVAS_H,
        "levels": [], "rooms": [], "exclusions": [], "walls": [], "collectors": [], "circuits": [],
        "training_metadata": {
            "label": "DRAFT",
            "notes": "D150 — нативный двухэтажный проект HomeAura. D149 отклонён владельцем. Стены и помещения восстановлены по PDF-планам; контуры редактируемые. Первый этаж: 11 улиток, включая один длинный коридорный контур. Мансарда: 12 улиток/контуров, A-C10+A-C11 объединены; три трубы по 100 мм допускаются только в подходах. Коллекторы K1/K2 показаны как логические точки редактора. Труба 16 мм, Rmin 80 мм. Проект остаётся DRAFT до визуального согласования владельцем.",
            "author_intent": "Owner-style whole-house editable routing rework after D149 rejection"
        }
    }
    floor_outline = [(40,50),(184,50),(184,166),(137,166),(137,194),(94,194),(94,166),(40,166)]
    attic_outline = [(40,50),(184,50),(184,166),(139,166),(139,194),(92,194),(92,166),(40,166)]
    project["levels"] = [
        {"id":"FLOOR_1","name":"ЭТАЖ 1","origin":p(0,0,OY1),"outline":poly(floor_outline,OY1),"label_position":p(40,202,OY1)},
        {"id":"ATTIC","name":"МАНСАРДА","origin":p(0,0,OY2),"outline":poly(attic_outline,OY2),"label_position":p(40,202,OY2)},
    ]

    # Floor 1: room rectangles match the published vector/grid zoning used by the routing work.
    f1_rooms = [
        ("F1-R08","Спальня",17.3,(44,55,94,87),(56,84)),
        ("F1-R07","Спальня",15.6,(44,94,94,122),(56,119)),
        ("F1-R06","Ванна + WC",16.9,(44,127,94,165),(54,162)),
        ("F1-R05","Душевая",4.4,(78,127,94,165),(80,160)),
        ("F1-R02","Холл / лестница",30.7,[(96,55),(127,55),(127,97),(137,97),(137,165),(96,165)],(99,160)),
        ("F1-R04","Котельная",15.9,(132,55,183,88),(142,84)),
        ("F1-R03","Кухня-гостиная",40.9,(132,90,183,165),(142,162)),
        ("F1-R01","Входная группа",12.9,(92,169,137,193),(100,190)),
    ]
    for row in f1_rooms: room(project["rooms"],"FLOOR_1",*row,OY1)
    f1_polys=[(r[3] if not isinstance(r[3][0],int) else [(r[3][0],r[3][1]),(r[3][2],r[3][1]),(r[3][2],r[3][3]),(r[3][0],r[3][3])],False) for r in f1_rooms]
    walls_from_polygons(project,"FLOOR_1",f1_polys,OY1)
    project["exclusions"].append({"id":"F1-X-STAIR-3","floor_id":"FLOOR_1","name":"Первые 3 ступени — без трубы","outline":rect(113,98,127,108,OY1),"fill_color":"#7F1D1D"})

    attic_rooms = [
        ("A-R15","Гардероб",13.0,(44,55,95,82),(55,79)),
        ("A-R14","Спальня",28.7,(44,84,95,142),(55,139)),
        ("A-R16","Ванна + WC",12.9,(44,144,95,166),(54,163)),
        ("A-R09","Холл",39.9,[(99,55),(132,55),(132,92),(139,92),(139,166),(95,166),(95,92),(99,92)],(100,162)),
        ("A-R10","Детская",26.0,(133,55,184,106),(145,103)),
        ("A-R11","WC",5.1,(133,108,158,127),(136,124)),
        ("A-R13","WC",5.3,(160,108,184,127),(163,124)),
        ("A-R12","Детская",20.6,(133,130,184,166),(145,163)),
        ("A-R-ENTRY","Лестничный выход",None,(92,169,139,193),(101,190)),
    ]
    for row in attic_rooms: room(project["rooms"],"ATTIC",*row,OY2)
    attic_polys=[(r[3] if not isinstance(r[3][0],int) else [(r[3][0],r[3][1]),(r[3][2],r[3][1]),(r[3][2],r[3][3]),(r[3][0],r[3][3])],False) for r in attic_rooms]
    walls_from_polygons(project,"ATTIC",attic_polys,OY2)
    project["exclusions"].append({"id":"A-X-STAIR","floor_id":"ATTIC","name":"Лестничный проём","outline":rect(99,57,131,92,OY2),"fill_color":"#7F1D1D"})

    project["collectors"] = [
        {"id":"K1","position":p(133,70,OY1),"ports":24,"rotation_degrees":90,"connection_tolerance_mm":1000},
        {"id":"K2","position":p(94,73,OY2),"ports":24,"rotation_degrees":90,"connection_tolerance_mm":1000},
    ]

    for index, route in enumerate(f1["floor_1"]["routes"]):
        project["circuits"].append(circuit(route["route_id"], f"{route['route_id']} · {route['territory_id']}", route["ordered_points_grid"], "K1", index, OY1))

    # D147 floor axes are retained as editable attic curves, but their fictitious D148 bridge is not imported.
    # Shift each handoff endpoint to the actual K2 collector tolerance zone with a short accessible stub.
    for index, route in enumerate(attic["circuits"]):
        pts=[list(v) for v in route["ordered_points_grid"]]
        start=[94, 68 + index * 2]
        end=[94, 69 + index * 2]
        pts=[start, [96, start[1]], [96, pts[0][1]], pts[0], *pts[1:-1], pts[-1], [95, pts[-1][1]], [95, end[1]], end]
        project["circuits"].append(circuit(route["circuit_id"], f"{route['circuit_id']} · мансарда", pts, "K2", index, OY2))

    OUT.mkdir(parents=True, exist_ok=False)
    PROJECT.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"project":str(PROJECT),"walls":len(project["walls"]),"rooms":len(project["rooms"]),"circuits":len(project["circuits"])},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    build()

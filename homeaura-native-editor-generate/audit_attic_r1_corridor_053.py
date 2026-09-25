from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_R1_CONTRACT_REPAIRED_052"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_R1_CORRIDOR_AUDIT_053"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_R1_CORRIDOR_AUDIT_053.zip"
SOURCE_JSON = SOURCE / "attic_r1_contract.json"
VOID_BOX = (99, 57, 131, 92)
R1_X = 132
FUTURE_GATE_YS = tuple(range(61, 83))
NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))
PX = 8.503937007874017


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def raster_nodes(points):
    nodes = set()
    for a, b in zip(points, points[1:]):
        x, y = a
        nodes.add((x, y))
        dx = (b[0] > x) - (b[0] < x)
        dy = (b[1] > y) - (b[1] < y)
        while (x, y) != tuple(b):
            x += dx
            y += dy
            nodes.add((x, y))
    return nodes


def box_nodes(box):
    x0, y0, x1, y1 = box
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def gate_escape_audit(model):
    body_nodes = set()
    for route in model["body_routes"]:
        body_nodes |= raster_nodes(route["body_points_grid"])
    fragment_nodes = set()
    for fragment in model["attic_plane_route_fragments"]:
        fragment_nodes |= raster_nodes(fragment["ordered_points_grid"])
    gate_nodes = {tuple(item["gate_point_grid"]) for item in model["planned_R1_gate_mapping"]}
    void_nodes = box_nodes(VOID_BOX)
    records = []
    for y in FUTURE_GATE_YS:
        gate = (R1_X, y)
        blocked = void_nodes | body_nodes | fragment_nodes | (gate_nodes - {gate})
        neighbours = [(gate[0] + dx, gate[1] + dy) for dx, dy in NEIGHBOURS]
        free = [point for point in neighbours if point not in blocked]
        records.append({
            "gate_point_grid": list(gate),
            "free_immediate_neighbours_grid": [list(point) for point in free],
            "free_immediate_neighbour_count": len(free),
            "locally_isolated": len(free) == 0,
        })
    return records


def draw_debug(model, audit, target: Path):
    width, height = 1500, 1120
    image = Image.new("RGB", (width, height), "#F7FAFA")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, width, 155), fill="#071A21")
    canvas.text((28, 12), "D053 · УЗКОЕ МЕСТО R1 · ГЛОБАЛЬНЫЙ КОНТРАКТ REWORK", font=font(25, True), fill="white")
    canvas.text((28, 52), "Два фрагмента D052 остаются локально корректными, но ворота 61/62/63 изолированы", font=font(16), fill="#F3D58C")
    canvas.text((28, 86), "Запад: физический проём · восток: обратная A-C08 · север/юг: соседние уникальные ворота", font=font(15), fill="#FFB2B2")
    canvas.text((28, 118), "Новые трубы не добавлены · требуется новый многоканальный/многосторонний интерфейс R1", font=font(15, True), fill="#A7EEE7")

    x_min, x_max, y_min, y_max = 97, 166, 54, 118
    scale = 11
    ox, oy = 45, 185
    for x in range(x_min, x_max + 1):
        px = ox + (x - x_min) * scale
        canvas.line((px, oy, px, oy + (y_max - y_min) * scale), fill="#D8E2E2")
    for y in range(y_min, y_max + 1):
        py = oy + (y - y_min) * scale
        canvas.line((ox, py, ox + (x_max - x_min) * scale, py), fill="#D8E2E2")

    def p(point):
        return ox + (point[0] - x_min) * scale, oy + (point[1] - y_min) * scale

    x0, y0, x1, y1 = VOID_BOX
    canvas.rectangle((*p((x0, y0)), *p((x1, y1))), fill="#F5C5C5", outline="#B00020", width=4)
    canvas.text((p((101, 75))[0], p((101, 75))[1]), "ФИЗИЧЕСКИЙ\nПРОЁМ", font=font(16, True), fill="#8B0018")

    colours = {"A-C09": "#5E9400", "A-C08": "#A26700"}
    for fragment in model["attic_plane_route_fragments"]:
        points = [p(tuple(point)) for point in fragment["ordered_points_grid"]]
        canvas.line(points, fill="white", width=10, joint="curve")
        canvas.line(points, fill=colours[fragment["route_id"]], width=5, joint="curve")

    isolated = {tuple(item["gate_point_grid"]) for item in audit if item["locally_isolated"]}
    all_gates = [tuple(item["gate_point_grid"]) for item in model["planned_R1_gate_mapping"]]
    for gate in all_gates:
        gx, gy = p(gate)
        fill = "#E4002B" if gate in isolated else "#00A7A0"
        canvas.ellipse((gx - 5, gy - 5, gx + 5, gy + 5), fill=fill, outline="white", width=2)
    for gate in sorted(isolated):
        gx, gy = p(gate)
        canvas.text((gx + 15, gy - 11), f"{gate[1]}: НЕТ ВЫХОДА", font=font(13, True), fill="#B00020", stroke_width=2, stroke_fill="white")

    cx0, cy0 = p((133, 65))
    cx1, cy1 = p((134, 91))
    canvas.rectangle((cx0 - 5, cy0, cx1 + 5, cy1), outline="#D97706", width=4)
    canvas.text((p((136, 87))[0], p((136, 87))[1]), "исходный проход\nвсего 2 колонки\nx=133/134", font=font(14, True), fill="#9A5200", stroke_width=2, stroke_fill="white")

    panel_x = 850
    canvas.rounded_rectangle((panel_x, 185, 1465, 830), radius=14, fill="#FFFFFFEE", outline="#9FB3BA", width=2)
    lines = [
        ("ЧТО ДОКАЗАНО", 18, True, "#071A21"),
        ("• A-C09 и A-C08: локальная геометрия PASS", 15, False, "#17343D"),
        ("• пересечений/касания/проёма: 0", 15, False, "#17343D"),
        ("• ворота y=61,62,63: степень выхода 0", 15, True, "#B00020"),
        ("• будущих отдельных труб: 22", 15, False, "#17343D"),
        ("", 10, False, "#17343D"),
        ("ПОЧЕМУ НЕЛЬЗЯ ПРОДОЛЖАТЬ ПО ОДНОЙ", 17, True, "#071A21"),
        ("Текущая обратная A-C08 закрыла восточные", 15, False, "#17343D"),
        ("соседние узлы. Слева находится проём,", 15, False, "#17343D"),
        ("а сверху/снизу — другие зарезервированные", 15, False, "#17343D"),
        ("точки R1. Следующая пара физически не выйдет.", 15, False, "#17343D"),
        ("", 10, False, "#17343D"),
        ("СЛЕДУЮЩИЙ ДОПУСТИМЫЙ ШАГ", 17, True, "#071A21"),
        ("1. Подтвердить отдельные транзитные коридоры.", 15, False, "#17343D"),
        ("2. Разнести ворота R1 по нескольким сторонам.", 15, False, "#17343D"),
        ("3. Проверить доступность всех будущих ворот", 15, False, "#17343D"),
        ("   после каждой принятой пары.", 15, False, "#17343D"),
        ("4. Только затем материализовать новые трубы.", 15, False, "#17343D"),
    ]
    y = 212
    for text, size, bold, colour in lines:
        canvas.text((panel_x + 25, y), text, font=font(size, bold), fill=colour)
        y += 34 if text else 18
    canvas.rounded_rectangle((panel_x, 855, 1465, 1055), radius=14, fill="#FFF2F2", outline="#D13A4A", width=3)
    canvas.text((panel_x + 25, 885), "ВЕРДИКТ", font=font(18, True), fill="#8B0018")
    canvas.text((panel_x + 25, 925), "REWORK_R1_CORRIDOR", font=font(25, True), fill="#B00020")
    canvas.text((panel_x + 25, 972), "Ни одна каноническая точка трубы D052\nв этом блоке не изменена.", font=font(15), fill="#17343D")
    image.save(target)


def draw_overlay(model, audit, target: Path):
    image = Image.open(SOURCE / "attic_r1_contract_repaired_overlay.png").convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 180), fill="#071A21")
    canvas.text((28, 10), "D053 · МАНСАРДА · АУДИТ КОРИДОРА R1", font=font(23, True), fill="white")
    canvas.text((28, 49), "D052 сохранён без изменений · 2 локальных фрагмента PASS · глобальный интерфейс R1 REWORK", font=font(15), fill="#A7EEE7")
    canvas.text((28, 81), "Ворота 61/62/63 изолированы: слева проём, справа A-C08, сверху/снизу соседние ворота", font=font(15, True), fill="#F3D58C")
    canvas.text((28, 113), "26-точечная вертикальная таблица НЕ ЯВЛЯЕТСЯ принятой разводкой всей мансарды", font=font(14, True), fill="#FFB2B2")
    canvas.text((28, 145), "ТРЕБУЕТСЯ МНОГОСТОРОННИЙ R1 ИЛИ ПОДТВЕРЖДЁННЫЙ ТРАНЗИТНЫЙ КОРИДОР", font=font(14, True), fill="#FFB2B2")
    for item in audit:
        if not item["locally_isolated"]:
            continue
        x, y = item["gate_point_grid"]
        px, py = round(x * PX), round(y * PX)
        canvas.ellipse((px - 9, py - 9, px + 9, py + 9), fill="#E4002B", outline="white", width=3)
        canvas.text((px + 12, py - 12), f"R1-{y} ЗАПЕРТ", font=font(12, True), fill="#B00020", stroke_width=3, stroke_fill="white")
    image.save(target)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D053 is append-only")
    source_bytes = SOURCE_JSON.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    audit = gate_escape_audit(source)
    isolated = [item["gate_point_grid"] for item in audit if item["locally_isolated"]]
    if isolated != [[132, 61], [132, 62], [132, 63]]:
        raise RuntimeError({"unexpected_isolated_gates": isolated})
    model = {
        "schema": "homeaura-attic-r1-corridor-audit-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_R1_CORRIDOR_AUDIT_053",
        "status": "TWO_LOCAL_FRAGMENTS_PASS_REWORK_GLOBAL_R1_CORRIDOR",
        "source_artifact_id": source["artifact_id"],
        "source_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_geometry_preserved": True,
        "source_fragment_count": len(source["attic_plane_route_fragments"]),
        "source_fragment_route_ids": [item["route_id"] for item in source["attic_plane_route_fragments"]],
        "source_local_fragment_geometry_status": "PASS_BOUNDED_ONLY",
        "source_26_gate_mapping_global_status": "REWORK_NOT_EXTENDABLE_WITH_CURRENT_FRAGMENTS",
        "grid_pitch_mm": 100,
        "structural_void_box_grid": list(VOID_BOX),
        "r1_vertical_gate_bank": {"x_grid": R1_X, "y_grid_inclusive": [57, 82], "gate_count": 26},
        "remaining_unbuilt_leg_count": 22,
        "upper_four_circuit_required_distinct_leg_count": 8,
        "baseline_corridor_free_columns_grid": [133, 134],
        "baseline_corridor_capacity_nodes_per_transverse_cut": 2,
        "future_gate_escape_audit": audit,
        "isolated_gate_points_grid": isolated,
        "isolated_gate_count": len(isolated),
        "blocker_explanation": "CURRENT_A-C08_RETURN_OCCUPIES_EAST_NEIGHBOURS_OF_GATES_61_62_63_WHILE_VOID_AND_RESERVED_GATES_BLOCK_OTHER_NEIGHBOURS",
        "candidate_body_translation_status": "NOT_MATERIALIZED_REQUIRES_EXACT_ROOM_POLYGON_CONTAINMENT",
        "required_next_contract": "MULTI_FACE_R1_GATE_BANK_OR_SOURCE_CONFIRMED_TRANSIT_CORRIDOR_WITH_GLOBAL_DISJOINT_ROUTING",
        "acceptance_requirements": [
            "ALL_26_LEGS_ASSIGNED_TO_DISTINCT_GATE_NODES",
            "ZERO_SELF_AND_INTER_ROUTE_CROSS_TOUCH_OVERLAP",
            "ZERO_STRUCTURAL_VOID_CONTACT",
            "FUTURE_GATE_REACHABILITY_RECOMPUTED_AFTER_EACH_ACCEPTED_PAIR",
            "RESIDUAL_CUT_CAPACITY_AT_LEAST_TWO_FOR_EVERY_UNBUILT_CIRCUIT_PAIR",
            "BODY_TRANSLATIONS_REQUIRE_EXACT_ROOM_POLYGON_CONTAINMENT",
        ],
        "complete_circuit_count": 0,
        "full_attic_route_claimed": False,
        "result": "REWORK_R1_CORRIDOR_NO_NEW_PIPE_GEOMETRY_PUBLISHED",
    }
    model["audit_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "source_geometry_preserved": True,
        "source_fragment_count": 2,
        "isolated_gate_count": 3,
        "isolated_gate_points_grid": isolated,
        "baseline_corridor_capacity": 2,
        "upper_group_required_leg_count": 8,
        "remaining_unbuilt_leg_count": 22,
        "global_mapping_extendability": "FAIL_CURRENT_D052_FRAGMENT_LAYOUT",
        "new_pipe_geometry_count": 0,
        "result": model["result"],
    }
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_r1_corridor_audit.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    draw_debug(source, audit, OUTPUT / "attic_r1_corridor_blocker_debug.png")
    draw_overlay(source, audit, OUTPUT / "attic_r1_corridor_blocker_overlay.png")
    (OUTPUT / "report.md").write_text(
        "# D053 — аудит узкого места R1\n\n"
        "Два ранее построенных планарных фрагмента A-C09 и A-C08 остаются корректными только в своём ограниченном объёме. "
        "Их нельзя использовать как неизменяемое начало полной разводки: обратная A-C08 заняла восточные соседние узлы ворот 61, 62 и 63. "
        "Слева эти ворота ограничены физическим проёмом, сверху и снизу — другими уникальными точками R1, поэтому степень выхода каждого из трёх ворот равна нулю.\n\n"
        "В этом блоке не изменена и не добавлена ни одна точка трубы. Глобальная 26-точечная вертикальная таблица переведена в REWORK. "
        "Следующая допустимая стадия — отдельный многосторонний интерфейс R1 либо подтверждённый источником широкий транзитный коридор, после чего все 26 труб должны решаться совместно с проверкой остаточной доступности после каждой пары.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "audit_digest": model["audit_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "isolated_gates": isolated,
        "new_pipe_geometry_count": 0,
        "audit_digest": model["audit_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

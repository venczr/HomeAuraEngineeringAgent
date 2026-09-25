from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058" / "attic_plan_space_diagnostic.json"
DOMAIN = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DOMAIN_AUDIT_059" / "attic_plan_space_domain_audit.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_EVIDENCE_060"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_PLANSPACE_EVIDENCE_060.zip"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


d041 = load_module(
    "attic_d041_for_d060",
    ROOT / "homeaura-native-editor-generate" / "build_attic_body_baseline_041.py",
)


COLOURS = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC", "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93", "#8A5A00"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def dashed_line(canvas: ImageDraw.ImageDraw, points, colour: str, width: int):
    dash = 10
    gap = 8
    for a, b in zip(points, points[1:]):
        ax, ay = a
        bx, by = b
        distance = abs(bx - ax) + abs(by - ay)
        if not distance:
            continue
        dx = (bx - ax) / distance
        dy = (by - ay) / distance
        cursor = 0.0
        while cursor < distance:
            end = min(cursor + dash, distance)
            canvas.line((ax + dx * cursor, ay + dy * cursor, ax + dx * end, ay + dy * end), fill=colour, width=width)
            cursor += dash + gap


def draw(source: dict, evidence: dict, target: Path, pipes_only: bool):
    image = Image.new("RGB", (1785, 1750), "#F7FAFA") if pipes_only else Image.open(d041.BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    if pipes_only:
        step = round(d041.PX)
        for x in range(0, image.width, step):
            canvas.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, step):
            canvas.line((0, y, image.width, y), fill="#D8E2E2")
    x0, y0, x1, y1 = source["structural_stair_void_box_grid"]
    canvas.rectangle((*d041.to_px((x0, y0)), *d041.to_px((x1, y1))), fill="#F7CACA", outline="#B00020", width=4)
    for route, colour in zip(source["body_routes"], COLOURS):
        points = [d041.to_px(point) for point in route["body_points_grid"]]
        canvas.line(points, fill="white", width=9, joint="curve")
        canvas.line(points, fill=colour, width=4, joint="curve")
    for fragment in source["diagnostic_planar_fragments"]:
        for key in ("supply_transit_points_grid", "return_transit_points_grid"):
            points = [d041.to_px(point) for point in fragment[key]]
            dashed_line(canvas, points, "white", 10)
            dashed_line(canvas, points, "#5D6670", 4)
        for point in (fragment["candidate_supply_endpoint_grid"], fragment["candidate_return_endpoint_grid"]):
            x, y = d041.to_px(point)
            canvas.rectangle((x - 5, y - 5, x + 5, y + 5), fill="#FFD45C", outline="#704800", width=2)

    canvas.rectangle((0, 0, image.width, 318), fill="#071A21")
    canvas.text((28, 10), "D060 · МАНСАРДА · ЧИСТОЕ ДОКАЗАТЕЛЬСТВО D058", font=d041.font(23, True), fill="white")
    canvas.text((28, 49), "Серый пунктир = диагностический подвод · цветная линия = регулярное тело D050", font=d041.font(15), fill="#A7EEE7")
    canvas.text((28, 81), "Текущих ворот R1: 0 · утверждённых труб: 0 · полных контуров K1: 0", font=d041.font(15, True), fill="#F3D58C")
    canvas.text((28, 113), "Физический интерфейс и 46,5 м в соседних неизвестных доменах: REWORK", font=d041.font(14, True), fill="#FFB2B2")
    canvas.text((28, 140), "ТАБЛИЦА ДИАГНОСТИЧЕСКИХ КОНЦОВ (координаты, не ворота)", font=d041.font(12, True), fill="#E8F0F2")
    rows = evidence["diagnostic_endpoint_table"]
    for index, row in enumerate(rows):
        column = 0 if index < 4 else 1
        line = index if index < 4 else index - 4
        x = 28 + column * 670
        y = 168 + line * 31
        canvas.text((x, y), f'{row["route_id"]}: S {row["supply_endpoint_grid"]} · R {row["return_endpoint_grid"]} · {row["planar_diagnostic_length_mm"] / 1000:.1f} м', font=d041.font(12, True), fill="#FFFFFF")
    canvas.text((28, 295), "Историческая 26-точечная таблица D050 не является текущим физическим интерфейсом", font=d041.font(11), fill="#FFB2B2")
    image.save(target)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D060 is append-only")
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    domain_bytes = DOMAIN.read_bytes()
    domain = json.loads(domain_bytes.decode("utf-8"))
    rows = [{
        "route_id": item["route_id"],
        "supply_endpoint_grid": item["candidate_supply_endpoint_grid"],
        "return_endpoint_grid": item["candidate_return_endpoint_grid"],
        "planar_diagnostic_length_mm": item["planar_fragment_length_mm"],
        "supply_return_are_current_R1_gates": False,
    } for item in source["diagnostic_planar_fragments"]]
    evidence = {
        "schema": "homeaura-attic-plan-space-evidence-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_PLANSPACE_EVIDENCE_060",
        "status": "D058_GEOMETRY_PASS_MACHINE_AND_VISUAL_GATE_SEMANTICS_REPAIRED_REWORK_SOURCE_DOMAINS_AND_INTERFACE",
        "source_D058_artifact_id": source["artifact_id"],
        "source_D058_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_D058_geometry_digest": source["geometry_digest"],
        "source_D059_artifact_id": domain["artifact_id"],
        "source_D059_sha256": hashlib.sha256(domain_bytes).hexdigest().upper(),
        "source_geometry_modified": False,
        "historical_D050_planned_R1_mapping_status": "SUPERSEDED_NOT_CURRENT_PHYSICAL_INTERFACE",
        "historical_D050_planned_R1_gate_count": source["planned_R1_gate_count"],
        "current_assigned_R1_gate_mapping": [],
        "current_assigned_R1_gate_count": 0,
        "diagnostic_candidate_endpoint_count": len(rows) * 2,
        "diagnostic_endpoint_table": rows,
        "approved_pipe_geometry_count": 0,
        "complete_circuit_count": 0,
        "physical_R1_interface_status": "NOT_EVALUATED",
        "full_attic_floor_union_status": domain["full_attic_floor_union_status"],
        "known_D047_transit_length_mm": domain["known_D047_transit_length_mm"],
        "unknown_adjacent_domain_transit_length_mm": domain["unknown_adjacent_domain_transit_length_mm"],
        "result": "PASS_CORRECTED_EVIDENCE_REWORK_FULL_ATTIC_SOURCE_POLYGONS_AND_PHYSICAL_R1_INTERFACE",
    }
    evidence["evidence_digest"] = digest(evidence)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "source_D058_geometry.json").write_bytes(source_bytes)
    (OUTPUT / "evidence_contract.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(source, evidence, OUTPUT / "attic_plan_space_evidence_overlay.png", False)
    draw(source, evidence, OUTPUT / "attic_plan_space_evidence_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D060 — исправленное доказательство D058\n\n"
        "Все точки и линии D058 сохранены побайтно. Текущий физический банк R1 удалён из машинного контракта: assigned R1 gates = 0. "
        "Историческая таблица D050 оставлена только как явно superseded metadata.\n\n"
        "На изображениях неподтверждённые подводы показаны единым серым пунктиром, а их S/R-координаты вынесены в таблицу. "
        "Физический интерфейс R1 и полный набор полигонов мансарды остаются REWORK.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": evidence["artifact_id"],
        "evidence_digest": evidence["evidence_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "current_assigned_R1_gates": 0,
        "diagnostic_endpoints": len(rows) * 2,
        "unknown_domain_transit_mm": evidence["unknown_adjacent_domain_transit_length_mm"],
        "evidence_digest": evidence["evidence_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

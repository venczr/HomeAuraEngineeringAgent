from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from shapely.geometry import LineString, shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058" / "attic_plan_space_diagnostic.json"
VECTOR = BASE / "HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047" / "attic_hall_exact_vector_contract.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DOMAIN_AUDIT_059"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DOMAIN_AUDIT_059.zip"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


d041 = load_module(
    "attic_d041_for_d059",
    ROOT / "homeaura-native-editor-generate" / "build_attic_body_baseline_041.py",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def to_mm(points):
    return [(point[0] * 100, point[1] * 100) for point in points]


def draw(source: dict, vector: dict, audit: dict, target: Path, pipes_only: bool):
    image = Image.new("RGB", (1785, 1750), "#F7FAFA") if pipes_only else Image.open(d041.BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    if pipes_only:
        step = round(d041.PX)
        for x in range(0, image.width, step):
            canvas.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, step):
            canvas.line((0, y, image.width, y), fill="#D8E2E2")
    polygon = shape(vector["hall_source_contract"]["routing_draft_allowed_floor_geojson"])
    exterior = list(polygon.exterior.coords)
    polygon_px = [d041.to_px((x / 100, y / 100)) for x, y in exterior]
    canvas.polygon(polygon_px, fill="#B9E4CA55", outline="#087F5B")
    canvas.text(d041.to_px((101, 95)), "ЗЕЛЁНАЯ ЗОНА = ТОЛЬКО D047", font=d041.font(11, True), fill="#087F5B", stroke_width=2, stroke_fill="white")
    x0, y0, x1, y1 = source["structural_stair_void_box_grid"]
    canvas.rectangle((*d041.to_px((x0, y0)), *d041.to_px((x1, y1))), fill="#F7CACA", outline="#B00020", width=4)
    colours = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC", "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93", "#8A5A00"]
    for route, colour in zip(source["body_routes"], colours):
        points = [d041.to_px(point) for point in route["body_points_grid"]]
        canvas.line(points, fill="white", width=9, joint="curve")
        canvas.line(points, fill=colour, width=4, joint="curve")
    for fragment in source["diagnostic_planar_fragments"]:
        colour = "#6C5CE7"
        for key in ("supply_transit_points_grid", "return_transit_points_grid"):
            points = [d041.to_px(point) for point in fragment[key]]
            for a, b in zip(points, points[1:]):
                canvas.line((a, b), fill="white", width=9)
                canvas.line((a, b), fill=colour, width=3)
        item = next(record for record in audit["fragment_domain_records"] if record["route_id"] == fragment["route_id"])
        x, y = d041.to_px(fragment["candidate_supply_endpoint_grid"])
        canvas.text((x + 4, y - 14), f'{fragment["route_id"]} D047 {item["known_D047_transit_ratio"] * 100:.0f}%', font=d041.font(9, True), fill=colour, stroke_width=2, stroke_fill="white")
    canvas.rectangle((0, 0, image.width, 184), fill="#071A21")
    canvas.text((28, 10), "D059 · МАНСАРДА · АУДИТ ИЗВЕСТНЫХ ДОМЕНОВ D058", font=d041.font(23, True), fill="white")
    canvas.text((28, 49), "Зелёным показан только source-backed пол D047 · остальная площадь не объявлена недопустимой", font=d041.font(15), fill="#A7EEE7")
    canvas.text((28, 81), "Фиолетовые линии = те же диагностические подводы D058 · новые трубы не создавались", font=d041.font(15, True), fill="#F3D58C")
    canvas.text((28, 113), "Вне D047 = UNKNOWN ADJACENT FLOOR DOMAIN, а не стена/пустота/запрет", font=d041.font(14, True), fill="#FFB2B2")
    canvas.text((28, 141), f'Из {audit["total_transit_length_mm"] / 1000:.1f} м подводов D058 подтверждено D047: {audit["known_D047_transit_length_mm"] / 1000:.1f} м; неизвестно: {audit["unknown_adjacent_domain_transit_length_mm"] / 1000:.1f} м', font=d041.font(14, True), fill="#FFB2B2")
    canvas.text((28, 166), "Следующий обязательный источник: полигоны пола соседних помещений и физический интерфейс R1", font=d041.font(12), fill="#E8F0F2")
    image.save(target)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D059 is append-only")
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    vector_bytes = VECTOR.read_bytes()
    vector = json.loads(vector_bytes.decode("utf-8"))
    allowed = shape(vector["hall_source_contract"]["routing_draft_allowed_floor_geojson"])
    records = []
    for fragment in source["diagnostic_planar_fragments"]:
        legs = []
        for leg, key in (("SUPPLY", "supply_transit_points_grid"), ("RETURN", "return_transit_points_grid")):
            line = LineString(to_mm(fragment[key]))
            known = line.intersection(allowed).length
            total = line.length
            unknown = total - known
            legs.append({
                "leg": leg,
                "transit_length_mm": total,
                "known_D047_length_mm": known,
                "unknown_adjacent_domain_length_mm": unknown,
                "entire_transit_covered_by_D047": allowed.covers(line),
                "candidate_interface_endpoint_covered_by_D047": allowed.covers(LineString([line.coords[0], line.coords[0]]).centroid),
                "outside_D047_interpretation": "UNKNOWN_ADJACENT_FLOOR_DOMAIN_NOT_PROVEN_INVALID",
            })
        total = sum(item["transit_length_mm"] for item in legs)
        known = sum(item["known_D047_length_mm"] for item in legs)
        records.append({
            "route_id": fragment["route_id"],
            "legs": legs,
            "transit_length_mm": total,
            "known_D047_transit_length_mm": known,
            "unknown_adjacent_domain_transit_length_mm": total - known,
            "known_D047_transit_ratio": known / total if total else 1.0,
            "source_containment_result": "PARTIAL_D047_ONLY_REWORK_FULL_ATTIC_FLOOR_UNION",
        })
    total = sum(item["transit_length_mm"] for item in records)
    known = sum(item["known_D047_transit_length_mm"] for item in records)
    audit = {
        "schema": "homeaura-attic-plan-space-domain-audit-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_PLANSPACE_DOMAIN_AUDIT_059",
        "status": "D058_PLANAR_TOPOLOGY_PRESERVED_REWORK_ADJACENT_FLOOR_SOURCE_DOMAINS",
        "source_D058_artifact_id": source["artifact_id"],
        "source_D058_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_D058_geometry_digest": source["geometry_digest"],
        "source_D047_artifact_id": vector["artifact_id"],
        "source_D047_sha256": hashlib.sha256(vector_bytes).hexdigest().upper(),
        "source_D047_scope": "LOCAL_CENTRAL_HALL_DRAFT_ONLY",
        "D047_not_claimed_as_whole_attic_floor_union": True,
        "fragment_geometry_modified": False,
        "new_pipe_geometry_count": 0,
        "fragment_domain_records": records,
        "total_transit_length_mm": total,
        "known_D047_transit_length_mm": known,
        "unknown_adjacent_domain_transit_length_mm": total - known,
        "known_D047_transit_ratio": known / total,
        "full_attic_floor_union_status": "MISSING",
        "physical_r1_interface_status": "NOT_EVALUATED",
        "result": "PASS_SOURCE_SCOPE_CLASSIFICATION_REWORK_ADJACENT_ROOM_POLYGONS_AND_PHYSICAL_R1_INTERFACE",
    }
    audit["audit_digest"] = digest(audit)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_plan_space_domain_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "source_D058_geometry.json").write_bytes(source_bytes)
    draw(source, vector, audit, OUTPUT / "attic_plan_space_domain_audit_overlay.png", False)
    draw(source, vector, audit, OUTPUT / "attic_plan_space_domain_audit_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D059 — граница доказанного источником пола\n\n"
        "Геометрия D058 не изменена. Для каждой подающей и обратной диагностической ноги измерена часть внутри локального полигона D047. "
        "Линия вне D047 не объявляется ошибкой: D047 описывает только центральный холл, а не весь пол мансарды. Такие части получили статус UNKNOWN ADJACENT FLOOR DOMAIN.\n\n"
        "До утверждения этих подводов нужны векторные полигоны соседних помещений и физически подтверждённый интерфейс R1. Новых труб и ворот в D059 нет.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": audit["artifact_id"],
        "audit_digest": audit["audit_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "total_transit_length_mm": total,
        "known_D047_transit_length_mm": known,
        "unknown_adjacent_domain_transit_length_mm": total - known,
        "known_ratio": known / total,
        "audit_digest": audit["audit_digest"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

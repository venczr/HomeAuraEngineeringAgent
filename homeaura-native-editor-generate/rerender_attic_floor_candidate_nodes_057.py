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
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_FLOOR_CANDIDATE_NODES_056" / "attic_floor_candidate_nodes.json"
BODY_SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_FLOOR_CANDIDATE_EVIDENCE_057"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_FLOOR_CANDIDATE_EVIDENCE_057.zip"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


d041 = load_module(
    "attic_d041_for_d057",
    ROOT / "homeaura-native-editor-generate" / "build_attic_body_baseline_041.py",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def draw(model: dict, bodies: dict, target: Path, pipes_only: bool):
    image = Image.new("RGB", (1785, 1750), "#F7FAFA") if pipes_only else Image.open(d041.BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    if pipes_only:
        step = round(d041.PX)
        for x in range(0, image.width, step):
            canvas.line((x, 0, x, image.height), fill="#D8E2E2")
        for y in range(0, image.height, step):
            canvas.line((0, y, image.width, y), fill="#D8E2E2")

    x0, y0, x1, y1 = bodies["structural_stair_void_box_grid"]
    canvas.rectangle((*d041.to_px((x0, y0)), *d041.to_px((x1, y1))), fill="#F7CACA", outline="#B00020", width=4)
    canvas.text(d041.to_px((x0, y0 - 2)), "ФИЗИЧЕСКИЙ ПРОЁМ", font=d041.font(11, True), fill="#B00020")

    colours = ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC", "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93", "#8A5A00"]
    for route, colour in zip(bodies["body_routes"], colours):
        points = [d041.to_px(point) for point in route["body_points_grid"]]
        canvas.line(points, fill="white", width=9, joint="curve")
        canvas.line(points, fill=colour, width=4, joint="curve")

    for item in model["candidate_nodes"]:
        x, y = d041.to_px(item["point_grid"])
        canvas.ellipse((x - 6, y - 6, x + 6, y + 6), fill="#FFD45C", outline="#704800", width=2)
    canvas.text(d041.to_px((101, 95)), "28 КАНДИДАТОВ ПОЛА — НЕ ВОРОТА", font=d041.font(11, True), fill="#704800", stroke_width=2, stroke_fill="white")

    canvas.rectangle((0, 0, image.width, 184), fill="#071A21")
    canvas.text((28, 10), "D057 · ЧИСТОЕ ДОКАЗАТЕЛЬСТВО УЗЛОВ ПОЛА D056", font=d041.font(23, True), fill="white")
    canvas.text((28, 49), "28 узлов x=101…128, y=93 · назначенных ворот/соединений/новых труб: 0", font=d041.font(15), fill="#A7EEE7")
    canvas.text((28, 81), "Старый вертикальный банк R1 удалён из изображения как отклонённая геометрия", font=d041.font(15, True), fill="#F3D58C")
    canvas.text((28, 113), "Жёлтые точки = только подтверждённые координаты пола · НЕ грань R1 и НЕ проход перекрытия", font=d041.font(14, True), fill="#FFB2B2")
    canvas.text((28, 141), "R1/СТОЯК/СТЕНЫ/3D-УПАКОВКА/ГИДРАВЛИКА/ПОЛНЫЕ МАРШРУТЫ: NOT EVALUATED", font=d041.font(14, True), fill="#FFB2B2")
    canvas.text((28, 166), "Геометрия и значения JSON D056 сохранены без изменений", font=d041.font(12), fill="#E8F0F2")
    image.save(target)


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D057 is append-only")
    source_bytes = SOURCE.read_bytes()
    model = json.loads(source_bytes.decode("utf-8"))
    body_bytes = BODY_SOURCE.read_bytes()
    bodies = json.loads(body_bytes.decode("utf-8"))
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_floor_candidate_nodes_d056.json").write_bytes(source_bytes)
    evidence = {
        "artifact_id": "HA_TWO_FLOOR_ATTIC_FLOOR_CANDIDATE_EVIDENCE_057",
        "status": "D056_DATA_PASS_VISUAL_LEGACY_R1_LAYER_REMOVED",
        "source_artifact_id": model["artifact_id"],
        "source_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_contract_digest": model["contract_digest"],
        "candidate_node_count": model["candidate_node_count"],
        "assigned_gate_count": model["assigned_gate_count"],
        "published_pipe_geometry_count": model["published_pipe_geometry_count"],
        "legacy_vertical_r1_bank_rendered": False,
        "candidate_nodes_rendered_as_gates": False,
        "candidate_nodes_rendered_as_pipe": False,
        "body_context_source_artifact_id": bodies["artifact_id"],
        "body_context_sha256": hashlib.sha256(body_bytes).hexdigest().upper(),
        "source_geometry_modified": False,
        "result": "PASS_CORRECTED_VISUAL_EVIDENCE_FOR_D056_REWORK_PHYSICAL_INTERFACE_AND_FULL_ROUTING",
    }
    (OUTPUT / "evidence_validation.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    draw(model, bodies, OUTPUT / "attic_floor_candidate_nodes_clean_overlay.png", False)
    draw(model, bodies, OUTPUT / "attic_floor_candidate_nodes_clean_pipes_only.png", True)
    (OUTPUT / "report.md").write_text(
        "# D057 — чистое визуальное доказательство D056\n\n"
        "Данные D056 сохранены побайтно. Старый вертикальный банк R1 полностью удалён из новых изображений, потому что он не является подтверждённым интерфейсом. "
        "Жёлтым показаны только 28 узлов пола без владельцев, ворот и труб.\n\n"
        "Физический выход R1, проход перекрытия, стены, 3D-упаковка и полные контуры по-прежнему не подтверждены.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": evidence["artifact_id"],
        "source_sha256": evidence["source_sha256"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "package": str(PACKAGE),
        "candidate_nodes": 28,
        "legacy_r1_bank_rendered": False,
        "source_sha256": evidence["source_sha256"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

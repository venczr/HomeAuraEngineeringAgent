from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_EVIDENCE_063"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_EVIDENCE_063.zip"
PX = 8.503937


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def to_px(point):
    return round(point[0] / 100 * PX), round(point[1] / 100 * PX)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D063 is append-only")
    source_bytes = SOURCE.read_bytes()
    model = json.loads(source_bytes.decode("utf-8"))
    image = Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    colours = ["#58C4DD", "#8C6FE8", "#EE6A8A", "#58B58A", "#F3A64A", "#557ED1", "#B85EAE"]
    labels = ["ЛЕВАЯ СЕВЕР", "ЛЕВАЯ ЦЕНТР", "ЛЕВАЯ ЮГ", "ПРАВАЯ СЕВЕР", "ПРАВАЯ С/Л", "ПРАВАЯ С/П", "ПРАВАЯ ЮГ"]
    for record, colour, label in zip(model["adjacent_floor_domains"], colours, labels):
        x0, y0, x1, y1 = record["finish_face_bbox_mm"]
        canvas.rectangle((*to_px((x0, y0)), *to_px((x1, y1))), fill=colour + "35", outline=colour, width=3)
        canvas.text(to_px((x0 + 100, y0 + 100)), label, font=font(9, True), fill=colour, stroke_width=2, stroke_fill="white")
    central = shape(model["known_floor_union_geojson"])
    # The union outline is intentionally not drawn: individual rectangles plus source plan are the evidence.
    canvas.rectangle((0, 0, image.width, 190), fill="#071A21")
    canvas.text((28, 10), "D063 · МАНСАРДА · ВЕКТОРНЫЕ ПОЛИГОНЫ D062", font=font(23, True), fill="white")
    canvas.text((28, 49), f'7 соседних прямоугольников: {model["adjacent_rectangles_area_m2"]:.2f} м² · локальный центральный D047: {model["D047_local_central_floor_area_m2"]:.2f} м²', font=font(15), fill="#A7EEE7")
    canvas.text((28, 81), f'Подводы D058: подтверждено полом {model["diagnostic_transit_known_floor_union_length_mm"] / 1000:.1f} м из {model["diagnostic_transit_total_length_mm"] / 1000:.1f} м', font=font(15, True), fill="#F3D58C")
    canvas.text((28, 113), f'Не классифицировано: {model["diagnostic_transit_unknown_wall_threshold_or_untraced_floor_length_mm"] / 1000:.1f} м · стены/пороги/неизвлечённый пол', font=font(14, True), fill="#FFB2B2")
    canvas.text((28, 141), "Пороги, полосы стен, полный union мансарды и физический R1: REWORK", font=font(14, True), fill="#FFB2B2")
    canvas.text((28, 166), "Цветные прямоугольники — finish-face candidates, не обмер и не готовая трасса", font=font(12), fill="#E8F0F2")
    OUTPUT.mkdir(parents=True)
    image.save(OUTPUT / "attic_adjacent_floor_domains_clean_overlay.png")
    (OUTPUT / "attic_adjacent_floor_domains_d062.json").write_bytes(source_bytes)
    evidence = {
        "artifact_id": "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_EVIDENCE_063",
        "status": "D062_CONTRACT_PRESERVED_CYRILLIC_VISUAL_EVIDENCE_REPAIRED",
        "source_D062_artifact_id": model["artifact_id"],
        "source_D062_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_D062_contract_digest": model["contract_digest"],
        "source_geometry_modified": False,
        "unicode_font": "Segoe UI",
        "adjacent_domain_count": 7,
        "current_assigned_R1_gate_count": 0,
        "new_pipe_geometry_count": 0,
        "result": "PASS_CORRECTED_VISUAL_EVIDENCE_REWORK_THRESHOLDS_WALLS_AND_PHYSICAL_R1_INTERFACE",
    }
    (OUTPUT / "evidence_validation.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "report.md").write_text(
        "# D063 — исправленный визуальный слой D062\n\n"
        "JSON D062 сохранён побайтно. Заголовок, подписи и числовые значения заново отрисованы Unicode-шрифтом; квадраты из-за неподдержанной кириллицы устранены. Геометрия полигонов не менялась.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": evidence["artifact_id"],
        "source_sha256": evidence["source_D062_sha256"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "domains": 7, "source_preserved": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()

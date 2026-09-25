from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_050 = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
SOURCE_058 = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058" / "attic_plan_space_diagnostic.json"
SOURCE_074 = BASE / "HA_TWO_FLOOR_OWNER_PHYSICAL_INPUTS_074" / "owner_physical_inputs.json"
OUTPUT = BASE / "HA_TWO_FLOOR_OWNER_BEND_RADIUS_AUDIT_075"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_OWNER_BEND_RADIUS_AUDIT_075.zip"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def direction(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return (0 if dx == 0 else (1 if dx > 0 else -1), 0 if dy == 0 else (1 if dy > 0 else -1))


def audit_points(route_id: str, points: list[list[int]], radius_mm: int) -> dict:
    segments = []
    failures = []
    for index, (a, b) in enumerate(zip(points, points[1:])):
        length_mm = (abs(a[0] - b[0]) + abs(a[1] - b[1])) * 100
        start_is_bend = index > 0 and direction(points[index - 1], a) != direction(a, b)
        end_is_bend = index + 2 < len(points) and direction(a, b) != direction(b, points[index + 2])
        required_tangent_mm = radius_mm * (int(start_is_bend) + int(end_is_bend))
        record = {
            "segment_index": index,
            "segment_grid": [a, b],
            "straight_length_mm": length_mm,
            "start_is_bend": start_is_bend,
            "end_is_bend": end_is_bend,
            "required_tangent_allowance_mm": required_tangent_mm,
            "remaining_straight_after_tangencies_mm": length_mm - required_tangent_mm,
            "passes_local_tangent_fit": length_mm >= required_tangent_mm,
        }
        segments.append(record)
        if not record["passes_local_tangent_fit"]:
            failures.append(record)
    return {
        "route_id": route_id,
        "segment_count": len(segments),
        "failing_segment_count": len(failures),
        "failing_segments": failures,
        "minimum_remaining_straight_after_tangencies_mm": min(item["remaining_straight_after_tangencies_mm"] for item in segments),
        "result": "PASS_LOCAL_R80_TANGENT_FIT" if not failures else "REWORK_SCHEMATIC_SHORT_SEGMENTS_FOR_R80",
    }


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D075 is append-only")
    raw_050 = SOURCE_050.read_bytes()
    raw_058 = SOURCE_058.read_bytes()
    raw_074 = SOURCE_074.read_bytes()
    source_050 = json.loads(raw_050.decode("utf-8"))
    source_058 = json.loads(raw_058.decode("utf-8"))
    source_074 = json.loads(raw_074.decode("utf-8"))
    radius_mm = source_074["owner_inputs"]["design_minimum_bend_radius_mm"]
    body_audits = [audit_points(route["route_id"], route["body_points_grid"], radius_mm) for route in source_050["body_routes"]]
    fragment_audits = [audit_points(route["route_id"], route["ordered_points_grid"], radius_mm) for route in source_058["diagnostic_planar_fragments"]]
    fragment_failures = [item for item in fragment_audits if item["failing_segment_count"]]
    model = {
        "schema": "homeaura-owner-bend-radius-audit-0.1",
        "artifact_id": "HA_TWO_FLOOR_OWNER_BEND_RADIUS_AUDIT_075",
        "status": "ALL_THIRTEEN_ATTIC_BODIES_PASS_LOCAL_R80_TANGENT_FIT_THREE_DIAGNOSTIC_FRAGMENTS_REWORK",
        "source_D050_artifact_id": source_050["artifact_id"],
        "source_D050_sha256": hashlib.sha256(raw_050).hexdigest().upper(),
        "source_D058_artifact_id": source_058["artifact_id"],
        "source_D058_sha256": hashlib.sha256(raw_058).hexdigest().upper(),
        "source_D074_artifact_id": source_074["artifact_id"],
        "source_D074_sha256": hashlib.sha256(raw_074).hexdigest().upper(),
        "pipe_outer_diameter_mm": source_074["owner_inputs"]["pipe_outer_diameter_mm"],
        "design_centerline_bend_radius_mm": radius_mm,
        "heated_radius_reduction_credited": False,
        "local_fit_method": "EACH_90_DEG_BEND_CONSUMES_ONE_RADIUS_OF_TANGENT_LENGTH_ON_EACH_ADJACENT_STRAIGHT",
        "two_bend_segment_minimum_length_mm": 2 * radius_mm,
        "scope_limit": "LOCAL_TANGENT_FIT_ONLY_NOT_FULL_ARC_CONTACT_OR_INSTALLATION_STRESS_MODEL",
        "attic_body_audits": body_audits,
        "attic_body_pass_count": sum(item["failing_segment_count"] == 0 for item in body_audits),
        "attic_body_rework_count": sum(item["failing_segment_count"] > 0 for item in body_audits),
        "diagnostic_fragment_audits": fragment_audits,
        "diagnostic_fragment_pass_count": sum(item["failing_segment_count"] == 0 for item in fragment_audits),
        "diagnostic_fragment_rework_count": len(fragment_failures),
        "diagnostic_fragment_rework_route_ids": [item["route_id"] for item in fragment_failures],
        "geometry_modified": False,
        "new_pipe_geometry_count": 0,
        "approved_complete_circuit_count": 0,
        "result": "PASS_BODY_R80_SCREENING_REWORK_A09_A08_A10_DIAGNOSTIC_JOINS_AND_PHYSICAL_TRANSITIONS",
    }
    model["bend_audit_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "owner_bend_radius_audit.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    image = Image.new("RGB", (1700, 1120), "#F7FAFA")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 205), fill="#071A21")
    canvas.text((34, 20), "D075 · ПРОВЕРКА РАДИУСА R80 ДЛЯ ТРУБЫ Ø16", font=font(29, True), fill="white")
    canvas.text((34, 73), "Консервативно: уменьшение радиуса при прогреве не используется", font=font(17, True), fill="#F3D58C")
    canvas.text((34, 118), "Локальный критерий: между двумя поворотами нужно ≥160 мм прямого участка", font=font(17), fill="#A7EEE7")
    canvas.text((34, 161), "Это проверка касательных; окончательная проверка дуг и контактов выполняется после физической трассировки", font=font(14), fill="#E8F0F2")

    canvas.rounded_rectangle((55, 250, 1645, 480), radius=22, fill="#EAF5EF", outline="#8AB9A0", width=3)
    canvas.text((90, 280), "13 регулярных тел мансарды", font=font(22, True), fill="#165E3B")
    canvas.text((90, 335), "13 / 13 проходят локальную проверку R80", font=font(26, True), fill="#165E3B")
    canvas.text((90, 395), "Минимальные сегменты 200 мм дают 40 мм прямого остатка между двумя касательными R80", font=font(16), fill="#234D3A")
    canvas.text((90, 435), "Тела сохраняются без изменения", font=font(16, True), fill="#234D3A")

    canvas.rounded_rectangle((55, 535, 1645, 865), radius=22, fill="#FFF0F0", outline="#D89090", width=3)
    canvas.text((90, 565), "Диагностические планарные стыки", font=font(22, True), fill="#8A1A1A")
    canvas.text((90, 620), f"REWORK: {', '.join(item['route_id'] for item in fragment_failures)}", font=font(25, True), fill="#B00020")
    y = 682
    for item in fragment_failures:
        segment = item["failing_segments"][0]
        canvas.text((105, y), f"{item['route_id']}: {segment['segment_grid'][0]} → {segment['segment_grid'][1]} = {segment['straight_length_mm']} мм; требуется {segment['required_tangent_allowance_mm']} мм", font=font(15), fill="#6F1515")
        y += 48
    canvas.text((90, 825), "Эти 100-мм стыки были схемой. Их надо перестроить естественными подводами с R80, не поджимать нагревом.", font=font(15, True), fill="#8A1A1A")

    canvas.text((60, 940), "Итог: тела укладки R80 совместимы по локальной геометрии; A-C09/A-C08/A-C10 нельзя переносить в монтаж без переразводки стыков.", font=font(17, True), fill="#143842")
    canvas.text((60, 1000), "Новых труб: 0 · полных утверждённых контуров: 0", font=font(15), fill="#566B73")
    image.save(OUTPUT / "owner_bend_radius_audit.png")

    (OUTPUT / "report.md").write_text(
        "# D075 — проверка радиуса изгиба 80 мм\n\n"
        "Для каждого прямого сегмента рассчитан запас касательной: один радиус 80 мм на каждый соседний поворот 90°. "
        "Все 13 регулярных тел мансарды проходят локальную проверку; их минимальные сегменты 200 мм достаточны для двух соседних касательных по 80 мм.\n\n"
        "У диагностических планарных фрагментов A-C09, A-C08 и A-C10 обнаружено по одному 100-мм стыку между двумя поворотами, где требуется минимум 160 мм. "
        "Эти стыки остаются схемой и должны быть перестроены при физической трассировке. Уменьшение радиуса прогревом не учитывается.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "bend_audit_digest": model["bend_audit_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "body_pass": model["attic_body_pass_count"], "fragment_rework": model["diagnostic_fragment_rework_route_ids"], "digest": model["bend_audit_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

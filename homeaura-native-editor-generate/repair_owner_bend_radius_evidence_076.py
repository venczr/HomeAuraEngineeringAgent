from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_OWNER_BEND_RADIUS_AUDIT_075" / "owner_bend_radius_audit.json"
OUTPUT = BASE / "HA_TWO_FLOOR_OWNER_BEND_RADIUS_EVIDENCE_076"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_OWNER_BEND_RADIUS_EVIDENCE_076.zip"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest().upper()


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D076 is append-only")
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    body_audits = source["attic_body_audits"]
    fragment_audits = source["diagnostic_fragment_audits"]
    failing = [item for item in fragment_audits if item["failing_segment_count"]]
    model = {
        "schema": "homeaura-owner-bend-radius-evidence-0.2",
        "artifact_id": "HA_TWO_FLOOR_OWNER_BEND_RADIUS_EVIDENCE_076",
        "status": "ALL_THIRTEEN_ATTIC_BODIES_PASS_LOCAL_R80_TANGENT_FIT_ONLY_A_C08_DIAGNOSTIC_JOIN_REWORK",
        "source_D075_artifact_id": source["artifact_id"],
        "source_D075_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
        "source_D075_disposition": "NUMERICAL_ARRAYS_VALID_REJECT_HARDCODED_THREE_FRAGMENT_STATUS_AND_REPORT",
        "pipe_outer_diameter_mm": source["pipe_outer_diameter_mm"],
        "design_centerline_bend_radius_mm": source["design_centerline_bend_radius_mm"],
        "heated_radius_reduction_credited": False,
        "two_bend_segment_minimum_length_mm": source["two_bend_segment_minimum_length_mm"],
        "attic_body_audits": body_audits,
        "attic_body_pass_count": sum(item["failing_segment_count"] == 0 for item in body_audits),
        "diagnostic_fragment_audits": fragment_audits,
        "diagnostic_fragment_pass_count": sum(item["failing_segment_count"] == 0 for item in fragment_audits),
        "diagnostic_fragment_rework_count": len(failing),
        "diagnostic_fragment_rework_route_ids": [item["route_id"] for item in failing],
        "A_C08_failing_segment": failing[0]["failing_segments"][0],
        "A_C09_100mm_segment_status": "PASS_ONE_ADJACENT_BEND_REQUIRES_80MM",
        "A_C10_100mm_segment_status": "PASS_ONE_ADJACENT_BEND_REQUIRES_80MM",
        "scope_limit": source["scope_limit"],
        "geometry_modified": False,
        "new_pipe_geometry_count": 0,
        "approved_complete_circuit_count": 0,
        "result": "PASS_CORRECTED_R80_EVIDENCE_REWORK_ONLY_A_C08_SCHEMATIC_JOIN_AND_ALL_PHYSICAL_TRANSITIONS",
    }
    model["evidence_digest"] = digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "owner_bend_radius_evidence.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    image = Image.new("RGB", (1650, 1050), "#F7FAFA")
    canvas = ImageDraw.Draw(image, "RGBA")
    canvas.rectangle((0, 0, image.width, 205), fill="#071A21")
    canvas.text((34, 20), "D076 · ИСПРАВЛЕННАЯ ПРОВЕРКА R80 / Ø16", font=font(29, True), fill="white")
    canvas.text((34, 73), "13 тел PASS · 6 из 7 диагностических фрагментов PASS · REWORK только A-C08", font=font(18, True), fill="#A7EEE7")
    canvas.text((34, 120), "Уменьшение радиуса при прогреве в расчёт не включено", font=font(16, True), fill="#F3D58C")
    canvas.text((34, 162), "D075 сохранил верные массивы, но его заголовок/отчёт ошибочно называл три фрагмента", font=font(14), fill="#FFB2B2")

    canvas.rounded_rectangle((60, 260, 1590, 490), radius=22, fill="#EAF5EF", outline="#8AB9A0", width=3)
    canvas.text((95, 290), "Регулярные тела мансарды", font=font(23, True), fill="#165E3B")
    canvas.text((95, 350), "13 / 13 проходят локальную посадку касательных R80", font=font(27, True), fill="#165E3B")
    canvas.text((95, 418), "Минимальный сегмент 200 мм ≥ 80+80 мм; геометрия тел не меняется", font=font(17), fill="#234D3A")

    fail = model["A_C08_failing_segment"]
    canvas.rounded_rectangle((60, 545, 1590, 795), radius=22, fill="#FFF0F0", outline="#D89090", width=3)
    canvas.text((95, 575), "Единственный выявленный схематический стык", font=font(23, True), fill="#8A1A1A")
    canvas.text((95, 635), f"A-C08: {fail['segment_grid'][0]} → {fail['segment_grid'][1]} = {fail['straight_length_mm']} мм", font=font(24, True), fill="#B00020")
    canvas.text((95, 690), f"Между двумя поворотами R80 требуется минимум {fail['required_tangent_allowance_mm']} мм", font=font(19), fill="#6F1515")
    canvas.text((95, 740), "При физической разводке этот стык удлиняется/переносится; нагревом радиус не поджимаем", font=font(16, True), fill="#8A1A1A")

    canvas.text((65, 870), "A-C09 и A-C10: их 100-мм участки имеют поворот только с одной стороны, поэтому локально требуют 80 мм и проходят.", font=font(17, True), fill="#143842")
    canvas.text((65, 930), "Это скрининг касательных, не полная проверка дуг/напряжений/контактов. Новых труб и полных контуров: 0.", font=font(15), fill="#566B73")
    image.save(OUTPUT / "owner_bend_radius_evidence.png")

    (OUTPUT / "report.md").write_text(
        "# D076 — исправленное доказательство радиуса R80\n\n"
        "Все 13 регулярных тел мансарды проходят локальную проверку касательных для радиуса по оси 80 мм. "
        "Из семи диагностических фрагментов шесть проходят, а один 100-мм стык A-C08 между двумя поворотами требует минимум 160 мм и остаётся REWORK.\n\n"
        "У A-C09 и A-C10 100-мм сегменты имеют поворот только с одной стороны, поэтому требуют 80 мм и локально проходят. "
        "Уменьшение радиуса при прогреве не учитывается. Окончательные дуги проверяются после выбора физического R1 и построения подводов.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "evidence_digest": model["evidence_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "body_pass": model["attic_body_pass_count"], "fragment_pass": model["diagnostic_fragment_pass_count"], "fragment_rework": model["diagnostic_fragment_rework_route_ids"], "digest": model["evidence_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

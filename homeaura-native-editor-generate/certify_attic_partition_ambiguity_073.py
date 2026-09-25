from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, box


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_071 = BASE / "HA_TWO_FLOOR_ATTIC_PARTITION_OPENING_EVIDENCE_071" / "attic_partition_opening_evidence.json"
SOURCE_058 = BASE / "HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058" / "attic_plan_space_diagnostic.json"
SOURCE_050 = BASE / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
SOURCE_011 = BASE / "HA_TWO_FLOOR_VECTOR_CONTRACT_011" / "vector_source_contract.json"
PDF = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf")
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_ATTIC_PARTITION_AMBIGUITY_073"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_PARTITION_AMBIGUITY_073.zip"
PX = 8.503937


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest().upper()


def rect_record(drawings, path_id: int) -> dict:
    rect = drawings[path_id]["rect"]
    return {"pdf_path_id": path_id, "raw_rect_pt": [rect.x0, rect.y0, rect.x1, rect.y1]}


def to_px(point_grid):
    return round(point_grid[0] * PX), round(point_grid[1] * PX)


def point_contacts(line: LineString, other: LineString) -> int:
    intersection = line.intersection(other)
    if intersection.is_empty:
        return 0
    if intersection.geom_type == "Point":
        return 1
    if intersection.geom_type == "MultiPoint":
        return len(intersection.geoms)
    return 1


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("D073 is append-only")
    raw_071 = SOURCE_071.read_bytes()
    raw_058 = SOURCE_058.read_bytes()
    raw_050 = SOURCE_050.read_bytes()
    raw_011 = SOURCE_011.read_bytes()
    source_071 = json.loads(raw_071.decode("utf-8"))
    source_058 = json.loads(raw_058.decode("utf-8"))
    source_050 = json.loads(raw_050.decode("utf-8"))
    source_011 = json.loads(raw_011.decode("utf-8"))
    void_grid = source_011["vector_traced_geometry"]["attic_structural_stair_void"]["conservative_blocked_box_grid"]
    void_mm = [value * 100 for value in void_grid]
    void_shape = box(*void_mm)
    body_lines = {route["route_id"]: LineString([(x * 100, y * 100) for x, y in route["body_points_grid"]]) for route in source_050["body_routes"]}
    fragment_lines = {}
    for fragment in source_058["diagnostic_planar_fragments"]:
        for leg, key in (("SUPPLY", "supply_transit_points_grid"), ("RETURN", "return_transit_points_grid")):
            fragment_lines[(fragment["route_id"], leg)] = LineString([(x * 100, y * 100) for x, y in fragment[key]])

    pdf_bytes = PDF.read_bytes()
    drawings = pymupdf.open(stream=pdf_bytes, filetype="pdf")[0].get_drawings()
    split_path_ids = [1559, 1556, 1586, 1589]
    continuous_path_ids = [579, 283]
    opening_y = source_071["opening_y_pt"]
    conflict_records = []
    for path_id in continuous_path_ids:
        rect = drawings[path_id]["rect"]
        conflict_records.append({
            **rect_record(drawings, path_id),
            "covers_complete_split_interval": rect.y0 <= opening_y[0] and rect.y1 >= opening_y[1],
            "classification": "CONFLICTING_CONTINUOUS_FILLED_WALL_FACE_PATH",
        })

    axes = []
    for source_axis in source_071["four_unowned_200mm_crossing_axes"]:
        line = LineString(source_axis["ordered_points_mm"])
        contacts = []
        for (route_id, leg), fragment_line in fragment_lines.items():
            count = point_contacts(line, fragment_line)
            if count:
                contacts.append({"route_id": route_id, "leg": leg, "contact_count": count})
        body_contacts = [{"route_id": route_id, "contact_count": point_contacts(line, body)} for route_id, body in body_lines.items() if point_contacts(line, body)]
        axes.append({
            **source_axis,
            "D050_body_contact_count": sum(item["contact_count"] for item in body_contacts),
            "D050_body_contacts": body_contacts,
            "D011_void_bbox_mm": void_mm,
            "D011_void_contact_count": 0 if line.disjoint(void_shape) else 1,
            "D058_fragment_contacts": contacts,
            "D058_fragment_contact_count": sum(item["contact_count"] for item in contacts),
            "global_contact_free_routing_candidate": False,
            "capacity_axis_only": True,
        })
    total_fragment_contacts = sum(axis["D058_fragment_contact_count"] for axis in axes)
    model = {
        "schema": "homeaura-attic-partition-ambiguity-0.1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_PARTITION_AMBIGUITY_073",
        "status": "MATCHED_SPLIT_PATH_INTERVAL_CANDIDATE_CONFLICTING_CONTINUOUS_PATHS_PRESENT_REWORK_PHYSICAL_CONFIRMATION",
        "source_D071_artifact_id": source_071["artifact_id"],
        "source_D071_sha256": hashlib.sha256(raw_071).hexdigest().upper(),
        "source_D071_disposition": "SUPERSEDED_OPENING_HEADLINE_AND_INCOMPLETE_CONTACT_PROVENANCE",
        "source_D058_artifact_id": source_058["artifact_id"],
        "source_D058_sha256": hashlib.sha256(raw_058).hexdigest().upper(),
        "source_D050_artifact_id": source_050["artifact_id"],
        "source_D050_sha256": hashlib.sha256(raw_050).hexdigest().upper(),
        "source_D011_contract_id": source_011["contract_id"],
        "source_D011_sha256": hashlib.sha256(raw_011).hexdigest().upper(),
        "source_pdf_path": str(PDF),
        "source_pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest().upper(),
        "source_pdf_page": 1,
        "split_path_records": [rect_record(drawings, path_id) for path_id in split_path_ids],
        "matched_split_path_interval_y_pt": opening_y,
        "matched_split_path_interval_width_mm": source_071["opening_clear_width_mm"],
        "conflicting_continuous_path_records": conflict_records,
        "continuous_paths_cover_complete_interval": all(item["covers_complete_split_interval"] for item in conflict_records),
        "physical_opening_confirmed": False,
        "abstract_capacity_axes": axes,
        "abstract_capacity_axis_count": len(axes),
        "D050_total_body_contact_count": sum(axis["D050_body_contact_count"] for axis in axes),
        "D011_total_void_contact_count": sum(axis["D011_void_contact_count"] for axis in axes),
        "D058_total_fragment_point_contact_count": total_fragment_contacts,
        "all_capacity_axes_contact_free_against_existing_D058_fragments": total_fragment_contacts == 0,
        "candidate_axis_ownership_assigned": False,
        "current_assigned_R1_gate_count": 0,
        "new_pipe_geometry_count": 0,
        "approved_pipe_geometry_count": 0,
        "complete_circuit_count": 0,
        "required_external_confirmation": [
            "site/architect confirmation that a usable opening exists",
            "measured clear opening width and elevation",
            "threshold and door leaf/swing",
            "wall construction, permitted sleeve zone and firestop",
            "physical R1 exit tied to plan coordinates",
        ],
        "result": "REWORK_ABSTRACT_CAPACITY_ONLY_NO_OPENING_OR_CONTACT_FREE_ROUTE_PROVEN",
    }
    model["ambiguity_digest"] = digest(model)

    OUTPUT.mkdir(parents=True)
    (OUTPUT / "attic_partition_ambiguity.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    image = Image.open(BACKGROUND).convert("RGB")
    canvas = ImageDraw.Draw(image, "RGBA")
    for axis in axes:
        points = [to_px(point) for point in axis["ordered_points_grid"]]
        canvas.line(points, fill="#6F42C1", width=4)
        for point in points:
            canvas.ellipse((point[0]-4, point[1]-4, point[0]+4, point[1]+4), fill="#FFF4A3", outline="#4930A8", width=2)
        for contact in axis["D058_fragment_contacts"]:
            fragment = fragment_lines[(contact["route_id"], contact["leg"])]
            intersection = LineString(axis["ordered_points_mm"]).intersection(fragment)
            geometries = [intersection] if intersection.geom_type == "Point" else list(getattr(intersection, "geoms", []))
            for point in geometries:
                px = to_px((point.x / 100, point.y / 100))
                canvas.ellipse((px[0]-7, px[1]-7, px[0]+7, px[1]+7), fill="#D50000", outline="white", width=2)
    canvas.rectangle((0, 0, image.width, 205), fill="#071A21")
    canvas.text((28, 10), "D073 · 901,7 мм — НЕ ПОДТВЕРЖДЁННЫЙ ФИЗИЧЕСКИЙ ПРОЁМ", font=font(22, True), fill="white")
    canvas.text((28, 48), "Раздельные paths 1559/1556 и 1586/1589 дают совпавший интервал", font=font(14), fill="#A7EEE7")
    canvas.text((28, 78), "Но непрерывные заполненные paths 579 и 283 проходят через весь тот же интервал", font=font(14, True), fill="#FFB2B2")
    canvas.text((28, 109), f"4 оси: тела D050 — 0 контактов · лестничный проём D011 — 0 · фрагменты D058 — {total_fragment_contacts} точек", font=font(14, True), fill="#F3D58C")
    canvas.text((28, 140), "Красные точки — пересечения с A-C13 S/R; это проверка вместимости, не готовая трасса", font=font(13, True), fill="#FFB2B2")
    canvas.text((28, 170), "Новых труб/ворот: 0 · нужен обмер проёма, стены, проходки и физического R1", font=font(12), fill="#E8F0F2")
    image.save(OUTPUT / "attic_partition_ambiguity_overlay.png")

    (OUTPUT / "report.md").write_text(
        "# D073 — неоднозначность разрыва перегородки\n\n"
        "Четыре раздельных векторных path дают совпавший интервал 901,6999 мм, однако две непрерывные заполненные линии стены (paths 579 и 283) перекрывают весь тот же интервал. "
        "Поэтому PDF не доказывает физический проём; требуется подтверждение проектом или на месте.\n\n"
        f"Четыре оси с шагом 200 мм не касаются тел D050 и конструктивного проёма лестницы D011, но суммарно имеют {total_fragment_contacts} точечных контактов с диагностическими ногами A-C13 из D058. "
        "Оси остаются только абстрактной проверкой вместимости — без владельцев, ворот R1 и утверждённой трубной геометрии.\n",
        encoding="utf-8",
    )
    files = [path for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({
        "artifact_id": model["artifact_id"],
        "ambiguity_digest": model["ambiguity_digest"],
        "append_only": True,
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "continuous_conflicts": len(conflict_records), "D058_point_contacts": total_fragment_contacts, "new_geometry": 0, "digest": model["ambiguity_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_LOCAL_GROUP_012"
OUTPUT = BASE / "HA_TWO_FLOOR_LOCAL_GROUP_013"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_LOCAL_GROUP_013.zip"
PX = 8.503937


def font(size: int, bold: bool = False):
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / name), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def canonical_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def to_px(point: list[int]) -> tuple[int, int]:
    return round(point[0] * PX), round(point[1] * PX)


def pipes_only(routes: list[dict], target: Path) -> dict:
    max_x = max(point[0] for route in routes for point in route["ordered_points_grid"])
    max_y = max(point[1] for route in routes for point in route["ordered_points_grid"])
    width = max(1785, round((max_x + 10) * PX))
    height = max(1500, round((max_y + 10) * PX))
    image = Image.new("RGB", (width, height), "#F7FAFA")
    draw = ImageDraw.Draw(image)
    grid_px = round(PX)
    for x in range(0, width, grid_px):
        draw.line((x, 0, x, height), fill="#D8E2E2", width=1)
    for y in range(0, height, grid_px):
        draw.line((0, y, width, y), fill="#D8E2E2", width=1)
    draw.rectangle((0, 0, width, 110), fill="#071A21")
    draw.text((35, 20), "D013 · КОТЕЛЬНАЯ И КУХНЯ · ПОЛНЫЙ VIEWPORT", font=font(28, True), fill="white")
    draw.text((35, 64), "Топология PASS · покрытие REWORK · нижние развороты не обрезаны", font=font(18), fill="#A7EEE7")
    k1 = tuple(round(value * PX) for value in (132, 56, 136, 82))
    draw.rectangle(k1, fill="#D8F3EE", outline="#00897B", width=5)
    draw.text((k1[0] + 5, k1[1] + 5), "K1", font=font(16, True), fill="#00695C")
    colours = ["#F28E2B", "#00A7E1", "#7A49E5"]
    for route, colour in zip(routes, colours):
        points = [to_px(point) for point in route["ordered_points_grid"]]
        draw.line(points, fill="white", width=10, joint="curve")
        draw.line(points, fill=colour, width=5, joint="curve")
        for prefix, key in (("S", "supply_port_grid"), ("R", "return_port_grid")):
            x, y = to_px(route[key])
            draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=colour, outline="white", width=2)
            draw.text((x + 8, y - 9), f'{route["route_id"]}-{prefix}', font=font(12, True), fill=colour, stroke_width=2, stroke_fill="white")
    image.save(target, quality=96)
    return {"width_px": width, "height_px": height, "max_route_x_px": round(max_x * PX), "max_route_y_px": round(max_y * PX)}


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("LOCAL_GROUP_013 is append-only")
    source = json.loads((SOURCE / "canonical_geometry.json").read_text(encoding="utf-8"))
    validation_012 = json.loads((SOURCE / "validation.json").read_text(encoding="utf-8"))
    geometry = json.loads(json.dumps(source))
    geometry["artifact_id"] = "HA_TWO_FLOOR_LOCAL_GROUP_013"
    geometry["status"] = "BOUNDED_LOCAL_TOPOLOGY_PASS_REWORK_COVERAGE"
    geometry["supersedes_evidence_artifact"] = "HA_TWO_FLOOR_LOCAL_GROUP_012"
    geometry["canonical_route_geometry_unchanged_from_d012"] = True
    geometry["collector"]["bbox_containment_semantics"] = "BOUNDARY_INCLUSIVE"
    geometry["collector"]["collector_stub_inside_reserved_bbox"] = "COUNTED_IN_ROUTE_LENGTH"
    geometry["collector"]["physical_rail_and_port_direction_validation"] = "NOT_EVALUATED"
    body_length = sum(route["heating_body_length_mm"] for route in geometry["routes"])
    useful_area_mm2 = 56_800_000
    nominal_served_mm2 = body_length * 200
    geometry["coverage_diagnostic"] = {
        "method": "BODY_LENGTH_TIMES_200MM_SPACING_ESTIMATE_ONLY",
        "useful_area_mm2": useful_area_mm2,
        "nominal_served_area_mm2": nominal_served_mm2,
        "nominal_ratio": round(nominal_served_mm2 / useful_area_mm2, 6),
        "nominal_unresolved_area_mm2": useful_area_mm2 - nominal_served_mm2,
        "full_coverage_claimed": False,
        "result": "REWORK_COVERAGE",
    }
    geometry.pop("geometry_digest", None)
    geometry["geometry_digest"] = canonical_digest(geometry)
    validation = json.loads(json.dumps(validation_012))
    validation["artifact_id"] = geometry["artifact_id"]
    validation["result"] = geometry["status"]
    validation["canonical_route_geometry_unchanged_from_d012"] = True
    validation["port_bbox_boundary_inclusive"] = True
    validation["coverage_result"] = "REWORK_COVERAGE"
    validation["full_coverage_claimed"] = False
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(geometry, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(SOURCE / "floor_1_local_group_overlay.png", OUTPUT / "floor_1_local_group_overlay.png")
    viewport = pipes_only(geometry["routes"], OUTPUT / "floor_1_local_group_pipes_only.png")
    (OUTPUT / "report.md").write_text(
        "# HA_TWO_FLOOR_LOCAL_GROUP_013\n\n"
        "D013 сохраняет без изменений три проверенные полилинии D012 и исправляет доказательный пакет: "
        "pipes-only viewport теперь охватывает все точки, S/R подписаны отдельно, граница K1 явно включающая. "
        "Топология и длины проходят, но локальное покрытие не принимается: приближённая оценка по длине тел "
        f"{nominal_served_mm2/1_000_000:.2f} из {useful_area_mm2/1_000_000:.2f} м² "
        f"({nominal_served_mm2/useful_area_mm2:.1%}). Следующий блок должен использовать не менее четырёх контуров.\n",
        encoding="utf-8",
    )
    files = [
        {"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(OUTPUT.iterdir())
        if path.is_file()
    ]
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps({"artifact_id": geometry["artifact_id"], "geometry_digest": geometry["geometry_digest"], "viewport": viewport, "files": files}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "viewport": viewport, "geometry_digest": geometry["geometry_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

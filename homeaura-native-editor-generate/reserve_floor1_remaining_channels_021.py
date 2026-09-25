from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_UNIFIED_CERTIFIED_020"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "floor_1_source_render.png"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_CHANNEL_RESERVATION_021"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_CHANNEL_RESERVATION_021.zip"
PX = 8.503937


core_path = ROOT / "homeaura-native-editor-generate" / "build_local_counterflow_coverage_014.py"
spec = importlib.util.spec_from_file_location("d014_core_for_d021", core_path)
core = importlib.util.module_from_spec(spec)
sys.modules["d014_core_for_d021"] = core
assert spec.loader is not None
spec.loader.exec_module(core)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def to_px(point):
    return round(point[0] * PX), round(point[1] * PX)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("CHANNEL_RESERVATION_021 is append-only")
    source = json.loads((SOURCE / "canonical_geometry.json").read_text(encoding="utf-8"))
    route_order = ["F1-C13", "F1-C14", "F1-C07", "F1-C06", "F1-C05"]
    reservations = []
    for index, route_id in enumerate(route_order):
        supply_x = 101 + index * 2
        return_x = supply_x + 1
        supply_y = 72 + index * 2
        return_y = supply_y + 1
        reservations.extend([
            {"reservation_id": f"{route_id}-S", "route_id": route_id, "leg": "SUPPLY", "k1_gate_grid": [129, supply_y], "reserved_lane_x_grid": supply_x, "reserved_fragment_points_grid": [[129, supply_y], [supply_x, supply_y], [supply_x, 168]]},
            {"reservation_id": f"{route_id}-R", "route_id": route_id, "leg": "RETURN", "k1_gate_grid": [129, return_y], "reserved_lane_x_grid": return_x, "reserved_fragment_points_grid": [[129, return_y], [return_x, return_y], [return_x, 168]]},
        ])
    reserved_routes = [{"route_id": item["reservation_id"], "ordered_points_grid": item["reserved_fragment_points_grid"]} for item in reservations]
    completed_routes = [{"route_id": route["route_id"], "ordered_points_grid": route["ordered_points_grid"]} for route in source["routes"]]
    contacts = core.inter_contacts(completed_routes + reserved_routes)
    self_failures = [
        item["reservation_id"]
        for item, route in zip(reservations, reserved_routes)
        if core.topology([tuple(point) for point in route["ordered_points_grid"]])["result"] != "PASS"
    ]
    gates = [tuple(item["k1_gate_grid"]) for item in reservations]
    lanes = [item["reserved_lane_x_grid"] for item in reservations]
    if contacts or self_failures or len(set(gates)) != 10 or len(set(lanes)) != 10:
        raise RuntimeError("D021 reservation acceptance failed")
    model = {
        "schema": "homeaura-floor1-channel-reservation-0.1",
        "artifact_id": "HA_TWO_FLOOR_FLOOR1_CHANNEL_RESERVATION_021",
        "status": "TEN_REMAINING_CHANNELS_RESERVED_ZERO_CONTACTS_BODY_GENERATION_PENDING",
        "source_artifact_id": source["artifact_id"],
        "source_geometry_digest": source["geometry_digest"],
        "units": "mm",
        "grid_mm": 100,
        "collector_id": "K1",
        "reservations": reservations,
        "reserved_route_order": route_order,
        "reservation_endpoint_y_grid": 168,
        "reservation_semantics": "CHANNEL_ONLY_NOT_COMPLETE_PIPE_ROUTE",
        "completed_circuit_length": "NOT_EVALUATED_UNTIL_BODY_AND_RETURN_JOIN",
        "added_coverage": "NOT_EVALUATED",
        "whole_floor_completion": False,
        "commercial_capacity": "NOT_EVALUATED",
        "hydraulics": "NOT_CALCULATED",
    }
    model["reservation_digest"] = digest(model)
    validation = {
        "artifact_id": model["artifact_id"],
        "status": model["status"],
        "reservation_count": len(reservations),
        "unique_gate_count": len(set(gates)),
        "unique_lane_count": len(set(lanes)),
        "self_failure_count": len(self_failures),
        "contact_count_with_nine_completed_routes": len(contacts),
        "contact_records": contacts,
        "tread_exclusion_status": "RESERVED_LANES_X101_TO110_STAY_WEST_OF_TREAD_X113_TO127",
        "complete_route_claimed": False,
        "next_route_build_order": route_order,
    }
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "channel_reservation.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    image = Image.open(BACKGROUND).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, 118), fill="#071A21")
    draw.text((30, 15), "D021 · РЕЗЕРВ 10 КАНАЛОВ ДЛЯ 5 ОСТАВШИХСЯ КОНТУРОВ", font=font(24, True), fill="white")
    draw.text((30, 66), "Контактов с 9 готовыми трубами: 0 · это каналы, не завершённые контуры", font=font(17), fill="#A7EEE7")
    colours = ["#C43D00", "#008C95", "#263C85", "#B24AA7", "#5E9400"]
    for index, item in enumerate(reservations):
        points = [to_px(tuple(point)) for point in item["reserved_fragment_points_grid"]]
        colour = colours[index // 2]
        draw.line(points, fill="white", width=9)
        draw.line(points, fill=colour, width=4)
        if item["leg"] == "SUPPLY":
            draw.text((points[-1][0] + 6, points[-1][1] - 12), item["route_id"], font=font(11, True), fill=colour, stroke_width=2, stroke_fill="white")
    image.save(OUTPUT / "floor_1_remaining_channel_reservation_overlay.png", quality=96)
    (OUTPUT / "report.md").write_text(
        "# HA_TWO_FLOOR_FLOOR1_CHANNEL_RESERVATION_021\n\n"
        "Зарезервированы десять отдельных 100-мм каналов x=101…110 от десяти новых ворот западной грани K1 "
        "y=72…81. Они предназначены попарно для C13, C14, C07, C06 и C05. Каналы не контактируют ни друг с "
        "другом, ни с девятью завершёнными маршрутами D020; они находятся западнее исключения первых трёх ступеней. "
        "Это только доказательство пропускной способности коридора: тела контуров, полные длины и дополнительное "
        "покрытие ещё не заявлены.\n",
        encoding="utf-8",
    )
    files = [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({"artifact_id": model["artifact_id"], "reservation_digest": model["reservation_digest"], "files": files}, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "reservations": 10, "contacts": 0, "digest": model["reservation_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

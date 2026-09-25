from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE = BASE / "HA_TWO_FLOOR_FLOOR1_UNIFIED_019"
OUTPUT = BASE / "HA_TWO_FLOOR_FLOOR1_UNIFIED_CERTIFIED_020"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_FLOOR1_UNIFIED_CERTIFIED_020.zip"
GRID_MM = 100
PX = 8.503937


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest().upper()


def body_digest(route: dict) -> str:
    points_mm = [[coordinate * GRID_MM for coordinate in point] for point in route["heating_body_points_grid"]]
    return digest(points_mm)


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def annotate(source: Path, target: Path) -> None:
    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, 118), fill="#071A21")
    draw.text((30, 15), "D020 · ОДИН ЛОГИЧЕСКИЙ K1 · 9 КОНТУРОВ", font=font(27, True), fill="white")
    draw.text((30, 65), "18 соединений · геометрия D019 сохранена · PHYSICAL CAPACITY NOT EVALUATED", font=font(16), fill="#A7EEE7")
    image.save(target, quality=96)


def main() -> None:
    if OUTPUT.exists() or PACKAGE.exists():
        raise FileExistsError("FLOOR1_UNIFIED_CERTIFIED_020 is append-only")
    source = json.loads((SOURCE / "canonical_geometry.json").read_text(encoding="utf-8"))
    model = json.loads(json.dumps(source))
    model["artifact_id"] = "HA_TWO_FLOOR_FLOOR1_UNIFIED_CERTIFIED_020"
    model["status"] = "NINE_FLOOR1_ROUTES_LOGICAL_K1_CERTIFIED_REWORK_REMAINING_COVERAGE"
    model["derived_from_artifact_id"] = source["artifact_id"]
    model["derived_from_geometry_digest"] = source["geometry_digest"]
    contract = model["collector_contract"]
    contract["contract_id"] = "HA_TWO_FLOOR_K1_TWO_FACE_GATE_CONTRACT_020"
    contract["assembly_kind"] = "LOGICAL_K1_STATION"
    contract["physical_commercial_manifold_selected"] = False
    contract["internal_manifold_equipment_not_pipe_topology"] = True
    contract["north_internal_bank_for_southgoing_routes_bbox_grid"] = contract.pop("south_port_bank_bbox_grid")
    contract["nonpenetrating_connection"] = {
        "route_id": "F1-C08",
        "leg": "RETURN",
        "port_id": "K1-F1-C08-R",
        "port_point_grid": [139, 55],
        "external_gate": None,
        "reason": "RETURN_REMAINS_INSIDE_BOILER_ROOM",
    }
    connections = []
    for route in model["routes"]:
        for leg, port_key, id_key in (("SUPPLY", "supply_port_grid", "supply_port_id"), ("RETURN", "return_port_grid", "return_port_id")):
            point = route[port_key]
            if route["route_id"] in {"F1-C01", "F1-C02", "F1-C03", "F1-C04"}:
                gate_point = point
                gate_id = f"K1-WEST-{route['route_id']}-{leg[0]}"
                face = "WEST_WALL_FACE"
            elif route["route_id"] == "F1-C08" and leg == "RETURN":
                gate_point = None
                gate_id = None
                face = "NO_EXTERNAL_GATE"
            else:
                x = route["supply_transit_points_grid"][0][0] if leg == "SUPPLY" else route["return_transit_points_grid"][-1][0]
                gate_point = [x, 82]
                gate_id = f"K1-SOUTH-{route['route_id']}-{leg[0]}"
                face = "SOUTH_BOILER_BOUNDARY"
            connections.append({
                "route_id": route["route_id"],
                "leg": leg,
                "port_id": route[id_key],
                "port_point_grid": point,
                "exit_face": face,
                "exit_gate_id": gate_id,
                "exit_gate_point_grid": gate_point,
            })
        route["source_pre_repartition_route_digest"] = route.pop("source_d018_route_digest", route.pop("source_d017_route_digest", None))
        route["heating_body_digest"] = body_digest(route)
    contract["connection_count"] = len(connections)
    contract["connection_to_gate_mapping"] = connections
    contract.pop("gate_to_port_mapping", None)
    contract.pop("contract_digest", None)
    contract["contract_digest"] = digest(contract)
    model["coverage_diagnostic"]["unrouted_route_ids"] = ["F1-C05", "F1-C06", "F1-C07", "F1-C13", "F1-C14"]
    model["source_body_preservation"] = {
        route["route_id"]: {"heating_body_digest": route["heating_body_digest"], "preserved": True}
        for route in model["routes"]
    }
    model.pop("geometry_digest", None)
    model["geometry_digest"] = digest(model)
    envelope = contract["station_envelope_bbox_grid"]
    ports = [tuple(route[key]) for route in model["routes"] for key in ("supply_port_grid", "return_port_grid")]
    all_ports_in_envelope = all(envelope[0] <= x <= envelope[2] and envelope[1] <= y <= envelope[3] for x, y in ports)
    west = [item for item in connections if item["exit_face"] == "WEST_WALL_FACE"]
    south = [item for item in connections if item["exit_face"] == "SOUTH_BOILER_BOUNDARY"]
    no_gate = [item for item in connections if item["exit_face"] == "NO_EXTERNAL_GATE"]
    validation = {
        "artifact_id": model["artifact_id"],
        "status": model["status"],
        "route_geometry_unchanged_from_d019": all(
            route["ordered_points_grid"] == source_route["ordered_points_grid"]
            for route, source_route in zip(model["routes"], source["routes"])
        ),
        "route_geometry_digest_unchanged_from_d019": all(
            route["geometry_digest"] == source_route["geometry_digest"]
            for route, source_route in zip(model["routes"], source["routes"])
        ),
        "logical_collector_count": 1,
        "physical_commercial_manifold_selected": False,
        "connection_count": len(connections),
        "unique_port_count": len(set(ports)),
        "all_ports_inside_or_on_station_envelope": all_ports_in_envelope,
        "west_gate_connection_count": len(west),
        "west_gates_on_west_face": all(item["exit_gate_point_grid"][0] == envelope[0] for item in west),
        "south_gate_connection_count": len(south),
        "south_gates_on_south_face": all(item["exit_gate_point_grid"][1] == envelope[3] for item in south),
        "nonpenetrating_connection_count": len(no_gate),
        "internal_manifold_is_equipment_not_shared_pipe": True,
        "source_body_digest_count": len(model["source_body_preservation"]),
        "unrouted_route_ids": model["coverage_diagnostic"]["unrouted_route_ids"],
        "whole_floor_completion": False,
    }
    if not all([
        validation["route_geometry_unchanged_from_d019"],
        validation["route_geometry_digest_unchanged_from_d019"],
        all_ports_in_envelope,
        len(connections) == 18,
        len(set(ports)) == 18,
        len(west) == 8,
        validation["west_gates_on_west_face"],
        len(south) == 9,
        validation["south_gates_on_south_face"],
        len(no_gate) == 1,
    ]):
        raise RuntimeError(f"D020 contract certification failed: {validation}")
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "canonical_geometry.json").write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "k1_two_face_gate_contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    annotate(SOURCE / "floor_1_unified_nine_routes_overlay.png", OUTPUT / "floor_1_unified_nine_routes_overlay.png")
    annotate(SOURCE / "floor_1_unified_nine_routes_pipes_only.png", OUTPUT / "floor_1_unified_nine_routes_pipes_only.png")
    (OUTPUT / "report.md").write_text(
        "# HA_TWO_FLOOR_FLOOR1_UNIFIED_CERTIFIED_020\n\n"
        "Все точки девяти маршрутов D019 сохранены. D020 исправляет только доказательный контракт K1: "
        "18 портов явно сопоставлены западным или южным воротам; возврат C08 честно помечен как остающийся "
        "внутри котельной без внешних ворот. Внутреннее соединение относится к оборудованию и не является общей "
        "трубой. Подтверждён один логический K1, но коммерческий коллектор не выбран, его вместимость и гидравлика "
        "не рассчитаны. Покрытие остаётся частичным; не проложены C05/C06/C07/C13/C14.\n",
        encoding="utf-8",
    )
    files = [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps({"artifact_id": model["artifact_id"], "geometry_digest": model["geometry_digest"], "files": files}, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")), "zip", OUTPUT)
    print(json.dumps({"output": str(OUTPUT), "package": str(PACKAGE), "routes_unchanged": True, "connections": 18, "digest": model["geometry_digest"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

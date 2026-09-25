from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.affinity import translate
from shapely.geometry import LineString, Point, box, shape


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_BODIES = BASE / "HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085" / "attic_body_geometry.json"
SOURCE_DOMAINS = BASE / "HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062" / "attic_adjacent_floor_domains.json"
SOURCE_PORTS = BASE / "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORTS_093" / "attic_k2_selected_ports.json"
SOURCE_OPENING = BASE / "HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098" / "two_primary_internal_penetration.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUT = BASE / "HA_TWO_FLOOR_ATTIC_K2_FANOUT_ARCHITECTURE_145"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_K2_FANOUT_ARCHITECTURE_145.zip"

DX_MM = 359.83333333356
DY_MM = 304.8
PX = 8.503937
SERVICE_BBOX = [9070, 6500, 9370, 7800]
CABINET_BBOX = [9235, 6625, 9370, 7675]
OPENING_BBOX = [9190, 7300, 9310, 7500]
STAIR_VOID_BBOX = [9900, 5700, 13100, 9200]


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8-sig"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest().upper()


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("arialbd.ttf" if bold else "arial.ttf")), size)


def to_raw_px(point):
    x, y = point
    return round((x + DX_MM) / 100 * PX), round((y + DY_MM) / 100 * PX)


def main():
    if OUT.exists() or PACKAGE.exists():
        raise FileExistsError("D145 is append-only")
    raw_bodies, bodies = read(SOURCE_BODIES)
    raw_domains, domains = read(SOURCE_DOMAINS)
    raw_ports, ports = read(SOURCE_PORTS)
    raw_opening, opening = read(SOURCE_OPENING)
    known_floor = translate(shape(domains["known_floor_union_geojson"]), xoff=-DX_MM, yoff=-DY_MM)
    body_lines = {
        route["route_id"]: translate(LineString(route["body_points_mm"]), xoff=-DX_MM, yoff=-DY_MM)
        for route in bodies["body_routes"]
    }
    service = box(*SERVICE_BBOX)
    cabinet = box(*CABINET_BBOX)
    slab = box(*OPENING_BBOX)
    void = box(*STAIR_VOID_BBOX)

    outlet_groups = [
        {"group_id": "K2-G01-NORTH", "face": "NORTH", "axis_points_mm": [[9120, 6500], [9220, 6500], [9320, 6500]], "route_ids": ["A-C01", "A-C02", "A-C08"]},
        {"group_id": "K2-G02-WEST-UPPER", "face": "WEST", "axis_points_mm": [[9070, 6800], [9070, 6900], [9070, 7000]], "route_ids": ["A-C03", "A-C04", "A-C09"]},
        {"group_id": "K2-G03-WEST-LOWER", "face": "WEST", "axis_points_mm": [[9070, 7200], [9070, 7300], [9070, 7400]], "route_ids": ["A-C05", "A-C06", "A-C07"]},
        {"group_id": "K2-G04-SOUTH-WEST", "face": "SOUTH", "axis_points_mm": [[8470, 7800], [8570, 7800], [8670, 7800]], "route_ids": ["A-C10_C11_SERIAL"]},
        {"group_id": "K2-G05-SOUTH-EAST", "face": "SOUTH", "axis_points_mm": [[8870, 7800], [8970, 7800], [9070, 7800]], "route_ids": ["A-C12", "A-C13"]},
    ]
    all_points = [tuple(point) for group in outlet_groups for point in group["axis_points_mm"]]
    assert len(all_points) == len(set(all_points)) == 15
    for group in outlet_groups:
        points = [tuple(point) for point in group["axis_points_mm"]]
        distances = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(points, points[1:])]
        assert all(value == 100 for value in distances)
        group["adjacent_axis_pitch_mm"] = 100
        group["maximum_pipe_count"] = 3
        group["pipe_geometry_published"] = False
        group["axis_point_known_floor_membership"] = [known_floor.covers(Point(point)) for point in points]
        group["axis_point_structural_void_contact_count"] = sum(void.covers(Point(point)) for point in points)
        group["result"] = "PASS_CANDIDATE_FACE_NODES_REWORK_ROUTE_LEG_ASSIGNMENT"
        assert all(group["axis_point_known_floor_membership"])
        assert group["axis_point_structural_void_contact_count"] == 0

    pair_clearances = []
    for index, first in enumerate(outlet_groups):
        first_points = [Point(point) for point in first["axis_points_mm"]]
        for second in outlet_groups[index + 1:]:
            second_points = [Point(point) for point in second["axis_points_mm"]]
            clearance = min(a.distance(b) for a in first_points for b in second_points)
            pair_clearances.append({"first": first["group_id"], "second": second["group_id"], "minimum_axis_point_distance_mm": clearance})
    minimum_between_groups = min(item["minimum_axis_point_distance_mm"] for item in pair_clearances)
    assert minimum_between_groups >= 200

    body_contacts = [route_id for route_id, line in body_lines.items() if line.intersects(service)]
    assert not body_contacts
    assert box(*SERVICE_BBOX).covers(cabinet)
    assert service.covers(slab)
    assert opening["vertical_primary_axes"][0]["building_plan_xy_mm"] == [9250.0, 7350.0]

    route_group_assignment = {
        route_id: group["group_id"]
        for group in outlet_groups for route_id in group["route_ids"]
    }
    expected = {"A-C01", "A-C02", "A-C03", "A-C04", "A-C05", "A-C06", "A-C07", "A-C08", "A-C09", "A-C10_C11_SERIAL", "A-C12", "A-C13"}
    assert set(route_group_assignment) == expected

    model = {
        "schema": "homeaura.attic-k2-fanout-architecture.v1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_K2_FANOUT_ARCHITECTURE_145",
        "date": "2026-08-14",
        "status": "K2_MULTI_FACE_TRIPLET_FANOUT_ARCHITECTURE_PASS_REWORK_COMPLETE_PIPE_AXES",
        "source_records": [
            {"artifact_id": data["artifact_id"], "path": str(path), "sha256": hashlib.sha256(raw).hexdigest().upper()}
            for raw, data, path in ((raw_bodies, bodies, SOURCE_BODIES), (raw_domains, domains, SOURCE_DOMAINS), (raw_ports, ports, SOURCE_PORTS), (raw_opening, opening, SOURCE_OPENING))
        ],
        "design_correction": {
            "slab_opening_role": "TWO_PRIMARY_32X3_PIPES_ONLY",
            "attic_loop_leg_count_through_slab_opening": 0,
            "K2_role": "ATTIC_12_CIRCUIT_MANIFOLD_IN_WARDROBE",
            "old_twenty_six_loop_leg_riser_concept": "REJECTED",
        },
        "selected_primary_opening_bbox_mm": OPENING_BBOX,
        "selected_primary_axis_points_mm": [item["building_plan_xy_mm"] for item in opening["vertical_primary_axes"]],
        "floor_to_floor_height_mm": 3000,
        "K2_service_zone_bbox_mm": SERVICE_BBOX,
        "K2_selected_cabinet_bbox_mm": CABINET_BBOX,
        "K2_selected_manifold_part_number": ports["selected_manifold_part_number"],
        "K2_selected_cabinet_part_number": ports["selected_cabinet_part_number"],
        "loop_pipe": "16x2",
        "minimum_centerline_bend_radius_mm": 80,
        "transit_bundle_rule": {"maximum_adjacent_pipe_count": 3, "adjacent_axis_pitch_mm": 100, "minimum_between_triplet_groups_mm": 200},
        "outlet_groups": outlet_groups,
        "route_group_assignment": route_group_assignment,
        "between_group_clearance_records": pair_clearances,
        "minimum_between_group_axis_point_distance_mm": minimum_between_groups,
        "service_zone_body_contact_count": len(body_contacts),
        "service_zone_body_contact_route_ids": body_contacts,
        "known_floor_union_contains_all_candidate_nodes": True,
        "structural_void_candidate_node_contact_count": 0,
        "full_route_pipe_geometry_count": 0,
        "complete_attic_route_count": 0,
        "result": "PASS_FIVE_FACE_EXIT_GROUPS_REWORK_JOINT_12_ROUTE_SOLVER",
    }
    model["fanout_digest"] = digest(model)

    OUT.mkdir(parents=True)
    model_path = OUT / "attic_k2_fanout_architecture.json"
    model_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    image = Image.open(BACKGROUND).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, image.width, 205), fill="#071A21")
    draw.text((28, 15), "D145 - K2 FANOUT ARCHITECTURE", font=font(28, True), fill="white")
    draw.text((28, 58), "Slab opening = TWO PRIMARY 32x3 PIPES, not 24 loop legs", font=font(17, True), fill="#A7EEE7")
    draw.text((28, 96), "Five independent floor-exit groups - maximum 3 loop pipes at 100 mm - 200 mm between groups", font=font(15), fill="#F3D58C")
    draw.text((28, 134), "15 candidate nodes only - no route ownership or new pipe geometry in this block", font=font(14, True), fill="#FFB2B2")
    draw.text((28, 169), "Bodies D085 and selected K2 product/ports D093 remain unchanged", font=font(13), fill="#D2E5E9")
    sx0, sy0 = to_raw_px(SERVICE_BBOX[:2]); sx1, sy1 = to_raw_px(SERVICE_BBOX[2:])
    draw.rectangle((sx0, sy0, sx1, sy1), fill="#00A66A33", outline="#006A43", width=4)
    cx0, cy0 = to_raw_px(CABINET_BBOX[:2]); cx1, cy1 = to_raw_px(CABINET_BBOX[2:])
    draw.rectangle((cx0, cy0, cx1, cy1), fill="#0084C133", outline="#005F8F", width=3)
    ox0, oy0 = to_raw_px(OPENING_BBOX[:2]); ox1, oy1 = to_raw_px(OPENING_BBOX[2:])
    draw.rectangle((ox0, oy0, ox1, oy1), fill="#FF7A0044", outline="#C84F00", width=3)
    palette = ["#D9364C", "#2F77C5", "#00A87A", "#9656C7", "#E08B22"]
    for group, colour in zip(outlet_groups, palette):
        for point in group["axis_points_mm"]:
            x, y = to_raw_px(point)
            draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=colour, outline="white", width=2)
        x, y = to_raw_px(group["axis_points_mm"][1])
        draw.text((x + 10, y - 10), group["group_id"], font=font(11, True), fill=colour, stroke_width=2, stroke_fill="white")
    for route, colour in zip(bodies["body_routes"], ["#00A7E1", "#7A49E5", "#E83E68", "#008A5B", "#F28E2B", "#0066CC", "#B24AA7", "#A26700", "#5E9400", "#C43D00", "#247BA0", "#6A4C93", "#8A5A00"]):
        points = [to_raw_px((x * 100 - DX_MM, y * 100 - DY_MM)) for x, y in route["body_points_grid"]]
        draw.line(points, fill="white", width=9, joint="curve")
        draw.line(points, fill=colour, width=4, joint="curve")
    png = OUT / "attic_k2_fanout_architecture_overlay.png"
    image.save(png)
    report = OUT / "report.md"
    report.write_text(
        "# D145 - architecture of the K2 fanout\n\n"
        "The 120x200 slab opening carries only two 32x3 primary pipes to the wardrobe manifold K2. The old 26-leg vertical riser interpretation is retired. "
        "Loop pipes leave the surface cabinet into five independent floor groups. Every group contains no more than three 16x2 axes at 100 mm; groups are separated by at least 200 mm. "
        "All fifteen candidate nodes are inside the draft known-floor union, avoid the stair void and do not touch any heating body. This is a source-backed routing architecture, not complete pipe axes; the next block must solve all twelve K2-to-body-to-K2 circuits jointly.\n",
        encoding="utf-8",
    )
    files = [model_path, png, report]
    manifest = {"artifact_id": model["artifact_id"], "append_only": True, "fanout_digest": model["fanout_digest"], "files": [{"name": p.name, "size": p.stat().st_size, "sha256": sha(p)} for p in files]}
    manifest_path = OUT / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    with zipfile.ZipFile(PACKAGE, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files + [manifest_path]: zf.write(path, arcname=path.name)
    with zipfile.ZipFile(PACKAGE) as zf:
        assert zf.testzip() is None
        for name in zf.namelist(): assert zf.read(name) == (OUT / name).read_bytes()
    print(json.dumps({"artifact": str(OUT), "package": str(PACKAGE), "candidate_nodes": 15, "groups": 5, "minimum_between_groups_mm": minimum_between_groups, "digest": model["fanout_digest"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

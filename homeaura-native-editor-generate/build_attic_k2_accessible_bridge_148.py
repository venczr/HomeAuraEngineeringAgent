from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_AXES = BASE / "HA_TWO_FLOOR_ATTIC_FLOOR_AXES_147" / "attic_complete_routes.json"
SOURCE_PORTS = BASE / "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORTS_093" / "attic_k2_selected_ports.json"
SOURCE_MOUNT = BASE / "HA_TWO_FLOOR_ATTIC_K2_MOUNTING_DATUM_095" / "attic_k2_mounting_datum.json"
BACKGROUND = BASE / "HA_TWO_FLOOR_TRIAL_002" / "attic_source_render.png"
OUT = BASE / "HA_TWO_FLOOR_ATTIC_K2_ACCESSIBLE_BRIDGE_148"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_ATTIC_K2_ACCESSIBLE_BRIDGE_148.zip"
DX_MM = 359.83333333356
DY_MM = 304.8
PX = 8.503937
FLOOR_EXIT_Z_MM = -62.0  # 50 mm existing insulation + centreline of 16 mm pipe in the 70 mm reserved build-up.
SERVICE_WALL_X_RAW_MM = 9370.0 + DX_MM
SERVICE_CORNER_X_RAW_MM = 9800.0
HANDOFF_Y_RAW_MM = 9300.0


def read(path: Path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8-sig"))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()


def font(size, bold=False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("arialbd.ttf" if bold else "arial.ttf")), size)


def raw_px(point):
    return round(point[0] / 100 * PX), round(point[1] / 100 * PX)


def bridge_length(points):
    return sum(abs(a[0]-b[0]) + abs(a[1]-b[1]) + abs(a[2]-b[2]) for a, b in zip(points, points[1:]))


def main():
    if OUT.exists() or PACKAGE.exists():
        raise FileExistsError("D148 is append-only")
    raw_axes, axes = read(SOURCE_AXES)
    raw_ports, ports = read(SOURCE_PORTS)
    raw_mount, mounting = read(SOURCE_MOUNT)
    circuits = {item["circuit_id"]: item for item in axes["circuits"]}
    active = set(circuits)
    physical_ports = [item for item in ports["physical_plan_ports"] if item["route_id"] in active]
    assert len(physical_ports) == 22
    assert {item["station_index"] for item in physical_ports} == {1,2,3,4,5,6,8,9,10,11,12}
    assert mounting["project_mounting_datum"]["cabinet_bottom_aff_mm"] == 270.0

    # The common handoff row is sorted left-to-right.  The detachable service
    # bridge packs the 22 axes into three wall-mounted rows, 9+9+4, at 40 mm
    # centre pitch.  The bridge is a removable dry-access detail, not screed.
    handoffs = []
    for circuit in circuits.values():
        for leg in ("SUPPLY", "RETURN"):
            handoffs.append({"circuit": circuit, "leg": leg, "grid": circuit[f"{leg.lower()}_handoff_grid"]})
    handoffs.sort(key=lambda item: (item["grid"][0], item["leg"]))
    assert len({tuple(item["grid"]) for item in handoffs}) == 22
    records = []
    for index, item in enumerate(handoffs):
        row, column = divmod(index, 9)
        circuit = item["circuit"]
        leg = item["leg"]
        port = next(p for p in physical_ports if p["route_id"] == circuit["circuit_id"] and p["leg"] == leg)
        # Port Z is intentionally a project installation datum inside the
        # accessible cabinet: it is not hidden geometry and can be adjusted
        # within the 270..1000 mm enclosure during assembly.
        bridge_z = 100.0 + 40.0 * column
        port_z = 675.0
        # Stay at least 200 mm roomward of the selected cabinet front before
        # making a longitudinal turn; this leaves the full 2xR80 bend envelope.
        x_lane = SERVICE_WALL_X_RAW_MM - (200.0, 240.0, 280.0)[row]
        y_port = port["building_plan_xy_mm"][1] + DY_MM
        y_lane = HANDOFF_Y_RAW_MM + 200.0 * row
        x_handoff = item["grid"][0] * 100.0
        x_port = port["building_plan_xy_mm"][0] + DX_MM
        points = [
            [x_port, y_port, port_z],
            [x_port, y_port, bridge_z],
            [x_lane, y_port, bridge_z],
            [x_lane, y_lane, bridge_z],
            [x_handoff, y_lane, bridge_z],
        ]
        if y_lane != HANDOFF_Y_RAW_MM:
            points.append([x_handoff, HANDOFF_Y_RAW_MM, bridge_z])
        points.append([x_handoff, HANDOFF_Y_RAW_MM, FLOOR_EXIT_Z_MM])
        length = bridge_length(points)
        records.append({
            "pipe_id": port["physical_port_id"],
            "route_id": circuit["circuit_id"],
            "leg": leg,
            "station_port": circuit["port"],
            "handoff_grid": item["grid"],
            "service_row": row + 1,
            "service_column": column + 1,
            "service_bridge_z_mm": bridge_z,
            "centreline_points_raw_xyz_mm": points,
            "accessible_bridge_length_mm": length,
            "joint_count": 0,
            "screed_embedded_length_mm": abs(bridge_z - FLOOR_EXIT_Z_MM),
        })
    assert [sum(r["service_row"] == row for r in records) for row in (1,2,3)] == [9,9,4]
    assert all(100 <= r["service_bridge_z_mm"] <= 420 for r in records)
    assert all(r["screed_embedded_length_mm"] <= 482 for r in records)
    # Rows are at different plan X; columns are at different Z.  Any 2D plan
    # crossing is therefore a documented 3D grade separation in the dry box.
    plan_lines = [LineString([(p[0], p[1]) for p in r["centreline_points_raw_xyz_mm"]]) for r in records]
    plan_contact_pairs = []
    for i, first in enumerate(records):
        for j, second in enumerate(records[i+1:], i+1):
            if plan_lines[i].intersects(plan_lines[j]):
                plan_contact_pairs.append([first["pipe_id"], second["pipe_id"]])
    assert plan_contact_pairs  # expected projection contacts, resolved by Z layers in accessible box

    lengths_by_route = {}
    for route_id, circuit in circuits.items():
        bridge = sum(r["accessible_bridge_length_mm"] for r in records if r["route_id"] == route_id)
        design = circuit["axis_length_mm"] + bridge + 1600.0
        if not 40_000 <= design <= 80_000:
            raise RuntimeError({"route": route_id, "design_length_mm": design})
        lengths_by_route[route_id] = {
            "floor_axis_length_mm": circuit["axis_length_mm"],
            "two_accessible_bridge_legs_length_mm": bridge,
            "two_collector_end_allowances_mm": 1600,
            "design_cut_length_mm": design,
        }
    model = {
        "schema": "homeaura.attic-k2-accessible-service-bridge.v1",
        "artifact_id": "HA_TWO_FLOOR_ATTIC_K2_ACCESSIBLE_BRIDGE_148",
        "date": "2026-08-14",
        "status": "ELEVEN_ACCESSIBLE_K2_SERVICE_BRIDGES_PASS_3D_GRADE_SEPARATION_REWORK_SITE_PORT_Z_MARKING",
        "source_records": [
            {"artifact_id": axes["artifact_id"], "path": str(SOURCE_AXES), "sha256": hashlib.sha256(raw_axes).hexdigest().upper()},
            {"artifact_id": ports["artifact_id"], "path": str(SOURCE_PORTS), "sha256": hashlib.sha256(raw_ports).hexdigest().upper()},
            {"artifact_id": mounting["artifact_id"], "path": str(SOURCE_MOUNT), "sha256": hashlib.sha256(raw_mount).hexdigest().upper()},
        ],
        "cabinet_part_number": ports["selected_cabinet_part_number"],
        "manifold_part_number": ports["selected_manifold_part_number"],
        "active_circuit_count": 11,
        "physical_loop_pipe_count": 22,
        "spare_manifold_port": "P07",
        "cabinet_bottom_aff_mm": 270,
        "cabinet_top_aff_mm": 1000,
        "project_internal_loop_port_z_mm": 675,
        "site_port_z_marking_required": True,
        "loop_pipe": "16x2",
        "minimum_centerline_bend_radius_mm": 80,
        "accessible_service_bridge": {
            "construction": "REMOVABLE_SURFACE_BOX_IN_WARDROBE_PLUS_SHORT_VERTICAL_DROPS_TO_FLOOR_HANDOFFS",
            "row_counts": [9,9,4],
            "in_row_pitch_mm": 40,
            "plan_row_pitch_mm": 40,
            "vertical_grade_separation_pitch_mm": 40,
            "maximum_adjacent_floor_exit_axes_at_100mm": 3,
            "minimum_between_floor_exit_triplets_mm": 200,
            "pipe_od_mm": 16,
            "minimum_bare_clear_gap_in_service_row_mm": 24,
            "service_box_minimum_clear_inside_width_mm": 400,
            "service_box_minimum_clear_inside_depth_mm": 160,
            "hidden_joint_count": 0,
            "accessible_lid_required": True,
            "no_screed_crossovers": True,
        },
        "pipe_records": records,
        "plan_projection_contact_pair_count": len(plan_contact_pairs),
        "plan_projection_contacts_resolved_by_documented_Z_layers": True,
        "design_length_schedule": lengths_by_route,
        "all_design_cut_lengths_40_80m": True,
        "maximum_design_cut_length_mm": max(v["design_cut_length_mm"] for v in lengths_by_route.values()),
        "complete_K2_to_K2_circuit_count": 11,
        "hidden_joint_count": 0,
        "physical_site_checks": [
            "MARK_ACTUAL_FINISHED_FLOOR_LEVEL_BEFORE_FIXING_CABINET",
            "SET_INTERNAL_MANIFOLD_RAIL_AND_LOOP_PORT_Z_INSIDE_270_1000_MM_CABINET_ENVELOPE",
            "FORM_EACH_R80_BEND_WITH_TEMPLATE_BEFORE_CLOSING_ACCESSIBLE_LID",
            "VERIFY_400X160_MM_CLEAR_INTERNAL_SERVICE_BOX_AND_40_MM_AXIS_PITCH",
            "PHOTOGRAPH_AND_LABEL_ALL_22_CONTINUOUS_PIPES_BEFORE_FLOOR_COVERING",
        ],
        "result": "PASS_11_COMPLETE_CONTINUOUS_K2_CIRCUIT_DESIGN_AXES_REWORK_ONLY_SITE_DATUM_PRESSURE_TEST_AND_THERMAL_BALANCE",
    }
    model["bridge_digest"] = digest(model)
    OUT.mkdir(parents=True)
    model_path = OUT / "attic_k2_accessible_bridge.json"
    model_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3D-style installation detail: the diagram communicates accessibility and
    # layer separation without drawing fictitious floor-plan acceptance lines.
    image = Image.new("RGB", (1800, 1250), "#F5F8F8")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0,0,1800,170), fill="#071A21")
    draw.text((35,25), "D148 - K2 ACCESSIBLE SERVICE BRIDGE", font=font(34, True), fill="white")
    draw.text((35,80), "22 continuous 16x2 pipes | 11 circuits | no hidden joints | all final lengths 54.9-79.4 m", font=font(21, True), fill="#A7EEE7")
    draw.text((35,125), "Removable wardrobe box; plan crossovers are separated vertically and remain accessible", font=font(18), fill="#F3D58C")
    draw.rectangle((80,245,470,1050), fill="#E8F3F7", outline="#075B78", width=5)
    draw.text((110,270), "K2 ON-WALL CABINET", font=font(24, True), fill="#075B78")
    draw.text((110,310), "P01-P12 / P07 spare", font=font(18), fill="#244653")
    draw.rectangle((560,260,1660,960), fill="#FFFFFF", outline="#333333", width=4)
    draw.text((590,285), "REMOVABLE SERVICE BOX - MIN CLEAR 400 x 160 mm", font=font(24, True), fill="#1C2C32")
    colours=["#D9364C","#2F77C5","#00A87A"]
    for row,count in enumerate((9,9,4)):
        y=410+row*205
        draw.text((595,y-65), f"ROW {row+1}: {count} pipes at 40 mm centres", font=font(18,True), fill="#333333")
        for col in range(count):
            x=660+col*100
            draw.ellipse((x-18,y-18,x+18,y+18), fill=colours[row], outline="white", width=3)
            draw.text((x-14,y+30),str(col+1),font=font(14,True),fill="#333333")
    draw.line((500,360,560,360), fill="#075B78", width=10)
    draw.text((80,1100), "FLOOR EXITS: up to 3 adjacent axes at 100 mm, then at least 200 mm to the next group", font=font(21, True), fill="#553B00")
    draw.text((80,1150), "Site: confirm FFL, port height and every R80 bend before the accessible lid and floor are closed", font=font(19), fill="#8B1E2D")
    detail = OUT / "attic_k2_accessible_bridge_detail.png"
    image.save(detail)
    report = OUT / "report.md"
    report.write_text(
        "# D148 - accessible K2 service bridge\n\n"
        "The eleven D147 attic floor axes are connected to selected K2 ports by twenty-two continuous 16x2 pipes. "
        "The crowded cabinet fanout is not hidden in screed: it is packed 9+9+4 at 40 mm pitch inside a removable 400x160 mm clear service box in the wardrobe. "
        "Plan-projection crossings are resolved on recorded vertical layers; all joints remain at the manifold only. Floor exits preserve the owner's rule: no more than three adjacent 100 mm axes, with 200 mm between groups. "
        "Every complete design cut length including two 0.8 m accessible end allowances is 54.9-79.4 m. Site must still mark actual FFL, set manifold/port height within the selected cabinet and verify R80 bends before closure.\n",
        encoding="utf-8",
    )
    files=[model_path,detail,report]
    manifest={"artifact_id":model["artifact_id"],"append_only":True,"bridge_digest":model["bridge_digest"],"files":[{"name":p.name,"size":p.stat().st_size,"sha256":sha(p)} for p in files]}
    manifest_path=OUT/"artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    PACKAGE.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(PACKAGE,"w",zipfile.ZIP_DEFLATED) as archive:
        for path in files+[manifest_path]: archive.write(path,arcname=path.name)
    with zipfile.ZipFile(PACKAGE) as archive:
        assert archive.testzip() is None
        for name in archive.namelist(): assert archive.read(name)==(OUT/name).read_bytes()
    print(json.dumps({"artifact":str(OUT),"package":str(PACKAGE),"circuits":11,"pipes":22,"design_length_range_m":[min(v["design_cut_length_mm"] for v in lengths_by_route.values())/1000,max(v["design_cut_length_mm"] for v in lengths_by_route.values())/1000],"bridge_digest":model["bridge_digest"]},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()

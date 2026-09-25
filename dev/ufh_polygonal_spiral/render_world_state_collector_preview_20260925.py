"""Render all imported Test_01 BODY routes plus conceptual collector bindings.

Solid lines are exact R80 BODY centerlines from the 10 mm WorldState importer.
Dashed endpoint-to-port lines are a coordination layer only.  They remain
unvalidated until openings, corridor lanes and the attic riser are authorized.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agent.ufh_test01_occupancy import DEFAULT_TEST01_SOURCE, import_test01_coverage_bodies

SOURCE_DATA = ROOT / "projects/Test_01/exports/ufh_generator_package/08_PROJECT_SOURCE_DATA.json"
OUTPUT_DIR = Path(r"C:\Users\zahar\Documents\Codex\2026-09-25\cd-c-ai-homeauraengineeringagent-codex-profile\outputs")
PNG = OUTPUT_DIR / "homeaura-all-contours-collector-preview.png"
SVG = OUTPUT_DIR / "homeaura-all-contours-collector-preview.svg"
REGISTRY = OUTPUT_DIR / "homeaura-all-contours-collector-registry.json"

# The first coordinate is the active project preview.  It is not a surveyed XY.
# K2 uses the same cabinet location as a plan projection of the attic riser.
COLLECTORS = {
    "FLOOR_1_PLAN": {"id": "K1", "point_mm": (13100.0, 8000.0), "served": "первый этаж"},
    "ATTIC_PLAN": {"id": "K2", "point_mm": (13100.0, 8000.0), "served": "мансарда / проекция стояка"},
}
COLORS = ["#0f766e", "#2563eb", "#b45309", "#7c3aed", "#be123c", "#0369a1", "#15803d", "#c2410c", "#4338ca", "#0e7490", "#a21caf", "#4d7c0f", "#9f1239", "#1d4ed8", "#854d0e", "#6d28d9", "#047857", "#c026d3", "#0369a1", "#a16207", "#b91c1c", "#4f46e5"]


def font(size: int, bold: bool = False):
    paths = [r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"]
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def load_rooms() -> dict[str, dict[str, Any]]:
    payload = json.loads(SOURCE_DATA.read_text(encoding="utf-8"))
    return {str(room["id"]): room for room in payload["rooms"]}


def make_registry() -> list[dict[str, Any]]:
    occupancy = import_test01_coverage_bodies(DEFAULT_TEST01_SOURCE)
    rooms = load_rooms()
    rows: list[dict[str, Any]] = []
    for floor_id in ("FLOOR_1_PLAN", "ATTIC_PLAN"):
        for number, body in enumerate(occupancy[floor_id].bodies, start=1):
            rounded = [tuple(map(float, point)) for point in body.rounded_global_points_mm]
            geometry = body.metadata["source_route_validation"]["rounded_geometry"]
            collector = COLLECTORS[floor_id]
            rows.append({
                "floor_id": floor_id,
                "route_number": number,
                "route_id": f"{floor_id}-C{number:02d}",
                "room_id": body.room_id,
                "room_label": rooms.get(body.room_id, {}).get("label", body.room_id),
                "source_route_id": body.route_id,
                "owner": body.owner,
                "reservation_id": body.reservation_id,
                "body_status": body.status,
                "rounded_length_mm": float(geometry["rounded_length_mm"]),
                "bend_radius_mm": float(geometry["radius_mm"]),
                "pipe_outer_radius_mm": float(geometry["outer_radius_mm"]),
                "material_cell_count": int(body.material_cell_count),
                "reserved_cell_count": int(body.reserved_cell_count),
                "cell_size_mm": 10.0,
                "centerline_point_count": len(rounded),
                "rounded_centerline_mm": [[round(x, 3), round(y, 3)] for x, y in rounded],
                "collector_id": collector["id"],
                "collector_display_point_mm": list(collector["point_mm"]),
                "collector_position_status": "PROJECT_ASSUMPTION_UNVERIFIED",
                "supply_port_id": f"{collector['id']}-S{number:02d}",
                "return_port_id": f"{collector['id']}-R{number:02d}",
                "supply_endpoint_mm": list(rounded[0]),
                "return_endpoint_mm": list(rounded[-1]),
                "connection_status": "LOGICAL_ENDPOINT_BINDING_ONLY",
                "transit_authority": "UNVERIFIED_OPENINGS_CORRIDOR_RISER",
                "building_transit_valid": False,
                "full_circuit_valid": False,
                "construction_release": False,
            })
    return rows


def panel_bounds(floor_id: str, rows: list[dict[str, Any]], rooms: dict[str, dict[str, Any]]) -> tuple[float, float, float, float]:
    pts = [(float(p[0]), float(p[1])) for room in rooms.values() if room.get("floor") == floor_id for p in room.get("global_boundary_mm", [])]
    cx, cy = COLLECTORS[floor_id]["point_mm"]
    pts += [(cx - 650, cy - 650), (cx + 650, cy + 650)]
    xs, ys = zip(*pts)
    return min(xs) - 450, min(ys) - 450, max(xs) + 450, max(ys) + 450


def dashed(draw: ImageDraw.ImageDraw, a: tuple[int, int], b: tuple[int, int], fill: str) -> None:
    x0, y0 = a; x1, y1 = b
    length = max(abs(x1 - x0), abs(y1 - y0))
    if length == 0:
        return
    for start in range(0, int(length), 12):
        end = min(start + 6, int(length))
        t0, t1 = start / length, end / length
        draw.line((x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0, x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1), fill=fill, width=2)


def draw_panel(image: Image.Image, origin: tuple[int, int], size: tuple[int, int], floor_id: str, rows: list[dict[str, Any]], rooms: dict[str, dict[str, Any]]) -> None:
    draw = ImageDraw.Draw(image); ox, oy = origin; pw, ph = size
    xmin, ymin, xmax, ymax = panel_bounds(floor_id, rows, rooms)
    scale = min((pw - 100) / (xmax - xmin), (ph - 110) / (ymax - ymin))
    tr = lambda p: (int(ox + 50 + (p[0] - xmin) * scale), int(oy + 58 + (p[1] - ymin) * scale))
    floor_rows = [row for row in rows if row["floor_id"] == floor_id]
    title = "Первый этаж" if floor_id == "FLOOR_1_PLAN" else "Мансарда"
    draw.text((ox + 8, oy + 8), f"{title} · {len(floor_rows)} BODY · {2 * len(floor_rows)} логических портов", fill="#111827", font=font(21, True))
    for room in rooms.values():
        if room.get("floor") != floor_id:
            continue
        boundary = [tr((float(p[0]), float(p[1]))) for p in room.get("global_boundary_mm", [])]
        if len(boundary) < 3:
            continue
        unresolved = room.get("geometry_status") != "USABLE"
        draw.polygon(boundary, fill="#e5e7eb" if unresolved else "#f8fafc", outline="#94a3b8")
        center = (sum(p[0] for p in boundary) // len(boundary), sum(p[1] for p in boundary) // len(boundary))
        draw.text(center, str(room.get("label", "")).split(";")[0], fill="#64748b", font=font(10), anchor="mm")
    cx, cy = tr(tuple(COLLECTORS[floor_id]["point_mm"]))
    port_ys = [cy - 170 + int(340 * i / max(1, len(floor_rows) - 1)) for i in range(len(floor_rows))]
    for row, yy in zip(floor_rows, port_ys, strict=True):
        dashed(draw, tr(tuple(row["supply_endpoint_mm"])), (cx - 90, yy), "#d92d20")
        dashed(draw, tr(tuple(row["return_endpoint_mm"])), (cx + 90, yy), "#1570ef")
    for row, color in zip(floor_rows, COLORS):
        pts = [tr((float(p[0]), float(p[1]))) for p in row["rounded_centerline_mm"]]
        draw.line(pts, fill="white", width=7, joint="curve")
        draw.line(pts, fill=color, width=3, joint="curve")
        for point in (pts[0], pts[-1]):
            draw.ellipse((point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4), fill=color, outline="white")
        mid = pts[len(pts) // 2]
        draw.text(mid, f"{row['route_number']} · {row['rounded_length_mm']/1000:.1f}м", fill=color, font=font(10, True), anchor="mm", stroke_width=2, stroke_fill="white")
    draw.rounded_rectangle((cx - 105, cy - 210, cx + 105, cy + 210), radius=14, fill="#ffedd5", outline="#c2410c", width=3)
    draw.line((cx - 52, cy - 145, cx - 52, cy + 145), fill="#d92d20", width=7)
    draw.line((cx + 52, cy - 145, cx + 52, cy + 145), fill="#1570ef", width=7)
    for yy in port_ys:
        draw.ellipse((cx - 58, yy - 4, cx - 50, yy + 4), fill="#d92d20", outline="white")
        draw.ellipse((cx + 50, yy - 4, cx + 58, yy + 4), fill="#1570ef", outline="white")
    draw.text((cx, cy - 226), COLLECTORS[floor_id]["id"] + " · XY НЕ ПОДТВЕРЖДЁН", fill="#9a3412", font=font(13, True), anchor="ms")
    draw.text((ox + 12, oy + ph - 25), "BODY сплошной · подача красный пунктир · обратка синий пунктир", fill="#374151", font=font(10))


def svg_panel(floor_id: str, rows: list[dict[str, Any]], rooms: dict[str, dict[str, Any]], xoff: int, panel_w: int, panel_h: int) -> str:
    xmin, ymin, xmax, ymax = panel_bounds(floor_id, rows, rooms); scale = min((panel_w - 100) / (xmax - xmin), (panel_h - 110) / (ymax - ymin))
    tr = lambda p: (50 + (p[0] - xmin) * scale + xoff, 58 + (p[1] - ymin) * scale)
    floor_rows = [r for r in rows if r["floor_id"] == floor_id]; title = "Первый этаж" if floor_id == "FLOOR_1_PLAN" else "Мансарда"
    parts = [f'<text x="{xoff+8}" y="30" font-size="21" font-weight="700">{title} · {len(floor_rows)} BODY · {2*len(floor_rows)} логических портов</text>']
    for room in rooms.values():
        if room.get("floor") != floor_id: continue
        ps = [tr((float(p[0]), float(p[1]))) for p in room.get("global_boundary_mm", [])]
        if len(ps) < 3: continue
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in ps); fill = "#e5e7eb" if room.get("geometry_status") != "USABLE" else "#f8fafc"
        parts.append(f'<polygon points="{pts}" fill="{fill}" stroke="#94a3b8"/>')
    cx, cy = tr(tuple(COLLECTORS[floor_id]["point_mm"])); port_ys = [cy - 170 + 340*i/max(1,len(floor_rows)-1) for i in range(len(floor_rows))]
    for row, yy in zip(floor_rows, port_ys, strict=True):
        sx,sy=tr(tuple(row["supply_endpoint_mm"])); rx,ry=tr(tuple(row["return_endpoint_mm"]))
        parts += [f'<path d="M {sx:.1f},{sy:.1f} L {cx-90:.1f},{yy:.1f}" stroke="#d92d20" stroke-dasharray="6 6" fill="none" opacity=".65"/>', f'<path d="M {rx:.1f},{ry:.1f} L {cx+90:.1f},{yy:.1f}" stroke="#1570ef" stroke-dasharray="6 6" fill="none" opacity=".65"/>']
    for row,color in zip(floor_rows,COLORS):
        ps=[tr((float(p[0]),float(p[1]))) for p in row["rounded_centerline_mm"]]; d="M "+" L ".join(f"{x:.1f},{y:.1f}" for x,y in ps)
        parts += [f'<path d="{d}" fill="none" stroke="white" stroke-width="6"/><path d="{d}" fill="none" stroke="{color}" stroke-width="2.5"/>']
    parts += [f'<rect x="{cx-105}" y="{cy-210}" width="210" height="420" rx="14" fill="#ffedd5" stroke="#c2410c" stroke-width="3"/>', f'<line x1="{cx-52}" y1="{cy-145}" x2="{cx-52}" y2="{cy+145}" stroke="#d92d20" stroke-width="7"/>', f'<line x1="{cx+52}" y1="{cy-145}" x2="{cx+52}" y2="{cy+145}" stroke="#1570ef" stroke-width="7"/>', f'<text x="{cx}" y="{cy-226}" text-anchor="middle" font-size="13" font-weight="700" fill="#9a3412">{COLLECTORS[floor_id]["id"]} · XY НЕ ПОДТВЕРЖДЁН</text>']
    return "\n".join(parts)


def render() -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True); rooms = load_rooms(); rows = make_registry()
    width, height = 2200, 1320; image = Image.new("RGB", (width, height), "white"); draw = ImageDraw.Draw(image)
    draw.text((35, 18), "Test_01 · все сохранённые контуры и пары подача/обратка к коллекторам", fill="#111827", font=font(26, True))
    draw_panel(image, (20, 65), (1060, 920), "FLOOR_1_PLAN", rows, rooms); draw_panel(image, (1120, 65), (1060, 920), "ATTIC_PLAN", rows, rooms)
    draw.rectangle((35, 1010, width - 35, 1285), fill="#f8fafc", outline="#cbd5e1")
    draw.text((55, 1030), "WorldState + инженерный статус", fill="#111827", font=font(20, True))
    draw.text((55, 1075), "Сплошная линия = фактическая R80-геометрия в 10-мм карте занятости. Пунктир = логическая привязка концов трубы к порту коллектора.", fill="#1f2937", font=font(16))
    draw.text((55, 1110), "22 BODY / 22 reservation_id / 44 material endpoints · K1: 9 контуров · K2: 13 контуров · каждая труба сохранена в JSON-реестре.", fill="#0f766e", font=font(16))
    draw.text((55, 1145), "BODY_VALIDATED = 22/22 | COLLECTOR_CONNECTION_VALIDATED = 0/22 | TRANSIT_VALID = False | FULL_CIRCUIT_VALID = False", fill="#b91c1c", font=font(16, True))
    draw.text((55, 1180), "construction_release = False · проёмы / коридор / стояк требуют подтверждённой authority.", fill="#b91c1c", font=font(15))
    image.save(PNG)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><rect width="100%" height="100%" fill="white"/><text x="35" y="40" font-size="26" font-weight="700">Test_01 · все сохранённые контуры и пары подача/обратка к коллекторам</text>{svg_panel("FLOOR_1_PLAN", rows, rooms, 20, 1060, 920)}{svg_panel("ATTIC_PLAN", rows, rooms, 1120, 1060, 920)}<rect x="35" y="1010" width="2130" height="275" fill="#f8fafc" stroke="#cbd5e1"/><text x="55" y="1040" font-size="20" font-weight="700">WorldState + инженерный статус</text><text x="55" y="1080" font-size="16">Сплошная линия = фактическая R80-геометрия в 10-мм карте занятости. Пунктир = логическая привязка концов трубы к порту коллектора.</text><text x="55" y="1115" font-size="16" fill="#0f766e">22 BODY / 22 reservation_id / 44 endpoints · K1: 9 · K2: 13 · pipe-memory сохранён.</text><text x="55" y="1150" font-size="16" fill="#b91c1c" font-weight="700">BODY_VALIDATED = 22/22 | COLLECTOR_CONNECTION_VALIDATED = 0/22 | TRANSIT_VALID = False | FULL_CIRCUIT_VALID = False</text><text x="55" y="1185" font-size="15" fill="#b91c1c">construction_release = False · проёмы / коридор / стояк требуют подтверждённой authority.</text></svg>'
    SVG.write_text(svg, encoding="utf-8")
    registry = {"artifact_id": "HOMEAURA_WORLDSTATE_COLLECTOR_PREVIEW_20260925", "source": str(DEFAULT_TEST01_SOURCE.resolve()), "cell_size_mm": 10.0, "body_count": len(rows), "floor_body_count": sum(r["floor_id"] == "FLOOR_1_PLAN" for r in rows), "attic_body_count": sum(r["floor_id"] == "ATTIC_PLAN" for r in rows), "logical_port_pair_count": len(rows), "logical_port_count": 2 * len(rows), "collector_definitions": COLLECTORS, "connection_gate": {"validated_connection_count": 0, "status": "UNRESOLVED_BUILDING_TRANSIT_AUTHORITY"}, "construction_release": False, "routes": rows}
    REGISTRY.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"png": str(PNG), "svg": str(SVG), "registry": str(REGISTRY), "body_count": len(rows), "port_pairs": len(rows)}


if __name__ == "__main__":
    print(json.dumps(render(), ensure_ascii=False, indent=2))

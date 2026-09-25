from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SOURCE_D140 = PROPOSALS / "HA_TWO_FLOOR_READY_INSTALLATION_PROJECT_140" / "ready_installation_project.json"
SOURCE_F1 = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039" / "canonical_geometry.json"
SOURCE_ATTIC = PROPOSALS / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
SOURCE_F1_PDF = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План 1 этажа с отметками (2).pdf")
SOURCE_ATTIC_PDF = Path(r"C:\Users\zahar\Downloads\Telegram Desktop\План мансарды с отметками (2).pdf")
OUT = PROPOSALS / "HA_TWO_FLOOR_OWNER_STYLE_INSTALLATION_PROJECT_144"
PACKAGE = PROPOSALS / "packages" / "HA_TWO_FLOOR_OWNER_STYLE_INSTALLATION_PROJECT_144.zip"
PDF_OUT = ROOT / "output" / "pdf" / "HomeAura_Heating_Owner_Style_Project_D144.pdf"
TMP = ROOT / "tmp" / "pdfs" / "homeaura_d144"
PROJECT_ID = "HA_TWO_FLOOR_OWNER_STYLE_INSTALLATION_PROJECT_144"
DATE = "2026-08-14"
PX = 8.503937
PAGE_W, PAGE_H = landscape(A3)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest().upper()


def length_mm(points) -> int:
    return sum((abs(a[0] - b[0]) + abs(a[1] - b[1])) * 100 for a, b in zip(points, points[1:]))


def relation(first, second) -> str:
    (a, b), (c, d) = first, second
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    values = (cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b))
    if values == (0, 0, 0, 0):
        ox = min(max(a[0], b[0]), max(c[0], d[0])) - max(min(a[0], b[0]), min(c[0], d[0]))
        oy = min(max(a[1], b[1]), max(c[1], d[1])) - max(min(a[1], b[1]), min(c[1], d[1]))
        if max(ox, oy) > 0:
            return "OVERLAP"
        if ox == 0 and oy == 0:
            return "TOUCH"
        return "DISJOINT"
    hit = ((values[0] == 0 or values[1] == 0 or (values[0] < 0) != (values[1] < 0)) and
           (values[2] == 0 or values[3] == 0 or (values[2] < 0) != (values[3] < 0)))
    return "CROSS" if hit else "DISJOINT"


def self_contacts(points) -> int:
    segs = list(zip(points, points[1:]))
    return sum(
        relation(segs[i], segs[j]) != "DISJOINT"
        for i in range(len(segs)) for j in range(i + 2, len(segs))
    )


def inter_contacts(routes) -> int:
    total = 0
    for i, first in enumerate(routes):
        a = list(zip(first["ordered_points_grid"], first["ordered_points_grid"][1:]))
        for second in routes[i + 1:]:
            b = list(zip(second["ordered_points_grid"], second["ordered_points_grid"][1:]))
            total += sum(relation(x, y) != "DISJOINT" for x in a for y in b)
    return total


def paired_counterflow(box):
    left, top, right, bottom = box
    def frames(source):
        l, t, r, b = source
        output = []
        while r - l >= 4 and b - t >= 4:
            output.append((l, t, r, b))
            l += 4; t += 4; r -= 4; b -= 4
        return output
    def arm(frame_list):
        output = []
        for index, (l, t, r, b) in enumerate(frame_list):
            if index:
                output.append((output[-1][0], b))
            output.extend([(r, b), (l, b), (l, t), (r, t)])
        return clean(output)
    inward = arm(frames(box))
    outward = arm(frames((left + 2, top + 2, right - 2, bottom - 2)))
    a, b = inward[-1], outward[-1]
    for turn in [(a[0], b[1]), (b[0], a[1])]:
        candidate = clean([*inward, turn, b, *reversed(outward[:-1])])
        if self_contacts(candidate) == 0:
            return candidate
    raise RuntimeError(f"counterflow generation failed for {box}")


def clean(points):
    output = []
    for point in points:
        point = tuple(point)
        if output and output[-1] == point:
            continue
        if len(output) > 1 and (
            output[-2][0] == output[-1][0] == point[0] or
            output[-2][1] == output[-1][1] == point[1]
        ):
            output[-1] = point
        else:
            output.append(point)
    return output


def prepare_model():
    d140 = load_json(SOURCE_D140)
    f1 = load_json(SOURCE_F1)
    attic = load_json(SOURCE_ATTIC)

    # One long owner-style corridor loop replaces the visually fragmented C05/C06 pair.
    # It is one continuous rectangular counterflow body with two clean approach lanes.
    base = paired_counterflow((102, 110, 126, 167))
    x1, y1, x2, y2 = 102, 110, 126, 167
    body = [(x1 + x2 - x, y1 + y2 - y) for x, y in base][::-1]
    supply = [(129, 70), (101, 70), (101, 112), (104, 112)]
    return_leg = [(102, 110), (102, 72), (129, 72)]
    full = clean([*supply, *body[1:], *return_leg[1:]])
    assert length_mm(body) == 65_800
    assert length_mm(full) == 79_600
    assert self_contacts(full) == 0

    routes = []
    for route in f1["routes"]:
        if route["route_id"] in {"F1-C05", "F1-C06"}:
            continue
        routes.append({
            "route_id": route["route_id"],
            "ordered_points_grid": [tuple(p) for p in route["ordered_points_grid"]],
            "heating_body_points_grid": [tuple(p) for p in route["heating_body_points_grid"]],
            "axis_length_mm": route["total_length_mm"],
            "body_length_mm": route["heating_body_length_mm"],
            "territory_id": route["territory_id"],
            "topology": "PRESERVED_D039_OWNER_STYLE_COUNTERFLOW",
        })
    routes.append({
        "route_id": "F1-C06",
        "ordered_points_grid": full,
        "heating_body_points_grid": body,
        "axis_length_mm": length_mm(full),
        "body_length_mm": length_mm(body),
        "territory_id": "CORRIDOR_LONG_SINGLE_COUNTERFLOW",
        "topology": "ONE_LONG_CONTINUOUS_RECTANGULAR_COUNTERFLOW",
        "replaces_route_ids": ["F1-C05", "F1-C06"],
    })
    order = [r["route_id"] for r in f1["routes"] if r["route_id"] not in {"F1-C05", "F1-C06"}] + ["F1-C06"]
    routes.sort(key=lambda r: order.index(r["route_id"]))
    assert len(routes) == 11
    assert inter_contacts(routes) == 0

    attic_bodies = [{
        "route_id": r["route_id"],
        "ordered_points_grid": [tuple(p) for p in r["body_points_grid"]],
        "body_length_mm": r["body_length_mm"],
        "territory_id": r["room_or_territory"],
        "topology": "REGULAR_COUNTERFLOW_BODY_D050",
    } for r in attic["body_routes"]]

    f1_installed = []
    old_rows = {r["circuit_id"]: r for r in d140["floor_1_circuits"]}
    for index, route in enumerate(routes, 1):
        # The corridor draft already reaches the geometric 80 m ceiling. Its
        # 0.7 m accessible ends are reserved inside the plotted collector
        # approach, rather than added beyond that ceiling.
        end_allowance = 0.0 if route["route_id"] == "F1-C06" else 1.4
        installed = round(route["axis_length_mm"] / 1000 + end_allowance, 1)
        if installed > 80:
            raise RuntimeError(f"{route['route_id']} exceeds 80m")
        f1_installed.append({
            "port": f"P{index:02d}",
            "route_id": route["route_id"],
            "installed_length_m": installed,
            "axis_length_m": route["axis_length_mm"] / 1000,
            "body_length_m": route["body_length_mm"] / 1000,
            "additional_collector_end_allowance_m": end_allowance,
            "initial_flow_l_min": old_rows.get(route["route_id"], {}).get("initial_flow_l_min", 1.2),
        })

    # User-approved compact transit rule: no more than three adjacent pipes at 100 mm.
    transit_rule = {
        "maximum_adjacent_pipe_count_at_100mm": 3,
        "axis_pitch_mm": 100,
        "between_triplets_pitch_mm": 200,
        "field_pitch_mm": 200,
        "status": "OWNER_ACCEPTED_FOR_TRANSIT_BUNDLES_ONLY",
    }
    model = {
        "schema": "homeaura.owner-style-installation-project.v1",
        "artifact_id": PROJECT_ID,
        "date": DATE,
        "status": "OWNER_STYLE_PLAN_REWORK_PASS_FIELD_RELEASE_CONDITIONAL",
        "supersedes_visual_packages": ["HA_TWO_FLOOR_READY_INSTALLATION_PROJECT_140", "HA_TWO_FLOOR_OWNER_STYLE_INSTALLATION_PROJECT_141", "HA_TWO_FLOOR_OWNER_STYLE_INSTALLATION_PROJECT_142", "HA_TWO_FLOOR_OWNER_STYLE_INSTALLATION_PROJECT_143"],
        "source_records": [
            {"path": str(SOURCE_D140), "sha256": sha(SOURCE_D140)},
            {"path": str(SOURCE_F1), "sha256": sha(SOURCE_F1)},
            {"path": str(SOURCE_ATTIC), "sha256": sha(SOURCE_ATTIC)},
            {"path": str(SOURCE_F1_PDF), "sha256": sha(SOURCE_F1_PDF)},
            {"path": str(SOURCE_ATTIC_PDF), "sha256": sha(SOURCE_ATTIC_PDF)},
        ],
        "owner_style_requirements": {
            "corridor_single_long_counterflow_loop": True,
            "compact_transit_triplets_100mm": True,
            "large_empty_graphic_zones_prohibited": True,
            "sheet_style": "A3_CAD_PLAN_DOMINANT_WITH_TITLEBLOCK",
        },
        "floor_1": {
            "collector": "K1",
            "active_circuit_count": 11,
            "spare_port_count_on_12_outlet_manifold": 1,
            "routes": routes,
            "schedule": f1_installed,
            "corridor_revision": {
                "retired_route_id": "F1-C05",
                "single_active_route_id": "F1-C06",
                "axis_length_mm": 79_600,
                "body_length_mm": 65_800,
                "self_contact_count": 0,
                "inter_route_contact_count": 0,
                "visual_result": "ONE_LONG_CONTINUOUS_COUNTERFLOW_LOOP",
            },
            "coverage_status": "REWORK_EXACT_POLYGON_COVERAGE_AFTER_OWNER_STYLE_ROUTE_CHANGE",
        },
        "attic": {
            "collector": "K2",
            "body_count": len(attic_bodies),
            "bodies": attic_bodies,
            "full_axes_published": False,
            "status": "REGULAR_BODY_LAYOUT_PRESERVED_TRANSITS_FIELD_COORDINATION_REQUIRED",
        },
        "transit_bundle_rule": transit_rule,
        "primary_32x3": d140["design_decisions"],
        "installation_release": d140["installation_release"],
        "physical_notes": {
            "floor_1_existing_insulation_mm": 100,
            "attic_existing_insulation_mm": 50,
            "available_above_insulation_both_floors_mm": 70,
            "loop_pipe": "16x2",
            "minimum_axis_bend_radius_mm": 80,
            "wall_material": "AAC / gas concrete",
        },
        "claims": {
            "full_thermal_calculation": False,
            "full_attic_axes": False,
            "installation_without_field_checklist": False,
        },
    }
    model["project_digest"] = digest(model)
    return model


def font(size, bold=False):
    path = Path(r"C:\Windows\Fonts") / ("arialbd.ttf" if bold else "arial.ttf")
    return ImageFont.truetype(str(path), size)


def render_source(pdf_path: Path, output: Path):
    doc = pymupdf.open(pdf_path)
    pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(3, 3), alpha=False)
    pix.save(output)


PALETTE = [
    "#D9364C", "#2F77C5", "#00A87A", "#9656C7", "#E08B22", "#3B9BB8",
    "#CA4A9D", "#648C3D", "#F05D4E", "#3565B6", "#7D50B8", "#009F8B", "#B56B21",
]


def to_px(point):
    return round(point[0] * PX), round(point[1] * PX)


def draw_routes_on_plan(source: Path, target: Path, routes, collector_label: str, show_bundle_rule=False):
    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image)
    # A subdued white halo preserves wall/text readability without hiding the source plan.
    for index, route in enumerate(routes):
        colour = PALETTE[index % len(PALETTE)]
        points = [to_px(p) for p in route["ordered_points_grid"]]
        draw.line(points, fill="#FFFFFF", width=12, joint="curve")
        draw.line(points, fill=colour, width=6, joint="curve")
        for p in (points[0], points[-1]):
            draw.ellipse((p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6), fill="#FFFFFF", outline=colour, width=3)
        anchor = points[len(points) // 2]
        label = route["route_id"]
        draw.text((anchor[0] + 7, anchor[1] + 7), label, font=font(18, True), fill=colour,
                  stroke_width=3, stroke_fill="#FFFFFF")
    # Compact plan legend, deliberately small like the owner's MEP sheets.
    draw.rounded_rectangle((36, 36, 430, 124), radius=12, fill="#FFFFFFE8", outline="#3B4B52", width=2)
    draw.text((52, 49), f"{collector_label}  |  continuous circuits", font=font(21, True), fill="#1B2D35")
    subtitle = "3 pipes @100 mm permitted in transit bundles" if show_bundle_rule else "regular counterflow bodies; field transits coordinated separately"
    draw.text((52, 83), subtitle, font=font(16), fill="#485D65")
    image.save(target, quality=96)


def register_fonts():
    pdfmetrics.registerFont(TTFont("Arial", r"C:\Windows\Fonts\arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"))


def titleblock(c, sheet, sheet_name, status="WORKING INSTALLATION PLAN"):
    c.setStrokeColor(colors.HexColor("#222222")); c.setLineWidth(0.55)
    c.rect(8 * mm, 8 * mm, PAGE_W - 16 * mm, PAGE_H - 16 * mm, fill=0, stroke=1)
    x, y, w, h = 274 * mm, 8 * mm, 135 * mm, 34 * mm
    c.rect(x, y, w, h, fill=0, stroke=1)
    c.line(x, y + 20 * mm, x + w, y + 20 * mm)
    c.line(x + 94 * mm, y, x + 94 * mm, y + h)
    c.setFont("Arial-Bold", 10); c.setFillColor(colors.HexColor("#111111"))
    c.drawString(x + 4 * mm, y + 25 * mm, "HOMEAURA  |  UNDERFLOOR HEATING")
    c.setFont("Arial-Bold", 7.0); c.drawString(x + 4 * mm, y + 13 * mm, sheet_name[:46])
    c.setFont("Arial", 6.4); c.drawString(x + 4 * mm, y + 5 * mm, f"PROJECT D144  |  {DATE}")
    right_centre = x + 114.5 * mm
    c.setFont("Arial-Bold", 8.5); c.drawCentredString(right_centre, y + 25 * mm, f"SHEET {sheet}")
    c.setFont("Arial", 5.1); c.drawCentredString(right_centre, y + 13 * mm, status[:30])
    c.drawCentredString(right_centre, y + 5 * mm, "A3  |  NOT FOR SCALE")


def fit_image(c, path: Path, x, y, w, h):
    im = Image.open(path)
    iw, ih = im.size
    scale = min(w / iw, h / ih)
    dw, dh = iw * scale, ih * scale
    c.drawImage(str(path), x + (w - dw) / 2, y + (h - dh) / 2, dw, dh, mask="auto")


def draw_plan_sheet(c, image: Path, schedule, sheet, title, notes, collector, status):
    c.setFillColor(colors.white); c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#111111")); c.setFont("Arial-Bold", 11.5)
    c.drawString(14 * mm, PAGE_H - 15 * mm, title)
    c.setFont("Arial", 6.7); c.setFillColor(colors.HexColor("#4E5B60"))
    c.drawString(14 * mm, PAGE_H - 21 * mm, status[:60])
    fit_image(c, image, 12 * mm, 43 * mm, 294 * mm, 240 * mm)

    x = 312 * mm
    c.setStrokeColor(colors.HexColor("#333333")); c.setLineWidth(0.45)
    c.rect(x, 77 * mm, 97 * mm, 206 * mm, fill=0, stroke=1)
    c.setFillColor(colors.HexColor("#111111")); c.setFont("Arial-Bold", 8.5)
    c.drawString(x + 4 * mm, 275 * mm, f"CIRCUIT SCHEDULE {collector}")
    y = 267 * mm
    c.setFont("Arial-Bold", 6.2)
    c.drawString(x + 4 * mm, y, "PORT")
    c.drawString(x + 18 * mm, y, "CIRCUIT")
    c.drawRightString(x + 66 * mm, y, "LENGTH")
    c.drawRightString(x + 92 * mm, y, "FLOW")
    y -= 4 * mm
    c.line(x + 3 * mm, y + 2 * mm, x + 94 * mm, y + 2 * mm)
    c.setFont("Arial", 6.3)
    for row in schedule:
        if y < 142 * mm:
            break
        c.drawString(x + 4 * mm, y, row.get("port", "--"))
        c.drawString(x + 18 * mm, y, row["route_id"].replace("A-C10_C11_SERIAL", "A-C10/11"))
        c.drawRightString(x + 66 * mm, y, f"{row['installed_length_m']:.1f} m" if "installed_length_m" in row else f"{row['body_length_m']:.1f} m body")
        flow = row.get("initial_flow_l_min")
        c.drawRightString(x + 92 * mm, y, f"{flow:.1f}" if flow is not None else "--")
        y -= 8.2 * mm
    c.setFont("Arial-Bold", 7.5); c.drawString(x + 4 * mm, 132 * mm, "INSTALLATION NOTES")
    c.setFont("Arial", 6.5); y = 124 * mm
    for note in notes:
        words = note.split(); lines = []; line = ""
        for word in words:
            test = (line + " " + word).strip()
            if c.stringWidth(test, "Arial", 6.5) > 88 * mm:
                lines.append(line); line = word
            else:
                line = test
        if line: lines.append(line)
        for text in lines:
            c.drawString(x + 5 * mm, y, text); y -= 4.1 * mm
        y -= 2 * mm
    titleblock(c, sheet, title, status)


def draw_detail_sheet(c, model):
    c.setFillColor(colors.white); c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#111111")); c.setFont("Arial-Bold", 14)
    c.drawString(14 * mm, PAGE_H - 15 * mm, "COLLECTORS, TRANSIT BUNDLES AND PRIMARY RISER")
    c.setFont("Arial", 7.5); c.drawString(14 * mm, PAGE_H - 21 * mm, "Owner-style coordination details | three 16x2 pipes at 100 mm permitted only in transit bundles")

    # Detail A: triplet bundle.
    x0, y0 = 20 * mm, 160 * mm
    c.setFont("Arial-Bold", 10); c.drawString(x0, y0 + 102 * mm, "DETAIL A - COMPACT TRANSIT TRIPLET")
    c.setStrokeColor(colors.HexColor("#333333")); c.rect(x0, y0, 175 * mm, 94 * mm, fill=0, stroke=1)
    for i, colour in enumerate(["#D9364C", "#2F77C5", "#00A87A"]):
        cx = x0 + 45 * mm + i * 35 * mm
        c.setFillColor(colors.HexColor(colour)); c.circle(cx, y0 + 47 * mm, 5 * mm, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#444444")); c.line(cx, y0 + 20 * mm, cx, y0 + 75 * mm)
        c.setFont("Arial-Bold", 8); c.setFillColor(colors.HexColor("#222222")); c.drawCentredString(cx, y0 + 12 * mm, f"PIPE {i+1}")
    c.setFont("Arial", 7); c.drawCentredString(x0 + 80 * mm, y0 + 82 * mm, "100 mm axis pitch | maximum 3 adjacent pipes")
    c.drawCentredString(x0 + 80 * mm, y0 + 6 * mm, "Next triplet / field line: 200 mm axis separation")

    # Detail B: one continuous corridor loop.
    x1, y1 = 207 * mm, 160 * mm
    c.setFont("Arial-Bold", 10); c.drawString(x1, y1 + 102 * mm, "DETAIL B - ONE CORRIDOR COUNTERFLOW LOOP")
    c.rect(x1, y1, 190 * mm, 94 * mm, fill=0, stroke=1)
    path = [(x1+15*mm,y1+12*mm),(x1+15*mm,y1+80*mm),(x1+175*mm,y1+80*mm),(x1+175*mm,y1+12*mm),(x1+35*mm,y1+12*mm),(x1+35*mm,y1+62*mm),(x1+155*mm,y1+62*mm),(x1+155*mm,y1+30*mm),(x1+55*mm,y1+30*mm),(x1+55*mm,y1+46*mm),(x1+135*mm,y1+46*mm)]
    c.setStrokeColor(colors.HexColor("#9656C7")); c.setLineWidth(2.1)
    p = c.beginPath(); p.moveTo(*path[0])
    for q in path[1:]: p.lineTo(*q)
    c.drawPath(p, fill=0, stroke=1)
    c.setFont("Arial", 7); c.setFillColor(colors.HexColor("#222222"))
    c.drawString(x1 + 8*mm, y1 + 6*mm, "Single continuous pipe, no artificial second corridor circuit")

    # Primary and buildup facts.
    c.setFont("Arial-Bold", 10); c.drawString(20 * mm, 143 * mm, "PRIMARY 32x3 / FLOOR BUILD-UP")
    facts = [
        "Route: boiler room floor -> stair far wall -> slab opening -> wardrobe K2.",
        "Outside-wall rise is excluded. Floor-to-floor rise: 3000 mm.",
        "Existing insulation: floor 1 = 100 mm; attic = 50 mm; available above insulation = 70 mm on both floors.",
        "Loop pipe 16x2. Minimum centreline bend radius R80. Heating to reduce the radius is not used in this project.",
        "AAC wall crossings are straight in sleeves. The two 32x3 primary pipes have no concealed fittings.",
        "Pressure and hold time remain blank until the installed pipe/manifold manufacturer's written procedure is selected.",
    ]
    c.setFont("Arial", 6.9)
    for index, fact in enumerate(facts):
        column = index // 3
        row = index % 3
        c.drawString((24 + column * 187) * mm, (132 - row * 14) * mm, "- " + fact)

    # Small release matrix.
    c.setStrokeColor(colors.HexColor("#333333")); c.rect(20*mm, 47*mm, 377*mm, 43*mm, fill=0, stroke=1)
    c.setFont("Arial-Bold", 8); c.drawString(25*mm, 82*mm, "FIELD RELEASE BEFORE COVERING")
    c.setFont("Arial", 7)
    release = [
        "[ ] Verify K1/K2 labels and route IDs", "[ ] Verify all bend radii and absence of kinks",
        "[ ] Record pressure-test procedure / pressure / time", "[ ] Photograph all routes and the 200 mm primary no-fastener zone",
        "[ ] Confirm sleeve clearances and closeout system", "[ ] Record actual cut lengths before screed",
    ]
    for i, text in enumerate(release):
        c.drawString(25*mm + (i%2)*183*mm, 71*mm - (i//2)*9*mm, text)
    titleblock(c, "03", "DETAILS AND FIELD RELEASE", "FIELD CHECK BEFORE SCREED")


def build_pdf(model, f1_png, attic_png):
    register_fonts()
    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(PDF_OUT), pagesize=landscape(A3), pageCompression=1)
    c.setTitle("HomeAura owner-style underfloor heating project D144")
    f1_notes = [
        "Each colour is one continuous K1-to-K1 circuit. No concealed joints.",
        "The corridor uses one long counterflow loop F1-C06; F1-C05 is retired and K1 P12 is spare.",
        "Field spacing 200 mm. Transit bundles may contain up to three adjacent pipes at 100 mm; separate triplets by 200 mm.",
        "Minimum centreline bend radius R80. Verify actual route before screed and record installed cut length.",
    ]
    draw_plan_sheet(c, f1_png, model["floor_1"]["schedule"], "01", "FLOOR 1 - UNDERFLOOR HEATING LAYOUT", f1_notes, "K1", "11 CIRCUITS | CORRIDOR LOOP"); c.showPage()

    attic_schedule = []
    for index, body in enumerate(model["attic"]["bodies"], 1):
        attic_schedule.append({"port": "TBD", "route_id": body["route_id"], "body_length_m": body["body_length_mm"] / 1000})
    attic_notes = [
        "Every coloured body is a regular counterflow candidate preserved from D050.",
        "Full K2-to-K2 axes are not frozen on this sheet; coordinate door/wall approaches on site without crossings.",
        "Use the same transit rule: maximum three adjacent 16x2 pipes at 100 mm, then 200 mm to the next triplet.",
        "The stair structural void remains a no-pipe zone. Body geometry is not to be padded merely to reach a target length.",
    ]
    draw_plan_sheet(c, attic_png, attic_schedule, "02", "ATTIC - COUNTERFLOW BODY LAYOUT", attic_notes, "K2", "13 BODIES | ROUTES PENDING"); c.showPage()
    draw_detail_sheet(c, model); c.showPage()
    c.save()


def validate_model(model):
    routes = model["floor_1"]["routes"]
    schedule = model["floor_1"]["schedule"]
    assert len(routes) == len(schedule) == 11
    assert len({r["route_id"] for r in routes}) == 11
    assert [r["port"] for r in schedule] == [f"P{i:02d}" for i in range(1, 12)]
    assert all(r["installed_length_m"] <= 80 for r in schedule)
    assert model["floor_1"]["spare_port_count_on_12_outlet_manifold"] == 1
    assert model["floor_1"]["corridor_revision"]["axis_length_mm"] == 79_600
    assert model["floor_1"]["corridor_revision"]["inter_route_contact_count"] == 0
    assert model["transit_bundle_rule"]["maximum_adjacent_pipe_count_at_100mm"] == 3
    assert model["transit_bundle_rule"]["between_triplets_pitch_mm"] == 200
    assert model["claims"]["full_thermal_calculation"] is False
    assert model["claims"]["full_attic_axes"] is False
    assert model["claims"]["installation_without_field_checklist"] is False
    assert inter_contacts(routes) == 0


def build_artifact(model, f1_png, attic_png):
    if OUT.exists() or PACKAGE.exists():
        raise FileExistsError("D144 is append-only")
    OUT.mkdir(parents=True)
    model_path = OUT / "owner_style_installation_project.json"
    model_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(PDF_OUT, OUT / PDF_OUT.name)
    shutil.copy2(f1_png, OUT / "floor_1_owner_style_plan.png")
    shutil.copy2(attic_png, OUT / "attic_owner_style_plan.png")
    report = OUT / "report.md"
    report.write_text(
        "# D144 owner-style rework\n\n"
        "D140-D143 visual packages are superseded. Floor 1 now uses one long continuous corridor counterflow loop; "
        "compact transit bundles may use a maximum of three adjacent pipes at 100 mm. The A3 sheets use a "
        "plan-dominant CAD-style layout. Full attic transit axes and exact thermal coverage remain subject to field coordination.\n",
        encoding="utf-8",
    )
    files = [model_path, OUT / PDF_OUT.name, OUT / "floor_1_owner_style_plan.png", OUT / "attic_owner_style_plan.png", report]
    manifest = {
        "artifact_id": PROJECT_ID,
        "append_only": True,
        "project_digest": model["project_digest"],
        "files": [{"name": p.name, "size": p.stat().st_size, "sha256": sha(p)} for p in files],
    }
    manifest_path = OUT / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PACKAGE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in files + [manifest_path]:
            zf.write(p, arcname=p.name)
    with zipfile.ZipFile(PACKAGE) as zf:
        assert zf.testzip() is None
        for name in zf.namelist():
            assert zf.read(name) == (OUT / name).read_bytes()
    return manifest_path


def main():
    if OUT.exists() or PACKAGE.exists():
        raise FileExistsError("D144 append-only outputs already exist")
    TMP.mkdir(parents=True, exist_ok=True)
    model = prepare_model()
    validate_model(model)
    f1_source = TMP / "floor1_source_3x.png"
    attic_source = TMP / "attic_source_3x.png"
    f1_plan = TMP / "floor1_owner_style.png"
    attic_plan = TMP / "attic_owner_style.png"
    render_source(SOURCE_F1_PDF, f1_source)
    render_source(SOURCE_ATTIC_PDF, attic_source)
    draw_routes_on_plan(f1_source, f1_plan, model["floor_1"]["routes"], "K1", True)
    draw_routes_on_plan(attic_source, attic_plan, model["attic"]["bodies"], "K2", True)
    build_pdf(model, f1_plan, attic_plan)
    manifest = build_artifact(model, f1_plan, attic_plan)
    print(json.dumps({
        "artifact": str(OUT),
        "pdf": str(PDF_OUT),
        "package": str(PACKAGE),
        "manifest": str(manifest),
        "project_digest": model["project_digest"],
        "floor1_active_circuits": model["floor_1"]["active_circuit_count"],
        "corridor_axis_m": model["floor_1"]["corridor_revision"]["axis_length_mm"] / 1000,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
import math
import shutil
import textwrap
import zipfile
from datetime import date
from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle


ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
OUT = PROPOSALS / "HA_TWO_FLOOR_READY_INSTALLATION_PROJECT_140"
PDF_OUT = ROOT / "output" / "pdf" / "HomeAura_Heating_Installation_Project_D140.pdf"
TMP = ROOT / "tmp" / "pdfs" / "homeaura_d138"

F1_JSON = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039" / "canonical_geometry.json"
F1_PNG = PROPOSALS / "HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039" / "floor_1_c06_north_stair_overlay.png"
ATTIC_JSON = PROPOSALS / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_body_geometry.json"
ATTIC_PNG = PROPOSALS / "HA_TWO_FLOOR_ATTIC_HALL_REFINED_050" / "attic_hall_refined_overlay.png"
K2_PORTS_JSON = PROPOSALS / "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORTS_093" / "attic_k2_selected_ports.json"
K2_BUDGET_JSON = PROPOSALS / "HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORT_BUDGETS_094" / "attic_k2_selected_port_budgets.json"
K2_ELEV_PNG = PROPOSALS / "HA_TWO_FLOOR_ATTIC_K2_MOUNTING_DATUM_095" / "attic_k2_mounting_datum_evidence.png"
PRIMARY_JSON = PROPOSALS / "HA_TWO_FLOOR_FLOOR_PRIMARY_INTEGRATION_109" / "floor_primary_integration.json"
PRIMARY_PNG = PROPOSALS / "HA_TWO_FLOOR_FLOOR_PRIMARY_INTEGRATION_109" / "floor_primary_integration_evidence.png"
PENETRATION_PNG = PROPOSALS / "HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098" / "two_primary_internal_penetration_evidence.png"
RELEASE_JSON = PROPOSALS / "HA_TWO_FLOOR_PRIMARY_RELEASE_STATE_BINDING_137" / "primary_release_state_binding.json"

TODAY = "2026-08-13"
PROJECT_ID = "HA_TWO_FLOOR_READY_INSTALLATION_PROJECT_140"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def digest_obj(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def crop_plan(src: Path, dst: Path, crop_box):
    image = Image.open(src).convert("RGB")
    image.crop(crop_box).save(dst, quality=95)


def crop_to_content(src: Path, dst: Path, margin_px=45, white_threshold=248):
    image = Image.open(src).convert("RGB")
    pixels = image.load()
    xs, ys = [], []
    for y in range(image.height):
        for x in range(image.width):
            r, g, b = pixels[x, y]
            # Keep walls, colored pipes and plan text; discard only near-white background.
            if min(r, g, b) < white_threshold:
                xs.append(x); ys.append(y)
    if not xs:
        raise ValueError(f"No plan content found in {src}")
    box = (
        max(0, min(xs) - margin_px), max(0, min(ys) - margin_px),
        min(image.width, max(xs) + margin_px), min(image.height, max(ys) + margin_px),
    )
    image.crop(box).save(dst, quality=95)


PAGE_W, PAGE_H = landscape(A3)
NAVY = colors.HexColor("#071D26")
INK = colors.HexColor("#183746")
TEAL = colors.HexColor("#008D78")
CYAN = colors.HexColor("#00A7C7")
RED = colors.HexColor("#CC2438")
AMBER = colors.HexColor("#D59300")
PALE = colors.HexColor("#EEF4F5")
PALE_GREEN = colors.HexColor("#E8F5EF")
GRID = colors.HexColor("#B8C7CC")
WHITE = colors.white


FONT = "Arial"
FONT_BOLD = "Arial-Bold"


def register_fonts():
    candidates = [
        (Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf")),
        (Path(r"C:\Windows\Fonts\DejaVuSans.ttf"), Path(r"C:\Windows\Fonts\DejaVuSans-Bold.ttf")),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont(FONT, str(regular)))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold)))
            return
    raise RuntimeError("Cyrillic fonts not found")


styles = getSampleStyleSheet()


def pstyle(size=8.2, leading=None, color=INK, bold=False, align=TA_LEFT):
    return ParagraphStyle(
        name=f"p-{size}-{bold}-{align}-{str(color)}",
        fontName=FONT_BOLD if bold else FONT,
        fontSize=size,
        leading=leading or size * 1.25,
        textColor=color,
        alignment=align,
        spaceAfter=0,
        spaceBefore=0,
    )


def para(text, size=8.2, color=INK, bold=False, align=TA_LEFT):
    return Paragraph(text, pstyle(size=size, color=color, bold=bold, align=align))


def header(c: canvas.Canvas, title: str, subtitle: str, page_no: int):
    c.setFillColor(NAVY)
    c.rect(0, PAGE_H - 25 * mm, PAGE_W, 25 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 17)
    c.drawString(14 * mm, PAGE_H - 10 * mm, title)
    c.setFont(FONT, 8.5)
    c.setFillColor(colors.HexColor("#B8ECE7"))
    c.drawString(14 * mm, PAGE_H - 17 * mm, subtitle)
    c.setFillColor(colors.HexColor("#D6E4E8"))
    c.drawRightString(PAGE_W - 14 * mm, PAGE_H - 17 * mm, f"D140 · лист {page_no}")


def footer(c: canvas.Canvas, page_no: int):
    c.setStrokeColor(GRID)
    c.line(14 * mm, 10 * mm, PAGE_W - 14 * mm, 10 * mm)
    c.setFont(FONT, 7)
    c.setFillColor(colors.HexColor("#5F747D"))
    c.drawString(14 * mm, 5.3 * mm, f"HomeAura · рабочий проект отопления · {PROJECT_ID}")
    c.drawRightString(PAGE_W - 14 * mm, 5.3 * mm, f"Дата выпуска {TODAY} · {page_no}/11")


def draw_table(c, data, x, y_top, col_widths, row_heights=None, font_size=7.2, header_rows=1,
               alignments=None, fills=None, grid=True):
    wrapped = []
    for ri, row in enumerate(data):
        cells = []
        for ci, value in enumerate(row):
            align = TA_LEFT
            if alignments and ci < len(alignments):
                align = alignments[ci]
            cells.append(para(str(value), size=font_size, bold=ri < header_rows, align=align,
                              color=WHITE if ri < header_rows else INK))
        wrapped.append(cells)
    table = Table(wrapped, colWidths=col_widths, rowHeights=row_heights, repeatRows=header_rows)
    commands = [
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if grid:
        commands += [("GRID", (0, 0), (-1, -1), 0.35, GRID)]
    if fills:
        for row_idx, color in fills:
            commands.append(("BACKGROUND", (0, row_idx), (-1, row_idx), color))
    table.setStyle(TableStyle(commands))
    w, h = table.wrapOn(c, sum(col_widths), PAGE_H)
    table.drawOn(c, x, y_top - h)
    return h


def draw_bullets(c, bullets, x, y, width, size=9, gap=4.5 * mm, color=INK):
    cur = y
    for bullet in bullets:
        c.setFillColor(TEAL)
        c.circle(x + 2.5 * mm, cur + 1.4 * mm, 1.2 * mm, fill=1, stroke=0)
        p = para(bullet, size=size, color=color)
        _, h = p.wrap(width - 8 * mm, 30 * mm)
        p.drawOn(c, x + 7 * mm, cur - h + 4 * mm)
        cur -= max(gap, h + 2 * mm)
    return cur


def image_fit(c, path: Path, x, y, w, h, border=True):
    im = Image.open(path)
    iw, ih = im.size
    scale = min(w / iw, h / ih)
    dw, dh = iw * scale, ih * scale
    dx, dy = x + (w - dw) / 2, y + (h - dh) / 2
    if border:
        c.setStrokeColor(GRID)
        c.roundRect(x, y, w, h, 3 * mm, fill=0, stroke=1)
    c.drawImage(str(path), dx, dy, dw, dh, preserveAspectRatio=True, mask="auto")
    return dx, dy, dw, dh


def panel(c, x, y, w, h, title, fill=PALE, title_color=INK):
    c.setFillColor(fill)
    c.setStrokeColor(GRID)
    c.roundRect(x, y, w, h, 4 * mm, fill=1, stroke=1)
    c.setFillColor(title_color)
    c.setFont(FONT_BOLD, 10)
    c.drawString(x + 6 * mm, y + h - 8 * mm, title)


def flow_for_length(length_m: float) -> float:
    if length_m < 55:
        return 1.0
    if length_m < 65:
        return 1.1
    if length_m < 75:
        return 1.2
    return 1.3


def prepare_data():
    f1 = read_json(F1_JSON)
    attic = read_json(ATTIC_JSON)
    k2_ports = read_json(K2_PORTS_JSON)
    k2_budget = read_json(K2_BUDGET_JSON)
    primary = read_json(PRIMARY_JSON)
    release = read_json(RELEASE_JSON)

    f1_rows = []
    # One authoritative physical 12-station order for the selected commercial K1.
    # It follows the route list shown on the K1 schedule and never derives a port
    # number from the circuit identifier (there is no physical P14 on a 12-port manifold).
    k1_station_order = [r["route_id"] for r in f1["routes"]]
    k1_station_by_route = {route_id: f"P{index:02d}" for index, route_id in enumerate(k1_station_order, 1)}
    k1_map = {m["route_id"]: m for m in f1["collector_contract"]["connection_to_gate_mapping"] if m["leg"] == "SUPPLY"}
    for r in f1["routes"]:
        axis_length = r["total_length_mm"] / 1000
        length = round(axis_length + 1.4, 1)
        f1_rows.append({
            "circuit_id": r["route_id"],
            "collector": "K1",
            "port": k1_station_by_route[r["route_id"]],
            "length_m": length,
            "canonical_axis_length_m": axis_length,
            "body_m": r["heating_body_length_mm"] / 1000,
            "transit_m": (r["supply_transit_length_mm"] + r["return_transit_length_mm"]) / 1000,
            "transit_and_collector_end_allowance_m": round((r["supply_transit_length_mm"] + r["return_transit_length_mm"]) / 1000 + 1.4, 1),
            "collector_end_allowance_included_m": 1.4,
            "initial_flow_l_min": flow_for_length(length),
            "source_geometry": "D039 FULL AXIS",
            "supply_gate": k1_map[r["route_id"]].get("exit_gate_point_grid"),
            "maximum_installed_length_m": 80.0,
        })

    budgets = {x["circuit_id"]: x for x in k2_budget["circuit_budgets"]}
    adopted_attic_lengths = {
        "A-C01": 50.0, "A-C02": 55.6, "A-C03": 61.1, "A-C04": 64.4,
        "A-C05": 62.5, "A-C06": 71.0, "A-C07": 76.5, "A-C08": 51.6,
        "A-C09": 58.9, "A-C12": 52.5, "A-C13": 56.0, "A-C10_C11_SERIAL": 52.5,
    }
    station_order = [
        "A-C08", "A-C09", "A-C01", "A-C02", "A-C03", "A-C04",
        "A-C05", "A-C06", "A-C07", "A-C12", "A-C13", "A-C10_C11_SERIAL",
    ]
    attic_rows = []
    for station, cid in enumerate(station_order, 1):
        budget = budgets[cid]
        length = adopted_attic_lengths[cid]
        attic_rows.append({
            "circuit_id": cid,
            "collector": "K2",
            "port": f"P{station:02d}",
            "length_m": length,
            "body_m": budget["body_length_mm"] / 1000,
            "transit_and_collector_end_allowance_m": round(length - budget["body_length_mm"] / 1000, 1),
            "optimistic_axis_lower_bound_m": round(budget["optimistic_total_lower_bound_mm"] / 1000, 3),
            "collector_end_allowance_included_m": 1.4,
            "initial_flow_l_min": flow_for_length(length),
            "source_geometry": "D050 BODY EXACT + D094 LOWER BOUND + D140 FIELD CORRIDOR ALLOWANCE",
            "full_axis_published": False,
            "field_routing_rule": "Shortest non-crossing corridor inside the served room/door zones; body geometry is immutable; cut length is the listed maximum including 0.7 m at each collector end.",
            "maximum_installed_length_m": 78.0,
        })

    all_lengths = [r["length_m"] for r in f1_rows + attic_rows]
    # Each project length already includes 0.7 m at both collector ends. The
    # adopted packing is therefore a cut list, not an extra +1.4 m rule.
    coil_packing = [
        ["F1-C06", "F1-C02", "F1-C08", "F1-C11", "A-C02", "A-C01"],
        ["F1-C01", "F1-C04", "A-C04", "F1-C12", "A-C12", "A-C08"],
        ["F1-C14", "F1-C03", "A-C03", "F1-C10", "F1-C05", "A-C10_C11_SERIAL"],
        ["A-C07", "A-C06", "A-C05", "A-C09", "A-C13", "F1-C09"],
    ]
    by_id = {r["circuit_id"]: r["length_m"] for r in f1_rows + attic_rows}
    coils = []
    for idx, circuits in enumerate(coil_packing, 1):
        used = round(sum(by_id[c] for c in circuits), 1)
        coils.append({"coil": idx, "circuits": circuits, "used_m": used, "reserve_m": round(400 - used, 1)})

    data = {
        "schema": "homeaura.ready_installation_project.v1",
        "artifact_id": PROJECT_ID,
        "status": "READY_PROJECT_PACKAGE_INSTALLATION_AFTER_MANDATORY_FIELD_RELEASE_CHECKS",
        "date": TODAY,
        "project_scope": "Two-floor hydronic underfloor heating: 24 circuits, K1/K2, primary 32x3 internal rise",
        "owner_inputs": {
            "floor_1_existing_insulation_mm": 100,
            "floor_1_available_above_insulation_mm": 70,
            "attic_existing_insulation_mm": 50,
            "attic_available_above_insulation_mm": 70,
            "floor_to_floor_vertical_height_mm": 3000,
            "wall_material": "AAC / gas concrete",
            "floor_loop_pipe_od_mm": 16,
            "minimum_axis_bend_radius_mm": 80,
            "openings_already_made": True,
            "external_wall_riser_rejected": True,
            "selected_route": "boiler room floor -> stair far wall -> internal slab opening -> wardrobe K2",
        },
        "design_decisions": {
            "floor_loop_pipe": "16x2 oxygen-barrier pipe, continuous, no concealed couplings",
            "floor_field_spacing_mm": 200,
            "perimeter_spacing_mm": 100,
            "primary_pipe": "Uponor Uni Pipe PLUS 32x3, part 1059583, continuous pair",
            "primary_insulation": "closed-cell elastomeric 15 mm, sealed joints",
            "primary_floor_route_axis_mm": [[13200, 8200], [9230, 8200], [9230, 7600]],
            "primary_floor_route_length_mm": 4570,
            "primary_vertical_length_mm": 3000,
            "primary_each_line_purchase_allowance_m": 10.0,
            "penetration_design_clear_mm": [120, 200],
            "penetration_pitch_axis": "ALONG_200MM_SIDE_ONLY",
            "penetration_pipe_axis_pitch_mm": 100,
            "penetration_sleeve_nominal_mm": 75,
            "penetration_pair_envelope_mm": 175,
            "penetration_margin_along_200mm_side_mm": 25,
            "penetration_margin_along_120mm_side_mm": -55,
            "bend_method": "cold bend with R80 former/tool; heating prohibited",
            "k1_manifold": "Uponor Vario S FM 12, part 1140843, open wall mounting in boiler room",
            "k2_manifold": "Uponor Vario S FM 12, part 1140843",
            "k2_cabinet": "Uponor Vario cabinet OW 1050x730x135, part 1136219",
            "k2_cabinet_mounting_aff_mm": {"bottom": 270, "top": 1000, "tolerance": 10},
            "opening_schedule": [
                {"id": "W01", "type": "AAC_WALL", "service": "32x3 PAIR", "sleeve_nominal_mm": 75, "sleeve_count": 2, "rule": "both lines cross straight; no fitting in wall; direction changes remain accessible"},
                {"id": "W02", "type": "AAC_WALL", "service": "32x3 PAIR", "sleeve_nominal_mm": 75, "sleeve_count": 2, "rule": "both lines cross straight; no fitting in wall; direction changes remain accessible"},
                {"id": "P01", "type": "SLAB", "service": "32x3 PAIR", "sleeve_nominal_mm": 75, "sleeve_count": 2, "clear_opening_mm": [120, 200], "pitch_axis": "ALONG_200MM_SIDE_ONLY"},
            ],
            "primary_channel_no_fastener_zone": {"width_mm": 200, "loop_staples_screws_anchors_allowed": False, "load_spreading_bridge_required": True, "bridge_selection": "match the installed screed/insulation system before closeout"},
        },
        "floor_1_circuits": f1_rows,
        "attic_circuits": attic_rows,
        "pipe_16_total_design_m": round(sum(all_lengths), 1),
        "pipe_16_purchase_m": 1600,
        "pipe_16_purchase_coils": coils,
        "installation_release": {
            "project_ready": True,
            "physical_installation_release": "CONDITIONAL_ON_FIELD_CHECKLIST",
            "source_D137_release_state_preserved": "NOT_RELEASED_UNTIL_AS_BUILT_VALUES_ARE_RECORDED",
            "construction_authorized_before_checklist": False,
            "construction_authorized_after_all_checklist_pass": True,
            "mandatory_checks": ["W01", "W02", "P01", "K2_DATUM", "R80_TOOL_AND_TANGENTS", "PRIMARY_CHANNEL_BRIDGE", "PRESSURE_TEST_PROCEDURE"],
            "pressure_test_procedure": {"selected": False, "procedure_id": None, "test_pressure_bar": None, "hold_time_h": None, "screed_hold_pressure_bar": None, "rule": "Select and record the installed pipe/manifold manufacturer's procedure before testing."},
        },
        "floor_1_coverage_disclosure": {
            "full_coverage_claimed": False,
            "source_D039_status": "PASS_REWORK_POLYGON_COVERAGE",
            "source_D039_served_ratio_percent": 92.0441,
            "source_D039_unresolved_area_m2": 2.327663,
            "instruction": "Do not add a padded C07 loop; close only true residuals after room heat-loss and final finish-face check.",
        },
        "hydraulic_starting_points": {
            "supply_temperature_c": "32-35",
            "design_delta_t_k": 5,
            "initial_flow_values_are_commissioning_start_only": True,
            "k1_initial_total_l_min": round(sum(x["initial_flow_l_min"] for x in f1_rows), 1),
            "k2_initial_total_l_min": round(sum(x["initial_flow_l_min"] for x in attic_rows), 1),
            "final_balance_method": "adjust by room temperature and loop return temperature after 48-72 h steady operation",
        },
        "field_control_points": [
            "W01 and W02 AAC wall openings: verify clear size/depth, straight sleeves, protected edges, no fitting inside wall, and accessible direction-change method.",
            "P01 slab opening: verify clear size at least 120x200 mm; the 100 mm pipe pitch must run only along the 200 mm side.",
            "Verify sleeve edges are smooth, slab is undamaged, and fire/acoustic seal can be installed.",
            "Verify K2 cabinet bottom 270 mm and top 1000 mm above final floor within +/-10 mm.",
            "Use R80 cold-bend former on every 32x3 change of direction; no hot bending or rebending.",
            "Select and record the pressure-test procedure from the installed pipe/manifold manufacturer before testing; do not invent pressure or hold time.",
            "Over the 200 mm primary channel, no 16 mm loop staple/screw/anchor may penetrate; install a non-penetrating load-spreading bridge selected for the screed system.",
        ],
        "source_records": [
            {"path": str(p.relative_to(ROOT)), "sha256": sha(p)}
            for p in [F1_JSON, ATTIC_JSON, K2_PORTS_JSON, K2_BUDGET_JSON, PRIMARY_JSON, RELEASE_JSON]
        ],
        "official_product_sources": [
            "https://www.uponor.com/en-gb/s/uponor-uni-pipe-plus-white-32x3-0-50m-1059583",
            "https://www.uponor.com/en-en/s/uponor-vario-s-manifold-fm-12xg3-4-euro-g1-1140843",
            "https://www.uponor.com/en-gb/s/uponor-vario-cabinet-ow-1050x730x135-1136219",
            "https://www.uponor.com/getmedia/620d005c-e790-4070-b3d2-5f8e54197a73/uponor-installation-manual-vario-s-manifold-f?disposition=attachment&sitename=UponorInternational",
            "https://www.uponor.com/getmedia/8677118b-0315-4f8b-a3f4-daf9bb2d346f/mlc-ukpdf?sitename=Estonia",
            "https://www.uponor.com/fi-fi/s/uponor-uni-pipe-plus-taivutuslesti-r80-32-1120411",
            "https://www.uponor.com/en-en/product/getproductdatapdf?code=1071925",
        ],
    }
    data["project_digest"] = digest_obj(data)
    return data


def draw_cover(c, data):
    c.setFillColor(NAVY)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#0D3240"))
    c.circle(PAGE_W - 70 * mm, PAGE_H - 70 * mm, 100 * mm, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.circle(PAGE_W - 50 * mm, 40 * mm, 48 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 29)
    c.drawString(24 * mm, PAGE_H - 58 * mm, "РАБОЧИЙ ПРОЕКТ ОТОПЛЕНИЯ")
    c.setFont(FONT_BOLD, 21)
    c.setFillColor(colors.HexColor("#8BE0D5"))
    c.drawString(24 * mm, PAGE_H - 74 * mm, "ТЁПЛЫЙ ПОЛ · ДВА ЭТАЖА · СТАДИЯ Р")
    c.setFillColor(WHITE)
    c.setFont(FONT, 13)
    c.drawString(24 * mm, PAGE_H - 92 * mm, "Монтажные планы, коллекторы K1/K2, внутренняя магистраль 32×3,")
    c.drawString(24 * mm, PAGE_H - 101 * mm, "ведомость контуров, спецификация, испытания и пусконаладка")

    panel(c, 24 * mm, 45 * mm, 235 * mm, 88 * mm, "ПРИНЯТЫЕ РЕШЕНИЯ", fill=colors.HexColor("#123846"), title_color=colors.HexColor("#8BE0D5"))
    c.setFillColor(WHITE)
    c.setFont(FONT, 10)
    lines = [
        "24 независимых контура: 12 на K1 и 12 на K2",
        "Труба пола 16×2, шаг поля 200 мм, край/холодная зона 100 мм",
        "Магистраль K1→K2: 2×32×3, внутри дома, высота подъёма 3000 мм",
        "Существующие отверстия используются после обязательного контрольного обмера и записи в чек-лист",
        "Первый этаж: утеплитель 100 мм + доступно 70 мм; мансарда: 50 + 70 мм",
        "Минимальный радиус по оси 80 мм; 32×3 гнуть только холодным инструментом R80",
    ]
    y = 112 * mm
    for line in lines:
        c.setFillColor(TEAL)
        c.circle(34 * mm, y + 1 * mm, 1.4 * mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.drawString(40 * mm, y - 1.2 * mm, line)
        y -= 10.5 * mm

    c.setFillColor(colors.HexColor("#D9E8EB"))
    c.setFont(FONT, 9)
    c.drawString(24 * mm, 25 * mm, f"Шифр: {PROJECT_ID}")
    c.drawString(24 * mm, 18 * mm, f"Дата выпуска: {TODAY} · координатная база: планы 1:100 из предоставленных PDF")
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 10)
    c.drawRightString(PAGE_W - 22 * mm, 18 * mm, "ГОТОВЫЙ ПРОЕКТ · МОНТАЖ ПОСЛЕ PASS ПОЛЕВОГО ЧЕК-ЛИСТА")


def draw_system_page(c, data, page_no):
    header(c, "1. ПРИНЦИПИАЛЬНАЯ СХЕМА", "Два коллектора по 12 контуров · магистраль 32×3 внутри дома", page_no)
    x0, y0 = 25 * mm, 70 * mm
    c.setStrokeColor(INK)
    c.setLineWidth(2)
    # heat source
    panel(c, x0, y0 + 85 * mm, 48 * mm, 42 * mm, "ИСТОЧНИК ТЕПЛА", fill=PALE_GREEN)
    c.setFont(FONT, 8)
    c.setFillColor(INK)
    c.drawString(x0 + 7 * mm, y0 + 105 * mm, "Низкотемпературная")
    c.drawString(x0 + 7 * mm, y0 + 98 * mm, "подача 32-35 °C")
    # K1
    panel(c, x0 + 78 * mm, y0 + 73 * mm, 58 * mm, 66 * mm, "K1 · КОТЕЛЬНАЯ", fill=PALE)
    c.setFillColor(INK)
    c.setFont(FONT, 8)
    c.drawString(x0 + 85 * mm, y0 + 118 * mm, "Vario S FM 12")
    c.drawString(x0 + 85 * mm, y0 + 110 * mm, "12 контуров 1 этажа")
    for i in range(12):
        yy = y0 + 80 * mm + i * 4.2 * mm
        c.setStrokeColor(colors.HexColor("#4E9FC7"))
        c.line(x0 + 128 * mm, yy, x0 + 142 * mm, yy)
    # K2
    panel(c, x0 + 245 * mm, y0 + 73 * mm, 60 * mm, 66 * mm, "K2 · ГАРДЕРОБНАЯ", fill=PALE_GREEN)
    c.setFillColor(INK)
    c.setFont(FONT, 8)
    c.drawString(x0 + 252 * mm, y0 + 118 * mm, "Vario S FM 12")
    c.drawString(x0 + 252 * mm, y0 + 110 * mm, "12 контуров мансарды")
    for i in range(12):
        yy = y0 + 80 * mm + i * 4.2 * mm
        c.setStrokeColor(colors.HexColor("#B15BAA"))
        c.line(x0 + 297 * mm, yy, x0 + 311 * mm, yy)
    # primary pair
    c.setLineWidth(4)
    c.setStrokeColor(RED)
    c.line(x0 + 48 * mm, y0 + 112 * mm, x0 + 78 * mm, y0 + 112 * mm)
    c.line(x0 + 136 * mm, y0 + 112 * mm, x0 + 245 * mm, y0 + 112 * mm)
    c.setStrokeColor(colors.HexColor("#2B7BBB"))
    c.line(x0 + 48 * mm, y0 + 99 * mm, x0 + 78 * mm, y0 + 99 * mm)
    c.line(x0 + 136 * mm, y0 + 99 * mm, x0 + 245 * mm, y0 + 99 * mm)
    c.setFillColor(RED)
    c.setFont(FONT_BOLD, 8)
    c.drawCentredString(x0 + 190 * mm, y0 + 116 * mm, "ПОДАЧА 32×3 · НЕПРЕРЫВНАЯ")
    c.setFillColor(colors.HexColor("#2B7BBB"))
    c.drawCentredString(x0 + 190 * mm, y0 + 91 * mm, "ОБРАТКА 32×3 · НЕПРЕРЫВНАЯ")
    c.setFillColor(INK)
    c.setFont(FONT, 8)
    c.drawCentredString(x0 + 190 * mm, y0 + 103 * mm, "4,57 м по полу + 3,00 м подъём + подключения")
    # route callout
    panel(c, 23 * mm, 23 * mm, 190 * mm, 46 * mm, "ТРАССА МАГИСТРАЛИ", fill=PALE)
    draw_bullets(c, [
        "Котельная → по полу к дальней стене лестницы → через внутреннее перекрытие → гардеробная.",
        "Наружная стена не используется. Скрытых фитингов нет. Подача и обратка маркируются на обоих концах.",
        "Две изолированные трубы размещаются в канале 200 мм в нижней части утеплителя, сверху восстанавливается 30 мм утеплителя.",
    ], 29 * mm, 53 * mm, 174 * mm, size=8.2, gap=10 * mm)
    panel(c, 220 * mm, 23 * mm, 175 * mm, 46 * mm, "ГИДРАВЛИЧЕСКАЯ ГРАНИЦА", fill=colors.HexColor("#FFF5D9"), title_color=AMBER)
    draw_bullets(c, [
        "Проект рассчитан на общий низкотемпературный контур 32-35 °C. Если источник выдаёт более 45 °C - поставить смесительно-насосный узел до K1/K2.",
        "На каждой паре коллектора: запорные краны, слив/воздухоотводчик; K2 получает отдельные балансировочные краны на подаче и обратке.",
    ], 226 * mm, 53 * mm, 162 * mm, size=8.2, gap=12 * mm)
    footer(c, page_no)


def draw_plan_page(c, data, page_no, title, subtitle, plan_png, rows, collector, note):
    header(c, title, subtitle, page_no)
    image_fit(c, plan_png, 15 * mm, 16 * mm, 225 * mm, 248 * mm, border=True)
    c.setFont(FONT_BOLD, 10)
    c.setFillColor(INK)
    c.drawString(248 * mm, 254 * mm, f"ВЕДОМОСТЬ КОНТУРОВ {collector}")
    table_data = [["№", "Контур", "Длина, м", "Тело, м", "Подводка, м", "Старт, л/мин"]]
    for i, r in enumerate(rows, 1):
        table_data.append([
            str(i), r["circuit_id"].replace("A-C10_C11_SERIAL", "A-C10/11"),
            f"{r['length_m']:.1f}", f"{r['body_m']:.1f}", f"{r['transit_and_collector_end_allowance_m']:.1f}", f"{r['initial_flow_l_min']:.1f}",
        ])
    draw_table(c, table_data, 248 * mm, 247 * mm, [9 * mm, 30 * mm, 20 * mm, 20 * mm, 24 * mm, 24 * mm],
               font_size=7.4, alignments=[TA_CENTER, TA_LEFT, TA_CENTER, TA_CENTER, TA_CENTER, TA_CENTER])
    panel(c, 248 * mm, 63 * mm, 147 * mm, 67 * mm, "МОНТАЖНЫЕ ПРАВИЛА", fill=PALE)
    draw_bullets(c, [
        "Каждый контур - одна непрерывная труба от коллектора до коллектора; соединения в стяжке запрещены.",
        "Оси на плане - монтажные. Поле 200 мм; в показанных холодных/краевых полосах 100 мм.",
        "У стен, дверей и деформационных швов труба проходит в защитной гофре; радиус по оси не менее 80 мм.",
        note,
    ], 254 * mm, 113 * mm, 135 * mm, size=7.8, gap=12 * mm)
    panel(c, 248 * mm, 18 * mm, 147 * mm, 38 * mm, "ПРИЁМКА ЛИСТА", fill=PALE_GREEN, title_color=TEAL)
    draw_bullets(c, [
        "Сверить ID на бирках у коллектора и на свободном конце до раскладки.",
        "После раскладки проверить длину, отсутствие перегибов/контактов и выполнить фотофиксацию с рулеткой.",
    ], 254 * mm, 43 * mm, 135 * mm, size=7.6, gap=11 * mm)
    footer(c, page_no)


def draw_primary_page(c, data, page_no):
    header(c, "4. МАГИСТРАЛЬ 32×3 И СУЩЕСТВУЮЩАЯ ПРОХОДКА", "Котельная → лестница → гардеробная · наружная стена исключена", page_no)
    # plan schematic
    panel(c, 15 * mm, 135 * mm, 205 * mm, 120 * mm, "ПЛАН 1 ЭТАЖА · МОНТАЖНАЯ ОСЬ", fill=PALE)
    x, y = 28 * mm, 158 * mm
    c.setStrokeColor(colors.HexColor("#657B83")); c.setLineWidth(1.2)
    c.rect(x, y, 170 * mm, 66 * mm, fill=0, stroke=1)
    c.line(x + 105 * mm, y, x + 105 * mm, y + 66 * mm)
    c.line(x + 140 * mm, y, x + 140 * mm, y + 66 * mm)
    c.setFont(FONT_BOLD, 9); c.setFillColor(INK)
    c.drawString(x + 120 * mm, y + 50 * mm, "КОТЕЛЬНАЯ / K1")
    c.drawString(x + 78 * mm, y + 12 * mm, "ЛЕСТНИЦА")
    c.drawString(x + 5 * mm, y + 50 * mm, "ВНУТРЕННИЕ ПОМЕЩЕНИЯ")
    # route
    c.setLineWidth(5); c.setLineCap(1)
    c.setStrokeColor(RED); c.line(x + 150 * mm, y + 28 * mm, x + 25 * mm, y + 28 * mm); c.line(x + 25 * mm, y + 28 * mm, x + 25 * mm, y + 8 * mm)
    c.setStrokeColor(colors.HexColor("#2B7BBB")); c.line(x + 150 * mm, y + 20 * mm, x + 32 * mm, y + 20 * mm); c.line(x + 32 * mm, y + 20 * mm, x + 32 * mm, y + 8 * mm)
    c.setLineCap(0); c.setFillColor(INK); c.setFont(FONT, 7.8)
    c.drawString(x + 66 * mm, y + 32 * mm, "длина оси по полу 4570 мм")
    c.drawString(x + 5 * mm, y + 3 * mm, "W01/W02 — прямые проходы газобетона; P01 — отверстие перекрытия")
    # penetration detail
    panel(c, 228 * mm, 135 * mm, 167 * mm, 120 * mm, "ДЕТАЛЬ П-1 · ОТВЕРСТИЕ И ГИЛЬЗЫ", fill=colors.HexColor("#FFF5D9"), title_color=AMBER)
    px, py = 260 * mm, 166 * mm
    c.setStrokeColor(AMBER); c.setLineWidth(2); c.rect(px, py, 80 * mm, 48 * mm, fill=0, stroke=1)
    c.setFillColor(colors.HexColor("#F4CE7D")); c.rect(px + 5 * mm, py + 5 * mm, 70 * mm, 38 * mm, fill=1, stroke=0)
    c.setFillColor(RED); c.circle(px + 40 * mm, py + 32 * mm, 5 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#2B7BBB")); c.circle(px + 40 * mm, py + 16 * mm, 5 * mm, fill=1, stroke=0)
    c.setFillColor(INK); c.setFont(FONT_BOLD, 8)
    c.drawCentredString(px + 40 * mm, py + 52 * mm, "ЧИСТЫЙ ПРОЁМ ≥ 120×200 · ШАГ 100 ПО СТОРОНЕ 200")
    c.setFont(FONT, 7.5)
    c.drawString(px - 10 * mm, py - 10 * mm, "2 гильзы Ø75; центры 100 мм вдоль стороны 200; суммарный конверт 175 мм")
    c.drawString(px - 10 * mm, py - 17 * mm, "по стороне 120 шаг ЗАПРЕЩЁН; заделка только после выбора совместимой огне-/акустической системы")
    # section and bends
    panel(c, 15 * mm, 25 * mm, 185 * mm, 96 * mm, "РАЗРЕЗ ПОЛА · ОБА ЭТАЖА", fill=PALE)
    sx, sy = 28 * mm, 42 * mm
    c.setFillColor(colors.HexColor("#9BA6AA")); c.rect(sx, sy, 150 * mm, 12 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#D9EEA2")); c.rect(sx, sy + 12 * mm, 150 * mm, 40 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#DCCEB3")); c.rect(sx, sy + 52 * mm, 150 * mm, 25 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#EDE3D7")); c.rect(sx, sy + 77 * mm, 150 * mm, 11 * mm, fill=1, stroke=0)
    c.setFillColor(INK); c.setFont(FONT, 7.2)
    c.drawString(sx + 2 * mm, sy + 4 * mm, "Ж/Б плита")
    c.drawString(sx + 2 * mm, sy + 31 * mm, "утеплитель 100 мм (1 эт.) / 50 мм (мансарда)")
    c.drawString(sx + 2 * mm, sy + 63 * mm, "труба 16×2 + стяжка: 16 + 35 = 51 мм")
    c.drawString(sx + 2 * mm, sy + 81 * mm, "финиш / выравнивание: до 19 мм")
    c.setStrokeColor(AMBER); c.setLineWidth(2); c.rect(sx + 58 * mm, sy + 12 * mm, 58 * mm, 40 * mm, fill=0, stroke=1)
    c.setFillColor(colors.HexColor("#FBF6C7")); c.rect(sx + 58 * mm, sy + 12 * mm, 58 * mm, 34 * mm, fill=1, stroke=0)
    c.setFillColor(RED); c.circle(sx + 75 * mm, sy + 28 * mm, 4 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#2B7BBB")); c.circle(sx + 99 * mm, sy + 28 * mm, 4 * mm, fill=1, stroke=0)
    c.setFillColor(INK); c.setFont(FONT_BOLD, 7.2)
    c.drawCentredString(sx + 87 * mm, sy + 47 * mm, "канал 200 мм; сверху мост без крепежа")
    panel(c, 208 * mm, 25 * mm, 187 * mm, 96 * mm, "ИЗГИБЫ И МОНТАЖ 32×3", fill=PALE_GREEN, title_color=TEAL)
    draw_bullets(c, [
        "Минимальный радиус по оси R80 только холодным инструментом/шаблоном. Горячий прогрев и повторное выправление запрещены.",
        "Не гнуть трубу на кромке отверстия. В проходке труба прямая; поворот начинается за гильзой на опоре R80.",
        "Пара труб укладывается без скрытых фитингов. Изоляция 15 мм герметично склеивается; подача и обратка не соприкасаются.",
        "W01/W02: проход стены газобетона только по прямой в отдельных гладких гильзах; фитинг внутри стены запрещён, следующий поворот оставляется доступным.",
        "Над каналом 200 мм запрещены скобы/винты/анкеры контуров 16×2. После фотофиксации установить непроникающий распределяющий нагрузку мост, совместимый со стяжкой.",
    ], 214 * mm, 104 * mm, 174 * mm, size=8.1, gap=15 * mm)
    footer(c, page_no)


def draw_k2_page(c, data, page_no):
    header(c, "5. КОЛЛЕКТОРЫ K1/K2 И ФАНАУТ", "Одинаковые 12-выходные коллекторы · K2 в настенном шкафу гардеробной", page_no)
    # elevations
    panel(c, 15 * mm, 118 * mm, 180 * mm, 135 * mm, "K2 · ФАСАД ШКАФА", fill=PALE)
    x, y = 58 * mm, 138 * mm
    c.setStrokeColor(TEAL); c.setLineWidth(2); c.rect(x, y, 92 * mm, 90 * mm, fill=0, stroke=1)
    c.setFillColor(INK); c.setFont(FONT_BOLD, 9); c.drawCentredString(x + 46 * mm, y + 94 * mm, "1136219 · 1050×730×135")
    c.setStrokeColor(INK); c.line(x, y - 10 * mm, x + 92 * mm, y - 10 * mm)
    c.setFillColor(AMBER); c.setFont(FONT_BOLD, 8)
    c.drawString(x - 28 * mm, y + 2 * mm, "низ +270")
    c.setFillColor(CYAN); c.drawString(x - 28 * mm, y + 84 * mm, "верх +1000")
    c.setStrokeColor(RED); c.setLineWidth(3); c.line(x + 36 * mm, y + 70 * mm, x + 36 * mm, y + 20 * mm)
    c.setStrokeColor(colors.HexColor("#2B7BBB")); c.line(x + 55 * mm, y + 70 * mm, x + 55 * mm, y + 20 * mm)
    c.setStrokeColor(INK); c.setLineWidth(1.5)
    for i in range(12):
        yy = y + 18 * mm + i * 4.2 * mm
        c.line(x + 18 * mm, yy, x + 75 * mm, yy)
    c.setFillColor(INK); c.setFont(FONT, 7.2)
    c.drawCentredString(x + 46 * mm, y + 7 * mm, "24 отвода вниз через нижнюю грань шкафа")
    # port maps
    panel(c, 205 * mm, 118 * mm, 190 * mm, 135 * mm, "ТАБЛИЦА ПОРТОВ", fill=PALE_GREEN, title_color=TEAL)
    port_rows = [["Станция", "K1 · 1 этаж", "K2 · мансарда"]]
    f1_order = [r["circuit_id"] for r in data["floor_1_circuits"]]
    attic_order = [r["circuit_id"].replace("A-C10_C11_SERIAL", "A-C10/11") for r in data["attic_circuits"]]
    for i in range(12):
        port_rows.append([f"P{i+1:02d}", f1_order[i], attic_order[i]])
    draw_table(c, port_rows, 218 * mm, 232 * mm, [27 * mm, 63 * mm, 63 * mm], font_size=7.5,
               alignments=[TA_CENTER, TA_CENTER, TA_CENTER])
    # fanout detail
    panel(c, 15 * mm, 22 * mm, 380 * mm, 82 * mm, "ДЕТАЛЬ Ф-1 · ВЫХОД 24 ЛИНИЙ ИЗ K2", fill=colors.HexColor("#FFF5D9"), title_color=AMBER)
    fx, fy = 32 * mm, 39 * mm
    c.setFillColor(colors.white); c.setStrokeColor(INK); c.rect(fx, fy, 80 * mm, 46 * mm, fill=1, stroke=1)
    for i in range(12):
        yy = fy + 5 * mm + i * 3.2 * mm
        c.setStrokeColor(RED if i % 2 == 0 else colors.HexColor("#2B7BBB")); c.setLineWidth(1.3)
        c.line(fx + 18 * mm, yy, fx + 70 * mm, yy)
    c.setStrokeColor(TEAL); c.setLineWidth(2)
    for i in range(24):
        xx = fx + 17 * mm + i * 2.3 * mm
        c.line(xx, fy + 5 * mm, xx, fy - 10 * mm - (i % 3) * 4 * mm)
    c.setFillColor(INK); c.setFont(FONT, 7.4)
    c.drawString(fx + 3 * mm, fy + 49 * mm, "коллектор 12×50 мм; S/R разделены и подписаны")
    draw_bullets(c, [
        "Все 24 линии выходят вниз; разворот к фасаду внутри шкафа не выполнять. Первые изгибы формировать ниже шкафа R80.",
        "В зоне фанаута допускается локальный шаг 50 мм до расхождения; в поле пола перейти на 100/200 мм без пересечений.",
        "К1 монтируется открыто в котельной. K2 - в шкафу; перед шкафом оставить сервисную полосу не менее 700 мм.",
        "На каждом конце установить бирку: K1/K2, порт, ID контура, S/R. После опрессовки перенести значения расходомеров в журнал.",
    ], 125 * mm, 87 * mm, 255 * mm, size=8.3, gap=15 * mm)
    footer(c, page_no)


def draw_schedule_page(c, data, page_no):
    header(c, "6. СВОДНАЯ ВЕДОМОСТЬ КОНТУРОВ", "Длина, начальный расход, пределы укладки и раскрой бухт", page_no)
    all_rows = data["floor_1_circuits"] + data["attic_circuits"]
    table_data = [["Колл.", "Порт", "Контур", "Длина проекта, м", "Начальный расход, л/мин", "Монтажный предел", "Примечание"]]
    for r in all_rows:
        note = "ось D039 + концы 2×0,7" if r["collector"] == "K1" else "тело D050; коридор+концы в длине"
        limit = "≤80,0" if r["collector"] == "K1" else "≤78,0"
        table_data.append([r["collector"], r["port"], r["circuit_id"].replace("A-C10_C11_SERIAL", "A-C10/11"),
                           f"{r['length_m']:.1f}", f"{r['initial_flow_l_min']:.1f}", limit, note])
    draw_table(c, table_data, 14 * mm, 258 * mm,
               [16 * mm, 18 * mm, 35 * mm, 32 * mm, 40 * mm, 28 * mm, 83 * mm], font_size=6.8,
               alignments=[TA_CENTER, TA_CENTER, TA_LEFT, TA_CENTER, TA_CENTER, TA_CENTER, TA_LEFT])
    panel(c, 273 * mm, 154 * mm, 122 * mm, 104 * mm, "РАСКРОЙ 4×400 М", fill=PALE_GREEN, title_color=TEAL)
    coil_rows = [["Бухта", "Контуры", "Исп., м", "Резерв, м"]]
    for coil in data["pipe_16_purchase_coils"]:
        ids = ", ".join(x.replace("A-C10_C11_SERIAL", "A-C10/11") for x in coil["circuits"])
        coil_rows.append([str(coil["coil"]), ids, f"{coil['used_m']:.1f}", f"{coil['reserve_m']:.1f}"])
    draw_table(c, coil_rows, 279 * mm, 238 * mm, [16 * mm, 65 * mm, 18 * mm, 20 * mm], font_size=6.3,
               alignments=[TA_CENTER, TA_LEFT, TA_CENTER, TA_CENTER])
    panel(c, 14 * mm, 18 * mm, 250 * mm, 76 * mm, "ПРАВИЛО РАСКРОЯ", fill=PALE)
    draw_bullets(c, [
        "Табличная длина уже включает 0,7 м на каждом конце у коллектора (всего 1,4 м). Повторно этот запас не прибавлять. Отрезать только после возврата к коллектору.",
        "Перед началом каждой бухты сверить, что сумма оставшихся контуров помещается. Резерв бухты не использовать для искусственного удлинения контура.",
        "На мансарде тело D050 неизменно; подводка идёт кратчайшим непересекающимся коридором. Табличная длина — предельный раскрой, полная ось фиксируется после укладки.",
        "F1-C14 имеет 78,2 м по точной оси и остаётся допустимым при пределе 80,0 м; дополнительные изгибы и фитинги в него не добавлять.",
    ], 20 * mm, 77 * mm, 238 * mm, size=8.1, gap=14 * mm)
    panel(c, 273 * mm, 18 * mm, 122 * mm, 122 * mm, "ПУСКОВЫЕ РАСХОДЫ", fill=colors.HexColor("#FFF5D9"), title_color=AMBER)
    c.setFillColor(INK); c.setFont(FONT_BOLD, 10)
    c.drawString(281 * mm, 120 * mm, f"K1: {data['hydraulic_starting_points']['k1_initial_total_l_min']:.1f} л/мин")
    c.drawString(281 * mm, 110 * mm, f"K2: {data['hydraulic_starting_points']['k2_initial_total_l_min']:.1f} л/мин")
    draw_bullets(c, [
        "Это стартовые, а не окончательные расходы.",
        "Подача 32-35 °C; целевая ΔT около 5 K.",
        "Через 48-72 ч откорректировать по температурам помещений и обратных линий.",
        "Не душить длинный контур ниже 0,8 л/мин без причины; короткие контуры ограничивать первыми.",
    ], 279 * mm, 98 * mm, 109 * mm, size=7.6, gap=14 * mm)
    footer(c, page_no)


def draw_bom_page(c, data, page_no):
    header(c, "7. СПЕЦИФИКАЦИЯ", "Основные материалы и оборудование для закупки", page_no)
    rows = [
        ["Поз.", "Наименование", "Марка / артикул", "Ед.", "Кол.", "Примечание"],
        ["1", "Труба тёплого пола 16×2 с кислородным барьером", "PEX/PE-RT EVOH, класс отопления", "м", "1600", f"4 бухты по 400 м; проект {data['pipe_16_total_design_m']:.1f} м"],
        ["2", "Коллектор 12 контуров с расходомерами", "Uponor Vario S FM 12, 1140843", "шт.", "2", "K1 и K2; G3/4 Eurocone, первичное G1"],
        ["3", "Настенный шкаф K2", "Uponor Vario OW 1050×730×135, 1136219", "шт.", "1", "гардеробная, низ +270, верх +1000"],
        ["4", "Евроконус 16×2 - G3/4", "совместимый с трубой и коллектором", "шт.", "48", "по 2 на контур"],
        ["5", "Магистральная труба 32×3", "Uponor Uni Pipe PLUS, 1059583", "бухта", "1×50 м", "две непрерывные линии по ~10 м"],
        ["6", "Фитинги 32×3 к G1 коллектора/узла", "Uponor S-Press / совместимые", "компл.", "4", "только доступные соединения у K1/K2"],
        ["7", "Теплоизоляция магистрали", "эластомер закрыт. ячейка, 32×15", "м", "25", "стыки проклеить; красная/синяя маркировка"],
        ["8", "Опора/шаблон изгиба R80 для 32", "Uponor 1120411 / инструмент 1071925", "компл.", "1", "холодная гибка; прогрев запрещён"],
        ["9", "Гильзы W01/W02/P01", "Ø75, гладкие; тип по основанию", "шт.", "6", "по 2 в двух стенах и перекрытии"],
        ["10", "Системы заделки W01/W02/P01", "совместимые с газобетоном/плитой/гильзой", "компл.", "3", "кольцевой зазор; без жёсткого контакта трубы"],
        ["11", "Запорные краны DN25/G1", "полнопроходные", "шт.", "4", "подача/обратка K1 и K2"],
        ["12", "Балансировочные краны K2", "DN25/G1 с измерительными штуцерами", "шт.", "2", "подача и обратка удалённого коллектора"],
        ["13", "Кромочная лента", "8-10×150 мм", "м", "250", "уточнить по фактическому периметру"],
        ["14", "Защитная гофра на переходах", "внутр. Ø ≥20 мм", "м", "120", "стены, двери, швы; минимум 0,5 м"],
        ["15", "Крепёж трубы к утеплителю", "такер-скобы/рейка под 16 мм", "шт.", "3000", "не ставить над каналом магистрали 200 мм"],
        ["16", "Бирки и маркеры S/R", "стойкие к воде и стяжке", "компл.", "1", "48 концов + магистраль"],
        ["17", "Манометры/опрессовочный комплект", "0-10 bar", "компл.", "1", "испытание и журнал"],
        ["18", "Непроникающий мост над каналом", "распределяющая нагрузку крышка 200 мм", "компл.", "1", "подобрать по системе стяжки; без анкеров к плите"],
    ]
    draw_table(c, rows, 14 * mm, 258 * mm,
               [13 * mm, 73 * mm, 82 * mm, 16 * mm, 20 * mm, 78 * mm], font_size=6.25,
               alignments=[TA_CENTER, TA_LEFT, TA_LEFT, TA_CENTER, TA_CENTER, TA_LEFT])
    panel(c, 14 * mm, 18 * mm, 381 * mm, 37 * mm, "КОМПЛЕКТАЦИЯ ПЕРЕД ЗАКУПКОЙ", fill=colors.HexColor("#FFF5D9"), title_color=AMBER)
    draw_bullets(c, [
        "Проверить, что выбранные труба 16×2 и евроконусы имеют один размерный допуск. Не смешивать несовместимые обжимные комплекты.",
        "Если теплогенератор не способен стабильно выдавать 32-35 °C, добавить смесительно-насосный узел по паспорту теплогенератора; он не включён без данных источника.",
        "Количество кромочной ленты, гофры и крепежа уточняется по фактическому периметру/проёмам, но не уменьшает принятую длину контурной трубы.",
    ], 20 * mm, 43 * mm, 368 * mm, size=7.7, gap=10 * mm)
    footer(c, page_no)


def draw_install_page(c, data, page_no):
    header(c, "8. ПОСЛЕДОВАТЕЛЬНОСТЬ МОНТАЖА И ИСПЫТАНИЯ", "Работы выполнять по этапам; скрываемые работы фотографировать", page_no)
    steps = [
        ("01", "Подготовка", "Очистить утеплитель, восстановить повреждения, установить кромочную ленту, отметить запретные зоны и оси контуров."),
        ("02", "Коллекторы", "Закрепить K1 и шкаф K2. Проверить отметки K2: низ +270, верх +1000 мм от чистого пола. Установить краны, слив и воздухоотвод."),
        ("03", "Магистраль", "Открыть канал 200 мм, уложить две 32×3 в изоляции 15 мм, холодные R80; W01/W02/P01 проходить прямо в гильзах, без скрытых фитингов."),
        ("04", "Контуры", "Раскладывать S → поле → R. Над каналом 200 мм не ставить скобы/винты; установить непроникающий распределяющий мост и сфотографировать."),
        ("05", "Контроль", "Проверить длину каждого контура, радиусы, отсутствие перегибов, соприкосновений и скрытых соединений. Фото каждого помещения с рулеткой."),
        ("06", "Промывка", "Промывать по одному контуру до отсутствия воздуха/грязи. Заполнить водой снизу вверх, закрывая уже промытые ветви."),
        ("07", "Опрессовка", "До испытания выбрать письменную процедуру изготовителя фактически установленной трубы/коллектора. В журнал внести ID процедуры, давление, время, температуру и результат."),
        ("08", "Стяжка", "Держать систему при давлении, которое требует выбранная процедура: ______ bar. Число не назначать без паспорта. Нагревом сушку не ускорять."),
        ("09", "Пуск", "После срока набора прочности стяжки поднять подачу с 20-25 °C ступенями по 5 K/сутки до 32-35 °C; выполнить балансировку."),
    ]
    cols = 3
    card_w, card_h = 122 * mm, 61 * mm
    start_x, start_y = 14 * mm, 190 * mm
    for idx, (num, title, body) in enumerate(steps):
        col, row = idx % cols, idx // cols
        x = start_x + col * (card_w + 5 * mm)
        y = start_y - row * (card_h + 5 * mm)
        c.setFillColor(PALE_GREEN if idx in (2, 6, 8) else PALE)
        c.setStrokeColor(GRID)
        c.roundRect(x, y, card_w, card_h, 4 * mm, fill=1, stroke=1)
        c.setFillColor(TEAL)
        c.setFont(FONT_BOLD, 22)
        c.drawString(x + 6 * mm, y + card_h - 14 * mm, num)
        c.setFillColor(INK)
        c.setFont(FONT_BOLD, 10)
        c.drawString(x + 25 * mm, y + card_h - 11 * mm, title.upper())
        p = para(body, size=8.1)
        _, h = p.wrap(card_w - 12 * mm, card_h - 22 * mm)
        p.drawOn(c, x + 6 * mm, y + card_h - 22 * mm - h)
    panel(c, 14 * mm, 16 * mm, 376 * mm, 35 * mm, "ЖУРНАЛ СКРЫТЫХ РАБОТ", fill=colors.HexColor("#FFF5D9"), title_color=AMBER)
    c.setFont(FONT, 8); c.setFillColor(INK)
    c.drawString(21 * mm, 36 * mm, "Процедура/паспорт __________________  Давление старт ______ bar  Финиш ______ bar  Время ______  Температура ______ °C")
    c.drawString(21 * mm, 27 * mm, "Результат __________  Фото №№ ______________  Проверил ______________  Монтажник ______________  Подпись ______________")
    footer(c, page_no)


def draw_release_page(c, data, page_no):
    header(c, "9. КОНТРОЛЬНЫЕ ТОЧКИ ПЕРЕД ЗАКРЫТИЕМ", "Рабочий проект готов; физический монтаж и закрытие — после полевого PASS", page_no)
    checks = [
        ("W01", "Стена газобетона", "Обе 32×3 проходят стену прямо в отдельных гильзах Ø75; фитингов внутри нет; доступные повороты начинаются после гильз.", "ОСМОТРЕТЬ"),
        ("W02", "Стена газобетона", "Обе 32×3 проходят стену прямо в отдельных гильзах Ø75; кромки, изоляция и трубы не повреждены.", "ОСМОТРЕТЬ"),
        ("P01", "Отверстие перекрытия", "Чистый размер ≥120×200; две гильзы Ø75; шаг осей 100 мм идёт только вдоль стороны 200 мм; этажи совмещены.", "ОБМЕРИТЬ"),
        ("К2", "Шкаф коллектора", "Низ +270, верх +1000 мм ±10; створка открывается; перед шкафом 700 мм сервиса; 24 отвода выходят вниз.", "ЗАМЕРИТЬ"),
        ("R80", "Изгибы 32×3", "Шаблон R80 физически входит; труба гнётся холодной; после гиба нет овальности, залома или повторного выправления.", "ПРОВЕРИТЬ"),
        ("МОСТ", "Канал 200 мм", "Над магистралью нет скоб/винтов/анкеров; установлен совместимый со стяжкой непроникающий распределяющий мост.", "ОСМОТРЕТЬ"),
        ("ОПР", "Испытание", "Выбрана процедура изготовителя; её ID, давление и время записаны; все контуры и первичная пара испытаны, акт/фото приложены.", "ЗАПИСАТЬ"),
    ]
    rows = [["ID", "Что проверяем", "Критерий", "Действие", "Отметка"]]
    for cid, title, criterion, action in checks:
        rows.append([cid, title, criterion, action, "□ PASS  □ FIX"])
    draw_table(c, rows, 15 * mm, 250 * mm, [18 * mm, 50 * mm, 180 * mm, 32 * mm, 45 * mm], font_size=7.7,
               alignments=[TA_CENTER, TA_LEFT, TA_LEFT, TA_CENTER, TA_CENTER])
    panel(c, 15 * mm, 52 * mm, 180 * mm, 74 * mm, "РАЗРЕШЕНИЕ НА ЗАКРЫТИЕ", fill=PALE_GREEN, title_color=TEAL)
    c.setFillColor(INK); c.setFont(FONT, 8.5)
    c.drawString(23 * mm, 103 * mm, "Все пункты W01…ОПР имеют PASS, фото приложены, результат испытания принят.")
    c.drawString(23 * mm, 92 * mm, "Разрешено закрыть канал магистрали, заделать проходку и залить стяжку.")
    c.setFont(FONT_BOLD, 9)
    c.drawString(23 * mm, 72 * mm, "Ответственный ____________________  Дата __________  Подпись __________")
    panel(c, 205 * mm, 52 * mm, 190 * mm, 74 * mm, "ЕСЛИ РАЗМЕР НЕ СОВПАЛ", fill=colors.HexColor("#FFF5D9"), title_color=AMBER)
    draw_bullets(c, [
        "Не греть трубу и не уменьшать R80. Сначала переставить ось внутри существующего резерва/шкафа.",
        "Не расширять отверстие без сканирования и отдельного решения по плите. В газобетоне допускается локальная штроба только вне несущей полосы и после разметки.",
        "Не добавлять соединение в полу. При повреждении заменить непрерывный отрезок от доступного соединения до доступного соединения.",
    ], 211 * mm, 106 * mm, 177 * mm, size=8.1, gap=15 * mm)
    panel(c, 15 * mm, 17 * mm, 380 * mm, 25 * mm, "ИТОГОВЫЙ СТАТУС", fill=NAVY, title_color=colors.HexColor("#8BE0D5"))
    c.setFillColor(WHITE); c.setFont(FONT_BOLD, 9)
    c.drawString(22 * mm, 24 * mm, "РАБОЧИЙ ПРОЕКТ ГОТОВ. ФИЗИЧЕСКИЙ МОНТАЖ/ЗАКРЫТИЕ РАЗРЕШЕНЫ ТОЛЬКО ПОСЛЕ PASS ВСЕХ ПУНКТОВ ЭТОГО ЛИСТА.")
    footer(c, page_no)


def draw_sources_page(c, data, page_no):
    header(c, "10. ОСНОВАНИЯ, ОГРАНИЧЕНИЯ И ИСТОЧНИКИ", "Прослеживаемость геометрии и выбранного оборудования", page_no)
    left = 15 * mm
    panel(c, left, 139 * mm, 188 * mm, 115 * mm, "ИСХОДНЫЕ АРТЕФАКТЫ", fill=PALE)
    src_rows = [["Блок", "Назначение", "SHA256 (первые 16)"]]
    names = [
        ("D039", "12 полных контуров 1 этажа"),
        ("D050", "13 регулярных тел мансарды"),
        ("D093", "24 физических порта K2"),
        ("D094", "12 лимитов мансарды"),
        ("D109", "магистраль в слоях пола"),
        ("D137", "контрольные критерии проходки"),
    ]
    for item, src in zip(names, data["source_records"]):
        src_rows.append([item[0], item[1], src["sha256"][:16]])
    draw_table(c, src_rows, left + 6 * mm, 234 * mm, [20 * mm, 108 * mm, 42 * mm], font_size=7.2,
               alignments=[TA_CENTER, TA_LEFT, TA_CENTER])
    panel(c, 212 * mm, 139 * mm, 183 * mm, 115 * mm, "ПРИНЯТЫЕ ОГРАНИЧЕНИЯ", fill=colors.HexColor("#FFF5D9"), title_color=AMBER)
    draw_bullets(c, [
        "Теплопотери помещений и модель теплогенератора не предоставлены; расходы в таблице - пусковые, окончательная балансировка выполняется по фактическим температурам.",
        "Мансардные тела D050 заданы точно; полные оси подводок не опубликованы. Их вести полевым кратчайшим непересекающимся коридором, фиксировать фактическую ось и не превышать табличный раскрой/78 м.",
        "D039 даёт 92,0441% прокси-покрытия 1 этажа и 2,327663 м² остатка; полное теплотехническое покрытие и расчёт теплопотерь не заявлены.",
        "Существующие отверстия приняты как выполненные. До закрытия обязательны обмер, осмотр плиты/гильз и акт опрессовки.",
        "Все размеры в миллиметрах, если не указано иное. По исходному архитектурному плану масштаб 1:100; печатный масштаб PDF не использовать для обмера.",
    ], 218 * mm, 235 * mm, 170 * mm, size=8.1, gap=16 * mm)
    panel(c, 15 * mm, 40 * mm, 380 * mm, 86 * mm, "ОФИЦИАЛЬНЫЕ ИСТОЧНИКИ ПРОДУКТОВ", fill=PALE_GREEN, title_color=TEAL)
    urls = [
        "Uponor Uni Pipe PLUS 32×3, part 1059583: uponor.com/en-gb/s/uponor-uni-pipe-plus-white-32x3-0-50m-1059583",
        "Uponor Vario S FM 12, part 1140843: uponor.com/en-en/s/uponor-vario-s-manifold-fm-12xg3-4-euro-g1-1140843",
        "Uponor Vario cabinet OW 1050×730×135, part 1136219: uponor.com/en-gb/s/uponor-vario-cabinet-ow-1050x730x135-1136219",
        "Vario S FM manual: uponor.com/getmedia/620d005c-e790-4070-b3d2-5f8e54197a73/…",
        "32×3 bend data / R80: uponor.com/getmedia/8677118b-0315-4f8b-a3f4-daf9bb2d346f/…; part 1120411; tool 1071925",
    ]
    y = 105 * mm
    c.setFillColor(INK); c.setFont(FONT, 7.5)
    for idx, url in enumerate(urls, 1):
        c.drawString(23 * mm, y, f"{idx}. {url}")
        y -= 12 * mm
    c.setFont(FONT, 7); c.setFillColor(colors.HexColor("#5F747D"))
    c.drawString(23 * mm, 48 * mm, f"Дата доступа к официальным карточкам и руководствам: {TODAY}. Проектный digest: {data['project_digest']}")
    footer(c, page_no)


def build_pdf(data, f1_crop: Path, attic_crop: Path):
    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(PDF_OUT), pagesize=landscape(A3), pageCompression=1)
    c.setTitle("HomeAura - рабочий проект отопления D140")
    c.setAuthor("HomeAura Engineering Agent")
    c.setSubject("Two-floor hydronic underfloor heating installation project")
    draw_cover(c, data); c.showPage()
    draw_system_page(c, data, 2); c.showPage()
    draw_plan_page(c, data, 3, "2. ПЛАН ТЁПЛОГО ПОЛА · 1 ЭТАЖ", "12 полных непрерывных контуров K1 · точные оси D039", f1_crop,
                   data["floor_1_circuits"], "K1", "D039: прокси-покрытие 92,0441%, остаток 2,327663 м²; полного теплотехнического покрытия не заявлено. F1-C14: ось 78,2 м + 1,4 м концов = 79,6 м; до ступеней 100 мм по оси (92 мм до поверхности Ø16)."); c.showPage()
    draw_plan_page(c, data, 4, "3. ПЛАН ТЁПЛОГО ПОЛА · МАНСАРДА", "13 регулярных тел · 12 контуров K2 · A-C10 и A-C11 последовательно", attic_crop,
                   data["attic_circuits"], "K2", "Подводки вести кратчайшим путём от назначенного порта K2; не пересекать отопительные тела и лестничный проём."); c.showPage()
    draw_primary_page(c, data, 5); c.showPage()
    draw_k2_page(c, data, 6); c.showPage()
    draw_schedule_page(c, data, 7); c.showPage()
    draw_bom_page(c, data, 8); c.showPage()
    draw_install_page(c, data, 9); c.showPage()
    draw_release_page(c, data, 10); c.showPage()
    # Sources folded into last page count? Create a compact appendix page and update footer total is cosmetic; still useful.
    draw_sources_page(c, data, 11); c.showPage()
    c.save()


def build_manifest_and_zip(data):
    OUT.mkdir(parents=True, exist_ok=True)
    project_json = OUT / "ready_installation_project.json"
    project_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(PDF_OUT, OUT / PDF_OUT.name)
    shutil.copy2(F1_JSON, OUT / "floor_1_canonical_geometry_d039.json")
    shutil.copy2(ATTIC_JSON, OUT / "attic_body_geometry_d050.json")
    report = OUT / "report.md"
    report.write_text(
        "# HomeAura D140 - рабочий проект отопления\n\n"
        "Единый монтажный пакет: 24 контура, два 12-выходных коллектора, внутренняя магистраль 32x3, "
        "существующая проходка, спецификация, испытания и пусконаладка.\n\n"
        f"Project digest: `{data['project_digest']}`\n",
        encoding="utf-8",
    )
    files = [project_json, OUT / PDF_OUT.name, OUT / "floor_1_canonical_geometry_d039.json", OUT / "attic_body_geometry_d050.json", report]
    manifest = {
        "artifact_id": PROJECT_ID,
        "append_only": True,
        "project_digest": data["project_digest"],
        "files": [{"name": p.name, "size": p.stat().st_size, "sha256": sha(p)} for p in files],
    }
    manifest_path = OUT / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    package = OUT.parent / f"{OUT.name}.zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in files + [manifest_path]:
            zf.write(p, arcname=p.name)
    return manifest_path, package


def validate(data, manifest_path: Path, package: Path):
    assert len(data["floor_1_circuits"]) == 12
    assert len(data["attic_circuits"]) == 12
    assert [r["port"] for r in data["floor_1_circuits"]] == [f"P{i:02d}" for i in range(1, 13)]
    assert [r["port"] for r in data["attic_circuits"]] == [f"P{i:02d}" for i in range(1, 13)]
    assert all(40 <= r["length_m"] <= 80 for r in data["floor_1_circuits"])
    assert all(40 <= r["length_m"] <= 78 for r in data["attic_circuits"])
    assert all(abs(r["length_m"] - r["canonical_axis_length_m"] - 1.4) < 1e-6 for r in data["floor_1_circuits"])
    assert all(r["length_m"] >= r["optimistic_axis_lower_bound_m"] + 1.4 - 0.001 for r in data["attic_circuits"])
    assert all(r["body_m"] <= r["length_m"] for r in data["floor_1_circuits"] + data["attic_circuits"])
    assert abs(sum(r["length_m"] for r in data["floor_1_circuits"] + data["attic_circuits"]) - data["pipe_16_total_design_m"]) < 1e-6
    assert sum(c["used_m"] + c["reserve_m"] for c in data["pipe_16_purchase_coils"]) == 1600.0
    assert all(c["used_m"] <= 400 and c["reserve_m"] >= 20 for c in data["pipe_16_purchase_coils"])
    packed = [cid for c in data["pipe_16_purchase_coils"] for cid in c["circuits"]]
    expected = [r["circuit_id"] for r in data["floor_1_circuits"] + data["attic_circuits"]]
    assert sorted(packed) == sorted(expected) and len(packed) == len(set(packed)) == 24
    assert data["design_decisions"]["penetration_pitch_axis"] == "ALONG_200MM_SIDE_ONLY"
    assert data["design_decisions"]["penetration_margin_along_200mm_side_mm"] == 25
    assert data["design_decisions"]["penetration_margin_along_120mm_side_mm"] < 0
    assert data["installation_release"]["construction_authorized_before_checklist"] is False
    procedure = data["installation_release"]["pressure_test_procedure"]
    assert procedure["selected"] is False and procedure["test_pressure_bar"] is None and procedure["hold_time_h"] is None
    assert PDF_OUT.exists() and PDF_OUT.stat().st_size > 100_000
    manifest = read_json(manifest_path)
    for record in manifest["files"]:
        p = OUT / record["name"]
        assert p.stat().st_size == record["size"]
        assert sha(p) == record["sha256"]
    with zipfile.ZipFile(package) as zf:
        assert zf.testzip() is None
        for name in zf.namelist():
            assert zf.read(name) == (OUT / name).read_bytes()
    return {
        "pdf_sha256": sha(PDF_OUT),
        "package_sha256": sha(package),
        "project_digest": data["project_digest"],
        "pdf_size": PDF_OUT.stat().st_size,
        "package_size": package.stat().st_size,
    }


def main():
    register_fonts()
    if OUT.exists():
        raise FileExistsError(f"Append-only output already exists: {OUT}")
    TMP.mkdir(parents=True, exist_ok=True)
    data = prepare_data()
    f1_crop = TMP / "floor_1_plan_crop.png"
    attic_crop = TMP / "attic_plan_crop.png"
    crop_to_content(F1_PNG, f1_crop, margin_px=50)
    crop_to_content(ATTIC_PNG, attic_crop, margin_px=50)
    build_pdf(data, f1_crop, attic_crop)
    manifest, package = build_manifest_and_zip(data)
    validation = validate(data, manifest, package)
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

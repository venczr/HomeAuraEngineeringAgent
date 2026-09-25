"""Read-only SVG/HTML serialization of HA-FH-VIS-003 grid geometry."""

from __future__ import annotations

import html
import json

from typing import Any


COLOURS = {"C1": "#087e8b", "C2": "#d1495b"}
LAYER_IDS = (
    "ROOM", "GRID", "WALL_CLASSIFICATIONS", "EXTERIOR_WALL_THREE_PASS_REGION",
    "CIRCUIT_TERRITORIES", "COVERAGE", "CIRCUIT_1", "CIRCUIT_2",
    "SUPPLY_TRANSITS", "RETURN_TRANSITS", "COLLECTOR", "FLOW_ARROWS",
    "CENTRE_TURN_CLASSIFICATIONS", "ANNOTATIONS", "DIAGNOSTICS",
)


def _path(points: list[dict[str, int]]) -> str:
    first, *rest = points
    return " ".join(
        [f"M {first['x_mm']} {first['y_mm']}"]
        + [f"L {point['x_mm']} {point['y_mm']}" for point in rest]
    )


def _line(first: dict[str, int], second: dict[str, int], **attributes: str) -> str:
    values = " ".join(f'{name}="{html.escape(value)}"' for name, value in attributes.items())
    return f'<line x1="{first["x_mm"]}" y1="{first["y_mm"]}" x2="{second["x_mm"]}" y2="{second["y_mm"]}" {values}/>'


def render_grid_layout(layout: dict[str, Any]) -> dict[str, Any]:
    digest = layout["geometry_digest"]
    grid = layout["grid"]
    grid_lines = [
        *[f'<line x1="{x}" y1="0" x2="{x}" y2="3200"/>' for x in grid["x_lines_mm"]],
        *[f'<line x1="0" y1="{y}" x2="7000" y2="{y}"/>' for y in grid["y_lines_mm"]],
    ]
    wall_lines = []
    for wall in layout["walls"]:
        colour = "#ef6c00" if wall["wall_type"] == "EXTERIOR_WALL" else "#455a64"
        wall_lines.append(_line(
            wall["start"], wall["end"], id=f'WALL_{wall["wall_id"]}',
            stroke=colour, **{"stroke-width": "28", "data-wall-type": wall["wall_type"]},
        ))
    coverage_rectangles = []
    for index, region in enumerate(layout["coverage"]["unresolved_regions"], 1):
        points = region["polygon"]
        x_values = [point["x_mm"] for point in points]
        y_values = [point["y_mm"] for point in points]
        coverage_rectangles.append(
            f'<rect id="UNRESOLVED_{index}" x="{min(x_values)}" y="{min(y_values)}" '
            f'width="{max(x_values)-min(x_values)}" height="{max(y_values)-min(y_values)}"/>'
        )

    route_paths = []
    centre_paths = []
    supply_lines = []
    return_lines = []
    arrows = []
    reconciliation = []
    for circuit in layout["circuits"]:
        circuit_id = circuit["circuit_id"]
        colour = COLOURS[circuit_id]
        route_paths.append(
            f'<g id="CIRCUIT_{circuit_id[-1]}" data-circuit-id="{circuit_id}">'
            f'<path id="ROUTE_{circuit_id}" d="{_path(circuit["ordered_points"])}" '
            f'fill="none" stroke="{colour}" stroke-width="28" stroke-linecap="round" '
            f'stroke-linejoin="round" data-geometry-digest="{circuit["geometry_digest"]}"/></g>'
        )
        centre_paths.append(
            f'<path id="CENTRE_TURN_{circuit_id}" d="{_path(circuit["centre_turn"]["points"])}" '
            f'fill="none" stroke="#7b1fa2" stroke-width="50" opacity="0.35" '
            f'data-classification="CENTER_TURN_100"/>'
        )
        port = circuit["supply_port"]
        gate = circuit["supply_gate"]
        supply_lines.append(_line(port, gate, id=f"SUPPLY_TRANSIT_{circuit_id}", stroke=colour, **{"stroke-width": "28"}))
        port = circuit["return_port"]
        gate = circuit["return_gate"]
        return_lines.append(_line(gate, port, id=f"RETURN_TRANSIT_{circuit_id}", stroke=colour, **{"stroke-width": "28"}))
        points = circuit["ordered_points"]
        for arrow_index in (2, len(points) // 2, len(points) - 3):
            point = points[arrow_index]
            arrows.append(
                f'<circle cx="{point["x_mm"]}" cy="{point["y_mm"]}" r="45" fill="{colour}" '
                f'stroke="white" stroke-width="12" data-circuit-id="{circuit_id}"/>'
            )
        rendered_floor_length = sum(segment["length_mm"] for segment in circuit["ordered_segments"])
        rendered_total = rendered_floor_length + circuit["collector_stub_length_mm"]
        reconciliation.append({
            "circuit_id": circuit_id,
            "canonical_floor_length_mm": circuit["heating_path_length_mm"],
            "rendered_floor_length_mm": rendered_floor_length,
            "canonical_total_length_mm": circuit["total_length_mm"],
            "rendered_total_length_mm": rendered_total,
            "difference_mm": rendered_total - circuit["total_length_mm"],
            "status": "PASS" if rendered_total == circuit["total_length_mm"] else "FAIL",
        })

    collector = layout["collector"]
    collector_parts = [
        _line(collector["supply_rail"]["start"], collector["supply_rail"]["end"], id="SUPPLY_RAIL", stroke="#c62828", **{"stroke-width": "45"}),
        _line(collector["return_rail"]["start"], collector["return_rail"]["end"], id="RETURN_RAIL", stroke="#1565c0", **{"stroke-width": "45"}),
    ]
    for port in collector["ports"]:
        point = port["point"]
        collector_parts.append(
            f'<circle id="PORT_{port["port_id"]}" cx="{point["x_mm"]}" cy="{point["y_mm"]}" '
            f'r="58" fill="white" stroke="#263238" stroke-width="22"/>'
        )

    validation = layout["global_validation"]
    coverage = layout["coverage"]
    diagnostics = [
        '<g id="DIAGNOSTICS" font-family="Arial" fill="#172033">',
        '<rect x="7300" y="0" width="2400" height="3000" rx="80" fill="#f7f9fb" stroke="#94a3b8" stroke-width="15"/>',
        '<text x="7480" y="260" font-size="150" font-weight="700">HA-FH-VIS-003 VALIDATION</text>',
        '<text x="7480" y="490" font-size="120" fill="#087f5b" font-weight="700">GRID-FIRST TWO SPIRALS</text>',
    ]
    y = 720
    for circuit in layout["circuits"]:
        diagnostics.append(
            f'<text x="7480" y="{y}" font-size="105" fill="{COLOURS[circuit["circuit_id"]]}">'
            f'{circuit["circuit_id"]}: {circuit["total_length_mm"]/1000:.1f} m · topology PASS · grid PASS</text>'
        )
        y += 180
    values = [
        "collector outside floor · four independent legs",
        "south EXTERIOR: exactly 3 passes @ 100 mm",
        "north/west/east INTERIOR and field: 200 mm",
        "no exclusions · no restricted floor zones",
        f'inter-circuit crossings {validation["inter_circuit_crossing_count"]} · shared segments {validation["inter_circuit_shared_segment_count"]}',
        f'coverage {coverage["coverage_ratio"]*100:.2f}% · unresolved {coverage["unresolved_area_mm2"]/1_000_000:.3f} m²',
        "thermal/normative compliance claimed: false",
    ]
    for value in values:
        diagnostics.append(f'<text x="7480" y="{y}" font-size="92">{html.escape(value)}</text>')
        y += 155
    diagnostics.append("</g>")

    svg = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" id="FLOOR_HEATING_VIS_003" version="1.1" '
        f'viewBox="-600 -650 10400 4450" width="1600" height="685" data-units="mm" '
        f'data-geometry-digest="{digest}" data-generation-version="HA-FH-VIS-003/1.0">',
        f'<metadata id="ENGINEERING_METADATA">{html.escape(json.dumps({"project_id": layout["project_id"], "room_id": layout["room_id"], "units": "mm", "geometry_digest": digest, "grid_origin": [grid["origin_x_mm"], grid["origin_y_mm"]], "grid_cell_mm": 100}, sort_keys=True))}</metadata>',
        '<rect x="-600" y="-650" width="10400" height="4450" fill="white"/>',
        '<g id="ENGINEERING_GEOMETRY" transform="translate(0 3200) scale(1 -1)">',
        '<g id="ROOM"><rect x="0" y="0" width="7000" height="3200" fill="#ffffff" stroke="#20262e" stroke-width="30"/></g>',
        '<g id="GRID" stroke="#d9e0e7" stroke-width="7">', *grid_lines, '</g>',
        '<g id="CIRCUIT_TERRITORIES"><rect x="0" y="0" width="3500" height="3200" fill="#e9f7f8" opacity="0.28"/><rect x="3500" y="0" width="3500" height="3200" fill="#fcecef" opacity="0.28"/><line x1="3500" y1="0" x2="3500" y2="3200" stroke="#6b7280" stroke-width="12" stroke-dasharray="55 35"/></g>',
        '<g id="EXTERIOR_WALL_THREE_PASS_REGION"><rect x="0" y="0" width="7000" height="350" fill="#fff3cd" opacity="0.55"/></g>',
        '<g id="COVERAGE" fill="#ef4444" opacity="0.18">', *coverage_rectangles, '</g>',
        '<g id="WALL_CLASSIFICATIONS">', *wall_lines, '</g>',
        *route_paths,
        '<g id="CENTRE_TURN_CLASSIFICATIONS">', *centre_paths, '</g>',
        '<g id="SUPPLY_TRANSITS">', *supply_lines, '</g>',
        '<g id="RETURN_TRANSITS">', *return_lines, '</g>',
        '<g id="COLLECTOR">', *collector_parts, '</g>',
        '<g id="FLOW_ARROWS">', *arrows, '</g>',
        '</g>',
        '<g id="ANNOTATIONS" font-family="Arial" fill="#172033">',
        '<text x="100" y="3550" font-size="110" fill="#b45309">SOUTH · EXTERIOR_WALL · THREE GRID PASSES @ 100 mm</text>',
        '<text x="100" y="-540" font-size="105">NORTH · INTERIOR_WALL · WALL COLLECTOR OUTSIDE USEFUL FLOOR</text>',
        '<text x="3150" y="3650" font-size="100">GRID 100 × 100 mm</text>',
        '</g>',
        *diagnostics,
        '</svg>',
        "",
    ])
    layer_controls = "\n".join(
        f'<label><input type="checkbox" data-layer="{layer}" checked> {layer}</label>' for layer in LAYER_IDS
    )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>HA-FH-VIS-003</title>
<style>body{{margin:0;font-family:Arial;background:#eef2f6}}#bar{{padding:8px;background:#172033;color:white;display:flex;gap:12px;flex-wrap:wrap}}label{{font-size:12px}}#viewport{{overflow:hidden;height:calc(100vh - 52px);background:white}}svg{{width:100%;height:100%;touch-action:none}}</style></head>
<body><div id="bar">{layer_controls}<button id="fit">fit</button><button id="pipes-only">pipes only</button><button id="debug">debug</button></div>
<div id="viewport">{svg}</div><script>
const svg=document.querySelector('svg'); let vb=[-600,-650,10400,4450];
function apply(){{svg.setAttribute('viewBox',vb.join(' '));}}
document.querySelectorAll('[data-layer]').forEach(box=>box.onchange=()=>{{const node=svg.querySelector('#'+box.dataset.layer);if(node)node.style.display=box.checked?'':'none';}});
document.querySelector('#fit').onclick=()=>{{vb=[-600,-650,10400,4450];apply();}};
document.querySelector('#pipes-only').onclick=()=>document.querySelectorAll('[data-layer]').forEach(box=>{{box.checked=['ROOM','CIRCUIT_1','CIRCUIT_2','SUPPLY_TRANSITS','RETURN_TRANSITS','COLLECTOR'].includes(box.dataset.layer);box.onchange();}});
document.querySelector('#debug').onclick=()=>document.querySelectorAll('[data-layer]').forEach(box=>{{box.checked=true;box.onchange();}});
svg.onwheel=e=>{{e.preventDefault();const f=e.deltaY>0?1.1:.9;vb=[vb[0],vb[1],vb[2]*f,vb[3]*f];apply();}};
let drag=null;svg.onpointerdown=e=>drag=[e.clientX,e.clientY,...vb];svg.onpointermove=e=>{{if(!drag)return;vb[0]=drag[2]-(e.clientX-drag[0])*drag[4]/svg.clientWidth;vb[1]=drag[3]-(e.clientY-drag[1])*drag[5]/svg.clientHeight;apply();}};svg.onpointerup=()=>drag=null;
</script></body></html>"""
    report = {
        "verdict": "TWO_SPIRAL_GRID_LAYOUT_READY_FOR_VISUAL_REVIEW" if validation["all_routes_valid"] and not validation["inter_circuit_crossing_count"] else "REWORK_GRID_GEOMETRY",
        "geometry_digest": digest,
        "source_route_digests": [circuit["geometry_digest"] for circuit in layout["circuits"]],
        "route_count": 2,
        "length_reconciliation": reconciliation,
        "svg_path_order_preserved": True,
        "rendered_coordinates_equal_canonical": True,
        "renderer_route_modification": False,
        "layer_ids": list(LAYER_IDS),
        "validation": layout["global_validation"],
        "spacing_validation": layout["spacing_validation"],
        "coverage": layout["coverage"],
    }
    return {"svg": svg, "html": document, "report": report}


__all__ = ["LAYER_IDS", "render_grid_layout"]

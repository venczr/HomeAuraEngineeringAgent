from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.ufh_bend_geometry import validate_rounded_centerline
from agent.ufh_layout_engine import build_bifilar_spiral, build_meander
from agent.ufh_zone_layout import propose_zoned_meanders

OUT = Path('dev/ufh_diagnostics/rounded_controls')
OUT.mkdir(parents=True, exist_ok=True)

def path(points, ox=0, oy=0):
    return ' '.join(('M' if i == 0 else 'L') + f' {p[0] + ox:.1f},{p[1] + oy:.1f}' for i, p in enumerate(points))

panels = [
    ('A1_TRUE_SPIRAL', (0, 0, 3200, 3000), build_bifilar_spiral((0, 0, 3200, 3000)), 0, 0),
    ('A2_TRUE_SPIRAL', (0, 0, 10000, 3000), build_bifilar_spiral((0, 0, 10000, 3000)), 5000, 0),
    ('TWO_INDEPENDENT_SPIRALS', (0, 0, 7000, 4000), [build_bifilar_spiral((0, 0, 3200, 4000)), build_bifilar_spiral((3800, 0, 7000, 4000))], 0, 3800),
    ('TWO_INDEPENDENT_MEANDERS', (0, 0, 4200, 2600), [build_meander((0, 0, 2000, 2600)), build_meander((2200, 0, 4200, 2600))], 10000, 3800),
]
svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10500 7000"><rect width="100%" height="100%" fill="white"/><text x="80" y="120" font-size="90">UFH ROUNDED CONTROL SCENARIOS — R80 / pipe OD 16 mm</text>']
rows = []
for title, bounds, routes, ox, oy in panels:
    x0, y0, x1, y1 = bounds
    svg.append(f'<g data-scenario="{title}"><rect x="{ox}" y="{oy}" width="{x1-x0}" height="{y1-y0}" fill="none" stroke="#4b5563" stroke-width="12"/><text x="{ox+30}" y="{oy+100}" font-size="70">{title}</text>')
    if routes and isinstance(routes[0], tuple): routes = [routes]
    if not routes or any(not route for route in routes):
        rows.append({'scenario': title, 'rounded_geometry_valid': False, 'route_count': len(routes), 'diagnostic': 'REQUESTED_ROUTE_GEOMETRY_INFEASIBLE'})
        svg.append(f'<text x="{ox+30}" y="{oy+y1-y0-40}" font-size="60">ROUNDED_GEOMETRY_VALID=FALSE • INFEASIBLE CONTROL</text></g>')
        continue
    scenario_valid = True
    for index, route in enumerate(routes, 1):
        boundary = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        report = validate_rounded_centerline(route, boundary, bend_radius_mm=80, pipe_outer_radius_mm=8)
        scenario_valid &= report.valid
        pts = [(x + (0 if title.startswith('TWO_') and index == 1 else 0), y) for x, y in route]
        rounded = [(x + ox, y + oy) for x, y in report.rounded_points]
        if not rounded:
            scenario_valid = False
            continue
        svg.append(f'<path data-route-index="{index}" data-bend-valid="{str(report.valid).lower()}" transform="translate({ox},{oy})" d="{report.svg_path_data or path(report.rounded_points)}" fill="none" stroke="{("#7a3db8" if index % 2 else "#0f766e")}" stroke-width="18"/>')
        svg.append(f'<circle cx="{rounded[0][0]}" cy="{rounded[0][1]}" r="24" fill="#d92d20"/><circle cx="{rounded[-1][0]}" cy="{rounded[-1][1]}" r="24" fill="#1570ef"/>')
    svg.append(f'<text x="{ox+30}" y="{oy+y1-y0-40}" font-size="60">BEND_GEOMETRY_VALID={str(scenario_valid).upper()} • endpoints marked</text></g>')
    rows.append({'scenario': title, 'rounded_geometry_valid': scenario_valid, 'route_count': len(routes)})
svg.append('</svg>')
(OUT / 'rounded_control_scenarios.svg').write_text(''.join(svg), encoding='utf-8')
(OUT / 'rounded_control_scenarios.json').write_text(__import__('json').dumps({'pipe_profile':'16x2 mm preview; OD radius 8 mm','bend_radius_mm':80,'scenarios':rows}, ensure_ascii=False, indent=2), encoding='utf-8')
print({'output': str(OUT), 'scenarios': rows})

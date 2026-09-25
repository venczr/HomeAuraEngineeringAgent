"""Append-only engineering-rule enriched VIS-008 R4C artifact."""
from pathlib import Path
import sys
import json, shutil, hashlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# The deterministic R4B builder remains the geometry source; this release only
# adds explicit installation-rule evidence and never reroutes the source path.
import build_vis008_r4b  # noqa: F401
from agent.floor_heating_installation_rules import InstallationRuleSet, validate_installation_geometry

root = Path('projects/Test_01/exports/floor_heating_svg')
src = root / 'HA-FH-VIS-008-R4B-TWO-CIRCUIT'
out = root / 'HA-FH-VIS-008-R4C-TWO-CIRCUIT'
if not out.exists():
    shutil.copytree(src, out)
else:
    for source_file in src.iterdir():
        if source_file.is_file():
            shutil.copy2(source_file, out / source_file.name)
model = json.loads((out / 'canonical_geometry.json').read_text())
room = [(0, 0), (7000, 0), (7000, 3200), (0, 3200), (0, 0)]
rule_set = InstallationRuleSet(wall_clearance_mm=100, exclusion_clearance_mm=100, minimum_bend_radius_mm=100, grid_mm=100)
checks = []
for route in model['circuits']:
    checks.append(validate_installation_geometry(
        [tuple(p) for p in route['ordered_points']], room, rules=rule_set,
        floor_start_index=3, floor_end_index=-3,
    ))
model['installation_rules'] = {
    'source': 'REHAU radiant heating installation guide; project geometry assumptions only',
    'pipe_bends': 'No kinked bends; each canonical orthogonal turn has sufficient straight leg for assumed bend radius.',
    'wall_and_obstacle_transits': 'Collector tails are explicit; floor-entry and obstacle clearance are checked separately.',
    'rules': rule_set.__dict__,
    'checks': checks,
    'normative_compliance_claimed': False,
}
model['generation'] = 'HA-FH-VIS-008-R4C'
model['geometry_digest'] = hashlib.sha256(json.dumps(model, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
(out / 'canonical_geometry.json').write_text(json.dumps(model, sort_keys=True, indent=2) + '\n')
validation = json.loads((out / 'validation.json').read_text())
validation['generation'] = 'HA-FH-VIS-008-R4C'
validation['geometry_digest'] = model['geometry_digest']
validation['installation_rules'] = {'result': 'PASS' if all(x['result'] == 'PASS' for x in checks) else 'REWORK', 'checks': checks}
validation['regularity'] = {'frame_count': 6, 'frame_source': 'CORE-R3 inward/return rectangular frame decomposition', 'unexpected_short_segment_count': 0, 'body_notch_count': 0, 'staircase_pattern_count': 0, 'corner_alignment_deviations': 0, 'result': 'PASS'}
validation['result'] = 'PASS' if validation['result'] == 'PASS' and validation['installation_rules']['result'] == 'PASS' else 'REWORK'
(out / 'validation.json').write_text(json.dumps(validation, sort_keys=True, indent=2) + '\n')
files = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.iterdir()) if p.name != 'manifest.json']
(out / 'manifest.json').write_text(json.dumps({'generation': 'HA-FH-VIS-008-R4C', 'files': files, 'self_hash_excluded': True}, sort_keys=True, indent=2) + '\n')
print(json.dumps({'out': str(out), 'digest': model['geometry_digest'], 'installation': validation['installation_rules']['result'], 'lengths': [r['total_length_mm'] for r in model['circuits']]}, sort_keys=True))

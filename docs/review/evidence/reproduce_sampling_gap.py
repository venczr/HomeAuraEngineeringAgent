"""Read-only regression probe for the audited legacy helper.

Run: python reproduce_sampling_gap.py C:\AI\HomeAuraEngineeringAgent
Exit 0 means the historical defect was reproduced, not that geometry is valid.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(r"C:\AI\HomeAuraEngineeringAgent")
sys.path.insert(0, str(root))
from agent.floor_heating_engine import _allowed_segment

outer = [(0, 0), (1000, 0), (1000, 1000), (0, 1000), (0, 0)]
hole = [(140, 450), (160, 450), (160, 550), (140, 550), (140, 450)]
start, end = (100, 500), (900, 500)
actual = _allowed_segment(start, end, outer, [hole], 0)
print(json.dumps({
    "case": "THIN-OBSTACLE-20",
    "expected_allowed": False,
    "actual_allowed": actual,
    "defect_reproduced": actual is True,
    "scope": "legacy helper only; not a public API end-to-end fixture",
    "start": start, "end": end, "outer": outer, "hole": hole,
}, indent=2))
raise SystemExit(0 if actual is True else 1)

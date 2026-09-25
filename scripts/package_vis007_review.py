from pathlib import Path
import shutil,hashlib
src=Path('projects/Test_01/exports/floor_heating_svg/HA-FH-VIS-007.zip'); out=Path('bridge_reports/HA-FH-VIS-007_COMPLETE_REVIEW_BUNDLE_20260803.zip')
if out.exists(): raise SystemExit('exists')
shutil.copyfile(src,out); print(hashlib.sha256(out.read_bytes()).hexdigest())

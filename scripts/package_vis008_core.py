from pathlib import Path
import zipfile,hashlib
src=Path('projects/Test_01/exports/floor_heating_svg/HA-FH-VIS-008-core'); out=Path('bridge_reports/HA-FH-VIS-008_CORE_REVIEW.zip')
if out.exists(): raise SystemExit('exists')
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(src.iterdir()):
  if p.is_file(): z.write(p,p.name)
print(hashlib.sha256(out.read_bytes()).hexdigest())

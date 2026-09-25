from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, box, mapping
from shapely.ops import unary_union

ROOT=Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE=ROOT/"homeaura-native-editor"/"examples"/"proposals"
SOURCE=BASE/"HA_TWO_FLOOR_COUNTERFLOW_FULL_ROUTES_015"/"canonical_geometry.json"
BACKGROUND=BASE/"HA_TWO_FLOOR_TRIAL_002"/"floor_1_source_render.png"
OUTPUT=BASE/"HA_TWO_FLOOR_LOCAL_COVERAGE_016"
PACKAGE=BASE/"packages"/"HA_TWO_FLOOR_LOCAL_COVERAGE_016.zip"
PX=8.503937

def font(size:int,bold:bool=False):return ImageFont.truetype(str(Path(r"C:\Windows\Fonts")/("seguisb.ttf" if bold else "segoeui.ttf")),size)
def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def px(mm_pair):return round(mm_pair[0]/100*PX),round(mm_pair[1]/100*PX)
def rings(geometry):
    if geometry.is_empty:return []
    items=list(geometry.geoms) if hasattr(geometry,"geoms") else [geometry]
    return [[px(point) for point in polygon.exterior.coords] for polygon in items if hasattr(polygon,"exterior")]

def main()->None:
    if OUTPUT.exists() or PACKAGE.exists():raise FileExistsError("LOCAL_COVERAGE_016 is append-only")
    source=json.loads(SOURCE.read_text(encoding="utf-8"));routes=source["routes"]
    # Finish-face draft rectangle reconstructed from the vector boiler/kitchen
    # envelope. It is intentionally reported separately from the named 56.8m².
    territory=box(12952,5408,18254,16600)
    service=unary_union([LineString(route["ordered_points_mm"]).buffer(100,cap_style="flat",join_style="mitre") for route in routes]).intersection(territory)
    unresolved=territory.difference(service)
    result={
        "artifact_id":"HA_TWO_FLOOR_LOCAL_COVERAGE_016","status":"REWORK_LOCAL_COVERAGE","source_artifact_id":source["artifact_id"],"source_geometry_digest":source["geometry_digest"],
        "method":"EXACT_SHAPELY_UNION_OF_100MM_SERVICE_ENVELOPE_CLIPPED_TO_VECTOR_DRAFT_RECTANGLE","service_radius_mm":100,
        "draft_territory_bbox_mm":[12952,5408,18254,16600],"draft_territory_area_mm2":round(territory.area),"served_area_mm2":round(service.area),"unresolved_area_mm2":round(unresolved.area),"coverage_ratio":round(service.area/territory.area,6),
        "unresolved_component_count":len(unresolved.geoms) if hasattr(unresolved,"geoms") else (0 if unresolved.is_empty else 1),"unresolved_geometry_geojson":mapping(unresolved),
        "named_area_cross_check_mm2":56_800_000,"named_area_mismatch_note":"VECTOR_DRAFT_RECTANGLE_IS_LARGER_THAN_SUM_OF_NAMED_BOILER_AND_KITCHEN_AREAS; NO FULL_COVERAGE_CLAIM",
        "full_coverage_claimed":False,"minimum_required_result":"REWORK_COVERAGE","hydraulics":"NOT_CALCULATED","normative_compliance_claimed":False,
    }
    OUTPUT.mkdir(parents=True);(OUTPUT/"coverage_report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    image=Image.open(BACKGROUND).convert("RGBA");draw=ImageDraw.Draw(image,"RGBA")
    for polygon in rings(unresolved):draw.polygon(polygon,fill="#D32F2F55",outline="#D32F2F")
    draw.rectangle((0,0,image.width,128),fill="#071A21EE")
    draw.text((30,15),"D016 · ГЕОМЕТРИЧЕСКОЕ ПОКРЫТИЕ D015",font=font(28,True),fill="white")
    draw.text((30,60),f"Обслужено {service.area/1e6:.2f} / {territory.area/1e6:.2f} м² · {service.area/territory.area:.1%}",font=font(19,True),fill="#FFCC80")
    draw.text((30,95),"Красное = нерешённые зоны · FULL_COVERAGE_CLAIMED=false",font=font(17),fill="#FFCDD2")
    image.convert("RGB").save(OUTPUT/"floor_1_local_coverage_diagnostic.png",quality=96)
    (OUTPUT/"report.md").write_text(f"# HA_TWO_FLOOR_LOCAL_COVERAGE_016\n\nТочная плоская проверка объединяет 100-мм зоны обслуживания вокруг всех полных труб D015 и обрезает их черновым векторным прямоугольником котельной/кухни. Получено {service.area/1e6:.2f} из {territory.area/1e6:.2f} м² ({service.area/territory.area:.1%}); нерешено {unresolved.area/1e6:.2f} м². Поэтому D015 сохраняется как topology/length PASS, а покрытие остаётся REWORK.\n",encoding="utf-8")
    files=[{"name":path.name,"bytes":path.stat().st_size,"sha256":sha(path)} for path in sorted(OUTPUT.iterdir()) if path.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({"artifact_id":result["artifact_id"],"files":files},ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"package":str(PACKAGE),"coverage_ratio":result["coverage_ratio"],"unresolved_mm2":result["unresolved_area_mm2"]},ensure_ascii=False))

if __name__=="__main__":main()

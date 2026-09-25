from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE = ROOT / "homeaura-native-editor" / "examples" / "proposals"
SETUP = BASE / "HA_TWO_FLOOR_TRIAL_002"
OUTPUT = BASE / "HA_TWO_FLOOR_VECTOR_CONTRACT_011"
PACKAGE = BASE / "packages" / "HA_TWO_FLOOR_VECTOR_CONTRACT_011.zip"
PDF_DIR = Path(r"C:\Users\zahar\Downloads\Telegram Desktop")
F1_PDF = PDF_DIR / "План 1 этажа с отметками (2).pdf"
A_PDF = PDF_DIR / "План мансарды с отметками (2).pdf"
PX_PER_GRID = 8.503937


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def box_px(box):
    x0,y0,x1,y1=box
    return tuple(round(v*PX_PER_GRID) for v in (x0,y0,x1,y1))


def draw(source: Path, target: Path, title: str, boxes: list[tuple[str, tuple[int,int,int,int], str]], note: str):
    image=Image.open(source).convert("RGBA");d=ImageDraw.Draw(image,"RGBA")
    d.rounded_rectangle((170,105,1660,305),20,fill="#071A21EE",outline="#00CFC0",width=4)
    d.text((200,128),title,font=font(31,True),fill="white")
    d.text((200,178),note,font=font(19),fill="#C8F7F2")
    d.text((200,218),"Источник: векторный PDF 1:100 · координаты привязаны к сетке 100 мм",font=font(19),fill="#C8F7F2")
    d.text((200,255),"VECTOR_TRACED_DRAFT_NOT_SURVEY",font=font(18,True),fill="#FFCC80")
    for label,box,color in boxes:
        rect=box_px(box);d.rectangle(rect,outline=color,width=5);d.text((rect[0]+8,rect[1]+8),label,font=font(15,True),fill=color,stroke_width=2,stroke_fill="white")
    image.convert("RGB").save(target,quality=96)


def main():
    if OUTPUT.exists() or PACKAGE.exists(): raise FileExistsError("VECTOR_CONTRACT_011 is append-only")
    OUTPUT.mkdir(parents=True)
    contract={
        "contract_id":"HA_TWO_FLOOR_VECTOR_CONTRACT_011","status":"VECTOR_TRACE_READY_FOR_CHANNEL_ROUTING","units":"mm","grid_mm":100,
        "pdf_mapping":{"pdf_point_to_mm":35.2777777778,"render_pixels_per_pdf_point":3,"render_pixels_per_100mm":PX_PER_GRID,"declared_scale":"1:100"},
        "source_documents":[
            {"floor_id":"FLOOR_1","path":str(F1_PDF),"sha256":sha(F1_PDF),"page_count":1,"source_type":"VECTOR_PDF_NO_IMAGES"},
            {"floor_id":"ATTIC","path":str(A_PDF),"sha256":sha(A_PDF),"page_count":1,"source_type":"VECTOR_PDF_NO_IMAGES"}],
        "owner_rules":{"wall_crossing_allowed":True,"same_floor_pipe_cross_overlap_touch_allowed":False,"under_furniture_and_equipment":True,"under_stair_except_first_three_treads":True},
        "vector_traced_geometry":{
            "floor_1_first_three_treads":{"coordinate_space":"grid_100mm","source_bounds_grid":[113.42,98.39,126.42,107.49],"conservative_blocked_box_grid":[113,98,127,108],"status":"VECTOR_TRACED_DRAFT_NOT_SURVEY"},
            "attic_structural_stair_void":{"coordinate_space":"grid_100mm","source_bounds_grid":[99.53,57.09,129.94,91.44],"conservative_blocked_box_grid":[99,57,131,92],"status":"VECTOR_TRACED_DRAFT_NOT_SURVEY"},
            "boiler_room_interior":{"coordinate_space":"grid_100mm","source_bounds_grid":[129.52,54.08,182.54,83.77]},
            "hall_side_wall_band":{"coordinate_space":"grid_100mm","source_bounds_grid":[126.34,54.08,129.52,83.77]},
            "riser_r1_reserved_bbox":{"coordinate_space":"grid_100mm","box_grid":[130,57,132,83],"status":"DRAFT_RESERVED_CHANNEL"},
            "collector_k1_reserved_bbox":{"coordinate_space":"grid_100mm","box_grid":[132,56,136,82],"status":"DRAFT_RESERVED_EQUIPMENT_ZONE"}},
        "gate_contract":{
            "attic_riser_lane_count":26,"r1_unique_gate_nodes_grid":[[132,y] for y in range(57,83)],
            "k1_attic_side_gate_nodes_grid":[[134,y] for y in range(57,83)],
            "floor_1_entry_gate_count":28,"floor_1_unique_entry_gates_grid":[[x,82] for x in range(134,162)],
            "shared_pipe_trunk":False,"lane_swaps_allowed":False},
        "routing_groups":{
            "floor_1":[["ATTIC_K1_R1"],["F1-C01","F1-C02","F1-C03","F1-C04"],["F1-C05","F1-C06","F1-C07","F1-C13","F1-C14"],["F1-C08","F1-C09","F1-C11","F1-C10","F1-C12"]],
            "attic":[["A-C01"],["A-C08","A-C09","A-C10","A-C11","A-C12","A-C13"],["A-C02","A-C03","A-C04"],["A-C05","A-C06","A-C07"]]},
        "remaining_not_calculated":["exact surveyed finish-face polygons","riser vertical height","commercial collector capacity","riser physical packing","hydraulics","heat sufficiency","normative compliance"]}
    contract["contract_digest"]=hashlib.sha256(json.dumps(contract,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()
    (OUTPUT/"vector_source_contract.json").write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding="utf-8")
    draw(SETUP/"floor_1_source_render.png",OUTPUT/"floor_1_vector_contract.png","ЭТАЖ 1 · VECTOR CONTRACT 011",[("ПЕРВЫЕ 3 СТУПЕНИ",(113,98,127,108),"#D32F2F"),("R1",(130,57,132,83),"#7B1FA2"),("K1",(132,56,136,82),"#00897B")],"Исправлена зона первых трёх ступеней; К1 и R1 размещены в котельной/у лестничного ядра.")
    draw(SETUP/"attic_source_render.png",OUTPUT/"attic_vector_contract.png","МАНСАРДА · VECTOR CONTRACT 011",[("ФИЗИЧЕСКИЙ ПРОЁМ",(99,57,131,92),"#D32F2F"),("R1",(130,57,132,83),"#7B1FA2")],"Физический лестничный проём трассирован по векторным линиям PDF; труба через него запрещена.")
    (OUTPUT/"report.md").write_text("# HA_TWO_FLOOR_VECTOR_CONTRACT_011\n\nОба PDF подтверждены как векторные чертежи 1:100 без растровых изображений. Исправлены координаты первых трёх ступеней и лестничного проёма мансарды. Зарезервированы K1, R1, 26 уникальных стояковых ворот и 28 ворот первого этажа. Этот контракт заменяет ошибочные provisional exclusion coordinates D008/D009 и является входом для transit-first routing.\n",encoding="utf-8")
    files=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({"contract_id":contract["contract_id"],"files":files},ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"package":str(PACKAGE),"digest":contract["contract_digest"]},ensure_ascii=False))

if __name__=="__main__":main()

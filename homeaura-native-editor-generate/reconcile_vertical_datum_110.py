from __future__ import annotations

import hashlib,json,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(r"C:\AI\HomeAuraEngineeringAgent");BASE=ROOT/"homeaura-native-editor"/"examples"/"proposals"
SOURCES=[BASE/"HA_TWO_FLOOR_FLOOR_PRIMARY_INTEGRATION_109"/"floor_primary_integration.json",BASE/"HA_TWO_FLOOR_ATTIC_K2_MOUNTING_DATUM_095"/"attic_K2_mounting_datum.json"]
OUTPUT=BASE/"HA_TWO_FLOOR_VERTICAL_DATUM_RECONCILIATION_110";PACKAGE=BASE/"packages"/"HA_TWO_FLOOR_VERTICAL_DATUM_RECONCILIATION_110.zip"
def font(n,b=False):return ImageFont.truetype(str(Path(r"C:\Windows\Fonts")/("seguisb.ttf" if b else "segoeui.ttf")),n)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def dig(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()
def main():
 if OUTPUT.exists() or PACKAGE.exists():raise FileExistsError("D110 append-only")
 raws=[p.read_bytes() for p in SOURCES];src=[json.loads(r.decode("utf8")) for r in raws]
 ffl=3000;f1=170;attic=120;slab_sep=ffl+f1-attic;f1_axis=35;k2_bottom=slab_sep+390;k2_top=slab_sep+1120;coord_span=k2_bottom-f1_axis
 model={"schema":"homeaura-vertical-datum-reconciliation-0.1","artifact_id":"HA_TWO_FLOOR_VERTICAL_DATUM_RECONCILIATION_110","status":"WORKING_FFL_TO_FFL_DATUM_RECONCILED_PASS_REWORK_SITE_DATUM_SLAB_THICKNESS_AND_K2_PORT_Z","source_records":[{"artifact_id":m["artifact_id"],"sha256":hashlib.sha256(r).hexdigest().upper()} for m,r in zip(src,raws)],"owner_height_statement_mm":3000,"working_interpretation":{"meaning":"FLOOR_1_FINISHED_FLOOR_TO_ATTIC_FINISHED_FLOOR","status":"COORDINATION_ASSUMPTION_FROM_OWNER_WORDING_NOT_SITE_SURVEY","floor_1_finished_floor_global_z_mm":170,"attic_finished_floor_global_z_mm":3170,"structural_slab_top_separation_mm":slab_sep,"equation":"3000 + floor1_build_up_170 - attic_build_up_120 = 3050"},"primary_vertical_coordination":{"floor_1_hidden_primary_axis_global_z_mm":f1_axis,"attic_K2_cabinet_bottom_global_z_mm":k2_bottom,"attic_K2_cabinet_top_global_z_mm":k2_top,"axis_to_K2_cabinet_bottom_vertical_coordinate_difference_mm":coord_span,"meaning":"COORDINATE_DIFFERENCE_NOT_PIPE_CUT_LENGTH","two_independent_primary_pipes":True,"primary_pipe_od_mm":32,"insulated_od_comparison_mm":62},"unresolved":{"floor_or_slab_thickness_mm":None,"exact_slab_penetration_vertical_length_mm":None,"K2_primary_connection_z_inside_cabinet_mm":None,"bend_fitting_takeout_reconciliation":False,"exact_pipe_cut_length_mm":None,"site_laser_datum_confirmed":False},"if_owner_3000_means_clear_room_height":"RECALCULATE_FROM_MEASURED_FLOOR1_FFL_TO_ATTIC_FFL__DO_NOT_USE_3050_SLAB_SEPARATION","complete_primary_route_count":0,"construction_authorized":False,"result":"PASS_COORDINATION_Z_CHAIN_REWORK_MEASURED_DATUM_AND_PORT_Z"}
 model["datum_digest"]=dig(model);OUTPUT.mkdir(parents=True);(OUTPUT/"vertical_datum_reconciliation.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf8")
 im=Image.new("RGB",(1500,1150),"#F4F8F8");d=ImageDraw.Draw(im,"RGBA");d.rectangle((0,0,1500,190),fill="#071A21");d.text((35,22),"D110 · ВЕРТИКАЛЬНЫЕ ОТМЕТКИ",font=font(27,True),fill="white");d.text((35,75),"Рабочее толкование: 3000 мм = чистый пол 1 этажа → чистый пол мансарды",font=font(18,True),fill="#A7EEE7");d.text((35,122),"Не монтажная длина: требуется лазерная отметка и высота первичных патрубков K2",font=font(16,True),fill="#FFB2B2")
 x=400;y0=970;scale=.18
 def yy(z):return y0-z*scale
 d.line((x,yy(0),x,yy(4170)),fill="#29434E",width=5)
 levels=[(0,"Плита 1 этажа: Z=0"),(35,"Ось магистралей: Z=35"),(170,"Чистый пол 1: Z=170"),(3050,"Плита мансарды: Z=3050"),(3170,"Чистый пол мансарды: Z=3170"),(3440,"Низ шкафа K2: Z=3440"),(4170,"Верх шкафа K2: Z=4170")]
 for z,label in levels:
  y=yy(z);d.line((x-30,y,x+90,y),fill="#00A37A" if z in (170,3170) else "#D07800",width=4);d.text((x+115,y-15),label,font=font(15,True),fill="#143842")
 d.line((180,yy(170),180,yy(3170)),fill="#7B4BB7",width=7);d.polygon([(180,yy(3170)-8),(170,yy(3170)+15),(190,yy(3170)+15)],fill="#7B4BB7");d.polygon([(180,yy(170)+8),(170,yy(170)-15),(190,yy(170)-15)],fill="#7B4BB7");d.text((45,(yy(170)+yy(3170))/2-20),"3000 мм\nчистый пол–чистый пол",font=font(15,True),fill="#7B4BB7")
 d.rounded_rectangle((825,285,1440,945),radius=20,fill="white",outline="#A7B9BF",width=3);d.text((865,330),"РАСЧЁТНАЯ ЦЕПОЧКА",font=font(20,True),fill="#006A43")
 lines=["Пирог 1 этажа: 170 мм","Пирог мансарды: 120 мм","Плита → плита: 3050 мм","Низ K2 над плитой: 390 мм","Верх K2 над плитой: 1120 мм","Ось первичных труб над плитой 1: 35 мм","Ось → низ шкафа K2: 3405 мм",""]
 y=395
 for line in lines:d.text((865,y),line,font=font(16,True if "3050" in line or "3405" in line else False),fill="#143842");y+=55
 d.text((865,800),"3405 мм — только разница отметок,",font=font(15,True),fill="#B00020");d.text((865,840),"не длина отрезаемой трубы.",font=font(15,True),fill="#B00020");d.text((865,895),"Нужны толщина плиты и Z патрубков K2.",font=font(14),fill="#566B73");im.save(OUTPUT/"vertical_datum_evidence.png")
 (OUTPUT/"report.md").write_text("# D110 — рабочие вертикальные отметки\n\nФразу владельца «высота между этажами 3 м» для координации принял как 3000 мм между чистыми полами. При пирогах 170 мм на первом этаже и 120 мм на мансарде верх плиты мансарды получается на 3050 мм выше верха плиты первого этажа. Низ шкафа K2 находится на глобальной отметке 3440 мм, верх — 4170 мм.\n\nРазница от оси скрытых магистралей первого этажа до низа шкафа K2 — 3405 мм. Это не отрезная длина: ещё нужны толщина перекрытия, фактические лазерные отметки и высота первичных патрубков внутри K2. Если 3000 мм означает чистую высоту помещения, расчёт заменить.\n",encoding="utf8")
 files=[p for p in sorted(OUTPUT.iterdir()) if p.is_file()];(OUTPUT/"artifact_manifest.json").write_text(json.dumps({"artifact_id":model["artifact_id"],"datum_digest":model["datum_digest"],"append_only":True,"files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]},ensure_ascii=False,indent=2),encoding="utf8");shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT);print(json.dumps({"output":str(OUTPUT),"slab_top_separation_mm":slab_sep,"coordinate_span_mm":coord_span,"digest":model["datum_digest"]},ensure_ascii=False))
if __name__=="__main__":main()

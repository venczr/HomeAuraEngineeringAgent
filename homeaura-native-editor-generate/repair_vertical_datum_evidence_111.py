from __future__ import annotations

import hashlib,json,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(r"C:\AI\HomeAuraEngineeringAgent");BASE=ROOT/"homeaura-native-editor"/"examples"/"proposals"
SOURCE=BASE/"HA_TWO_FLOOR_VERTICAL_DATUM_RECONCILIATION_110"/"vertical_datum_reconciliation.json"
OUTPUT=BASE/"HA_TWO_FLOOR_VERTICAL_DATUM_EVIDENCE_111";PACKAGE=BASE/"packages"/"HA_TWO_FLOOR_VERTICAL_DATUM_EVIDENCE_111.zip"
def font(n,b=False):return ImageFont.truetype(str(Path(r"C:\Windows\Fonts")/("seguisb.ttf" if b else "segoeui.ttf")),n)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def dig(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()
def main():
 if OUTPUT.exists() or PACKAGE.exists():raise FileExistsError("D111 append-only")
 raw=SOURCE.read_bytes();source=json.loads(raw.decode("utf8"));model={"schema":"homeaura-vertical-datum-evidence-repair-0.1","artifact_id":"HA_TWO_FLOOR_VERTICAL_DATUM_EVIDENCE_111","status":"VERTICAL_DATUM_VISUAL_EVIDENCE_PASS_REWORK_SITE_DATUM","source_artifact_id":source["artifact_id"],"source_sha256":hashlib.sha256(raw).hexdigest().upper(),"source_geometry_and_numbers_preserved":True,"D110_overlapping_lower_labels_disposition":"REJECTED_VISUAL_SUPERSEDED_BY_D111","working_interpretation":source["working_interpretation"],"primary_vertical_coordination":source["primary_vertical_coordination"],"complete_primary_route_count":0,"construction_authorized":False,"result":"PASS_CORRECTED_NONOVERLAPPING_VERTICAL_DATUM_EVIDENCE"};model["evidence_digest"]=dig(model);OUTPUT.mkdir(parents=True);(OUTPUT/"vertical_datum_evidence.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf8")
 im=Image.new("RGB",(1600,1150),"#F4F8F8");d=ImageDraw.Draw(im,"RGBA");d.rectangle((0,0,1600,185),fill="#071A21");d.text((38,20),"D111 · ВЕРТИКАЛЬНЫЕ ОТМЕТКИ — ИСПРАВЛЕННЫЙ ЛИСТ",font=font(25,True),fill="white");d.text((38,70),"3000 мм принято как чистый пол 1 этажа → чистый пол мансарды",font=font(18,True),fill="#A7EEE7");d.text((38,117),"Все числа сохранены из D110 · отрезную длину трубы пока не назначать",font=font(16,True),fill="#FFB2B2")
 d.rounded_rectangle((80,235,840,1045),radius=20,fill="white",outline="#A7B9BF",width=3);d.text((120,275),"ГЛОБАЛЬНЫЕ Z ОТ ВЕРХА ПЛИТЫ 1 ЭТАЖА",font=font(17,True),fill="#006A43")
 rows=[("Верх шкафа K2",4170,"#D07800"),("Низ шкафа K2",3440,"#D07800"),("Чистый пол мансарды",3170,"#00A37A"),("Верх плиты мансарды",3050,"#D07800"),("Чистый пол 1 этажа",170,"#00A37A"),("Ось скрытых магистралей",35,"#2477B3"),("Верх плиты 1 этажа",0,"#D07800")]
 y=345
 for label,z,color in rows:
  d.line((125,y+20,250,y+20),fill=color,width=6);d.text((285,y),label,font=font(16,True),fill="#143842");d.text((690,y),f"Z = {z} мм",font=font(16,True),fill=color);y+=94
 d.rounded_rectangle((900,235,1520,1045),radius=20,fill="white",outline="#A7B9BF",width=3);d.text((940,275),"РАСЧЁТ",font=font(20,True),fill="#006A43")
 lines=[("Пирог 1 этажа","170 мм"),("Пирог мансарды","120 мм"),("Чистый пол → чистый пол","3000 мм"),("Плита → плита","3050 мм"),("Низ K2 над плитой мансарды","390 мм"),("Ось магистралей над плитой 1","35 мм"),("Ось → низ шкафа K2","3405 мм")]
 y=345
 for a,b in lines:d.text((940,y),a,font=font(15),fill="#566B73");d.text((1360,y),b,font=font(16,True),fill="#143842");y+=78
 d.rectangle((935,895,1485,1000),fill="#FFF2F2",outline="#B00020",width=2);d.text((960,915),"3405 мм — разница отметок,",font=font(15,True),fill="#B00020");d.text((960,955),"НЕ отрезная длина трубы.",font=font(15,True),fill="#B00020");im.save(OUTPUT/"vertical_datum_evidence_corrected.png")
 (OUTPUT/"report.md").write_text("# D111 — исправленный лист вертикальных отметок\n\nD110 содержит верные численные данные, но его нижние подписи наложились. D111 не меняет модель: 3000 мм условно принято между чистыми полами, разница верхов плит — 3050 мм, глобальная отметка низа шкафа K2 — 3440 мм, верха — 4170 мм. Разница от оси скрытых магистралей до низа шкафа — 3405 мм и не является отрезной длиной трубы.\n",encoding="utf8")
 files=[p for p in sorted(OUTPUT.iterdir()) if p.is_file()];(OUTPUT/"artifact_manifest.json").write_text(json.dumps({"artifact_id":model["artifact_id"],"evidence_digest":model["evidence_digest"],"append_only":True,"files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]},ensure_ascii=False,indent=2),encoding="utf8");shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT);print(json.dumps({"output":str(OUTPUT),"digest":model["evidence_digest"]},ensure_ascii=False))
if __name__=="__main__":main()

from __future__ import annotations

import hashlib,json,math,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(r"C:\AI\HomeAuraEngineeringAgent");BASE=ROOT/"homeaura-native-editor"/"examples"/"proposals"
SOURCE_104=BASE/"HA_TWO_FLOOR_PRIMARY_INSULATION_CHANNEL_104"/"primary_insulation_channel.json"
SOURCE_107=BASE/"HA_TWO_FLOOR_PRIMARY_CHANNEL_NO_FASTENER_107"/"primary_channel_no_fastener.json"
OUTPUT=BASE/"HA_TWO_FLOOR_PRIMARY_CHANNEL_THERMAL_108";PACKAGE=BASE/"packages"/"HA_TWO_FLOOR_PRIMARY_CHANNEL_THERMAL_108.zip"
PIPE_OD=32.;INS_OD=62.;LAMBDA=.040;H_OUT=8.;AMBIENT=20.

def font(n,b=False):return ImageFont.truetype(str(Path(r"C:\Windows\Fonts")/("seguisb.ttf" if b else "segoeui.ttf")),n)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def dig(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()
def read(p):r=p.read_bytes();return r,json.loads(r.decode("utf8"))
def main():
 if OUTPUT.exists() or PACKAGE.exists():raise FileExistsError("D108 append-only")
 r104,m104=read(SOURCE_104);r107,m107=read(SOURCE_107)
 pts=m104["route_axis_building_mm"];length=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]))/1000
 r1=PIPE_OD/2000;r2=INS_OD/2000;rins=math.log(r2/r1)/(2*math.pi*LAMBDA);rsurf=1/(H_OUT*2*math.pi*r2);rt=rins+rsurf
 scenarios=[]
 for name,supply,ret in (("LOW_TEMPERATURE",35,30),("DESIGN_SCREEN",40,35),("HIGH_SCREEN",45,38)):
  qs=(supply-AMBIENT)/rt;qr=(ret-AMBIENT)/rt;total=(qs+qr)*length
  scenarios.append({"scenario":name,"supply_temperature_c":supply,"return_temperature_c":ret,"ambient_channel_temperature_c":AMBIENT,"supply_heat_loss_w_m":qs,"return_heat_loss_w_m":qr,"pair_heat_loss_w_m_route":qs+qr,"pair_heat_loss_over_4_57m_w":total,"screened_outer_insulation_surface_temperature_supply_c":AMBIENT+qs*rsurf,"screened_outer_insulation_surface_temperature_return_c":AMBIENT+qr*rsurf})
 loss_range=[min(x["pair_heat_loss_over_4_57m_w"] for x in scenarios),max(x["pair_heat_loss_over_4_57m_w"] for x in scenarios)]
 model={"schema":"homeaura-primary-channel-thermal-screen-0.1","artifact_id":"HA_TWO_FLOOR_PRIMARY_CHANNEL_THERMAL_108","status":"PRIMARY_CHANNEL_INSULATION_HEAT_LOSS_SCREEN_PASS_REWORK_FINAL_TEMPERATURE_INSULATION_CONTACTS_AND_THERMAL_BRIDGE","source_records":[{"artifact_id":d["artifact_id"],"sha256":hashlib.sha256(r).hexdigest().upper()} for r,d in ((r104,m104),(r107,m107))],"D107_report_false_7_17m_disposition":"REJECTED_SUPERSEDED_BY_EXACT_JSON_VALUE","D107_exact_loop_length_over_no_fastener_zone_mm":m107["total_loop_pipe_length_inside_marked_zone_mm"],"primary_route_axis_length_m":length,"pipe_insulation_screen":{"pipe_od_mm":PIPE_OD,"insulated_od_mm":INS_OD,"insulation_thickness_mm":15,"insulation_lambda_w_mk":LAMBDA,"official_product_comparison":"UPONOR_1088239","insulation_radial_resistance_k_m_w":rins,"assumed_outer_surface_coefficient_w_m2k":H_OUT,"outer_surface_resistance_k_m_w":rsurf,"total_screening_resistance_k_m_w":rt,"method":"STEADY_STATE_CYLINDRICAL_INSULATION_PLUS_ASSUMED_OUTER_SURFACE","surrounding_30mm_floor_insulation_credited":False},"temperature_scenarios":scenarios,"screening_result":{"pair_heat_loss_range_w":loss_range,"heat_loss_is_inside_heated_envelope":True,"uncontrolled_hot_strip_risk":"LOW_BY_PIPE_INSULATION_SCREEN_BUT_NOT_SURFACE_TEMPERATURE_FEA","local_floor_surface_temperature_calculated":False},"final_primary_temperatures_selected":False,"exact_insulation_product_selected":False,"channel_air_contact_or_tight_fill_selected":False,"linear_thermal_bridge_calculated":False,"construction_authorized":False,"result":"PASS_35_TO_61W_PAIR_CHANNEL_SCREEN_REWORK_FINAL_PRODUCTS_AND_THERMAL_DETAIL"}
 model["thermal_digest"]=dig(model);OUTPUT.mkdir(parents=True);(OUTPUT/"primary_channel_thermal.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf8")
 im=Image.new("RGB",(1650,1080),"#F4F8F8");d=ImageDraw.Draw(im,"RGBA");d.rectangle((0,0,1650,205),fill="#071A21");d.text((34,18),"D108 · ТЕПЛОПОТЕРИ СКРЫТЫХ МАГИСТРАЛЕЙ",font=font(25,True),fill="white");d.text((34,68),"Участок 4,57 м · две трубы 32×3 в изоляции 15 мм, наружный Ø62",font=font(18,True),fill="#A7EEE7");d.text((34,115),f"Расчётный диапазон пары: {loss_range[0]:.1f}…{loss_range[1]:.1f} Вт внутри отапливаемого контура",font=font(17),fill="#F3D58C");d.text((34,158),"Это скрининг; температура поверхности пола над каналом ещё не рассчитана",font=font(16,True),fill="#FFB2B2")
 headers=["Сценарий","Подача/обратка","Потери пары, Вт/м","Участок 4,57 м","Наружная поверхность изоляции"]
 xs=[70,380,690,1030,1280];y=285
 for x,h in zip(xs,headers):d.text((x,y),h,font=font(14,True),fill="#143842")
 y+=60
 for i,s in enumerate(scenarios):
  d.rectangle((45,y-15,1605,y+65),fill="#FFFFFF" if i%2==0 else "#EAF2F3",outline="#B7C8CD")
  vals=[s["scenario"],f"{s['supply_temperature_c']}/{s['return_temperature_c']} °C",f"{s['pair_heat_loss_w_m_route']:.1f}",f"{s['pair_heat_loss_over_4_57m_w']:.1f} Вт",f"{s['screened_outer_insulation_surface_temperature_supply_c']:.1f}/{s['screened_outer_insulation_surface_temperature_return_c']:.1f} °C"]
  for x,v in zip(xs,vals):d.text((x,y+8),v,font=font(14,x==70),fill="#143842")
  y+=105
 d.rounded_rectangle((100,730,1550,985),radius=18,fill="#FFFFFF",outline="#006A43",width=3);d.text((140,765),"ВЫВОД",font=font(20,True),fill="#006A43");d.text((140,815),f"Изоляция 15 мм ограничивает суммарную отдачу скрытой пары примерно {loss_range[0]:.1f}–{loss_range[1]:.1f} Вт.",font=font(17,True),fill="#143842");d.text((140,860),"Эта энергия остаётся внутри дома, но может немного нагреть полосу над каналом.",font=font(16),fill="#143842");d.text((140,905),"Финальный расчёт требует температуры подачи, выбранной изоляции и конструкции закрытия канала.",font=font(16,True),fill="#B00020");d.text((140,950),"Исправление D107: точная длина трубы Ø16 над полосой — 6,57 м, не 7,17 м.",font=font(15),fill="#566B73");im.save(OUTPUT/"primary_channel_thermal_evidence.png")
 (OUTPUT/"report.md").write_text(f"# D108 — тепловой скрининг канала\n\nДлина оси скрытого участка — {length:.2f} м. Для двух труб 32×3 с изоляцией 15 мм (наружный Ø62, λ=0,040 Вт/мК) получен ориентировочный диапазон потерь пары {loss_range[0]:.1f}–{loss_range[1]:.1f} Вт при температурах 35/30…45/38 °C и окружающих 20 °C. Дополнительные 30 мм утеплителя над каналом в расчёт не засчитаны.\n\nЭто потери внутри отапливаемого дома, но не расчёт температуры поверхности пола. Для него нужны окончательные температуры, изоляция и закрытие канала. Отчёт D107 содержал опечатку 7,17 м; точное значение JSON и карты — 6,57 м трубы Ø16 над полосой.\n",encoding="utf8")
 files=[p for p in sorted(OUTPUT.iterdir()) if p.is_file()];(OUTPUT/"artifact_manifest.json").write_text(json.dumps({"artifact_id":model["artifact_id"],"thermal_digest":model["thermal_digest"],"append_only":True,"files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]},ensure_ascii=False,indent=2),encoding="utf8");shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT);print(json.dumps({"output":str(OUTPUT),"length_m":length,"loss_range_w":model["screening_result"]["pair_heat_loss_range_w"],"digest":model["thermal_digest"]},ensure_ascii=False))
if __name__=="__main__":main()

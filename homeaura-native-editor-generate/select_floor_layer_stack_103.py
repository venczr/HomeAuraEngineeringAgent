from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT=Path(r"C:\AI\HomeAuraEngineeringAgent")
BASE=ROOT/"homeaura-native-editor"/"examples"/"proposals"
SOURCE=BASE/"HA_TWO_FLOOR_OWNER_FLOOR_BUILDUP_100"/"owner_floor_build_up.json"
OUTPUT=BASE/"HA_TWO_FLOOR_FLOOR_LAYER_STACK_103"
PACKAGE=BASE/"packages"/"HA_TWO_FLOOR_FLOOR_LAYER_STACK_103.zip"

AVAILABLE_MM=70.0
PIPE_OD_MM=16.0
DESIGN_COVER_MM=35.0
SCREED_TOTAL_MM=PIPE_OD_MM+DESIGN_COVER_MM
FINISH_ALLOWANCE_MM=AVAILABLE_MM-SCREED_TOTAL_MM
STANDARD_DOMESTIC_TOTAL_SCREED_MM=65.0


def font(size:int,bold:bool=False):
    return ImageFont.truetype(str(Path(r"C:\Windows\Fonts")/("seguisb.ttf" if bold else "segoeui.ttf")),size)


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def digest(v:object)->str:
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest().upper()


def main():
    if OUTPUT.exists() or PACKAGE.exists(): raise FileExistsError("D103 is append-only")
    raw=SOURCE.read_bytes(); source=json.loads(raw.decode("utf-8"))
    model={
        "schema":"homeaura-floor-layer-stack-0.1",
        "artifact_id":"HA_TWO_FLOOR_FLOOR_LAYER_STACK_103",
        "status":"70MM_WET_FLOOR_STACK_DESIGN_BASIS_PASS_REWORK_SCREEED_PRODUCT_LOAD_FINISH_AND_EXPANSION_JOINTS",
        "source_artifact_id":source["artifact_id"],
        "source_sha256":hashlib.sha256(raw).hexdigest().upper(),
        "applies_to":["FLOOR_1","ATTIC_FLOOR_2"],
        "available_height_above_installed_insulation_mm":AVAILABLE_MM,
        "loop_pipe":{
            "design_basis":"UPONOR_COMFORT_PIPE_PLUS_16X2",
            "outer_diameter_mm":PIPE_OD_MM,
            "official_example_part_number":"1062046",
            "official_product_url":"https://www.uponor.com/en-en/s/uponor-comfort-pipe-plus-16x2-0-640m-1062046",
            "product_length_and_local_article_not_procurement_selection":True,
        },
        "selected_layer_design_basis":{
            "system":"WET_FLOW_OR_CALCIUM_SULPHATE_SCREEED_OVER_16MM_PIPE",
            "pipe_axis_above_insulation_mm":PIPE_OD_MM/2,
            "pipe_top_above_insulation_mm":PIPE_OD_MM,
            "design_screed_cover_above_pipe_mm":DESIGN_COVER_MM,
            "total_screed_from_insulation_top_mm":SCREED_TOTAL_MM,
            "remaining_finish_adhesive_underlay_allowance_mm":FINISH_ALLOWANCE_MM,
            "height_reconciliation_mm":SCREED_TOTAL_MM+FINISH_ALLOWANCE_MM,
            "fits_available_70mm":SCREED_TOTAL_MM<=AVAILABLE_MM,
            "load_scope":"OFFICIAL_35MM_COVER_REFERENCE_FOR_MAX_SURFACE_LOAD_UP_TO_2_KN_M2_PENDING_PROJECT_CONFIRMATION",
        },
        "official_method_basis":{
            "document":"UPONOR_UNDERFLOOR_HEATING_COOLING_PLANNING_INFORMATION_1186660_V1",
            "url":"https://brandportal.uponor.com/m/7187327a41365ace/original/TI-planning-principles-UFHC-EN-1186660-v1.pdf",
            "official_cover_reference_mm":35,
            "official_reference_scope":"MAX_SURFACE_LOAD_LE_2_KN_M2_EL_LE_1KN_DIN18560_TABLE1",
            "lower_cover_requires_manufacturer_agreement":True,
            "screed_manufacturer_must_confirm_strength_thickness_joints_and_heating_protocol":True,
            "accessed_date":"2026-08-13",
        },
        "standard_sand_cement_comparison":{
            "official_uponor_uk_domestic_total_screed_depth_over_insulation_mm":STANDARD_DOMESTIC_TOTAL_SCREED_MM,
            "remaining_finish_allowance_mm":AVAILABLE_MM-STANDARD_DOMESTIC_TOTAL_SCREED_MM,
            "general_finish_flexibility":"LOW_ONLY_5MM_REMAINS",
            "selected_as_default":False,
            "source_url":"https://www.uponor.com/getmedia/55d4b2f6-778d-435d-9167-0e27ea46a9eb/ufh-installation-guide?disposition=attachment&sitename=UK",
        },
        "finish_examples_within_19mm_allowance_are_not_product_approvals":True,
        "insulation_compressive_grade_verified":False,
        "screed_product_selected":False,
        "final_floor_finish_selected":False,
        "design_surface_load_confirmed":False,
        "movement_and_expansion_joint_layout_published":False,
        "pressure_and_function_heating_protocol_published":False,
        "construction_authorized":False,
        "result":"PASS_51MM_SCREEED_PLUS_19MM_FINISH_DESIGN_BASIS_REWORK_MATERIAL_ENGINEER_AND_FINISH_SELECTION",
    }
    model["layer_stack_digest"]=digest(model)
    OUTPUT.mkdir(parents=True)
    (OUTPUT/"floor_layer_stack.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")

    im=Image.new("RGB",(1700,1150),"#F4F8F8"); d=ImageDraw.Draw(im,"RGBA")
    d.rectangle((0,0,1700,210),fill="#071A21")
    d.text((34,18),"D103 · РАБОЧИЙ ПИРОГ ТЁПЛОГО ПОЛА В 70 ММ",font=font(25,True),fill="white")
    d.text((34,68),"Труба Ø16 + 35 мм покрытия стяжкой = 51 мм · остаток на чистовой слой 19 мм",font=font(18,True),fill="#A7EEE7")
    d.text((34,116),"Для обоих этажей · жидкая/кальций-сульфатная стяжка как проектная основа",font=font(16),fill="#F3D58C")
    d.text((34,160),"Марка смеси, нагрузка, швы и финиш пока не утверждены",font=font(17,True),fill="#FFB2B2")
    x0,x1=260,1440; base_y=930; scale=9
    d.rectangle((x0,base_y,x1,base_y+70),fill="#F5D76E",outline="#B58C00",width=3)
    d.text((x0+25,base_y+20),"УЖЕ УЛОЖЕННЫЙ УТЕПЛИТЕЛЬ",font=font(15,True),fill="#5C4500")
    screed_top=base_y-int(SCREED_TOTAL_MM*scale); finish_top=screed_top-int(FINISH_ALLOWANCE_MM*scale)
    d.rectangle((x0,screed_top,x1,base_y),fill="#CCD5D8",outline="#607D84",width=3)
    d.rectangle((x0,finish_top,x1,screed_top),fill="#D9B38C",outline="#7A4E2D",width=3)
    pipe_cy=base_y-int(PIPE_OD_MM/2*scale); pipe_r=int(PIPE_OD_MM/2*scale)
    d.ellipse((760-pipe_r,pipe_cy-pipe_r,760+pipe_r,pipe_cy+pipe_r),fill="#D84315",outline="white",width=4)
    d.text((840,pipe_cy-16),"ПЕТЛЯ Ø16",font=font(16,True),fill="#B00020")
    d.text((x0+25,screed_top+20),"СТЯЖКА 51 ММ ОТ УТЕПЛИТЕЛЯ",font=font(16,True),fill="#143842")
    d.text((x0+25,finish_top+30),"ФИНИШ + КЛЕЙ/ПОДЛОЖКА · РЕЗЕРВ 19 ММ",font=font(15,True),fill="#4C2C18")
    d.line((1510,finish_top,1510,base_y),fill="#247BA0",width=3)
    d.text((1530,(finish_top+base_y)//2-15),"70 мм",font=font(18,True),fill="#247BA0")
    d.rounded_rectangle((120,1010,1580,1100),radius=14,fill="#FFF0F0",outline="#B00020",width=3)
    d.text((150,1032),"35 мм — официальный расчётный ориентир при ограниченной нагрузке, а не разрешение лить любую смесь толщиной 51 мм.",font=font(15,True),fill="#B00020")
    d.text((150,1068),"До работ смесь и финиш должен подтвердить производитель/проектировщик стяжки.",font=font(15),fill="#143842")
    im.save(OUTPUT/"floor_layer_stack_evidence.png")

    (OUTPUT/"report.md").write_text(
        "# D103 — рабочий пирог тёплого пола\n\n"
        "В доступных 70 мм принят проектный вариант: труба Ø16 на утеплителе, 35 мм стяжки над верхом трубы, всего 51 мм стяжки от утеплителя и 19 мм на клей/подложку/чистовое покрытие. Он применяется как основа для обоих этажей.\n\n"
        "Официальная информация Uponor приводит 35 мм покрытия для нагрузки до 2 кН/м²; меньшие толщины требуют отдельного согласования. Марка жидкой или кальций-сульфатной смеси, фактическая нагрузка, прочность утеплителя, швы и протокол прогрева пока не выбраны. Обычная бытовая песчано-цементная стяжка 65 мм оставила бы лишь 5 мм на покрытие и поэтому не является вариантом по умолчанию.\n",
        encoding="utf-8",
    )
    files=[p for p in sorted(OUTPUT.iterdir()) if p.is_file()]
    (OUTPUT/"artifact_manifest.json").write_text(json.dumps({"artifact_id":model["artifact_id"],"layer_stack_digest":model["layer_stack_digest"],"append_only":True,"files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in files]},ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.make_archive(str(PACKAGE.with_suffix("")),"zip",OUTPUT)
    print(json.dumps({"output":str(OUTPUT),"screed_mm":SCREED_TOTAL_MM,"finish_allowance_mm":FINISH_ALLOWANCE_MM,"digest":model["layer_stack_digest"]},ensure_ascii=False))


if __name__=="__main__": main()

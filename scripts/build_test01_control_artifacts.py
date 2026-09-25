from __future__ import annotations
import json
from pathlib import Path
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/'projects/Test_01/exports/ufh_generator_package'
PUBLIC=ROOT/'homeaura-editor/public/plans'
SOURCE=ROOT/'projects/Test_01/engineering/source_documents'
TARGET=PKG/'control_rooms'
TARGET.mkdir(parents=True,exist_ok=True)
project=json.loads((PUBLIC/'test01-project.json').read_text(encoding='utf-8'))
rooms={r['label'].split(';')[0].strip():r for r in project['rooms']}
selection={
 'ROOM_7': next(r for r in project['rooms'] if r['label'].startswith('7 /')),
 'ROOM_4': next(r for r in project['rooms'] if r['label'].startswith('4 /')),
 'ROOM_3': next(r for r in project['rooms'] if r['label'].startswith('3 /')),
 'ROOM_12': next(r for r in project['rooms'] if r['label'].startswith('12 /')),
 'ROOM_2': next(r for r in project['rooms'] if r['label'].startswith('2 /')),
}
for key,room in selection.items():
    floor=room['floor']; source=SOURCE/('Test_01_floor_1_plan.pdf' if floor=='FLOOR_1_PLAN' else 'Test_01_attic_plan.pdf')
    doc=pymupdf.open(str(source)); page=doc[0]
    routes=room.get('routes',[])
    for idx,route in enumerate(routes,1):
        pts=[pymupdf.Point(float(x),float(y)) for x,y in route]
        if len(pts)<2: continue
        mid=max(1,len(pts)//2)
        page.draw_polyline(pts[:mid+1],color=(0.85,0.08,0.12),width=1.8,overlay=True)
        page.draw_polyline(pts[mid:],color=(0.08,0.25,0.85),width=1.8,overlay=True)
        page.draw_circle(pts[0],radius=3,color=(0.1,0.6,0.2),fill=(0.1,0.6,0.2),overlay=True)
        page.draw_circle(pts[-1],radius=3,color=(0.45,0.1,0.7),fill=(0.45,0.1,0.7),overlay=True)
        page.insert_text((pts[0].x+4,pts[0].y-4),room.get('route_ids',['route'])[idx-1],fontsize=6,color=(0.1,0.35,0.1),overlay=True)
    page.insert_text((18,24),f"{room['label']} | {room.get('strategy','UNRESOLVED')}",fontsize=9,color=(0.75,0.2,0.05),overlay=True)
    page.insert_text((18,36),f"lengths: {', '.join(f'{v/1000:.1f} m' for v in room.get('lengths_mm',[])) or 'none'} | MANIFOLD_CONNECTED=UNVERIFIED",fontsize=7,color=(0.75,0.2,0.05),overlay=True)
    boundary=room.get('boundary') or []
    if boundary:
        xs=[p[0] for p in boundary]; ys=[p[1] for p in boundary]
        rect=pymupdf.Rect(min(xs)-25,min(ys)-25,max(xs)+25,max(ys)+25) & page.rect
        page.set_cropbox(rect)
    out_pdf=TARGET/f'{key}.pdf'; doc.save(str(out_pdf),garbage=4,deflate=True); doc.close()
    doc2=pymupdf.open(str(out_pdf)); pix=doc2[0].get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False); pix.save(str(TARGET/f'{key}.png')); doc2.close()
    (TARGET/f'{key}.json').write_text(json.dumps({k:room.get(k) for k in ('id','label','floor','strategy','strategy_reason','route_ids','lengths_mm','route_validation','diagnostics')},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(TARGET),'rooms':list(selection)},ensure_ascii=False))

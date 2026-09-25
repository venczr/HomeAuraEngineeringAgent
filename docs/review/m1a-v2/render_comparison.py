import json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT=Path(__file__).resolve().parent
def points(p):
    if p['kind']=='line':return [p['a'],p['b']]
    return [[p['c'][0]+p['r']*math.cos(p['start']+p['sweep']*i/100),p['c'][1]+p['r']*math.sin(p['start']+p['sweep']*i/100)] for i in range(101)]
def draw(ax,curves,title,zones=False):
    ax.add_patch(Rectangle((0,0),4000,3000,facecolor='white',edgecolor='#111827',lw=1.5))
    if zones:
        for p in curves:
            if p['kind']=='arc':
                q=points(p);xs=[v[0] for v in q];ys=[v[1] for v in q]
                ax.add_patch(Rectangle((min(xs)-100,min(ys)-100),max(xs)-min(xs)+200,max(ys)-min(ys)+200,facecolor='#fbbf24',alpha=.13,edgecolor='#d97706',lw=.4))
    signs=[math.copysign(1,p['sweep']) for p in curves if p['kind']=='arc'];first=signs[0];color='#c24136'
    for p in curves:
        if p['kind']=='arc' and math.copysign(1,p['sweep'])!=first:color='#2563a6'
        q=points(p);ax.plot([v[0] for v in q],[v[1] for v in q],color=color,lw=1.4)
    ax.scatter([200,3800],[100,2900],s=36,color=['#16a34a','#111827'],zorder=5)
    ax.set_xlim(-100,4100);ax.set_ylim(3100,-100);ax.set_aspect('equal');ax.set_title(title,fontsize=11,pad=12)
    ax.set_xticks([0,2000,4000]);ax.set_yticks([0,1500,3000]);ax.tick_params(labelsize=8)
fig,axes=plt.subplots(1,3,figsize=(15,4.9))
for ax,name,title in zip(axes,['ufh-analytic-original','reference','ufh-adapted'],['UFH Designer: FAIL\nконцы и покрытие','Ручная улитка: synthetic PASS\n58,20 м · R100 · фиксированные концы','Попытка адаптации: FAIL\nналожение проходов']):
    data=json.loads((ROOT/(name+'.json')).read_text());draw(ax,data['curves'],title)
fig.suptitle('HomeAura M1a · один неизменный контракт 4000 × 3000 мм',fontsize=15)
fig.text(.5,.035,'Зелёная / чёрная точки — требуемые концы. Проверка синтетическая; экспорт в CAD запрещён.',ha='center',fontsize=10)
fig.tight_layout(rect=[0,.07,1,.92]);fig.savefig(ROOT/'comparison.png',dpi=150);fig.savefig(ROOT/'comparison.svg');plt.close(fig)
fig,ax=plt.subplots(figsize=(9,7));draw(ax,json.loads((ROOT/'reference.json').read_text())['curves'],'Ручной эталон: объявленные BOX-зоны поворотов',True)
fig.text(.5,.02,'Жёлтый: bbox дуги + 100 мм. Ориентационные полосы прямых в этой схеме не показаны.',ha='center',fontsize=9)
fig.tight_layout(rect=[0,.05,1,1]);fig.savefig(ROOT/'reference-turn-zones.png',dpi=140)

import json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle
root=Path(__file__).resolve().parent
f=json.loads((root/'fixtures.json').read_text());L=json.loads((root/'L-two-circuits.json').read_text());u=json.loads((root/'L-ufh-candidate.json').read_text())
def trace(ax,curves,color):
    for p in curves:
        if p['kind']=='line':q=[p['a'],p['b']]
        else:q=[[p['c'][0]+p['r']*math.cos(p['start']+p['sweep']*i/90),p['c'][1]+p['r']*math.sin(p['start']+p['sweep']*i/90)] for i in range(91)]
        ax.plot([v[0] for v in q],[v[1] for v in q],color=color,lw=1.35)
fig,axes=plt.subplots(1,3,figsize=(14,7))
for ax in axes[:2]:
    ax.add_patch(Polygon(f['L_room']['outline'],closed=True,facecolor='#fafafa',edgecolor='#111827',lw=1.7));ax.set_aspect('equal');ax.set_xlim(-100,4100);ax.set_ylim(7100,-100);ax.tick_params(labelsize=8)
trace(axes[0],u['curves'],'#b45309');axes[0].set_title('Одна L-улитка UFH: FAIL\n95,45 м > 80 м; есть пробелы',fontsize=11)
for c,col in zip(L['curves'],['#c24136','#2563a6']):trace(axes[1],c,col)
axes[1].plot([0,3000],[3000,3000],ls='--',color='#6b7280',lw=1);axes[1].set_title('Г-комната: 2 BODY-контура\nпо 58,20 м · synthetic PASS',fontsize=11)
d=json.loads((root/'door900.json').read_text());ax=axes[2]
ax.add_patch(Rectangle((4000,0),200,1050,facecolor='#737373'));ax.add_patch(Rectangle((4000,1950),200,1050,facecolor='#737373'))
for c,col in zip(d['curves'],['#c24136','#2563a6']):trace(ax,c,col)
ax.annotate('Проём 900 мм',xy=(4100,1100),xytext=(4400,1030),arrowprops={'arrowstyle':'->'},fontsize=9)
ax.annotate('Оси через 200 мм',xy=(4050,1500),xytext=(4350,1780),arrowprops={'arrowstyle':'->'},fontsize=9)
ax.set_title('Дверь: отдельная пара подводок\nR100 · проход через стену 200 мм',fontsize=11);ax.set_xlim(3100,4900);ax.set_ylim(2200,500);ax.set_aspect('equal');ax.tick_params(labelsize=8)
fig.suptitle('HomeAura · Г-образная комната и дверной проход',fontsize=16)
fig.text(.5,.045,'Два BODY-контура и дверная пара проверены отдельно. Полного соединения с коллектором пока нет.',ha='center',fontsize=10)
fig.tight_layout(rect=[0,.09,1,.93]);fig.savefig(root/'complex-comparison.png',dpi=160,bbox_inches='tight');fig.savefig(root/'complex-comparison.svg',bbox_inches='tight')

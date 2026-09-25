import json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=Path(__file__).resolve().parent
def plot(ax,curves):
    for p in curves:
        if p['kind']=='line':q=[p['a'],p['b']]
        else:q=[[p['c'][0]+p['r']*math.cos(p['start']+p['sweep']*i/150),p['c'][1]+p['r']*math.sin(p['start']+p['sweep']*i/150)] for i in range(151)]
        ax.plot([v[0] for v in q],[v[1] for v in q],color='#1765a1',lw=2)
fig,(a,b)=plt.subplots(1,2,figsize=(12,5))
candidate=json.loads((root/'terminal-transition-candidate.json').read_text())
plot(a,candidate['curves']);a.set_xlim(0,750);a.set_ylim(600,0);a.set_aspect('equal');a.set_title('Угол: max-distance200 достигается,\nно шаг местами 20 мм — НЕ ПРИНЯТО',fontsize=11)
a.scatter([200],[100],color='green',s=30);a.annotate('20 мм между проходами',(280,110),(410,65),arrowprops={'arrowstyle':'->'},fontsize=9)
omega=json.loads((root/'omega-u-candidate.json').read_text())
plot(b,omega['curves']);b.add_patch(Rectangle((0,-30),173.27379053088816,160,facecolor='#fbbf24',alpha=.15,edgecolor='#d97706'))
b.set_xlim(-120,220);b.set_ylim(160,-60);b.set_aspect('equal');b.set_title('Изолированный разворот p100/R80\n3 дуги; средняя 251,32°',fontsize=11)
b.annotate('100 мм',(0,50),(-100,55),fontsize=10);b.annotate('173,27 мм вперёд',(173.27,50),(20,150),arrowprops={'arrowstyle':'->'},fontsize=9)
for ax in (a,b):ax.tick_params(labelsize=9);ax.set_xlabel('мм')
fig.suptitle('M2 preflight: геометрические эксперименты, не готовая раскладка',fontsize=14)
fig.tight_layout(rect=[0,.04,1,.9]);fig.savefig(root/'preflight.png',dpi=150,bbox_inches='tight');fig.savefig(root/'preflight.svg',bbox_inches='tight')

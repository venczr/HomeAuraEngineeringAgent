import json,math
import numpy as np
import shapely
from shapely.geometry import Polygon
from run import ROOT,geometry,plen,physical,E,ends,tangent
data=json.loads((ROOT/'L-ufh-candidate.json').read_text());curves=data['curves'];room=Polygon(data['outline']);g=geometry(curves)
x,y=np.meshgrid(np.arange(0,4000,25),np.arange(0,7000,25));x=x.ravel();y=y.ravel();mask=shapely.intersects(shapely.box(x,y,x+25,y+25),room)
sampled=float(max(shapely.distance(shapely.points(x[mask]+12.5,y[mask]+12.5),g)))
length=sum(plen(p) for p in curves)
checks={'length80m':'PASS' if length<=80000 else 'FAIL','inside_actual_L':'PASS' if room.covers(g) else 'FAIL','G1':'PASS' if all(math.dist(tangent(a,True),tangent(b))<1e-6 for a,b in zip(curves,curves[1:])) else 'FAIL','R80':'PASS' if all(p['r']>=80 for p in curves if p['kind']=='arc') else 'FAIL','OD':physical(curves,{'pipe_od_mm':16})[0],'max_distance250':'FAIL' if sampled-25/math.sqrt(2)-E>250 else 'PASS' if sampled+25/math.sqrt(2)+E<=250 else 'INDETERMINATE','fixed_terminal_contract':'INDETERMINATE','L_morphology':'INDETERMINATE'}
report={'status':'FAIL' if 'FAIL' in checks.values() else 'INDETERMINATE','export_allowed':False,'checks':checks,'metrics':{'length_mm':length,'coverage_lower_bound':room.intersection(g.buffer(250-E,quad_segs=64)).area/room.area,'sampled_max_distance':sampled,'domain_max_distance_lower_bound':sampled-25/math.sqrt(2)-E,'max_distance_upper_bound':sampled+25/math.sqrt(2)+E},'note':'One circuit vs explicit80m limit. No inferred terminal contract and no claim of general L morphology certification. Lower bound accounts for retained grid centres outside the domain.'}
(ROOT/'L-ufh-check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

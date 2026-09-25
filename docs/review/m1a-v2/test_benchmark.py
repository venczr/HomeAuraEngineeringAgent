import copy,json,math,unittest
from pathlib import Path
from reference import build,rounded,SUPPLY,RETURN
from validator import validate,physical,ends,pitch_check
ROOT=Path(__file__).resolve().parent
F=json.loads((ROOT/'fixture.json').read_text())
RESULTS={}
def run_case(name,curves,f=F):
    report=validate(curves,f);RESULTS[name]=report
    (ROOT/(name+'.json')).write_text(json.dumps({'curves':curves,'fixture':f,'report':report},indent=2),encoding='utf8')
    return report
def transform(curves,f,m,offset):
    def point(q):return [sum(m[i][j]*q[j] for j in range(2))+offset[i] for i in range(2)]
    def vec(q):return [sum(m[i][j]*q[j] for j in range(2)) for i in range(2)]
    det=m[0][0]*m[1][1]-m[0][1]*m[1][0];out=[]
    for p in curves:
        if p['kind']=='line':out.append({'kind':'line','a':point(p['a']),'b':point(p['b'])})
        else:
            c=point(p['c']);a=point(ends(p)[0]);out.append({'kind':'arc','c':c,'r':p['r'],'start':math.atan2(a[1]-c[1],a[0]-c[0]),'sweep':det*p['sweep']})
    f=copy.deepcopy(f)
    f['polygon']=[point(q) for q in f['polygon']]
    for k in ['supply','return']:f[k]=point(f[k])
    for k in ['supply_traversal_tangent','return_traversal_tangent']:f[k]=vec(f[k])
    return out,f
class Benchmark(unittest.TestCase):
    def test_01_positive(self):
        r=run_case('reference',build());self.assertEqual(r['status'],'PASS');self.assertFalse(r['export_allowed'])
    def test_02_shifted_end(self):
        p=build();p[0]['a'][0]+=10
        self.assertEqual(run_case('shifted_endpoint',p)['checks']['endpoints'],'FAIL')
    def test_03_radius_isolated(self):
        p=rounded(SUPPLY,50)+[build()[28]]+rounded(RETURN,50)
        r=run_case('radius50_continuous',p)
        self.assertEqual(r['checks']['radius'],'FAIL');self.assertEqual(r['checks']['continuity'],'PASS');self.assertEqual(r['checks']['tangency'],'PASS')
    def test_04_duplicate(self):
        p=build();p.insert(1,copy.deepcopy(p[0]));self.assertEqual(run_case('duplicate',p)['status'],'FAIL')
    def test_05_broken_short(self):
        p=build();p[0]['b'][0]-=20;self.assertEqual(run_case('broken_short',p)['checks']['continuity'],'FAIL')
    def test_06_hole(self):
        f=copy.deepcopy(F);f['holes']=[[[1140,80],[1160,80],[1160,120],[1140,120]]]
        self.assertEqual(run_case('thin_obstacle',build(),f)['checks']['wall_clearance'],'FAIL')
    def test_07_arc_collision(self):
        p=build();p[1]['c'][0]+=100;self.assertEqual(run_case('arc_wall_collision',p)['checks']['wall_clearance'],'FAIL')
    def test_08_od_contact_without_axis_intersection(self):
        p=rounded([[200,100],[3900,100],[3900,2700],[100,2700],[100,115],[3000,115]])
        r=run_case('od15_no_axis_crossing',p)
        self.assertEqual(r['checks']['axis_simple'],'PASS');self.assertEqual(r['checks']['continuity'],'PASS');self.assertEqual(r['checks']['tangency'],'PASS');self.assertEqual(r['checks']['pipe_clearance'],'FAIL')
    def test_09_meander_morphology(self):
        p=[]
        for i in range(15):
            y=100+200*i;a,b=([200,y],[3800,y]) if i%2==0 else ([3800,y],[200,y])
            p.append({'kind':'line','a':a,'b':b})
            if i<14:p.append({'kind':'arc','c':[b[0],y+100],'r':100,'start':-math.pi/2,'sweep':math.pi if i%2==0 else -math.pi})
        r=run_case('meander_wrong_morphology',p)
        self.assertEqual(r['checks']['morphology'],'FAIL');self.assertEqual(r['checks']['pipe_clearance'],'PASS')
    def test_10_fake_pitch_evidence(self):
        vertices=copy.deepcopy(SUPPLY)
        vertices[5][0]-=50;vertices[6][0]-=50
        payload={'curves':rounded(vertices)+[build()[28]]+rounded(RETURN),'spacing_segments':[{'distance_mm':200,'status':'PASS'}]}
        r=run_case('pitch150_forged_evidence',payload['curves'])
        (ROOT/'forged-evidence-input.json').write_text(json.dumps(payload,indent=2))
        self.assertEqual(r['checks']['pitch'],'FAIL')
    def test_11_translation(self):
        p,f=transform(build(),F,[[1,0],[0,1]],[1234,-2345]);self.assertEqual(run_case('translated',p,f)['status'],'PASS')
    def test_12_rotation90(self):
        p,f=transform(build(),F,[[0,-1],[1,0]],[5000,2000]);self.assertEqual(run_case('rotated90',p,f)['status'],'PASS')
    def test_13_reflection(self):
        p,f=transform(build(),F,[[-1,0],[0,1]],[4000,0]);self.assertEqual(run_case('reflected',p,f)['status'],'PASS')
    def test_14_indeterminate_clearance_threshold(self):
        p=rounded([[200,100],[3900,100],[3900,2700],[100,2700],[100,116],[3000,116]])
        r=run_case('od16_threshold',p);self.assertEqual(r['checks']['pipe_clearance'],'INDETERMINATE');self.assertFalse(r['export_allowed'])
    def test_15_invalid_diagonal(self):
        p=build();p[0]['a'][1]+=1;self.assertEqual(run_case('diagonal',p)['checks']['orthogonal_line_quarter_half_arc_grammar'],'FAIL')
    def test_16_deterministic(self):
        self.assertEqual(json.dumps(build()),json.dumps(build()))
    def test_17_independent_review_pitch_counterexample(self):
        p=[{'kind':'line','a':[0,y],'b':[1000,y]} for y in [0,600,800]]+[{'kind':'line','a':[500,0],'b':[500,600]}]
        status,metrics=pitch_check(p,200)
        (ROOT/'pitch-review-counterexample.json').write_text(json.dumps({'curves':p,'status':status,'metrics':metrics},indent=2))
        self.assertEqual(status,'FAIL')
if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Benchmark)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (ROOT/'test-summary.json').write_text(json.dumps({'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'cases':{k:{'status':v['status'],'checks':v['checks']} for k,v in RESULTS.items()}},indent=2))
    raise SystemExit(not result.wasSuccessful())

import copy,json,unittest
from pathlib import Path
from template import generate
ROOT=Path(__file__).resolve().parent
F=json.loads((ROOT/'fixture.json').read_text())
class Template(unittest.TestCase):
    def test_supported_widths(self):
        result={}
        for width in [4000,4000.001,4250,4500,4750,4999.999,5000]:
            f=copy.deepcopy(F);f['polygon'][1][0]=width;f['polygon'][2][0]=width;f['return'][0]=width-200
            r=generate(f);result[str(width)]={'status':r['status'],'report':r.get('report')}
            self.assertEqual(r['status'],'ValidSynthetic',str(width))
        (ROOT/'template-width-results.json').write_text(json.dumps(result,indent=2))
    def test_outside_domain_is_unsupported(self):
        for width in [3999.999,5000.001]:
            f=copy.deepcopy(F);f['polygon'][1][0]=width;f['polygon'][2][0]=width;f['return'][0]=width-200
            self.assertEqual(generate(f)['status'],'Unsupported')
    def test_wrong_endpoint_not_moved(self):
        f=copy.deepcopy(F);f['return'][0]-=1;before=copy.deepcopy(f)
        self.assertEqual(generate(f)['status'],'Unsupported');self.assertEqual(f,before)
    def test_actual_length_gate(self):
        f=copy.deepcopy(F);f['maximum_length_mm']=58000
        self.assertEqual(generate(f)['status'],'NoFeasibleCandidateFound')
    def test_repeat_output(self):
        self.assertEqual(generate(F)['curves'],generate(F)['curves'])
if __name__=='__main__':unittest.main(verbosity=2)

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class SkillCLITests(unittest.TestCase):
    def run_request(self,request):
        work=ROOT/'data/work'
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work,prefix='skill-check-') as folder:
            path=Path(folder)/'request.json'
            path.write_text(json.dumps(request,ensure_ascii=False),encoding='utf-8')
            result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/advise.py'),'--request',str(path),'--compact'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
            return result.returncode,json.loads(result.stdout)

    def test_structured_evaluation_preserves_units_and_evidence(self):
        status,result=self.run_request({'action':'evaluate','frame':'sour','recipe':[{'name':'金酒','amount':45,'unit':'ml'},{'name':'青柠汁','amount':25,'unit':'ml'},{'name':'糖浆','amount':20,'unit':'ml'}],'method':'shake'})
        self.assertEqual(status,0)
        self.assertEqual(result['score'],100)
        self.assertTrue(result['sources'])
        self.assertEqual(result['items'][0]['canonical_id'],'gin')

    def test_structured_completion_and_brand_ambiguity(self):
        status,result=self.run_request({'action':'complete','frame':'negroni','recipe':[{'name':'金酒','amount':30,'unit':'ml'}],'pantry':['金巴利','马天尼红']})
        self.assertEqual(status,0)
        self.assertEqual(result['shopping'],[])
        self.assertEqual(result['recipe'][0]['amount'],30)
        status,result=self.run_request({'action':'complete','frame':'negroni','recipe':['马天尼']})
        self.assertEqual(status,0)
        self.assertTrue(result['blocked'])
        self.assertEqual(result['unresolved'][0]['status'],'ambiguous')

    def test_unsupported_preference_field_not_silently_ignored(self):
        status,result=self.run_request({'action':'complete','frame':'sour','no_shopping':True})
        self.assertEqual(status,1)
        self.assertIn('no_shopping',result['error'])

    def test_literal_user_text_is_not_shell_code(self):
        status,result=self.run_request({'action':'resolve','recipe':[{'name':'神秘酒 $(not-a-command) `quoted` "test"'}]})
        self.assertEqual(status,0)
        self.assertEqual(result['items'][0]['status'],'unknown')

if __name__=='__main__':unittest.main()

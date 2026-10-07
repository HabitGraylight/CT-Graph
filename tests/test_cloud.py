import json
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from api.app import handler
from cloud.preferences import baseline, personalize
from cloud.service import ApiError, advise, private_action
from cocktail import engine
from cocktail.runtime import public_runtime

RECIPE='gin 45 ml, lemon juice 25 ml, simple syrup 20 ml'


class CloudEngineTests(unittest.TestCase):
    def test_public_runtime_never_reads_local_knowledge_or_feedback(self):
        with patch.object(Path,'open',side_effect=AssertionError('Local read')), patch('cocktail.learning.records',side_effect=AssertionError('Local DB')):
            with public_runtime():
                self.assertEqual(engine.corpus(),[])
                self.assertEqual(engine.comparisons(),[])
                self.assertEqual(engine.catalog()['stats']['recipes'],0)
                self.assertEqual(engine.evaluate('sour',RECIPE,'shake')['score'],100)
            result=advise('recommend',{'frame':'sour','recipe':RECIPE,'method':'shake'})
            self.assertEqual(len(result['candidates']),3)

    def test_runtime_restores_local_context(self):
        from cocktail.runtime import PUBLIC_ONLY
        with self.assertRaises(RuntimeError):
            with public_runtime():raise RuntimeError()
        self.assertFalse(PUBLIC_ONLY.get())

    def test_zero_missing_and_frame_conditioning(self):
        profile={'preferences':{'sweet':0}}
        rows=[{'frame':'sour','liking':8,'intensities':{'sweet':4}},
              {'frame':'martini','liking':9,'intensities':{'sweet':10}},
              {'frame':'sour','liking':2,'intensities':{'sweet':10}}]
        result=baseline(profile,rows,'sour')
        self.assertEqual(result['targets']['sweet']['value'],1)
        self.assertEqual(result['targets']['sweet']['samples'],1)
        self.assertIsNone(result['targets']['aroma']['value'])
        self.assertEqual(result['tasted_recipes'],2)

    def test_personal_completion_only_changes_unspecified_amount(self):
        low={'preferences':{'sweet':2}}
        result=advise('complete',{'frame':'sour','recipe':RECIPE},low,[])
        self.assertEqual(next(r for r in result['recipe'] if r['name']=='simple_syrup')['amount'],20)
        less=advise('complete',{'frame':'sour','recipe':'gin 45 ml, lemon juice 25 ml, simple syrup'},low,[])
        ordinary=advise('complete',{'frame':'sour','recipe':'gin 45 ml, lemon juice 25 ml, simple syrup'})
        self.assertLess(less['recipe'][2]['amount'],ordinary['recipe'][2]['amount'])

    def test_cloud_write_uses_authenticated_identity(self):
        from unittest.mock import Mock
        db=Mock();db.request.return_value=[]
        private_action(db,'profile',{'user_id':'attacker-choice','display_name':'Synthetic','preferences':{}},{'id':'verified-id'},'caller-jwt')
        args=db.request.call_args.args
        self.assertEqual(args[2]['user_id'],'verified-id')
        self.assertEqual(args[3],'caller-jwt')

    def test_simulation_cannot_be_submitted_as_tasting(self):
        with self.assertRaises(ApiError):private_action(None,'taste',{'tasted':False,'as_recipe':True},{'id':'x'},'token')
        with self.assertRaises(ApiError):private_action(None,'taste',{'data_kind':'synthetic','tasted':True,'as_recipe':True},{'id':'x'},'token')


class CloudHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),handler)
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.origin='http://127.0.0.1:'+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def request(self,body=None,resource='',origin=None,cookie=None):
        headers={'Content-Type':'application/json','Origin':origin or self.origin}
        if cookie:headers['Cookie']=cookie
        req=Request(self.origin+'/api/app'+resource,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        try:r=urlopen(req)
        except HTTPError as e:r=e
        return r.status,json.loads(r.read()),r.headers

    @patch.dict('os.environ',{},clear=True)
    def test_anonymous_evaluation_works_without_cloud_credentials(self):
        status,data,_=self.request({'action':'evaluate','frame':'sour','recipe':RECIPE,'method':'shake'})
        self.assertEqual(status,200);self.assertEqual(data['score'],100)

    @patch.dict('os.environ',{},clear=True)
    def test_cross_origin_rejected_and_no_private_endpoints(self):
        self.assertEqual(self.request({'action':'evaluate'},origin='https://elsewhere.example')[0],403)
        self.assertEqual(self.request(resource='?resource=history')[0],404)
        self.assertEqual(self.request({'action':'profile','display_name':'Synthetic'})[0],401)

    @patch.dict('os.environ',{},clear=True)
    def test_unconfigured_auth_is_explicit_and_no_store(self):
        status,data,headers=self.request(resource='?resource=state')
        self.assertEqual(status,200);self.assertFalse(data['configured']);self.assertIsNone(data['user'])
        self.assertIn('no-store',headers['Cache-Control'])

    @patch.dict('os.environ',{'APP_ORIGIN':'https://synthetic.example','SUPABASE_URL':'https://synthetic.supabase.co','SUPABASE_PUBLISHABLE_KEY':'synthetic-placeholder'},clear=True)
    @patch('cloud.service.Supabase.request')
    def test_login_returns_only_httponly_session_not_tokens(self,mock):
        mock.return_value={'access_token':'test-access','refresh_token':'test-refresh'}
        status,data,headers=self.request({'action':'login','email':'synthetic@example.invalid','password':'synthetic-pass'},origin='https://synthetic.example')
        self.assertEqual(status,200);self.assertNotIn('access_token',data)
        cookies=headers.get_all('Set-Cookie')
        self.assertEqual(len(cookies),2)
        for c in cookies:
            self.assertIn('HttpOnly',c);self.assertIn('Secure',c);self.assertIn('SameSite=Lax',c);self.assertIn('Path=/api',c)

    @patch.dict('os.environ',{'APP_ORIGIN':'https://synthetic.example','VERCEL':'1'},clear=True)
    def test_wrong_deployment_origin_is_not_accepted(self):
        self.assertEqual(self.request({'action':'evaluate'},origin='https://preview.example')[0],403)


if __name__=='__main__':unittest.main()

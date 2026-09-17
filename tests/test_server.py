import http.client
import json
import threading
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from server import Handler
from cocktail import learning
from cocktail.knowledge import ROOT

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def request(self,path,body=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        connection.request('POST' if body is not None else 'GET',path,json.dumps(body).encode() if body is not None else None,headers or {})
        r=connection.getresponse();status=r.status;data=r.read();connection.close()
        return status,data

    def test_catalog_and_static_page(self):
        status,data=self.request('/api/catalog')
        self.assertEqual(status,200)
        self.assertEqual(len(json.loads(data)['frameworks']),12)
        status,data=self.request('/')
        self.assertEqual(status,200)
        self.assertIn('调酒手记'.encode(),data)

    def test_score_and_completion_api(self):
        status,data=self.request('/api/evaluate',{'frame':'sour','recipe':'金酒45ml，柠檬汁25ml，糖浆20ml','method':'shake'})
        self.assertEqual(status,200);self.assertEqual(json.loads(data)['score'],100)
        status,data=self.request('/api/complete',{'frame':'negroni','recipe':'金酒30ml','pantry':'金巴利、甜红味美思'})
        self.assertEqual(status,200);self.assertEqual(json.loads(data)['shopping'],[])

    def test_invalid_input_and_nonlocal_origins(self):
        status,_=self.request('/api/evaluate',{'frame':'missing','recipe':'gin'})
        self.assertEqual(status,400)
        status,_=self.request('/api/evaluate',{'frame':'sour','recipe':'gin'}, {'Origin':'https://unrelated.example'})
        self.assertEqual(status,403)

    def test_raw_project_files_not_exposed(self):
        status,_=self.request('/data/raw/iba_official/robots.txt')
        self.assertEqual(status,404)
        status,_=self.request('/../README.md')
        self.assertEqual(status,404)

    def test_judge_feedback_and_revision_round_trip(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'data/work') as folder,patch.object(learning,'DB',Path(folder)/'feedback.sqlite'):
            status,data=self.request('/api/judge-catalog')
            self.assertEqual(status,200);self.assertEqual(len(json.loads(data)['dimensions']),7)
            status,data=self.request('/api/feedback',{'frame':'sour','recipe':'gin 45ml, lemon_juice 25ml, simple_syrup 20ml','method':'shake',
                'tasting':{'tasted':True,'descriptors':['too_sweet'],'notes':'isolated synthetic test fixture'}})
            self.assertEqual(status,200);id=json.loads(data)['id']
            status,data=self.request('/api/improve',{'feedback_id':id})
            self.assertEqual(status,200);self.assertEqual(json.loads(data)['change']['after'],17.5)
            status,data=self.request('/api/history')
            self.assertEqual(status,200);self.assertEqual(len(json.loads(data)['trials']),1)
            status,_=self.request('/api/feedback',{'tasting':{'tasted':False,'ratings':{'aroma':9}}})
            self.assertEqual(status,400)

if __name__=='__main__':unittest.main()

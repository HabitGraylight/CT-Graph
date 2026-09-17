"""Run locally: python server.py --port 8765"""
import argparse
import json
import mimetypes
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qs
from cocktail.knowledge import ROOT
from cocktail import engine
from cocktail import judge, learning
from scripts.advise import dispatch

STATIC=ROOT/'web'
class Handler(BaseHTTPRequestHandler):
    def send(self,status,data,content_type='application/json; charset=utf-8'):
        if not isinstance(data,bytes):data=json.dumps(data,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def local_request(self):
        host=self.headers.get('Host','')
        allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        origin=self.headers.get('Origin')
        if host not in allowed or (origin and origin not in {'http://'+h for h in allowed}):
            self.send(403,{'error':'只接受本地页面请求'})
            return False
        return True

    def do_GET(self):
        if not self.local_request():return
        url=urlsplit(self.path)
        if url.path=='/api/catalog':return self.send(200,engine.catalog())
        if url.path=='/api/judge-catalog':return self.send(200,{'dimensions':judge.DIMENSIONS,'descriptors':learning.DESCRIPTORS,**judge.knowledge_status()})
        if url.path=='/api/history':return self.send(200,{'trials':learning.records()})
        if url.path=='/api/knowledge':return self.send(200,judge.inspect_ingredient(parse_qs(url.query).get('name',['lemon_juice'])[0]))
        if url.path=='/api/compare':
            return self.send(200,engine.compare(parse_qs(url.query).get('name',['Negroni'])[0]))
        paths={'/':'index.html','/app.js':'app.js','/judge.js':'judge.js','/style.css':'style.css'}
        if url.path not in paths:return self.send(404,{'error':'页面不存在'})
        path=STATIC/paths[url.path]
        self.send(200,path.read_bytes(),(mimetypes.guess_type(str(path))[0] or 'text/plain')+'; charset=utf-8')

    def do_POST(self):
        if not self.local_request():return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<=0 or size>65536:raise ValueError('请求体大小需在 1–65536 字节之间')
            body=json.loads(self.rfile.read(size))
            if not isinstance(body,dict):raise ValueError('请求需要是 JSON 对象')
            if self.path=='/api/evaluate':
                result=engine.evaluate(body.get('frame'),body.get('recipe',''),body.get('method'),body.get('context'))
            elif self.path=='/api/complete':
                result=engine.complete(body.get('frame'),body.get('recipe',''),body.get('pantry',''),body.get('avoid',''),body.get('preference','balanced'),body.get('context'),body.get('taster','local'))
            elif self.path=='/api/pantry':result=engine.pantry_matches(body.get('pantry',''))
            elif self.path in {'/api/judge','/api/improve','/api/feedback','/api/profile','/api/knowledge_note'}:
                result=dispatch({**body,'action':self.path.removeprefix('/api/')})
            else:return self.send(404,{'error':'接口不存在'})
            self.send(200,result)
        except (ValueError,TypeError,KeyError) as e:
            self.send(400,{'error':str(e)})

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--port',type=int,default=8765)
    args=p.parse_args()
    if not (ROOT/'data/aligned/recipes.jsonl').exists():
        raise SystemExit('请先运行 python scripts/align_data.py')
    engine.corpus()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Cocktail Atelier: http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()

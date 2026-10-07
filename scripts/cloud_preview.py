"""Preview the Vercel handler and static UI on loopback. Does not import local data."""
import argparse
import mimetypes
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from api.app import handler


class Preview(handler):
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/api/app':return super().do_GET()
        files={'/':'index.html','/app.js':'app.js','/style.css':'style.css','/mark.svg':'mark.svg'}
        if path not in files:return self.send_json(404,{'error':'页面不存在'})
        file=ROOT/'cloud/web'/files[path]
        raw=file.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type',(mimetypes.guess_type(str(file))[0] or 'text/plain')+'; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(raw)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8877)
    args=parser.parse_args()
    print(f'Cloud app preview: http://127.0.0.1:{args.port}/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Preview).serve_forever()

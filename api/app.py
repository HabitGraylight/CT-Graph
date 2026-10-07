"""One Vercel Python function. Session cookies are HttpOnly; all DB access uses RLS."""
import json
import os
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qs, urlencode
from cloud.service import ApiError, Supabase, advise, private_action, text
from cocktail import engine
from cocktail.runtime import public_runtime


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # No recipe, email, authentication or tasting content in HTTP logs.

    def send_json(self, status, data):
        raw = json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','private, no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        for cookie in getattr(self,'out_cookies',[]):self.send_header('Set-Cookie',cookie)
        self.end_headers()
        self.wfile.write(raw)

    def set_session(self, session=None):
        self.out_cookies = []
        for name, field in [('ct_access','access_token'),('ct_refresh','refresh_token')]:
            c = SimpleCookie()
            c[name] = session[field] if session else ''
            c[name]['httponly'] = True
            c[name]['samesite'] = 'Lax'
            c[name]['path'] = '/api'
            c[name]['max-age'] = 30*86400 if session else 0
            if self.db.origin.startswith('https://') or os.environ.get('VERCEL'):c[name]['secure'] = True
            self.out_cookies.append(c[name].OutputString())

    def authentication(self):
        cookies = SimpleCookie()
        try:cookies.load(self.headers.get('Cookie',''))
        except Exception:raise ApiError('登录信息无效，请重新登录。',401)
        access = cookies['ct_access'].value if 'ct_access' in cookies else None
        refresh = cookies['ct_refresh'].value if 'ct_refresh' in cookies else None
        if access:
            try:return self.db.user(access),access
            except ApiError as e:
                if e.status!=401:raise
        if refresh:
            try:session = self.db.request('/auth/v1/token?grant_type=refresh_token','POST',{'refresh_token':refresh})
            except ApiError as e:
                if e.status==401:self.set_session()
                raise
            user = self.db.user(session['access_token'])
            self.set_session(session)
            return user,session['access_token']
        raise ApiError('请先登录',401)

    def do_GET(self):
        self.db = Supabase()
        self.out_cookies = []
        try:
            resource = parse_qs(urlsplit(self.path).query).get('resource',['catalog'])[0]
            if resource=='catalog':
                with public_runtime():result=engine.catalog()
                result['configured']=self.db.configured
            elif resource=='community':
                result={'recipes':self.db.request('/rest/v1/rpc/community_cards','POST',{}) if self.db.configured else [],'configured':self.db.configured}
            elif resource=='state':
                if not self.db.configured:result={'configured':False,'user':None}
                else:
                    try:user,token=self.authentication()
                    except ApiError as e:
                        if e.status!=401:raise
                        self.set_session()
                        return self.send_json(200,{'configured':True,'user':None})
                    result=self.db.state(user,token)
            else:raise ApiError('接口不存在',404)
            self.send_json(200,result)
        except ApiError as e:self.send_json(e.status,{'error':str(e)})
        except Exception:self.send_json(500,{'error':'请求未完成，请稍后重试。'})

    def do_POST(self):
        self.db=Supabase()
        self.out_cookies=[]
        try:
            origin=self.headers.get('Origin','')
            expected=self.db.origin
            # Local preview is read-only until explicitly configured.
            if not expected and not os.environ.get('VERCEL'):
                host=self.headers.get('Host','')
                if urlsplit('http://'+host).hostname in {'localhost','127.0.0.1'}:expected='http://'+host
            if not expected or origin!=expected:raise ApiError('请求来源不匹配',403)
            if self.headers.get_content_type()!='application/json':raise ApiError('需要 JSON 请求',415)
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=32768:raise ApiError('请求内容过长或为空',413)
            body=json.loads(self.rfile.read(size),parse_constant=lambda _: (_ for _ in ()).throw(ValueError('数值无效')))
            if not isinstance(body,dict):raise ApiError('请求格式错误')
            action=body.get('action')
            if action in {'signup','login','recover'}:
                email=text(body.get('email',''),'邮箱',254,True)
                if '@' not in email:raise ApiError('请填写有效邮箱')
                if action=='recover':
                    self.db.request('/auth/v1/recover?'+urlencode({'redirect_to':self.db.origin+'/'}),'POST',{'email':email})
                    result={'message':'如果邮箱已注册，重置链接将发送至邮箱。'}
                else:
                    password=text(body.get('password',''),'密码',128,True,trim=False)
                    if action=='signup' and len(password)<10:raise ApiError('密码至少 10 位')
                    path='/auth/v1/signup?'+urlencode({'redirect_to':self.db.origin+'/'}) if action=='signup' else '/auth/v1/token?grant_type=password'
                    session=self.db.request(path,'POST',{'email':email,'password':password})
                    if session.get('access_token'):self.set_session(session)
                    result={'message':'登录成功' if session.get('access_token') else '请查收确认邮件，点击链接完成注册后登录。'}
            elif action=='session':
                access=text(body.get('access_token',''),'登录凭证',8192,True)
                refresh=text(body.get('refresh_token',''),'刷新凭证',1024,True)
                self.db.user(access)
                # Exchange refresh once to ensure both tokens belong to a valid session.
                session=self.db.request('/auth/v1/token?grant_type=refresh_token','POST',{'refresh_token':refresh})
                if self.db.user(session['access_token'])['id']!=self.db.user(access)['id']:raise ApiError('登录会话不匹配',401)
                self.set_session(session)
                result={'message':'邮箱验证完成'}
            elif action=='logout':
                try:
                    user,token=self.authentication()
                    self.db.request('/auth/v1/logout?scope=local','POST',{},token)
                except ApiError:pass
                self.set_session()
                result={'message':'已退出登录'}
            elif action in {'evaluate','complete','recommend'} and not body.get('personalize'):
                result=advise(action,body)
            else:
                user,token=self.authentication()
                if action=='password':
                    password=text(body.get('password',''),'密码',128,True,trim=False)
                    if len(password)<10:raise ApiError('密码至少 10 位')
                    self.db.request('/auth/v1/user','PUT',{'password':password},token)
                    result={'message':'密码已更新'}
                else:result=private_action(self.db,action,body,user,token)
            self.send_json(200,result)
        except ApiError as e:self.send_json(e.status,{'error':str(e)})
        except (ValueError,TypeError,KeyError) as e:self.send_json(400,{'error':'输入格式或原料条件不正确，请检查后重试。'})
        except Exception:self.send_json(500,{'error':'请求未完成，请稍后重试。'})

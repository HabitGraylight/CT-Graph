"""Supabase REST adapter using the caller JWT, never a service-role credential."""
import json
import os
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from cocktail import engine, planning
from cocktail.runtime import public_runtime
from .preferences import baseline, personalize


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def text(value, label, limit, required=False, trim=True):
    if not isinstance(value, str) or len(value)>limit or (required and not value.strip()):
        raise ApiError(f'{label}格式不正确（最多 {limit} 字）')
    return value.strip() if trim else value


def identifier(value):
    try:return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):raise ApiError('记录 ID 无效')


class Supabase:
    def __init__(self):
        self.url = os.environ.get('SUPABASE_URL', '').rstrip('/')
        self.key = os.environ.get('SUPABASE_PUBLISHABLE_KEY', '')
        self.origin = os.environ.get('APP_ORIGIN', '').rstrip('/')

    @property
    def configured(self):
        return bool(self.url and self.key and self.origin)

    def request(self, path, method='GET', payload=None, token=None, prefer=None):
        if not self.configured:raise ApiError('账号与数据库尚未配置，请按部署说明连接 Supabase。', 503)
        if urlsplit(self.url).scheme != 'https':raise ApiError('Supabase 地址必须使用 HTTPS', 503)
        headers = {'apikey':self.key, 'Content-Type':'application/json'}
        if token:headers['Authorization'] = 'Bearer '+token
        if prefer:headers['Prefer'] = prefer
        data = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode() if payload is not None else None
        try:
            with urlopen(Request(self.url+path, data=data, method=method, headers=headers), timeout=12) as r:
                raw = r.read(4_500_001)
                if len(raw)>4_500_000:raise ApiError('返回内容过大，请缩小查询范围。',413)
                return json.loads(raw) if raw else None
        except HTTPError as e:
            # Provider bodies can contain submitted values. Never echo or log them.
            if e.code == 429:raise ApiError('请求较频繁，请稍后再试。', 429)
            if e.code in (401,403) or (e.code==400 and 'grant_type=refresh_token' in path):raise ApiError('登录已过期或没有权限。', 401)
            if path.startswith('/auth/'):
                raise ApiError('认证未完成：请检查邮箱确认、密码或链接是否过期。')
            if e.code == 409:raise ApiError('记录已存在，请刷新后重试。', 409)
            raise ApiError('数据库未接受请求，请检查输入或是否已执行建表脚本。', 400 if e.code<500 else 502)
        except (URLError, TimeoutError):raise ApiError('暂时无法连接账号服务，请稍后重试。', 502)

    def user(self, token):
        if not token:raise ApiError('请先登录', 401)
        result = self.request('/auth/v1/user', token=token)
        if not result.get('id'):raise ApiError('登录无效', 401)
        return result

    def profile(self, uid, token):
        rows = self.request('/rest/v1/profiles?'+urlencode({'user_id':'eq.'+uid,'select':'display_name,preferences'}), token=token)
        return rows[0] if rows else {'display_name':'调酒同好','preferences':{}}

    def state(self, user, token):
        uid = user['id']
        profile = self.profile(uid, token)
        recipes = self.request('/rest/v1/recipes?'+urlencode({'owner_id':'eq.'+uid,'select':'*','order':'created_at.desc','limit':'50'}), token=token)
        raw = self.request('/rest/v1/tastings?'+urlencode({'user_id':'eq.'+uid,'select':'*,recipes(frame,title)','order':'updated_at.desc','limit':'200'}), token=token)
        tastings = [{**t,'frame':(t.get('recipes') or {}).get('frame'),'title':(t.get('recipes') or {}).get('title','已撤回的配方')} for t in raw]
        return {'configured':True,'user':{'id':uid,'email':user.get('email')},'profile':profile,'recipes':recipes,
                'tastings':tastings,'baseline':baseline(profile,tastings),
                'baselines':{key:baseline(profile,tastings,key) for key in engine.FRAMES},'recipe_window':50,'tasting_window':200}


def advise(action, body, profile=None, tastings=None):
    with public_runtime():
        frame = text(body.get('frame','sour'),'框架',40,True)
        recipe = text(body.get('recipe',''),'配方',6000)
        context = body.get('context') or {}
        if not isinstance(context,dict):raise ApiError('调制条件格式错误')
        method = body.get('method') or None
        if action == 'evaluate':return engine.evaluate(frame,recipe,method,context)
        args = dict(pantry=text(body.get('pantry',''),'材料架',3000),avoid=text(body.get('avoid',''),'排除原料',1000),context=context)
        target = baseline(profile,tastings or [],frame)
        if action == 'complete':
            # A low target changes only the unspecified syrup slot. Existing amounts stay intact.
            sweet = target['targets']['sweet']['value']
            preference = 'drier' if sweet is not None and sweet<=4 else 'balanced'
            result = engine.complete(frame,recipe,preference=preference,**args)
            result['baseline'] = target
            result['personal_note'] = '甜感目标较低，未填写的糖浆槽位采用少糖浆试配起点；已有用量保持。' if preference=='drier' else '按均衡框架补齐；已有用量保持。'
            return result
        if action == 'recommend':
            return personalize(planning.recommend(frame=frame,recipe=recipe,method=method,**args),target)
        raise ApiError('不支持的调配操作')


def private_action(db, action, body, user, token):
    uid = user['id']
    if action in {'evaluate','complete','recommend'}:
        state = db.state(user,token) if body.get('personalize') else None
        return advise(action,body,state['profile'] if state else None,state['tastings'] if state else None)
    if action == 'profile':
        row = {'user_id':uid,'display_name':text(body.get('display_name',''),'昵称',40,True),'preferences':body.get('preferences',{})}
        return db.request('/rest/v1/profiles?on_conflict=user_id','POST',row,token,'resolution=merge-duplicates,return=representation')
    if action == 'save_recipe':
        evaluation = advise('evaluate',body)
        if not evaluation['items'] or any(i['status']!='matched' for i in evaluation['items']):raise ApiError('请先确认所有原料名称再保存。')
        if any(i['amount'] is None for i in evaluation['items']):raise ApiError('保存版本前请填写所有原料用量。')
        row = {'id':identifier(body.get('request_id')),'owner_id':uid,'title':text(body.get('title',''),'配方名称',80,True),
               'frame':evaluation['frame_id'],'recipe':body['recipe'],'method':body.get('method') or '',
               'context':evaluation['judge']['snapshot']['context'],'visibility':'private'}
        existing = db.request('/rest/v1/recipes?'+urlencode({'id':'eq.'+row['id'],'owner_id':'eq.'+uid}),token=token)
        if existing:
            if any(existing[0].get(k)!=v for k,v in row.items() if k!='visibility'):
                raise ApiError('重试内容已改变，请重新保存为另一版本。',409)
            return existing
        # Immutable versions. The client reuses this UUID on an unchanged retry.
        return db.request('/rest/v1/recipes','POST',row,token,'return=representation')
    if action == 'visibility':
        visibility = body.get('visibility')
        if visibility not in {'private','public'}:raise ApiError('发布状态无效')
        if visibility=='public' and body.get('consent') is not True:raise ApiError('请确认公开这一版本的配方和调制条件。')
        return db.request('/rest/v1/recipes?'+urlencode({'id':'eq.'+identifier(body.get('id')),'owner_id':'eq.'+uid}),
                          'PATCH',{'visibility':visibility},token,'return=representation')
    if action == 'taste':
        if body.get('data_kind','real')!='real' or body.get('tasted') is not True or body.get('as_recipe') is not True:
            raise ApiError('只接受实际制作并按该版本用量试饮的记录；改配方请先另存版本。')
        row = {'user_id':uid,'recipe_id':identifier(body.get('recipe_id')),'tasted':True,'as_recipe':True,
               'liking':body.get('liking'),'quality':body.get('quality',{}),'intensities':body.get('intensities',{}),
               'notes':text(body.get('notes',''),'笔记',2000),'public_vote':body.get('public_vote') is True}
        return db.request('/rest/v1/tastings?on_conflict=user_id,recipe_id','POST',row,token,'resolution=merge-duplicates,return=representation')
    if action == 'delete_taste':
        return db.request('/rest/v1/tastings?'+urlencode({'id':'eq.'+identifier(body.get('id')),'user_id':'eq.'+uid}), 'DELETE',token=token)
    raise ApiError('不支持的操作')

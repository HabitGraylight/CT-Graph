"""Append-only trials and evidence notes. Personal preference is not scientific truth."""
import copy
import json
import re
import sqlite3
import uuid
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from .knowledge import ROOT
from .normalization import parse_items
from . import judge

DB = ROOT/'data/feedback/advisor.sqlite'
DESCRIPTORS = {'too_sweet':'偏甜','too_sour':'偏酸','too_bitter':'偏苦','too_strong':'酒精刺激突兀',
               'watery':'水感过重','flat':'气泡不足','aroma_weak':'香气弱','astringent':'过涩','foam_unstable':'泡沫不稳','balanced':'平衡合意'}


def now():return datetime.now(timezone.utc).isoformat()


def connect():
    DB.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(DB,timeout=15)
    db.execute('CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL)')
    return db


def records(kind='trial'):
    if not DB.exists():return []
    with closing(connect()) as db:
        rows=db.execute('SELECT payload FROM records WHERE kind=? ORDER BY created DESC,id DESC',(kind,)).fetchall()
    return [json.loads(row[0]) for row in rows]


def record(payload,kind,request_id=None):
    id=request_id or str(uuid.uuid4())
    if not isinstance(id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',id):raise ValueError('request_id 需为 8–80 位字母、数字、横线或下划线')
    with closing(connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT payload FROM records WHERE id=?',(id,)).fetchone()
        if old:
            prior=json.loads(old[0])
            def logical_input(value):
                if kind=='trial':return {k:value.get(k) for k in ('snapshot','tasting','parent_trial_id','supersedes_trial_id')}
                return {k:v for k,v in value.items() if k!='knowledge_version'}
            if prior['kind']!=kind or logical_input(prior['input'])!=logical_input(payload):raise ValueError('request_id 已用于不同内容；请为新记录使用新 ID')
            return {**prior,'duplicate':True}
        correction=payload.get('supersedes_trial_id') if kind=='trial' else None
        if correction:
            existing=[json.loads(r[0]) for r in db.execute("SELECT payload FROM records WHERE kind='trial'")]
            prior=next((r for r in existing if r['id']==correction),None)
            if prior is None:raise ValueError('待更正的试饮记录不存在')
            if prior['input']['tasting'].get('taster','local')!=payload['tasting'].get('taster','local'):raise ValueError('只能更正同一品鉴者的记录')
            if any(r['input'].get('supersedes_trial_id')==correction for r in existing):raise ValueError('该记录已有更正，请继续更正最新版本')
        result={'id':id,'kind':kind,'created_at':now(),'input':payload}
        db.execute('INSERT INTO records VALUES (?,?,?,?)',(id,kind,result['created_at'],json.dumps(result,ensure_ascii=False)))
    return result


def text_field(value,name,maxlength=3000):
    if not isinstance(value,str) or len(value)>maxlength:raise ValueError(name+' 文本无效或过长')
    return value


def sensory_report(tasting):
    if not isinstance(tasting,dict) or set(tasting)-{'tasted','ratings','descriptors','notes','overall_liking','taster'}:raise ValueError('tasting 字段无效')
    if type(tasting.get('tasted')) is not bool:raise ValueError('必须明确 tasted：是否已经实际试饮')
    ratings=tasting.get('ratings',{})
    if not isinstance(ratings,dict) or set(ratings)-{id for id,_,_ in judge.DIMENSIONS}:raise ValueError('ratings 的维度无效')
    for id,v in ratings.items():judge.number(v,id,0,10)
    if not tasting['tasted'] and (ratings or 'overall_liking' in tasting):raise ValueError('未实际试饮不能提交感官分数')
    descriptors=tasting.get('descriptors',[])
    if not isinstance(descriptors,list) or any(not isinstance(d,str) or d not in DESCRIPTORS for d in descriptors):raise ValueError('试饮描述选项无效')
    if len(set(descriptors))!=len(descriptors):raise ValueError('试饮描述不能重复')
    text_field(tasting.get('notes',''),'notes')
    text_field(tasting.get('taster','local'),'taster',80)
    if 'overall_liking' in tasting:judge.number(tasting['overall_liking'],'overall_liking',0,10)
    return {'dimensions':[{'id':id,'name':name,'score':ratings.get(id)} for id,name,_ in judge.DIMENSIONS],
        'total':round(sum(ratings.values()),2) if len(ratings)==7 and tasting['tasted'] else None,'maximum':70,
        'rated_dimensions':len(ratings),'overall_liking':tasting.get('overall_liking'),
        'provenance':'用户报告的真实试饮；系统未独立品尝' if tasting['tasted'] else '设计笔记，排除在口味学习之外'}


def save_feedback(frame,recipe,method=None,context=None,tasting=None,request_id=None,parent_trial_id=None,supersedes_trial_id=None):
    from .engine import evaluate
    report=sensory_report(tasting)
    evaluation=evaluate(frame,recipe,method,context)
    if not evaluation['items']:raise ValueError('请先提供配方再记录试饮')
    if tasting['tasted']:
        if any(i['status']!='matched' for i in evaluation['items']):raise ValueError('真实试饮记录需先确认原料名称')
        if any(i['amount'] is None for i in evaluation['items'] if not set(i['ingredient']['roles'])&{'garnish','ice','seasoning'}):raise ValueError('真实试饮记录需保存实际原料用量')
    if parent_trial_id and not any(r['id']==parent_trial_id for r in records()):raise ValueError('父试饮记录不存在')
    payload={'snapshot':evaluation['judge']['snapshot'],'recipe_id':evaluation['judge']['recipe_id'],
        'knowledge_version':evaluation['judge']['version'],'knowledge_hash':evaluation['judge']['knowledge_hash'],
        'design_review':evaluation['judge'],'framework_score':evaluation['score'],
        'tasting':tasting,'sensory':report,'parent_trial_id':parent_trial_id,'supersedes_trial_id':supersedes_trial_id}
    return record(payload,'trial',request_id)


def preference_profile(frame=None,taster='local'):
    all_trials=records();superseded={r['input'].get('supersedes_trial_id') for r in all_trials}
    trials=[r for r in all_trials if r['id'] not in superseded and r['input']['tasting']['tasted'] and r['input']['tasting'].get('taster','local')==taster
            and (frame is None or r['input']['snapshot']['frame']==frame)]
    counts=Counter(d for r in trials for d in r['input']['tasting'].get('descriptors',[]))
    # A majority of at least three trials is a hint for this user and framework, never a universal calibration.
    hint='drier' if counts['too_sweet']>=3 and counts['too_sweet']/len(trials)>.5 else 'balanced'
    return {'taster':taster,'frame':frame,'tasted_trials':len(trials),'descriptors':dict(counts),
        'completion_preference':hint,'supporting_trial_ids':[r['id'] for r in trials[:20]],
        'confidence':'初步个人倾向，仍受配方和操作差异影响' if len(trials)>=3 else '样本不足，不推断稳定偏好',
        'policy':'仅在选择 personal 补全时使用；同一框架至少 3 次且超过一半反馈偏甜，才减少新补糖浆。'}


def improve(frame=None,recipe=None,method=None,context=None,feedback_id=None,avoid=''):
    from .engine import evaluate, assign, get_frame, ancestors
    feedback=None;descriptors=[]
    if feedback_id:
        feedback=next((r for r in records() if r['id']==feedback_id),None)
        if feedback is None:raise ValueError('反馈记录不存在')
        if any(r['input'].get('supersedes_trial_id')==feedback_id for r in records()):raise ValueError('该反馈已被更正，请使用最新记录')
        if not feedback['input']['tasting']['tasted']:raise ValueError('设计笔记不能作为实饮反馈来改进')
        saved=feedback['input']['snapshot']
        frame=saved['frame'] if frame is None else frame
        recipe=saved['recipe'] if recipe is None else recipe
        method=saved['method'] if method is None else method
        context=saved['context'] if context is None else context
        descriptors=feedback['input']['tasting'].get('descriptors',[])
    before=evaluate(frame or 'sour',recipe or '',method,context)
    if feedback and before['judge']['recipe_id']!=feedback['input']['recipe_id']:raise ValueError('当前配方/技法/条件与该反馈记录不一致，请使用记录原版')
    if not feedback and before['judge']['composition']['process_stage']=='whole_drink_transformation':
        return {'blocked':True,'reason':'整杯澄清后的成分保留未知，不能只按投料比例自动减糖或减酸。先记录工艺和真实试饮，再提出单变量对照。','before':before}
    items=before['items'];snap=before['judge']['snapshot'];slots,_=assign(get_frame(before['frame_id']),items)
    excluded=parse_items(avoid)
    if any(i['status']!='matched' for i in excluded):raise ValueError('排除原料需先消除歧义')
    if not items or any(i['status']!='matched' for i in items):return {'blocked':True,'reason':'先确认配方原料，再做可追溯的小改动。','before':before}
    excluded_ids={i['ingredient']['id'] for i in excluded}
    if any(ancestors(i['ingredient']['id'])&excluded_ids for i in items):return {'blocked':True,'reason':'原版包含当前排除的原料；请先明确替代方案，再做用量对照。','before':before}
    new=copy.deepcopy(snap);change=None
    if not descriptors:
        for c in before['checks']:
            if c['slot']=='sweet' and c['state']=='high':descriptors=['too_sweet'];break
            if c['slot']=='acid' and c['state']=='high':descriptors=['too_sour'];break
        if any(r['id']=='shake_carbonated' for r in before['judge']['risks']):descriptors=['flat']
    for d in descriptors:
        target={'too_sweet':'sweet','too_sour':'acid','too_bitter':'bitter'}.get(d)
        entries=slots.get(target,[])
        if entries:
            if len(entries)!=1 or entries[0]['ml'] is None:continue
            item=entries[0];old=item['ml'];delta=min(2.5,old*.2)
            idx=items.index(item);new['recipe'][idx]['amount']=round(old-delta,2);new['recipe'][idx]['unit']='ml'
            change={'variable':item['ingredient']['id'],'before':old,'after':round(old-delta,2),'unit':'ml',
                'reason':DESCRIPTORS[d]+'：先减少一个相关材料做对照；也会改变该材料的其他风味。'}
            break
        if d=='flat' and any(r['id']=='shake_carbonated' for r in before['judge']['risks']):
            new['method']='shake_top';change={'variable':'method','before':method,'after':'shake_top','reason':'气泡材料在无气部分摇和后加入。'};break
        if d=='too_strong':
            if any(i['ingredient']['id']=='water' for i in excluded):continue
            # Add an explicit recipe dose; unknown melting is not silently replaced with 5 ml.
            water=next((i for i in new['recipe'] if i['name']=='water'),None)
            if water:
                idx=new['recipe'].index(water)
                if items[idx]['ml'] is None:continue
                old=items[idx]['ml'];water.update(amount=old+5,unit='ml')
            else:old=0;new['recipe'].append({'name':'water','amount':5,'unit':'ml'})
            change={'variable':'water','before':old,'after':old+5,'unit':'ml','reason':'明确增加 5 ml 水，测试刺激感与香气的变化；原融冰假设保持。'};break
        if d=='watery' and new['context'].get('dilution_ml',0)>=5:
            old=new['context']['dilution_ml'];new['context']['dilution_ml']=old-5
            change={'variable':'dilution_ml','before':old,'after':old-5,'unit':'ml','reason':'比较少 5 ml 融水的情景；需要改变实际操作并测量，不能只改记录。'};break
    if not change:return {'blocked':True,'reason':'目前没有足够依据自动改用量。先记录糖/酸浓度、温度、融水或泡沫表现，再做单变量试验。','before':before,'feedback_id':feedback_id}
    after=evaluate(new['frame'],new['recipe'],new['method'],new['context'])
    return {'blocked':False,'before':before,'after':after,'candidate':new,'change':change,'feedback_id':feedback_id,
            'basis':'用户真实试饮' if feedback else '编辑规则的设计提示',
            'verification':'原版 A 与候选 B 保持其他条件一致，最好隐藏杯标并交换品尝顺序。实际更喜欢 B 才视为改善。',
            'predicted_taste_gain':None,'framework_score_delta':after['score']-before['score'] if before['score'] is not None and after['score'] is not None else None,
            'note':'候选不覆盖原版。框架分下降也可能更合个人口味；未将自评高分当成试饮证据。'}


def evidence_note(rule_id,url,finding,request_id=None):
    from urllib.parse import urlsplit
    if rule_id not in {r['id'] for r in judge.knowledge()['rules']}:raise ValueError('规则不存在')
    if not isinstance(url,str) or urlsplit(url).scheme!='https' or not urlsplit(url).hostname:raise ValueError('证据需提供 HTTPS 来源链接')
    text_field(finding,'finding')
    if not finding.strip():raise ValueError('请说明支持、反驳或缩小适用范围的证据')
    return record({'rule_id':rule_id,'url':url,'finding':finding,'status':'pending_review',
                   'knowledge_version':judge.knowledge()['version']},'evidence',request_id)

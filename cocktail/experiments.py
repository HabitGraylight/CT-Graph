"""Local append-only paired trials. Samples, observations and preferences are distinct."""
import copy
import json
import re
import secrets
import uuid
from contextlib import closing
from . import learning, judge, graph

INTENSITIES = {'sweet','sour','bitter','alcohol_heat','aroma','body','carbonation','astringency'}


def _retry(kind, parameters, request_id):
    if request_id is None: return None
    if not isinstance(request_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',request_id):
        raise ValueError('request_id 需为 8–80 位字母、数字、横线或下划线')
    if not learning.DB.exists(): return None
    with closing(learning.connect()) as db:
        row=db.execute('SELECT payload FROM records WHERE id=?',(request_id,)).fetchone()
    if row:
        prior=json.loads(row[0])
        if prior['kind']!=kind or prior['input'].get('parameters')!=parameters:
            raise ValueError('request_id 已用于不同内容')
        return {**prior,'duplicate':True}


def _append(kind, payload, request_id=None, check=None):
    key = request_id or str(uuid.uuid4())
    if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',key):
        raise ValueError('request_id 需为 8–80 位字母、数字、横线或下划线')
    with closing(learning.connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        all_rows = [json.loads(x[0]) for x in db.execute('SELECT payload FROM records')]
        prior = next((r for r in all_rows if r['id']==key),None)
        if prior:
            original=prior['input'].get('parameters',prior['input'])
            incoming=payload.get('parameters',payload)
            if prior['kind']!=kind or original!=incoming: raise ValueError('request_id 已用于不同内容')
            return {**prior,'duplicate':True}
        if check: check(all_rows)
        result={'id':key,'kind':kind,'created_at':learning.now(),'input':payload}
        db.execute('INSERT INTO records VALUES (?,?,?,?)',
                   (key,kind,result['created_at'],json.dumps(result,ensure_ascii=False)))
    return result


def get(experiment_id):
    result=next((r for r in learning.records('experiment') if r['id']==experiment_id),None)
    if result is None: raise ValueError('试验计划不存在')
    return result


def create(frame='sour', recipe='', pantry='', avoid='', context=None, taster='local', method=None, candidate_id='water_swap', request_id=None, data_kind='real'):
    from .planning import recommend, VERSION
    learning.text_field(taster,'taster',80)
    if not taster.strip(): raise ValueError('品鉴者不能为空')
    if data_kind not in {'real','synthetic'}: raise ValueError('data_kind 需为 real 或 synthetic')
    parameters=dict(frame=frame,recipe=recipe,pantry=pantry,avoid=avoid,context=context,taster=taster,method=method,candidate_id=candidate_id,data_kind=data_kind)
    prior=_retry('experiment',parameters,request_id)
    if prior: return prior
    recommendation=recommend(frame,recipe,pantry,avoid,context,taster,method)
    if recommendation['blocked']: return recommendation
    candidates={c['id']:c for c in recommendation['candidates']}
    if candidate_id=='reference' or candidate_id not in candidates: raise ValueError('请选择一个改版与原版对照')
    pair=[candidates['reference'],candidates[candidate_id]]
    secrets.SystemRandom().shuffle(pair)
    samples=[]
    for code,c in zip(('A','B'),pair):
        samples.append({'code':code,'serving_id':str(uuid.uuid4()),'candidate_id':c['id'],
                        'snapshot':c['snapshot'],'recipe_id':c['recipe_id'],'tradeoff':c['tradeoff'],
                        'intervention':c['intervention'],'trace':c['trace']})
    payload={'parameters':parameters,'policy_version':VERSION,'session_id':str(uuid.uuid4()),
             'reference_recipe_id':candidates['reference']['recipe_id'],
             'taster':taster,'data_kind':data_kind,'samples':samples,'presentation_order':['A','B'],
             'assignment':'randomized_order_not_blinded','planned_timepoints_s':[0,120],
             'controls':['同一批次原料与相同杯型、份量基准','记录实际温度、融水和步骤偏离','随机次序不等于盲评；同杯多时点评分不算独立重复'],
             'candidate_evidence':{'policy':recommendation['ranking_policy'],'personal':recommendation['personal_evidence']}}
    # Serialize creation/retries; concurrent identical requests return the first assignment.
    if request_id:
        with closing(learning.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            prior=db.execute('SELECT payload FROM records WHERE id=?',(request_id,)).fetchone()
            if prior:
                saved=json.loads(prior[0])
                if saved['kind']!='experiment' or saved['input']['parameters']!=parameters: raise ValueError('request_id 已用于不同计划')
                return {**saved,'duplicate':True}
            result={'id':request_id,'kind':'experiment','created_at':learning.now(),'input':payload}
            db.execute('INSERT INTO records VALUES (?,?,?,?)',(request_id,'experiment',result['created_at'],json.dumps(result,ensure_ascii=False)))
            return result
    return _append('experiment',payload)


def observe(experiment_id, serving_id, tasting, observation, request_id=None, supersedes=None):
    parameters=copy.deepcopy(dict(experiment_id=experiment_id,serving_id=serving_id,tasting=tasting,observation=observation,supersedes=supersedes))
    prior=_retry('observation',parameters,request_id)
    if prior: return prior
    experiment=get(experiment_id)['input']
    sample=next((s for s in experiment['samples'] if s['serving_id']==serving_id),None)
    if sample is None: raise ValueError('样品不属于该试验')
    if not isinstance(observation,dict) or set(observation)-{'timepoint_s','intensities','as_planned','actual_snapshot','deviations','temperature_c','observed_volume_ml'}:
        raise ValueError('observation 字段无效')
    judge.number(observation.get('timepoint_s'),'timepoint_s',0,86400)
    intensities=observation.get('intensities',{})
    if not isinstance(intensities,dict) or set(intensities)-INTENSITIES: raise ValueError('感官强度字段无效')
    for k,v in intensities.items(): judge.number(v,k,0,10)
    observed_conditions={k:observation[k] for k in ('temperature_c','observed_volume_ml') if k in observation}
    for k,lo,hi in [('temperature_c',-30,100),('observed_volume_ml',0,10000)]:
        if k in observed_conditions:judge.number(observed_conditions[k],k,lo,hi)
    if not isinstance(tasting,dict): raise ValueError('tasting 需要是对象')
    tasting=copy.deepcopy(tasting); tasting.setdefault('taster',experiment['taster'])
    if tasting['taster']!=experiment['taster']: raise ValueError('品鉴者与计划不一致，请另建会话')
    sensory=learning.sensory_report(tasting,data_kind=experiment['data_kind'])
    if experiment['data_kind']=='real' and tasting['tasted'] is not True: raise ValueError('真实试验观察需明确已经实际试饮；设计笔记使用原 feedback 接口')
    if type(observation.get('as_planned')) is not bool: raise ValueError('需明确 as_planned：是否按计划制作')
    deviations=observation.get('deviations',''); learning.text_field(deviations,'deviations')
    if observation['as_planned']:
        if 'actual_snapshot' in observation: raise ValueError('按计划制作时不同时提供另一份 actual_snapshot')
        actual=sample['snapshot']
    else:
        actual=observation.get('actual_snapshot')
        if not isinstance(actual,dict) or set(actual)!={'frame','recipe','method','context'}: raise ValueError('偏离计划时需记录完整 actual_snapshot')
    from .engine import evaluate
    actual_review=evaluate(actual['frame'],actual['recipe'],actual['method'],actual['context'])
    if any(i['status']!='matched' or i['amount'] is None for i in actual_review['items']): raise ValueError('实际制作需确认原料和用量')
    snap=actual_review['judge']['snapshot']
    trace=graph.from_evaluation(actual_review)
    observation_node=graph.identity('observation',[parameters,actual_review['judge']['recipe_id']])
    trace['nodes'].extend([
        {'id':'experiment:'+experiment_id,'type':'Experiment','session_id':experiment['session_id']},
        {'id':'serving:'+serving_id,'type':'Serving'},
        {'id':observation_node,'type':'Observation','data_kind':experiment['data_kind'],'timepoint_s':observation['timepoint_s'],'intensities':intensities,'sensory':sensory,'conditions':observed_conditions},
        {'id':graph.identity('taster',experiment['taster']),'type':'Taster','label':experiment['taster']},
    ])
    trace['edges'].extend([
        {'source':'experiment:'+experiment_id,'relation':'HAS_SERVING','target':'serving:'+serving_id},
        {'source':'serving:'+serving_id,'relation':'MADE_FROM','target':trace['recipe_id']},
        {'source':observation_node,'relation':'OBSERVES','target':'serving:'+serving_id},
        {'source':observation_node,'relation':'REPORTED_BY','target':graph.identity('taster',experiment['taster'])},
    ])
    payload={'parameters':parameters,'experiment_id':experiment_id,'session_id':experiment['session_id'],'serving_id':serving_id,
             'timepoint_s':observation['timepoint_s'],'intensities':intensities,'tasting':tasting,'sensory':sensory,'observed_conditions':observed_conditions,
             'actual_snapshot':snap,'actual_recipe_id':actual_review['judge']['recipe_id'],'deviations':deviations,
             'as_planned':observation['as_planned'],'data_kind':experiment['data_kind'],
             'supersedes':supersedes,'trace':trace}
    def check(rows):
        observations=[r for r in rows if r['kind']=='observation']
        replaced={r['input'].get('supersedes') for r in observations}
        active=[r for r in observations if r['id'] not in replaced]
        same=[r for r in active if r['input']['serving_id']==serving_id and r['input']['timepoint_s']==payload['timepoint_s']]
        if same and supersedes!=same[0]['id']: raise ValueError('该杯此时间点已有记录；更正请提供 supersedes_observation_id')
        if supersedes and (not same or same[0]['id']!=supersedes): raise ValueError('只能更正该杯同一时间点的当前记录')
        other=[r for r in active if r['input']['serving_id']==serving_id and r['id']!=supersedes]
        if any(r['input']['actual_recipe_id']!=payload['actual_recipe_id'] for r in other): raise ValueError('同一杯的实际配方不能随时间点改变，请另建制作记录')
    return _append('observation',payload,request_id,check)


def active_observations(experiment_id):
    rows=[r for r in learning.records('observation') if r['input']['experiment_id']==experiment_id]
    superseded={r['input'].get('supersedes') for r in rows}
    return [r for r in rows if r['id'] not in superseded]


def choose(experiment_id, preferred, timepoint_s=0, request_id=None):
    parameters=dict(experiment_id=experiment_id,preferred=preferred,timepoint_s=timepoint_s)
    prior=_retry('pair_result',parameters,request_id)
    if prior: return prior
    experiment=get(experiment_id)['input']
    if preferred not in {'A','B','tie','inconclusive'}: raise ValueError('preferred 需为 A、B、tie 或 inconclusive')
    judge.number(timepoint_s,'timepoint_s',0,86400)
    observations=active_observations(experiment_id)
    pair=[]
    for sample in experiment['samples']:
        found=next((r for r in observations if r['input']['serving_id']==sample['serving_id'] and r['input']['timepoint_s']==timepoint_s),None)
        if not found: raise ValueError('两杯需在同一时间点都有观察，才能比较；真实计划只接受实饮记录')
        pair.append(found)
    selected=next((s for s in experiment['samples'] if s['code']==preferred),None)
    payload={'parameters':parameters,'experiment_id':experiment_id,'taster':experiment['taster'],'preferred':preferred,'timepoint_s':timepoint_s,
             'reference_recipe_id':experiment['reference_recipe_id'],
             'candidate_id':selected['candidate_id'] if selected else None,'intervention':selected['intervention'] if selected else None,
             'observation_ids':sorted(r['id'] for r in pair),'data_kind':experiment['data_kind'],
             'eligible':experiment['data_kind']=='real' and all(r['input']['as_planned'] and not r['input']['deviations'] for r in pair)}
    return _append('pair_result',payload,request_id)


def preference(taster='local', reference_recipe_id=None):
    results=learning.records('pair_result'); latest={}
    for result in results:
        p=result['input']
        if p['taster']==taster and p['reference_recipe_id']==reference_recipe_id and p['experiment_id'] not in latest: latest[p['experiment_id']]=p
    wins={}; count=0
    for experiment_id,p in latest.items():
        current={r['id'] for r in active_observations(experiment_id)}
        if not p['eligible'] or not set(p['observation_ids'])<=current or p['preferred'] in {'tie','inconclusive'}: continue
        count+=1; wins[p['intervention']]=wins.get(p['intervention'],0)+1
    best=max(wins,key=wins.get) if wins else None
    preferred=best if count>=3 and wins[best]/count>.5 else None
    return {'taster':taster,'reference_recipe_id':reference_recipe_id,'eligible_pairs':count,'wins':wins,'preferred_intervention':preferred,
            'scope':'相同参照配方、材料条件和品鉴者的探索性策略倾向；每个试验只计最近一次比较，不把多时点算成重复。非因果效应或稳定口味模型。'}


def history():
    return {'experiments':learning.records('experiment'),'observations':learning.records('observation'),
            'results':learning.records('pair_result')}

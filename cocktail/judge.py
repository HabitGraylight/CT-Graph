"""Evidence-backed design review. Sensory observations are never synthesized."""
import hashlib
import json
import math
from datetime import date, timedelta
from .knowledge import ROOT
from .normalization import resolve
from . import design

DIMENSIONS = [
    ('appearance','外观','风格所需的清澈、色泽、泡沫和装饰是否实现？'),
    ('aroma','香气','分别记录鼻前、鼻后香气、主次与异味。'),
    ('balance','平衡度','按目标风格判断酸甜苦咸、烈度及涩感，勿要求所有酒隐藏酒精。'),
    ('structure','结构与层次','记录入口、中段、余韵；复杂或悠长本身不等于更好。'),
    ('texture','质地与口感','记录厚薄、顺滑、泡沫、气泡和涩感；在这里评价感受。'),
    ('execution','温度与物理状态','记录实测温度、融水、冰杯和操作；不重复给口感加减分。'),
    ('expression','创意与表达','原创看主题与风味自洽；复刻看目标版本忠实度，不强求创新。'),
]


def knowledge():
    # Read on each review so a newly reviewed version takes effect without stale caches.
    return json.loads((ROOT/'data/knowledge/judge.json').read_text(encoding='utf-8'))


def number(value, label, low, high):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:
        raise ValueError(f'{label} 需为 {low}–{high} 之间的有限数值')
    return value


def validate_context(value=None):
    c={} if value is None else value
    if not isinstance(c,dict):raise ValueError('context 需要是对象')
    allowed={'intent','appearance_target','texture_target','theme','garnish','glass_chilled','dilution_ml','temperature_c','final_ph','composition','process'}
    if set(c)-allowed:raise ValueError('不支持的 context 字段：'+','.join(sorted(set(c)-allowed)))
    for k,choices in [('intent',{'classic','original','milk_clarified'}),('appearance_target',{'clear','cloudy','foam','any'}),('texture_target',{'silky','light','foamy','sparkling','any'})]:
        if k in c and c[k] not in choices:raise ValueError(k+' 选项无效')
    for k in ('theme','garnish'):
        if k in c and (not isinstance(c[k],str) or len(c[k])>1000):raise ValueError(k+' 需为不超过 1000 字的文本')
    if 'glass_chilled' in c and type(c['glass_chilled']) is not bool:raise ValueError('glass_chilled 需为布尔值')
    for k,lo,hi in [('dilution_ml',0,5000),('temperature_c',-30,100),('final_ph',0,14)]:
        if k in c:number(c[k],k,lo,hi)
    process=c.get('process',{})
    if not isinstance(process,dict) or set(process)-{'clarification','carbonation','service','batched','preparations'}:
        raise ValueError('process 字段无效')
    for k,choices in [('clarification',{'none','strained','whole_drink'}),('carbonation',{'none','top_up','force'}),('service',{'up','on_ice'})]:
        if k in process and (not isinstance(process[k],str) or process[k] not in choices):raise ValueError('process.'+k+' 选项无效')
    if 'batched' in process and type(process['batched']) is not bool:raise ValueError('process.batched 需为布尔值')
    if c.get('intent')=='milk_clarified' and process.get('clarification') in {'none','strained'}:
        raise ValueError('奶洗澄清与 process.clarification 冲突')
    preparations=process.get('preparations',[])
    if not isinstance(preparations,list) or len(preparations)>80:raise ValueError('preparations 需要是最多 80 项的列表')
    prepared_ids=set()
    for entry in preparations:
        if not isinstance(entry,dict) or set(entry)!={'name','state'} or not isinstance(entry.get('name'),str):raise ValueError('preparations 需提供 name 与 state')
        if not isinstance(entry['state'],str) or entry['state'] not in {'fresh','heated','infused','fermented','clarified'}:raise ValueError('原料加工状态无效')
        resolved=resolve(entry['name'])
        if resolved['status']!='matched':raise ValueError('加工原料须先消除歧义')
        key=resolved['ingredient']['id']
        if key in prepared_ids:raise ValueError('同一原料只能声明一个当前加工状态')
        prepared_ids.add(key)
    composition=c.get('composition',[])
    if not isinstance(composition,list) or len(composition)>80:raise ValueError('composition 需要是最多 80 项的列表')
    ids=set()
    for entry in composition:
        if not isinstance(entry,dict) or set(entry)-{'name','abv','sugar_g_l','acid_g_l','basis','source'}:raise ValueError('成分测量字段无效')
        if not isinstance(entry.get('name'),str):raise ValueError('成分数据需提供原料 name')
        r=resolve(entry['name'])
        if r['status']!='matched':raise ValueError('成分数据的原料须先消除歧义')
        id=r['ingredient']['id']
        if id in ids:raise ValueError('同一原料不能有两组冲突的成分数据')
        ids.add(id)
        if entry.get('basis') not in {'label','measurement','assumption'}:raise ValueError('成分数据需注明 label、measurement 或 assumption')
        if not isinstance(entry.get('source'),str) or not entry['source'].strip() or len(entry['source'])>1000:raise ValueError('成分数据需注明瓶标、测量记录或假设来源')
        if not {'abv','sugar_g_l','acid_g_l'}&entry.keys():raise ValueError('请至少提供一项成分数值')
        for k,hi in [('abv',100),('sugar_g_l',1500),('acid_g_l',500)]:
            if k in entry:number(entry[k],k,0,hi)
    return c


def recipe_snapshot(evaluation, context=None):
    return {'frame':evaluation['frame_id'], 'recipe':[
        {'name':i['ingredient']['id'] if i['status']=='matched' else i['name'],'amount':i['amount'],'unit':i['unit']}
        for i in evaluation['items']], 'method':evaluation.get('method'), 'context':validate_context(context)}


def fingerprint(snapshot):
    return hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:24]


def composition_report(items, context):
    specs={resolve(e['name'])['ingredient']['id']:e for e in context.get('composition',[])}
    known={i['ingredient']['id'] for i in items if i['status']=='matched'}
    if specs.keys()-known:raise ValueError('成分数据引用了当前配方中没有的原料')
    preparations=context.get('process',{}).get('preparations',[])
    if {resolve(e['name'])['ingredient']['id'] for e in preparations}-known:raise ValueError('加工状态引用了当前配方中没有的原料')
    nonliquid={'garnish','ice','herb','fruit','seasoning','solid_sweet'}
    liquids=[i for i in items if i['status']!='matched' or not set(i['ingredient']['roles'])&nonliquid]
    missing_volume=[i['name'] for i in liquids if i['ml'] is None]
    volume=sum(i['ml'] or 0 for i in liquids)
    dilution=context.get('dilution_ml')
    final_volume=volume+(dilution or 0)
    output={'measured_liquid_ml':round(volume,2),'additional_water_ml':dilution,
            'dilution_definition':'额外融冰/加水体积 ÷ 配方中已计量液体体积；已写进原料的水不要重复填。',
            'dilution_ratio':round(dilution/volume,4) if dilution is not None and volume and not missing_volume else None,
            'missing_volume':missing_volume,'estimates':{},
            'note':'体积近似可加，未建模混合收缩、固体溶解体积、过滤损失。pH 不由原料 pH 求平均；糖浆甜味系数不是糖克数。'}
    for metric,unit in [('abv','% vol'),('sugar_g_l','g/L'),('acid_g_l','g/L')]:
        missing=[];numerator=0;assumed=[]
        # A solid sugar dose invalidates sugar concentration until a mass model is supplied.
        if metric in {'sugar_g_l','acid_g_l'}:
            missing.extend(i['name']+'（固体贡献未建模）' for i in items if i['status']=='matched' and set(i['ingredient']['roles'])&{'solid_sweet','fruit'})
        for i in liquids:
            spec=specs.get(i['ingredient']['id'],{}) if i['status']=='matched' else {}
            if metric not in spec or i['ml'] is None:missing.append(i['name']);continue
            numerator+=i['ml']*spec[metric]
            if spec['basis']=='assumption':assumed.append(i['name'])
        output['estimates'][metric]={'value':round(numerator/final_volume,3) if liquids and not missing and final_volume>0 else None,
              'unit':unit,'stage':'已声明额外水量的情景估算' if dilution is not None else '融冰前估算',
              'missing':missing,'assumed_ingredients':assumed,'inputs':context.get('composition',[])}
    transformed=context.get('intent')=='milk_clarified' or context.get('process',{}).get('clarification')=='whole_drink'
    output['process_stage']='whole_drink_transformation' if transformed else 'mixing_scenario'
    if transformed:
        output['input_scenario_estimates']=output['estimates']
        output['estimates']={k:{**v,'value':None,'stage':'整杯澄清后未知，需成品测量',
            'missing':v['missing']+['工艺后各成分保留率或成品测量']} for k,v in output['estimates'].items()}
        output['note']+=' 整杯澄清后的成分保留尚未建模；投料情景单独保留，不能只凭出液量反推浓度。'
    if preparations:
        output['note']+=' composition 数值必须对应实际投料的加工后原料，原料名称不能保证浓度或香气谱不变。'
    return output


def review(evaluation, method=None, context=None):
    c=validate_context(context); kb=knowledge();items=evaluation['items']
    profiles={p['ingredient_id']:p for p in kb['profiles']}
    used=[profiles[i['ingredient']['id']] for i in items if i['status']=='matched']
    components={component for p in used for component in p['component_ids']}
    interactions=[]
    for rule in kb['rules']:
        if rule['status']!='active' or not set(rule['requires'])<=components:continue
        r=dict(rule)
        r['triggered_by']={comp:[p['name'] for p in used if comp in p['component_ids']] for comp in rule['requires']}
        r['application']='工艺目标：聚集后过滤，成品是否澄清待验证' if rule['id']=='milk_acid' and c.get('intent')=='milk_clarified' else '条件性提示，不代表反应已经发生'
        if c.get('process',{}).get('preparations') or c.get('process',{}).get('clarification')=='whole_drink' or c.get('intent')=='milk_clarified':
            r['application']+='；依据投料类别触发，加工后的成分保留与反应状态未实测'
        interactions.append(r)
    risks=[]
    def risk(id,text,dims,level='watch',refs=None):risks.append({'id':id,'message':text,'dimensions':dims,'level':level,'source_ids':refs or []})
    for check in evaluation['checks']:
        if check['state'] in {'high','low','missing'}:
            risk('slot_'+check['slot'],check['label']+'：'+{'high':'相对框架偏多','low':'相对框架偏少','missing':'缺少'}[check['state']],['balance','structure'],'design',[])
    if 'co2' in components and method=='shake':risk('shake_carbonated','气泡料应在无气部分摇和完成后加入；当前整杯摇和方案需调整。',['execution','texture'],'action',['co2'])
    if 'casein' in components and 'organic_acids' in components and c.get('intent')!='milk_clarified':risk('curdling_check','牛乳与酸同用：先小样检查絮凝，确认是否需要澄清工艺。',['appearance','texture'],'watch',['casein'])
    if c.get('appearance_target')=='clear' and components&{'egg_protein','suspended_solids','casein'}:risk('clarity_target','投料可能带入泡沫或悬浮物；已有加工记录也需核对成品清澈度，清澈不等于无色。',['appearance'],'watch',['iba_sour'])
    if c.get('intent')=='milk_clarified':risk('clarified_unmodeled','奶洗会改变成分保留与体积，当前计算只适用于过滤前投料。',['balance','texture'],'watch',['casein'])
    has_unknown=any(i['status']!='matched' for i in items)
    if has_unknown:risk('unresolved','未识别原料可能引入额外机制；当前化学检查不完整。',[id for id,_,_ in DIMENSIONS],'information')
    dimensions=[]
    for id,name,prompt in DIMENSIONS:
        checks=[r for r in risks if id in r['dimensions']]
        basis=[];plan_score=None
        if id=='balance':
            basis=['以框架槽位比例为代理，未测果汁酸度、糖浓度与口腔感受。']
            if evaluation['score'] is not None:plan_score=round(sum(x['fit'] for x in evaluation['checks'])/len(evaluation['checks'])*10,1)
        elif id=='structure':
            basis=['只评核心结构完整性；入口—中段—余韵仍需试饮。']
            if evaluation['score'] is not None:plan_score=round(sum(x['state']!='missing' for x in evaluation['checks'])/len(evaluation['checks'])*10,1)
        elif id=='execution':
            basis=['仅检查所选技法与框架相符及气泡料的加入方式；冰杯、温度、融水是记录项。']
            if method and not has_unknown:plan_score=0 if any(r['id']=='shake_carbonated' for r in risks) else evaluation['components']['technique']
        elif id=='appearance':basis=['浑浊和颜色按目标风格判断；不能从配方确认清澈度、鲜度与装饰完成度。']
        elif id=='aroma':basis=['可以提示来源与相互作用；不凭原料名断言鼻前、鼻后香气已经协调。']
        elif id=='texture':basis=['配料提示酒体、乳化和气泡可能性；最终质地取决于浓度及操作。']
        elif id=='expression':basis=['主题：'+c['theme'] if c.get('theme') else '尚未提供主题或指定复刻版本；不因写了主题自动给高分。']
        dimensions.append({'id':id,'name':name,'plan_score':plan_score,'score_kind':'设计检查 / 10；编辑规则，非感官预测分','sensory_score':None,
            'status':'有待检查' if checks else '待实测','basis':basis,'risks':[r['id'] for r in checks],
            'interaction_ids':[r['id'] for r in interactions if id in r['dimensions']],'tasting_prompt':prompt})
    source_ids={s for r in interactions+risks for s in r['source_ids']}|{'usbg2025','iba_martini','iba_sour'}
    snapshot=recipe_snapshot({**evaluation,'method':method},c)
    return {'version':kb['version'],'knowledge_hash':hashlib.sha256(json.dumps(kb,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
        'design_review':design.review({**evaluation,'method':method},c),
        'recipe_id':fingerprint(snapshot),'snapshot':snapshot,'dimensions':dimensions,'sensory_total':None,
        'verdict':'资料不足，需先澄清原料与用量' if evaluation['score'] is None else '存在需要调整或试验的设计问题' if risks else '可作为试饮候选，尚无真实口味验证',
        'scoring_policy':'七项实际品鉴各 0–10 分；全部实填才汇总 /70。设计代理分不合成感官总分，机制不自动加减分。',
        'risks':risks,'interactions':interactions,'ingredient_profiles':used,'composition':composition_report(items,c),
        'sources':[s for s in kb['sources'] if s['id'] in source_ids],
        'next_trial':['同配方、同温度、同冰与杯型做 A/B；每次只改一个变量。','分别记录第一口和放置 2 分钟后的感受；保留原配方和修改量。'],
        'self_review':'推荐与 judge 共用规则，属于内部复核；只有实际试饮反馈能检验口味改进。'}


def inspect_ingredient(name):
    r=resolve(name)
    if r['status']!='matched':return r
    kb=knowledge();p=next(p for p in kb['profiles'] if p['ingredient_id']==r['ingredient']['id'])
    return {'version':kb['version'],'profile':p,'components':[c for c in kb['components'] if c['id'] in p['component_ids']],
        'potential_interactions':[r for r in kb['rules'] if set(r['requires'])&set(p['component_ids'])],
        'sources':[s for s in kb['sources'] if s['id'] in p['source_ids']]}


def knowledge_status(today=None):
    kb=knowledge();now=today or date.today()
    return {'version':kb['version'],'counts':{key:len(kb[key]) for key in ('sources','components','profiles','rules')},
            'sources':[{**s,'review_due':(date.fromisoformat(s['reviewed_at'])+timedelta(days=s['review_after_days'])).isoformat(),
                       'needs_review':now>=date.fromisoformat(s['reviewed_at'])+timedelta(days=s['review_after_days'])} for s in kb['sources']],
            'policy':'到期表示需要复查，并非旧论文自动失效。新证据与用户反馈分别记录；审核后更新版本，不自动把试饮偏好写成化学事实。'}

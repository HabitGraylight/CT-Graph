"""Sour candidates with traceable tradeoffs, never synthetic sensory scores."""
import copy
from . import engine, graph
from .normalization import resolve, parse_items

VERSION = 'sour-policy-2.0.0'


def recommend(frame='sour', recipe='', pantry='', avoid='', context=None, taster='local', method=None):
    from .learning import text_field
    text_field(taster,'taster',80)
    if not taster.strip(): raise ValueError('品鉴者不能为空')
    if frame != 'sour':
        return {'blocked': True, 'reason': '多候选闭环当前以 Sour 为样板；其他框架仍可使用原有评价和补全。'}
    if method not in {None,'','shake'}:
        return {'blocked':True,'reason':'此轮 Sour 对照采用摇和；其他技法请先单独评价，不自动覆盖已选方法。'}
    completed = engine.complete(frame, recipe, pantry, avoid, 'balanced', context, taster)
    if completed['blocked']: return completed
    base = completed['evaluation']; snap = copy.deepcopy(base['judge']['snapshot'])
    slots, extras = engine.assign(engine.get_frame(frame), base['items'])
    if (any(len(slots[s]) != 1 or slots[s][0]['ml'] is None for s in ('base','acid','sweet'))
            or any(set(i['ingredient']['roles']) - {'water'} for i in extras)
            or base['judge']['composition']['process_stage'] == 'whole_drink_transformation'):
        return {'blocked': True, 'reason': '此轮候选比较需要单一基酒、酸源和糖浆，且无未建模的整杯澄清；请先用 Judge 核对当前设计。', 'evaluation': base}
    sweet_item = slots['sweet'][0]
    if 'syrup' not in sweet_item['ingredient']['roles']:
        return {'blocked': True, 'reason': '当前控量策略只适用于可计量糖浆。'}
    base_trace=graph.from_evaluation(base)
    supported={n['id'].rsplit(':',1)[-1] for n in base_trace['nodes'] if n['type']=='MechanismClaim'}
    if 'sweet_acid' not in supported:
        return {'blocked':True,'reason':'当前证据图没有启用的酸甜机制断言，暂停生成糖浆干预，先复核知识版本。','evaluation':base,'trace':base_trace}
    syrup_spec=next((s for s in snap['context'].get('composition',[]) if resolve(s['name'])['ingredient']['id']==sweet_item['ingredient']['id']),{})
    if syrup_spec.get('sugar_g_l')==0:
        return {'blocked':True,'reason':'该糖浆已声明糖浓度为零，不能套用减少糖浆来降低糖量的策略；需另建甜味剂模型。','evaluation':base}
    index = base['items'].index(sweet_item); dose = sweet_item['ml']; delta = round(min(2.5, dose * .125), 3)
    if delta <= 0: return {'blocked': True, 'reason': '糖浆用量不足以构造可计量对照。'}
    less = copy.deepcopy(snap); less['recipe'][index].update(amount=round(dose-delta,3), unit='ml')
    swap = copy.deepcopy(less)
    water_index = next((i for i,x in enumerate(swap['recipe']) if x['name']=='water'),None)
    if water_index is None:
        water_index = len(swap['recipe']); swap['recipe'].append({'name':'water','amount':delta,'unit':'ml'})
        steps = swap['context'].get('process',{}).get('steps')
        if steps: next(s for s in steps if s['op']=='add')['uses'].append(water_index)
    else:
        old = base['items'][water_index]['ml']
        if old is None: return {'blocked':True,'reason':'水的用量需明确为可换算体积。'}
        swap['recipe'][water_index].update(amount=round(old+delta,3),unit='ml')
    specs = swap['context'].setdefault('composition',[])
    if not any(resolve(s['name'])['ingredient']['id']=='water' for s in specs):
        specs.append({'name':'water','abv':0,'sugar_g_l':0,'acid_g_l':0,'basis':'assumption','source':'本候选明确加入纯水的组成假设；不代表其他原料测量'})
    definitions = [
        ('reference','原版参照',snap,'保留已填写用量；缺少的槽位按编辑模板补全。','reference',[]),
        ('less_syrup','少量减糖浆',less,f'糖浆减少 {delta:g} ml；总体积也降低，其他成分浓度可能上升。','dose_change',['sweet_acid','aroma_partition']),
        ('water_swap','等体积替换糖浆',swap,f'糖浆减少 {delta:g} ml，同时加入 {delta:g} ml 纯水；可能减弱糖浆自身香气。','volume_preserving_substitution',['sweet_acid','aroma_partition']),
    ]
    candidates = []
    original_metrics = base['judge']['composition']['estimates']
    for key,title,snapshot,tradeoff,intervention,claims in definitions:
        evaluated = engine.evaluate(snapshot['frame'],snapshot['recipe'],snapshot['method'],snapshot['context'])
        trace = graph.from_evaluation(evaluated)
        changes = {}
        for metric, estimate in evaluated['judge']['composition']['estimates'].items():
            original = original_metrics[metric]['value']; value = estimate['value']
            changes[metric] = {'before':original,'after':value,'delta':round(value-original,3) if original is not None and value is not None else None,
                               'unit':estimate['unit'],'stage':estimate['stage']}
        matched_claims = [n['id'] for n in trace['nodes'] if n['type']=='MechanismClaim' and n['id'].rsplit(':',1)[-1] in claims]
        candidates.append({'id':key,'recipe_id':evaluated['judge']['recipe_id'],'title':title,
                           'snapshot':evaluated['judge']['snapshot'],'tradeoff':tradeoff,'intervention':intervention,
                           'composition_changes':changes,'evidence_ids':matched_claims,'trace':trace,
                           'evaluation':evaluated,'taste_prediction':None})
    from .experiments import preference
    if any(i['ingredient']['id']=='water' for i in parse_items(avoid)):
        candidates=[c for c in candidates if c['id']!='water_swap']
    from .runtime import PUBLIC_ONLY
    personal = ({'eligible_pairs':0,'preferred_intervention':None,'scope':'云端未接入本地 A/B 偏好'}
                if PUBLIC_ONLY.get() else preference(taster,base['judge']['recipe_id']))
    preferred = personal['preferred_intervention']
    for candidate in candidates:
        candidate['rank_basis'] = {'unresolved_action_risks':sum(r['level']=='action' for r in candidate['evaluation']['judge']['risks']),
                                   'personal_pairwise_support':candidate['intervention']==preferred if preferred else False}
    candidates.sort(key=lambda c:(c['rank_basis']['unresolved_action_risks'],not c['rank_basis']['personal_pairwise_support'],c['id']!='reference'))
    # Ingredient substitutions remain distinct suggestions until their actual composition is supplied.
    alternatives = []
    for slot in completed['alternatives']:
        for option in slot['options']:
            if option['in_pantry']:
                alternatives.append({**option,'slot':slot['slot'],'requires':'确认实际产品/加工状态和浓度后重新评价，不能默认等量等味。'})
    return {'blocked':False,'policy_version':VERSION,'frame':'sour','candidates':candidates,
            'generation_basis':'仅在证据图存在启用的酸甜交互断言时提出糖浆对照；断言支持试验问题，不证明候选更好喝。',
            'shopping':completed['shopping'],'completion_changes':completed['changes'],
            'pantry_alternatives':alternatives,'personal_evidence':personal,
            'ranking_policy':'先排除明确操作问题，再参考匹配品鉴者的已完成 A/B 偏好；无有效个人依据时原版优先。不是好喝概率。',
            'next_step':'选择两个候选生成随机呈现的 A/B 计划；实际制作后记录感官强度、七维质量和总体喜欢。'}

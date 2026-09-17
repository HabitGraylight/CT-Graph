"""Deterministic advisor. No network or model key required at runtime."""
import json
import math
from functools import lru_cache
from .knowledge import ROOT, FRAMEWORKS, INGREDIENTS, METHODS
from .normalization import BY_ID, parse_items, resolve, category_id, key

FRAMES={f['id']:f for f in FRAMEWORKS}

def get_frame(id):
    if id not in FRAMES: raise ValueError('请选择支持的调酒框架')
    return FRAMES[id]

@lru_cache(maxsize=1)
def corpus():
    with (ROOT/'data/aligned/recipes.jsonl').open(encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]

@lru_cache(maxsize=1)
def comparisons():
    with (ROOT/'data/aligned/comparisons.jsonl').open(encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]

def assign(frame,items):
    slots={s['id']:[] for s in frame['slots']}
    extras=[]
    for i in items:
        if i['status']!='matched':continue
        match=next((s for s in frame['slots'] if set(s['roles']) & set(i['ingredient']['roles'])),None)
        if match:slots[match['id']].append(i)
        else:extras.append(i)
    return slots,extras

def measured(slot,items):
    if not items:return 0.0
    amounts=[]
    for i in items:
        if slot['unit']=='ml':
            v=i['ml']
            if v is not None and 'syrup' in i['ingredient']['roles']:
                v*=i['ingredient']['sweetness']
        else:
            v=i['amount'] if i['unit']==slot['unit'] else None
        if v is None:return None
        amounts.append(v)
    return sum(amounts)

def nearest(items,limit=4):
    present={category_id(i['ingredient']['id']) for i in items if i['status']=='matched' and not set(i['ingredient']['roles'])&{'ice','garnish','water'}}
    ranked=[]
    for r in corpus():
        if r['dataset']!='iba_official':continue
        wanted={i['category_id'] for i in r['ingredients'] if i['category_id'] and i['category_id'] not in {'ice','water','egg_white'}}
        common=present&wanted
        if not common:continue
        unmapped=sum(not i['canonical_id'] for i in r['ingredients'])
        score=len(common)/(len(present|wanted)+unmapped)
        ranked.append({'id':r['id'],'name':r['canonical_name'],'name_zh':r['name_zh'],
                       'source_url':r['source_url'],'shared':sorted(common),'missing':sorted(wanted-present),
                       'ingredient_overlap':round(score*100),'unmapped_source_lines':unmapped,'note':'按原料类别重合度排序，未识别的来源原料计入分母；不是味觉相似度或配方忠实度。'})
    return sorted(ranked,key=lambda r:(-r['ingredient_overlap'],r['name']))[:limit]

def evaluate(frame_id,value,method=None,context=None):
    frame=get_frame(frame_id)
    if method and method not in METHODS:raise ValueError('制作技法无效')
    items=parse_items(value)
    slots,extras=assign(frame,items)
    unresolved=[i for i in items if i['status']!='matched']
    base=measured(frame['slots'][0],slots['base'])
    checks=[]
    suggestions=[]
    unknown_amounts=[]
    for s in frame['slots']:
        entries=slots[s['id']]
        v=measured(s,entries)
        missing=not entries
        ratio=v/base if s['unit']=='ml' and base and v is not None else v if s['unit']!='ml' else None
        low,high=s['low'],s['high']
        # Base sets scale; only the other ml slots are ratios to it.
        if s['id']=='base':
            ratio=1 if base else None
        fit=0.0
        state='missing' if missing else 'quantity_needed' if v is None else 'in_range'
        if not missing and v is None:
            unknown_amounts.append(s['label'])
        if ratio is not None and not missing:
            fit=1 if low<=ratio<=high else max(0,1-abs(ratio-(low if ratio<low else high))/max(high-low,.15))
            if fit<1:state='low' if ratio<low else 'high'
        if s['id']=='base' and base:fit=1
        target=round(s['amount']*((base or frame['slots'][0]['amount'])/frame['slots'][0]['amount']),1) if s['unit']=='ml' else s['amount']
        if state=='missing':suggestions.append(f"缺少{s['label']}：可先考虑 {BY_ID[s['default']]['zh']} {target:g} {s['unit']}。")
        elif state=='quantity_needed':suggestions.append(f"请补充{s['label']}的明确用量与单位；暂不换算不明确的 oz、吧匙、方糖或薄荷枝。")
        elif state in ('low','high'):
            suggestions.append(f"{s['label']}相对当前框架{'偏少' if state=='low' else '偏多'}，试配参照约 {target:g} {s['unit']}；这是风格提示，不代表配方无效。")
        checks.append({'slot':s['id'],'label':s['label'],'state':state,'value':v,'unit':s['unit'],
                       'ratio_to_base':round(ratio,3) if ratio is not None else None,'range':[low,high],
                       'fit':round(fit,3),'ingredients':[i['ingredient']['zh'] for i in entries],
                       'target':target})
    relevant_extras=[i for i in extras if not set(i['ingredient']['roles'])&{'ice','garnish','water','seasoning','foam'}]
    for i in relevant_extras:
        suggestions.append(f"{i['ingredient']['zh']}不属于此框架的核心槽位，可能改变风格；未计入酸甜比例。")
    if method and method not in frame['methods']:
        suggestions.append('此框架建议'+ ' / '.join(METHODS[m] for m in frame['methods'])+'。')
    if method=='shake' and any(i['status']=='matched' and 'carbonated' in i['ingredient']['roles'] for i in items):
        suggestions.append('气泡材料应在摇和结束后加入，不放入密闭摇壶摇和。')
    for i in items:
        if i['status']=='matched' and i['ingredient']['note']:
            suggestions.append(i['ingredient']['zh']+'：'+i['ingredient']['note'])
    for i in unresolved:
        suggestions.append(f"“{i['name']}”{'有多种解释，请确认具体品类或产品' if i['status']=='ambiguous' else '尚未识别，请选用词典名称或补充类型'}。")
    complete=sum(bool(v) for v in slots.values())/len(frame['slots'])
    fits=sum(c['fit'] for c in checks)/len(checks)
    technique=10 if method in frame['methods'] else 0
    # Extras are explicitly outside the calibration; suppress a misleading overall number.
    scorable=bool(items) and not unresolved and not unknown_amounts and not relevant_extras
    score=round((40*complete+40*fits+10+(technique if method else 0))/(100 if method else 90)*100) if scorable else None
    total_ml=sum(i['ml'] or 0 for i in items)
    if total_ml>250 and frame_id not in {'highball','mule','spritz','collins'}:
        suggestions.append('当前单杯总体积较大；可用份数缩放分杯，比例分不会因整体放大而变化。')
    result={'frame_id':frame_id,'score':score,'score_label':'框架契合度','taste_score':None,
            'score_explanation':'结构完整 40% + 槽位比例 40% + 输入清晰 10% + 技法 10%；未选技法时按其余 90 分折算。范围是编辑定义，不是实测好喝程度。',
            'confidence':'规则可评估，口味仍需试饮' if scorable else '信息不全或超出框架，暂不输出总分',
            'components':{'structure':round(40*complete,1),'proportion':round(40*fits,1),'clarity':10 if not unresolved and not unknown_amounts else None,'technique':technique if method else None},
            'items':items,'checks':checks,'suggestions':list(dict.fromkeys(suggestions)),
            'missing_slots':[c['label'] for c in checks if c['state']=='missing'],
            'nearest_classics':nearest(items),'sources':frame['source_urls'],'notes':[frame['note']],'total_measured_ml':round(total_ml,1)}
    from .judge import review
    result['judge']=review(result,method,context)
    return result

def ancestors(id):
    result={id}
    while BY_ID[id].get('parent'):
        id=BY_ID[id]['parent'];result.add(id)
    return result

def complete(frame_id,value='',pantry='',avoid='',preference='balanced',context=None,taster='local'):
    frame=get_frame(frame_id)
    from .judge import validate_context
    context=validate_context(context)
    personal=None
    if preference=='personal':
        from .learning import preference_profile
        personal=preference_profile(frame_id,taster)
        preference=personal['completion_preference']
    if preference not in ('balanced','drier'):raise ValueError('口味选项无效')
    original=parse_items(value)
    available=parse_items(pantry)
    excluded=parse_items(avoid)
    if any(i['status']!='matched' for i in excluded):
        raise ValueError('不使用的原料有歧义或未识别，请先用词典中的准确名称指定')
    excluded_ids={i['ingredient']['id'] for i in excluded}
    def allowed(ing):return not ancestors(ing['id'])&excluded_ids
    if any(i['status']!='matched' for i in original):
        return {'blocked':True,'reason':'请先确认配方中未识别或有歧义的原料，系统不会代猜。','unresolved':[i for i in original if i['status']!='matched']}
    if any(not allowed(i['ingredient']) for i in original):
        return {'blocked':True,'reason':'当前配方含有你设置不使用的原料；请先移除或调整。'}
    slots,extras=assign(frame,original)
    base=measured(frame['slots'][0],slots['base']) or frame['slots'][0]['amount']
    result=[];shopping=[];notes=[];changes=[]
    for s in frame['slots']:
        entries=slots[s['id']]
        target=s['amount']*base/frame['slots'][0]['amount'] if s['unit']=='ml' else s['amount']
        if preference=='drier' and s['id']=='sweet':target*=.8
        if entries:
            if len(entries)>1 and any(i['amount'] is None for i in entries) and any(i['amount'] is not None for i in entries):
                return {'blocked':True,'reason':f"{s['label']}有多种材料且只填写了部分用量，请先确认它们的分配比例。"}
            for i in entries:
                has_amount=i['amount'] is not None
                if has_amount and measured(s,[i]) is None:
                    return {'blocked':True,'reason':f"{i['name']}的用量单位无法用于该槽位，请明确单位后再补全；未覆盖你原来的用量。"}
                dose=i['amount'] if has_amount else target/len(entries)/i['ingredient']['sweetness'] if 'syrup' in i['ingredient']['roles'] else target/len(entries)
                result.append({'name':i['ingredient']['id'],'display_name':i['ingredient']['zh'],'amount':round(dose,2),'unit':i['unit'] if has_amount else s['unit'],
                               'origin':'kept' if has_amount else 'quantity_completed','slot':s['id']})
                if not has_amount:changes.append(f"为{i['ingredient']['zh']}补充试配用量。")
            continue
        options=[i for i in available if i['status']=='matched' and allowed(i['ingredient']) and set(i['ingredient']['roles'])&set(s['roles'])]
        options.sort(key=lambda i:(i['ingredient']['id']!=s['default'],i['ingredient']['id']))
        selected=options[0]['ingredient'] if options else BY_ID[s['default']] if allowed(BY_ID[s['default']]) else next((i for i in INGREDIENTS if allowed(i) and set(i['roles'])&set(s['roles'])),None)
        if selected is None:
            return {'blocked':True,'reason':f"在当前排除条件下，找不到{s['label']}的合适材料。"}
        dose=target/selected['sweetness'] if 'syrup' in selected['roles'] else target
        line={'name':selected['id'],'display_name':selected['zh'],'amount':round(dose,2),'unit':s['unit'],
              'origin':'pantry' if options else 'shopping','slot':s['id']}
        result.append(line)
        if not options:shopping.append(line)
        changes.append(f"用{'现有' if options else '待补充的'}{selected['zh']}填入{s['label']}。")
    for i in extras:
        result.append({'name':i['ingredient']['id'],'display_name':i['ingredient']['zh'],'amount':i['amount'],'unit':i['unit'],'origin':'kept','slot':'extra'})
    unresolved=[i for i in available if i['status']!='matched']
    if unresolved:notes.append('库存中有未识别或有歧义的名称，未将它们算作已经拥有的材料。')
    if preference=='drier':notes.append('偏干选项只对新补充的糖浆减少 20%；保留已填写用量，不替你重写配方。')
    notes.extend(['库存按有无匹配，不计算瓶中剩余量。','这是传统结构启发的试配草案；建议的评分只说明规则内部契合，未经过实际试饮。'])
    scored=evaluate(frame_id,result,frame['methods'][0],context)
    alternatives=[]
    in_pantry={i['ingredient']['id'] for i in available if i['status']=='matched'}
    used={i['name'] for i in result}
    for s in frame['slots']:
        candidates=[i for i in INGREDIENTS if i['id'] not in used and allowed(i) and set(i['roles'])&set(s['roles'])]
        candidates.sort(key=lambda i:(i['id'] not in in_pantry,bool(i['brand']),i['id']))
        alternatives.append({'slot':s['label'],'options':[{'id':i['id'],'name':i['zh'],'in_pantry':i['id'] in in_pantry,
                             'note':i['note'] or '可承担相同结构角色，但香气与口感会变化，需重新试配。'} for i in candidates[:3]]})
    from .learning import improve
    refinement=improve(frame_id,result,frame['methods'][0],context,avoid=avoid) if any(r['level'] in {'action','design'} for r in scored['judge']['risks']) else None
    return {'blocked':False,'recipe':result,'shopping':shopping,'changes':changes,'method':frame['methods'][0],
            'steps':frame['steps'],'notes':notes+[frame['note']],'unresolved_pantry':unresolved,'evaluation':scored,
            'sources':frame['source_urls'],'alternatives':alternatives,'optional':[BY_ID[x] for x in frame['optional'] if allowed(BY_ID[x])],
            'personal_preference':personal,'refinement':refinement}

def catalog():
    stats=json.loads((ROOT/'data/aligned/stats.json').read_text(encoding='utf-8'))
    return {'frameworks':FRAMEWORKS,'ingredients':INGREDIENTS,'methods':METHODS,'stats':stats,
            'comparison_groups':[{'name':c['name'],'name_key':c['name_key'],'versions':len(c['version_ids'])} for c in comparisons()]}

def compare(name):
    from .normalization import drink_name
    name_key=key(drink_name(name))
    versions=[r for r in corpus() if r['name_key']==name_key]
    return {'name_key':name_key,'versions':versions,'comparison':next((c for c in comparisons() if c['name_key']==name_key),None)}

def pantry_matches(value):
    items=parse_items(value)
    present={category_id(i['ingredient']['id']) for i in items if i['status']=='matched'}
    available=[];shopping={}
    for r in corpus():
        if r['dataset']!='iba_official':continue
        core=[i for i in r['ingredients'] if not (i['canonical_id'] and set(BY_ID[i['canonical_id']]['roles'])&{'ice','water','garnish'})
              and not i['original'].get('optional') and '(optional)' not in str(i['original'].get('name','')).lower()]
        unresolved=[i for i in core if not i['canonical_id']]
        if unresolved:continue # Never claim a recipe is makeable by ignoring unmapped ingredients.
        required={i['category_id'] for i in core}
        missing=required-present
        if len(missing)<=1:
            available.append({'name':r['canonical_name'],'name_zh':r['name_zh'],'missing':list(missing),'source_url':r['source_url'],
                              'note':'按原料类别匹配，仍需查看用量、品牌风格和技法。'})
        if len(missing)==1:
            mid=next(iter(missing));shopping[mid]=shopping.get(mid,0)+1
    return {'items':items,'recipes':sorted(available,key=lambda x:(len(x['missing']),x['name'])),
            'shopping_priority':[{'id':id,'name':BY_ID[id]['zh'],'unlocks':count} for id,count in sorted(shopping.items(),key=lambda t:(-t[1],t[0]))[:8]],
            'scope':'仅匹配原料已全部识别的 IBA 配方；按有无，不核算剩余量。'}

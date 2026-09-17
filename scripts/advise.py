"""JSON interface for using the advisor from an assistant or shell."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cocktail import engine, judge, learning
from cocktail.knowledge import FRAMEWORKS
from cocktail.normalization import parse_items

ACTIONS = ['evaluate','judge','complete','improve','feedback','history','profile','knowledge','knowledge_review','knowledge_note','compare','pantry','catalog','resolve','frameworks']

def compact(result, action):
    """Keep evidence and blockers, omit repeated vocabulary payloads."""
    def item(i):
        r={k:i[k] for k in ('name','status','amount','unit','ml') if k in i}
        if i.get('ingredient'):
            r['canonical_id']=i['ingredient']['id'];r['canonical_name']=i['ingredient']['zh']
        if i.get('choices'):
            r['choices']=[{'id':c['id'],'name':c['zh']} for c in i['choices']]
        return r
    def evaluation(r):
        return {**r,'items':[item(i) for i in r['items']]}
    if action in ('evaluate','judge'):return evaluation(result)
    if action=='improve':
        return {**result,**{k:evaluation(result[k]) for k in ('before','after') if k in result}}
    if action=='resolve':return {'items':[item(i) for i in result['items']]}
    if action=='complete':
        result=dict(result)
        if result.get('evaluation'):result['evaluation']=evaluation(result['evaluation'])
        for k in ('unresolved','unresolved_pantry'):
            if k in result:result[k]=[item(i) for i in result[k]]
        if 'optional' in result:result['optional']=[{'id':i['id'],'name':i['zh'],'note':i['note']} for i in result['optional']]
        return result
    if action=='pantry':return {**result,'items':[item(i) for i in result['items']]}
    return result

def dispatch(request):
    if not isinstance(request,dict):raise ValueError('请求需要是 JSON 对象')
    permitted={'action','frame','recipe','pantry','avoid','method','preference','name','context','tasting','request_id','feedback_id','parent_trial_id','supersedes_trial_id','taster','rule_id','url','finding'}
    if set(request)-permitted:raise ValueError('不支持的字段：'+','.join(sorted(set(request)-permitted)))
    action=request.get('action')
    if action not in ACTIONS:raise ValueError('请求需要提供有效 action')
    new_fields={'context','tasting','request_id','feedback_id','parent_trial_id','supersedes_trial_id','taster','rule_id','url','finding'}
    supported={
        'evaluate':{'context'},'judge':{'context'},'complete':{'context','taster'},
        'improve':{'context','feedback_id'},'feedback':{'context','tasting','request_id','parent_trial_id','supersedes_trial_id'},
        'profile':{'taster'},'knowledge_note':{'rule_id','url','finding','request_id'}}
    if (set(request)&new_fields)-supported.get(action,set()):raise ValueError('当前 action 不支持提供的附加字段')
    if action in ('evaluate','judge'):result=engine.evaluate(request.get('frame','sour'),request.get('recipe',''),request.get('method'),request.get('context'))
    elif action=='complete':result=engine.complete(request.get('frame','sour'),request.get('recipe',''),request.get('pantry',''),request.get('avoid',''),request.get('preference','balanced'),request.get('context'),request.get('taster','local'))
    elif action=='improve':result=learning.improve(request.get('frame'),request.get('recipe'),request.get('method'),request.get('context'),request.get('feedback_id'),request.get('avoid',''))
    elif action=='feedback':result=learning.save_feedback(request.get('frame','sour'),request.get('recipe',''),request.get('method'),request.get('context'),request.get('tasting'),request.get('request_id'),request.get('parent_trial_id'),request.get('supersedes_trial_id'))
    elif action=='history':result={'trials':learning.records(),'evidence_notes':learning.records('evidence')}
    elif action=='profile':result=learning.preference_profile(request.get('frame'),request.get('taster','local'))
    elif action=='knowledge':result=judge.inspect_ingredient(request.get('name','lemon_juice'))
    elif action=='knowledge_review':result={**judge.knowledge_status(),'pending_evidence':learning.records('evidence')}
    elif action=='knowledge_note':result=learning.evidence_note(request.get('rule_id'),request.get('url'),request.get('finding'),request.get('request_id'))
    elif action=='compare':result=engine.compare(request.get('name','Negroni'))
    elif action=='pantry':result=engine.pantry_matches(request.get('pantry',''))
    elif action=='resolve':result={'items':parse_items(request.get('recipe',request.get('pantry','')))}
    elif action=='frameworks':result={'frameworks':[{k:f[k] for k in ('id','zh','formula','slots','methods','note','source_urls')} for f in FRAMEWORKS]}
    else:result=engine.catalog()
    return result

def main():
    p=argparse.ArgumentParser(description='本地鸡尾酒建议：评分、补全、配方对照、材料架匹配')
    p.add_argument('action',choices=ACTIONS,nargs='?')
    p.add_argument('--request',type=Path,help='UTF-8 JSON 请求文件；支持结构化原料列表')
    p.add_argument('--compact',action='store_true',help='减少重复的词典属性，保留解释和来源')
    p.add_argument('--frame',default='sour')
    p.add_argument('--recipe',default='')
    p.add_argument('--pantry',default='')
    p.add_argument('--avoid',default='')
    p.add_argument('--method',default=None)
    p.add_argument('--preference',default='balanced')
    p.add_argument('--name',default='Negroni')
    args=p.parse_args()
    try:
        if args.request:
            if args.action:raise ValueError('--request 与位置 action 不能同时使用')
            request=json.loads(args.request.read_text(encoding='utf-8-sig'))
        else:
            request={k:getattr(args,k) for k in ('action','frame','recipe','pantry','avoid','method','preference','name')}
        result=dispatch(request)
        if args.compact:result=compact(result,request['action'])
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,TypeError,OSError) as e:
        print(json.dumps({'error':str(e)},ensure_ascii=False))
        return 1
    return 0

if __name__=='__main__':sys.exit(main())

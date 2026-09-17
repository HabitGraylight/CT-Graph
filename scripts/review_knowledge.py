"""Publish a locally reviewed knowledge candidate, with immutable prior versions."""
import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cocktail.knowledge import ROOT, INGREDIENTS
from cocktail.judge import DIMENSIONS


def validate(data):
    if data.get('schema_version')!=1:raise ValueError('schema_version 必须为 1')
    if not isinstance(data.get('version'),str) or not data['version'].strip():raise ValueError('需要非空版本号')
    date.fromisoformat(data['reviewed_at'])
    groups={}
    for group in ('sources','components','profiles','rules'):
        key='ingredient_id' if group=='profiles' else 'id'
        ids=[r[key] for r in data[group]]
        if len(ids)!=len(set(ids)):raise ValueError(group+' ID 重复')
        groups[group]=set(ids)
    if groups['profiles']!={i['id'] for i in INGREDIENTS}:raise ValueError('原料档案须覆盖现有词典，未知内容应明确留空')
    dims={d[0] for d in DIMENSIONS}
    for source in data['sources']:
        if not source['url'].startswith('https://'):raise ValueError('来源需 HTTPS URL')
        if date.fromisoformat(source['reviewed_at'])>date.today():raise ValueError('复核日期不能在未来')
        if type(source['review_after_days']) is not int or not 1<=source['review_after_days']<=3650:raise ValueError('复核间隔无效')
        if not source.get('scope') or not source.get('evidence_type'):raise ValueError('来源需描述证据范围与类型')
    for group in ('components','profiles','rules'):
        for r in data[group]:
            if not set(r['source_ids'])<=groups['sources']:raise ValueError('存在悬空来源引用')
            if group in ('components','rules') and (not r['source_ids'] or not set(r['dimensions'])<=dims):raise ValueError('维度或证据引用无效')
            if group=='profiles' and not set(r['component_ids'])<=groups['components']:raise ValueError('成分引用无效')
            if group=='rules':
                if not r['requires'] or not set(r['requires'])<=groups['components']:raise ValueError('触发条件无效')
                if r['numeric_score_effect'] is not None:raise ValueError('未经感官校准的机制不能直接产生分数')
                if r['status'] not in {'active','retired'}:raise ValueError('规则状态无效')
                if not all(isinstance(r.get(k),str) and r[k].strip() for k in ('title','effect','conditions','verification')):raise ValueError('规则需提供机制、条件、验证方法')
    return {key:len(value) for key,value in groups.items()}


def publish(candidate,reason):
    path=Path(candidate).resolve()
    if not path.is_relative_to(ROOT.resolve()):raise ValueError('候选知识文件须在项目内')
    target=ROOT/'data/knowledge/judge.json'
    if path==target:raise ValueError('请使用单独候选文件，保留线上知识供对照')
    data=json.loads(path.read_text(encoding='utf-8-sig'));counts=validate(data)
    old=target.read_bytes();prior=json.loads(old)
    if data['version']==prior['version']:raise ValueError('审核发布必须使用新版本号')
    if not reason.strip():raise ValueError('请记录审核理由及证据变化')
    archive=ROOT/'data/knowledge/history';archive.mkdir(parents=True,exist_ok=True)
    sha=hashlib.sha256(old).hexdigest()
    previous=archive/(sha+'.json')
    if not previous.exists():previous.write_bytes(old)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    audit={'from':prior['version'],'to':data['version'],'previous_sha256':sha,'reviewed_at':datetime.now(timezone.utc).isoformat(),'reason':reason}
    candidate_bytes=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    audit['new_sha256']=hashlib.sha256(candidate_bytes).hexdigest()
    # A staged file and atomic rename keep readers from seeing partially written JSON.
    staged=target.with_suffix('.next.json');staged.write_bytes(candidate_bytes)
    staged.replace(target)
    (archive/(stamp+'.audit.json')).write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    return {**audit,'counts':counts}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--reason');p.add_argument('--check',action='store_true');a=p.parse_args()
    try:
        result=validate(json.loads(Path(a.candidate).read_text(encoding='utf-8-sig'))) if a.check else publish(a.candidate,a.reason or '')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,KeyError,TypeError,OSError) as e:print(str(e),file=sys.stderr);sys.exit(1)

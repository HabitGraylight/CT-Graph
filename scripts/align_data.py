"""Build separate aligned views without changing the source corpus."""
import json
import re
import sys
from collections import Counter,defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cocktail.knowledge import ROOT,INGREDIENTS,FRAMEWORKS,DRINK_ALIASES
from cocktail.normalization import resolve,drink_name,key,unit_key,category_id,numeric

OUT = ROOT/'data/aligned'
OUT.mkdir(parents=True,exist_ok=True)
def lines(path):
    with path.open(encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]
def write(name,rows):
    with (OUT/(name+'.jsonl')).open('w',encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r,ensure_ascii=False)+'\n')

def source_ingredient(i):
    name = i.get('name')
    if not name:
        raw = i.get('raw')
        name = raw.get('special') if isinstance(raw,dict) else None
    r = resolve(name or '')
    # Conservative prefix repair for already documented textual source quantities.
    if r['status']=='unknown' and name:
        cleaned = re.sub(r'^(?:few\s+(?:dashes|drops)(?:\s+of)?|(?:a\s+)?splash\s+of|dash\s+of|(?:fill\s+up|top)\s+with|\d+\s*(?:teaspoons?|tablespoons?|pcs|fresh|strong)?|of)\s+', '', name,flags=re.I)
        cleaned = re.sub(r'\s*\(optional\)\s*$','',cleaned,flags=re.I)
        if cleaned != name:
            candidate = resolve(cleaned)
            if candidate['status']=='matched':
                r=candidate
                r['repair']='removed_quantity_prefix; original retained'
    return {'original':i,'status':r['status'],'canonical_id':r.get('ingredient',{}).get('id'),
            'canonical_name_zh':r.get('ingredient',{}).get('zh'),'brand':r.get('ingredient',{}).get('brand'),
            'category_id':category_id(r['ingredient']['id']) if r['status']=='matched' else None,
            'amount_ml':i.get('amount_ml'),'amount_raw':i.get('amount_raw'),'unit':unit_key(i.get('unit_raw') or ''),
            'repair':r.get('repair'),'choices':[x['id'] for x in r.get('choices',[])]}

def main():
    recipes=lines(ROOT/'data/processed/recipes.jsonl')
    sources={s['id']:s for s in lines(ROOT/'data/processed/sources.jsonl')}
    result=[]
    unresolved=Counter()
    groups=defaultdict(list)
    for r in recipes:
        ingredients=[source_ingredient(i) for i in r['ingredients']]
        for i in ingredients:
            if i['status']!='matched':
                unresolved[str(i['original'].get('name') or i['original'].get('raw'))]+=1
        name=drink_name(r['name'])
        row={'id':r['id'],'name':r['name'],'canonical_name':name,'name_key':key(name),
             'name_zh':next(iter(DRINK_ALIASES.get(name,[])),None),'dataset':r['dataset'],'source_id':r['source_id'],
             'source_url':sources[r['source_id']]['url'],'ingredients':ingredients,'instructions':r.get('instructions'),
             'glass':r.get('glass'),'garnish':r.get('garnish'),'method':r.get('method'),
             'license_status':r.get('license_status'),'alignment_status':'exact_aliases_and_audited_prefix_repairs; unresolved_retained'}
        result.append(row)
        groups[key(name)].append(row)
    comparisons=[]
    for name,vs in groups.items():
        if len(vs)<2:
            continue
        ref=next((v for v in vs if v['dataset']=='iba_official'),vs[0])
        def quantities(v):
            values=defaultdict(list)
            for i in v['ingredients']:
                ident=i['category_id'] or 'unresolved:'+str(i['original'].get('name'))
                values[ident].append({'ml':i['amount_ml'],'raw':i['amount_raw'],'unit':i['unit'],'ingredient_id':i['canonical_id']})
            return dict(values)
        rv=quantities(ref)
        differences=[]
        for v in vs:
            if v['id']==ref['id']:continue
            vv=quantities(v)
            changes=[]
            for ident in sorted(set(rv)|set(vv)):
                left,right=rv.get(ident),vv.get(ident)
                kind=None
                if left is None:kind='added_ingredient'
                elif right is None:kind='omitted_ingredient'
                elif ident.startswith('unresolved:'):kind='unresolved_name'
                elif all(x['ml'] is not None for x in left+right):
                    delta=sum(x['ml'] for x in right)-sum(x['ml'] for x in left)
                    if abs(delta)>1e-6:kind='metric_quantity_changed'
                    elif {x['ingredient_id'] for x in left}!={x['ingredient_id'] for x in right}:kind='product_changed_same_metric_quantity'
                else:
                    def comparable(xs):
                        out=[]
                        for x in xs:
                            try:n=numeric(x['raw'])
                            except ValueError:n=None
                            out.append((x['ingredient_id'],x['unit'],n))
                        return sorted(out,key=str)
                    if comparable(left)!=comparable(right):kind='unit_or_quantity_incomparable'
                    elif any(x['raw'] is None for x in left+right):kind='quantity_not_specified'
                if kind:
                    change={'ingredient_category':ident,'reference':left,'variant':right,'comparison':kind}
                    if kind=='metric_quantity_changed':change['delta_ml']=round(delta,3)
                    changes.append(change)
            differences.append({'variant_id':v['id'],'ingredient_differences':changes,
                                'instructions_differ':v['instructions']!=ref['instructions'],'glass_differ':v['glass']!=ref['glass'],
                                'garnish_differ':v['garnish']!=ref['garnish']})
        comparisons.append({'name_key':name,'name':ref['canonical_name'],'reference_id':ref['id'],
                            'reference_reason':'IBA official' if ref['dataset']=='iba_official' else 'first available; no authority implied',
                            'version_ids':[v['id'] for v in vs],'differences':differences})
    write('recipes',result)
    write('comparisons',comparisons)
    write('unresolved',[{'name':k,'occurrences':v} for k,v in unresolved.most_common()])
    (OUT/'ingredients.json').write_text(json.dumps(INGREDIENTS,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'frameworks.json').write_text(json.dumps(FRAMEWORKS,ensure_ascii=False,indent=2),encoding='utf-8')
    stats={'recipes':len(result),'canonical_ingredients':len(INGREDIENTS),'frameworks':len(FRAMEWORKS),
           'ingredient_lines':sum(len(r['ingredients']) for r in result),'matched_lines':sum(i['status']=='matched' for r in result for i in r['ingredients']),
           'comparison_groups':len(comparisons),'official_with_other_versions':sum(any(v['dataset']=='iba_official' for v in groups[c['name_key']]) for c in comparisons),
           'unresolved_labels':len(unresolved)}
    (OUT/'stats.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(stats,ensure_ascii=False,indent=2))

if __name__=='__main__':main()

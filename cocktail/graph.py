"""Versioned domain graph projections, with explicit identity and evidence boundaries."""
import hashlib
import json
from .normalization import BY_ID, resolve
from . import design

VERSION = '2.0.0'


def identity(kind, value):
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()[:24]
    return f'{kind}:{digest}'


class Graph:
    def __init__(self):
        self.nodes = {}; self.edges = []; self.edge_keys = set()

    def node(self, id, type, **attrs):
        value = dict(id=id, type=type, **attrs)
        existing=self.nodes.get(id,{})
        if any(existing[k]!=v for k,v in value.items() if k in existing):
            raise ValueError('Graph identity conflict: ' + id)
        self.nodes[id] = {**existing,**value}
        return id

    def edge(self, source, relation, target):
        edge = dict(source=source, relation=relation, target=target)
        key=(source,relation,target)
        if key not in self.edge_keys:
            self.edges.append(edge); self.edge_keys.add(key)

    def export(self):
        if any(e['source'] not in self.nodes or e['target'] not in self.nodes for e in self.edges):
            raise ValueError('Graph has dangling references')
        return {'schema_version': VERSION, 'privacy': 'local_only',
                'nodes': list(self.nodes.values()), 'edges': self.edges,
                'semantics': '领域与证据关系图；不是已识别或拟合的因果 DAG。'}


def ingredient(g, id):
    item = BY_ID[id]
    key = g.node('ingredient:' + id, 'Product' if item['brand'] else 'IngredientCategory',
                 label=item['zh'], en=item['en'], roles=item['roles'])
    if item['parent']: g.edge(key, 'IS_A', ingredient(g, item['parent']))
    if item['brand']:
        brand = g.node(identity('brand', item['brand']), 'Brand', label=item['brand'])
        g.edge(key, 'BRANDED_BY', brand)
    return key


def evidence(g, review, recipe_id):
    source_prefix='source:'+review['knowledge_hash']+':'
    for source in review['sources']:
        g.node(source_prefix + source['id'], 'Source', **{k:v for k,v in source.items() if k!='id'})
    for rule in review['interactions']:
        cid = g.node(f"claim:{review['knowledge_hash']}:{rule['id']}", 'MechanismClaim',
                     label=rule['title'], statement=rule['effect'], conditions=rule['conditions'],
                     kind=rule['kind'], status=rule['status'], effect_size=None,
                     verification=rule['verification'],
                     version=review['version'], required_components=rule['requires'])
        application=g.node(identity('claim-application',[recipe_id,cid]),'MechanismApplication',applicability=rule['application'])
        g.edge(recipe_id,'HAS_MECHANISM_APPLICATION',application);g.edge(application,'APPLIES_CLAIM',cid)
        for sid in rule['source_ids']: g.edge(cid, 'SUPPORTED_BY', source_prefix + sid)
    for source in review['design_review']['sources']:
        g.node('design-source:' + design.VERSION + ':' + source['id'], 'Source', **{k:v for k,v in source.items() if k!='id'})
    for prompt in review['design_review']['prompts']:
        cid = g.node(f"design-claim:{design.VERSION}:{prompt['id']}", 'DesignClaim',
                     statement=prompt['message'], verification=prompt['verification'],
                     evidence_kind=prompt['evidence_kind'], numeric_score_effect=None)
        for sid in prompt['source_ids']: g.edge(cid, 'INFORMED_BY', 'design-source:' + design.VERSION + ':' + sid)


def from_evaluation(evaluation):
    g = Graph(); review = evaluation['judge']; snap = review['snapshot']; c = snap['context']
    rid = g.node('recipe:' + review['recipe_id'], 'RecipeVersion', frame=snap['frame'], method=snap['method'])
    frame = g.node('framework:' + snap['frame'], 'Framework', role='editorial_reference')
    g.edge(rid, 'USES_FRAMEWORK', frame)
    for classic in evaluation.get('nearest_classics',[]):
        ref=g.node('reference-recipe:'+classic['id'],'ReferenceRecipeVersion',label=classic['name'],url=classic['source_url'])
        match=g.node(identity('reference-match',[rid,classic['id']]),'ReferenceMatch',
                     ingredient_overlap=classic['ingredient_overlap'],basis='ingredient_categories_not_exact_recipe_or_taste')
        g.edge(rid,'HAS_REFERENCE_MATCH',match);g.edge(match,'REFERS_TO',ref)
    materials = {resolve(m['name'])['ingredient']['id']:m for m in c.get('materials', [])}
    specs = {resolve(m['name'])['ingredient']['id']:m for m in c.get('composition', [])}
    for index, item in enumerate(evaluation['items']):
        use = g.node(f'{rid}:use:{index}', 'IngredientUse', amount=item['amount'], unit=item['unit'], ml=item['ml'])
        g.edge(rid, 'HAS_USE', use)
        resolution = g.node(f'{rid}:resolution:{index}', 'Resolution', expression=item['name'],
                            status=item['status'], candidates=[x['id'] for x in item.get('choices', [])])
        g.edge(use, 'HAS_RESOLUTION', resolution)
        if item['status'] != 'matched': continue
        key = item['ingredient']['id']; canonical = ingredient(g, key)
        g.edge(resolution, 'RESOLVES_TO', canonical)
        selected = canonical
        if key in materials:
            record = {**materials[key], 'name': key}
            version = {k:v for k,v in record.items() if k!='batch'}
            selected = g.node(identity('product-variant', version), 'ProductVariant', **version,
                              basis='user_declared_not_verified_product_equivalence')
            g.edge(selected, 'INSTANCE_OF', canonical)
            if 'batch' in record:
                batch = g.node(identity('batch', record), 'Batch', label=record['batch'], basis='user_declared')
                g.edge(batch, 'BATCH_OF', selected); selected = batch
        g.edge(use, 'USES_MATERIAL', selected)
        if key in specs:
            spec = {**specs[key], 'name': key}
            mid = g.node(identity('measurement', [selected, spec]), 'CompositionRecord', **spec)
            g.edge(use, 'USES_COMPOSITION', mid); g.edge(mid, 'MEASURES', selected)
    previous = rid
    for state in review['composition']['process_trace']['states']:
        step = g.node(f"{rid}:step:{state['index']}", 'ProcessStep', **c['process']['steps'][state['index']])
        sid = g.node(f"{rid}:state:{state['index']}", 'MixtureState', **state)
        g.edge(previous, 'INPUT_TO', step); g.edge(step, 'PRODUCES_STATE', sid); previous = sid
    evidence(g, review, rid)
    for node in list(g.nodes.values()):
        if node['type'] in {'MechanismClaim', 'DesignClaim'}: g.edge(rid, 'REVIEWED_WITH', node['id'])
    result = g.export(); result['recipe_id'] = rid
    return result


def reference_graph(recipes):
    """Bridge aligned source recipes without mutating or merging their original versions."""
    g = Graph(); matched = total = 0
    for row in recipes:
        rid = g.node('reference-recipe:' + row['id'], 'ReferenceRecipeVersion', label=row.get('canonical_name',row['name']),dataset=row['dataset'],url=row['source_url'])
        source = g.node('reference-source:' + row['source_id'], 'Source', url=row['source_url'])
        g.edge(rid, 'DERIVED_FROM', source)
        for index, item in enumerate(row['ingredients']):
            total += 1
            use = g.node(f'{rid}:use:{index}', 'IngredientUse', original=item['original'], ml=item['amount_ml'])
            g.edge(rid, 'HAS_USE', use)
            resolution = g.node(f'{rid}:resolution:{index}', 'Resolution', status=item['status'],
                                repair=item.get('repair'), candidates=item.get('choices', []))
            g.edge(use, 'HAS_RESOLUTION', resolution)
            if item['canonical_id']:
                matched += 1; g.edge(resolution, 'RESOLVES_TO', ingredient(g, item['canonical_id']))
    result = g.export(); result['coverage'] = {'ingredient_lines': total, 'matched_lines': matched}
    return result

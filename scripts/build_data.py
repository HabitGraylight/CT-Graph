"""Offline normalization and evidence graph; never invent missing measurements."""
import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from urllib.parse import unquote
from bs4 import BeautifulSoup
from collect import ROOT, RAW

OUT = ROOT / 'data' / 'processed'
OUT.mkdir(parents=True, exist_ok=True)
def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))
def write(name, rows):
    with (OUT / (name + '.jsonl')).open('w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(s)).casefold()).strip()
def uid(kind, value):
    return kind + ':' + hashlib.sha256(norm(value).encode()).hexdigest()[:20]
def number(v):
    if v is None or isinstance(v, bool):
        return None
    try:
        parts = str(v).strip().split()
        if len(parts) == 2:
            return float(Fraction(parts[0]) + Fraction(parts[1]))
        return float(Fraction(str(v)))
    except (ValueError, ZeroDivisionError):
        return None

recipes, documents, sources, history, issues = [], [], [], [], []
nodes, edges = {}, []
def node(kind, label, **attrs):
    key = uid(kind, label)
    if key not in nodes:
        nodes[key] = {'id': key, 'type': kind, 'label': label, **attrs}
    return key
def edge(a, relation, b, source_id, **attrs):
    edges.append({'from': a, 'relation': relation, 'to': b, 'source_id': source_id, **attrs})
def source(path, dataset, url=None, license='unknown'):
    sid = uid('source', str(path.relative_to(ROOT)))
    mp = path.with_suffix(path.suffix + '.meta.json')
    meta = read(mp) if mp.exists() else read(RAW / dataset / 'repository.zip.meta.json')
    row = {'id': sid, 'dataset': dataset, 'url': url or meta['url'], 'raw_path': path.relative_to(ROOT).as_posix(),
           'retrieved_at': meta['retrieved_at'], 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'license': license,
           'snapshot_url': meta['url'], 'snapshot_sha256': meta['sha256']}
    sources.append(row)
    nodes[sid] = {'id': sid, 'type': 'source', 'label': row['url']}
    return sid

def ingredient(name, amount=None, unit=None, raw=None, **extra):
    n = number(amount)
    # Only unambiguous metric units. oz, spoon, dash and historical measures stay raw.
    factor = {'ml': 1, 'cl': 10, 'l': 1000}.get(norm(unit or ''))
    return {'name': name or None, 'amount_raw': amount, 'unit_raw': unit,
            'amount_numeric': n, 'amount_ml': n * factor if n is not None and factor is not None else None,
            'raw': raw, **extra}

def add_recipe(row):
    recipes.append(row)
    rid, sid = row['id'], row['source_id']
    nodes[rid] = {'id': rid, 'type': 'recipe_version', 'label': row['name'], 'dataset': row['dataset']}
    drink = node('drink_name', row['name'], grouping_rule='NFKC + casefold + whitespace; name grouping, not identity proof')
    edge(drink, 'HAS_RECIPE_VERSION', rid, sid)
    edge(rid, 'SOURCED_FROM', sid, sid)
    for i, ing in enumerate(row['ingredients']):
        if ing['name']:
            unresolved = ing.get('parse_status') == 'unparsed_line'
            iid = node('ingredient_expression' if unresolved else 'ingredient', ing['name'])
            if unresolved:
                issues.append({'recipe_id': rid, 'issue': 'unparsed_ingredient_line', 'position': i + 1, 'raw': ing['raw']})
            edge(rid, 'HAS_UNPARSED_INGREDIENT' if unresolved else 'USES_INGREDIENT', iid, sid, position=i + 1,
                 amount_raw=ing['amount_raw'], unit_raw=ing['unit_raw'], amount_ml=ing['amount_ml'], optional=ing.get('optional'))
            for sub in ing.get('substitutes', []):
                if sub.get('name'):
                    edge(iid, 'HAS_RECIPE_SPECIFIC_SUBSTITUTE', node('ingredient', sub['name']), sid, recipe_id=rid)
        else:
            issues.append({'recipe_id': rid, 'issue': 'ingredient_name_missing', 'position': i + 1, 'raw': ing['raw']})
    for field, kind, rel in [('glass', 'glass', 'SERVED_IN'), ('method', 'method', 'USES_METHOD')]:
        if row.get(field):
            edge(rid, rel, node(kind, row[field]), sid)
    for tag in row.get('tags', []):
        edge(rid, 'HAS_SOURCE_TAG', node('tag', tag), sid)
    if not row['ingredients']:
        issues.append({'recipe_id': rid, 'issue': 'no_structured_ingredients'})
    if not row.get('instructions'):
        issues.append({'recipe_id': rid, 'issue': 'missing_instructions'})

def build_repositories():
    base = RAW / 'bar_assistant' / 'files'
    for p in sorted((base / 'data' / 'cocktails').glob('*/data.json')):
        d = read(p)
        sid = source(p, 'bar_assistant', 'https://github.com/bar-assistant/data/blob/main/' + p.relative_to(base).as_posix())
        add_recipe({'id': uid('recipe', 'bar_assistant/' + p.parent.name), 'name': d['name'], 'dataset': 'bar_assistant', 'source_id': sid,
                    'ingredients': [ingredient(x.get('name'), x.get('amount'), x.get('units'), x, optional=x.get('optional'), substitutes=x.get('substitutes', []), amount_max=x.get('amount_max'), note=x.get('note')) for x in d.get('ingredients', [])],
                    'instructions': d.get('instructions'), 'garnish': d.get('garnish'), 'description': d.get('description'),
                    'glass': d.get('glass'), 'method': d.get('method'), 'tags': d.get('tags', []), 'upstream_source': d.get('source'),
                    'source_abv_unverified': d.get('abv'), 'license_status': 'unknown_in_downloaded_snapshot'})
    for p in sorted((base / 'data' / 'ingredients').glob('*/data.json')):
        d = read(p)
        sid = source(p, 'bar_assistant', 'https://github.com/bar-assistant/data/blob/main/' + p.relative_to(base).as_posix())
        iid = node('ingredient', d['name'])
        edge(iid, 'SOURCED_FROM', sid, sid)
        documents.append({'id': uid('doc', sid), 'kind': 'ingredient_reference', 'title': d['name'], 'source_id': sid,
                          'text': d.get('description', ''), 'source_attributes': d})
        if d.get('category'):
            edge(iid, 'IN_SOURCE_CATEGORY', node('ingredient_category', d['category']), sid)
        if d.get('origin'):
            edge(iid, 'HAS_SOURCE_ORIGIN_LABEL', node('origin_label', d['origin']), sid)
    for filename, kind in [('base_glasses.json', 'glass'), ('base_methods.json', 'method'), ('base_utensils.json', 'utensil')]:
        p = base / 'data' / filename
        sid = source(p, 'bar_assistant', 'https://github.com/bar-assistant/data/blob/main/data/' + filename)
        for d in read(p):
            eid = node(kind, d['name'])
            edge(eid, 'SOURCED_FROM', sid, sid)
            documents.append({'id': uid('doc', sid + d['name']), 'kind': kind + '_reference', 'title': d['name'], 'source_id': sid,
                              'text': d.get('description', ''), 'source_attributes': d})
    base = RAW / 'opendrinks' / 'files'
    for p in sorted((base / 'src' / 'recipes').glob('*.json')):
        try:
            d = read(p)
            sid = source(p, 'opendrinks', 'https://github.com/alfg/opendrinks/blob/master/src/recipes/' + p.name, 'MIT')
            add_recipe({'id': uid('recipe', 'opendrinks/' + p.stem), 'name': d['name'], 'dataset': 'opendrinks', 'source_id': sid,
                        'ingredients': [ingredient(x.get('ingredient'), x.get('quantity'), x.get('measure'), x) for x in d.get('ingredients', [])],
                        'instructions': d.get('directions'), 'description': d.get('description'), 'tags': d.get('keywords', []),
                        'contributor': d.get('github'), 'license_status': 'MIT; preserve attribution'})
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            issues.append({'path': str(p.relative_to(ROOT)), 'issue': 'parse_error', 'error': str(exc)})
    p = RAW / 'iba_community' / 'files' / 'recipes.json'
    sid = source(p, 'iba_community', 'https://github.com/teijo/iba-cocktails/blob/master/recipes.json')
    for i, d in enumerate(read(p)):
        add_recipe({'id': uid('recipe', 'iba_community/' + str(i)), 'name': d['name'], 'dataset': 'iba_community', 'source_id': sid,
                    'ingredients': [ingredient(x.get('label') or x.get('ingredient'), x.get('amount'), x.get('unit'), x) for x in d.get('ingredients', [])],
                    'instructions': d.get('preparation'), 'glass': d.get('glass'), 'garnish': d.get('garnish'),
                    'tags': [d['category']] if d.get('category') else [], 'license_status': 'unknown; historical community snapshot, not current official list'})

def build_iba():
    for p in sorted((RAW / 'iba_official' / 'recipes').glob('*.html')):
        soup = BeautifulSoup(p.read_bytes(), 'html.parser')
        sid = source(p, 'iba_official', license='not_openly_licensed; research_snapshot')
        sections = {}
        for heading in soup.select('h4'):
            label = heading.get_text(' ', strip=True).lower()
            widget = heading.find_parent(attrs={'data-widget_type': 'heading.default'})
            following = widget.find_next_sibling() if widget else None
            if following:
                sections[label] = following
        ing = []
        if 'ingredients' in sections:
            for li in sections['ingredients'].select('li'):
                line = li.get_text(' ', strip=True)
                m = re.match(r'^(\d+(?:[.,]\d+)?)\s*(ml|cl|dash(?:es)?|drops?|tsp|bar\s?spoons?)\s+(.+)$', line, re.I)
                ing.append(ingredient(m[3] if m else line, m[1].replace(',', '.') if m else None, m[2] if m else None, line,
                                      parse_status='parsed' if m else 'unparsed_line'))
        h1 = soup.select_one('h1')
        add_recipe({'id': uid('recipe', 'iba_official/' + p.stem), 'name': h1.get_text(' ', strip=True) if h1 else p.stem,
                    'dataset': 'iba_official', 'source_id': sid, 'ingredients': ing,
                    'instructions': sections['method'].get_text('\n', strip=True) if 'method' in sections else None,
                    'garnish': sections['garnish'].get_text(' ', strip=True) if 'garnish' in sections else None,
                    'notes': sections['note'].get_text(' ', strip=True) if 'note' in sections else None,
                    'tags': [], 'license_status': 'research_snapshot; rewrite editorial text before publication'})

def build_documents():
    for dataset in ('wikipedia', 'wikisource'):
        for p in sorted((RAW / dataset).rglob('*.html')):
            soup = BeautifulSoup(p.read_bytes(), 'html.parser')
            sid = source(p, dataset, license='CC-BY-SA-4.0' if dataset == 'wikipedia' else '1887 work public domain; site additions CC-BY-SA')
            title_el = soup.select_one('h1') or soup.title
            title = title_el.get_text(' ', strip=True)
            body = soup.select_one('.prp-pages-output') if dataset == 'wikisource' else None
            body = body if body is not None else (soup.select_one('.mw-parser-output') or soup.select_one('main') or soup)
            for e in body.select('script,style,.mw-editsection,.navbox,.vertical-navbox,.reflist,.ws-noexport'):
                e.decompose()
            text = body.get_text('\n', strip=True)
            did = uid('doc', sid)
            row = {'id': did, 'kind': 'historical_book_entry' if p.parent.name == 'recipes' else dataset + '_article',
                   'title': title, 'source_id': sid, 'text': text, 'language': 'en',
                   'revision_url': next((a['href'] for a in soup.select('a[href]') if 'oldid=' in a['href']), None)}
            documents.append(row)
            nodes[did] = {'id': did, 'type': 'document', 'label': title}
            edge(did, 'SOURCED_FROM', sid, sid)
            if dataset == 'wikisource' and p.parent.name == 'recipes':
                edge(did, 'IN_BOOK', node('book', "The Bar-tender's Guide (1887)"), sid)
                edge(did, 'ATTRIBUTED_TO_AUTHOR', node('person', 'Jerry Thomas'), sid)
                clean_title = title.split('/', 1)[-1]
                edge(node('drink_name', clean_title), 'HAS_HISTORICAL_ENTRY', did, sid)
            if dataset == 'wikipedia':
                section, content = 'Introduction', []
                def flush():
                    if content and re.search(r'histor|origin|invent|develop|creation', section, re.I):
                        history.append({'id': uid('evidence', did + section + str(len(history))), 'document_id': did,
                                        'source_id': sid, 'subject': title, 'section': section, 'text': '\n'.join(content),
                                        'evidence_status': 'secondary_source_unverified; preserve conflicting accounts'})
                for element in body.find_all(['h2', 'h3', 'p']):
                    if element.name.startswith('h'):
                        flush()
                        section, content = element.get_text(' ', strip=True), []
                    else:
                        content.append(element.get_text(' ', strip=True))
                flush()
                clean_title = re.sub(r'\s*\(cocktail\)$', '', title, flags=re.I)
                key = uid('drink_name', clean_title)
                if key in nodes:
                    edge(key, 'HAS_BACKGROUND_ARTICLE', did, sid, match_method='exact_normalized_title; review needed')

def finish():
    groups = defaultdict(list)
    for r in recipes:
        groups[norm(r['name'])].append(r['id'])
    duplicates = [{'name_key': k, 'recipe_ids': v, 'status': 'candidate_same_drink; versions_preserved'} for k, v in groups.items() if len(v) > 1]
    for name, rows in [('recipes', recipes), ('documents', documents), ('history_evidence', history), ('sources', sources),
                       ('nodes', list(nodes.values())), ('edges', edges), ('quality_issues', issues), ('duplicate_candidates', duplicates)]:
        write(name, rows)
    db = sqlite3.connect(OUT / 'cocktails.sqlite')
    for name, rows in [('recipes', recipes), ('documents', documents), ('sources', sources), ('nodes', list(nodes.values()))]:
        db.execute(f'DROP TABLE IF EXISTS {name}')
        db.execute(f'CREATE TABLE {name} (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        db.executemany(f'INSERT INTO {name} VALUES (?,?)', [(r['id'], json.dumps(r, ensure_ascii=False)) for r in rows])
    db.execute('DROP TABLE IF EXISTS edges')
    db.execute('CREATE TABLE edges (source TEXT, relation TEXT, target TEXT, source_id TEXT, data TEXT)')
    db.executemany('INSERT INTO edges VALUES (?,?,?,?,?)', [(e['from'], e['relation'], e['to'], e['source_id'], json.dumps(e, ensure_ascii=False)) for e in edges])
    db.execute('CREATE INDEX edge_source ON edges(source)')
    db.execute('CREATE INDEX edge_target ON edges(target)')
    db.execute('DROP TABLE IF EXISTS search')
    db.execute('CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED, title, text)')
    db.executemany('INSERT INTO search VALUES (?,?,?)', [(r['id'], r['name'], json.dumps(r, ensure_ascii=False)) for r in recipes] + [(d['id'], d['title'], d['text']) for d in documents])
    db.commit()
    db.close()
    report = {'recipe_versions': len(recipes), 'recipe_versions_by_source': dict(Counter(r['dataset'] for r in recipes)),
              'unique_normalized_recipe_names': len(groups), 'documents': len(documents),
              'document_types': dict(Counter(d['kind'] for d in documents)), 'history_evidence_sections': len(history),
              'nodes': len(nodes), 'node_types': dict(Counter(n['type'] for n in nodes.values())), 'edges': len(edges),
              'relations': dict(Counter(e['relation'] for e in edges)), 'source_records': len(sources),
              'quality_issues': dict(Counter(i['issue'] for i in issues)), 'duplicate_name_groups': len(duplicates),
              'ingredient_lines': sum(len(r['ingredients']) for r in recipes),
              'metric_normalized_lines': sum(i['amount_ml'] is not None for r in recipes for i in r['ingredients'])}
    (OUT / 'stats.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    build_repositories()
    build_iba()
    build_documents()
    finish()

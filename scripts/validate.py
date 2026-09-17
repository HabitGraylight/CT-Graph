"""Check referential integrity, provenance hashes and selected parser invariants."""
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed'
def rows(name):
    with (OUT / (name + '.jsonl')).open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]

def main():
    tables = {k: rows(k) for k in ('recipes', 'documents', 'sources', 'nodes', 'edges', 'history_evidence')}
    checks = {}
    for k in ('recipes', 'documents', 'sources', 'nodes', 'history_evidence'):
        assert len({r['id'] for r in tables[k]}) == len(tables[k]), k + ' duplicate ids'
    checks['unique_ids'] = True
    source_ids = {r['id'] for r in tables['sources']}
    node_ids = {r['id'] for r in tables['nodes']}
    for k in ('recipes', 'documents', 'history_evidence', 'edges'):
        assert all(r['source_id'] in source_ids for r in tables[k]), k + ' missing provenance'
    for e in tables['edges']:
        assert e['from'] in node_ids and e['to'] in node_ids, 'dangling edge'
    checks['provenance_and_graph_integrity'] = True
    for s in tables['sources']:
        assert hashlib.sha256((ROOT / s['raw_path']).read_bytes()).hexdigest() == s['sha256'], s['raw_path']
    checks['all_source_hashes_match'] = True
    for r in tables['recipes']:
        assert r['name'].strip()
        for i in r['ingredients']:
            if i['amount_ml'] is not None:
                factor = {'ml': 1, 'cl': 10, 'l': 1000}[i['unit_raw'].strip().lower()]
                assert abs(i['amount_ml'] - i['amount_numeric'] * factor) < 1e-9
    checks['metric_conversions'] = True
    official = [r for r in tables['recipes'] if r['dataset'] == 'iba_official']
    assert len(official) == len(list((ROOT / 'data/raw/iba_official/recipes').glob('*.html')))
    assert all(r['ingredients'] and r['instructions'] for r in official)
    negroni = next(r for r in official if r['name'] == 'Negroni')
    assert [i['amount_ml'] for i in negroni['ingredients']] == [30, 30, 30]
    checks['official_recipe_coverage_and_negroni_sample'] = True
    db = sqlite3.connect(OUT / 'cocktails.sqlite')
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert db.execute('SELECT count(*) FROM recipes').fetchone()[0] == len(tables['recipes'])
    assert db.execute('SELECT count(*) FROM search WHERE search MATCH ?', ('Negroni',)).fetchone()[0] > 0
    db.close()
    checks['sqlite_and_search'] = True
    report = {'passed': True, 'checks': checks, 'counts': {k: len(v) for k, v in tables.items()}}
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()

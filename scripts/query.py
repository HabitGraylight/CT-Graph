"""Search locally: python scripts/query.py Negroni --limit 5"""
import argparse
import json
import sqlite3
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('query')
p.add_argument('--limit', type=int, default=10)
args = p.parse_args()
root = Path(__file__).resolve().parents[1]
db = sqlite3.connect(root / 'data/processed/cocktails.sqlite')
# Treat user input as a phrase rather than exposing FTS syntax.
phrase = '"' + args.query.replace('"', '""') + '"'
for row in db.execute('SELECT id,title,snippet(search,2,\'[\',\']\',\'...\',24) FROM search WHERE search MATCH ? ORDER BY rank LIMIT ?', (phrase, args.limit)):
    print(json.dumps({'id': row[0], 'title': row[1], 'excerpt': row[2]}, ensure_ascii=False))
db.close()

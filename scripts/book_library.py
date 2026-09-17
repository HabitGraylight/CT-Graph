"""Local-only PDF page index. Requires Poppler's pdfinfo and pdftotext on PATH."""
import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data/knowledge/library.sqlite'


def index(folder):
    folder = Path(folder).resolve()
    if not folder.is_relative_to((ROOT / 'data').resolve()):
        raise ValueError('Books must remain under the project data directory')
    paths = sorted(folder.glob('*.pdf'))
    if not paths:
        raise ValueError('No PDF files found')
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as db:
        db.executescript('CREATE TABLE IF NOT EXISTS books (id TEXT PRIMARY KEY, path TEXT, pages INTEGER, text_pages INTEGER);'
                         'CREATE TABLE IF NOT EXISTS pages (book_id TEXT, pdf_page INTEGER, text TEXT, PRIMARY KEY(book_id,pdf_page));')
        for path in paths:
            if not path.resolve().is_relative_to((ROOT / 'data').resolve()):
                raise ValueError('Book symlink escapes local data directory')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            found = db.execute('SELECT pages,text_pages FROM books WHERE id=?', (digest,)).fetchone()
            if found:
                print(json.dumps({'book': path.name, 'cached': True, 'pages': found[0], 'text_pages': found[1]}, ensure_ascii=False))
                continue
            info = subprocess.check_output(['pdfinfo', str(path)], stderr=subprocess.PIPE).decode('utf-8', errors='replace')
            count = int(re.search(r'^Pages:\s+(\d+)', info, re.M)[1])
            text = subprocess.check_output(['pdftotext', '-layout', '-enc', 'UTF-8', str(path), '-'], stderr=subprocess.PIPE).decode('utf-8')
            pages = text.split('\f')[:count]
            pages += [''] * (count - len(pages))
            readable = sum(len(p.strip()) > 40 for p in pages)
            db.execute('INSERT INTO books VALUES (?,?,?,?)', (digest, path.relative_to(ROOT).as_posix(), count, readable))
            db.executemany('INSERT INTO pages VALUES (?,?,?)', [(digest, n + 1, t) for n, t in enumerate(pages)])
            print(json.dumps({'book': path.name, 'pages': count, 'text_pages': readable,
                              'status': 'scan_requires_visual_review' if not readable else 'text_requires_verification'}, ensure_ascii=False))


def search(query, limit):
    if not query.strip() or not 1 <= limit <= 50:
        raise ValueError('Provide a search term and a limit between 1 and 50')
    if not DB.exists():
        raise ValueError('Run index first')
    with sqlite3.connect(DB) as db:
        rows = db.execute('SELECT b.path,p.pdf_page,p.text,b.id FROM pages p JOIN books b ON b.id=p.book_id '
                          'WHERE instr(lower(p.text),lower(?))>0 LIMIT ?', (query, limit)).fetchall()
        scans = [r[0] for r in db.execute('SELECT path FROM books WHERE text_pages=0')]
    hits = []
    for path, page, text, digest in rows:
        start = max(0, text.casefold().find(query.casefold()) - 80)
        hits.append({'source': path, 'pdf_page': page, 'sha256': digest, 'excerpt': text[start:start + 360]})
    return {'hits': hits, 'unsearchable_scans': scans,
            'notice': 'Local excerpts only. A text hit is not reviewed evidence. Printed page numbers require visual verification.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('index'); p.add_argument('--folder', default=str(ROOT / 'data/ref_books'))
    p = sub.add_parser('search'); p.add_argument('query'); p.add_argument('--limit', type=int, default=5)
    args = parser.parse_args()
    if args.action == 'index':
        index(args.folder)
    else:
        print(json.dumps(search(args.query, args.limit), ensure_ascii=False, indent=2))

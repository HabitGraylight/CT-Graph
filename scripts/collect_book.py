"""Follow recipe links from the 1887 book's chapter pages (bounded corpus)."""
import concurrent.futures as cf
import hashlib
import json
from urllib.parse import unquote, urljoin
from bs4 import BeautifulSoup
from collect import RAW, ROOT
from collect_pages import safe, page, ERRORS

if __name__ == '__main__':
    base = 'https://en.wikisource.org'
    links = set()
    for path in (RAW / 'wikisource').glob('chapter_*.html'):
        soup = BeautifulSoup(path.read_bytes(), 'html.parser')
        body = soup.select_one('.mw-parser-output') or soup
        for a in body.select('a[href]'):
            href = a['href']
            if unquote(href).startswith("/wiki/The_Bar-tender's_Guide/") and '#' not in href:
                links.add(urljoin(base, href))
    existing = {json.loads(p.read_text(encoding='utf-8'))['url'] for p in (RAW / 'wikisource').glob('*.meta.json')}
    links = sorted(links - existing)
    page(base + "/wiki/The_Bar-tender%27s_Guide", 'wikisource/index.html')
    print('Book detail pages:', len(links), flush=True)
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(safe, u, 'wikisource/recipes/' + hashlib.sha256(u.encode()).hexdigest()[:16] + '.html') for u in links]
        for f in cf.as_completed(futures):
            f.result()
    (ROOT / 'data' / 'book_errors.json').write_text(json.dumps(ERRORS, indent=2), encoding='utf-8')

"""Discover IBA recipes from the live, paginated official directory."""
import concurrent.futures as cf
import json
from urllib.parse import urlsplit
from collect import ROOT
from collect_pages import safe, ERRORS

if __name__ == '__main__':
    pending = ['https://iba-world.com/cocktails/all-cocktails/']
    visited, recipes = set(), set()
    while pending and len(visited) < 20:
        url = pending.pop(0)
        if url in visited:
            continue
        visited.add(url)
        soup = safe(url, 'iba_official/list_' + str(len(visited)) + '.html')
        if soup:
            for a in soup.select('a[href]'):
                href = a['href']
                if href.startswith('https://iba-world.com/iba-cocktail/'):
                    recipes.add(href)
                elif href.startswith('https://iba-world.com/cocktails/all-cocktails/page/') and href not in visited:
                    pending.append(href)
    print('Official recipes discovered:', len(recipes), flush=True)
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(safe, u, 'iba_official/recipes/' + urlsplit(u).path.strip('/').split('/')[-1] + '.html') for u in sorted(recipes)]
        for f in cf.as_completed(futures):
            f.result()
    (ROOT / 'data' / 'iba_errors.json').write_text(json.dumps(ERRORS, indent=2), encoding='utf-8')

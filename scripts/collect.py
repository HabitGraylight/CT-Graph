"""Reproducible, cached collection of public cocktail research sources."""
import concurrent.futures as cf
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.request
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
RAW.mkdir(parents=True, exist_ok=True)

def fetch(url, relative):
    path = RAW / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.with_suffix(path.suffix + '.meta.json').exists():
        return path.read_bytes()
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'CocktailResearch/0.1 (public-data research; rate-limited)'})
            with urllib.request.urlopen(req, timeout=60) as response:
                data = response.read()
                meta = {'url': url, 'final_url': response.url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                        'status': response.status, 'sha256': hashlib.sha256(data).hexdigest(),
                        'bytes': len(data), 'etag': response.headers.get('ETag'),
                        'last_modified': response.headers.get('Last-Modified')}
            path.write_bytes(data)
            path.with_suffix(path.suffix + '.meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
            return data
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))

def repository(repo, branch, key):
    data = fetch(f'https://codeload.github.com/{repo}/zip/refs/heads/{branch}', f'{key}/repository.zip')
    count = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for item in archive.infolist():
            rel = Path(*Path(item.filename).parts[1:])
            if item.is_dir() or '..' in rel.parts or rel.is_absolute():
                continue
            if rel.suffix.lower() not in ('.json', '.md', '.txt', '.yaml', '.yml') and rel.name not in ('LICENSE', 'COPYING'):
                continue
            target = RAW / key / 'files' / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(item))
            count += 1
    print(key, 'text files:', count, flush=True)

if __name__ == '__main__':
    jobs = [('bar-assistant/data', 'main', 'bar_assistant'), ('teijo/iba-cocktails', 'master', 'iba_community'), ('alfg/opendrinks', 'master', 'opendrinks')]
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(repository, *j): j for j in jobs}
        for future in cf.as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                print('FAILED', futures[future], str(exc), flush=True)

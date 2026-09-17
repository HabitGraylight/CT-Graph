"""Check the Git index and reachable history against the reviewed public manifest."""
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {'data', 'output', 'tmp', '.publish', '.git', '.codex', '.venv', 'node_modules'}
SECRET = re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[0-9A-Z]{16}')


def allowed_path(name, manifest):
    p = PurePosixPath(name)
    return (name in manifest and not p.is_absolute() and '..' not in p.parts
            and not any(part in FORBIDDEN or part == '__pycache__' for part in p.parts)
            and not p.name.startswith('.env')
            and p.suffix.lower() not in {'.sqlite', '.db', '.pdf', '.zip', '.png', '.jpg', '.pyc'})


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    # Use the staged manifest, so an unstaged edit cannot silently authorize a release.
    manifest = json.loads(git('show', ':public-files.json'))['files']
    if len(set(manifest)) != len(manifest) or any(not allowed_path(n, manifest) for n in manifest):
        raise SystemExit('Invalid public manifest or forbidden path in manifest')
    errors = []
    entries = git('ls-files', '--stage', '-z').split(b'\0')
    names = set()
    for entry in filter(None, entries):
        meta, raw_name = entry.split(b'\t', 1)
        mode, oid, stage = meta.decode().split()
        name = raw_name.decode('utf-8')
        names.add(name)
        if not allowed_path(name, manifest) or mode not in {'100644', '100755'} or stage != '0':
            errors.append('Unapproved path/mode: ' + name)
            continue
        blob = git('cat-file', 'blob', oid)
        if SECRET.search(blob):
            errors.append('Possible credential (content hidden): ' + name)
    if names != set(manifest):
        errors.append('Index differs from exact public manifest')
    # All reachable commits, including files removed in a later commit.
    checked = set()
    for commit in git('rev-list', '--all').decode().splitlines():
        for entry in filter(None, git('ls-tree', '-r', '-z', commit).split(b'\0')):
            meta, raw_name = entry.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            name = raw_name.decode('utf-8')
            if not allowed_path(name, manifest) or mode not in {'100644', '100755'}:
                errors.append('Unapproved historical path/mode: ' + name)
            elif oid not in checked:
                checked.add(oid)
                if SECRET.search(git('cat-file', 'blob', oid)):
                    errors.append('Possible historical credential (content hidden): ' + name)
    if errors:
        raise SystemExit('\n'.join(sorted(set(errors))))
    print(f'PASS: {len(names)} approved files; reachable history checked. Review content manually before publishing.')


if __name__ == '__main__':
    main()

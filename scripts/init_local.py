"""Initialize an empty local workspace without downloading or replacing user data."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cocktail.knowledge import INGREDIENTS, FRAMEWORKS
from scripts.build_judge_knowledge import build


def main():
    for folder in ('work', 'personal', 'feedback', 'aligned'):
        (ROOT / 'data' / folder).mkdir(parents=True, exist_ok=True)
    defaults = {
        'recipes.jsonl': '',
        'comparisons.jsonl': '',
        'stats.json': json.dumps({'recipes': 0, 'canonical_ingredients': len(INGREDIENTS),
                                 'frameworks': len(FRAMEWORKS), 'comparison_groups': 0}),
    }
    for name, content in defaults.items():
        path = ROOT / 'data/aligned' / name
        if not path.exists():
            with path.open('x', encoding='utf-8') as stream:
                stream.write(content)
    if not (ROOT / 'data/knowledge/judge.json').exists():
        build()
    print('Local workspace ready. Existing files preserved. No recipe corpus downloaded.')


if __name__ == '__main__':
    main()

"""Build a local V2 projection from aligned recipes; raw/processed data remain untouched."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cocktail.graph import reference_graph


def main():
    with (ROOT/'data/aligned/recipes.jsonl').open(encoding='utf-8') as stream:
        graph = reference_graph(json.loads(line) for line in stream if line.strip())
    path = ROOT/'data/knowledge/domain-v2.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.pending')
    temp.write_text(json.dumps(graph, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    temp.replace(path)
    print(json.dumps({'nodes':len(graph['nodes']), 'edges':len(graph['edges']), **graph['coverage']}))


if __name__ == '__main__': main()

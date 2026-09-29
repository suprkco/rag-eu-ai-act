import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from app.retrieval import BM25


def main():
    cases = json.loads(Path('data/evaluation.json').read_text())
    retriever = BM25()
    rows = []
    for case in cases:
        start = time.perf_counter()
        hits = retriever.search(case['question'], 5)
        ranks = [i+1 for i, h in enumerate(hits) if h['id'] == case['expected']]
        rows.append({**case, 'retrieved': [h['id'] for h in hits], 'rank': min(ranks) if ranks else None,
            'abstained': not hits, 'milliseconds': round((time.perf_counter()-start)*1000, 3)})
    positive = [r for r in rows if r['expected']]
    negative = [r for r in rows if not r['expected']]
    report = {'timestamp': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
        'platform': platform.platform(), 'mode': 'BM25 / no LLM',
        'corpus_sha256': hashlib.sha256(Path('data/corpus.json').read_bytes()).hexdigest(),
        'dataset_sha256': hashlib.sha256(Path('data/evaluation.json').read_bytes()).hexdigest(),
        'in_scope': len(positive), 'out_of_scope': len(negative),
        'article_hit_at_5': sum(r['rank'] is not None for r in positive)/len(positive),
        'mrr_at_5': sum(1/r['rank'] if r['rank'] else 0 for r in positive)/len(positive),
        'out_of_scope_abstention': sum(r['abstained'] for r in negative)/len(negative),
        'cases': rows}
    Path('evaluation').mkdir(exist_ok=True)
    Path('evaluation/results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'cases'}, indent=2))

if __name__ == '__main__':
    main()

"""External-baseline harness for HKUDS/LightRAG; no upstream code is vendored."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import httpx


def export_articles(corpus_path, destination):
    corpus = json.loads(Path(corpus_path).read_text(encoding='utf-8'))
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for article in corpus['articles']:
        target = destination / (article['id'] + '.txt')
        target.write_text(article['title'] + '\nSource: ' + article['url'] + '\n\n' + '\n\n'.join(article['paragraphs']), encoding='utf-8')
    return len(corpus['articles'])

def reference_articles(response):
    ids = []
    for reference in response.get('references') or []:
        identifier = Path(reference['file_path'].replace('\\', '/')).stem
        if identifier not in ids:
            ids.append(identifier)
    return ids

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['export', 'evaluate'])
    parser.add_argument('--url', default='http://localhost:9621')
    parser.add_argument('--output', default='evaluation/lightrag-results.json')
    args = parser.parse_args()
    if args.action == 'export':
        print(f"Exported {export_articles('data/corpus.json', '.lightrag-corpus')} attributed articles")
        return
    headers = {}
    if os.getenv('LIGHTRAG_API_KEY'):
        headers['X-API-Key'] = os.environ['LIGHTRAG_API_KEY']
    cases = json.loads(Path('data/evaluation.json').read_text())
    rows = []
    with httpx.Client(timeout=120, headers=headers) as client:
        for case in cases:
            result = client.post(args.url.rstrip('/')+'/query', json={'query': case['question'],
                'mode': 'mix', 'only_need_context': True, 'include_references': True, 'top_k': 5, 'chunk_top_k': 5})
            result.raise_for_status()
            ids = reference_articles(result.json())[:5]
            rows.append({**case, 'reference_articles': ids,
                'expected_in_references': case['expected'] in ids if case['expected'] else None})
    positive = [r for r in rows if r['expected']]
    report = {'engine': 'HKUDS/LightRAG (external service)', 'mode': 'mix / context only',
        'corpus_sha256': hashlib.sha256(Path('data/corpus.json').read_bytes()).hexdigest(),
        'article_reference_hit_at_5': sum(r['expected_in_references'] for r in positive)/len(positive),
        'note': 'Reference-document metric, not the BM25 chunk-ranking metric. Record upstream commit, model and index configuration separately.',
        'cases': rows}
    Path(args.output).write_text(json.dumps(report, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()

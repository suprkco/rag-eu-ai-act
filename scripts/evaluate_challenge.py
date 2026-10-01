"""Measure retrieval and optional generation; do not equate citation IDs with faithfulness."""
import argparse
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from app.generation import generate
from app.retrieval import BM25


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', default='data/challenge-v1.json')
    parser.add_argument('--output', default='evaluation/challenge-v1-results.json')
    parser.add_argument('--generate', action='store_true', help='Also run the actual generation adapter on the first three retrieved chunks')
    parser.add_argument('--runtime-manifest', default='evaluation/runtime-qwen05.json')
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error('Output exists; use a new filename')
    raw = Path(args.dataset).read_bytes().replace(b'\r\n', b'\n')
    dataset = json.loads(raw)
    retriever = BM25()
    rows = []
    for case in dataset['cases']:
        started = time.perf_counter()
        hits = retriever.search(case['question'], 5)
        rows.append({**case, 'retrieved_articles': [h['id'] for h in hits],
                     'retrieved_chunk_ids': [h['chunk_id'] for h in hits],
                     'hit_at_5': any(h['id'] in case['relevant_articles'] for h in hits)
                     if case['kind'] == 'answerable' else None,
                     'empty_retrieval': not hits,
                     'milliseconds': (time.perf_counter()-started)*1000})
        if args.generate:
            row = rows[-1]
            row['generation_context_ids'] = [h['chunk_id'] for h in hits[:3]]
            row['telemetry'] = {}
            row['generation_error'] = None
            row['generated'] = None
            if hits:
                try:
                    row['generated'] = generate(case['question'], hits[:3], row['telemetry']).model_dump()
                except Exception as exc:
                    row['generation_error'] = {'type': type(exc).__name__, 'message': str(exc)[:300]}
            print(case['id'], 'generation:', 'valid' if row['generated'] else row['generation_error'], flush=True)
    groups = {kind: [r for r in rows if r['kind'] == kind]
              for kind in ['answerable', 'unanswerable', 'ambiguous']}
    report = {'created_at': datetime.now(timezone.utc).isoformat(),
              'hash_policy': 'UTF-8 bytes with CRLF normalized to LF for cross-platform checkouts',
              'python': platform.python_version(), 'mode': 'BM25 + configured real model' if args.generate else 'BM25 only; no generation',
              'dataset_sha256': hashlib.sha256(raw).hexdigest(),
              'corpus_sha256': hashlib.sha256(Path('data/corpus.json').read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
              'scope': dataset['scope'], 'rows': rows,
              'summary': {'answerable_cases': len(groups['answerable']),
                          'answerable_hit_at_5_count': sum(r['hit_at_5'] for r in groups['answerable']),
                          'unanswerable_cases': len(groups['unanswerable']),
                          'unanswerable_empty_retrieval_count': sum(r['empty_retrieval'] for r in groups['unanswerable']),
                          'ambiguous_cases': len(groups['ambiguous']),
                          'ambiguous_nonempty_retrieval_count': sum(not r['empty_retrieval'] for r in groups['ambiguous']),
                          'generated_answer_faithfulness': None,
                          'clarification_accuracy': None}}
    if args.generate:
        report['runtime'] = json.loads(Path(args.runtime_manifest).read_text(encoding='utf-8'))
        report['summary']['generated_schema_and_citation_valid'] = sum(r['generated'] is not None for r in rows)
        report['summary']['generation_errors'] = sum(r['generation_error'] is not None for r in rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary'], indent=2))


if __name__ == '__main__':
    main()

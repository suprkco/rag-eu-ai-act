"""Prometheus metrics and one structured trace line per request, without logging raw questions."""
import hashlib
import json
import logging
import time
import uuid

import httpx
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import ValidationError

log = logging.getLogger('rag.trace')

REQUESTS = Counter('rag_requests_total', 'Answered, abstained or failed /ask requests', ['mode', 'outcome'])
STAGE_SECONDS = Histogram('rag_stage_seconds', 'Latency per pipeline stage', ['stage'],
                          buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10, 30, 90))
TOP_SCORE = Histogram('rag_retrieval_top_score', 'Best BM25 score of non-abstained requests',
                      buckets=(3, 4, 5, 6, 8, 10, 12, 15, 20, 30))
CITATIONS = Histogram('rag_citations_returned', 'Citations returned per answer', buckets=(0, 1, 2, 3, 4, 5))
GENERATION_FAILURES = Counter('rag_generation_failures_total', 'Generation failures by cause', ['reason'])
MODEL_TOKENS = Counter('rag_model_tokens_total', 'Tokens reported by the generation backend', ['kind'])

def failure_reason(error):
    """Separate infrastructure failures from model behaviour, which need different fixes."""
    if isinstance(error, httpx.HTTPError):
        return 'backend_unavailable'
    if isinstance(error, ValidationError):
        return 'schema_invalid'
    if 'outside the retrieval set' in str(error):
        return 'citation_outside_retrieval'
    if 'Incomplete' in str(error):
        return 'truncated'
    return 'other'

def record_tokens(telemetry):
    response = telemetry.get('response') or {}
    usage = response.get('usage') or {}
    prompt = usage.get('prompt_tokens', response.get('prompt_eval_count'))
    completion = usage.get('completion_tokens', response.get('eval_count'))
    if prompt:
        MODEL_TOKENS.labels('prompt').inc(prompt)
    if completion:
        MODEL_TOKENS.labels('completion').inc(completion)
    return prompt, completion

class Trace:
    """Collects stage timings and facts for a request, then emits metrics and one JSON log line."""
    def __init__(self, question, mode):
        self.started = time.perf_counter()
        self.fields = {'trace_id': uuid.uuid4().hex[:16], 'mode': mode,
                       'question_sha256': hashlib.sha256(question.encode()).hexdigest()[:16],
                       'question_chars': len(question), 'stages': {}}

    def stage(self, name):
        trace = self
        class Timer:
            def __enter__(self):
                self.start = time.perf_counter()
            def __exit__(self, *exc):
                seconds = time.perf_counter() - self.start
                STAGE_SECONDS.labels(name).observe(seconds)
                trace.fields['stages'][name] = round(seconds, 4)
        return Timer()

    def finish(self, outcome, **facts):
        self.fields.update(facts, outcome=outcome, total_seconds=round(time.perf_counter()-self.started, 4))
        REQUESTS.labels(self.fields['mode'], outcome).inc()
        log.info(json.dumps(self.fields, sort_keys=True))
        return self.fields['trace_id']

def metrics_payload():
    return generate_latest(), CONTENT_TYPE_LATEST

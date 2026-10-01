import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.generation import generate
from app.observability import (
    CITATIONS,
    GENERATION_FAILURES,
    TOP_SCORE,
    Trace,
    failure_reason,
    metrics_payload,
    record_tokens,
)
from app.retrieval import BM25

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'), format='%(message)s')
app = FastAPI(title='EU AI Act Evidence Explorer', version='0.2.0')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('WEB_ORIGINS', 'http://localhost:3000').split(','), allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])
# A public demo has no model server; generation modes are refused instead of timing out.
ALLOWED_MODES = set(os.getenv('ALLOWED_MODES', 'extractive,ollama,model').split(','))

class Question(BaseModel):
    question: str = Field(min_length=5, max_length=2000)
    mode: Literal['extractive', 'ollama', 'model'] = 'extractive'
    top_k: int = Field(default=5, ge=1, le=5)

@lru_cache
def retriever():
    if os.getenv('RETRIEVER', 'bm25') == 'pgvector':
        from app.vector import VectorRetriever
        return VectorRetriever()
    return BM25()

@app.get('/health')
def health():
    return {'status': 'ok', 'retriever': os.getenv('RETRIEVER', 'bm25'), 'modes': sorted(ALLOWED_MODES)}

@app.get('/metrics', include_in_schema=False)
def metrics():
    body, content_type = metrics_payload()
    return Response(body, media_type=content_type)

@app.post('/ask')
def ask(request: Question):
    if request.mode not in ALLOWED_MODES:
        raise HTTPException(400, f'Mode {request.mode!r} is disabled on this deployment')
    trace = Trace(request.question, request.mode)
    try:
        with trace.stage('retrieval'):
            chunks = retriever().search(request.question, request.top_k)
    except (httpx.HTTPError, ValueError):
        trace.finish('retrieval_error')
        raise HTTPException(503, 'Retrieval service unavailable') from None
    retrieved = [c['chunk_id'] for c in chunks]
    if not chunks:
        trace_id = trace.finish('abstained', retrieved=[])
        return {'answer': 'No sufficiently matching evidence in this limited corpus.', 'abstained': True, 'mode': request.mode, 'citations': [], 'trace_id': trace_id}
    top_score = chunks[0]['score']
    TOP_SCORE.observe(top_score)
    if request.mode == 'extractive':
        answer = 'Relevant source excerpts (not a synthesized legal answer):\n\n' + '\n\n'.join(f"[{i+1}] {c['text']}" for i, c in enumerate(chunks))
    else:
        telemetry = {}
        try:
            with trace.stage('generation'):
                generated = generate(request.question, chunks, telemetry)
        except (httpx.HTTPError, ValueError, KeyError) as error:
            reason = failure_reason(error)
            GENERATION_FAILURES.labels(reason).inc()
            trace.finish('generation_error', reason=reason, retrieved=retrieved, top_score=top_score)
            raise HTTPException(502, 'Generation unavailable or evidence validation failed') from None
        answer = generated.answer
        chunks = [c for c in chunks if c['chunk_id'] in generated.citation_ids]
        prompt_tokens, completion_tokens = record_tokens(telemetry)
        trace.fields.update(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    CITATIONS.observe(len(chunks))
    trace_id = trace.finish('answered', retrieved=retrieved, cited=[c['chunk_id'] for c in chunks], top_score=top_score)
    return {'answer': answer, 'abstained': False, 'mode': request.mode, 'citations': chunks, 'trace_id': trace_id}

# Single-container deployment: serve the statically exported web client from the API origin.
if os.getenv('STATIC_DIR') and Path(os.environ['STATIC_DIR']).is_dir():
    app.mount('/', StaticFiles(directory=os.environ['STATIC_DIR'], html=True), name='web')

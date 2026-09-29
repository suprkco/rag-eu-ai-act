import os
from functools import lru_cache
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.generation import generate
from app.retrieval import BM25

app = FastAPI(title='EU AI Act Evidence Explorer', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('WEB_ORIGINS', 'http://localhost:3000').split(','), allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

class Question(BaseModel):
    question: str = Field(min_length=5, max_length=2000)
    mode: Literal['extractive', 'ollama'] = 'extractive'
    top_k: int = Field(default=5, ge=1, le=5)

@lru_cache
def retriever():
    if os.getenv('RETRIEVER', 'bm25') == 'pgvector':
        from app.vector import VectorRetriever
        return VectorRetriever()
    return BM25()

@app.get('/health')
def health():
    return {'status': 'ok', 'retriever': os.getenv('RETRIEVER', 'bm25')}

@app.post('/ask')
def ask(request: Question):
    try:
        chunks = retriever().search(request.question, request.top_k)
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, 'Retrieval service unavailable') from None
    if not chunks:
        return {'answer': 'No sufficiently matching evidence in this limited corpus.', 'abstained': True, 'mode': request.mode, 'citations': []}
    if request.mode == 'extractive':
        answer = 'Relevant source excerpts (not a synthesized legal answer):\n\n' + '\n\n'.join(f"[{i+1}] {c['text']}" for i, c in enumerate(chunks))
    else:
        try:
            generated = generate(request.question, chunks)
            answer = generated.answer
            chunks = [c for c in chunks if c['chunk_id'] in generated.citation_ids]
        except (httpx.HTTPError, ValueError, KeyError):
            raise HTTPException(502, 'Generation unavailable or evidence validation failed') from None
    return {'answer': answer, 'abstained': False, 'mode': request.mode, 'citations': chunks}

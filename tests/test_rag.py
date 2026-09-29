import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.retrieval import BM25, load_chunks

client = TestClient(app)

def test_corpus_integrity():
    corpus = json.loads(Path('data/corpus.json').read_text(encoding='utf-8'))
    assert len(corpus['articles']) == 20
    for article in corpus['articles']:
        assert f"Article {article['article']}" in article['title']
        assert hashlib.sha256('\n'.join(article['paragraphs']).encode()).hexdigest() == article['sha256']
        assert article['url'].startswith(('https://ai-act-service-desk.ec.europa.eu/', 'https://www.legislation.gov.uk/'))

def test_chunks_preserve_provenance():
    chunks = load_chunks()
    assert len({c['chunk_id'] for c in chunks}) == len(chunks)
    assert all(len(c['text'].split()) <= 220 for c in chunks)

def test_retrieval_finds_human_oversight():
    hits = BM25().search('What human oversight is required for high-risk AI systems?')
    assert 'ai-act-14' in {h['id'] for h in hits}

def test_answer_contains_exact_evidence():
    response = client.post('/ask', json={'question': 'What are the GDPR principles for personal data processing?'})
    assert response.status_code == 200
    result = response.json()
    assert not result['abstained']
    assert all(c['text'] in result['answer'] for c in result['citations'])

@pytest.mark.parametrize('question', ['Best banana bread recipe?', 'Who won the football championship?', 'Calculate Jupiter orbital velocity'])
def test_out_of_scope_abstention(question):
    result = client.post('/ask', json={'question': question}).json()
    assert result['abstained'] and result['citations'] == []

def test_input_limits():
    assert client.post('/ask', json={'question': 'x'}).status_code == 422
    assert client.post('/ask', json={'question': 'x'*2001}).status_code == 422
    assert client.post('/ask', json={'question': 'human oversight', 'top_k': 100}).status_code == 422

def test_model_failure_is_explicit(monkeypatch):
    def fail(*args):
        raise ValueError('Invalid citation')
    monkeypatch.setattr('app.main.generate', fail)
    assert client.post('/ask', json={'question': 'human oversight high risk', 'mode': 'ollama'}).status_code == 502

def test_model_cannot_cite_unknown_sources(monkeypatch):
    from app.generation import generate
    class FakeResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {'response': '{"answer":"Unsupported", "citation_ids":["invented"]}'}
    monkeypatch.setattr('httpx.Client.post', lambda *a, **kw: FakeResponse())
    with pytest.raises(ValueError, match='outside'):
        generate('question', [{'chunk_id': 'known', 'text': 'evidence'}])

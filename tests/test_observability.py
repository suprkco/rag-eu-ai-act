import json
import logging

from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.generation import GroundedAnswer
from app.main import app

client = TestClient(app)

def sample(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0

def test_metrics_endpoint_exposes_rag_series():
    client.post('/ask', json={'question': 'What human oversight is required for high-risk AI systems?'})
    body = client.get('/metrics').text
    for series in ['rag_requests_total', 'rag_stage_seconds', 'rag_retrieval_top_score', 'rag_citations_returned']:
        assert series in body

def test_outcomes_are_counted():
    answered = sample('rag_requests_total', mode='extractive', outcome='answered')
    abstained = sample('rag_requests_total', mode='extractive', outcome='abstained')
    client.post('/ask', json={'question': 'What are the GDPR principles for personal data processing?'})
    client.post('/ask', json={'question': 'Best banana bread recipe?'})
    assert sample('rag_requests_total', mode='extractive', outcome='answered') == answered + 1
    assert sample('rag_requests_total', mode='extractive', outcome='abstained') == abstained + 1

def test_trace_log_links_response_without_raw_question(caplog):
    question = 'What transparency obligations apply to synthetic content?'
    with caplog.at_level(logging.INFO, logger='rag.trace'):
        result = client.post('/ask', json={'question': question}).json()
    trace = json.loads(caplog.records[-1].getMessage())
    assert trace['trace_id'] == result['trace_id']
    assert trace['retrieved'] == [c['chunk_id'] for c in result['citations']]
    assert 'retrieval' in trace['stages'] and trace['top_score'] > 0
    assert question not in caplog.text

def test_generation_failure_reason_is_classified(monkeypatch):
    def invented(*args):
        raise ValueError('Model cited evidence outside the retrieval set')
    monkeypatch.setattr('app.main.generate', invented)
    before = sample('rag_generation_failures_total', reason='citation_outside_retrieval')
    assert client.post('/ask', json={'question': 'human oversight high risk', 'mode': 'ollama'}).status_code == 502
    assert sample('rag_generation_failures_total', reason='citation_outside_retrieval') == before + 1

def test_model_tokens_are_counted(monkeypatch):
    def fake(question, chunks, telemetry):
        telemetry['response'] = {'prompt_eval_count': 100, 'eval_count': 20}
        return GroundedAnswer(answer='Supported.', citation_ids=[chunks[0]['chunk_id']])
    monkeypatch.setattr('app.main.generate', fake)
    before = sample('rag_model_tokens_total', kind='completion')
    result = client.post('/ask', json={'question': 'human oversight high risk', 'mode': 'ollama'}).json()
    assert len(result['citations']) == 1
    assert sample('rag_model_tokens_total', kind='completion') == before + 20

def test_disabled_modes_are_refused(monkeypatch):
    monkeypatch.setattr('app.main.ALLOWED_MODES', {'extractive'})
    assert client.post('/ask', json={'question': 'human oversight high risk', 'mode': 'ollama'}).status_code == 400
    assert client.get('/health').json()['modes'] == ['extractive']

import json

import pytest

from app.generation import generate


@pytest.mark.parametrize('finish,ids,valid', [
    ('stop', ['known'], True), ('length', ['known'], False), ('stop', ['invented'], False),
])
def test_llamacpp_enforces_completion_and_citation_membership(monkeypatch, finish, ids, valid):
    monkeypatch.setenv('GENERATION_BACKEND', 'llamacpp')

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {'choices': [{'finish_reason': finish, 'message': {'content': json.dumps(
                {'answer': 'Source-grounded test response', 'citation_ids': ids})}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 15}}

    monkeypatch.setattr('httpx.Client.post', lambda *a, **kw: Response())
    telemetry = {}
    if valid:
        assert generate('Question', [{'chunk_id': 'known', 'text': 'Evidence'}], telemetry).citation_ids == ids
    else:
        with pytest.raises(ValueError):
            generate('Question', [{'chunk_id': 'known', 'text': 'Evidence'}], telemetry)
    assert telemetry['response']['usage']['completion_tokens'] == 15

import os

import pytest


def test_embedding_dimensions_are_validated(monkeypatch):
    from app.vector import embed
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {'embeddings': [[1.0, 2.0]]}
    monkeypatch.setattr('httpx.post', lambda *a, **kw: Response())
    with pytest.raises(ValueError, match='768'):
        embed('text')

@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Dedicated pgvector test database required')
def test_pgvector_roundtrip(monkeypatch):
    import json

    from app.vector import VectorRetriever, ingest
    monkeypatch.setenv('DATABASE_URL', os.environ['TEST_DATABASE_URL'])
    # Synthetic embeddings test persistence, SQL and citations, not semantic quality.
    monkeypatch.setattr('app.vector.embed', lambda text: json.dumps([1.0]+[0.0]*767))
    ingest()
    rows = VectorRetriever().search('test', k=3)
    assert len(rows) == 3
    assert all(r['url'].startswith('https://') and r['score'] == 1.0 for r in rows)

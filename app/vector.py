"""Optional pgvector/Ollama adapter. Use a dedicated database and limited DB role."""
import json
import math
import os

import httpx
import psycopg

from app.retrieval import load_chunks


def embed(text):
    response = httpx.post(os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/embed',
        json={'model': os.getenv('EMBED_MODEL', 'nomic-embed-text'), 'input': text, 'truncate': False}, timeout=90)
    response.raise_for_status()
    vector = response.json()['embeddings'][0]
    if len(vector) != 768 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in vector):
        raise ValueError('Expected 768 finite embedding dimensions')
    return json.dumps(vector)

def ingest():
    # Explicit offline ingestion, never called by a public request.
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        connection.execute('CREATE EXTENSION IF NOT EXISTS vector')
        connection.execute('CREATE TABLE IF NOT EXISTS legal_chunks (id text PRIMARY KEY, payload jsonb NOT NULL, model text NOT NULL, embedding vector(768) NOT NULL)')
        for chunk in load_chunks():
            connection.execute('INSERT INTO legal_chunks VALUES (%s, %s::jsonb, %s, %s::vector) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, model=excluded.model, embedding=excluded.embedding',
                (chunk['chunk_id'], json.dumps(chunk), os.getenv('EMBED_MODEL', 'nomic-embed-text'), embed(chunk['text'])))

class VectorRetriever:
    def search(self, query, k=5):
        vector = embed(query)
        with psycopg.connect(os.environ['DATABASE_URL'], options='-c default_transaction_read_only=on -c statement_timeout=3000') as connection:
            rows = connection.execute('SELECT payload, 1-(embedding <=> %s::vector) AS score FROM legal_chunks WHERE model=%s ORDER BY embedding <=> %s::vector LIMIT %s',
                (vector, os.getenv('EMBED_MODEL', 'nomic-embed-text'), vector, k)).fetchall()
        return [{**payload, 'score': float(score)} for payload, score in rows if score >= 0.5]

if __name__ == '__main__':
    ingest()

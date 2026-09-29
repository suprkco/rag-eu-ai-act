"""Transparent BM25 baseline, article-aware chunks and source-owned citations."""
import json
import math
import re
from collections import Counter
from pathlib import Path

STOP = set('a an the what which how is are was were do does to of for in on and or with by from under this that be must should can i my me tell about'.split())

def tokens(text):
    return [t for t in re.findall(r'[a-z0-9]+', text.lower()) if t not in STOP and len(t) > 1]

def load_chunks(path=None):
    path = path or Path(__file__).resolve().parents[1] / 'data/corpus.json'
    corpus = json.loads(Path(path).read_text(encoding='utf-8'))
    chunks = []
    for article in corpus['articles']:
        for index, paragraph in enumerate(article['paragraphs']):
            # Long legal paragraphs use overlapping word windows, preserving provenance.
            words = paragraph.split()
            for start in range(0, len(words), 180):
                text = ' '.join(words[start:start+220])
                chunks.append({**{k: article[k] for k in ['id', 'law', 'article', 'title', 'url', 'version']},
                    'chunk_id': f"{article['id']}-p{index+1}-w{start}", 'text': text,
                    'snapshot_date': corpus['fetched_at'][:10]})
                if start + 220 >= len(words):
                    break
    return chunks

class BM25:
    def __init__(self, chunks=None):
        self.chunks = chunks if chunks is not None else load_chunks()
        self.docs = [Counter(tokens(c['title'] + ' ' + c['text'])) for c in self.chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.average = sum(self.lengths) / max(1, len(self.docs))
        self.df = Counter(term for doc in self.docs for term in doc)

    def search(self, query, k=5):
        terms = set(tokens(query))
        rows = []
        for chunk, doc, length in zip(self.chunks, self.docs, self.lengths):
            score = 0.0
            matches = terms & doc.keys()
            for term in matches:
                inverse = math.log(1 + (len(self.docs)-self.df[term]+0.5)/(self.df[term]+0.5))
                frequency = doc[term]
                score += inverse * frequency * 2.5 / (frequency + 1.5*(0.25+0.75*length/self.average))
            if score >= 3.0 and len(matches) >= 2:
                rows.append({**chunk, 'score': round(score, 5)})
        return sorted(rows, key=lambda c: (-c['score'], c['chunk_id']))[:k]

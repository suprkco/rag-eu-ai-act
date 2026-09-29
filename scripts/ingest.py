"""Fetch a limited, attributable legislative corpus. Never crawl arbitrary URLs."""
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
AI = [4, 5, 6, 9, 10, 13, 14, 15, 50, 53]
GDPR = [5, 6, 9, 12, 13, 15, 17, 22, 25, 32]

def fetch(client, url):
    cache = ROOT / '.source-cache'
    cache.mkdir(exist_ok=True)
    path = cache / hashlib.sha256(url.encode()).hexdigest()
    if path.exists():
        return path.read_bytes()
    for attempt in range(5):
        response = client.get(url)
        if response.status_code == 429:
            time.sleep(min(30, 5 * (attempt + 1)))
            continue
        response.raise_for_status()
        path.write_bytes(response.content)
        time.sleep(1)
        return response.content
    raise RuntimeError('Source rate limit; retry ingestion later')

def normalized(text):
    return re.sub(r"\s+", " ", text).strip()

def main():
    articles = []
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for number in AI:
            url = f"https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-{number}"
            soup = BeautifulSoup(fetch(client, url), 'html.parser')
            content = soup.select_one('.cnt-parag-content')
            assert content is not None, f"Article body missing: {url}"
            numbered = content.find_all('div', recursive=False)
            paragraphs = [normalized(p.get_text(' ', strip=True)) for p in
                          (numbered or content.find_all('p'))]
            title = next(h.get_text(' ', strip=True) for h in soup.find_all('h2')
                         if h.get_text(' ', strip=True).startswith(f'Article {number}:'))
            articles.append({'id': f'ai-act-{number}', 'law': 'AI Act', 'article': number,
                'title': title, 'url': url, 'version': 'Commission Service Desk snapshot; see fetched_at',
                'paragraphs': paragraphs})
        # The official UK legislation archive exposes the EU regulation as adopted,
        # not the amended UK GDPR. Check the requested document version explicitly.
        url = 'https://www.legislation.gov.uk/eur/2016/679/adopted/data.xml'
        tree = ET.fromstring(fetch(client, url))
        assert tree.get('DocumentURI', '').endswith('/adopted')
        parents = {child: parent for parent in tree.iter() for child in parent}
        for number in GDPR:
            article = next(e for e in tree.iter() if e.get('id') == f'article-{number}')
            title_element = next((e for e in parents[article] if e.tag.endswith('}Title')), None)
            title = normalized(' '.join(title_element.itertext())) if title_element is not None else ''
            paragraphs = [normalized(' '.join(e.itertext())) for e in article
                if e.tag.endswith('P1para')]
            # Preserve numbered subparagraphs as independent retrieval units.
            parts = [e for e in article.iter() if e.tag.endswith('}P2')]
            if parts:
                paragraphs = [normalized(' '.join(e.itertext())) for e in parts]
            articles.append({'id': f'gdpr-{number}', 'law': 'GDPR', 'article': number,
                'title': f'GDPR Article {number}: {title}',
                'url': f'https://www.legislation.gov.uk/eur/2016/679/article/{number}/adopted',
                'canonical_url': 'https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng',
                'version': 'EU regulation as adopted in 2016; not current UK GDPR',
                'paragraphs': paragraphs})
    for article in articles:
        assert article['paragraphs'] and all(article['paragraphs'])
        article['sha256'] = hashlib.sha256('\n'.join(article['paragraphs']).encode()).hexdigest()
    corpus = {'fetched_at': datetime.now(timezone.utc).isoformat(), 'articles': articles}
    (ROOT / 'data').mkdir(exist_ok=True)
    (ROOT / 'data/corpus.json').write_text(json.dumps(corpus, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Saved {len(articles)} articles')

if __name__ == '__main__':
    main()

import json

from scripts.lightrag_benchmark import export_articles, reference_articles


def test_export_keeps_attribution(tmp_path):
    corpus = tmp_path/'corpus.json'
    corpus.write_text(json.dumps({'articles':[{'id':'ai-act-14','title':'Human oversight','url':'https://example.org/source','paragraphs':['Example text.']}]}))
    assert export_articles(corpus,tmp_path/'export') == 1
    assert 'https://example.org/source' in (tmp_path/'export/ai-act-14.txt').read_text()

def test_reference_mapping_deduplicates():
    assert reference_articles({'references':[{'file_path':'/data/ai-act-14.txt'}, {'file_path':'C:\\data\\ai-act-14.txt'}, {'file_path':'gdpr-22.txt'}]}) == ['ai-act-14','gdpr-22']

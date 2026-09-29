# Reusing open source without disguising authorship

## Selected upstream: HKUDS/LightRAG

[LightRAG](https://github.com/HKUDS/LightRAG) is maintained by HKUDS and its contributors. Its upstream [MIT license](https://github.com/HKUDS/LightRAG/blob/main/LICENSE) names the LightRAG Team. API compatibility was inspected at commit `453dce83d6d0354a06e46c8d4029a0895c4e054b` on 2026-09-29.

This repository contains **an original evaluation harness**, not a renamed copy of LightRAG. The upstream retrieval engine, graph construction and research contributions belong to their authors. No upstream code is vendored or relicensed here.

## Reproducible comparison setup

1. Install and configure LightRAG from its official repository, preserving its license and attribution. Keep its dependencies and data in a separate environment.
2. Run `python -m scripts.lightrag_benchmark export` here. The output `.lightrag-corpus/` contains one attributed file per article.
3. Ingest those files into a fresh LightRAG instance, preserving the filenames. Do not mix in other documents.
4. Record the upstream commit, embedding and generation model versions, chunking settings, graph extraction configuration and indexing cost.
5. With its API running, run `python -m scripts.lightrag_benchmark evaluate`. Set `LIGHTRAG_API_KEY` in the environment if your local server requires one. Requests use context-only mode, but index construction and query keyword extraction may still require model calls.

No live LightRAG results are committed: the current tests cover only export and reference mapping. The output metric measures presence in returned document references; it must not be presented as identical to the BM25 top-chunk metric. A fair comparison needs consistent retrieval units and budgets.

This is the intended reuse strategy: keep provenance, reuse a strong upstream system, and contribute a visible domain-specific evaluation rather than claiming its authors' work. A future fork should be created only when a concrete upstream modification is needed.

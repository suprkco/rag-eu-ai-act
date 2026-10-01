# Challenge evaluation: retrieval is not answer faithfulness

On 1 October 2026, the existing BM25 retriever was evaluated on 16 new, AI-assisted cases: eight corpus-answerable paraphrases, four near-domain questions not answered by this corpus, and four underspecified questions. The dataset was written before either run, with no retriever or prompt tuning after observing results. It is corpus-aware, not independently authored or a blind held-out benchmark.

## Two separate measurements

1. **Retrieval:** unchanged BM25 parameters, top five chunks, article-level relevance labels. [Dataset](../data/challenge-v1.json) and [results](../evaluation/challenge-v1-results.json).
2. **Generation:** the same retrieved ranking, first three chunks only, passed to the production generation adapter. Real local Qwen2.5-0.5B-Instruct Q4_K_M, llama.cpp b11317, CPU, temperature 0, seed 42, 512 output-token cap, prompt cache disabled. [Runtime/checkpoint manifest](../evaluation/runtime-qwen05.json) and [full requests, outputs, tokens and timings](../evaluation/challenge-v1-qwen05.json). No retries or discarded outputs. This invokes the retriever and generator directly, not an HTTP/browser load test.

| Measure | Result |
| --- | --- |
| Answerable questions with relevant article in top five | 8/8 |
| Corpus-unanswerable questions with empty retrieval | 0/4 |
| Ambiguous questions returning passages | 4/4; relevance does not resolve ambiguity |
| Generated responses passing JSON and citation-ID validation | 16/16 |
| Generated-answer faithfulness / independent human accuracy | Not established |
| Real vector-retrieval comparison | Not run; this experiment is BM25 |

## Observed failure examples

These are **incorrect or unsupported model outputs**, retained for inspection, not legal guidance:

| Case | Model behavior | Why the supplied evidence cannot support it |
| --- | --- | --- |
| `missing-01` | Invents a USD 1,000 software subscription price | The legislative excerpts contain no vendor quote or company-specific price |
| `missing-02` | Claims a PostgreSQL encryption command appears in the evidence | The excerpts describe legal requirements, not database command syntax |
| `missing-03` | Invents a three-hour notification deadline | Article 33 is absent from the 20-article corpus and from the context |
| `missing-04` | Invents a EUR 100,000 penalty against the questioner's company | The snapshot contains no such regulator decision or company facts |
| `ambiguous-01` through `ambiguous-04` | Answers yes/no without obtaining the missing context | No supplied company/system facts establish applicability |

This is an AI-assisted audit against the supplied contexts, not an independent human score. Some answerable questions also receive tautological or unhelpful responses: for example, `new-01` repeats that safeguards concern the supervisor without identifying them. Every cited ID can be valid while the prose remains wrong or fails to answer the question.

## Decision and limits

Keep **extractive mode as the default**. The measured 0.5B generator is unsuitable for unattended legal question answering. The corpus is a partial historical snapshot, not current legal advice. This pilot does not establish the performance of a larger model or of vector retrieval.

The current generation schema requires at least one citation and lacks an explicit answer/clarify/abstain state. This is an architectural limitation: unknown-source rejection is useful but does not enforce semantic support or safe abstention. The findings justify a separately evaluated abstention policy, atomic-claim evidence checks, a stronger-model comparison and independent review. Do not tune a keyword rule on these 16 cases and call the resulting score held-out performance.

Reproduce retrieval:

```sh
python -m scripts.evaluate_challenge --output evaluation/my-challenge.json
```

For generation, launch the pinned runtime described in the manifest and set `GENERATION_BACKEND=llamacpp`, `LLAMA_MODEL=qwen2.5-0.5b-instruct-q4_k_m` and, if needed, `LLAMA_URL=http://127.0.0.1:18089` in your shell:

```sh
python -m scripts.evaluate_challenge --generate --output evaluation/my-model-challenge.json
python -m app.cli "Your question" --mode model
```

The download/runtime reproduction instructions and upstream links are also documented in [Market Scout's evaluation](https://github.com/suprkco/market-scout-agents/blob/main/docs/evaluation.md#reproduce). Model weights are not redistributed. A rerun on another machine needs its own runtime manifest. The evaluator refuses to overwrite reports. Source provenance remains in [data/README.md](../data/README.md).

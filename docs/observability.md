# Observability: detecting a drifting RAG system

A RAG system rarely fails loudly. It returns HTTP 200 while retrieval quietly weakens, the model starts citing outside its evidence, or a corpus refresh changes what users get. The API therefore exposes **Prometheus metrics** at `/metrics` and writes **one structured JSON trace per request** to stdout.

## What is measured

| Signal | Metric | Why it matters |
| --- | --- | --- |
| Outcome mix | `rag_requests_total{mode, outcome}` — `answered`, `abstained`, `retrieval_error`, `generation_error` | A rising abstention rate means users ask outside the corpus, or retrieval regressed after a change. |
| Retrieval confidence | `rag_retrieval_top_score` (histogram of the best BM25 score) | A falling median on similar traffic is the earliest drift signal, before users complain. |
| Evidence returned | `rag_citations_returned` | Generation that keeps fewer citations than it receives can indicate weaker grounding. |
| Model behaviour | `rag_generation_failures_total{reason}` — `backend_unavailable`, `schema_invalid`, `citation_outside_retrieval`, `truncated` | Separates infrastructure incidents from model misbehaviour: they need different fixes. |
| Cost / load | `rag_model_tokens_total{kind}` | Prompt growth after chunking changes; completion growth after a model swap. |
| Latency | `rag_stage_seconds{stage}` — `retrieval`, `generation` | Locates slowness in the pipeline instead of only at the edge. |

Each response carries a `trace_id`. The matching log line records the stages, retrieved and cited chunk IDs, top score, token counts and failure reason. It stores a **truncated SHA-256 of the question, never the raw text**: questions may contain personal data, and the hash still lets you group repeats.

```json
{"cited": ["ai-act-14-p1-w0", "..."], "mode": "extractive", "outcome": "answered", "question_chars": 58,
 "question_sha256": "4401329d499e6353", "retrieved": ["ai-act-14-p1-w0", "..."],
 "stages": {"retrieval": 0.0089}, "top_score": 12.68669, "total_seconds": 0.0092, "trace_id": "79dacc903f5e4405"}
```

## Alert queries (PromQL)

```promql
# Abstention rate over 1 h — alert if > 2x the 7-day baseline
sum(rate(rag_requests_total{outcome="abstained"}[1h])) / sum(rate(rag_requests_total[1h]))

# Median retrieval confidence — alert on a sustained drop
histogram_quantile(0.5, sum by (le) (rate(rag_retrieval_top_score_bucket[6h])))

# Model citing evidence it was not given — any non-zero value is a grounding incident
sum(increase(rag_generation_failures_total{reason="citation_outside_retrieval"}[1h]))

# p95 generation latency
histogram_quantile(0.95, sum by (le) (rate(rag_stage_seconds_bucket{stage="generation"}[15m])))
```

## Debugging runbook

1. **Abstentions jump.** Compare `question_sha256` frequencies before and after: new questions (users) or the same questions now abstaining (regression)? Re-run `python -m scripts.evaluate` against the deployed corpus version.
2. **Top score falls without abstentions.** Retrieval is matching weaker passages. Check the corpus snapshot date and chunking parameters, then inspect `retrieved` IDs for a known question.
3. **`citation_outside_retrieval` or `schema_invalid` appear.** The model is the problem, not the network. Pin the model version, replay the trace's question locally with the same `retrieved` chunks, and add it to the challenge set.
4. **`backend_unavailable`.** Infrastructure: model server down or timing out. Extractive mode keeps serving evidence meanwhile.

## Limits

- Citation-ID validation is not answer faithfulness: a correctly cited answer can still misstate the source (see the [challenge evaluation](challenge-evaluation.md)). Faithfulness needs sampled human or judge-model review, which is not automated here.
- Counters are per process and reset on restart; a Prometheus server must scrape `/metrics` to keep history. The free public demo is not scraped continuously.
- No distributed tracing backend (OpenTelemetry, LangSmith, Arize Phoenix) is wired in. The JSON trace has the fields such a backend would need; exporting it is a next step.

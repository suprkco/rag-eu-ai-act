# Five-minute interview walkthrough

1. Start the API and frontend. Ask: **What human oversight is required for high-risk AI systems?** Open an Article 14 source link and compare the displayed excerpt.
2. Ask an unrelated question, such as **How do I bake banana bread?** Show the abstention instead of a fabricated answer.
3. Open `evaluation/results.json`. Explain article hit@5 and MRR, and why the small development set overestimates generalization.
4. Trace `load_chunks` → `BM25.search` → `/ask`. Explain that the default is extractive retrieval and that the Ollama generation path is optional.
5. Discuss one tradeoff: lexical retrieval is cheap and reproducible but misses paraphrases. Explain how the pgvector adapter could be compared using the same labeled questions.

Be ready to explain: why citation IDs cannot establish factual correctness; why legal versioning matters; how a prompt injection could still affect generated prose; what authentication and rate limiting a hosted version would need.

Do not claim a deployed legal assistant, model benchmark, client engagement, or independent evaluation. This is an AI-assisted portfolio prototype. Before presenting it, reproduce the commands and inspect at least one failing or ambiguous retrieval case yourself.

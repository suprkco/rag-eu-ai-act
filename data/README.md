# Corpus provenance

`corpus.json` contains 20 selected English articles and their source URLs, text hashes, versions and extraction timestamp.

- **AI Act:** articles 4, 5, 6, 9, 10, 13, 14, 15, 50 and 53 from the [European Commission AI Act Service Desk](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50). Only the article body is extracted, not navigation, summaries or commentary. The Service Desk displays an amendment-related disclaimer; this project does not determine current legal applicability.
- **GDPR:** articles 5, 6, 9, 12, 13, 15, 17, 22, 25 and 32 from the [official UK legislation archive, EU regulation as adopted](https://www.legislation.gov.uk/eur/2016/679/adopted). The importer requests `/adopted/data.xml` and verifies the version. This is not the amended UK GDPR. The canonical EU instrument is [Regulation (EU) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng).

EUR-Lex automated access was unavailable during preparation; the alternate official sources are recorded explicitly. Text normalization collapses whitespace. Full source documents and ingestion caches are not committed. No personal, employer or client data is included.

`evaluation.json` is an authored development set: 20 source-specific questions and five unrelated questions. Each positive label identifies the main expected article, not every article that might be relevant. Do not report these results as general legal QA accuracy.

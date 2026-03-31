---
title: Replace hardcoded FTS stop-word list with spaCy's STOP_WORDS
date: 2026-03-31
status: accepted
amends: "2026-03-26-spacy-model-moved-from-deps-to-runtime-install.md"
tags: [search, fts, nlp, spacy, stop-words]
---

# Replace hardcoded FTS stop-word list with spaCy's STOP_WORDS

## Context

The FTS5 query sanitizer in `charlieverse/db/fts.py` filtered stop words using a ~70-word hardcoded `frozenset`. This was a manual approximation of standard English stop words — reasonable as a bootstrap but not exhaustive.

Since spaCy is already a required dependency (see [2026-03-26 — spaCy model moved from deps to runtime install](2026-03-26-spacy-model-moved-from-deps-to-runtime-install.md)), its `STOP_WORDS` set from `spacy.lang.en.stop_words` is available at import time without the model download. The spaCy list covers ~300+ words, including many domain terms the hardcoded set missed.

## Decision

Replace the hardcoded `_STOPWORDS` frozenset with:

```python
from spacy.lang.en.stop_words import STOP_WORDS
```

This amends the earlier decision to keep spaCy as a dependency — it is now used both for NLP extraction at import time and for FTS query sanitization at search time.

## Alternatives Considered

- **Keep the hardcoded set**: Simpler, no external import. But it will diverge from reality as the codebase evolves and misses common words that produce noisy FTS results.
- **Use NLTK stop words**: Adds a second NLP dependency. spaCy is already required; adding NLTK just for stop words is wasteful.

## Consequences

- FTS searches will filter a broader set of stop words, producing cleaner queries and fewer false matches.
- The `spacy` package (core, not the model) must be importable at server startup. It is already a required dependency so this is no change in practice.
- `spacy.lang.en.stop_words.STOP_WORDS` is available without downloading `en_core_web_sm`. The model is only needed for NLP extraction during `charlie import`.

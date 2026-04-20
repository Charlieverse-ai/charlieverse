---
title: Text Cleaning Helpers Extracted to helpers/text.py
date: 2026-04-20
status: accepted
tags: [refactoring, nlp, helpers, architecture]
---

# Text Cleaning Helpers Extracted to helpers/text.py

## Context

Text cleaning logic (`strip_noise`, `is_ignored`, `clean_text`, `strip_markdown`) was scattered across `charlieverse/db/fts.py` and `charlieverse/nlp/markdown.py`. Multiple modules needed these functions, causing either duplication or awkward cross-layer imports (NLP importing from the DB layer).

The `nlp/extractor.py` module imported `clean_text` from `charlieverse.db.fts`, which is a layer violation — the NLP layer shouldn't depend on the database layer.

## Decision

Create `charlieverse/helpers/text.py` as the single canonical location for text cleaning utilities. Move `strip_noise`, `is_ignored`, `clean_text`, `strip_markdown`, `strip_punctuation`, and `extract_stuff` there. `charlieverse/nlp/markdown.py` now re-exports `strip_markdown` from `helpers.text` for backwards compatibility. The DB FTS module retains only its sanitization logic.

`extract_entities` in the NLP extractor is renamed to `extract_keywords` and accepts a pre-cleaned `CleanedText` type instead of a raw string, removing the internal `clean_text` call and making the contract explicit.

## Alternatives Considered

- **Keep functions in `db/fts.py`**: Maintains the layer violation and obscures that this is general-purpose text processing.
- **Duplicate into `helpers/banned_words.py`**: Creates two copies of the same logic that can drift.

## Consequences

- All text cleaning flows through `helpers.text` — consistent behavior across banned-words detection, NLP extraction, FTS indexing, and reminder rules.
- `CleanedText` type at `extract_keywords` boundary makes it clear that callers are responsible for pre-cleaning.
- The `nlp/markdown.py` re-export is a backwards-compat shim; direct callers should import from `helpers.text`.

---
title: FTS5 query sanitizer returns str, not Optional[str]
date: 2026-04-16
status: accepted
tags: [fts5, sqlite, search, bugfix, api-design]
---

# FTS5 query sanitizer returns str, not Optional[str]

## Context

`sanitize_fts_query` in `charlieverse/db/fts.py` takes raw user input and produces a FTS5 query string with prefix matching (`"token"* OR "token"*`). It used to return `str | None` — `None` when no meaningful tokens survived stopword filtering, a joined query string otherwise. Callers had to handle both truthy/falsy-empty and `None`, though in practice every caller checked with `if not fts_query:` which already short-circuits on both.

Three related crash inputs surfaced in real traffic:

- Raw input containing a null byte (e.g. a paste like `'00\x00'`) reached SQLite and produced an "unterminated string" parser error, because `\x00` terminates a C string and SQLite's FTS5 tokenizer didn't expect embedded null bytes.
- Input containing a bare double quote (e.g. `foo"bar`) got tokenized whole and then wrapped in FTS5's required phrase quotes, producing `"foo"bar"*` — a malformed phrase that crashed the parser.
- Short leftovers from quote stripping (single characters) would also be wrapped and produce noise queries.

## Decision

Harden the sanitizer and simplify the return type:

- Return `str` unconditionally. On no usable tokens, return `""`. Every existing caller already short-circuits on `if not fts_query:` so the behavior at call sites is unchanged.
- Route raw input through a new `clean_text()` helper that strips null bytes (`text.replace("\x00", "")`), rejects ignored inputs (slash commands, XML-tagged messages, interruption markers), normalizes noise (URLs, snake/kebab/camel/Pascal case identifiers, file paths, code blocks, UUIDs, git log lines, multi-spaces), and filters stopwords and tokens shorter than three characters.
- Strip stray double quotes from each token before wrapping (`t.replace('"', "")`) and re-filter any tokens that drop below two characters after stripping.

## Alternatives Considered

- **Escape quotes with FTS5's `""` doubling instead of stripping**: Preserves more input fidelity but adds per-token escaping logic and the searchable content of a token with an embedded quote is nearly always unhelpful. Stripping is simpler and the information loss is acceptable for a search index.
- **Reject hostile input upstream at the API boundary**: Would duplicate the sanitizer in every handler that accepts a search query and still leaves the FTS layer trusting its input. Centralizing the sanitization at the query builder is the cleaner boundary.
- **Keep `str | None`**: Redundant with the empty-string check that callers already do. The distinction between "no input" and "input that filtered to nothing" is not used anywhere — both branches want "don't issue the query".

## Consequences

- Hostile input (null bytes, embedded quotes) no longer crashes the FTS5 parser — the sanitizer produces `""` or a clean query.
- Caller signatures are simpler: `sanitize_fts_query(raw) -> str` with a single `if not fts_query:` guard.
- More input gets filtered away by the noise stripper than before — searches over text that is mostly file paths or code blocks will return fewer tokens, which may reduce recall slightly. The tradeoff is intentional; those tokens rarely produce useful FTS matches.
- The `clean_text()` and `strip_noise()` helpers are reusable for any future sanitization needs (e.g. embedding input, tag extraction).
- Stopwords moved from `spacy.lang.en.stop_words` to `charlieverse.helpers.stop_words`, imported lazily inside `clean_text()` to avoid paying spaCy's import cost on every call.

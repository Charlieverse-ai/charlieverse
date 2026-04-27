---
title: Split Multi-Word NLP Entities for Memory Recall
date: 2026-04-27
status: accepted
tags: [nlp, extractor, enrichment, recall, keywords]
---

# Split Multi-Word NLP Entities for Memory Recall

## Context

The NLP keyword extractor (`charlieverse/nlp/extractor.py`) uses spaCy named entity recognition to pull terms from conversation text. Previously each entity was stored as a whole — a phrase like "Emily Laguna" became a single term "Emily Laguna". When these terms were used to enrich context (i.e., find related memories), the FTS and vector search needed to match the full phrase exactly, which reduced recall for memories that referenced "Emily" or "Laguna" individually.

## Decision

Split each multi-word NLP entity into its individual tokens before adding to the keyword list. "Emily Laguna" becomes `["Emily", "Laguna"]`. Each token goes through the same deduplication and minimum-length check as before.

Also removed `ORG` and `DATE` from the set of relevant entity labels — organizations were generating too many false-positive enrichments (every tool name, file name, and library was being treated as a meaningful recall term), and dates were rarely load-bearing for memory search.

## Alternatives Considered

- **Keep full phrases, use phrase search in FTS**: Would preserve precision but requires FTS phrase query syntax and doesn't help with partial-name memory matches.
- **Keep ORG with a stopword filter**: Would require maintaining a custom org stopword list; not worth the complexity at this stage.
- **Use both the phrase and the individual tokens**: Adds redundancy to the keyword list; the FTS tokenizer already handles sub-phrase matching for most cases.

## Consequences

- Memory recall breadth improves for single-word matches within multi-word entities.
- Slightly higher keyword count per call, mitigated by the 10-keyword cap introduced in the same batch.
- Some precision may be lost for ambiguous single tokens (e.g., "Emily" matching unrelated memories mentioning a different Emily), but this is acceptable — recall is the priority.

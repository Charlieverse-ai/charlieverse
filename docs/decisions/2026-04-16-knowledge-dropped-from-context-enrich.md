---
title: Drop knowledge injection from the context-enrich path
date: 2026-04-16
status: accepted
tags: [context, enrichment, knowledge, reminders, signal]
---

# Drop knowledge injection from the context-enrich path

## Context

Two surfaces enriched a running session with memory lookups against the entities extracted from user text: the `/api/hooks/enrich_context` REST endpoint (`charlieverse/server/api/hooks/enrich_context.py`) and the `SearchMemoriesRule` reminder rule (`charlieverse/context/reminders/rules/search_memories.py`). Both paths fanned out across two stores — `EntityStore` and `KnowledgeStore` — and returned a merged payload with a `"memories"` list and a `"knowledge"` list per matched entity.

In practice this duplicated content that was already loaded. Pinned knowledge articles are injected into activation context on session start; searching knowledge again during enrichment re-surfaced the same long-form articles and pushed them back in front of the model. The knowledge blobs (200-char content previews in the REST path, full-body in the reminder path) also crowded out higher-signal memory hits under the per-enrichment budget.

The snippet extractor in `charlieverse/nlp/snippets.py` was independently sized for a looser budget: `max_chars=800` was chosen when enrichment was carrying both memories and knowledge.

## Decision

Narrow both enrichment paths to entities only.

- `enrich_context.py` drops the `KnowledgeStore` import, removes the per-entity `knowledge.search(...)` call, and stops emitting a `"knowledge"` key in each `found` entry. The seen-ids bookkeeping at the bottom of the handler no longer tracks knowledge ids.
- `SearchMemoriesRule` in the reminder path drops the loop that appended `[knowledge: {topic}] {content}` lines to the injection text.
- `extract_snippet`'s default `max_chars` drops from 800 to 500, matching the tighter single-store budget.

The response field that used to be `"entities"` on the REST payload is renamed to `"memories"` to match the narrowed contents.

## Alternatives Considered

- **Keep the knowledge branch but deduplicate against pinned-in-context ids**: Would solve the duplication but not the crowding — knowledge blobs would still consume the per-enrichment budget when they weren't already pinned. The stronger claim is that knowledge belongs in activation context (loaded once, reused across the session), not in per-turn enrichment.
- **Keep knowledge in the reminder path, drop it only from the REST endpoint**: The two paths exist to serve the same need from different directions; diverging their behavior would make "what does enrichment surface" depend on which caller asked.
- **Keep the 800-char snippet ceiling**: Leaving the budget wide while halving the content sources is wasteful — the snippet extractor doesn't need the headroom it was given.

## Consequences

- Enrichment output is smaller and more memory-dense. The entity path that remains already reranks via `_rank_by_relevance_and_recency`, so what survives is the highest-signal slice.
- Knowledge articles are still discoverable through the dedicated knowledge search tools and through pinned-article activation-context injection — the capability isn't lost, just moved out of the per-turn enrichment hot path.
- `KnowledgeStore` is no longer a dependency of `enrich_context`; the import surface of that file is one store smaller.
- Callers of `extract_snippet` that relied on the 800-char default now get 500-char snippets. Any caller that needed the old ceiling would have to pass `max_chars=800` explicitly; none do at the time of this change.
- If duplication between pinned articles and enrichment ever re-emerges as a concern for entities too, the same argument applies and the same shape of fix is available.

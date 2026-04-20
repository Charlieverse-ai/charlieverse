---
title: Memory Recall Response Flattened from Grouped to Entity List
date: 2026-04-20
status: accepted
tags: [recall, search, api, reminders, memory]
---

# Memory Recall Response Flattened from Grouped to Entity List

## Context

The `SearchMemoriesRule` previously called `/api/context/enrich` which returned grouped results (`found[].memories[].content` plus separate stories array). This required the rule to iterate two separate paths and rendered memories as plain text lines.

The grouping was an artifact of the NLP extraction pipeline (entities grouped by extracted term). For the reminder injection use case, what matters is the ranked list of relevant memories, not which NLP term triggered each one.

## Decision

`SearchMemoriesRule` now calls the search endpoint directly and expects a flat list of `EntitySummary` objects. Each memory is rendered as an XML-tagged element: `<{type} date="{age}">{content}</{type}>`. The rule uses `strip_markdown` on the content before injection to keep the reminder compact.

The entity ranker (`_rank_by_relevance_and_recency`) in `mcp.py` was simplified: the FTS/vector dual-source relevance scoring was dropped because it caused a minimum-score filter that cut relevant-but-older items. The new scorer uses a constant floor plus recency decay — all items pass, recency just determines order.

## Alternatives Considered

- **Keep grouped format, update rule to parse it**: Would preserve the NLP grouping but it adds no value for the injection use case.
- **Return both groups and flat list**: Over-engineering; the rule only needs ranked items.
- **Keep relevance-based min-score filter**: Was cutting valid memories when they were older than 4 weeks. Recency ordering without a hard floor is better.

## Consequences

- The recall injection uses a cleaner XML tagging format that Claude understands structurally.
- Stories are no longer included in the search-memories reminder (they were rarely relevant to the immediate prompt).
- The ranker no longer has a minimum-score threshold — all merged results are returned, just ordered by recency.
- `truncate()` and `MAX_*` constants moved to `server/responses/summaries.py` and are shared across the MCP layer.

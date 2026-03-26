---
title: Recall re-ranking by combined relevance and recency
date: 2026-03-25
status: accepted
tags: [search, recall, ranking, recency]
---

# Recall re-ranking by combined relevance and recency

## Context

Hybrid FTS5 + vector search produces results ordered by individual search scores (BM25 for FTS, cosine for vector). When merging the two result sets, entities found by only one method are interleaved with those found by both. The result set tends to surface older pinned or frequently-embedded entities high up even when recent entries are more contextually appropriate. Charlie's memory grows over time, and recent context should carry more weight by default.

## Decision

After merging FTS and vector results, re-rank entities using a composite score:

```
score = (1 - recency_weight) * relevance + recency_weight * recency
```

- **Relevance**: 1.0 if found by both FTS and vector, 0.5 if found by only one.
- **Recency**: Exponential decay with a 14-day half-life (`exp(-ln(2) * days_old / 14)`).
- **Recency weight**: 0.4 (configurable at call site).

Entities found by both sources outrank single-source results; within a source tier, more recent entities rank higher.

## Alternatives Considered

- **FTS score only**: Fast but ignores semantic relevance and recency.
- **Vector score only**: Semantic but can miss exact keyword matches that FTS finds reliably.
- **RRF (Reciprocal Rank Fusion)**: A standard hybrid merge strategy, but doesn't incorporate recency — all merging is purely rank-based.
- **Constant weights, no decay**: Would require tuning per query type and doesn't naturally favor recent content.

## Consequences

- Recall results are more temporally appropriate for a personal memory assistant where "what was I working on?" implies recent context.
- Entities updated recently will outrank semantically similar but stale entries.
- A 14-day half-life means content from 4 weeks ago scores 0.25 on recency — still surfaced if highly relevant, but not dominant.
- The recency weight (0.4) means relevance still drives most of the ranking for strong matches.
- Future callers can override `recency_weight` if they need pure relevance (e.g., historical search).

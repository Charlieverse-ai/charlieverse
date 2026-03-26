---
title: Recall includes story search and strips markdown before truncation
date: 2026-03-25
status: accepted
tags: [recall, stories, markdown, truncation, context-density]
---

# Recall includes story search and strips markdown before truncation

## Context

The `recall` tool searched entities and knowledge but not stories. Stories (session, daily, weekly, monthly) contain synthesized narrative summaries that are highly relevant to "what has been happening" queries. Excluding them meant a large portion of Charlie's memory was inaccessible through recall.

Separately, recall results returned raw content including markdown formatting (headers, bold, code fences, list bullets). This markup adds length without adding information density when the content is being passed back in an API response — the LLM reading the result doesn't benefit from the formatting symbols, only from the underlying text.

## Decision

1. **Stories included in recall**: `StoryStore.search` is called alongside entity and knowledge search. Up to 5 story results are returned in a new `stories` field in `RecallResponse`. Stories surface via their `summary` field if present, falling back to truncated `content`.

2. **Markdown stripped before truncation**: A new `charlieverse.nlp.markdown.strip_markdown` utility converts content to plain text before applying character limits. This means the same character budget carries more semantic content — a 500-char limit on stripped text is denser than 500 chars of markdown.

3. **Truncation with signaling**: All content fields now return a `(text, truncated: bool)` tuple. The `truncated` flag is surfaced in response schemas so callers can prompt the user to use a focused lookup if they need the full content.

## Alternatives Considered

- **Stories excluded**: Stories were already in activation context via the hook system. But recall is used mid-session for targeted queries and should surface the best available memory across all stores.
- **Return markdown as-is**: Simpler, but wastes token budget on formatting noise. A note about a 3-bullet decision becomes much shorter as plain text.
- **HTML-encode or quote markdown**: Still includes the structural noise.
- **Server-side rendering**: Converting markdown to HTML is even heavier and still inflates character count.

## Consequences

- Recall responses are denser and carry more information per token.
- Story search adds one async DB call per recall invocation — acceptable given stories are infrequently written.
- Content with heavy code blocks will have code stripped; this is appropriate for memory/narrative content but would be wrong for a code search use case. Callers querying for code should use a dedicated path.
- The `strip_markdown` function handles common patterns but is not a full parser — edge cases with nested formatting may leave residual symbols. This is acceptable for the memory use case.
- The `truncated` flag enables progressive disclosure: recall surfaces a summary, a targeted `get` or `search_knowledge` call retrieves the full content.

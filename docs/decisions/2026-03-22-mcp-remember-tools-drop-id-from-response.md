---
title: MCP remember tools return URL only, dropping id from response
date: 2026-03-22
status: accepted
tags: [mcp, tools, api, memory]
---

# MCP remember tools return URL only, dropping id from response

## Context

The `remember_*` MCP tools (`remember_with_url`, `update_memory`, `update_knowledge`) returned a dict containing both `id` and `url`. The `id` field is a raw UUID — it is an internal database identifier with no actionable meaning for an LLM client. The `url` is a permalink that encodes the same identity and is directly usable for linking. Returning both creates redundancy and exposes an internal detail that callers don't need.

## Decision

Remove the `id` field from all `remember_*` and `update_memory` / `update_knowledge` tool responses. These tools now return `{"url": "..."}` only.

## Alternatives Considered

- **Keep both fields**: No cost except minor token overhead. But exposing the raw `id` invites LLM clients to store or reference it directly, which creates coupling to internal identifiers that could change.
- **Return neither, just acknowledge success**: A boolean or empty success response loses the ability to link to the created/updated entity.
- **Return `id` only**: The URL is more useful (human-readable, directly navigable) and already encodes the ID.

## Consequences

- Any client that was extracting `id` from tool responses to use in subsequent calls will need to parse the `id` out of the URL instead, or use the `forget` / `update_memory` tools which accept the UUID directly (those still accept an `id` parameter as input).
- Tool responses are slightly smaller.
- The URL is the canonical external reference to a memory entity; this decision reinforces that convention.

---
title: Make all meaningful fields required on MCP remember_* tools
date: 2026-03-26
status: accepted
tags: [mcp, memory, tools, api-contract]
---

# Make all meaningful fields required on MCP remember_* tools

## Context

All `remember_*` MCP tools (`remember_decision`, `remember_solution`, `remember_preference`, `remember_person`, `remember_milestone`, `remember_moment`, `remember_project`, `remember_event`) and the `update_knowledge` and `session_update` tools had most of their parameters marked as optional (`| None = None`). Fields like `rationale`, `significance`, `feeling`, `context`, `details`, `who`, `where`, `why`, `session_id`, and `tags` could all be omitted.

In practice, an LLM calling these tools without providing `session_id` would create orphaned memories with no session association, and omitting `tags` produced untagged entries that were harder to search and recall. The optional fields for rich context (`rationale`, `feeling`, `significance`, etc.) were the entire point of having separate tool types — a `remember_decision` without a `rationale` is just a `remember_preference` with a different label.

Making fields optional also sent the wrong signal to the LLM client: it suggested that omitting them was acceptable, when in fact missing context degrades memory quality significantly.

## Decision

Make all meaningful fields required (non-optional) on all `remember_*` tools, `update_knowledge`, and `session_update`. `session_id` and `tags` are now required on every tool. Context-rich fields (`rationale`, `significance`, `feeling`, `context`, `details`, `who`, `where`, `why`) are required on the tools that have them.

`pinned` remains optional (defaults to `False`). `workspace` on `session_update` remains optional as it is genuinely situational. `session_id` on `session_update` stays optional since the server can generate a new one if none is provided.

## Alternatives Considered

- **Keep fields optional with better LLM instructions**: Rely on system prompt guidance to make LLMs always fill in the fields. Rejected — required fields in the tool schema are enforced at the protocol level; instructions are not.
- **Add validation that rejects calls with missing fields**: Equivalent to making them required in the schema, but adds runtime error handling. Schema-level required fields are cleaner.
- **Separate minimal vs. rich versions of each tool**: e.g., `remember_decision_brief` vs `remember_decision`. Rejected — unnecessary proliferation. One tool with required fields is simpler.

## Consequences

- Any LLM client that was calling `remember_*` tools without all fields will now receive a validation error. This is intentional — it forces better memory quality.
- The MCP tool reference docs (`docs/mcp-tools.md`) have been updated to reflect all required fields.
- `session_id` being required means the LLM must always pass a valid session UUID. This is already available to the LLM from the activation context injected at session start.

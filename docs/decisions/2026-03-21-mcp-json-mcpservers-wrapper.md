---
title: MCP JSON Config Must Use mcpServers Wrapper Key
date: 2026-03-21
status: accepted
tags: [mcp, integration, config, convention]
---

# MCP JSON Config Must Use mcpServers Wrapper Key

## Context

The `integrations/shared/mcp-json.sh` script generates MCP server configuration JSON consumed by
Claude Code, GitHub Copilot, and other MCP-compatible clients. The original output placed the
server entry at the top level (`charlie-tools: { type, url }`), which does not match the MCP
config schema used by clients.

## Decision

All generated MCP JSON must nest server entries under a `mcpServers` key:

```json
{
  "mcpServers": {
    "charlie-tools": {
      "type": "http",
      "url": "..."
    }
  }
}
```

This matches the format expected by Claude Code's `mcp add` command and the broader MCP
specification for multi-server configs.

## Alternatives Considered

- **Flat top-level keys**: Some early MCP client implementations accepted flat configs, but this
  is not the canonical format and breaks newer clients.

## Consequences

- `integrations/shared/mcp-json.sh` is the single source of truth for MCP config generation;
  all integration scripts that call it inherit the correct format.
- Any future integrations that emit MCP JSON manually must also use the `mcpServers` wrapper.
- Existing users who pasted the old flat JSON into their config files may need to wrap it.

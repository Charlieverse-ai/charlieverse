---
title: Install script uses force-sync and explicit rm/re-add for clean plugin state
date: 2026-03-22
status: accepted
tags: [install, deployment, plugin, claude]
---

# Install script uses force-sync and explicit rm/re-add for clean plugin state

## Context

The Claude plugin install script had two problems that caused stale state to accumulate across installs:

1. `rsync` was called without `--delete`, so files removed from the plugin template were left behind in the deployed plugin directory. Old files could shadow new ones or cause Claude to load behavior that had been intentionally removed.

2. `plugin marketplace update` was being called without first removing the existing marketplace entry. The marketplace `update` command only refreshes existing state — it does not reload the plugin from scratch. Combined with the non-deleting rsync, this meant reinstalls were additive, not clean.

A third issue: `setup_mcp_json` was calling `charlie server url` to retrieve the server URL at install time. This created a runtime dependency on the server being up during install and introduced an indirection that was no longer needed since the URL is passed directly.

## Decision

1. Switch `rsync` to `rsync -av --delete` so the plugin directory is always an exact mirror of the template.
2. Before calling `plugin marketplace update`, explicitly `rm` the existing marketplace entry and its cached directory, then `add` the plugin fresh. This guarantees the marketplace sees a clean load, not a delta.
3. Remove the `charlie server url` call. The URL is passed as `$MCP_URL` and written directly by `mcp-json.sh`.

## Alternatives Considered

- **Keep `rsync` without --delete, manually prune known stale files**: Brittle. Requires the script to know what was removed, which is the opposite of what rsync should handle.
- **Use `marketplace remove + add` without rsync --delete**: Fixes the marketplace state but leaves stale files in the plugin directory that could affect behavior.
- **Regenerate from scratch on every install (full rm -rf)**: More aggressive than needed and would destroy any user customizations in the plugin directory outside the template.

## Consequences

- Installs are now idempotent and clean — running the install script twice produces the same result as running it once.
- Files intentionally removed from the plugin template will be removed from deployed installs on the next `install.sh` run.
- The server does not need to be running during install. `MCP_URL` must be set in the environment or passed as an argument.
- The `upsert_marketplace` function now has a harder dependency on the marketplace CLI accepting `rm` before `update`. If the Claude CLI changes this behavior, the install will fail loudly rather than silently succeeding with stale state.

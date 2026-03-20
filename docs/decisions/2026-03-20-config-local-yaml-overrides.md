---
title: Local config overrides via config.local.yaml
date: 2026-03-20
status: accepted
tags: [config, developer-experience, deployment]
---

# Local config overrides via config.local.yaml

## Context

The main `config.yaml` is tracked in git with default values (host, port, paths). Different machines need different values — Emily's work machine runs on a different port, development might use a different host. Previously this meant stashing changes, pulling, and unstashing on every git operation. All CLI commands had hardcoded `127.0.0.1:8765` references scattered across 6 files.

## Decision

Add `config.local.yaml` support. It's gitignored and deep-merges on top of `config.yaml` at load time. All CLI commands read from `config.server` helpers instead of hardcoded values. The config module exposes `ip_address()`, `port()`, and `api_url()` methods that resolve through the merge chain.

## Alternatives Considered

- **Environment variables**: Standard approach but verbose for multiple settings. `CHARLIEVERSE_HOST=x CHARLIEVERSE_PORT=y charlie server start` is annoying to type every time.
- **CLI flags on every command**: Same verbosity problem. Forces remembering flags instead of setting once.
- **Separate config profiles**: Over-engineered for the current scale. There are two machines, not twenty.

## Consequences

- Machine-specific config never touches git. No more stash/pull/unstash.
- Single source of truth for server connection details across all CLI commands.
- New config values are added to `config.yaml` (tracked) with override capability in `config.local.yaml` (untracked).
- Deep merge means you only specify what differs — a local file with just `server.port: 9000` inherits everything else from the tracked config.

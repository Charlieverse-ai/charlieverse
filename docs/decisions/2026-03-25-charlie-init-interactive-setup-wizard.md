---
title: charlie init rewritten as interactive setup wizard
date: 2026-03-25
status: accepted
tags: [cli, onboarding, init, developer-experience, distribution]
---

# charlie init rewritten as interactive setup wizard

## Context

The original `charlie init` created directories, checked the spaCy model, and built the web dashboard. That was appropriate when Charlieverse was always run from a dev checkout. With wheel distribution, the web dashboard is pre-built (no npm needed), and setup now involves more steps: starting the server, connecting provider integrations, and optionally importing conversation history.

First-run experience was fragmented — users had to run `charlie init`, then manually run `integrations/claude/install.sh`, then `charlie server start`, then figure out import. The old README listed each step with no guidance on which were required.

## Decision

Rewrite `charlie init` as a guided, interactive walkthrough with five phases:

1. **Directories** — create `~/.charlieverse/` structure (always runs)
2. **Dependencies** — verify spaCy, web dashboard presence, jq (always runs)
3. **Server** — detect if running; start if not
4. **Providers** — auto-detect Claude Code / GitHub Copilot in PATH; prompt per detected provider and run its `install.sh`
5. **Import** — offer to import conversation history from detected providers

Add `--quick` / `-q` to run only phases 1–2 for non-interactive environments (CI, scripted installs). The command uses `paths.integration(provider)` to find install scripts so it works from both a dev checkout and an installed wheel.

## Alternatives Considered

- **Keep separate commands, improve docs**: Users still need to know the order and remember to run each one. The original README already had the steps documented — they weren't being followed.
- **Single setup.sh script**: Works fine for dev checkout but doesn't compose with `uvx` installs where the user has no repo to `cd` into.
- **Provider setup as a separate `charlie connect` command**: Splitting it out is cleaner in theory but adds friction. The right time to set up providers is immediately after installing Charlieverse, which is exactly when `init` runs.

## Consequences

- `charlie init` is now the single command for fresh installs — from `uvx install charlieverse && charlie init` to a working setup.
- The `--quick` flag makes it safe to call from scripted environments.
- Provider detection is PATH-based, so if a provider is installed after `charlie init`, the user re-runs `charlie init` to connect it.
- The command calls `paths.integration(provider)` — if the integration assets aren't bundled, it reports a failure rather than crashing.

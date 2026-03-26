---
title: charlie update as a self-contained updater command
date: 2026-03-26
status: accepted
tags: [cli, distribution, update, developer-experience, providers]
---

# charlie update as a self-contained updater command

## Context

After `charlieverse` became a published PyPI package (v1.13.0), users can install it via `uv tool install charlieverse` rather than cloning the repo. Keeping the package current and provider integrations working after an upgrade requires multiple manual steps:

1. `uv tool upgrade charlieverse` (or `git pull && pip install -e .` for dev installs)
2. Re-run each provider's `install.sh` to refresh hooks and agent files
3. `charlie server restart`
4. Reconnect MCP in the AI tool

These steps are not obvious, especially step 2 — provider hooks point to the installed binary, so after an upgrade the hooks still work, but the agent prompt files and output style files may be stale versions from before the upgrade.

## Decision

Add `charlie update` as a single command that:

1. **Detects install mode** by checking for a `.git` directory in the parent of the package directory. If found, it's a dev checkout (editable install); otherwise it's a package install.
2. **Upgrades accordingly**: `git pull && pip install -e .` for dev installs; `uv tool upgrade charlieverse` for package installs.
3. **Reinstalls detected provider integrations** by scanning for installed artifacts (output style symlinks for Claude, agent file for Copilot) and re-running each provider's `install.sh`.
4. **Restarts the server** via `charlie server restart`.
5. **Prints a reconnect reminder** for the MCP client.

## Alternatives Considered

- **Document the manual steps**: Already the case — but documentation is easy to miss. A command is discoverable and repeatable.
- **Auto-update on server start**: Surprising behavior that could break a working session mid-session. Updates should be explicit.
- **`charlie update --provider NAME` flag**: Considered for selective provider reinstall, but the overhead of reinstalling all providers is negligible and the default should always ensure consistency.

## Consequences

- Users can update and reconnect with a single command: `charlie update`.
- Dev installs and package installs are handled identically from the user's perspective.
- Provider detection is heuristic (checks for installed artifacts) — it may miss providers installed in non-standard locations, but it fails gracefully (reports "no integrations detected").
- The command does not bump the version in pyproject.toml or tag — it is purely an operational tool, not part of the release pipeline.

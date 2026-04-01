---
title: Remove Codex and Copilot CLI Agent Integrations
date: 2026-04-01
status: accepted
tags: [agents, integrations, simplification]
---

# Remove Codex and Copilot CLI Agent Integrations

## Context

Charlieverse shipped with two CLI agent integrations: a Codex subagent (`prompts/cli/Codex.md`, `prompts/skills/codex/`) that delegated tasks to OpenAI Codex CLI via `codex exec`, and a Copilot subagent (`prompts/cli/Copilot.md`, `prompts/skills/copilot/`) that delegated to GitHub Copilot CLI via `copilot -p`. Both were passthrough wrappers — they received tasks from Charlie and forwarded them to the respective CLI tool in non-interactive mode.

In practice these integrations were not being used and added surface area that needed to stay in sync with the underlying CLI tools' flag interfaces. The Codex CLI API surface in particular has shifted. The Copilot CLI integration overlapped with the direct use of Claude Code. Maintaining documentation, testing, and prompt quality for these wrappers was a cost with no current benefit.

## Decision

Remove the Codex and Copilot CLI agent definitions and their bundled skills entirely. The `prompts/cli/` directory now only contains agents that are actively used. The installer (`integrations/claude/install.sh`) was also cleaned up to remove references to these agents.

## Alternatives Considered

- **Keep but deprecate (stub with a warning):** Adds noise without benefit. If these are unused, they should not be discoverable or loadable.
- **Move to an optional add-on package:** Premature. If demand returns, adding them back is straightforward.

## Consequences

- The `/codex` and `/copilot` skills are no longer available via Charlie.
- Users who were relying on these passthrough agents will need to invoke those CLI tools directly.
- The bundled skills list is shorter and more focused on what actually ships and works.
- Future re-addition would require verifying current CLI flag interfaces before publishing.

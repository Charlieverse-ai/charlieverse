---
title: Commit .charlie/ workspace to version control
date: 2026-03-20
status: accepted
tags: [tricks, workspace, gitignore, project-conventions]
---

# Commit .charlie/ workspace to version control

## Context

`.charlie/` is the project-local workspace directory — tricks, ideas, and configuration specific to this project's development workflow. It was initially gitignored alongside `.claude/` on the assumption that workspace config is per-machine and personal, similar to `.env` or editor config.

As the ship pipeline and trick system matured, it became clear that project tricks (`commit`, `docs`, `adr`, `changelog`, `qc`, `ship`) are part of the project's development infrastructure, not personal machine config. They define how changes get committed, how documentation gets generated, and how code gets shipped. Any developer (or agent) working on this project should use the same tricks.

## Decision

Remove `.charlie/` from `.gitignore` and commit it to the repo. Project tricks in `.charlie/tricks/` are part of the project's development toolchain. The `.charlie/ideas/` directory is also committed — idea documents are project artifacts, not ephemeral notes.

`.claude/` remains gitignored — Claude Code's session state, hooks config, and local overrides are still machine-specific.

## Alternatives Considered

- **Keep gitignored, document manually**: Developers would have to set up their own tricks from scratch or copy them from docs. Tricks would drift out of sync with the codebase they operate on.
- **Move tricks to a named directory like `tools/`**: Loses the convention — `.charlie/tricks/` is the auto-discovered path. Moving them would break `charlie trick list` discovery without additional config.
- **Ship tricks inside `integrations/`**: Tricks are not provider-specific. They run under any agent that supports the Ditto pattern. Mixing them with provider integrations adds confusion.

## Consequences

- Project tricks are versioned alongside the code they operate on. When the ship pipeline changes, the change is reviewed and tracked.
- Any agent or developer working on this repo gets the tricks automatically via `charlie trick list`.
- The `.charlie/ideas/` directory captures design thinking in-repo. Ideas can reference code and be linked from ADRs.
- Personal or machine-specific workspace files still belong in `config.local.yaml` or `~/.charlieverse/`, not `.charlie/`.
- `.claude/` remains gitignored to avoid committing session state or machine-specific hook paths.

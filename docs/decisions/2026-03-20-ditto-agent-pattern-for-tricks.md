---
title: Ditto agent pattern for tricks (SKILL.md)
date: 2026-03-20
status: accepted
tags: [skills, tricks, agents, extensibility]
---

# Ditto agent pattern for tricks (SKILL.md)

## Context

Charlieverse needs reusable workflows — committing, generating changelogs, shipping, running research — that can be shared across projects and providers. These workflows are too complex for a single prompt but too small to justify a dedicated agent with its own codebase. They need to be discoverable, portable, and executable by any provider that supports subagents.

## Decision

Use a "Ditto" agent pattern: a generic Skill agent reads a SKILL.md file and becomes that skill — absorbing its instructions, constraints, and workflow as its own identity. SKILL.md files are markdown with YAML frontmatter (name, description, argument-hint) and a body containing the workflow steps. The Skill agent is provider-agnostic — any system that can spawn a subagent with a file path can run tricks.

Tricks are discovered automatically from multiple paths: `~/.charlieverse/tricks/`, project `.charlie/tricks/`, and provider-specific skill directories.

## Alternatives Considered

- **Hardcoded agent per workflow**: Each trick gets its own agent definition. Doesn't scale — adding a new trick means modifying agent configuration, not just dropping a file in a directory.
- **Shell scripts**: Portable and simple but can't reason about code, make judgment calls, or adapt to context. A commit script can't decide how to group changes into atomic commits.
- **Plugin system with code**: More powerful but higher barrier to create. A markdown file with steps is writable by anyone, including AI agents generating new tricks.

## Consequences

- Adding a new trick is creating a single SKILL.md file in the right directory. No code, no registration.
- The Skill agent follows the file's instructions literally — if the SKILL.md says step 1, 2, 3, it does 1, 2, 3. Predictable behavior.
- Tricks are composable — the `ship` trick runs `commit`, `docs`, and `changelog` tricks in sequence.
- Quality depends on how well the SKILL.md is written. A vague skill file produces vague results.
- Provider-specific tricks (codex, copilot) can use `context: fork` to run in their own agent context.

---
title: Trick non-blocking dispatch enforced by convention, not frontmatter
date: 2026-03-20
status: accepted
amends: 2026-03-20-ditto-agent-pattern-for-tricks.md
tags: [skills, tricks, agents, subagents, non-blocking]
---

# Trick non-blocking dispatch enforced by convention, not frontmatter

## Context

The original Ditto agent ADR noted that provider-specific tricks could use `context: fork` frontmatter to run in their own agent context. The trick SKILL.md itself had `agent: Charlieverse:tools:Trick` and `context: fork` in its frontmatter to declare that skill execution should be non-blocking.

This amends [2026-03-20 - Ditto agent pattern for tricks (SKILL.md)](2026-03-20-ditto-agent-pattern-for-tricks.md).

## Decision

Remove `agent:` and `context: fork` from the trick SKILL.md frontmatter. Instead, enforce non-blocking dispatch as an explicit rule in the skill's instruction body: "ALL skills should be run using the `Charlieverse:tools:Trick` background subagent to be non-blocking."

The dispatch mechanism moves from a declarative metadata hint (interpreted by the provider) to an imperative instruction (followed by the executing agent).

## Alternatives Considered

- **Keep `context: fork` in frontmatter**: Relies on provider infrastructure to interpret and honor the metadata. The behavior is implicit and only works where the provider supports the property.
- **Per-skill opt-in**: Let each SKILL.md declare its own blocking/non-blocking preference. More flexible but inconsistent — some tricks would block the parent while others would not.

## Consequences

- Non-blocking behavior is now self-documented in the skill file itself, visible to anyone reading the SKILL.md without needing to understand provider-specific frontmatter conventions.
- The rule is enforced by the agent following the skill, not by infrastructure — it works wherever the Trick agent can spawn a subagent, regardless of whether the provider honors frontmatter metadata.
- Removing `context: fork` from frontmatter means that providers relying solely on that property to fork execution will no longer get it automatically; they depend on the agent reading and following the instructions.

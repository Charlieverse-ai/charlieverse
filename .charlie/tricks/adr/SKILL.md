---
name: adr
description: Scan commits and diffs for architectural decisions, record them as immutable ADRs in docs/decisions/. Use when the user says "/adr", wants to record decisions, or asks to extract architectural choices from recent work.
argument-hint: '[commit range (default: last commit) | "all" to scan full history]'
---

## What this trick does

Architectural Decision Record extractor. Analyzes code diffs and identifies significant technical decisions that should be recorded for future reference. Writes immutable ADR files to `docs/decisions/`.

The quality bar: "Would someone joining this project in 6 months benefit from knowing WHY this choice was made?" If no, skip it.

## When to Create an ADR

Create a record when the diff contains:

- A new architectural pattern being introduced (new type strategy, new abstraction layer)
- A library or SDK being added or replaced
- A significant trade-off being made (choosing X over Y for a specific reason)
- A convention being established that future code should follow
- An explicit choice NOT to do something

## When NOT to Create an ADR

Do NOT create a record for:

- Bug fixes
- Version bumps (unless major version with breaking changes)
- Formatting or style changes
- Adding tests for existing code
- Documentation updates
- Routine feature implementation following established patterns
- Config file tweaks

## Steps

### 1. Determine scope

If `$ARGUMENTS` is "all":
```bash
git log --oneline --all
```
Scan the full commit history.

If `$ARGUMENTS` is a commit range (e.g., `HEAD~5..HEAD`):
```bash
git log --oneline $ARGUMENTS
git diff $ARGUMENTS
```

If `$ARGUMENTS` is empty (default — last commit):
```bash
git log --oneline -1
git diff HEAD~1..HEAD
```

### 2. Read existing decisions

```bash
ls docs/decisions/ 2>/dev/null
```

Read any existing ADRs to understand what's already recorded. This prevents duplicates and enables amendment detection.

### 3. Analyze the diff

For each commit in the range, read the full diff and apply the relevance filter (create vs skip criteria above).

For each decision found:
- Identify WHAT was decided
- Identify WHY (from commit messages, code comments, or infer from the change pattern)
- Identify what ALTERNATIVES were considered or rejected (if visible in the diff)
- Identify what it SUPERSEDES (check existing ADRs)

### 4. Amendment detection

Before creating a new decision, check if an existing ADR covers the same area. If a new decision modifies or supersedes an existing one:

1. Do NOT modify the original file (decisions are immutable)
2. Create a new ADR file with `amends: "YYYY-MM-DD-original-title.md"` in the frontmatter
3. Reference the original in the Context section: "This amends [YYYY-MM-DD - Original Title](../category/YYYY-MM-DD-original-title.md)"

### 5. Write ADR files

Create `docs/decisions/` if it doesn't exist:
```bash
mkdir -p docs/decisions
```

For each decision, write a file named `YYYY-MM-DD-kebab-case-topic.md` using today's date:

```markdown
---
title: [Decision Title]
date: YYYY-MM-DD
status: accepted
amends: (optional, filename of superseded ADR)
tags: [relevant, tags]
---

# [Decision Title]

## Context

What situation or problem led to this decision? What constraints existed?

## Decision

What was decided. Be specific about the choice made.

## Alternatives Considered

What other approaches were evaluated and why they were rejected.

## Consequences

What follows from this decision — both positive and negative. What does future code need to respect?
```

### 6. Commit

```bash
git add docs/decisions/
charlie-commit -m "Record architectural decisions from recent changes"
```

### 7. Report

For each decision created, output:
```
ADR: docs/decisions/YYYY-MM-DD-topic.md
  Decision: [one-line summary]
  Why: [one-line rationale]
```

If no decisions were found: "No architectural decisions detected in this changeset."

## Rules

- Decisions are immutable — never edit an existing ADR file, create amendments instead
- Always use `charlie-commit` (never `git commit`)
- Never include co-authored-by or AI references
- Use today's date for the filename, not the commit date
- Signal over noise — fewer high-quality ADRs beat a pile of trivial ones
- The WHY matters more than the WHAT — the code shows what changed, the ADR explains why

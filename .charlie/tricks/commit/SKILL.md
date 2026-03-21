---
name: commit
description: Review repo changes and create logical atomic commits. Use when the user says "/commit", wants to commit their work, or asks to break changes into commits.
argument-hint: '[message (optional)]'
---

## What this skill does

Reviews all staged and unstaged changes in the repo, groups them into logical atomic commits, and commits each one using `charlie-commit`.

## Steps

### 1. Review changes

```bash
git status -u
git diff --stat
git diff
```

Analyze what changed and group into logical commits. Each commit should be a single concern — don't lump unrelated changes together.

### 2. If $ARGUMENTS has a message

Stage all changes and commit with that message:

```bash
git add -A
charlie-commit -m "$ARGUMENTS"
```

Done.

### 3. If no message provided

For each logical group:
1. Stage the relevant files: `git add <files>`
2. Draft a concise commit message (imperative mood, focus on the "why")
3. Commit: `charlie-commit -m "<message>"`

### Rules

- Always use `charlie-commit` (never `git commit`)
- Never include co-authored-by or AI references
- Commit message ends with: `Charlie 🐕 <charlie@charlieverse.ai>`
- Break into atomic commits — one concern per commit
- Don't push. That's a separate step.

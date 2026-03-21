---
name: ship
description: Commit, docs, changelog, and push in one go. Use when the user says "/ship", wants to ship their changes, or asks to commit and push everything.
argument-hint: '[bump type: patch|minor|major (default: patch)]'
---

Runs the full ship pipeline where each step is a Charlie project trick (.charlie/tricks/name)

Execute the workflow, using background subagents for the non-synchronous tasks

```workflow
commit → [docs + adr + changelog] → push
```

Show what was shipped:
- Number of commits
- New version number
- Summary of changes
- ADRs recorded (if any)
- Confirm push succeeded

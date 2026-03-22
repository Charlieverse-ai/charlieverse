---
title: Test coverage runs before commit in the ship workflow
date: 2026-03-22
status: accepted
tags: [workflow, testing, ship, tricks]
---

# Test coverage runs before commit in the ship workflow

## Context

The `ship` trick orchestrates the full release pipeline. The original workflow was:

```
qc → commit → [docs + adr + changelog] → push
```

Tests were not explicitly evaluated as part of shipping. Coverage gaps could be committed and shipped without notice. The `test-coverage` trick (added in v1.10.0) provides an agent-driven step that reviews recent diffs and identifies missing or stale tests, then updates them.

## Decision

Reorder the ship workflow to:

```
test-coverage → qc → [docs + adr + changelog] → commit → push
```

Two changes:
1. `test-coverage` runs first — before quality checks and before committing. Any test additions or updates are included in the commit, not tacked on after.
2. `commit` moves after the parallel `[docs + adr + changelog]` block. This means the commit captures all artifacts (tests, docs, ADRs, changelog entry) in one shot rather than requiring a follow-up commit for documentation.

## Alternatives Considered

- **Add test-coverage as a post-commit step**: Tests would not be part of the same commit as the feature changes. The commit history would have "feature" commits followed by "add tests for feature" commits, which is noisy.
- **Run test-coverage in parallel with docs/adr/changelog**: These tasks can technically run in parallel, but test updates may affect what goes in the changelog (tests added should appear under "Added"). Running test-coverage first gives the changelog skill accurate input.
- **Leave tests to the developer, don't add a ship step**: The skill exists precisely because test coverage tends to be an afterthought. Making it part of the automated pipeline catches gaps automatically.

## Consequences

- The ship pipeline is longer — `test-coverage` adds an agent invocation before QC runs.
- Commits produced by `ship` will more reliably include test coverage for new functionality.
- The `ship` summary now reports tests added/updated as a first-class output alongside version number and ADRs.
- Future tricks inserted into the ship workflow should be placed relative to `commit` deliberately — tricks that produce artifacts (files) belong before `commit`; tricks that validate or publish belong after.

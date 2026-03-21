---
name: changelog
description: Generate or update CHANGELOG.md from git commits using semantic versioning. Use when the user says "/changelog", wants to update the changelog, or asks to generate release notes.
argument-hint: '[bump type: patch|minor|major]'
---

## What this skill does

Reviews commits since the last version tag, determines the version bump, and updates CHANGELOG.md.

## Steps

### 1. Find the latest version

```bash
git tag --sort=-v:refname | head -5
```

If no tags exist, the starting version is `v1.0.0` and all commits are included.

### 2. Get commits since last version

```bash
git log <last-tag>..HEAD --oneline --no-merges
```

If no tag, use all commits:
```bash
git log --oneline --no-merges
```

### 3. Determine version bump

If `$ARGUMENTS` specifies `patch`, `minor`, or `major`, use that.

Otherwise, analyze the commits:
- **major**: breaking changes, architecture rewrites, API changes
- **minor**: new features, new commands, new skills, new integrations
- **patch**: bug fixes, config tweaks, documentation, refactors

### 4. Generate changelog entry

Read existing `CHANGELOG.md` if it exists. Prepend the new version entry at the top.

Format:
```markdown
## [vX.Y.Z] - YYYY-MM-DD

### Added
- New features, skills, commands

### Changed
- Modifications to existing behavior

### Fixed
- Bug fixes

### Removed
- Removed features or deprecated code
```

Group commits by category. Write concise human-readable descriptions (not raw commit messages). Skip empty categories.

### 5. Commit the changelog

Update the version in pyproject.toml

```bash
git add CHANGELOG.md
charlie-commit -m "Update CHANGELOG for vX.Y.Z

Charlie 🐕 <charlie@charlieverse.ai>"
```

### 6. Tag the version

```bash
git tag vX.Y.Z
```

Report the new version and a summary of changes.

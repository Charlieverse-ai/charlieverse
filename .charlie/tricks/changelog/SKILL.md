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

### 3. Check if the latest tag has been pushed

```bash
git log origin/main..HEAD --oneline 2>/dev/null
```

If the latest version tag exists only locally (i.e. the tagged commit appears in the `origin/main..HEAD` range), then this version has NOT been pushed yet. In that case:
1. Delete the existing local tag: `git tag -d <latest-tag>`
2. Merge the new commits into the EXISTING changelog entry for that version (update the entry in place, don't create a new one)
3. Re-tag the new changelog commit with the same version
4. Do NOT bump the version number — keep the same version

Only create a new version bump when the latest tag has already been pushed to origin.

### 3b. Determine version bump (only if bumping)

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

**Filter out noise.** Do NOT include trivial commits that don't matter to someone reading a changelog:
- Formatting fixes (missing newlines, whitespace, trailing commas)
- Lockfile updates (`uv.lock`, `package-lock.json`)
- Version bumps that are just the changelog commit itself
- Typo fixes in non-user-facing files

Only include changes that affect functionality, behavior, or developer experience.

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

### 7. Build the wheel and create a GitHub release

Build the distributable wheel with all bundled assets:

```bash
cd web && npm run build && cd ..
rm -rf dist/
uv build --wheel
```

Create a GitHub release with the wheel attached. Use the changelog entry for this version as the release notes — extract the `## [vX.Y.Z]` section from CHANGELOG.md and pass it as `--notes`:

```bash
gh release create vX.Y.Z dist/*.whl --title "vX.Y.Z" --notes "$(changelog_entry)"
```

Where `changelog_entry` is the markdown content between the `## [vX.Y.Z]` header and the next `## [` header (or end of file). Do NOT use a lazy "See CHANGELOG.md for details" — the release notes should contain the full changelog entry.

Report the new version, summary of changes, and the release URL.

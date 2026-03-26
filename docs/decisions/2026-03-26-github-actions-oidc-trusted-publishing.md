---
title: GitHub Actions release workflow uses OIDC trusted publishing for PyPI
date: 2026-03-26
status: accepted
tags: [ci-cd, github-actions, pypi, security, release, oidc]
---

# GitHub Actions release workflow uses OIDC trusted publishing for PyPI

## Context

Publishing Python packages to PyPI traditionally requires a long-lived API token stored as a GitHub Actions secret. Tokens are:
- Long-lived (valid until manually rotated)
- Stored in repository secrets (a credential that could be exfiltrated)
- Scoped to the account or a specific project, but are bearer tokens — anyone with the token can publish

PyPI added support for OIDC-based Trusted Publishing, where GitHub Actions exchanges a short-lived OIDC token for a scoped PyPI upload token at publish time. No credentials are stored in the repository.

## Decision

The `.github/workflows/release.yml` workflow uses PyPI Trusted Publishing via `uv publish`. The workflow:

1. Triggers on `v*` tag push
2. Builds the web dashboard (`npm run build`)
3. Builds the Python wheel (`uv build --wheel`)
4. Publishes to PyPI using `uv publish` with `id-token: write` permission (OIDC)
5. Creates a GitHub Release with changelog notes

The PyPI project has a Trusted Publisher configured pointing to this repository, the `release.yml` workflow file, and the `pypi` environment (a GitHub environment requiring no approvals).

`uv publish` is used instead of the `pypa/gh-action-pypi-publish` Docker action to avoid the overhead of a Docker image pull in the workflow and to stay consistent with `uv` as the project's package manager.

## Alternatives Considered

- **Long-lived PyPI API token in GitHub secrets**: Works but requires credential management, rotation, and is a stored secret. Ruled out in favor of OIDC.
- **`pypa/gh-action-pypi-publish` Docker action**: Standard approach, but adds Docker pull time and is a separate tool from the rest of the toolchain. `uv publish` achieves the same result and is already present as the package manager.
- **Manual publish from developer machine**: Requires the developer to have PyPI credentials and remember to publish after tagging. Automation ensures every tag push produces a release consistently.

## Consequences

- PyPI releases happen automatically on `git push --tags` with no stored credentials.
- The `pypi` GitHub environment must be configured with a Trusted Publisher in PyPI project settings before the workflow will succeed.
- The web assets must be built before the wheel (`npm run build` runs first) so the wheel bundles the current dashboard.
- Workflow failures (PyPI down, build errors) do not block code merges — the tag still exists and can be re-pushed after fixing the workflow.

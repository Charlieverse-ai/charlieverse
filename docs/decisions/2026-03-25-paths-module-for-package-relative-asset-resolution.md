---
title: Centralized paths module for package-relative asset resolution
date: 2026-03-25
status: accepted
tags: [packaging, distribution, paths, wheel, dev-experience]
---

# Centralized paths module for package-relative asset resolution

## Context

As Charlieverse moves toward `uvx` / wheel distribution, several places in the codebase resolved bundled assets using `Path(__file__).parent.parent.parent / "something"` — hardcoded relative traversal to the repo root. This works in a dev checkout but breaks when installed from a wheel, where the package lives inside a `site-packages` directory and the repo root (with `web/`, `integrations/`, `tools/`, `prompts/`) no longer exists at that relative location.

The problem showed up in at least five files: `spa.py`, `doctor_cmd.py`, `import_cmd.py`, `init_cmd.py`, and `config.py`. Each had its own ad-hoc version of the same resolution logic.

## Decision

Introduce `charlieverse/paths.py` with a small set of named helpers: `web_dist()`, `integrations()`, `integration(provider)`, `prompts()`, and `tools_scripts()`. Each returns a `Path | None`, looking first for the asset bundled inside the package directory (`_PKG_DIR / relative`), then falling back to the repo root (`_REPO_DIR / relative`). `tools_scripts()` handles the name difference — bundled as `tools_scripts/` in the wheel, `tools/` in a dev checkout.

All callers are updated to use these helpers and handle `None` gracefully (e.g., return a 404 response, show a warning, skip a check).

## Alternatives Considered

- **Keep ad-hoc traversal, fix it per file**: Fixes the symptom in each location but leaves the fragility. The next feature that needs a bundled asset will repeat the mistake.
- **Use `importlib.resources`**: The standard approach for Python packages. More robust for deeply nested assets but verbose and requires careful manifest configuration. Overkill for a handful of well-known top-level directories that may or may not be bundled.
- **Always bundle everything in the wheel**: Ensures assets are always present but inflates the wheel size and removes the ability to use a dev checkout without rebuilding.

## Consequences

- All code that needs a bundled asset calls `paths.something()` and checks for `None`. Missing assets degrade gracefully rather than raising `FileNotFoundError`.
- The pattern is self-documenting: a new bundled asset just needs a function in `paths.py`.
- `tools_scripts/` in the wheel vs. `tools/` in the repo is now a single place to maintain.
- Future callers must not re-introduce `Path(__file__).parent.parent.parent` patterns — that's the smell this module was created to eliminate.

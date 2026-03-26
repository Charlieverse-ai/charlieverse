---
title: Move spaCy model install from pyproject.toml to charlie init runtime
date: 2026-03-26
status: accepted
tags: [distribution, pypi, spacy, nlp, dependencies, charlie-init]
---

# Move spaCy model install from pyproject.toml to charlie init runtime

## Context

The spaCy `en_core_web_sm` model was listed as a direct URL dependency in `pyproject.toml`:

```toml
dependencies = [
  "en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/..."
]
```

PyPI rejects wheels that contain direct URL (non-index) dependencies. When the v1.13.0 release workflow tried to upload the built wheel, it failed validation because the wheel's metadata referenced a GitHub URL rather than a PyPI package name. PyPI policy prohibits this to ensure packages can be installed from index alone.

## Decision

Remove `en_core_web_sm` from `pyproject.toml` dependencies entirely. Instead, `charlie init` auto-installs it at runtime if not found — trying `uv pip install` first (for `uv`-managed environments), falling back to `pip install`. The model URL is embedded in `init_cmd.py`.

The `_verify_dependencies()` step in `charlie init` already caught a missing model and warned; this changes the warn to an auto-install attempt.

## Alternatives Considered

- **Use the `spacy` package name instead of direct URL**: `spacy` on PyPI does not include the `en_core_web_sm` model — it is a separate download from the spaCy GitHub releases. There is no PyPI-indexed package for the model.
- **Ship the model inside the wheel**: The model is ~12 MB and would significantly bloat the wheel. Packaging guidelines discourage bundling large binary data.
- **Make spaCy optional**: spaCy drives the NLP extraction that tags memories during import. Making it optional would require conditional import guards throughout the NLP layer. The model is only used by `charlie import` and the NLP extractor, not the MCP server core — so a non-fatal warning for missing model (as existed before) was reasonable, but auto-install on first run is a better experience.

## Consequences

- Charlieverse wheels are now accepted by PyPI.
- First run of `charlie init` on a machine without the spaCy model will perform a network download (~12 MB). This is visible to the user via the step output.
- If neither `uv` nor `pip` is accessible, init falls back to a warning. NLP features degrade gracefully — the MCP server still operates without spaCy.
- `uv`-managed virtual environments require `uv pip install` rather than the bare `python -m pip` (which may not be able to modify the env). The installer now tries `uv` first.

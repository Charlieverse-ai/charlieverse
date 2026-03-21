---
title: Switch to Apache-2.0 License
date: 2026-03-21
status: accepted
tags: [licensing, open-source]
---

# Switch to Apache-2.0 License

## Context

The project was originally released under the MIT license. As Charlieverse moves toward broader
distribution — including GitHub Copilot plugin packaging and potential enterprise use — a license
that explicitly addresses patent grants, contributor terms, and derivative works became necessary.

## Decision

Switch from MIT to Apache License 2.0. The `LICENSE` file, `pyproject.toml`, and all plugin
manifests (`plugin.json`) now reflect Apache-2.0.

## Alternatives Considered

- **MIT**: Simple and permissive, but provides no explicit patent grant and no contributor
  license agreement framing. Adequate for personal tools but weaker for projects anticipating
  commercial downstream use.
- **GPL / LGPL**: Copyleft terms are incompatible with how Charlieverse integrates into
  proprietary AI coding environments (Copilot, Cursor, Codex). Rejected.

## Consequences

- All distribution channels (PyPI, Copilot plugin marketplace, npm if applicable) must surface
  the Apache-2.0 SPDX identifier.
- Contributors implicitly grant a patent license under Apache-2.0 terms.
- Downstream users embedding Charlieverse must retain the `NOTICE` file if one is added.

---
title: Config defaults to ~/.charlieverse without requiring config.yaml
date: 2026-03-25
status: accepted
tags: [config, distribution, defaults, packaging]
amends: "2026-03-20-config-local-yaml-overrides.md"
---

# Config defaults to ~/.charlieverse without requiring config.yaml

## Context

This amends [2026-03-20 - Local config overrides via config.local.yaml](../decisions/2026-03-20-config-local-yaml-overrides.md).

The original config module required a `config.yaml` at the repo root to function — if it wasn't found, `Config()` was returned with empty `Path()` defaults, which broke downstream code. That design assumed Charlieverse was always run from a dev checkout.

With wheel distribution via `uvx`, there is no repo root. Users install the package, run `charlie init`, and everything lives in `~/.charlieverse`. There is no `config.yaml` until the user creates one. The `path: ""` default from an empty `Config()` caused database paths like `Path("") / "charlie.db"` to resolve to the current working directory.

## Decision

Config now has hardcoded defaults that are always valid: `~/.charlieverse` for the data directory, with `database`, `logs`, and `hooks` derived from it. The load order is:

1. Start from `_default_config()` (always valid defaults)
2. Look for `~/.charlieverse/config.yaml` — user config
3. Fall back to `config.yaml` at the repo root — dev checkout
4. If neither exists, return defaults as-is
5. If a yaml is found, deep-merge its values over the defaults, then merge `config.local.yaml` on top

`ServerConfig.host` defaults to `"0.0.0.0"` (was `"127.0.0.1"`) so the server binds to all interfaces by default, consistent with typical local server behavior.

## Alternatives Considered

- **Ship a default `config.yaml` in the wheel**: Possible but requires wheel manifest changes and creates confusion when users can't find the "config file" to edit.
- **Environment variable `CHARLIEVERSE_PATH`**: Clean but adds another thing to document and remember.
- **Prompt for path on first run**: Moves the friction to the wrong place — config shouldn't require interaction.

## Consequences

- `charlie` works immediately after `uvx install charlieverse` with no config file.
- Users who want to customize port, path, or host create `~/.charlieverse/config.yaml` — they don't need to know about or touch the repo.
- Dev checkouts with a `config.yaml` at the repo root continue to work.
- `config.local.yaml` for per-machine overrides continues to work (amends, does not replace, the earlier decision).
- Code that assumes `config.path` is always set (non-empty) is now safe — it will always be `~/.charlieverse` or whatever the yaml specifies.

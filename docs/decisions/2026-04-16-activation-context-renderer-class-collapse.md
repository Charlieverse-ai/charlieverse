---
title: Collapse activation context renderer into a single class
date: 2026-04-16
status: accepted
tags: [architecture, renderer, activation-context, refactoring]
---

# Collapse activation context renderer into a single class

## Context

The activation context renderer in `charlieverse/context/renderer.py` was a module-level `render(bundle)` function orchestrating roughly a dozen private helpers — `_render_entity`, `_render_session`, `_render_recent_messages`, `_render_tricks`, `_render_first_run`, `_session_time`, `_date_group_key`, `_parse_period_date`, `_display_path`, and more. Each helper took the same `bundle` and the same `now` timestamp, threaded shared state through parameters, and individually contributed lines to a local `parts: list[str]` inside `render()`.

Section ordering was implicit — you had to read the body of `render()` top-to-bottom to see which section came before which. Any helper that wanted to emit multiple fragments had to return a newline-joined string, which meant lost control over per-section formatting. And the module exported a dozen private symbols that were all effectively implementation details of one public function.

## Decision

Collapse everything into `ActivationContextRenderer`, a single class whose constructor assembles the output and whose `render()` returns the XML string.

- `__init__(bundle)` stores `self._parts: list[str]` and `self.bundle: ContextBundle`, then picks one of two ordered section lists based on `bundle.is_first_run` and invokes each section in turn.
- Each section is a method (`_render_meta`, `_render_messages`, `_render_sessions`, `_render_moments`, `_render_pinned_memories`, `_render_pinned_knowledge`, `_render_related`, `_render_story`, `_render_first_run`) that appends directly to `self._parts` via `self.append(...)`.
- `render()` joins `self._parts` with newlines and returns the result.

Section ordering is now explicit — you read the list in `__init__` and the order is obvious.

## Alternatives Considered

- **Keep the module-level function, add section-ordering constants**: Would clarify ordering without addressing the shared-state-through-parameters problem. Helpers would still have to return strings rather than directly emitting fragments.
- **Split each section into its own renderer class**: Over-engineered for the current size. Sections are not independently reusable and none has complex enough internal state to justify its own class.
- **Jinja or another template engine**: The output is XML-ish with conditional inclusion per section — templates are a poor fit for conditional structure. The class-with-methods form reads as straight Python without template indirection.

## Consequences

- The public surface of `renderer.py` is one symbol, `ActivationContextRenderer`. Every other name is a method of that class.
- Sections share state through `self._parts` and `self.bundle` instead of threaded parameters. Adding `workspace` or `now` or some new cross-cutting value means setting an attribute in `__init__`, not amending every section signature.
- First-run vs. normal-run branching happens once in `__init__` as a choice of section list, not scattered across helpers checking `bundle.is_first_run`.
- The class is consumed as `ActivationContextRenderer(bundle).render()` — cheap to construct, no lifecycle concerns, no reuse across bundles.
- Tests in `test_renderer.py` were rewritten against `ActivationContextRenderer` rather than the old `render()` function. The test count decreased because section-level helpers no longer have independent public tests.

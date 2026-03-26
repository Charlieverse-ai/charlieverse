---
title: Current workspace surfaced as workspace_directory tag in activation context
date: 2026-03-26
status: accepted
tags: [activation, context, workspace, renderer]
---

# Current workspace surfaced as workspace_directory tag in activation context

## Context

The `workspace` value (the directory where Charlie was started) was stored on sessions and displayed as a line inside the session block in the renderer. However, it was not available at the top level of the activation context as the current working directory — only as a property of historical sessions.

The hooks API accepted a `workspace` query parameter and the session-start hook passed it through, but the `ActivationBuilder.build()` method did not accept or propagate the workspace. It was lost before reaching the renderer for the current session's context header.

The context renderer also showed `session.workspace` without a label, making it easy to miss.

## Decision

Pass `workspace` through the full pipeline: `build(session, workspace)` now accepts the workspace as an explicit parameter. `ContextBundle` gains a `workspace` field. The renderer emits `<workspace_directory>{workspace}</workspace_directory>` near the top of the activation output, before the session ID, so the model knows where it is running before reading any session history.

The in-session workspace display in `_render_session` gains a `Session Dir:` prefix for clarity.

## Alternatives Considered

- **Read workspace from session.workspace**: The current session may not yet have a saved workspace (it is set at session-save time, not session-start time). Passing it explicitly from the hook ensures it is always available even before the first save.
- **Put workspace in the system prompt via a different channel**: The activation context is the right place — it is already the dynamic, session-specific context layer.
- **Tag it as `<cwd>` or `<working_directory>`**: `workspace_directory` is more descriptive and consistent with the existing `workspace` field naming across the codebase.

## Consequences

- The model now knows its working directory at the very start of the activation context, before reading any session history or memory.
- Both the API hooks (`/api/sessions/context`, `/api/sessions/start`) now forward `workspace` into the builder — both call sites were updated.
- The `ContextBundle.workspace` field may be `None` when no workspace is provided (e.g. API calls without the query param). The renderer renders `None` in that case — this is a known rough edge; callers should always pass workspace when available.
- Session-level workspace display in session history blocks now shows `Session Dir:` prefix for readability.

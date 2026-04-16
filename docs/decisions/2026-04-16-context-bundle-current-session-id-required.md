---
title: ContextBundle.current_session_id is a required field
date: 2026-04-16
status: accepted
tags: [activation-context, bugfix, sessions, data-model]
---

# ContextBundle.current_session_id is a required field

## Context

`ContextBundle` used to carry the full current `Session` object as a `session: Session` field, and the renderer derived the current session id by reading `bundle.session.id`. The builder's public API accepted the session object directly: `async def build(session: Session, workspace: str | None)`.

A Python loop-variable-leak bug slipped through this shape: the renderer read what it thought was "the current session id" out of a value that, downstream of a `for session in recent_sessions:` iteration, actually held the last element of `recent_sessions` rather than the session the hook had opened. Activation context went out carrying the wrong UUID.

The user-visible symptom was that `session-save` would update a stale row — it trusted the session id in the activation XML, so it overwrote whatever session happened to be last in the recent list. That caused mixed-format `updated_at` timestamps to appear in the sessions table as the wrong rows were touched repeatedly.

## Decision

Make the current session id an explicit, required field on `ContextBundle`:

```python
@dataclass
class ContextBundle:
    current_session_id: SessionId
    workspace: WorkspaceFilePath | None = None
    recent_sessions: list[Session] = field(default_factory=list)
    ...
```

`ActivationBuilder.build` accepts the id directly — `async def build(session_id: SessionId, workspace: WorkspaceFilePath | None)` — rather than a full `Session`. The renderer's `_render_meta` method emits `<session_id>{self.bundle.current_session_id}</session_id>`. There is no longer a `bundle.session` field for a loop variable (or anything else) to shadow.

## Alternatives Considered

- **Rename `bundle.session` to `bundle.current_session` and rely on naming discipline**: Doesn't address the root cause — a `Session` field on the bundle is still ambient state that any iteration over a list of sessions can accidentally confuse. The fix has to be structural.
- **Pass the session id into the renderer explicitly, leave the bundle unchanged**: Fixes the renderer but leaves the bundle's shape ambiguous about which of its many sessions is "current". The bundle is the data contract; the field belongs there.
- **Keep `bundle.session` alongside `current_session_id`**: Redundant state, two sources of truth for the same fact. Removed `session` entirely.

## Consequences

- The current session id is a typed `SessionId` sitting on the bundle by name. The renderer reads it via `self.bundle.current_session_id` with no indirection and no risk of referencing a loop leftover.
- `session-save` writes to the correct row because the activation context carries the correct id.
- The builder's `build` signature is narrower — it only needs the id and workspace, not the full session object. Callers that already have the session pass `session.id`.
- `workspace` tightens from `str | None` to `WorkspaceFilePath | None` as part of the same change, picking up the branded-string-type discipline.
- The `_dedup` helper local to `build` is no longer applied — dedup now happens via the `ignoring` parameter on `search_by_vector` and the pre-populated `seen_ids` set. This is an incidental simplification visible in the same diff.

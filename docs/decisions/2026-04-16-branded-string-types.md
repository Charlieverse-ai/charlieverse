---
title: Branded string types for validated content
date: 2026-04-16
status: accepted
tags: [types, validation, pydantic, ty, architecture]
---

# Branded string types for validated content

## Context

Before this change, validated string-like content (non-empty strings, workspace paths, tag lists) was typed as plain `str` or `list[str]` throughout models, stores, MCP tools, and the renderer. Pydantic enforced `min_length=1` and similar constraints at runtime, but the type checker had no way to distinguish "any string" from "a string we've already validated as non-empty". A handler could pass the raw `request.json()["title"]` straight into a store call and ty would not complain — the validation happened (or didn't) a layer deeper, at model construction.

The result: tag lists, workspace paths, and required content fields all had runtime guardrails but no compile-time discipline. Missing validation showed up as Pydantic exceptions in tests, not as red squiggles during editing.

## Decision

Introduce branded types in `charlieverse/types/`:

- `NonEmptyString` (in `strings.py`) — subclasses `str` with a custom `__new__` that calls `_parse_non_empty_str`. Registers a Pydantic core schema so it validates from JSON and serializes as a plain string. Also provides `NonEmptyString.or_none(value)` for best-effort construction.
- `WorkspaceFilePath` (in `strings.py`) — subclasses `NonEmptyString`, adds a `display_path` property that collapses `$HOME` back to `~`.
- `TagList` (in `lists.py`) — `NewType("TagList", Annotated[list[NonEmptyString], Field(min_length=1)])`. A list of at least one non-empty string.

Applied across entity, knowledge, session, story, and message models, their stores, the MCP tool signatures, and the activation context renderer. Helpers in the test suite (`_tags()`, `NonEmptyString()` constructors) make it cheap to build these in fixtures.

## Alternatives Considered

- **Keep plain `str` everywhere, rely on Pydantic at the edges**: Validation works but ty cannot help. Every refactor risks introducing a handler that skips model construction and passes raw strings through to a store.
- **Use `Annotated[str, Field(min_length=1)]` in place everywhere**: Verbose at every call site and doesn't give the type a name to rally around. `NonEmptyString` reads as a domain concept; `Annotated[str, Field(...)]` reads as a validator bolted onto a primitive.
- **Wrapper dataclasses (`@dataclass class NonEmptyString: value: str`)**: Strongest separation but breaks ergonomics — every use needs `.value` access and the object no longer works in `f"{x}"` or string concatenation. Subclassing `str` keeps interpolation and slicing while giving the type a distinct identity.

## Consequences

- ty catches raw `str` passed where validated content is expected — the failure mode shifts from runtime exception to editor diagnostic.
- Pydantic still validates at runtime for inputs that arrive as plain JSON strings. `NonEmptyString.__get_pydantic_core_schema__` handles the union of "already a `NonEmptyString`" and "arbitrary string that needs stripping and length-checking".
- Serialization is transparent — `NonEmptyString` serializes to plain `str` via `plain_serializer_function_ser_schema(str, when_used="json")`, so JSON output is unchanged.
- The three types live in one place (`charlieverse/types/`) and are the first reach when a new validated-string concept shows up in the domain.
- Test fixtures had to be updated to wrap literals in `NonEmptyString(...)` or helper factories; the fixture cost is one-time.

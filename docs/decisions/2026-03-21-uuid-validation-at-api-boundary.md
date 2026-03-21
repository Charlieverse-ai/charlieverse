---
title: UUID validation at the REST API boundary
date: 2026-03-21
status: accepted
tags: [api, validation, error-handling, rest]
---

# UUID validation at the REST API boundary

## Context

The REST API routes for entities, knowledge, stories, and sessions all accept a UUID as a path parameter (e.g., `/api/entities/{id}`). The original implementation passed the raw string directly to `UUID(value)`, which raises a `ValueError` on malformed input. FastAPI/Starlette does not automatically catch this, so a request with a syntactically invalid UUID (e.g., `/api/entities/not-a-uuid`) would produce an unhandled exception and a 500 response.

## Decision

Introduce a `_parse_uuid(value: str) -> UUID | None` helper in each API module that wraps the `UUID()` constructor in a try/except and returns `None` on failure. Every path-param handler calls this helper first and returns a pre-constructed `_BAD_UUID = JSONResponse({"error": "Invalid UUID format"}, status_code=400)` sentinel immediately if the result is `None`.

This pattern is applied consistently across `entities.py` and `stories.py`. New API modules must follow the same convention.

## Alternatives Considered

- **Starlette path convertor**: Starlette supports `{id:uuid}` path type converters that reject non-UUID segments at the routing layer. Rejected because the existing route definitions use plain `{id}` and the framework version in use does not guarantee UUID conversion behavior across all methods uniformly.
- **Let it raise a 500**: Simple but exposes implementation details to clients and makes the API appear broken rather than incorrect input.
- **Pydantic validation model for path params**: Would require wrapping each handler with a request model. Heavier than needed for a single scalar field.

## Consequences

- Malformed UUID path params return a `400 Bad Request` with `{"error": "Invalid UUID format"}` rather than a `500 Internal Server Error`.
- The `_parse_uuid` helper is duplicated across API modules rather than shared. This is intentional to keep each module self-contained; a future shared `charlieverse.api.helpers` module could consolidate if the duplication becomes a maintenance burden.
- All new API route handlers that accept a UUID path param must call `_parse_uuid` and guard before proceeding.

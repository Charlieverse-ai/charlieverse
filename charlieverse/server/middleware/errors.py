"""Error-handling middleware that turns Pydantic validation noise into a single
human-readable line before it ever reaches the model.

FastMCP's stock ``ErrorHandlingMiddleware`` falls through to ``Internal error: {error!s}``
for any exception that isn't ``ValueError``/``TypeError``/``NotFoundError``/etc. A
``pydantic.ValidationError`` stringifies to a multi-line wall with ``pydantic.dev``
links and a ``"N validation errors for call[tool_name]"`` envelope — useless to a
model and embarrassing to ship. This middleware intercepts validation errors and
collapses them to one ``field: msg`` line per offending field, returning JSON-RPC
``-32602 Invalid params``. Everything else flows through the parent unchanged.
"""

from __future__ import annotations

from fastmcp.server.middleware import MiddlewareContext
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from mcp import McpError
from mcp.types import ErrorData
from pydantic import ValidationError


class CharlieverseErrorMiddleware(ErrorHandlingMiddleware):
    """Stock FastMCP error middleware plus a clean ``ValidationError`` branch."""

    def _transform_error(self, error: Exception, context: MiddlewareContext) -> Exception:
        if isinstance(error, ValidationError):
            return McpError(ErrorData(code=-32602, message=_format_validation_error(error)))
        return super()._transform_error(error, context)


def _format_validation_error(error: ValidationError) -> str:
    """Compress a Pydantic ``ValidationError`` into a single short line.

    For each field, drop ``is_instance_of`` errors when a sibling error on the same
    field is present (those are noise from union schemas — the sibling is always more
    informative). Dedup identical lines. Format as ``field: msg`` joined by ``; ``.
    """
    raw = error.errors()
    field_types: dict[str, set[str]] = {}
    for err in raw:
        field = _field_path(err.get("loc", ()))
        field_types.setdefault(field, set()).add(str(err.get("type", "")))

    lines: list[str] = []
    seen: set[str] = set()
    for err in raw:
        field = _field_path(err.get("loc", ()))
        err_type = str(err.get("type", ""))

        # Drop is_instance_of noise when there's a more useful sibling on the same field.
        if err_type == "is_instance_of" and len(field_types.get(field, set())) > 1:
            continue

        msg = str(err.get("msg") or "invalid value")
        line = f"{field}: {msg}"
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)

    if not lines:
        lines = ["invalid params"]

    return "Invalid params — " + "; ".join(lines)


def _field_path(loc: object) -> str:
    """Field path with Pydantic union/chain branch tags stripped.

    Pydantic embeds union-branch markers like ``is-instance[SessionId]`` or
    ``chain[uuid,function-plain[validate_uuid()]]`` *inside* the ``loc`` tuple. Real
    field names never contain ``[``, so dropping any segment with one leaves just the
    field path the model author actually wrote.
    """
    if not isinstance(loc, (tuple, list)) or not loc:
        return "params"
    parts = [str(p) for p in loc if "[" not in str(p)]
    if not parts:
        return "params"
    return ".".join(parts)

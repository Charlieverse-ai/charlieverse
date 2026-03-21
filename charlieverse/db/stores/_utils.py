"""Shared utilities for store modules."""

from __future__ import annotations

import json


def _tags_json(tags: list[str] | None) -> str | None:
    return json.dumps(tags) if tags else None


def _tags_list(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    parsed = json.loads(raw)
    return parsed if parsed else None

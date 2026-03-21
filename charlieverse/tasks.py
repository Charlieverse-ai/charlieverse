"""Background task tracking — prevents asyncio tasks from being garbage-collected."""

from __future__ import annotations

import asyncio

# Keep references to background tasks so they don't get GC'd mid-flight (H-02)
_background_tasks: set[asyncio.Task] = set()


def track_task(task: asyncio.Task) -> asyncio.Task:
    """Register a background task so it won't be garbage-collected."""
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task

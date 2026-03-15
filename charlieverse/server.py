"""Charlieverse MCP server — the brain."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastmcp import Context, FastMCP
from fastmcp.server.dependencies import CurrentContext
from fastmcp.server.lifespan import lifespan
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from charlieverse.context import ActivationBuilder
from charlieverse.context import renderer as context_renderer
from charlieverse.db import database
from charlieverse.db.stores import KnowledgeStore, MemoryStore, SessionStore, WorkLogStore
from charlieverse.models import Session
from charlieverse.tools import knowledge as knowledge_tools
from charlieverse.tools import memory as memory_tools
from charlieverse.tools import sessions as session_tools
from charlieverse.tools import work_log as work_log_tools

# Default database path
DEFAULT_DB_PATH = Path.home() / ".charlieverse" / "charlie.db"


@lifespan
async def app_lifespan(server):
    """Initialize database and stores on server start."""
    db_path = DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = await database.connect(db_path)

    # Pre-warm the embedding model so first recall isn't slow
    from charlieverse.embeddings.service import _get_model
    _get_model()

    stores = {
        "db": db,
        "memories": MemoryStore(db),
        "sessions": SessionStore(db),
        "knowledge": KnowledgeStore(db),
        "work_logs": WorkLogStore(db),
    }
    try:
        yield stores
    finally:
        await db.close()


mcp = FastMCP("Charlieverse", lifespan=app_lifespan)


# --- Helper to get stores from context ---

def _stores(ctx: Context) -> dict:
    return ctx.lifespan_context


# ============================================================
# Memory tools
# ============================================================


@mcp.tool
async def remember_decision(
    decision: str,
    rationale: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
):
    """Remember a decision and why it was made."""
    return await memory_tools.remember_decision(
        content=decision, rationale=rationale, session_id=session_id,
        tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
    )


@mcp.tool
async def remember_solution(
    problem: str,
    solution: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    ctx: Context = CurrentContext(),
):
    """Remember a problem and how it was solved."""
    return await memory_tools.remember_solution(
        problem=problem, solution=solution, session_id=session_id,
        tags=tags, memories=_stores(ctx)["memories"],
    )


@mcp.tool
async def remember_preference(
    content: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    ctx: Context = CurrentContext(),
):
    """Remember a user preference or working style note."""
    return await memory_tools.remember_preference(
        content=content, session_id=session_id,
        tags=tags, memories=_stores(ctx)["memories"],
    )


@mcp.tool
async def remember_person(
    content: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    ctx: Context = CurrentContext(),
):
    """Remember a person — who they are, relationship, context."""
    return await memory_tools.remember_person(
        content=content, session_id=session_id,
        tags=tags, memories=_stores(ctx)["memories"],
    )


@mcp.tool
async def remember_milestone(
    milestone: str,
    significance: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    ctx: Context = CurrentContext(),
):
    """Remember a significant achievement or moment."""
    return await memory_tools.remember_milestone(
        milestone=milestone, significance=significance, session_id=session_id,
        tags=tags, memories=_stores(ctx)["memories"],
    )


@mcp.tool
async def remember_moment(
    moment: str,
    feeling: str | None = None,
    context: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    ctx: Context = CurrentContext(),
):
    """Remember a moment from our interactions — write it like a journal entry."""
    return await memory_tools.remember_moment(
        moment=moment, feeling=feeling, context=context, session_id=session_id,
        tags=tags, memories=_stores(ctx)["memories"],
    )


@mcp.tool
async def recall(
    query: str,
    limit: int = 10,
    type: str | None = None,
    ctx: Context = CurrentContext(),
):
    """Search across entities and knowledge. Results are relevance-ordered."""
    return await memory_tools.recall(
        query=query, limit=limit, type=type,
        memories=_stores(ctx)["memories"],
        knowledge_store=_stores(ctx)["knowledge"],
    )


@mcp.tool
async def update_memory(
    id: str,
    content: str | None = None,
    tags: list[str] | None = None,
    session_id: str | None = None,
    ctx: Context = CurrentContext(),
):
    """Update an existing memory's content and/or tags. Preserves creation date and provenance."""
    return await memory_tools.update_memory(
        id=id, content=content, tags=tags, session_id=session_id,
        memories=_stores(ctx)["memories"],
    )


@mcp.tool
async def forget(
    id: str,
    ctx: Context = CurrentContext(),
):
    """Soft-delete an entity."""
    return await memory_tools.forget(id=id, memories=_stores(ctx)["memories"])


@mcp.tool
async def pin(
    id: str,
    pinned: bool,
    ctx: Context = CurrentContext(),
):
    """Pin or unpin an entity. Pinned entities appear in every session's context."""
    return await memory_tools.pin(id=id, pinned=pinned, memories=_stores(ctx)["memories"])


# ============================================================
# Session tools
# ============================================================


@mcp.tool
async def session_update(
    id: str,
    what_happened: str,
    for_next_session: str,
    tags: list[str] | None = None,
    ctx: Context = CurrentContext(),
):
    """Save a detailed snapshot of the current session."""
    return await session_tools.session_update(
        id=id, what_happened=what_happened, for_next_session=for_next_session,
        tags=tags, sessions=_stores(ctx)["sessions"],
    )



# ============================================================
# Knowledge tools
# ============================================================


@mcp.tool
async def search_knowledge(
    query: str,
    limit: int = 5,
    ctx: Context = CurrentContext(),
):
    """Search the knowledge base. Semantic + full-text search across knowledge articles."""
    return await knowledge_tools.search_knowledge(
        query=query, limit=limit,
        knowledge_store=_stores(ctx)["knowledge"],
    )


@mcp.tool
async def update_knowledge(
    topic: str,
    content: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
):
    """Create or update a knowledge article."""
    return await knowledge_tools.update_knowledge(
        topic=topic, content=content, session_id=session_id,
        tags=tags, pinned=pinned,
        knowledge_store=_stores(ctx)["knowledge"],
    )


# ============================================================
# Work log tools
# ============================================================


@mcp.tool
async def log_work(
    content: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    ctx: Context = CurrentContext(),
):
    """Log a work entry — captures technical details that sessions don't."""
    return await work_log_tools.log_work(
        content=content, session_id=session_id,
        tags=tags, work_logs=_stores(ctx)["work_logs"],
    )


@mcp.tool
async def list_work_logs(
    session_id: str | None = None,
    limit: int = 20,
    ctx: Context = CurrentContext(),
):
    """List work log entries, optionally filtered by session."""
    return await work_log_tools.list_work_logs(
        session_id=session_id, limit=limit,
        work_logs=_stores(ctx)["work_logs"],
    )


@mcp.tool
async def search_work_logs(
    query: str,
    limit: int = 10,
    ctx: Context = CurrentContext(),
):
    """Search work logs using full-text search."""
    return await work_log_tools.search_work_logs(
        query=query, limit=limit,
        work_logs=_stores(ctx)["work_logs"],
    )


# ============================================================
# Message search tools
# ============================================================


@mcp.tool
async def search_messages(
    query: str,
    limit: int = 20,
    session_id: str | None = None,
    ctx: Context = CurrentContext(),
):
    """Search past messages in conversations. Returns matching messages with role and date."""
    db = _stores(ctx)["db"]
    if session_id:
        cursor = await db.execute(
            """SELECT m.* FROM messages m
               JOIN messages_fts fts ON m.rowid = fts.rowid
               WHERE messages_fts MATCH ? AND m.session_id = ?
               ORDER BY bm25(messages_fts) LIMIT ?""",
            (query, session_id, limit),
        )
    else:
        cursor = await db.execute(
            """SELECT m.* FROM messages m
               JOIN messages_fts fts ON m.rowid = fts.rowid
               WHERE messages_fts MATCH ?
               ORDER BY bm25(messages_fts) LIMIT ?""",
            (query, limit),
        )

    rows = await cursor.fetchall()
    return {
        "messages": [
            {"id": row["id"], "role": row["role"],
             "content": row["content"][:500], "created_at": row["created_at"]}
            for row in rows
        ]
    }


# ============================================================
# REST API endpoints (for hooks CLI + future web UI)
# ============================================================

# Store references for REST routes (populated during lifespan)
_rest_stores: dict = {}


# Patch lifespan to also populate REST store refs
_original_lifespan = app_lifespan


@lifespan
async def _patched_lifespan(server):
    async with _original_lifespan(server) as stores:
        _rest_stores.update(stores)
        yield stores


# Re-create mcp with patched lifespan
mcp._lifespan = _patched_lifespan


@mcp.custom_route("/api/sessions/start", methods=["POST"])
async def api_session_start(request: Request) -> JSONResponse:
    """Start or resume a session. Returns activation XML."""
    body = await request.json()
    session_id = body.get("session_id", str(uuid4()))
    source = body.get("source", "unknown")
    workspace = body.get("workspace")

    sessions_store: SessionStore = _rest_stores["sessions"]
    memories_store: MemoryStore = _rest_stores["memories"]
    knowledge_store: KnowledgeStore = _rest_stores["knowledge"]

    # Get or create session
    session = await sessions_store.get(UUID(session_id))
    if not session:
        session = Session(id=UUID(session_id), workspace=workspace)
        await sessions_store.create(session)

    # Build activation context
    builder = ActivationBuilder(memories_store, sessions_store, knowledge_store)
    bundle = await builder.build(session)
    activation = context_renderer.render(bundle)

    return JSONResponse({
        "session_id": str(session.id),
        "activation": activation,
    })


@mcp.custom_route("/api/sessions/heartbeat", methods=["POST"])
async def api_heartbeat(request: Request) -> JSONResponse:
    """Heartbeat — keeps session alive."""
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/api/sessions/end", methods=["POST"])
async def api_session_end(request: Request) -> JSONResponse:
    """End a session."""
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/api/health", methods=["GET"])
async def api_health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "server": "charlieverse"})


@mcp.custom_route("/api/hooks/events", methods=["POST"])
async def api_list_hook_events(request: Request) -> JSONResponse:
    """List hook events, optionally filtered by session and date range."""
    body = await request.json()
    db = _rest_stores["db"]
    session_id = body.get("session_id")
    since = body.get("since")  # ISO datetime string
    until = body.get("until")
    limit = body.get("limit", 100)

    conditions = []
    params = []

    if session_id:
        conditions.append("session_id = ?")
        params.append(session_id)
    if since:
        conditions.append("created_at >= ?")
        params.append(since)
    if until:
        conditions.append("created_at <= ?")
        params.append(until)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    cursor = await db.execute(
        f"SELECT * FROM hook_events {where} ORDER BY created_at DESC LIMIT ?",
        params,
    )
    rows = await cursor.fetchall()
    return JSONResponse({
        "events": [
            {
                "id": row["id"], "session_id": row["session_id"],
                "event_type": row["event_type"], "tool_name": row["tool_name"],
                "content": row["content"], "metadata": row["metadata"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    })


@mcp.custom_route("/api/work-logs/latest", methods=["GET"])
async def api_latest_work_log(request: Request) -> JSONResponse:
    """Get the most recent work log entry (for determining unprocessed event range)."""
    db = _rest_stores["db"]
    cursor = await db.execute(
        "SELECT * FROM work_logs WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT 1"
    )
    row = await cursor.fetchone()
    if row:
        return JSONResponse({
            "id": row["id"], "content": row["content"],
            "created_at": row["created_at"],
            "end_date": row["end_date"] if "end_date" in row.keys() else None,
        })
    return JSONResponse({"id": None})


@mcp.custom_route("/api/log", methods=["POST"])
async def api_log_work(request: Request) -> JSONResponse:
    """Record a logbook entry via REST."""
    body = await request.json()
    from datetime import datetime, timezone

    content = body.get("content", "")
    session_id = body.get("session_id", str(uuid4()))
    tags = body.get("tags")

    entry_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    db = _rest_stores["db"]
    await db.execute(
        """INSERT INTO work_logs (id, content, tags, created_session_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (entry_id, content, json.dumps(tags) if tags else None, session_id, now, now),
    )
    await db.execute("INSERT INTO work_logs_fts(work_logs_fts) VALUES('rebuild')")
    await db.commit()

    return JSONResponse({"id": entry_id})


@mcp.custom_route("/api/hooks/event", methods=["POST"])
async def api_hook_event(request: Request) -> JSONResponse:
    """Receive hook events from CLI — tool use, messages, etc."""
    body = await request.json()
    db = _rest_stores["db"]

    event_id = body.get("id", str(uuid4()))
    event_type = body.get("event_type", "unknown")
    session_id = body.get("session_id")
    tool_name = body.get("tool_name")
    content = body.get("content")
    metadata = body.get("metadata")

    import json
    from datetime import datetime, timezone

    await db.execute(
        """INSERT OR IGNORE INTO hook_events (id, session_id, event_type, tool_name, content, metadata, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            event_id, session_id, event_type, tool_name,
            content, json.dumps(metadata) if metadata else None,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    await db.commit()
    return JSONResponse({"saved": True})


@mcp.custom_route("/api/messages", methods=["POST"])
async def api_save_message(request: Request) -> JSONResponse:
    """Save a message captured from hooks."""
    body = await request.json()
    db = _rest_stores["db"]

    msg_id = body.get("id", str(uuid4()))
    session_id = body.get("session_id")
    role = body.get("role", "user")
    content = body.get("content", "")

    from datetime import datetime, timezone

    await db.execute(
        """INSERT OR IGNORE INTO messages (id, session_id, role, content, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (msg_id, session_id, role, content, datetime.now(timezone.utc).isoformat()),
    )

    # Rebuild FTS
    await db.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
    await db.commit()
    return JSONResponse({"saved": True})


@mcp.custom_route("/api/messages/search", methods=["POST"])
async def api_search_messages(request: Request) -> JSONResponse:
    """Search messages via FTS."""
    body = await request.json()
    db = _rest_stores["db"]
    query = body.get("query", "")
    limit = body.get("limit", 20)
    session_id = body.get("session_id")

    if session_id:
        cursor = await db.execute(
            """SELECT m.* FROM messages m
               JOIN messages_fts fts ON m.rowid = fts.rowid
               WHERE messages_fts MATCH ? AND m.session_id = ?
               ORDER BY bm25(messages_fts) LIMIT ?""",
            (query, session_id, limit),
        )
    else:
        cursor = await db.execute(
            """SELECT m.* FROM messages m
               JOIN messages_fts fts ON m.rowid = fts.rowid
               WHERE messages_fts MATCH ?
               ORDER BY bm25(messages_fts) LIMIT ?""",
            (query, limit),
        )

    rows = await cursor.fetchall()
    return JSONResponse({
        "messages": [
            {"id": row["id"], "session_id": row["session_id"], "role": row["role"],
             "content": row["content"][:500], "created_at": row["created_at"]}
            for row in rows
        ]
    })

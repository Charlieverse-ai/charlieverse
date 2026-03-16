"""Charlieverse MCP server — the brain."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

from fastmcp import Context, FastMCP
from fastmcp.server.dependencies import CurrentContext
from fastmcp.server.lifespan import lifespan
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from charlieverse.config import config
from charlieverse.context import ActivationBuilder
from charlieverse.context import renderer as context_renderer
from charlieverse.db import database
from charlieverse.db.stores import KnowledgeStore, MemoryStore, SessionStore, StoryStore, WorkLogStore
from charlieverse.models import EntityType, Session, StoryTier
from charlieverse.tools import knowledge as knowledge_tools
from charlieverse.tools import memory as memory_tools
from charlieverse.tools import sessions as session_tools
from charlieverse.tools import work_log as work_log_tools


@lifespan
async def app_lifespan(server):
    """Initialize database and stores on server start."""
    db_path = config.database.resolved_path
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
        "stories": StoryStore(db),
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
    pinned: bool = False,
    ctx: Context = CurrentContext(),
):
    """Remember a problem and how it was solved."""
    return await memory_tools.remember_solution(
        problem=problem, solution=solution, session_id=session_id,
        tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
    )


@mcp.tool
async def remember_preference(
    content: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
):
    """Remember a user preference or working style note."""
    return await memory_tools.remember_preference(
        content=content, session_id=session_id,
        tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
    )


@mcp.tool
async def remember_person(
    content: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
):
    """Remember a person — who they are, relationship, context."""
    return await memory_tools.remember_person(
        content=content, session_id=session_id,
        tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
    )


@mcp.tool
async def remember_milestone(
    milestone: str,
    significance: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
):
    """Remember a significant achievement or moment."""
    return await memory_tools.remember_milestone(
        milestone=milestone, significance=significance, session_id=session_id,
        tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
    )


@mcp.tool
async def remember_moment(
    moment: str,
    feeling: str | None = None,
    context: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
):
    """Remember a moment from our interactions — write it like a journal entry."""
    return await memory_tools.remember_moment(
        moment=moment, feeling=feeling, context=context, session_id=session_id,
        tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
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
    workspace: str | None = None,
    ctx: Context = CurrentContext(),
):
    """Save a detailed snapshot of the current session."""
    return await session_tools.session_update(
        id=id, what_happened=what_happened, for_next_session=for_next_session,
        tags=tags, workspace=workspace, sessions=_stores(ctx)["sessions"],
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

@mcp.custom_route("/api/sessions/context", methods=["GET"])
async def api_session_context(request: Request) -> PlainTextResponse:
    """Preview activation context for debugging. Returns rendered context as plain text."""
    sessions_store: SessionStore = _rest_stores["sessions"]
    memories_store: MemoryStore = _rest_stores["memories"]
    knowledge_store: KnowledgeStore = _rest_stores["knowledge"]

    session_id = request.query_params.get('session_id')
    workspace = request.query_params.get('workspace')
    session: Session | None = None

    if not session_id:
        recent_sessions = await sessions_store.recent(limit=1, workspace=workspace)
        session = recent_sessions[0] if recent_sessions else None
    else:
        session = await sessions_store.get(session_id=session_id)

    if not session:
        return PlainTextResponse("Missing")

    # Build activation context
    builder = ActivationBuilder(memories_store, sessions_store, knowledge_store)
    bundle = await builder.build(session)
    activation = context_renderer.render(bundle)

    return PlainTextResponse(activation)

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


# ============================================================
# Web UI REST API endpoints
# ============================================================


def _serialize_entity(entity) -> dict:
    """Convert an Entity model to a JSON-safe dict."""
    return {
        "id": str(entity.id),
        "type": entity.type.value,
        "content": entity.content,
        "tags": entity.tags,
        "pinned": entity.pinned,
        "created_session_id": str(entity.created_session_id),
        "created_at": entity.created_at.isoformat(),
        "updated_at": entity.updated_at.isoformat(),
    }


def _serialize_session(session) -> dict:
    """Convert a Session model to a JSON-safe dict."""
    return {
        "id": str(session.id),
        "what_happened": session.what_happened,
        "for_next_session": session.for_next_session,
        "tags": session.tags,
        "workspace": session.workspace,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


def _serialize_knowledge(article) -> dict:
    """Convert a Knowledge model to a JSON-safe dict."""
    return {
        "id": str(article.id),
        "topic": article.topic,
        "content": article.content,
        "tags": article.tags,
        "pinned": article.pinned,
        "created_at": article.created_at.isoformat(),
        "updated_at": article.updated_at.isoformat(),
    }


@mcp.custom_route("/api/entities", methods=["GET"])
async def api_list_entities(request: Request) -> JSONResponse:
    """List entities, optionally filtered by type."""
    memories: MemoryStore = _rest_stores["memories"]
    type_param = request.query_params.get("type")
    limit = int(request.query_params.get("limit", "100"))

    entity_type = EntityType(type_param) if type_param else None
    entities = await memories.list(entity_type=entity_type, limit=limit)

    return JSONResponse({"entities": [_serialize_entity(e) for e in entities]})


@mcp.custom_route("/api/entities/{id}", methods=["GET"])
async def api_get_entity(request: Request) -> JSONResponse:
    """Get a single entity by ID."""
    memories: MemoryStore = _rest_stores["memories"]
    entity_id = request.path_params["id"]

    entity = await memories.get(UUID(entity_id))
    if not entity:
        return JSONResponse({"error": "Entity not found"}, status_code=404)

    return JSONResponse(_serialize_entity(entity))


@mcp.custom_route("/api/sessions/list", methods=["GET"])
async def api_list_sessions(request: Request) -> JSONResponse:
    """List recent sessions."""
    sessions: SessionStore = _rest_stores["sessions"]
    limit = int(request.query_params.get("limit", "50"))

    session_list = await sessions.recent(limit=limit)

    return JSONResponse({"sessions": [_serialize_session(s) for s in session_list]})


@mcp.custom_route("/api/sessions/{id}", methods=["GET"])
async def api_get_session(request: Request) -> JSONResponse:
    """Get a single session by ID."""
    sessions: SessionStore = _rest_stores["sessions"]
    session_id = request.path_params["id"]

    session = await sessions.get(UUID(session_id))
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    return JSONResponse(_serialize_session(session))


@mcp.custom_route("/api/knowledge", methods=["GET"])
async def api_list_knowledge(request: Request) -> JSONResponse:
    """List knowledge articles."""
    knowledge: KnowledgeStore = _rest_stores["knowledge"]
    limit = int(request.query_params.get("limit", "50"))

    articles = await knowledge.list(limit=limit)

    return JSONResponse({"articles": [_serialize_knowledge(a) for a in articles]})


@mcp.custom_route("/api/knowledge/{id}", methods=["GET"])
async def api_get_knowledge(request: Request) -> JSONResponse:
    """Get a single knowledge article by ID."""
    knowledge: KnowledgeStore = _rest_stores["knowledge"]
    article_id = request.path_params["id"]

    article = await knowledge.get(UUID(article_id))
    if not article:
        return JSONResponse({"error": "Knowledge article not found"}, status_code=404)

    return JSONResponse(_serialize_knowledge(article))


def _fts_query(raw: str) -> str:
    """Convert raw search input to FTS5 query with prefix matching.

    Handles hyphens (FTS5 token separators) and adds prefix wildcards.
    """
    import re
    # Split on non-alphanumeric, keep tokens
    tokens = re.findall(r'[a-zA-Z0-9]+', raw)
    if not tokens:
        return raw
    # Each token gets a prefix wildcard, joined with implicit AND
    return ' '.join(f'"{t}"*' for t in tokens)


@mcp.custom_route("/api/search", methods=["POST"])
async def api_search(request: Request) -> JSONResponse:
    """Unified search — FTS5 with prefix matching, vector fallback."""
    body = await request.json()
    query = body.get("query", "")
    limit = body.get("limit", 10)

    if not query:
        return JSONResponse({"entities": [], "knowledge": []})

    memories: MemoryStore = _rest_stores["memories"]
    knowledge: KnowledgeStore = _rest_stores["knowledge"]

    # Try FTS with prefix matching first
    fts_query = _fts_query(query)
    entity_results = []
    knowledge_results = []

    try:
        entity_results = await memories.search(fts_query, limit=limit)
    except Exception:
        pass

    try:
        knowledge_results = await knowledge.search(fts_query, limit=limit)
    except Exception:
        pass

    # If FTS returned nothing, fall back to vector search
    if not entity_results and not knowledge_results:
        try:
            from charlieverse.embeddings.service import embed

            embedding = embed(query)
            entity_results = await memories.search_by_vector(embedding, limit=limit)
            knowledge_results = await knowledge.search_by_vector(embedding, limit=limit)
        except Exception:
            pass

    return JSONResponse({
        "entities": [_serialize_entity(e) for e in entity_results],
        "knowledge": [_serialize_knowledge(a) for a in knowledge_results],
    })


@mcp.custom_route("/api/stats", methods=["GET"])
async def api_stats(request: Request) -> JSONResponse:
    """Dashboard stats — entity counts by type, session count, knowledge count."""
    db = _rest_stores["db"]

    # Entity counts by type
    cursor = await db.execute(
        "SELECT type, COUNT(*) as count FROM entities WHERE deleted_at IS NULL GROUP BY type"
    )
    entity_rows = await cursor.fetchall()
    entity_counts = {row["type"]: row["count"] for row in entity_rows}

    # Session count
    cursor = await db.execute(
        "SELECT COUNT(*) as count FROM sessions WHERE deleted_at IS NULL AND what_happened IS NOT NULL"
    )
    session_row = await cursor.fetchone()
    session_count = session_row["count"] if session_row else 0

    # Knowledge count
    cursor = await db.execute(
        "SELECT COUNT(*) as count FROM knowledge WHERE deleted_at IS NULL"
    )
    knowledge_row = await cursor.fetchone()
    knowledge_count = knowledge_row["count"] if knowledge_row else 0

    return JSONResponse({
        "entities": entity_counts,
        "sessions": session_count,
        "knowledge": knowledge_count,
    })


# ============================================================
# Story API endpoints
# ============================================================


def _serialize_story(story) -> dict:
    """Convert a Story model to a JSON-safe dict."""
    return {
        "id": str(story.id),
        "title": story.title,
        "content": story.content,
        "tier": story.tier.value,
        "period_start": story.period_start,
        "period_end": story.period_end,
        "tags": story.tags,
        "created_at": story.created_at.isoformat(),
        "updated_at": story.updated_at.isoformat(),
    }


@mcp.custom_route("/api/stories", methods=["GET"])
async def api_list_stories(request: Request) -> JSONResponse:
    """List stories, optionally filtered by tier."""
    stories: StoryStore = _rest_stores["stories"]
    tier_param = request.query_params.get("tier")
    limit = int(request.query_params.get("limit", "50"))

    tier = StoryTier(tier_param) if tier_param else None
    story_list = await stories.list(tier=tier, limit=limit)

    return JSONResponse({"stories": [_serialize_story(s) for s in story_list]})


@mcp.custom_route("/api/stories/{id}", methods=["GET"])
async def api_get_story(request: Request) -> JSONResponse:
    """Get a single story by ID."""
    stories: StoryStore = _rest_stores["stories"]
    story_id = request.path_params["id"]

    story = await stories.get(UUID(story_id))
    if not story:
        return JSONResponse({"error": "Story not found"}, status_code=404)

    return JSONResponse(_serialize_story(story))


# ============================================================
# Static file serving (Web UI)
# ============================================================

_WEB_DIST = Path(__file__).parent.parent / "web" / "dist"


@mcp.custom_route("/{path:path}", methods=["GET"])
async def serve_spa(request: Request):
    """Serve the React SPA — static files + index.html fallback."""
    from starlette.responses import FileResponse

    path = request.path_params.get("path", "")

    # Don't serve SPA for API routes
    if path.startswith("api/"):
        return JSONResponse({"error": "Not found"}, status_code=404)

    # Try to serve the exact file
    file_path = _WEB_DIST / path
    if file_path.is_file():
        return FileResponse(file_path)

    # SPA fallback — serve index.html for client-side routing
    index = _WEB_DIST / "index.html"
    if index.is_file():
        return FileResponse(index)

    return PlainTextResponse("Web UI not built. Run: cd web && npm run build", status_code=404)

"""Charlieverse MCP server — the brain."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4
from typing import Literal, TypeAlias

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
from charlieverse.models import EntityType, Session, StoryTier, Entity, Knowledge
from charlieverse.tools import knowledge as knowledge_tools
from charlieverse.tools import memory as memory_tools
from charlieverse.embeddings.service import encode_one

@lifespan
async def app_lifespan(server):
    """Initialize database and stores on server start."""
    db_path = config.database
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = await database.connect(db_path)

    # Pre-warm models so first requests aren't slow
    from charlieverse.embeddings.service import _get_model
    _get_model()

    from charlieverse.nlp.extractor import _get_nlp
    _get_nlp()

    stores = {
        "db": db,
        "memories": MemoryStore(db),
        "sessions": SessionStore(db),
        "knowledge": KnowledgeStore(db),
        "work_logs": WorkLogStore(db),
        "stories": StoryStore(db),
    }

    # Rebuild FTS indexes on startup (fast, ensures consistency)
    try:
        await stores["memories"].rebuild_fts()
        await stores["knowledge"].rebuild_fts()
        await stores["stories"].rebuild_fts()
    except Exception:
        pass

    # Rebuild vector indexes in the background (slow, don't block startup)
    import asyncio

    async def _background_vec_rebuild():
        try:
            await stores["memories"].rebuild_vec()
            await stores["knowledge"].rebuild_vec()
            await stores["stories"].rebuild_vec()
        except Exception:
            pass

    asyncio.create_task(_background_vec_rebuild())

    try:
        yield stores
    finally:
        await db.close()


mcp = FastMCP("Charlieverse", lifespan=app_lifespan)
McpTransport: TypeAlias = Literal["stdio", "http", "sse", "streamable-http"]


# --- Helper to get stores from context ---

def _stores(ctx: Context) -> dict:
    return ctx.lifespan_context


def _permalink(kind: str, id: str) -> str:
    """Build a web UI permalink URL."""
    return f"{config.server.dashboard_url()}{kind}/{id}"


async def _remember_with_url(result, kind: str = "memories") -> dict:
    """Wrap a remember_* result to include a permalink URL."""
    return {"id": str(result.id), "url": _permalink(kind, str(result.id))}


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
    result = await memory_tools.remember_decision(
        content=decision, rationale=rationale, session_id=session_id,
        tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
    )
    return await _remember_with_url(result)


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
    result = await memory_tools.remember_solution(
        problem=problem, solution=solution, session_id=session_id,
        tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
    )
    return await _remember_with_url(result)


@mcp.tool
async def remember_preference(
    content: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
):
    """Remember a user preference or working style note."""
    result = await memory_tools.remember_preference(
        content=content, session_id=session_id,
        tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
    )
    return await _remember_with_url(result)


@mcp.tool
async def remember_person(
    content: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    pinned: bool = False,
    ctx: Context = CurrentContext(),
):
    """Remember a person — who they are, relationship, context."""
    result = await memory_tools.remember_person(
        content=content, session_id=session_id,
        tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
    )
    return await _remember_with_url(result)


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
    result = await memory_tools.remember_milestone(
        milestone=milestone, significance=significance, session_id=session_id,
        tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
    )
    return await _remember_with_url(result)


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
    result = await memory_tools.remember_moment(
        moment=moment, feeling=feeling, context=context, session_id=session_id,
        tags=tags, pinned=pinned, memories=_stores(ctx)["memories"],
    )
    return await _remember_with_url(result)


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
        db=_stores(ctx)["db"],
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
    result = await memory_tools.update_memory(
        id=id, content=content, tags=tags, session_id=session_id,
        memories=_stores(ctx)["memories"],
    )
    return {"id": id, "url": _permalink("memories", id)}


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
    result = await knowledge_tools.update_knowledge(
        topic=topic, content=content, session_id=session_id,
        tags=tags, pinned=pinned,
        knowledge_store=_stores(ctx)["knowledge"],
    )
    return {"id": str(result.id), "url": _permalink("knowledge", str(result.id))}

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
# Session tools
# ============================================================


@mcp.tool
async def session_update(
    what_happened: str,
    for_next_session: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    workspace: str | None = None,
    ctx: Context = CurrentContext(),
):
    """Save a detailed snapshot of the current session — what happened and what's next."""
    from charlieverse.tools.sessions import session_update as _session_update

    stores = _stores(ctx)
    sessions: SessionStore = stores["sessions"]

    # Use provided session_id or generate one
    sid = session_id or str(uuid4())

    result = await _session_update(
        id=sid,
        what_happened=what_happened,
        for_next_session=for_next_session,
        tags=tags,
        workspace=workspace,
        sessions=sessions,
    )
    return {"saved": True, "session_id": sid, "url": _permalink("sessions", sid)}


# ============================================================
# Story tools (MCP — for Storyteller subagent)
# ============================================================


@mcp.tool
async def upsert_story(
    title: str,
    content: str,
    tier: str,
    period_start: str,
    period_end: str,
    summary: str | None = None,
    session_id: str | None = None,
    workspace: str | None = None,
    tags: list[str] | None = None,
    ctx: Context = CurrentContext(),
):
    """Create or update a story. For session stories, matches on session_id."""
    from charlieverse.models.story import Story

    stores = _stores(ctx)
    story_store: StoryStore = stores["stories"]
    sessions_store: SessionStore = stores["sessions"]

    sid = UUID(session_id) if session_id else None

    # Auto-create session row if needed (prevents FK violation)
    if sid:
        existing = await sessions_store.get(sid)
        if not existing:
            await sessions_store.create(Session(id=sid, workspace=workspace))

    story = Story(
        title=title,
        summary=summary,
        content=content,
        tier=StoryTier(tier),
        period_start=period_start,
        period_end=period_end,
        workspace=workspace,
        session_id=sid,
        tags=tags,
    )

    result = await story_store.upsert(story)

    return {"id": str(result.id), "title": result.title, "tier": result.tier.value, "url": _permalink("stories", str(result.id))}


@mcp.tool
async def list_stories(
    tier: str | None = None,
    limit: int = 20,
    ctx: Context = CurrentContext(),
):
    """List stories, optionally filtered by tier (session, daily, weekly, monthly, all-time)."""
    stores = _stores(ctx)
    story_store: StoryStore = stores["stories"]

    story_tier = StoryTier(tier) if tier else None
    stories = await story_store.list(tier=story_tier, limit=limit)

    return {
        "stories": [
            {
                "id": str(s.id),
                "title": s.title,
                "tier": s.tier.value,
                "period_start": s.period_start,
                "period_end": s.period_end,
                "summary": s.summary,
            }
            for s in stories
        ]
    }


@mcp.tool
async def get_story(
    id: str,
    ctx: Context = CurrentContext(),
):
    """Get a story by ID. Returns full content."""
    stores = _stores(ctx)
    story_store: StoryStore = stores["stories"]

    story = await story_store.get(UUID(id))
    if not story:
        return {"error": "Story not found"}

    return {
        "id": str(story.id),
        "title": story.title,
        "summary": story.summary,
        "content": story.content,
        "tier": story.tier.value,
        "period_start": story.period_start,
        "period_end": story.period_end,
        "session_id": str(story.session_id) if story.session_id else None,
        "workspace": story.workspace,
    }


@mcp.tool
async def delete_story(
    id: str,
    ctx: Context = CurrentContext(),
):
    """Soft-delete a story."""
    stores = _stores(ctx)
    story_store: StoryStore = stores["stories"]

    story = await story_store.get(UUID(id))
    if not story:
        return {"error": "Story not found"}

    await story_store.delete(UUID(id))
    return {"deleted": True, "id": id}


@mcp.tool
async def get_story_data(
    target: str,
    ctx: Context = CurrentContext(),
):
    """Get data for the Storyteller to generate a story.

    Args:
        target: Either a session_id (UUID) for session stories,
                or a tier name (daily, weekly, monthly) for rollups.
                Rollups return lower-tier stories for synthesis.
    """
    from datetime import date, timedelta

    stores = _stores(ctx)
    story_store: StoryStore = stores["stories"]
    db = stores["db"]

    # Check if target is a tier name (rollup) or a session_id
    tier_names = {"daily", "weekly", "monthly", "quarterly", "yearly"}
    if target in tier_names:
        today = date.today()

        if target == "daily":
            # Daily rolls up from raw sessions + entities created today
            sessions_store: SessionStore = stores["sessions"]
            sessions = await sessions_store.recent_within_days(days=1)
            session_ids = [str(s.id) for s in sessions]

            # Messages from today's sessions
            messages = []
            for sid in session_ids:
                cursor = await db.execute(
                    """SELECT role, content, created_at FROM messages
                       WHERE session_id = ? ORDER BY created_at ASC""",
                    (sid,),
                )
                for row in await cursor.fetchall():
                    messages.append({
                        "from": "charlie" if row["role"] == "assistant" else "user",
                        "content": row["content"][:500],
                        "created_at": row["created_at"],
                    })

            # Memories created today
            today_start = f"{today.isoformat()}T00:00:00"
            cursor = await db.execute(
                """SELECT type, content, tags FROM entities
                   WHERE deleted_at IS NULL AND created_at >= ?
                   ORDER BY created_at ASC""",
                (today_start,),
            )
            memories = [
                {"type": row["type"], "content": row["content"][:300], "tags": row["tags"]}
                for row in await cursor.fetchall()
            ]

            # Knowledge created today
            cursor = await db.execute(
                """SELECT topic, content, tags FROM knowledge
                   WHERE deleted_at IS NULL AND created_at >= ?
                   ORDER BY created_at ASC""",
                (today_start,),
            )
            knowledge = [
                {"topic": row["topic"], "content": row["content"][:300], "tags": row["tags"]}
                for row in await cursor.fetchall()
            ]

            return {
                "type": "rollup",
                "tier": "daily",
                "range_start": today.isoformat(),
                "range_end": today.isoformat(),
                "sessions": [
                    {
                        "id": str(s.id),
                        "what_happened": s.what_happened,
                        "for_next_session": s.for_next_session,
                        "workspace": s.workspace,
                        "tags": s.tags,
                        "created_at": s.created_at.isoformat(),
                    }
                    for s in sessions
                ],
                "messages": messages,
                "memories": memories,
                "knowledge": knowledge,
            }

        # Weekly+ rolls up from lower-tier stories
        source_tier = None
        range_start = None
        range_end = None

        if target == "weekly":
            source_tier = StoryTier.daily
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)
            range_start = monday.isoformat()
            range_end = sunday.isoformat()
        elif target == "monthly":
            source_tier = StoryTier.weekly
            range_start = today.replace(day=1).isoformat()
            if today.month == 12:
                range_end = today.replace(year=today.year + 1, month=1, day=1).isoformat()
            else:
                range_end = today.replace(month=today.month + 1, day=1).isoformat()

        stories = await story_store.find_by_period(range_start, range_end, limit=50)
        if source_tier:
            stories = [s for s in stories if s.tier == source_tier]

        return {
            "type": "rollup",
            "tier": target,
            "range_start": range_start,
            "range_end": range_end,
            "stories": [
                {
                    "id": str(s.id),
                    "title": s.title,
                    "summary": s.summary,
                    "content": s.content,
                    "tier": s.tier.value,
                    "period_start": s.period_start,
                    "period_end": s.period_end,
                }
                for s in stories
            ],
        }
    else:
        # Session story data
        session_id = target
        sessions_store: SessionStore = stores["sessions"]

        session = await sessions_store.get(UUID(session_id))
        existing_story = await story_store.find_by_session(UUID(session_id))
        last_update = existing_story.updated_at.isoformat() if existing_story else None

        # Get messages
        if last_update:
            cursor = await db.execute(
                """SELECT id, role, content, created_at FROM messages
                   WHERE session_id = ? AND created_at > ?
                   ORDER BY created_at ASC""",
                (session_id, last_update),
            )
        else:
            cursor = await db.execute(
                """SELECT id, role, content, created_at FROM messages
                   WHERE session_id = ? ORDER BY created_at ASC""",
                (session_id,),
            )
        msg_rows = await cursor.fetchall()

        from datetime import datetime as dt

        messages = []
        prev_time = None
        for row in msg_rows:
            created = dt.fromisoformat(row["created_at"])
            seconds_between = None
            if prev_time:
                seconds_between = str(int((created - prev_time).total_seconds()))
            prev_time = created
            messages.append({
                "content": row["content"],
                "from": "charlie" if row["role"] == "assistant" else "user",
                "date_time": created.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                "seconds_between": seconds_between,
            })

        # Recent memories from this session
        cursor = await db.execute(
            """SELECT type, content, tags FROM entities
               WHERE created_session_id = ? AND deleted_at IS NULL
               ORDER BY created_at ASC""",
            (session_id,),
        )
        memories = [
            {"type": row["type"], "content": row["content"][:300], "tags": row["tags"]}
            for row in await cursor.fetchall()
        ]

        return {
            "type": "session",
            "session_id": session_id,
            "workspace": session.workspace if session else None,
            "existing_story": {
                "title": existing_story.title,
                "summary": existing_story.summary,
                "content": existing_story.content,
            } if existing_story else None,
            "messages": messages,
            "memories": memories,
        }


# ============================================================
# REST API endpoints (for hooks CLI + future web UI)
# ============================================================

# Store references for REST routes (populated during lifespan)
_rest_stores: dict = {}
_activation_seen_ids: dict[str, set[str]] = {}  # session_id → IDs delivered at activation


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
    builder = ActivationBuilder(memories_store, sessions_store, knowledge_store, stories=_rest_stores.get("stories"))
    bundle = await builder.build(session)
    activation = context_renderer.render(bundle)

    return PlainTextResponse(activation)

@mcp.custom_route("/api/sessions/start", methods=["POST"])
async def api_session_start(request: Request) -> JSONResponse:
    """Start or resume a session. Returns activation XML."""
    body = await request.json()
    session_id = body.get("session_id", str(uuid4()))
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
    builder = ActivationBuilder(memories_store, sessions_store, knowledge_store, stories=_rest_stores.get("stories"))
    bundle = await builder.build(session)
    activation = context_renderer.render(bundle)

    # Track which IDs were delivered so /api/context/enrich can skip them
    _activation_seen_ids[str(session.id)] = bundle.seen_ids

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


@mcp.custom_route("/api/messages/latest", methods=["GET"])
async def api_latest_message(request: Request) -> JSONResponse:
    """Get the most recent message for a session, optionally filtered by role."""
    db = _rest_stores["db"]
    session_id = request.query_params.get("session_id")
    role = request.query_params.get("role")

    query = "SELECT id, session_id, role, content, created_at FROM messages WHERE 1=1"
    params: list = []

    if session_id:
        query += " AND session_id = ?"
        params.append(session_id)
    if role:
        query += " AND role = ?"
        params.append(role)

    query += " ORDER BY created_at DESC LIMIT 1"

    async with db.execute(query, params) as cursor:
        row = await cursor.fetchone()

    if not row:
        return JSONResponse({})

    return JSONResponse({
        "id": row[0],
        "session_id": row[1],
        "role": row[2],
        "content": row[3][:200],
        "created_at": row[4],
    })


@mcp.custom_route("/api/context/enrich", methods=["POST"])
async def api_context_enrich(request: Request) -> JSONResponse:
    """Extract entities from text and search memories for matches.

    Used by the reminders engine to inject relevant context on each prompt.
    Returns found memories grouped by entity, plus entities with no matches.
    """
    body = await request.json()
    text = body.get("text", "")
    seen_ids = set(body.get("seen_ids", []))
    session_id = body.get("session_id")

    # Merge IDs already delivered during activation so we don't re-inject them
    if session_id:
        seen_ids |= _activation_seen_ids.get(session_id, set())

    if not text:
        return JSONResponse({"entities": [], "found": [], "not_found": [], "stories": []})

    from charlieverse.nlp import extract_entities, extract_temporal_refs

    entities = extract_entities(text)
    temporal_refs = extract_temporal_refs(text)

    memories: MemoryStore = _rest_stores["memories"]
    knowledge: KnowledgeStore = _rest_stores["knowledge"]

    found: list[dict] = []
    not_found: list[str] = []

    for entity in entities:
        # Search memories + knowledge for this entity
        memory_results = await memories.search(entity, limit=3)
        knowledge_results = await knowledge.search(entity, limit=2)

        # Filter out already-seen items and items created in this session
        new_memories = [
            m for m in memory_results
            if str(m.id) not in seen_ids
            and (not session_id or str(m.created_session_id) != session_id)
        ]
        new_knowledge = [
            k for k in knowledge_results
            if str(k.id) not in seen_ids
            and (not session_id or str(k.created_session_id) != session_id)
        ]

        if new_memories or new_knowledge:
            found.append({
                "entity": entity,
                "memories": [
                    {
                        "id": str(m.id),
                        "type": m.type.value,
                        "content": m.content[:200],
                        "tags": m.tags,
                    }
                    for m in new_memories
                ],
                "knowledge": [
                    {
                        "id": str(k.id),
                        "topic": k.topic,
                        "content": k.content[:200],
                    }
                    for k in new_knowledge
                ],
            })
        else:
            not_found.append(entity)

    # Story search — FTS keywords + optional date range in one pass
    # Story search — vector similarity (semantic) with optional date range
    stories_result: list[dict] = []
    story_store: StoryStore = _rest_stores["stories"]

    if text and len(text.strip()) > 5:
        from charlieverse.embeddings import encode_one
        from charlieverse.nlp.snippets import extract_snippet

        try:
            query_embedding = await encode_one(text)

            def _story_entry(story, query_emb, ref_text=None):
                snippet = extract_snippet(story.content, query_emb)
                entry = {
                    "id": str(story.id),
                    "title": story.title,
                    "tier": story.tier.value,
                    "content": snippet,
                    "period_start": story.period_start,
                    "period_end": story.period_end,
                }
                if ref_text:
                    entry["ref"] = ref_text
                return entry

            if temporal_refs:
                for ref in temporal_refs:
                    matching = await story_store.search_by_vector(
                        embedding=query_embedding,
                        period_start=ref.start.isoformat(),
                        period_end=ref.end.isoformat(),
                        limit=3,
                    )
                    for story in matching:
                        if str(story.id) not in seen_ids:
                            seen_ids.add(str(story.id))
                            stories_result.append(_story_entry(story, query_embedding, ref.text))
            else:
                matching = await story_store.search_by_vector(
                    embedding=query_embedding,
                    limit=3,
                )
                for story in matching:
                    if str(story.id) not in seen_ids:
                        stories_result.append(_story_entry(story, query_embedding))
        except Exception:
            pass  # Vector search is best-effort

    # Accumulate IDs returned this prompt so they aren't re-injected next prompt
    if session_id:
        prompt_ids: set[str] = set()
        for entry in found:
            prompt_ids.update(m["id"] for m in entry.get("memories", []))
            prompt_ids.update(k["id"] for k in entry.get("knowledge", []))
        prompt_ids.update(s["id"] for s in stories_result)
        if prompt_ids:
            _activation_seen_ids.setdefault(session_id, set()).update(prompt_ids)

    return JSONResponse({
        "entities": entities,
        "found": found,
        "not_found": not_found,
        "stories": stories_result,
    })


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
        "transcript_path": session.transcript_path,
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


@mcp.custom_route("/api/entities", methods=["POST"])
async def api_create_entity(request: Request) -> JSONResponse:
    """Create a new entity."""
    body = await request.json()
    memories: MemoryStore = _rest_stores["memories"]

    entity = Entity(
        type=EntityType(body["type"]),
        content=body["content"],
        tags=body.get("tags"),
        pinned=body.get("pinned", False),
        created_session_id=UUID(body.get("session_id", str(uuid4()))),
    )
    created = await memories.create(entity)

    # Best-effort embedding
    try:
        from charlieverse.embeddings import encode_one
        embedding = await encode_one(created.content)
        await memories.upsert_embedding(created.id, embedding)
    except Exception:
        pass

    return JSONResponse(_serialize_entity(created), status_code=201)


@mcp.custom_route("/api/entities/{id}", methods=["PATCH"])
async def api_update_entity(request: Request) -> JSONResponse:
    """Update an entity's content, tags, or pinned status."""
    memories: MemoryStore = _rest_stores["memories"]
    entity_id = request.path_params["id"]
    body = await request.json()

    entity = await memories.get(UUID(entity_id))
    if not entity:
        return JSONResponse({"error": "Entity not found"}, status_code=404)

    from datetime import datetime, timezone

    if "content" in body:
        entity.content = body["content"]
    if "tags" in body:
        entity.tags = body["tags"]
    if "pinned" in body:
        entity.pinned = body["pinned"]

    entity.updated_at = datetime.now(timezone.utc)
    updated = await memories.update(entity)

    # Re-embed if content changed
    if "content" in body:
        try:
            from charlieverse.embeddings import encode_one
            embedding = await encode_one(updated.content)
            await memories.upsert_embedding(updated.id, embedding)
        except Exception:
            pass

    return JSONResponse(_serialize_entity(updated))


@mcp.custom_route("/api/entities/{id}", methods=["DELETE"])
async def api_delete_entity(request: Request) -> JSONResponse:
    """Soft-delete an entity."""
    memories: MemoryStore = _rest_stores["memories"]
    entity_id = request.path_params["id"]

    entity = await memories.get(UUID(entity_id))
    if not entity:
        return JSONResponse({"error": "Entity not found"}, status_code=404)

    await memories.delete(UUID(entity_id))
    return JSONResponse({"deleted": True})


@mcp.custom_route("/api/entities/{id}/pin", methods=["POST"])
async def api_pin_entity(request: Request) -> JSONResponse:
    """Toggle pin status on an entity."""
    memories: MemoryStore = _rest_stores["memories"]
    entity_id = request.path_params["id"]
    body = await request.json()

    entity = await memories.get(UUID(entity_id))
    if not entity:
        return JSONResponse({"error": "Entity not found"}, status_code=404)

    pinned = body.get("pinned", not entity.pinned)
    await memories.pin(UUID(entity_id), pinned)

    entity.pinned = pinned
    return JSONResponse(_serialize_entity(entity))


@mcp.custom_route("/api/knowledge", methods=["POST"])
async def api_create_knowledge(request: Request) -> JSONResponse:
    """Create a new knowledge article."""
    body = await request.json()
    knowledge_store: KnowledgeStore = _rest_stores["knowledge"]

    article = Knowledge(
        topic=body["topic"],
        content=body["content"],
        tags=body.get("tags"),
        pinned=body.get("pinned", False),
        created_session_id=UUID(body.get("session_id", str(uuid4()))),
    )
    created = await knowledge_store.create(article)

    try:
        from charlieverse.embeddings import encode_one
        embedding = await encode_one(f"{created.topic} {created.content}")
        await knowledge_store.upsert_embedding(created.id, embedding)
    except Exception:
        pass

    return JSONResponse(_serialize_knowledge(created), status_code=201)


@mcp.custom_route("/api/knowledge/{id}", methods=["PATCH"])
async def api_update_knowledge(request: Request) -> JSONResponse:
    """Update a knowledge article's topic, content, tags, or pinned status."""
    knowledge_store: KnowledgeStore = _rest_stores["knowledge"]
    article_id = request.path_params["id"]
    body = await request.json()

    article = await knowledge_store.get(UUID(article_id))
    if not article:
        return JSONResponse({"error": "Knowledge article not found"}, status_code=404)

    from datetime import datetime, timezone

    if "topic" in body:
        article.topic = body["topic"]
    if "content" in body:
        article.content = body["content"]
    if "tags" in body:
        article.tags = body["tags"]
    if "pinned" in body:
        article.pinned = body["pinned"]

    article.updated_at = datetime.now(timezone.utc)
    updated = await knowledge_store.upsert(article)

    if "topic" in body or "content" in body:
        try:
            from charlieverse.embeddings import encode_one
            embedding = await encode_one(f"{updated.topic} {updated.content}")
            await knowledge_store.upsert_embedding(updated.id, embedding)
        except Exception:
            pass

    return JSONResponse(_serialize_knowledge(updated))


@mcp.custom_route("/api/knowledge/{id}", methods=["DELETE"])
async def api_delete_knowledge(request: Request) -> JSONResponse:
    """Delete a knowledge article."""
    knowledge_store: KnowledgeStore = _rest_stores["knowledge"]
    article_id = request.path_params["id"]

    article = await knowledge_store.get(UUID(article_id))
    if not article:
        return JSONResponse({"error": "Knowledge article not found"}, status_code=404)

    await knowledge_store.delete(UUID(article_id))
    return JSONResponse({"deleted": True})


@mcp.custom_route("/api/knowledge/{id}/pin", methods=["POST"])
async def api_pin_knowledge(request: Request) -> JSONResponse:
    """Toggle pin status on a knowledge article."""
    knowledge_store: KnowledgeStore = _rest_stores["knowledge"]
    article_id = request.path_params["id"]
    body = await request.json()

    article = await knowledge_store.get(UUID(article_id))
    if not article:
        return JSONResponse({"error": "Knowledge article not found"}, status_code=404)

    pinned = body.get("pinned", not article.pinned)
    await knowledge_store.pin(UUID(article_id), pinned)

    article.pinned = pinned
    return JSONResponse(_serialize_knowledge(article))


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
    """Convert raw search input to FTS5 query with prefix matching."""
    from charlieverse.db.fts import sanitize_fts_query

    return sanitize_fts_query(raw)


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
            embedding = encode_one(query)
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
        "summary": story.summary,
        "content": story.content,
        "tier": story.tier.value,
        "period_start": story.period_start,
        "period_end": story.period_end,
        "workspace": story.workspace,
        "session_id": str(story.session_id) if story.session_id else None,
        "tags": story.tags,
        "created_at": story.created_at.isoformat(),
        "updated_at": story.updated_at.isoformat(),
    }


@mcp.custom_route("/api/story-data/{session_id}", methods=["GET"])
async def api_story_data_session(request: Request) -> JSONResponse:
    """Get all data needed for the Storyteller to generate/update a session story.

    Returns: messages, existing story, recent memories/knowledge since last save.
    """
    from datetime import datetime

    session_id = request.path_params["session_id"]
    db = _rest_stores["db"]
    sessions_store: SessionStore = _rest_stores["sessions"]
    story_store: StoryStore = _rest_stores["stories"]

    # Get session
    session = await sessions_store.get(UUID(session_id))
    session_data = {
        "id": session_id,
        "workspace": session.workspace if session else None,
        "transcript_path": session.transcript_path if session else None,
        "created_at": session.created_at.isoformat() if session else None,
    }

    # Get existing session story
    existing_story = await story_store.find_by_session(UUID(session_id))
    existing_story_data = _serialize_story(existing_story) if existing_story else None

    # Get the last story update time to only fetch new messages
    last_update = existing_story.updated_at.isoformat() if existing_story else None

    # Get messages for this session (since last story update, or all)
    if last_update:
        cursor = await db.execute(
            """SELECT id, session_id, role, content, created_at
               FROM messages
               WHERE session_id = ? AND created_at > ?
               ORDER BY created_at ASC""",
            (session_id, last_update),
        )
    else:
        cursor = await db.execute(
            """SELECT id, session_id, role, content, created_at
               FROM messages
               WHERE session_id = ?
               ORDER BY created_at ASC""",
            (session_id,),
        )
    msg_rows = await cursor.fetchall()

    # Build messages with seconds_between and localized times
    messages = []
    prev_time = None
    for row in msg_rows:
        created = datetime.fromisoformat(row["created_at"])
        seconds_between = None
        if prev_time:
            seconds_between = str(int((created - prev_time).total_seconds()))
        prev_time = created

        messages.append({
            "content": row["content"],
            "from": "charlie" if row["role"] == "assistant" else "user",
            "date_time": created.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            "seconds_between_messages": seconds_between,
        })

    # Get recent memories created during this session
    cursor = await db.execute(
        """SELECT id, type, content, tags, created_at FROM entities
           WHERE created_session_id = ? AND deleted_at IS NULL
           ORDER BY created_at ASC""",
        (session_id,),
    )
    memory_rows = await cursor.fetchall()
    memories_data = [
        {"type": row["type"], "content": row["content"][:300], "tags": row["tags"]}
        for row in memory_rows
    ]

    # Get recent knowledge created during this session
    cursor = await db.execute(
        """SELECT id, topic, content, tags, created_at FROM knowledge
           WHERE created_session_id = ? AND deleted_at IS NULL
           ORDER BY created_at ASC""",
        (session_id,),
    )
    knowledge_rows = await cursor.fetchall()
    knowledge_data = [
        {"topic": row["topic"], "content": row["content"][:300], "tags": row["tags"]}
        for row in knowledge_rows
    ]

    return JSONResponse({
        "session": session_data,
        "existing_story": existing_story_data,
        "messages": messages,
        "memories": memories_data,
        "knowledge": knowledge_data,
    })


@mcp.custom_route("/api/story-data/{tier}/{date}", methods=["GET"])
async def api_story_data_tier(request: Request) -> JSONResponse:
    """Get lower-tier stories for rollup generation.

    E.g., /api/story-data/weekly/2026-03-16 returns daily stories for that week.
    """
    tier = request.path_params["tier"]
    date_str = request.path_params["date"]
    story_store: StoryStore = _rest_stores["stories"]

    from datetime import date, timedelta
    target_date = date.fromisoformat(date_str)

    # Determine source tier and date range based on target tier
    source_tier = None
    range_start = None
    range_end = None

    if tier == "daily":
        # Daily rolls up from raw sessions + entities created that day
        sessions_store: SessionStore = _rest_stores["sessions"]
        db = _rest_stores["db"]
        sessions = await sessions_store.recent_within_days(days=1)
        session_ids = [str(s.id) for s in sessions]

        messages = []
        for sid in session_ids:
            cursor = await db.execute(
                """SELECT role, content, created_at FROM messages
                   WHERE session_id = ? ORDER BY created_at ASC""",
                (sid,),
            )
            for row in await cursor.fetchall():
                messages.append({
                    "from": "charlie" if row["role"] == "assistant" else "user",
                    "content": row["content"][:500],
                    "created_at": row["created_at"],
                })

        day_start = f"{target_date.isoformat()}T00:00:00"
        cursor = await db.execute(
            """SELECT type, content, tags FROM entities
               WHERE deleted_at IS NULL AND created_at >= ?
               ORDER BY created_at ASC""",
            (day_start,),
        )
        memories = [
            {"type": row["type"], "content": row["content"][:300], "tags": row["tags"]}
            for row in await cursor.fetchall()
        ]

        cursor = await db.execute(
            """SELECT topic, content, tags FROM knowledge
               WHERE deleted_at IS NULL AND created_at >= ?
               ORDER BY created_at ASC""",
            (day_start,),
        )
        knowledge = [
            {"topic": row["topic"], "content": row["content"][:300], "tags": row["tags"]}
            for row in await cursor.fetchall()
        ]

        return JSONResponse({
            "tier": "daily",
            "date": date_str,
            "range_start": target_date.isoformat(),
            "range_end": target_date.isoformat(),
            "sessions": [_serialize_session(s) for s in sessions],
            "messages": messages,
            "memories": memories,
            "knowledge": knowledge,
        })
    elif tier == "weekly":
        source_tier = StoryTier.daily
        # Monday to Sunday of the week containing target_date
        monday = target_date - timedelta(days=target_date.weekday())
        sunday = monday + timedelta(days=6)
        range_start = monday.isoformat()
        range_end = sunday.isoformat()
    elif tier == "monthly":
        source_tier = StoryTier.weekly
        range_start = target_date.replace(day=1).isoformat()
        # Last day of month
        if target_date.month == 12:
            range_end = target_date.replace(year=target_date.year + 1, month=1, day=1).isoformat()
        else:
            range_end = target_date.replace(month=target_date.month + 1, day=1).isoformat()
    elif tier == "quarterly":
        source_tier = StoryTier.monthly
        quarter_start_month = ((target_date.month - 1) // 3) * 3 + 1
        range_start = target_date.replace(month=quarter_start_month, day=1).isoformat()
        end_month = quarter_start_month + 3
        if end_month > 12:
            range_end = target_date.replace(year=target_date.year + 1, month=end_month - 12, day=1).isoformat()
        else:
            range_end = target_date.replace(month=end_month, day=1).isoformat()
    elif tier == "yearly":
        source_tier = StoryTier.quarterly
        range_start = target_date.replace(month=1, day=1).isoformat()
        range_end = target_date.replace(year=target_date.year + 1, month=1, day=1).isoformat()
    else:
        return JSONResponse({"error": f"Unknown tier: {tier}"}, status_code=400)

    # Fetch source stories within the date range
    stories = await story_store.find_by_period(range_start, range_end, limit=50)
    # Filter to source tier
    if source_tier:
        stories = [s for s in stories if s.tier == source_tier]

    return JSONResponse({
        "tier": tier,
        "date": date_str,
        "source_tier": source_tier.value if source_tier else None,
        "range_start": range_start,
        "range_end": range_end,
        "stories": [_serialize_story(s) for s in stories],
    })


@mcp.custom_route("/api/stories", methods=["PUT"])
async def api_upsert_story(request: Request) -> JSONResponse:
    """Upsert a story. For session stories, matches on session_id."""
    from charlieverse.models.story import Story

    body = await request.json()
    story_store: StoryStore = _rest_stores["stories"]

    session_id = UUID(body["session_id"]) if body.get("session_id") else None

    # Auto-create session row if it doesn't exist (prevents FK violation)
    if session_id:
        sessions_store: SessionStore = _rest_stores["sessions"]
        existing = await sessions_store.get(session_id)
        if not existing:
            await sessions_store.create(Session(
                id=session_id,
                workspace=body.get("workspace"),
            ))

    # Guard against Storyteller returning raw JSON as fields
    title = body.get("title", "")
    summary = body.get("summary")
    content = body.get("content", "")

    # If the title looks like a JSON object, try to extract the actual title
    if isinstance(title, str) and title.strip().startswith("{"):
        try:
            parsed = json.loads(title)
            if isinstance(parsed, dict):
                title = parsed.get("title", title)
                summary = summary or parsed.get("summary")
                content = content or parsed.get("content", content)
        except json.JSONDecodeError:
            pass

    # If content is a JSON object, extract fields from it
    if isinstance(content, str) and content.strip().startswith("{"):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "content" in parsed:
                title = title or parsed.get("title", "")
                summary = summary or parsed.get("summary")
                content = parsed.get("content", content)
        except json.JSONDecodeError:
            pass

    # Reject empty/test stories
    if not title or not content or len(content.strip()) < 20:
        return JSONResponse({"error": "Story must have a title and content (min 20 chars)"}, status_code=400)

    story = Story(
        title=title,
        summary=summary,
        content=content,
        tier=StoryTier(body.get("tier", "session")),
        period_start=body.get("period_start"),
        period_end=body.get("period_end"),
        workspace=body.get("workspace"),
        session_id=session_id,
        tags=body.get("tags"),
    )

    result = await story_store.upsert(story)

    # Sync embedding
    try:
        from charlieverse.embeddings import encode_one
        from sqlite_vec import serialize_float32

        text = f"{result.title}\n{result.summary or ''}\n{result.content}"
        embedding = await encode_one(text)
        db = _rest_stores["db"]
        cursor = await db.execute(
            "SELECT rowid FROM stories WHERE id = ?", (str(result.id),)
        )
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "INSERT OR REPLACE INTO stories_vec(rowid, embedding) VALUES(?, ?)",
                (row[0], serialize_float32(embedding)),
            )
            await db.commit()
    except Exception:
        pass  # Embedding sync is best-effort

    return JSONResponse(_serialize_story(result))


@mcp.custom_route("/api/stories/{id}", methods=["DELETE"])
async def api_delete_story(request: Request) -> JSONResponse:
    """Delete a story."""
    story_store: StoryStore = _rest_stores["stories"]
    story_id = request.path_params["id"]

    story = await story_store.get(UUID(story_id))
    if not story:
        return JSONResponse({"error": "Story not found"}, status_code=404)

    await story_store.delete(UUID(story_id))
    return JSONResponse({"deleted": True})


@mcp.custom_route("/api/stories/cleanup", methods=["POST"])
async def api_cleanup_stories(request: Request) -> JSONResponse:
    """Delete all stories with empty or 'test' titles."""
    story_store: StoryStore = _rest_stores["stories"]
    db = _rest_stores["db"]

    cursor = await db.execute(
        """SELECT id FROM stories
           WHERE deleted_at IS NULL
           AND (title IS NULL OR title = '' OR LOWER(title) = 'test' OR LOWER(title) = 'test title'
                OR LENGTH(TRIM(title)) < 5)"""
    )
    rows = await cursor.fetchall()
    deleted = 0

    for row in rows:
        await story_store.delete(UUID(row["id"]))
        deleted += 1

    return JSONResponse({"deleted": deleted})


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


async def _rebuild_all(stores: dict) -> dict:
    """Rebuild FTS + vector indexes for all tables."""
    memories: MemoryStore = stores["memories"]
    knowledge: KnowledgeStore = stores["knowledge"]
    stories: StoryStore = stores["stories"]

    await memories.rebuild_fts()
    await knowledge.rebuild_fts()
    await stories.rebuild_fts()

    await memories.rebuild_vec()
    await knowledge.rebuild_vec()
    await stories.rebuild_vec()

    return {"fts": "rebuilt", "vec": "rebuilt"}


@mcp.custom_route("/api/rebuild", methods=["POST"])
async def api_rebuild(request: Request) -> JSONResponse:
    """Rebuild all FTS and vector indexes across entities, knowledge, and stories."""
    result = await _rebuild_all(_rest_stores)
    return JSONResponse(result)


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

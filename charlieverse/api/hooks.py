"""REST hook endpoints: session lifecycle, heartbeat, health, work-logs, messages, context enrich."""

from __future__ import annotations

from uuid import uuid4

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from charlieverse.context import ActivationBuilder
from charlieverse.context import renderer as context_renderer
from charlieverse.db.fts import clean_text, sanitize_fts_query
from charlieverse.embeddings import encode_one
from charlieverse.helpers.uuid import uuid_from_str
from charlieverse.memory.context import StoreContext
from charlieverse.memory.entities import EntityStore
from charlieverse.memory.knowledge import KnowledgeStore
from charlieverse.memory.sessions import Session, SessionId, UpdateSession
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stories import StoryStore
from charlieverse.types.dates import utc_now
from charlieverse.types.id import ModelId


def register_routes(mcp: FastMCP, rest_stores: StoreContext) -> None:
    """Register hook REST endpoints on the given FastMCP instance."""
    # Lazy import to avoid circular dependency (hooks → server → mcp → tools → server)
    from charlieverse.server import get_seen_ids, set_seen_ids

    @mcp.custom_route("/api/sessions/context", methods=["GET"])
    async def api_session_context(request: Request) -> PlainTextResponse:
        """Preview activation context for debugging. Returns rendered context as plain text."""
        sessions_store: SessionStore = rest_stores["sessions"]
        memories_store: EntityStore = rest_stores["memories"]
        knowledge_store: KnowledgeStore = rest_stores["knowledge"]

        session_id = uuid_from_str(request.query_params.get("session_id"))
        workspace = request.query_params.get("workspace")
        session: Session | None = None

        if not session_id:
            recent_sessions = await sessions_store.recent(limit=1, workspace=workspace)
            session = recent_sessions[0] if recent_sessions else None
        else:
            session = await sessions_store.get(SessionId(session_id))

        if not session:
            return PlainTextResponse("Missing")

        builder = ActivationBuilder(
            memories_store,
            sessions_store,
            knowledge_store,
            stories=rest_stores.get("stories"),
        )
        bundle = await builder.build(session, workspace)
        activation = context_renderer.render(bundle)

        return PlainTextResponse(activation)

    @mcp.custom_route("/api/sessions/start", methods=["POST"])
    async def api_session_start(request: Request) -> JSONResponse:
        """Start or resume a session. Returns activation XML."""
        body = await request.json()
        session_id = body.get("session_id", str(uuid4()))
        workspace = body.get("workspace")

        sessions_store: SessionStore = rest_stores["sessions"]
        memories_store: EntityStore = rest_stores["memories"]
        knowledge_store: KnowledgeStore = rest_stores["knowledge"]

        session = await sessions_store.upsert(UpdateSession(id=session_id, workspace=workspace))

        builder = ActivationBuilder(
            memories_store,
            sessions_store,
            knowledge_store,
            stories=rest_stores.get("stories"),
        )
        bundle = await builder.build(session, workspace)
        activation = context_renderer.render(bundle)

        set_seen_ids(session.id, bundle.seen_ids)

        return JSONResponse(
            {
                "session_id": str(session.id),
                "activation": activation,
            }
        )

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

    @mcp.custom_route("/api/messages", methods=["POST"])
    async def api_save_message(request: Request) -> JSONResponse:
        """Save a message captured from hooks."""
        body = await request.json()
        db = rest_stores["db"]

        msg_id = body.get("id", str(uuid4()))
        session_id = body.get("session_id")
        role = body.get("role")
        content = str(body.get("content", "")).strip()

        if not session_id or not role or not content:
            return JSONResponse({"error": "Missing Required params"}, status_code=400)

        # TODO: Move this into a validation helper
        if "<task-notification>" in content and "</task-notification>" in content:
            return JSONResponse({"saved": False, "reason": "Not saved because the user message is not valid"})

        cursor = await db.execute(
            """INSERT OR IGNORE INTO messages (id, session_id, role, content, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (msg_id, session_id, role, content, utc_now().isoformat()),
        )
        # Only sync FTS if the row was actually inserted (not a duplicate)
        if cursor.rowcount > 0:
            row_cursor = await db.execute("SELECT rowid FROM messages WHERE id = ?", (msg_id,))
            msg_row = await row_cursor.fetchone()
            if msg_row:
                await db.execute(
                    "INSERT INTO messages_fts(rowid, content) VALUES(?, ?)",
                    (msg_row[0], content),
                )
        await db.commit()
        return JSONResponse({"saved": True})

    @mcp.custom_route("/api/messages/latest", methods=["GET"])
    async def api_latest_message(request: Request) -> JSONResponse:
        """Get the most recent message for a session, optionally filtered by role."""
        db = rest_stores["db"]
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

        return JSONResponse(
            {
                "id": row[0],
                "session_id": row[1],
                "role": row[2],
                "content": row[3][:200],
                "created_at": row[4],
            }
        )

    @mcp.custom_route("/api/context/enrich", methods=["POST"])
    async def api_context_enrich(request: Request) -> JSONResponse:
        """Extract entities from text and search memories for matches.

        Used by the reminders engine to inject relevant context on each prompt.
        Returns found memories grouped by entity, plus entities with no matches.
        """
        body = await request.json()
        text = clean_text(body.get("text", ""))

        if not text:
            return JSONResponse({"entities": [], "found": [], "not_found": [], "stories": []})

        seen_ids: set[ModelId] = set(body.get("seen_ids", []))
        session_id = body.get("session_id")

        if session_id:
            seen_ids |= get_seen_ids(session_id)

        from charlieverse.nlp import extract_entities, extract_temporal_refs

        entities = extract_entities(text)
        temporal_refs = extract_temporal_refs(text)

        memories: EntityStore = rest_stores["memories"]
        knowledge: KnowledgeStore = rest_stores["knowledge"]

        found: list[dict] = []
        not_found: list[str] = []

        for entity in entities:
            memory_results = await memories.search(entity, limit=3, include_pinned=False)
            knowledge_results = await knowledge.search(entity, limit=1, include_pinned=False)

            new_memories = [m for m in memory_results if m.id not in seen_ids and (not session_id or m.created_session_id != session_id)]
            new_knowledge = [k for k in knowledge_results if k.id not in seen_ids and (not session_id or k.created_session_id != session_id)]

            if new_memories or new_knowledge:
                found.append(
                    {
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
                    }
                )
            else:
                not_found.append(entity)

        stories_result: list[dict] = []
        story_store: StoryStore = rest_stores["stories"]

        if text and len(text.strip()) > 5:
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
                                seen_ids.add(story.id)
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
                pass

        if session_id:
            prompt_ids: set[ModelId] = set()
            for entry in found:
                prompt_ids.update(m["id"] for m in entry.get("memories", []))
                prompt_ids.update(k["id"] for k in entry.get("knowledge", []))
            prompt_ids.update(s["id"] for s in stories_result)
            if prompt_ids:
                existing = get_seen_ids(session_id)
                existing.update(prompt_ids)
                set_seen_ids(session_id, existing)

        return JSONResponse(
            {
                "entities": entities,
                "found": found,
                "not_found": not_found,
                "stories": stories_result,
            }
        )

    @mcp.custom_route("/api/messages/search", methods=["POST"])
    async def api_search_messages(request: Request) -> JSONResponse:
        """Search messages via FTS."""
        body = await request.json()
        db = rest_stores["db"]
        query = body.get("query", "")
        limit = body.get("limit", 20)
        session_id = body.get("session_id")
        safe_query = sanitize_fts_query(query)

        if not safe_query:
            return JSONResponse({"messages": []})

        if session_id:
            cursor = await db.execute(
                """SELECT m.* FROM messages m
                   JOIN messages_fts fts ON m.rowid = fts.rowid
                   WHERE messages_fts MATCH ? AND m.session_id = ?
                   ORDER BY bm25(messages_fts) LIMIT ?""",
                (safe_query, session_id, limit),
            )
        else:
            cursor = await db.execute(
                """SELECT m.* FROM messages m
                   JOIN messages_fts fts ON m.rowid = fts.rowid
                   WHERE messages_fts MATCH ?
                   ORDER BY bm25(messages_fts) LIMIT ?""",
                (safe_query, limit),
            )

        rows = await cursor.fetchall()
        return JSONResponse(
            {
                "messages": [
                    {
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "role": row["role"],
                        "content": row["content"][:500],
                        "created_at": row["created_at"],
                    }
                    for row in rows
                ]
            }
        )

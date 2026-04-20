from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request

from charlieverse.helpers.text import clean_stopwords, clean_text, extract_stuff
from charlieverse.memory.entities import EntityId, EntityStore
from charlieverse.memory.messages import MessageRole
from charlieverse.memory.sessions import SessionId
from charlieverse.memory.stores import Stores
from charlieverse.server.responses import EmptyResponse, ModelListResponse
from charlieverse.server.responses.summaries import EntitySummary
from charlieverse.server.utils.seen_models import process_enriched_topics, set_seen_ids


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    """Register hook REST endpoints on the given FastMCP instance."""
    # Lazy import to avoid circular dependency (hooks → server → mcp → tools → server)
    from charlieverse.nlp import extract_keywords
    from charlieverse.server.utils.seen_models import get_seen_ids

    @mcp.custom_route("/api/context/enrich", methods=["POST"])
    async def api_context_enrich(request: Request) -> EmptyResponse | ModelListResponse:
        """Extract entities from text and search memories for matches.

        Used by the reminders engine to inject relevant context on each prompt.
        Returns found memories grouped by entity, plus entities with no matches.
        """
        body = await request.json()
        text = body.get("text")
        session_id = SessionId.or_none(body.get("session_id"))
        seen_ids: set[EntityId] = set(body.get("seen_ids") or [])

        if not text or not session_id:
            return EmptyResponse()

        session = await rest_stores.sessions.get(session_id)
        if not session:
            return EmptyResponse()

        last_charlie = await rest_stores.messages.latest(session, role=MessageRole.charlie)
        if last_charlie:
            text += f" {last_charlie.content}"

        keywords = [
            *extract_keywords(clean_text(text)),
            *extract_stuff(text),
        ]
        keywords = process_enriched_topics(session_id, clean_stopwords(keywords))

        if not keywords:
            return EmptyResponse()

        seen_ids |= get_seen_ids(session_id)
        memories: EntityStore = rest_stores.memories

        # Let sanitize_fts_query build the FTS5 query shape. Passing our own
        # pre-quoted tokens gets them re-wrapped as "tok*"* which breaks
        # prefix matching.
        results = await memories.search(
            " ".join(keywords),
            limit=3,
            include_pinned=False,
            ignoring=list(seen_ids),
            excluding_session_id=session_id,
        )

        seen_ids |= {memory.id for memory in results}
        set_seen_ids(session_id, seen_ids)

        return ModelListResponse([EntitySummary.from_memory(memory, False) for memory in results])

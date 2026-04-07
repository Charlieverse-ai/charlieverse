"""REST hook endpoints: session lifecycle, heartbeat, health, work-logs, messages, context enrich."""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from charlieverse.db.fts import clean_text
from charlieverse.embeddings import encode_one
from charlieverse.memory.entities import EntityStore
from charlieverse.memory.knowledge import KnowledgeStore
from charlieverse.memory.stores import Stores
from charlieverse.memory.stories import StoryStore
from charlieverse.types.id import ModelId


def register_routes(mcp: FastMCP, rest_stores: Stores) -> None:
    """Register hook REST endpoints on the given FastMCP instance."""
    # Lazy import to avoid circular dependency (hooks → server → mcp → tools → server)
    from charlieverse.server.utils.seen_models import get_seen_ids, set_seen_ids

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

        memories: EntityStore = rest_stores.memories
        knowledge: KnowledgeStore = rest_stores.knowledge

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
                                "id": m.id,
                                "type": m.type.value,
                                "content": m.content[:200],
                                "tags": m.tags,
                            }
                            for m in new_memories
                        ],
                        "knowledge": [
                            {
                                "id": k.id,
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
        story_store: StoryStore = rest_stores.stories

        if text and len(text.strip()) > 5:
            from charlieverse.nlp.snippets import extract_snippet

            try:
                query_embedding = await encode_one(text)

                def _story_entry(story, query_emb, ref_text=None):
                    snippet = extract_snippet(story.content, query_emb)
                    entry = {
                        "id": story.id,
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
                            if story.id not in seen_ids:
                                seen_ids.add(story.id)
                                stories_result.append(_story_entry(story, query_embedding, ref.text))
                else:
                    matching = await story_store.search_by_vector(
                        embedding=query_embedding,
                        limit=3,
                    )
                    for story in matching:
                        if story.id not in seen_ids:
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

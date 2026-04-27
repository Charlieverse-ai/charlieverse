"""Activation context builder — assembles the context bundle for session start."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from charlieverse.embeddings import encode_one
from charlieverse.helpers.banned_words import BANNED_WORDS
from charlieverse.memory.entities import Entity, EntityId
from charlieverse.memory.entities.mcp import _rank_by_relevance_and_recency
from charlieverse.memory.knowledge import Knowledge
from charlieverse.memory.messages import Message
from charlieverse.memory.sessions import Session, SessionId
from charlieverse.memory.stores import Stores
from charlieverse.types.strings import WorkspaceFilePath

logger = logging.getLogger(__name__)


@dataclass
class ContextBundle:
    """Everything needed to render the activation context."""

    current_session_id: SessionId
    workspace: WorkspaceFilePath | None = None
    recent_sessions: list[Session] = field(default_factory=list)
    pinned_entities: list[Entity] = field(default_factory=list)
    moments: list[Entity] = field(default_factory=list)
    session_entities: list[Entity] = field(default_factory=list)
    related_entities: list[Entity] = field(default_factory=list)
    pinned_knowledge: list[Knowledge] = field(default_factory=list)
    recent_messages: list[Message] = field(default_factory=list)
    banned_words: list[str] = field(default_factory=list)

    @property
    def is_first_run(self) -> bool:
        """True when the database has no prior context — birthday time."""
        return not self.recent_sessions and not self.pinned_entities and not self.moments

    @property
    def seen_ids(self) -> set[EntityId]:
        """All IDs delivered in this activation — used for downstream dedup."""
        ids: set[EntityId] = set()
        for group in (self.moments, self.pinned_entities, self.session_entities, self.related_entities):
            ids.update(e.id for e in group)

        return ids


class ActivationBuilder:
    """Assembles the activation context for a session.

    Priority order for entities (earlier = higher priority, deduped):
    1. Moments (personality — always loaded)
    2. Pinned entities (skip if already in moments)
    3. Session-linked entities (skip if already above)
    4. Related entities via embeddings (skip if already above)
    """

    stores: Stores

    def __init__(self, stores: Stores) -> None:
        self.stores = stores

    async def build(self, session_id: SessionId, workspace: WorkspaceFilePath | None) -> ContextBundle:
        """Build the full context bundle for the given session."""
        # Deduplicate entities: moments → pinned → session → related
        seen_ids: set[EntityId] = set()

        # Fetch recent sessions
        recent_sessions = await self.stores.sessions.recent(limit=3)

        # Fetch moments — personality entities, always global
        # moments = await self.stores.memories.fetch(entity_type=EntityType.moment, limit=10)
        # moments = _rank_by_relevance_and_recency(moments)
        # [seen_ids.add(memory.id) for memory in moments]

        # Fetch pinned entities
        pinned_entities = await self.stores.memories.pinned()
        [seen_ids.add(memory.id) for memory in pinned_entities]

        # Fetch entities linked to recent sessions
        min_date = min((s.updated_at for s in recent_sessions), default=None)

        session_entities = await self.stores.memories.created_since(min_date, ignoring=list(seen_ids)) if min_date else []
        session_entities = _rank_by_relevance_and_recency(session_entities)
        [seen_ids.add(memory.id) for memory in session_entities]

        # Fetch related entities via vector search if we have a session description
        related_entities: list[Entity] = []
        from charlieverse.embeddings import prepare_session_text

        if recent_sessions:
            texts: list[str] = []
            for session in recent_sessions:
                content = prepare_session_text(session)
                if content:
                    texts.append(content)

            if texts:
                try:
                    embedding = await encode_one("\n".join(texts))
                    related_entities = await self.stores.memories.search_by_vector(embedding, limit=10, ignoring=list(seen_ids))

                except Exception:
                    logger.exception("Related-entity embedding failed")

        related_entities = _rank_by_relevance_and_recency(related_entities)

        # Fetch recent messages for context seeding (last 3 turns)
        recent_messages = await self.stores.messages.recent_messages(turns=6)

        # Fetch pinned knowledge
        pinned_knowledge = await self.stores.knowledge.pinned()

        banned = sorted(BANNED_WORDS)

        entities = [*session_entities, *related_entities]

        return ContextBundle(
            banned_words=banned,
            current_session_id=session_id,
            moments=[],
            pinned_entities=pinned_entities,
            pinned_knowledge=pinned_knowledge,
            recent_messages=recent_messages,
            recent_sessions=recent_sessions,
            related_entities=entities[:10],
            session_entities=[],
            workspace=workspace,
        )

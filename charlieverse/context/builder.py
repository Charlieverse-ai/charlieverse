"""Activation context builder — assembles the context bundle for session start."""

from __future__ import annotations

from dataclasses import dataclass, field

from charlieverse.embeddings import encode_one
from charlieverse.helpers.banned_words import BANNED_WORDS
from charlieverse.memory.entities import Entity, EntityId, EntityType
from charlieverse.memory.entities.mcp import _rank_by_relevance_and_recency
from charlieverse.memory.knowledge import Knowledge
from charlieverse.memory.messages import Message
from charlieverse.memory.sessions import Session, SessionId
from charlieverse.memory.stores import Stores
from charlieverse.memory.stories import Story, StoryTier
from charlieverse.types.dates import local_now
from charlieverse.types.id import ModelId
from charlieverse.types.strings import WorkspaceFilePath


@dataclass
class ContextBundle:
    """Everything needed to render the activation context."""

    current_session_id: SessionId
    workspace: WorkspaceFilePath | None = None
    recent_sessions: list[Session] = field(default_factory=list)
    weekly_stories: list[Story] = field(default_factory=list)
    pinned_entities: list[Entity] = field(default_factory=list)
    moments: list[Entity] = field(default_factory=list)
    session_entities: list[Entity] = field(default_factory=list)
    related_entities: list[Entity] = field(default_factory=list)
    pinned_knowledge: list[Knowledge] = field(default_factory=list)
    recent_messages: list[Message] = field(default_factory=list)
    all_time_story: Story | None = field(default=None)
    banned_words: list[str] = field(default_factory=list)

    @property
    def is_first_run(self) -> bool:
        """True when the database has no prior context — birthday time."""
        return not self.recent_sessions and not self.weekly_stories and not self.pinned_entities and not self.moments and not self.all_time_story

    @property
    def seen_ids(self) -> set[ModelId]:
        """All IDs delivered in this activation — used for downstream dedup."""
        ids: set[ModelId] = set()
        for group in (self.moments, self.pinned_entities, self.session_entities, self.related_entities):
            ids.update(e.id for e in group)
        for k in self.pinned_knowledge:
            ids.add(k.id)
        for s in self.weekly_stories:
            ids.add(s.id)
        if self.all_time_story:
            ids.add(self.all_time_story.id)
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
        recent_sessions = await self.stores.sessions.recent(limit=10)

        # Fetch moments — personality entities, always global
        moments = await self.stores.memories.fetch(entity_type=EntityType.moment, limit=1000)
        moments = _rank_by_relevance_and_recency(moments, set(), set())
        [seen_ids.add(memory.id) for memory in moments]

        # Fetch pinned entities
        pinned_entities = await self.stores.memories.pinned()
        [seen_ids.add(memory.id) for memory in pinned_entities]

        # Fetch entities linked to recent sessions
        min_date = min(recent_sessions, key=lambda x: x.updated_at).updated_at

        session_entities = await self.stores.memories.created_since(min_date, ignoring=list(seen_ids)) if min_date else []
        session_entities = _rank_by_relevance_and_recency(session_entities, set(), set())
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

                except Exception as e:
                    print("🦄 Embedding failed", e)

        related_entities = _rank_by_relevance_and_recency(related_entities, set(), set())
        # Fetch stories — weekly for compressed history, all-time for the arc
        weekly_stories: list[Story] = []
        all_time_story: Story | None = None

        today = local_now().strftime("%Y-%m-%d")

        weekly_stories = await self.stores.stories.fetch(
            tier=StoryTier.weekly,
            limit=4,
        )
        weekly_stories = [s for s in weekly_stories if s.period_start and s.period_start < today]
        all_time_story = await self.stores.stories.get_all_time()

        # Fetch recent messages for context seeding (last 3 turns)
        recent_messages = await self.stores.messages.recent_messages(turns=6)

        # Fetch pinned knowledge
        pinned_knowledge = await self.stores.knowledge.pinned()

        def _dedup(entities: list[Entity]) -> list[Entity]:
            result = []
            for e in entities:
                if e.id not in seen_ids and not e.is_deleted:
                    seen_ids.add(e.id)
                    result.append(e)
            return result

        banned = list(BANNED_WORDS)
        banned.sort()

        return ContextBundle(
            current_session_id=session_id,
            workspace=workspace,
            recent_sessions=recent_sessions,
            weekly_stories=weekly_stories,
            pinned_entities=pinned_entities,
            moments=moments,
            session_entities=session_entities,
            related_entities=related_entities,
            pinned_knowledge=pinned_knowledge,
            recent_messages=recent_messages,
            all_time_story=all_time_story,
            banned_words=banned,
        )

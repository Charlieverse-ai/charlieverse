"""Activation context builder — assembles the context bundle for session start."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from charlieverse.db.stores import MemoryStore
from charlieverse.memory.knowledge import Knowledge, KnowledgeStore
from charlieverse.memory.sessions import Session
from charlieverse.memory.sessions.store import SessionStore
from charlieverse.memory.stories import Story, StoryStore, StoryTier
from charlieverse.models import ContextMessage, Entity, EntityType
from charlieverse.types.dates import local_now


@dataclass
class ContextBundle:
    """Everything needed to render the activation context."""

    session: Session
    workspace: str | None = None
    recent_sessions: list[Session] = field(default_factory=list)
    weekly_stories: list[Story] = field(default_factory=list)
    pinned_entities: list[Entity] = field(default_factory=list)
    moments: list[Entity] = field(default_factory=list)
    session_entities: list[Entity] = field(default_factory=list)
    related_entities: list[Entity] = field(default_factory=list)
    pinned_knowledge: list[Knowledge] = field(default_factory=list)
    recent_messages: list[ContextMessage] = field(default_factory=list)
    all_time_story: Story | None = field(default=None)

    @property
    def is_first_run(self) -> bool:
        """True when the database has no prior context — birthday time."""
        return not self.recent_sessions and not self.weekly_stories and not self.pinned_entities and not self.moments and not self.all_time_story

    @property
    def seen_ids(self) -> set[str]:
        """All IDs delivered in this activation — used for downstream dedup."""
        ids: set[str] = set()
        for group in (self.moments, self.pinned_entities, self.session_entities, self.related_entities):
            ids.update(str(e.id) for e in group)
        for k in self.pinned_knowledge:
            ids.add(str(k.id))
        for s in self.weekly_stories:
            ids.add(str(s.id))
        if self.all_time_story:
            ids.add(str(self.all_time_story.id))
        return ids


class ActivationBuilder:
    """Assembles the activation context for a session.

    Priority order for entities (earlier = higher priority, deduped):
    1. Moments (personality — always loaded)
    2. Pinned entities (skip if already in moments)
    3. Session-linked entities (skip if already above)
    4. Related entities via embeddings (skip if already above)
    """

    def __init__(
        self,
        memories: MemoryStore,
        sessions: SessionStore,
        knowledge: KnowledgeStore,
        stories: StoryStore | None = None,
    ) -> None:
        self.memories = memories
        self.sessions = sessions
        self.knowledge = knowledge
        self.stories = stories

    async def build(self, session: Session, workspace: str | None) -> ContextBundle:
        """Build the full context bundle for the given session."""
        # Fetch sessions from the last 2 days (raw data, no story layer dependency)
        recent_sessions = await self.sessions.recent(limit=3)

        # Fetch moments — personality entities, always global
        moments = await self.memories.list(entity_type=EntityType.moment, limit=50)

        # Fetch pinned entities
        pinned_entities = await self.memories.pinned()

        # Fetch entities linked to recent sessions
        recent_ids = [s.id for s in recent_sessions]
        session_entities = await self.memories.for_sessions(recent_ids) if recent_ids else []

        # Fetch related entities via vector search if we have a session description
        related_entities: list[Entity] = []

        # Fetch stories — weekly for compressed history, all-time for the arc
        weekly_stories: list[Story] = []
        all_time_story: Story | None = None
        if self.stories:
            today = local_now().strftime("%Y-%m-%d")

            weekly_stories = await self.stories.list(
                tier=StoryTier.weekly,
                limit=4,
            )
            weekly_stories = [s for s in weekly_stories if s.period_start and s.period_start < today]
            all_time_story = await self.stories.get_all_time()

        # Fetch recent messages for context seeding (last 3 turns)
        recent_messages = await self.sessions.recent_messages(turns=6)

        # Fetch pinned knowledge
        pinned_knowledge = await self.knowledge.pinned()

        # Deduplicate entities: moments → pinned → session → related
        seen_ids: set[UUID] = set()

        def _dedup(entities: list[Entity]) -> list[Entity]:
            result = []
            for e in entities:
                if e.id not in seen_ids and not e.is_deleted:
                    seen_ids.add(e.id)
                    result.append(e)
            return result

        moments = _dedup(moments)
        pinned_entities = _dedup(pinned_entities)
        session_entities = _dedup(session_entities)
        related_entities = _dedup(related_entities)

        return ContextBundle(
            workspace=workspace,
            session=session,
            recent_sessions=recent_sessions,
            weekly_stories=weekly_stories,
            pinned_entities=pinned_entities,
            moments=moments,
            session_entities=session_entities,
            related_entities=related_entities,
            pinned_knowledge=pinned_knowledge,
            recent_messages=recent_messages,
            all_time_story=all_time_story,
        )

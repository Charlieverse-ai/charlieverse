"""Pydantic payload envelopes for /api/story-data/* routes.

These models match the exact shapes the Storyteller subagent consumes —
field names and nesting must stay stable, or the session-save skill breaks.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from charlieverse.memory.messages import MessageRole
from charlieverse.memory.stories import Story
from charlieverse.types.dates import UTCDatetime
from charlieverse.types.strings import WorkspaceFilePath


class SessionStub(BaseModel):
    """Minimal session header used in the session story-data payload."""

    id: str
    workspace: WorkspaceFilePath | None
    created_at: str | None


class SessionSummary(BaseModel):
    """Full session summary used in daily rollup payloads."""

    id: str
    what_happened: str
    workspace: WorkspaceFilePath | None
    created_at: str
    updated_at: str


class EntityStub(BaseModel):
    """Trimmed memory entry for rollup payloads."""

    type: str
    content: str


class KnowledgeStub(BaseModel):
    """Trimmed knowledge entry for rollup payloads."""

    topic: str
    content: str


class SessionStoryMessage(BaseModel):
    """Message entry inside a session story-data payload."""

    # `from` is a Python keyword, so the field is named from_ and serialized as "from".
    model_config = ConfigDict(populate_by_name=True)

    content: str | None
    from_: str = Field(serialization_alias="from")
    date_time: str
    seconds_between_messages: str | None


class DailyRollupMessage(BaseModel):
    """Message entry inside a daily rollup payload."""

    model_config = ConfigDict(populate_by_name=True)

    role: MessageRole
    content: str
    created_at: UTCDatetime


class SessionStoryData(BaseModel):
    """Payload for GET /api/story-data/{session_id}."""

    session: SessionStub
    existing_story: Story | None
    messages: list[SessionStoryMessage]
    memories: list[EntityStub]
    knowledge: list[KnowledgeStub]


class DailyRollupData(BaseModel):
    """Payload for GET /api/story-data/daily/{date}."""

    range_start: str
    range_end: str
    sessions: list[SessionSummary]
    messages: list[DailyRollupMessage]
    memories: list[EntityStub]
    knowledge: list[KnowledgeStub]


class TierRollupData(BaseModel):
    """Payload for GET /api/story-data/{tier}/{date} (weekly, monthly, quarterly, yearly)."""

    date: str
    range_start: str | None
    range_end: str | None
    stories: list[Story]

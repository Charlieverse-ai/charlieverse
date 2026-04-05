"""Session model — tracks conversation sessions across providers."""

from __future__ import annotations

from typing import Self

import aiosqlite
from pydantic import BaseModel, Field

from charlieverse.types.dates import UTCDatetime, from_iso, from_iso_or_none, utc_now
from charlieverse.types.id import ModelId
from charlieverse.types.lists import TagList
from charlieverse.types.strings import NonEmptyString, ShortDescription


class SessionId(ModelId):
    pass


class Session(BaseModel):
    """A conversation session with Charlie."""

    id: SessionId
    what_happened: ShortDescription
    for_next_session: ShortDescription
    tags: TagList | None
    workspace: NonEmptyString
    created_at: UTCDatetime
    updated_at: UTCDatetime
    deleted_at: UTCDatetime | None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> Self:
        from charlieverse.types.lists import decode_tag_list

        return cls.model_construct(
            id=SessionId(row["id"]),
            what_happened=row["what_happened"],
            for_next_session=row["for_next_session"],
            tags=decode_tag_list(row["tags"]),
            workspace=str(row["workspace"]),
            created_at=from_iso(row["created_at"]),
            updated_at=from_iso(row["updated_at"]),
            deleted_at=from_iso_or_none(row["deleted_at"]),
        )


class NewSession(BaseModel):
    id: SessionId = Field(default_factory=SessionId)
    workspace: NonEmptyString
    created_at: UTCDatetime = Field(default_factory=utc_now)

    @classmethod
    def from_update(cls, update: UpdateSession) -> Self:
        return cls(id=update.id, workspace=update.workspace, created_at=update.updated_at)


class SessionContent(BaseModel):
    what_happened: ShortDescription
    for_next_session: ShortDescription


class UpdateSession(BaseModel):
    id: SessionId
    workspace: NonEmptyString
    content: SessionContent | None = None
    tags: TagList | None = None
    updated_at: UTCDatetime = Field(default_factory=utc_now)

    def tag_value(self) -> str:
        from charlieverse.types.lists import encode_tag_list

        return encode_tag_list(self.tags)


class DeleteSession(BaseModel):
    id: SessionId
    deleted_at: UTCDatetime = Field(default_factory=utc_now)

from __future__ import annotations

from enum import StrEnum
from typing import Self

from aiosqlite import Row
from pydantic import BaseModel

from charlieverse.memory.sessions import SessionId
from charlieverse.types.dates import UTCDatetime, from_iso
from charlieverse.types.id import ModelId
from charlieverse.types.strings import NonEmptyString


class MessageId(ModelId):
    pass


class MessageRole(StrEnum):
    user = "user"
    charlie = "charlie"

    @classmethod
    def _missing_(cls, value):
        value = value.lower().strip()

        if value == "assistant":
            return cls.charlie

        for member in cls:
            if member.value == value:
                return member

        return super()._missing_(value)


class Message(BaseModel):
    id: MessageId
    session_id: SessionId
    content: NonEmptyString
    role: MessageRole
    created_at: UTCDatetime

    @classmethod
    def from_row(cls, row: Row) -> Self:
        return cls.model_construct(
            id=MessageId(row["id"]),
            session_id=SessionId(row["session_id"]),
            content=row["content"],
            role=MessageRole(row["role"]),
            created_at=from_iso(row["created_at"]),
        )


class LatestMessage(Message):
    message_count: MessageCounts


class MessageCounts(BaseModel):
    total: MessageCount
    since_last_save: MessageCount

    @classmethod
    def zero(cls) -> Self:
        return cls(total=MessageCount.zero(), since_last_save=MessageCount.zero())


class MessageCount(BaseModel):
    messages: int
    turns: int

    @classmethod
    def zero(cls) -> Self:
        return cls(messages=0, turns=0)

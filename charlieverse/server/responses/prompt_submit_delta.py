from __future__ import annotations

from typing import Self

from pydantic import BaseModel

from charlieverse.memory.messages.models import LatestMessage, MessageCounts
from charlieverse.memory.sessions import Session
from charlieverse.server.utils.seen_models import get_seen_ids
from charlieverse.types.dates import utc_now
from charlieverse.types.id import ModelId
from charlieverse.types.time import Seconds


class PromptSubmitContext(BaseModel):
    session_start: Seconds
    last_save: Seconds | None
    last_user_message: Seconds | None
    last_assistant_message: str | None = None
    last_assistant_message_age: Seconds | None = None
    seen_memory_ids: list[ModelId]
    message_count: MessageCounts

    @classmethod
    def from_session(
        cls,
        session: Session,
        user_message: LatestMessage | None,
        assistant_message: LatestMessage | None = None,
    ) -> Self:
        now = utc_now()
        session_start = Seconds((now - session.created_at).total_seconds())
        last_save = Seconds((now - session.updated_at).total_seconds()) if session.created_at != session.updated_at else None
        last_user_message = Seconds((now - user_message.created_at).total_seconds()) if user_message else None
        last_assistant_message = assistant_message.content if assistant_message else None
        last_assistant_message_age = Seconds((now - assistant_message.created_at).total_seconds()) if assistant_message else None
        message_count = user_message.message_count if user_message else MessageCounts.zero()

        return cls.model_construct(
            session_start=session_start,
            last_save=last_save,
            last_user_message=last_user_message,
            last_assistant_message=last_assistant_message,
            last_assistant_message_age=last_assistant_message_age,
            seen_memory_ids=list(get_seen_ids(session.id)),
            message_count=message_count,
        )

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Self
from uuid import UUID

from pydantic_core import CoreSchema, core_schema

# Default value signal to distinguish between None and no arguments
__default_uuid__ = "__default_uuid__"


def _parse_uuid(value: str | UUID | None) -> UUID | None:
    """Parse a UUID string, returning None on malformed input."""
    if not value:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None


class ModelId(str):
    def __new__(cls, value: str | None | UUID | ModelId = __default_uuid__) -> Self:
        if isinstance(value, ModelId):
            return super().__new__(cls, str(value))

        if value is __default_uuid__:
            from uuid import uuid4

            return super().__new__(cls, str(uuid4()))

        if isinstance(value, UUID):
            return super().__new__(cls, str(value))

        parsed_uuid = _parse_uuid(value)
        if not parsed_uuid:
            raise ValueError(f"{value} was not a valid UUID")

        return super().__new__(cls, str(parsed_uuid))

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], CoreSchema],
    ) -> core_schema.CoreSchema:
        def validate_uuid(value: str | UUID) -> Self:
            if isinstance(value, cls):
                return value
            try:
                return cls(value)
            except ValueError as e:
                raise e from e

        from_string_or_uuid = core_schema.chain_schema(
            [
                core_schema.uuid_schema(),
                core_schema.no_info_plain_validator_function(validate_uuid),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_string_or_uuid,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(cls),
                    from_string_or_uuid,
                ],
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(str, when_used="json"),
        )

        return core_schema.no_info_plain_validator_function(validate_uuid)

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Self
from uuid import UUID

from pydantic import model_serializer
from pydantic_core import CoreSchema, core_schema

from charlieverse.helpers.uuid import create_uuid, uuid_from_str


class ParseError(Exception):
    pass


# Default value signal to distinguish between None and no arguments
__default_uuid__ = "__default_uuid__"


class ModelId:
    _uuid: UUID

    def __init__(self, value: str | None | UUID | ModelId = __default_uuid__) -> None:
        if isinstance(value, ModelId):
            self._uuid = value._uuid
            return super().__init__()

        if value is __default_uuid__:
            self._uuid = create_uuid()
            return super().__init__()

        if isinstance(value, UUID):
            self._uuid = value
            return super().__init__()

        parsed_uuid = uuid_from_str(value)
        if not parsed_uuid:
            raise ParseError(f"{value} was not a valid UUID")

        self._uuid = parsed_uuid
        return super().__init__()

    @model_serializer(mode="plain")
    def serialize_model(self) -> str:
        return str(self._uuid)

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
            except ParseError as e:
                raise ValueError("Invalid UUID") from e

        from_string_or_uuid = core_schema.chain_schema(
            [
                core_schema.uuid_schema(),
                # core_schema.union_schema(
                #     [
                #         core_schema.str_schema(),
                #         core_schema.uuid_schema(),
                #     ]
                # ),
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

    def __str__(self):
        return str(self._uuid)

from __future__ import annotations

import os.path
from collections.abc import Callable
from typing import Any, Self

from pydantic_core import CoreSchema, core_schema

type _NonEmptyStringTypes = str | NonEmptyString | None


def _parse_non_empty_str(value: _NonEmptyStringTypes) -> str:
    if not value:
        raise ValueError("None is not a valid NonEmptyString")

    if isinstance(value, NonEmptyString):
        return value

    value = value.strip()

    if len(value) <= 0:
        raise ValueError("String was empty")

    return value


class NonEmptyString(str):
    def __new__(cls, value: _NonEmptyStringTypes) -> Self:
        return super().__new__(cls, _parse_non_empty_str(value))

    @classmethod
    def or_none(cls, value: _NonEmptyStringTypes) -> Self | None:
        try:
            return cls.__new__(cls, value)
        except ValueError:
            return None

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], CoreSchema],
    ) -> core_schema.CoreSchema:

        schema = core_schema.union_schema(
            [
                core_schema.is_instance_schema(cls),
                core_schema.str_schema(min_length=1, strip_whitespace=True),
                core_schema.no_info_plain_validator_function(_parse_non_empty_str),
            ],
        )
        return core_schema.json_or_python_schema(
            json_schema=schema,
            python_schema=schema,
            serialization=core_schema.plain_serializer_function_ser_schema(str, when_used="json"),
        )


class WorkspaceFilePath(NonEmptyString):
    @property
    def display_path(self) -> str:
        return self.replace(os.path.expanduser("~"), "~", 1)


class CleanedText(NonEmptyString):
    pass

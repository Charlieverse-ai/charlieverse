from __future__ import annotations

from collections.abc import Callable
from typing import Any, Self, SupportsFloat

from pydantic_core import CoreSchema, core_schema


class Seconds(float):
    """A float tagged as 'seconds' — for API surfaces where the unit matters.

    Tolerates `None` on construction (coerces to 0) so callers can build from
    `(now - maybe_dt).total_seconds()`-style expressions without guarding.
    """

    def __new__(cls, value: SupportsFloat | str | None) -> Self:
        return super().__new__(cls, float(value or 0))

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], CoreSchema],
    ) -> core_schema.CoreSchema:
        schema = core_schema.union_schema(
            [
                core_schema.is_instance_schema(cls),
                core_schema.float_schema(allow_inf_nan=False),
            ],
        )
        return core_schema.json_or_python_schema(
            json_schema=schema,
            python_schema=schema,
            serialization=core_schema.plain_serializer_function_ser_schema(float, when_used="json"),
        )

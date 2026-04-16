from typing import Annotated, NewType

from pydantic import Field

from charlieverse.types.strings import NonEmptyString

TagList = NewType("TagList", Annotated[list[NonEmptyString], Field(min_length=1)])


def decode_tag_list(value: str | None) -> TagList | None:
    if not value:
        return None

    from json import JSONDecoder

    return JSONDecoder().decode(value)


def encode_tag_list(tags: TagList | None) -> str:
    from json import JSONEncoder

    return JSONEncoder().encode(tags)

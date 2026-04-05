from typing import Annotated

from pydantic import StringConstraints

type NonEmptyString = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
type ShortString = Annotated[NonEmptyString, StringConstraints(max_length=50)]
type ShortDescription = Annotated[NonEmptyString, StringConstraints(min_length=50, max_length=200)]
type MediumDescription = Annotated[ShortDescription, StringConstraints(max_length=400)]

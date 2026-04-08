from typing import Annotated

from pydantic import StringConstraints

type NonEmptyString = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
type VeryShortString = NonEmptyString  # Annotated[NonEmptyString, StringConstraints(max_length=50)]
type ShortString = NonEmptyString  # Annotated[NonEmptyString, StringConstraints(max_length=100)]
type ShortDescription = NonEmptyString  # Annotated[NonEmptyString, StringConstraints(min_length=50, max_length=300)]
type MediumDescription = NonEmptyString  # Annotated[ShortDescription, StringConstraints(max_length=400)]
type LongDescription = NonEmptyString  # Annotated[ShortDescription, StringConstraints(max_length=1000)]

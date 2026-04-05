from uuid import UUID

# TODO Move this into id


def uuid_from_str(value: str | UUID | None) -> UUID | None:
    """Parse a UUID string, returning None on malformed input."""
    if not value:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None


""" Parses the incoming optional string value, and returns the parsed UUID as a string, or None if the UUID was invalid"""


def uuid_str_from_str(value: str | None) -> str | None:
    uuid = uuid_from_str(value)

    if uuid:
        return str(uuid)


def create_uuid() -> UUID:
    from uuid import uuid4

    return uuid4()

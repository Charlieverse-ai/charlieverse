from collections.abc import Callable, Iterable


def compact_map[T, R](items: Iterable[T], fn: Callable[[T], R | None]) -> list[R]:
    """Map fn over items, dropping elements where fn returns None.

    Mirrors Swift's Sequence.compactMap. Only None is dropped — other
    falsy values (0, '', False, []) are preserved.
    """
    return [result for item in items if (result := fn(item)) is not None]

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ExtractID:
    """Base identifier for media objects."""

    extractor: str
    id: str
    url: str


class GenericList(Sequence):
    def __init__(self, iterable: Iterable) -> None:
        self._list = list(iterable)

    def __iter__(self):
        for f in self._list:
            yield f

    def __bool__(self) -> bool:
        return True if self._list else False

    def __len__(self) -> int:
        return self._list.__len__()

    def __repr__(self) -> str:
        return self._list.__repr__()

    def __rich_repr__(self):
        yield self._list

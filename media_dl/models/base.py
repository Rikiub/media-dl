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

    def __contains__(self, value: object) -> bool:
        return value in self._list

    def __iter__(self):
        return iter(self._list)

    def __len__(self) -> int:
        return len(self._list)

    def __bool__(self) -> bool:
        return bool(self._list)

    def __repr__(self) -> str:
        return repr(self._list)

    def __rich_repr__(self):
        yield self._list

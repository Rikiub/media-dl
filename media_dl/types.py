from dataclasses import dataclass
from typing import Literal


__all__ = ["Media", "Playlist"]

EXT_VIDEO = Literal["mp4", "mkv"]
EXT_AUDIO = Literal["mp3", "mka", "m4a", "ogg"]
EXTENSION = EXT_VIDEO | EXT_AUDIO
"""Common containers formats with thumbnail support and lossy compression. Sorted by usage."""

QUALITY = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]
QUALITY_VIDEO = Literal[
    "144", "240", "360", "480", "720", "1080", "1440", "2160", "4320"
]


@dataclass(slots=True, frozen=True)
class _BasicMeta:
    url: str
    thumbnail: str | None
    extractor: str
    id: str
    title: str


@dataclass(slots=True, frozen=True)
class Media(_BasicMeta):
    creator: str
    duration: int

    def is_completed(self) -> bool:
        if self.title or self.creator or self.duration:
            return True
        else:
            return False


@dataclass(slots=True, frozen=True)
class Playlist(_BasicMeta):
    count: int
    entries: list[Media]

    def __len__(self):
        return self.count

    def __iter__(self):
        for item in self.entries:
            yield item


ResultType = Media | Playlist

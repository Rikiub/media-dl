from dataclasses import dataclass
from typing import Literal


__all__ = ["Media", "Playlist"]

FORMAT = Literal["video", "audio"]
EXT_VIDEO = Literal["mp4", "mkv"]
EXT_AUDIO = Literal["m4a", "mp3", "ogg"]
EXTENSION = EXT_VIDEO | EXT_AUDIO
"""Common containers formats with thumbnail, metadata and lossy compression support."""

AUDIO_QUALITY = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]
VIDEO_RES = Literal["144", "240", "360", "480", "720", "1080", "1440", "2160", "4320"]


@dataclass(slots=True, frozen=True)
class _BasicMeta:
    url: str
    thumbnail: str
    extractor: str
    id: str
    title: str


@dataclass(slots=True, frozen=True)
class Media(_BasicMeta):
    creator: str
    duration: int

    def is_complete(self) -> bool:
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

from dataclasses import dataclass
from typing import Literal


__all__ = ["Result", "Playlist"]

EXT_VIDEO = Literal["avi", "flv", "mkv", "mov", "mp4", "webm"]
EXT_AUDIO = Literal["aiff", "alac", "flac", "m4a", "mka", "mp3", "ogg", "opus", "wav"]

QUALITY = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]
VIDEO_QUALITY = Literal[
    "144", "240", "360", "480", "720", "1080", "1440", "2160", "4320"
]


@dataclass(slots=True, frozen=True)
class Url:
    original: str
    download: str
    thumbnail: str | None


@dataclass(slots=True, frozen=True)
class _BasicMeta:
    url: Url
    extractor: str
    id: str
    title: str


@dataclass(slots=True, frozen=True)
class Result(_BasicMeta):
    uploader: str
    duration: int


@dataclass(slots=True, frozen=True)
class Playlist(_BasicMeta):
    count: int
    entries: list[Result]

    def __len__(self):
        return self.count

    def __iter__(self):
        for item in self.entries:
            yield item

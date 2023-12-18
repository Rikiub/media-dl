from typing import TypedDict, Generator
from dataclasses import dataclass


class FormatDict(TypedDict):
    url: str
    ext: str


@dataclass(slots=True)
class Track:
    title: str
    album_name: str
    artists: list[str]
    album_artist: str
    track_number: int
    tracks_count: int
    disc_number: int
    disc_count: int
    year: int
    genres: list[str] | None = None
    isrc: str | None = None
    cover_url: str | None = None
    lyrics: str | None = None


@dataclass(slots=True)
class Result:
    source: str
    id: str
    title: str
    uploader: str
    duration: int
    url: str
    thumbnail_url: str | None = None
    _formats: list[FormatDict] | None = None

    @property
    def formats(self) -> dict | None:
        if self._formats:
            return {"title": self.title, "id": self.id, "formats": self._formats}
        else:
            return None


@dataclass(slots=True)
class Playlist:
    title: str
    entries: list[Result]

    def __iter__(self) -> Generator[Result, None, None]:
        for item in self.entries:
            yield item

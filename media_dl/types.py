from dataclasses import dataclass
from typing import TypeAlias

__all__ = ["Result", "Playlist"]

JSON: TypeAlias = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None


@dataclass(slots=True, frozen=True)
class URL:
    original: str
    download: str
    thumbnail: str | None


@dataclass(slots=True, frozen=True)
class BasicMeta:
    url: URL
    extractor: str
    id: str
    title: str


@dataclass(slots=True, frozen=True)
class Result(BasicMeta):
    uploader: str
    duration: int


@dataclass(slots=True, frozen=True)
class Playlist(BasicMeta):
    count: int
    entries: list[Result]

    def __len__(self):
        return self.count

    def __iter__(self):
        for item in self.entries:
            yield item


@dataclass(slots=True)
class Track:
    year: int
    title: str
    artists: list[str]
    album_title: str | None = None
    album_artist: str | None = None
    genres: list[str] | None = None
    track_number: int | None = None
    tracks_total: int | None = None
    disc_number: int | None = None
    disc_total: int | None = None
    isrc: str | None = None
    lyrics: str | None = None

    def __post_init__(self):
        # Interpret as single album.
        if not self.album_title:
            self.album_title = self.title

        # Interpret as first artist.
        if not self.album_artist:
            self.album_artist = self.artists[0]

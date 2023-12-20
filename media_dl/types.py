from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class URL:
    original: str
    download: str
    thumbnail: str | None


@dataclass(slots=True, frozen=True)
class BasicMeta:
    url: URL
    source: str
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

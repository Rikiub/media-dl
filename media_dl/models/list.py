from __future__ import annotations

from dataclasses import dataclass

from media_dl import ydl_base
from media_dl.models.base import MetaID, extract_meta, extract_thumbnail, extract_url
from media_dl.models.stream import Stream, StreamList, InfoDict


@dataclass(slots=True, frozen=True)
class _BaseList(MetaID):
    lenght: int
    streams: list[Stream]

    def __len__(self):
        return self.lenght


@dataclass(slots=True, frozen=True)
class Playlist(_BaseList):
    extractor: str
    id: str
    url: str
    thumbnail: str
    title: str

    @classmethod
    def from_url(cls, url: str) -> Playlist:
        info = extract_url(url)
        return cls.from_info(info)

    @classmethod
    def from_info(cls, info: InfoDict) -> Playlist:
        if not ydl_base.is_playlist(info):
            raise TypeError("Not is a playlist. Must have 'entries' key.")

        return cls(
            *extract_meta(info),
            thumbnail=extract_thumbnail(info),
            title=info.get("title") or "",
            lenght=info["playlist_count"],
            streams=list(Stream.from_info(entry) for entry in info["entries"]),
        )

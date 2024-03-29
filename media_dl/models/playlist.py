from __future__ import annotations

from dataclasses import dataclass

from media_dl import helper
from media_dl.models.base import ExtractID
from media_dl.models.stream import Stream, InfoDict


@dataclass(slots=True, frozen=True)
class _StreamList(ExtractID):
    lenght: int
    streams: list[Stream]

    def __len__(self):
        return self.lenght


@dataclass(slots=True, frozen=True)
class Playlist(_StreamList):
    """List of streams with basic metadata. Access them with the attribute `streams`."""

    thumbnail: str
    title: str

    @classmethod
    def _from_info(cls, info: InfoDict) -> Playlist:
        if not helper.is_playlist(info):
            raise TypeError("Unable to serialize dict. Not is a playlist.")

        return cls(
            *helper.extract_meta(info),
            thumbnail=helper.extract_thumbnail(info),
            title=info.get("title") or "",
            lenght=info["playlist_count"],
            streams=list(Stream._from_info(entry) for entry in info["entries"]),
        )

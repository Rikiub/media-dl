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
    """Stream list with basic metadata. Access them with attribute `streams`."""

    thumbnail: str
    title: str

    @classmethod
    def _from_info(cls, info: InfoDict) -> Playlist:
        if not helper.info_is_playlist(info):
            raise TypeError("Unable to serialize dict. Not is a playlist.")

        return cls(
            *helper.info_extract_meta(info),
            thumbnail=helper.info_extract_thumbnail(info),
            title=info.get("title") or "",
            lenght=info["playlist_count"],
            streams=list(Stream._from_info(entry) for entry in info["entries"]),
        )

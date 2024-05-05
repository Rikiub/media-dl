from __future__ import annotations

from dataclasses import dataclass

from media_dl._ydl import InfoDict
from media_dl.extractor import serializer
from media_dl.models.base import ExtractID
from media_dl.models.stream import LazyStreams


@dataclass(slots=True, frozen=True)
class Playlist(ExtractID):
    """Stream list with basic metadata."""

    streams: LazyStreams
    title: str = ""
    thumbnail: str = ""

    @classmethod
    def _from_info(cls, info: InfoDict) -> Playlist:
        if not serializer.is_playlist(info):
            raise TypeError("Unable to serialize dict. Not is a playlist.")

        return cls(
            *serializer.extract_meta(info),
            streams=LazyStreams._from_info(info),
            title=info.get("title") or "",
            thumbnail=serializer.extract_thumbnail(info),
        )

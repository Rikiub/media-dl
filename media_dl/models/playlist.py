from __future__ import annotations

from pydantic import AliasPath, Field

from media_dl.models.base import ExtractID
from media_dl.models.stream import LazyStreams


class Playlist(ExtractID):
    """Playlist with multiple Streams."""

    title: str = Field(alias="playlist_title")
    thumbnail: str = Field(validation_alias=AliasPath("thumbsnails", -1))
    streams: LazyStreams = Field(alias="entries")

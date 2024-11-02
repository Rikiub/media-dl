from __future__ import annotations

from typing import Annotated

from pydantic import Field

from media_dl.models.base import ExtractID
from media_dl.models.metadata import ThumbnailList
from media_dl.models.stream import LazyStreams


class Playlist(ExtractID):
    """Playlist with multiple Streams."""

    title: str
    thumbnails: ThumbnailList = []
    streams: Annotated[LazyStreams, Field(alias="entries")]

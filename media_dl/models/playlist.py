from __future__ import annotations

from typing import Annotated

from pydantic import AliasChoices, AliasPath, Field

from media_dl.models.base import ExtractID
from media_dl.models.stream import LazyStreams


class Playlist(ExtractID):
    """Playlist with multiple Streams."""

    title: Annotated[
        str, Field(validation_alias=AliasChoices("playlist_title", "title"))
    ]
    thumbnail: Annotated[
        str,
        Field(validation_alias=AliasChoices("thumbnail", AliasPath("thumbsnails", -1))),
    ] = ""
    streams: Annotated[LazyStreams, Field(alias="entries")]

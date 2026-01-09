from __future__ import annotations

import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    AliasChoices,
    BeforeValidator,
    Field,
    PlainSerializer,
)

from media_dl.models.base import Extract
from media_dl.models.formats.list import FormatList
from media_dl.models.metadata import Chapter, MusicMetadata, Subtitles, Thumbnail
from media_dl.types import MUSIC_SITES

DatetimeTimestamp = Annotated[
    datetime.datetime, PlainSerializer(lambda d: d.timestamp())
]


class LazyStream(MusicMetadata, Extract):
    title: str = ""
    uploader: Annotated[
        str,
        BeforeValidator(lambda d: "" if not d else d.split(",")[0]),
        Field(validation_alias=AliasChoices("creator", "uploader")),
    ] = ""
    uploader_id: str | None = None
    description: str | None = None
    datetime: Annotated[DatetimeTimestamp | None, Field(alias="timestamp")] = None
    duration: float = 0
    thumbnails: list[Thumbnail] = []

    @property
    def is_music(self) -> bool:
        if any(s in self.url for s in MUSIC_SITES):
            return True
        else:
            return False

    def fetch(self, use_cache: bool = True) -> Stream:
        """Fetch real stream.

        Returns:
            Updated version of self Stream.

        Raises:
            ExtractError: Something bad happens when extract.
        """

        return Stream.from_url(self.url, use_cache)


class Stream(LazyStream):
    """Online media stream representation."""

    chapters: list[Chapter] | None = None
    subtitles: Subtitles | None = None
    formats: Annotated[
        FormatList,
        AfterValidator(lambda list: list.sort_by("best")),
        Field(min_length=1),
    ]

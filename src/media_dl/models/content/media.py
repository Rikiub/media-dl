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

from media_dl.models.content.base import LazyExtract
from media_dl.models.content.metadata import (
    Chapter,
    MusicMetadata,
    Subtitles,
    Thumbnail,
)
from media_dl.models.format.list import FormatList
from media_dl.types import MUSIC_SITES

DatetimeTimestamp = Annotated[
    datetime.datetime, PlainSerializer(lambda d: d.timestamp())
]


class LazyMedia(MusicMetadata, LazyExtract["Media"]):
    title: str = ""
    uploader: Annotated[
        str,
        BeforeValidator(lambda d: d.split(",")[0] if d else ""),
        BeforeValidator(lambda d: d.removesuffix(" - Topic") if d else ""),
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

    @property
    def _target_class(self):
        return Media


class Media(LazyMedia):
    """Online media representation."""

    chapters: list[Chapter] | None = None
    subtitles: Subtitles | None = None
    formats: Annotated[
        FormatList,
        AfterValidator(lambda list: list.sort_by("best")),
        Field(min_length=1),
    ]

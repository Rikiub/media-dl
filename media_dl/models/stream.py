from __future__ import annotations

import datetime
from typing import Annotated

from pydantic import AliasChoices, Field, PlainSerializer
from typing_extensions import Self

from media_dl.models.base import ExtractID
from media_dl.models.format import FormatList
from media_dl.models.metadata import MusicMetadata, Subtitles, Thumbnail


class LazyStream(MusicMetadata, ExtractID):
    title: str = ""
    uploader: Annotated[
        str, Field(validation_alias=AliasChoices("creator", "uploader"))
    ] = ""
    uploader_id: str | None = None
    description: str | None = None
    datetime: Annotated[DatetimeTimestamp | None, Field(alias="timestamp")] = None
    duration: float = 0
    thumbnails: list[Thumbnail] = []

    def fetch(self) -> Stream:
        """Fetch real stream.

        Returns:
            Updated version of self Stream.

        Raises:
            ExtractError: Something bad happens when extract.
        """

        return Stream.from_url(self.url)


DatetimeTimestamp = Annotated[
    datetime.datetime, PlainSerializer(lambda d: d.timestamp())
]


class Stream(LazyStream):
    """Online media stream representation."""

    subtitles: Subtitles | None = None
    formats: Annotated[FormatList, Field(min_length=1)]

    @classmethod
    def from_json(cls, json: str) -> Self:
        return cls.model_validate_json(json)

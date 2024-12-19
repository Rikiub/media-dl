from __future__ import annotations

import datetime
from typing import Annotated

from pydantic import AliasChoices, Field, PlainSerializer

from media_dl.extractor import info as info_extractor
from media_dl.models.base import ExtractID
from media_dl.models.format import FormatList
from media_dl.models.metadata import MusicMetadata, Subtitles, Thumbnail


class LazyStream(ExtractID):
    title: str = ""
    uploader: Annotated[
        str, Field(validation_alias=AliasChoices("creator", "uploader"))
    ] = ""

    def fetch(self) -> Stream:
        """Fetch real stream.

        Returns:
            Updated version of self Stream.

        Raises:
            ExtractError: Something bad happens when extract.
        """

        info = info_extractor.extract_url(self.url)
        return Stream(**info)


DatetimeTimestamp = Annotated[
    datetime.datetime, PlainSerializer(lambda d: d.timestamp())
]


class Stream(LazyStream, MusicMetadata):
    """Online media stream representation."""

    uploader_id: str | None = None
    description: str | None = None
    datetime: Annotated[DatetimeTimestamp | None, Field(alias="timestamp")] = None
    duration: float = 0
    formats: Annotated[FormatList, Field(min_length=1)]
    thumbnails: list[Thumbnail] = []
    subtitles: Subtitles | None = None
    has_cache: Annotated[bool, Field(exclude=True)] = False

    def __eq__(self, o: object) -> bool:
        if isinstance(o, self.__class__):
            return o.id == self.id
        else:
            return False

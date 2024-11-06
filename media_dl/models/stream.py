from __future__ import annotations

import datetime
from typing import Annotated

from pydantic import AliasChoices, Field, PlainSerializer

from media_dl.extractor import info as info_extractor
from media_dl.models.base import ExtractID
from media_dl.models.format import FormatList
from media_dl.models.metadata import MusicMetadata, Subtitle, ThumbnailList
from media_dl.types import MUSIC_SITES


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
        stream = Stream(**info)
        return stream

    def _is_music_site(self) -> bool:
        if any(s in self.url for s in MUSIC_SITES):
            return True
        else:
            return False

    @property
    def display_name(self) -> str:
        """Get pretty representation of the stream name."""

        if self._is_music_site() and self.uploader and self.title:
            return self.uploader + " - " + self.title
        elif self.title:
            return self.title
        else:
            return ""


DatetimeTimestamp = Annotated[
    datetime.datetime, PlainSerializer(lambda d: d.timestamp())
]


class Stream(MusicMetadata, LazyStream):
    """Online media stream representation."""

    uploader_id: str | None = None
    description: str | None = None
    datetime: Annotated[DatetimeTimestamp | None, Field(alias="timestamp")] = None
    duration: float = 0
    formats: Annotated[FormatList, Field(min_length=1)]
    thumbnails: ThumbnailList = []
    subtitles: dict[str, list[Subtitle]] | None = None

    def __eq__(self, o: object) -> bool:
        if isinstance(o, self.__class__):
            return o.id == self.id
        else:
            return False

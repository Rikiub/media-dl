from __future__ import annotations

import datetime
from typing import Annotated, cast

from pydantic import AliasChoices, Field, PlainSerializer, PrivateAttr

from media_dl._ydl import InfoDict
from media_dl.extractor import info as info_extractor
from media_dl.models.base import ExtractID, GenericList
from media_dl.models.format import FormatList
from media_dl.models.metadata import ThumbnailList
from media_dl.types import MUSIC_SITES


class DeferredStream(ExtractID):
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


class Stream(DeferredStream):
    """Online media stream representation."""

    uploader_id: str | None = None
    description: str = ""
    date: Annotated[DatetimeTimestamp | None, Field(alias="timestamp")] = None
    duration: float = 0
    formats: Annotated[FormatList, Field(min_length=1)]
    thumbnails: ThumbnailList = []
    subtitles: dict[str, list[dict]] | None = None
    _extra_info: Annotated[InfoDict, PrivateAttr()]

    def __init__(self, **data):
        super().__init__(**data)

        d = cast(InfoDict, data)
        self._extra_info = d

    def __eq__(self, o: object) -> bool:
        if isinstance(o, self.__class__):
            return o.id == self.id
        else:
            return False


class LazyStreams(GenericList[DeferredStream | Stream]):
    """Unproccesed list of streams.

    Each time you access a stream by index, it will check if is completed.
    If not is complete, will fetch a complete version and save for future use.

    Raises:
        ExtractError: Failed to fetch complete stream.
    """

    def _resolve_stream(self, index: int) -> Stream:
        stream = self.root[index]

        if type(stream) is DeferredStream:
            self.root[index] = stream = stream.fetch()

        if type(stream) is not Stream:
            raise ValueError(f"Could not fetch Stream, got: {type(stream).__name__}")

        return stream

    def __iter__(self):
        for index, _ in enumerate(self.root):
            yield self._resolve_stream(index)

    def __getitem__(self, index) -> Stream:  # type: ignore
        stream = super().__getitem__(index)
        stream = self._resolve_stream(index)
        return stream

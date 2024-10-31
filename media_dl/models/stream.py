from __future__ import annotations

import datetime
from typing import Annotated, cast

from pydantic import AliasChoices, Field, OnErrorOmit, PlainSerializer, PrivateAttr

from media_dl._ydl import InfoDict
from media_dl.extractor import info
from media_dl.models.base import ExtractID, GenericList
from media_dl.models.format import FormatList
from media_dl.models.metadata import Thumbnail
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

        info = info.extract_url(self.url)
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

    date: Annotated[
        DatetimeTimestamp | None,
        Field(alias="timestamp", validation_alias=AliasChoices("timestamp")),
    ] = None
    duration: float = 0
    formats: FormatList
    thumbnails: list[OnErrorOmit[Thumbnail]]
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

    def _is_music_site(self) -> bool:
        if super()._is_music_site():
            return True

        elif self._extra_info.get("track") and self._extra_info.get("artist"):
            return True

        else:
            return False


class LazyStreams(GenericList[DeferredStream]):
    """Unproccesed list of streams.

    Each time you access a stream by index, it will check if is completed.
    If not is complete, will fetch a complete version and save for future use.

    Raises:
        ExtractError: Failed to fetch complete stream.
    """

    def _resolve_stream(self, index: int) -> Stream:
        stream = self.root[index]

        if isinstance(stream.__class__, DeferredStream):
            self.root[index] = stream = stream.fetch()

        if not isinstance(stream, Stream):
            raise ValueError("Unable to fetch Stream.")

        return stream

    def __iter__(self):
        for index, _ in enumerate(self.root):
            yield self._resolve_stream(index)

    def __getitem__(self, index) -> Stream:  # type: ignore
        stream = super().__getitem__(index)
        stream = self._resolve_stream(index)
        return stream

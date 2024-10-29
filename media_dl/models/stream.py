from __future__ import annotations

import datetime
from typing import Annotated, cast

from pydantic import AliasChoices, AliasPath, Field, PrivateAttr

from media_dl._ydl import MUSIC_SITES, InfoDict
from media_dl.extractor import raw
from media_dl.models.base import ExtractID, GenericList
from media_dl.models.format import FormatList


class DeferredStream(ExtractID):
    title: str = ""

    def get_updated(self) -> Stream:
        """Fetch the stream again.

        Returns:
            Updated version of the Stream.

        Raises:
            ExtractError: Something bad happens when extract.
        """

        info = raw.extract_url(self.url)
        stream = Stream(**info)
        return stream


class Stream(DeferredStream):
    """Online media stream representation."""

    uploader: str = ""
    thumbnail: Annotated[
        str, Field(validation_alias=AliasPath("thumbnails", -1, "url"))
    ]
    date: Annotated[
        datetime.date | None,
        Field(validation_alias=AliasChoices("release_date")),
    ] = None
    duration: int = 0
    formats: FormatList
    _extra_info: Annotated[InfoDict, PrivateAttr()]

    def __init__(self, **data):
        super().__init__(**data)

        d = cast(InfoDict, data)
        self._extra_info = d

    @property
    def display_name(self) -> str:
        """Get pretty representation of the stream name."""

        if self._is_music_site() and self.uploader and self.title:
            return self.uploader + " - " + self.title
        elif self.title:
            return self.title
        else:
            return ""

    def has_missing_info(self) -> bool:
        """
        Check if has more information to extract.
        To get the complete information, use `get_updated` method.
        """

        if not (self.formats and self.duration and self.date and self.title):
            return True
        else:
            return False

    def _is_music_site(self) -> bool:
        if any(s in self.url for s in MUSIC_SITES):
            return True

        elif self._extra_info.get("track") and self._extra_info.get("artist"):
            return True

        else:
            return False

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

        if isinstance(stream, DeferredStream):
            self.root[index] = stream = stream.get_updated()

        return stream

    def __iter__(self):
        for index, _ in enumerate(self.root):
            yield self._resolve_stream(index)

    def __getitem__(self, index):  # type: ignore
        result = super().__getitem__(index)

        if isinstance(result, DeferredStream):
            result = self._resolve_stream(index)

        return result

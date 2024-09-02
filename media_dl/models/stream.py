from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import overload

from media_dl._ydl import MUSIC_SITES, InfoDict
from media_dl.extractor import raw, serializer
from media_dl.models.base import ExtractID, GenericList
from media_dl.models.format import FormatList


@dataclass(slots=True, frozen=True, order=True)
class Stream(ExtractID):
    """Online media stream representation."""

    title: str = ""
    uploader: str = ""
    thumbnail: str = ""
    date: datetime.date | None = None
    duration: int = 0
    formats: FormatList = FormatList([])
    _extra_info: InfoDict = field(default_factory=lambda: InfoDict({}), repr=False)

    @property
    def display_name(self) -> str:
        """Get pretty representation of the stream name."""

        if self._is_music_site() and self.uploader and self.title:
            return self.uploader + " - " + self.title
        elif self.title:
            return self.title
        else:
            return ""

    def get_updated(self) -> Stream:
        """Fetch the stream again.

        Returns:
            Updated version of the Stream.

        Raises:
            ExtractError: Something bad happens when extract.
        """

        info = raw.extract_url(self.url)
        stream = Stream._from_info(info)
        return stream

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

    @classmethod
    def _from_info(cls, info: InfoDict) -> Stream:
        if not serializer.is_stream(info):
            raise ValueError("Unable to serialize dict. It's not a stream.")

        return cls(
            *serializer.extract_meta(info),
            title=info.get("title") or "",
            uploader=info.get("uploader") or "",
            thumbnail=serializer.extract_thumbnail(info),
            date=serializer.extract_date(info),
            duration=info.get("duration") or 0,
            formats=FormatList._from_info(info),
            _extra_info=serializer.sanitize(info),
        )

    def __eq__(self, o: object) -> bool:
        if isinstance(o, Stream):
            return o.id == self.id
        else:
            return False


class LazyStreams(GenericList):
    """Unproccesed list of streams.

    Each time you access a stream by index, it will check if is completed.
    If not is complete, will fetch a complete version and save for future use.

    Raises:
        ExtractError: Failed to fetch complete stream.
    """

    def _resolve_stream(self, index: int) -> Stream:
        stream = self._list[index]

        if stream.has_missing_info():
            self._list[index] = stream = stream.get_updated()

        return stream

    @classmethod
    def _from_info(cls, info: InfoDict) -> LazyStreams:
        streams = []

        for entry in info["entries"]:
            try:
                streams.append(Stream._from_info(entry))
            except ValueError:
                continue

        return cls(streams)

    def __iter__(self):
        for index, _ in enumerate(self._list):
            yield self._resolve_stream(index)

    @overload
    def __getitem__(self, index: int) -> Stream: ...

    @overload
    def __getitem__(self, index: slice) -> LazyStreams: ...

    def __getitem__(self, index):
        match index:
            case slice():
                return LazyStreams(self._list[index])
            case int():
                return self._resolve_stream(index)
            case _:
                raise ValueError(index)

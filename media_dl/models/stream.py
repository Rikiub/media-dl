from __future__ import annotations

from dataclasses import dataclass, field
from typing import overload

from media_dl._ydl import MUSIC_SITES, InfoDict
from media_dl.extractor import serializer, raw

from media_dl.models.base import ExtractID, GenericList
from media_dl.models.format import FormatList


@dataclass(slots=True, frozen=True, order=True)
class Stream(ExtractID):
    """Online media stream representation."""

    title: str = ""
    uploader: str = ""
    thumbnail: str = ""
    duration: int = 0
    formats: FormatList = FormatList([])
    _extra_info: InfoDict = field(default_factory=lambda: InfoDict({}), repr=False)

    @property
    def display_name(self) -> str:
        """Get pretty representation of the `Stream` name."""

        if self._is_music_site() and self.uploader and self.title:
            return self.uploader + " - " + self.title
        elif self.title:
            return self.title
        else:
            return "?"

    def _is_complete(self) -> bool:
        if self.formats:
            return True
        else:
            return False

    def _is_music_site(self) -> bool:
        for site in MUSIC_SITES:
            if site in self.url:
                return True

        d = self._extra_info
        if d.get("track") and d.get("artist"):
            return True

        return False

    @classmethod
    def _from_info(cls, info: InfoDict) -> Stream:
        if serializer.is_playlist(info):
            raise TypeError("Unable to serialize dict. It's a playlist, not a stream.")

        return cls(
            *serializer.extract_meta(info),
            _extra_info=serializer.sanitize(info),
            title=info.get("title") or "",
            uploader=info["uploader"].split(",")[0] if info.get("uploader") else "",
            thumbnail=serializer.extract_thumbnail(info),
            duration=info.get("duration") or 0,
            formats=FormatList._from_info(info),
        )


def update_stream(stream: Stream) -> Stream:
    info = raw.extract_url(stream.url)
    stream = Stream._from_info(info)
    return stream


class LazyStreams(GenericList):
    """Unproccesed list of streams.

    Each time you access a stream by index, it will check if is completed.
    If not is complete, will fetch a complete version and save for future use.

    Raises:
        ExtractError: Failed to fetch complete stream.
    """

    @classmethod
    def _from_info(cls, info: InfoDict) -> LazyStreams:
        return cls([Stream._from_info(entry) for entry in info["entries"]])

    def _resolve_stream(self, index: int) -> Stream:
        stream = self._list[index]

        if not stream._is_complete():
            self._list[index] = stream = update_stream(stream)

        return stream

    def __iter__(self):
        for index, _ in enumerate(self._list):
            yield self._resolve_stream(index)

    @overload
    def __getitem__(self, index: int) -> Stream: ...

    @overload
    def __getitem__(self, index: slice) -> LazyStreams: ...

    def __getitem__(self, index):
        if isinstance(index, slice):
            return LazyStreams(
                [
                    self._resolve_stream(index)
                    for index, _ in enumerate(self._list[index])
                ]
            )
        elif isinstance(index, int):
            return self._resolve_stream(index)
        else:
            raise TypeError(index)

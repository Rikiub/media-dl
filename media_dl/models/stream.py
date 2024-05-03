from __future__ import annotations

from dataclasses import dataclass, field

from media_dl.extractor import info_helper
from media_dl.models.base import ExtractID, InfoDict
from media_dl.models.format import FormatList
from media_dl._ydl import MUSIC_SITES


@dataclass(slots=True, frozen=True, order=True)
class Stream(ExtractID):
    """Single `Stream` information.

    If `Stream` was obtained from a `Playlist`, will be incomplete and couldn't have `formats` to filter.
    To access to complete `Stream` information, you need do::

        >>> stream = stream.update()
    """

    title: str = ""
    uploader: str = ""
    thumbnail: str = ""
    duration: int = 0
    formats: FormatList = FormatList()
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

    def update(self) -> Stream:
        """Get updated version of the `Stream` doing another request."""
        return self.from_url(self.url)

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
        if info_helper.is_playlist(info):
            raise TypeError(
                "Unable to serialize dict. It's a playlist, not single stream."
            )

        return cls(
            *info_helper.extract_meta(info),
            _extra_info=info_helper.sanitize(info),
            title=info.get("title") or "",
            uploader=info["uploader"].split(",")[0] if info.get("uploader") else "",
            thumbnail=info_helper.extract_thumbnail(info),
            duration=info.get("duration") or 0,
            formats=FormatList._from_info(info),
        )


"""
from collections.abc import Sequence
from typing import overload
from media_dl.extractor import extract_url

class StreamList(Sequence[Stream]):
    def __init__(self, streams: list[Stream]):
        self._list = streams

    @overload
    def __getitem__(self, index: int) -> Stream: ...

    @overload
    def __getitem__(self, index: slice) -> StreamList: ...

    def __getitem__(self, index):
        if isinstance(index, slice):
            return StreamList(self._list[index])
        elif isinstance(index, int):
            stream = self._list[index]

            if not stream.formats:
                stream = extract_url(stream.url)

                if isinstance(stream, Stream):
                    self._list[index] = stream

            return stream
        else:
            raise TypeError(index)

    def __rich_repr__(self):
        yield self._list

    def __repr__(self) -> str:
        return self._list.__repr__()

    def __bool__(self):
        return True if self._list else False

    def __iter__(self):
        for f in self._list:
            yield f

    def __len__(self) -> int:
        return len(self._list)
"""

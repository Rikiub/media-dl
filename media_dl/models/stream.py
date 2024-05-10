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
    date: str = ""
    duration: int = 0
    formats: FormatList = FormatList([])
    _extra_info: InfoDict = field(default_factory=lambda: InfoDict({}), repr=False)

    def get_updated(self) -> Stream:
        info = raw.extract_url(self.url)
        stream = Stream._from_info(info)
        return stream

    @property
    def display_name(self) -> str:
        """Get pretty representation of the `Stream` name."""

        if self._is_music_site() and self.uploader and self.title:
            return self.uploader + " - " + self.title
        elif self.title:
            return self.title
        else:
            return "?"

    def has_missing_info(self) -> bool:
        if not (self.title and self.duration and self.formats):
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
            raise TypeError("Unable to serialize dict. It's not a stream.")

        return cls(
            *serializer.extract_meta(info),
            title=info.get("title") or "",
            uploader=info.get("uploader") or "",
            thumbnail=serializer.extract_thumbnail(info),
            date=info.get("release_date") or info.get("upload_date") or "",
            duration=info.get("duration") or 0,
            formats=FormatList._from_info(info),
            _extra_info=serializer.sanitize(info),
        )


class LazyStreams(GenericList):
    """Unproccesed list of streams.

    Each time you access a stream by index, it will check if is completed.
    If not is complete, will fetch a complete version and save for future use.

    Raises:
        ExtractError: Failed to fetch complete stream.
    """

    @classmethod
    def _from_info(cls, info: InfoDict) -> LazyStreams:
        streams = []

        for entry in info["entries"]:
            try:
                streams.append(Stream._from_info(entry))
            except TypeError:
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
                raise TypeError(index)

    def _resolve_stream(self, index: int) -> Stream:
        stream = self._list[index]

        if stream.has_missing_info():
            self._list[index] = stream = stream.get_updated()

        return stream

from __future__ import annotations

from dataclasses import dataclass
from typing import overload

from media_dl import ydl_base

from media_dl.models.base import (
    GLOBAL_INFO,
    MetaID,
    InfoDict,
    extract_meta,
    extract_thumbnail,
    extract_url,
)
from media_dl.models.format import Format, FormatList


@dataclass(slots=True, frozen=True)
class Stream(MetaID):
    thumbnail: str
    title: str
    uploader: str
    duration: int
    formats: FormatList

    def get_updated(self) -> Stream:
        return self.from_url(self.url)

    @property
    def display_name(self) -> str:
        if self.uploader and self.title:
            return self.uploader + " - " + self.title
        elif self.title:
            return self.title
        else:
            return "..."

    @classmethod
    def from_url(cls, url: str) -> Stream:
        info = extract_url(url)
        return cls.from_info(info)

    @classmethod
    def from_format(cls, format: Format) -> Stream:
        info = format.get_info()
        return cls.from_info(info)

    @classmethod
    def from_info(cls, info: InfoDict) -> Stream:
        extractor, id, url = extract_meta(info)

        if ydl_base.is_playlist(info):
            raise TypeError("It is a playlist, not a stream.")
        elif ydl_base.is_single(info):
            GLOBAL_INFO.save(info, extractor, id)

        return cls(
            extractor=extractor,
            id=id,
            url=url,
            thumbnail=extract_thumbnail(info),
            title=info.get("track") or info.get("title") or "",
            uploader=(
                info.get("artist")
                or info.get("channel")
                or info.get("creator")
                or info.get("uploader")
                or ""
            ),
            duration=info.get("duration") or 0,
            formats=FormatList.from_info(info),
        )


class StreamList(list[Stream]):
    @overload
    def __getitem__(self, index: int) -> Stream: ...

    @overload
    def __getitem__(self, index: slice) -> StreamList: ...

    def __getitem__(self, index):  # type: ignore
        result = super().__getitem__(index)

        match result:
            case Stream():
                return self._resolve_stream(result)
            case list():
                return StreamList(self._resolve_stream(f) for f in result)
            case _:
                raise TypeError(result)

    def get_direct(self, index):
        return super().__getitem__(index)

    def _resolve_stream(self, stream: Stream) -> Stream:
        if stream.formats.guess_type() == "incomplete":
            if info := GLOBAL_INFO.load(stream.extractor, stream.id):
                stream = Stream.from_info(info)
            else:
                stream = stream.get_updated()
        return stream

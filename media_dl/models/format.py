from __future__ import annotations

from abc import ABC, abstractmethod
import bisect
from dataclasses import dataclass, field, asdict
from functools import cached_property
from typing import Any, SupportsIndex, overload

from media_dl._ydl import FORMAT_TYPE, InfoDict, SupportedExtensions
from media_dl.models.base import GenericList


@dataclass(slots=True, frozen=True, kw_only=True)
class FormatBase:
    _downloader_options: dict = field(default_factory=dict, repr=False)
    url: str
    id: str
    filesize: int
    extension: str

    def __post_init__(self):
        if not (
            self.extension in SupportedExtensions.video
            or self.extension in SupportedExtensions.audio
        ):
            raise ValueError(self.extension, "not is a valid extension.")

    @classmethod
    def _from_info(cls, entry: dict[str, Any]) -> FormatBase:
        return cls(
            _downloader_options=entry.get("downloader_options") or {},
            url=entry["url"],
            id=entry["format_id"],
            filesize=entry.get("filesize") or 0,
            extension=entry["ext"],
        )


class Format(ABC, FormatBase):
    @property
    @abstractmethod
    def codec(self) -> str: ...

    @property
    @abstractmethod
    def quality(self) -> int: ...

    @property
    @abstractmethod
    def display_quality(self) -> str: ...

    @classmethod
    @abstractmethod
    def _from_info(cls, entry: dict[str, Any]):
        return super()._from_info(entry)

    @abstractmethod
    def _format_dict(self) -> InfoDict:
        d = {
            "format_id": self.id,
            "url": self.url,
            "ext": self.extension,
            "downloader_options": self._downloader_options,
        }

        if self.filesize != 0:
            d |= {"filesize": self.filesize}

        return InfoDict(d)


@dataclass(slots=True, frozen=True)
class VideoFormat(Format):
    video_codec: str
    audio_codec: str
    width: int
    height: int
    fps: int

    @property
    def codec(self) -> str:
        return self.video_codec

    @property
    def quality(self) -> int:
        return self.height

    @property
    def display_quality(self) -> str:
        return str(self.height) + "p"

    @classmethod
    def _from_info(cls, entry: dict[str, Any]) -> VideoFormat:
        meta = FormatBase._from_info(entry)

        return cls(
            **asdict(meta),
            video_codec=entry.get("vcodec") or "",
            audio_codec=entry.get("acodec") or "",
            width=entry.get("width") or 0,
            height=entry.get("height") or 0,
            fps=entry.get("fps") or 0,
        )

    def _format_dict(self) -> InfoDict:
        d = super()._format_dict()
        d |= {
            "height": self.height,
            "vcodec": self.audio_codec,
            "acodec": self.audio_codec,
            "fps": self.fps,
        }
        return d


@dataclass(slots=True, frozen=True)
class AudioFormat(Format):
    audio_codec: str
    bitrate: int

    @property
    def codec(self) -> str:
        return self.audio_codec

    @property
    def quality(self) -> int:
        return self.bitrate

    @property
    def display_quality(self) -> str:
        return str(round(self.bitrate)) + "kbps"

    @classmethod
    def _from_info(cls, entry: dict[str, Any]) -> AudioFormat:
        meta = FormatBase._from_info(entry)

        codec = entry.get("acodec") or ""

        return cls(
            **asdict(meta),
            audio_codec=codec if codec != "none" else "",
            bitrate=entry.get("abr") or 0,
        )

    def _format_dict(self) -> InfoDict:
        d = super()._format_dict()
        d |= {
            "acodec": self.audio_codec,
            "abr": self.bitrate,
        }
        return d


class FormatList(GenericList):
    """List of formats which can be filtered."""

    @cached_property
    def type(self) -> FORMAT_TYPE:
        """
        Determine main format type.
        It will check if is 'video' or 'audio'.
        """

        if self.filter(type="video"):
            return "video"
        elif self.filter(type="audio"):
            return "audio"
        else:
            return "video"

    def filter(
        self,
        type: FORMAT_TYPE | None = None,
        extension: str | None = None,
        codec: str | None = None,
        quality: int | None = None,
    ) -> FormatList:
        """Get filtered format list by options."""

        formats = self._list

        if type:
            match type:
                case "video":
                    selected = VideoFormat
                case "audio":
                    selected = AudioFormat

            formats = [f for f in formats if isinstance(f, selected)]
        if extension:
            formats = [f for f in formats if f.extension == extension]
        if quality:
            formats = [f for f in formats if f.quality == quality]
        if codec:
            formats = [f for f in formats if f.codec.startswith(codec)]

        return FormatList(formats)

    def sort_by(self, attribute: str, reverse: bool = False) -> FormatList:
        """Sort by `Format` attribute."""

        return FormatList(
            sorted(
                self._list,
                key=lambda f: getattr(f, attribute),
                reverse=reverse,
            )
        )

    def get_by_id(self, id: str) -> Format:
        """Get `Format` by `id`.

        Raises:
            IndexError: Provided id has not been founded.
        """

        if result := [f for f in self if f.id == id]:
            return result[0]
        else:
            raise IndexError(f"Format with id '{id}' has not been founded")

    def get_best_quality(self) -> Format:
        """Get `Format` with best quality."""

        formats = self.sort_by("quality")
        return formats[-1]

    def get_worst_quality(self) -> Format:
        """Get `Format` with worst quality."""

        formats = self.sort_by("quality")
        return formats[0]

    def get_closest_quality(self, quality: int) -> Format:
        """Get `Format` with closest quality."""

        qualities = [i.quality for i in self.sort_by("quality")]
        pos = bisect.bisect_left(qualities, quality)

        if pos == 0:
            return self[0]
        elif pos == len(self):
            return self[-1]
        else:
            before = self[pos - 1]
            after = self[pos]

            if after.quality - quality < quality - before.quality:
                return after
            else:
                return before

    @classmethod
    def _from_info(cls, info: InfoDict) -> FormatList:
        formats = []

        for format in info.get("formats") or {}:
            try:
                try:
                    fmt = VideoFormat._from_info(format)
                except ValueError:
                    fmt = AudioFormat._from_info(format)

                formats.append(fmt)
            except ValueError:
                continue

        return FormatList(formats)

    def __contains__(self, other) -> bool:
        if isinstance(other, Format):
            try:
                self.get_by_id(other.id)
                return True
            except IndexError:
                return False
        else:
            return False

    @overload
    def __getitem__(self, index: SupportsIndex) -> Format: ...

    @overload
    def __getitem__(self, index: slice) -> FormatList: ...

    def __getitem__(self, index):
        match index:
            case int():
                return self._list[index]
            case slice():
                return FormatList(self._list[index])
            case _:
                raise ValueError(index)

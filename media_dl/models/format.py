from __future__ import annotations

import bisect
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Annotated, Self, cast

from media_dl._ydl import FORMAT_TYPE, InfoDict, SupportedExtensions
from media_dl.models.base import GenericList

from pydantic import AfterValidator, BaseModel, Field


def validate_extension(value: str):
    if not (value in SupportedExtensions.video or value in SupportedExtensions.audio):
        raise ValueError(value, "not is a valid extension.")


Extension = Annotated[str, AfterValidator(validate_extension)]


class FormatBase(BaseModel):
    url: str
    id: Annotated[str, Field(alias="format_id")]
    filesize: int = 0
    extension: Annotated[Extension, Field(alias="ext")]
    downloader_options: Annotated[
        dict, Field(alias="downloader_options", default_factory=dict, repr=False)
    ]

    def _format_dict(self) -> InfoDict:
        d = self.model_dump(by_alias=True)
        d = cast(InfoDict, d)
        return d


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


class VideoFormat(Format):
    video_codec: str = Field(alias="vcodec")
    audio_codec: str = Field(alias="acodec")
    width: int = 0
    height: int = 0
    fps: int = 0

    @property
    def codec(self) -> str:
        return self.video_codec

    @property
    def quality(self) -> int:
        return self.height

    @property
    def display_quality(self) -> str:
        return str(self.height) + "p"


class AudioFormat(Format):
    audio_codec: str = Field(alias="acodec")
    bitrate: int = Field(alias="abr")

    @property
    def codec(self) -> str:
        return self.audio_codec

    @property
    def quality(self) -> int:
        return self.bitrate

    @property
    def display_quality(self) -> str:
        return str(round(self.bitrate)) + "kbps"


class FormatList(GenericList[AudioFormat | VideoFormat]):
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

        formats = self.root

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
                self.root,
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
    def _from_info(cls, info: InfoDict) -> Self:
        formats = []

        for format in info.get("formats") or {}:
            try:
                try:
                    fmt = VideoFormat(**format)
                except ValueError:
                    fmt = AudioFormat(**format)

                formats.append(fmt)
            except ValueError:
                continue

        return cls(formats)

    def __contains__(self, other) -> bool:
        if isinstance(other, FormatList):
            try:
                self.get_by_id(other.id)
                return True
            except IndexError:
                return False
        else:
            return False

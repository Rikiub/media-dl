from __future__ import annotations

import bisect
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Annotated, Generic, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    OnErrorOmit,
    SerializerFunctionWrapHandler,
    field_serializer,
    field_validator,
    model_serializer,
)
from typing_extensions import Self

from media_dl._ydl import SupportedExtensions
from media_dl.models.base import GenericList
from media_dl.types import FORMAT_TYPE


Codec = Annotated[str, AfterValidator(lambda v: None if v == "none" else v)]


class YDLArgs(BaseModel):
    downloader_options: Annotated[dict, Field(default_factory=dict, repr=False)]
    http_headers: Annotated[dict, Field(default_factory=dict, repr=False)]
    cookies: str | None = None


class Format(ABC, YDLArgs, BaseModel):
    """Base Format"""

    id: Annotated[str, Field(alias="format_id")]
    url: str
    protocol: str
    filesize: int | None = 0
    extension: Annotated[str, Field(alias="ext")]

    @property
    def codec(self) -> str: ...

    @property
    def quality(self) -> int: ...

    @property
    @abstractmethod
    def display_quality(self) -> str: ...


class VideoFormat(Format):
    extension: Annotated[str, Field(alias="ext")]
    video_codec: Annotated[Codec, Field(alias="vcodec")]
    audio_codec: Annotated[Codec | None, Field(alias="acodec")] = None
    width: int
    height: int
    fps: float = 0

    @property
    def codec(self) -> str:
        return self.video_codec

    @property
    def quality(self) -> int:
        return self.height

    @property
    def display_quality(self) -> str:
        return str(self.quality) + "p"

    @field_validator("extension")
    @classmethod
    def _validate_extension(cls, value) -> str:
        if value not in SupportedExtensions.video:
            raise ValueError(f"{value} not is a valid extension.")

        return value

    @field_serializer("audio_codec")
    def _none_to_str(self, value) -> str:
        if not value:
            return "none"

        return value


class AudioFormat(Format):
    extension: Annotated[str, Field(alias="ext")]
    audio_codec: Annotated[Codec, Field(alias="acodec")]
    bitrate: Annotated[float | None, Field(alias="abr")]

    @property
    def codec(self) -> str:
        return self.audio_codec

    @property
    def quality(self) -> int:
        if self.bitrate:
            return int(self.bitrate)
        else:
            return 0

    @property
    def display_quality(self) -> str:
        return str(round(self.quality)) + "kbps"

    @field_validator("extension")
    @classmethod
    def _validate_extension(cls, value) -> str:
        if value not in SupportedExtensions.audio:
            raise ValueError(f"{value} not is a valid extension.")

        return value

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler: SerializerFunctionWrapHandler):
        result: dict = handler(self)
        result |= {"vcodec": "none"}
        return result


FormatItem = OnErrorOmit[VideoFormat | AudioFormat]

T = TypeVar("T")


class FormatList(GenericList[FormatItem], Generic[T]):
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
    ) -> Self:
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

        return self.__class__(formats)

    def sort_by(self, attribute: str, reverse: bool = False) -> Self:
        """Sort by `Format` attribute."""

        return self.__class__(
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

    def __contains__(self, other) -> bool:
        if isinstance(other, Format):
            try:
                self.get_by_id(other.id)
                return True
            except IndexError:
                return False
        else:
            return False

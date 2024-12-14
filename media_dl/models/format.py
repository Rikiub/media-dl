from __future__ import annotations

import bisect
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Annotated, Generic, Literal, overload

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    OnErrorOmit,
    RootModel,
    SerializerFunctionWrapHandler,
    field_serializer,
    field_validator,
    model_serializer,
)
from typing_extensions import Self, TypeVar

from media_dl._ydl import SupportedExtensions
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
    @abstractmethod
    def quality(self) -> int: ...

    @property
    @abstractmethod
    def display_quality(self) -> str: ...


class VideoFormat(Format):
    video_codec: Annotated[Codec, Field(alias="vcodec")]
    audio_codec: Annotated[Codec | None, Field(alias="acodec")] = None
    width: int
    height: int
    fps: float | None = None

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
    codec: Annotated[Codec, Field(alias="acodec")]
    bitrate: Annotated[float, Field(alias="abr")] = 0

    @property
    def quality(self) -> int:
        return int(self.bitrate)

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


F = TypeVar("F", default=Format)
FormatType = OnErrorOmit[VideoFormat | AudioFormat]


class FormatList(RootModel[list[FormatType]], Generic[F]):
    """List of formats which can be filtered."""

    @overload
    def filter(
        self,
        type: Literal["video"],
        protocol: str | None = None,
        extension: str | None = None,
        codec: str | None = None,
        quality: int | None = None,
    ) -> FormatList[VideoFormat]: ...

    @overload
    def filter(
        self,
        type: Literal["audio"],
        protocol: str | None = None,
        extension: str | None = None,
        codec: str | None = None,
        quality: int | None = None,
    ) -> FormatList[AudioFormat]: ...

    @overload
    def filter(
        self,
        type: None = None,
        protocol: str | None = None,
        extension: str | None = None,
        codec: str | None = None,
        quality: int | None = None,
    ) -> FormatList[F]: ...

    def filter(
        self,
        type: FORMAT_TYPE | None = None,
        protocol: str | None = None,
        extension: str | None = None,
        codec: str | None = None,
        quality: int | None = None,
    ):
        """Get filtered formats by options."""

        formats = self.root
        selected = {"video": VideoFormat, "audio": AudioFormat}.get(str(type))

        filters = [
            (selected, lambda f: isinstance(f, selected)),  # type: ignore
            (extension, lambda f: f.extension == extension),
            (quality, lambda f: f.quality == quality),
            (codec, lambda f: f.codec.startswith(codec)),
            (protocol, lambda f: f.protocol == protocol),
        ]

        for value, condition in filters:
            if value:
                formats = [f for f in formats if condition(f)]

        if selected:
            return FormatList[selected](formats)
        else:
            return FormatList(formats)

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

    def sort_by(self, attribute: str, reverse: bool = False) -> Self:
        """Sort by `Format` attribute."""

        return self.__class__(
            sorted(
                self.root,
                key=lambda f: getattr(f, attribute),
                reverse=reverse,
            )
        )

    def get_by_id(self, id: str) -> F:
        """Get `Format` by `id`.

        Raises:
            IndexError: Provided id has not been founded.
        """

        if result := [f for f in self if f.id == id]:
            return result[0]  # type: ignore
        else:
            raise IndexError(f"Format with id '{id}' has not been founded")

    def get_best_quality(self) -> F:
        """Get `Format` with best quality."""

        formats = self.sort_by("quality")
        return formats[-1]

    def get_worst_quality(self) -> F:
        """Get `Format` with worst quality."""

        formats = self.sort_by("quality")
        return formats[0]

    def get_closest_quality(self, quality: int) -> F:
        """Get `Format` with closest quality."""

        qualities = [i.quality for i in self.sort_by("quality")]
        pos = bisect.bisect_left(qualities, quality)

        item = None

        if pos == 0:
            item = self[0]
        elif pos == len(self):
            item = self[-1]
        else:
            before = self[pos - 1]
            after = self[pos]

            if after.quality - quality < quality - before.quality:  # type: ignore
                item = after
            else:
                item = before

        return item

    def __contains__(self, other) -> bool:
        if isinstance(other, Format):
            try:
                self.get_by_id(other.id)
                return True
            except IndexError:
                return False
        else:
            return False

    def __iter__(self):  # type: ignore
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def __bool__(self) -> bool:
        return bool(self.root)

    @overload
    def __getitem__(self, index: int) -> F: ...

    @overload
    def __getitem__(self, index: slice) -> Self: ...

    def __getitem__(self, index) -> F | Self:
        match index:
            case int():
                return self.root[index]  # type: ignore
            case slice():
                return self.__class__(self.root[index])
            case _:
                raise TypeError(index)

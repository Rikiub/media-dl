from abc import ABC, abstractmethod
from pathlib import Path
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    SerializerFunctionWrapHandler,
    field_serializer,
    field_validator,
    model_serializer,
)

from media_dl.models.base import Serializable
from media_dl.models.progress.format import FormatDownloadCallback, FormatState
from media_dl.types import StrPath
from media_dl.ydl.downloader import download_format
from media_dl.ydl.types import SupportedExtensions, YDLFormatInfo

Codec = Annotated[str, AfterValidator(lambda v: None if v == "none" else v)]


class YDLArgs(BaseModel):
    downloader_options: Annotated[dict, Field(default_factory=dict, repr=False)]
    http_headers: Annotated[dict, Field(default_factory=dict, repr=False)]
    cookies: str | None = None


class Format(ABC, YDLArgs, Serializable):
    """Base Format"""

    id: Annotated[str, Field(alias="format_id")]
    url: str
    protocol: str
    filesize: int | None = None
    extension: Annotated[str, Field(alias="ext")]

    def download(
        self,
        filepath: StrPath,
        on_progress: FormatDownloadCallback | None = None,
    ) -> Path:
        state = FormatState()
        path = download_format(
            filepath,
            format_info=self.to_ydl_dict(),
            callback=lambda data: state._ydl_progress(
                data,
                on_progress,  # type: ignore
            )
            if on_progress
            else None,
        )
        return path

    @property
    @abstractmethod
    def quality(self) -> int: ...

    @property
    @abstractmethod
    def display_quality(self) -> str: ...

    def to_ydl_dict(self) -> YDLFormatInfo:
        return super().to_ydl_dict()


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


FormatType = VideoFormat | AudioFormat

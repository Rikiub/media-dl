from abc import ABC, abstractmethod
from pathlib import Path
from typing import Annotated, Literal
from typing_extensions import override

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    HttpUrl,
    SerializerFunctionWrapHandler,
    field_serializer,
    field_validator,
    model_serializer,
)

from media_dl.models.base import YDLSerializable
from media_dl.models.progress.format import FormatDownloadCallback, FormatState
from media_dl.types import StrPath
from media_dl.ydl.types import SupportedExtensions, YDLFormatInfo

Codec = Annotated[str, AfterValidator(lambda v: None if v == "none" else v)]
AudioCodecField = Field(alias="acodec")


class YDLArgs(BaseModel):
    downloader_options: Annotated[dict, Field(default_factory=dict, repr=False)]
    http_headers: Annotated[dict, Field(default_factory=dict, repr=False)]
    cookies: str | None = None


class Format(ABC, YDLArgs, YDLSerializable):
    """Base Format"""

    id: Annotated[str, Field(alias="format_id")]
    url: HttpUrl
    protocol: str
    extension: Annotated[str, Field(alias="ext")]
    filesize: int | None = None
    bitrate: Annotated[float, Field(alias="tbr")] = 0
    audio_codec: Annotated[Codec | None, AudioCodecField] = None

    def download(
        self,
        filepath: StrPath,
        on_progress: FormatDownloadCallback | None = None,
    ) -> Path:
        from media_dl.ydl.downloader import download_format

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

    def to_ydl_dict(self) -> YDLFormatInfo:
        return super().to_ydl_dict()

    @property
    @abstractmethod
    def quality(self) -> int: ...

    @property
    @abstractmethod
    def display_quality(self) -> str: ...

    @property
    def has_audio(self) -> bool:
        return bool(self.audio_codec)

    @field_serializer("audio_codec")
    def _serialize_acodec(self, value) -> str:
        return value if value else "none"


class AudioFormat(Format):
    type: Literal["audio"] = "audio"
    audio_codec: Annotated[  # type: ignore
        Codec, AudioCodecField
    ]

    @property
    @override
    def quality(self) -> int:
        return int(self.bitrate)

    @property
    @override
    def display_quality(self) -> str:
        return str(round(self.quality)) + "kbps"

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler: SerializerFunctionWrapHandler):
        result: dict = handler(self)
        result |= {"vcodec": "none"}
        return result

    @field_validator("extension")
    @classmethod
    def _validate_extension(cls, value) -> str:
        if value not in SupportedExtensions.audio:
            raise ValueError(f"{value} not is a valid extension.")
        return value


class VideoFormat(Format):
    video_codec: Annotated[Codec, Field(alias="vcodec")]
    type: Literal["video"] = "video"
    width: int
    height: int
    fps: float | None = None

    @property
    @override
    def quality(self) -> int:
        return self.height

    @property
    @override
    def display_quality(self) -> str:
        return str(self.quality) + "p"

    @field_validator("extension")
    @classmethod
    def _validate_extension(cls, value) -> str:
        if value not in SupportedExtensions.video:
            raise ValueError(f"{value} not is a valid extension.")
        return value

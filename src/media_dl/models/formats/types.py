from abc import ABC, abstractmethod
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

from media_dl.ydl.types import SupportedExtensions, YDLExtractInfo

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
    filesize: int | None = None
    extension: Annotated[str, Field(alias="ext")]

    @property
    @abstractmethod
    def quality(self) -> int: ...

    @property
    @abstractmethod
    def display_quality(self) -> str: ...

    def as_info_dict(self) -> YDLExtractInfo:
        return self.model_dump(by_alias=True)


class VideoFormat(Format):
    video_codec: Annotated[Codec, Field(validation_alias="vcodec")]
    audio_codec: Annotated[Codec | None, Field(validation_alias="acodec")] = None
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
    codec: Annotated[Codec, Field(alias="audio_codec", validation_alias="acodec")]
    bitrate: Annotated[float, Field(validation_alias="abr")] = 0

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

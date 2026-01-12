from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal

from pydantic import Field

from media_dl.models.content.media import LazyMedia, Media
from media_dl.models.formats.types import AudioFormat, VideoFormat
from media_dl.models.progress.base import HasFile, State
from media_dl.models.progress.format import FormatState
from media_dl.models.progress.processor import ProcessingState


class ExtractingState(State):
    status: Literal["extracting"] = "extracting"
    media: LazyMedia


class ResolvedState(State):
    status: Literal["resolved"] = "resolved"
    media: Media


class DownloadingState(FormatState, State):
    status: Literal["downloading"] = "downloading"


class MergingState(State):
    status: Literal["merging"] = "merging"

    video_format: VideoFormat
    audio_format: AudioFormat


class ErrorState(State):
    status: Literal["error"] = "error"
    message: str


class SkippedState(HasFile):
    status: Literal["skipped"] = "skipped"


class CompletedState(HasFile):
    status: Literal["completed"] = "completed"


ProgressState = Annotated[
    ExtractingState
    | ResolvedState
    | DownloadingState
    | MergingState
    | ProcessingState
    | ErrorState
    | SkippedState
    | CompletedState,
    Field(discriminator="status"),
]


ProgressDownloadCallback = Callable[[ProgressState], None]

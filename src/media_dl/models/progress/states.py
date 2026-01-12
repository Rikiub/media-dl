from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal

from pydantic import Field

from media_dl.models.formats.types import AudioFormat, VideoFormat
from media_dl.models.progress.base import HasFile, State
from media_dl.models.progress.format import FormatState
from media_dl.models.progress.processor import ProcessingState
from media_dl.models.stream import LazyStream, Stream


class ExtractingState(State):
    status: Literal["extracting"] = "extracting"
    stream: LazyStream


class ResolvedState(State):
    status: Literal["resolved"] = "resolved"
    stream: Stream


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

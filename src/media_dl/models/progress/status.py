from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Literal, Annotated

from pydantic import BaseModel, Field

from media_dl.models.formats.types import AudioFormat, VideoFormat
from media_dl.models.progress.format import FormatsContainer
from media_dl.models.stream import LazyStream, Stream


class HasFile(BaseModel):
    filepath: Path


class State(BaseModel): ...


class ExtractingState(State):
    status: Literal["extracting"] = "extracting"
    stream: LazyStream


class ResolvedState(State):
    status: Literal["resolved"] = "resolved"
    stream: Stream


class DownloadingState(FormatsContainer, State):
    status: Literal["downloading"] = "downloading"


class MergingState(State):
    status: Literal["merging"] = "merging"

    video_format: VideoFormat
    audio_format: AudioFormat


class ErrorState(State):
    status: Literal["error"] = "error"
    message: str


class ProcessingState(HasFile, State):
    status: Literal["processing"] = "processing"


class SkippedState(HasFile, State):
    status: Literal["skipped"] = "skipped"


class CompletedState(HasFile, State):
    status: Literal["completed"] = "completed"


ProgressStatus = Annotated[
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


ProgressDownloadCallback = Callable[[ProgressStatus], None]

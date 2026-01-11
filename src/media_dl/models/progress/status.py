from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Literal, Annotated


from pydantic import BaseModel, Field

from media_dl.models.progress.format import FormatsContainer
from media_dl.models.stream import LazyStream, Stream


class HasFile(BaseModel):
    filepath: Path


class State(BaseModel): ...


class FetchingState(State):
    status: Literal["fetching"] = "fetching"
    stream: LazyStream


class ReadyState(State):
    status: Literal["ready"] = "ready"
    stream: Stream


class DownloadingState(FormatsContainer, State):
    status: Literal["downloading"] = "downloading"


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
    FetchingState
    | ReadyState
    | DownloadingState
    | ProcessingState
    | ErrorState
    | SkippedState
    | CompletedState,
    Field(discriminator="status"),
]


ProgressDownloadCallback = Callable[[ProgressStatus], None]

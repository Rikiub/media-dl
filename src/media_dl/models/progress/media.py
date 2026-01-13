from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal

from pydantic import Field

from media_dl.models.content.media import LazyMedia, Media
from media_dl.models.progress.base import HasFile, State
from media_dl.models.progress.format import FormatState
from media_dl.models.progress.processor import ProcessingState


class ResolvingState(State):
    status: Literal["resolving"] = "resolving"
    media: LazyMedia


class ResolvedState(State):
    status: Literal["resolved"] = "resolved"
    media: Media


class DownloadingState(FormatState, State):
    status: Literal["downloading"] = "downloading"


class ErrorState(State):
    status: Literal["error"] = "error"
    message: str


class SkippedState(HasFile):
    status: Literal["skipped"] = "skipped"


class CompletedState(HasFile):
    status: Literal["completed"] = "completed"


MediaDownloadState = Annotated[
    ResolvingState
    | ResolvedState
    | DownloadingState
    | ProcessingState
    | ErrorState
    | SkippedState
    | CompletedState,
    Field(discriminator="status"),
]


MediaDownloadCallback = Callable[[MediaDownloadState], None]

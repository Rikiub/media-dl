from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal

from pydantic import Field

from remora.models.content.media import LazyMedia, Media
from remora.models.progress.base import HasFile, State
from remora.models.progress.format import FormatState
from remora.models.progress.processor import ProcessingState


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


class CompletedState(HasFile):
    status: Literal["completed"] = "completed"
    reason: Literal["skipped", "error", "completed"]


MediaDownloadState = Annotated[
    ResolvingState
    | ResolvedState
    | DownloadingState
    | ProcessingState
    | ErrorState
    | CompletedState,
    Field(discriminator="status"),
]


MediaDownloadCallback = Callable[[MediaDownloadState], None]

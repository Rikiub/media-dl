from typing import Callable, Literal

from remora.models.progress.base import StageType, State


class PlaylistState(State):
    stage: Literal[StageType, "update"]

    completed: int
    total: int


PlaylistDownloadState = PlaylistState
PlaylistDownloadCallback = Callable[[PlaylistState], None]

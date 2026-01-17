from typing import Callable, Literal

from media_dl.models.progress.base import StageType, State


class PlaylistState(State):
    stage: Literal[StageType, "update"]

    completed: int
    total: int


PlaylistDownloadCallback = Callable[[PlaylistState], None]

from collections.abc import Callable
from typing import Annotated
from typing_extensions import Self
from pydantic import BaseModel, Field

from media_dl.types import FORMAT_TYPE


class FormatStatus(BaseModel):
    type: FORMAT_TYPE

    speed: float = 0
    elapsed: float = 0

    downloaded_bytes: float = 0
    total_bytes: float = 0

    def _ydl_progress(self, data: dict, callback: Callable[[Self], None]) -> None:
        """`YT-DLP` progress hook, but stable and without issues."""

        d = data

        match d["status"]:
            case "downloading":
                self._ydl_on_downloading(data)
            case "finished":
                self.downloaded_bytes = self.total_bytes
                self.total_bytes = self.downloaded_bytes

        callback(self)

    def _ydl_on_downloading(self, d: dict):
        self.downloaded_bytes = d.get("downloaded_bytes") or 0
        total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

        if total_bytes > self.total_bytes:
            self.total_bytes = total_bytes

        self.speed = d.get("speed") or 0
        self.elapsed = d.get("elapsed") or 0


class VideoFormatStatus(FormatStatus):
    fragments_completed: Annotated[int, Field(alias="fragment_index")] = 0
    """Available if `type` is video."""
    fragments_total: Annotated[int, Field(alias="fragment_count")] = 0
    """Available if `type` is video."""

    def _ydl_on_downloading(self, d: dict):
        super()._ydl_on_downloading(d)
        self.fragments_completed = d.get("fragment_index") or 0
        self.fragments_total = d.get("fragment_count") or 0


class FormatsContainer(BaseModel):
    video_format: VideoFormatStatus | None = None
    audio_format: FormatStatus | None = None

    current_step: FORMAT_TYPE
    steps_completed: int = 0
    steps_total: int = 1

    @property
    def completed(self) -> bool:
        return self.steps_completed >= self.steps_total

    @property
    def speed(self) -> float:
        if self.video_format:
            return self.video_format.speed
        elif self.audio_format:
            return self.audio_format.speed
        else:
            return 0

    @property
    def elapsed(self) -> float:
        if self.video_format:
            return self.video_format.elapsed
        elif self.audio_format:
            return self.audio_format.elapsed
        else:
            return 0

    @property
    def downloaded_bytes(self) -> float:
        current_bytes = 0

        if self.video_format:
            current_bytes += self.video_format.downloaded_bytes
        if self.audio_format:
            current_bytes += self.audio_format.downloaded_bytes

        return current_bytes

    @property
    def total_bytes(self) -> float:
        current_bytes = 0

        if self.video_format:
            current_bytes += self.video_format.downloaded_bytes
        if self.audio_format:
            current_bytes += self.audio_format.downloaded_bytes

        return current_bytes


FormatDownloadCallback = Callable[[FormatStatus], None]
